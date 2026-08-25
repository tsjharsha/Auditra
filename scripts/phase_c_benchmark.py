from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
import tracemalloc
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import ValidationError

from auditra.agent_tools import DatasetIndex
from auditra.evaluator import IndependentEvaluator
from auditra.models import ControllerRun, DatasetBundle, EvaluationRun, ReconciliationStatus, ScenarioMode, ScenarioRequest, money
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


TERMINAL_REVIEW = {ReconciliationStatus.HUMAN_REVIEW.value, ReconciliationStatus.UNRESOLVED.value}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase C adversarial scale benchmark.")
    parser.add_argument("--counts", nargs="*", type=int, default=[100, 500, 1000, 5000, 10000, 50000])
    parser.add_argument("--mode", choices=[item.value for item in ScenarioMode], default=ScenarioMode.MIXED.value)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="phase_c_benchmark.json")
    args = parser.parse_args()

    rows = []
    generator = ScenarioGenerator()
    evaluator = IndependentEvaluator()

    for count in args.counts:
        try:
            generation_started = time.perf_counter()
            tracemalloc.start()
            dataset = generator.generate(ScenarioRequest(mode=ScenarioMode(args.mode), record_count=count, seed=args.seed))
            _, generation_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            generation_ms = elapsed_ms(generation_started)
        except ValidationError as exc:
            rows.append(
                {
                    "records": count,
                    "mode": "not_run",
                    "status": "rejected_by_input_contract",
                    "error": str(exc).splitlines()[0],
                    "max_supported_records": 10000,
                }
            )
            continue

        normalization_started = time.perf_counter()
        DatasetIndex(dataset)
        normalization_ms = elapsed_ms(normalization_started)

        for label, enable_ai in (("deterministic_only", False), ("ai_assisted", True)):
            gc.collect()
            row_started = time.perf_counter()
            tracemalloc.start()
            try:
                controller = ReconciliationEngine(enable_ai=enable_ai)
                run_started = time.perf_counter()
                run = controller.run(dataset)
                reconciliation_ms = elapsed_ms(run_started)
                evaluation_started = time.perf_counter()
                evaluation = evaluator.evaluate(dataset, run)
                evaluation_ms = elapsed_ms(evaluation_started)
                _, peak = tracemalloc.get_traced_memory()
                rows.append(
                    {
                        "records": count,
                        "mode": label,
                        "status": "completed",
                        "seed": args.seed,
                        "scenario_mode": args.mode,
                        "generation_ms": generation_ms,
                        "generation_peak_kb": round(generation_peak / 1024, 2),
                        "normalization_ms": normalization_ms,
                        "controller_reported_normalization_ms": run.metrics.normalization_ms,
                        "reconciliation_ms": reconciliation_ms,
                        "ai_investigation_ms": run.metrics.ai_investigation_ms,
                        "database_ms": 0.0,
                        "database_enabled": bool(os.getenv("AUDITRA_DATABASE_URL")),
                        "evaluation_ms": evaluation_ms,
                        "total_ms": elapsed_ms(row_started) + generation_ms,
                        "throughput_records_per_sec": run.metrics.throughput_records_per_sec,
                        "peak_memory_kb": round(peak / 1024, 2),
                        "accuracy": evaluation.metrics.accuracy,
                        "precision": evaluation.metrics.precision,
                        "recall": evaluation.metrics.recall,
                        "f1": evaluation.metrics.f1,
                        "failures": len(evaluation.failures),
                        "review_count": sum(1 for case in run.cases if str(case.status) in TERMINAL_REVIEW),
                        "ai_investigations": run.metrics.ai_investigation_count,
                        "ai_invocation_rate": run.metrics.ai_invocation_rate,
                        "llm_calls": run.metrics.llm_calls,
                        "agent_tool_calls": run.metrics.agent_tool_calls,
                        "estimated_ai_cost_usd": str(run.metrics.estimated_ai_cost_usd),
                        "cost_per_case_usd": cost_per_case(run),
                        "cost_per_1000_cases_usd": cost_per_1000(run),
                        "p50_latency_ms": run.metrics.median_latency_ms,
                        "p95_latency_ms": run.metrics.p95_latency_ms,
                        "p99_latency_ms": run.metrics.p99_latency_ms,
                        "failure_taxonomy": evaluation.metrics.failure_taxonomy,
                        "class_confusion": class_confusion(evaluation),
                        "financial_confusion": financial_confusion(dataset, run),
                    }
                )
            except Exception as exc:
                _, peak = tracemalloc.get_traced_memory()
                rows.append(
                    {
                        "records": count,
                        "mode": label,
                        "status": "failed",
                        "seed": args.seed,
                        "scenario_mode": args.mode,
                        "generation_ms": generation_ms,
                        "normalization_ms": normalization_ms,
                        "total_ms": elapsed_ms(row_started) + generation_ms,
                        "peak_memory_kb": round(peak / 1024, 2),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
            finally:
                tracemalloc.stop()

    report = {
        "benchmark": "phase_c_scale",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "database_note": "AUDITRA_DATABASE_URL not configured; database_ms is 0.0 for direct in-memory benchmarks."
        if not os.getenv("AUDITRA_DATABASE_URL")
        else "PostgreSQL is configured; this script measures controller path directly, not API storage writes.",
        "rows": rows,
    }
    write_report(args.output, report)
    print(json.dumps(report, indent=2))
    return 0


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 4)


def cost_per_case(run: ControllerRun) -> str:
    return str(money(run.metrics.estimated_ai_cost_usd / Decimal(max(run.metrics.transactions_processed, 1))))


def cost_per_1000(run: ControllerRun) -> str:
    return str(money((run.metrics.estimated_ai_cost_usd / Decimal(max(run.metrics.transactions_processed, 1))) * Decimal("1000")))


def class_confusion(evaluation: EvaluationRun) -> Dict[str, Dict[str, int]]:
    matrix = evaluation.metrics.confusion_matrix
    labels = sorted(
        label
        for label in matrix
        if sum(matrix[label].values()) > 0 or any(row.get(label, 0) > 0 for row in matrix.values())
    )
    total = sum(sum(row.values()) for row in matrix.values())
    rows: Dict[str, Dict[str, int]] = {}
    for label in labels:
        tp = matrix.get(label, {}).get(label, 0)
        fp = sum(row.get(label, 0) for expected, row in matrix.items() if expected != label)
        fn = sum(count for predicted, count in matrix.get(label, {}).items() if predicted != label)
        rows[label] = {"tp": tp, "tn": total - tp - fp - fn, "fp": fp, "fn": fn}
    return rows


def financial_confusion(dataset: DatasetBundle, run: ControllerRun) -> Dict[str, str]:
    payments = {payment.payment_id: payment for payment in dataset.payments}
    totals = {
        "correctly_resolved": Decimal("0.00"),
        "falsely_resolved": Decimal("0.00"),
        "correctly_escalated": Decimal("0.00"),
        "incorrectly_escalated": Decimal("0.00"),
    }
    for case in run.cases:
        truth = dataset.ground_truth.get(case.payment_id)
        payment = payments.get(case.payment_id)
        if truth is None or payment is None:
            continue
        expected = str(truth.expected_status)
        predicted = str(case.status)
        predicted_review = predicted in TERMINAL_REVIEW
        expected_review = expected in TERMINAL_REVIEW
        if predicted_review and expected_review:
            totals["correctly_escalated"] += payment.amount
        elif predicted_review and not expected_review:
            totals["incorrectly_escalated"] += payment.amount
        elif not predicted_review and expected == predicted:
            totals["correctly_resolved"] += payment.amount
        else:
            totals["falsely_resolved"] += payment.amount
    return {key: str(money(value)) for key, value in totals.items()}


def write_report(filename: str, payload: Dict[str, Any]) -> None:
    out_path = ROOT / "evaluation" / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

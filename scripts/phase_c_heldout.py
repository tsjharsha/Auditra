from __future__ import annotations

import argparse
import json
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.evaluator import IndependentEvaluator
from auditra.financial_world import FinancialWorldService, FinancialWorldSpec
from auditra.financial_world.models import AnomalyMode
from auditra.models import ControllerRun, EvaluationRun
from auditra.reconciliation import ReconciliationEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase C held-out benchmark without tuning against the results.")
    parser.add_argument("--records-per-slice", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42000)
    args = parser.parse_args()

    service = FinancialWorldService()
    evaluator = IndependentEvaluator()
    rows = []
    for idx, spec in enumerate(slice_specs(args.records_per_slice, args.seed), start=1):
        world = service.build_from_spec(spec)
        for label, enable_ai in (("deterministic_only", False), ("ai_assisted", True)):
            run = ReconciliationEngine(enable_ai=enable_ai).run(world.dataset)
            evaluation = evaluator.evaluate(world.dataset, run)
            rows.append(
                {
                    "slice": spec.world_name,
                    "slice_index": idx,
                    "mode": label,
                    "world_id": world.world_id,
                    "dataset_id": world.dataset_id,
                    "records": run.metrics.transactions_processed,
                    "accuracy": evaluation.metrics.accuracy,
                    "precision": evaluation.metrics.precision,
                    "recall": evaluation.metrics.recall,
                    "f1": evaluation.metrics.f1,
                    "failures": len(evaluation.failures),
                    "failure_taxonomy": evaluation.metrics.failure_taxonomy,
                    "class_metrics": evaluation.metrics.class_metrics,
                    "financial_impact_of_errors": str(evaluation.metrics.financial_impact_of_errors),
                    "incorrectly_classified_amount": str(evaluation.metrics.financial_amount_incorrectly_classified),
                    "human_review_rate": run.metrics.human_review_rate,
                    "ai_invocation_rate": run.metrics.ai_invocation_rate,
                    "llm_calls": run.metrics.llm_calls,
                    "agent_tool_calls": run.metrics.agent_tool_calls,
                    "estimated_ai_cost_usd": str(run.metrics.estimated_ai_cost_usd),
                    "p50_latency_ms": run.metrics.median_latency_ms,
                    "p95_latency_ms": run.metrics.p95_latency_ms,
                    "p99_latency_ms": run.metrics.p99_latency_ms,
                    "financial_confusion": financial_confusion(world.dataset, run),
                }
            )

    report = {
        "benchmark": "phase_c_heldout",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_records_per_mode": sum(row["records"] for row in rows if row["mode"] == "ai_assisted"),
        "note": "Fixed seeds and specs are treated as held-out. Do not tune controller thresholds against this file.",
        "aggregate": aggregate(rows),
        "rows": rows,
    }
    out_path = ROOT / "evaluation" / "phase_c_heldout.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def slice_specs(records: int, seed: int) -> List[FinancialWorldSpec]:
    return [
        FinancialWorldSpec(
            prompt="Held-out normal ecommerce controls.",
            world_name="Heldout Normal",
            merchant_name="Heldout Normal Merchant",
            record_count=records,
            seed=seed + 1,
            anomaly_mode=AnomalyMode.NORMAL,
            anomaly_rates={},
        ),
        FinancialWorldSpec(
            prompt="Held-out easy amount and settlement anomalies.",
            world_name="Heldout Easy",
            merchant_name="Heldout Easy Merchant",
            record_count=records,
            seed=seed + 2,
            anomaly_mode=AnomalyMode.STRESSED,
            anomaly_rates={"AMOUNT_MISMATCH": "0.0200", "MISSING_SETTLEMENT": "0.0200", "TIMING_MISMATCH": "0.0100"},
        ),
        FinancialWorldSpec(
            prompt="Held-out hard refund, partial settlement and fee anomalies.",
            world_name="Heldout Hard",
            merchant_name="Heldout Hard Merchant",
            record_count=records,
            seed=seed + 3,
            anomaly_mode=AnomalyMode.STRESSED,
            anomaly_rates={
                "AMOUNT_MISMATCH": "0.0500",
                "FEE_MISMATCH": "0.0400",
                "REFUND_MISMATCH": "0.0400",
                "PARTIAL_SETTLEMENT": "0.0400",
                "TIMING_MISMATCH": "0.0300",
            },
        ),
        FinancialWorldSpec(
            prompt="Held-out adversarial duplicate, missing and conflicting evidence cases.",
            world_name="Heldout Adversarial",
            merchant_name="Heldout Adversarial Merchant",
            record_count=records,
            seed=seed + 4,
            anomaly_mode=AnomalyMode.ADVERSARIAL,
            anomaly_rates={
                "AMOUNT_MISMATCH": "0.0600",
                "MISSING_SETTLEMENT": "0.0500",
                "DUPLICATE_PAYMENT": "0.0500",
                "CONFLICTING_EVIDENCE": "0.0500",
                "TIMING_MISMATCH": "0.0400",
            },
        ),
        FinancialWorldSpec(
            prompt="Held-out multi-factor settlement and refund stress.",
            world_name="Heldout Multi Factor",
            merchant_name="Heldout Multi Factor Merchant",
            record_count=records,
            seed=seed + 5,
            anomaly_mode=AnomalyMode.CHAOS,
            anomaly_rates={
                "AMOUNT_MISMATCH": "0.0600",
                "MISSING_SETTLEMENT": "0.0500",
                "DUPLICATE_PAYMENT": "0.0400",
                "FEE_MISMATCH": "0.0500",
                "REFUND_MISMATCH": "0.0500",
                "PARTIAL_SETTLEMENT": "0.0500",
                "TIMING_MISMATCH": "0.0500",
                "CONFLICTING_EVIDENCE": "0.0500",
            },
        ),
        FinancialWorldSpec(
            prompt="Held-out ambiguous and unresolved relationship/currency attacks.",
            world_name="Heldout Ambiguous Unresolved",
            merchant_name="Heldout Ambiguous Merchant",
            record_count=records,
            seed=seed + 6,
            anomaly_mode=AnomalyMode.CHAOS,
            anomaly_rates={
                "CONFLICTING_EVIDENCE": "0.0700",
                "CURRENCY_MISMATCH": "0.0500",
                "ENTITY_LINK_FAILURE": "0.0500",
                "MISSING_SETTLEMENT": "0.0400",
                "REFUND_MISMATCH": "0.0400",
                "TIMING_MISMATCH": "0.0400",
            },
        ),
    ]


def aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_mode: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_mode.setdefault(str(row["mode"]), []).append(row)
    result: Dict[str, Dict[str, Any]] = {}
    for mode, mode_rows in by_mode.items():
        records = sum(int(row["records"]) for row in mode_rows)
        result[mode] = {
            "records": records,
            "weighted_accuracy": weighted(mode_rows, "accuracy"),
            "weighted_precision": weighted(mode_rows, "precision"),
            "weighted_recall": weighted(mode_rows, "recall"),
            "weighted_f1": weighted(mode_rows, "f1"),
            "failures": sum(int(row["failures"]) for row in mode_rows),
            "financial_impact_of_errors": str(sum_decimal(mode_rows, "financial_impact_of_errors")),
            "incorrectly_classified_amount": str(sum_decimal(mode_rows, "incorrectly_classified_amount")),
            "estimated_ai_cost_usd": str(sum_decimal(mode_rows, "estimated_ai_cost_usd")),
            "llm_calls": sum(int(row["llm_calls"]) for row in mode_rows),
            "agent_tool_calls": sum(int(row["agent_tool_calls"]) for row in mode_rows),
        }
    return result


def weighted(rows: List[Dict[str, Any]], key: str) -> float:
    total = sum(int(row["records"]) for row in rows)
    return round(sum(float(row[key]) * int(row["records"]) for row in rows) / max(total, 1), 4)


def sum_decimal(rows: List[Dict[str, Any]], key: str) -> Decimal:
    return sum((Decimal(str(row[key])) for row in rows), Decimal("0.00"))


def financial_confusion(dataset, run: ControllerRun) -> Dict[str, str]:
    terminal_review = {"HUMAN_REVIEW", "UNRESOLVED"}
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
        if predicted in terminal_review and expected in terminal_review:
            totals["correctly_escalated"] += payment.amount
        elif predicted in terminal_review and expected not in terminal_review:
            totals["incorrectly_escalated"] += payment.amount
        elif predicted not in terminal_review and predicted == expected:
            totals["correctly_resolved"] += payment.amount
        else:
            totals["falsely_resolved"] += payment.amount
    return {key: str(value.quantize(Decimal("0.01"))) for key, value in totals.items()}


if __name__ == "__main__":
    raise SystemExit(main())

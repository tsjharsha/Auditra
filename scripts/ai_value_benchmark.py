from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.evaluator import IndependentEvaluator
from auditra.financial_world import FinancialWorldService
from auditra.models import ControllerRun, DatasetBundle, EvaluationRun
from auditra.reconciliation import ReconciliationEngine


PROMPT_TEMPLATE = (
    "Generate an Indian e-commerce merchant with {records} orders, UPI and card payments, "
    "2% platform fees, T+2 settlement, refunds, refund mismatches, partial settlements, "
    "duplicates, timing issues and conflicting evidence."
)


def run_controller(dataset: DatasetBundle, label: str, enable_ai: bool) -> Dict[str, Any]:
    controller_run = ReconciliationEngine(enable_ai=enable_ai).run(dataset)
    evaluation = IndependentEvaluator().evaluate(dataset, controller_run)
    return {
        "label": label,
        "controller_run_id": controller_run.run_id,
        "run": controller_run,
        "evaluation": evaluation,
        "summary": summarize(controller_run, evaluation),
    }


def summarize(controller_run: ControllerRun, evaluation: EvaluationRun) -> Dict[str, Any]:
    metrics = evaluation.metrics
    return {
        "records": controller_run.metrics.transactions_processed,
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "failures": len(evaluation.failures),
        "failure_taxonomy": metrics.failure_taxonomy,
        "class_metrics": metrics.class_metrics,
        "match_rate": metrics.match_rate,
        "automatic_resolution_rate": metrics.automatic_resolution_rate,
        "escalation_rate": metrics.escalation_rate,
        "unresolved_rate": metrics.unresolved_rate,
        "throughput_records_per_sec": metrics.throughput_records_per_sec,
        "median_latency_ms": metrics.median_latency_ms,
        "p95_latency_ms": metrics.p95_latency_ms,
        "p99_latency_ms": metrics.p99_latency_ms,
        "ai_investigations": controller_run.metrics.ai_investigation_count,
        "ai_invocation_rate": controller_run.metrics.ai_invocation_rate,
        "llm_calls": metrics.llm_calls,
        "agent_tool_calls": metrics.agent_tool_calls,
        "estimated_ai_cost_usd": str(metrics.estimated_ai_cost_usd),
        "financial_amount_incorrectly_classified": str(metrics.financial_amount_incorrectly_classified),
        "financial_impact_of_errors": str(metrics.financial_impact_of_errors),
    }


def class_lift(baseline: EvaluationRun, ai: EvaluationRun) -> Dict[str, Dict[str, float]]:
    labels = sorted(set(baseline.metrics.class_metrics) | set(ai.metrics.class_metrics))
    rows: Dict[str, Dict[str, float]] = {}
    for label in labels:
        base = baseline.metrics.class_metrics.get(label, {})
        assisted = ai.metrics.class_metrics.get(label, {})
        rows[label] = {
            "support": assisted.get("support", base.get("support", 0.0)),
            "baseline_precision": base.get("precision", 0.0),
            "ai_precision": assisted.get("precision", 0.0),
            "precision_lift": round(assisted.get("precision", 0.0) - base.get("precision", 0.0), 4),
            "baseline_recall": base.get("recall", 0.0),
            "ai_recall": assisted.get("recall", 0.0),
            "recall_lift": round(assisted.get("recall", 0.0) - base.get("recall", 0.0), 4),
            "baseline_f1": base.get("f1", 0.0),
            "ai_f1": assisted.get("f1", 0.0),
            "f1_lift": round(assisted.get("f1", 0.0) - base.get("f1", 0.0), 4),
        }
    return rows


def decimal_delta(left: Decimal, right: Decimal) -> str:
    return str(left - right)


def build_report(records: int, seed: int) -> Dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(records=records)
    world = FinancialWorldService().build_from_prompt(prompt, seed=seed)
    if world.dataset is None:
        raise RuntimeError("world builder did not return an auditable dataset")

    baseline = run_controller(world.dataset, "deterministic_only", enable_ai=False)
    ai = run_controller(world.dataset, "ai_assisted", enable_ai=True)
    base_eval = baseline["evaluation"]
    ai_eval = ai["evaluation"]

    return {
        "benchmark": "phase_a_ai_value",
        "prompt": prompt,
        "seed": seed,
        "world_id": world.world_id,
        "dataset_id": world.dataset_id,
        "world_summary": world.summary.model_dump(mode="json"),
        "deterministic_only": baseline["summary"],
        "ai_assisted": ai["summary"],
        "lift": {
            "accuracy": round(ai_eval.metrics.accuracy - base_eval.metrics.accuracy, 4),
            "precision": round(ai_eval.metrics.precision - base_eval.metrics.precision, 4),
            "recall": round(ai_eval.metrics.recall - base_eval.metrics.recall, 4),
            "f1": round(ai_eval.metrics.f1 - base_eval.metrics.f1, 4),
            "failures_reduced": len(base_eval.failures) - len(ai_eval.failures),
            "failure_rate_reduction": round((len(base_eval.failures) - len(ai_eval.failures)) / max(len(base_eval.failures), 1), 4),
            "escalation_rate_reduction": round(base_eval.metrics.escalation_rate - ai_eval.metrics.escalation_rate, 4),
            "financial_error_impact_reduction": decimal_delta(
                base_eval.metrics.financial_impact_of_errors,
                ai_eval.metrics.financial_impact_of_errors,
            ),
            "incorrectly_classified_amount_reduction": decimal_delta(
                base_eval.metrics.financial_amount_incorrectly_classified,
                ai_eval.metrics.financial_amount_incorrectly_classified,
            ),
            "p95_latency_ms_delta": round(ai_eval.metrics.p95_latency_ms - base_eval.metrics.p95_latency_ms, 4),
            "tool_call_delta": ai_eval.metrics.agent_tool_calls - base_eval.metrics.agent_tool_calls,
            "llm_call_delta": ai_eval.metrics.llm_calls - base_eval.metrics.llm_calls,
            "ai_invocation_rate": ai["run"].metrics.ai_invocation_rate,
            "estimated_ai_cost_usd": str(ai_eval.metrics.estimated_ai_cost_usd),
        },
        "class_lift": class_lift(base_eval, ai_eval),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure Phase A AI value on a prompt-built financial world.")
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    report = build_report(records=args.records, seed=args.seed)
    out_path = ROOT / "evaluation" / "ai_value_benchmark.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

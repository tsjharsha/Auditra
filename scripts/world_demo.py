from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.evaluator import IndependentEvaluator
from auditra.financial_world import FinancialWorldService
from auditra.reconciliation import ReconciliationEngine


DEFAULT_PROMPT = (
    "Generate an Indian e-commerce merchant with 500 orders, UPI and card payments, "
    "2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies."
)


def summarize_comparison(rows: list[dict]) -> list[dict]:
    return [
        {
            "mode": row["mode"],
            "accuracy": row["metrics"].accuracy,
            "precision": row["metrics"].precision,
            "recall": row["metrics"].recall,
            "f1": row["metrics"].f1,
            "auto_resolution": row["metrics"].automatic_resolution_rate,
            "human_review": row["metrics"].escalation_rate,
            "throughput": row["controller"].metrics.throughput_records_per_sec,
            "p95_latency_ms": row["controller"].metrics.p95_latency_ms,
            "llm_calls": row["controller"].metrics.llm_calls,
            "tool_calls": row["controller"].metrics.agent_tool_calls,
            "estimated_ai_cost_usd": str(row["controller"].metrics.estimated_ai_cost_usd),
            "failures": len(row["evaluation"].failures),
        }
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Auditra prompt-to-world-to-audit demo.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    service = FinancialWorldService()
    world = service.build_from_prompt(args.prompt, seed=args.seed)
    evaluator = IndependentEvaluator()
    comparison = []
    for label, enable_ai in (("deterministic_only", False), ("ai_assisted", True)):
        controller = ReconciliationEngine(enable_ai=enable_ai)
        run = controller.run(world.dataset)
        evaluation = evaluator.evaluate(world.dataset, run)
        comparison.append({"mode": label, "controller": run, "evaluation": evaluation, "metrics": evaluation.metrics})

    ai_row = comparison[-1]
    summary = {
        "world": service.public_build_result(world),
        "controller_run_id": ai_row["controller"].run_id,
        "evaluation_run_id": ai_row["evaluation"].evaluation_run_id,
        "evaluation": ai_row["evaluation"].metrics.model_dump(mode="json"),
        "comparison": summarize_comparison(comparison),
        "survival_status": "CONTROLLER SURVIVED" if not ai_row["evaluation"].failures else f"CONTROLLER FAILED {len(ai_row['evaluation'].failures)} CASES",
    }

    out_dir = ROOT / "data" / "world_demo"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest_world_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

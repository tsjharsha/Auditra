from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.evaluator import IndependentEvaluator
from auditra.financial_world import FinancialWorldService
from auditra.reconciliation import ReconciliationEngine


DEFAULT_PROMPT = (
    "Generate an Indian e-commerce merchant with 500 orders, UPI and card payments, "
    "2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the exact Phase B 5-minute demo repeatedly.")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--records", type=int, default=500)
    args = parser.parse_args()

    rows = []
    for idx in range(args.runs):
        started = time.perf_counter()
        try:
            prompt = DEFAULT_PROMPT.replace("500 orders", f"{args.records} orders")
            world = FinancialWorldService().build_from_prompt(prompt, seed=args.seed)
            controller_run = ReconciliationEngine(enable_ai=True).run(world.dataset)
            evaluation = IndependentEvaluator().evaluate(world.dataset, controller_run)
            rows.append(
                {
                    "iteration": idx + 1,
                    "status": "completed",
                    "duration_ms": round((time.perf_counter() - started) * 1000, 4),
                    "world_id": world.world_id,
                    "dataset_id": world.dataset_id,
                    "controller_run_id": controller_run.run_id,
                    "evaluation_run_id": evaluation.evaluation_run_id,
                    "records": controller_run.metrics.transactions_processed,
                    "accuracy": evaluation.metrics.accuracy,
                    "f1": evaluation.metrics.f1,
                    "failures": len(evaluation.failures),
                    "human_review_rate": controller_run.metrics.human_review_rate,
                    "ai_invocation_rate": controller_run.metrics.ai_invocation_rate,
                    "survival_status": "CONTROLLER SURVIVED" if not evaluation.failures else f"CONTROLLER FAILED {len(evaluation.failures)} CASES",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "iteration": idx + 1,
                    "status": "failed",
                    "duration_ms": round((time.perf_counter() - started) * 1000, 4),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    report = {
        "benchmark": "phase_c_demo_reliability",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runs_requested": args.runs,
        "system_failures": sum(1 for row in rows if row["status"] != "completed"),
        "rows": rows,
    }
    out_path = ROOT / "evaluation" / "phase_c_demo_reliability.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.evaluator import IndependentEvaluator
from auditra.models import ScenarioMode, ScenarioRequest
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


def run_mode(dataset, label: str, enable_ai: bool) -> dict:
    engine = ReconciliationEngine(enable_ai=enable_ai)
    evaluator = IndependentEvaluator()
    run = engine.run(dataset)
    evaluation = evaluator.evaluate(dataset, run)
    return {
        "mode": label,
        "controller_run_id": run.run_id,
        "records": run.metrics.transactions_processed,
        "duration_ms": run.duration_ms,
        "throughput_records_per_sec": run.metrics.throughput_records_per_sec,
        "median_latency_ms": run.metrics.median_latency_ms,
        "p95_latency_ms": run.metrics.p95_latency_ms,
        "p99_latency_ms": run.metrics.p99_latency_ms,
        "accuracy": evaluation.metrics.accuracy,
        "precision": evaluation.metrics.precision,
        "recall": evaluation.metrics.recall,
        "f1": evaluation.metrics.f1,
        "failures": len(evaluation.failures),
        "failure_taxonomy": evaluation.metrics.failure_taxonomy,
        "class_metrics": evaluation.metrics.class_metrics,
        "ai_investigations": run.metrics.ai_investigation_count,
        "ai_invocation_rate": run.metrics.ai_invocation_rate,
        "llm_calls": run.metrics.llm_calls,
        "agent_tool_calls": run.metrics.agent_tool_calls,
        "estimated_ai_cost_usd": str(run.metrics.estimated_ai_cost_usd),
        "average_risk_score": run.metrics.average_risk_score,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare deterministic-only and AI-assisted Auditra controllers.")
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--mode", choices=[item.value for item in ScenarioMode], default=ScenarioMode.MIXED.value)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset = ScenarioGenerator().generate(
        ScenarioRequest(mode=ScenarioMode(args.mode), record_count=args.records, seed=args.seed)
    )
    rows = [
        run_mode(dataset, "deterministic_only", enable_ai=False),
        run_mode(dataset, "ai_assisted", enable_ai=True),
    ]

    out_path = ROOT / "evaluation" / "controller_comparison.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

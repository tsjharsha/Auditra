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


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Auditra controller throughput.")
    parser.add_argument("--counts", nargs="*", type=int, default=[100, 500, 1000, 5000, 10000])
    parser.add_argument("--mode", choices=[item.value for item in ScenarioMode], default=ScenarioMode.MIXED.value)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generator = ScenarioGenerator()
    engine = ReconciliationEngine()
    evaluator = IndependentEvaluator()
    rows = []

    for count in args.counts:
        dataset = generator.generate(ScenarioRequest(mode=ScenarioMode(args.mode), record_count=count, seed=args.seed))
        run = engine.run(dataset)
        evaluation = evaluator.evaluate(dataset, run)
        rows.append(
            {
                "records": count,
                "duration_ms": run.duration_ms,
                "throughput_records_per_sec": run.metrics.throughput_records_per_sec,
                "median_latency_ms": run.metrics.median_latency_ms,
                "p95_latency_ms": run.metrics.p95_latency_ms,
                "p99_latency_ms": run.metrics.p99_latency_ms,
                "accuracy": evaluation.metrics.accuracy,
                "failures": len(evaluation.failures),
                "ai_investigations": run.metrics.ai_investigation_count,
                "llm_calls": run.metrics.llm_calls,
                "agent_tool_calls": run.metrics.agent_tool_calls,
                "cost_estimate_usd": str(run.metrics.estimated_ai_cost_usd),
                "average_risk_score": run.metrics.average_risk_score,
                "failure_taxonomy": evaluation.metrics.failure_taxonomy,
            }
        )

    out_path = ROOT / "evaluation" / "benchmark_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

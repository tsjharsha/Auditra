from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.evaluator import IndependentEvaluator
from auditra.models import ScenarioMode, ScenarioRequest
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Auditra demo mode end to end.")
    parser.add_argument("--mode", choices=[item.value for item in ScenarioMode], default=ScenarioMode.MIXED.value)
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    request = ScenarioRequest(mode=ScenarioMode(args.mode), record_count=args.records, seed=args.seed)
    dataset = ScenarioGenerator().generate(request)
    controller_run = ReconciliationEngine().run(dataset)
    evaluation = IndependentEvaluator().evaluate(dataset, controller_run)

    out_dir = ROOT / "data" / "demo" / dataset.dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(out_dir / "orders.csv", [item.model_dump(mode="json") for item in dataset.orders])
    write_csv(out_dir / "payments.csv", [item.model_dump(mode="json") for item in dataset.payments])
    write_csv(out_dir / "settlements.csv", [item.model_dump(mode="json") for item in dataset.settlements])
    write_csv(out_dir / "refunds.csv", [item.model_dump(mode="json") for item in dataset.refunds])
    write_csv(out_dir / "fees.csv", [item.model_dump(mode="json") for item in dataset.fee_rules])

    (out_dir / "controller_run.json").write_text(
        json.dumps(controller_run.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (out_dir / "evaluation_report.json").write_text(
        json.dumps(evaluation.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    summary = {
        "dataset_id": dataset.dataset_id,
        "controller_run_id": controller_run.run_id,
        "evaluation_run_id": evaluation.evaluation_run_id,
        "records": controller_run.metrics.transactions_processed,
        "match_rate": controller_run.metrics.match_rate,
        "automatic_resolution_rate": controller_run.metrics.automatic_resolution_rate,
        "accuracy": evaluation.metrics.accuracy,
        "precision": evaluation.metrics.precision,
        "recall": evaluation.metrics.recall,
        "f1": evaluation.metrics.f1,
        "false_positive_rate": evaluation.metrics.false_positive_rate,
        "false_negative_rate": evaluation.metrics.false_negative_rate,
        "throughput_records_per_sec": evaluation.metrics.throughput_records_per_sec,
        "failures": len(evaluation.failures),
        "output_dir": str(out_dir),
    }
    (ROOT / "data" / "demo" / "latest_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    if evaluation.failures:
        print(f"CONTROLLER FAILED {len(evaluation.failures)} CASES")
    else:
        print("CONTROLLER SURVIVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

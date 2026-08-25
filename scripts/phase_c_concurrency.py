from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.storage import AuditraStore


PROMPT = (
    "Generate an Indian e-commerce merchant with {records} orders, UPI and card payments, "
    "2% platform fees, T+2 settlement, refunds, duplicates, partial settlements and adversarial anomalies."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase C concurrency probe against the shared in-memory store.")
    parser.add_argument("--levels", nargs="*", type=int, default=[1, 5, 10, 25, 50])
    parser.add_argument("--records", type=int, default=120)
    parser.add_argument("--seed", type=int, default=9000)
    args = parser.parse_args()

    rows = [run_level(level, args.records, args.seed) for level in args.levels]
    report = {
        "benchmark": "phase_c_concurrency",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": rows,
    }
    out_path = ROOT / "evaluation" / "phase_c_concurrency.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def run_level(level: int, records: int, seed: int) -> Dict[str, Any]:
    store = AuditraStore()
    started = time.perf_counter()
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=level) as pool:
        futures = [pool.submit(run_one, store, records, seed + idx) for idx in range(level)]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append({"type": type(exc).__name__, "message": str(exc)})
    duration_ms = round((time.perf_counter() - started) * 1000, 4)
    world_ids = [item["world_id"] for item in results]
    dataset_ids = [item["dataset_id"] for item in results]
    run_ids = [item["run_id"] for item in results]
    evaluation_ids = [item["evaluation_run_id"] for item in results]
    duplicate_ids = len(world_ids) != len(set(world_ids)) or len(dataset_ids) != len(set(dataset_ids)) or len(run_ids) != len(set(run_ids))
    state_corruption = any(item["dataset_id"] != item["run_dataset_id"] or item["dataset_id"] != item["evaluation_dataset_id"] for item in results)
    return {
        "concurrent_runs": level,
        "records_per_run": records,
        "status": "completed" if not errors else "failed",
        "duration_ms": duration_ms,
        "throughput_runs_per_sec": round(len(results) / max(duration_ms / 1000, 0.001), 4),
        "completed": len(results),
        "errors": errors,
        "duplicate_processing_detected": duplicate_ids,
        "state_corruption_detected": state_corruption,
        "stored_worlds": len(store.worlds),
        "stored_datasets": len(store.datasets),
        "stored_controller_runs": len(store.controller_runs),
        "stored_evaluation_runs": len(store.evaluation_runs),
        "latest_run_id_known": store.latest_run_id in store.controller_runs if store.latest_run_id else False,
    }


def run_one(store: AuditraStore, records: int, seed: int) -> Dict[str, Any]:
    world = store.build_world_from_prompt(PROMPT.format(records=records), seed=seed)
    run = store.run_controller(world.dataset_id)
    evaluation = store.run_evaluation(world.dataset_id, run.run_id)
    public = store.world_service.public_build_result(world)
    text = json.dumps(public)
    if "ground_truth" in text or "expected_status" in text:
        raise AssertionError("public world leaked hidden labels during concurrency run")
    return {
        "world_id": world.world_id,
        "dataset_id": world.dataset_id,
        "run_id": run.run_id,
        "run_dataset_id": run.dataset_id,
        "evaluation_run_id": evaluation.evaluation_run_id,
        "evaluation_dataset_id": evaluation.dataset_id,
        "failures": len(evaluation.failures),
        "records": run.metrics.transactions_processed,
    }


if __name__ == "__main__":
    raise SystemExit(main())

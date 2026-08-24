from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.agent_tools import DatasetIndex
from auditra.models import ScenarioMode, ScenarioRequest
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


class GroundTruthIsolationTests(unittest.TestCase):
    def test_dataset_index_strips_hidden_ground_truth(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=50, seed=42))
        self.assertGreater(len(dataset.ground_truth), 0)

        index = DatasetIndex(dataset)
        self.assertEqual(index.dataset.ground_truth, {})

    def test_controller_run_does_not_emit_ground_truth_fields(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=50, seed=42))
        run = ReconciliationEngine(enable_ai=True).run(dataset)
        payload = json.dumps(run.model_dump(mode="json"))

        self.assertNotIn("ground_truth", payload)
        self.assertNotIn("expected_status", payload)
        self.assertNotIn('"scenario"', payload)


if __name__ == "__main__":
    unittest.main()

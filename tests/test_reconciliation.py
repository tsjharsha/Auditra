from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.evaluator import IndependentEvaluator
from auditra.models import ScenarioMode, ScenarioRequest
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


class ReconciliationTests(unittest.TestCase):
    def test_mixed_batch_reconciles_and_evaluates(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=120, seed=42))
        run = ReconciliationEngine().run(dataset)
        evaluation = IndependentEvaluator().evaluate(dataset, run)

        self.assertEqual(len(run.cases), 120)
        self.assertGreater(run.metrics.total_payment_volume, 0)
        self.assertGreater(run.metrics.throughput_records_per_sec, 0)
        self.assertGreaterEqual(evaluation.metrics.accuracy, 0.80)
        self.assertGreater(sum(len(case.tool_calls) for case in run.cases), 0)

    def test_missing_settlement_fails_closed_without_auto_resolution(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=80, seed=42))
        run = ReconciliationEngine(enable_ai=False).run(dataset)
        case = next(item for item in run.cases if item.status == "MISSING_SETTLEMENT")

        self.assertEqual(case.decision.status, "MISSING_SETTLEMENT")
        self.assertIn("MISSING_SETTLEMENT", case.decision.reason_codes)
        self.assertIsNone(case.decision.actual_settlement)
        self.assertNotIn(str(case.status), {"MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"})
        self.assertTrue(any(item.type == "Payment" for item in case.graph.nodes))
        self.assertFalse(any(item.type == "Settlement" for item in case.graph.nodes))

    def test_required_exception_types_are_present(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=80, seed=42))
        run = ReconciliationEngine().run(dataset)
        statuses = {str(case.status) for case in run.cases}

        self.assertIn("MISSING_SETTLEMENT", statuses)
        self.assertIn("DUPLICATE", statuses)
        self.assertIn("AMOUNT_MISMATCH", statuses)
        self.assertIn("TIMING_MISMATCH", statuses)


if __name__ == "__main__":
    unittest.main()

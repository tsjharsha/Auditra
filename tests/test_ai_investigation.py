from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.models import ScenarioMode, ScenarioRequest
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


class AIInvestigationTests(unittest.TestCase):
    def test_exception_cases_have_structured_ai_investigation(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=120, seed=42))
        run = ReconciliationEngine(enable_ai=True).run(dataset)
        investigated = [case for case in run.cases if case.ai_investigation is not None]

        self.assertGreater(len(investigated), 0)
        self.assertEqual(run.metrics.ai_investigation_count, len(investigated))
        self.assertGreater(run.metrics.agent_tool_calls, 0)

        dynamic_tool_names = {
            "find_merchant",
            "check_duplicate",
            "find_related_transactions",
            "check_fee_applicability",
            "get_graph_neighborhood",
            "create_hypothesis",
            "verify_hypothesis",
        }
        used_tools = {call.tool_name for case in investigated for call in case.tool_calls}
        self.assertTrue(dynamic_tool_names & used_tools)

        sample = investigated[0].ai_investigation
        self.assertIsNotNone(sample)
        self.assertGreater(len(sample.hypotheses), 0)
        self.assertIsNotNone(sample.selected_hypothesis_id)
        self.assertFalse(sample.verification_summary["ai_may_override_arithmetic"])

    def test_invariants_are_attached_to_every_case(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=50, seed=42))
        run = ReconciliationEngine(enable_ai=True).run(dataset)

        self.assertTrue(all(case.invariants for case in run.cases))
        self.assertTrue(all(case.decision.invariants for case in run.cases))
        self.assertTrue(any(any(item.rule_id == "SETTLEMENT_NET_AMOUNT" for item in case.invariants) for case in run.cases))
        self.assertGreaterEqual(run.metrics.p99_latency_ms, run.metrics.median_latency_ms)


if __name__ == "__main__":
    unittest.main()

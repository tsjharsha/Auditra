from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.ai_provider import MockStructuredInvestigationProvider
from auditra.models import ReconciliationStatus, ScenarioMode, ScenarioRequest
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


class AIFailureFallbackTests(unittest.TestCase):
    def test_configured_ai_failure_escalates_to_human_review(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=80, seed=42))
        provider = MockStructuredInvestigationProvider(error=TimeoutError("mock timeout"))

        run = ReconciliationEngine(enable_ai=True, ai_provider=provider).run(dataset)
        unavailable_cases = [case for case in run.cases if case.ai_investigation and case.ai_investigation.ai_unavailable]

        self.assertGreater(len(unavailable_cases), 0)
        self.assertTrue(all(case.status == ReconciliationStatus.HUMAN_REVIEW for case in unavailable_cases))
        self.assertTrue(all("AI_UNAVAILABLE" in case.decision.reason_codes for case in unavailable_cases))
        self.assertTrue(all(case.ai_investigation.provider_error for case in unavailable_cases))
        self.assertTrue(all(case.ai_investigation.tool_call_count == 0 for case in unavailable_cases))


if __name__ == "__main__":
    unittest.main()

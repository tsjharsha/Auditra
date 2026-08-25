from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.agent_tools import DatasetIndex, InvestigationTools, ToolValidationError
from auditra.models import ScenarioMode, ScenarioRequest
from auditra.scenario_generator import ScenarioGenerator


class ToolSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.MIXED, record_count=20, seed=42))
        self.tools = InvestigationTools(DatasetIndex(dataset), run_id="RUN_TEST", case_id="CASE_TEST")

    def test_path_like_entity_id_is_rejected_and_logged(self) -> None:
        with self.assertRaises(ToolValidationError):
            self.tools.get_evidence("payment", "../secret")

        self.assertEqual(len(self.tools.calls), 1)
        call = self.tools.calls[0]
        self.assertFalse(call.success)
        self.assertEqual(call.error_type, "ToolValidationError")
        self.assertGreater(call.result_size_bytes, 0)

    def test_query_like_input_is_rejected(self) -> None:
        with self.assertRaises(ToolValidationError):
            self.tools.get_evidence("payment", "DROP TABLE payments")

        self.assertEqual(self.tools.calls[-1].error_type, "ToolValidationError")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ai_value_benchmark import build_report


class AIValueBenchmarkTests(unittest.TestCase):
    def test_phase_a_benchmark_reports_global_and_class_lift(self) -> None:
        report = build_report(records=250, seed=42)

        self.assertEqual(report["benchmark"], "phase_a_ai_value")
        self.assertGreater(report["ai_assisted"]["ai_invocation_rate"], 0)
        self.assertIn("AMOUNT_MISMATCH", report["class_lift"])
        self.assertGreaterEqual(report["lift"]["failures_reduced"], 0)
        self.assertGreaterEqual(report["lift"]["accuracy"], 0)
        self.assertIn("financial_error_impact_reduction", report["lift"])


if __name__ == "__main__":
    unittest.main()

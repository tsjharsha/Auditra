from __future__ import annotations

from decimal import Decimal
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.models import money


class FinancialInvariantTests(unittest.TestCase):
    def test_money_uses_decimal_quantization(self) -> None:
        self.assertEqual(money("10.005"), Decimal("10.01"))
        self.assertEqual(money(Decimal("7.004")), Decimal("7.00"))

    def test_float_style_error_is_not_present(self) -> None:
        value = money("0.10") + money("0.20")
        self.assertEqual(value, Decimal("0.30"))


if __name__ == "__main__":
    unittest.main()

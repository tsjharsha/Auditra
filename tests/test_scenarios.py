from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.models import ScenarioMode, ScenarioRequest
from auditra.scenario_generator import ScenarioGenerator


def stable_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class ScenarioGeneratorTests(unittest.TestCase):
    def test_seed_reproducibility(self) -> None:
        request = ScenarioRequest(mode=ScenarioMode.DIFFICULT, record_count=100, seed=42)
        first = ScenarioGenerator().generate(request)
        second = ScenarioGenerator().generate(request)

        self.assertEqual(stable_hash([item.model_dump(mode="json") for item in first.payments]), stable_hash([item.model_dump(mode="json") for item in second.payments]))
        self.assertEqual(stable_hash([item.model_dump(mode="json") for item in first.settlements]), stable_hash([item.model_dump(mode="json") for item in second.settlements]))
        self.assertEqual(stable_hash({k: v.model_dump(mode="json") for k, v in first.ground_truth.items()}), stable_hash({k: v.model_dump(mode="json") for k, v in second.ground_truth.items()}))

    def test_refunds_do_not_exceed_payment_amount(self) -> None:
        dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.ADVERSARIAL, record_count=200, seed=99))
        payments = {payment.payment_id: payment for payment in dataset.payments}
        for refund in dataset.refunds:
            self.assertLessEqual(refund.amount, payments[refund.payment_id].amount)


if __name__ == "__main__":
    unittest.main()

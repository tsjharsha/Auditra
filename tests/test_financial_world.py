from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.financial_world import FinancialWorldService
from auditra.financial_world.models import FinancialWorldSpec
from auditra.reconciliation import ReconciliationEngine


PROMPT = (
    "Generate an Indian e-commerce merchant with 120 orders, UPI and card payments, "
    "2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies."
)


class FinancialWorldTests(unittest.TestCase):
    def test_prompt_builds_valid_reproducible_world(self) -> None:
        service = FinancialWorldService()
        first = service.build_from_prompt(PROMPT, seed=42)
        second = service.build_from_prompt(PROMPT, seed=42)

        self.assertEqual(first.world_id, second.world_id)
        self.assertEqual(first.dataset_id, second.dataset_id)
        self.assertTrue(first.validation.valid)
        self.assertEqual(first.spec.record_count, 120)
        self.assertEqual(str(first.spec.fee_rate), "0.0200")
        self.assertEqual(first.spec.settlement_delay_days, 2)
        self.assertIn("UPI", first.spec.payment_methods)
        self.assertIn("CARD", first.spec.payment_methods)
        self.assertGreater(first.summary.anomalies, 0)
        self.assertGreater(first.summary.payment_volume, 0)

    def test_world_public_result_hides_ground_truth(self) -> None:
        service = FinancialWorldService()
        result = service.build_from_prompt(PROMPT, seed=7)
        public_payload = json.dumps(service.public_build_result(result))
        visible_dataset_payload = json.dumps(result.dataset.model_dump(mode="json", exclude={"ground_truth"}))

        self.assertNotIn("ground_truth", public_payload)
        self.assertNotIn("expected_status", public_payload)
        self.assertNotIn('"scenario"', public_payload)
        self.assertNotIn('"anomaly":', visible_dataset_payload)

    def test_world_public_result_exposes_safe_source_records(self) -> None:
        service = FinancialWorldService()
        result = service.build_from_prompt(PROMPT, seed=11)
        public_dataset = service.public_build_result(result)["dataset"]
        public_payload = json.dumps(public_dataset)

        self.assertIn("records", public_dataset)
        self.assertEqual(len(public_dataset["records"]["payments"]), len(result.dataset.payments))
        self.assertEqual(len(public_dataset["records"]["orders"]), len(result.dataset.orders))
        self.assertNotIn("ground_truth", public_payload)
        self.assertNotIn("expected_status", public_payload)
        self.assertNotIn('"scenario"', public_payload)
        self.assertNotIn('"anomaly":', public_payload)

    def test_controlled_entity_link_failures_are_valid_adversarial_worlds(self) -> None:
        service = FinancialWorldService()
        spec = FinancialWorldSpec(
            prompt="Adversarial entity link failure regression.",
            record_count=80,
            seed=808,
            anomaly_rates={"ENTITY_LINK_FAILURE": Decimal("0.0500")},
        )

        result = service.build_from_spec(spec)

        self.assertTrue(result.validation.valid)
        self.assertTrue(any(check.check_id == "REFERENTIAL_INTEGRITY" and check.status == "WARNING" for check in result.validation.checks))

    def test_duplicate_payment_does_not_inherit_broken_entity_link(self) -> None:
        service = FinancialWorldService()
        prompt = (
            "Generate an Indian e-commerce merchant with 120 orders, UPI and card payments, "
            "2% platform fees, T+2 settlement, refunds, duplicates, partial settlements and adversarial anomalies."
        )

        result = service.build_from_prompt(prompt, seed=9005)
        payment_by_id = {payment.payment_id: payment for payment in result.dataset.payments}

        self.assertTrue(result.validation.valid)
        for payment in result.dataset.payments:
            if result.dataset.ground_truth[payment.payment_id].scenario == "duplicate_payment":
                canonical_id = payment.original.get("duplicate_of")
                self.assertIsNotNone(canonical_id)
                self.assertEqual(payment.order_id, payment_by_id[canonical_id].order_id)
                self.assertFalse(str(payment.order_id).startswith("ORD_MISSING_"))

    def test_financial_world_spec_rejects_unsupported_tokens(self) -> None:
        with self.assertRaises(ValueError):
            FinancialWorldSpec(currencies=["BTC"])
        with self.assertRaises(ValueError):
            FinancialWorldSpec(payment_methods=["cash"])
        with self.assertRaises(ValueError):
            FinancialWorldSpec(anomaly_rates={"UNKNOWN": Decimal("0.0100")})

    def test_generated_world_can_be_audited(self) -> None:
        result = FinancialWorldService().build_from_prompt(PROMPT, seed=42)
        run = ReconciliationEngine(enable_ai=True).run(result.dataset)
        run_payload = json.dumps(run.model_dump(mode="json"))

        self.assertEqual(len(run.cases), len(result.dataset.payments))
        self.assertGreater(run.metrics.agent_tool_calls, 0)
        self.assertGreaterEqual(run.metrics.ai_investigation_count, 1)
        self.assertNotIn('"anomaly":', run_payload)

    def test_json_ingestion_creates_auditable_dataset(self) -> None:
        payload = {
            "orders": [
                {
                    "order_id": "ORD_1",
                    "merchant_id": "MCH_1",
                    "customer_id": "CUS_1",
                    "amount": "1000.00",
                    "currency": "INR",
                    "created_at": "2026-01-05T09:30:00+00:00",
                }
            ],
            "payments": [
                {
                    "payment_id": "PAY_1",
                    "order_id": "ORD_1",
                    "merchant_id": "MCH_1",
                    "customer_id": "CUS_1",
                    "amount": "1000.00",
                    "currency": "INR",
                    "captured_at": "2026-01-05T09:40:00+00:00",
                    "payment_method": "upi",
                }
            ],
            "settlements": [
                {
                    "settlement_id": "SET_1",
                    "payment_id": "PAY_1",
                    "merchant_id": "MCH_1",
                    "amount": "980.00",
                    "currency": "INR",
                    "settled_at": "2026-01-07T09:40:00+00:00",
                    "batch_id": "BATCH_1",
                }
            ],
            "fees": [{"fee_rule_id": "FEE_1", "merchant_id": "MCH_1", "currency": "INR", "percent_bps": 200}],
        }
        result = FinancialWorldService().ingest("json", payload, seed=42)

        self.assertTrue(result.validation.valid)
        self.assertEqual(result.rows_loaded["payments"], 1)
        self.assertEqual(len(result.dataset.payments), 1)


if __name__ == "__main__":
    unittest.main()

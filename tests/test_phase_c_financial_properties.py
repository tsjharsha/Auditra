from __future__ import annotations

import sys
import unittest
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.models import DatasetBundle, Payment, ReconciliationCase, ReconciliationStatus, Refund, ScenarioMode, ScenarioRequest, money
from auditra.reconciliation import ReconciliationEngine
from auditra.scenario_generator import ScenarioGenerator


HEALTHY = {ReconciliationStatus.MATCHED.value, ReconciliationStatus.FEE_EXPLAINED.value, ReconciliationStatus.REFUND_ADJUSTED.value}


class PhaseCFinancialPropertyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = ScenarioGenerator().generate(ScenarioRequest(mode=ScenarioMode.NORMAL, record_count=80, seed=31415))

    def test_unrelated_transaction_change_does_not_alter_another_case(self) -> None:
        target, other = self._two_distinct_healthy_payments()
        base_target = self._case_for(self.dataset, target.payment_id)
        modified = self.dataset.model_copy(deep=True)
        other_settlement = self._settlement_for(modified, other.payment_id)
        other_settlement.amount = money(other_settlement.amount + Decimal("57.00"))

        changed_target = self._case_for(modified, target.payment_id)

        self.assertEqual(changed_target.status, base_target.status)
        self.assertEqual(changed_target.decision.expected_settlement, base_target.decision.expected_settlement)
        self.assertEqual(changed_target.decision.actual_settlement, base_target.decision.actual_settlement)

    def test_fee_rule_change_affects_only_applicable_transactions(self) -> None:
        before, after = self._two_healthy_payments_for_same_merchant()
        base_before = self._case_for(self.dataset, before.payment_id)
        modified = self.dataset.model_copy(deep=True)
        rule = next(item for item in modified.fee_rules if item.merchant_id == after.merchant_id)
        rule.active_to = after.captured_at - timedelta(minutes=1)

        changed_before = self._case_for(modified, before.payment_id)
        changed_after = self._case_for(modified, after.payment_id)

        self.assertEqual(changed_before.status, base_before.status)
        self.assertEqual(status_value(changed_after.status), ReconciliationStatus.HUMAN_REVIEW.value)
        self.assertIn("MISSING_FEE_RULE", changed_after.decision.reason_codes)

    def test_removing_settlement_creates_missing_settlement(self) -> None:
        payment = self._healthy_payment_without_refund()
        modified = self.dataset.model_copy(deep=True)
        modified.settlements = [item for item in modified.settlements if item.payment_id != payment.payment_id]

        case = self._case_for(modified, payment.payment_id)

        self.assertEqual(status_value(case.status), ReconciliationStatus.MISSING_SETTLEMENT.value)
        self.assertGreater(case.decision.financial_impact, Decimal("0.00"))

    def test_increasing_refund_changes_expected_settlement(self) -> None:
        payment = self._healthy_payment_without_refund()
        base = self._case_for(self.dataset, payment.payment_id)
        refund_amount = money(min(Decimal("100.00"), payment.amount / Decimal("10")))
        modified = self.dataset.model_copy(deep=True)
        modified.refunds.append(
            Refund(
                source="phase_c_property",
                source_record_id=f"phase-c-refund:{payment.payment_id}",
                ingested_at=payment.captured_at,
                refund_id=f"PHASE_C_REFUND_{payment.payment_id}",
                payment_id=payment.payment_id,
                merchant_id=payment.merchant_id,
                amount=refund_amount,
                currency=payment.currency,
                refunded_at=payment.captured_at + timedelta(hours=1),
                reason="customer_request",
                original={"source": "phase_c"},
            )
        )

        changed = self._case_for(modified, payment.payment_id)

        self.assertEqual(changed.decision.expected_settlement, money(base.decision.expected_settlement - refund_amount))
        self.assertIn(status_value(changed.status), {ReconciliationStatus.HUMAN_REVIEW.value, ReconciliationStatus.AMOUNT_MISMATCH.value})

    def test_currency_change_prevents_unsafe_comparison(self) -> None:
        payment = self._healthy_payment_without_refund()
        modified = self.dataset.model_copy(deep=True)
        settlement = self._settlement_for(modified, payment.payment_id)
        settlement.currency = "USD"

        case = self._case_for(modified, payment.payment_id)

        self.assertEqual(status_value(case.status), ReconciliationStatus.HUMAN_REVIEW.value)
        self.assertIn("BLOCKING_INVARIANT_FAILED", case.decision.reason_codes)
        self.assertTrue(any(item.rule_id == "CURRENCY_CONSISTENCY" and str(item.status) == "FAILED" for item in case.invariants))

    def test_duplicate_insertion_is_detected(self) -> None:
        payment = self._healthy_payment_without_refund()
        modified = self.dataset.model_copy(deep=True)
        duplicate = payment.model_copy(
            update={
                "payment_id": f"PHASE_C_DUP_{payment.payment_id}",
                "source_record_id": f"phase-c-dup:{payment.payment_id}",
                "captured_at": payment.captured_at + timedelta(seconds=30),
                "original": {"source": "phase_c_duplicate"},
            }
        )
        modified.payments.append(duplicate)

        case = self._case_for(modified, duplicate.payment_id)

        self.assertEqual(status_value(case.status), ReconciliationStatus.DUPLICATE.value)
        self.assertIn("DUPLICATE_PAYMENT", case.decision.reason_codes)

    def test_late_settlement_changes_temporal_status(self) -> None:
        payment = self._healthy_payment_without_refund()
        modified = self.dataset.model_copy(deep=True)
        settlement = self._settlement_for(modified, payment.payment_id)
        settlement.settled_at = payment.captured_at + timedelta(days=20)

        case = self._case_for(modified, payment.payment_id)

        self.assertEqual(status_value(case.status), ReconciliationStatus.TIMING_MISMATCH.value)
        self.assertIn("SETTLEMENT_TIMING", case.decision.reason_codes)

    def _case_for(self, dataset: DatasetBundle, payment_id: str) -> ReconciliationCase:
        run = ReconciliationEngine(enable_ai=False).run(dataset)
        return next(case for case in run.cases if case.payment_id == payment_id)

    def _healthy_payment_without_refund(self) -> Payment:
        run = ReconciliationEngine(enable_ai=False).run(self.dataset)
        refunds = {refund.payment_id for refund in self.dataset.refunds}
        settled = {settlement.payment_id for settlement in self.dataset.settlements}
        for case in run.cases:
            if status_value(case.status) in HEALTHY and case.payment_id in settled and case.payment_id not in refunds:
                return next(payment for payment in self.dataset.payments if payment.payment_id == case.payment_id)
        raise AssertionError("no healthy payment without refund found")

    def _two_distinct_healthy_payments(self) -> tuple[Payment, Payment]:
        run = ReconciliationEngine(enable_ai=False).run(self.dataset)
        settled = {settlement.payment_id for settlement in self.dataset.settlements}
        healthy = [
            next(payment for payment in self.dataset.payments if payment.payment_id == case.payment_id)
            for case in run.cases
            if case.status in HEALTHY and case.payment_id in settled
        ]
        if len(healthy) < 2:
            raise AssertionError("not enough healthy payments found")
        return healthy[0], healthy[-1]

    def _two_healthy_payments_for_same_merchant(self) -> tuple[Payment, Payment]:
        run = ReconciliationEngine(enable_ai=False).run(self.dataset)
        settled = {settlement.payment_id for settlement in self.dataset.settlements}
        by_merchant: dict[str, list[Payment]] = defaultdict(list)
        for case in run.cases:
            if status_value(case.status) in HEALTHY and case.payment_id in settled:
                payment = next(item for item in self.dataset.payments if item.payment_id == case.payment_id)
                by_merchant[payment.merchant_id].append(payment)
        for payments in by_merchant.values():
            ordered = sorted(payments, key=lambda item: item.captured_at)
            if len(ordered) >= 2 and ordered[0].captured_at < ordered[-1].captured_at - timedelta(minutes=1):
                return ordered[0], ordered[-1]
        raise AssertionError("no healthy same-merchant pair found")

    def _settlement_for(self, dataset: DatasetBundle, payment_id: str):
        return next(settlement for settlement in dataset.settlements if settlement.payment_id == payment_id)


def status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)


if __name__ == "__main__":
    unittest.main()

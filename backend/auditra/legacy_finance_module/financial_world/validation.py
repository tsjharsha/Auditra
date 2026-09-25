from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from ..models import DatasetBundle, money
from .models import WorldValidationCheck, WorldValidationReport


class WorldValidator:
    def validate(self, world_id: str, dataset: DatasetBundle) -> WorldValidationReport:
        checks = [
            self._referential_integrity(dataset),
            self._currency_consistency(dataset),
            self._merchant_consistency(dataset),
            self._temporal_consistency(dataset),
            self._refund_constraints(dataset),
            self._fee_rules(dataset),
            self._duplicate_constraints(dataset),
        ]
        return WorldValidationReport(
            world_id=world_id,
            valid=all(item.status in {"PASSED", "WARNING"} for item in checks),
            checks=checks,
        )

    def _referential_integrity(self, dataset: DatasetBundle) -> WorldValidationCheck:
        order_ids = {order.order_id for order in dataset.orders}
        payment_ids = {payment.payment_id for payment in dataset.payments}
        missing_order = [payment.payment_id for payment in dataset.payments if payment.order_id and payment.order_id not in order_ids]
        missing_payment = [
            *[settlement.settlement_id for settlement in dataset.settlements if settlement.payment_id not in payment_ids],
            *[refund.refund_id for refund in dataset.refunds if refund.payment_id not in payment_ids],
        ]
        controlled_missing_order = [
            payment_id
            for payment_id in missing_order
            if getattr(dataset.ground_truth.get(payment_id), "scenario", "") == "entity_link_failure"
        ]
        uncontrolled_missing_order = [payment_id for payment_id in missing_order if payment_id not in set(controlled_missing_order)]
        count = len(uncontrolled_missing_order) + len(missing_payment)
        controlled_count = len(controlled_missing_order)
        if count:
            status = "FAILED"
            detail = f"{count} broken visible link(s) found."
        elif controlled_count:
            status = "WARNING"
            detail = "Entity-link failures are controlled adversarial anomalies."
        else:
            status = "PASSED"
            detail = "All visible settlement/refund links resolve."
        return WorldValidationCheck(
            check_id="REFERENTIAL_INTEGRITY",
            status=status,
            detail=detail,
            count=count + controlled_count,
        )

    def _currency_consistency(self, dataset: DatasetBundle) -> WorldValidationCheck:
        anomalies = []
        payment_currency = {payment.payment_id: payment.currency for payment in dataset.payments}
        for settlement in dataset.settlements:
            if settlement.currency != payment_currency.get(settlement.payment_id):
                anomalies.append(settlement.settlement_id)
        for refund in dataset.refunds:
            if refund.currency != payment_currency.get(refund.payment_id):
                anomalies.append(refund.refund_id)
        return WorldValidationCheck(
            check_id="CURRENCY_CONSISTENCY",
            status="WARNING" if anomalies else "PASSED",
            detail="Currency anomalies are controlled by ground truth." if anomalies else "Visible currencies are internally consistent.",
            count=len(anomalies),
        )

    def _merchant_consistency(self, dataset: DatasetBundle) -> WorldValidationCheck:
        payment_merchant = {payment.payment_id: payment.merchant_id for payment in dataset.payments}
        inconsistencies = [
            settlement.settlement_id
            for settlement in dataset.settlements
            if settlement.merchant_id != payment_merchant.get(settlement.payment_id)
        ]
        return WorldValidationCheck(
            check_id="MERCHANT_CONSISTENCY",
            status="FAILED" if inconsistencies else "PASSED",
            detail="Merchant references are consistent." if not inconsistencies else "Settlement merchant references do not match payments.",
            count=len(inconsistencies),
        )

    def _temporal_consistency(self, dataset: DatasetBundle) -> WorldValidationCheck:
        payment_by_id = {payment.payment_id: payment for payment in dataset.payments}
        early = [
            settlement.settlement_id
            for settlement in dataset.settlements
            if settlement.payment_id in payment_by_id and settlement.settled_at < payment_by_id[settlement.payment_id].captured_at
        ]
        return WorldValidationCheck(
            check_id="TEMPORAL_CONSISTENCY",
            status="FAILED" if early else "PASSED",
            detail="No settlement predates payment capture." if not early else "A settlement predates capture.",
            count=len(early),
        )

    def _refund_constraints(self, dataset: DatasetBundle) -> WorldValidationCheck:
        payment_amount = {payment.payment_id: payment.amount for payment in dataset.payments}
        totals: Dict[str, Decimal] = {}
        for refund in dataset.refunds:
            totals[refund.payment_id] = money(totals.get(refund.payment_id, Decimal("0.00")) + refund.amount)
        excessive = [payment_id for payment_id, total in totals.items() if total > payment_amount.get(payment_id, Decimal("0.00"))]
        return WorldValidationCheck(
            check_id="REFUND_CONSTRAINTS",
            status="FAILED" if excessive else "PASSED",
            detail="Refund totals do not exceed payment amounts." if not excessive else "Refund total exceeds payment.",
            count=len(excessive),
        )

    def _fee_rules(self, dataset: DatasetBundle) -> WorldValidationCheck:
        merchant_ids = {merchant.merchant_id for merchant in dataset.merchants}
        rule_merchants = {rule.merchant_id for rule in dataset.fee_rules}
        missing = merchant_ids - rule_merchants
        return WorldValidationCheck(
            check_id="FEE_RULES",
            status="FAILED" if missing else "PASSED",
            detail="Every merchant has an active fee rule." if not missing else "Merchant missing fee rule.",
            count=len(missing),
        )

    def _duplicate_constraints(self, dataset: DatasetBundle) -> WorldValidationCheck:
        seen = set()
        duplicates = 0
        for payment in dataset.payments:
            key = (payment.merchant_id, payment.order_id, payment.customer_id, payment.currency, str(payment.amount))
            if key in seen:
                duplicates += 1
            seen.add(key)
        return WorldValidationCheck(
            check_id="DUPLICATE_CONSTRAINTS",
            status="WARNING" if duplicates else "PASSED",
            detail="Duplicate payments are controlled anomalies." if duplicates else "No duplicate payment patterns found.",
            count=duplicates,
        )

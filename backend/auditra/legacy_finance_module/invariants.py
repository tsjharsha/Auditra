from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from .models import (
    FeeRule,
    InvariantResult,
    InvariantStatus,
    Order,
    Payment,
    Refund,
    Settlement,
    money,
)


class FinancialInvariantEngine:
    """Rule-level financial controls that are independent of AI output."""

    def __init__(self, amount_tolerance: Decimal = Decimal("1.00")):
        self.amount_tolerance = money(amount_tolerance)

    def evaluate(
        self,
        payment: Payment,
        order: Optional[Order],
        settlements: List[Settlement],
        refunds: List[Refund],
        fee_rule: Optional[FeeRule],
        expected_settlement: Optional[Decimal],
        actual_settlement: Optional[Decimal],
        duplicate_info: Dict[str, Any],
    ) -> List[InvariantResult]:
        refund_total = money(sum((refund.amount for refund in refunds), Decimal("0.00")))
        return [
            self._payment_order_amount(payment, order),
            self._currency_consistency(payment, order, settlements, refunds, fee_rule),
            self._merchant_consistency(payment, order, settlements, refunds, fee_rule),
            self._settlement_net_amount(payment, settlements, fee_rule, expected_settlement, actual_settlement),
            self._refund_limit(payment, refunds, refund_total),
            self._payment_before_settlement(payment, settlements),
            self._refund_after_payment(payment, refunds),
            self._duplicate_consistency(payment, duplicate_info),
            self._relationship_completeness(payment, order, settlements, fee_rule),
            self._fee_rule_applicability(payment, fee_rule),
        ]

    def _result(
        self,
        rule_id: str,
        status: InvariantStatus,
        reason: str,
        evidence_ids: List[str],
        expected: Optional[Decimal] = None,
        actual: Optional[Decimal] = None,
        difference: Optional[Decimal] = None,
        severity: str = "info",
    ) -> InvariantResult:
        return InvariantResult(
            rule_id=rule_id,
            status=status,
            expected=expected,
            actual=actual,
            difference=difference,
            evidence_ids=evidence_ids,
            reason=reason,
            severity=severity,
        )

    def _payment_order_amount(self, payment: Payment, order: Optional[Order]) -> InvariantResult:
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        if order is None:
            return self._result(
                "PAYMENT_ORDER_AMOUNT",
                InvariantStatus.NOT_APPLICABLE,
                "Order record is unavailable.",
                evidence_ids,
                severity="review",
            )
        evidence_ids.append(f"EVD_ORDER_{order.order_id}")
        difference = money(payment.amount - order.amount)
        passed = abs(difference) <= self.amount_tolerance and payment.currency == order.currency
        return self._result(
            "PAYMENT_ORDER_AMOUNT",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "Payment amount and currency match the order." if passed else "Payment amount or currency differs from the order.",
            evidence_ids,
            expected=order.amount,
            actual=payment.amount,
            difference=difference,
            severity="high" if not passed else "info",
        )

    def _currency_consistency(
        self,
        payment: Payment,
        order: Optional[Order],
        settlements: List[Settlement],
        refunds: List[Refund],
        fee_rule: Optional[FeeRule],
    ) -> InvariantResult:
        currencies = {payment.currency}
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        if order:
            currencies.add(order.currency)
            evidence_ids.append(f"EVD_ORDER_{order.order_id}")
        for settlement in settlements:
            currencies.add(settlement.currency)
            evidence_ids.append(f"EVD_SETTLEMENT_{settlement.settlement_id}")
        for refund in refunds:
            currencies.add(refund.currency)
            evidence_ids.append(f"EVD_REFUND_{refund.refund_id}")
        if fee_rule:
            currencies.add(fee_rule.currency)
            evidence_ids.append(f"EVD_FEE_RULE_{fee_rule.fee_rule_id}")
        passed = len(currencies) == 1
        return self._result(
            "CURRENCY_CONSISTENCY",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "All visible records use the same currency." if passed else f"Multiple currencies found: {', '.join(sorted(currencies))}.",
            evidence_ids,
            severity="high" if not passed else "info",
        )

    def _merchant_consistency(
        self,
        payment: Payment,
        order: Optional[Order],
        settlements: List[Settlement],
        refunds: List[Refund],
        fee_rule: Optional[FeeRule],
    ) -> InvariantResult:
        merchant_ids = {payment.merchant_id}
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        if order:
            merchant_ids.add(order.merchant_id)
            evidence_ids.append(f"EVD_ORDER_{order.order_id}")
        for settlement in settlements:
            merchant_ids.add(settlement.merchant_id)
            evidence_ids.append(f"EVD_SETTLEMENT_{settlement.settlement_id}")
        for refund in refunds:
            merchant_ids.add(refund.merchant_id)
            evidence_ids.append(f"EVD_REFUND_{refund.refund_id}")
        if fee_rule:
            merchant_ids.add(fee_rule.merchant_id)
            evidence_ids.append(f"EVD_FEE_RULE_{fee_rule.fee_rule_id}")
        passed = len(merchant_ids) == 1
        return self._result(
            "MERCHANT_CONSISTENCY",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "All visible records belong to one merchant." if passed else "Records reference multiple merchants.",
            evidence_ids,
            severity="high" if not passed else "info",
        )

    def _settlement_net_amount(
        self,
        payment: Payment,
        settlements: List[Settlement],
        fee_rule: Optional[FeeRule],
        expected_settlement: Optional[Decimal],
        actual_settlement: Optional[Decimal],
    ) -> InvariantResult:
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        evidence_ids.extend(f"EVD_SETTLEMENT_{settlement.settlement_id}" for settlement in settlements)
        if fee_rule:
            evidence_ids.append(f"EVD_FEE_RULE_{fee_rule.fee_rule_id}")
        if expected_settlement is None or actual_settlement is None:
            return self._result(
                "SETTLEMENT_NET_AMOUNT",
                InvariantStatus.NOT_APPLICABLE,
                "Expected and actual settlement cannot both be computed.",
                evidence_ids,
                severity="review",
            )
        difference = money(actual_settlement - expected_settlement)
        passed = abs(difference) <= self.amount_tolerance
        return self._result(
            "SETTLEMENT_NET_AMOUNT",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "Actual settlement matches expected net amount." if passed else "Actual settlement differs from expected net amount.",
            evidence_ids,
            expected=expected_settlement,
            actual=actual_settlement,
            difference=difference,
            severity="high" if not passed else "info",
        )

    def _refund_limit(self, payment: Payment, refunds: List[Refund], refund_total: Decimal) -> InvariantResult:
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        evidence_ids.extend(f"EVD_REFUND_{refund.refund_id}" for refund in refunds)
        if not refunds:
            return self._result(
                "REFUND_DOES_NOT_EXCEED_PAYMENT",
                InvariantStatus.NOT_APPLICABLE,
                "No refunds are present.",
                evidence_ids,
            )
        passed = refund_total <= payment.amount
        return self._result(
            "REFUND_DOES_NOT_EXCEED_PAYMENT",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "Refund total is within payment amount." if passed else "Refund total exceeds payment amount.",
            evidence_ids,
            expected=payment.amount,
            actual=refund_total,
            difference=money(refund_total - payment.amount),
            severity="critical" if not passed else "info",
        )

    def _payment_before_settlement(self, payment: Payment, settlements: List[Settlement]) -> InvariantResult:
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        evidence_ids.extend(f"EVD_SETTLEMENT_{settlement.settlement_id}" for settlement in settlements)
        if not settlements:
            return self._result(
                "TEMPORAL_PAYMENT_BEFORE_SETTLEMENT",
                InvariantStatus.NOT_APPLICABLE,
                "No settlement timestamp is present.",
                evidence_ids,
                severity="review",
            )
        passed = all(settlement.settled_at >= payment.captured_at for settlement in settlements)
        return self._result(
            "TEMPORAL_PAYMENT_BEFORE_SETTLEMENT",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "Settlement happens after capture." if passed else "A settlement predates capture.",
            evidence_ids,
            severity="high" if not passed else "info",
        )

    def _refund_after_payment(self, payment: Payment, refunds: List[Refund]) -> InvariantResult:
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        evidence_ids.extend(f"EVD_REFUND_{refund.refund_id}" for refund in refunds)
        if not refunds:
            return self._result("TEMPORAL_REFUND_AFTER_PAYMENT", InvariantStatus.NOT_APPLICABLE, "No refund timestamp is present.", evidence_ids)
        passed = all(refund.refunded_at >= payment.captured_at for refund in refunds)
        return self._result(
            "TEMPORAL_REFUND_AFTER_PAYMENT",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "Refunds happen after capture." if passed else "A refund predates capture.",
            evidence_ids,
            severity="high" if not passed else "info",
        )

    def _duplicate_consistency(self, payment: Payment, duplicate_info: Dict[str, Any]) -> InvariantResult:
        duplicate_ids = duplicate_info.get("duplicate_payment_ids", [])
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        evidence_ids.extend(f"EVD_PAYMENT_{payment_id}" for payment_id in duplicate_ids)
        is_duplicate = duplicate_info.get("canonical_payment_id") not in (None, payment.payment_id)
        return self._result(
            "DUPLICATE_CONSISTENCY",
            InvariantStatus.FAILED if is_duplicate else InvariantStatus.PASSED,
            "Payment appears to duplicate a canonical transaction." if is_duplicate else "No duplicate payment pattern found.",
            evidence_ids,
            severity="high" if is_duplicate else "info",
        )

    def _relationship_completeness(
        self,
        payment: Payment,
        order: Optional[Order],
        settlements: List[Settlement],
        fee_rule: Optional[FeeRule],
    ) -> InvariantResult:
        missing = []
        if order is None:
            missing.append("order")
        if not settlements:
            missing.append("settlement")
        if fee_rule is None:
            missing.append("fee_rule")
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        if order:
            evidence_ids.append(f"EVD_ORDER_{order.order_id}")
        evidence_ids.extend(f"EVD_SETTLEMENT_{settlement.settlement_id}" for settlement in settlements)
        if fee_rule:
            evidence_ids.append(f"EVD_FEE_RULE_{fee_rule.fee_rule_id}")
        return self._result(
            "RELATIONSHIP_COMPLETENESS",
            InvariantStatus.FAILED if missing else InvariantStatus.PASSED,
            "Missing related records: " + ", ".join(missing) if missing else "Required related records are present.",
            evidence_ids,
            severity="review" if missing else "info",
        )

    def _fee_rule_applicability(self, payment: Payment, fee_rule: Optional[FeeRule]) -> InvariantResult:
        evidence_ids = [f"EVD_PAYMENT_{payment.payment_id}"]
        if fee_rule is None:
            return self._result(
                "FEE_RULE_APPLICABILITY",
                InvariantStatus.NOT_APPLICABLE,
                "No fee rule is available.",
                evidence_ids,
                severity="review",
            )
        evidence_ids.append(f"EVD_FEE_RULE_{fee_rule.fee_rule_id}")
        passed = fee_rule.currency == payment.currency and fee_rule.applies_at(payment.captured_at)
        return self._result(
            "FEE_RULE_APPLICABILITY",
            InvariantStatus.PASSED if passed else InvariantStatus.FAILED,
            "Fee rule applies to the payment." if passed else "Fee rule is not applicable at capture time or currency.",
            evidence_ids,
            severity="high" if not passed else "info",
        )

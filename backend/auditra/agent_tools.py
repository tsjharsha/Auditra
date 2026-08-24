from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from .models import (
    AgentToolCall,
    DatasetBundle,
    FeeRule,
    Order,
    Payment,
    Refund,
    Settlement,
    money,
    now_utc,
)


class ToolBudgetExceeded(RuntimeError):
    pass


class DatasetIndex:
    def __init__(self, dataset: DatasetBundle):
        self.dataset = dataset
        self.orders_by_id = {order.order_id: order for order in dataset.orders}
        self.payments_by_id = {payment.payment_id: payment for payment in dataset.payments}
        self.settlements_by_payment: Dict[str, List[Settlement]] = {}
        self.refunds_by_payment: Dict[str, List[Refund]] = {}
        self.fee_rules_by_merchant: Dict[str, List[FeeRule]] = {}

        for settlement in dataset.settlements:
            self.settlements_by_payment.setdefault(settlement.payment_id, []).append(settlement)
        for refund in dataset.refunds:
            self.refunds_by_payment.setdefault(refund.payment_id, []).append(refund)
        for rule in dataset.fee_rules:
            self.fee_rules_by_merchant.setdefault(rule.merchant_id, []).append(rule)

        self.payments_by_composite: Dict[tuple, List[Payment]] = {}
        for payment in dataset.payments:
            key = (
                payment.merchant_id,
                payment.order_id,
                payment.customer_id,
                payment.currency,
                str(payment.amount),
            )
            self.payments_by_composite.setdefault(key, []).append(payment)
        for payment_list in self.payments_by_composite.values():
            payment_list.sort(key=lambda item: (item.captured_at, item.payment_id))


class InvestigationTools:
    allowlist = {
        "find_payment",
        "find_order",
        "find_settlement",
        "find_refunds",
        "find_fee_rules",
        "get_transaction_history",
        "compare_amounts",
        "check_temporal_relationship",
        "find_related_records",
        "get_evidence",
        "create_reconciliation_case",
        "request_human_review",
    }

    def __init__(self, index: DatasetIndex, run_id: str, case_id: str, max_calls: int = 24):
        self.index = index
        self.run_id = run_id
        self.case_id = case_id
        self.max_calls = max_calls
        self.calls: List[AgentToolCall] = []

    def _record(self, tool_name: str, inputs: Dict[str, Any], func: Callable[[], Any], output_mapper: Callable[[Any], Dict[str, Any]]) -> Any:
        if tool_name not in self.allowlist:
            raise ValueError(f"tool is not allowlisted: {tool_name}")
        if len(self.calls) >= self.max_calls:
            self.request_human_review("agent exceeded tool-call budget")
            raise ToolBudgetExceeded("agent exceeded tool-call budget")

        started = now_utc()
        success = True
        try:
            result = func()
            output = output_mapper(result)
        except Exception as exc:
            success = False
            result = None
            output = {"error": str(exc)}
        finished = now_utc()
        self.calls.append(
            AgentToolCall(
                call_id=f"TOOL_{uuid.uuid4().hex[:10]}",
                run_id=self.run_id,
                case_id=self.case_id,
                tool_name=tool_name,
                input=inputs,
                output=output,
                started_at=started,
                finished_at=finished,
                success=success,
            )
        )
        if not success:
            raise RuntimeError(output["error"])
        return result

    def find_payment(self, payment_id: str) -> Optional[Payment]:
        return self._record(
            "find_payment",
            {"payment_id": payment_id},
            lambda: self.index.payments_by_id.get(payment_id),
            lambda payment: {"found": payment is not None, "payment_id": getattr(payment, "payment_id", None)},
        )

    def find_order(self, order_id: Optional[str]) -> Optional[Order]:
        return self._record(
            "find_order",
            {"order_id": order_id},
            lambda: self.index.orders_by_id.get(order_id or ""),
            lambda order: {"found": order is not None, "order_id": getattr(order, "order_id", None)},
        )

    def find_settlement(self, payment_id: str) -> List[Settlement]:
        return self._record(
            "find_settlement",
            {"payment_id": payment_id},
            lambda: self.index.settlements_by_payment.get(payment_id, []),
            lambda settlements: {"count": len(settlements), "settlement_ids": [item.settlement_id for item in settlements]},
        )

    def find_refunds(self, payment_id: str) -> List[Refund]:
        return self._record(
            "find_refunds",
            {"payment_id": payment_id},
            lambda: self.index.refunds_by_payment.get(payment_id, []),
            lambda refunds: {"count": len(refunds), "refund_ids": [item.refund_id for item in refunds]},
        )

    def find_fee_rules(self, merchant_id: str, payment: Payment) -> List[FeeRule]:
        return self._record(
            "find_fee_rules",
            {"merchant_id": merchant_id, "captured_at": payment.captured_at.isoformat()},
            lambda: [rule for rule in self.index.fee_rules_by_merchant.get(merchant_id, []) if rule.applies_at(payment.captured_at)],
            lambda rules: {"count": len(rules), "fee_rule_ids": [item.fee_rule_id for item in rules]},
        )

    def get_transaction_history(self, payment_id: str) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            payment = self.index.payments_by_id[payment_id]
            return {
                "payment_id": payment.payment_id,
                "order_id": payment.order_id,
                "settlement_ids": [item.settlement_id for item in self.index.settlements_by_payment.get(payment_id, [])],
                "refund_ids": [item.refund_id for item in self.index.refunds_by_payment.get(payment_id, [])],
            }

        return self._record(
            "get_transaction_history",
            {"payment_id": payment_id},
            compute,
            lambda history: history,
        )

    def compare_amounts(self, actual: Decimal, expected: Decimal, tolerance: Decimal) -> Dict[str, Any]:
        def compare() -> Dict[str, Any]:
            difference = money(actual - expected)
            return {
                "actual": str(money(actual)),
                "expected": str(money(expected)),
                "difference": str(difference),
                "within_tolerance": abs(difference) <= tolerance,
                "tolerance": str(tolerance),
            }

        return self._record(
            "compare_amounts",
            {"actual": str(money(actual)), "expected": str(money(expected)), "tolerance": str(tolerance)},
            compare,
            lambda result: result,
        )

    def check_temporal_relationship(self, payment: Payment, settlements: List[Settlement], cycle_days: int, tolerance_days: int = 1) -> Dict[str, Any]:
        def check() -> Dict[str, Any]:
            if not settlements:
                return {"valid": False, "reason": "no settlement"}
            latest_allowed = payment.captured_at + timedelta(days=cycle_days + tolerance_days)
            earliest_allowed = payment.captured_at
            violations = [
                settlement.settlement_id
                for settlement in settlements
                if settlement.settled_at < earliest_allowed or settlement.settled_at > latest_allowed
            ]
            return {
                "valid": len(violations) == 0,
                "violating_settlement_ids": violations,
                "earliest_allowed": earliest_allowed.isoformat(),
                "latest_allowed": latest_allowed.isoformat(),
            }

        return self._record(
            "check_temporal_relationship",
            {"payment_id": payment.payment_id, "cycle_days": cycle_days, "tolerance_days": tolerance_days},
            check,
            lambda result: result,
        )

    def find_related_records(self, payment: Payment) -> Dict[str, Any]:
        def related() -> Dict[str, Any]:
            key = (payment.merchant_id, payment.order_id, payment.customer_id, payment.currency, str(payment.amount))
            duplicates = self.index.payments_by_composite.get(key, [])
            return {
                "duplicate_payment_ids": [item.payment_id for item in duplicates if item.payment_id != payment.payment_id],
                "canonical_payment_id": duplicates[0].payment_id if duplicates else payment.payment_id,
                "duplicate_count": max(0, len(duplicates) - 1),
            }

        return self._record(
            "find_related_records",
            {"payment_id": payment.payment_id},
            related,
            lambda result: result,
        )

    def get_evidence(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        def evidence() -> Dict[str, Any]:
            return {"entity_type": entity_type, "entity_id": entity_id, "available": True}

        return self._record(
            "get_evidence",
            {"entity_type": entity_type, "entity_id": entity_id},
            evidence,
            lambda result: result,
        )

    def create_reconciliation_case(self, payment_id: str) -> Dict[str, Any]:
        def create() -> Dict[str, Any]:
            return {"case_id": self.case_id, "payment_id": payment_id, "created": True}

        return self._record(
            "create_reconciliation_case",
            {"payment_id": payment_id},
            create,
            lambda result: result,
        )

    def request_human_review(self, reason: str) -> Dict[str, Any]:
        started = now_utc()
        output = {"requested": True, "reason": reason}
        self.calls.append(
            AgentToolCall(
                call_id=f"TOOL_{uuid.uuid4().hex[:10]}",
                run_id=self.run_id,
                case_id=self.case_id,
                tool_name="request_human_review",
                input={"reason": reason},
                output=output,
                started_at=started,
                finished_at=now_utc(),
                success=True,
            )
        )
        return output

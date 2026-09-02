from __future__ import annotations

import json
import re
import time
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from .models import (
    AgentToolCall,
    DatasetBundle,
    FeeRule,
    Merchant,
    Order,
    Payment,
    Refund,
    Settlement,
    money,
    now_utc,
)


class ToolBudgetExceeded(RuntimeError):
    pass


class ToolValidationError(ValueError):
    pass


class DatasetIndex:
    def __init__(self, dataset: DatasetBundle):
        self.dataset = dataset.model_copy(update={"ground_truth": {}})
        self.merchants_by_id = {merchant.merchant_id: merchant for merchant in self.dataset.merchants}
        self.orders_by_id = {order.order_id: order for order in self.dataset.orders}
        self.payments_by_id = {payment.payment_id: payment for payment in self.dataset.payments}
        self.settlements_by_payment: Dict[str, List[Settlement]] = {}
        self.refunds_by_payment: Dict[str, List[Refund]] = {}
        self.fee_rules_by_merchant: Dict[str, List[FeeRule]] = {}

        for settlement in self.dataset.settlements:
            self.settlements_by_payment.setdefault(settlement.payment_id, []).append(settlement)
        for refund in self.dataset.refunds:
            self.refunds_by_payment.setdefault(refund.payment_id, []).append(refund)
        for rule in self.dataset.fee_rules:
            self.fee_rules_by_merchant.setdefault(rule.merchant_id, []).append(rule)

        self.payments_by_composite: Dict[tuple, List[Payment]] = {}
        for payment in self.dataset.payments:
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
        "find_merchant",
        "find_settlement",
        "find_refunds",
        "find_fee_rules",
        "get_transaction_history",
        "compare_amounts",
        "check_temporal_relationship",
        "find_related_records",
        "find_related_transactions",
        "check_fee_applicability",
        "check_duplicate",
        "get_graph_neighborhood",
        "get_evidence",
        "create_hypothesis",
        "verify_hypothesis",
        "create_reconciliation_case",
        "request_human_review",
    }
    evidence_entity_types = {"MERCHANT", "ORDER", "PAYMENT", "SETTLEMENT", "REFUND", "FEE_RULE"}

    def __init__(
        self,
        index: DatasetIndex,
        run_id: str,
        case_id: str,
        max_calls: int = 64,
        tool_timeout_ms: int = 1000,
        max_result_bytes: int = 4096,
    ):
        self.index = index
        self.run_id = run_id
        self.case_id = case_id
        self.max_calls = max_calls
        self.tool_timeout_ms = tool_timeout_ms
        self.max_result_bytes = max_result_bytes
        self.calls: List[AgentToolCall] = []

    def _record(self, tool_name: str, inputs: Dict[str, Any], func: Callable[[], Any], output_mapper: Callable[[Any], Dict[str, Any]]) -> Any:
        if tool_name not in self.allowlist:
            raise ValueError(f"tool is not allowlisted: {tool_name}")
        if len(self.calls) >= self.max_calls:
            self.request_human_review("agent exceeded tool-call budget")
            raise ToolBudgetExceeded("agent exceeded tool-call budget")

        started = now_utc()
        started_perf = time.perf_counter()
        success = True
        error_type = None
        original_error: Optional[Exception] = None
        result_size = 0
        try:
            self._validate_inputs(tool_name, inputs)
            result = func()
            output = output_mapper(result)
            duration_ms = round((time.perf_counter() - started_perf) * 1000, 4)
            if duration_ms > self.tool_timeout_ms:
                raise TimeoutError(f"{tool_name} exceeded {self.tool_timeout_ms}ms tool timeout")
            output, result_size = self._summarize_output(output)
        except Exception as exc:
            success = False
            original_error = exc
            result = None
            output = {"error": str(exc)}
            output, result_size = self._summarize_output(output)
            error_type = type(exc).__name__
            duration_ms = round((time.perf_counter() - started_perf) * 1000, 4)
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
                duration_ms=duration_ms,
                result_size_bytes=result_size,
                error_type=error_type,
            )
        )
        if not success:
            if isinstance(original_error, ToolValidationError):
                raise ToolValidationError(output["error"]) from original_error
            if isinstance(original_error, ToolBudgetExceeded):
                raise original_error
            raise RuntimeError(output["error"])
        return result

    def _validate_inputs(self, tool_name: str, inputs: Dict[str, Any]) -> None:
        self._validate_value("tool_name", tool_name, depth=0)
        self._validate_value("inputs", inputs, depth=0)

    def _validate_value(self, key: str, value: Any, depth: int) -> None:
        if depth > 4:
            raise ToolValidationError("tool input nesting is too deep")
        if value is None or isinstance(value, (bool, int, float, Decimal)):
            return
        if hasattr(value, "model_dump"):
            return
        if isinstance(value, str):
            if len(value) > 256:
                raise ToolValidationError(f"{key} exceeds maximum string length")
            lowered = value.lower()
            if re.search(r"\b(select|insert|update|delete|drop|alter|truncate|union|exec)\b|;--|/\*|\*/", lowered):
                raise ToolValidationError(f"{key} contains disallowed query syntax")
            if any(char in value for char in ("\x00", "\r", "\n")):
                raise ToolValidationError(f"{key} contains disallowed control characters")
            id_like = key.endswith("_id") or key in {"entity_id", "payment_id", "order_id", "merchant_id", "hypothesis_id"}
            if id_like and (".." in value or "/" in value or "\\" in value):
                raise ToolValidationError(f"{key} contains disallowed path characters")
            return
        if isinstance(value, list):
            if len(value) > 100:
                raise ToolValidationError(f"{key} contains too many items")
            for item in value:
                self._validate_value(key, item, depth + 1)
            return
        if isinstance(value, dict):
            if len(value) > 100:
                raise ToolValidationError(f"{key} contains too many fields")
            for child_key, child_value in value.items():
                if not isinstance(child_key, str) or len(child_key) > 64:
                    raise ToolValidationError("tool input keys must be short strings")
                self._validate_value(child_key, child_value, depth + 1)
            return
        raise ToolValidationError(f"{key} has unsupported type {type(value).__name__}")

    def _summarize_output(self, output: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
        encoded = json.dumps(output, default=str, sort_keys=True)
        size = len(encoded.encode("utf-8"))
        if size <= self.max_result_bytes:
            return output, size
        budget = max(80, self.max_result_bytes - 120)
        return {"truncated": True, "result_size_bytes": size, "summary": encoded[:budget]}, size

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

    def find_merchant(self, merchant_id: str) -> Optional[Merchant]:
        return self._record(
            "find_merchant",
            {"merchant_id": merchant_id},
            lambda: self.index.merchants_by_id.get(merchant_id),
            lambda merchant: {
                "found": merchant is not None,
                "merchant_id": getattr(merchant, "merchant_id", None),
                "risk_tier": getattr(merchant, "risk_tier", None),
                "settlement_cycle_days": getattr(merchant, "settlement_cycle_days", None),
            },
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

    def find_related_transactions(self, payment: Payment, window_minutes: int = 10) -> Dict[str, Any]:
        def related() -> Dict[str, Any]:
            start = payment.captured_at - timedelta(minutes=window_minutes)
            end = payment.captured_at + timedelta(minutes=window_minutes)
            same_order = []
            same_reference = []
            nearby_same_amount = []
            for candidate in self.index.dataset.payments:
                if candidate.payment_id == payment.payment_id:
                    continue
                if candidate.order_id and candidate.order_id == payment.order_id:
                    same_order.append(candidate.payment_id)
                if candidate.reference_id and candidate.reference_id == payment.reference_id:
                    same_reference.append(candidate.payment_id)
                if (
                    candidate.merchant_id == payment.merchant_id
                    and candidate.customer_id == payment.customer_id
                    and candidate.currency == payment.currency
                    and candidate.amount == payment.amount
                    and start <= candidate.captured_at <= end
                ):
                    nearby_same_amount.append(candidate.payment_id)
            return {
                "payment_id": payment.payment_id,
                "same_order_payment_ids": sorted(set(same_order)),
                "same_reference_payment_ids": sorted(set(same_reference)),
                "nearby_same_amount_payment_ids": sorted(set(nearby_same_amount)),
                "window_minutes": window_minutes,
            }

        return self._record(
            "find_related_transactions",
            {"payment_id": payment.payment_id, "window_minutes": window_minutes},
            related,
            lambda result: result,
        )

    def check_fee_applicability(self, fee_rule: Optional[FeeRule], payment: Payment) -> Dict[str, Any]:
        def check() -> Dict[str, Any]:
            if fee_rule is None:
                return {"applicable": False, "reason": "fee rule missing"}
            applies_at = fee_rule.applies_at(payment.captured_at)
            currency_matches = fee_rule.currency == payment.currency
            expected_fee = fee_rule.calculate_fee(payment.amount)
            expected_gst = fee_rule.calculate_gst(expected_fee)
            return {
                "applicable": applies_at and currency_matches,
                "applies_at_capture": applies_at,
                "currency_matches": currency_matches,
                "fee_rule_id": fee_rule.fee_rule_id,
                "expected_fee": str(expected_fee),
                "expected_gst": str(expected_gst),
            }

        return self._record(
            "check_fee_applicability",
            {"payment_id": payment.payment_id, "fee_rule_id": getattr(fee_rule, "fee_rule_id", None)},
            check,
            lambda result: result,
        )

    def check_duplicate(self, payment: Payment) -> Dict[str, Any]:
        def check() -> Dict[str, Any]:
            key = (payment.merchant_id, payment.order_id, payment.customer_id, payment.currency, str(payment.amount))
            duplicates = self.index.payments_by_composite.get(key, [])
            duplicate_ids = [item.payment_id for item in duplicates if item.payment_id != payment.payment_id]
            canonical = duplicates[0].payment_id if duplicates else payment.payment_id
            return {
                "is_duplicate": canonical != payment.payment_id,
                "canonical_payment_id": canonical,
                "duplicate_payment_ids": duplicate_ids,
                "duplicate_count": len(duplicate_ids),
            }

        return self._record(
            "check_duplicate",
            {"payment_id": payment.payment_id},
            check,
            lambda result: result,
        )

    def get_graph_neighborhood(self, payment_id: str) -> Dict[str, Any]:
        def neighborhood() -> Dict[str, Any]:
            payment = self.index.payments_by_id[payment_id]
            settlements = self.index.settlements_by_payment.get(payment_id, [])
            refunds = self.index.refunds_by_payment.get(payment_id, [])
            order_id = payment.order_id if payment.order_id in self.index.orders_by_id else None
            key = (payment.merchant_id, payment.order_id, payment.customer_id, payment.currency, str(payment.amount))
            duplicates = self.index.payments_by_composite.get(key, [])
            duplicate_payment_ids = [item.payment_id for item in duplicates if item.payment_id != payment.payment_id]
            return {
                "center": f"PAYMENT:{payment.payment_id}",
                "nodes": [
                    f"PAYMENT:{payment.payment_id}",
                    f"MERCHANT:{payment.merchant_id}",
                    f"CUSTOMER:{payment.customer_id}",
                    *([f"ORDER:{order_id}"] if order_id else []),
                    *[f"SETTLEMENT:{item.settlement_id}" for item in settlements],
                    *[f"REFUND:{item.refund_id}" for item in refunds],
                    *[f"PAYMENT:{item}" for item in duplicate_payment_ids],
                ],
                "relationships": [
                    "BELONGS_TO",
                    *(['CREATED'] if order_id else []),
                    *(['SETTLED'] if settlements else []),
                    *(['REFUNDED'] if refunds else []),
                    *(['RELATED_TO'] if duplicate_payment_ids else []),
                ],
            }

        return self._record(
            "get_graph_neighborhood",
            {"payment_id": payment_id},
            neighborhood,
            lambda result: result,
        )

    def get_evidence(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        def evidence() -> Dict[str, Any]:
            normalized = entity_type.strip().upper()
            if normalized not in self.evidence_entity_types:
                raise ToolValidationError(f"entity_type is not evidence-allowlisted: {entity_type}")
            if not self._entity_exists(normalized, entity_id):
                raise ToolValidationError(f"evidence entity not found for allowlisted type: {normalized}")
            return {"entity_type": normalized, "entity_id": entity_id, "available": True}

        return self._record(
            "get_evidence",
            {"entity_type": entity_type, "entity_id": entity_id},
            evidence,
            lambda result: result,
        )

    def _entity_exists(self, entity_type: str, entity_id: str) -> bool:
        if entity_type == "MERCHANT":
            return entity_id in self.index.merchants_by_id
        if entity_type == "ORDER":
            return entity_id in self.index.orders_by_id
        if entity_type == "PAYMENT":
            return entity_id in self.index.payments_by_id
        if entity_type == "SETTLEMENT":
            return any(item.settlement_id == entity_id for items in self.index.settlements_by_payment.values() for item in items)
        if entity_type == "REFUND":
            return any(item.refund_id == entity_id for items in self.index.refunds_by_payment.values() for item in items)
        if entity_type == "FEE_RULE":
            return any(item.fee_rule_id == entity_id for items in self.index.fee_rules_by_merchant.values() for item in items)
        return False

    def create_hypothesis(self, label: str, evidence_ids: List[str]) -> Dict[str, Any]:
        def create() -> Dict[str, Any]:
            return {
                "hypothesis_id": f"HYP_{uuid.uuid4().hex[:10]}",
                "label": label,
                "evidence_ids": evidence_ids,
                "created": True,
            }

        return self._record(
            "create_hypothesis",
            {"label": label, "evidence_ids": evidence_ids},
            create,
            lambda result: result,
        )

    def verify_hypothesis(self, hypothesis_id: str, checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        def verify() -> Dict[str, Any]:
            failed = [item for item in checks if not bool(item.get("passed"))]
            return {
                "hypothesis_id": hypothesis_id,
                "passed": len(failed) == 0,
                "failed_checks": failed,
                "check_count": len(checks),
            }

        return self._record(
            "verify_hypothesis",
            {"hypothesis_id": hypothesis_id, "checks": checks},
            verify,
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
        result_size = len(json.dumps(output, default=str, sort_keys=True).encode("utf-8"))
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
                duration_ms=0.0,
                result_size_bytes=result_size,
            )
        )
        return output

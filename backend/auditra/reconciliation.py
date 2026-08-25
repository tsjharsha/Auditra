from __future__ import annotations

import statistics
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .agent_tools import DatasetIndex, InvestigationTools, ToolBudgetExceeded
from .ai_investigator import AIInvestigationAgent
from .ai_provider import StructuredInvestigationProvider
from .audit import AuditLog
from .evidence_graph import build_evidence_items, build_graph
from .invariants import FinancialInvariantEngine
from .models import (
    ConfidenceBand,
    ControllerDecision,
    ControllerRun,
    DatasetBundle,
    FeeRule,
    HypothesisStatus,
    InvariantResult,
    Payment,
    ReconciliationCase,
    ReconciliationStatus,
    RunMetrics,
    VerificationResult,
    money,
    now_utc,
)


MATCH_STATUSES = {
    ReconciliationStatus.MATCHED,
    ReconciliationStatus.FEE_EXPLAINED,
    ReconciliationStatus.REFUND_ADJUSTED,
}
MATCH_STATUS_VALUES = {item.value for item in MATCH_STATUSES}

TERMINAL_REVIEW_STATUSES = {
    ReconciliationStatus.HUMAN_REVIEW,
    ReconciliationStatus.UNRESOLVED,
}
TERMINAL_REVIEW_VALUES = {item.value for item in TERMINAL_REVIEW_STATUSES}


class ReconciliationEngine:
    def __init__(
        self,
        amount_tolerance: Decimal = Decimal("1.00"),
        enable_ai: bool = True,
        ai_provider: Optional[StructuredInvestigationProvider] = None,
    ):
        self.amount_tolerance = money(amount_tolerance)
        self.enable_ai = enable_ai
        self.invariants = FinancialInvariantEngine(amount_tolerance=self.amount_tolerance)
        self.ai_agent = AIInvestigationAgent(provider=ai_provider)

    def run(self, dataset: DatasetBundle) -> ControllerRun:
        run_id = f"RUN_{uuid.uuid4().hex[:12]}"
        started_at = now_utc()
        start = time.perf_counter()
        audit = AuditLog(correlation_id=run_id)
        normalize_start = time.perf_counter()
        index = DatasetIndex(dataset)
        normalization_ms = (time.perf_counter() - normalize_start) * 1000
        cases: List[ReconciliationCase] = []
        latencies: List[float] = []

        audit.record(
            actor="system",
            action="controller_run_started",
            entity="dataset",
            entity_id=dataset.dataset_id,
            reason="deterministic reconciliation run",
            inputs_ref={"payments": len(dataset.payments)},
        )

        for payment in sorted(dataset.payments, key=lambda item: item.captured_at):
            case_start = time.perf_counter()
            case = self._reconcile_payment(payment, index, run_id, audit)
            cases.append(case)
            latencies.append((time.perf_counter() - case_start) * 1000)

        duration_ms = (time.perf_counter() - start) * 1000
        finished_at = now_utc()
        metrics = self._build_metrics(dataset, cases, duration_ms, latencies, normalization_ms)

        audit.record(
            actor="system",
            action="controller_run_finished",
            entity="controller_run",
            entity_id=run_id,
            reason="run completed without mutating source records",
            output_ref=metrics.model_dump(mode="json"),
        )

        return ControllerRun(
            run_id=run_id,
            dataset_id=dataset.dataset_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round(duration_ms, 2),
            metrics=metrics,
            cases=cases,
            audit_events=audit.events,
        )

    def _reconcile_payment(
        self,
        payment: Payment,
        index: DatasetIndex,
        run_id: str,
        audit: AuditLog,
    ) -> ReconciliationCase:
        case_id = f"CASE_{payment.payment_id}"
        tools = InvestigationTools(index=index, run_id=run_id, case_id=case_id)
        timeline = ["Investigation started"]
        reason_codes: List[str] = []
        contradicting: List[str] = []
        supporting: List[str] = []
        tool_failure_requires_review = False

        audit.record(
            actor="controller",
            action="reconciliation_started",
            entity="payment",
            entity_id=payment.payment_id,
            reason="payment selected for reconciliation",
        )

        try:
            tools.create_reconciliation_case(payment.payment_id)
            located_payment = tools.find_payment(payment.payment_id)
            order = tools.find_order(payment.order_id)
            settlements = tools.find_settlement(payment.payment_id)
            refunds = tools.find_refunds(payment.payment_id)
            fee_rules = tools.find_fee_rules(payment.merchant_id, payment)
            history = tools.get_transaction_history(payment.payment_id)
            related = tools.find_related_records(payment)
        except ToolBudgetExceeded:
            order = None
            settlements = []
            refunds = []
            fee_rules = []
            history = {}
            related = {}
            located_payment = payment
            reason_codes.append("TOOL_BUDGET_EXCEEDED")
            tool_failure_requires_review = True
        except Exception:
            order = None
            settlements = []
            refunds = []
            fee_rules = []
            history = {}
            related = {}
            located_payment = payment
            reason_codes.append("TOOL_LOOKUP_FAILED")
            contradicting.append("initial lookup tool failed")
            timeline.append("Initial lookup tool failed")
            tool_failure_requires_review = True

        if located_payment:
            timeline.append("Payment located")
            supporting.append(f"EVD_PAYMENT_{payment.payment_id}")
        if order:
            timeline.append("Order matched by exact order_id")
            supporting.append(f"EVD_ORDER_{order.order_id}")
        else:
            timeline.append("Order could not be matched")
            contradicting.append("missing_order")
            reason_codes.append("MISSING_ORDER")

        if settlements:
            timeline.append(f"{len(settlements)} settlement record(s) located")
            supporting.extend(f"EVD_SETTLEMENT_{item.settlement_id}" for item in settlements)
        else:
            timeline.append("No settlement record located")

        if refunds:
            timeline.append(f"{len(refunds)} refund record(s) located")
            supporting.extend(f"EVD_REFUND_{item.refund_id}" for item in refunds)
        else:
            timeline.append("Refund history checked: no refunds")

        fee_rule = fee_rules[0] if fee_rules else None
        if fee_rule:
            timeline.append("Fee configuration checked")
            supporting.append(f"EVD_FEE_RULE_{fee_rule.fee_rule_id}")
        else:
            timeline.append("No fee rule found")
            contradicting.append("missing_fee_rule")
            reason_codes.append("MISSING_FEE_RULE")

        duplicate_info = related or {}
        is_duplicate = duplicate_info.get("canonical_payment_id") not in (None, payment.payment_id)
        if is_duplicate:
            timeline.append("Duplicate payment pattern detected")
            reason_codes.append("DUPLICATE_PAYMENT")

        refund_total = money(sum((refund.amount for refund in refunds), Decimal("0.00")))
        actual_settlement = money(sum((settlement.amount for settlement in settlements), Decimal("0.00"))) if settlements else None
        expected_fee = fee_rule.calculate_fee(payment.amount) if fee_rule else None
        expected_settlement = None
        difference = None
        temporal_result = {"valid": False, "reason": "not checked"}
        amount_result = {"within_tolerance": False}

        if expected_fee is not None:
            expected_settlement = money(payment.amount - expected_fee - refund_total)
        if actual_settlement is not None and expected_settlement is not None:
            difference = money(actual_settlement - expected_settlement)
            try:
                amount_result = tools.compare_amounts(actual_settlement, expected_settlement, self.amount_tolerance)
                if amount_result["within_tolerance"]:
                    timeline.append("Amount comparison passed deterministic tolerance")
                else:
                    timeline.append("Amount discrepancy detected")
                    reason_codes.append("AMOUNT_DIFFERENCE")
            except Exception:
                amount_result = {"within_tolerance": False, "reason": "amount comparison tool failed"}
                tool_failure_requires_review = True
                timeline.append("Amount comparison tool failed")
                reason_codes.append("AMOUNT_TOOL_FAILED")
                contradicting.append("amount comparison tool failed")

        if settlements:
            cycle_days = self._merchant_cycle_days(index, payment.merchant_id)
            try:
                temporal_result = tools.check_temporal_relationship(payment, settlements, cycle_days)
                if temporal_result["valid"]:
                    timeline.append("Settlement timing verified")
                else:
                    timeline.append("Settlement timing violates configured window")
                    reason_codes.append("SETTLEMENT_TIMING")
            except Exception:
                temporal_result = {"valid": False, "reason": "temporal relationship tool failed"}
                tool_failure_requires_review = True
                timeline.append("Temporal relationship tool failed")
                reason_codes.append("TEMPORAL_TOOL_FAILED")
                contradicting.append("temporal relationship tool failed")

        status, impact = self._classify(
            payment=payment,
            order_exists=order is not None,
            fee_rule=fee_rule,
            settlements_present=bool(settlements),
            refund_total=refund_total,
            expected_settlement=expected_settlement,
            actual_settlement=actual_settlement,
            difference=difference,
            amount_within_tolerance=bool(amount_result.get("within_tolerance")),
            temporal_valid=bool(temporal_result.get("valid")),
            is_duplicate=is_duplicate,
            refunds_before_settlement=self._refunds_before_settlement(refunds, settlements),
            reason_codes=reason_codes,
            contradicting=contradicting,
            timeline=timeline,
        )

        if tool_failure_requires_review and status not in TERMINAL_REVIEW_STATUSES:
            status = ReconciliationStatus.HUMAN_REVIEW
            impact = impact if impact > 0 else payment.amount
            confidence = min(0.62, 0.55)
            band = self._confidence_band(confidence)
            reason_codes.append("TOOL_CHECK_FAILED")
            timeline.append("Tool check failed; escalated to human review")

        confidence = self._confidence_score(
            status=status,
            order_exists=order is not None,
            settlements_present=bool(settlements),
            fee_rule_exists=fee_rule is not None,
            amount_checked=actual_settlement is not None and expected_settlement is not None,
            amount_within_tolerance=bool(amount_result.get("within_tolerance")),
            temporal_checked=bool(settlements),
            temporal_valid=bool(temporal_result.get("valid")),
            is_duplicate=is_duplicate,
            contradictions=len(contradicting),
        )
        band = self._confidence_band(confidence)

        verification = self._verify(
            status=status,
            payment=payment,
            fee_rule=fee_rule,
            settlements_present=bool(settlements),
            refunds_present=bool(refunds),
            refund_total=refund_total,
            amount_within_tolerance=bool(amount_result.get("within_tolerance")),
            temporal_valid=bool(temporal_result.get("valid")),
            is_duplicate=is_duplicate,
            difference=difference,
            expected_settlement=expected_settlement,
            actual_settlement=actual_settlement,
            refunds_before_settlement=self._refunds_before_settlement(refunds, settlements),
        )

        if not verification.passed and status not in TERMINAL_REVIEW_STATUSES:
            reason_codes.append("VERIFICATION_FAILED")
            contradicting.extend(verification.challenges)
            status = ReconciliationStatus.HUMAN_REVIEW
            confidence = min(confidence, 0.62)
            band = self._confidence_band(confidence)
            timeline.append("Verification failed; escalated to human review")
            verification = self._verify(
                status=status,
                payment=payment,
                fee_rule=fee_rule,
                settlements_present=bool(settlements),
                refunds_present=bool(refunds),
                refund_total=refund_total,
                amount_within_tolerance=bool(amount_result.get("within_tolerance")),
                temporal_valid=bool(temporal_result.get("valid")),
                is_duplicate=is_duplicate,
                difference=difference,
                expected_settlement=expected_settlement,
                actual_settlement=actual_settlement,
                refunds_before_settlement=self._refunds_before_settlement(refunds, settlements),
            )

        evidence = build_evidence_items(payment, order, settlements, refunds, fee_rule)
        evidence_ids = [item.evidence_id for item in evidence]
        invariants = self.invariants.evaluate(
            payment=payment,
            order=order,
            settlements=settlements,
            refunds=refunds,
            fee_rule=fee_rule,
            expected_settlement=expected_settlement,
            actual_settlement=actual_settlement,
            duplicate_info=duplicate_info,
        )
        blocking_invariants = self._blocking_invariant_failures(status, invariants)
        if blocking_invariants:
            status = ReconciliationStatus.HUMAN_REVIEW
            impact = impact if impact > 0 else payment.amount
            confidence = min(confidence, 0.62)
            band = self._confidence_band(confidence)
            reason_codes.append("BLOCKING_INVARIANT_FAILED")
            reason_codes.extend(f"INVARIANT_FAILED_{item.rule_id}" for item in blocking_invariants)
            contradicting.extend(item.reason for item in blocking_invariants)
            timeline.append("Blocking invariant failed; escalated to human review")
            verification = self._verify(
                status=status,
                payment=payment,
                fee_rule=fee_rule,
                settlements_present=bool(settlements),
                refunds_present=bool(refunds),
                refund_total=refund_total,
                amount_within_tolerance=bool(amount_result.get("within_tolerance")),
                temporal_valid=bool(temporal_result.get("valid")),
                is_duplicate=is_duplicate,
                difference=difference,
                expected_settlement=expected_settlement,
                actual_settlement=actual_settlement,
                refunds_before_settlement=self._refunds_before_settlement(refunds, settlements),
            )
        confidence_factors = self._confidence_factors(
            order_exists=order is not None,
            settlements_present=bool(settlements),
            fee_rule_exists=fee_rule is not None,
            amount_checked=actual_settlement is not None and expected_settlement is not None,
            amount_within_tolerance=bool(amount_result.get("within_tolerance")),
            temporal_checked=bool(settlements),
            temporal_valid=bool(temporal_result.get("valid")),
            verification_passed=verification.passed,
            failed_invariant_count=sum(1 for item in invariants if str(item.status) == "FAILED"),
        )
        risk_score, risk_factors = self._risk_score(
            payment=payment,
            index=index,
            status=status,
            impact=impact,
            confidence=confidence,
            invariants=invariants,
            settlements_present=bool(settlements),
            is_duplicate=is_duplicate,
            contradictions=len(contradicting),
        )
        ai_investigation = None
        if self.enable_ai and self._should_run_ai(status, confidence, invariants):
            ai_investigation = self.ai_agent.investigate(
                payment=payment,
                tools=tools,
                status=status,
                reason_codes=reason_codes,
                evidence_ids=evidence_ids,
                supporting_evidence=supporting,
                contradicting_evidence=[str(item) for item in contradicting],
                invariants=invariants,
                fee_rule=fee_rule,
                settlements_present=bool(settlements),
                refunds_present=bool(refunds),
                amount_within_tolerance=bool(amount_result.get("within_tolerance")),
                temporal_valid=bool(temporal_result.get("valid")),
                is_duplicate=is_duplicate,
                verification_passed=verification.passed,
            )
            timeline.append(f"AI investigation considered {len(ai_investigation.hypotheses)} hypothesis path(s)")
            supporting.extend(ai_investigation.supporting_evidence_ids)
            contradicting.extend(ai_investigation.contradicting_evidence_ids)
            if ai_investigation.ai_unavailable:
                reason_codes.append("AI_UNAVAILABLE")
                status = ReconciliationStatus.HUMAN_REVIEW
                impact = impact if impact > 0 else payment.amount
                confidence = min(confidence, 0.55)
                confidence_factors["ai_available"] = 0.0
                timeline.append("Configured AI provider unavailable; escalated to human review")
                verification = self._verify(
                    status=status,
                    payment=payment,
                    fee_rule=fee_rule,
                    settlements_present=bool(settlements),
                    refunds_present=bool(refunds),
                    refund_total=refund_total,
                    amount_within_tolerance=bool(amount_result.get("within_tolerance")),
                    temporal_valid=bool(temporal_result.get("valid")),
                    is_duplicate=is_duplicate,
                    difference=difference,
                    expected_settlement=expected_settlement,
                    actual_settlement=actual_settlement,
                    refunds_before_settlement=self._refunds_before_settlement(refunds, settlements),
                )
            else:
                confidence = self._blend_ai_confidence(confidence, ai_investigation.confidence_factors, ai_investigation.negative_factors)
                refined_status, refined_impact, refined_verification, refined = self._apply_ai_verified_refinement(
                    status=status,
                    impact=impact,
                    payment=payment,
                    fee_rule=fee_rule,
                    settlements_present=bool(settlements),
                    refunds_present=bool(refunds),
                    refund_total=refund_total,
                    amount_within_tolerance=bool(amount_result.get("within_tolerance")),
                    temporal_valid=bool(temporal_result.get("valid")),
                    is_duplicate=is_duplicate,
                    difference=difference,
                    expected_settlement=expected_settlement,
                    actual_settlement=actual_settlement,
                    refunds_before_settlement=self._refunds_before_settlement(refunds, settlements),
                    reason_codes=reason_codes,
                    invariants=invariants,
                    ai_investigation=ai_investigation,
                )
                if refined:
                    status = refined_status
                    impact = refined_impact
                    verification = refined_verification
                    reason_codes.append("AI_VERIFIED_REFUND_MISMATCH")
                    confidence = max(confidence, 0.78)
                    confidence_factors["ai_verified_refinement"] = 1.0
                    confidence_factors["verification_passed"] = 1.0 if verification.passed else 0.0
                    ai_investigation.recommendation = status
                    ai_investigation.verification_summary["controller_refinement"] = status.value
                    timeline.append("AI-supported refund mismatch was verified by deterministic controls")
                confidence_factors["ai_available"] = 1.0
            band = self._confidence_band(confidence)

        risk_score, risk_factors = self._risk_score(
            payment=payment,
            index=index,
            status=status,
            impact=impact,
            confidence=confidence,
            invariants=invariants,
            settlements_present=bool(settlements),
            is_duplicate=is_duplicate,
            contradictions=len(contradicting),
        )

        graph = build_graph(
            payment,
            order,
            settlements,
            refunds,
            fee_rule,
            case_id=case_id,
            status=status,
            evidence_items=evidence,
            supporting_evidence=sorted(set(supporting)),
            contradicting_evidence=sorted(set(str(item) for item in contradicting)),
            ai_investigation=ai_investigation,
            risk_score=risk_score,
        )

        decision = ControllerDecision(
            case_id=case_id,
            payment_id=payment.payment_id,
            status=status,
            confidence_score=round(confidence, 4),
            confidence_band=band,
            financial_impact=impact,
            expected_settlement=expected_settlement,
            actual_settlement=actual_settlement,
            expected_fee=expected_fee,
            refund_total=refund_total,
            difference=difference,
            reason_codes=sorted(set(reason_codes)),
            evidence_ids=evidence_ids,
            supporting_evidence=sorted(set(supporting)),
            contradicting_evidence=sorted(set(str(item) for item in contradicting)),
            confidence_factors=confidence_factors,
            risk_score=risk_score,
            risk_factors=risk_factors,
            invariants=invariants,
            ai_investigation=ai_investigation,
            verification=verification,
        )

        audit.record(
            actor="controller",
            action="decision_verified",
            entity="reconciliation_case",
            entity_id=case_id,
            reason=f"final status {status}",
            output_ref=decision.model_dump(mode="json"),
        )

        return ReconciliationCase(
            case_id=case_id,
            run_id=run_id,
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            merchant_id=payment.merchant_id,
            status=status,
            decision=decision,
            graph=graph,
            evidence=evidence,
            tool_calls=tools.calls,
            invariants=invariants,
            ai_investigation=ai_investigation,
            risk_score=risk_score,
            risk_factors=risk_factors,
            investigation_timeline=timeline,
        )

    def _classify(
        self,
        payment: Payment,
        order_exists: bool,
        fee_rule: Optional[FeeRule],
        settlements_present: bool,
        refund_total: Decimal,
        expected_settlement: Optional[Decimal],
        actual_settlement: Optional[Decimal],
        difference: Optional[Decimal],
        amount_within_tolerance: bool,
        temporal_valid: bool,
        is_duplicate: bool,
        refunds_before_settlement: bool,
        reason_codes: List[str],
        contradicting: List[str],
        timeline: List[str],
    ) -> Tuple[ReconciliationStatus, Decimal]:
        if is_duplicate:
            return ReconciliationStatus.DUPLICATE, payment.amount
        if not order_exists:
            return ReconciliationStatus.HUMAN_REVIEW, payment.amount
        if not settlements_present:
            impact = expected_settlement if expected_settlement is not None else payment.amount
            return ReconciliationStatus.MISSING_SETTLEMENT, impact
        if fee_rule is None or expected_settlement is None or actual_settlement is None:
            return ReconciliationStatus.HUMAN_REVIEW, payment.amount

        if refund_total > 0 and refunds_before_settlement and difference is not None and difference > self.amount_tolerance:
            reason_codes.append("REFUND_CONFLICT")
            contradicting.append("refund existed before settlement but net settlement does not reflect it")
            timeline.append("Refund evidence conflicts with settlement math")
            return ReconciliationStatus.HUMAN_REVIEW, abs(difference)

        if amount_within_tolerance:
            if not temporal_valid:
                return ReconciliationStatus.TIMING_MISMATCH, Decimal("0.00")
            if refund_total > 0:
                return ReconciliationStatus.REFUND_ADJUSTED, Decimal("0.00")
            if fee_rule.calculate_fee(payment.amount) > 0:
                return ReconciliationStatus.FEE_EXPLAINED, Decimal("0.00")
            return ReconciliationStatus.MATCHED, Decimal("0.00")

        if difference is None:
            return ReconciliationStatus.UNRESOLVED, payment.amount

        if actual_settlement > 0 and actual_settlement < expected_settlement:
            ratio = actual_settlement / max(expected_settlement, Decimal("1.00"))
            if Decimal("0.25") <= ratio <= Decimal("0.85"):
                return ReconciliationStatus.PARTIAL_MATCH, abs(difference)

        return ReconciliationStatus.AMOUNT_MISMATCH, abs(difference)

    def _verify(
        self,
        status: ReconciliationStatus,
        payment: Payment,
        fee_rule: Optional[FeeRule],
        settlements_present: bool,
        refunds_present: bool,
        refund_total: Decimal,
        amount_within_tolerance: bool,
        temporal_valid: bool,
        is_duplicate: bool,
        difference: Optional[Decimal],
        expected_settlement: Optional[Decimal],
        actual_settlement: Optional[Decimal],
        refunds_before_settlement: bool,
    ) -> VerificationResult:
        checks: List[Dict[str, Any]] = []
        challenges: List[str] = []

        def add_check(name: str, passed: bool, detail: str) -> None:
            checks.append({"check": name, "passed": passed, "detail": detail})
            if not passed:
                challenges.append(detail)

        if status == ReconciliationStatus.FEE_EXPLAINED:
            add_check("fee_rule_exists", fee_rule is not None, "fee rule is missing")
            add_check("amounts_match", amount_within_tolerance, "settlement does not match fee-adjusted expectation")
            add_check("no_refund_driver", not refunds_present, "refund evidence could explain the difference instead")
            add_check("not_duplicate", not is_duplicate, "duplicate evidence exists")
            add_check("timing_valid", temporal_valid, "settlement timing is outside the configured window")
        elif status == ReconciliationStatus.REFUND_ADJUSTED:
            add_check("refund_exists", refunds_present and refund_total > 0, "refund evidence is missing")
            add_check("refund_before_settlement", refunds_before_settlement, "refund occurred after settlement window")
            add_check("amounts_match", amount_within_tolerance, "settlement does not reflect refund-adjusted expectation")
        elif status == ReconciliationStatus.MATCHED:
            add_check("settlement_exists", settlements_present, "settlement is missing")
            add_check("amounts_match", amount_within_tolerance, "gross settlement does not match payment")
            add_check("no_refunds", not refunds_present, "refund exists on a matched case")
        elif status == ReconciliationStatus.DUPLICATE:
            add_check("duplicate_detected", is_duplicate, "no exact duplicate relationship found")
        elif status == ReconciliationStatus.MISSING_SETTLEMENT:
            add_check("settlement_missing", not settlements_present, "settlement exists, so missing-settlement decision is invalid")
            add_check("not_duplicate", not is_duplicate, "duplicate should be classified before missing settlement")
        elif status == ReconciliationStatus.TIMING_MISMATCH:
            add_check("settlement_exists", settlements_present, "settlement is missing")
            add_check("amounts_match", amount_within_tolerance, "amount mismatch should be classified before timing")
            add_check("timing_invalid", not temporal_valid, "settlement timing is valid")
        elif status == ReconciliationStatus.PARTIAL_MATCH:
            add_check("settlement_exists", settlements_present, "settlement is missing")
            add_check("amount_difference", difference is not None and abs(difference) > self.amount_tolerance, "no material difference exists")
            add_check(
                "less_than_expected",
                actual_settlement is not None and expected_settlement is not None and actual_settlement < expected_settlement,
                "actual settlement is not less than expected",
            )
        elif status == ReconciliationStatus.AMOUNT_MISMATCH:
            add_check("settlement_exists", settlements_present, "settlement is missing")
            add_check("material_difference", difference is not None and abs(difference) > self.amount_tolerance, "difference is within tolerance")
            add_check("not_duplicate", not is_duplicate, "duplicate evidence exists")
        elif status == ReconciliationStatus.HUMAN_REVIEW:
            add_check("requires_review", True, "evidence conflict or verification failure requires review")
        elif status == ReconciliationStatus.UNRESOLVED:
            add_check("unresolved_allowed", True, "no deterministic explanation exists")

        return VerificationResult(decision_status=status, passed=len(challenges) == 0, challenges=challenges, checks=checks)

    def _confidence_score(
        self,
        status: ReconciliationStatus,
        order_exists: bool,
        settlements_present: bool,
        fee_rule_exists: bool,
        amount_checked: bool,
        amount_within_tolerance: bool,
        temporal_checked: bool,
        temporal_valid: bool,
        is_duplicate: bool,
        contradictions: int,
    ) -> float:
        if is_duplicate and status == ReconciliationStatus.DUPLICATE:
            base = 0.92
        else:
            base = 0.10
            base += 0.18 if order_exists else 0.0
            base += 0.16 if settlements_present else 0.0
            base += 0.14 if fee_rule_exists else 0.0
            if amount_checked:
                base += 0.22 if amount_within_tolerance else 0.16
            if temporal_checked:
                base += 0.10 if temporal_valid else 0.06
            base += 0.08

        if status in (ReconciliationStatus.MISSING_SETTLEMENT, ReconciliationStatus.AMOUNT_MISMATCH, ReconciliationStatus.PARTIAL_MATCH):
            base += 0.06
        if status == ReconciliationStatus.HUMAN_REVIEW:
            base = min(base, 0.66)
        base -= min(0.35, contradictions * 0.18)
        return max(0.0, min(0.995, base))

    def _confidence_factors(
        self,
        order_exists: bool,
        settlements_present: bool,
        fee_rule_exists: bool,
        amount_checked: bool,
        amount_within_tolerance: bool,
        temporal_checked: bool,
        temporal_valid: bool,
        verification_passed: bool,
        failed_invariant_count: int,
    ) -> Dict[str, float]:
        return {
            "order_link": 1.0 if order_exists else 0.0,
            "settlement_link": 1.0 if settlements_present else 0.0,
            "fee_rule": 1.0 if fee_rule_exists else 0.0,
            "amount_check": 1.0 if amount_checked else 0.0,
            "amount_within_tolerance": 1.0 if amount_within_tolerance else 0.0,
            "temporal_check": 1.0 if temporal_checked else 0.0,
            "temporal_valid": 1.0 if temporal_valid else 0.0,
            "verification_passed": 1.0 if verification_passed else 0.0,
            "failed_invariant_penalty": float(failed_invariant_count),
        }

    def _should_run_ai(self, status: ReconciliationStatus, confidence: float, invariants: List[InvariantResult]) -> bool:
        status_text = status.value if isinstance(status, ReconciliationStatus) else str(status)
        if status_text not in MATCH_STATUS_VALUES:
            return True
        if confidence < 0.75:
            return True
        return any(str(item.status) == "FAILED" for item in invariants)

    def _blocking_invariant_failures(self, status: ReconciliationStatus, invariants: List[InvariantResult]) -> List[InvariantResult]:
        blocking_rule_ids = {
            "CURRENCY_CONSISTENCY",
            "MERCHANT_CONSISTENCY",
            "PAYMENT_ORDER_AMOUNT",
            "FEE_RULE_APPLICABILITY",
            "REFUND_DOES_NOT_EXCEED_PAYMENT",
        }
        failures = [item for item in invariants if str(item.status) == "FAILED"]
        blocking = [item for item in failures if item.rule_id in blocking_rule_ids]
        if status != ReconciliationStatus.DUPLICATE:
            blocking.extend(item for item in failures if item.rule_id == "DUPLICATE_CONSISTENCY")
        return blocking

    def _blend_ai_confidence(self, confidence: float, ai_factors: Dict[str, float], negative_factors: Dict[str, float]) -> float:
        selected = ai_factors.get("selected_hypothesis_confidence", 0.0)
        verification = ai_factors.get("deterministic_verification", 0.0)
        penalty = min(0.08, negative_factors.get("failed_invariants", 0.0) * 0.01)
        lift = 0.03 if selected >= 0.75 and verification >= 1.0 else 0.0
        return max(0.0, min(0.995, confidence + lift - penalty))

    def _apply_ai_verified_refinement(
        self,
        status: ReconciliationStatus,
        impact: Decimal,
        payment: Payment,
        fee_rule: Optional[FeeRule],
        settlements_present: bool,
        refunds_present: bool,
        refund_total: Decimal,
        amount_within_tolerance: bool,
        temporal_valid: bool,
        is_duplicate: bool,
        difference: Optional[Decimal],
        expected_settlement: Optional[Decimal],
        actual_settlement: Optional[Decimal],
        refunds_before_settlement: bool,
        reason_codes: List[str],
        invariants: List[InvariantResult],
        ai_investigation,
    ) -> Tuple[ReconciliationStatus, Decimal, VerificationResult, bool]:
        current_verification = self._verify(
            status=status,
            payment=payment,
            fee_rule=fee_rule,
            settlements_present=settlements_present,
            refunds_present=refunds_present,
            refund_total=refund_total,
            amount_within_tolerance=amount_within_tolerance,
            temporal_valid=temporal_valid,
            is_duplicate=is_duplicate,
            difference=difference,
            expected_settlement=expected_settlement,
            actual_settlement=actual_settlement,
            refunds_before_settlement=refunds_before_settlement,
        )
        if status != ReconciliationStatus.HUMAN_REVIEW:
            return status, impact, current_verification, False
        if "REFUND_CONFLICT" not in reason_codes or difference is None:
            return status, impact, current_verification, False

        failed_rules = {item.rule_id for item in invariants if str(item.status) == "FAILED"}
        blocking_rules = failed_rules - {"SETTLEMENT_NET_AMOUNT"}
        if blocking_rules:
            return status, impact, current_verification, False

        supported_labels = {
            hypothesis.label
            for hypothesis in ai_investigation.hypotheses
            if str(hypothesis.status) == HypothesisStatus.SUPPORTED.value
        }
        if not supported_labels.intersection({"refund_adjustment", "partial_or_incorrect_settlement", "fee_discrepancy"}):
            return status, impact, current_verification, False

        refined_status = ReconciliationStatus.AMOUNT_MISMATCH
        refined_verification = self._verify(
            status=refined_status,
            payment=payment,
            fee_rule=fee_rule,
            settlements_present=settlements_present,
            refunds_present=refunds_present,
            refund_total=refund_total,
            amount_within_tolerance=amount_within_tolerance,
            temporal_valid=temporal_valid,
            is_duplicate=is_duplicate,
            difference=difference,
            expected_settlement=expected_settlement,
            actual_settlement=actual_settlement,
            refunds_before_settlement=refunds_before_settlement,
        )
        if not refined_verification.passed:
            return status, impact, current_verification, False
        return refined_status, money(abs(difference)), refined_verification, True

    def _risk_score(
        self,
        payment: Payment,
        index: DatasetIndex,
        status: ReconciliationStatus,
        impact: Decimal,
        confidence: float,
        invariants: List[InvariantResult],
        settlements_present: bool,
        is_duplicate: bool,
        contradictions: int,
    ) -> Tuple[float, List[str]]:
        factors: List[str] = []
        score = 0.0
        status_text = status.value if isinstance(status, ReconciliationStatus) else str(status)
        if status_text not in MATCH_STATUS_VALUES:
            score += 18.0
            factors.append(f"exception_status:{status_text}")
        if status_text in {ReconciliationStatus.HUMAN_REVIEW.value, ReconciliationStatus.UNRESOLVED.value}:
            score += 12.0
            factors.append("manual_resolution_required")
        if is_duplicate:
            score += 20.0
            factors.append("duplicate_pattern")
        if not settlements_present:
            score += 14.0
            factors.append("settlement_missing")
        failed_invariants = [item for item in invariants if str(item.status) == "FAILED"]
        if failed_invariants:
            score += min(30.0, len(failed_invariants) * 8.0)
            factors.extend(f"invariant_failed:{item.rule_id}" for item in failed_invariants[:4])
        if impact > 0:
            score += min(20.0, float(impact) / 1000.0)
            factors.append("financial_impact")
        if confidence < 0.70:
            score += 10.0
            factors.append("low_confidence")
        if contradictions:
            score += min(12.0, contradictions * 4.0)
            factors.append("contradicting_evidence")
        merchant = index.merchants_by_id.get(payment.merchant_id)
        if merchant and merchant.risk_tier != "standard":
            score += 8.0
            factors.append(f"merchant_risk:{merchant.risk_tier}")
        return round(min(100.0, score), 2), sorted(set(factors))

    def _confidence_band(self, score: float) -> ConfidenceBand:
        if score >= 0.90:
            return ConfidenceBand.HIGH
        if score >= 0.75:
            return ConfidenceBand.MEDIUM
        if score >= 0.55:
            return ConfidenceBand.REVIEW
        return ConfidenceBand.LOW

    def _merchant_cycle_days(self, index: DatasetIndex, merchant_id: str) -> int:
        for merchant in index.dataset.merchants:
            if merchant.merchant_id == merchant_id:
                return merchant.settlement_cycle_days
        return 2

    def _refunds_before_settlement(self, refunds: List[Any], settlements: List[Any]) -> bool:
        if not refunds:
            return False
        if not settlements:
            return True
        first_settlement = min(settlement.settled_at for settlement in settlements)
        return all(refund.refunded_at <= first_settlement for refund in refunds)

    def _build_metrics(
        self,
        dataset: DatasetBundle,
        cases: List[ReconciliationCase],
        duration_ms: float,
        latencies: List[float],
        normalization_ms: float,
    ) -> RunMetrics:
        total = len(cases)
        total_volume = money(sum((payment.amount for payment in dataset.payments), Decimal("0.00")))
        payment_by_id = {payment.payment_id: payment for payment in dataset.payments}
        match_cases = [case for case in cases if str(case.status) in MATCH_STATUS_VALUES]
        auto_cases = [case for case in cases if str(case.status) not in TERMINAL_REVIEW_VALUES]
        exception_cases = [case for case in cases if str(case.status) not in MATCH_STATUS_VALUES]
        unresolved_cases = [case for case in cases if str(case.status) == ReconciliationStatus.UNRESOLVED.value]
        review_cases = [case for case in cases if str(case.status) == ReconciliationStatus.HUMAN_REVIEW.value]
        reconciled_amount = money(sum((payment_by_id[case.payment_id].amount for case in match_cases), Decimal("0.00")))

        throughput = total / max(duration_ms / 1000, 0.001)
        sorted_latencies = sorted(latencies or [0.0])
        p95_idx = min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95))
        p99_idx = min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.99))
        ai_cases = [case for case in cases if case.ai_investigation is not None]
        ai_cost = money(
            sum(
                (
                    case.ai_investigation.estimated_cost_usd
                    for case in ai_cases
                    if case.ai_investigation is not None
                ),
                Decimal("0.00"),
            )
        )
        ai_investigation_ms = sum(
            case.ai_investigation.duration_ms
            for case in ai_cases
            if case.ai_investigation is not None
        )

        return RunMetrics(
            transactions_processed=total,
            total_payment_volume=total_volume,
            reconciled_amount=reconciled_amount,
            normalization_ms=round(normalization_ms, 4),
            ai_investigation_ms=round(ai_investigation_ms, 4),
            match_rate=round(len(match_cases) / max(total, 1), 4),
            automatic_resolution_rate=round(len(auto_cases) / max(total, 1), 4),
            exception_rate=round(len(exception_cases) / max(total, 1), 4),
            unresolved_rate=round(len(unresolved_cases) / max(total, 1), 4),
            human_review_rate=round(len(review_cases) / max(total, 1), 4),
            throughput_records_per_sec=round(throughput, 2),
            median_latency_ms=round(statistics.median(sorted_latencies), 4),
            p95_latency_ms=round(sorted_latencies[p95_idx], 4),
            p99_latency_ms=round(sorted_latencies[p99_idx], 4),
            ai_investigation_count=len(ai_cases),
            llm_calls=sum(case.ai_investigation.llm_calls for case in ai_cases if case.ai_investigation is not None),
            agent_tool_calls=sum(len(case.tool_calls) for case in cases),
            estimated_ai_cost_usd=ai_cost,
            ai_invocation_rate=round(len(ai_cases) / max(total, 1), 4),
            average_risk_score=round(sum(case.risk_score for case in cases) / max(total, 1), 4),
        )

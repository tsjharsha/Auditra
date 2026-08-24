from __future__ import annotations

import time
import uuid
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .agent_tools import InvestigationTools, ToolBudgetExceeded
from .ai_provider import OfflineStructuredProvider, OpenAIProvider, StructuredInvestigationProvider
from .models import (
    AIInvestigationResult,
    FeeRule,
    HypothesisStatus,
    InvestigationHypothesis,
    InvariantResult,
    Payment,
    ReconciliationStatus,
    money,
    now_utc,
)


def _status_value(status: ReconciliationStatus | str) -> str:
    return status.value if isinstance(status, ReconciliationStatus) else str(status)


class AIInvestigationAgent:
    """Evidence-first hypothesis agent that stays behind deterministic controls."""

    def __init__(self, provider: Optional[StructuredInvestigationProvider] = None):
        if provider is not None:
            self.provider = provider
        elif os.getenv("AUDITRA_USE_OPENAI_INVESTIGATOR") == "1":
            self.provider = OpenAIProvider()
        else:
            self.provider = OfflineStructuredProvider()

    def investigate(
        self,
        payment: Payment,
        tools: InvestigationTools,
        status: ReconciliationStatus | str,
        reason_codes: List[str],
        evidence_ids: List[str],
        supporting_evidence: List[str],
        contradicting_evidence: List[str],
        invariants: List[InvariantResult],
        fee_rule: Optional[FeeRule],
        settlements_present: bool,
        refunds_present: bool,
        amount_within_tolerance: bool,
        temporal_valid: bool,
        is_duplicate: bool,
        verification_passed: bool,
    ) -> AIInvestigationResult:
        started_at = now_utc()
        started_perf = time.perf_counter()
        initial_tool_count = len(tools.calls)
        failed_invariants = [item.rule_id for item in invariants if str(item.status) == "FAILED"]
        context = {
            "payment_id": payment.payment_id,
            "status": _status_value(status),
            "reason_codes": reason_codes,
            "failed_invariants": failed_invariants,
            "supporting_evidence_ids": supporting_evidence,
            "contradicting_evidence_ids": contradicting_evidence,
        }

        try:
            proposal = self.provider.propose(context)
        except Exception as exc:
            proposal = OfflineStructuredProvider().propose(context)
            proposal["provider_error"] = str(exc)

        labels = proposal.get("candidate_labels", ["matched_low_risk"])
        hypotheses: List[InvestigationHypothesis] = []
        for label in labels:
            hypotheses.append(
                self._investigate_label(
                    label=label,
                    payment=payment,
                    tools=tools,
                    evidence_ids=evidence_ids,
                    supporting_evidence=supporting_evidence,
                    contradicting_evidence=contradicting_evidence,
                    invariants=invariants,
                    fee_rule=fee_rule,
                    settlements_present=settlements_present,
                    refunds_present=refunds_present,
                    amount_within_tolerance=amount_within_tolerance,
                    temporal_valid=temporal_valid,
                    is_duplicate=is_duplicate,
                    reason_codes=reason_codes,
                )
            )

        selected = max(hypotheses, key=lambda item: item.confidence) if hypotheses else None
        status_text = _status_value(status)
        escalation_reason = None
        if status_text in {"HUMAN_REVIEW", "UNRESOLVED"}:
            escalation_reason = "Deterministic controller requires review or unresolved handling."
        elif not verification_passed:
            escalation_reason = "Deterministic verification did not pass."

        usage = proposal.get("usage")
        llm_calls = int(getattr(usage, "llm_calls", 0))
        input_tokens = int(getattr(usage, "input_tokens", 0))
        output_tokens = int(getattr(usage, "output_tokens", 0))
        estimated_cost = Decimal(str(getattr(usage, "estimated_cost_usd", "0.00")))
        finished_at = now_utc()
        duration_ms = (time.perf_counter() - started_perf) * 1000
        failed_count = len(failed_invariants)
        passed_count = sum(1 for item in invariants if str(item.status) == "PASSED")
        invariant_total = max(len(invariants), 1)

        return AIInvestigationResult(
            investigation_id=f"INV_{uuid.uuid4().hex[:12]}",
            payment_id=payment.payment_id,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            mode="ai_assisted_offline" if llm_calls == 0 else "ai_assisted_llm",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round(duration_ms, 4),
            llm_calls=llm_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=money(estimated_cost),
            hypotheses=hypotheses,
            selected_hypothesis_id=selected.hypothesis_id if selected else None,
            recommendation=status,
            rationale=self._rationale(status_text, selected),
            self_challenge=proposal.get("self_challenge", []),
            supporting_evidence_ids=sorted(set(selected.supporting_evidence_ids if selected else supporting_evidence)),
            contradicting_evidence_ids=sorted(set(selected.contradicting_evidence_ids if selected else contradicting_evidence)),
            confidence_factors={
                "invariant_pass_rate": round(passed_count / invariant_total, 4),
                "selected_hypothesis_confidence": round(selected.confidence if selected else 0.0, 4),
                "deterministic_verification": 1.0 if verification_passed else 0.0,
            },
            negative_factors={
                "failed_invariants": float(failed_count),
                "contradiction_count": float(len(contradicting_evidence)),
            },
            verification_summary={
                "deterministic_status": status_text,
                "deterministic_verification_passed": verification_passed,
                "ai_may_override_arithmetic": False,
            },
            escalation_reason=escalation_reason,
            tool_call_count=len(tools.calls) - initial_tool_count,
        )

    def _investigate_label(
        self,
        label: str,
        payment: Payment,
        tools: InvestigationTools,
        evidence_ids: List[str],
        supporting_evidence: List[str],
        contradicting_evidence: List[str],
        invariants: List[InvariantResult],
        fee_rule: Optional[FeeRule],
        settlements_present: bool,
        refunds_present: bool,
        amount_within_tolerance: bool,
        temporal_valid: bool,
        is_duplicate: bool,
        reason_codes: List[str],
    ) -> InvestigationHypothesis:
        before_calls = len(tools.calls)
        label_evidence = self._evidence_for_label(label, evidence_ids, invariants)
        try:
            created = tools.create_hypothesis(label, label_evidence)
            hypothesis_id = created["hypothesis_id"]
            tool_notes = self._run_dynamic_tools(label, payment, tools, fee_rule)
            checks = self._checks_for_label(
                label,
                settlements_present=settlements_present,
                refunds_present=refunds_present,
                amount_within_tolerance=amount_within_tolerance,
                temporal_valid=temporal_valid,
                is_duplicate=is_duplicate,
                reason_codes=reason_codes,
                invariants=invariants,
                tool_notes=tool_notes,
            )
            verified = tools.verify_hypothesis(hypothesis_id, checks)
        except ToolBudgetExceeded:
            hypothesis_id = f"HYP_{uuid.uuid4().hex[:10]}"
            checks = [{"check": "tool_budget", "passed": False, "detail": "Tool-call budget exceeded"}]
            verified = {"passed": False, "failed_checks": checks}

        tool_call_ids = [call.call_id for call in tools.calls[before_calls:]]
        status = self._hypothesis_status(checks)
        confidence = self._hypothesis_confidence(status, checks, verified)
        local_contradictions = list(contradicting_evidence)
        if status == HypothesisStatus.REJECTED:
            local_contradictions.extend(item.get("detail", item.get("check", "")) for item in checks if not item.get("passed"))

        return InvestigationHypothesis(
            hypothesis_id=hypothesis_id,
            label=label,
            status=status,
            confidence=confidence,
            supporting_evidence_ids=sorted(set(label_evidence + supporting_evidence)),
            contradicting_evidence_ids=sorted(set(str(item) for item in local_contradictions if item)),
            tool_call_ids=tool_call_ids,
            verification_checks=checks,
            rationale=self._hypothesis_rationale(label, status),
        )

    def _run_dynamic_tools(
        self,
        label: str,
        payment: Payment,
        tools: InvestigationTools,
        fee_rule: Optional[FeeRule],
    ) -> Dict[str, Any]:
        notes: Dict[str, Any] = {}
        tools.find_merchant(payment.merchant_id)
        if label == "duplicate_or_replayed_payment":
            notes["duplicate"] = tools.check_duplicate(payment)
            notes["related_transactions"] = tools.find_related_transactions(payment)
        elif label == "missing_or_delayed_settlement":
            notes["graph_neighborhood"] = tools.get_graph_neighborhood(payment.payment_id)
            notes["related_transactions"] = tools.find_related_transactions(payment)
        elif label == "fee_discrepancy":
            notes["fee_applicability"] = tools.check_fee_applicability(fee_rule, payment)
        elif label == "refund_adjustment":
            notes["refunds"] = tools.find_refunds(payment.payment_id)
            notes["graph_neighborhood"] = tools.get_graph_neighborhood(payment.payment_id)
        elif label == "partial_or_incorrect_settlement":
            notes["settlements"] = tools.find_settlement(payment.payment_id)
            notes["graph_neighborhood"] = tools.get_graph_neighborhood(payment.payment_id)
        elif label == "settlement_timing_mismatch":
            notes["history"] = tools.get_transaction_history(payment.payment_id)
            notes["graph_neighborhood"] = tools.get_graph_neighborhood(payment.payment_id)
        elif label == "unlinked_or_misaligned_order":
            notes["order"] = tools.find_order(payment.order_id)
            notes["related_transactions"] = tools.find_related_transactions(payment)
        return notes

    def _checks_for_label(
        self,
        label: str,
        settlements_present: bool,
        refunds_present: bool,
        amount_within_tolerance: bool,
        temporal_valid: bool,
        is_duplicate: bool,
        reason_codes: List[str],
        invariants: List[InvariantResult],
        tool_notes: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        failed_rules = {item.rule_id for item in invariants if str(item.status) == "FAILED"}
        if label == "duplicate_or_replayed_payment":
            duplicate = tool_notes.get("duplicate", {})
            return [
                {"check": "duplicate_detected", "passed": is_duplicate or bool(duplicate.get("is_duplicate")), "detail": "Duplicate evidence found"},
                {"check": "canonical_known", "passed": bool(duplicate.get("canonical_payment_id")), "detail": "Canonical payment identified"},
            ]
        if label == "missing_or_delayed_settlement":
            return [
                {"check": "settlement_absent", "passed": not settlements_present, "detail": "No settlement linked to payment"},
                {"check": "relationship_gap", "passed": "RELATIONSHIP_COMPLETENESS" in failed_rules, "detail": "Required relationship is missing"},
            ]
        if label == "fee_discrepancy":
            applicability = tool_notes.get("fee_applicability", {})
            return [
                {"check": "fee_rule_available", "passed": bool(applicability.get("fee_rule_id")), "detail": "Fee rule exists"},
                {"check": "fee_rule_applicable", "passed": bool(applicability.get("applicable")), "detail": "Fee rule applies to payment"},
                {"check": "amount_requires_explanation", "passed": not amount_within_tolerance, "detail": "Amount difference needs explanation"},
            ]
        if label == "refund_adjustment":
            refunds = tool_notes.get("refunds", [])
            return [
                {"check": "refunds_present", "passed": refunds_present or bool(refunds), "detail": "Refund evidence exists"},
                {"check": "amount_explained_or_reviewed", "passed": not amount_within_tolerance or refunds_present, "detail": "Refund can affect net settlement"},
            ]
        if label == "partial_or_incorrect_settlement":
            return [
                {"check": "settlement_present", "passed": settlements_present, "detail": "Settlement evidence exists"},
                {"check": "net_amount_failed", "passed": "SETTLEMENT_NET_AMOUNT" in failed_rules, "detail": "Net-settlement invariant failed"},
            ]
        if label == "settlement_timing_mismatch":
            return [
                {"check": "settlement_present", "passed": settlements_present, "detail": "Settlement evidence exists"},
                {"check": "timing_invalid", "passed": not temporal_valid or "SETTLEMENT_TIMING" in reason_codes, "detail": "Settlement timing is invalid"},
            ]
        if label == "unlinked_or_misaligned_order":
            return [
                {"check": "missing_order_reason", "passed": "MISSING_ORDER" in reason_codes, "detail": "Order link is missing or invalid"},
            ]
        return [{"check": "low_risk_match", "passed": not failed_rules and amount_within_tolerance, "detail": "No failed invariant found"}]

    def _hypothesis_status(self, checks: List[Dict[str, Any]]) -> HypothesisStatus:
        if not checks:
            return HypothesisStatus.INCONCLUSIVE
        passed = sum(1 for item in checks if bool(item.get("passed")))
        if passed == len(checks):
            return HypothesisStatus.SUPPORTED
        if passed == 0:
            return HypothesisStatus.REJECTED
        return HypothesisStatus.INCONCLUSIVE

    def _hypothesis_confidence(self, status: HypothesisStatus, checks: List[Dict[str, Any]], verified: Dict[str, Any]) -> float:
        passed = sum(1 for item in checks if bool(item.get("passed")))
        ratio = passed / max(len(checks), 1)
        base = 0.25 + (0.55 * ratio)
        if status == HypothesisStatus.SUPPORTED and verified.get("passed"):
            base += 0.15
        if status == HypothesisStatus.REJECTED:
            base = min(base, 0.35)
        return round(max(0.0, min(0.98, base)), 4)

    def _evidence_for_label(self, label: str, evidence_ids: List[str], invariants: List[InvariantResult]) -> List[str]:
        relevant_rules = {
            "duplicate_or_replayed_payment": {"DUPLICATE_CONSISTENCY"},
            "missing_or_delayed_settlement": {"RELATIONSHIP_COMPLETENESS", "SETTLEMENT_NET_AMOUNT"},
            "fee_discrepancy": {"FEE_RULE_APPLICABILITY", "SETTLEMENT_NET_AMOUNT"},
            "refund_adjustment": {"REFUND_DOES_NOT_EXCEED_PAYMENT", "SETTLEMENT_NET_AMOUNT"},
            "partial_or_incorrect_settlement": {"SETTLEMENT_NET_AMOUNT"},
            "settlement_timing_mismatch": {"TEMPORAL_PAYMENT_BEFORE_SETTLEMENT"},
            "unlinked_or_misaligned_order": {"PAYMENT_ORDER_AMOUNT", "RELATIONSHIP_COMPLETENESS"},
        }.get(label, set())
        selected = []
        for invariant in invariants:
            if invariant.rule_id in relevant_rules:
                selected.extend(invariant.evidence_ids)
        return sorted(set(selected or evidence_ids))

    def _hypothesis_rationale(self, label: str, status: HypothesisStatus) -> str:
        return f"{label} is {status.value.lower()} by logged tools and invariant checks."

    def _rationale(self, status_text: str, selected: Optional[InvestigationHypothesis]) -> str:
        if selected is None:
            return "No hypothesis was selected."
        return (
            f"Selected {selected.label} while preserving deterministic status {status_text}; "
            "AI output is explanatory and cannot override verified arithmetic."
        )

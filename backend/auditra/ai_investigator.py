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

    model_tool_allowlist = {
        "find_payment",
        "find_order",
        "find_settlement",
        "find_refunds",
        "find_fee_rules",
        "find_merchant",
        "find_related_transactions",
        "get_transaction_history",
        "get_graph_neighborhood",
        "compare_amounts",
        "check_temporal_relationship",
        "check_fee_applicability",
        "check_duplicate",
        "get_evidence",
    }

    known_labels = {
        "fee_discrepancy",
        "refund_adjustment",
        "partial_or_incorrect_settlement",
        "missing_or_delayed_settlement",
        "duplicate_or_replayed_payment",
        "settlement_timing_mismatch",
        "unlinked_or_misaligned_order",
        "matched_low_risk",
    }
    max_model_tool_plan_steps = 24

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
            "order_id": payment.order_id,
            "merchant_id": payment.merchant_id,
            "payment_amount": str(payment.amount),
            "payment_currency": payment.currency,
            "status": _status_value(status),
            "reason_codes": reason_codes,
            "failed_invariants": failed_invariants,
            "supporting_evidence_ids": supporting_evidence,
            "contradicting_evidence_ids": contradicting_evidence,
            "relationships": {
                "settlement_present": settlements_present,
                "refund_present": refunds_present,
                "amount_within_tolerance": amount_within_tolerance,
                "temporal_valid": temporal_valid,
                "duplicate_pattern": is_duplicate,
            },
            "available_tools": sorted(self.model_tool_allowlist),
            "guardrails": [
                "Use only visible transaction evidence.",
                "Do not access evaluator ground truth.",
                "Do not override deterministic arithmetic or invariant checks.",
                "Escalate if evidence conflicts.",
            ],
        }

        try:
            proposal = self.provider.propose(context)
        except Exception as exc:
            return self._ai_unavailable_result(payment, tools, status, started_at, started_perf, exc)

        labels = [label for label in proposal.get("candidate_labels", ["matched_low_risk"]) if label in self.known_labels]
        if not labels:
            labels = ["matched_low_risk"]
        tool_plan = self._group_tool_plan(proposal.get("tool_plan", []))
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
                    tool_plan=tool_plan.get(label, []),
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
        provider_attempts = int(getattr(usage, "attempts", 0))
        provider_latency_ms = float(getattr(usage, "latency_ms", 0.0))
        finished_at = now_utc()
        duration_ms = (time.perf_counter() - started_perf) * 1000
        failed_count = len(failed_invariants)
        passed_count = sum(1 for item in invariants if str(item.status) == "PASSED")
        invariant_total = max(len(invariants), 1)

        return AIInvestigationResult(
            investigation_id=f"INV_{uuid.uuid4().hex[:12]}",
            payment_id=payment.payment_id,
            case_id=tools.case_id,
            objective="Select evidence-backed hypotheses and safe tool calls for this reconciliation case.",
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            mode="ai_assisted_offline" if llm_calls == 0 else "ai_assisted_llm",
            prompt_version=self.provider.prompt_version,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round(duration_ms, 4),
            llm_calls=llm_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=money(estimated_cost),
            provider_attempts=provider_attempts,
            provider_latency_ms=round(provider_latency_ms, 4),
            available_tools=sorted(self.model_tool_allowlist),
            verification_requirements=proposal.get("verification_requirements", []),
            max_tool_calls=tools.max_calls,
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
                "tool_plan_steps_requested": sum(len(steps) for steps in tool_plan.values()),
            },
            escalation_reason=escalation_reason,
            tool_call_count=len(tools.calls) - initial_tool_count,
        )

    def _ai_unavailable_result(
        self,
        payment: Payment,
        tools: InvestigationTools,
        status: ReconciliationStatus | str,
        started_at,
        started_perf: float,
        exc: Exception,
    ) -> AIInvestigationResult:
        finished_at = now_utc()
        status_text = _status_value(status)
        return AIInvestigationResult(
            investigation_id=f"INV_{uuid.uuid4().hex[:12]}",
            payment_id=payment.payment_id,
            case_id=tools.case_id,
            objective="Select evidence-backed hypotheses and safe tool calls for this reconciliation case.",
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            mode="ai_unavailable",
            prompt_version=self.provider.prompt_version,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round((time.perf_counter() - started_perf) * 1000, 4),
            ai_unavailable=True,
            provider_error=str(exc)[:300],
            provider_attempts=1,
            available_tools=sorted(self.model_tool_allowlist),
            verification_requirements=["Escalate because the configured AI provider did not return a valid typed plan."],
            max_tool_calls=tools.max_calls,
            recommendation=ReconciliationStatus.HUMAN_REVIEW,
            rationale="Configured AI provider was unavailable; no synthetic hypothesis was substituted.",
            self_challenge=["No LLM-backed self-challenge was available."],
            confidence_factors={"deterministic_verification": 0.0},
            negative_factors={"ai_unavailable": 1.0},
            verification_summary={
                "deterministic_status": status_text,
                "deterministic_verification_passed": False,
                "ai_available": False,
                "ai_may_override_arithmetic": False,
            },
            escalation_reason="AI_UNAVAILABLE",
            tool_call_count=0,
        )

    def _group_tool_plan(self, tool_plan: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        accepted = 0
        for raw_step in tool_plan:
            if accepted >= self.max_model_tool_plan_steps:
                break
            step = raw_step.model_dump(mode="json") if hasattr(raw_step, "model_dump") else raw_step
            if not isinstance(step, dict):
                continue
            label = str(step.get("hypothesis_label", ""))
            tool_name = str(step.get("tool_name", ""))
            if label not in self.known_labels or tool_name not in self.model_tool_allowlist:
                continue
            grouped.setdefault(label, []).append(step)
            accepted += 1
        return grouped

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
        tool_plan: List[Dict[str, Any]],
    ) -> InvestigationHypothesis:
        before_calls = len(tools.calls)
        label_evidence = self._evidence_for_label(label, evidence_ids, invariants)
        hypothesis_id = f"HYP_{uuid.uuid4().hex[:10]}"
        checks: List[Dict[str, Any]] = []
        try:
            created = tools.create_hypothesis(label, label_evidence)
            hypothesis_id = created["hypothesis_id"]
            tool_notes = self._run_dynamic_tools(label, payment, tools, fee_rule, tool_plan)
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
            checks = [{"check": "tool_budget", "passed": False, "detail": "Tool-call budget exceeded"}]
            verified = {"passed": False, "failed_checks": checks}
        except Exception as exc:
            checks = [{"check": "tool_execution", "passed": False, "detail": f"{type(exc).__name__}: {str(exc)[:160]}"}]
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
        tool_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        notes: Dict[str, Any] = {}
        steps = tool_plan or self._fallback_tool_plan(label)
        for step in steps:
            tool_name = str(step.get("tool_name", ""))
            if tool_name not in self.model_tool_allowlist:
                continue
            result = self._execute_tool_plan_step(tool_name, step.get("arguments", {}) or {}, payment, tools, fee_rule)
            self._store_note(notes, tool_name, result)
        return notes

    def _fallback_tool_plan(self, label: str) -> List[Dict[str, Any]]:
        by_label: Dict[str, List[str]] = {
            "duplicate_or_replayed_payment": ["find_merchant", "check_duplicate", "find_related_transactions"],
            "missing_or_delayed_settlement": ["find_merchant", "find_settlement", "get_graph_neighborhood"],
            "fee_discrepancy": ["find_merchant", "check_fee_applicability"],
            "refund_adjustment": ["find_merchant", "find_refunds", "get_graph_neighborhood"],
            "partial_or_incorrect_settlement": ["find_merchant", "find_settlement", "get_graph_neighborhood"],
            "settlement_timing_mismatch": ["find_merchant", "get_transaction_history", "check_temporal_relationship"],
            "unlinked_or_misaligned_order": ["find_order", "find_related_transactions"],
        }
        return [{"tool_name": name, "arguments": {}} for name in by_label.get(label, ["find_payment"])]

    def _execute_tool_plan_step(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        payment: Payment,
        tools: InvestigationTools,
        fee_rule: Optional[FeeRule],
    ) -> Any:
        if tool_name == "find_payment":
            return tools.find_payment(payment.payment_id)
        if tool_name == "find_order":
            return tools.find_order(payment.order_id)
        if tool_name == "find_settlement":
            return tools.find_settlement(payment.payment_id)
        if tool_name == "find_refunds":
            return tools.find_refunds(payment.payment_id)
        if tool_name == "find_fee_rules":
            return tools.find_fee_rules(payment.merchant_id, payment)
        if tool_name == "find_merchant":
            return tools.find_merchant(payment.merchant_id)
        if tool_name == "find_related_transactions":
            window = max(1, min(60, int(arguments.get("window_minutes", 10))))
            return tools.find_related_transactions(payment, window_minutes=window)
        if tool_name == "get_transaction_history":
            return tools.get_transaction_history(payment.payment_id)
        if tool_name == "get_graph_neighborhood":
            return tools.get_graph_neighborhood(payment.payment_id)
        if tool_name == "compare_amounts":
            actual = Decimal(str(arguments.get("actual", payment.amount)))
            expected = Decimal(str(arguments.get("expected", payment.amount)))
            tolerance = Decimal(str(arguments.get("tolerance", "1.00")))
            return tools.compare_amounts(actual, expected, tolerance)
        if tool_name == "check_temporal_relationship":
            settlements = tools.index.settlements_by_payment.get(payment.payment_id, [])
            merchant = tools.index.merchants_by_id.get(payment.merchant_id)
            cycle_days = int(arguments.get("cycle_days", getattr(merchant, "settlement_cycle_days", 2)))
            tolerance_days = max(0, min(7, int(arguments.get("tolerance_days", 1))))
            return tools.check_temporal_relationship(payment, settlements, cycle_days, tolerance_days=tolerance_days)
        if tool_name == "check_fee_applicability":
            return tools.check_fee_applicability(fee_rule, payment)
        if tool_name == "check_duplicate":
            return tools.check_duplicate(payment)
        if tool_name == "get_evidence":
            entity_type = str(arguments.get("entity_type", "payment"))
            entity_id = str(arguments.get("entity_id", payment.payment_id))
            return tools.get_evidence(entity_type, entity_id)
        raise ValueError(f"tool is not available to the model: {tool_name}")

    def _store_note(self, notes: Dict[str, Any], tool_name: str, result: Any) -> None:
        if tool_name == "check_duplicate":
            key = "duplicate"
        elif tool_name == "find_refunds":
            key = "refunds"
        elif tool_name == "find_settlement":
            key = "settlements"
        elif tool_name == "check_fee_applicability":
            key = "fee_applicability"
        elif tool_name == "get_transaction_history":
            key = "history"
        elif tool_name == "get_graph_neighborhood":
            key = "graph_neighborhood"
        else:
            key = tool_name
        if key in notes:
            existing = notes[key]
            notes[key] = [*existing, result] if isinstance(existing, list) else [existing, result]
        else:
            notes[key] = result

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

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from .llm import LLMInvalidResponse, LLMProvider, LLMProviderConfig, MockProvider, OfflineProvider, OpenAIProvider as OpenAILLMProvider


HypothesisLabel = Literal[
    "fee_discrepancy",
    "refund_adjustment",
    "partial_or_incorrect_settlement",
    "missing_or_delayed_settlement",
    "duplicate_or_replayed_payment",
    "settlement_timing_mismatch",
    "unlinked_or_misaligned_order",
    "matched_low_risk",
]

AllowedToolName = Literal[
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
]


class ToolPlanStep(BaseModel):
    hypothesis_label: HypothesisLabel
    tool_name: AllowedToolName
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class InvestigationPlan(BaseModel):
    candidate_labels: List[HypothesisLabel]
    tool_plan: List[ToolPlanStep] = Field(default_factory=list)
    self_challenge: List[str] = Field(default_factory=list)
    verification_requirements: List[str] = Field(default_factory=list)
    confidence_factors: Dict[str, float] = Field(default_factory=dict)

    @field_validator("candidate_labels")
    @classmethod
    def require_candidates(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("candidate_labels must not be empty")
        return list(dict.fromkeys(value))


@dataclass(frozen=True)
class ProviderUsage:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: str = "0.00"
    latency_ms: float = 0.0
    attempts: int = 0


class StructuredInvestigationProvider:
    provider_name = "offline_structured"
    model_name = "auditra-hypothesis-agent-v1"
    prompt_version = "investigation-plan-v2"

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class OfflineStructuredProvider(StructuredInvestigationProvider):
    """Deterministic local provider used when no external LLM is configured."""

    provider_name = "offline"
    model_name = "offline-investigation-planner-v2"

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        labels = self._candidate_labels(context)
        plan = InvestigationPlan(
            candidate_labels=labels,
            tool_plan=self._tool_plan(labels),
            self_challenge=[
                "Could a refund, fee rule, duplicate, timing issue, or missing link explain the same evidence?",
                "Does every arithmetic claim have deterministic verification?",
                "Is any key relationship missing from the graph neighborhood?",
            ],
            verification_requirements=[
                "Run deterministic amount, fee, refund, duplicate, temporal, currency and relationship checks.",
                "Escalate if critical invariant conflicts with the selected hypothesis.",
            ],
            confidence_factors={"provider_confidence": 0.72},
        )
        return {**plan.model_dump(mode="json"), "usage": ProviderUsage()}

    def _candidate_labels(self, context: Dict[str, Any]) -> List[HypothesisLabel]:
        candidates: List[HypothesisLabel] = []
        status = context.get("status")
        reason_codes = set(context.get("reason_codes", []))
        failed_invariants = set(context.get("failed_invariants", []))

        if status in {"DUPLICATE"} or "DUPLICATE_PAYMENT" in reason_codes or "DUPLICATE_CONSISTENCY" in failed_invariants:
            candidates.append("duplicate_or_replayed_payment")
        if status in {"MISSING_SETTLEMENT"} or "RELATIONSHIP_COMPLETENESS" in failed_invariants:
            candidates.append("missing_or_delayed_settlement")
        if status in {"AMOUNT_MISMATCH", "PARTIAL_MATCH", "HUMAN_REVIEW"} or "SETTLEMENT_NET_AMOUNT" in failed_invariants:
            candidates.extend(["fee_discrepancy", "refund_adjustment", "partial_or_incorrect_settlement"])
        if status in {"TIMING_MISMATCH"} or "SETTLEMENT_TIMING" in reason_codes:
            candidates.append("settlement_timing_mismatch")
        if "MISSING_ORDER" in reason_codes:
            candidates.append("unlinked_or_misaligned_order")
        if not candidates:
            candidates.append("matched_low_risk")
        return list(dict.fromkeys(candidates))

    def _tool_plan(self, labels: List[HypothesisLabel]) -> List[ToolPlanStep]:
        steps: List[ToolPlanStep] = []
        for label in labels:
            steps.append(ToolPlanStep(hypothesis_label=label, tool_name="find_merchant", reason="Confirm merchant context"))
            if label == "duplicate_or_replayed_payment":
                steps.extend(
                    [
                        ToolPlanStep(hypothesis_label=label, tool_name="check_duplicate", reason="Check canonical duplicate relationship"),
                        ToolPlanStep(hypothesis_label=label, tool_name="find_related_transactions", reason="Inspect nearby same-order/payment patterns"),
                    ]
                )
            elif label == "missing_or_delayed_settlement":
                steps.extend(
                    [
                        ToolPlanStep(hypothesis_label=label, tool_name="find_settlement", reason="Verify settlement absence"),
                        ToolPlanStep(hypothesis_label=label, tool_name="get_graph_neighborhood", reason="Inspect relationship completeness"),
                    ]
                )
            elif label == "fee_discrepancy":
                steps.append(ToolPlanStep(hypothesis_label=label, tool_name="check_fee_applicability", reason="Verify configured fee applicability"))
            elif label == "refund_adjustment":
                steps.extend(
                    [
                        ToolPlanStep(hypothesis_label=label, tool_name="find_refunds", reason="Inspect refund evidence"),
                        ToolPlanStep(hypothesis_label=label, tool_name="get_graph_neighborhood", reason="Review linked evidence"),
                    ]
                )
            elif label == "partial_or_incorrect_settlement":
                steps.extend(
                    [
                        ToolPlanStep(hypothesis_label=label, tool_name="find_settlement", reason="Inspect settlement records"),
                        ToolPlanStep(hypothesis_label=label, tool_name="get_graph_neighborhood", reason="Review graph evidence"),
                    ]
                )
            elif label == "settlement_timing_mismatch":
                steps.extend(
                    [
                        ToolPlanStep(hypothesis_label=label, tool_name="get_transaction_history", reason="Inspect event sequence"),
                        ToolPlanStep(hypothesis_label=label, tool_name="get_graph_neighborhood", reason="Review linked timing evidence"),
                    ]
                )
            elif label == "unlinked_or_misaligned_order":
                steps.extend(
                    [
                        ToolPlanStep(hypothesis_label=label, tool_name="find_order", reason="Verify order link"),
                        ToolPlanStep(hypothesis_label=label, tool_name="find_related_transactions", reason="Look for matching transaction references"),
                    ]
                )
        return steps


class OpenAIInvestigationProvider(StructuredInvestigationProvider):
    provider_name = "openai"
    prompt_version = "investigation-plan-v2"

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        self.llm_provider = llm_provider or OpenAILLMProvider(config=config or LLMProviderConfig.from_env("AUDITRA_INVESTIGATION_LLM"))
        self.model_name = self.llm_provider.config.model

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        for attempt in range(1, 3):
            response = self.llm_provider.generate_structured(
                schema_name="AuditraInvestigationPlan",
                schema=InvestigationPlan.model_json_schema(),
                system_prompt=(
                    "You are Auditra's bounded investigation planner. Return structured JSON only. "
                    "Choose plausible hypotheses and typed tools. Do not perform authoritative arithmetic, "
                    "modify financial records, access evaluator internals, or expose chain-of-thought."
                ),
                user_payload=context,
            )
            try:
                plan = InvestigationPlan.model_validate(response.output)
                return {
                    **plan.model_dump(mode="json"),
                    "usage": ProviderUsage(
                        llm_calls=response.llm_calls,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        estimated_cost_usd=str(response.estimated_cost_usd),
                        latency_ms=response.latency_ms,
                        attempts=max(response.attempts, attempt),
                    ),
                    "response_id": response.response_id,
                }
            except ValidationError as exc:
                last_error = exc
        raise LLMInvalidResponse(f"invalid investigation plan: {last_error}")


class OpenAIProvider(OpenAIInvestigationProvider):
    """Backwards-compatible investigation provider name."""


class MockStructuredInvestigationProvider(StructuredInvestigationProvider):
    provider_name = "mock"
    model_name = "mock-investigation-planner"
    prompt_version = "investigation-plan-v2"

    def __init__(self, plan: Optional[InvestigationPlan] = None, error: Optional[Exception] = None):
        self.plan = plan
        self.error = error

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self.error:
            raise self.error
        plan = self.plan or InvestigationPlan(
            candidate_labels=["refund_adjustment"],
            tool_plan=[ToolPlanStep(hypothesis_label="refund_adjustment", tool_name="find_refunds")],
            self_challenge=["Could duplicate or fee evidence contradict this?"],
            verification_requirements=["Deterministic verification must pass."],
        )
        return {**plan.model_dump(mode="json"), "usage": ProviderUsage(llm_calls=1, input_tokens=100, output_tokens=40, estimated_cost_usd="0.01")}


__all__ = [
    "AllowedToolName",
    "HypothesisLabel",
    "InvestigationPlan",
    "LLMProvider",
    "LLMProviderConfig",
    "MockProvider",
    "MockStructuredInvestigationProvider",
    "OfflineProvider",
    "OfflineStructuredProvider",
    "OpenAIInvestigationProvider",
    "OpenAIProvider",
    "ProviderUsage",
    "StructuredInvestigationProvider",
    "ToolPlanStep",
]

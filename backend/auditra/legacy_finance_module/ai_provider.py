from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from .llm import (
    OFFLINE_AI,
    REAL_GEMINI_AI,
    REAL_HUGGINGFACE_AI,
    REAL_OPENROUTER_AI,
    REAL_GROQ_AI,
    REAL_OPENAI_AI,
    GeminiProvider as GeminiLLMProvider,
    GroqProvider as GroqLLMProvider,
    HuggingFaceProvider as HuggingFaceLLMProvider,
    OpenRouterProvider as OpenRouterLLMProvider,
    LLMInvalidResponse,
    LLMProvider,
    LLMProviderConfig,
    LLMUnavailable,
    MockProvider,
    OfflineProvider,
    OpenAIProvider as OpenAILLMProvider,
    resolve_llm_provider,
)


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
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[str] = None
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
        return {
            **plan.model_dump(mode="json"),
            "provider": self.provider_name,
            "model": self.model_name,
            "execution_mode": OFFLINE_AI,
            "prompt_version": self.prompt_version,
            "usage": ProviderUsage(estimated_cost_usd="0.00"),
            "provider_trace": [
                {
                    "execution_mode": OFFLINE_AI,
                    "provider": self.provider_name,
                    "model": self.model_name,
                    "prompt_version": self.prompt_version,
                    "timestamp": None,
                    "latency_ms": 0.0,
                    "attempts": 0,
                    "llm_calls": 0,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "cost_usd": "0.00",
                    "success": True,
                    "failure_type": None,
                }
            ],
        }

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


class LLMInvestigationProvider(StructuredInvestigationProvider):
    execution_mode = REAL_OPENAI_AI
    prompt_version = "investigation-plan-v2"

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.provider_name = llm_provider.provider_name
        self.model_name = self.llm_provider.config.model

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        calls = 0
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        token_usage_known = True
        cost_total = 0.0
        cost_known = True
        latency_ms = 0.0
        provider_attempts = 0
        last_response = None
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
            last_response = response
            calls += response.llm_calls
            latency_ms += response.latency_ms
            provider_attempts += response.attempts
            if response.input_tokens is None or response.output_tokens is None:
                token_usage_known = False
            else:
                input_tokens += response.input_tokens
                output_tokens += response.output_tokens
                total_tokens += response.total_tokens or response.input_tokens + response.output_tokens
            if response.estimated_cost_usd is None:
                cost_known = False
            else:
                cost_total += float(response.estimated_cost_usd)
            try:
                plan = InvestigationPlan.model_validate(response.output)
                cost = f"{cost_total:.6f}" if cost_known else None
                return {
                    **plan.model_dump(mode="json"),
                    "provider": response.provider,
                    "model": response.model,
                    "execution_mode": self.execution_mode,
                    "prompt_version": self.prompt_version,
                    "usage": ProviderUsage(
                        llm_calls=response.llm_calls,
                        input_tokens=input_tokens if token_usage_known else None,
                        output_tokens=output_tokens if token_usage_known else None,
                        total_tokens=total_tokens if token_usage_known else None,
                        estimated_cost_usd=cost,
                        latency_ms=round(latency_ms, 4),
                        attempts=max(provider_attempts, attempt),
                    ),
                    "response_id": response.response_id,
                    "provider_trace": [
                        {
                            "execution_mode": self.execution_mode,
                            "provider": response.provider,
                            "model": response.model,
                            "prompt_version": self.prompt_version,
                            "timestamp": response.timestamp,
                            "latency_ms": round(latency_ms, 4),
                            "attempts": max(provider_attempts, attempt),
                            "llm_calls": response.llm_calls,
                            "input_tokens": input_tokens if token_usage_known else None,
                            "output_tokens": output_tokens if token_usage_known else None,
                            "total_tokens": total_tokens if token_usage_known else None,
                            "cost_usd": cost,
                            "success": True,
                            "failure_type": None,
                            "response_id": response.response_id,
                        }
                    ],
                }
            except ValidationError as exc:
                last_error = exc
        raise LLMInvalidResponse(f"invalid investigation plan: {last_error}")


class OpenAIInvestigationProvider(LLMInvestigationProvider):
    execution_mode = REAL_OPENAI_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or OpenAILLMProvider(config=config or LLMProviderConfig.from_env("AUDITRA_INVESTIGATION_LLM"))
        )


class GroqInvestigationProvider(LLMInvestigationProvider):
    execution_mode = REAL_GROQ_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or GroqLLMProvider(config=config or LLMProviderConfig.from_groq_env("AUDITRA_INVESTIGATION_LLM"))
        )


class GeminiInvestigationProvider(LLMInvestigationProvider):
    execution_mode = REAL_GEMINI_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or GeminiLLMProvider(config=config or LLMProviderConfig.from_gemini_env("AUDITRA_INVESTIGATION_LLM"))
        )


class OpenRouterInvestigationProvider(LLMInvestigationProvider):
    execution_mode = REAL_OPENROUTER_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or OpenRouterLLMProvider(config=config or LLMProviderConfig.from_openrouter_env("AUDITRA_INVESTIGATION_LLM"))
        )


class HuggingFaceInvestigationProvider(LLMInvestigationProvider):
    execution_mode = REAL_HUGGINGFACE_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or HuggingFaceLLMProvider(config=config or LLMProviderConfig.from_huggingface_env("AUDITRA_INVESTIGATION_LLM"))
        )


class UnsupportedConfiguredInvestigationProvider(StructuredInvestigationProvider):
    """Represents an explicitly requested provider that is not integrated yet."""

    prompt_version = "investigation-plan-v2"

    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise LLMUnavailable(
            f"{self.provider_name} provider is architecturally supported but not integrated",
            failure_type="provider_not_integrated",
            attempts=0,
        )

class TransparentFallbackInvestigationProvider(StructuredInvestigationProvider):
    """Uses offline planning after an external failure and labels the fallback."""

    def __init__(
        self,
        primary: StructuredInvestigationProvider,
        fallback: Optional[StructuredInvestigationProvider] = None,
    ):
        self.primary = primary
        self.fallback = fallback or OfflineStructuredProvider()
        self.provider_name = primary.provider_name
        self.model_name = primary.model_name
        self.prompt_version = primary.prompt_version
        self._circuit_open = False
        self._circuit_failure_type: Optional[str] = None
        self._circuit_failure_trace: Optional[Dict[str, Any]] = None
        self._primary_calls = 0
        self._primary_call_limit = max(0, int(os.getenv("AUDITRA_EXTERNAL_LLM_CASE_LIMIT", "12")))

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._primary_call_limit and self._primary_calls >= self._primary_call_limit:
            proposal = self.fallback.propose(context)
            proposal["fallback_reason"] = "provider_budget_exhausted"
            proposal["usage"] = ProviderUsage(estimated_cost_usd="0.00")
            proposal["provider_trace"] = [
                {
                    "execution_mode": getattr(self.primary, "execution_mode", "AI_UNAVAILABLE"),
                    "provider": self.primary.provider_name,
                    "model": self.primary.model_name,
                    "prompt_version": self.primary.prompt_version,
                    "timestamp": None,
                    "latency_ms": 0.0,
                    "attempts": 0,
                    "llm_calls": 0,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "cost_usd": None,
                    "success": False,
                    "failure_type": "provider_budget_exhausted",
                },
                *proposal.get("provider_trace", []),
            ]
            return proposal
        if self._circuit_open:
            proposal = self.fallback.propose(context)
            failure_type = self._circuit_failure_type or "provider_circuit_open"
            proposal["fallback_reason"] = f"provider_circuit_open:{failure_type}"
            proposal["usage"] = ProviderUsage(estimated_cost_usd="0.00")
            if self._circuit_failure_trace:
                proposal["provider_trace"] = [{**self._circuit_failure_trace, "failure_type": proposal["fallback_reason"]}, *proposal.get("provider_trace", [])]
            return proposal
        try:
            self._primary_calls += 1
            return self.primary.propose(context)
        except Exception as exc:
            proposal = self.fallback.propose(context)
            failure_type = getattr(exc, "failure_type", "invalid_structured_output")
            self._circuit_open = True
            self._circuit_failure_type = failure_type
            proposal["fallback_reason"] = failure_type
            proposal["usage"] = ProviderUsage(
                llm_calls=0,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
                estimated_cost_usd="0.00",
                latency_ms=float(getattr(exc, "latency_ms", 0.0)),
                attempts=int(getattr(exc, "attempts", 0)),
            )
            failure_trace = {
                    "execution_mode": getattr(self.primary, "execution_mode", "AI_UNAVAILABLE"),
                    "provider": self.primary.provider_name,
                    "model": self.primary.model_name,
                    "prompt_version": self.primary.prompt_version,
                    "timestamp": getattr(exc, "timestamp", None),
                    "latency_ms": getattr(exc, "latency_ms", 0.0),
                    "attempts": getattr(exc, "attempts", 0),
                    "llm_calls": 0,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "cost_usd": None,
                    "success": False,
                    "failure_type": failure_type,
            }
            self._circuit_failure_trace = failure_trace
            proposal["provider_trace"] = [failure_trace, *proposal.get("provider_trace", [])]
            return proposal


def _bounded_investigation_config(config: LLMProviderConfig) -> LLMProviderConfig:
    timeout_cap = float(os.getenv("AUDITRA_EXTERNAL_LLM_TIMEOUT_CAP", "8"))
    retry_cap = int(os.getenv("AUDITRA_EXTERNAL_LLM_MAX_RETRIES_CAP", "0"))
    return replace(
        config,
        timeout_seconds=min(config.timeout_seconds, timeout_cap),
        max_retries=min(config.max_retries, retry_cap),
    )

def runtime_investigation_provider() -> StructuredInvestigationProvider:
    provider = resolve_llm_provider("INVESTIGATION")
    if provider == "groq":
        return TransparentFallbackInvestigationProvider(GroqInvestigationProvider(config=_bounded_investigation_config(LLMProviderConfig.from_groq_env("AUDITRA_INVESTIGATION_LLM"))))
    if provider == "gemini":
        return TransparentFallbackInvestigationProvider(GeminiInvestigationProvider(config=_bounded_investigation_config(LLMProviderConfig.from_gemini_env("AUDITRA_INVESTIGATION_LLM"))))
    if provider == "openrouter":
        return TransparentFallbackInvestigationProvider(OpenRouterInvestigationProvider(config=_bounded_investigation_config(LLMProviderConfig.from_openrouter_env("AUDITRA_INVESTIGATION_LLM"))))
    if provider == "huggingface":
        return TransparentFallbackInvestigationProvider(HuggingFaceInvestigationProvider(config=_bounded_investigation_config(LLMProviderConfig.from_huggingface_env("AUDITRA_INVESTIGATION_LLM"))))
    if provider == "openai":
        return TransparentFallbackInvestigationProvider(OpenAIInvestigationProvider(config=_bounded_investigation_config(LLMProviderConfig.from_env("AUDITRA_INVESTIGATION_LLM"))))
    if provider == "anthropic":
        config = LLMProviderConfig.from_anthropic_env("AUDITRA_INVESTIGATION_LLM")
        return TransparentFallbackInvestigationProvider(UnsupportedConfiguredInvestigationProvider("anthropic", config.model))
    if provider == "ollama":
        config = LLMProviderConfig.from_ollama_env("AUDITRA_INVESTIGATION_LLM")
        return TransparentFallbackInvestigationProvider(UnsupportedConfiguredInvestigationProvider("ollama", config.model))
    return OfflineStructuredProvider()


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
        return {
            **plan.model_dump(mode="json"),
            "provider": self.provider_name,
            "model": self.model_name,
            "execution_mode": "MOCK_AI",
            "prompt_version": self.prompt_version,
            "usage": ProviderUsage(
                llm_calls=1,
                input_tokens=100,
                output_tokens=40,
                total_tokens=140,
                estimated_cost_usd="0.01",
                attempts=1,
            ),
            "provider_trace": [
                {
                    "execution_mode": "MOCK_AI",
                    "provider": self.provider_name,
                    "model": self.model_name,
                    "prompt_version": self.prompt_version,
                    "timestamp": None,
                    "latency_ms": 0.0,
                    "attempts": 1,
                    "llm_calls": 1,
                    "input_tokens": 100,
                    "output_tokens": 40,
                    "total_tokens": 140,
                    "cost_usd": "0.01",
                    "success": True,
                    "failure_type": None,
                }
            ],
        }


__all__ = [
    "AllowedToolName",
    "HypothesisLabel",
    "InvestigationPlan",
    "GeminiInvestigationProvider",
    "GroqInvestigationProvider",
    "HuggingFaceInvestigationProvider",
    "OpenRouterInvestigationProvider",
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
    "TransparentFallbackInvestigationProvider",
    "ToolPlanStep",
    "UnsupportedConfiguredInvestigationProvider",
    "runtime_investigation_provider",
]

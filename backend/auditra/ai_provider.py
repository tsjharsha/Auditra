from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ProviderUsage:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: str = "0.00"


class StructuredInvestigationProvider:
    provider_name = "offline_structured"
    model_name = "auditra-hypothesis-agent-v1"

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class OfflineStructuredProvider(StructuredInvestigationProvider):
    """Deterministic local provider used when no external LLM is configured."""

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        candidates: List[str] = []
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

        return {
            "candidate_labels": list(dict.fromkeys(candidates)),
            "self_challenge": [
                "Could a refund, fee rule, or duplicate explain the same evidence?",
                "Does every arithmetic claim have deterministic verification?",
                "Is any key relationship missing from the graph neighborhood?",
            ],
            "usage": ProviderUsage(),
        }


class OpenAIProvider(StructuredInvestigationProvider):
    """Placeholder adapter boundary for a real LLM provider.

    The local project stays offline by default. This class makes the integration
    point explicit without importing network SDKs or performing hidden calls.
    """

    provider_name = "openai"
    model_name = os.getenv("AUDITRA_OPENAI_MODEL", "gpt-5-mini")

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured")
        raise RuntimeError("OpenAIProvider is intentionally not enabled in the local offline demo")

from __future__ import annotations

import os
import json
import urllib.request
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
    """Opt-in structured LLM provider for investigation planning."""

    provider_name = "openai"
    model_name = os.getenv("AUDITRA_OPENAI_MODEL", "gpt-5-mini")

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        body = {
            "model": self.model_name,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are Auditra's bounded investigation planner. "
                        "Return only JSON. Select candidate hypothesis labels and self-challenge checks. "
                        "Do not perform authoritative arithmetic or alter financial records."
                    ),
                },
                {"role": "user", "content": json.dumps(context)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "AuditraInvestigationPlan",
                    "strict": False,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "candidate_labels": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "fee_discrepancy",
                                        "refund_adjustment",
                                        "partial_or_incorrect_settlement",
                                        "missing_or_delayed_settlement",
                                        "duplicate_or_replayed_payment",
                                        "settlement_timing_mismatch",
                                        "unlinked_or_misaligned_order",
                                        "matched_low_risk",
                                    ],
                                },
                            },
                            "self_challenge": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["candidate_labels", "self_challenge"],
                    },
                }
            },
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        parsed = self._extract_json(payload)
        usage = payload.get("usage", {})
        parsed["usage"] = ProviderUsage(
            llm_calls=1,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            estimated_cost_usd="0.00",
        )
        return parsed

    def _extract_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "output_text" in payload:
            return json.loads(payload["output_text"])
        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return json.loads(text)
        raise RuntimeError("OpenAI response did not contain JSON text")

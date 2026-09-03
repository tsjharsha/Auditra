from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

import httpx
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auditra.ai_provider import ProviderUsage, StructuredInvestigationProvider
from auditra.llm import LLMProviderConfig, LLMUnavailable, REAL_GEMINI_AI, REAL_GROQ_AI

spec = importlib.util.spec_from_file_location("real_llm_validation", ROOT / "scripts" / "real_llm_validation.py")
assert spec and spec.loader
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class FakeExternalProvider(StructuredInvestigationProvider):
    prompt_version = "investigation-plan-v2"

    def __init__(self, provider_name: str, model_name: str, execution_mode: str, failure_type: str | None = None):
        self.provider_name = provider_name
        self.model_name = model_name
        self.execution_mode = execution_mode
        self.failure_type = failure_type
        self.calls = 0

    def propose(self, context):
        self.calls += 1
        if self.failure_type:
            raise LLMUnavailable(
                f"{self.provider_name} failed",
                failure_type=self.failure_type,
                attempts=1,
                latency_ms=12.5,
            )
        return {
            "candidate_labels": ["refund_adjustment"],
            "tool_plan": [],
            "self_challenge": ["Check deterministic controls."],
            "verification_requirements": ["Verification must pass."],
            "confidence_factors": {"provider_confidence": 0.8},
            "provider": self.provider_name,
            "model": self.model_name,
            "execution_mode": self.execution_mode,
            "prompt_version": self.prompt_version,
            "usage": ProviderUsage(llm_calls=1, input_tokens=10, output_tokens=4, total_tokens=14, attempts=1),
            "provider_trace": [{
                "execution_mode": self.execution_mode,
                "provider": self.provider_name,
                "model": self.model_name,
                "prompt_version": self.prompt_version,
                "timestamp": None,
                "latency_ms": 3.0,
                "attempts": 1,
                "llm_calls": 1,
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
                "cost_usd": None,
                "success": True,
                "failure_type": None,
            }],
        }


class RealProviderValidationTests(unittest.TestCase):
    def test_gemini_schema_flattens_local_references(self) -> None:
        schema = {
            "$defs": {"Step": {"type": "object", "additionalProperties": True, "title": "Step"}},
            "properties": {"plan": {"items": {"$ref": "#/$defs/Step"}, "title": "Plan", "type": "array"}},
            "title": "Plan",
            "type": "object",
        }

        flattened = validation._gemini_response_schema(schema)

        self.assertEqual(flattened, {"properties": {"plan": {"items": {"type": "object"}, "type": "array"}}, "type": "object"})
    def test_validation_gemini_retries_with_generic_json_schema(self) -> None:
        request_schemas = []

        def handler(request: httpx.Request) -> httpx.Response:
            request_schemas.append(json.loads(request.content)["generationConfig"]["responseSchema"])
            if len(request_schemas) == 1:
                return httpx.Response(400, json={"error": {"message": "unsupported schema"}})
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{\"ok\": true}"}]}}]})

        provider = validation.ValidationGeminiProvider(
            config=LLMProviderConfig(provider="gemini", model="gemini-test"),
            transport=httpx.MockTransport(handler),
        )
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            response = provider.generate_structured("Plan", {"$defs": {"Step": {"type": "object"}}, "$ref": "#/$defs/Step"}, "Return JSON.", {})

        self.assertEqual(response.output, {"ok": True})
        self.assertEqual(request_schemas[-1], {"type": "object"})
    def test_failover_uses_second_real_provider_and_records_first_failure(self) -> None:
        groq = FakeExternalProvider("groq", "groq-test", REAL_GROQ_AI, failure_type="rate_limit")
        gemini = FakeExternalProvider("gemini", "gemini-test", REAL_GEMINI_AI)
        provider = validation.RealProviderFailoverInvestigator([groq, gemini])

        proposal = provider.propose({"payment_id": "PAY_1"})

        self.assertEqual(groq.calls, 1)
        self.assertEqual(gemini.calls, 1)
        self.assertEqual(proposal["provider"], "gemini")
        self.assertEqual(proposal["model"], "gemini-test")
        self.assertEqual(len(proposal["provider_trace"]), 2)
        self.assertEqual(proposal["provider_trace"][0]["failure_type"], "rate_limit")
        self.assertTrue(proposal["provider_trace"][1]["success"])
        self.assertNotIn("offline", str(proposal["provider_trace"]).lower())

    def test_all_provider_failures_raise_without_offline_plan(self) -> None:
        provider = validation.RealProviderFailoverInvestigator([
            FakeExternalProvider("groq", "groq-test", REAL_GROQ_AI, failure_type="rate_limit"),
            FakeExternalProvider("gemini", "gemini-test", REAL_GEMINI_AI, failure_type="timeout"),
        ])

        with self.assertRaises(LLMUnavailable) as caught:
            provider.propose({"payment_id": "PAY_2"})

        self.assertEqual(caught.exception.failure_type, "rate_limit")
        attempts = provider.case_attempts["PAY_2"]
        self.assertEqual([attempt["provider"] for attempt in attempts], ["groq", "gemini"])
        self.assertTrue(all(attempt["success"] is False for attempt in attempts))
        self.assertTrue(all(attempt["execution_mode"] != "OFFLINE_AI" for attempt in attempts))


if __name__ == "__main__":
    unittest.main()
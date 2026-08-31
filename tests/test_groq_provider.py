from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.ai_provider import (
    GroqInvestigationProvider,
    OfflineStructuredProvider,
    TransparentFallbackInvestigationProvider,
)
from auditra.financial_world.understanding import GroqWorldSpecProvider
from auditra.llm import (
    GROQ_API_URL,
    OFFLINE_AI,
    REAL_GROQ_AI,
    GroqProvider,
    LLMProviderConfig,
    LLMUnavailable,
)
from auditra.runtime import runtime_ai_status


class GroqProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = LLMProviderConfig(
            provider="groq",
            model="openai/gpt-oss-20b",
            max_tokens=700,
            timeout_seconds=3,
            max_retries=1,
            input_cost_per_1m=LLMProviderConfig.from_groq_env().input_cost_per_1m,
            output_cost_per_1m=LLMProviderConfig.from_groq_env().output_cost_per_1m,
        )

    def test_native_groq_request_and_observability(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers["Authorization"]
            captured["body"] = json.loads(request.content)
            return groq_response({"candidate_labels": ["matched_low_risk"]}, prompt_tokens=120, completion_tokens=30)

        with patch.dict(os.environ, {"GROQ_API_KEY": "local-test-key"}, clear=False):
            provider = GroqProvider(config=self.config, transport=httpx.MockTransport(handler))
            response = provider.generate_structured(
                "AuditraPlan",
                {"type": "object", "properties": {"candidate_labels": {"type": "array"}}},
                "Return a typed plan.",
                {"payment_id": "PAY_1"},
            )

        self.assertEqual(captured["url"], GROQ_API_URL)
        self.assertEqual(captured["authorization"], "Bearer local-test-key")
        self.assertEqual(captured["body"]["model"], "openai/gpt-oss-20b")
        self.assertEqual(captured["body"]["max_completion_tokens"], 700)
        self.assertFalse(captured["body"]["response_format"]["json_schema"]["strict"])
        self.assertEqual(response.provider, "groq")
        self.assertEqual(response.model, "openai/gpt-oss-20b")
        self.assertEqual(response.total_tokens, 150)
        self.assertIsNotNone(response.estimated_cost_usd)
        self.assertTrue(response.timestamp)
        self.assertTrue(response.success)

    def test_missing_key_is_typed_and_never_makes_a_request(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GROQ_API_KEY", None)
            provider = GroqProvider(config=self.config, transport=httpx.MockTransport(lambda _: self.fail("called")))
            with self.assertRaises(LLMUnavailable) as caught:
                provider.generate_structured("Plan", {"type": "object"}, "Return JSON.", {})

        self.assertEqual(caught.exception.failure_type, "missing_api_key")
        self.assertEqual(caught.exception.attempts, 0)

    def test_rate_limit_retries_then_reports_failure(self) -> None:
        calls = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(429, json={"error": {"message": "rate limited"}})

        with patch.dict(os.environ, {"GROQ_API_KEY": "local-test-key"}, clear=False):
            provider = GroqProvider(config=self.config, transport=httpx.MockTransport(handler))
            with self.assertRaises(LLMUnavailable) as caught:
                provider.generate_structured("Plan", {"type": "object"}, "Return JSON.", {})

        self.assertEqual(calls, 2)
        self.assertEqual(caught.exception.failure_type, "rate_limit")
        self.assertEqual(caught.exception.attempts, 2)

    def test_malformed_output_retries_then_reports_failure(self) -> None:
        with patch.dict(os.environ, {"GROQ_API_KEY": "local-test-key"}, clear=False):
            provider = GroqProvider(
                config=self.config,
                transport=httpx.MockTransport(lambda _: groq_text_response("not-json")),
            )
            with self.assertRaises(LLMUnavailable) as caught:
                provider.generate_structured("Plan", {"type": "object"}, "Return JSON.", {})

        self.assertEqual(caught.exception.failure_type, "malformed_response")
        self.assertEqual(caught.exception.attempts, 2)


    def test_groq_retries_with_json_object_when_schema_envelope_is_rejected(self) -> None:
        bodies = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            if len(bodies) == 1:
                return httpx.Response(400, json={"error": {"message": "schema unsupported"}})
            return groq_response({"candidate_labels": ["matched_low_risk"]}, prompt_tokens=90, completion_tokens=20)

        with patch.dict(os.environ, {"GROQ_API_KEY": "local-test-key"}, clear=False):
            provider = GroqProvider(config=self.config, transport=httpx.MockTransport(handler))
            response = provider.generate_structured("Plan", {"type": "object"}, "Return JSON.", {})

        self.assertEqual(bodies[0]["response_format"]["type"], "json_schema")
        self.assertEqual(bodies[1]["response_format"]["type"], "json_object")
        self.assertIn("JSON Schema", bodies[1]["messages"][0]["content"])
        self.assertEqual(response.provider, "groq")
        self.assertEqual(response.llm_calls, 1)

    def test_groq_investigation_plan_is_typed_and_labeled(self) -> None:
        plan = {
            "candidate_labels": ["refund_adjustment"],
            "tool_plan": [
                {
                    "hypothesis_label": "refund_adjustment",
                    "tool_name": "find_refunds",
                    "arguments": {},
                    "reason": "Inspect refund evidence",
                }
            ],
            "self_challenge": ["Could fee evidence contradict this?"],
            "verification_requirements": ["Deterministic verification must pass."],
            "confidence_factors": {"provider_confidence": 0.8},
        }
        with patch.dict(os.environ, {"GROQ_API_KEY": "local-test-key"}, clear=False):
            low_level = GroqProvider(config=self.config, transport=httpx.MockTransport(lambda _: groq_response(plan)))
            proposal = GroqInvestigationProvider(llm_provider=low_level).propose({"payment_id": "PAY_1"})

        self.assertEqual(proposal["execution_mode"], REAL_GROQ_AI)
        self.assertEqual(proposal["provider"], "groq")
        self.assertEqual(proposal["candidate_labels"], ["refund_adjustment"])
        self.assertTrue(proposal["provider_trace"][0]["success"])

    def test_groq_world_spec_is_validated_before_generation(self) -> None:
        output = {
            "world_name": "Groq Commerce India",
            "merchant_name": "Groq Commerce India",
            "record_count": 80,
            "currencies": ["INR"],
            "payment_methods": ["UPI", "CARD"],
            "fee_rate": "0.0200",
            "settlement_delay_days": 2,
            "anomaly_rates": {"REFUND_MISMATCH": "0.0200"},
        }
        with patch.dict(os.environ, {"GROQ_API_KEY": "local-test-key"}, clear=False):
            low_level = GroqProvider(config=self.config, transport=httpx.MockTransport(lambda _: groq_response(output)))
            spec, steps = GroqWorldSpecProvider(llm_provider=low_level).parse("Build an INR world", seed=77)

        self.assertEqual(spec.seed, 77)
        self.assertEqual(spec.record_count, 80)
        self.assertEqual(spec.understanding_source, "groq:openai/gpt-oss-20b")
        self.assertEqual(steps[0].metadata["execution_mode"], REAL_GROQ_AI)


    def test_groq_world_spec_canonicalizes_common_anomaly_aliases(self) -> None:
        output = {
            "world_name": "Groq Commerce India",
            "merchant_name": "Groq Commerce India",
            "record_count": 80,
            "currencies": ["INR"],
            "payment_methods": ["UPI", "Card"],
            "fee_rate": 0.02,
            "settlement_delay_days": 2,
            "anomaly_rates": {"duplicate": 0.03, "timing_issue": 0.04, "refund_mismatch": 0.05},
        }
        with patch.dict(os.environ, {"GROQ_API_KEY": "local-test-key"}, clear=False):
            low_level = GroqProvider(config=self.config, transport=httpx.MockTransport(lambda _: groq_response(output)))
            spec, _ = GroqWorldSpecProvider(llm_provider=low_level).parse("Build an INR world", seed=77)

        self.assertEqual(spec.anomaly_rates["DUPLICATE_PAYMENT"], spec.anomaly_rates["DUPLICATE_PAYMENT"].quantize(spec.anomaly_rates["DUPLICATE_PAYMENT"]))
        self.assertIn("TIMING_MISMATCH", spec.anomaly_rates)
        self.assertIn("REFUND_MISMATCH", spec.anomaly_rates)
        self.assertNotIn("duplicate", spec.anomaly_rates)

    def test_external_failure_falls_back_with_an_honest_label(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GROQ_API_KEY", None)
            primary = GroqInvestigationProvider(llm_provider=GroqProvider(config=self.config))
            provider = TransparentFallbackInvestigationProvider(primary, OfflineStructuredProvider())
            proposal = provider.propose({"status": "AMOUNT_MISMATCH", "reason_codes": []})

        self.assertEqual(proposal["execution_mode"], OFFLINE_AI)
        self.assertEqual(proposal["provider"], "offline")
        self.assertEqual(proposal["fallback_reason"], "missing_api_key")
        self.assertFalse(proposal["provider_trace"][0]["success"])
        self.assertTrue(proposal["provider_trace"][1]["success"])

    def test_runtime_status_never_contains_the_key(self) -> None:
        with patch.dict(os.environ, {"GROQ_API_KEY": "never-emit-this", "AUDITRA_LLM_PROVIDER": "groq"}, clear=False):
            payload = runtime_ai_status()
        self.assertNotIn("never-emit-this", json.dumps(payload))
        self.assertEqual(payload["investigation"]["execution_mode"], REAL_GROQ_AI)


def groq_response(output: dict, prompt_tokens: int = 80, completion_tokens: int = 20) -> httpx.Response:
    return groq_text_response(json.dumps(output), prompt_tokens, completion_tokens)


def groq_text_response(content: str, prompt_tokens: int = 80, completion_tokens: int = 20) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-auditra-test",
            "model": "openai/gpt-oss-20b",
            "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        },
    )


if __name__ == "__main__":
    unittest.main()

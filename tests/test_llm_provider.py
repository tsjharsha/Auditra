from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.ai_provider import InvestigationPlan, OpenAIInvestigationProvider, ToolPlanStep
from auditra.financial_world.understanding import OpenAIWorldSpecProvider
from auditra.llm import LLMInvalidResponse, MockProvider


class LLMProviderTests(unittest.TestCase):
    def test_investigation_provider_retries_malformed_structured_output(self) -> None:
        valid_plan = InvestigationPlan(
            candidate_labels=["refund_adjustment"],
            tool_plan=[ToolPlanStep(hypothesis_label="refund_adjustment", tool_name="find_refunds")],
            self_challenge=["Could a duplicate contradict refund evidence?"],
            verification_requirements=["Deterministic amount verification must pass."],
        ).model_dump(mode="json")
        mock_llm = MockProvider(responses=[valid_plan], malformed_before_success=1)
        provider = OpenAIInvestigationProvider(llm_provider=mock_llm)

        proposal = provider.propose({"payment_id": "PAY_1", "status": "HUMAN_REVIEW"})

        self.assertEqual(proposal["candidate_labels"], ["refund_adjustment"])
        self.assertEqual(mock_llm.calls, 2)
        self.assertEqual(proposal["usage"].llm_calls, 1)
        self.assertEqual(proposal["usage"].attempts, 2)

    def test_investigation_provider_rejects_repeated_invalid_structured_output(self) -> None:
        provider = OpenAIInvestigationProvider(llm_provider=MockProvider(malformed_before_success=2))

        with self.assertRaises(LLMInvalidResponse):
            provider.propose({"payment_id": "PAY_1", "status": "HUMAN_REVIEW"})

    def test_world_provider_validates_mocked_financial_world_spec(self) -> None:
        mock_llm = MockProvider(
            responses=[
                {
                    "world_name": "Demo Commerce India",
                    "merchant_name": "Demo Commerce India",
                    "record_count": 75,
                    "currencies": ["INR"],
                    "payment_methods": ["UPI", "CARD"],
                    "fee_rate": "0.0200",
                    "settlement_delay_days": 2,
                    "anomaly_rates": {"REFUND_MISMATCH": "0.0300"},
                }
            ]
        )
        provider = OpenAIWorldSpecProvider(llm_provider=mock_llm)

        spec, steps = provider.parse("Make a 75 order UPI/card world", seed=99)

        self.assertEqual(spec.record_count, 75)
        self.assertEqual(spec.seed, 99)
        self.assertEqual(spec.understanding_source, "openai:mock-model")
        self.assertTrue(any(step.step == "Record AI usage" for step in steps))


if __name__ == "__main__":
    unittest.main()

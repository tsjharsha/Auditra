from __future__ import annotations

import json
import os
import re
import urllib.request
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from .models import AnomalyMode, FinancialWorldSpec, UnderstandingStep, rate


DEFAULT_ANOMALIES = {
    AnomalyMode.NORMAL: {
        "AMOUNT_MISMATCH": Decimal("0.0100"),
        "MISSING_SETTLEMENT": Decimal("0.0100"),
        "TIMING_MISMATCH": Decimal("0.0100"),
    },
    AnomalyMode.STRESSED: {
        "AMOUNT_MISMATCH": Decimal("0.0500"),
        "MISSING_SETTLEMENT": Decimal("0.0300"),
        "DUPLICATE_PAYMENT": Decimal("0.0200"),
        "FEE_MISMATCH": Decimal("0.0300"),
        "REFUND_MISMATCH": Decimal("0.0200"),
        "PARTIAL_SETTLEMENT": Decimal("0.0300"),
        "TIMING_MISMATCH": Decimal("0.0300"),
        "CONFLICTING_EVIDENCE": Decimal("0.0100"),
    },
    AnomalyMode.ADVERSARIAL: {
        "AMOUNT_MISMATCH": Decimal("0.1000"),
        "MISSING_SETTLEMENT": Decimal("0.0700"),
        "DUPLICATE_PAYMENT": Decimal("0.0500"),
        "FEE_MISMATCH": Decimal("0.0600"),
        "REFUND_MISMATCH": Decimal("0.0400"),
        "PARTIAL_SETTLEMENT": Decimal("0.0500"),
        "TIMING_MISMATCH": Decimal("0.0600"),
        "CURRENCY_MISMATCH": Decimal("0.0200"),
        "ENTITY_LINK_FAILURE": Decimal("0.0200"),
        "CONFLICTING_EVIDENCE": Decimal("0.0200"),
    },
    AnomalyMode.CHAOS: {
        "AMOUNT_MISMATCH": Decimal("0.1200"),
        "MISSING_SETTLEMENT": Decimal("0.0800"),
        "DUPLICATE_PAYMENT": Decimal("0.0600"),
        "FEE_MISMATCH": Decimal("0.0800"),
        "REFUND_MISMATCH": Decimal("0.0600"),
        "PARTIAL_SETTLEMENT": Decimal("0.0600"),
        "TIMING_MISMATCH": Decimal("0.0800"),
        "CURRENCY_MISMATCH": Decimal("0.0300"),
        "ENTITY_LINK_FAILURE": Decimal("0.0300"),
        "CONFLICTING_EVIDENCE": Decimal("0.0400"),
    },
}


class PromptUnderstandingError(ValueError):
    pass


class DeterministicPromptParser:
    def parse(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        text = prompt.strip()
        lowered = text.lower()
        mode = self._mode(lowered)
        record_count = self._record_count(lowered)
        fee_rate = self._fee_rate(lowered)
        settlement_days = self._settlement_days(lowered)
        payment_methods = self._payment_methods(lowered)
        currencies = self._currencies(lowered)
        merchant_name = self._merchant_name(lowered)
        refund_rate = Decimal("0.0800")
        if "refund" in lowered and "10%" in lowered:
            refund_rate = Decimal("0.1000")
        anomaly_rates = dict(DEFAULT_ANOMALIES[mode])
        anomaly_rates.update(self._explicit_anomaly_rates(lowered))

        spec = FinancialWorldSpec(
            prompt=text,
            world_name=merchant_name,
            merchant_name=merchant_name,
            record_count=record_count,
            seed=seed,
            currencies=currencies,
            payment_methods=payment_methods,
            fee_rate=fee_rate,
            fixed_fee=Decimal("0.00"),
            settlement_delay_days=settlement_days,
            refund_rate=refund_rate,
            partial_settlement_rate=anomaly_rates.get("PARTIAL_SETTLEMENT", Decimal("0.0300")),
            anomaly_mode=mode,
            anomaly_rates=anomaly_rates,
            understanding_source="deterministic_parser",
        )
        steps = [
            UnderstandingStep(step="Understand intent", detail="Parsed merchant, volume, payment rails, fees, settlement policy and anomaly intent."),
            UnderstandingStep(step="Extract financial entities", detail="MERCHANT, ORDER, PAYMENT, SETTLEMENT, REFUND and FEE_RULE selected."),
            UnderstandingStep(step="Build schema", detail="Canonical Auditra finance schema prepared for preview."),
            UnderstandingStep(step="Build relationship model", detail="Order-payment-settlement-refund-fee relationships derived."),
            UnderstandingStep(step="Configure rules", detail=f"{self._percent(spec.fee_rate)} fee, T+{spec.settlement_delay_days}, {self._mode_value(spec.anomaly_mode)} anomaly mode."),
        ]
        return spec, steps

    def _record_count(self, text: str) -> int:
        matches = re.findall(r"(\d{2,6})\s*(?:orders|records|transactions|payments)", text)
        if matches:
            return min(10000, max(10, int(matches[0])))
        return 500

    def _fee_rate(self, text: str) -> Decimal:
        match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:platform\s*)?(?:fee|fees|commission)", text)
        if not match:
            match = re.search(r"(?:fee|fees|commission).*?(\d+(?:\.\d+)?)\s*%", text)
        if not match:
            return Decimal("0.0200")
        return rate(Decimal(match.group(1)) / Decimal("100"))

    def _settlement_days(self, text: str) -> int:
        match = re.search(r"t\s*\+\s*(\d+)", text)
        if match:
            return min(30, int(match.group(1)))
        return 2

    def _payment_methods(self, text: str) -> List[str]:
        methods = []
        if "upi" in text:
            methods.append("UPI")
        if "card" in text or "cards" in text:
            methods.append("CARD")
        if "wallet" in text:
            methods.append("WALLET")
        if "netbanking" in text or "net banking" in text:
            methods.append("NETBANKING")
        return methods or ["UPI", "CARD"]

    def _currencies(self, text: str) -> List[str]:
        currencies = []
        if "inr" in text or "indian" in text or "india" in text:
            currencies.append("INR")
        if "usd" in text:
            currencies.append("USD")
        if "eur" in text:
            currencies.append("EUR")
        return currencies or ["INR"]

    def _mode(self, text: str) -> AnomalyMode:
        if "chaos" in text:
            return AnomalyMode.CHAOS
        if "adversarial" in text or "break" in text:
            return AnomalyMode.ADVERSARIAL
        if "stress" in text or "stressed" in text or "anomal" in text or "partial settlement" in text:
            return AnomalyMode.STRESSED
        return AnomalyMode.NORMAL

    def _merchant_name(self, text: str) -> str:
        if "marketplace" in text:
            return "Auditra Marketplace India"
        if "e-commerce" in text or "ecommerce" in text or "commerce" in text:
            return "Demo Commerce India"
        if "saas" in text:
            return "Nila SaaS Demo"
        return "Demo Commerce India"

    def _explicit_anomaly_rates(self, text: str) -> Dict[str, Decimal]:
        patterns = {
            "AMOUNT_MISMATCH": r"amount mismatch(?:es)?[:\s]+(\d+(?:\.\d+)?)\s*%",
            "MISSING_SETTLEMENT": r"missing settlement(?:s)?[:\s]+(\d+(?:\.\d+)?)\s*%",
            "DUPLICATE_PAYMENT": r"duplicate(?:s| payments)?[:\s]+(\d+(?:\.\d+)?)\s*%",
            "FEE_MISMATCH": r"fee anomal(?:y|ies|ies)[:\s]+(\d+(?:\.\d+)?)\s*%",
        }
        rates: Dict[str, Decimal] = {}
        for name, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                rates[name] = rate(Decimal(match.group(1)) / Decimal("100"))
        return rates

    def _percent(self, value: Decimal) -> str:
        return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"

    def _mode_value(self, value: AnomalyMode | str) -> str:
        return value.value if isinstance(value, AnomalyMode) else str(value)


class OpenAIWorldSpecProvider:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("AUDITRA_OPENAI_MODEL", "gpt-5-mini")

    def parse(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise PromptUnderstandingError("OPENAI_API_KEY is not configured")
        schema = FinancialWorldSpec.model_json_schema()
        body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": "Convert the user prompt into a valid Auditra FinancialWorldSpec JSON object. Do not generate records.",
                },
                {"role": "user", "content": prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "FinancialWorldSpec",
                    "schema": schema,
                    "strict": False,
                }
            },
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise PromptUnderstandingError(f"OpenAI world builder failed: {exc}") from exc
        parsed = self._extract_json(payload)
        parsed.setdefault("prompt", prompt)
        parsed.setdefault("seed", seed)
        parsed["understanding_source"] = f"openai:{self.model}"
        try:
            spec = FinancialWorldSpec.model_validate(parsed)
        except ValidationError as exc:
            raise PromptUnderstandingError(f"OpenAI returned invalid FinancialWorldSpec: {exc}") from exc
        steps = [
            UnderstandingStep(step="Understand intent", detail=f"LLM provider {self.model} produced a validated world specification."),
            UnderstandingStep(step="Validate structured output", detail="Pydantic schema validation passed before generation."),
        ]
        return spec, steps

    def _extract_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "output_text" in payload:
            return json.loads(payload["output_text"])
        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return json.loads(text)
        raise PromptUnderstandingError("OpenAI response did not contain JSON text")


class WorldUnderstandingService:
    def __init__(self):
        self.parser = DeterministicPromptParser()
        self.openai = OpenAIWorldSpecProvider()

    def understand(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        if os.getenv("AUDITRA_USE_OPENAI_WORLD_BUILDER") == "1":
            return self.openai.parse(prompt, seed=seed)
        return self.parser.parse(prompt, seed=seed)

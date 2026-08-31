from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError

from .models import money


DETERMINISTIC = "DETERMINISTIC"
OFFLINE_AI = "OFFLINE_AI"
REAL_GROQ_AI = "REAL_GROQ_AI"
REAL_GEMINI_AI = "REAL_GEMINI_AI"
REAL_OPENROUTER_AI = "REAL_OPENROUTER_AI"
REAL_HUGGINGFACE_AI = "REAL_HUGGINGFACE_AI"
REAL_OPENAI_AI = "REAL_OPENAI_AI"
REAL_ANTHROPIC_AI = "REAL_ANTHROPIC_AI"
REAL_OLLAMA_AI = "REAL_OLLAMA_AI"
AI_UNAVAILABLE = "AI_UNAVAILABLE"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
HUGGINGFACE_API_URL = "https://router.huggingface.co/v1/chat/completions"
GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_MODEL_COSTS: Dict[str, tuple[Optional[Decimal], Optional[Decimal]]] = {
    "openai/gpt-oss-20b": (Decimal("0.075"), Decimal("0.30")),
    "openai/gpt-oss-120b": (Decimal("0.15"), Decimal("0.60")),
}


class LLMUnavailable(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        failure_type: str = "provider_unavailable",
        attempts: int = 0,
        latency_ms: float = 0.0,
        timestamp: Optional[str] = None,
    ):
        super().__init__(message)
        self.failure_type = failure_type
        self.attempts = attempts
        self.latency_ms = latency_ms
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()


class LLMInvalidResponse(RuntimeError):
    pass


class LLMStructuredResponse(BaseModel):
    provider: str
    model: str
    output: Dict[str, Any]
    llm_calls: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[Decimal] = None
    latency_ms: float = 0.0
    attempts: int = 1
    response_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: bool = True
    failure_type: Optional[str] = None


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str = "offline"
    model: str = "gpt-5-mini"
    temperature: float = 0.0
    max_tokens: int = 1200
    timeout_seconds: float = 30.0
    max_retries: int = 1
    input_cost_per_1m: Optional[Decimal] = Decimal("0.00")
    output_cost_per_1m: Optional[Decimal] = Decimal("0.00")

    @classmethod
    def from_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        return cls(
            provider=os.getenv(f"{prefix}_PROVIDER", os.getenv("AI_PROVIDER", os.getenv("AUDITRA_LLM_PROVIDER", "offline"))),
            model=os.getenv(f"{prefix}_MODEL", os.getenv("AUDITRA_OPENAI_MODEL", "gpt-5-mini")),
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", "0")),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", "1200")),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", "30")),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", "1")),
            input_cost_per_1m=Decimal(os.getenv(f"{prefix}_INPUT_COST_PER_1M", "0.00")),
            output_cost_per_1m=Decimal(os.getenv(f"{prefix}_OUTPUT_COST_PER_1M", "0.00")),
        )

    @classmethod
    def from_groq_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        model = os.getenv(f"{prefix}_MODEL") or os.getenv("GROQ_MODEL") or "openai/gpt-oss-20b"
        default_input_cost, default_output_cost = GROQ_MODEL_COSTS.get(model, (None, None))
        input_cost = os.getenv(f"{prefix}_INPUT_COST_PER_1M") or os.getenv("GROQ_INPUT_COST_PER_1M")
        output_cost = os.getenv(f"{prefix}_OUTPUT_COST_PER_1M") or os.getenv("GROQ_OUTPUT_COST_PER_1M")
        return cls(
            provider="groq",
            model=model,
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", os.getenv("GROQ_TEMPERATURE", "0"))),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", os.getenv("GROQ_MAX_TOKENS", "1200"))),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", os.getenv("GROQ_TIMEOUT", "20"))),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", os.getenv("GROQ_MAX_RETRIES", "1"))),
            input_cost_per_1m=Decimal(input_cost) if input_cost else default_input_cost,
            output_cost_per_1m=Decimal(output_cost) if output_cost else default_output_cost,
        )

    @classmethod
    def from_gemini_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        return cls(
            provider="gemini",
            model=os.getenv(f"{prefix}_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash",
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", os.getenv("GEMINI_TEMPERATURE", "0"))),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", os.getenv("GEMINI_MAX_TOKENS", "1200"))),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "20"))),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", os.getenv("GEMINI_MAX_RETRIES", "1"))),
            input_cost_per_1m=None,
            output_cost_per_1m=None,
        )

    @classmethod
    def from_openrouter_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        return cls(
            provider="openrouter",
            model=os.getenv(f"{prefix}_MODEL") or os.getenv("OPENROUTER_MODEL") or "qwen/qwen-2.5-72b-instruct:free",
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", os.getenv("OPENROUTER_TEMPERATURE", "0"))),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", os.getenv("OPENROUTER_MAX_TOKENS", "1200"))),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", os.getenv("OPENROUTER_TIMEOUT", "20"))),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", os.getenv("OPENROUTER_MAX_RETRIES", "1"))),
            input_cost_per_1m=None,
            output_cost_per_1m=None,
        )

    @classmethod
    def from_huggingface_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        return cls(
            provider="huggingface",
            model=os.getenv(f"{prefix}_MODEL") or os.getenv("HF_MODEL") or "openai/gpt-oss-120b:fastest",
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", os.getenv("HF_TEMPERATURE", "0"))),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", os.getenv("HF_MAX_TOKENS", "1200"))),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", os.getenv("HF_TIMEOUT", "30"))),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", os.getenv("HF_MAX_RETRIES", "1"))),
            input_cost_per_1m=None,
            output_cost_per_1m=None,
        )

    @classmethod
    def from_anthropic_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        return cls(
            provider="anthropic",
            model=os.getenv(f"{prefix}_MODEL") or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-haiku-latest",
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", os.getenv("ANTHROPIC_TEMPERATURE", "0"))),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", os.getenv("ANTHROPIC_MAX_TOKENS", "1200"))),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", os.getenv("ANTHROPIC_TIMEOUT", "20"))),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", os.getenv("ANTHROPIC_MAX_RETRIES", "1"))),
            input_cost_per_1m=None,
            output_cost_per_1m=None,
        )

    @classmethod
    def from_ollama_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        return cls(
            provider="ollama",
            model=os.getenv(f"{prefix}_MODEL") or os.getenv("OLLAMA_MODEL") or "llama3.1",
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", os.getenv("OLLAMA_TEMPERATURE", "0"))),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", os.getenv("OLLAMA_MAX_TOKENS", "1200"))),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "20"))),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", os.getenv("OLLAMA_MAX_RETRIES", "1"))),
            input_cost_per_1m=None,
            output_cost_per_1m=None,
        )


def resolve_llm_provider(scope: str) -> str:
    normalized = scope.strip().upper()
    explicit = os.getenv(f"AUDITRA_{normalized}_LLM_PROVIDER") or os.getenv("AI_PROVIDER") or os.getenv("AUDITRA_LLM_PROVIDER")
    if explicit:
        return explicit.strip().lower()
    if normalized == "WORLD" and os.getenv("AUDITRA_USE_OPENAI_WORLD_BUILDER") == "1":
        return "openai"
    if normalized == "INVESTIGATION" and os.getenv("AUDITRA_USE_OPENAI_INVESTIGATOR") == "1":
        return "openai"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY"):
        return "huggingface"
    return "offline"


def llm_runtime_status(scope: str) -> Dict[str, Any]:
    provider = resolve_llm_provider(scope)
    prefix = f"AUDITRA_{scope.strip().upper()}_LLM"
    if provider == "deterministic":
        return {
            "provider": "deterministic",
            "model": "financial-control-engine",
            "execution_mode": DETERMINISTIC,
            "configured": True,
            "fallback_mode": None,
        }
    if provider == "groq":
        config = LLMProviderConfig.from_groq_env(prefix)
        configured = bool(os.getenv("GROQ_API_KEY"))
        return {
            "provider": "groq",
            "model": config.model,
            "execution_mode": REAL_GROQ_AI if configured else AI_UNAVAILABLE,
            "configured": configured,
            "fallback_mode": OFFLINE_AI,
        }
    if provider == "gemini":
        config = LLMProviderConfig.from_gemini_env(prefix)
        configured = bool(os.getenv("GEMINI_API_KEY"))
        return {
            "provider": "gemini",
            "model": config.model,
            "execution_mode": REAL_GEMINI_AI if configured else AI_UNAVAILABLE,
            "configured": configured,
            "fallback_mode": OFFLINE_AI,
        }
    if provider == "openrouter":
        config = LLMProviderConfig.from_openrouter_env(prefix)
        configured = bool(os.getenv("OPENROUTER_API_KEY"))
        return {
            "provider": "openrouter",
            "model": config.model,
            "execution_mode": REAL_OPENROUTER_AI if configured else AI_UNAVAILABLE,
            "configured": configured,
            "fallback_mode": OFFLINE_AI,
        }
    if provider == "huggingface":
        config = LLMProviderConfig.from_huggingface_env(prefix)
        configured = bool(os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY"))
        return {
            "provider": "huggingface",
            "model": config.model,
            "execution_mode": REAL_HUGGINGFACE_AI if configured else AI_UNAVAILABLE,
            "configured": configured,
            "fallback_mode": OFFLINE_AI,
        }
    if provider == "openai":
        config = LLMProviderConfig.from_env(prefix)
        configured = bool(os.getenv("OPENAI_API_KEY"))
        return {
            "provider": "openai",
            "model": config.model,
            "execution_mode": REAL_OPENAI_AI if configured else AI_UNAVAILABLE,
            "configured": configured,
            "fallback_mode": OFFLINE_AI,
        }
    if provider == "anthropic":
        config = LLMProviderConfig.from_anthropic_env(prefix)
        return {
            "provider": "anthropic",
            "model": config.model,
            "execution_mode": AI_UNAVAILABLE,
            "configured": bool(os.getenv("ANTHROPIC_API_KEY")),
            "fallback_mode": OFFLINE_AI,
            "implementation": "architecture_supported_not_integrated",
        }
    if provider == "ollama":
        config = LLMProviderConfig.from_ollama_env(prefix)
        return {
            "provider": "ollama",
            "model": config.model,
            "execution_mode": AI_UNAVAILABLE,
            "configured": bool(os.getenv("OLLAMA_BASE_URL")),
            "fallback_mode": OFFLINE_AI,
            "implementation": "architecture_supported_not_integrated",
        }
    return {
        "provider": "offline",
        "model": "offline-structured",
        "execution_mode": OFFLINE_AI,
        "configured": True,
        "fallback_mode": None,
    }


class LLMProvider:
    provider_name = "base"

    def __init__(self, config: Optional[LLMProviderConfig] = None):
        self.config = config or LLMProviderConfig()

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        raise NotImplementedError


class OfflineProvider(LLMProvider):
    provider_name = "offline"

    def __init__(self, output: Optional[Dict[str, Any]] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(config or LLMProviderConfig(provider="offline", model="offline-structured"))
        self.output = output or {}

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        return LLMStructuredResponse(
            provider=self.provider_name,
            model=self.config.model,
            output=dict(self.output),
            llm_calls=0,
            estimated_cost_usd=Decimal("0.00"),
            latency_ms=0.0,
            attempts=0,
        )


class MockProvider(LLMProvider):
    provider_name = "mock"

    def __init__(
        self,
        responses: Optional[List[Dict[str, Any]]] = None,
        failures_before_success: int = 0,
        malformed_before_success: int = 0,
        config: Optional[LLMProviderConfig] = None,
    ):
        super().__init__(config or LLMProviderConfig(provider="mock", model="mock-model"))
        self.responses = responses or [{}]
        self.failures_before_success = failures_before_success
        self.malformed_before_success = malformed_before_success
        self.calls = 0

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        self.calls += 1
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise LLMUnavailable("mock provider unavailable")
        output = {"malformed": True} if self.malformed_before_success > 0 else self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if self.malformed_before_success > 0:
            self.malformed_before_success -= 1
        return LLMStructuredResponse(
            provider=self.provider_name,
            model=self.config.model,
            output=dict(output),
            llm_calls=1,
            input_tokens=123,
            output_tokens=45,
            total_tokens=168,
            estimated_cost_usd=Decimal("0.01"),
            latency_ms=1.0,
            attempts=1,
            response_id=f"mock-{self.calls}",
        )


class GroqProvider(LLMProvider):
    """Native Groq Chat Completions provider with typed JSON output."""

    provider_name = "groq"
    api_key_env = "GROQ_API_KEY"
    api_url = GROQ_API_URL
    service_name = "Groq"
    max_tokens_field = "max_completion_tokens"
    retryable_failures = {"timeout", "network", "rate_limit", "provider_error", "malformed_response"}

    def __init__(
        self,
        config: Optional[LLMProviderConfig] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        super().__init__(config or LLMProviderConfig.from_groq_env())
        self.config = LLMProviderConfig(
            provider=self.provider_name,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout_seconds=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
            input_cost_per_1m=self.config.input_cost_per_1m,
            output_cost_per_1m=self.config.output_cost_per_1m,
        )
        self.transport = transport

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        api_key = os.getenv(self.api_key_env)
        timestamp = datetime.now(timezone.utc).isoformat()
        if not api_key:
            raise LLMUnavailable(
                f"{self.api_key_env} is not configured",
                failure_type="missing_api_key",
                timestamp=timestamp,
            )

        attempts = max(1, self.config.max_retries + 1)
        overall_started = time.perf_counter()
        last_error: Optional[LLMUnavailable] = None
        for attempt in range(1, attempts + 1):
            try:
                payload = self._request(api_key, schema_name, schema, system_prompt, user_payload)
                output = self._extract_output(payload)
                usage = payload.get("usage") or {}
                input_tokens = self._optional_int(usage.get("prompt_tokens"))
                output_tokens = self._optional_int(usage.get("completion_tokens"))
                total_tokens = self._optional_int(usage.get("total_tokens"))
                if total_tokens is None and input_tokens is not None and output_tokens is not None:
                    total_tokens = input_tokens + output_tokens
                latency_ms = round((time.perf_counter() - overall_started) * 1000, 4)
                return LLMStructuredResponse(
                    provider=self.provider_name,
                    model=str(payload.get("model") or self.config.model),
                    output=output,
                    llm_calls=1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=self._estimate_cost(input_tokens, output_tokens),
                    latency_ms=latency_ms,
                    attempts=attempt,
                    response_id=payload.get("id"),
                    timestamp=timestamp,
                    success=True,
                )
            except LLMUnavailable as exc:
                last_error = exc
            except (json.JSONDecodeError, LLMInvalidResponse, TypeError, ValueError) as exc:
                last_error = LLMUnavailable(
                    f"{self.service_name} returned malformed structured output",
                    failure_type="malformed_response",
                    attempts=attempt,
                    timestamp=timestamp,
                )
                last_error.__cause__ = exc

            if last_error.failure_type not in self.retryable_failures or attempt >= attempts:
                break
            time.sleep(min(0.35 * attempt, 1.5))

        latency_ms = round((time.perf_counter() - overall_started) * 1000, 4)
        failure_type = last_error.failure_type if last_error else "provider_unavailable"
        raise LLMUnavailable(
            self._safe_failure_message(failure_type),
            failure_type=failure_type,
            attempts=attempt,
            latency_ms=latency_ms,
            timestamp=timestamp,
        ) from last_error

    def _request(
        self,
        api_key: str,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
        schema_mode: str = "json_schema",
    ) -> Dict[str, Any]:
        safe_schema_name = "".join(char for char in schema_name if char.isalnum() or char in "_-")[:64] or "AuditraOutput"
        effective_system_prompt = system_prompt
        response_format: Dict[str, Any]
        if schema_mode == "json_object":
            effective_system_prompt = (
                f"{system_prompt} Return only one JSON object. Validate it against this JSON Schema: "
                f"{json.dumps(schema, default=str)}"
            )
            response_format = {"type": "json_object"}
        else:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": safe_schema_name,
                    "strict": False,
                    "schema": schema,
                },
            }
        body: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": effective_system_prompt},
                {"role": "user", "content": json.dumps(user_payload, default=str)},
            ],
            "temperature": self.config.temperature,
            self.max_tokens_field: self.config.max_tokens,
            "stream": False,
            "response_format": response_format,
        }
        try:
            with httpx.Client(timeout=self.config.timeout_seconds, transport=self.transport) as client:
                response = client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise LLMUnavailable(f"{self.service_name} request timed out", failure_type="timeout") from exc
        except httpx.RequestError as exc:
            raise LLMUnavailable(f"{self.service_name} network request failed", failure_type="network") from exc

        if response.status_code in {401, 403}:
            raise LLMUnavailable(f"{self.service_name} authentication failed", failure_type="authentication")
        if response.status_code == 429:
            raise LLMUnavailable(f"{self.service_name} rate limit exceeded", failure_type="rate_limit")
        if response.status_code in {408, 504}:
            raise LLMUnavailable(f"{self.service_name} request timed out", failure_type="timeout")
        if response.status_code >= 500:
            raise LLMUnavailable(f"{self.service_name} service is unavailable", failure_type="provider_error")
        if response.status_code >= 400:
            if schema_mode == "json_schema":
                return self._request(api_key, schema_name, schema, system_prompt, user_payload, schema_mode="json_object")
            raise LLMUnavailable(f"{self.service_name} rejected the structured request", failure_type="invalid_request")
        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMUnavailable(f"{self.service_name} returned invalid JSON", failure_type="malformed_response") from exc
        if not isinstance(payload, dict):
            raise LLMUnavailable(f"{self.service_name} returned an invalid response envelope", failure_type="malformed_response")
        return payload

    def _extract_output(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMInvalidResponse(f"missing {self.service_name} completion choice")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMInvalidResponse(f"missing {self.service_name} structured content")
        output = json.loads(content)
        if not isinstance(output, dict):
            raise LLMInvalidResponse(f"{self.service_name} structured content was not an object")
        return output

    def _estimate_cost(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[Decimal]:
        if (
            input_tokens is None
            or output_tokens is None
            or self.config.input_cost_per_1m is None
            or self.config.output_cost_per_1m is None
        ):
            return None
        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * self.config.input_cost_per_1m
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * self.config.output_cost_per_1m
        return (input_cost + output_cost).quantize(Decimal("0.000001"))

    def _optional_int(self, value: Any) -> Optional[int]:
        return int(value) if value is not None else None

    def _safe_failure_message(self, failure_type: str) -> str:
        messages = {
            "missing_api_key": f"{self.api_key_env} is not configured",
            "authentication": f"{self.service_name} authentication failed",
            "rate_limit": f"{self.service_name} rate limit exceeded",
            "timeout": f"{self.service_name} request timed out",
            "network": f"{self.service_name} network request failed",
            "provider_error": f"{self.service_name} service is unavailable",
            "invalid_request": f"{self.service_name} rejected the structured request",
            "malformed_response": f"{self.service_name} returned malformed structured output",
        }
        return messages.get(failure_type, "Groq provider is unavailable")


class OpenRouterProvider(GroqProvider):
    """OpenRouter chat-completions provider with structured output support."""

    provider_name = "openrouter"
    api_key_env = "OPENROUTER_API_KEY"
    api_url = OPENROUTER_API_URL
    service_name = "OpenRouter"
    max_tokens_field = "max_tokens"

    def __init__(self, config: Optional[LLMProviderConfig] = None, transport: Optional[httpx.BaseTransport] = None):
        super().__init__(config or LLMProviderConfig.from_openrouter_env(), transport=transport)


class HuggingFaceProvider(GroqProvider):
    """Hugging Face Inference Providers chat-completions adapter."""

    provider_name = "huggingface"
    api_key_env = "HF_TOKEN"
    api_url = HUGGINGFACE_API_URL
    service_name = "Hugging Face"
    max_tokens_field = "max_tokens"

    def __init__(self, config: Optional[LLMProviderConfig] = None, transport: Optional[httpx.BaseTransport] = None):
        super().__init__(config or LLMProviderConfig.from_huggingface_env(), transport=transport)

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        if not os.getenv("HF_TOKEN") and os.getenv("HF_API_KEY"):
            os.environ["HF_TOKEN"] = os.environ["HF_API_KEY"]
        return super().generate_structured(schema_name, schema, system_prompt, user_payload)


class GeminiProvider(LLMProvider):
    """Native Gemini Generate Content provider with JSON schema output."""

    provider_name = "gemini"
    service_name = "Gemini"
    retryable_failures = {"timeout", "network", "rate_limit", "provider_error", "malformed_response"}

    def __init__(self, config: Optional[LLMProviderConfig] = None, transport: Optional[httpx.BaseTransport] = None):
        super().__init__(config or LLMProviderConfig.from_gemini_env())
        self.transport = transport

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        api_key = os.getenv("GEMINI_API_KEY")
        timestamp = datetime.now(timezone.utc).isoformat()
        if not api_key:
            raise LLMUnavailable("GEMINI_API_KEY is not configured", failure_type="missing_api_key", timestamp=timestamp)
        attempts = max(1, self.config.max_retries + 1)
        overall_started = time.perf_counter()
        last_error: Optional[LLMUnavailable] = None
        for attempt in range(1, attempts + 1):
            try:
                payload = self._request(api_key, schema_name, schema, system_prompt, user_payload)
                output = self._extract_output(payload)
                usage = payload.get("usageMetadata") or {}
                input_tokens = self._optional_int(usage.get("promptTokenCount"))
                output_tokens = self._optional_int(usage.get("candidatesTokenCount"))
                total_tokens = self._optional_int(usage.get("totalTokenCount"))
                if total_tokens is None and input_tokens is not None and output_tokens is not None:
                    total_tokens = input_tokens + output_tokens
                return LLMStructuredResponse(
                    provider=self.provider_name,
                    model=self.config.model,
                    output=output,
                    llm_calls=1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=None,
                    latency_ms=round((time.perf_counter() - overall_started) * 1000, 4),
                    attempts=attempt,
                    response_id=payload.get("responseId"),
                    timestamp=timestamp,
                    success=True,
                )
            except LLMUnavailable as exc:
                last_error = exc
            except (json.JSONDecodeError, LLMInvalidResponse, TypeError, ValueError) as exc:
                last_error = LLMUnavailable(
                    "Gemini returned malformed structured output",
                    failure_type="malformed_response",
                    attempts=attempt,
                    timestamp=timestamp,
                )
                last_error.__cause__ = exc
            if last_error.failure_type not in self.retryable_failures or attempt >= attempts:
                break
            time.sleep(min(0.35 * attempt, 1.5))
        latency_ms = round((time.perf_counter() - overall_started) * 1000, 4)
        failure_type = last_error.failure_type if last_error else "provider_unavailable"
        raise LLMUnavailable(
            self._safe_failure_message(failure_type),
            failure_type=failure_type,
            attempts=attempt,
            latency_ms=latency_ms,
            timestamp=timestamp,
        ) from last_error

    def _request(self, api_key: str, schema_name: str, schema: Dict[str, Any], system_prompt: str, user_payload: Mapping[str, Any]) -> Dict[str, Any]:
        url = GEMINI_API_URL_TEMPLATE.format(model=self.config.model)
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(user_payload, default=str)}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        try:
            with httpx.Client(timeout=self.config.timeout_seconds, transport=self.transport) as client:
                response = client.post(url, headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json=body)
        except httpx.TimeoutException as exc:
            raise LLMUnavailable("Gemini request timed out", failure_type="timeout") from exc
        except httpx.RequestError as exc:
            raise LLMUnavailable("Gemini network request failed", failure_type="network") from exc
        if response.status_code in {401, 403}:
            raise LLMUnavailable("Gemini authentication failed", failure_type="authentication")
        if response.status_code == 429:
            raise LLMUnavailable("Gemini rate limit exceeded", failure_type="rate_limit")
        if response.status_code in {408, 504}:
            raise LLMUnavailable("Gemini request timed out", failure_type="timeout")
        if response.status_code >= 500:
            raise LLMUnavailable("Gemini service is unavailable", failure_type="provider_error")
        if response.status_code >= 400:
            raise LLMUnavailable("Gemini rejected the structured request", failure_type="invalid_request")
        payload = response.json()
        if not isinstance(payload, dict):
            raise LLMUnavailable("Gemini returned an invalid response envelope", failure_type="malformed_response")
        return payload

    def _extract_output(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise LLMInvalidResponse("missing Gemini candidate")
        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text.strip():
            raise LLMInvalidResponse("missing Gemini structured content")
        output = json.loads(text)
        if not isinstance(output, dict):
            raise LLMInvalidResponse("Gemini structured content was not an object")
        return output

    def _optional_int(self, value: Any) -> Optional[int]:
        return int(value) if value is not None else None

    def _safe_failure_message(self, failure_type: str) -> str:
        messages = {
            "missing_api_key": "GEMINI_API_KEY is not configured",
            "authentication": "Gemini authentication failed",
            "rate_limit": "Gemini rate limit exceeded",
            "timeout": "Gemini request timed out",
            "network": "Gemini network request failed",
            "provider_error": "Gemini service is unavailable",
            "invalid_request": "Gemini rejected the structured request",
            "malformed_response": "Gemini returned malformed structured output",
        }
        return messages.get(failure_type, "Gemini provider is unavailable")

class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, config: Optional[LLMProviderConfig] = None):
        super().__init__(config or LLMProviderConfig.from_env())
        self.config = LLMProviderConfig(
            provider="openai",
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout_seconds=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
            input_cost_per_1m=self.config.input_cost_per_1m,
            output_cost_per_1m=self.config.output_cost_per_1m,
        )

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMUnavailable("OPENAI_API_KEY is not configured")
        last_error: Optional[Exception] = None
        attempts = max(1, self.config.max_retries + 1)
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                payload = self._request(api_key, schema_name, schema, system_prompt, user_payload)
                output = self._extract_output(payload)
                usage = payload.get("usage", {})
                input_tokens = int(usage.get("input_tokens", 0))
                output_tokens = int(usage.get("output_tokens", 0))
                return LLMStructuredResponse(
                    provider=self.provider_name,
                    model=self.config.model,
                    output=output,
                    llm_calls=1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=self._estimate_cost(input_tokens, output_tokens),
                    latency_ms=round((time.perf_counter() - started) * 1000, 4),
                    attempts=attempt,
                    response_id=payload.get("id"),
                )
            except (json.JSONDecodeError, LLMInvalidResponse, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                time.sleep(min(0.5 * attempt, 2.0))
        raise LLMUnavailable(f"OpenAI structured response failed: {last_error}")

    def _request(
        self,
        api_key: str,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, default=str)},
            ],
            "max_output_tokens": self.config.max_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name[:64],
                    "schema": schema,
                    "strict": False,
                }
            },
        }
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _extract_output(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload.get("status") not in (None, "completed"):
            raise LLMInvalidResponse(f"response status was {payload.get('status')}")
        if payload.get("output_text"):
            return json.loads(payload["output_text"])
        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return json.loads(text)
        raise LLMInvalidResponse("missing structured output text")

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * self.config.input_cost_per_1m
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * self.config.output_cost_per_1m
        return money(input_cost + output_cost)


def validate_structured_output(model_type: type[BaseModel], response: LLMStructuredResponse) -> BaseModel:
    try:
        return model_type.model_validate(response.output)
    except ValidationError as exc:
        raise LLMInvalidResponse(str(exc)) from exc

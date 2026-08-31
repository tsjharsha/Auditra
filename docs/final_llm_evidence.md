# Final LLM Evidence

## Provider Architecture

Auditra is model-agnostic at the architecture level. The investigation engine and Financial World Builder depend on a common `LLMProvider` contract for structured generation. Finance records, verification, evaluation, evidence graph construction, challenge generation, retest logic, and assurance remain deterministic and independent of the model.

Implemented real-provider adapters in this repository:

| Provider | Status | Runtime mode |
| --- | --- | --- |
| Groq | Primary real-model submission path | `REAL_GROQ_AI` |
| Gemini | Implemented adapter | `REAL_GEMINI_AI` |
| OpenRouter | Implemented adapter | `REAL_OPENROUTER_AI` |
| Hugging Face | Implemented adapter | `REAL_HUGGINGFACE_AI` |
| OpenAI | Implemented legacy adapter | `REAL_OPENAI_AI` |
| Offline AI | Implemented no-network planner | `OFFLINE_AI` |
| Deterministic baseline | Implemented non-AI controller path | `DETERMINISTIC` |
| Anthropic | Architecture-supported placeholder, not integrated | `AI_UNAVAILABLE` |
| Ollama | Architecture-supported placeholder, not integrated | `AI_UNAVAILABLE` |

A future provider should be addable by implementing `LLMProvider.generate_structured`; it should not require rewriting the investigator, tools, evaluator, evidence graph, verification, assurance, or frontend architecture.

## Groq Implementation

Groq uses the OpenAI-compatible chat completions endpoint with JSON schema structured outputs. The default model is `openai/gpt-oss-20b`, verified against Groq documentation on 2026-08-31 as a supported structured-output model. `GROQ_MODEL` remains the source of truth for actual local runs.

The provider records safe metadata only: provider, model, timestamp, latency, response ID when returned, token counts when returned, estimated cost when calculable, attempts, and success/failure. API keys are never returned by the backend, written to artifacts, or bundled into the frontend.

## World Builder Test

Real Groq path:

```text
USER PROMPT -> GROQ -> FinancialWorldSpec -> validation -> deterministic generator -> financial world
```

The model interprets the prompt into a schema-validated spec. It does not generate authoritative financial records.

Measured evidence is written to `artifacts/real_groq.json` by:

```powershell
py -3.13 scripts/real_groq_validation.py
```

## Investigation Test

Real Groq path:

```text
EXCEPTION -> GROQ -> structured investigation plan -> bounded tools -> evidence -> verification -> decision
```

The model proposes candidate labels and typed tool plans. Auditra validates and executes only allowlisted tools with typed arguments and budget limits. Deterministic invariants remain authoritative.

## Smoke Benchmark And Comparisons

The real Groq evidence runner uses one Groq-built world and evaluates the same dataset through:

- deterministic controller
- offline AI controller
- real Groq controller

The artifact records accuracy, precision, recall, F1, false-positive/false-negative rates, auto-resolution, human escalation, unresolved rate, financial volume, correctly resolved amount, incorrectly classified amount, financial error impact, latency, throughput, LLM calls, AI invocation rate, tokens, estimated cost, provider failures, fallback count, class metrics, and failure taxonomy.

AI lift is reported separately for:

- real Groq vs deterministic
- real Groq vs offline AI

No README or report metric should be copied by hand when `artifacts/real_groq.json` is available.

## Metric Provenance

Every published real-Groq metric must identify:

- dataset prompt and seed
- world ID
- dataset ID
- dataset version
- controller version
- provider
- model
- mode
- record count
- artifact source

`artifacts/real_groq.json` is the machine-readable source of truth.

## Failures And Limitations

Auditra does not hide provider failures. If Groq is missing, unavailable, rate-limited, times out, or returns malformed structured output, the run is labeled as fallback/offline rather than `REAL_GROQ_AI`.

Token and cost fields are `null` when unavailable. Cost is reported only when the model pricing is known or explicitly configured.

## Ground-Truth Isolation

The LLM never receives hidden anomaly labels, expected classifications, evaluation score, assurance score, failure fingerprints, test-set labels, or ground-truth metadata. Those remain available only to independent evaluation after the controller run.

## Reproducibility

1. Configure `.env` with `AI_PROVIDER=groq`, `GROQ_API_KEY`, and `GROQ_MODEL`.
2. Run `py -3.13 scripts/real_groq_validation.py`.
3. Inspect `artifacts/real_groq.json`.
4. Run backend tests and frontend build.
5. Confirm `/health` reports provider status without exposing secrets.

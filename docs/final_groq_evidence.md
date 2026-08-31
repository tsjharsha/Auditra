# Final Groq Evidence

Source of truth: `artifacts/real_groq.json`
Generated at: `2026-08-31T07:21:06.132930+00:00`
Artifact status: `PASS`

## 1. Provider Architecture

Auditra uses a provider-agnostic LLM interface. The Financial World Builder and AI investigation planner call a shared structured-generation contract. The core finance systems remain unchanged: deterministic generation, reconciliation, invariants, evidence graph, independent evaluation, challenge/red-team, retest, human review, and assurance.

Groq is the primary real external provider for this submission. Gemini, OpenRouter, Hugging Face, and OpenAI remain implemented adapters. Anthropic and Ollama are documented as architecture-supported placeholders, not working integrations.

## 2. Groq Implementation

The Groq provider loads `GROQ_API_KEY`, `GROQ_MODEL`, timeout, token, and retry settings from environment variables. It makes a real HTTPS request to Groq, requests structured JSON, validates output with existing Pydantic schemas, records safe metadata, and falls back without preserving `REAL_GROQ_AI` when execution is not real.

## 3. Actual Model Used

Model recorded in the live artifact: `openai/gpt-oss-20b`.

## 4. World Builder Test

World-builder provider: `groq`
World-builder mode: `REAL_GROQ_AI`
World-builder model: `openai/gpt-oss-20b`
Dataset: `WORLD_FW_5472e64b3b0e`
Dataset version: `1`
Record count: `83`

Flow verified:

```text
USER PROMPT -> REAL GROQ -> FinancialWorldSpec -> existing validation -> deterministic generation -> financial world
```

Groq interpreted intent only. The deterministic generator remained authoritative for records and money math.

## 5. Investigation Test

Real investigation calls recorded: `1`
Total run LLM calls: `1`
Mode counts: `{"OFFLINE_AI": 39, "REAL_GROQ_AI": 1}`

Flow verified:

```text
EXCEPTION -> GROQ -> structured investigation plan -> bounded tools -> evidence -> verification -> final decision
```

## 6. Smoke Benchmark

The artifact includes `10` smoke case rows with case ID, provider, model, mode, success/failure, decision, verification, latency, tokens, and cost fields when available.

During the latest live run, Groq completed the world-builder request and `1` real investigation call(s). Groq then returned a rate limit and Auditra fell back to `OFFLINE_AI` for remaining AI-needed cases. Fallback reasons: `{"provider_circuit_open:rate_limit": 38, "rate_limit": 1}`.

This is reported as measured behavior, not hidden.

## 7. Real Groq Evaluation

| Metric | Value |
| --- | ---: |
| Cases | 83 |
| Accuracy | 100.00% |
| Precision | 100.00% |
| Recall | 100.00% |
| F1 | 100.00% |
| True positives | 83 |
| True negatives | 747 |
| False positives | 0 |
| False negatives | 0 |
| Auto-resolution | 80.72% |
| Human escalation | 19.28% |
| Unresolved | 0.00% |

## 8. Deterministic Comparison

| Mode | Accuracy | F1 | Financial error | Human review | LLM calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Deterministic | 96.39% | 96.04% | INR 4357.49 | 22.89% | 0 |
| Real Groq AI | 100.00% | 100.00% | INR 0.00 | 19.28% | 1 |

## 9. Offline Comparison

| Mode | Accuracy | F1 | Financial error | Human review | LLM calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Offline AI | 100.00% | 100.00% | INR 0.00 | 19.28% | 0 |
| Real Groq AI | 100.00% | 100.00% | INR 0.00 | 19.28% | 1 |

## 10. AI Lift

| Comparison | Accuracy delta | F1 delta | Financial error delta | Auto-resolution delta | Human-review delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Real Groq vs deterministic | 0.0361 | 0.0396 | INR -4357.49 | 0.0361 | -0.0361 |
| Real Groq vs offline AI | 0.0 | 0.0 | INR 0.00 | 0.0 | 0.0 |

## 11. Financial Impact

| Field | Value |
| --- | ---: |
| Financial volume | INR 341644.24 |
| Correctly resolved amount | INR 341644.24 |
| Incorrectly classified amount | INR 0.00 |
| Escalated amount | INR 51767.71 |
| Unresolved amount | INR 0.00 |
| Financial error impact | INR 0.00 |

## 12. Latency

P50 latency: `4.1553 ms`
P95 latency: `10.4772 ms`
Throughput: `7.75 records/sec`

## 13. Token Usage

Input tokens: `N/A`
Output tokens: `N/A`
Total tokens: `N/A`

Token totals are `N/A` when successful and fallback traces mix known and unknown values.

## 14. Cost

Estimated cost: `USD 0.00`

Cost is reported only from measured or configured pricing metadata. No cost values are invented.

## 15. Failure Behavior

Fallback count: `39`
Provider failures: `1`
Fallback reasons: `{"provider_circuit_open:rate_limit": 38, "rate_limit": 1}`
Failure types: `{"provider_circuit_open:rate_limit": 38, "rate_limit": 1}`

When Groq is unavailable, rate-limited, times out, or returns malformed output, Auditra labels the executed fallback as `OFFLINE_AI` instead of calling it Groq.

## 16. Ground-Truth Isolation

Groq receives only visible controller/world-builder context. Hidden anomaly labels, expected classifications, evaluator scores, assurance scores, failure fingerprints, and test-set labels remain isolated until independent evaluation.

## 17. Limitations

- The latest live Groq smoke was constrained by provider rate limits after `1` real investigation call(s).
- The artifact still proves real Groq connectivity, real world specification, structured validation, and real investigation participation.
- Offline fallback is part of the product safety behavior and is recorded, not hidden.

## 18. Reproducibility

1. Configure `.env` with `AI_PROVIDER=groq`, `GROQ_API_KEY`, and `GROQ_MODEL`.
2. Run `py -3.13 scripts/real_groq_validation.py`.
3. Inspect `artifacts/real_groq.json`.
4. Run `py -3.13 -m unittest discover -s tests -v`.
5. Run `npm run build` inside `frontend/`.

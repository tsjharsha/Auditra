# Auditra Agent Design

Auditra now runs a deterministic finance controller with an evidence-first AI investigation layer around exception and low-confidence cases.

## Authority Model

- Deterministic code performs all money arithmetic, duplicate checks, fee calculations, timing checks, invariant evaluation, status classification, and verification.
- The AI investigation layer returns a structured plan containing candidate hypotheses, typed tool calls, self-challenge prompts, and verification requirements.
- AI output cannot override deterministic arithmetic or mutate source records. It can only support a refinement when deterministic verification passes.
- Human review remains the required path for unresolved conflicts, failed verification, or insufficient evidence.
- Provider failure or repeatedly malformed structured output becomes `ai_unavailable=True` and escalates to `HUMAN_REVIEW`.

## Investigation Flow

```text
visible source records
  -> DatasetIndex with hidden ground truth stripped
  -> deterministic base investigation
  -> financial invariant engine
  -> risk scoring
  -> AI hypothesis agent when exception/low-confidence/failing invariant
  -> deterministic verification remains final authority
```

## Model-Selectable Tool Surface

The model can request only these mapped tools:

- `find_payment`
- `find_order`
- `find_settlement`
- `find_refunds`
- `find_fee_rules`
- `find_merchant`
- `get_transaction_history`
- `get_graph_neighborhood`
- `find_related_transactions`
- `compare_amounts`
- `check_temporal_relationship`
- `check_fee_applicability`
- `check_duplicate`
- `get_evidence`

Controller-internal tools such as `create_hypothesis`, `verify_hypothesis`, `create_reconciliation_case`, `request_human_review` and `find_related_records` remain logged but are not directly model-selectable.

Every tool call records input, summarized output, timestamps, duration, result size, success state and error type. Inputs are validated for path traversal, query-shaped strings, excessive length, deep nesting and oversized collections.
- `create_hypothesis`
- `verify_hypothesis`
- `create_reconciliation_case`
- `request_human_review`

## Hypotheses

The offline structured provider currently emits candidates such as:

- `fee_discrepancy`
- `refund_adjustment`
- `partial_or_incorrect_settlement`
- `missing_or_delayed_settlement`
- `duplicate_or_replayed_payment`
- `settlement_timing_mismatch`
- `unlinked_or_misaligned_order`

Each hypothesis records:

- supporting evidence IDs
- contradicting evidence IDs
- tool call IDs
- verification checks
- confidence
- rationale

## Provider Boundary

`OfflineStructuredProvider` performs no network calls. Real providers are opt-in through the shared LLM interface, with Groq as the primary submission path and Gemini/OpenRouter/Hugging Face/OpenAI preserved as implemented adapters. Configure provider, model, timeout, retries, max tokens and token-cost assumptions with environment variables such as `AI_PROVIDER`, `GROQ_MODEL`, `AUDITRA_WORLD_LLM_MODEL`, `AUDITRA_INVESTIGATION_LLM_TIMEOUT` and `AUDITRA_INVESTIGATION_LLM_MAX_RETRIES`.

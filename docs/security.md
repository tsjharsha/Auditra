# Auditra Security Notes

## Ground Truth Isolation

Scenario ground truth exists only for evaluation. `DatasetIndex` strips `ground_truth` before any controller tool receives data, and tests assert that controller run payloads do not contain:

- `ground_truth`
- `expected_status`
- scenario labels

## Agent Boundaries

- Tools are allowlisted.
- Evidence lookup is restricted to public entity types and existing record IDs.
- Model-selected tools are mapped to current visible records instead of arbitrary data access.
- Model-proposed tool plans are capped.
- Every tool call is logged with input, summarized output, timestamps, duration, result size, success state, and error type.
- Tool-call budgets trigger human review.
- Tool inputs reject path traversal, query-shaped strings, excessive nesting, long strings, and oversized arrays/maps.
- Tool result logs are capped to avoid oversized model-facing payloads.
- AI investigation output is advisory and cannot override deterministic arithmetic.
- AI provider, lookup, amount-tool, or temporal-tool failure escalates to `HUMAN_REVIEW`.
- Source records are not mutated during reconciliation.

## Secret Handling

- Do not commit Razorpay, Groq, OpenAI, database, payout, or webhook secrets.
- Provider adapters should read credentials from environment variables.
- The local demo uses an offline provider and makes no network LLM calls.
- `.env` is ignored; `.env.example` contains placeholders only.
- CORS defaults are limited to local Vite dev/preview hosts, with `AUDITRA_CORS_ORIGINS` override.

## Ingestion Controls

Current source ingestion rejects oversized payloads and excessive entity rows. Production upload surfaces should keep:

- file size limits
- extension and content-type validation
- schema validation before persistence
- path traversal prevention
- quarantine for malformed files
- row-level error reporting
- audit events for every accepted upload

## Persistence Requirements For Production

PostgreSQL persistence should keep ground truth tables and controller-visible tables in separate access paths. Controller services should not have read permissions on evaluation-only labels.

## Explicit Non-Goals

- No live money movement.
- No credentialed Razorpay production adapter.
- No model override of deterministic financial truth.

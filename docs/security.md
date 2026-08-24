# Auditra Security Notes

## Ground Truth Isolation

Scenario ground truth exists only for evaluation. `DatasetIndex` strips `ground_truth` before any controller tool receives data, and tests assert that controller run payloads do not contain:

- `ground_truth`
- `expected_status`
- scenario labels

## Agent Boundaries

- Tools are allowlisted.
- Every tool call is logged with input, output, timestamps, and success state.
- Tool-call budgets trigger human review.
- AI investigation output is explanatory and cannot override deterministic arithmetic.
- Source records are not mutated during reconciliation.

## Secret Handling

- Do not commit Razorpay, OpenAI, database, payout, or webhook secrets.
- Provider adapters should read credentials from environment variables.
- The local demo uses an offline provider and makes no network LLM calls.

## Ingestion Requirements For Production

When upload ingestion is added, it should include:

- file size limits
- extension and content-type validation
- schema validation before persistence
- path traversal prevention
- quarantine for malformed files
- row-level error reporting
- audit events for every accepted upload

## Persistence Requirements For Production

PostgreSQL persistence should keep ground truth tables and controller-visible tables in separate access paths. Controller services should not have read permissions on evaluation-only labels.

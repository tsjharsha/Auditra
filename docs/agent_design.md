# Auditra Agent Design

Auditra now runs a deterministic finance controller with an evidence-first AI investigation layer around exception and low-confidence cases.

## Authority Model

- Deterministic code performs all money arithmetic, duplicate checks, fee calculations, timing checks, invariant evaluation, status classification, and verification.
- The AI investigation layer proposes and ranks hypotheses, selects tools dynamically, summarizes support/contradiction, and recommends review context.
- AI output cannot override deterministic arithmetic or mutate source records.
- Human review remains the required path for unresolved conflicts, failed verification, or insufficient evidence.

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

## Tool Surface

The agent is limited to allowlisted, logged tools:

- `find_payment`
- `find_order`
- `find_merchant`
- `find_settlement`
- `find_refunds`
- `find_fee_rules`
- `get_transaction_history`
- `compare_amounts`
- `check_temporal_relationship`
- `find_related_records`
- `find_related_transactions`
- `check_fee_applicability`
- `check_duplicate`
- `get_graph_neighborhood`
- `get_evidence`
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

`OfflineStructuredProvider` is the default and performs no network calls. `OpenAIProvider` is present only as an explicit adapter boundary and is intentionally disabled in the local offline demo unless a production integration is added.

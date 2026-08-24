# Auditra Current State Audit

Date: 2026-08-24

## Baseline Commands

```powershell
python -m unittest discover -s tests -v
python scripts/demo_run.py --mode MIXED --records 1000 --seed 42
python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42
```

## Baseline Results

- Unit tests: 7 discovered, 6 passed, 1 skipped because FastAPI is not installed for the default Python interpreter.
- Mixed demo, 1,000 records, seed 42:
  - Accuracy: 0.979
  - Precision: 0.8387
  - Recall: 0.8515
  - F1: 0.8439
  - Match rate: 0.754
  - Automatic resolution rate: 0.999
  - False positive rate: 0.0131
  - False negative rate: 0.0
  - Throughput: 2364.68 records/sec
  - Failed cases: 21
- Benchmark, mixed mode, seed 42:
  - 100 records: 34.3 ms, 2915.05 records/sec, 0.96 accuracy, 4 failures
  - 500 records: 178.18 ms, 2806.2 records/sec, 0.948 accuracy, 26 failures
  - 1,000 records: 458.54 ms, 2180.85 records/sec, 0.979 accuracy, 21 failures

## What Exists

- Deterministic scenario generation with merchants, orders, payments, settlements, refunds, fee rules, and hidden ground truth.
- Decimal-based reconciliation math with deterministic fee, refund, settlement, duplicate, timing, and amount checks.
- Allowlisted investigation tools with structured tool-call logs.
- Verification checks before final decisions.
- Per-case evidence items and evidence graph.
- Human-review and unresolved terminal states.
- Independent evaluator that compares controller outputs with hidden ground truth only after controller execution.
- FastAPI and static frontend surfaces for datasets, runs, cases, exceptions, evidence, graphs, audit, evaluation, and demo mode.

## Main Gaps Against The Target Prompt

- The investigation loop is still a fixed deterministic script; every case uses the same broad tool sequence.
- There is no explicit AI investigation result object with hypotheses, self-challenge, provider metadata, token/cost fields, or supporting/contradicting evidence IDs.
- The evidence graph is source-record centric and does not yet represent investigations, decisions, evidence nodes, or support/contradiction edges as first-class relationships.
- Financial checks exist inside reconciliation logic, but there is no reusable invariant engine that emits rule-level pass/fail/not-applicable results.
- Confidence is a scalar score, not a factorized evidence/risk calculation.
- Risk scoring and review prioritization are not first-class fields.
- Evaluation does not yet compare deterministic-only and AI-assisted controller modes in one command.
- Upload ingestion, Razorpay adapters, PostgreSQL persistence, and production auth are planned but not implemented.

## Guardrails To Preserve

- Hidden ground truth must remain outside controller tools, controller responses, evidence items, graphs, and frontend data.
- LLMs must not perform authoritative arithmetic or mutate source records.
- Source records should remain immutable during a controller run.
- Tool calls should stay allowlisted, logged, and budgeted.
- Human review should remain an explicit outcome for conflicting or low-confidence cases.
- The local demo must run without external network calls or credentials.

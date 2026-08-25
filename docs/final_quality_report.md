# Final Quality Report

Date: 2026-08-25

## Acceptance Evidence

- `python -m unittest discover -s tests -v`: 24 tests discovered, 22 passed, 2 skipped because FastAPI is not installed in the default interpreter.
- `py -3.13 -m unittest discover -s tests -p test_api.py -v`: 2 passed.
- `python scripts/world_demo.py --seed 42`: completed prompt -> world -> audit -> evaluation -> AI-vs-baseline.
- `python scripts/ai_value_benchmark.py --records 1000 --seed 42`: completed deterministic vs AI-assisted value measurement.
- `python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42`: completed.

## Category Evidence

| Category | Evidence | Remaining Risk |
| --- | --- | --- |
| Financial correctness | Decimal money models, invariant tests, validation checks, deterministic verification | More adversarial currency/entity-link tuning needed |
| AI depth | Structured world-spec provider, OpenAI opt-in path, hypotheses, tool selection, self-challenge | Local run uses offline provider unless API key is configured |
| Agent quality | Allowlisted tools, model-selected typed tool plans, evidence IDs, tool logs, fail-closed AI unavailable state | Legacy mixed benchmark remains flat |
| Evidence quality | Evidence graph includes source records, investigation, decision, and evidence nodes | UI graph is compact rather than deeply filterable |
| Verification | Rule-specific verification and invariant engine | More counter-checks can be added per anomaly family |
| Evaluation rigor | Independent evaluator, confusion matrix, failure taxonomy, AI-vs-baseline | Held-out scenario split is not yet separate |
| Ground-truth integrity | DatasetIndex strips ground truth; tests assert no public leak | PostgreSQL access controls must be configured in deployment |
| Performance | Benchmarks report measured throughput/latency | 50,000-record benchmark not run in local environment |
| Security | No secrets committed; opt-in env providers; upload ingestion uses schema validation path | Authentication is not implemented |
| Backend architecture | Modular world builder, adapters, controller, evaluator, optional Postgres | PostgreSQL runtime needs external database to exercise fully |
| Frontend quality | Unified CREATE/STRESS/AUDIT/PROVE app with nav, builder, explorer, investigations, review, evaluation | Not migrated to React/Vite stack |
| UX | First screen supports prompt, schema preview, build, audit, break controller | No advanced graph filters yet |
| Product clarity | README/docs/demo script explain the product loop | Demo depends on local API being running |
| Documentation | Final architecture, world builder, data model, benchmarks, security, demo script, decisions | Deployment guide can be expanded |
| Razorpay relevance | Razorpay test adapter boundary; no live money movement | Live Razorpay credentialed adapter intentionally absent |

## Measured Demo Result

Seed-42 prompt world:

- 500 orders
- 506 payments
- 486 settlements
- 60 refunds
- 112 controlled anomalies
- INR 2145335.29 payment volume
- 0 ground-truth labels exposed publicly
- 0 external LLM calls by default

AI-assisted controller:

- Accuracy: 0.9960
- Precision: 0.9868
- Recall: 0.9953
- F1: 0.9907
- Automatic resolution: 0.9921
- Human escalation: 0.0079
- Throughput: 629.88 records/sec
- P95 latency: 2.2599 ms
- Tool calls: 6276
- Failures: 2

Phase A AI-value benchmark:

- Deterministic failures: 28
- AI-assisted failures: 3
- Accuracy lift: +0.0245
- F1 lift: +0.0796
- AMOUNT_MISMATCH recall: 0.6923 -> 0.9670
- AI invocation rate: 0.2153

## Final Assessment

Auditra now credibly demonstrates an AI-native financial control loop with its own controlled evaluation environment. It proves AI lift on the prompt-built refund-conflict dataset and keeps the legacy mixed benchmark result explicit rather than generalizing beyond the measured evidence.

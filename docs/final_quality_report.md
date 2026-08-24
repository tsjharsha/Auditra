# Final Quality Report

Date: 2026-08-25

## Acceptance Evidence

- `python -m unittest discover -s tests -v`: 16 tests discovered, 14 passed, 2 skipped because FastAPI is not installed in the default interpreter.
- `py -3.13 -m unittest discover -s tests -p test_api.py -v`: 2 passed.
- `python scripts/world_demo.py --seed 42`: completed prompt -> world -> audit -> evaluation -> AI-vs-baseline.
- `python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42`: completed.

## Category Evidence

| Category | Evidence | Remaining Risk |
| --- | --- | --- |
| Financial correctness | Decimal money models, invariant tests, validation checks, deterministic verification | More adversarial currency/entity-link tuning needed |
| AI depth | Structured world-spec provider, OpenAI opt-in path, hypotheses, tool selection, self-challenge | Local run uses offline provider unless API key is configured |
| Agent quality | Allowlisted tools, dynamic hypothesis paths, evidence IDs, tool logs | AI-assisted mode did not improve accuracy in seed-42 world demo |
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

- Accuracy: 0.9585
- Precision: 0.8067
- Recall: 0.9011
- F1: 0.8199
- Automatic resolution: 0.9664
- Human escalation: 0.0336
- Throughput: 813.47 records/sec
- P95 latency: 1.723 ms
- Tool calls: 6462
- Failures: 21

## Final Assessment

Auditra now credibly demonstrates an AI-native financial control loop with its own controlled evaluation environment. It does not claim that AI improves every metric; it proves the result with measured comparison.

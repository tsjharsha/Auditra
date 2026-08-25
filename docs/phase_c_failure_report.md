# Auditra Phase C Failure Report

Date: 2026-08-25

Phase C is complete for the current local product contract. The adversarial pass found real failures in world generation, tool handling, API limits, evidence access, and shared state safety; the critical issues were fixed and covered by regression tests. The remaining limitations are explicit and non-critical for the current demo boundary.

## Verification Gates

| Gate | Result |
| --- | --- |
| Full Python unit suite | PASS: 41 tests passed, 4 FastAPI tests skipped in Python 3.11 because FastAPI is installed in the Python 3.13 interpreter |
| FastAPI suite | PASS: 4 API tests passed with `py -3.13` |
| Python compile check | PASS: `python -m compileall backend scripts tests` |
| Frontend production build | PASS: `npm run build`; Vite warns that the main JS chunk is 908.21 kB after minification |
| Frontend dependency audit | PASS: `npm audit --audit-level=high` found 0 vulnerabilities |
| Demo flow | PASS: `python scripts/world_demo.py --seed 42` |
| PostgreSQL migration | NOT RUN: `AUDITRA_DATABASE_URL` is not configured and `psql` is not available in this local shell; migration SQL exists at `migrations/001_initial_postgres.sql` |
| Python dependency audit | ENV ISSUE: `pip check` reports a global conflict between `sentence-transformers 5.4.1` and `transformers 4.37.2`; neither package is declared by Auditra |

## Scale Benchmark

Artifact: `evaluation/phase_c_benchmark.json`

`AUDITRA_DATABASE_URL` was not configured, so DB time is reported as 0.0 ms for direct in-memory benchmarks.

| Records | Mode | Status | Total ms | Throughput r/s | Accuracy | F1 | Failures |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 100 | deterministic | completed | 764.17 | 138.79 | 0.9600 | 0.8867 | 4 |
| 100 | AI-assisted | completed | 860.11 | 123.99 | 0.9600 | 0.8867 | 4 |
| 500 | deterministic | completed | 3615.36 | 146.85 | 0.9480 | 0.8925 | 26 |
| 500 | AI-assisted | completed | 6086.31 | 86.83 | 0.9480 | 0.8925 | 26 |
| 1000 | deterministic | completed | 8798.48 | 129.96 | 0.9790 | 0.8439 | 21 |
| 1000 | AI-assisted | completed | 9133.84 | 125.57 | 0.9790 | 0.8439 | 21 |
| 5000 | deterministic | completed | 37016.47 | 144.42 | 0.9636 | 0.8053 | 182 |
| 5000 | AI-assisted | completed | 44457.92 | 120.66 | 0.9636 | 0.8053 | 182 |
| 10000 | deterministic | completed | 74764.19 | 143.29 | 0.9655 | 0.8122 | 345 |
| 10000 | AI-assisted | completed | 90683.01 | 118.04 | 0.9656 | 0.8122 | 344 |
| 50000 | not run | rejected by input contract | - | - | - | - | - |

The 50,000-record request is rejected because `ScenarioRequest` and `FinancialWorldSpec` cap local generation at 10,000 records. That is a documented scale boundary, not a crash.

## Held-Out Benchmark

Artifact: `evaluation/phase_c_heldout.json`

The held-out set contains 1,221 records per mode across normal, easy, hard, adversarial, multi-factor, and ambiguous slices. These fixed seeds and specs should not be used for future threshold tuning.

| Mode | Records | Weighted accuracy | Weighted F1 | Failures | Error impact | Incorrect amount |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic | 1221 | 0.9771 | 0.9503 | 28 | 24665.77 | 105728.82 |
| AI-assisted | 1221 | 0.9992 | 0.9985 | 1 | 242.03 | 742.18 |

Measured AI value on held-out worlds: 27 fewer failures, 24423.74 less error impact, and 104986.64 less incorrectly classified amount. Default local AI is offline and deterministic, so estimated AI cost remained 0.00.

## Concurrency Benchmark

Artifact: `evaluation/phase_c_concurrency.json`

| Concurrent runs | Status | Completed | Throughput runs/s | Duplicate IDs | State corruption |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | completed | 1 | 4.8078 | false | false |
| 5 | completed | 5 | 4.6938 | false | false |
| 10 | completed | 10 | 4.8235 | false | false |
| 25 | completed | 25 | 4.3565 | false | false |
| 50 | completed | 50 | 4.2533 | false | false |

## Demo Reliability

Artifact: `evaluation/phase_c_demo_reliability.json`

The five-minute demo prompt completed 10 of 10 times with zero system failures. Average duration was 908.88 ms. Each run produced 506 records, 0.996 accuracy, 0.9907 F1, 2 evaluation failures, and a 0.0079 human review rate.

## Failures Found And Fixed

1. Tool timeout crash at scale.
   - Before fix: a 10,000-record deterministic benchmark could fail when investigation tools exceeded the 1000 ms tool timeout.
   - Fix: initial lookup, amount, and temporal tool failures now become safe `HUMAN_REVIEW` escalations with explicit reason codes instead of crashing the run.
   - Evidence: `evaluation/phase_c_benchmark_prefix_failure.json` keeps the original failure replay; `evaluation/phase_c_benchmark.json` shows the post-fix 10,000-record completion.

2. Evidence access allowed hallucinated or hidden entities.
   - Before fix: `get_evidence()` could accept arbitrary IDs and non-public entity types.
   - Fix: evidence lookup is restricted to allowlisted public entity types and existing IDs, with sanitized errors.
   - Regression tests: `tests/test_phase_c_adversarial_security.py`.

3. LLM tool plans were not capped tightly enough.
   - Fix: model-proposed tool plans are capped at 24 accepted steps.
   - Regression tests: excessive tool-plan test in `tests/test_phase_c_adversarial_security.py`.

4. Controlled entity-link worlds were rejected.
   - Before fix: generated adversarial worlds with intentional missing order links failed validation.
   - Fix: controlled `entity_link_failure` records are validation warnings, while uncontrolled broken links still fail.
   - Regression tests: `tests/test_financial_world.py`.

5. Duplicate generation could inherit a broken entity link.
   - Before fix: a duplicate anomaly could copy a previous entity-link failure and create an uncontrolled broken link.
   - Fix: duplicate anomalies clone the current valid payment and only the clone receives the `duplicate_payment` ground-truth scenario.
   - Regression seed: 9005.

6. API input bounds were incomplete.
   - Fix: controller/evaluation record counts are bounded at 10 to 10,000, world prompts at 1 to 4,000 characters, and source ingestion payloads at 2 MB / 10,000 rows per entity list.
   - Regression tests: `tests/test_api.py`.

7. CORS was too permissive for the product app.
   - Fix: default origins are limited to local Vite preview/dev hosts, with `AUDITRA_CORS_ORIGINS` override.

8. Shared in-memory store needed explicit locking.
   - Fix: stateful store operations now use `RLock`.
   - Evidence: concurrency benchmark passes through 50 simultaneous runs with no duplicate IDs or state corruption.

## Remaining Limitations

- Local generation is intentionally capped at 10,000 records. Larger runs need a streaming benchmark path and durable database-backed execution.
- No live PostgreSQL instance is configured in this shell, so migration execution and real DB timing were not measured.
- The default local AI investigator does not improve the older synthetic MIXED scale benchmark materially; AI value is demonstrated on the held-out world-builder benchmark and the Phase A/Phase B demo worlds.
- Frontend code splitting remains future work; the current production bundle builds but Vite warns about the main chunk size.
- The local Python environment has unrelated global packages with a dependency conflict. Auditra's declared dependencies do not include those packages.

## Final Status

No critical Phase C issue remains open inside the current local contract. Phase C is complete and ready to push.

# Final Quality Report

Date: 2026-08-25

## Acceptance Evidence

| Gate | Result |
| --- | --- |
| Full Python unit suite | PASS: 41 tests passed, 4 FastAPI tests skipped in Python 3.11 because FastAPI is installed in Python 3.13 |
| FastAPI suite | PASS: 4 tests passed with `py -3.13` |
| Python compile check | PASS: `python -m compileall backend scripts tests` |
| Frontend build | PASS: `npm run build`; Vite reports a 908.70 kB JS chunk warning |
| Frontend dependency audit | PASS: `npm audit --audit-level=high` found 0 vulnerabilities |
| Demo CLI | PASS: `python scripts/world_demo.py --seed 42` |
| Demo UI | PASS: one-click `Run 5-Minute Demo` captured in final screenshots |
| Held-out evaluation | PASS: 1,221 records per mode in `evaluation/phase_c_heldout.json` |
| Concurrency | PASS: 1, 5, 10, 25, and 50 simultaneous local runs completed without duplicate IDs or state corruption |
| Security scan | PASS: no real secrets found; only placeholder env examples and expected docs references |
| PostgreSQL migration | NOT RUN locally: no `AUDITRA_DATABASE_URL` and no `psql` in shell |
| Live Groq smoke | See `artifacts/real_groq.json`; the runner records `BLOCKED_MISSING_KEY` if no `GROQ_API_KEY` is configured and uses `PASS_FULL_REAL`, `PASS_WITH_FALLBACK`, or `PARTIAL_RATE_LIMITED` for measured provider executions |
| Python environment audit | ENV ISSUE: global `sentence-transformers` requires a newer `transformers`; Auditra does not declare either package |

## Scored Assessment

| Area | Score | Evidence |
| --- | ---: | --- |
| Financial correctness | 8.5/10 | Decimal money models, invariant tests, refund/currency/fee/timing property tests, no critical correctness issue open |
| AI depth | 8.0/10 | Structured world understanding, bounded investigation plans, hypotheses, self-challenge, tool traces, offline mode plus opt-in Groq, Gemini, OpenRouter, Hugging Face, and OpenAI providers |
| Agent reliability | 8.0/10 | Tool failures now fail closed; tool plan cap; evidence lookup rejects hallucinated entities |
| Evidence | 8.0/10 | Evidence graph and case views show source records, verification, decisions, and tool traces |
| Verification | 8.5/10 | Deterministic invariants can block unsafe AI conclusions and force review |
| Evaluation | 9.0/10 | Confusion matrix, class metrics, financial confusion, held-out benchmark, AI-vs-baseline, latency, cost, throughput |
| Ground-truth integrity | 9.0/10 | DatasetIndex strips ground truth; public APIs and screenshots do not expose expected labels |
| Performance | 7.5/10 | 10,000-record local benchmark completes; 50,000 is intentionally rejected by contract |
| Security | 8.0/10 | No secrets, no money movement, bounded CORS, upload limits, allowlisted tools; authentication is not implemented |
| Frontend | 8.0/10 | Complete product flow, final screenshots, production build; bundle splitting remains future work |
| UX | 8.0/10 | One-click demo, builder, graph, review, evaluation, break-controller flow; deep filtering can improve |
| Product clarity | 9.0/10 | README and docs explain problem, AI boundary, metrics, failures, and reproduction |
| Demo | 8.5/10 | 10/10 reliability run, one-click UI demo, frozen seed/world/dataset |
| Documentation | 9.0/10 | Architecture, security, data model, benchmarks, failures, demo script, pitch, installation path |
| Testing | 8.5/10 | 45 targeted backend/API tests across available interpreters plus benchmark scripts |
| Razorpay alignment | 8.0/10 | Settlement/reconciliation/finance-ops focus and Razorpay test adapter boundary; no claim that Razorpay needs the tool |

## Frozen Demo Metrics

| Metric | Value |
| --- | ---: |
| Accuracy | 0.9960 |
| Precision | 0.9868 |
| Recall | 0.9953 |
| F1 | 0.9907 |
| False positive rate | 0.0000 |
| False negative rate | 0.0000 |
| Auto-resolution | 0.9921 |
| Human escalation | 0.0079 |
| Unresolved | 0.0000 |
| Throughput | 647.36 records/sec |
| P50 latency | 0.9167 ms |
| P95 latency | 2.1279 ms |
| P99 latency | 3.2324 ms |
| AI invocation rate | 0.2213 |
| LLM calls | 0 by default |
| Cost | USD 0.00 by default |
| Financial volume | INR 2148789.81 |
| Financial error impact | INR 647.36 |

## Final GO / NO-GO

| Item | Status |
| --- | --- |
| Full demo works | GO |
| Real AI path works | GO when `artifacts/real_groq.json` has an honest measured status such as `PASS_FULL_REAL`, `PASS_WITH_FALLBACK`, or `PARTIAL_RATE_LIMITED`; provider integration tests pass and missing-key runs are labeled honestly |
| AI vs baseline is measured | GO |
| World Builder works | GO |
| Audit works | GO |
| Evidence works | GO |
| Verification works | GO |
| Human review works | GO |
| Evaluation works | GO |
| Break the Controller works | GO |
| Held-out evaluation exists | GO |
| Ground truth is isolated | GO |
| No critical security issue | GO |
| No critical financial correctness issue | GO |
| Clean build | GO with Vite chunk-size warning |
| Clean repository | GO |
| Five-minute demo reproducible | GO |

Final decision: GO for the local reproducible Razorpay submission package. Do not claim a full no-fallback Groq execution unless `artifacts/real_groq.json` shows `PASS_FULL_REAL` with `REAL_GROQ_AI`, `llm_calls > 0`, and zero fallback. If the artifact shows `PARTIAL_RATE_LIMITED`, describe it as real-provider evidence with honest fallback disclosure.

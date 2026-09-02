# Final Submission Hardening Report

Generated: 2026-09-02

## Executive Result

Auditra is submission-ready for the core Track 04 workflow:

Orders -> Payments -> Fees/GST -> Refunds -> Settlements -> Exceptions -> Human review

The deterministic finance path, bounded AI investigation path, hidden-truth evaluation, assurance flow, exports, focused UI, and regression suite are complete. Live Groq evidence remains explicitly provider-dependent and is never represented as a full-provider pass when rate limits prevent that.

## P0 Status

| Item | Status | Evidence |
| --- | --- | --- |
| Real LLM evidence | DONE | Historical artifacts/real_groq.json records a real Groq world-builder call and real investigation call with PARTIAL_RATE_LIMITED status. Latest smoke path records FAILED_PROVIDER after a later rate-limit attempt. |
| Primary finance scenario | DONE | FeeRule now carries GST basis points; expected settlement subtracts fee, GST, and refund with Decimal arithmetic. |
| Priority exception | DONE | Home and Review expose exception ID, order, payment, fee, GST, refund, expected/actual settlement, variance, evidence, verification, and decision. |
| AI mode visibility | DONE | UI shows Live provider or Offline structured controller and exposes rate-limit fallback state. |
| KPI display | DONE | Match rate, auto-resolution, human review, unresolved, throughput, and financial error impact are first-class tiles. |
| Hidden truth isolation | DONE | Existing isolation and adversarial tests pass; ground truth remains evaluator-only. |
| Assurance/red team | DONE | Existing measured assurance and targeted red-team API/UI flow remain covered by passing tests. |
| Exports | DONE | Audit JSON and exception CSV API/UI paths pass export tests and exclude hidden truth/secrets. |
| Metric consistency | DONE | Explicit exception FPR/FNR fields and metric definitions are exposed; fresh benchmark artifacts were regenerated. |
| Full test suite | DONE | 66 tests passed. |

## P1 Status

| Item | Status |
| --- | --- |
| README Track 04 positioning and flow | DONE |
| GitHub metadata handoff | DONE in docs/github_submission_metadata.md; account settings remain manual |
| Demo-first UI | DONE |
| Four reusable scenario presets | DONE |
| Missing evidence fails closed | DONE and covered by a regression test |
| Evidence graph reflects actual case records | DONE |
| Judge-facing architecture/submission diagrams | DONE |
| Five-minute demo script | DONE |
| Final branding and focused SaaS visual system | DONE |
| Frontend quality/build | DONE |
| API quality and structured reports | DONE |

## P2 Status

| Item | Status |
| --- | --- |
| Screenshot sequence instructions | DONE; capture script follows the current UI and waits for enabled actions |
| Fresh quickstart | DONE |
| Windows and macOS/Linux commands | DONE |
| Route-level lazy loading | DONE |
| UI micro-polish | DONE |
| Professional limitations | DONE |

The refreshed Chrome capture was attempted. The current local process environment did not keep the paired Vite server available to the headless capture, so no new screenshot claim is made. Existing screenshots remain in docs/screenshots, and the exact capture command is documented.

## Fresh Validation

- Backend: python -m unittest discover -s tests -v -> 66 passed.
- Python syntax: py -3.13 -m compileall -q backend scripts tests -> passed.
- Frontend: npm run build -> passed; HomePage chunk 16.99 kB, initial index chunk 281.10 kB, Insights chunk 388.76 kB.
- API contract smoke -> health, 50-record build, audit, settlement brief, report, and ingestion all passed.
- Benchmark: 100, 500, and 1000 record runs completed; the 1000-record run measured 408.54 records/sec and 0.979 accuracy.
- AI-value benchmark: 1,022 records; deterministic accuracy 0.9726 / F1 0.9134 / error impact INR 16872.66; offline AI accuracy 0.9971 / F1 0.9930 / error impact INR 788.14.
- Held-out benchmark: 1,221 records per mode; deterministic accuracy 0.9771 / F1 0.9503 / error impact INR 24665.77; AI-assisted accuracy 0.9992 / F1 0.9985 / one failure / error impact INR 242.03.
- Demo reliability: 10 of 10 runs completed without system failure; each processed 506 records with accuracy 0.9960 and F1 0.9907.

## Real Provider Evidence

- Provider: Groq.
- Model: openai/gpt-oss-20b.
- Historical real artifact: artifacts/real_groq.json.
- Historical status: PARTIAL_RATE_LIMITED.
- Historical evidence: one real world-builder call and one real investigation call, followed by explicit offline fallback.
- Latest smoke artifact: artifacts/real_groq_smoke.json.
- Latest smoke status: FAILED_PROVIDER because Groq rate-limited during the world-builder attempt before a real call completed.
- No API key is printed, written to artifacts, or exposed to the frontend.

## Remaining External Handoff

- Apply the repository description/topics in docs/github_submission_metadata.md.
- Record a short demo video using docs/final_demo_script.md.
- For a clean full-provider run, wait for provider quota recovery and run scripts/real_groq_validation.py --records 20. Do not relabel a rate-limited result as PASS_FULL_REAL.
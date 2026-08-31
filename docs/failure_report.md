# Final Failure Report

Date: 2026-08-25

This report uses the frozen seed-42 demo and Phase C held-out artifacts. It does not hide remaining controller errors.

## Frozen Demo Failure Summary

Artifact: `data/world_demo/latest_world_summary.json`

| Category | Count | Financial impact | Representative example | Mitigation |
| --- | ---: | ---: | --- | --- |
| CLASSIFICATION_ERROR | 2 | INR 647.36 | Some amount-mismatch cases are predicted as partial settlement when the observed settlement is below expected net amount. | Keep deterministic amount/partial thresholds explicit; add more targeted tests for near-boundary partial-vs-mismatch cases before changing thresholds. |

Frozen demo totals:

- Accuracy: 0.9960
- F1: 0.9907
- Incorrectly classified amount: INR 3090.57
- Financial error impact: INR 647.36
- False positive rate: 0.0000
- False negative rate: 0.0000
- Unresolved rate: 0.0000

## Held-Out Failure Summary

Artifact: `evaluation/phase_c_heldout.json`

| Mode | Failures | Financial impact | Incorrect amount |
| --- | ---: | ---: | ---: |
| deterministic_only | 28 | INR 24665.77 | INR 105728.82 |
| ai_assisted | 1 | INR 242.03 | INR 742.18 |

The remaining AI-assisted held-out failure is a classification error in a hard amount/partial boundary case.

## Fixed During Hardening

| Failure | Impact | Fix |
| --- | --- | --- |
| Tool timeout crash at 10,000 records | Benchmark could fail instead of producing a measured result | Tool errors now fail closed into human review; failure replay preserved in `evaluation/phase_c_benchmark_prefix_failure.json` |
| Evidence lookup accepted non-public or hallucinated entities | Model/tool path could cite unavailable evidence | `get_evidence()` is allowlisted and validates entity existence |
| LLM tool plans could be excessive | Excessive tool-call loops | Accepted model tool plan steps are capped |
| Controlled entity-link worlds failed validation | Adversarial worlds could be rejected before audit | Controlled link failures are warnings; uncontrolled broken links still fail |
| Duplicate anomaly copied prior broken links | Concurrency run surfaced invalid generated worlds | Duplicates now clone the current valid payment and label only the clone as duplicate |
| API request bounds were incomplete | Oversized local runs/uploads were not clearly rejected | Request and ingestion size limits are enforced |
| Local CORS missed fallback dev port | Frontend on `5174` could not call the API | `5174` localhost origins are included and env override remains available |

## Remaining Limitations

- 50,000-record local benchmark requests are rejected by the 10,000-record input contract.
- Live Groq evidence requires a real `GROQ_API_KEY`; local fallback/offline behavior remains available without secrets.
- No live PostgreSQL migration was applied in this shell because no database/`psql` was available.
- No authentication layer is included in this prototype.

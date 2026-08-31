# AUDITRA

FROM FINANCIAL INTENT TO VERIFIED CONTROL.

Auditra is the scenario lab for autonomous finance controllers. It generates controlled payment worlds, lets a controller close them, verifies every decision against hidden ground truth, attacks measured weaknesses, and returns a versioned assurance decision.

It does not ask you to trust an AI. It measures whether you should.

## Problem

Financial AI agents are starting to touch reconciliation, settlement operations, exception triage, and finance workflows. The hard question is not whether a model can explain a transaction. The hard question is whether the system can prove that the explanation is correct, safe, and reproducible.

Traditional demos usually start with a static dataset and show a plausible answer. That leaves key questions unanswered:

- Was the exception actually planted and known?
- Did the AI improve accuracy or just sound confident?
- Did it leak ground truth into the controller?
- What happened when tools failed or evidence conflicted?
- How much money was classified incorrectly?

Auditra starts one step earlier by creating controlled financial worlds, then using those worlds to evaluate the controller.

## Solution

```text
GENERATE -> CLOSE -> VERIFY -> CHALLENGE -> ASSURE
```

1. Prompt a merchant/payment world.
2. Generate merchants, orders, payments, settlements, refunds, and fee rules.
3. Inject hidden controlled anomalies.
4. Build a financial evidence graph.
5. Run deterministic reconciliation controls.
6. Invoke bounded AI investigation only where useful.
7. Verify every decision against invariant checks and evidence.
8. Evaluate against hidden ground truth after the run.
9. Fingerprint the controller's highest-risk failure pattern.
10. Generate a targeted adversarial batch and retest the controller.
11. Issue a scored deployment recommendation with unsafe-action penalties.

## Architecture

![Auditra architecture](docs/assets/auditra_architecture.svg)

Core modules:

- `backend/auditra/financial_world/`: prompt understanding, schema, ontology, generation, adapters, validation.
- `backend/auditra/reconciliation.py`: deterministic financial controller plus AI-assisted investigation.
- `backend/auditra/agent_tools.py`: allowlisted, typed, logged investigation tools.
- `backend/auditra/invariants.py`: deterministic financial safety checks.
- `backend/auditra/evidence_graph.py`: evidence and decision graph.
- `backend/auditra/evaluator.py`: independent ground-truth evaluation.
- `backend/auditra/assurance.py`: challenge catalog, failure fingerprints, targeted retests, and assurance scoring.
- `backend/auditra/postgres.py`: optional PostgreSQL persistence.
- `frontend/`: React Scenario Lab and Finance Controller Challenge experience.

## Enterprise Challenge API

The Option B workflow is available through versioned, ground-truth-safe contracts:

```text
GET  /challenges
POST /challenges/{challenge_id}/build
POST /worlds/{world_id}/audit
GET  /audits/{evaluation_run_id}/assurance
POST /audits/{evaluation_run_id}/red-team
```

The assurance report includes weighted dimensions, unsafe auto-action penalties, financial exposure, control checks, a failure fingerprint, and one of three recommendations: controlled deployment, human-supervised operation, or remediation required. Public responses never expose hidden ground-truth labels.

## AI Architecture

AI is bounded by design:

- LLMs may produce structured world specs or investigation plans.
- LLMs do not generate authoritative money math.
- Tools are allowlisted and input-validated.
- Tool plans are capped.
- Ground truth is stripped from controller/tool access.
- Deterministic invariants can override AI confidence.
- Tool failures fail closed into human review.

Auditra uses a provider abstraction for external LLMs. The current real-model implementation used for this submission is Groq. Local demos can still run offline without secrets or network access.

## Financial Safety

Auditra uses decimal money arithmetic and explicit invariants for:

- Amount and fee consistency.
- Refund totals.
- Settlement timing.
- Currency consistency.
- Merchant consistency.
- Duplicate detection.
- Missing evidence and broken links.

No live money movement is implemented. Razorpay support is represented as a test-data adapter boundary, not a credentialed production integration.

## Final Metrics

Frozen demo:

- Prompt version: default seed-42 demo prompt.
- Seed: `42`
- World ID: `FW_0a7d61b20d15`
- Dataset ID: `WORLD_FW_0a7d61b20d15`
- Controller model: `ai_assisted` with offline deterministic investigator by default.
- Records: 506 payments from 500 orders.
- Payment volume: INR 2148789.81.

AI-assisted demo result:

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
| LLM calls | 0 by default |
| AI invocation rate | 0.2213 |
| Estimated AI cost | USD 0.00 |
| Financial amount correctly reconciled | INR 2145699.24 |
| Financial amount incorrectly classified | INR 3090.57 |
| Financial error impact | INR 647.36 |

AI vs baseline on the same frozen demo:

| Metric | Baseline | Auditra AI |
| --- | ---: | ---: |
| Accuracy | 0.9704 | 0.9960 |
| Precision | 0.8913 | 0.9868 |
| Recall | 0.9646 | 0.9953 |
| F1 | 0.8951 | 0.9907 |
| Auto-resolution | 0.9664 | 0.9921 |
| Human review | 0.0336 | 0.0079 |
| P95 latency | 1.8545 ms | 2.1279 ms |
| Cost / 1K | USD 0.00 | USD 0.00 |
| Failures | 15 | 2 |

Held-out benchmark:

| Mode | Records | Accuracy | F1 | Failures | Error impact | Incorrect amount |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 1221 | 0.9771 | 0.9503 | 28 | INR 24665.77 | INR 105728.82 |
| ai_assisted | 1221 | 0.9992 | 0.9985 | 1 | INR 242.03 | INR 742.18 |

Where AI helped: refund/amount ambiguity, over-escalation reduction, and exception investigation on harder world-builder slices.

Where AI did not help: the older synthetic MIXED scale benchmark remains mostly flat because the deterministic controller already makes the same decisions for those cases.

Where AI is intentionally not used: direct financial arithmetic, final invariant checks, ground-truth access, and authoritative settlement math.

## Real Groq AI Evidence

Source artifact: `artifacts/real_groq.json`

| Field | Value |
| --- | --- |
| Artifact status | `PASS` |
| Provider | Groq |
| Model | `openai/gpt-oss-20b` |
| Dataset | `WORLD_FW_5472e64b3b0e` |
| Dataset version | `1` |
| Cases | 83 |
| Mode | `REAL_GROQ_AI` |
| Accuracy | 100.00% |
| Precision | 100.00% |
| Recall | 100.00% |
| F1 | 100.00% |
| True positives | 83 |
| True negatives | 747 |
| False positives | 0 |
| False negatives | 0 |
| Financial volume | INR 341644.24 |
| Correct amount | INR 341644.24 |
| Incorrect amount | INR 0.00 |
| Escalated amount | INR 51767.71 |
| Unresolved amount | INR 0.00 |
| Financial error impact | INR 0.00 |
| P50 latency | 4.1553 ms |
| P95 latency | 10.4772 ms |
| Throughput | 7.75 records/sec |
| LLM calls | 1 |
| AI invocation rate | 48.19% |
| Input tokens | N/A |
| Output tokens | N/A |
| Total tokens | N/A |
| Estimated cost | USD 0.00 |
| Fallback count | 39 |
| Fallback reasons | `{"provider_circuit_open:rate_limit": 38, "rate_limit": 1}` |

The smoke artifact contains 10 case rows. During the latest live run Groq completed the world-builder request and 1 real investigation call(s), then the provider returned a rate limit and Auditra fell back to `OFFLINE_AI` for the remaining AI-needed cases. This is intentionally preserved in the artifact instead of being hidden.

Comparison on the same generated dataset:

| Mode | Accuracy | F1 | Financial error | Human review | LLM calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Deterministic baseline | 96.39% | 96.04% | INR 4357.49 | 22.89% | 0 |
| Offline AI | 100.00% | 100.00% | INR 0.00 | 19.28% | 0 |
| Real Groq AI | 100.00% | 100.00% | INR 0.00 | 19.28% | 1 |

Measured lift:

| Comparison | Accuracy delta | F1 delta | Financial error delta | Auto-resolution delta | Human-review delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Real Groq vs deterministic | 0.0361 | 0.0396 | INR -4357.49 | 0.0361 | -0.0361 |
| Real Groq vs offline AI | 0.0 | 0.0 | INR 0.00 | 0.0 | 0.0 |

## Failure Handling

Auditra does not hide failures. The frozen demo still has 2 classification errors with INR 647.36 financial error impact. Phase C also preserved a replay artifact for a scale-timeout crash that was fixed.

See:

- [Failure Report](docs/failure_report.md)
- [Phase C Failure Report](docs/phase_c_failure_report.md)

## Screenshots

Final screenshots are stored in `docs/screenshots/`:

- [Home](docs/screenshots/01-home-demo-ready.png)
- [World Builder](docs/screenshots/02-world-builder.png)
- [Schema](docs/screenshots/03-schema.png)
- [Financial World](docs/screenshots/04-financial-world.png)
- [Controller](docs/screenshots/05-controller.png)
- [Investigation](docs/screenshots/06-investigation.png)
- [Evidence Graph](docs/screenshots/07-evidence-graph.png)
- [Human Review](docs/screenshots/08-human-review.png)
- [Evaluation](docs/screenshots/09-evaluation.png)
- [Break the Controller](docs/screenshots/10-break-the-controller.png)

## Quick Start

Use Python 3.11+ and Node 20+.

```powershell
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Run tests:

```powershell
python -m unittest discover -s tests -v
py -3.13 -m unittest discover -s tests -p test_api.py -v
```

Run the API:

```powershell
py -3.13 -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002
```

Run the frontend:

```powershell
cd frontend
$env:VITE_AUDITRA_API_BASE="http://127.0.0.1:8002"
npx vite --host 127.0.0.1 --port 5174
```

Open:

```text
http://127.0.0.1:5174/
```

## Demo

Run from the UI with `Run 5-Minute Demo`, or from CLI:

```powershell
python scripts/world_demo.py --seed 42
```

Recreate final screenshots:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/capture_phase_d_screenshots.ps1 -BaseUrl http://127.0.0.1:5174
```

## Benchmarks

```powershell
python scripts/ai_value_benchmark.py --records 1000 --seed 42
python scripts/phase_c_heldout.py --records-per-slice 200 --seed 42000
python scripts/phase_c_benchmark.py --counts 100 500 1000 5000 10000 50000 --mode MIXED --seed 42 --output phase_c_benchmark.json
python scripts/phase_c_concurrency.py --levels 1 5 10 25 50 --records 120 --seed 9000
python scripts/phase_c_demo_reliability.py --runs 10 --seed 42 --records 500
```

## Optional LLM Providers

Primary real-model submission path:

```powershell
$env:AI_PROVIDER="groq"
$env:GROQ_API_KEY="..."
$env:GROQ_MODEL="openai/gpt-oss-20b"
py -3.13 scripts/real_groq_validation.py
```

This writes measured provider evidence to `artifacts/real_groq.json`. Auditra also keeps implemented adapters for Gemini, OpenRouter, Hugging Face, and OpenAI behind the same provider interface. Anthropic and Ollama are represented as architecture-supported placeholders and are not claimed as integrated providers.

Without provider variables, Auditra runs fully offline.

## Optional PostgreSQL

Apply:

```text
migrations/001_initial_postgres.sql
```

Then set:

```powershell
$env:AUDITRA_DATABASE_URL="postgresql://user:password@localhost:5432/auditra"
```

Without `AUDITRA_DATABASE_URL`, Auditra uses in-memory storage for local demos.

## Installation Test

Clean-environment reproduction:

```powershell
git clone https://github.com/tsjharsha/Auditra.git
cd Auditra
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python -m unittest discover -s tests -v
py -3.13 -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002
```

In a second terminal:

```powershell
cd frontend
$env:VITE_AUDITRA_API_BASE="http://127.0.0.1:8002"
npx vite --host 127.0.0.1 --port 5174
```

## Limitations

- Local generation is capped at 10,000 records; 50,000-record requests are rejected by input contract.
- Live Groq evidence requires a real `GROQ_API_KEY`; without it `scripts/real_groq_validation.py` records a blocked artifact instead of fabricated metrics.
- No authentication layer is implemented for the local prototype.
- No credentialed Razorpay money-movement integration is included.
- PostgreSQL migration execution requires an external database that was not available in this shell.
- Frontend production build passes, but Vite warns that the main JS chunk is larger than 500 kB.

## Documentation

- [Final Architecture](docs/final_architecture.md)
- [Agent Design](docs/agent_design.md)
- [World Builder](docs/world_builder.md)
- [Evaluation](docs/evaluation.md)
- [Security](docs/security.md)
- [Data Model](docs/data_model.md)
- [Benchmarks](docs/benchmarks.md)
- [Failure Report](docs/failure_report.md)
- [Final Demo Script](docs/final_demo_script.md)
- [30 Second Pitch](docs/30_second_pitch.md)
- [One Minute Technical Version](docs/one_minute_technical_version.md)
- [Installation Test](docs/installation_test.md)
- [Phase C Failure Report](docs/phase_c_failure_report.md)
- [Galarix Integration Boundary](docs/galarix_integration.md)
- [Engineering Decisions](docs/decisions.md)
- [Final Quality Report](docs/final_quality_report.md)
- [Final LLM Evidence](docs/final_llm_evidence.md)

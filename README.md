# AUDITRA

### AI Finance Controller for Razorpay-style payment reconciliation.

Built for Razorpay AI Buildathon 2026 - Track 04: AI Finance Controller.

Auditra closes a synthetic finance-ops batch across orders, payments, fees/GST, refunds, and settlements. It reports match rate, auto-resolution, human review, unresolved exceptions, throughput, and financial error impact, then verifies every controller decision against hidden ground truth.

> Do not trust the AI. Measure whether you should.

## Track 04 Fit

Razorpay's Track 04 asks teams to run one finance-ops loop over synthetic data, report match rate, list exceptions the agent could not resolve, and show throughput plus measured accuracy. Auditra is built around exactly that loop:

```text
Orders -> Payments -> Fees/GST -> Refunds -> Settlements -> Exceptions -> Human review
```

The controller never receives hidden labels. It closes the batch, bounded AI investigates ambiguous cases, deterministic controls verify money math, and an independent evaluator reveals what was correct only after the run.

## What The Demo Shows

1. Choose one payment-operations scenario: settlement close, refund net settlement, fee/GST variance, or peak-day exceptions.
2. Build a Razorpay-style batch with 50+ synthetic records and locked hidden truth.
3. Run the controller and see match rate, auto-resolution, human review, unresolved rate, throughput, and measured financial error impact.
4. Open one priority exception to compare expected and actual settlement, evidence, and verification checks.
5. Read a data-derived settlement brief, then export the audit JSON or exceptions CSV.
6. Run assurance and a targeted red-team retest against the controller's weakest measured failure pattern.

## Product Surface

The frontend is intentionally focused for judges:

- `Build batch`: generates the synthetic payment operations world and locks hidden ground truth.
- `Run controller`: reconciles payments, fees, refunds, and settlements.
- `Inspect evidence`: opens the priority exception and its evidence chain.
- `Audit JSON` / `Exceptions CSV`: exports a lightweight submission report.

Advanced pages still exist for world exploration, review, insights, settings, evidence graph, and evaluation lab, but the first screen keeps the story simple.

## Submission Flow

![Auditra submission flow](docs/assets/submission_flow.svg)

## Architecture

![Auditra architecture](docs/assets/auditra_architecture.svg)

Core modules:

- `backend/auditra/financial_world/`: prompt understanding, schema, generation, adapters, validation.
- `backend/auditra/reconciliation.py`: deterministic finance controller plus bounded AI investigation.
- `backend/auditra/agent_tools.py`: allowlisted, typed, logged investigation tools.
- `backend/auditra/invariants.py`: deterministic financial safety checks.
- `backend/auditra/evidence_graph.py`: evidence and decision graph.
- `backend/auditra/evaluator.py`: independent ground-truth evaluation.
- `backend/auditra/assurance.py`: challenge catalog, failure fingerprints, targeted retests, and assurance scoring.
- `backend/auditra/api.py`: FastAPI contracts for demo, challenge, audit, reports, review, and assurance.
- `frontend/`: React AI Finance Controller experience.

## API Contracts

```text
GET  /health
GET  /challenges
POST /challenges/{challenge_id}/build
POST /worlds/{world_id}/audit
GET  /audits/{evaluation_run_id}/assurance
POST /audits/{evaluation_run_id}/red-team
GET  /reports/{evaluation_run_id}
GET  /reports/{evaluation_run_id}/settlement-brief
GET  /reports/{evaluation_run_id}/exceptions.csv
POST /datasets/{dataset_id}/audit
```

Report endpoints are read-only and derive from existing controller and evaluation artifacts.

## AI Boundary

AI is bounded by design:

- LLMs may interpret prompts or propose structured investigation plans.
- LLMs do not perform authoritative money math.
- Decimal arithmetic, fee/refund/settlement checks, and final verification are deterministic.
- Investigation tools are allowlisted, typed, capped, and logged.
- Tool failures fail closed into review instead of auto-closing money movement.
- Ground truth is stripped from controller/tool access and used only by the evaluator.

## Metrics

### Metric Semantics

Accuracy is exact final-status agreement against hidden ground truth. F1 is macro F1 across the active reconciliation statuses.

Exception false-positive rate means normal payments raised as exceptions. Exception false-negative rate means true exceptions that were incorrectly closed as normal. This distinction is intentional: a final-status classification error is not automatically a missed financial exception.

### Razorpay-Style Operations

Auditra keeps the submission narrow, but makes the payment-operations loop concrete:

- **Payment settlement close:** captured payments, fee/GST deductions, refunds, and T+2 settlement reconciliation.
- **Refund net-settlement control:** post-settlement and partial refunds against expected net settlement.
- **Fee and GST variance:** fee-rule and GST assumptions compared with the resulting settlement.
- **Peak-day exception close:** duplicates, delayed settlements, missing links, and conflicting evidence.
### Offline Reproducible Demo

Runs without API keys and is suitable for a clean clone.

| Metric | Value |
| --- | ---: |
| Controller mode | `ai_assisted` with offline structured investigator |
| Seed | `42` |
| Orders | 500 |
| Payments | 506 |
| Payment volume | INR 2148789.81 |
| Accuracy | 0.9960 |
| F1 | 0.9907 |
| Auto-resolution | 0.9921 |
| Human escalation | 0.0079 |
| Throughput | 647.36 records/sec |
| External LLM calls | 0 by default |
| Financial error impact | INR 647.36 |

Why zero external calls here: the default local demo uses Auditra's offline structured investigator so judges can run it without secrets, rate limits, or network dependency.

### Held-Out Benchmark

| Mode | Records | Accuracy | F1 | Failures | Error impact | Incorrect amount |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 1221 | 0.9771 | 0.9503 | 28 | INR 24665.77 | INR 105728.82 |
| ai_assisted | 1221 | 0.9992 | 0.9985 | 1 | INR 242.03 | INR 742.18 |

### Real External LLM Evidence

Historical source artifact: `artifacts/real_groq.json`

Latest reproducible smoke artifact: `artifacts/real_groq_smoke.json` when a real Groq run is available. The current checked-in smoke path is `FAILED_PROVIDER` after a provider rate limit; the historical artifact remains the verified real-call evidence.

| Field | Value |
| --- | --- |
| Artifact status | `PARTIAL_RATE_LIMITED` |
| Provider | Groq |
| Model | `openai/gpt-oss-20b` |
| Mode | `REAL_GROQ_AI` with fallback disclosure |
| Cases | 83 |
| Accuracy | 100.00% |
| F1 | 100.00% |
| Financial error impact | INR 0.00 |
| LLM calls | 1 |
| Fallback count | 39 |
| Fallback reasons | `{"provider_circuit_open:rate_limit": 38, "rate_limit": 1}` |

The live run completed the Groq world-builder request and one real investigation call. Groq then rate-limited the run, so Auditra recorded offline fallback for the remaining AI-needed cases instead of pretending the entire run was external LLM-powered.

Status vocabulary used by the runner:

```text
PASS_FULL_REAL       - all required real-provider calls completed with no fallback
PASS_WITH_FALLBACK   - real provider ran and non-rate-limit fallback occurred
PARTIAL_RATE_LIMITED - real provider ran, then rate limits forced fallback
BLOCKED_MISSING_KEY  - provider key was not configured
FAILED_PROVIDER      - provider path did not produce valid real-provider evidence
```

## Screenshots

Final screenshots are stored in `docs/screenshots/`:

- [Home](docs/screenshots/01-home-demo-ready.png)
- [World builder](docs/screenshots/02-world-builder.png)
- [Controller](docs/screenshots/05-controller.png)
- [Human review](docs/screenshots/08-human-review.png)

Refresh the evidence set with `scripts/capture_phase_d_screenshots.ps1` while the frontend is running.

## Quick Start

Use Python 3.11+ and Node 20+.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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

Run the frontend in a second terminal:

```powershell
cd frontend
$env:VITE_AUDITRA_API_BASE="http://127.0.0.1:8002"
npx vite --host 127.0.0.1 --port 5174
```

Open `http://127.0.0.1:5174/`.

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Run the API:

```bash
python -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002
```

Run the frontend in a second terminal:

```bash
cd frontend
VITE_AUDITRA_API_BASE=http://127.0.0.1:8002 npx vite --host 127.0.0.1 --port 5174
```

Open `http://127.0.0.1:5174/`.

## Demo Commands

CLI smoke demo:

```powershell
python scripts/world_demo.py --seed 42
```

Benchmarks:

```powershell
python scripts/ai_value_benchmark.py --records 1000 --seed 42
python scripts/phase_c_heldout.py --records-per-slice 200 --seed 42000
python scripts/phase_c_demo_reliability.py --runs 10 --seed 42 --records 500
```

Real Groq validation:

```powershell
$env:AI_PROVIDER="groq"
$env:GROQ_API_KEY="..."
$env:GROQ_MODEL="openai/gpt-oss-20b"
py -3.13 scripts/real_groq_validation.py --records 20
# writes artifacts/real_groq_smoke.json; use --output to choose another path
```

Auditra also includes implemented adapters for Gemini, OpenRouter, Hugging Face, and OpenAI behind the same provider interface. Anthropic and Ollama are documented as architecture-supported placeholders and are not claimed as working integrations.

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

## Limitations

- Local generation is capped at 10,000 records; larger requests are rejected by input contract.
- Live Groq evidence requires a real `GROQ_API_KEY`; without it the runner writes `BLOCKED_MISSING_KEY` to the requested smoke path instead of fabricated metrics.
- No credentialed Razorpay money-movement integration is included; the submission uses safe synthetic Razorpay-style records.
- No full production authentication layer is implemented in this prototype.
- PostgreSQL migration execution requires an external database.
- The advanced analytics bundle remains larger than the focused home bundle; route-level lazy loading keeps the first screen small.

## Documentation

- [Top-Tier Submission Strategy](docs/top_tier_submission_strategy.md)
- [Final Architecture](docs/final_architecture.md)
- [Agent Design](docs/agent_design.md)
- [Evaluation](docs/evaluation.md)
- [Security](docs/security.md)
- [Data Model](docs/data_model.md)
- [Benchmarks](docs/benchmarks.md)
- [Failure Report](docs/failure_report.md)
- [Final Demo Script](docs/final_demo_script.md)
- [30 Second Pitch](docs/30_second_pitch.md)
- [One Minute Technical Version](docs/one_minute_technical_version.md)
- [Installation Test](docs/installation_test.md)
- [GitHub Submission Metadata](docs/github_submission_metadata.md)
- [Final Submission Hardening Report](docs/final_submission_hardening_report.md)
- [Final Quality Report](docs/final_quality_report.md)
- [Final LLM Evidence](docs/final_llm_evidence.md)

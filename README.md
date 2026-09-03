# AUDITRA

## AI Finance Controller for Razorpay-style Payment Operations

> **Run a finance close. Know what cash should settle. Investigate what does not. Measure whether the controller earned trust.**

Built for **Razorpay AI Buildathon 2026, Track 04: AI Finance Controller**.

Auditra is a finance-control workspace for a Razorpay-style payment operation. It builds a reproducible synthetic payment batch, reconciles orders, payments, fees, GST, refunds, and settlements, then gives a finance reviewer the answer that matters first:

```text
What cash should have settled? What was recorded? What is still pending? What needs attention before close?
```

It is deliberately not an AI chatbot around financial data. Auditra uses bounded AI only where interpretation helps, while deterministic controls remain authoritative for money arithmetic, settlement logic, verification, and final close decisions.

> **AI investigates. Deterministic controls verify. Hidden truth evaluates. Humans handle uncertainty.**
>
> **Do not trust the AI. Measure whether you should.**

![Auditra submission flow](docs/assets/submission_flow.svg)

---

## What A Reviewer Sees In 30 Seconds

1. Choose a payment-operations scenario and build a controlled batch with locked hidden truth.
2. Click **Run Finance Close**.
3. Read the backend-derived **Cash Position**: expected net settlement, recorded settlement, pending/unsettled cash, and settlement variance.
4. See the most important **Controller Alerts**, open the priority exception, and inspect linked evidence plus deterministic verification.
5. Review independent hidden-truth evaluation, assurance, a targeted red-team retest, and exportable audit evidence.

The primary demo is **Payment settlement close** with 500 synthetic source records. It is built for a five-minute judge flow, not a maze of dashboards.

---

## Track 04 Fit

| Track requirement | How Auditra answers it |
| --- | --- |
| Run a finance-operations loop | Closes linked orders, payments, fee/GST, refunds, and settlements. |
| Use synthetic data | Generates reproducible Razorpay-style worlds from fixed scenario specs and seeds. |
| Report reconciliation quality | Shows match rate, auto-resolution, human review, throughput, and independent accuracy/F1. |
| Surface exceptions | Raises current-run alerts, ranks a priority case, retains an exception queue, and supports human review. |
| Show real AI value | Compares deterministic-only and AI-assisted controller runs against held-out hidden truth. |
| Make the system trustworthy | Separates AI investigation from deterministic verification, evaluator-only truth, evidence logs, assurance, and red-team retesting. |

### The Finance Loop

```text
Orders
  -> Payments
  -> Fees / GST
  -> Refunds
  -> Settlements
  -> Reconciliation
  -> Exception Investigation
  -> Human Review
  -> Finance Close
```

---

## The Product: A Controller, Not A Chatbot

### 1. Can this batch close?

Auditra runs deterministic reconciliation across the current batch, then returns a close result with match rate, exposure, human-review count, unresolved rate, throughput, and assurance recommendation.

### 2. What cash should be here?

The Cash Position is calculated in the backend from `ControllerRun` reconciliation decisions using `Decimal` money values. The frontend never invents or calculates these values.

| Cash Position field | Meaning |
| --- | --- |
| Expected net settlement | Sum of the expected settlement amounts established by reconciliation. |
| Recorded settlement | Sum of settlement evidence that was actually recorded. |
| Pending / unsettled | Expected cash for cases without recorded settlement evidence. |
| Settlement variance | Absolute variance across recorded settlement mismatches. |

A non-zero variance marks the batch as **INVESTIGATION REQUIRED**. Pending settlement remains visible separately, so a reviewer can distinguish timing exposure from a recorded mismatch.

### 3. What needs attention?

The main Close workspace projects the four highest-priority current-run alerts from real reconciliation cases. It prioritizes missing settlement, amount or partial variance, refund conflicts, fee/GST signals, delayed settlement, duplicates, unresolved cases, high-risk cases, and human-review cases. Each actionable alert opens the underlying case.

### 4. Why should I trust the answer?

Every exception can be traced through linked payment-operation evidence, structured investigation output, invariant checks, verification results, tool traces, audit events, and independent post-run evaluation.

## Complete Product Surface

| Workflow | Delivered capability |
| --- | --- |
| Build | Four scenario templates create reproducible INR payment worlds with linked orders, payments, fees, GST, refunds, settlements, controlled anomalies, and evaluator-only hidden truth. |
| Close | **Run Finance Close** reconciles the current batch and reports match rate, exposure, unresolved work, human-review demand, and throughput. |
| Cash control | Backend-derived Cash Position separates expected settlement, recorded settlement, pending cash, and settlement variance. |
| Triage | Controller Alerts prioritize the material exceptions blocking close and deep-link into the underlying reconciliation case. |
| Investigation | Each case retains linked evidence, an evidence graph, deterministic invariants, verification results, bounded tool traces, and a typed AI investigation plan where ambiguity remains. |
| Review and evidence | Finance reviewers can record human decisions and export exception, audit, evaluation, and settlement-brief evidence as CSV or JSON. |
| Measured AI | Deterministic-only and AI-assisted outcomes are compared against hidden truth after the controller has decided. |
| Assurance | Assurance scores observed performance and safety, fingerprints measured failures, then produces a focused adversarial retest. |
| Deployment path | The local demo runs in memory with typed FastAPI contracts; an optional PostgreSQL schema is included for durable storage. |
| Provider integrity | Offline, real-provider, fallback, failure, retry, token, latency, and cost signals remain explicit rather than being presented as one undifferentiated AI result. |

---

## Four Finance-Control Scenarios

| Scenario | Operational question | Default batch | Stress profile |
| --- | --- | ---: | --- |
| **Payment settlement close** | Did captured payments, fees/GST, refunds, and T+2 settlements close correctly? | 500 | Stressed |
| **Refund net-settlement control** | Do post-settlement and partial refunds reconcile to expected net settlement? | 400 | Adversarial |
| **Fee and GST variance** | Do payment-method fee rules and GST assumptions tie to settlement results? | 400 | Stressed |
| **Peak-day exception close** | Can the controller handle duplicate payments, delays, missing links, and contradictory evidence? | 600 | Chaos |

All scenarios use INR, linked financial records, controlled anomalies, and hidden labels that are withheld from the controller until evaluation.

---

## How A Finance Close Runs

```text
Build controlled world
  -> validate financial relationships
  -> strip hidden truth from controller access
  -> run deterministic reconciliation
  -> investigate only ambiguous cases with bounded AI
  -> verify with financial invariants
  -> calculate cash position and alerts
  -> evaluate against hidden truth
  -> score assurance and optionally red-team the measured weakness
```

### Deterministic Finance Controls

Auditra keeps financial authority in code, not in a model response:

- `Decimal` arithmetic quantized to two places
- expected settlement, fee, GST, and refund calculations
- settlement amount, timing, duplicate, merchant, currency, and relationship checks
- financial invariants attached to each reconciliation case
- verification that can block unsafe automatic closure
- fail-closed escalation to `HUMAN_REVIEW` when an AI provider, tool, or safety check cannot establish a safe result

### Bounded AI Investigation

AI can help with the parts that require interpretation, not financial authority:

- interpret a world-building prompt into a typed `FinancialWorldSpec`
- propose structured hypotheses for ambiguous exceptions
- select from allowlisted, typed investigation tools
- explain evidence and self-challenge an investigation plan

AI cannot access hidden truth, execute arbitrary tools, change financial arithmetic, override a failed invariant, or silently close an unsafe exception.

---

## Trust Architecture

![Auditra architecture](docs/assets/auditra_architecture.svg)

| Layer | Responsibility | Trust boundary |
| --- | --- | --- |
| Financial World Builder | Produces linked merchants, orders, payments, settlements, refunds, and fee rules from a typed specification. | Hidden anomaly truth is stored separately. |
| Reconciliation Engine | Calculates expected settlement and classifies cases. | Deterministic controls own money logic. |
| AI Investigation Agent | Produces structured hypotheses and bounded tool plans for ambiguous cases. | Advisory only; no direct authority over money. |
| Evidence and Verification | Creates evidence graphs, invariant results, verification checks, and audit events. | Public records only; tool calls are allowlisted, capped, and logged. |
| Independent Evaluator | Compares final controller decisions to hidden ground truth after the run. | The controller never receives the labels. |
| Assurance and Red Team | Scores safety, fingerprints measured failures, and generates focused retests. | The controller is judged on its observed failure modes. |

### Hidden Ground Truth Isolated By Design

`DatasetIndex` removes `ground_truth` from controller and tool access. The evaluator receives it only after reconciliation completes. Tests assert that controller payloads do not expose ground-truth fields, expected labels, or scenario labels.

### Evidence Is Operational, Not Decorative

For a reconciliation case, Auditra retains:

- linked canonical records and evidence graph
- reasons, confidence, risk factors, and financial impact
- invariant results and verification checks
- investigation hypotheses, self-challenge, and selected recommendation
- typed tool-call inputs, summarized outputs, timestamps, durations, and errors
- human review actions and audit events

---

## Measured Evaluation, Not A Single Happy Path

The controller is evaluated after its decision against labels it could not see. The evaluator reports exact final-status agreement, macro F1, precision, recall, exception false-positive/false-negative rates, latency percentiles, throughput, financial amounts, financial error impact, confusion matrices, class metrics, and a failure taxonomy.

### Held-Out Benchmark

Artifact: [`evaluation/phase_c_heldout.json`](evaluation/phase_c_heldout.json)

| Mode | Records | Accuracy | Macro F1 | Failures | Financial error impact | Incorrectly classified amount |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Deterministic only | 1,221 | 97.71% | 95.03% | 28 | INR 24,665.77 | INR 105,728.82 |
| AI assisted | 1,221 | 99.92% | 99.85% | 1 | INR 242.03 | INR 742.18 |

The held-out artifact uses Auditra's offline structured investigator and records zero external LLM calls. That is intentional: it measures the implemented control architecture reproducibly, without claiming an external-provider run when one did not happen.

### Frozen Offline Demo

Artifact: [`data/world_demo/latest_world_summary.json`](data/world_demo/latest_world_summary.json)

| Metric | Measured value |
| --- | ---: |
| Orders / payments | 500 / 506 |
| Controlled anomalies | 112 |
| Payment volume | INR 2,148,789.81 |
| Accuracy | 99.60% |
| Macro F1 | 99.07% |
| Auto-resolution | 99.21% |
| Human escalation | 0.79% |
| Throughput | 647.36 records/sec |
| External LLM calls | 0 |
| Financial error impact | INR 647.36 |

### Reliability Evidence

Artifact: [`evaluation/phase_c_demo_reliability.json`](evaluation/phase_c_demo_reliability.json)

The recorded 500-record offline demo completed **10 of 10 runs** with zero system failures. Average duration was **908.88 ms**. These are local artifact results, not theoretical performance claims.

---

## Honest AI Provider Disclosure

Auditra runs without an API key by default using its **offline structured investigator**. The UI and API label this mode as offline; it is never presented as a live model call.

Implemented provider adapters share one structured-provider contract:

| Provider path | Runtime status |
| --- | --- |
| Groq | Implemented primary real-provider path (`REAL_GROQ_AI`) |
| Gemini | Implemented (`REAL_GEMINI_AI`) |
| OpenRouter | Implemented (`REAL_OPENROUTER_AI`) |
| Hugging Face | Implemented (`REAL_HUGGINGFACE_AI`) |
| OpenAI | Implemented legacy adapter (`REAL_OPENAI_AI`) |
| Offline structured investigator | Implemented, reproducible no-network mode (`OFFLINE_AI`) |
| Deterministic baseline | Implemented (`DETERMINISTIC`) |
| Anthropic / Ollama | Architecture-supported placeholders; not claimed as integrated providers |

### Real Groq Evidence

Auditra preserves provider failures rather than rewriting history:

- Historical artifact: [`artifacts/real_groq.json`](artifacts/real_groq.json)
- Status: `PARTIAL_RATE_LIMITED`
- Verified real calls: Groq world-building request and one real investigation call
- Dataset: 83 cases; recorded accuracy/F1: 100%; recorded financial error impact: INR 0.00
- Fallback count: 39 after rate limiting
- Latest smoke path: [`artifacts/real_groq_smoke.json`](artifacts/real_groq_smoke.json), currently `FAILED_PROVIDER` because the provider rate-limited

A rate-limited run is disclosed as fallback/offline. It is not presented as a fully successful external-LLM benchmark.

### Dedicated Multi-Provider Real-LLM Validation

The held-out 1,221-case benchmark remains a reproducible offline structured-investigator benchmark. It is separate from [`artifacts/real_llm_validation.json`](artifacts/real_llm_validation.json), a 20-30-record validation that attempts each AI investigation through **Groq -> Gemini -> OpenRouter -> Hugging Face**. This validation never uses the offline investigator as a fallback: a case succeeds only when a real provider returns a valid typed plan, and a case fails when all configured real providers fail. The artifact records per-case provider attempts, provider/model usage, failovers, failures, rate limits, and `offline_fallback_calls`.

Latest recorded validation: **`PASS_FULL_REAL`**. It processed 22 controller cases, completed all 10 required AI investigations through real providers, recorded two real-provider failovers, and recorded **zero offline fallback calls**. See the versioned [`real LLM validation artifact`](artifacts/real_llm_validation.json) for the per-case evidence.

---

## Assurance And Adversarial Retesting

A good demo batch is not enough. After evaluation, Auditra:

1. Calculates an assurance score across accuracy, safe autonomy, escalation, anomaly detection, financial-impact control, and evidence coverage.
2. Identifies unsafe automatic actions and measured error impact.
3. Produces a failure fingerprint from the actual evaluation failures.
4. Builds a targeted adversarial financial world around that weakness.
5. Re-runs the controller and reports whether the retest survived or confirmed the weakness.

The assurance response includes the recommendation (`CONTROLLED_DEPLOYMENT`, `HUMAN_SUPERVISED`, or `REMEDIATION_REQUIRED`), controls, unsafe exposure, measured error impact, and retest comparison.

---

## Five-Minute Judge Demo

Use **Payment settlement close**, **500 records**, and seed `42`.

| Time | Show | Say |
| --- | --- | --- |
| 0:00-0:25 | Close workspace | “Auditra runs the payment-operations close and brings only material exceptions to finance.” |
| 0:25-0:50 | Build batch | “This batch is synthetic and repeatable. Its truth labels are locked before the controller decides.” |
| 0:50-1:35 | Run Finance Close | “Deterministic controls reconcile money. Bounded AI investigates ambiguity but cannot override verification.” |
| 1:35-2:20 | Cash Position and alerts | “This is expected cash, recorded cash, pending cash, and variance. These alerts are the few cases blocking a safe close.” |
| 2:20-3:05 | Priority exception | “Here are the linked payment, fee/GST, refund, settlement, evidence, and verification results.” |
| 3:05-3:40 | Evaluation | “Hidden truth is revealed only after the run, so accuracy and financial impact are independent measurements.” |
| 3:40-4:25 | Assurance and red team | “Auditra retests its measured weakness instead of assuming one successful run proves safety.” |
| 4:25-5:00 | Export | “The close leaves behind exportable audit evidence and an exceptions CSV.” |

The detailed script is in [`docs/final_demo_script.md`](docs/final_demo_script.md).

---

## Run Locally

### Prerequisites

- Python 3.11+
- Node.js 20+
- No database or LLM key is required for the reproducible local demo.

### Windows PowerShell

```powershell
git clone https://github.com/tsjharsha/Auditra.git
cd Auditra
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

cd frontend
npm install
cd ..
```

Start the API:

```powershell
py -3.13 -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002
```

In a second terminal, start the frontend:

```powershell
cd frontend
$env:VITE_AUDITRA_API_BASE="http://127.0.0.1:8002"
npx vite --host 127.0.0.1 --port 5174
```

Open `http://127.0.0.1:5174/`.

### macOS / Linux

```bash
git clone https://github.com/tsjharsha/Auditra.git
cd Auditra
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cd frontend
npm install
cd ..
```

Start the API:

```bash
python -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002
```

In a second terminal, start the frontend:

```bash
cd frontend
VITE_AUDITRA_API_BASE=http://127.0.0.1:8002 npx vite --host 127.0.0.1 --port 5174
```

Open `http://127.0.0.1:5174/`.

---

## Reproduce The Evidence

### Test And Build

```powershell
python -m unittest discover -s tests -v

cd frontend
npm run build
cd ..
```

The final local validation ran **66 unit and integration tests** successfully, including financial invariants, provider fallback honesty, ground-truth isolation, API exports, assurance, red-team contracts, adversarial security, and financial property tests.

### CLI Demos And Benchmarks

```powershell
# Reproducible finance-world demo
python scripts/world_demo.py --seed 42

# AI value comparison on a prompt-built financial world
python scripts/ai_value_benchmark.py --records 1000 --seed 42

# Held-out benchmark
python scripts/phase_c_heldout.py --records-per-slice 200 --seed 42000

# Scale benchmark
python scripts/phase_c_benchmark.py --counts 100 500 1000 5000 10000 50000 --mode MIXED --seed 42 --output phase_c_benchmark.json

# Ten-run local reliability exercise
python scripts/phase_c_demo_reliability.py --runs 10 --seed 42 --records 500
```

### Dedicated Multi-Provider Validation

Configure any of the four existing real-provider keys in [`.env.example`](.env.example), then run:

```powershell
py -3.13 scripts/real_llm_validation.py --records 24
```

This writes `artifacts/real_llm_validation.json`. It is intentionally separate from the 1,221-case benchmark and returns `PASS_FULL_REAL` only when every attempted investigation completed through a real provider with `offline_fallback_calls = 0`.

### Historical Single-Provider Groq Smoke

```powershell
$env:AI_PROVIDER="groq"
$env:GROQ_API_KEY="..."
$env:GROQ_MODEL="openai/gpt-oss-20b"
py -3.13 scripts/real_groq_validation.py --records 20
```

This writes `artifacts/real_groq_smoke.json`. Inspect its status before making any external-provider claim. If a key is missing, the artifact says `BLOCKED_MISSING_KEY`; if the provider rate-limits or fails, it records fallback/failure instead of fabricated success.

Other implemented provider variables are documented in [`.env.example`](.env.example).

---

## API Surface

The frontend uses FastAPI endpoints that return typed, current-run artifacts.

```text
GET   /health
GET   /challenges
POST  /challenges/{challenge_id}/build
POST  /worlds/{world_id}/audit
GET   /reports/{evaluation_run_id}
GET   /reports/{evaluation_run_id}/settlement-brief
GET   /reports/{evaluation_run_id}/exceptions.csv
GET   /audits/{evaluation_run_id}/assurance
POST  /audits/{evaluation_run_id}/red-team

POST  /worlds/preview
POST  /worlds/build
POST  /ingest/{adapter}
POST  /controller/runs
GET   /reconciliation
GET   /exceptions
GET   /graph/{transaction_id}
POST  /investigations/{case_id}/run
POST  /review/{case_id}
GET   /audit
POST  /evaluation/compare
```

The audit and report responses include `cash_position` and `controller_alerts`, both derived server-side from the controller run. Export endpoints are read-only projections of existing audit and evaluation artifacts.

---

## Repository Map

| Path | What it contains |
| --- | --- |
| `backend/auditra/financial_world/` | Typed financial world understanding, generation, adapters, and validation. |
| `backend/auditra/reconciliation.py` | Deterministic close logic and AI-assisted exception handling. |
| `backend/auditra/finance_control.py` | Cash-position and controller-alert projections from the current run. |
| `backend/auditra/invariants.py` | Financial safety checks. |
| `backend/auditra/agent_tools.py` | Bounded, typed, logged evidence tools. |
| `backend/auditra/evidence_graph.py` | Evidence graph construction. |
| `backend/auditra/evaluator.py` | Independent hidden-truth evaluation. |
| `backend/auditra/assurance.py` | Assurance score, failure fingerprint, and targeted retest generation. |
| `backend/auditra/api.py` | FastAPI contract for demo, audit, reports, review, and evaluation. |
| `frontend/` | React finance-control workspace. |
| `tests/` | Unit, integration, security, financial-property, provider, and API tests. |
| `evaluation/` and `artifacts/` | Versioned benchmark and provider-evidence artifacts. |

---

## Optional PostgreSQL

Auditra defaults to in-memory storage so judges can run it immediately. For the optional PostgreSQL path:

1. Create a PostgreSQL database.
2. Apply [`migrations/001_initial_postgres.sql`](migrations/001_initial_postgres.sql).
3. Set `AUDITRA_DATABASE_URL`.
4. Restart the API.

The migration includes separate structures for canonical records, investigations, evidence, decisions, verification, audit events, evaluation, ground truth, and human reviews. Production deployment should keep controller-visible data and evaluator-only ground truth on separate access paths.

---

## Scope And Deliberate Limits

Auditra is a buildathon-grade, finance-control prototype. Its scope is intentionally focused:

- It uses safe, synthetic Razorpay-style records; it does not execute live payments or connect to credentialed Razorpay money movement.
- Local generation is capped at 10,000 records by input contract.
- The local demo uses in-memory storage unless PostgreSQL is configured.
- PostgreSQL migration execution requires an external database.
- No production authentication layer is included.
- Anthropic and Ollama are documented architectural extension points, not implemented provider integrations.
- Live-provider results depend on configured credentials and provider availability; the UI and artifacts disclose offline, fallback, and failure states.

Those boundaries are deliberate: the submission demonstrates a measurable finance-control loop without pretending to be a production payment processor.

---

## Submission Checklist

- [x] Four working finance-control scenarios
- [x] 50+ record synthetic batches with locked hidden truth
- [x] Cash Position from authoritative controller artifacts
- [x] Controller Alerts from current-run exceptions and exposure
- [x] Deterministic money logic and verification
- [x] Bounded, observable AI investigation
- [x] Human review, evidence, audit trail, and CSV/JSON exports
- [x] Independent evaluation, held-out benchmark, assurance, and targeted red-team retest
- [x] Reproducible offline local demo and test/build commands
- [ ] Record and link the final demo video
- [x] Set GitHub repository description and topics from [`docs/github_submission_metadata.md`](docs/github_submission_metadata.md)

---

## Further Reading

- [Final demo script](docs/final_demo_script.md)
- [30-second pitch](docs/30_second_pitch.md)
- [One-minute technical version](docs/one_minute_technical_version.md)
- [Final architecture](docs/final_architecture.md)
- [Evaluation methodology](docs/evaluation.md)
- [Benchmarks](docs/benchmarks.md)
- [Security notes](docs/security.md)
- [Data model](docs/data_model.md)
- [Agent design](docs/agent_design.md)
- [Provider setup](docs/llm_provider_setup.md)
- [Final LLM evidence](docs/final_llm_evidence.md)
- [Submission metadata](docs/github_submission_metadata.md)
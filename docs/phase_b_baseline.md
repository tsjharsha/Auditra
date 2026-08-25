# Phase B Baseline

Date: 2026-08-25

## Repository State

- Backend package is present under `backend/auditra`.
- Frontend is a single static file at `frontend/index.html`.
- No existing React/Vite package manifest was present before Phase B.
- Phase A documents and benchmark artifacts are present.

## Backend API Surface

Available endpoints from `backend/auditra/api.py`:

- `GET /health`
- `POST /worlds/preview`
- `POST /worlds/build`
- `POST /worlds/spec`
- `GET /worlds`
- `GET /worlds/{world_id}`
- `POST /worlds/{world_id}/audit`
- `POST /datasets`
- `GET /datasets`
- `POST /controller/runs`
- `GET /controller/runs/{run_id}`
- `GET /reconciliation`
- `GET /reconciliation/{case_id}`
- `GET /exceptions`
- `GET /exceptions/{case_id}`
- `GET /evidence/{evidence_id}`
- `GET /graph/{transaction_id}`
- `POST /investigations/{case_id}/run`
- `POST /review/{case_id}`
- `GET /audit`
- `POST /evaluation/scenarios`
- `POST /evaluation/runs`
- `POST /evaluation/compare`
- `GET /evaluation/runs/{evaluation_run_id}`
- `GET /evaluation/runs/{evaluation_run_id}/failures`
- `POST /demo`

## Test Baseline

```powershell
python -m unittest discover -s tests -v
py -3.13 -m unittest discover -s tests -p test_api.py -v
```

- Default Python: 24 tests run, 22 passed, 2 skipped because FastAPI is not installed in that interpreter.
- Python 3.13 API tests: 2 passed.

## Live API Smoke

The backend was already listening at `http://127.0.0.1:8000`.

Smoke flow:

1. `GET /health`
2. `POST /worlds/preview`
3. `POST /worlds/build`
4. `POST /worlds/{world_id}/audit`
5. `POST /evaluation/compare`

Result:

- Health: healthy
- Preview records: 120
- Schema entities: 6
- World: `FW_e15f0590b43c`
- Payments: 123
- Controlled anomalies: 29
- Audit cases: 123
- Accuracy: 0.9512
- F1: 0.8056
- Comparison modes: deterministic_only, ai_assisted
- Survival: `CONTROLLER FAILED 6 CASES`

## Phase A Verification

Phase A AI functionality is active through the backend models and artifacts:

- Structured LLM abstraction with offline, mock and OpenAI providers.
- Prompt world builder validates `FinancialWorldSpec`.
- AI investigations include hypotheses, tool calls, self-challenge and verification summaries.
- `evaluation/ai_value_benchmark.json` reports the Phase A seeded AI-value lift.

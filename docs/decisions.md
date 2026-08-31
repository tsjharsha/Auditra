# Engineering Decisions

## Deterministic Arithmetic Remains Authoritative

LLMs can create world specs or investigation plans. They do not create financial records, compute authoritative settlement math, or override verification.

## Offline Demo By Default

Both the world builder and investigator use a provider-agnostic LLM interface. Groq is the primary real-model submission path; Gemini, OpenRouter, Hugging Face and OpenAI remain optional implemented adapters. Offline/deterministic operation remains available so the demo runs without secrets or network calls.

Environment flags:

- `AUDITRA_USE_OPENAI_WORLD_BUILDER=1`
- `AUDITRA_USE_OPENAI_INVESTIGATOR=1`
- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `AUDITRA_OPENAI_MODEL`
- `AUDITRA_WORLD_LLM_TIMEOUT`
- `AUDITRA_INVESTIGATION_LLM_MAX_RETRIES`

## Dependency-Free Frontend

The brief requested React/Vite/Tailwind. The existing repo had a static frontend and no Node build chain. For demo stability, the product UI was rebuilt as a dependency-free application in `frontend/index.html`. This preserves the current localhost flow and avoids adding an untested build stack.

## PostgreSQL Is Optional Locally

`AUDITRA_DATABASE_URL` enables PostgreSQL persistence. Without it, the local demo uses in-memory storage. The migration is present, and the repository writes visible datasets separately from ground truth.

## AI vs Baseline Is Honest

Phase A reports AI value only where the measured dataset proves it. The prompt-built refund-conflict world improved from 15 failures to 2 in the seed-42 demo, and the 1000-record AI-value benchmark improved from 28 failures to 3. The legacy `ScenarioGenerator` mixed benchmark remains flat, so docs keep that distinction explicit.

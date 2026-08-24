# Engineering Decisions

## Deterministic Arithmetic Remains Authoritative

LLMs can create world specs or investigation plans. They do not create financial records, compute authoritative settlement math, or override verification.

## Offline Demo By Default

Both the world builder and investigator support opt-in OpenAI providers. The default path is deterministic and offline so the demo runs without secrets or network calls.

Environment flags:

- `AUDITRA_USE_OPENAI_WORLD_BUILDER=1`
- `AUDITRA_USE_OPENAI_INVESTIGATOR=1`
- `OPENAI_API_KEY`
- `AUDITRA_OPENAI_MODEL`

## Dependency-Free Frontend

The brief requested React/Vite/Tailwind. The existing repo had a static frontend and no Node build chain. For demo stability, the product UI was rebuilt as a dependency-free application in `frontend/index.html`. This preserves the current localhost flow and avoids adding an untested build stack.

## PostgreSQL Is Optional Locally

`AUDITRA_DATABASE_URL` enables PostgreSQL persistence. Without it, the local demo uses in-memory storage. The migration is present, and the repository writes visible datasets separately from ground truth.

## AI vs Baseline Is Honest

In the measured seed-42 world demo, AI-assisted mode did not improve classification accuracy. It added investigation traceability, hypotheses, evidence links, and tool activity at a throughput cost. The product reports that directly.

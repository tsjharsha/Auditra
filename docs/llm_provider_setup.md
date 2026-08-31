# Auditra LLM Provider Setup

Auditra can run with offline deterministic planning or a real external LLM provider. The LLM only interprets intent and proposes investigation plans. Deterministic Auditra code still owns financial generation, verification, evaluation, and assurance.

## Provider Selection

Set one of these values in project-root `.env`:

```env
AI_PROVIDER=groq
```

Supported values:

- `offline`
- `groq`
- `gemini`
- `openrouter`
- `huggingface`
- `openai`
- `anthropic` (architecture-supported placeholder; not integrated)
- `ollama` (architecture-supported placeholder; not integrated)

You can also scope providers separately:

```env
AUDITRA_WORLD_LLM_PROVIDER=gemini
AUDITRA_INVESTIGATION_LLM_PROVIDER=openrouter
```

If no provider is set, Auditra auto-selects the first configured key in this order: Groq, Gemini, OpenRouter, Hugging Face, then offline. Use an explicit provider when testing a specific model.

## Recommended Buildathon Default

Use Groq for the submission path:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT=20
GROQ_MAX_TOKENS=1200
GROQ_MAX_RETRIES=1
```

Auditra remains model-agnostic, but the real-model evidence artifact for this submission is generated through Groq.

## Groq

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT=20
GROQ_MAX_TOKENS=1200
GROQ_MAX_RETRIES=1
```

Use this when speed is more important than best reasoning quality.

## OpenRouter

```env
AUDITRA_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=qwen/qwen-2.5-72b-instruct:free
OPENROUTER_TIMEOUT=20
OPENROUTER_MAX_TOKENS=1200
OPENROUTER_MAX_RETRIES=1
```

Use this to try many free/cheap models quickly. If a selected model does not support structured outputs reliably, Auditra will fallback honestly instead of pretending it succeeded.

## Hugging Face Inference Providers

```env
AUDITRA_LLM_PROVIDER=huggingface
HF_TOKEN=your_token_here
HF_MODEL=openai/gpt-oss-120b:fastest
HF_TIMEOUT=30
HF_MAX_TOKENS=1200
HF_MAX_RETRIES=1
```

Use this to route open-source models through Hugging Face's provider router.

## Verify Runtime

Start backend:

```powershell
py -3.13 -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002
```

Check runtime labels:

```powershell
Invoke-RestMethod http://127.0.0.1:8002/health | ConvertTo-Json -Depth 5
```

Expected labels include:

- `REAL_GROQ_AI`
- `REAL_GEMINI_AI`
- `REAL_OPENROUTER_AI`
- `REAL_HUGGINGFACE_AI`
- `REAL_OPENAI_AI`
- `OFFLINE_AI`
- `AI_UNAVAILABLE` for configured-but-not-integrated placeholders such as Anthropic/Ollama

## Real Groq Evidence

After configuring `GROQ_API_KEY`, generate measured evidence:

```powershell
py -3.13 scripts/real_groq_validation.py
```

This writes `artifacts/real_groq.json` with dataset provenance, model/mode labels, measured controller metrics, token fields when returned by Groq, cost only when calculable, and AI lift against deterministic and offline runs. If the key is missing, the artifact records `BLOCKED` instead of fabricating numbers.

## Run Verification

```powershell
$env:AUDITRA_LLM_PROVIDER='offline'
py -3.13 -m unittest discover -s tests -v
Remove-Item Env:\AUDITRA_LLM_PROVIDER
```

```powershell
cd frontend
npm run build
```

## Real Provider Benchmark Plan

For each provider, run the same world prompt and the same 5-10 evaluation cases. Compare:

- structured output success rate
- fallback count
- investigation quality
- accuracy / precision / recall / F1
- financial error impact
- latency
- token usage if available
- estimated cost if available

The demo default should be whichever provider gives the best structured reliability and controller quality, not whichever is flashiest.



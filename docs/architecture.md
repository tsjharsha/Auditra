# Auditra Architecture

## Overview
Auditra separates the probabilistic generation of code (AI) from the deterministic evaluation of code (Verification Engine). 

## Component Flow

```text
Frontend (React War Room)
   ↓
FastAPI (SSE Stream)
   ↓
Verification Engine
   ├── Scenario Generator (Creates adversarial & boundary cases)
   ├── Oracle (Trusted deterministic evaluator)
   ├── Patch Validator (AST parsing & security filters)
   ├── Sandbox (Isolated subprocess execution)
   ├── State Machine (Enforces strict ATTACK -> PATCH -> VERIFY -> ROLLBACK transitions)
   └── Target Services (Vulnerable financial mock services)
```

## The Verification Loop

1. **Baseline Load**: Load the target vulnerable service.
2. **Attack**: Generate adversarial scenarios and push them through the target.
3. **Detection**: The independent Oracle detects behavioral variance.
4. **Diagnosis**: Extract the variance footprint and prompt the untrusted LLM for a repair.
5. **Validation**: The Patch Validator checks the generated patch AST for safe imports and syntax.
6. **Execution**: The patch is applied in an isolated Sandbox.
7. **Regression / Reverification**: The Oracle pushes ALL scenarios (including normal regression cases) through the patched code.
8. **Verdict**: If 100% agreement with the Oracle is reached, the patch is ACCEPTED. If the patch fails, it is REJECTED and ROLLED BACK instantly.

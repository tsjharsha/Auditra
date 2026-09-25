# Auditra Threat Model

## Trust Boundary

```text
                  ┌──────────────┐
                  │     LLM      │
                  │  UNTRUSTED   │
                  └──────┬───────┘
                         │
                    proposal
                         ↓
                  ┌──────────────┐
                  │ Patch Guard  │
                  └──────┬───────┘
                         ↓
                  ┌──────────────┐
                  │   Sandbox    │
                  └──────┬───────┘
                         ↓
                  ┌──────────────┐
                  │   Oracle     │
                  │   TRUSTED    │
                  └──────┬───────┘
                         ↓
                  ACCEPT / REJECT
```

Auditra explicitly treats AI-generated code as untrusted. The core philosophy is **AI proposes. Auditra verifies.**

## Mitigations

1. **Untrusted LLM Output**
   - **Threat**: The LLM generates syntactically invalid or non-executable code.
   - **Mitigation**: The Patch Validator runs an AST (Abstract Syntax Tree) check before execution. Malformed Python is instantly rejected.

2. **Malicious Patch (Command Injection / Data Exfiltration)**
   - **Threat**: The LLM proposes a patch containing `os.system('rm -rf /')` or `requests.post(...)`.
   - **Mitigation**: 
     - **Static**: `ASTValidator` recursively inspects the AST and explicitly blocks unsafe modules (`os`, `sys`, `subprocess`, `socket`) and built-ins (`eval`, `exec`, `open`).
     - **Runtime**: The Sandbox executes the patch in a constrained `subprocess` boundary.

3. **Infinite Loops / Denial of Service**
   - **Threat**: The AI proposes code with a `while True:` loop, hanging the verification engine.
   - **Mitigation**: The Sandbox applies a strict time bound (e.g., 2 seconds). If the process exceeds this, it is terminated, and the patch is rejected.

4. **Regression / Unintended Behavioral Changes**
   - **Threat**: The AI successfully fixes the reported defect but breaks another edge case.
   - **Mitigation**: The independent Oracle runs a full regression suite (normal cases, boundary cases, adversarial cases) against the patched target. The patch is only accepted if it reaches 100% behavioral agreement.

5. **Oracle Corruption**
   - **Threat**: The Oracle itself is flawed.
   - **Limitation**: Verification quality is bounded by Oracle quality and scenario coverage. Auditra does not mathematically prove arbitrary program correctness; it provides independent behavioral verification over defined invariants.

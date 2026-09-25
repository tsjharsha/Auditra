# The Verification Engine

Auditra's core capability is not generating code, but **verifying it deterministically**.

## 1. Scenario Generation
The engine synthesizes a predefined matrix of scenarios against each target service. Scenarios are broken down into:

- **Normal cases**: Expected, standard inputs (e.g. `state_code="CA"`).
- **Boundary cases**: Inputs at the exact edge of conditional logic (e.g. amount = `10000.00`).
- **Adversarial cases**: Invalid or unexpected types (e.g. `1e9`, `unknown_state`, negative amounts).

## 2. Independent Oracle
The Oracle is a hidden, trusted reference implementation. It explicitly represents the **invariants** of the financial system. 
For every scenario, both the untrusted target code and the Oracle execute. If their outputs differ (e.g. the untrusted target calculates an $0.08 tax rate instead of $0.0825), the Verification Engine flags a behavioral variance.

## 3. Sandboxing & AST Validation
If the AI proposes a patch to fix the variance:
1. **AST Validation**: The Python Abstract Syntax Tree is traversed. If the LLM tried to inject `import os`, `subprocess.run`, or `eval()`, the patch is instantly rejected without execution.
2. **Subprocess Isolation**: The patch is saved to a temporary file and executed in a constrained `subprocess` with a strict time limit (to prevent infinite loops or DoS attacks).

## 4. Regression Verification
A patch is only accepted if it achieves **100% regression verification**. This means the patched code must pass not only the scenario it originally failed, but *all 30+ other regression scenarios* across normal, boundary, and adversarial test cases.

## 5. Rollback
If the patched code fails regression or fails to agree with the Oracle, Auditra performs an immediate, file-level rollback to the last known secure state.

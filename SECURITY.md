# Security Policy

## Reporting a Vulnerability
Security vulnerabilities should **NOT** be disclosed through public GitHub issues.

Please direct all vulnerability reports to the repository maintainer:
Sriharsha Telikicherla

## Security Model
Auditra operates under a strict trust boundary:
- **AI-generated patches are inherently untrusted.**
- The deterministic verification Oracle serves as the ultimate authority for behavioral correctness.
- The global release gate blocks deployment unless the required behavioral verification and security checks pass.
- The AI repair agent cannot modify the Oracle or invariant logic through the MCP interface; it strictly consumes verification feedback.

## Execution Sandbox
Auditra evaluates untrusted AI code within a lightweight local sandbox implemented in Python. The current sandbox provides:
- An isolated temporary execution workspace
- Subprocess execution isolation
- A restricted environment (stripped variables)
- Output size limits to prevent memory exhaustion
- Strict execution timeouts
- OS-level resource limits (where supported, e.g., on Linux/macOS)
- Network restriction via a python-level socket monkeypatch

**This sandbox is not a hardened VM or container security boundary.** 

It is intended strictly as a practical demonstration and development isolation mechanism. It should **NOT** be treated as protection against a sophisticated attacker executing malicious code with local privilege escalation capabilities.

## Verification Scope
Auditra verifies target service behavior strictly against its explicitly defined scenarios and independent Oracle logic. 

Passing verification does **NOT** constitute a mathematical proof of arbitrary program correctness, memory safety, or absolute security. It only guarantees that the code conforms to the specific behaviors modeled by the Oracle.

## MCP Integration
IBM Bob (or any compatible AI agent) interfaces with Auditra via the Model Context Protocol (MCP) server. 
The agent can autonomously invoke:
- `verify_target`
- `verify_all`

The MCP interface exposes verification operations without exposing direct modification of the Oracle, invariants, or sandbox constraints.

## Security Limitations
Important known limitations of the Auditra verification engine include:
- The sandbox is lightweight and does not provide the robust isolation of a hardened VM or container boundary.
- Verification coverage is entirely dependent on the completeness of the defined scenarios and Oracle logic.
- Passing the current verification suite does not guarantee the complete absence of all vulnerabilities.
- Resource isolation features rely on OS-level capabilities and have notable limitations on Windows compared to Linux/macOS.

## Relevant Implementation References
- [`backend/auditra/sandbox.py`](backend/auditra/sandbox.py)
- [`mcp_server/server.py`](mcp_server/server.py)
- [`README.md`](README.md)
- [`docs/bob-usage.md`](docs/bob-usage.md)

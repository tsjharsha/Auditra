# Contributing to Auditra

Thank you for your interest in contributing to Auditra! 

## Development Setup

To set up your local development environment:
1. Clone the repository.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows: .venv\Scripts\activate
   # On Linux/macOS: source .venv/bin/activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: The project dependencies are defined in `pyproject.toml` and `requirements.txt`.)*
4. Do **not** commit your local `.env` file (if you create one).
5. Do **not** commit the `.venv` directory, `.bob/artifacts/`, `scratch/`, or `action_log.txt` to version control. They are explicitly excluded in `.gitignore`.

## Project Structure

Familiarize yourself with the core architecture of the repository:
- `backend/target_templates/`: Contains the target microservices meant for testing/patching.
- `backend/auditra/`: Core engine for verification, sandbox execution, and mutation testing.
- `mcp_server/`: Source code exposing the Auditra verification toolset via the Model Context Protocol (MCP).
- `.bob/mcp.json`: The cross-platform configuration for IBM Bob's MCP integration.
- `.github/workflows/test.yml`: The CI pipeline definition.
- `docs/bob-usage.md`: Documentation for using Auditra alongside IBM Bob.

## Adding or Modifying a Target

When implementing new functionality or modifying targets, please follow the expected workflow:
- **Target Implementation**: Code goes into the target files (e.g., in `backend/target_templates/`).
- **Deterministic Oracle/Invariants**: Must accurately capture the expected behavior of the target. **The Oracle must remain strictly independent from the implementation being tested.**
- **Adversarial Scenarios**: Define rigorous test inputs targeting edge cases, boundaries, and adversarial vectors.
- **Verification**: Run `python -m backend.auditra verify --json` to prove the target implementations against the Oracle.
- **Mutation Testing**: Ensure your target changes do not break the mutation test suite (which dynamically alters code to verify the Oracle's strictness).

## Testing Requirements

Before submitting any changes, contributors must run the project's existing verification and test workflows. 

Your PR will be checked against the existing CI procedure defined in `.github/workflows/test.yml`. This workflow runs code linting (Ruff), behavioral verification (with failures expected on vulnerable targets and successes on patched targets), and mutation testing.

## Sandbox Boundary

Code intended for verification must remain within Auditra's existing sandbox boundary. 

*Note: The current sandbox is a lightweight local execution isolation mechanism designed for demonstration workloads. It is not a hardened security boundary (VM/container) and should be respected as a practical constraint rather than absolute protection against sophisticated attacks.*

## MCP / IBM Bob

The `mcp_server/server.py` file exposes Auditra's core verification tools (`verify_target` and `verify_all`) via MCP, and `.bob/mcp.json` automatically configures the IBM Bob integration.

**Preserve the Trust Boundary:** Contributors modifying the MCP server must ensure that AI agents can only request verification feedback. The MCP interface must never grant direct modification of the Oracle, invariants, or sandbox constraints.

## Pull Requests

When opening a Pull Request, please ensure you:
- Clearly explain what changed and why.
- Explain how the change was tested locally.
- Preserve the independent verification model of the Oracle.
- Do **not** commit API secrets, `.env` files, or generated artifacts (`scratch/`, `.bob/artifacts/`, etc.).

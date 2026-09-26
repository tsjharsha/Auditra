#!/usr/bin/env python
"""
Auditra MCP Server
==================
Exposes Auditra's existing independent verification pipeline as MCP tools
that an AI agent (e.g. IBM Bob) can call.

Trust boundary: this server is the *integration layer only*.
- It calls into backend.auditra.verification_api for all verification logic.
- It does NOT duplicate or modify any oracle, sandbox, or target logic.
- The caller can trigger verification and read results; it cannot modify
  oracles, invariants, templates, or the release gate.
"""
import asyncio
import sys
from pathlib import Path

# Ensure the project root is on sys.path so backend.auditra imports work
# regardless of where the interpreter is launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer

# ---------------------------------------------------------------------------
# Import Auditra's existing verification entry points (read-only use)
# ---------------------------------------------------------------------------
from backend.auditra.verification_api import (
    TARGETS,
    VERIFICATION_NODES,
    run_mutation_suite,
    verify_node,
)

mcp = MCPServer(
    name="auditra-verification",
    title="Auditra Verification Oracle",
    description=(
        "Zero-Trust Verification Fabric for AI-Generated Software. "
        "Exposes Auditra's independent deterministic oracle as callable MCP tools. "
        "The oracle cannot be modified via this interface."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Tool: verify_target
# ---------------------------------------------------------------------------

_VALID_NODES = list(TARGETS.keys())  # ["tax_router", "billing_engine", "ledger_sync", "fraud_detector"]


@mcp.tool(
    name="verify_target",
    description=(
        "Run Auditra's independent oracle verification against a single target service node. "
        "Returns a structured result including verification status, test metrics, "
        "per-scenario details, and a release decision. "
        f"Valid node names: {', '.join(_VALID_NODES)}."
    ),
)
async def verify_target(node_name: str) -> dict:
    """
    Parameters
    ----------
    node_name : str
        One of: tax_router, billing_engine, ledger_sync, fraud_detector
    """
    if node_name not in TARGETS:
        return {
            "error": f"Unknown node '{node_name}'. Valid nodes: {_VALID_NODES}",
            "release_decision": "BLOCKED",
        }

    node = next((n for n in VERIFICATION_NODES if n["id"] == node_name), None)
    if node is None:
        return {
            "error": f"Verification node definition missing for '{node_name}'.",
            "release_decision": "BLOCKED",
        }

    target_path = TARGETS[node_name]
    # verify_node is synchronous — run it in a thread so we don't block the event loop
    result = await asyncio.get_running_loop().run_in_executor(
        None, verify_node, node, target_path
    )

    metrics = result.get("metrics", {})
    failures = result.get("failures", [])
    verified = result.get("status") == "verified"

    return {
        "node": node_name,
        "verification_status": "VERIFIED" if verified else "FAILED",
        "total_tests": metrics.get("total", 0),
        "passed_tests": metrics.get("passed", 0),
        "failed_tests": metrics.get("failed", 0),
        "oracle_agreement": metrics.get("oracle_agreement", "0.0%"),
        "failures": failures,
        "release_decision": "APPROVED" if verified else "BLOCKED",
    }


# ---------------------------------------------------------------------------
# Tool: verify_all
# ---------------------------------------------------------------------------


@mcp.tool(
    name="verify_all",
    description=(
        "Run Auditra's independent oracle verification against all four target service nodes "
        "(tax_router, billing_engine, ledger_sync, fraud_detector) and the mutation test suite. "
        "Returns a per-node breakdown and an overall release decision."
    ),
)
async def verify_all() -> dict:
    node_results = {}
    all_verified = True

    for node in VERIFICATION_NODES:
        node_id = node["id"]
        target_path = TARGETS.get(node_id)
        if not target_path:
            continue

        result = await asyncio.get_running_loop().run_in_executor(
            None, verify_node, node, target_path
        )
        metrics = result.get("metrics", {})
        failures = result.get("failures", [])
        verified = result.get("status") == "verified"
        if not verified:
            all_verified = False

        node_results[node_id] = {
            "node": node_id,
            "verification_status": "VERIFIED" if verified else "FAILED",
            "total_tests": metrics.get("total", 0),
            "passed_tests": metrics.get("passed", 0),
            "failed_tests": metrics.get("failed", 0),
            "oracle_agreement": metrics.get("oracle_agreement", "0.0%"),
            "failures": failures,
            "release_decision": "APPROVED" if verified else "BLOCKED",
        }

    mutation_results = await asyncio.get_running_loop().run_in_executor(
        None, run_mutation_suite
    )
    detected = sum(1 for r in mutation_results if r["detected"])
    total_mutations = len(mutation_results)
    mutation_score = f"{int((detected / total_mutations) * 100)}%" if total_mutations else "0%"

    return {
        "nodes": node_results,
        "mutation_testing": {
            "score": mutation_score,
            "detected": detected,
            "total": total_mutations,
        },
        "overall_release_decision": "APPROVED" if all_verified else "BLOCKED",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())

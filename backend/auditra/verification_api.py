"""
Server-Sent Events endpoint for the Verification War Room.
Streams real-time events as the Autonomous Red-Team Loop executes.
"""
import json
import time
import importlib
import importlib.util
import sys
import random
import logging
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["verification"])

# ──────────────────────────────────────────────────────────────
# Deterministic Oracle (inline for SSE isolation)
# ──────────────────────────────────────────────────────────────

class _Oracle:
    domestic_rate = Decimal("0.02")
    international_rate = Decimal("0.03")
    gst_rate = Decimal("0.18")

    def expected(self, amount_str: str, is_international: bool) -> Dict[str, str]:
        amount = Decimal(amount_str)
        rate = self.international_rate if is_international else self.domestic_rate
        fee = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        gst = (fee * self.gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        settlement = amount - fee - gst
        return {"amount": str(amount), "fee": str(fee), "gst": str(gst), "settlement": str(settlement)}


def _load_billing_engine(path: str):
    spec = importlib.util.spec_from_file_location("billing_engine_live", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BillingEngine()


def _generate_scenarios(count: int, seed: int = 42) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    scenarios = []
    for i in range(count):
        is_intl = rng.choice([True, False])
        roll = rng.random()
        if roll < 0.10:
            amt = round(rng.uniform(0.01, 1.99), 2)
        elif roll < 0.20:
            amt = round(rng.uniform(100000.0, 999999.99), 2)
        else:
            amt = round(rng.uniform(10.0, 5000.0), 2)
        scenarios.append({"tx_id": f"tx_sim_{i:06d}", "amount_str": str(amt), "is_international": is_intl})
    return scenarios


TARGET_PATH = str(Path(__file__).resolve().parent.parent / "target_service" / "billing_engine.py")

# ──────────────────────────────────────────────────────────────
# Simulated IBM Bob 2.0 Agent patch generation
# ──────────────────────────────────────────────────────────────

def _generate_patch(source: str, failure: Dict[str, Any]) -> str:
    """Simulate IBM Bob 2.0 reading the failure fingerprint and producing a code fix."""
    if "gst" in str(failure.get("variances", {})):
        return source.replace(
            'gst = Decimal("0.00") # Hallucinated or missed logic',
            'gst = (fee * self.gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)',
        )
    return source


# ──────────────────────────────────────────────────────────────
# SSE streaming endpoint
# ──────────────────────────────────────────────────────────────

def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _run_loop_generator(scenario_count: int, seed: int):
    """Synchronous generator that yields SSE strings."""
    oracle = _Oracle()
    max_iterations = 5

    # Step 0 — Read source
    with open(TARGET_PATH, "r", encoding="utf-8") as f:
        source_code = f.read()
    yield _sse("source", {"code": source_code, "path": TARGET_PATH})

    for iteration in range(1, max_iterations + 1):
        yield _sse("iteration_start", {"iteration": iteration})

        engine = _load_billing_engine(TARGET_PATH)
        scenarios = _generate_scenarios(scenario_count, seed=seed + iteration)

        passed = 0
        failure_info = None

        for sc in scenarios:
            target_out = engine.calculate_settlement(sc["amount_str"], sc["is_international"])
            oracle_out = oracle.expected(sc["amount_str"], sc["is_international"])

            variances = {}
            for key in ("amount", "fee", "gst", "settlement"):
                if target_out.get(key) != oracle_out.get(key):
                    variances[key] = {"expected": oracle_out[key], "actual": target_out[key]}

            if variances:
                failure_info = {
                    "failed_scenario": sc,
                    "target_output": target_out,
                    "expected_output": oracle_out,
                    "variances": variances,
                    "passed_before_fail": passed,
                }
                yield _sse("variance_detected", failure_info)
                break

            passed += 1
            # Stream progress every 50 transactions
            if passed % 50 == 0:
                yield _sse("progress", {"passed": passed, "total": scenario_count, "iteration": iteration})

        if failure_info is None:
            # All passed!
            yield _sse("iteration_passed", {"iteration": iteration, "passed": passed, "total": scenario_count})
            yield _sse("certificate", {
                "status": "VERIFIED",
                "iterations": iteration,
                "scenarios_passed": passed,
                "seal": "CRYPTOGRAPHIC_ORACLE_SEAL_OF_APPROVAL",
            })

            with open(TARGET_PATH, "r", encoding="utf-8") as f:
                final_code = f.read()
            yield _sse("final_source", {"code": final_code})
            return

        # Failure path — ask Bob 2.0 for a fix
        yield _sse("prompting_ai", {"iteration": iteration, "variance": failure_info["variances"]})
        time.sleep(0.8)  # Simulate thinking time for dramatic effect

        with open(TARGET_PATH, "r", encoding="utf-8") as f:
            current_source = f.read()
        patched = _generate_patch(current_source, failure_info)

        with open(TARGET_PATH, "w", encoding="utf-8") as f:
            f.write(patched)

        yield _sse("patch_applied", {"iteration": iteration, "new_code": patched})
        time.sleep(0.3)

    # If we exhaust iterations
    yield _sse("failed", {"message": "Max iterations reached without full verification."})


@router.get("/stream")
def verification_stream(scenarios: int = 1000, seed: int = 42):
    """
    SSE endpoint that streams the Autonomous Red-Team Verification Loop in real-time.
    The frontend connects and receives events as the loop executes.
    """
    return StreamingResponse(
        _run_loop_generator(scenarios, seed),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/source")
def get_target_source():
    """Returns the current target service source code."""
    with open(TARGET_PATH, "r", encoding="utf-8") as f:
        return {"code": f.read(), "path": TARGET_PATH}


@router.post("/reset")
def reset_target_source():
    """Resets the billing engine to its original buggy state for re-demo."""
    buggy_code = '''from decimal import Decimal, ROUND_HALF_UP

class BillingEngine:
    """
    Simulated IBM Bob 2.0 Generated Code
    This microservice calculates fees, GST, and settlement for a given payment.
    """
    def __init__(self):
        self.domestic_rate = Decimal("0.02")      # 2% fee
        self.international_rate = Decimal("0.03") # 3% fee
        self.gst_rate = Decimal("0.18")           # 18% GST on fees

    def calculate_settlement(self, amount_str: str, is_international: bool) -> dict:
        amount = Decimal(amount_str)
        
        if is_international:
            # BUG: Missing GST deduction for international payments
            fee = (amount * self.international_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gst = Decimal("0.00") # Hallucinated or missed logic
            settlement = amount - fee - gst
        else:
            fee = (amount * self.domestic_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gst = (fee * self.gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            settlement = amount - fee - gst
            
        return {
            "amount": str(amount),
            "fee": str(fee),
            "gst": str(gst),
            "settlement": str(settlement)
        }
'''
    with open(TARGET_PATH, "w", encoding="utf-8") as f:
        f.write(buggy_code)
    return {"status": "reset", "code": buggy_code}

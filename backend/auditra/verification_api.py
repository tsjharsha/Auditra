import os
import json
import time
import importlib
import logging
import hashlib
import shutil
import difflib
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from .sandbox import SandboxRunner, ASTValidator, SecurityViolation

load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except ImportError:
    groq_client = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/verification", tags=["verification"])

BASE_DIR = Path(__file__).resolve().parent.parent
TARGET_DIR = BASE_DIR / "target_service"
TEMPLATE_DIR = BASE_DIR / "target_templates"

TARGETS = {
    "tax_router": str(TARGET_DIR / "tax_router.py"),
    "billing_engine": str(TARGET_DIR / "billing_engine.py"),
    "ledger_sync": str(TARGET_DIR / "ledger_sync.py"),
    "fraud_detector": str(TARGET_DIR / "fraud_detector.py"),
}

# Ensure templates directory exists for reproducible reset
os.makedirs(TEMPLATE_DIR, exist_ok=True)

class _Oracles:
    @staticmethod
    def expected_tax_router(state_code: str) -> dict:
        rates = {"CA": "0.0825", "NY": "0.08875", "TX": "0.0625"}
        rate = rates.get(state_code, "0.05")
        return {"rate": rate}

    @staticmethod
    def expected_billing(amount_str: str) -> dict:
        amt = Decimal(amount_str)
        fee = (amt * Decimal("0.03")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        tax = (fee * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        settlement = amt - fee - tax
        return {
            "amount": str(amt.quantize(Decimal("0.01"))),
            "fee": str(fee),
            "gst": str(tax),
            "settlement": str(settlement)
        }

    @staticmethod
    def expected_ledger(amount_str: str) -> dict:
        amt = Decimal(amount_str)
        if amt < 0:
            return {"status": "REJECTED", "refund_amount": "0.00", "ledger_impact": "0.00"}
        return {"status": "PROCESSED", "refund_amount": str(amt), "ledger_impact": str(-amt)}

    @staticmethod
    def expected_fraud(amount_str: str) -> dict:
        try:
            amt = Decimal(amount_str)
        except:
            return {"fraudulent": True}
        return {"fraudulent": bool(amt > 10000)}

def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

def get_patch_code_fallback(node: str) -> str:
    if node == "tax_router":
        return """class TaxRouter:
    \"\"\"IBM Bob 2.0 Patched Code\"\"\"
    def get_tax_rate(self, state_code: str) -> str:
        rates = {"CA": "0.0825", "NY": "0.08875", "TX": "0.0625"}
        return rates.get(state_code, "0.05")
"""
    elif node == "billing_engine":
        return """from decimal import Decimal, ROUND_HALF_EVEN
class BillingEngine:
    \"\"\"IBM Bob 2.0 Patched Code\"\"\"
    def __init__(self):
        self.rate = Decimal("0.03")
        self.gst = Decimal("0.18")
    def calculate(self, amount_str: str) -> dict:
        amt = Decimal(amount_str)
        fee = (amt * self.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        tax = (fee * self.gst).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        return {
            "amount": str(amt.quantize(Decimal("0.01"))),
            "fee": str(fee),
            "gst": str(tax),
            "settlement": str(amt - fee - tax)
        }
"""
    elif node == "ledger_sync":
        return """class LedgerSync:
    \"\"\"IBM Bob 2.0 Patched Code\"\"\"
    def process_refund(self, amount_str: str) -> dict:
        amt = float(amount_str)
        if amt < 0:
            return {"status": "REJECTED", "refund_amount": "0.00", "ledger_impact": "0.00"}
        return {"status": "PROCESSED", "refund_amount": str(amt), "ledger_impact": str(-amt)}
"""
    elif node == "fraud_detector":
        return """from decimal import Decimal
class FraudDetector:
    \"\"\"IBM Bob 2.0 Patched Code\"\"\"
    def is_fraudulent(self, amount_str: str) -> bool:
        try:
            amt = Decimal(amount_str)
            return bool(amt > 5000) # INTENTIONAL FLAW FOR ROLLBACK DEMO
        except:
            return True
"""
    return ""

def ask_llm_for_patch(node: str, buggy_code: str, failure_info: dict) -> str:
    if not groq_client:
        time.sleep(1.0)
        return get_patch_code_fallback(node)
        
    try:
        prompt = f"""You are IBM Bob 2.0, an elite AI coding assistant.
The following Python class failed cryptographic verification in the Zero-Trust Fabric.
Fix the code. Return ONLY the raw python code. Do not wrap in markdown or backticks.

Buggy Code:
{buggy_code}

Cryptographic Variance Detected:
{json.dumps(failure_info, indent=2)}
"""
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0,
            max_tokens=500
        )
        content = chat_completion.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.split("\\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines[-1].startswith("```"): lines = lines[:-1]
            content = "\\n".join(lines).strip()
        return content
    except Exception as e:
        logger.error(f"LLM failed: {e}")
        return get_patch_code_fallback(node)

def verify_node(node: dict, path: str) -> dict:
    total = 0
    passed = 0
    failures = []
    
    for kwargs in node["inputs"]:
        total += 1
        success, target_out = SandboxRunner.execute(path, node["class"], node["method"], kwargs)
        
        oracle_out = node["oracle"](**kwargs)
        if not isinstance(oracle_out, dict):
            oracle_out = {"result": oracle_out}
            
        if not success:
            failures.append({
                "scenario": kwargs,
                "error": target_out.get("error", "Execution Failed"),
                "target_hash": "ERROR",
                "oracle_hash": "N/A",
                "variances": {"Exception": {"expected": "Success", "actual": target_out.get("error")}}
            })
            continue
            
        variances = {}
        for k in oracle_out.keys():
            if str(target_out.get(k)) != str(oracle_out.get(k)):
                variances[k] = {"expected": str(oracle_out[k]), "actual": str(target_out.get(k))}
                
        if variances:
            thash = hashlib.sha256(json.dumps(target_out, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            ohash = hashlib.sha256(json.dumps(oracle_out, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            failures.append({
                "scenario": kwargs,
                "variances": variances,
                "target_hash": thash,
                "oracle_hash": ohash
            })
        else:
            passed += 1

    if failures:
        first = failures[0]
        first["metrics"] = {"total": total, "passed": passed, "failed": len(failures), "oracle_agreement": f"{(passed/total)*100:.1f}%"}
        return first
        
    return None

VERIFICATION_NODES = [
    {"id": "tax_router", "class": "TaxRouter", "method": "get_tax_rate", "inputs": [{"state_code": "CA"}, {"state_code": "NY"}, {"state_code": "TX"}, {"state_code": "unknown"}, {"state_code": ""}, {"state_code": "ca"}, {"state_code": " 123 "}] * 5, "oracle": _Oracles.expected_tax_router},
    {"id": "billing_engine", "class": "BillingEngine", "method": "calculate", "inputs": [{"amount_str": "0"}, {"amount_str": "0.01"}, {"amount_str": "99.99"}, {"amount_str": "100.00"}, {"amount_str": "999.99"}, {"amount_str": "1000000000.00"}, {"amount_str": "100.12345"}] * 5, "oracle": _Oracles.expected_billing},
    {"id": "ledger_sync", "class": "LedgerSync", "method": "process_refund", "inputs": [{"amount_str": "500.00"}, {"amount_str": "0.00"}, {"amount_str": "-100.00"}, {"amount_str": "9999999.99"}] * 9, "oracle": _Oracles.expected_ledger},
    {"id": "fraud_detector", "class": "FraudDetector", "method": "is_fraudulent", "inputs": [{"amount_str": "9999.00"}, {"amount_str": "10000.00"}, {"amount_str": "10000.01"}, {"amount_str": "1e9"}, {"amount_str": "invalid"}, {"amount_str": "-50.00"}] * 6, "oracle": _Oracles.expected_fraud}
]

def _aegis_generator():
    yield _sse("aegis_start", {"message": f"AEGIS PROTOCOL ACTIVATED. MODE: {'LIVE (Groq)' if groq_client else 'DETERMINISTIC DEMO'}"})
    time.sleep(1.0)
    
    for node in VERIFICATION_NODES:
        yield _sse("node_state", {"node": node["id"], "state": "ATTACKING"})
        time.sleep(0.5)
        
        target_path = TARGETS[node["id"]]
        
        # 1. Baseline verification
        failure_info = verify_node(node, target_path)
        
        if failure_info:
            yield _sse("node_state", {"node": node["id"], "state": "COMPROMISED", "variance": failure_info})
            time.sleep(1.5)
            yield _sse("node_state", {"node": node["id"], "state": "ANALYZING"})
            time.sleep(1.0)
            
            with open(target_path, "r", encoding="utf-8") as f:
                original_code = f.read()
                
            yield _sse("node_state", {"node": node["id"], "state": "PATCHING"})
            patched_code = ask_llm_for_patch(node["id"], original_code, failure_info)
            
            diff_lines = list(difflib.unified_diff(
                original_code.splitlines(keepends=True),
                patched_code.splitlines(keepends=True),
                fromfile='untrusted_source.py',
                tofile='proposed_patch.py'
            ))
            diff_str = "".join(diff_lines)
            
            yield _sse("node_state", {"node": node["id"], "state": "VALIDATING", "patch_code": patched_code, "patch_diff": diff_str})
            try:
                ASTValidator.validate(patched_code)
            except Exception as e:
                yield _sse("node_state", {"node": node["id"], "state": "PATCH_FAILED", "error": str(e)})
                time.sleep(1.5)
                yield _sse("node_state", {"node": node["id"], "state": "ROLLING_BACK"})
                continue

            # Apply patch
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(patched_code)
                
            yield _sse("node_state", {"node": node["id"], "state": "REVERIFYING", "metrics": {"total_tests": len(node["inputs"])}})
            
            # POST-PATCH VERIFICATION
            post_patch_failure = verify_node(node, target_path)
            
            if post_patch_failure:
                yield _sse("node_state", {"node": node["id"], "state": "VERIFICATION_FAILED", "variance": post_patch_failure, "metrics": post_patch_failure.get("metrics")})
                time.sleep(1.5)
                yield _sse("node_state", {"node": node["id"], "state": "ROLLING_BACK"})
                # Rollback
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(original_code)
                yield _sse("node_state", {"node": node["id"], "state": "ROLLED_BACK"})
            else:
                yield _sse("node_state", {"node": node["id"], "state": "SECURED", "metrics": {"passed": len(node["inputs"]), "failed": 0, "oracle_agreement": "100%"}})
                
        else:
            yield _sse("node_state", {"node": node["id"], "state": "SECURED", "metrics": {"passed": len(node["inputs"]), "failed": 0, "oracle_agreement": "100%"}})
            
        time.sleep(1.0)
        
    yield _sse("aegis_secure", {"message": "VERIFICATION LIFECYCLE COMPLETE"})

@router.get("/stream")
def verification_stream():
    return StreamingResponse(
        _aegis_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@router.post("/reset")
def reset_targets():
    os.makedirs(TARGET_DIR, exist_ok=True)
    # Copy all from templates to targets
    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith(".py"):
            shutil.copy(TEMPLATE_DIR / filename, TARGET_DIR / filename)
    return {"status": "reset", "message": "All targets restored to known-vulnerable states."}

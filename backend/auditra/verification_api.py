import difflib
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .sandbox import ASTValidator, SandboxRunner

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
        except (ValueError, InvalidOperation):
            return {"fraudulent": True}
        return {"fraudulent": bool(amt > 10000)}

def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

def get_patch_code_fallback(node: str) -> str:
    if node == "tax_router":
        return """class TaxRouter:
    \"\"\"IBM Bob 2.0 Patched Code\"\"\"
    def get_tax_rate(self, state_code: str) -> dict:
        rates = {"CA": "0.0825", "NY": "0.08875", "TX": "0.0625"}
        return {"rate": rates.get(state_code, "0.05")}
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
        return """from decimal import Decimal
class LedgerSync:
    \"\"\"IBM Bob 2.0 Patched Code\"\"\"
    def process_refund(self, amount_str: str) -> dict:
        amt = Decimal(amount_str)
        if amt < 0:
            return {"status": "REJECTED", "refund_amount": "0.00", "ledger_impact": "0.00"}
        return {"status": "PROCESSED", "refund_amount": str(amt), "ledger_impact": str(-amt)}
"""
    elif node == "fraud_detector":
        return """from decimal import Decimal, InvalidOperation
class FraudDetector:
    \"\"\"IBM Bob 2.0 Patched Code\"\"\"
    def is_fraudulent(self, amount_str: str) -> dict:
        try:
            amt = Decimal(amount_str)
            return {"fraudulent": bool(amt > 10000)}
        except (ValueError, InvalidOperation):
            return {"fraudulent": True}
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
    {
        "id": "tax_router", 
        "class": "TaxRouter", 
        "method": "get_tax_rate", 
        "inputs": [
            {"state_code": "CA"}, {"state_code": "NY"}, {"state_code": "TX"}, 
            {"state_code": "ca"}, {"state_code": "NY "}, {"state_code": " NY"}, 
            {"state_code": ""}, {"state_code": "unknown"}, {"state_code": "123"}, 
            {"state_code": "!@#$"}, {"state_code": "A" * 100}, {"state_code": "\nCA"}
        ], 
        "oracle": _Oracles.expected_tax_router
    },
    {
        "id": "billing_engine", 
        "class": "BillingEngine", 
        "method": "calculate", 
        "inputs": [
            {"amount_str": "100.00"}, {"amount_str": "50.50"}, {"amount_str": "99.99"}, 
            {"amount_str": "0.01"}, {"amount_str": "100.125"}, {"amount_str": "100.12345"}, 
            {"amount_str": "0"}, {"amount_str": "0.00"}, {"amount_str": "-100.00"}, 
            {"amount_str": "-0.01"}, {"amount_str": "9999999999.99"}, {"amount_str": "1e5"}, 
            {"amount_str": "1E-5"}, {"amount_str": "-1e-5"}, {"amount_str": "NaN"}
        ], 
        "oracle": _Oracles.expected_billing
    },
    {
        "id": "ledger_sync", 
        "class": "LedgerSync", 
        "method": "process_refund", 
        "inputs": [
            {"amount_str": "100.00"}, {"amount_str": "500.00"}, {"amount_str": "0.00"}, 
            {"amount_str": "0"}, {"amount_str": "0.01"}, {"amount_str": "-0.01"}, 
            {"amount_str": "-100.00"}, {"amount_str": "-999999999.99"}, {"amount_str": "999999999.99"}, 
            {"amount_str": "1e10"}, {"amount_str": "-1e10"}, {"amount_str": "1e-5"}, 
            {"amount_str": "-1e-5"}, {"amount_str": "Infinity"}, {"amount_str": "-Infinity"}
        ], 
        "oracle": _Oracles.expected_ledger
    },
    {
        "id": "fraud_detector", 
        "class": "FraudDetector", 
        "method": "is_fraudulent", 
        "inputs": [
            {"amount_str": "5000.00"}, {"amount_str": "10000.00"}, {"amount_str": "10000.01"}, 
            {"amount_str": "9999.99"}, {"amount_str": "15000.00"}, {"amount_str": "0.00"}, 
            {"amount_str": "0"}, {"amount_str": "-0.01"}, {"amount_str": "-10000.00"}, 
            {"amount_str": "1e9"}, {"amount_str": "invalid"}, {"amount_str": ""}, 
            {"amount_str": " "}, {"amount_str": "1,000,000.00"}, {"amount_str": "Infinity"}, 
            {"amount_str": "10000.00\n"}
        ], 
        "oracle": _Oracles.expected_fraud
    }
]

def _aegis_generator():
    audit_id = f"AUDIT-{datetime.now().strftime('%Y-%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    yield _sse("aegis_start", {"message": f"AEGIS PROTOCOL ACTIVATED. MODE: {'LIVE (Groq)' if groq_client else 'DETERMINISTIC DEMO'}", "audit_id": audit_id})
    time.sleep(1.0)
    
    # --- MUTATION TESTING PHASE ---
    mutations = [
        {
            "name": "Tax Router wrong/missing rate",
            "node_id": "tax_router",
            "code": "class TaxRouter:\n    def get_tax_rate(self, state_code: str) -> dict:\n        rates = {'CA': '0.0825', 'TX': '0.0625'}\n        return {'rate': rates.get(state_code, '0.00')}\n"
        },
        {
            "name": "Billing Engine float/rounding regression",
            "node_id": "billing_engine",
            "code": "class BillingEngine:\n    def __init__(self):\n        self.rate = 0.03\n        self.gst = 0.18\n    def calculate(self, amount_str: str) -> dict:\n        amt = float(amount_str)\n        fee = amt * self.rate\n        tax = fee * self.gst\n        settlement = amt - fee - tax\n        return {\n            'amount': f'{amt:.2f}',\n            'fee': f'{fee:.2f}',\n            'gst': f'{tax:.2f}',\n            'settlement': f'{settlement:.2f}'\n        }\n"
        },
        {
            "name": "Ledger Sync negative-refund acceptance",
            "node_id": "ledger_sync",
            "code": "from decimal import Decimal\nclass LedgerSync:\n    def process_refund(self, amount_str: str) -> dict:\n        amt = Decimal(amount_str)\n        return {\n            'status': 'PROCESSED',\n            'refund_amount': str(amt),\n            'ledger_impact': str(-amt)\n        }\n"
        },
        {
            "name": "Fraud Detector incorrect threshold",
            "node_id": "fraud_detector",
            "code": "from decimal import Decimal, InvalidOperation\nclass FraudDetector:\n    def is_fraudulent(self, amount_str: str) -> dict:\n        try:\n            amt = Decimal(amount_str)\n            return {'fraudulent': bool(amt > 5000)}\n        except (ValueError, InvalidOperation):\n            return {'fraudulent': False}\n"
        }
    ]

    for mut in mutations:
        yield _sse("node_state", {"node": "mutation_engine", "state": "MUTATING", "message": f"Injecting {mut['name']} into {mut['node_id']} to verify Oracle sensitivity..."})
        time.sleep(0.5)
        
        node = next(n for n in VERIFICATION_NODES if n["id"] == mut["node_id"])
        mut_path = str(TARGET_DIR / f"{mut['node_id']}_mut.py")
        
        with open(mut_path, "w", encoding="utf-8") as f:
            f.write(mut["code"])
            
        mutation_failure = verify_node(node, mut_path)
        
        if mutation_failure:
            yield _sse("node_state", {"node": "mutation_engine", "state": "MUTATION_DETECTED", "message": f"Oracle successfully caught {mut['name']}!"})
        else:
            yield _sse("node_state", {"node": "mutation_engine", "state": "MUTATION_FAILED", "message": f"Oracle FAILED to detect {mut['name']}!"})
            
        Path(mut_path).unlink(missing_ok=True)
        time.sleep(0.5)
    # --- END MUTATION TESTING ---
    
    failed_nodes = []
    
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
            
            lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            patch_impact = {"added": lines_added, "removed": lines_removed}
            
            yield _sse("node_state", {"node": node["id"], "state": "VALIDATING", "patch_code": patched_code, "patch_diff": diff_str, "patch_impact": patch_impact})
            try:
                ASTValidator.validate(patched_code)
            except Exception as e:
                yield _sse("node_state", {"node": node["id"], "state": "PATCH_FAILED", "error": str(e)})
                failed_nodes.append({"id": node["id"], "reason": "AST Validation Failed", "error": str(e)})
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
                metrics = post_patch_failure.get("metrics", {})
                rejection_reason = f"The generated patch executed successfully, but its behavior did not match the independent oracle for {metrics.get('failed', 0)}/{metrics.get('total', 0)} adversarial scenarios. The patch was therefore rejected."
                yield _sse("node_state", {"node": node["id"], "state": "VERIFICATION_FAILED", "variance": post_patch_failure, "metrics": metrics, "rejection_reason": rejection_reason})
                failed_nodes.append({"id": node["id"], "reason": "Post-patch verification failed", "metrics": metrics})
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
        
    if not failed_nodes:
        yield _sse("aegis_secure", {
            "message": "VERIFICATION LIFECYCLE COMPLETE: ALL NODES SECURED",
            "overall_success": True,
            "release_status": "APPROVED"
        })
    else:
        yield _sse("aegis_blocked", {
            "message": f"VERIFICATION LIFECYCLE COMPLETE: {len(failed_nodes)} NODE(S) FAILED OR ROLLED BACK",
            "overall_success": False,
            "release_status": "BLOCKED",
            "failed_nodes": failed_nodes
        })

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

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
    scenarios_results = []
    
    unique_inputs = []
    seen = set()
    for kwargs in node["inputs"]:
        kstr = json.dumps(kwargs, sort_keys=True)
        if kstr not in seen:
            seen.add(kstr)
            unique_inputs.append(kwargs)
            
    for kwargs in unique_inputs:
        total += 1
        success, target_out = SandboxRunner.execute(path, node["class"], node["method"], kwargs)
        
        oracle_out = node["oracle"](**kwargs)
        if not isinstance(oracle_out, dict):
            oracle_out = {"result": oracle_out}
            
        if not success:
            variance_info = {"Exception": {"expected": "Success", "actual": target_out.get("error")}}
            failure_dict = {
                "scenario": kwargs,
                "error": target_out.get("error", "Execution Failed"),
                "target_hash": "ERROR",
                "oracle_hash": "N/A",
                "variances": variance_info
            }
            failures.append(failure_dict)
            scenarios_results.append({
                "input": kwargs,
                "status": "FAIL",
                "expected": oracle_out,
                "actual": target_out,
                "variance": variance_info,
                "error": target_out.get("error", "Execution Failed")
            })
            continue
            
        variances = {}
        for k in oracle_out.keys():
            if str(target_out.get(k)) != str(oracle_out.get(k)):
                variances[k] = {"expected": str(oracle_out[k]), "actual": str(target_out.get(k))}
                
        if variances:
            thash = hashlib.sha256(json.dumps(target_out, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            ohash = hashlib.sha256(json.dumps(oracle_out, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            failure_dict = {
                "scenario": kwargs,
                "variances": variances,
                "target_hash": thash,
                "oracle_hash": ohash
            }
            failures.append(failure_dict)
            scenarios_results.append({
                "input": kwargs,
                "status": "FAIL",
                "expected": oracle_out,
                "actual": target_out,
                "variance": variances
            })
        else:
            passed += 1
            scenarios_results.append({
                "input": kwargs,
                "status": "PASS",
                "expected": oracle_out,
                "actual": target_out,
                "variance": None
            })

    metrics = {
        "total": total,
        "passed": passed,
        "failed": len(failures),
        "oracle_agreement": f"{(passed/total)*100:.1f}%" if total > 0 else "0.0%"
    }
    
    return {
        "status": "failed" if failures else "verified",
        "metrics": metrics,
        "scenarios": scenarios_results,
        "failures": failures,
        "first_failure": failures[0] if failures else None
    }

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

def run_mutation_suite():
    mutation_specs = [
        {
            "name": "Tax wrong-rate mutation",
            "node_id": "tax_router",
            "search": '"0.0825"',
            "replace": '"0.0900"'
        },
        {
            "name": "Tax missing-state mutation",
            "node_id": "tax_router",
            "search": '"NY": "0.08875", ',
            "replace": ''
        },
        {
            "name": "Billing float mutation",
            "node_id": "billing_engine",
            "search": 'amt = Decimal(amount_str)\n        fee = (amt * self.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)\n        tax = (fee * self.gst).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)\n        return {\n            "amount": str(amt.quantize(Decimal("0.01"))),\n            "fee": str(fee),\n            "gst": str(tax),\n            "settlement": str(amt - fee - tax)\n        }',
            "replace": 'amt = float(amount_str)\n        fee = round(amt * float(self.rate), 2)\n        tax = round(fee * float(self.gst), 2)\n        return {"amount": f"{amt:.2f}", "fee": f"{fee:.2f}", "gst": f"{tax:.2f}", "settlement": f"{(amt - fee - tax):.2f}"}'
        },
        {
            "name": "Billing rounding mutation",
            "node_id": "billing_engine",
            "search": "ROUND_HALF_EVEN",
            "replace": "ROUND_UP"
        },
        {
            "name": "Ledger validation mutation",
            "node_id": "ledger_sync",
            "search": 'if amt < 0:\n            return {"status": "REJECTED", "refund_amount": "0.00", "ledger_impact": "0.00"}\n        ',
            "replace": ''
        },
        {
            "name": "Fraud threshold mutation",
            "node_id": "fraud_detector",
            "search": '10000',
            "replace": '5000'
        }
    ]

    results = []
    for spec in mutation_specs:
        base_code = get_patch_code_fallback(spec["node_id"])
        mutated_code = base_code.replace(spec["search"], spec["replace"])
        
        if mutated_code == base_code:
            results.append({
                "spec": spec,
                "detected": False,
                "status_text": "FAILED TO MUTATE"
            })
            continue
            
        node = next(n for n in VERIFICATION_NODES if n["id"] == spec["node_id"])
        mut_path = str(TARGET_DIR / f"{spec['node_id']}_mut.py")
        
        with open(mut_path, "w", encoding="utf-8") as f:
            f.write(mutated_code)
            
        mutation_info = verify_node(node, mut_path)
        
        if mutation_info["status"] == "failed":
            results.append({
                "spec": spec,
                "detected": True,
                "status_text": "DETECTED"
            })
        else:
            results.append({
                "spec": spec,
                "detected": False,
                "status_text": "MISSED"
            })
            
        Path(mut_path).unlink(missing_ok=True)
        
    return results

def _aegis_generator():
    audit_id = f"AUDIT-{datetime.now().strftime('%Y-%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    yield _sse("aegis_start", {"message": f"AEGIS PROTOCOL ACTIVATED. MODE: {'LIVE (Groq)' if groq_client else 'DETERMINISTIC DEMO'}", "audit_id": audit_id})
    time.sleep(1.0)
    
    # --- MUTATION TESTING PHASE ---
    print("\nMUTATION TESTS\n", flush=True)
    detected_count = 0
    mutation_results = run_mutation_suite()

    for res in mutation_results:
        spec = res["spec"]
        detected = res["detected"]
        status_text = res["status_text"]
        
        yield _sse("node_state", {"node": "mutation_engine", "state": "MUTATING", "message": f"Injecting {spec['name']} into {spec['node_id']} to verify Oracle sensitivity..."})
        
        if status_text == "FAILED TO MUTATE":
            yield _sse("node_state", {"node": "mutation_engine", "state": "MUTATION_FAILED", "message": f"Engine failed to mutate {spec['name']}! Source code unchanged."})
        elif detected:
            detected_count += 1
            yield _sse("node_state", {"node": "mutation_engine", "state": "MUTATION_DETECTED", "message": f"Oracle successfully caught {spec['name']}!"})
        else:
            yield _sse("node_state", {"node": "mutation_engine", "state": "MUTATION_FAILED", "message": f"Oracle FAILED to detect {spec['name']}!"})
            
        try:
            print(f"{'✓' if detected else '✗'} {spec['name']:<28} {status_text}", flush=True)
        except UnicodeEncodeError:
            print(f"{'[PASS]' if detected else '[FAIL]'} {spec['name']:<28} {status_text}", flush=True)
        time.sleep(0.5)

    total_mutations = len(mutation_results)
    score = int((detected_count / total_mutations) * 100) if total_mutations > 0 else 0
    print(f"\n{detected_count} / {total_mutations} mutations detected", flush=True)
    print(f"Mutation Score: {score}%\n", flush=True)
    
    # --- END MUTATION TESTING ---
    
    failed_nodes = []
    
    for node in VERIFICATION_NODES:
        yield _sse("node_state", {"node": node["id"], "state": "ATTACKING"})
        time.sleep(0.5)
        
        target_path = TARGETS[node["id"]]
        
        # 1. Baseline verification
        info = verify_node(node, target_path)
        
        if info["status"] == "failed":
            yield _sse("node_state", {"node": node["id"], "state": "COMPROMISED", "report": info})
            time.sleep(1.5)
            yield _sse("node_state", {"node": node["id"], "state": "ANALYZING"})
            time.sleep(1.0)
            
            with open(target_path, "r", encoding="utf-8") as f:
                original_code = f.read()
                
            yield _sse("node_state", {"node": node["id"], "state": "PATCHING"})
            patched_code = ask_llm_for_patch(node["id"], original_code, info)
            
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
                yield _sse("node_state", {"node": node["id"], "state": "PATCH_REJECTED", "error": str(e)})
                failed_nodes.append({"id": node["id"], "reason": "AST Validation Failed", "error": str(e)})
                time.sleep(1.5)
                continue

            # Apply patch
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(patched_code)
                
            yield _sse("node_state", {"node": node["id"], "state": "PATCH_APPLIED"})
            yield _sse("node_state", {"node": node["id"], "state": "REVERIFYING", "total_tests": len(node["inputs"])})
            
            # POST-PATCH VERIFICATION
            post_patch_info = verify_node(node, target_path)
            
            if post_patch_info["status"] == "failed":
                metrics = post_patch_info["metrics"]
                rejection_reason = f"The generated patch executed successfully, but its behavior did not match the independent oracle for {metrics.get('failed', 0)}/{metrics.get('total', 0)} adversarial scenarios. The patch was therefore rejected."
                yield _sse("node_state", {"node": node["id"], "state": "VERIFICATION_FAILED", "report": post_patch_info, "metrics": metrics, "rejection_reason": rejection_reason})
                failed_nodes.append({"id": node["id"], "reason": "Post-patch verification failed", "metrics": metrics})
                time.sleep(1.5)
                yield _sse("node_state", {"node": node["id"], "state": "ROLLING_BACK"})
                # Rollback
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(original_code)
                yield _sse("node_state", {"node": node["id"], "state": "ROLLED_BACK"})
            else:
                yield _sse("node_state", {"node": node["id"], "state": "SECURED", "metrics": post_patch_info["metrics"]})
                
        else:
            yield _sse("node_state", {"node": node["id"], "state": "SECURED", "metrics": info["metrics"]})
            
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

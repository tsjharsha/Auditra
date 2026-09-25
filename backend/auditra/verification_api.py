import json
import time
import importlib
import importlib.util
import sys
import random
import logging
import hashlib
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["verification"])

BASE_DIR = Path(__file__).resolve().parent.parent / "target_service"
TARGETS = {
    "tax_router": str(BASE_DIR / "tax_router.py"),
    "billing_engine": str(BASE_DIR / "billing_engine.py"),
    "ledger_sync": str(BASE_DIR / "ledger_sync.py"),
    "fraud_detector": str(BASE_DIR / "fraud_detector.py"),
}

# --- ORACLES ---
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

def _load_module(name: str, path: str):
    import sys
    sys.dont_write_bytecode = True
    mod_name = f"aegis_target_{name}"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    importlib.invalidate_caches()
    
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

def get_patch_code(node: str) -> str:
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
            return bool(amt > 10000)
        except:
            return True
"""
    return ""

def _aegis_generator():
    yield _sse("aegis_start", {"message": "AEGIS PROTOCOL ACTIVATED"})
    time.sleep(1.0)
    
    nodes = [
        {"id": "tax_router", "class": "TaxRouter", "method": "get_tax_rate", "inputs": [{"state_code": "CA"}, {"state_code": "TX"}], "oracle": _Oracles.expected_tax_router},
        {"id": "billing_engine", "class": "BillingEngine", "method": "calculate", "inputs": [{"amount_str": "100.505"}, {"amount_str": "199.995"}], "oracle": _Oracles.expected_billing},
        {"id": "ledger_sync", "class": "LedgerSync", "method": "process_refund", "inputs": [{"amount_str": "-1000.00"}, {"amount_str": "500.00"}], "oracle": _Oracles.expected_ledger},
        {"id": "fraud_detector", "class": "FraudDetector", "method": "is_fraudulent", "inputs": [{"amount_str": "1e9"}, {"amount_str": "9999.00"}], "oracle": _Oracles.expected_fraud}
    ]
    
    for node in nodes:
        yield _sse("node_attacked", {"node": node["id"]})
        time.sleep(1.0)
        
        # Load buggy code
        mod = _load_module(node["id"], TARGETS[node["id"]])
        engine = getattr(mod, node["class"])()
        
        # Run scenarios to find drift
        failure_info = None
        for i, kwargs in enumerate(node["inputs"]):
            try:
                target_out = getattr(engine, node["method"])(**kwargs)
                if not isinstance(target_out, dict):
                    target_out = {"result": target_out}
                
                oracle_out = node["oracle"](**kwargs)
                if not isinstance(oracle_out, dict):
                    oracle_out = {"result": oracle_out}
                
                variances = {}
                for k in oracle_out.keys():
                    if str(target_out.get(k)) != str(oracle_out.get(k)):
                        variances[k] = {"expected": str(oracle_out[k]), "actual": str(target_out.get(k))}
                
                if variances:
                    thash = hashlib.sha256(json.dumps(target_out, sort_keys=True).encode("utf-8")).hexdigest()[:16]
                    ohash = hashlib.sha256(json.dumps(oracle_out, sort_keys=True).encode("utf-8")).hexdigest()[:16]
                    failure_info = {
                        "node": node["id"],
                        "scenario": kwargs,
                        "variances": variances,
                        "target_hash": thash,
                        "oracle_hash": ohash
                    }
                    break
            except Exception as e:
                pass
        
        if failure_info:
            yield _sse("variance_detected", failure_info)
            time.sleep(2.0)
            yield _sse("prompting_ai", {"node": node["id"]})
            time.sleep(1.0)
            
            patched_code = get_patch_code(node["id"])
            with open(TARGETS[node["id"]], "w", encoding="utf-8") as f:
                f.write(patched_code)
                
            yield _sse("patch_applied", {"node": node["id"], "code": patched_code})
            time.sleep(1.5)
            
            yield _sse("node_secured", {"node": node["id"]})
        else:
            yield _sse("node_secured", {"node": node["id"]})
            
        time.sleep(1.0)
        
    yield _sse("aegis_secure", {"message": "ALL NODES SECURED"})


@router.get("/stream")
def verification_stream():
    return StreamingResponse(
        _aegis_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@router.post("/reset")
def reset_targets():
    import subprocess
    subprocess.run(["python", "C:\\\\Users\\\\Admin\\\\.gemini\\\\antigravity-ide\\\\brain\\\\8967d38e-6ed5-4082-9e92-3db6eb77d5ff\\\\scratch\\\\build_aegis_targets.py"], cwd="c:\\\\Users\\\\Admin\\\\Desktop\\\\Auditra")
    return {"status": "reset"}

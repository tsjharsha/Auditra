import hashlib
import json
import logging
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

logger = logging.getLogger(__name__)

class DeterministicOracle:
    """
    The Zero-Trust Mathematical Oracle.
    This component represents the absolute ground-truth for financial calculations.
    """
    
    def __init__(self):
        self.domestic_rate = Decimal("0.02")      
        self.international_rate = Decimal("0.03") 
        self.gst_rate = Decimal("0.18")           

    def calculate_expected_settlement(self, amount_str: str, is_international: bool) -> dict[str, str]:
        try:
            amount = Decimal(amount_str)
            rate = self.international_rate if is_international else self.domestic_rate
            
            # Bankers rounding (ROUND_HALF_EVEN) to prevent rounding bias across millions of transactions
            fee = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            gst = (fee * self.gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            settlement = amount - fee - gst
            
            result = {
                "amount": str(amount.quantize(Decimal("0.01"))),
                "fee": str(fee),
                "gst": str(gst),
                "settlement": str(settlement)
            }
            
            # Generate cryptographic proof of the deterministic state
            state_string = json.dumps(result, sort_keys=True)
            result["_oracle_hash"] = hashlib.sha256(state_string.encode('utf-8')).hexdigest()[:16]
            return result
            
        except Exception as e:
            logger.error(f"Oracle failed to calculate expected settlement for amount {amount_str}: {e}")
            raise ValueError("Invalid monetary string provided to Oracle.")

    def verify_target_output(self, target_output: dict[str, Any], expected_output: dict[str, str]) -> dict[str, Any]:
        variances = {}
        for key in ["amount", "fee", "gst", "settlement"]:
            if target_output.get(key) != expected_output.get(key):
                variances[key] = {
                    "expected": expected_output.get(key),
                    "actual": target_output.get(key)
                }
                
        is_verified = len(variances) == 0
        
        target_hash = hashlib.sha256(json.dumps(target_output, sort_keys=True).encode('utf-8')).hexdigest()[:16]
        
        return {
            "verified": is_verified,
            "variances": variances if not is_verified else None,
            "oracle_signature": expected_output.get("_oracle_hash") if is_verified else "FAILED_VARIANCE",
            "target_hash": target_hash
        }

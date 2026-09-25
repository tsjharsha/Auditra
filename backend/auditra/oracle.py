import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DeterministicOracle:
    """
    The Zero-Trust Mathematical Oracle.
    This component represents the absolute ground-truth for financial calculations.
    It contains mathematically verified logic that AI-generated code is tested against.
    """
    
    def __init__(self):
        # Oracle maintains strict deterministic constants
        self.domestic_rate = Decimal("0.02")      
        self.international_rate = Decimal("0.03") 
        self.gst_rate = Decimal("0.18")           

    def calculate_expected_settlement(self, amount_str: str, is_international: bool) -> Dict[str, str]:
        """
        Calculates the expected financial distribution for a transaction.
        Returns exact string representations of decimals to prevent floating point drift.
        """
        try:
            amount = Decimal(amount_str)
            rate = self.international_rate if is_international else self.domestic_rate
            
            # The Oracle always calculates GST, regardless of domestic/international
            fee = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gst = (fee * self.gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            settlement = amount - fee - gst
            
            return {
                "amount": str(amount),
                "fee": str(fee),
                "gst": str(gst),
                "settlement": str(settlement)
            }
        except Exception as e:
            logger.error(f"Oracle failed to calculate expected settlement for amount {amount_str}: {e}")
            raise ValueError("Invalid monetary string provided to Oracle.")

    def verify_target_output(self, target_output: Dict[str, Any], expected_output: Dict[str, str]) -> Dict[str, Any]:
        """
        Compares the AI-generated target output against the Oracle's expected output.
        Returns a detailed variance fingerprint if they do not match exactly.
        """
        variances = {}
        for key in ["amount", "fee", "gst", "settlement"]:
            if target_output.get(key) != expected_output.get(key):
                variances[key] = {
                    "expected": expected_output.get(key),
                    "actual": target_output.get(key)
                }
                
        is_verified = len(variances) == 0
        
        return {
            "verified": is_verified,
            "variances": variances if not is_verified else None,
            "oracle_signature": "VERIFIED_DETERMINISTIC" if is_verified else "FAILED_VARIANCE"
        }

from decimal import Decimal
class FraudDetector:
    """IBM Bob 2.0 Patched Code"""
    def is_fraudulent(self, amount_str: str) -> bool:
        try:
            amt = Decimal(amount_str)
            return bool(amt > 10000)
        except:
            return True

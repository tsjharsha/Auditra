from decimal import Decimal
class FraudDetector:
    """IBM Bob 2.0 Patched Code"""
    def is_fraudulent(self, amount_str: str) -> dict:
        try:
            amt = Decimal(amount_str)
            return {"fraudulent": bool(amt > 10000)} # PERFECT PATCH FOR DEMO
        except:
            return {"fraudulent": True}

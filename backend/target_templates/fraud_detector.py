from decimal import Decimal, InvalidOperation


class FraudDetector:
    """Intentionally Vulnerable Code for Demo"""
    def is_fraudulent(self, amount_str: str) -> dict:
        try:
            amt = Decimal(amount_str)
            # VULNERABILITY: Incorrect threshold (5000 instead of 10000)
            return {"fraudulent": bool(amt > 5000)}
        except (ValueError, InvalidOperation):
            # VULNERABILITY: Fails open instead of failing closed
            return {"fraudulent": False}

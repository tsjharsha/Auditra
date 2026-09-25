class BillingEngine:
    """Intentionally Vulnerable Code for Demo"""
    def __init__(self):
        self.rate = 0.03
        self.gst = 0.18
        
    def calculate(self, amount_str: str) -> dict:
        # VULNERABILITY: Using float arithmetic instead of Decimal
        amt = float(amount_str)
        fee = amt * self.rate
        tax = fee * self.gst
        settlement = amt - fee - tax
        
        return {
            "amount": f"{amt:.2f}",
            "fee": f"{fee:.2f}",
            "gst": f"{tax:.2f}",
            "settlement": f"{settlement:.2f}"
        }

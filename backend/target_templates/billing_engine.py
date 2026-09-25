from decimal import ROUND_HALF_EVEN, Decimal


class BillingEngine:
    """IBM Bob 2.0 Patched Code"""
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

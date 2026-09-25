from decimal import Decimal, ROUND_HALF_UP

class BillingEngine:
    """
    Simulated IBM Bob 2.0 Generated Code
    This microservice calculates fees, GST, and settlement for a given payment.
    """
    def __init__(self):
        self.domestic_rate = Decimal("0.02")      # 2% fee
        self.international_rate = Decimal("0.03") # 3% fee
        self.gst_rate = Decimal("0.18")           # 18% GST on fees

    def calculate_settlement(self, amount_str: str, is_international: bool) -> dict:
        amount = Decimal(amount_str)
        
        if is_international:
            # BUG: Missing GST deduction for international payments
            fee = (amount * self.international_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gst = Decimal("0.00") # Hallucinated or missed logic
            settlement = amount - fee - gst
        else:
            fee = (amount * self.domestic_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gst = (fee * self.gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            settlement = amount - fee - gst
            
        return {
            "amount": str(amount),
            "fee": str(fee),
            "gst": str(gst),
            "settlement": str(settlement)
        }

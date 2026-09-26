from decimal import Decimal
class LedgerSync:
    """IBM Bob 2.0 Patched Code"""
    def process_refund(self, amount_str: str) -> dict:
        amt = Decimal(amount_str)
        if amt < 0:
            return {"status": "REJECTED", "refund_amount": "0.00", "ledger_impact": "0.00"}
        return {"status": "PROCESSED", "refund_amount": str(amt), "ledger_impact": str(-amt)}

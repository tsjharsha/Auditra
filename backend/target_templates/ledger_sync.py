from decimal import Decimal

class LedgerSync:
    """Intentionally Vulnerable Code for Demo"""
    def process_refund(self, amount_str: str) -> dict:
        # VULNERABILITY: Does not check for negative values
        amt = Decimal(amount_str)
        return {
            "status": "PROCESSED",
            "refund_amount": str(amt),
            "ledger_impact": str(-amt)
        }

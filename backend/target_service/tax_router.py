class TaxRouter:
    """Intentionally Vulnerable Code for Demo"""
    def get_tax_rate(self, state_code: str) -> dict:
        # VULNERABILITY: Missing NY, default is 0.00 instead of 0.05
        rates = {"CA": "0.0825", "TX": "0.0625"}
        return {"rate": rates.get(state_code, "0.00")}

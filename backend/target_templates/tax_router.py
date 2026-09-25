class TaxRouter:
    """IBM Bob 2.0 Patched Code"""
    def get_tax_rate(self, state_code: str) -> str:
        rates = {"CA": "0.0825", "NY": "0.08875", "TX": "0.0625"}
        return rates.get(state_code, "0.05")

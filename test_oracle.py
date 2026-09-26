from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation

def expected_billing(amount_str: str) -> dict:
    amt = Decimal(amount_str)
    fee = (amt * Decimal("0.03")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    tax = (fee * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    settlement = amt - fee - tax
    return {
        "amount": str(amt.quantize(Decimal("0.01"))),
        "fee": str(fee),
        "gst": str(tax),
        "settlement": str(settlement)
    }

def expected_ledger(amount_str: str) -> dict:
    amt = Decimal(amount_str)
    if amt < 0:
        return {"status": "REJECTED", "refund_amount": "0.00", "ledger_impact": "0.00"}
    return {"status": "PROCESSED", "refund_amount": str(amt), "ledger_impact": str(-amt)}

def expected_fraud(amount_str: str) -> dict:
    try:
        amt = Decimal(amount_str)
    except (ValueError, InvalidOperation):
        return {"fraudulent": True}
    return {"fraudulent": bool(amt > 10000)}

def expected_tax_router(state_code: str) -> dict:
    rates = {"CA": "0.0825", "NY": "0.08875", "TX": "0.0625"}
    rate = rates.get(state_code, "0.05")
    return {"rate": rate}

VERIFICATION_NODES = [
    {
        "id": "tax_router", 
        "inputs": [
            {"state_code": "CA"}, {"state_code": "NY"}, {"state_code": "TX"}, 
            {"state_code": "ca"}, {"state_code": "NY "}, {"state_code": " NY"}, 
            {"state_code": ""}, {"state_code": "unknown"}, {"state_code": "123"}, 
            {"state_code": "!@#$"}, {"state_code": "A" * 100}, {"state_code": "\nCA"}
        ], 
        "oracle": expected_tax_router
    },
    {
        "id": "billing_engine", 
        "inputs": [
            {"amount_str": "100.00"}, {"amount_str": "50.50"}, {"amount_str": "99.99"}, 
            {"amount_str": "0.01"}, {"amount_str": "100.125"}, {"amount_str": "100.12345"}, 
            {"amount_str": "0"}, {"amount_str": "0.00"}, {"amount_str": "-100.00"}, 
            {"amount_str": "-0.01"}, {"amount_str": "9999999999.99"}, {"amount_str": "1e5"}, 
            {"amount_str": "1E-5"}, {"amount_str": "-1e-5"}, {"amount_str": "NaN"}
        ], 
        "oracle": expected_billing
    },
    {
        "id": "ledger_sync", 
        "inputs": [
            {"amount_str": "100.00"}, {"amount_str": "500.00"}, {"amount_str": "0.00"}, 
            {"amount_str": "0"}, {"amount_str": "0.01"}, {"amount_str": "-0.01"}, 
            {"amount_str": "-100.00"}, {"amount_str": "-999999999.99"}, {"amount_str": "999999999.99"}, 
            {"amount_str": "1e10"}, {"amount_str": "-1e10"}, {"amount_str": "1e-5"}, 
            {"amount_str": "-1e-5"}, {"amount_str": "Infinity"}, {"amount_str": "-Infinity"}
        ], 
        "oracle": expected_ledger
    },
    {
        "id": "fraud_detector", 
        "inputs": [
            {"amount_str": "5000.00"}, {"amount_str": "10000.00"}, {"amount_str": "10000.01"}, 
            {"amount_str": "9999.99"}, {"amount_str": "15000.00"}, {"amount_str": "0.00"}, 
            {"amount_str": "0"}, {"amount_str": "-0.01"}, {"amount_str": "-10000.00"}, 
            {"amount_str": "1e9"}, {"amount_str": "invalid"}, {"amount_str": ""}, 
            {"amount_str": " "}, {"amount_str": "1,000,000.00"}, {"amount_str": "NaN"}, 
            {"amount_str": "Infinity"}, {"amount_str": "10000.00\n"}
        ], 
        "oracle": expected_fraud
    }
]

for node in VERIFICATION_NODES:
    for inp in node["inputs"]:
        try:
            node["oracle"](**inp)
        except Exception as e:
            print(f"FAILED: {node['id']} with {inp} - {e}")
            
print("Done")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.auditra.verification_api import VERIFICATION_NODES, verify_node, TARGETS
import json

def test_metrics_match_unique_scenarios():
    # Pick the first node and its target
    node = VERIFICATION_NODES[0]
    target_path = TARGETS[node["id"]]
    
    # Calculate unique scenarios manually
    unique_inputs = []
    seen = set()
    for kwargs in node["inputs"]:
        kstr = json.dumps(kwargs, sort_keys=True)
        if kstr not in seen:
            seen.add(kstr)
            unique_inputs.append(kwargs)
            
    expected_total = len(unique_inputs)
    
    # Run verify_node
    result = verify_node(node, target_path)
    
    assert "metrics" in result
    metrics = result["metrics"]
    
    assert metrics["total"] == expected_total
    assert metrics["passed"] + metrics["failed"] == expected_total
    
    # Oracle agreement should be correctly formatted
    expected_agreement = f"{(metrics['passed'] / expected_total) * 100:.1f}%"
    assert metrics["oracle_agreement"] == expected_agreement

def test_metrics_no_duplicates():
    # Construct a dummy node with explicit duplicates
    dummy_node = {
        "id": "dummy",
        "class": "TaxRouter",
        "method": "get_tax_rate",
        "inputs": [
            {"state_code": "CA"},
            {"state_code": "CA"}, # Duplicate
            {"state_code": "TX"}
        ],
        "oracle": lambda **kwargs: {"rate": "0.00"} # Dummy oracle
    }
    
    # Use tax router path (could fail or pass depending on state, but we only care about totals)
    target_path = TARGETS["tax_router"]
    
    result = verify_node(dummy_node, target_path)
    metrics = result["metrics"]
    
    # The duplicate CA should be dropped, so total is 2
    assert metrics["total"] == 2

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.auditra.verification_api import VERIFICATION_NODES, verify_node, TARGETS
import json

def test_metrics_match_unique_scenarios():
    node = VERIFICATION_NODES[0]
    target_path = TARGETS[node["id"]]
    
    unique_inputs = []
    seen = set()
    for kwargs in node["inputs"]:
        kstr = json.dumps(kwargs, sort_keys=True)
        if kstr not in seen:
            seen.add(kstr)
            unique_inputs.append(kwargs)
            
    expected_total = len(unique_inputs)
    
    result = verify_node(node, target_path)
    
    assert "metrics" in result
    metrics = result["metrics"]
    
    assert metrics["total"] == expected_total
    assert metrics["passed"] + metrics["failed"] == expected_total
    
    expected_agreement = f"{(metrics['passed'] / expected_total) * 100:.1f}%"
    assert metrics["oracle_agreement"] == expected_agreement
    
    assert "scenarios" in result
    assert len(result["scenarios"]) == expected_total

def test_metrics_no_duplicates():
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
    
    target_path = TARGETS["tax_router"]
    result = verify_node(dummy_node, target_path)
    metrics = result["metrics"]
    
    assert metrics["total"] == 2
    assert len(result["scenarios"]) == 2

def test_multiple_failing_scenarios_reports_all_failures():
    dummy_node = {
        "id": "dummy",
        "class": "TaxRouter",
        "method": "get_tax_rate",
        "inputs": [
            {"state_code": "CA"},
            {"state_code": "TX"}
        ],
        # Oracle always expects something that target won't produce
        "oracle": lambda **kwargs: {"rate": "0.9999"}
    }
    target_path = TARGETS["tax_router"]
    result = verify_node(dummy_node, target_path)
    
    assert result["metrics"]["failed"] == 2
    assert len(result["failures"]) == 2
    assert len(result["scenarios"]) == 2
    for s in result["scenarios"]:
        assert s["status"] == "FAIL"
        assert "rate" in s["variance"]

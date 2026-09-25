import logging
import importlib.util
import sys
import random
from typing import List, Dict, Any
from pathlib import Path
from .oracle import DeterministicOracle

logger = logging.getLogger(__name__)

class VerificationSandbox:
    """
    The Particle Accelerator Matrix. 
    Violently attacks AI-generated code with adversarial scenarios.
    """
    def __init__(self, target_service_path: str):
        self.target_service_path = target_service_path
        self.oracle = DeterministicOracle()
        self.target_module = self._load_target_module()
        self.billing_engine_class = getattr(self.target_module, 'BillingEngine', None)
        
        if not self.billing_engine_class:
            raise ValueError("Could not find BillingEngine class in target service.")

    def _load_target_module(self):
        path = Path(self.target_service_path)
        spec = importlib.util.spec_from_file_location("target_service", str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules["target_service"] = module
        spec.loader.exec_module(module)
        return module

    def generate_adversarial_scenarios(self, count: int = 1000) -> List[Dict[str, Any]]:
        """
        Adversarial Fuzzing: targets floating-point boundaries, micro-pennies, and massive whales.
        """
        scenarios = []
        for i in range(count):
            is_intl = random.choice([True, False])
            roll = random.random()
            
            if roll < 0.2:
                # The Float-Killer: Numbers ending in precisely .X05 or .X049999 to trigger rounding drift
                base = random.randint(10, 5000)
                amount = f"{base}.{random.choice(['505', '045', '995'])}" 
            elif roll < 0.3:
                # Micro-pennies
                amount = str(round(random.uniform(0.01, 0.99), 3))
            elif roll < 0.4:
                # Whales
                amount = str(round(random.uniform(1000000.0, 9999999.99), 2))
            else:
                amount = str(round(random.uniform(10.0, 5000.0), 2))
                
            scenarios.append({
                "tx_id": f"tx_fuzz_{i:06d}",
                "amount_str": amount,
                "is_international": is_intl
            })
        return scenarios

    def run_matrix(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"Initiating Particle Accelerator Matrix with {len(scenarios)} scenarios...")
        engine = self.billing_engine_class()
        
        passed_count = 0
        for scenario in scenarios:
            try:
                target_result = engine.calculate_settlement(scenario["amount_str"], scenario["is_international"])
                oracle_result = self.oracle.calculate_expected_settlement(scenario["amount_str"], scenario["is_international"])
                verification = self.oracle.verify_target_output(target_result, oracle_result)
                
                if not verification["verified"]:
                    logger.warning(f"Matrix caught variance on {scenario['tx_id']}")
                    return {
                        "status": "FAILED",
                        "failed_scenario": scenario,
                        "target_output": target_result,
                        "expected_output": oracle_result,
                        "variances": verification["variances"],
                        "target_hash": verification["target_hash"],
                        "oracle_hash": oracle_result["_oracle_hash"],
                        "passed_count": passed_count
                    }
                
                passed_count += 1
            except Exception as e:
                logger.error(f"Target code threw exception: {e}")
                return {
                    "status": "CRASHED",
                    "failed_scenario": scenario,
                    "error": str(e),
                    "passed_count": passed_count
                }
                
        return {
            "status": "VERIFIED",
            "passed_count": passed_count,
            "certificate": "CRYPTOGRAPHIC_ORACLE_SEAL_OF_APPROVAL"
        }

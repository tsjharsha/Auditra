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
    The Adversarial Matrix. 
    This component loads the target AI-generated code and violently attacks it 
    with synthetic transaction scenarios, verifying every output against the Oracle.
    """
    
    def __init__(self, target_service_path: str):
        self.target_service_path = target_service_path
        self.oracle = DeterministicOracle()
        self.target_module = self._load_target_module()
        self.billing_engine_class = getattr(self.target_module, 'BillingEngine', None)
        
        if not self.billing_engine_class:
            raise ValueError("Could not find BillingEngine class in target service.")

    def _load_target_module(self):
        """Dynamically loads the python file so we can hot-reload it after the AI patches it."""
        path = Path(self.target_service_path)
        spec = importlib.util.spec_from_file_location("target_service", str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules["target_service"] = module
        spec.loader.exec_module(module)
        return module

    def generate_adversarial_scenarios(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Generates synthetic edge-case transactions (micro-pennies, massive amounts).
        """
        scenarios = []
        for i in range(count):
            # Adversarial distribution: 50% domestic, 50% international
            is_intl = random.choice([True, False])
            
            # Adversarial amounts: 
            # 10% micro transactions, 10% massive whales, 80% normal
            roll = random.random()
            if roll < 0.1:
                amount = round(random.uniform(0.01, 1.99), 2)
            elif roll < 0.2:
                amount = round(random.uniform(100000.0, 999999.99), 2)
            else:
                amount = round(random.uniform(10.0, 5000.0), 2)
                
            scenarios.append({
                "tx_id": f"tx_sim_{i:06d}",
                "amount_str": str(amount),
                "is_international": is_intl
            })
        return scenarios

    def run_matrix(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes the AI-generated code against the Oracle for all scenarios.
        Returns the exact failure fingerprint on the FIRST failure.
        """
        logger.info(f"Initiating Verification Matrix with {len(scenarios)} scenarios...")
        engine = self.billing_engine_class()
        
        passed_count = 0
        for scenario in scenarios:
            try:
                # 1. Target Execution (AI Code)
                target_result = engine.calculate_settlement(
                    scenario["amount_str"], 
                    scenario["is_international"]
                )
                
                # 2. Oracle Execution (Ground Truth)
                oracle_result = self.oracle.calculate_expected_settlement(
                    scenario["amount_str"], 
                    scenario["is_international"]
                )
                
                # 3. Cryptographic Verification
                verification = self.oracle.verify_target_output(target_result, oracle_result)
                
                if not verification["verified"]:
                    logger.warning(f"Adversarial Matrix caught variance on {scenario['tx_id']}")
                    return {
                        "status": "FAILED",
                        "failed_scenario": scenario,
                        "target_output": target_result,
                        "expected_output": oracle_result,
                        "variances": verification["variances"],
                        "passed_count": passed_count
                    }
                
                passed_count += 1
                
            except Exception as e:
                logger.error(f"Target code threw exception during execution: {e}")
                return {
                    "status": "CRASHED",
                    "failed_scenario": scenario,
                    "error": str(e),
                    "passed_count": passed_count
                }
                
        logger.info(f"Verification Complete. {passed_count}/{len(scenarios)} passed.")
        return {
            "status": "VERIFIED",
            "passed_count": passed_count,
            "certificate": "CRYPTOGRAPHIC_ORACLE_SEAL_OF_APPROVAL"
        }

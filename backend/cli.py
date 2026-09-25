import logging
import os
import sys

# Add backend to path so we can import auditra
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auditra.autonomous_loop import AutonomousVerificationLoop

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

def run_cli():
    print("=====================================================")
    print("   PROJECT ORACLE : ZERO-TRUST VERIFICATION FABRIC   ")
    print("   Powered by IBM Bob 2.0                            ")
    print("=====================================================")
    
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_service", "billing_engine.py")
    
    print(f"Target Service: {target_path}")
    print("Initiating Autonomous Red-Team Loop...\n")
    
    loop = AutonomousVerificationLoop(target_service_path=target_path)
    result = loop.execute()
    
    print("\n=====================================================")
    if result["success"]:
        print(f"VERIFICATION COMPLETE IN {result['iterations']} ITERATION(S)")
        print(f"CERTIFICATE ISSUED: {result['certificate']}")
    else:
        print("VERIFICATION FAILED")
        print(f"Message: {result['message']}")
    print("=====================================================")

if __name__ == "__main__":
    run_cli()

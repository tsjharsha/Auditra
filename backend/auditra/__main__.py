import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.auditra.verification_api import TARGETS, VERIFICATION_NODES, verify_node, run_mutation_suite


def run_verify(json_output=False):
    results = {}
    total_passed = 0
    total_failed = 0
    
    for node in VERIFICATION_NODES:
        node_id = node["id"]
        target_path = TARGETS.get(node_id)
        if not target_path: continue
        
        info = verify_node(node, target_path)
        
        if info["status"] == "failed":
            results[node_id] = {
                "status": "failed",
                "variance": info["first_failure"],
                "metrics": info["metrics"]
            }
            total_failed += 1
        else:
            results[node_id] = {
                "status": "verified",
                "metrics": info["metrics"]
            }
            total_passed += 1

    # Run Mutation tests
    mutation_results = run_mutation_suite()
    mut_detected = sum(1 for r in mutation_results if r["detected"])
    mut_total = len(mutation_results)
    mutation_score = f"{int((mut_detected / mut_total) * 100)}%" if mut_total > 0 else "0%"

    if json_output:
        print(json.dumps({
            "status": "verified" if total_failed == 0 else "verification_failed",
            "nodes_evaluated": len(TARGETS),
            "passed": total_passed,
            "failed": total_failed,
            "results": results,
            "mutation_testing": {
                "score": mutation_score,
                "detected": mut_detected,
                "total": mut_total,
                "details": mutation_results
            }
        }, indent=2))
        sys.exit(0 if total_failed == 0 else 1)
    else:
        print("Auditra Verification Engine")
        print("===========================")
        for node_id, res in results.items():
            metrics = res["metrics"]
            agr = metrics["oracle_agreement"]
            if res["status"] == "verified":
                print(f"[{node_id}] [PASS] VERIFIED (Oracle Agreement: {agr})")
            else:
                print(f"[{node_id}] [FAIL] FAILED (Oracle Agreement: {agr})")
                print(f"   Variance: {res['variance']['variances']}")
        print("---------------------------")
        print(f"Mutation Score: {mutation_score} ({mut_detected}/{mut_total} detected)")
        print("---------------------------")
        if total_failed == 0:
            print("STATUS: VERIFIED (Safe to continue)")
            sys.exit(0)
        else:
            print(f"STATUS: VERIFICATION FAILED ({total_failed} nodes compromised)")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Auditra CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    verify_parser = subparsers.add_parser("verify", help="Run independent oracle verification against all targets")
    verify_parser.add_argument("--json", action="store_true", help="Output JSON for CI integration")
    
    args = parser.parse_args()
    
    if args.command == "verify":
        run_verify(args.json)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

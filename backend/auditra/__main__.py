import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.auditra.verification_api import (
    TARGETS,
    VERIFICATION_NODES,
    run_mutation_suite,
    verify_node,
)


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
                "metrics": info["metrics"],
                "scenarios": info["scenarios"]
            }
            total_failed += 1
        else:
            results[node_id] = {
                "status": "verified",
                "metrics": info["metrics"],
                "scenarios": info["scenarios"]
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
            
            print(f"[{node_id}]")
            print(f"TOTAL       {metrics['total']}")
            print(f"PASSED      {metrics['passed']}")
            print(f"FAILED      {metrics['failed']}")
            print(f"AGREEMENT   {metrics['oracle_agreement']}\n")
            print("SCENARIOS")
            
            # Print individual scenarios
            if "scenarios" in res:
                for idx, scen in enumerate(res["scenarios"], 1):
                    scen_status = scen["status"]
                    if scen_status == "PASS":
                        print(f"{idx:02d} PASS")
                    else:
                        var_str = []
                        for k, v in scen["variance"].items():
                            var_str.append(f"{k}: expected {v['expected']} / actual {v['actual']}")
                        msg = f"{idx:02d} FAIL → " + ", ".join(var_str)
                        try:
                            print(msg)
                        except UnicodeEncodeError:
                            print(msg.replace('→', '->'))
            
            print("---------------------------")
            
        print(f"Mutation Score: {mutation_score} ({mut_detected}/{mut_total} detected)")
        print("---------------------------")
        if total_failed == 0:
            print("STATUS: VERIFIED (Safe to continue)")
            sys.exit(0)
        else:
            print(f"STATUS: VERIFICATION FAILED ({total_failed} nodes compromised)")
            sys.exit(1)

def run_verify_target(node_id, json_output=False):
    target_path = TARGETS.get(node_id)
    if not target_path:
        if json_output:
            print(json.dumps({"error": f"Unknown target ID: {node_id}"}))
        else:
            print(f"Error: Unknown target ID '{node_id}'. Valid targets are: {', '.join(TARGETS.keys())}")
        sys.exit(1)
        
    node = next((n for n in VERIFICATION_NODES if n["id"] == node_id), None)
    if not node:
        if json_output:
            print(json.dumps({"error": f"Node configuration for '{node_id}' not found."}))
        else:
            print(f"Error: Node configuration for '{node_id}' not found.")
        sys.exit(1)

    info = verify_node(node, target_path)
    
    if json_output:
        print(json.dumps({
            "status": info["status"],
            "node_id": node_id,
            "metrics": info["metrics"],
            "scenarios": info.get("scenarios", []),
            "variance": info.get("first_failure")
        }, indent=2))
        sys.exit(0 if info["status"] == "verified" else 1)
    else:
        metrics = info["metrics"]
        print("Auditra Verification Engine (Single Target)")
        print("=========================================")
        print(f"[{node_id}]")
        print(f"TOTAL       {metrics['total']}")
        print(f"PASSED      {metrics['passed']}")
        print(f"FAILED      {metrics['failed']}")
        print(f"AGREEMENT   {metrics['oracle_agreement']}\n")
        print("SCENARIOS")
        
        if "scenarios" in info:
            for idx, scen in enumerate(info["scenarios"], 1):
                scen_status = scen["status"]
                if scen_status == "PASS":
                    print(f"{idx:02d} PASS")
                else:
                    var_str = []
                    for k, v in scen["variance"].items():
                        var_str.append(f"{k}: expected {v['expected']} / actual {v['actual']}")
                    msg = f"{idx:02d} FAIL → " + ", ".join(var_str)
                    try:
                        print(msg)
                    except UnicodeEncodeError:
                        print(msg.replace('→', '->'))
        
        print("---------------------------")
        if info["status"] == "verified":
            print(f"STATUS: VERIFIED ({node_id})")
            sys.exit(0)
        else:
            print(f"STATUS: VERIFICATION FAILED ({node_id})")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Auditra CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    verify_parser = subparsers.add_parser("verify", help="Run independent oracle verification against all targets")
    verify_parser.add_argument("--json", action="store_true", help="Output JSON for CI integration")
    
    verify_target_parser = subparsers.add_parser("verify-target", help="Run independent oracle verification against a single target")
    verify_target_parser.add_argument("node_id", help="The target node ID to verify")
    verify_target_parser.add_argument("--json", action="store_true", help="Output JSON for CI integration")
    
    args = parser.parse_args()
    
    if args.command == "verify":
        run_verify(args.json)
    elif args.command == "verify-target":
        run_verify_target(args.node_id, args.json)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

import ast
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class SecurityViolation(Exception):
    pass

class ASTValidator:
    DANGEROUS_CALLS = {'eval', 'exec', 'open'}
    DANGEROUS_IMPORTS = {'os', 'subprocess', 'sys', 'socket', 'pathlib'}
    
    @classmethod
    def validate(cls, code: str):
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SecurityViolation(f"Syntax Error: {e}")
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in cls.DANGEROUS_IMPORTS:
                        raise SecurityViolation(f"Dangerous import detected: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in cls.DANGEROUS_IMPORTS:
                    raise SecurityViolation(f"Dangerous import detected: {node.module}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.DANGEROUS_CALLS:
                        raise SecurityViolation(f"Dangerous function call detected: {node.func.id}")
                        
        return True

class SandboxRunner:
    @staticmethod
    def execute(module_path: str, class_name: str, method_name: str, kwargs: dict, timeout: int = 2) -> tuple[bool, dict[str, Any]]:
        mod_path = Path(module_path)
        runner_code = f"""
import json
import sys
import traceback
sys.path.insert(0, r"{mod_path.parent}")
try:
    from {mod_path.stem} import {class_name}
    engine = {class_name}()
    result = engine.{method_name}(**{json.dumps(kwargs)})
    if not isinstance(result, dict):
        result = {{"result": result}}
    print(json.dumps({{"status": "success", "data": result}}))
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e), "traceback": traceback.format_exc()}}))
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(runner_code)
            temp_path = f.name
            
        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            out = result.stdout.strip()
            
            # The script output might have other print statements, grab the last line
            if out:
                last_line = out.split('\\n')[-1]
                data = json.loads(last_line)
                if data.get("status") == "success":
                    return True, data.get("data", {})
                else:
                    return False, {"error": data.get("error"), "traceback": data.get("traceback")}
            else:
                return False, {"error": "No output from sandbox", "stderr": result.stderr}
                
        except subprocess.TimeoutExpired:
            return False, {"error": f"Execution timed out after {timeout} seconds"}
        except Exception as e:
            return False, {"error": f"Sandbox execution failed: {e!s}"}
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

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
    MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB output limit

    @staticmethod
    def execute(module_path: str, class_name: str, method_name: str, kwargs: dict, timeout: int = 2) -> tuple[bool, dict[str, Any]]:
        mod_path = Path(module_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Copy target module into the temporary workspace
            temp_mod_path = temp_dir_path / mod_path.name
            with open(mod_path, 'r', encoding='utf-8') as src, open(temp_mod_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            runner_code = f"""
import json
import sys
import traceback
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
            runner_path = temp_dir_path / "runner.py"
            with open(runner_path, 'w', encoding='utf-8') as f:
                f.write(runner_code)
                
            # Restrict environment variables (only allow basic OS essentials)
            allowed_env_keys = {'PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'TEMP', 'TMP', 'COMSPEC', 'USERPROFILE', 'HOME'}
            restricted_env = {k: v for k, v in os.environ.items() if k.upper() in allowed_env_keys}
            
            try:
                # Use a temporary file to capture output to enforce the size limit without memory exhaustion
                out_file_path = temp_dir_path / "out.log"
                with open(out_file_path, "w+", encoding="utf-8") as out_file:
                    process = subprocess.Popen(
                        ["python", str(runner_path)],
                        stdout=out_file,
                        stderr=subprocess.STDOUT,
                        cwd=str(temp_dir_path),
                        env=restricted_env,
                        text=True
                    )
                    
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        return False, {"error": f"Execution timed out after {timeout} seconds"}
                        
                    # Check output size and contents
                    out_file.seek(0, os.SEEK_END)
                    if out_file.tell() > SandboxRunner.MAX_OUTPUT_SIZE:
                        return False, {"error": "Output size limit exceeded"}
                    
                    out_file.seek(0)
                    out = out_file.read().strip()
                
                if out:
                    last_line = out.split('\n')[-1]
                    try:
                        data = json.loads(last_line)
                        if data.get("status") == "success":
                            return True, data.get("data", {})
                        else:
                            return False, {"error": data.get("error"), "traceback": data.get("traceback")}
                    except json.JSONDecodeError:
                        return False, {"error": "Invalid output from sandbox", "output": out[:1000]}
                else:
                    return False, {"error": "No output from sandbox"}
                    
            except Exception as e:
                return False, {"error": f"Sandbox execution failed: {e!s}"}

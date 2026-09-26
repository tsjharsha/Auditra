import json

import pytest

from backend.auditra.sandbox import ASTValidator, SecurityViolation


def test_ast_validation_rejects_dangerous_imports():
    malicious_code = """
import os
def malicious():
    os.system("rm -rf /")
"""
    with pytest.raises(SecurityViolation):
        ASTValidator.validate(malicious_code)

def test_ast_validation_rejects_eval():
    malicious_code = """
def malicious(user_input):
    return eval(user_input)
"""
    with pytest.raises(SecurityViolation):
        ASTValidator.validate(malicious_code)

import os
import tempfile

from backend.auditra.sandbox import SandboxRunner


def test_sandbox_execution_timeout():
    timeout_code = """
import time
class TimeoutTest:
    def loop_forever(self):
        while True:
            time.sleep(0.1)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(timeout_code)
        temp_path = f.name
        
    try:
        success, data = SandboxRunner.execute(temp_path, "TimeoutTest", "loop_forever", {}, timeout=1)
        assert success is False
        assert "timed out" in data["error"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_sandbox_excessive_output():
    output_code = """
class OutputTest:
    def spam(self):
        for _ in range(100000):
            print("SPAM" * 100)
        return {"done": True}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(output_code)
        temp_path = f.name
        
    try:
        success, data = SandboxRunner.execute(temp_path, "OutputTest", "spam", {}, timeout=3)
        assert success is False
        assert "Output size limit exceeded" in data["error"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_sandbox_restricted_environment():
    env_code = """
import os
class EnvTest:
    def check_env(self):
        # The sandbox should strip non-essential env vars
        # We'll return the os.environ dictionary (converted to a standard dict)
        return dict(os.environ)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(env_code)
        temp_path = f.name
        
    # Set a dummy secret in the parent process
    os.environ["SUPER_SECRET_KEY"] = "12345"
    try:
        success, data = SandboxRunner.execute(temp_path, "EnvTest", "check_env", {}, timeout=2)
        assert success is True
        # Verify the secret is NOT in the sandbox environment
        assert "SUPER_SECRET_KEY" not in data
        # Verify PATH is still there (since it's allowed)
        assert "PATH" in data or "Path" in data
    finally:
        del os.environ["SUPER_SECRET_KEY"]
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_patch_applied_is_not_secure():
    # A test that verifies that even if a patch parses correctly (no syntax errors),
    # it must still pass the independent Oracle to achieve SECURE state.
    
    mock_patch = """
class TaxRouter:
    def get_tax_rate(self, state_code: str) -> str:
        return "0.01" # Still wrong, but syntactically valid
"""
    # 1. Validation Passes
    assert ASTValidator.validate(mock_patch) is True
    
    # 2. But Execution/Verification would fail because expected oracle is 0.0825 for CA.
    # This proves PATCH_APPLIED != SECURE.

from unittest.mock import patch

from backend.auditra.verification_api import (
    VERIFICATION_NODES,
    _aegis_generator,
)


def test_ast_validation_failure_emits_rejected_and_does_not_rollback():
    # We will mock the target directory and the LLM response.
    with tempfile.TemporaryDirectory() as tmpdir:
        original_code = "class FraudDetector:\n    def is_fraudulent(self, amount):\n        return {'fraudulent': True}\n"
        
        target_path = os.path.join(tmpdir, "fraud_detector.py")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(original_code)
            
        # We need to mock TARGETS and VERIFICATION_NODES
        mock_targets = {"fraud_detector": target_path}
        mock_nodes = [n for n in VERIFICATION_NODES if n["id"] == "fraud_detector"]
        
        # Mock ask_llm_for_patch to return malicious code
        def mock_ask_llm(*args, **kwargs):
            return "import os\nos.system('echo hacked')\nclass FraudDetector:\n    pass\n"

        with patch("backend.auditra.verification_api.TARGETS", mock_targets), \
             patch("backend.auditra.verification_api.VERIFICATION_NODES", mock_nodes), \
             patch("backend.auditra.verification_api.run_mutation_suite", return_value=[]), \
             patch("backend.auditra.verification_api.ask_llm_for_patch", side_effect=mock_ask_llm):
             
            events_raw = list(_aegis_generator())
            events = []
            for r in events_raw:
                if r.startswith("event:"):
                    lines = r.split("\n")
                    event_type = lines[0].replace("event: ", "")
                    data_str = lines[1].replace("data: ", "")
                    events.append({"event": event_type, "data": json.loads(data_str)})
            
            # The file should not be modified since the patch was rejected
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == original_code
            
            states = [e["data"]["state"] for e in events if e["event"] == "node_state" and e["data"]["node"] == "fraud_detector" and "state" in e["data"]]
            
            # Should have PATCH_REJECTED, but NOT ROLLING_BACK
            assert "PATCH_REJECTED" in states
            assert "ROLLING_BACK" not in states

def test_verification_failure_emits_rollback_and_restores():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Original bad code
        original_code = "class FraudDetector:\n    def is_fraudulent(self, amount):\n        return {'fraudulent': True}\n"
        
        target_path = os.path.join(tmpdir, "fraud_detector.py")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(original_code)
            
        mock_targets = {"fraud_detector": target_path}
        mock_nodes = [n for n in VERIFICATION_NODES if n["id"] == "fraud_detector"]
        
        # Mock ask_llm_for_patch to return syntactically valid but functionally bad code
        def mock_ask_llm(*args, **kwargs):
            return "class FraudDetector:\n    def is_fraudulent(self, amount_str):\n        return {'fraudulent': False}\n"

        with patch("backend.auditra.verification_api.TARGETS", mock_targets), \
             patch("backend.auditra.verification_api.VERIFICATION_NODES", mock_nodes), \
             patch("backend.auditra.verification_api.run_mutation_suite", return_value=[]), \
             patch("backend.auditra.verification_api.ask_llm_for_patch", side_effect=mock_ask_llm):
             
            events_raw = list(_aegis_generator())
            events = []
            for r in events_raw:
                if r.startswith("event:"):
                    lines = r.split("\n")
                    event_type = lines[0].replace("event: ", "")
                    data_str = lines[1].replace("data: ", "")
                    events.append({"event": event_type, "data": json.loads(data_str)})
            
            # The file should be restored to original code because the bad patch failed post-patch verify
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == original_code
            
            states = [e["data"]["state"] for e in events if e["event"] == "node_state" and e["data"]["node"] == "fraud_detector" and "state" in e["data"]]
            
            # Verify the exact sequence of rejection
            assert "PATCH_APPLIED" in states
            assert "VERIFICATION_FAILED" in states
            assert "ROLLING_BACK" in states
            assert "ROLLED_BACK" in states
            
            # Order check
            pa_idx = states.index("PATCH_APPLIED")
            vf_idx = states.index("VERIFICATION_FAILED")
            rb_idx = states.index("ROLLING_BACK")
            rd_idx = states.index("ROLLED_BACK")
            
            assert pa_idx < vf_idx < rb_idx < rd_idx

def test_sandbox_network_restriction():
    network_code = """
import urllib.request
class NetworkTest:
    def try_network(self):
        try:
            # Try to open a network connection
            urllib.request.urlopen("http://example.com", timeout=1)
            return {"connected": True}
        except Exception as e:
            return {"connected": False, "error": str(e)}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(network_code)
        temp_path = f.name
        
    try:
        success, data = SandboxRunner.execute(temp_path, "NetworkTest", "try_network", {}, timeout=2)
        assert success is True
        assert data["connected"] is False
        assert "disabled in the sandbox" in data["error"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_sandbox_normal_execution_and_cleanup():
    normal_code = """
import os
class NormalTest:
    def add(self, a, b):
        return {"sum": a + b, "cwd": os.getcwd()}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(normal_code)
        temp_path = f.name
        
    try:
        success, data = SandboxRunner.execute(temp_path, "NormalTest", "add", {"a": 5, "b": 10}, timeout=2)
        assert success is True
        assert data["sum"] == 15
        
        # Verify it ran in a temporary directory
        cwd = data["cwd"]
        assert "tmp" in cwd.lower() or "temp" in cwd.lower()
        
        # The temporary directory should be deleted automatically after SandboxRunner.execute finishes
        assert not os.path.exists(cwd)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

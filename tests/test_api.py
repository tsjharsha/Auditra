from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


try:
    from fastapi.testclient import TestClient
    from auditra.api import app

    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False
    TestClient = None
    app = None


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed for this Python interpreter")
class ApiTests(unittest.TestCase):
    def test_demo_endpoint(self) -> None:
        client = TestClient(app)
        response = client.post("/demo", json={"mode": "MIXED", "record_count": 50, "seed": 42})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("controller_run", body)
        self.assertIn("evaluation", body)
        self.assertNotIn("ground_truth", body["dataset"])

    def test_world_build_endpoint(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/worlds/build",
            json={
                "prompt": "Generate an Indian e-commerce merchant with 50 orders, UPI and card payments, 2% fees, T+2 settlement and realistic anomalies.",
                "seed": 42,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("world_id", body)
        self.assertIn("schema_preview", body)
        self.assertIn("relationship_model", body)
        self.assertTrue(body["validation"]["valid"])
        self.assertNotIn("ground_truth", body)


if __name__ == "__main__":
    unittest.main()

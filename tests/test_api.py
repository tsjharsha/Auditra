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

    def test_controller_run_rejects_oversized_record_count(self) -> None:
        client = TestClient(app)
        response = client.post("/controller/runs", json={"mode": "MIXED", "record_count": 50000, "seed": 42})

        self.assertEqual(response.status_code, 422)

    def test_submission_report_exports(self) -> None:
        client = TestClient(app)
        world_response = client.post(
            "/challenges/settlement-reconciliation/build",
            json={"record_count": 60, "seed": 7},
        )
        self.assertEqual(world_response.status_code, 200)
        world = world_response.json()
        audit_response = client.post(f"/worlds/{world['world_id']}/audit")
        self.assertEqual(audit_response.status_code, 200)
        audit = audit_response.json()
        evaluation_run_id = audit["evaluation"]["evaluation_run_id"]

        report_response = client.get(f"/reports/{evaluation_run_id}")
        self.assertEqual(report_response.status_code, 200)
        report = report_response.json()
        self.assertEqual(report["track_fit"]["track"], "Razorpay AI Buildathon Track 04 - AI Finance Controller")
        self.assertIn("controller_run", report)
        self.assertIn("assurance", report)
        self.assertIn("exception_false_negative_rate", report["evaluation"]["metrics"])
        self.assertIn("metric_definitions", report)

        brief_response = client.get(f"/reports/{evaluation_run_id}/settlement-brief")
        self.assertEqual(brief_response.status_code, 200)
        self.assertEqual(brief_response.json()["mode"], "DETERMINISTIC_SETTLEMENT_BRIEF")
        self.assertEqual(len(brief_response.json()["answers"]), 3)

        csv_response = client.get(f"/reports/{evaluation_run_id}/exceptions.csv")
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response.headers["content-type"])
        self.assertTrue(csv_response.text.startswith("case_id,payment_id,status"))

    def test_ingestion_rejects_oversized_entity_payload(self) -> None:
        client = TestClient(app)
        response = client.post("/ingest/json", json={"payload": {"orders": [{} for _ in range(10001)]}, "seed": 42})

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

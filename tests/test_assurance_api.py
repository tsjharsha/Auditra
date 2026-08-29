from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient

from auditra.api import app


class AssuranceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_challenge_build_locks_ground_truth(self) -> None:
        response = self.client.post(
            "/challenges/settlement-reconciliation/build", json={"record_count": 60, "seed": 21}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["ground_truth"]["status"], "LOCKED")
        self.assertNotIn("ground_truth", body["dataset"])

    def test_assurance_and_targeted_red_team_contract(self) -> None:
        built = self.client.post(
            "/challenges/settlement-reconciliation/build", json={"record_count": 60, "seed": 22}
        ).json()
        audit = self.client.post(f"/worlds/{built['world_id']}/audit").json()
        evaluation_id = audit["evaluation"]["evaluation_run_id"]
        report_response = self.client.get(f"/audits/{evaluation_id}/assurance")
        self.assertEqual(report_response.status_code, 200)
        report = report_response.json()
        self.assertIn("score", report)
        self.assertIn("failure_fingerprint", report)
        self.assertNotIn("ground_truth", report)
        attack_response = self.client.post(
            f"/audits/{evaluation_id}/red-team", json={"record_count": 50, "seed": 99}
        )
        self.assertEqual(attack_response.status_code, 200)
        attack = attack_response.json()
        self.assertEqual(attack["generated_cases"], 50)
        self.assertIn("targeted_failure_replay", attack["world"]["spec"]["constraints"])
        self.assertIn("verdict", attack["comparison"])
        self.assertNotIn("ground_truth", attack["world"]["dataset"])


if __name__ == "__main__":
    unittest.main()

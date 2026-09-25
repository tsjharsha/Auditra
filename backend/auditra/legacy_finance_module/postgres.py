from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class PostgresRepository:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("AUDITRA_DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("AUDITRA_DATABASE_URL is not configured")
        try:
            import psycopg
        except Exception as exc:
            raise RuntimeError("psycopg is required for PostgreSQL persistence") from exc
        self.psycopg = psycopg

    def upsert_world(self, world_id: str, dataset_id: str, payload: Dict[str, Any]) -> None:
        self._execute(
            """
            insert into worlds (world_id, dataset_id, payload)
            values (%s, %s, %s::jsonb)
            on conflict (world_id) do update set dataset_id = excluded.dataset_id, payload = excluded.payload, updated_at = now()
            """,
            (world_id, dataset_id, json.dumps(payload)),
        )

    def upsert_dataset(self, dataset_id: str, payload: Dict[str, Any]) -> None:
        self._execute(
            """
            insert into datasets (dataset_id, payload)
            values (%s, %s::jsonb)
            on conflict (dataset_id) do update set payload = excluded.payload, updated_at = now()
            """,
            (dataset_id, json.dumps(payload)),
        )

    def replace_ground_truth(self, dataset_id: str, ground_truth: Dict[str, Any]) -> None:
        with self.psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("delete from ground_truth_cases where dataset_id = %s", (dataset_id,))
                for payment_id, payload in ground_truth.items():
                    cur.execute(
                        """
                        insert into ground_truth_cases (dataset_id, payment_id, expected_status, scenario, payload)
                        values (%s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            dataset_id,
                            payment_id,
                            str(payload.get("expected_status")),
                            str(payload.get("scenario")),
                            json.dumps(payload),
                        ),
                    )
            conn.commit()

    def upsert_controller_run(self, run_id: str, dataset_id: str, payload: Dict[str, Any]) -> None:
        self._execute(
            """
            insert into controller_runs (run_id, dataset_id, payload)
            values (%s, %s, %s::jsonb)
            on conflict (run_id) do update set payload = excluded.payload, updated_at = now()
            """,
            (run_id, dataset_id, json.dumps(payload)),
        )

    def upsert_evaluation_run(self, evaluation_run_id: str, controller_run_id: str, dataset_id: str, payload: Dict[str, Any]) -> None:
        self._execute(
            """
            insert into evaluation_runs (evaluation_run_id, controller_run_id, dataset_id, payload)
            values (%s, %s, %s, %s::jsonb)
            on conflict (evaluation_run_id) do update set payload = excluded.payload, updated_at = now()
            """,
            (evaluation_run_id, controller_run_id, dataset_id, json.dumps(payload)),
        )

    def insert_human_review(self, case_id: str, payload: Dict[str, Any]) -> None:
        self._execute(
            "insert into human_reviews (case_id, payload) values (%s, %s::jsonb)",
            (case_id, json.dumps(payload)),
        )

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        with self.psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()


def optional_postgres_repository() -> Optional[PostgresRepository]:
    if not os.getenv("AUDITRA_DATABASE_URL"):
        return None
    return PostgresRepository()

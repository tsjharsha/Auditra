from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .financial_world import FinancialWorldSpec
from .models import ReviewRequest, ScenarioMode, ScenarioRequest
from .storage import AuditraStore


class ControllerRunRequest(BaseModel):
    dataset_id: Optional[str] = None
    mode: ScenarioMode = ScenarioMode.MIXED
    record_count: int = Field(default=1000, ge=10, le=10000)
    seed: int = 42


class EvaluationRunRequest(BaseModel):
    dataset_id: Optional[str] = None
    controller_run_id: Optional[str] = None
    mode: ScenarioMode = ScenarioMode.MIXED
    record_count: int = Field(default=1000, ge=10, le=10000)
    seed: int = 42


class WorldPromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    seed: int = 42


class SourceIngestionRequest(BaseModel):
    payload: Dict[str, Any]
    seed: int = 42

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        encoded = json.dumps(value, default=str).encode("utf-8")
        if len(encoded) > 2_000_000:
            raise ValueError("ingestion payload exceeds 2MB limit")
        for key in ("merchants", "orders", "payments", "settlements", "refunds", "fees", "fee_rules"):
            rows = value.get(key)
            if isinstance(rows, list) and len(rows) > 10000:
                raise ValueError(f"{key} exceeds 10000 row ingestion limit")
        return value


store = AuditraStore()
app = FastAPI(
    title="Auditra API",
    version="0.1.0",
    description="Autonomous financial control you can verify.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "AUDITRA_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173",
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _public_dataset(dataset) -> Dict[str, Any]:
    return {
        "dataset_id": dataset.dataset_id,
        "mode": dataset.mode,
        "seed": dataset.seed,
        "requested_records": dataset.requested_records,
        "generated_at": dataset.generated_at,
        "counts": {
            "merchants": len(dataset.merchants),
            "orders": len(dataset.orders),
            "payments": len(dataset.payments),
            "settlements": len(dataset.settlements),
            "refunds": len(dataset.refunds),
            "fee_rules": len(dataset.fee_rules),
        },
    }


def _get_run_or_latest(run_id: Optional[str]):
    try:
        return store.get_controller_run(run_id) if run_id else store.latest_run()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "healthy", "product": "Auditra"}


@app.post("/datasets")
def create_dataset(request: ScenarioRequest) -> Dict[str, Any]:
    dataset = store.create_dataset(request)
    return _public_dataset(dataset)


@app.get("/datasets")
def list_datasets() -> Dict[str, Any]:
    return {"datasets": [_public_dataset(dataset) for dataset in store.list_datasets()]}


@app.post("/worlds/preview")
def preview_world(request: WorldPromptRequest) -> Dict[str, Any]:
    try:
        preview = store.preview_world_from_prompt(request.prompt, seed=request.seed)
        return {
            "spec": preview["spec"].model_dump(mode="json"),
            "schema_preview": preview["schema_preview"].model_dump(mode="json"),
            "relationship_model": preview["relationship_model"].model_dump(mode="json"),
            "understanding_steps": [item.model_dump(mode="json") for item in preview["understanding_steps"]],
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/worlds/build")
def build_world(request: WorldPromptRequest) -> Dict[str, Any]:
    try:
        result = store.build_world_from_prompt(request.prompt, seed=request.seed)
        return store.world_service.public_build_result(result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/worlds/spec")
def build_world_from_spec(spec: FinancialWorldSpec) -> Dict[str, Any]:
    try:
        result = store.build_world_from_spec(spec)
        return store.world_service.public_build_result(result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/worlds")
def list_worlds() -> Dict[str, Any]:
    return {
        "worlds": [
            store.world_service.public_build_result(result)
            for result in store.list_worlds()
        ]
    }


@app.post("/worlds/{world_id}/audit")
def audit_world(world_id: str) -> Dict[str, Any]:
    try:
        world = store.get_world(world_id)
        controller_run = store.run_controller(world.dataset_id)
        evaluation = store.run_evaluation(world.dataset_id, controller_run.run_id)
        comparison = store.compare_controllers(world.dataset_id)
        return {
            "world": store.world_service.public_build_result(world),
            "controller_run": controller_run.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
            "comparison": comparison,
            "survival_status": "CONTROLLER SURVIVED" if not evaluation.failures else f"CONTROLLER FAILED {len(evaluation.failures)} CASES",
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/worlds/{world_id}")
def get_world(world_id: str) -> Dict[str, Any]:
    try:
        return store.world_service.public_build_result(store.get_world(world_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/ingest/{adapter}")
def ingest_source(adapter: str, request: SourceIngestionRequest) -> Dict[str, Any]:
    try:
        result = store.ingest_source(adapter, request.payload, seed=request.seed)
        return store.world_service.public_ingestion_result(result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/controller/runs")
def create_controller_run(request: ControllerRunRequest) -> Dict[str, Any]:
    try:
        dataset_id = request.dataset_id
        if not dataset_id:
            dataset = store.create_dataset(
                ScenarioRequest(mode=request.mode, record_count=request.record_count, seed=request.seed)
            )
            dataset_id = dataset.dataset_id
        run = store.run_controller(dataset_id)
        return run.model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/controller/runs/{run_id}")
def get_controller_run(run_id: str) -> Dict[str, Any]:
    try:
        return store.get_controller_run(run_id).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/reconciliation")
def list_reconciliation(
    run_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    cases = run.cases
    if status:
        cases = [case for case in cases if str(case.status) == status]
    return {
        "run_id": run.run_id,
        "count": len(cases),
        "cases": [case.model_dump(mode="json") for case in cases[:limit]],
    }


@app.get("/reconciliation/{case_id}")
def get_reconciliation_case(case_id: str, run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    for case in run.cases:
        if case.case_id == case_id:
            return case.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="case not found")


@app.get("/exceptions")
def list_exceptions(run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    cases = [
        case for case in run.cases
        if str(case.status) not in {"MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"}
    ]
    return {"run_id": run.run_id, "count": len(cases), "cases": [case.model_dump(mode="json") for case in cases]}


@app.get("/exceptions/{case_id}")
def get_exception(case_id: str, run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    case = get_reconciliation_case(case_id, run_id)
    if case["status"] in {"MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"}:
        raise HTTPException(status_code=404, detail="case is not an exception")
    return case


@app.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: str, run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    for case in run.cases:
        for item in case.evidence:
            if item.evidence_id == evidence_id:
                return item.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="evidence not found")


@app.get("/graph/{transaction_id}")
def get_graph(transaction_id: str, run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    for case in run.cases:
        if case.payment_id == transaction_id:
            return case.graph.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="transaction graph not found")


@app.post("/investigations/{case_id}/run")
def rerun_investigation(case_id: str, run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    dataset = store.get_dataset(run.dataset_id)
    new_run = store.run_controller(dataset.dataset_id)
    for case in new_run.cases:
        if case.case_id == case_id:
            return case.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="case not found in rerun")


@app.post("/review/{case_id}")
def review_case(case_id: str, request: ReviewRequest, run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    for case in run.cases:
        if case.case_id == case_id:
            event = {
                "case_id": case_id,
                "action": request.action,
                "reviewer": request.reviewer,
                "note": request.note,
                "recorded": True,
            }
            return store.record_review(event)
    raise HTTPException(status_code=404, detail="case not found")


@app.get("/audit")
def list_audit(run_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    run = _get_run_or_latest(run_id)
    return {"run_id": run.run_id, "events": [event.model_dump(mode="json") for event in run.audit_events]}


@app.post("/evaluation/scenarios")
def create_evaluation_scenario(request: ScenarioRequest) -> Dict[str, Any]:
    dataset = store.create_dataset(request)
    return _public_dataset(dataset)


@app.post("/evaluation/runs")
def create_evaluation_run(request: EvaluationRunRequest) -> Dict[str, Any]:
    try:
        dataset_id = request.dataset_id
        if not dataset_id:
            dataset = store.create_dataset(
                ScenarioRequest(mode=request.mode, record_count=request.record_count, seed=request.seed)
            )
            dataset_id = dataset.dataset_id
        evaluation = store.run_evaluation(dataset_id, request.controller_run_id)
        return evaluation.model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/evaluation/compare")
def compare_controller_modes(request: EvaluationRunRequest) -> Dict[str, Any]:
    try:
        dataset_id = request.dataset_id
        if not dataset_id:
            dataset = store.create_dataset(
                ScenarioRequest(mode=request.mode, record_count=request.record_count, seed=request.seed)
            )
            dataset_id = dataset.dataset_id
        return store.compare_controllers(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/evaluation/runs/{evaluation_run_id}")
def get_evaluation_run(evaluation_run_id: str) -> Dict[str, Any]:
    try:
        return store.get_evaluation_run(evaluation_run_id).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/evaluation/runs/{evaluation_run_id}/failures")
def get_evaluation_failures(evaluation_run_id: str) -> Dict[str, Any]:
    try:
        evaluation = store.get_evaluation_run(evaluation_run_id)
        return {
            "evaluation_run_id": evaluation.evaluation_run_id,
            "count": len(evaluation.failures),
            "failures": [failure.model_dump(mode="json") for failure in evaluation.failures],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/demo")
def demo_mode(request: ScenarioRequest = ScenarioRequest(mode=ScenarioMode.MIXED, record_count=1000, seed=42)) -> Dict[str, Any]:
    dataset = store.create_dataset(request)
    controller_run = store.run_controller(dataset.dataset_id)
    evaluation = store.run_evaluation(dataset.dataset_id, controller_run.run_id)
    return {
        "dataset": _public_dataset(dataset),
        "controller_run": {
            "run_id": controller_run.run_id,
            "metrics": controller_run.metrics.model_dump(mode="json"),
        },
        "evaluation": evaluation.model_dump(mode="json"),
        "survival_status": "CONTROLLER SURVIVED" if not evaluation.failures else f"CONTROLLER FAILED {len(evaluation.failures)} CASES",
    }

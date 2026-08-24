from __future__ import annotations

from typing import Dict, List, Optional

from .evaluator import IndependentEvaluator
from .financial_world import AdapterIngestionResult, FinancialWorldBuildResult, FinancialWorldService, FinancialWorldSpec
from .models import ControllerRun, DatasetBundle, EvaluationRun, ReviewRequest, ScenarioRequest
from .postgres import optional_postgres_repository
from .reconciliation import ReconciliationEngine
from .scenario_generator import ScenarioGenerator


class AuditraStore:
    def __init__(self):
        self.generator = ScenarioGenerator()
        self.world_service = FinancialWorldService()
        self.controller = ReconciliationEngine()
        self.evaluator = IndependentEvaluator()
        self.worlds: Dict[str, FinancialWorldBuildResult] = {}
        self.datasets: Dict[str, DatasetBundle] = {}
        self.controller_runs: Dict[str, ControllerRun] = {}
        self.evaluation_runs: Dict[str, EvaluationRun] = {}
        self.review_events: List[Dict[str, object]] = []
        self.postgres = optional_postgres_repository()
        self.latest_world_id: Optional[str] = None
        self.latest_dataset_id: Optional[str] = None
        self.latest_run_id: Optional[str] = None
        self.latest_evaluation_id: Optional[str] = None

    def create_dataset(self, request: ScenarioRequest) -> DatasetBundle:
        dataset = self.generator.generate(request)
        self.datasets[dataset.dataset_id] = dataset
        self._persist_dataset(dataset)
        self.latest_dataset_id = dataset.dataset_id
        return dataset

    def build_world_from_prompt(self, prompt: str, seed: int = 42) -> FinancialWorldBuildResult:
        result = self.world_service.build_from_prompt(prompt, seed=seed)
        self._store_world_result(result)
        return result

    def build_world_from_spec(self, spec: FinancialWorldSpec) -> FinancialWorldBuildResult:
        result = self.world_service.build_from_spec(spec)
        self._store_world_result(result)
        return result

    def preview_world_from_prompt(self, prompt: str, seed: int = 42) -> Dict[str, object]:
        spec, steps = self.world_service.understand(prompt, seed=seed)
        preview = self.world_service.preview(spec)
        preview["understanding_steps"] = steps
        return preview

    def ingest_source(self, adapter: str, payload: Dict[str, object], seed: int = 42) -> AdapterIngestionResult:
        result = self.world_service.ingest(adapter, payload, seed=seed)
        if result.dataset:
            self.datasets[result.dataset.dataset_id] = result.dataset
            self._persist_dataset(result.dataset)
            self.latest_dataset_id = result.dataset.dataset_id
        return result

    def list_worlds(self) -> List[FinancialWorldBuildResult]:
        return sorted(self.worlds.values(), key=lambda item: item.spec.start_at, reverse=True)

    def get_world(self, world_id: str) -> FinancialWorldBuildResult:
        if world_id not in self.worlds:
            raise KeyError(f"world not found: {world_id}")
        return self.worlds[world_id]

    def _store_world_result(self, result: FinancialWorldBuildResult) -> None:
        self.worlds[result.world_id] = result
        if result.dataset:
            self.datasets[result.dataset.dataset_id] = result.dataset
            self._persist_dataset(result.dataset)
            self.latest_dataset_id = result.dataset.dataset_id
        self.latest_world_id = result.world_id
        if self.postgres:
            self.postgres.upsert_world(
                result.world_id,
                result.dataset_id,
                result.model_dump(mode="json", exclude={"dataset"}),
            )

    def list_datasets(self) -> List[DatasetBundle]:
        return sorted(self.datasets.values(), key=lambda item: item.generated_at, reverse=True)

    def get_dataset(self, dataset_id: str) -> DatasetBundle:
        if dataset_id not in self.datasets:
            raise KeyError(f"dataset not found: {dataset_id}")
        return self.datasets[dataset_id]

    def run_controller(self, dataset_id: str) -> ControllerRun:
        dataset = self.get_dataset(dataset_id)
        run = self.controller.run(dataset)
        self.controller_runs[run.run_id] = run
        if self.postgres:
            self.postgres.upsert_controller_run(run.run_id, dataset_id, run.model_dump(mode="json"))
        self.latest_run_id = run.run_id
        return run

    def get_controller_run(self, run_id: str) -> ControllerRun:
        if run_id not in self.controller_runs:
            raise KeyError(f"controller run not found: {run_id}")
        return self.controller_runs[run_id]

    def run_evaluation(self, dataset_id: str, controller_run_id: Optional[str] = None) -> EvaluationRun:
        dataset = self.get_dataset(dataset_id)
        if controller_run_id:
            controller_run = self.get_controller_run(controller_run_id)
        else:
            controller_run = self.run_controller(dataset_id)
        evaluation = self.evaluator.evaluate(dataset, controller_run)
        self.evaluation_runs[evaluation.evaluation_run_id] = evaluation
        if self.postgres:
            self.postgres.upsert_evaluation_run(
                evaluation.evaluation_run_id,
                controller_run.run_id,
                dataset_id,
                evaluation.model_dump(mode="json"),
            )
        self.latest_evaluation_id = evaluation.evaluation_run_id
        return evaluation

    def compare_controllers(self, dataset_id: str) -> Dict[str, object]:
        dataset = self.get_dataset(dataset_id)
        rows = []
        for label, enable_ai in (("deterministic_only", False), ("ai_assisted", True)):
            run = ReconciliationEngine(enable_ai=enable_ai).run(dataset)
            evaluation = self.evaluator.evaluate(dataset, run)
            self.controller_runs[run.run_id] = run
            self.evaluation_runs[evaluation.evaluation_run_id] = evaluation
            rows.append(
                {
                    "mode": label,
                    "controller_run_id": run.run_id,
                    "evaluation_run_id": evaluation.evaluation_run_id,
                    "metrics": evaluation.metrics.model_dump(mode="json"),
                    "controller_metrics": run.metrics.model_dump(mode="json"),
                    "failures": len(evaluation.failures),
                }
            )
        self.latest_run_id = rows[-1]["controller_run_id"]  # type: ignore[index]
        self.latest_evaluation_id = rows[-1]["evaluation_run_id"]  # type: ignore[index]
        return {"dataset_id": dataset_id, "comparison": rows}

    def record_review(self, event: Dict[str, object]) -> Dict[str, object]:
        self.review_events.append(event)
        if self.postgres:
            self.postgres.insert_human_review(str(event.get("case_id")), event)
        return event

    def _persist_dataset(self, dataset: DatasetBundle) -> None:
        if not self.postgres:
            return
        visible_dataset = dataset.model_copy(update={"ground_truth": {}})
        self.postgres.upsert_dataset(dataset.dataset_id, visible_dataset.model_dump(mode="json"))
        self.postgres.replace_ground_truth(
            dataset.dataset_id,
            {key: value.model_dump(mode="json") for key, value in dataset.ground_truth.items()},
        )

    def get_evaluation_run(self, evaluation_run_id: str) -> EvaluationRun:
        if evaluation_run_id not in self.evaluation_runs:
            raise KeyError(f"evaluation run not found: {evaluation_run_id}")
        return self.evaluation_runs[evaluation_run_id]

    def latest_run(self) -> ControllerRun:
        if not self.latest_run_id:
            raise KeyError("no controller run exists")
        return self.get_controller_run(self.latest_run_id)

    def latest_evaluation(self) -> EvaluationRun:
        if not self.latest_evaluation_id:
            raise KeyError("no evaluation run exists")
        return self.get_evaluation_run(self.latest_evaluation_id)

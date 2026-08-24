from __future__ import annotations

from typing import Dict, List, Optional

from .evaluator import IndependentEvaluator
from .models import ControllerRun, DatasetBundle, EvaluationRun, ReviewAction, ReviewRequest, ScenarioRequest
from .reconciliation import ReconciliationEngine
from .scenario_generator import ScenarioGenerator


class AuditraStore:
    def __init__(self):
        self.generator = ScenarioGenerator()
        self.controller = ReconciliationEngine()
        self.evaluator = IndependentEvaluator()
        self.datasets: Dict[str, DatasetBundle] = {}
        self.controller_runs: Dict[str, ControllerRun] = {}
        self.evaluation_runs: Dict[str, EvaluationRun] = {}
        self.latest_dataset_id: Optional[str] = None
        self.latest_run_id: Optional[str] = None
        self.latest_evaluation_id: Optional[str] = None

    def create_dataset(self, request: ScenarioRequest) -> DatasetBundle:
        dataset = self.generator.generate(request)
        self.datasets[dataset.dataset_id] = dataset
        self.latest_dataset_id = dataset.dataset_id
        return dataset

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
        self.latest_evaluation_id = evaluation.evaluation_run_id
        return evaluation

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

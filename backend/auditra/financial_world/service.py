from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ..models import DatasetBundle
from .adapters import CSVAdapter, JSONAdapter, RazorpayTestAdapter
from .generator import FinancialWorldGenerator
from .models import AdapterIngestionResult, FinancialWorldBuildResult, FinancialWorldSpec
from .schema import build_relationship_model, build_schema_preview
from .understanding import WorldUnderstandingService
from .validation import WorldValidator


class FinancialWorldService:
    def __init__(self):
        self.understanding = WorldUnderstandingService()
        self.generator = FinancialWorldGenerator()
        self.validator = WorldValidator()
        self.adapters = {
            "csv": CSVAdapter(),
            "json": JSONAdapter(),
            "razorpay_test": RazorpayTestAdapter(),
        }

    def understand(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, list]:
        return self.understanding.understand(prompt, seed=seed)

    def preview(self, spec: FinancialWorldSpec) -> Dict[str, Any]:
        return {
            "spec": spec,
            "schema_preview": build_schema_preview(),
            "relationship_model": build_relationship_model(),
        }

    def build_from_prompt(self, prompt: str, seed: int = 42) -> FinancialWorldBuildResult:
        spec, steps = self.understanding.understand(prompt, seed=seed)
        return self.build_from_spec(spec, steps=steps)

    def build_from_spec(self, spec: FinancialWorldSpec, steps: list | None = None) -> FinancialWorldBuildResult:
        world_id, dataset, summary = self.generator.generate(spec)
        validation = self.validator.validate(world_id, dataset)
        if not validation.valid:
            raise ValueError("generated world failed validation")
        return FinancialWorldBuildResult(
            world_id=world_id,
            world_version=spec.version,
            prompt=spec.prompt,
            spec=spec,
            schema_preview=build_schema_preview(),
            relationship_model=build_relationship_model(),
            understanding_steps=steps or [],
            validation=validation,
            summary=summary,
            dataset_id=dataset.dataset_id,
            dataset=dataset,
        )

    def ingest(self, adapter: str, payload: Mapping[str, Any], seed: int = 42) -> AdapterIngestionResult:
        if adapter not in self.adapters:
            raise KeyError(f"adapter not found: {adapter}")
        return self.adapters[adapter].ingest(payload, seed=seed)

    def public_build_result(self, result: FinancialWorldBuildResult) -> Dict[str, Any]:
        payload = result.model_dump(mode="json", exclude={"dataset"})
        payload["dataset"] = self.public_dataset(result.dataset) if result.dataset else None
        return payload

    def public_ingestion_result(self, result: AdapterIngestionResult) -> Dict[str, Any]:
        payload = result.model_dump(mode="json", exclude={"dataset"})
        payload["dataset"] = self.public_dataset(result.dataset) if result.dataset else None
        return payload

    def public_dataset(self, dataset: DatasetBundle | None) -> Dict[str, Any] | None:
        if dataset is None:
            return None
        return {
            "dataset_id": dataset.dataset_id,
            "mode": dataset.mode,
            "seed": dataset.seed,
            "requested_records": dataset.requested_records,
            "generated_at": dataset.generated_at.isoformat(),
            "counts": {
                "merchants": len(dataset.merchants),
                "orders": len(dataset.orders),
                "payments": len(dataset.payments),
                "settlements": len(dataset.settlements),
                "refunds": len(dataset.refunds),
                "fee_rules": len(dataset.fee_rules),
            },
            "records": {
                "merchants": [item.model_dump(mode="json") for item in dataset.merchants],
                "orders": [item.model_dump(mode="json") for item in dataset.orders],
                "payments": [item.model_dump(mode="json") for item in dataset.payments],
                "settlements": [item.model_dump(mode="json") for item in dataset.settlements],
                "refunds": [item.model_dump(mode="json") for item in dataset.refunds],
                "fee_rules": [item.model_dump(mode="json") for item in dataset.fee_rules],
            },
        }

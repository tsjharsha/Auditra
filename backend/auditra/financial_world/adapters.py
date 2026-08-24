from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from typing import Any, Dict, List, Mapping

from ..models import DatasetBundle, FeeRule, Merchant, Order, Payment, Refund, ScenarioMode, Settlement
from .models import AdapterIngestionResult
from .validation import WorldValidator


class FinancialSourceAdapter:
    name = "base"

    def ingest(self, payload: Mapping[str, Any], seed: int = 42) -> AdapterIngestionResult:
        raise NotImplementedError


class CanonicalRecordBuilder:
    def __init__(self, source: str, seed: int = 42):
        self.source = source
        self.seed = seed
        self.base_time = datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc)

    def dataset(self, rows: Mapping[str, List[Dict[str, Any]]]) -> DatasetBundle:
        merchants = [self.merchant(idx, row) for idx, row in enumerate(rows.get("merchants", []), start=1)]
        orders = [self.order(idx, row) for idx, row in enumerate(rows.get("orders", []), start=1)]
        payments = [self.payment(idx, row) for idx, row in enumerate(rows.get("payments", []), start=1)]
        settlements = [self.settlement(idx, row) for idx, row in enumerate(rows.get("settlements", []), start=1)]
        refunds = [self.refund(idx, row) for idx, row in enumerate(rows.get("refunds", []), start=1)]
        fee_rows = rows.get("fee_rules") or rows.get("fees") or []
        fee_rules = [self.fee_rule(idx, row) for idx, row in enumerate(fee_rows, start=1)]

        merchant_ids = {merchant.merchant_id for merchant in merchants}
        for merchant_id in sorted({payment.merchant_id for payment in payments} - merchant_ids):
            merchants.append(
                Merchant(
                    source=self.source,
                    source_record_id=f"{self.source}_MERCHANT_{merchant_id}",
                    ingested_at=self.base_time,
                    merchant_id=merchant_id,
                    name=merchant_id,
                    settlement_cycle_days=2,
                )
            )
        fee_merchants = {rule.merchant_id for rule in fee_rules}
        for merchant in merchants:
            if merchant.merchant_id not in fee_merchants:
                fee_rules.append(
                    FeeRule(
                        source=self.source,
                        source_record_id=f"{self.source}_FEE_{merchant.merchant_id}",
                        ingested_at=self.base_time,
                        fee_rule_id=f"FEE_{merchant.merchant_id}",
                        merchant_id=merchant.merchant_id,
                        currency="INR",
                        percent_bps=200,
                        fixed_fee=Decimal("0.00"),
                        active_from=self.base_time - timedelta(days=365),
                    )
                )

        dataset_id = self._dataset_id(rows)
        return DatasetBundle(
            dataset_id=dataset_id,
            mode=ScenarioMode.MIXED,
            seed=self.seed,
            requested_records=len(payments),
            generated_at=self.base_time,
            merchants=merchants,
            orders=orders,
            payments=payments,
            settlements=settlements,
            refunds=refunds,
            fee_rules=fee_rules,
            ground_truth={},
        )

    def merchant(self, idx: int, row: Dict[str, Any]) -> Merchant:
        return Merchant(
            source=self.source,
            source_record_id=str(row.get("source_record_id") or f"{self.source}_MERCHANT_{idx}"),
            ingested_at=self._time(row.get("ingested_at"), idx),
            merchant_id=str(row.get("merchant_id") or f"MCH_{idx:04d}"),
            name=str(row.get("name") or row.get("merchant_name") or f"Merchant {idx}"),
            settlement_cycle_days=int(row.get("settlement_cycle_days") or 2),
            risk_tier=str(row.get("risk_tier") or "standard"),
            original=dict(row),
        )

    def order(self, idx: int, row: Dict[str, Any]) -> Order:
        return Order(
            source=self.source,
            source_record_id=str(row.get("source_record_id") or f"{self.source}_ORDER_{idx}"),
            ingested_at=self._time(row.get("ingested_at"), idx),
            order_id=str(row.get("order_id") or f"ORD_{idx:05d}"),
            merchant_id=str(row.get("merchant_id") or "MCH_DEFAULT"),
            customer_id=str(row.get("customer_id") or f"CUS_{idx:05d}"),
            amount=Decimal(str(row.get("amount") or "0.00")),
            currency=str(row.get("currency") or "INR"),
            created_at=self._time(row.get("created_at"), idx),
            invoice_id=row.get("invoice_id"),
            reference_id=row.get("reference_id"),
            original=dict(row),
        )

    def payment(self, idx: int, row: Dict[str, Any]) -> Payment:
        return Payment(
            source=self.source,
            source_record_id=str(row.get("source_record_id") or f"{self.source}_PAYMENT_{idx}"),
            ingested_at=self._time(row.get("ingested_at"), idx),
            payment_id=str(row.get("payment_id") or row.get("id") or f"PAY_{idx:05d}"),
            order_id=row.get("order_id"),
            merchant_id=str(row.get("merchant_id") or "MCH_DEFAULT"),
            customer_id=str(row.get("customer_id") or f"CUS_{idx:05d}"),
            amount=Decimal(str(row.get("amount") or "0.00")),
            currency=str(row.get("currency") or "INR"),
            captured_at=self._time(row.get("captured_at") or row.get("created_at"), idx),
            payment_method=str(row.get("payment_method") or row.get("method") or "upi").lower(),
            reference_id=row.get("reference_id"),
            original=dict(row),
        )

    def settlement(self, idx: int, row: Dict[str, Any]) -> Settlement:
        return Settlement(
            source=self.source,
            source_record_id=str(row.get("source_record_id") or f"{self.source}_SETTLEMENT_{idx}"),
            ingested_at=self._time(row.get("ingested_at"), idx),
            settlement_id=str(row.get("settlement_id") or row.get("id") or f"SET_{idx:05d}"),
            payment_id=str(row.get("payment_id") or ""),
            merchant_id=str(row.get("merchant_id") or "MCH_DEFAULT"),
            amount=Decimal(str(row.get("amount") or "0.00")),
            currency=str(row.get("currency") or "INR"),
            settled_at=self._time(row.get("settled_at") or row.get("created_at"), idx),
            batch_id=str(row.get("batch_id") or f"BATCH_{idx // 25:04d}"),
            original=dict(row),
        )

    def refund(self, idx: int, row: Dict[str, Any]) -> Refund:
        return Refund(
            source=self.source,
            source_record_id=str(row.get("source_record_id") or f"{self.source}_REFUND_{idx}"),
            ingested_at=self._time(row.get("ingested_at"), idx),
            refund_id=str(row.get("refund_id") or row.get("id") or f"RFD_{idx:05d}"),
            payment_id=str(row.get("payment_id") or ""),
            merchant_id=str(row.get("merchant_id") or "MCH_DEFAULT"),
            amount=Decimal(str(row.get("amount") or "0.00")),
            currency=str(row.get("currency") or "INR"),
            refunded_at=self._time(row.get("refunded_at") or row.get("created_at"), idx),
            reason=str(row.get("reason") or "customer_request"),
            original=dict(row),
        )

    def fee_rule(self, idx: int, row: Dict[str, Any]) -> FeeRule:
        percent_bps = row.get("percent_bps")
        if percent_bps is None and row.get("fee_rate") is not None:
            percent_bps = int(Decimal(str(row["fee_rate"])) * Decimal("10000"))
        return FeeRule(
            source=self.source,
            source_record_id=str(row.get("source_record_id") or f"{self.source}_FEE_{idx}"),
            ingested_at=self._time(row.get("ingested_at"), idx),
            fee_rule_id=str(row.get("fee_rule_id") or f"FEE_{idx:04d}"),
            merchant_id=str(row.get("merchant_id") or "MCH_DEFAULT"),
            currency=str(row.get("currency") or "INR"),
            percent_bps=int(percent_bps or 200),
            fixed_fee=Decimal(str(row.get("fixed_fee") or "0.00")),
            active_from=self._time(row.get("active_from"), idx) if row.get("active_from") else self.base_time - timedelta(days=365),
            original=dict(row),
        )

    def _time(self, value: Any, idx: int) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if value:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return self.base_time + timedelta(minutes=idx)

    def _dataset_id(self, rows: Mapping[str, List[Dict[str, Any]]]) -> str:
        digest = hashlib.sha256(repr(sorted((key, len(value)) for key, value in rows.items())).encode("utf-8")).hexdigest()[:12]
        return f"INGEST_{self.source.upper()}_{digest}"


class JSONAdapter(FinancialSourceAdapter):
    name = "json"

    def ingest(self, payload: Mapping[str, Any], seed: int = 42) -> AdapterIngestionResult:
        rows = {key: list(value or []) for key, value in payload.items() if isinstance(value, list)}
        dataset = CanonicalRecordBuilder(self.name, seed=seed).dataset(rows)
        validation = WorldValidator().validate(dataset.dataset_id, dataset)
        return AdapterIngestionResult(
            adapter=self.name,
            dataset_id=dataset.dataset_id,
            rows_seen={key: len(value) for key, value in rows.items()},
            rows_loaded={
                "merchants": len(dataset.merchants),
                "orders": len(dataset.orders),
                "payments": len(dataset.payments),
                "settlements": len(dataset.settlements),
                "refunds": len(dataset.refunds),
                "fee_rules": len(dataset.fee_rules),
            },
            validation=validation,
            dataset=dataset,
        )


class CSVAdapter(FinancialSourceAdapter):
    name = "csv"

    def ingest(self, payload: Mapping[str, Any], seed: int = 42) -> AdapterIngestionResult:
        rows: Dict[str, List[Dict[str, Any]]] = {}
        for entity, text in payload.items():
            if not isinstance(text, str) or not text.strip():
                continue
            reader = csv.DictReader(StringIO(text))
            rows[entity] = [dict(row) for row in reader]
        dataset = CanonicalRecordBuilder(self.name, seed=seed).dataset(rows)
        validation = WorldValidator().validate(dataset.dataset_id, dataset)
        return AdapterIngestionResult(
            adapter=self.name,
            dataset_id=dataset.dataset_id,
            rows_seen={key: len(value) for key, value in rows.items()},
            rows_loaded={
                "merchants": len(dataset.merchants),
                "orders": len(dataset.orders),
                "payments": len(dataset.payments),
                "settlements": len(dataset.settlements),
                "refunds": len(dataset.refunds),
                "fee_rules": len(dataset.fee_rules),
            },
            validation=validation,
            dataset=dataset,
        )


class RazorpayTestAdapter(JSONAdapter):
    name = "razorpay_test"

    def ingest(self, payload: Mapping[str, Any], seed: int = 42) -> AdapterIngestionResult:
        canonical = {
            "payments": payload.get("payments", []),
            "orders": payload.get("orders", []),
            "settlements": payload.get("settlements", []),
            "refunds": payload.get("refunds", []),
            "fees": payload.get("fees", []),
            "merchants": payload.get("merchants", []),
        }
        result = super().ingest(canonical, seed=seed)
        result.adapter = self.name
        return result

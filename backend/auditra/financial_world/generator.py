from __future__ import annotations

import hashlib
import random
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from ..models import (
    DatasetBundle,
    FeeRule,
    GroundTruthCase,
    Merchant,
    Order,
    Payment,
    ReconciliationStatus,
    Refund,
    Settlement,
    money,
)
from .models import AnomalyMode, FinancialWorldSpec, WorldSummary


HEALTHY_STATUSES = {
    ReconciliationStatus.MATCHED.value,
    ReconciliationStatus.FEE_EXPLAINED.value,
    ReconciliationStatus.REFUND_ADJUSTED.value,
}


class FinancialWorldGenerator:
    def generate(self, spec: FinancialWorldSpec) -> Tuple[str, DatasetBundle, WorldSummary]:
        rng = random.Random(self._seed(spec))
        world_id = self._world_id(spec)
        base_time = spec.start_at
        merchant = Merchant(
            source="financial_world_builder",
            source_record_id=f"{world_id}_MERCHANT",
            ingested_at=base_time,
            merchant_id=f"MCH_{world_id[-8:]}",
            name=spec.merchant_name,
            settlement_cycle_days=spec.settlement_delay_days,
            risk_tier="elevated" if self._mode_value(spec) in (AnomalyMode.ADVERSARIAL.value, AnomalyMode.CHAOS.value) else "standard",
            original={"world_id": world_id, "country": spec.country},
        )
        fee_rule = FeeRule(
            source="financial_world_builder",
            source_record_id=f"{world_id}_FEE_RULE",
            ingested_at=base_time,
            fee_rule_id=f"FEE_{world_id[-8:]}",
            merchant_id=merchant.merchant_id,
            currency=spec.currencies[0],
            percent_bps=int(spec.fee_rate * Decimal("10000")),
            fixed_fee=spec.fixed_fee,
            active_from=base_time - timedelta(days=365),
            original={"world_id": world_id, "fee_rate": str(spec.fee_rate)},
        )

        orders: List[Order] = []
        payments: List[Payment] = []
        settlements: List[Settlement] = []
        refunds: List[Refund] = []
        ground_truth: Dict[str, GroundTruthCase] = {}
        anomaly_plan = self._anomaly_plan(spec, rng)
        anomaly_counts: Dict[str, int] = {}

        previous_payment: Payment | None = None
        previous_order: Order | None = None
        for idx, anomaly in enumerate(anomaly_plan, start=1):
            amount = self._amount(rng)
            customer_id = f"CUS_{rng.randint(100000, 999999)}"
            currency = rng.choice(spec.currencies)
            order = Order(
                source="financial_world_builder",
                source_record_id=f"{world_id}_ORDER_{idx:05d}",
                ingested_at=base_time,
                order_id=f"ORD_{world_id[-6:]}_{idx:05d}",
                merchant_id=merchant.merchant_id,
                customer_id=customer_id,
                amount=amount,
                currency=currency,
                created_at=base_time + timedelta(minutes=idx * 3),
                original={"world_id": world_id},
            )
            orders.append(order)

            payment = self._payment(spec, world_id, idx, order, merchant, rng, currency)
            payments.append(payment)
            expected_fee = fee_rule.calculate_fee(payment.amount)
            refund_amount = Decimal("0.00")
            expected_status = ReconciliationStatus.FEE_EXPLAINED if expected_fee > 0 else ReconciliationStatus.MATCHED
            reason = "payment, fee rule and settlement agree"
            financial_impact = Decimal("0.00")

            if rng.random() < float(spec.refund_rate) and anomaly not in {"ENTITY_LINK_FAILURE", "DUPLICATE_PAYMENT"}:
                refund_amount = self._refund_amount(payment.amount, rng)
                refunds.append(self._refund(world_id, idx, payment, merchant, refund_amount))
                expected_status = ReconciliationStatus.REFUND_ADJUSTED
                reason = "settlement correctly reflects refund and fee"

            expected_settlement = money(payment.amount - expected_fee - refund_amount)
            actual_settlement = expected_settlement
            settlement_time = payment.captured_at + timedelta(days=spec.settlement_delay_days, hours=rng.randint(1, 6))
            create_settlement = True

            if anomaly not in {"NORMAL", "DUPLICATE_PAYMENT"}:
                anomaly_counts[anomaly] = anomaly_counts.get(anomaly, 0) + 1

            if anomaly == "AMOUNT_MISMATCH":
                delta = self._delta(rng)
                actual_settlement = money(expected_settlement + delta)
                expected_status = ReconciliationStatus.AMOUNT_MISMATCH
                financial_impact = abs(delta)
                reason = "settlement amount differs from expected net amount"
            elif anomaly == "MISSING_SETTLEMENT":
                create_settlement = False
                expected_status = ReconciliationStatus.MISSING_SETTLEMENT
                financial_impact = expected_settlement
                reason = "payment has no settlement record"
            elif anomaly == "FEE_MISMATCH":
                delta = self._delta(rng, low=Decimal("8.00"), high=Decimal("90.00"))
                actual_settlement = money(expected_settlement - delta)
                expected_status = ReconciliationStatus.AMOUNT_MISMATCH
                financial_impact = abs(delta)
                reason = "settlement implies a fee that differs from configured fee rule"
            elif anomaly == "REFUND_MISMATCH":
                if refund_amount == 0:
                    refund_amount = self._refund_amount(payment.amount, rng)
                    refunds.append(self._refund(world_id, idx, payment, merchant, refund_amount))
                    expected_settlement = money(payment.amount - expected_fee - refund_amount)
                actual_settlement = money(payment.amount - expected_fee)
                expected_status = ReconciliationStatus.AMOUNT_MISMATCH
                financial_impact = abs(actual_settlement - expected_settlement)
                reason = "refund exists but settlement does not reflect it"
            elif anomaly == "PARTIAL_SETTLEMENT":
                actual_settlement = money(expected_settlement * Decimal(str(rng.uniform(0.35, 0.80))))
                expected_status = ReconciliationStatus.PARTIAL_MATCH
                financial_impact = abs(expected_settlement - actual_settlement)
                reason = "settlement partially covers expected net amount"
            elif anomaly == "TIMING_MISMATCH":
                settlement_time = payment.captured_at + timedelta(days=spec.settlement_delay_days + 9)
                expected_status = ReconciliationStatus.TIMING_MISMATCH
                reason = "settlement amount is correct but outside the settlement window"
            elif anomaly == "CURRENCY_MISMATCH":
                actual_settlement = expected_settlement
                currency = "USD" if payment.currency != "USD" else "INR"
                expected_status = ReconciliationStatus.HUMAN_REVIEW
                reason = "settlement currency conflicts with payment currency"
            elif anomaly == "CONFLICTING_EVIDENCE":
                if refund_amount == 0:
                    refund_amount = self._refund_amount(payment.amount, rng)
                    refunds.append(self._refund(world_id, idx, payment, merchant, refund_amount))
                    expected_settlement = money(payment.amount - expected_fee - refund_amount)
                actual_settlement = money(payment.amount - expected_fee)
                expected_status = ReconciliationStatus.HUMAN_REVIEW
                financial_impact = abs(actual_settlement - expected_settlement)
                reason = "refund evidence conflicts with settlement amount"
            elif anomaly == "ENTITY_LINK_FAILURE":
                payment.order_id = f"ORD_MISSING_{idx:05d}"
                expected_status = ReconciliationStatus.HUMAN_REVIEW
                financial_impact = payment.amount
                reason = "payment cannot be linked to a valid order"

            if create_settlement:
                settlements.append(
                    Settlement(
                        source="financial_world_builder",
                        source_record_id=f"{world_id}_SETTLEMENT_{idx:05d}",
                        ingested_at=base_time,
                        settlement_id=f"SET_{world_id[-6:]}_{idx:05d}",
                        payment_id=payment.payment_id,
                        merchant_id=merchant.merchant_id,
                        amount=actual_settlement,
                        currency=currency,
                        settled_at=settlement_time,
                        batch_id=f"BATCH_{world_id[-6:]}_{idx // 25:04d}",
                        original={"world_id": world_id, "anomaly": anomaly},
                    )
                )

            ground_truth[payment.payment_id] = GroundTruthCase(
                payment_id=payment.payment_id,
                expected_status=expected_status,
                scenario=anomaly.lower(),
                financial_impact=financial_impact,
                reason=reason,
            )

            if anomaly == "DUPLICATE_PAYMENT" and previous_payment and previous_order:
                dup_idx = len(payments) + 1
                duplicate = previous_payment.model_copy(
                    update={
                        "source_record_id": f"{world_id}_PAYMENT_DUP_{idx:05d}",
                        "payment_id": f"PAY_{world_id[-6:]}_DUP_{idx:05d}",
                        "captured_at": payment.captured_at + timedelta(minutes=1),
                        "original": {"world_id": world_id, "duplicate_of": previous_payment.payment_id},
                    }
                )
                payments.append(duplicate)
                ground_truth[duplicate.payment_id] = GroundTruthCase(
                    payment_id=duplicate.payment_id,
                    expected_status=ReconciliationStatus.DUPLICATE,
                    scenario="duplicate_payment",
                    financial_impact=duplicate.amount,
                    reason="payment duplicates an earlier payment for the same order, merchant, amount and customer",
                )
                anomaly_counts["DUPLICATE_PAYMENT"] = anomaly_counts.get("DUPLICATE_PAYMENT", 0) + 1

            previous_payment = payment
            previous_order = order

        dataset = DatasetBundle(
            dataset_id=f"WORLD_{world_id}",
            mode=self._scenario_mode(spec),
            seed=spec.seed,
            requested_records=len(payments),
            generated_at=base_time,
            merchants=[merchant],
            orders=orders,
            payments=payments,
            settlements=settlements,
            refunds=refunds,
            fee_rules=[fee_rule],
            ground_truth=ground_truth,
        )
        summary = self._summary(world_id, spec, dataset, anomaly_counts)
        return world_id, dataset, summary

    def _payment(self, spec: FinancialWorldSpec, world_id: str, idx: int, order: Order, merchant: Merchant, rng: random.Random, currency: str) -> Payment:
        return Payment(
            source="financial_world_builder",
            source_record_id=f"{world_id}_PAYMENT_{idx:05d}",
            ingested_at=spec.start_at,
            payment_id=f"PAY_{world_id[-6:]}_{idx:05d}",
            order_id=order.order_id,
            merchant_id=merchant.merchant_id,
            customer_id=order.customer_id,
            amount=order.amount,
            currency=currency,
            captured_at=order.created_at + timedelta(minutes=rng.randint(2, 45)),
            payment_method=rng.choice(spec.payment_methods).lower(),
            reference_id=f"REF_{world_id[-6:]}_{idx:05d}",
            original={"world_id": world_id},
        )

    def _refund(self, world_id: str, idx: int, payment: Payment, merchant: Merchant, amount: Decimal) -> Refund:
        return Refund(
            source="financial_world_builder",
            source_record_id=f"{world_id}_REFUND_{idx:05d}",
            ingested_at=payment.ingested_at,
            refund_id=f"RFD_{world_id[-6:]}_{idx:05d}",
            payment_id=payment.payment_id,
            merchant_id=merchant.merchant_id,
            amount=amount,
            currency=payment.currency,
            refunded_at=payment.captured_at + timedelta(hours=12),
            reason="customer_request",
            original={"world_id": world_id},
        )

    def _anomaly_plan(self, spec: FinancialWorldSpec, rng: random.Random) -> List[str]:
        names = ["NORMAL"]
        weights = [max(Decimal("0.0000"), Decimal("1.0000") - sum(spec.anomaly_rates.values()))]
        for name, value in sorted(spec.anomaly_rates.items()):
            names.append(name)
            weights.append(value)
        plan = rng.choices(names, weights=[float(item) for item in weights], k=spec.record_count)
        mode = self._mode_value(spec)
        if spec.record_count >= 50 and mode != AnomalyMode.NORMAL.value:
            required = ["AMOUNT_MISMATCH", "MISSING_SETTLEMENT", "DUPLICATE_PAYMENT", "PARTIAL_SETTLEMENT", "TIMING_MISMATCH", "CONFLICTING_EVIDENCE"]
            if mode in (AnomalyMode.ADVERSARIAL.value, AnomalyMode.CHAOS.value):
                required.extend(["REFUND_MISMATCH", "CURRENCY_MISMATCH", "ENTITY_LINK_FAILURE"])
            for offset, name in enumerate(required):
                if offset < len(plan):
                    plan[offset] = name
        return plan

    def _summary(self, world_id: str, spec: FinancialWorldSpec, dataset: DatasetBundle, anomaly_counts: Dict[str, int]) -> WorldSummary:
        payment_volume = money(sum((payment.amount for payment in dataset.payments), Decimal("0.00")))
        settlement_volume = money(sum((settlement.amount for settlement in dataset.settlements), Decimal("0.00")))
        human_review_amount = money(
            sum(
                (
                    payment.amount
                    for payment in dataset.payments
                    if str(dataset.ground_truth[payment.payment_id].expected_status) == ReconciliationStatus.HUMAN_REVIEW.value
                ),
                Decimal("0.00"),
            )
        )
        unresolved_amount = money(
            sum(
                (
                    dataset.ground_truth[payment.payment_id].financial_impact
                    for payment in dataset.payments
                    if str(dataset.ground_truth[payment.payment_id].expected_status) not in HEALTHY_STATUSES
                ),
                Decimal("0.00"),
            )
        )
        return WorldSummary(
            world_id=world_id,
            world_version=spec.version,
            merchant=spec.merchant_name,
            orders=len(dataset.orders),
            payments=len(dataset.payments),
            settlements=len(dataset.settlements),
            refunds=len(dataset.refunds),
            fee_rules=len(dataset.fee_rules),
            payment_volume=payment_volume,
            reconciled_amount=settlement_volume,
            unresolved_amount=unresolved_amount,
            human_review_amount=human_review_amount,
            currencies=spec.currencies,
            payment_methods=spec.payment_methods,
            settlement=f"T+{spec.settlement_delay_days}",
            fee=f"{(spec.fee_rate * Decimal('100')).quantize(Decimal('0.01'))}%",
            anomalies=sum(anomaly_counts.values()),
            anomaly_mix=anomaly_counts,
        )

    def _amount(self, rng: random.Random) -> Decimal:
        base = Decimal(str(rng.lognormvariate(8.2, 0.55)))
        return money(max(Decimal("120.00"), min(base, Decimal("250000.00"))))

    def _refund_amount(self, amount: Decimal, rng: random.Random) -> Decimal:
        return money(amount * Decimal(str(rng.uniform(0.08, 0.40))))

    def _delta(self, rng: random.Random, low: Decimal = Decimal("25.00"), high: Decimal = Decimal("350.00")) -> Decimal:
        sign = Decimal("1.00") if rng.random() >= 0.45 else Decimal("-1.00")
        return money(Decimal(str(rng.uniform(float(low), float(high)))) * sign)

    def _world_id(self, spec: FinancialWorldSpec) -> str:
        digest = hashlib.sha256(
            (spec.prompt + "|" + spec.model_dump_json(exclude={"start_at"}) + "|" + str(spec.seed)).encode("utf-8")
        ).hexdigest()[:12]
        return f"FW_{digest}"

    def _seed(self, spec: FinancialWorldSpec) -> int:
        digest = hashlib.sha256((spec.prompt + "|" + str(spec.seed)).encode("utf-8")).hexdigest()[:8]
        return int(digest, 16)

    def _scenario_mode(self, spec: FinancialWorldSpec):
        from ..models import ScenarioMode

        mode = self._mode_value(spec)
        if mode == AnomalyMode.NORMAL.value:
            return ScenarioMode.NORMAL
        if mode in (AnomalyMode.ADVERSARIAL.value, AnomalyMode.CHAOS.value):
            return ScenarioMode.ADVERSARIAL
        return ScenarioMode.DIFFICULT

    def _mode_value(self, spec: FinancialWorldSpec) -> str:
        return spec.anomaly_mode.value if isinstance(spec.anomaly_mode, AnomalyMode) else str(spec.anomaly_mode)

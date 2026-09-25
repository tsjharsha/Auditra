from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple

from .models import (
    DatasetBundle,
    FeeRule,
    GroundTruthCase,
    Merchant,
    Order,
    Payment,
    ReconciliationStatus,
    Refund,
    ScenarioMode,
    ScenarioRequest,
    Settlement,
    money,
)


class ScenarioGenerator:
    """Generate linked finance-ops records with hidden ground truth."""

    merchant_templates = [
        ("MCH_ZERO", "Zero Fee Internal Rail", 0, Decimal("0.00"), 1),
        ("MCH_SWIFT", "SwiftKart Marketplace", 180, Decimal("3.00"), 2),
        ("MCH_CAFE", "Kaveri Coffee Roasters", 220, Decimal("2.00"), 2),
        ("MCH_SAAS", "Nila SaaS Systems", 250, Decimal("5.00"), 3),
        ("MCH_HEALTH", "Prana Health Online", 200, Decimal("4.00"), 2),
        ("MCH_TRAVEL", "Vista Travel Desk", 190, Decimal("6.00"), 3),
    ]

    scenario_weights = {
        ScenarioMode.NORMAL: {
            "normal": 0.88,
            "refund_adjusted": 0.09,
            "amount_mismatch": 0.01,
            "missing_settlement": 0.01,
            "timing_mismatch": 0.01,
        },
        ScenarioMode.MIXED: {
            "normal": 0.68,
            "refund_adjusted": 0.10,
            "amount_mismatch": 0.05,
            "fee_mismatch": 0.03,
            "missing_settlement": 0.04,
            "duplicate": 0.04,
            "timing_mismatch": 0.03,
            "partial_settlement": 0.03,
        },
        ScenarioMode.DIFFICULT: {
            "normal": 0.49,
            "refund_adjusted": 0.10,
            "amount_mismatch": 0.08,
            "fee_mismatch": 0.06,
            "missing_settlement": 0.07,
            "duplicate": 0.06,
            "timing_mismatch": 0.05,
            "partial_settlement": 0.05,
            "refund_mismatch": 0.02,
            "conflicting_evidence": 0.02,
        },
        ScenarioMode.ADVERSARIAL: {
            "normal": 0.35,
            "refund_adjusted": 0.08,
            "amount_mismatch": 0.12,
            "fee_mismatch": 0.08,
            "missing_settlement": 0.10,
            "duplicate": 0.08,
            "timing_mismatch": 0.07,
            "partial_settlement": 0.07,
            "refund_mismatch": 0.03,
            "conflicting_evidence": 0.02,
        },
    }

    payment_methods = ["upi", "card", "netbanking", "wallet"]

    def generate(self, request: ScenarioRequest) -> DatasetBundle:
        rng = random.Random(request.seed)
        generated_at = datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc)
        mode_value = request.mode.value if hasattr(request.mode, "value") else str(request.mode)
        dataset_id = f"DS_{mode_value}_{request.seed}_{request.record_count}"

        merchants, fee_rules = self._build_merchants_and_rules(generated_at)
        merchant_by_id = {merchant.merchant_id: merchant for merchant in merchants}
        rule_by_merchant = {rule.merchant_id: rule for rule in fee_rules}

        orders: List[Order] = []
        payments: List[Payment] = []
        settlements: List[Settlement] = []
        refunds: List[Refund] = []
        ground_truth: Dict[str, GroundTruthCase] = {}

        scenario_plan = self._scenario_plan(request.mode, request.record_count, rng)
        previous_payment: Payment | None = None
        previous_order: Order | None = None

        for idx, scenario_name in enumerate(scenario_plan, start=1):
            if scenario_name == "duplicate" and previous_payment and previous_order:
                order = previous_order
                amount = previous_payment.amount
                customer_id = previous_payment.customer_id
                merchant = merchant_by_id[previous_payment.merchant_id]
            else:
                merchant = rng.choice(merchants)
                amount = self._random_amount(rng)
                customer_id = f"CUS_{rng.randint(10000, 99999)}"
                order = self._make_order(idx, merchant, customer_id, amount, generated_at, rng)
                orders.append(order)

            payment = self._make_payment(idx, order, merchant, amount, generated_at, rng)
            payments.append(payment)

            rule = rule_by_merchant[merchant.merchant_id]
            expected_fee = rule.calculate_fee(payment.amount)
            expected_gst = rule.calculate_gst(expected_fee)
            refund_amount = Decimal("0.00")
            expected_status = self._normal_status_for(rule)
            reason = "payment, order, fee rule and settlement agree"
            financial_impact = Decimal("0.00")

            if scenario_name in ("refund_adjusted", "refund_mismatch", "conflicting_evidence"):
                refund_amount = self._refund_amount(payment.amount, rng)
                refund = self._make_refund(idx, payment, merchant, refund_amount, generated_at, rng)
                refunds.append(refund)
                expected_status = ReconciliationStatus.REFUND_ADJUSTED
                reason = "settlement correctly reflects refund and fee"

            expected_settlement = money(payment.amount - expected_fee - expected_gst - refund_amount)
            actual_settlement = expected_settlement
            settlement_time = payment.captured_at + timedelta(days=merchant.settlement_cycle_days, hours=rng.randint(1, 8))
            create_settlement = True

            if scenario_name == "missing_settlement":
                create_settlement = False
                expected_status = ReconciliationStatus.MISSING_SETTLEMENT
                financial_impact = expected_settlement
                reason = "payment has no settlement record"
            elif scenario_name == "duplicate":
                create_settlement = False
                expected_status = ReconciliationStatus.DUPLICATE
                financial_impact = payment.amount
                reason = "payment duplicates an earlier payment for the same order, merchant, amount and customer"
            elif scenario_name == "amount_mismatch":
                delta = self._delta(rng)
                actual_settlement = money(expected_settlement + delta)
                expected_status = ReconciliationStatus.AMOUNT_MISMATCH
                financial_impact = abs(delta)
                reason = "settlement amount differs from deterministic expectation"
            elif scenario_name == "fee_mismatch":
                delta = self._delta(rng, low=Decimal("7.00"), high=Decimal("85.00"))
                actual_settlement = money(expected_settlement - delta)
                expected_status = ReconciliationStatus.AMOUNT_MISMATCH
                financial_impact = abs(delta)
                reason = "fee implied by settlement does not match fee rule"
            elif scenario_name == "refund_mismatch":
                actual_settlement = money(payment.amount - expected_fee - expected_gst)
                expected_status = ReconciliationStatus.AMOUNT_MISMATCH
                financial_impact = abs(actual_settlement - expected_settlement)
                reason = "refund exists but is not reflected in settlement"
            elif scenario_name == "conflicting_evidence":
                actual_settlement = money(payment.amount - expected_fee - expected_gst)
                expected_status = ReconciliationStatus.HUMAN_REVIEW
                financial_impact = abs(actual_settlement - expected_settlement)
                reason = "refund evidence conflicts with settlement amount, requiring human review"
            elif scenario_name == "timing_mismatch":
                settlement_time = payment.captured_at + timedelta(days=merchant.settlement_cycle_days + 9)
                expected_status = ReconciliationStatus.TIMING_MISMATCH
                reason = "settlement amount is right but the timing window is violated"
            elif scenario_name == "partial_settlement":
                partial_ratio = Decimal(str(rng.uniform(0.35, 0.80)))
                actual_settlement = money(expected_settlement * partial_ratio)
                expected_status = ReconciliationStatus.PARTIAL_MATCH
                financial_impact = abs(expected_settlement - actual_settlement)
                reason = "settlement is present but only partially covers expected net amount"

            if create_settlement:
                settlements.append(
                    self._make_settlement(idx, payment, merchant, actual_settlement, settlement_time)
                )

            ground_truth[payment.payment_id] = GroundTruthCase(
                payment_id=payment.payment_id,
                expected_status=expected_status,
                scenario=scenario_name,
                financial_impact=financial_impact,
                reason=reason,
            )

            previous_payment = payment
            previous_order = order

        return DatasetBundle(
            dataset_id=dataset_id,
            mode=request.mode,
            seed=request.seed,
            requested_records=request.record_count,
            generated_at=generated_at,
            merchants=merchants,
            orders=orders,
            payments=payments,
            settlements=settlements,
            refunds=refunds,
            fee_rules=fee_rules,
            ground_truth=ground_truth,
        )

    def _scenario_plan(self, mode: ScenarioMode, record_count: int, rng: random.Random) -> List[str]:
        weights = self.scenario_weights[mode]
        names = list(weights.keys())
        values = list(weights.values())
        plan = rng.choices(names, weights=values, k=record_count)
        if record_count >= 50:
            required = ["amount_mismatch", "missing_settlement", "duplicate", "timing_mismatch", "partial_settlement"]
            if mode in (ScenarioMode.DIFFICULT, ScenarioMode.ADVERSARIAL):
                required.extend(["refund_mismatch", "conflicting_evidence"])
            for offset, required_name in enumerate(required):
                plan[offset + 1] = required_name
        return plan

    def _build_merchants_and_rules(self, active_from: datetime) -> Tuple[List[Merchant], List[FeeRule]]:
        merchants: List[Merchant] = []
        rules: List[FeeRule] = []
        for idx, (merchant_id, name, bps, fixed_fee, cycle_days) in enumerate(self.merchant_templates, start=1):
            merchants.append(
                Merchant(
                    source="generator",
                    source_record_id=f"SRC_MERCHANT_{idx}",
                    ingested_at=active_from,
                    merchant_id=merchant_id,
                    name=name,
                    settlement_cycle_days=cycle_days,
                    original={"template": name},
                )
            )
            rules.append(
                FeeRule(
                    source="generator",
                    source_record_id=f"SRC_FEE_RULE_{idx}",
                    ingested_at=active_from,
                    fee_rule_id=f"FEE_RULE_{idx:02d}",
                    merchant_id=merchant_id,
                    percent_bps=bps,
                    gst_bps=1800,
                    fixed_fee=fixed_fee,
                    active_from=active_from - timedelta(days=365),
                    original={"percent_bps": bps, "fixed_fee": str(fixed_fee)},
                )
            )
        return merchants, rules

    def _make_order(
        self,
        idx: int,
        merchant: Merchant,
        customer_id: str,
        amount: Decimal,
        base_time: datetime,
        rng: random.Random,
    ) -> Order:
        created_at = base_time + timedelta(minutes=idx * 7 + rng.randint(0, 5))
        order_id = f"ORD_{idx:06d}"
        return Order(
            source="orders.csv",
            source_record_id=f"orders:{order_id}",
            ingested_at=base_time,
            order_id=order_id,
            merchant_id=merchant.merchant_id,
            customer_id=customer_id,
            amount=amount,
            currency="INR",
            created_at=created_at,
            invoice_id=f"INV_{idx:06d}",
            reference_id=f"REF_{idx:06d}",
            original={"amount": str(amount), "merchant": merchant.name},
        )

    def _make_payment(
        self,
        idx: int,
        order: Order,
        merchant: Merchant,
        amount: Decimal,
        base_time: datetime,
        rng: random.Random,
    ) -> Payment:
        payment_id = f"PAY_{idx:06d}"
        captured_at = order.created_at + timedelta(minutes=rng.randint(1, 18))
        return Payment(
            source="payments.csv",
            source_record_id=f"payments:{payment_id}",
            ingested_at=base_time,
            payment_id=payment_id,
            order_id=order.order_id,
            merchant_id=merchant.merchant_id,
            customer_id=order.customer_id,
            amount=amount,
            currency="INR",
            captured_at=captured_at,
            payment_method=rng.choice(self.payment_methods),
            reference_id=order.reference_id,
            original={"amount": str(amount), "captured_at": captured_at.isoformat()},
        )

    def _make_settlement(
        self,
        idx: int,
        payment: Payment,
        merchant: Merchant,
        amount: Decimal,
        settled_at: datetime,
    ) -> Settlement:
        settlement_id = f"SET_{idx:06d}"
        return Settlement(
            source="settlements.csv",
            source_record_id=f"settlements:{settlement_id}",
            ingested_at=settled_at,
            settlement_id=settlement_id,
            payment_id=payment.payment_id,
            merchant_id=merchant.merchant_id,
            amount=money(amount),
            currency=payment.currency,
            settled_at=settled_at,
            batch_id=f"BATCH_{settled_at.strftime('%Y%m%d')}",
            original={"amount": str(money(amount)), "settled_at": settled_at.isoformat()},
        )

    def _make_refund(
        self,
        idx: int,
        payment: Payment,
        merchant: Merchant,
        amount: Decimal,
        base_time: datetime,
        rng: random.Random,
    ) -> Refund:
        refund_id = f"REFUND_{idx:06d}"
        refunded_at = payment.captured_at + timedelta(hours=rng.randint(3, 30))
        return Refund(
            source="refunds.csv",
            source_record_id=f"refunds:{refund_id}",
            ingested_at=base_time,
            refund_id=refund_id,
            payment_id=payment.payment_id,
            merchant_id=merchant.merchant_id,
            amount=amount,
            currency=payment.currency,
            refunded_at=refunded_at,
            original={"amount": str(amount), "refunded_at": refunded_at.isoformat()},
        )

    def _random_amount(self, rng: random.Random) -> Decimal:
        rupees = rng.randint(300, 90000)
        paise = rng.choice([0, 0, 0, 25, 50, 75])
        return money(Decimal(rupees) + (Decimal(paise) / Decimal(100)))

    def _refund_amount(self, amount: Decimal, rng: random.Random) -> Decimal:
        ratio = Decimal(str(rng.uniform(0.08, 0.45)))
        return money(amount * ratio)

    def _delta(
        self,
        rng: random.Random,
        low: Decimal = Decimal("5.00"),
        high: Decimal = Decimal("250.00"),
    ) -> Decimal:
        cents_low = int(low * 100)
        cents_high = int(high * 100)
        sign = -1 if rng.random() < 0.45 else 1
        return money(Decimal(sign * rng.randint(cents_low, cents_high)) / Decimal(100))

    def _normal_status_for(self, rule: FeeRule) -> ReconciliationStatus:
        if rule.percent_bps == 0 and rule.fixed_fee == Decimal("0.00"):
            return ReconciliationStatus.MATCHED
        return ReconciliationStatus.FEE_EXPLAINED

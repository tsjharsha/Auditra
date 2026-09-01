from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Dict, List, Set

from .models import (
    ControllerRun,
    DatasetBundle,
    EvaluationMetrics,
    EvaluationRun,
    FailureRecord,
    ReconciliationStatus,
    money,
)
from .reconciliation import MATCH_STATUSES, TERMINAL_REVIEW_STATUSES


MATCH_STATUS_VALUES = {item.value for item in MATCH_STATUSES}
TERMINAL_REVIEW_VALUES = {item.value for item in TERMINAL_REVIEW_STATUSES}


class IndependentEvaluator:
    """Compare controller predictions against hidden scenario ground truth."""

    def evaluate(self, dataset: DatasetBundle, controller_run: ControllerRun) -> EvaluationRun:
        truth = dataset.ground_truth
        payment_by_id = {payment.payment_id: payment for payment in dataset.payments}
        labels: Set[str] = set(status.value for status in ReconciliationStatus)
        confusion: Dict[str, Dict[str, int]] = {label: {inner: 0 for inner in labels} for label in labels}

        correct = 0
        total = 0
        failures: List[FailureRecord] = []
        failure_taxonomy: Dict[str, int] = {}
        correct_amount = Decimal("0.00")
        incorrect_amount = Decimal("0.00")
        error_impact = Decimal("0.00")

        expected_exception_count = 0
        expected_normal_count = 0
        false_positive_count = 0
        false_negative_count = 0

        for case in controller_run.cases:
            expected_case = truth.get(case.payment_id)
            if expected_case is None:
                continue

            expected = str(expected_case.expected_status)
            predicted = str(case.status)
            labels.add(expected)
            labels.add(predicted)
            confusion.setdefault(expected, {})
            confusion[expected].setdefault(predicted, 0)
            confusion[expected][predicted] += 1
            total += 1

            payment_amount = payment_by_id[case.payment_id].amount
            expected_is_normal = expected in MATCH_STATUS_VALUES
            predicted_is_normal = predicted in MATCH_STATUS_VALUES
            if expected_is_normal:
                expected_normal_count += 1
            else:
                expected_exception_count += 1
            if predicted_is_normal and not expected_is_normal:
                false_negative_count += 1
            if not predicted_is_normal and expected_is_normal:
                false_positive_count += 1

            if expected == predicted:
                correct += 1
                correct_amount += payment_amount
            else:
                incorrect_amount += payment_amount
                impact = max(expected_case.financial_impact, case.decision.financial_impact)
                error_impact += impact
                failures.append(
                    FailureRecord(
                        case_id=case.case_id,
                        payment_id=case.payment_id,
                        expected=expected_case.expected_status,
                        predicted=case.status,
                        root_cause=self._root_cause(expected, predicted, case.decision.reason_codes),
                        evidence_available=case.decision.evidence_ids,
                        failure_category=self._failure_category(expected, predicted),
                        financial_impact=impact,
                    )
                )
                category = self._failure_category(expected, predicted)
                failure_taxonomy[category] = failure_taxonomy.get(category, 0) + 1

        precision, recall, f1 = self._macro_scores(confusion)
        class_metrics = self._class_metrics(confusion)
        accuracy = correct / max(total, 1)
        escalation_count = sum(1 for case in controller_run.cases if str(case.status) in TERMINAL_REVIEW_VALUES)
        unresolved_count = sum(1 for case in controller_run.cases if str(case.status) == ReconciliationStatus.UNRESOLVED.value)

        metrics = EvaluationMetrics(
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            false_positive_rate=round(false_positive_count / max(expected_normal_count, 1), 4),
            false_negative_rate=round(false_negative_count / max(expected_exception_count, 1), 4),
            exception_false_positive_rate=round(false_positive_count / max(expected_normal_count, 1), 4),
            exception_false_negative_rate=round(false_negative_count / max(expected_exception_count, 1), 4),
            match_rate=controller_run.metrics.match_rate,
            automatic_resolution_rate=controller_run.metrics.automatic_resolution_rate,
            escalation_rate=round(escalation_count / max(total, 1), 4),
            unresolved_rate=round(unresolved_count / max(total, 1), 4),
            throughput_records_per_sec=controller_run.metrics.throughput_records_per_sec,
            median_latency_ms=controller_run.metrics.median_latency_ms,
            p95_latency_ms=controller_run.metrics.p95_latency_ms,
            p99_latency_ms=controller_run.metrics.p99_latency_ms,
            llm_calls=controller_run.metrics.llm_calls,
            agent_tool_calls=controller_run.metrics.agent_tool_calls,
            estimated_ai_cost_usd=controller_run.metrics.estimated_ai_cost_usd,
            financial_amount_correctly_reconciled=money(correct_amount),
            financial_amount_incorrectly_classified=money(incorrect_amount),
            financial_impact_of_errors=money(error_impact),
            confusion_matrix=confusion,
            class_metrics=class_metrics,
            failure_taxonomy=failure_taxonomy,
        )

        return EvaluationRun(
            evaluation_run_id=f"EVAL_{uuid.uuid4().hex[:12]}",
            controller_run_id=controller_run.run_id,
            dataset_id=dataset.dataset_id,
            metrics=metrics,
            failures=failures,
        )

    def _macro_scores(self, confusion: Dict[str, Dict[str, int]]) -> tuple[float, float, float]:
        active_labels = set()
        for expected, predictions in confusion.items():
            if sum(predictions.values()) > 0:
                active_labels.add(expected)
            for predicted, count in predictions.items():
                if count > 0:
                    active_labels.add(predicted)

        precisions = []
        recalls = []
        f1s = []
        for label in sorted(active_labels):
            tp = confusion.get(label, {}).get(label, 0)
            fp = sum(predictions.get(label, 0) for expected, predictions in confusion.items() if expected != label)
            fn = sum(count for predicted, count in confusion.get(label, {}).items() if predicted != label)
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = (2 * precision * recall / max(precision + recall, 1e-12)) if (precision + recall) else 0.0
            precisions.append(precision)
            recalls.append(recall)
            f1s.append(f1)

        if not active_labels:
            return 0.0, 0.0, 0.0
        return sum(precisions) / len(precisions), sum(recalls) / len(recalls), sum(f1s) / len(f1s)

    def _class_metrics(self, confusion: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, float]]:
        metrics: Dict[str, Dict[str, float]] = {}
        active_labels = set()
        for expected, predictions in confusion.items():
            if sum(predictions.values()) > 0:
                active_labels.add(expected)
            for predicted, count in predictions.items():
                if count > 0:
                    active_labels.add(predicted)

        for label in sorted(active_labels):
            tp = confusion.get(label, {}).get(label, 0)
            fp = sum(predictions.get(label, 0) for expected, predictions in confusion.items() if expected != label)
            fn = sum(count for predicted, count in confusion.get(label, {}).items() if predicted != label)
            support = sum(confusion.get(label, {}).values())
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = (2 * precision * recall / max(precision + recall, 1e-12)) if (precision + recall) else 0.0
            metrics[label] = {
                "support": float(support),
                "true_positive": float(tp),
                "false_positive": float(fp),
                "false_negative": float(fn),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }
        return metrics

    def _root_cause(self, expected: str, predicted: str, reason_codes: List[str]) -> str:
        if predicted == ReconciliationStatus.HUMAN_REVIEW.value and expected != predicted:
            return "Controller escalated instead of resolving deterministically."
        if expected == ReconciliationStatus.HUMAN_REVIEW.value and predicted != expected:
            return "Controller resolved despite conflicting evidence."
        if "REFUND_CONFLICT" in reason_codes:
            return "Refund evidence changed the classification path."
        if "AMOUNT_DIFFERENCE" in reason_codes:
            return "Amount-difference rule selected the wrong exception class."
        if "SETTLEMENT_TIMING" in reason_codes:
            return "Timing and amount evidence competed."
        return "Classification differed from hidden scenario label."

    def _failure_category(self, expected: str, predicted: str) -> str:
        if predicted == ReconciliationStatus.HUMAN_REVIEW.value:
            return "OVER_ESCALATION"
        if expected == ReconciliationStatus.HUMAN_REVIEW.value:
            return "MISSED_CONFLICT"
        if expected in MATCH_STATUS_VALUES and predicted not in MATCH_STATUS_VALUES:
            return "FALSE_EXCEPTION"
        if expected not in MATCH_STATUS_VALUES and predicted in MATCH_STATUS_VALUES:
            return "MISSED_EXCEPTION"
        return "CLASSIFICATION_ERROR"

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from .models import (
    AIInvestigationResult,
    EvidenceGraph,
    EvidenceItem,
    FeeRule,
    GraphEdge,
    GraphNode,
    Order,
    Payment,
    Refund,
    ReconciliationStatus,
    Settlement,
)


def build_evidence_items(
    payment: Payment,
    order: Optional[Order],
    settlements: List[Settlement],
    refunds: List[Refund],
    fee_rule: Optional[FeeRule],
) -> List[EvidenceItem]:
    evidence: List[EvidenceItem] = [
        EvidenceItem(
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
            entity_type="payment",
            entity_id=payment.payment_id,
            source=payment.source,
            summary=f"Payment {payment.payment_id} for {payment.amount} {payment.currency}",
            payload=payment.model_dump(mode="json"),
        )
    ]
    if order:
        evidence.append(
            EvidenceItem(
                evidence_id=f"EVD_ORDER_{order.order_id}",
                entity_type="order",
                entity_id=order.order_id,
                source=order.source,
                summary=f"Order {order.order_id} for {order.amount} {order.currency}",
                payload=order.model_dump(mode="json"),
            )
        )
    for settlement in settlements:
        evidence.append(
            EvidenceItem(
                evidence_id=f"EVD_SETTLEMENT_{settlement.settlement_id}",
                entity_type="settlement",
                entity_id=settlement.settlement_id,
                source=settlement.source,
                summary=f"Settlement {settlement.settlement_id} for {settlement.amount} {settlement.currency}",
                payload=settlement.model_dump(mode="json"),
            )
        )
    for refund in refunds:
        evidence.append(
            EvidenceItem(
                evidence_id=f"EVD_REFUND_{refund.refund_id}",
                entity_type="refund",
                entity_id=refund.refund_id,
                source=refund.source,
                summary=f"Refund {refund.refund_id} for {refund.amount} {refund.currency}",
                payload=refund.model_dump(mode="json"),
            )
        )
    if fee_rule:
        evidence.append(
            EvidenceItem(
                evidence_id=f"EVD_FEE_RULE_{fee_rule.fee_rule_id}",
                entity_type="fee_rule",
                entity_id=fee_rule.fee_rule_id,
                source=fee_rule.source,
                summary=f"Fee rule {fee_rule.fee_rule_id}: {fee_rule.percent_bps} bps + {fee_rule.fixed_fee} fixed, GST {fee_rule.gst_bps} bps",
                payload=fee_rule.model_dump(mode="json"),
            )
        )
    return evidence


def build_graph(
    payment: Payment,
    order: Optional[Order],
    settlements: List[Settlement],
    refunds: List[Refund],
    fee_rule: Optional[FeeRule],
    case_id: Optional[str] = None,
    status: Optional[ReconciliationStatus | str] = None,
    evidence_items: Optional[List[EvidenceItem]] = None,
    supporting_evidence: Optional[List[str]] = None,
    contradicting_evidence: Optional[List[str]] = None,
    ai_investigation: Optional[AIInvestigationResult] = None,
    risk_score: float = 0.0,
) -> EvidenceGraph:
    def edge(
        id: str,
        source: str,
        target: str,
        relationship: str,
        confidence: float,
        evidence_id: Optional[str] = None,
        record_source: str = "auditra",
        timestamp: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> GraphEdge:
        data = {"record_source": record_source}
        if timestamp:
            data["timestamp"] = timestamp
        if extra:
            data.update(extra)
        return GraphEdge(
            id=id,
            source=source,
            target=target,
            relationship=relationship,
            confidence=confidence,
            evidence_id=evidence_id,
            data=data,
        )

    transaction_node_id = f"TRANSACTION:{payment.payment_id}"
    nodes: List[GraphNode] = [
        GraphNode(
            id=transaction_node_id,
            type="Transaction",
            label=payment.payment_id,
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
            data={"amount": str(payment.amount), "currency": payment.currency, "risk_score": risk_score},
        ),
        GraphNode(
            id=f"PAYMENT:{payment.payment_id}",
            type="Payment",
            label=payment.payment_id,
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
            data={"amount": str(payment.amount), "currency": payment.currency},
        ),
        GraphNode(
            id=f"MERCHANT:{payment.merchant_id}",
            type="Merchant",
            label=payment.merchant_id,
            data={"merchant_id": payment.merchant_id},
        ),
        GraphNode(
            id=f"CUSTOMER:{payment.customer_id}",
            type="Customer",
            label=payment.customer_id,
            data={"customer_id": payment.customer_id},
        ),
    ]
    edges: List[GraphEdge] = [
        edge(
            f"EDGE_TRANSACTION_PAYMENT_{payment.payment_id}",
            transaction_node_id,
            f"PAYMENT:{payment.payment_id}",
            "PAID",
            1.0,
            f"EVD_PAYMENT_{payment.payment_id}",
            payment.source,
            payment.captured_at.isoformat(),
        ),
        edge(
            id=f"EDGE_MERCHANT_PAYMENT_{payment.payment_id}",
            source=f"MERCHANT:{payment.merchant_id}",
            target=transaction_node_id,
            relationship="BELONGS_TO",
            confidence=1.0,
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
            record_source=payment.source,
            timestamp=payment.captured_at.isoformat(),
        ),
        edge(
            id=f"EDGE_CUSTOMER_PAYMENT_{payment.payment_id}",
            source=f"CUSTOMER:{payment.customer_id}",
            target=transaction_node_id,
            relationship="PAID",
            confidence=1.0,
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
            record_source=payment.source,
            timestamp=payment.captured_at.isoformat(),
        ),
    ]
    if order:
        nodes.append(
            GraphNode(
                id=f"ORDER:{order.order_id}",
                type="Order",
                label=order.order_id,
                evidence_id=f"EVD_ORDER_{order.order_id}",
                data={"amount": str(order.amount), "currency": order.currency},
            )
        )
        edges.append(
            edge(
                id=f"EDGE_ORDER_PAYMENT_{payment.payment_id}",
                source=f"ORDER:{order.order_id}",
                target=f"PAYMENT:{payment.payment_id}",
                relationship="CREATED",
                confidence=1.0 if order.order_id == payment.order_id else 0.0,
                evidence_id=f"EVD_ORDER_{order.order_id}",
                record_source=order.source,
                timestamp=order.created_at.isoformat(),
            )
        )
    for settlement in settlements:
        nodes.append(
            GraphNode(
                id=f"SETTLEMENT:{settlement.settlement_id}",
                type="Settlement",
                label=settlement.settlement_id,
                evidence_id=f"EVD_SETTLEMENT_{settlement.settlement_id}",
                data={"amount": str(settlement.amount), "currency": settlement.currency},
            )
        )
        edges.append(
            edge(
                id=f"EDGE_PAYMENT_SETTLEMENT_{settlement.settlement_id}",
                source=f"PAYMENT:{payment.payment_id}",
                target=f"SETTLEMENT:{settlement.settlement_id}",
                relationship="SETTLED",
                confidence=1.0,
                evidence_id=f"EVD_SETTLEMENT_{settlement.settlement_id}",
                record_source=settlement.source,
                timestamp=settlement.settled_at.isoformat(),
            )
        )
    for refund in refunds:
        nodes.append(
            GraphNode(
                id=f"REFUND:{refund.refund_id}",
                type="Refund",
                label=refund.refund_id,
                evidence_id=f"EVD_REFUND_{refund.refund_id}",
                data={"amount": str(refund.amount), "currency": refund.currency},
            )
        )
        edges.append(
            edge(
                id=f"EDGE_PAYMENT_REFUND_{refund.refund_id}",
                source=f"PAYMENT:{payment.payment_id}",
                target=f"REFUND:{refund.refund_id}",
                relationship="REFUNDED",
                confidence=1.0,
                evidence_id=f"EVD_REFUND_{refund.refund_id}",
                record_source=refund.source,
                timestamp=refund.refunded_at.isoformat(),
            )
        )
    if fee_rule:
        nodes.append(
            GraphNode(
                id=f"FEE_RULE:{fee_rule.fee_rule_id}",
                type="FeeRule",
                label=fee_rule.fee_rule_id,
                evidence_id=f"EVD_FEE_RULE_{fee_rule.fee_rule_id}",
                data={"percent_bps": fee_rule.percent_bps, "fixed_fee": str(fee_rule.fixed_fee), "gst_bps": fee_rule.gst_bps},
            )
        )
        edges.append(
            edge(
                id=f"EDGE_PAYMENT_FEE_{payment.payment_id}",
                source=f"PAYMENT:{payment.payment_id}",
                target=f"FEE_RULE:{fee_rule.fee_rule_id}",
                relationship="GOVERNED_BY",
                confidence=1.0,
                evidence_id=f"EVD_FEE_RULE_{fee_rule.fee_rule_id}",
                record_source=fee_rule.source,
                timestamp=fee_rule.active_from.isoformat(),
            )
        )
    if case_id:
        investigation_id = f"INVESTIGATION:{case_id}"
        decision_id = f"DECISION:{case_id}"
        nodes.extend(
            [
                GraphNode(
                    id=investigation_id,
                    type="Investigation",
                    label=case_id,
                    data={
                        "ai_investigation_id": ai_investigation.investigation_id if ai_investigation else None,
                        "hypothesis_count": len(ai_investigation.hypotheses) if ai_investigation else 0,
                    },
                ),
                GraphNode(
                    id=decision_id,
                    type="Decision",
                    label=str(status) if status is not None else "PENDING",
                    data={"status": str(status) if status is not None else None, "risk_score": risk_score},
                ),
            ]
        )
        edges.extend(
            [
                edge(
                    f"EDGE_TRANSACTION_INVESTIGATION_{case_id}",
                    transaction_node_id,
                    investigation_id,
                    "INVESTIGATED_BY",
                    1.0,
                    record_source="auditra_controller",
                ),
                edge(
                    f"EDGE_INVESTIGATION_DECISION_{case_id}",
                    investigation_id,
                    decision_id,
                    "RESULTED_IN",
                    1.0,
                    record_source="auditra_controller",
                ),
            ]
        )

        support_set = set(supporting_evidence or [])
        contradiction_set = set(contradicting_evidence or [])
        for item in evidence_items or []:
            evidence_node_id = f"EVIDENCE:{item.evidence_id}"
            nodes.append(
                GraphNode(
                    id=evidence_node_id,
                    type="Evidence",
                    label=item.evidence_id,
                    evidence_id=item.evidence_id,
                    data={"entity_type": item.entity_type, "entity_id": item.entity_id, "summary": item.summary},
                )
            )
            if item.evidence_id in support_set:
                relationship = "SUPPORTED_BY"
                confidence = 1.0
            elif item.evidence_id in contradiction_set:
                relationship = "CONTRADICTED_BY"
                confidence = 0.75
            else:
                relationship = "RELATED_TO"
                confidence = 0.65
            edges.append(
                edge(
                    f"EDGE_DECISION_EVIDENCE_{case_id}_{item.evidence_id}",
                    decision_id,
                    evidence_node_id,
                    relationship,
                    confidence,
                    item.evidence_id,
                    item.source,
                    extra={"entity_type": item.entity_type, "entity_id": item.entity_id},
                )
            )
    return EvidenceGraph(transaction_id=payment.payment_id, nodes=nodes, edges=edges)

from __future__ import annotations

from typing import Iterable, List, Optional

from .models import EvidenceGraph, EvidenceItem, FeeRule, GraphEdge, GraphNode, Order, Payment, Refund, Settlement


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
                summary=f"Fee rule {fee_rule.fee_rule_id}: {fee_rule.percent_bps} bps plus {fee_rule.fixed_fee}",
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
) -> EvidenceGraph:
    nodes: List[GraphNode] = [
        GraphNode(
            id=f"PAYMENT:{payment.payment_id}",
            type="payment",
            label=payment.payment_id,
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
            data={"amount": str(payment.amount), "currency": payment.currency},
        ),
        GraphNode(
            id=f"MERCHANT:{payment.merchant_id}",
            type="merchant",
            label=payment.merchant_id,
            data={"merchant_id": payment.merchant_id},
        ),
        GraphNode(
            id=f"CUSTOMER:{payment.customer_id}",
            type="customer",
            label=payment.customer_id,
            data={"customer_id": payment.customer_id},
        ),
    ]
    edges: List[GraphEdge] = [
        GraphEdge(
            id=f"EDGE_MERCHANT_PAYMENT_{payment.payment_id}",
            source=f"MERCHANT:{payment.merchant_id}",
            target=f"PAYMENT:{payment.payment_id}",
            relationship="receives",
            confidence=1.0,
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
        ),
        GraphEdge(
            id=f"EDGE_CUSTOMER_PAYMENT_{payment.payment_id}",
            source=f"CUSTOMER:{payment.customer_id}",
            target=f"PAYMENT:{payment.payment_id}",
            relationship="pays",
            confidence=1.0,
            evidence_id=f"EVD_PAYMENT_{payment.payment_id}",
        ),
    ]
    if order:
        nodes.append(
            GraphNode(
                id=f"ORDER:{order.order_id}",
                type="order",
                label=order.order_id,
                evidence_id=f"EVD_ORDER_{order.order_id}",
                data={"amount": str(order.amount), "currency": order.currency},
            )
        )
        edges.append(
            GraphEdge(
                id=f"EDGE_ORDER_PAYMENT_{payment.payment_id}",
                source=f"ORDER:{order.order_id}",
                target=f"PAYMENT:{payment.payment_id}",
                relationship="creates",
                confidence=1.0 if order.order_id == payment.order_id else 0.0,
                evidence_id=f"EVD_ORDER_{order.order_id}",
            )
        )
    for settlement in settlements:
        nodes.append(
            GraphNode(
                id=f"SETTLEMENT:{settlement.settlement_id}",
                type="settlement",
                label=settlement.settlement_id,
                evidence_id=f"EVD_SETTLEMENT_{settlement.settlement_id}",
                data={"amount": str(settlement.amount), "currency": settlement.currency},
            )
        )
        edges.append(
            GraphEdge(
                id=f"EDGE_PAYMENT_SETTLEMENT_{settlement.settlement_id}",
                source=f"PAYMENT:{payment.payment_id}",
                target=f"SETTLEMENT:{settlement.settlement_id}",
                relationship="settles_through",
                confidence=1.0,
                evidence_id=f"EVD_SETTLEMENT_{settlement.settlement_id}",
            )
        )
    for refund in refunds:
        nodes.append(
            GraphNode(
                id=f"REFUND:{refund.refund_id}",
                type="refund",
                label=refund.refund_id,
                evidence_id=f"EVD_REFUND_{refund.refund_id}",
                data={"amount": str(refund.amount), "currency": refund.currency},
            )
        )
        edges.append(
            GraphEdge(
                id=f"EDGE_PAYMENT_REFUND_{refund.refund_id}",
                source=f"PAYMENT:{payment.payment_id}",
                target=f"REFUND:{refund.refund_id}",
                relationship="adjusted_by",
                confidence=1.0,
                evidence_id=f"EVD_REFUND_{refund.refund_id}",
            )
        )
    if fee_rule:
        nodes.append(
            GraphNode(
                id=f"FEE_RULE:{fee_rule.fee_rule_id}",
                type="fee_rule",
                label=fee_rule.fee_rule_id,
                evidence_id=f"EVD_FEE_RULE_{fee_rule.fee_rule_id}",
                data={"percent_bps": fee_rule.percent_bps, "fixed_fee": str(fee_rule.fixed_fee)},
            )
        )
        edges.append(
            GraphEdge(
                id=f"EDGE_PAYMENT_FEE_{payment.payment_id}",
                source=f"PAYMENT:{payment.payment_id}",
                target=f"FEE_RULE:{fee_rule.fee_rule_id}",
                relationship="governed_by",
                confidence=1.0,
                evidence_id=f"EVD_FEE_RULE_{fee_rule.fee_rule_id}",
            )
        )
    return EvidenceGraph(transaction_id=payment.payment_id, nodes=nodes, edges=edges)

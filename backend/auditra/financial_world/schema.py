from __future__ import annotations

from .models import EntitySchema, RelationshipEdge, RelationshipModel, SchemaField, SchemaPreview


def build_schema_preview() -> SchemaPreview:
    return SchemaPreview(
        entities=[
            EntitySchema(
                entity="MERCHANT",
                fields=[
                    SchemaField(name="merchant_id", type="string", description="Canonical merchant identifier"),
                    SchemaField(name="name", type="string", description="Merchant display name"),
                    SchemaField(name="settlement_cycle_days", type="integer", description="T+N settlement delay"),
                    SchemaField(name="risk_tier", type="string", description="Review prioritization tier"),
                ],
            ),
            EntitySchema(
                entity="ORDER",
                fields=[
                    SchemaField(name="order_id", type="string"),
                    SchemaField(name="merchant_id", type="string"),
                    SchemaField(name="customer_id", type="string"),
                    SchemaField(name="amount", type="decimal_money"),
                    SchemaField(name="currency", type="string"),
                    SchemaField(name="created_at", type="datetime_tz"),
                ],
            ),
            EntitySchema(
                entity="PAYMENT",
                fields=[
                    SchemaField(name="payment_id", type="string"),
                    SchemaField(name="order_id", type="string", required=False),
                    SchemaField(name="merchant_id", type="string"),
                    SchemaField(name="customer_id", type="string"),
                    SchemaField(name="amount", type="decimal_money"),
                    SchemaField(name="currency", type="string"),
                    SchemaField(name="payment_method", type="string"),
                    SchemaField(name="captured_at", type="datetime_tz"),
                ],
            ),
            EntitySchema(
                entity="SETTLEMENT",
                fields=[
                    SchemaField(name="settlement_id", type="string"),
                    SchemaField(name="payment_id", type="string"),
                    SchemaField(name="merchant_id", type="string"),
                    SchemaField(name="amount", type="decimal_money"),
                    SchemaField(name="currency", type="string"),
                    SchemaField(name="settled_at", type="datetime_tz"),
                    SchemaField(name="batch_id", type="string"),
                ],
            ),
            EntitySchema(
                entity="REFUND",
                fields=[
                    SchemaField(name="refund_id", type="string"),
                    SchemaField(name="payment_id", type="string"),
                    SchemaField(name="merchant_id", type="string"),
                    SchemaField(name="amount", type="decimal_money"),
                    SchemaField(name="currency", type="string"),
                    SchemaField(name="refunded_at", type="datetime_tz"),
                    SchemaField(name="reason", type="string"),
                ],
            ),
            EntitySchema(
                entity="FEE_RULE",
                fields=[
                    SchemaField(name="fee_rule_id", type="string"),
                    SchemaField(name="merchant_id", type="string"),
                    SchemaField(name="currency", type="string"),
                    SchemaField(name="percent_bps", type="integer"),
                    SchemaField(name="fixed_fee", type="decimal_money"),
                    SchemaField(name="active_from", type="datetime_tz"),
                    SchemaField(name="active_to", type="datetime_tz", required=False),
                ],
            ),
        ]
    )


def build_relationship_model() -> RelationshipModel:
    return RelationshipModel(
        nodes=["MERCHANT", "ORDER", "PAYMENT", "SETTLEMENT", "REFUND", "FEE_RULE"],
        edges=[
            RelationshipEdge(source="MERCHANT", relationship="CREATED", target="ORDER", description="Merchant has orders"),
            RelationshipEdge(source="ORDER", relationship="PAID", target="PAYMENT", description="Order is paid by payment"),
            RelationshipEdge(source="PAYMENT", relationship="SETTLED", target="SETTLEMENT", description="Payment settles into settlement"),
            RelationshipEdge(source="PAYMENT", relationship="REFUNDED", target="REFUND", required=False, description="Refund adjusts a payment"),
            RelationshipEdge(source="PAYMENT", relationship="GOVERNED_BY", target="FEE_RULE", description="Payment uses merchant fee rule"),
            RelationshipEdge(source="PAYMENT", relationship="RELATED_TO", target="PAYMENT", required=False, description="Duplicate or linked payment relation"),
        ],
    )

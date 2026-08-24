from __future__ import annotations

import uuid
from typing import Any, Dict, List

from .models import AuditEvent


class AuditLog:
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.events: List[AuditEvent] = []

    def record(
        self,
        actor: str,
        action: str,
        entity: str,
        entity_id: str,
        reason: str = "",
        inputs_ref: Dict[str, Any] | None = None,
        output_ref: Dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=f"AUD_{uuid.uuid4().hex[:12]}",
            actor=actor,
            action=action,
            entity=entity,
            entity_id=entity_id,
            inputs_ref=inputs_ref or {},
            output_ref=output_ref or {},
            reason=reason,
            correlation_id=self.correlation_id,
        )
        self.events.append(event)
        return event

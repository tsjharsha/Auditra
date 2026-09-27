import asyncio
import json
import time
from collections import deque
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

# ---------------------------------------------------------------------------
# Observability Layer (IBM Bob ↔ MCP ↔ Auditra)
# ---------------------------------------------------------------------------
# This module provides a lightweight event stream for the War Room UI.
# It is purely for OBSERVABILITY. It does NOT enforce verification logic,
# it does NOT manage the sandbox, and it is NOT authoritative.
# Trust boundary: The MCP server executes the verified tools; this layer
# merely records what the MCP server and Verification Engine are doing.
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/observability", tags=["observability"])

class EventBus:
    def __init__(self, maxlen=200):
        self.events = deque(maxlen=maxlen)
        self.listeners = []

    def emit(self, event: dict[str, Any]):
        if "timestamp" not in event:
            event["timestamp"] = time.time()
            
        # Ensure event is well-formed
        safe_event = {
            "timestamp": event.get("timestamp"),
            "source": event.get("source", "SYSTEM"),
            "event_type": event.get("event_type", "INFO"),
            "node_id": event.get("node_id"),
            "tool_name": event.get("tool_name"),
            "status": event.get("status"),
            "message": event.get("message", ""),
            "metrics": event.get("metrics")
        }
        
        self.events.append(safe_event)
        
        # Notify all active subscribers
        for queue in self.listeners:
            try:
                queue.put_nowait(safe_event)
            except asyncio.QueueFull:
                pass

    async def subscribe(self):
        queue = asyncio.Queue(maxsize=100)
        self.listeners.append(queue)
        try:
            # Yield history first so new clients catch up instantly
            for evt in list(self.events):
                yield evt
                
            # Then yield new events as they arrive
            while True:
                evt = await queue.get()
                yield evt
        finally:
            self.listeners.remove(queue)

# Global in-memory event bus
bus = EventBus(maxlen=200)

@router.post("/event")
async def post_event(event: dict[str, Any]):
    """
    Ingest a real-time event from the MCP server or Verification Engine.
    This is an internal unauthenticated endpoint for local processes.
    """
    bus.emit(event)
    return {"status": "ok"}

@router.get("/stream")
async def stream_events():
    """
    SSE stream for the War Room UI to consume observability events.
    """
    async def event_generator():
        async for evt in bus.subscribe():
            yield f"data: {json.dumps(evt)}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

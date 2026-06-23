"""SSE endpoint for streaming alerts to connected clients."""

import asyncio
import json
import logging

from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.routing import Route

from openhive.events import event_store

logger = logging.getLogger(__name__)


async def _event_stream(request: Request):
    """Generate SSE events from the event store subscriber queue."""
    queue = event_store.subscribe()
    try:
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"

        # Send any existing unread alerts as a batch
        existing = event_store.list_alerts()
        if existing:
            yield f"event: sync\ndata: {json.dumps([a.to_dict() for a in existing])}\n\n"

        # Stream new alerts as they arrive
        while True:
            if await request.is_disconnected():
                break
            try:
                alert = await asyncio.wait_for(queue.get(), timeout=30.0)
                data = json.dumps(alert.to_dict())
                yield f"event: alert\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        event_store.unsubscribe(queue)
        logger.info("SSE client disconnected")


async def handle_sse(request: Request) -> StreamingResponse:
    """SSE endpoint for streaming alerts to clients."""
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


sse_routes = [
    Route("/events", handle_sse),
]

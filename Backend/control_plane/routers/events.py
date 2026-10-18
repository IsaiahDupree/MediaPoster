"""
Events Router

Handles event streaming (SSE) for real-time job updates.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from ..storage import event_store

router = APIRouter()


@router.get("/events/stream")
async def events_stream(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    cursor: Optional[str] = Query(None, description="Resume from cursor")
):
    """
    Server-Sent Events (SSE) stream for real-time job updates.
    
    Supports filtering by job_id or correlation_id.
    Use cursor parameter to resume after disconnection.
    
    Returns:
        SSE stream of EventEnvelope objects
    """
    async def event_generator():
        last_cursor = cursor
        
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        
        while True:
            events = event_store.get_since_cursor(
                cursor=last_cursor,
                job_id=job_id,
                correlation_id=correlation_id,
                limit=10
            )
            
            for event in events:
                event_data = {
                    "version": "1.0",
                    "event_id": event.get("event_id"),
                    "job_id": event.get("job_id"),
                    "correlation_id": event.get("correlation_id"),
                    "type": event.get("type"),
                    "stage": event.get("stage"),
                    "percent": event.get("percent"),
                    "message": event.get("message"),
                    "data": event.get("data", {}),
                    "timestamp": event.get("timestamp").isoformat() if event.get("timestamp") else None,
                    "cursor": event.get("cursor")
                }
                
                yield f"data: {json.dumps(event_data)}\n\n"
                
                if event.get("cursor"):
                    last_cursor = event["cursor"]
            
            yield f": keepalive {datetime.utcnow().isoformat()}\n\n"
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

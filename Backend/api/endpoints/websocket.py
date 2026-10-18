"""
WebSocket Endpoint for Real-Time Events
=======================================
Streams EventBus events to connected frontend clients in real-time.

Features:
- Subscribe to specific topics or wildcards
- Automatic event serialization
- Connection management with heartbeat
- Filter events by correlation_id for workflow tracking

Usage:
    ws://localhost:5555/api/ws/events
    ws://localhost:5555/api/ws/events?topics=publish.*,scheduler.*
    ws://localhost:5555/api/ws/events?correlation_id=abc-123
"""

import asyncio
import json
import logging
from typing import Set, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from services.event_bus import EventBus, Event, Topics

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and event subscriptions.
    
    Each connection can subscribe to specific topics using wildcards.
    Events are filtered and sent only to relevant subscribers.
    """
    
    def __init__(self):
        self.active_connections: dict[WebSocket, dict] = {}
        self._event_bus: Optional[EventBus] = None
        self._subscription_id: Optional[str] = None
    
    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            self._event_bus = EventBus.get_instance()
        return self._event_bus
    
    async def connect(
        self,
        websocket: WebSocket,
        topics: List[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Accept a new WebSocket connection with optional topic filters."""
        await websocket.accept()
        
        # Store connection metadata
        self.active_connections[websocket] = {
            "topics": topics or ["*"],  # Default to all events
            "correlation_id": correlation_id,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "events_sent": 0
        }
        
        logger.info(f"WebSocket connected: topics={topics}, correlation_id={correlation_id}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to MediaPoster Event Stream",
            "subscribed_topics": topics or ["*"],
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Ensure we're subscribed to the event bus
        await self._ensure_subscribed()
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")
    
    async def _ensure_subscribed(self):
        """Subscribe to EventBus if not already subscribed."""
        if self._subscription_id is None:
            # Subscribe to all events with wildcard
            self._subscription_id = self.event_bus.subscribe(
                "*",
                self._handle_event
            )
            logger.info("WebSocket manager subscribed to EventBus")
    
    async def _handle_event(self, event: Event):
        """Handle an event from the EventBus and broadcast to relevant WebSocket clients."""
        if not self.active_connections:
            return
        
        # Serialize event for sending
        event_data = {
            "type": "event",
            "event": {
                "id": event.id,
                "topic": event.topic,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "correlation_id": event.correlation_id,
                "payload": event.payload,
                "source": event.source
            }
        }
        
        # Send to matching connections
        disconnected = []
        for websocket, metadata in self.active_connections.items():
            try:
                if self._should_send(event, metadata):
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(event_data)
                        metadata["events_sent"] += 1
            except Exception as e:
                logger.warning(f"Error sending to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)
    
    def _should_send(self, event: Event, metadata: dict) -> bool:
        """Check if an event should be sent to a specific connection."""
        # Check correlation_id filter
        if metadata.get("correlation_id"):
            if event.correlation_id != metadata["correlation_id"]:
                return False
        
        # Check topic filters
        topics = metadata.get("topics", ["*"])
        for pattern in topics:
            if self._topic_matches(event.topic, pattern):
                return True
        
        return False
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if a topic matches a pattern (supports * wildcard)."""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return topic == pattern
        
        # Handle prefix wildcard (e.g., "publish.*")
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix + ".")
        
        # Handle suffix wildcard (e.g., "*.completed")
        if pattern.startswith("*."):
            suffix = pattern[2:]
            return topic.endswith("." + suffix)
        
        return topic == pattern
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for websocket in self.active_connections:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)
        
        for ws in disconnected:
            self.disconnect(ws)
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "connections": [
                {
                    "topics": meta["topics"],
                    "correlation_id": meta["correlation_id"],
                    "connected_at": meta["connected_at"],
                    "events_sent": meta["events_sent"]
                }
                for meta in self.active_connections.values()
            ]
        }


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    topics: Optional[str] = Query(None, description="Comma-separated topic patterns (e.g., 'publish.*,scheduler.*')"),
    correlation_id: Optional[str] = Query(None, description="Filter by workflow correlation ID")
):
    """
    WebSocket endpoint for real-time event streaming.
    
    Query Parameters:
        - topics: Comma-separated list of topic patterns (supports * wildcard)
        - correlation_id: Filter events by a specific workflow correlation ID
    
    Example URLs:
        ws://localhost:5555/api/ws/events
        ws://localhost:5555/api/ws/events?topics=publish.*,scheduler.*
        ws://localhost:5555/api/ws/events?correlation_id=abc-123
    
    Messages sent:
        - {"type": "connected", ...}  - On connection
        - {"type": "event", "event": {...}}  - For each matching event
        - {"type": "pong"}  - Response to ping
    """
    # Parse topic patterns
    topic_list = None
    if topics:
        topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    
    try:
        await manager.connect(websocket, topic_list, correlation_id)
    except WebSocketDisconnect:
        # Client disconnected during connection - this is normal during page navigation
        logger.debug("Client disconnected during WebSocket connection setup")
        return
    except Exception as e:
        logger.debug(f"WebSocket connection failed: {e}")
        return
    
    try:
        while True:
            # Wait for messages from client (ping/pong, unsubscribe, etc.)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client messages
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")
                    
                    if msg_type == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
                    
                    elif msg_type == "subscribe":
                        # Update subscription topics
                        new_topics = message.get("topics", [])
                        if new_topics:
                            manager.active_connections[websocket]["topics"] = new_topics
                            await websocket.send_json({
                                "type": "subscribed",
                                "topics": new_topics
                            })
                    
                    elif msg_type == "unsubscribe":
                        # Remove specific topics
                        remove_topics = message.get("topics", [])
                        current = manager.active_connections[websocket]["topics"]
                        updated = [t for t in current if t not in remove_topics]
                        manager.active_connections[websocket]["topics"] = updated
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "topics": updated
                        })
                
                except json.JSONDecodeError:
                    # Plain text message, could be a ping
                    if data == "ping":
                        await websocket.send_text("pong")
            
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return manager.get_stats()


@router.get("/ws/topics")
async def get_available_topics():
    """Get list of available event topics for subscription."""
    return {
        "topics": Topics.all_topics(),
        "example_patterns": [
            "*",              # All events
            "publish.*",      # All publish events
            "scheduler.*",    # All scheduler events
            "*.completed",    # All completion events
            "*.failed",       # All failure events
        ]
    }

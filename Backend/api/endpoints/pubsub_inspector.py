"""
Pub/Sub Inspector API Endpoints (AC-007)
=========================================
Topics list, recent events, consumer lag, and subscription management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone
import logging

router = APIRouter(prefix="/api/pubsub", tags=["Pub/Sub Inspector"])
logger = logging.getLogger(__name__)


# =============================================================================
# Topics
# =============================================================================

@router.get("/topics")
async def list_topics(domain: Optional[str] = None):
    """
    List all registered event topics (AC-007).
    Optionally filter by domain (e.g. 'media', 'publish', 'twitter').
    """
    from services.event_bus import Topics

    all_topics = Topics.all_topics()

    if domain:
        all_topics = [t for t in all_topics if t.startswith(f"{domain}.")]

    # Group by domain
    domains = {}
    for topic in sorted(all_topics):
        d = topic.split(".")[0]
        if d not in domains:
            domains[d] = []
        domains[d].append(topic)

    return {
        "topics": sorted(all_topics),
        "count": len(all_topics),
        "domains": domains,
        "domain_count": len(domains),
    }


@router.get("/topics/{topic:path}/events")
async def get_topic_events(
    topic: str,
    limit: int = Query(default=20, le=100),
):
    """
    Get recent events for a specific topic (AC-007).
    Returns the last N events published to this topic.
    """
    from services.event_bus import get_event_bus

    bus = get_event_bus()
    history = bus.get_topic_history(topic, limit=limit)

    return {
        "topic": topic,
        "events": history,
        "count": len(history),
    }


@router.get("/topics/{topic:path}/stats")
async def get_topic_stats(topic: str):
    """
    Get statistics for a specific topic (AC-007).
    Shows subscriber count, event rate, and last event timestamp.
    """
    from services.event_bus import get_event_bus

    bus = get_event_bus()
    subscribers = bus.get_topic_subscribers(topic)
    history = bus.get_topic_history(topic, limit=1)

    last_event_at = None
    if history:
        last_event_at = history[0].get("timestamp") or history[0].get("created_at")

    return {
        "topic": topic,
        "subscriber_count": len(subscribers),
        "subscribers": subscribers,
        "last_event_at": last_event_at,
    }


# =============================================================================
# Subscribers / Consumer Lag
# =============================================================================

@router.get("/subscribers")
async def list_subscribers():
    """
    List all active subscribers across all topics (AC-007).
    Shows which workers/services are listening to which events.
    """
    from services.event_bus import get_event_bus

    bus = get_event_bus()
    all_subs = bus.get_all_subscribers()

    return {
        "subscribers": all_subs,
        "count": sum(len(subs) for subs in all_subs.values()),
    }


@router.get("/lag")
async def get_consumer_lag():
    """
    Get consumer lag across all topics (AC-007).
    Shows pending messages per consumer group for Redis-backed bus.
    """
    from services.event_bus import get_event_bus

    bus = get_event_bus()
    lag_data = bus.get_consumer_lag()

    return {
        "lag": lag_data,
        "total_pending": sum(v.get("pending", 0) for v in lag_data.values()) if isinstance(lag_data, dict) else 0,
    }


# =============================================================================
# Event Bus Stats
# =============================================================================

@router.get("/stats")
async def get_bus_stats():
    """
    Get overall event bus statistics (AC-007).
    Shows total events published/consumed, errors, and uptime.
    """
    from services.event_bus import get_event_bus

    bus = get_event_bus()
    stats = bus.get_stats()

    return {
        "stats": stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
async def get_bus_health():
    """
    Health check for the event bus (AC-007).
    Returns bus type (in-memory vs Redis), connection status, topic count.
    """
    from services.event_bus import get_event_bus, Topics

    bus = get_event_bus()
    stats = bus.get_stats()
    all_topics = Topics.all_topics()

    return {
        "healthy": True,
        "bus_type": getattr(bus, "bus_type", "in-memory"),
        "registered_topics": len(all_topics),
        "stats": stats,
    }

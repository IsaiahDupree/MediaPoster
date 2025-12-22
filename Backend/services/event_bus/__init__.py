"""
Event Bus Module
================
Topic-based pub/sub architecture for long-running workflows.

Usage:
    from services.event_bus import EventBus, Topics, Event
    
    # Get the global event bus instance
    bus = EventBus.get_instance()
    
    # Subscribe to a topic
    bus.subscribe(Topics.MEDIA_INGESTED, my_handler)
    
    # Publish an event
    await bus.publish(Topics.MEDIA_INGESTED, {"media_id": "abc123"})
"""

from .event import Event
from .topics import Topics
from .bus import EventBus

__all__ = ['Event', 'Topics', 'EventBus']

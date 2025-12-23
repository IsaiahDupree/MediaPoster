"""
Agent Framework
================
Pub/Sub event bus and background scheduler for AI agents.
"""

from .event_bus import (
    AgentEventBus,
    AgentEvent,
    AgentEventEmitter,
    AgentType,
    EventType,
    get_event_bus
)

from .background_scheduler import (
    AgentBackgroundScheduler,
    ScheduledTask,
    TaskStatus,
    get_scheduler,
    start_background_agents,
    stop_background_agents
)

__all__ = [
    'AgentEventBus',
    'AgentEvent',
    'AgentEventEmitter',
    'AgentType',
    'EventType',
    'get_event_bus',
    'AgentBackgroundScheduler',
    'ScheduledTask',
    'TaskStatus',
    'get_scheduler',
    'start_background_agents',
    'stop_background_agents',
]

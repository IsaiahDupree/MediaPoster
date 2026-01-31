"""
MediaPoster Control Plane

External command & control interface for MediaPoster.
Runs on port 9100 and allows external services to:
- Submit pipeline commands
- Receive status updates
- Fetch results

Usage:
    # Start the Control Plane API
    python -m control_plane.main
    
    # Or with uvicorn directly
    uvicorn control_plane.main:app --host 127.0.0.1 --port 9100
"""

from .main import app, start
from .schemas import (
    CommandEnvelope,
    CommandAck,
    EventEnvelope,
    JobState,
    HealthResponse,
    ReadyResponse
)

__all__ = [
    "app",
    "start",
    "CommandEnvelope",
    "CommandAck", 
    "EventEnvelope",
    "JobState",
    "HealthResponse",
    "ReadyResponse"
]

__version__ = "1.0.0"

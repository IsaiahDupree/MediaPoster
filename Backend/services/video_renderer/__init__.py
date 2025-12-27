"""
Video Renderer Service
======================
Abstract adapter pattern for video rendering engines.

Supports:
- Motion Canvas (default, open-source)
- Remotion (fallback, React-based)
"""

from .base import VideoRenderer, RenderRequest, RenderResponse, RenderJobStatus
from .motion_canvas_adapter import MotionCanvasAdapter
from .remotion_adapter import RemotionAdapter

__all__ = [
    "VideoRenderer",
    "RenderRequest",
    "RenderResponse",
    "RenderJobStatus",
    "MotionCanvasAdapter",
    "RemotionAdapter",
]


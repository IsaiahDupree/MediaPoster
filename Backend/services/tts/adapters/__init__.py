"""
TTS Adapters
============
Adapter implementations for different TTS models.
"""

from .base import TTSAdapter
from .indextts2 import IndexTTS2Adapter

__all__ = [
    "TTSAdapter",
    "IndexTTS2Adapter",
]


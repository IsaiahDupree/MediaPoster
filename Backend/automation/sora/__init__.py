"""
Sora Browser Automation Module

Automates Safari to interact with sora.chatgpt.com for AI video generation.
"""

from .sora_controller import SoraController
from .generation_monitor import GenerationMonitor
from .video_downloader import VideoDownloader
from .pipeline import SoraPipeline

__all__ = [
    "SoraController",
    "GenerationMonitor",
    "VideoDownloader",
    "SoraPipeline",
]

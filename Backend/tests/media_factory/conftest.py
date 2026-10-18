"""
Media Factory Test Configuration
================================
Shared fixtures and configuration for Media Factory tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import tempfile
import shutil

from services.event_bus import EventBus


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    bus = Mock(spec=EventBus)
    bus.publish = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.get_instance = Mock(return_value=bus)
    return bus


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create sample audio file for testing."""
    audio_file = temp_dir / "test_audio.wav"
    audio_file.write_bytes(b"fake audio content")
    return audio_file


@pytest.fixture
def sample_video_file(temp_dir):
    """Create sample video file for testing."""
    video_file = temp_dir / "test_video.mp4"
    video_file.write_bytes(b"fake video content")
    return video_file


@pytest.fixture
def sample_image_file(temp_dir):
    """Create sample image file for testing."""
    image_file = temp_dir / "test_image.png"
    image_file.write_bytes(b"fake image content")
    return image_file


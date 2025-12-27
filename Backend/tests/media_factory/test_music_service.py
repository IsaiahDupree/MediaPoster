"""
Music Service Tests
==================
Tests for music service functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from services.music.models import MusicRequest, MusicResponse, MusicSource, MusicSearchCriteria
from services.music.adapters.suno import SunoAdapter
from services.music.adapters.soundcloud import SoundCloudAdapter
from services.music.worker import MusicWorker


class TestMusicModels:
    """Test music data models."""
    
    def test_music_request_creation(self):
        """Test MusicRequest model creation."""
        request = MusicRequest(
            source=MusicSource.SUNO,
            suno_file_path="/path/to/suno.mp3"
        )
        assert request.source == MusicSource.SUNO
        assert request.suno_file_path == "/path/to/suno.mp3"
        assert request.job_id is not None
    
    def test_music_search_criteria(self):
        """Test MusicSearchCriteria model."""
        criteria = MusicSearchCriteria(
            mood="energetic",
            genre="hip-hop",
            bpm_min=120,
            bpm_max=140,
            trending=True
        )
        assert criteria.mood == "energetic"
        assert criteria.genre == "hip-hop"
        assert criteria.trending is True


class TestSunoAdapter:
    """Test Suno adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create Suno adapter."""
        return SunoAdapter(suno_dir="/tmp/test_suno")
    
    def test_get_source_name(self, adapter):
        """Test source name."""
        assert adapter.get_source_name() == "suno"
    
    def test_supports_search(self, adapter):
        """Test search support."""
        assert adapter.supports_search() is True
    
    @pytest.mark.asyncio
    async def test_search_music(self, adapter):
        """Test music search."""
        # Create test audio file
        test_file = adapter.suno_dir / "test.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        
        criteria = MusicSearchCriteria()
        results = await adapter.search_music(criteria, limit=10)
        
        assert len(results) > 0
        assert results[0]["source"] == "suno"
        
        # Cleanup
        test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_get_music(self, adapter):
        """Test getting music file."""
        # Create test audio file
        test_file = adapter.suno_dir / "test.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        
        result = await adapter.get_music("test.mp3")
        
        assert result.success is True
        assert result.music_path is not None
        
        # Cleanup
        test_file.unlink()


class TestSoundCloudAdapter:
    """Test SoundCloud adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create SoundCloud adapter."""
        return SoundCloudAdapter(rapidapi_key="test_key")
    
    def test_get_source_name(self, adapter):
        """Test source name."""
        assert adapter.get_source_name() == "soundcloud"
    
    @pytest.mark.asyncio
    async def test_search_music_mock(self, adapter):
        """Test music search with mocked API."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "tracks": [
                    {
                        "id": "123",
                        "title": "Test Track",
                        "duration": 180000,
                        "genre": "hip-hop"
                    }
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            criteria = MusicSearchCriteria(genre="hip-hop")
            results = await adapter.search_music(criteria, limit=10)
            
            assert len(results) > 0
            assert results[0]["source"] == "soundcloud"


class TestMusicWorker:
    """Test music worker."""
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = AsyncMock()
        return bus
    
    @pytest.fixture
    def worker(self, event_bus):
        """Create music worker."""
        return MusicWorker(event_bus)
    
    def test_get_subscriptions(self, worker):
        """Test worker subscriptions."""
        from services.event_bus import Topics
        subscriptions = worker.get_subscriptions()
        assert Topics.MUSIC_REQUESTED in subscriptions


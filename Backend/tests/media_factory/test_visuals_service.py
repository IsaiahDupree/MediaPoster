"""
Visuals Service Tests
=====================
Tests for visuals service functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from services.visuals.models import VisualsRequest, VisualsResponse, VisualsType, VisualsSource, VisualsSearchCriteria
from services.visuals.adapters.meme import MemeAdapter
from services.visuals.adapters.broll import BrollAdapter
from services.visuals.adapters.ugc import UGCAdapter
from services.visuals.worker import VisualsWorker


class TestVisualsModels:
    """Test visuals data models."""
    
    def test_visuals_request_creation(self):
        """Test VisualsRequest model creation."""
        request = VisualsRequest(
            visuals_type=VisualsType.MEME,
            source=VisualsSource.LOCAL,
            file_path="/path/to/meme.png"
        )
        assert request.visuals_type == VisualsType.MEME
        assert request.source == VisualsSource.LOCAL
        assert request.job_id is not None
    
    def test_visuals_search_criteria(self):
        """Test VisualsSearchCriteria model."""
        criteria = VisualsSearchCriteria(
            visuals_type=VisualsType.BROLL,
            keywords=["tech", "lifestyle"],
            mood="energetic",
            trending=True
        )
        assert criteria.visuals_type == VisualsType.BROLL
        assert "tech" in criteria.keywords
        assert criteria.trending is True


class TestMemeAdapter:
    """Test Meme adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create Meme adapter."""
        return MemeAdapter(meme_dir="/tmp/test_memes")
    
    def test_get_source_name(self, adapter):
        """Test source name."""
        assert adapter.get_source_name() == "meme"
    
    @pytest.mark.asyncio
    async def test_search_visuals(self, adapter):
        """Test meme search."""
        # Create test meme file
        test_file = adapter.meme_dir / "test_meme.png"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        
        criteria = VisualsSearchCriteria(visuals_type=VisualsType.MEME)
        results = await adapter.search_visuals(VisualsType.MEME, criteria, limit=10)
        
        assert len(results) > 0
        assert results[0]["type"] == "meme"
        
        # Cleanup
        test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_get_visuals(self, adapter):
        """Test getting meme file."""
        # Create test meme file
        test_file = adapter.meme_dir / "test_meme.png"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        
        result = await adapter.get_visuals("test_meme.png")
        
        assert result.success is True
        assert result.visuals_path is not None
        
        # Cleanup
        test_file.unlink()


class TestBrollAdapter:
    """Test B-roll adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create B-roll adapter."""
        return BrollAdapter(broll_dir="/tmp/test_broll")
    
    def test_get_source_name(self, adapter):
        """Test source name."""
        assert adapter.get_source_name() == "broll"
    
    @pytest.mark.asyncio
    async def test_search_visuals(self, adapter):
        """Test B-roll search."""
        # Create test video file
        test_file = adapter.broll_dir / "test_broll.mp4"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        
        criteria = VisualsSearchCriteria(visuals_type=VisualsType.BROLL)
        results = await adapter.search_visuals(VisualsType.BROLL, criteria, limit=10)
        
        assert len(results) > 0
        assert results[0]["type"] == "broll"
        
        # Cleanup
        test_file.unlink()


class TestUGCAdapter:
    """Test UGC adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create UGC adapter."""
        return UGCAdapter(ugc_dir="/tmp/test_ugc")
    
    def test_get_source_name(self, adapter):
        """Test source name."""
        assert adapter.get_source_name() == "ugc"
    
    @pytest.mark.asyncio
    async def test_search_visuals(self, adapter):
        """Test UGC search."""
        # Create test UGC file
        test_file = adapter.ugc_dir / "test_ugc.mp4"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        
        criteria = VisualsSearchCriteria(visuals_type=VisualsType.UGC)
        results = await adapter.search_visuals(VisualsType.UGC, criteria, limit=10)
        
        assert len(results) > 0
        assert results[0]["source"] == "local_ugc"
        
        # Cleanup
        test_file.unlink()


class TestVisualsWorker:
    """Test visuals worker."""
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = AsyncMock()
        return bus
    
    @pytest.fixture
    def worker(self, event_bus):
        """Create visuals worker."""
        return VisualsWorker(event_bus)
    
    def test_get_subscriptions(self, worker):
        """Test worker subscriptions."""
        from services.event_bus import Topics
        subscriptions = worker.get_subscriptions()
        assert Topics.VISUALS_REQUESTED in subscriptions


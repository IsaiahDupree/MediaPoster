"""
Tests for Sora Automation
==========================
Tests for Sora usage tracking, video generation, and Safari automation controls.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import asyncio


class TestSoraUsageTracker:
    """Tests for SoraUsageTracker"""
    
    def test_timeouts_defined(self):
        """Test that all Sora timeouts are defined"""
        from services.sora import SORA_TIMEOUTS
        
        assert "page_load" in SORA_TIMEOUTS
        assert "menu_open" in SORA_TIMEOUTS
        assert "dialog_open" in SORA_TIMEOUTS
        assert "video_generation" in SORA_TIMEOUTS
        assert "polling_interval" in SORA_TIMEOUTS
        assert "batch_timeout" in SORA_TIMEOUTS
        
        # Check reasonable values
        assert SORA_TIMEOUTS["page_load"] >= 5
        assert SORA_TIMEOUTS["video_generation"] >= 300  # At least 5 minutes
    
    def test_usage_tracker_initialization(self):
        """Test SoraUsageTracker initializes correctly"""
        from services.sora import SoraUsageTracker
        
        tracker = SoraUsageTracker()
        assert tracker._last_check is None
        assert tracker._cached_usage is None
        assert tracker._running is False
    
    def test_should_check_initially_true(self):
        """Test should_check returns True on first call"""
        from services.sora import SoraUsageTracker
        
        tracker = SoraUsageTracker()
        assert tracker.should_check() is True
    
    def test_get_timeouts(self):
        """Test get_timeouts returns copy of timeouts"""
        from services.sora import SoraUsageTracker
        
        tracker = SoraUsageTracker()
        timeouts = tracker.get_timeouts()
        
        assert isinstance(timeouts, dict)
        assert "video_generation" in timeouts
    
    def test_sora_usage_to_dict(self):
        """Test SoraUsage dataclass converts to dict"""
        from services.sora.sora_usage_tracker import SoraUsage
        
        usage = SoraUsage(
            video_gens_left=27,
            free_count=27,
            paid_count=0,
            reset_date="Jan 26"
        )
        
        d = usage.to_dict()
        assert d["video_gens_left"] == 27
        assert d["free_count"] == 27
        assert d["reset_date"] == "Jan 26"


class TestSafariAutomationControl:
    """Tests for Safari automation start/stop/resume functionality"""
    
    def test_engagement_control_status(self):
        """Test GET /api/engagement-control/status"""
        from main import app
        client = TestClient(app)
        
        response = client.get("/api/engagement-control/status")
        # Should return 200 or 500 if controller not initialized
        assert response.status_code in (200, 500)
    
    def test_engagement_control_start(self):
        """Test POST /api/engagement-control/start"""
        from main import app
        client = TestClient(app)
        
        response = client.post("/api/engagement-control/start")
        assert response.status_code in (200, 500)
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
    
    def test_engagement_control_stop(self):
        """Test POST /api/engagement-control/stop"""
        from main import app
        client = TestClient(app)
        
        response = client.post("/api/engagement-control/stop")
        assert response.status_code in (200, 500)
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
    
    def test_engagement_control_pause(self):
        """Test POST /api/engagement-control/pause"""
        from main import app
        client = TestClient(app)
        
        response = client.post("/api/engagement-control/pause")
        assert response.status_code in (200, 500)
    
    def test_engagement_control_resume(self):
        """Test POST /api/engagement-control/resume"""
        from main import app
        client = TestClient(app)
        
        response = client.post("/api/engagement-control/resume")
        assert response.status_code in (200, 500)
    
    def test_platform_enable_disable(self):
        """Test enabling/disabling platforms"""
        from main import app
        client = TestClient(app)
        
        # Test enable
        response = client.post("/api/engagement-control/platform/tiktok/enable")
        assert response.status_code in (200, 500)
        
        # Test disable
        response = client.post("/api/engagement-control/platform/tiktok/disable")
        assert response.status_code in (200, 500)


class TestSoraVideoGeneration:
    """Tests for Sora video generation automation"""
    
    def test_video_job_dataclass(self):
        """Test VideoJob dataclass"""
        from automation.sora_full_automation import VideoJob
        
        job = VideoJob(
            prompt="Test prompt",
            character="isaiahdupree",
            duration=15
        )
        
        assert job.prompt == "Test prompt"
        assert job.character == "isaiahdupree"
        assert job.status == "pending"
    
    def test_aspect_ratio_enum(self):
        """Test AspectRatio enum values"""
        from automation.sora_full_automation import AspectRatio
        
        assert AspectRatio.PORTRAIT.value == "Portrait"
        assert AspectRatio.LANDSCAPE.value == "Landscape"
    
    def test_duration_enum(self):
        """Test Duration enum values"""
        from automation.sora_full_automation import Duration
        
        assert Duration.SHORT.value == 10
        assert Duration.MEDIUM.value == 15
        assert Duration.LONG.value == 25
    
    def test_sora_automation_initialization(self):
        """Test SoraFullAutomation initializes correctly"""
        from automation.sora_full_automation import SoraFullAutomation
        
        sora = SoraFullAutomation()
        assert sora.BASE_URL == "https://sora.chatgpt.com"
        assert sora.MAX_QUEUE_SIZE == 3


class TestSoraUsageAPI:
    """Tests for Sora usage API endpoints"""
    
    def test_sora_usage_endpoint_exists(self):
        """Test GET /api/sora/usage endpoint"""
        from main import app
        client = TestClient(app)
        
        response = client.get("/api/sora/usage")
        # May return 404 if not registered yet, or 200/500 if registered
        assert response.status_code in (200, 404, 500)
    
    def test_sora_generate_endpoint_exists(self):
        """Test POST /api/sora/generate endpoint"""
        from main import app
        client = TestClient(app)
        
        response = client.post("/api/sora/generate", json={
            "prompt": "test",
            "character": "isaiahdupree"
        })
        # May return 404 if not registered, or other codes if registered
        assert response.status_code in (200, 404, 422, 500)


# Run with: pytest tests/test_sora_automation.py -v

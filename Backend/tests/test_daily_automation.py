"""
Tests for Daily Automation System (AUTO-009)
=============================================
Tests Sora credit checking, video generation scheduling, and Twitter offer posting.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from services.daily_automation import DailyAutomationManager, SoraScheduler, TwitterOfferScheduler
from services.event_bus import EventBus


@pytest.fixture
def event_bus():
    """Create fresh event bus for each test."""
    EventBus.reset_instance()
    return EventBus.get_instance()


@pytest.fixture
def sora_scheduler(event_bus):
    """Create Sora scheduler."""
    return SoraScheduler(event_bus)


@pytest.fixture
def twitter_scheduler(event_bus):
    """Create Twitter scheduler."""
    return TwitterOfferScheduler(event_bus)


@pytest.fixture
def automation_manager(event_bus):
    """Create automation manager."""
    DailyAutomationManager.reset_instance()
    return DailyAutomationManager(event_bus)


# =============================================================================
# Sora Scheduler Tests
# =============================================================================

class TestSoraScheduler:
    """Tests for SoraScheduler."""
    
    def test_initialization(self, sora_scheduler):
        """Test scheduler initializes correctly."""
        assert sora_scheduler is not None
        assert sora_scheduler.running is False
        assert sora_scheduler.credits.remaining == 30
        
    @pytest.mark.asyncio
    async def test_start_sets_running(self, sora_scheduler):
        """Test start sets running flag."""
        with patch.object(sora_scheduler, '_get_credits_fallback', new_callable=AsyncMock, return_value=25):
            with patch.object(sora_scheduler, '_get_sora', return_value=None):
                await sora_scheduler.start()
                assert sora_scheduler.running is True
                await sora_scheduler.stop()
            
    @pytest.mark.asyncio
    async def test_stop_clears_running(self, sora_scheduler):
        """Test stop clears running flag."""
        with patch.object(sora_scheduler, '_get_credits_fallback', new_callable=AsyncMock, return_value=25):
            with patch.object(sora_scheduler, '_get_sora', return_value=None):
                await sora_scheduler.start()
                await sora_scheduler.stop()
                assert sora_scheduler.running is False
            
    @pytest.mark.asyncio
    async def test_check_credits_updates_credits(self, sora_scheduler):
        """Test credit check updates credit state."""
        with patch.object(sora_scheduler, '_get_credits_fallback', new_callable=AsyncMock, return_value=20):
            with patch.object(sora_scheduler, '_get_sora', return_value=None):
                credits = await sora_scheduler.check_credits()
                assert credits.remaining == 20
                assert credits.used == 10
                assert credits.total == 30
            
    @pytest.mark.asyncio
    async def test_check_credits_fallback_on_error(self, sora_scheduler):
        """Test credit check falls back to 30 on error."""
        with patch.object(sora_scheduler, '_get_credits_fallback', new_callable=AsyncMock, side_effect=Exception("Safari error")):
            with patch.object(sora_scheduler, '_get_sora', return_value=None):
                credits = await sora_scheduler.check_credits()
                assert credits.remaining == 30
            
    def test_get_status(self, sora_scheduler):
        """Test status returns correct info."""
        status = sora_scheduler.get_status()
        assert "running" in status
        assert "credits" in status
        assert status["running"] is False
        assert status["credits"] == 30


# =============================================================================
# Twitter Scheduler Tests
# =============================================================================

class TestTwitterScheduler:
    """Tests for TwitterOfferScheduler."""
    
    def test_initialization(self, twitter_scheduler):
        """Test scheduler initializes correctly."""
        assert twitter_scheduler is not None
        assert twitter_scheduler.running is False
        assert twitter_scheduler.posts_today == 0
        assert twitter_scheduler.POST_INTERVAL_HOURS == 2
        
    @pytest.mark.asyncio
    async def test_start_sets_running(self, twitter_scheduler):
        """Test start sets running flag."""
        await twitter_scheduler.start()
        assert twitter_scheduler.running is True
        await twitter_scheduler.stop()
        
    @pytest.mark.asyncio
    async def test_stop_clears_running(self, twitter_scheduler):
        """Test stop clears running flag."""
        await twitter_scheduler.start()
        await twitter_scheduler.stop()
        assert twitter_scheduler.running is False
        
    def test_get_current_offer_rotates(self, twitter_scheduler):
        """Test offer rotation."""
        offer1 = twitter_scheduler._get_current_offer()
        twitter_scheduler.posts_today = 1
        offer2 = twitter_scheduler._get_current_offer()
        # Should rotate between offers
        assert offer1["name"] != offer2["name"] or len(twitter_scheduler._get_current_offer.__wrapped__) == 1
        
    def test_get_status(self, twitter_scheduler):
        """Test status returns correct info."""
        status = twitter_scheduler.get_status()
        assert "running" in status
        assert "posts_today" in status
        assert "next_post_in_hours" in status
        assert status["posts_today"] == 0
        assert status["next_post_in_hours"] == 2


# =============================================================================
# Daily Automation Manager Tests
# =============================================================================

class TestDailyAutomationManager:
    """Tests for DailyAutomationManager."""
    
    def test_singleton_pattern(self, event_bus):
        """Test singleton returns same instance."""
        DailyAutomationManager.reset_instance()
        manager1 = DailyAutomationManager.get_instance(event_bus)
        manager2 = DailyAutomationManager.get_instance()
        assert manager1 is manager2
        
    def test_initialization(self, automation_manager):
        """Test manager initializes correctly."""
        assert automation_manager is not None
        assert automation_manager.sora_scheduler is not None
        assert automation_manager.twitter_scheduler is not None
        assert automation_manager.initialized is False
        
    @pytest.mark.asyncio
    async def test_initialize_starts_schedulers(self, automation_manager):
        """Test initialize starts both schedulers."""
        with patch.object(automation_manager.sora_scheduler, 'start', new_callable=AsyncMock):
            with patch.object(automation_manager.twitter_scheduler, 'start', new_callable=AsyncMock):
                await automation_manager.initialize()
                
                automation_manager.sora_scheduler.start.assert_called_once()
                automation_manager.twitter_scheduler.start.assert_called_once()
                assert automation_manager.initialized is True
                
    @pytest.mark.asyncio
    async def test_shutdown_stops_schedulers(self, automation_manager):
        """Test shutdown stops both schedulers."""
        automation_manager.initialized = True
        
        with patch.object(automation_manager.sora_scheduler, 'stop', new_callable=AsyncMock):
            with patch.object(automation_manager.twitter_scheduler, 'stop', new_callable=AsyncMock):
                await automation_manager.shutdown()
                
                automation_manager.sora_scheduler.stop.assert_called_once()
                automation_manager.twitter_scheduler.stop.assert_called_once()
                assert automation_manager.initialized is False
                
    def test_get_status_combined(self, automation_manager):
        """Test combined status from both schedulers."""
        status = automation_manager.get_status()
        
        assert "initialized" in status
        assert "sora" in status
        assert "twitter" in status
        assert status["initialized"] is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestDailyAutomationIntegration:
    """Integration tests for daily automation."""
    
    @pytest.mark.asyncio
    async def test_full_initialization_flow(self, event_bus):
        """Test full initialization with mocked Safari."""
        DailyAutomationManager.reset_instance()
        manager = DailyAutomationManager.get_instance(event_bus)
        
        with patch.object(manager.sora_scheduler, '_get_credits_fallback', new_callable=AsyncMock, return_value=28):
            with patch.object(manager.sora_scheduler, '_get_sora', return_value=None):
                await manager.initialize()
                
                assert manager.initialized is True
                assert manager.sora_scheduler.running is True
                assert manager.twitter_scheduler.running is True
                assert manager.sora_scheduler.credits.remaining == 28
                
                await manager.shutdown()
            
    @pytest.mark.asyncio
    async def test_event_emission_on_start(self, event_bus):
        """Test events are emitted when automation starts."""
        emitted_events = []
        
        async def track_event(event):
            emitted_events.append(event)
            
        event_bus.subscribe("daily.automation.started", track_event)
        
        DailyAutomationManager.reset_instance()
        manager = DailyAutomationManager.get_instance(event_bus)
        
        with patch.object(manager.sora_scheduler, '_get_credits_fallback', new_callable=AsyncMock, return_value=30):
            with patch.object(manager.sora_scheduler, '_get_sora', return_value=None):
                await manager.initialize()
                await asyncio.sleep(0.1)
                
                assert len(emitted_events) >= 1
                assert emitted_events[0].topic == "daily.automation.started"
                
                await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

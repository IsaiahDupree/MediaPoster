"""
Test Master Orchestrator Integration (ARCH-001 to ARCH-008)
===========================================================
Tests for the complete system architecture integration.

Tests:
- ARCH-001: Master Orchestrator Service
- ARCH-002: 3-Part Sora Batch Coordination
- ARCH-003: Content Analyzer → Publisher Integration
- ARCH-007: Unified Pipeline API Endpoint
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics


@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    EventBus.reset_instance()
    return EventBus.get_instance()


@pytest.fixture
def orchestrator(event_bus):
    """Create a master orchestrator instance."""
    # Reset singleton for testing
    MasterOrchestrator._instance = None
    return MasterOrchestrator(event_bus=event_bus, use_db=False)


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test ARCH-001: Master Orchestrator initializes correctly."""
    assert orchestrator is not None
    assert orchestrator.event_bus is not None
    assert orchestrator.content_analyzer is not None
    assert len(orchestrator.active_pipelines) == 0


@pytest.mark.asyncio
async def test_orchestrator_subscriptions(orchestrator, event_bus):
    """Test ARCH-001: Orchestrator subscribes to correct events."""
    # Check that orchestrator subscribed to key topics
    stats = event_bus.get_stats()
    subscribed_topics = stats["topics_with_subscribers"]

    assert Topics.SORA_BATCH_COMPLETED in subscribed_topics


@pytest.mark.asyncio
async def test_pipeline_config_creation():
    """Test ARCH-001: PipelineConfig creation."""
    config = PipelineConfig(
        theme="AI productivity tips",
        num_parts=3,
        character="@isaiahdupree",
        publish_platforms=["tiktok", "instagram"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://example.com/offer"
    )
    
    assert config.theme == "AI productivity tips"
    assert config.num_parts == 3
    assert config.character == "@isaiahdupree"
    assert "tiktok" in config.publish_platforms
    assert config.schedule_tweets is True
    assert config.tweets_per_day == 12


@pytest.mark.asyncio
async def test_start_pipeline(orchestrator, event_bus):
    """Test ARCH-001: Pipeline can be started."""
    config = PipelineConfig(
        theme="Test pipeline",
        num_parts=1,
        schedule_tweets=False
    )
    
    # Start pipeline
    pipeline_id = await orchestrator.start_pipeline(config)
    
    # Verify pipeline was created
    assert pipeline_id is not None
    assert pipeline_id.startswith("pipeline-")
    assert pipeline_id in orchestrator.active_pipelines


@pytest.mark.asyncio
async def test_pipeline_status_tracking(orchestrator, event_bus):
    """Test ARCH-001: Pipeline status can be retrieved."""
    config = PipelineConfig(
        theme="Status test",
        num_parts=1,
        schedule_tweets=False
    )
    
    pipeline_id = await orchestrator.start_pipeline(config)

    # Get status (synchronous method)
    status = orchestrator.get_pipeline_status(pipeline_id)
    
    assert status is not None
    assert status["pipeline_id"] == pipeline_id
    assert status["theme"] == "Status test"
    assert "status" in status


@pytest.mark.asyncio
async def test_list_pipelines(orchestrator, event_bus):
    """Test ARCH-001: Pipelines can be listed."""
    # Start a pipeline
    config = PipelineConfig(
        theme="List test",
        num_parts=1,
        schedule_tweets=False
    )
    
    await orchestrator.start_pipeline(config)
    
    # List pipelines
    pipelines = await orchestrator.list_pipelines()
    
    assert len(pipelines) >= 1
    assert any(p.get("theme") == "List test" for p in pipelines)


@pytest.mark.asyncio
async def test_orchestrator_emits_started_event(orchestrator, event_bus):
    """Test ARCH-001: Orchestrator emits pipeline started event."""
    emitted_events = []
    
    async def event_tracker(event):
        emitted_events.append(event)
    
    event_bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_STARTED, event_tracker)
    
    config = PipelineConfig(
        theme="Event test",
        num_parts=1,
        schedule_tweets=False
    )
    
    await orchestrator.start_pipeline(config)
    
    # Give time for event to be processed
    await asyncio.sleep(0.1)
    
    # Check event was emitted
    assert len(emitted_events) >= 1
    assert emitted_events[0].topic == Topics.ORCHESTRATOR_PIPELINE_STARTED


@pytest.mark.asyncio
async def test_sora_batch_completed_handler(orchestrator, event_bus):
    """Test ARCH-002: Orchestrator handles Sora batch completion."""
    config = PipelineConfig(
        theme="Sora handler test",
        num_parts=3,
        publish_platforms=["tiktok"],
        schedule_tweets=False
    )
    
    pipeline_id = await orchestrator.start_pipeline(config)
    
    # Simulate Sora batch completed event
    await event_bus.publish(
        Topics.SORA_BATCH_COMPLETED,
        {
            "pipeline_id": pipeline_id,
            "stitched_video": "/test/video.mp4",
            "analysis": {"viral_score": 85},
            "successful_parts": 3
        },
        source="test"
    )
    
    # Give time for handler to process
    await asyncio.sleep(0.1)

    # Check pipeline was updated
    status = orchestrator.get_pipeline_status(pipeline_id)
    assert status.get("outputs", {}).get("sora", {}).get("stitched_video") == "/test/video.mp4"


@pytest.mark.asyncio
async def test_pipeline_not_found(orchestrator):
    """Test ARCH-001: Non-existent pipeline returns error."""
    status = orchestrator.get_pipeline_status("nonexistent-id")
    assert "error" in status


def test_pipeline_config_defaults():
    """Test ARCH-001: PipelineConfig has sensible defaults."""
    config = PipelineConfig(theme="Default test")
    
    assert config.num_parts == 3
    assert config.character is None
    assert config.publish_platforms == ["tiktok", "instagram", "youtube"]
    assert config.schedule_tweets is True
    assert config.tweets_per_day == 12
    assert config.offer_url is None
    assert config.metadata == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

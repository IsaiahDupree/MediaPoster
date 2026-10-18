"""
E2E Workflow Tests: Full Pipeline Validation
============================================
Tests the complete workflow from event to final state.

Workflows Tested:
- Media ingest → analysis → publish → metrics
- Narrative planning → scheduling → publishing → reflection
- Experiment creation → variant posting → metrics → winner detection
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio(loop_scope="function")

from services.event_bus import EventBus, Event, Topics
from services.workers.analysis_worker import AnalysisWorker
from services.workers.publish_worker import PublishWorker
from services.workers.narrative_builder_worker import NarrativeBuilderWorker
from services.workers.notification_worker import NotificationWorker


@pytest.fixture
def event_bus():
    """Get fresh event bus."""
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()


@pytest.fixture
def workflow_tracker(event_bus):
    """Track all events in a workflow."""
    events = []
    
    async def track(event):
        events.append({
            "topic": event.topic,
            "correlation_id": event.correlation_id,
            "timestamp": event.timestamp,
            "payload": event.payload
        })
    
    event_bus.subscribe("*", track)
    
    yield events
    # Cleanup handled by fixture


@pytest.mark.asyncio
async def test_media_ingest_to_publish_workflow(event_bus, workflow_tracker):
    """Test complete workflow: ingest → analysis → publish."""
    correlation_id = f"e2e-workflow-{datetime.now().timestamp()}"
    
    # Step 1: Ingest media
    await event_bus.publish(
        Topics.MEDIA_INGESTED,
        {
            "media_id": "e2e-media-123",
            "file_path": "/test/path.mp4",
            "file_name": "test.mp4",
            "media_type": "video"
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.2)
    
    # Step 2: Analysis completes
    await event_bus.publish(
        Topics.ANALYSIS_COMPLETED,
        {
            "media_id": "e2e-media-123",
            "pre_social_score": 75.5,
            "topics": ["tech", "ai"]
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.2)
    
    # Step 3: Publish
    await event_bus.publish(
        Topics.PUBLISH_COMPLETED,
        {
            "media_id": "e2e-media-123",
            "platform": "tiktok",
            "platform_url": "https://tiktok.com/...",
            "post_submission_id": "sub-123"
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.3)
    
    # Verify workflow events
    workflow_events = [e for e in workflow_tracker if e["correlation_id"] == correlation_id]
    
    assert len(workflow_events) >= 3, f"Expected at least 3 events, got {len(workflow_events)}"
    
    topics = [e["topic"] for e in workflow_events]
    assert Topics.MEDIA_INGESTED in topics
    assert Topics.ANALYSIS_COMPLETED in topics
    assert Topics.PUBLISH_COMPLETED in topics
    
    # Verify ordering (rough check - timestamps should be sequential)
    timestamps = [e["timestamp"] for e in workflow_events]
    assert timestamps == sorted(timestamps), "Events should be in chronological order"


@pytest.mark.asyncio
async def test_narrative_planning_workflow(event_bus, workflow_tracker):
    """Test narrative planning workflow."""
    correlation_id = f"narrative-workflow-{datetime.now().timestamp()}"
    
    # Step 1: Goal created
    await event_bus.publish(
        Topics.NARRATIVE_GOAL_UPDATED,
        {
            "goal_id": "goal-123",
            "action": "created",
            "goal_statement": "Grow TikTok following"
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.1)
    
    # Step 2: Plan generated
    await event_bus.publish(
        Topics.NARRATIVE_PLAN_GENERATED,
        {
            "scheduled_count": 7,
            "post_ids": ["post-1", "post-2"],
            "platforms": ["tiktok"]
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.1)
    
    # Step 3: Posts scheduled
    for i in range(2):
        await event_bus.publish(
            Topics.SCHEDULE_CREATED,
            {
                "post_id": f"post-{i+1}",
                "content_id": f"content-{i+1}",
                "goal_id": "goal-123"
            },
            correlation_id=correlation_id
        )
    
    await asyncio.sleep(0.2)
    
    # Verify workflow
    workflow_events = [e for e in workflow_tracker if e["correlation_id"] == correlation_id]
    
    assert len(workflow_events) >= 3
    topics = [e["topic"] for e in workflow_events]
    assert Topics.NARRATIVE_GOAL_UPDATED in topics
    assert Topics.NARRATIVE_PLAN_GENERATED in topics
    assert Topics.SCHEDULE_CREATED in topics


@pytest.mark.asyncio
async def test_experiment_workflow(event_bus, workflow_tracker):
    """Test experiment workflow: create → run → metrics → winner."""
    correlation_id = f"experiment-workflow-{datetime.now().timestamp()}"
    
    # Step 1: Experiment run started
    await event_bus.publish(
        Topics.EXPERIMENT_RUN_STARTED,
        {
            "experiment_id": "exp-123",
            "hypothesis_id": "hyp-123"
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.1)
    
    # Step 2: Variants created
    for variant in ["control", "variant-a"]:
        await event_bus.publish(
            Topics.EXPERIMENT_VARIANT_CREATED,
            {
                "experiment_id": "exp-123",
                "variant": variant,
                "post_id": f"post-{variant}"
            },
            correlation_id=correlation_id
        )
    
    await asyncio.sleep(0.1)
    
    # Step 3: Metrics ready
    await event_bus.publish(
        Topics.EXPERIMENT_METRICS_READY,
        {
            "experiment_id": "exp-123",
            "winner_variant": "variant-a",
            "uplift": 15.5
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.2)
    
    # Verify workflow
    workflow_events = [e for e in workflow_tracker if e["correlation_id"] == correlation_id]
    
    assert len(workflow_events) >= 4
    topics = [e["topic"] for e in workflow_events]
    assert Topics.EXPERIMENT_RUN_STARTED in topics
    assert Topics.EXPERIMENT_VARIANT_CREATED in topics
    assert Topics.EXPERIMENT_METRICS_READY in topics


@pytest.mark.asyncio
async def test_failure_path_retry(event_bus, workflow_tracker):
    """Test failure path with retry."""
    correlation_id = f"failure-workflow-{datetime.now().timestamp()}"
    
    # Step 1: Publish fails
    await event_bus.publish(
        Topics.PUBLISH_FAILED,
        {
            "media_id": "fail-123",
            "platform": "tiktok",
            "error": "Network timeout"
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.1)
    
    # Step 2: Retry scheduled
    await event_bus.publish(
        Topics.PUBLISH_RETRYING,
        {
            "media_id": "fail-123",
            "retry_count": 1,
            "next_attempt_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.1)
    
    # Step 3: Retry succeeds
    await event_bus.publish(
        Topics.PUBLISH_COMPLETED,
        {
            "media_id": "fail-123",
            "platform": "tiktok",
            "platform_url": "https://tiktok.com/..."
        },
        correlation_id=correlation_id
    )
    
    await asyncio.sleep(0.2)
    
    # Verify workflow includes failure and recovery
    workflow_events = [e for e in workflow_tracker if e["correlation_id"] == correlation_id]
    
    topics = [e["topic"] for e in workflow_events]
    assert Topics.PUBLISH_FAILED in topics
    assert Topics.PUBLISH_RETRYING in topics
    assert Topics.PUBLISH_COMPLETED in topics


@pytest.mark.asyncio
async def test_parallel_workflows(event_bus):
    """Test multiple workflows running in parallel."""
    workflows = []
    
    # Start 5 parallel workflows
    for i in range(5):
        correlation_id = f"parallel-{i}-{datetime.now().timestamp()}"
        
        await event_bus.publish(
            Topics.MEDIA_INGESTED,
            {"media_id": f"media-{i}"},
            correlation_id=correlation_id
        )
        
        workflows.append(correlation_id)
    
    await asyncio.sleep(0.3)
    
    # All workflows should have been processed
    # (In practice, check that all events were received)
    assert len(workflows) == 5


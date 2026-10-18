"""
Pipeline Tests
==============
Tests for pipeline orchestration.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from services.pipeline.models import PipelineRequest, PipelineStatus, PipelineStage
from services.pipeline.orchestrator import PipelineOrchestrator


class TestPipelineModels:
    """Test pipeline data models."""
    
    def test_pipeline_request_creation(self):
        """Test PipelineRequest model creation."""
        request = PipelineRequest(
            brief_id="test_brief_123"
        )
        assert request.brief_id == "test_brief_123"
        assert request.pipeline_id is not None
        assert request.correlation_id is not None
        assert PipelineStage.BRIEF in request.stages
        assert PipelineStage.SCRIPT in request.stages
        assert PipelineStage.TTS in request.stages
        assert PipelineStage.REMOTION in request.stages
        assert PipelineStage.PUBLISH in request.stages
    
    def test_pipeline_status_progress(self):
        """Test pipeline status progress calculation."""
        status = PipelineStatus(
            pipeline_id="test_123",
            status=PipelineStatus.RUNNING
        )
        
        # No stages = 0 progress
        assert status.get_progress() == 0.0
        
        # Add stages with progress
        from services.pipeline.models import StageStatus
        from datetime import datetime, timezone
        
        status.stages[PipelineStage.BRIEF] = StageStatus(
            stage=PipelineStage.BRIEF,
            status="completed",
            progress=1.0
        )
        status.stages[PipelineStage.SCRIPT] = StageStatus(
            stage=PipelineStage.SCRIPT,
            status="running",
            progress=0.5
        )
        
        # Average progress: (1.0 + 0.5) / 2 = 0.75
        assert status.get_progress() == 0.75


class TestPipelineOrchestrator:
    """Test pipeline orchestrator."""
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = AsyncMock()
        return bus
    
    @pytest.fixture
    def orchestrator(self, event_bus):
        """Create pipeline orchestrator."""
        return PipelineOrchestrator(event_bus)
    
    @pytest.mark.asyncio
    async def test_execute_pipeline(self, orchestrator, event_bus):
        """Test pipeline execution."""
        request = PipelineRequest(
            brief_id="test_brief_123",
            stages=[
                PipelineStage.BRIEF,
                PipelineStage.SCRIPT,
                PipelineStage.TTS,
                PipelineStage.REMOTION
            ]
        )
        
        # Mock event bus to track events
        event_calls = []
        async def track_publish(topic, payload, correlation_id=None, source=None):
            event_calls.append((topic, payload))
        
        event_bus.publish = track_publish
        
        # Execute pipeline
        status = await orchestrator.execute(request)
        
        # Check status
        assert status.pipeline_id == request.pipeline_id
        assert PipelineStage.BRIEF in status.stages
        assert PipelineStage.SCRIPT in status.stages
        assert PipelineStage.TTS in status.stages
        assert PipelineStage.REMOTION in status.stages
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, orchestrator, event_bus):
        """Test pipeline error handling."""
        request = PipelineRequest(
            brief_id="test_brief_123"
        )
        
        # Mock event bus to raise error
        async def failing_publish(topic, payload, correlation_id=None, source=None):
            raise Exception("Test error")
        
        event_bus.publish = failing_publish
        
        # Execute pipeline
        status = await orchestrator.execute(request)
        
        # Should handle error gracefully
        assert status.status == PipelineStatus.FAILED
        assert status.error is not None
    
    def test_get_pipeline_status(self, orchestrator):
        """Test getting pipeline status."""
        request = PipelineRequest(brief_id="test_123")
        
        # Execute pipeline (will create status)
        import asyncio
        status = asyncio.run(orchestrator.execute(request))
        
        # Get status
        retrieved = orchestrator.get_pipeline_status(status.pipeline_id)
        assert retrieved is not None
        assert retrieved.pipeline_id == status.pipeline_id


"""
Pipeline Orchestrator
=====================
Orchestrates the end-to-end media factory pipeline.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from services.event_bus import EventBus, Topics

from .models import PipelineRequest, PipelineStatus, PipelineStage, StageStatus

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the media factory pipeline.
    
    Pipeline stages:
    1. Brief → Generate content brief (if needed)
    2. Script → Generate script.json + shotlist.json
    3. TTS → Generate voice.wav + word_timestamps.json
    4. Music → Generate music.wav (optional)
    5. Visuals → Generate matting, b-roll, memes (optional)
    6. Remotion → Render final video
    7. Publish → Publish to platforms
    
    Usage:
        orchestrator = PipelineOrchestrator()
        status = await orchestrator.execute(request)
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize orchestrator.
        
        Args:
            event_bus: Event bus for publishing events
        """
        self.event_bus = event_bus or EventBus.get_instance()
        self._pipelines: Dict[str, PipelineStatus] = {}
    
    async def execute(self, request: PipelineRequest) -> PipelineStatus:
        """
        Execute the full pipeline.
        
        Args:
            request: Pipeline execution request
        
        Returns:
            PipelineStatus with execution results
        """
        # Create pipeline status
        status = PipelineStatus(
            pipeline_id=request.pipeline_id,
            status=PipelineStatus.PENDING,
            correlation_id=request.correlation_id,
            started_at=datetime.now(timezone.utc)
        )
        self._pipelines[request.pipeline_id] = status
        
        status.status = PipelineStatus.RUNNING
        
        try:
            # Stage 1: Brief (if needed)
            if PipelineStage.BRIEF in request.stages:
                await self._execute_brief_stage(request, status)
            
            # Stage 2: Script
            if PipelineStage.SCRIPT in request.stages:
                await self._execute_script_stage(request, status)
            
            # Stage 3: TTS
            if PipelineStage.TTS in request.stages:
                await self._execute_tts_stage(request, status)
            
            # Stage 4: Music (optional)
            if PipelineStage.MUSIC in request.stages and PipelineStage.MUSIC not in (request.skip_stages or []):
                await self._execute_music_stage(request, status)
            
            # Stage 5: Visuals (optional)
            if PipelineStage.VISUALS in request.stages and PipelineStage.VISUALS not in (request.skip_stages or []):
                await self._execute_visuals_stage(request, status)
            
            # Stage 6: Remotion
            if PipelineStage.REMOTION in request.stages:
                await self._execute_remotion_stage(request, status)
            
            # Stage 7: Publish
            if PipelineStage.PUBLISH in request.stages:
                await self._execute_publish_stage(request, status)
            
            status.status = PipelineStatus.COMPLETED
            status.completed_at = datetime.now(timezone.utc)
            
            # Emit completion event
            await self.event_bus.publish(
                Topics.PIPELINE_COMPLETED,  # TODO: Add this topic
                {
                    "pipeline_id": request.pipeline_id,
                    "status": "completed",
                    "correlation_id": request.correlation_id
                },
                request.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Pipeline {request.pipeline_id} failed: {e}", exc_info=True)
            status.status = PipelineStatus.FAILED
            status.error = str(e)
            status.completed_at = datetime.now(timezone.utc)
            
            await self.event_bus.publish(
                Topics.PIPELINE_FAILED,  # TODO: Add this topic
                {
                    "pipeline_id": request.pipeline_id,
                    "error": str(e),
                    "correlation_id": request.correlation_id
                },
                request.correlation_id
            )
        
        return status
    
    async def _execute_brief_stage(self, request: PipelineRequest, status: PipelineStatus) -> None:
        """Execute brief generation stage."""
        stage_status = StageStatus(
            stage=PipelineStage.BRIEF,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        status.stages[PipelineStage.BRIEF] = stage_status
        
        # If brief_id provided, use existing brief
        if request.brief_id:
            stage_status.status = "completed"
            stage_status.completed_at = datetime.now(timezone.utc)
            stage_status.progress = 1.0
            stage_status.output = {"brief_id": request.brief_id}
            return
        
        # Otherwise, generate brief from brief_data
        # TODO: Implement brief generation
        logger.warning("Brief generation from data not yet implemented")
        stage_status.status = "skipped"
        stage_status.progress = 1.0
    
    async def _execute_script_stage(self, request: PipelineRequest, status: PipelineStatus) -> None:
        """Execute script generation stage."""
        stage_status = StageStatus(
            stage=PipelineStage.SCRIPT,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        status.stages[PipelineStage.SCRIPT] = stage_status
        
        # Get brief_id from previous stage or request
        brief_id = request.brief_id
        if not brief_id and PipelineStage.BRIEF in status.stages:
            brief_stage = status.stages[PipelineStage.BRIEF]
            if brief_stage.output:
                brief_id = brief_stage.output.get("brief_id")
        
        if not brief_id:
            stage_status.status = "failed"
            stage_status.error = "No brief_id available"
            return
        
        # Generate script from brief
        # This would call the enhanced brief service to generate script.json
        # For now, emit an event that script generation service would handle
        await self.event_bus.publish(
            Topics.CONTENT_BRIEF_SCRIPT_GENERATED,
            {
                "brief_id": brief_id,
                "pipeline_id": request.pipeline_id,
                "correlation_id": request.correlation_id
            },
            request.correlation_id
        )
        
        # Wait for script generation (in production, would wait for event)
        # For now, mark as completed
        stage_status.status = "completed"
        stage_status.completed_at = datetime.now(timezone.utc)
        stage_status.progress = 1.0
        stage_status.output = {
            "brief_id": brief_id,
            "script_json": f"data/scripts/{brief_id}/script.json"
        }
    
    async def _execute_tts_stage(self, request: PipelineRequest, status: PipelineStatus) -> None:
        """Execute TTS generation stage."""
        stage_status = StageStatus(
            stage=PipelineStage.TTS,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        status.stages[PipelineStage.TTS] = stage_status
        
        # Get script from previous stage
        script_stage = status.stages.get(PipelineStage.SCRIPT)
        script_json_path = None
        if script_stage and script_stage.output:
            script_json_path = script_stage.output.get("script_json")
        
        if not script_json_path:
            stage_status.status = "failed"
            stage_status.error = "No script.json available"
            return
        
        # Request TTS generation
        # This would read script.json and extract text
        # For now, emit TTS request event
        await self.event_bus.publish(
            Topics.TTS_REQUESTED,
            {
                "text": "Sample text from script",  # TODO: Read from script.json
                "model": "indextts2",
                "voice_reference": "/path/to/voice.wav",  # TODO: Get from config
                "pipeline_id": request.pipeline_id,
                "correlation_id": request.correlation_id
            },
            request.correlation_id
        )
        
        # Wait for TTS completion (in production, would wait for tts.completed event)
        stage_status.status = "completed"
        stage_status.completed_at = datetime.now(timezone.utc)
        stage_status.progress = 1.0
        stage_status.output = {
            "audio_path": f"data/tts_outputs/pipeline_{request.pipeline_id}.wav",
            "word_timestamps": f"data/tts_outputs/pipeline_{request.pipeline_id}_timestamps.json"
        }
    
    async def _execute_music_stage(self, request: PipelineRequest, status: PipelineStatus) -> None:
        """Execute music generation stage."""
        stage_status = StageStatus(
            stage=PipelineStage.MUSIC,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        status.stages[PipelineStage.MUSIC] = stage_status
        
        # Get script from previous stage for context
        script_output = status.stages.get(PipelineStage.SCRIPT)
        
        # Request music generation/selection
        # Default to trending music from social platforms
        await self.event_bus.publish(
            Topics.MUSIC_REQUESTED,
            {
                "source": "social_platform",
                "search_criteria": {
                    "trending": True,
                    "platform": "tiktok",  # Default to TikTok trending
                    "duration_min": 30.0,
                    "duration_max": 60.0
                },
                "pipeline_id": request.pipeline_id,
                "correlation_id": request.correlation_id
            },
            request.correlation_id
        )
        
        # Wait for music completion (in production, would wait for music.completed event)
        stage_status.status = "completed"
        stage_status.completed_at = datetime.now(timezone.utc)
        stage_status.progress = 1.0
        stage_status.output = {
            "music_path": f"data/music/pipeline_{request.pipeline_id}.mp3"
        }
    
    async def _execute_visuals_stage(self, request: PipelineRequest, status: PipelineStatus) -> None:
        """Execute visuals generation stage."""
        stage_status = StageStatus(
            stage=PipelineStage.VISUALS,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        status.stages[PipelineStage.VISUALS] = stage_status
        
        # Get script from previous stage for context
        script_output = status.stages.get(PipelineStage.SCRIPT)
        
        # Request visuals (b-roll, memes, UGC)
        # Request b-roll
        await self.event_bus.publish(
            Topics.VISUALS_REQUESTED,
            {
                "visuals_type": "broll",
                "source": "local",  # Start with local, can use RapidAPI for trending
                "search_criteria": {
                    "trending": True,
                    "keywords": ["tech", "lifestyle"]  # Default keywords
                },
                "pipeline_id": request.pipeline_id,
                "correlation_id": request.correlation_id
            },
            request.correlation_id
        )
        
        # Request memes (optional)
        await self.event_bus.publish(
            Topics.VISUALS_REQUESTED,
            {
                "visuals_type": "meme",
                "source": "local",
                "search_criteria": {
                    "trending": True
                },
                "pipeline_id": request.pipeline_id,
                "correlation_id": request.correlation_id
            },
            request.correlation_id
        )
        
        # Wait for visuals completion (in production, would wait for visuals.completed events)
        stage_status.status = "completed"
        stage_status.completed_at = datetime.now(timezone.utc)
        stage_status.progress = 1.0
        stage_status.output = {
            "broll_path": f"data/visuals/broll/pipeline_{request.pipeline_id}.mp4",
            "memes_path": f"data/visuals/memes/pipeline_{request.pipeline_id}.png"
        }
    
    async def _execute_remotion_stage(self, request: PipelineRequest, status: PipelineStatus) -> None:
        """Execute Remotion rendering stage."""
        stage_status = StageStatus(
            stage=PipelineStage.REMOTION,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        status.stages[PipelineStage.REMOTION] = stage_status
        
        # Get TTS output from previous stage
        tts_stage = status.stages.get(PipelineStage.TTS)
        audio_path = None
        if tts_stage and tts_stage.output:
            audio_path = tts_stage.output.get("audio_path")
        
        if not audio_path:
            stage_status.status = "failed"
            stage_status.error = "No TTS audio available"
            return
        
        # Request Remotion render
        await self.event_bus.publish(
            Topics.REMOTION_REQUESTED,
            {
                "composition": "MainComposition",
                "layers": [
                    {
                        "id": "voice_layer",
                        "type": "audio",
                        "source": audio_path,
                        "source_type": "local",
                        "start": 0,
                        "volume": 1.0
                    }
                ],
                "output": {
                    "format": "mp4",
                    "resolution": "1080x1920",
                    "fps": 30
                },
                "pipeline_id": request.pipeline_id,
                "correlation_id": request.correlation_id
            },
            request.correlation_id
        )
        
        # Wait for Remotion completion (in production, would wait for remotion.completed event)
        stage_status.status = "completed"
        stage_status.completed_at = datetime.now(timezone.utc)
        stage_status.progress = 1.0
        stage_status.output = {
            "video_path": f"data/remotion_outputs/pipeline_{request.pipeline_id}.mp4"
        }
    
    async def _execute_publish_stage(self, request: PipelineRequest, status: PipelineStatus) -> None:
        """Execute publishing stage."""
        stage_status = StageStatus(
            stage=PipelineStage.PUBLISH,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        status.stages[PipelineStage.PUBLISH] = stage_status
        
        # Get Remotion output from previous stage
        remotion_stage = status.stages.get(PipelineStage.REMOTION)
        video_path = None
        if remotion_stage and remotion_stage.output:
            video_path = remotion_stage.output.get("video_path")
        
        if not video_path:
            stage_status.status = "failed"
            stage_status.error = "No video available"
            return
        
        # Request publishing
        # This would use existing MediaPoster publishing service
        await self.event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "media_path": video_path,
                "platforms": ["youtube_shorts", "tiktok", "instagram_reels"],
                "pipeline_id": request.pipeline_id,
                "correlation_id": request.correlation_id
            },
            request.correlation_id
        )
        
        # Wait for publish completion (in production, would wait for publish.completed event)
        stage_status.status = "completed"
        stage_status.completed_at = datetime.now(timezone.utc)
        stage_status.progress = 1.0
        stage_status.output = {
            "published_urls": []  # Would be populated from publish.completed events
        }
    
    def get_pipeline_status(self, pipeline_id: str) -> Optional[PipelineStatus]:
        """Get status of a pipeline."""
        return self._pipelines.get(pipeline_id)


"""
Analysis Worker
================
Event-driven worker for video analysis pipeline.

Subscribes to:
    - media.ingested (auto-analyze new media)
    - media.analysis.requested (manual analysis request)

Emits:
    - media.analysis.started
    - media.analysis.progress
    - media.analysis.step.completed
    - media.analysis.completed
    - media.analysis.failed
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from services.event_bus import EventBus, Event, Topics
from services.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class AnalysisWorker(BaseWorker):
    """
    Worker for processing video analysis requests.
    
    Pipeline steps:
        1. Transcript extraction
        2. Visual analysis
        3. AI analysis (captions, hashtags, platform content)
    
    Usage:
        worker = AnalysisWorker()
        await worker.start()
        
        # Worker will automatically process events from:
        # - media.ingested
        # - media.analysis.requested
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None, worker_id: Optional[str] = None):
        super().__init__(event_bus, worker_id)
        self._video_analyzer = None  # Lazy load
    
    def get_subscriptions(self) -> List[str]:
        """Subscribe to analysis-related events."""
        return [
            Topics.ANALYSIS_REQUESTED,
            # Topics.MEDIA_INGESTED,  # Uncomment to auto-analyze on ingest
        ]
    
    async def handle_event(self, event: Event) -> None:
        """Process analysis events."""
        media_id = event.payload.get("media_id")
        
        if not media_id:
            logger.warning(f"[{self.worker_id}] No media_id in event payload")
            return
        
        # Run the analysis pipeline
        await self._run_analysis_pipeline(media_id, event.correlation_id)
    
    async def _run_analysis_pipeline(self, media_id: str, correlation_id: str) -> Dict[str, Any]:
        """
        Run the full analysis pipeline with progress events.
        
        Steps:
            1. Transcript (0-33%)
            2. Visual analysis (33-66%)
            3. AI analysis (66-100%)
        """
        try:
            # Emit started event
            await self.emit(
                Topics.ANALYSIS_STARTED,
                {"media_id": media_id, "step": "initializing"},
                correlation_id
            )
            
            # Step 1: Transcript
            await self.emit_progress("media.analysis", 5, "transcript", correlation_id, media_id=media_id)
            transcript = await self._run_transcript(media_id)
            await self.emit(
                Topics.TRANSCRIPT_COMPLETED,
                {"media_id": media_id, "transcript_length": len(transcript) if transcript else 0},
                correlation_id
            )
            await self.emit_progress("media.analysis", 33, "transcript_complete", correlation_id, media_id=media_id)
            
            # Step 2: Visual Analysis
            await self.emit_progress("media.analysis", 40, "visual", correlation_id, media_id=media_id)
            visual_data = await self._run_visual_analysis(media_id)
            await self.emit(
                Topics.VISUAL_COMPLETED,
                {"media_id": media_id, "frames_analyzed": visual_data.get("frame_count", 0) if visual_data else 0},
                correlation_id
            )
            await self.emit_progress("media.analysis", 66, "visual_complete", correlation_id, media_id=media_id)
            
            # Step 3: AI Analysis
            await self.emit_progress("media.analysis", 75, "ai_analysis", correlation_id, media_id=media_id)
            analysis_result = await self._run_ai_analysis(media_id, transcript, visual_data)
            await self.emit(
                Topics.AI_ANALYSIS_COMPLETED,
                {"media_id": media_id, "platforms": list(analysis_result.keys()) if analysis_result else []},
                correlation_id
            )
            await self.emit_progress("media.analysis", 100, "complete", correlation_id, media_id=media_id)
            
            # Emit completion
            await self.emit(
                Topics.ANALYSIS_COMPLETED,
                {
                    "media_id": media_id,
                    "has_transcript": bool(transcript),
                    "has_visual": bool(visual_data),
                    "platforms_analyzed": list(analysis_result.keys()) if analysis_result else [],
                    "completed_at": datetime.now(timezone.utc).isoformat()
                },
                correlation_id
            )
            
            return {
                "success": True,
                "media_id": media_id,
                "transcript": transcript,
                "visual": visual_data,
                "analysis": analysis_result
            }
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Analysis failed for {media_id}: {e}")
            
            await self.emit(
                Topics.ANALYSIS_FAILED,
                {
                    "media_id": media_id,
                    "error": str(e),
                    "failed_at": datetime.now(timezone.utc).isoformat()
                },
                correlation_id
            )
            raise
    
    async def _run_transcript(self, media_id: str) -> Optional[str]:
        """Extract transcript from video."""
        try:
            analyzer = self._get_video_analyzer()
            if analyzer:
                # Get video path from database
                video_path = await self._get_video_path(media_id)
                if video_path:
                    result = await asyncio.to_thread(
                        analyzer.extract_transcript, video_path
                    )
                    return result
            return None
        except Exception as e:
            logger.warning(f"Transcript extraction failed: {e}")
            return None
    
    async def _run_visual_analysis(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Run visual analysis on video frames."""
        try:
            analyzer = self._get_video_analyzer()
            if analyzer:
                video_path = await self._get_video_path(media_id)
                if video_path:
                    result = await asyncio.to_thread(
                        analyzer.analyze_frames, video_path
                    )
                    return result
            return None
        except Exception as e:
            logger.warning(f"Visual analysis failed: {e}")
            return None
    
    async def _run_ai_analysis(
        self,
        media_id: str,
        transcript: Optional[str],
        visual_data: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Run AI analysis to generate captions and hashtags."""
        try:
            analyzer = self._get_video_analyzer()
            if analyzer:
                result = await asyncio.to_thread(
                    analyzer.generate_platform_content,
                    media_id,
                    transcript,
                    visual_data
                )
                return result
            return None
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
            return None
    
    def _get_video_analyzer(self):
        """Lazy load the video analyzer."""
        if self._video_analyzer is None:
            try:
                from services.video_analyzer import VideoAnalyzer
                self._video_analyzer = VideoAnalyzer()
            except Exception as e:
                logger.warning(f"Could not load VideoAnalyzer: {e}")
        return self._video_analyzer
    
    async def _get_video_path(self, media_id: str) -> Optional[str]:
        """Get video file path from database."""
        try:
            from sqlalchemy import create_engine, text
            import os
            
            DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
            engine = create_engine(DATABASE_URL)
            
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT source_uri FROM videos WHERE id = :id"),
                    {"id": media_id}
                ).fetchone()
                
                if result and result[0]:
                    return result[0]
            return None
        except Exception as e:
            logger.warning(f"Could not get video path: {e}")
            return None


# Convenience function to create and start worker
async def start_analysis_worker(event_bus: Optional[EventBus] = None) -> AnalysisWorker:
    """Create and start an analysis worker."""
    worker = AnalysisWorker(event_bus)
    await worker.start()
    return worker

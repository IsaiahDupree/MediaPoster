"""
Ingestion Analysis Integrator (BM-003)
=======================================
Automatically triggers AI analysis after content ingestion.

This service:
1. Listens to content ingestion events
2. Triggers OpenAI Vision analysis for ingested media
3. Generates titles, descriptions, hashtags
4. Calculates quality scores
5. Stores analysis results in database

Integrates:
- ContentSourcingEngine (BM-001) - Content discovery and ingestion
- VideoAnalysisService - OpenAI Vision analysis
- Event Bus - Event-driven coordination
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

from services.event_bus import EventBus, Topics
from services.video_analysis import VideoAnalysisService
from database.models import Video, AnalyzedVideo


class IngestionAnalysisIntegrator:
    """
    Integrates content ingestion with AI analysis

    This service automatically triggers AI analysis when new content
    is ingested via the ContentSourcingEngine. It ensures all ingested
    content receives comprehensive AI analysis for titles, descriptions,
    hashtags, and quality scoring.

    Usage:
        integrator = IngestionAnalysisIntegrator(db_session)
        await integrator.start()

        # Content ingestion events will automatically trigger analysis
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize Ingestion Analysis Integrator

        Args:
            db: Database session
        """
        self.db = db
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("ingestion-analysis-integrator")

        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client: Optional["OpenAI"] = None

        if not OPENAI_AVAILABLE:
            logger.warning("⚠️  OpenAI package not installed - AI analysis will be disabled")
        elif not self.openai_api_key:
            logger.warning("⚠️  OPENAI_API_KEY not set - AI analysis will be disabled")
        else:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize OpenAI client: {e}")

        # Video analysis service
        self.video_analyzer: Optional[VideoAnalysisService] = None

        # Processing state
        self._is_running = False
        self._event_subscription = None
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

        logger.info("🔗 Ingestion Analysis Integrator initialized")

    async def start(self) -> None:
        """Start listening for ingestion events"""
        if self._is_running:
            logger.warning("Integrator already running")
            return

        self._is_running = True

        # Subscribe to content ingestion events
        self._event_subscription = await self.event_bus.subscribe(
            Topics.CONTENT_INGESTED,
            self._handle_ingestion_event
        )

        # Start background worker
        self._worker_task = asyncio.create_task(self._process_queue())

        logger.success("✓ Ingestion Analysis Integrator started")

    async def stop(self) -> None:
        """Stop listening for ingestion events"""
        self._is_running = False

        # Unsubscribe from events
        if self._event_subscription:
            await self.event_bus.unsubscribe(
                Topics.CONTENT_INGESTED,
                self._event_subscription
            )

        # Stop worker
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Ingestion Analysis Integrator stopped")

    async def _handle_ingestion_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle content ingestion event

        Args:
            event_data: Event data containing video_id and file details
        """
        try:
            video_id = event_data.get("video_id")
            file_path = event_data.get("file_path")
            media_type = event_data.get("media_type")

            if not video_id or not file_path:
                logger.warning("Ingestion event missing required fields")
                return

            logger.info(f"📥 Content ingested: {video_id} - queuing for analysis")

            # Add to processing queue
            await self._processing_queue.put({
                "video_id": video_id,
                "file_path": file_path,
                "media_type": media_type,
                "ingested_at": datetime.now(timezone.utc)
            })

        except Exception as e:
            logger.error(f"Error handling ingestion event: {e}")

    async def _process_queue(self) -> None:
        """Background worker to process analysis queue"""
        logger.info("🔄 Analysis worker started")

        while self._is_running:
            try:
                # Get next item from queue (with timeout)
                try:
                    item = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process the item
                await self._analyze_content(item)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analysis worker: {e}")
                await asyncio.sleep(5)  # Brief pause on error

        logger.info("🛑 Analysis worker stopped")

    async def _analyze_content(self, item: Dict[str, Any]) -> None:
        """
        Analyze ingested content using AI

        Args:
            item: Content item to analyze (video_id, file_path, media_type)
        """
        video_id = item["video_id"]
        file_path = item["file_path"]
        media_type = item["media_type"]

        try:
            logger.info(f"🤖 Analyzing content: {video_id}")

            # Publish analysis start event
            await self.event_bus.publish(
                Topics.CONTENT_ANALYSIS_STARTED,
                {
                    "video_id": video_id,
                    "file_path": file_path,
                    "media_type": media_type,
                    "started_at": datetime.now(timezone.utc).isoformat()
                }
            )

            # Perform AI analysis based on media type
            if media_type == "video":
                analysis_result = await self._analyze_video(video_id, file_path)
            elif media_type == "image":
                analysis_result = await self._analyze_image(video_id, file_path)
            else:
                logger.warning(f"Unsupported media type: {media_type}")
                return

            # Publish analysis complete event
            await self.event_bus.publish(
                Topics.CONTENT_ANALYSIS_COMPLETED,
                {
                    "video_id": video_id,
                    "file_path": file_path,
                    "media_type": media_type,
                    "analysis": analysis_result,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
            )

            logger.success(f"✓ Analysis completed: {video_id}")

        except Exception as e:
            logger.error(f"Error analyzing content {video_id}: {e}")

            # Publish analysis failed event
            await self.event_bus.publish(
                Topics.CONTENT_ANALYSIS_FAILED,
                {
                    "video_id": video_id,
                    "file_path": file_path,
                    "error": str(e),
                    "failed_at": datetime.now(timezone.utc).isoformat()
                }
            )

    async def _analyze_video(self, video_id: str, file_path: str) -> Dict[str, Any]:
        """
        Analyze video using OpenAI Vision

        Args:
            video_id: Video UUID
            file_path: Path to video file

        Returns:
            Analysis results
        """
        if not self.openai_api_key:
            logger.warning("OpenAI API key not configured - skipping analysis")
            return {"error": "OpenAI API key not configured"}

        # Initialize video analyzer if needed
        if not self.video_analyzer:
            from database.connection import get_sync_db
            with get_sync_db() as db:
                self.video_analyzer = VideoAnalysisService(
                    db=db,
                    openai_api_key=self.openai_api_key
                )

        # Run video analysis
        # Convert video_id string to UUID
        from uuid import UUID
        video_uuid = UUID(video_id) if isinstance(video_id, str) else video_id

        result = self.video_analyzer.analyze_video_frames(
            video_path=file_path,
            video_id=video_uuid,
            sampling_interval_s=2.0,  # Sample every 2 seconds
            analysis_type="comprehensive",
            store_in_db=True
        )

        # Generate title, description, and hashtags using GPT-4
        content_metadata = await self._generate_content_metadata(
            video_id=video_id,
            file_path=file_path,
            analysis_result=result
        )

        # Calculate quality score
        quality_score = self._calculate_quality_score(result)

        return {
            "frames_analyzed": result.get("frames_analyzed", 0),
            "pattern_interrupts": result.get("pattern_interrupts", 0),
            "title": content_metadata.get("title"),
            "description": content_metadata.get("description"),
            "hashtags": content_metadata.get("hashtags", []),
            "quality_score": quality_score,
            "analysis_complete": True
        }

    async def _analyze_image(self, video_id: str, file_path: str) -> Dict[str, Any]:
        """
        Analyze image using OpenAI Vision

        Args:
            video_id: Video UUID (also used for images)
            file_path: Path to image file

        Returns:
            Analysis results
        """
        if not self.openai_api_key:
            logger.warning("OpenAI API key not configured - skipping analysis")
            return {"error": "OpenAI API key not configured"}

        # Use VisionAnalyzer for single image
        from services.vision_analyzer import VisionAnalyzer

        analyzer = VisionAnalyzer(api_key=self.openai_api_key)
        analysis = analyzer.analyze_frame(
            frame_path=file_path,
            analysis_type="comprehensive"
        )

        # Generate title, description, and hashtags
        content_metadata = await self._generate_content_metadata(
            video_id=video_id,
            file_path=file_path,
            analysis_result={"single_frame": analysis}
        )

        # Calculate quality score for image
        quality_score = 0.7  # Base score for images
        if analysis.get("description"):
            quality_score += 0.1
        if analysis.get("objects"):
            quality_score += 0.1
        if analysis.get("emotions"):
            quality_score += 0.1

        return {
            "image_analysis": analysis,
            "title": content_metadata.get("title"),
            "description": content_metadata.get("description"),
            "hashtags": content_metadata.get("hashtags", []),
            "quality_score": min(quality_score, 1.0),
            "analysis_complete": True
        }

    async def _generate_content_metadata(
        self,
        video_id: str,
        file_path: str,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate title, description, and hashtags using GPT-4

        Args:
            video_id: Content UUID
            file_path: Path to content file
            analysis_result: Vision analysis results

        Returns:
            Metadata dict with title, description, hashtags
        """
        try:
            # Check if OpenAI client is available
            if not self.openai_client:
                logger.warning("OpenAI client not available - using fallback metadata")
                return {
                    "title": f"Content {video_id[:8]}",
                    "description": "AI-generated content",
                    "hashtags": ["content", "ai", "generated"]
                }

            # Prepare prompt based on analysis
            prompt = self._build_metadata_prompt(file_path, analysis_result)

            # Call GPT-4 using OpenAI client
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content marketer. Generate engaging titles, descriptions, and hashtags for social media content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )

            # Parse response
            content = response.choices[0].message.content.strip() if response.choices else ""

            # Extract title, description, hashtags
            metadata = self._parse_metadata_response(content)

            return metadata

        except Exception as e:
            logger.error(f"Error generating content metadata: {e}")
            return {
                "title": f"Content {video_id[:8]}",
                "description": "AI-generated content",
                "hashtags": ["content", "ai", "generated"]
            }

    def _build_metadata_prompt(
        self,
        file_path: str,
        analysis_result: Dict[str, Any]
    ) -> str:
        """Build prompt for metadata generation"""
        file_name = os.path.basename(file_path)

        prompt = f"Content file: {file_name}\n\n"
        prompt += "Analysis results:\n"

        if "frames_analyzed" in analysis_result:
            prompt += f"- Frames analyzed: {analysis_result['frames_analyzed']}\n"
        if "pattern_interrupts" in analysis_result:
            prompt += f"- Pattern interrupts: {analysis_result['pattern_interrupts']}\n"

        prompt += "\nGenerate:\n"
        prompt += "1. A compelling title (max 100 characters)\n"
        prompt += "2. An engaging description (max 300 characters)\n"
        prompt += "3. 5-10 relevant hashtags\n\n"
        prompt += "Format:\n"
        prompt += "TITLE: [title]\n"
        prompt += "DESCRIPTION: [description]\n"
        prompt += "HASHTAGS: [hashtag1, hashtag2, ...]"

        return prompt

    def _parse_metadata_response(self, content: str) -> Dict[str, Any]:
        """Parse GPT-4 response into structured metadata"""
        lines = content.split("\n")

        title = ""
        description = ""
        hashtags = []

        for line in lines:
            line = line.strip()
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("DESCRIPTION:"):
                description = line.replace("DESCRIPTION:", "").strip()
            elif line.startswith("HASHTAGS:"):
                hashtag_str = line.replace("HASHTAGS:", "").strip()
                # Parse hashtags (comma-separated or space-separated)
                hashtags = [
                    tag.strip().lstrip("#")
                    for tag in hashtag_str.replace(",", " ").split()
                    if tag.strip()
                ]

        return {
            "title": title or "Untitled Content",
            "description": description or "No description",
            "hashtags": hashtags[:10]  # Limit to 10 hashtags
        }

    def _calculate_quality_score(self, analysis_result: Dict[str, Any]) -> float:
        """
        Calculate quality score based on analysis results

        Args:
            analysis_result: Analysis results

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.5  # Base score

        # Add points for frame analysis
        frames_analyzed = analysis_result.get("frames_analyzed", 0)
        if frames_analyzed > 0:
            score += 0.1
        if frames_analyzed > 10:
            score += 0.1
        if frames_analyzed > 50:
            score += 0.1

        # Add points for pattern interrupts (indicates engaging content)
        pattern_interrupts = analysis_result.get("pattern_interrupts", 0)
        if pattern_interrupts > 0:
            score += 0.1
        if pattern_interrupts > 3:
            score += 0.1

        # Ensure score is between 0.0 and 1.0
        return min(max(score, 0.0), 1.0)


# Singleton instance
_integrator_instance: Optional[IngestionAnalysisIntegrator] = None


def get_ingestion_analysis_integrator(db: AsyncSession) -> IngestionAnalysisIntegrator:
    """
    Get singleton instance of Ingestion Analysis Integrator

    Args:
        db: Database session

    Returns:
        IngestionAnalysisIntegrator instance
    """
    global _integrator_instance
    if _integrator_instance is None:
        _integrator_instance = IngestionAnalysisIntegrator(db)
    return _integrator_instance

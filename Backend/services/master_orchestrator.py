"""
Master Orchestrator Service (ARCH-001) - Database-Persisted Version
====================================================================
Coordinates all subsystems into unified pipelines with persistent state tracking.

Features:
- EventBus coordination of all subsystems
- Database persistence for pipeline state and steps
- Real-time progress tracking
- Error handling and retry logic
- Performance metrics and analytics

Workflow:
    Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                          ↓
    Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from uuid import uuid4
import os
from enum import Enum

from services.event_bus import EventBus, Event, Topics
from services.content_analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)

# Pipeline step timeout defaults (in seconds)
STEP_TIMEOUTS = {
    "sora_generation": 900,   # 15 minutes for video generation
    "video_stitching": 120,   # 2 minutes for stitching
    "content_analysis": 60,   # 1 minute for AI analysis
    "publishing": 300,        # 5 minutes for multi-platform publish
    "twitter_campaign": 60,   # 1 minute for scheduling tweets
}

# Maximum retry attempts per step
MAX_STEP_RETRIES = 2


class PipelineStatus(Enum):
    """Enum for pipeline status values."""
    INITIALIZING = "initializing"
    GENERATING_VIDEO = "generating_video"
    ANALYZING = "analyzing"
    PUBLISHING = "publishing"
    SCHEDULING_TWEETS = "scheduling_tweets"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineConfig:
    """Configuration for a pipeline execution."""

    def __init__(
        self,
        theme: str,
        num_parts: int = 3,
        character: Optional[str] = None,
        publish_platforms: Optional[List[str]] = None,
        schedule_tweets: bool = True,
        tweets_per_day: int = 12,
        offer_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        step_timeouts: Optional[Dict[str, int]] = None,
        max_retries: int = MAX_STEP_RETRIES,
        on_step_complete: Optional[Callable] = None,
    ):
        self.theme = theme
        self.num_parts = num_parts
        self.character = character
        self.publish_platforms = publish_platforms or ["tiktok", "instagram", "youtube"]
        self.schedule_tweets = schedule_tweets
        self.tweets_per_day = tweets_per_day
        self.offer_url = offer_url
        self.metadata = metadata or {}
        self.step_timeouts = {**STEP_TIMEOUTS, **(step_timeouts or {})}
        self.max_retries = max_retries
        self.on_step_complete = on_step_complete


class MasterOrchestrator:
    """
    Master Orchestrator Service (ARCH-001) - Database-Persisted Version

    Coordinates all subsystems via EventBus with persistent state tracking.
    Stores pipeline state in database for monitoring, debugging, and analytics.
    """

    _instance: Optional['MasterOrchestrator'] = None

    def __init__(self, event_bus: Optional[EventBus] = None, use_db: bool = True):
        self.event_bus = event_bus or EventBus.get_instance()
        self.content_analyzer = ContentAnalyzer()
        self.use_db = use_db
        self._running = False

        # Initialize subsystem services (ARCH-001)
        # Initialize eagerly to support test mocking
        try:
            from automation.sora.pipeline import SoraPipeline
            self.sora_pipeline = SoraPipeline()
        except Exception as e:
            logger.warning(f"⚠️ Sora Pipeline initialization failed: {e}")
            self.sora_pipeline = None

        try:
            from services.blotato_service import BlotatoService
            self.blotato_service = BlotatoService()
        except Exception as e:
            logger.warning(f"⚠️ Blotato Service initialization failed: {e}")
            self.blotato_service = None

        try:
            from services.twitter_campaign_service import TwitterCampaignService
            self.twitter_service = TwitterCampaignService()
        except Exception as e:
            logger.warning(f"⚠️ Twitter Campaign Service initialization failed: {e}")
            self.twitter_service = None

        try:
            from services.analytics_feedback import get_analytics_feedback
            self.analytics_feedback = get_analytics_feedback()
        except Exception as e:
            logger.warning(f"⚠️ Analytics Feedback initialization failed: {e}")
            self.analytics_feedback = None

        # In-memory cache for fast access
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}
        self.completed_pipelines: Dict[str, Dict[str, Any]] = {}

        # Timeout monitoring tasks
        self._timeout_tasks: Dict[str, asyncio.Task] = {}

        # Database connection
        self._db_engine = None
        if use_db:
            self._init_db()

        self._setup_subscriptions()
        logger.info(f"🎯 Master Orchestrator initialized (db_mode={use_db})")

    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None, use_db: bool = True) -> 'MasterOrchestrator':
        if cls._instance is None:
            cls._instance = cls(event_bus, use_db)
        return cls._instance

    def _init_db(self) -> None:
        """Initialize database connection."""
        try:
            from sqlalchemy import create_engine
            DATABASE_URL = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:54322/postgres"
            )
            self._db_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            logger.info("✅ Database connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Database initialization failed: {e}, falling back to in-memory mode")
            self.use_db = False
            self._db_engine = None

    def _setup_subscriptions(self) -> None:
        self.event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, self._handle_sora_batch_completed)
        self.event_bus.subscribe(Topics.SORA_BATCH_FAILED, self._handle_sora_batch_failed)
        self.event_bus.subscribe("blotato.publish.completed", self._handle_publish_completed)
        self.event_bus.subscribe("blotato.publish.failed", self._handle_publish_failed)
        self.event_bus.subscribe("twitter.campaign.scheduled", self._handle_twitter_scheduled)
        logger.info("📫 Orchestrator subscribed to subsystem events")

    async def start(self) -> None:
        """
        Start the orchestrator and all subsystems.

        Services are already initialized in __init__, this method starts
        async services that need event loop.
        """
        if self._running:
            logger.warning("Orchestrator already running")
            return

        logger.info("🚀 Starting Master Orchestrator...")

        # Start analytics feedback service if available
        if self.analytics_feedback and hasattr(self.analytics_feedback, 'start'):
            try:
                await self.analytics_feedback.start()
                logger.info("✅ Analytics Feedback started")
            except Exception as e:
                logger.warning(f"⚠️ Analytics Feedback start failed: {e}")

        self._running = True
        logger.info("✅ Master Orchestrator started successfully")

    async def stop(self) -> None:
        """Stop the orchestrator and cleanup resources."""
        if not self._running:
            return

        logger.info("🛑 Stopping Master Orchestrator...")

        # Stop analytics feedback if running
        if self.analytics_feedback and hasattr(self.analytics_feedback, 'stop'):
            try:
                await self.analytics_feedback.stop()
            except Exception as e:
                logger.error(f"Error stopping analytics feedback: {e}")

        self._running = False
        logger.info("✅ Master Orchestrator stopped")

    async def run_full_pipeline(
        self,
        theme: str,
        num_parts: int = 3,
        character: Optional[str] = None,
        publish_platforms: Optional[List[str]] = None,
        schedule_tweets: bool = True,
        tweets_per_day: int = 12,
        offer_url: Optional[str] = None
    ) -> str:
        """
        Convenience method to start a pipeline with individual parameters.

        This is a wrapper around start_pipeline() for easier API usage.
        """
        config = PipelineConfig(
            theme=theme,
            num_parts=num_parts,
            character=character,
            publish_platforms=publish_platforms,
            schedule_tweets=schedule_tweets,
            tweets_per_day=tweets_per_day,
            offer_url=offer_url
        )
        return await self.start_pipeline(config)

    async def start_pipeline(self, config: PipelineConfig) -> str:
        """
        Start a new pipeline execution.

        Creates pipeline record, initializes steps, and triggers Sora batch generation.
        """
        pipeline_id = f"pipeline-{uuid4().hex[:8]}"
        correlation_id = str(uuid4())

        logger.info(f"🚀 Starting pipeline {pipeline_id}: {config.theme}")

        # Store pipeline in memory
        pipeline = {
            "pipeline_id": pipeline_id,
            "config": config,
            "correlation_id": correlation_id,
            "theme": config.theme,
            "status": "initializing",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "current_step": "sora_generation",
            "outputs": {}
        }
        self.active_pipelines[pipeline_id] = pipeline

        # Save to database (ARCH-001)
        await self._db_save_pipeline(pipeline_id, pipeline)

        # Initialize pipeline steps (ARCH-001)
        steps = [
            ("sora_generation", 1),
            ("video_stitching", 2),
            ("content_analysis", 3),
            ("publishing", 4),
        ]
        if config.schedule_tweets:
            steps.append(("twitter_campaign", 5))

        for step_name, step_order in steps:
            await self._db_add_pipeline_step(pipeline_id, step_name, step_order)

        # Emit pipeline started event
        await self.event_bus.publish(
            Topics.ORCHESTRATOR_PIPELINE_STARTED,
            {"pipeline_id": pipeline_id, "theme": config.theme, "num_parts": config.num_parts},
            correlation_id=correlation_id,
            source="MasterOrchestrator"
        )

        # Update step: sora_generation -> running
        await self._db_update_pipeline_step(pipeline_id, "sora_generation", "running")

        pipeline["status"] = "generating_video"
        await self._db_update_pipeline_status(pipeline_id, "generating_video")

        # Start timeout monitor for sora_generation step
        self._start_step_timeout(pipeline_id, "sora_generation")

        # Start Sora video generation asynchronously.
        # We use create_task so start_pipeline returns immediately with the
        # pipeline still in active_pipelines.  The SoraWorker will pick up
        # the event and drive the pipeline forward through its event handlers.
        asyncio.create_task(
            self.event_bus.publish(
                Topics.SORA_BATCH_REQUESTED,
                {
                    "pipeline_id": pipeline_id,
                    "theme": config.theme,
                    "num_parts": config.num_parts,
                    "character": config.character,
                    "stitch": True,
                    "remove_watermark": True
                },
                correlation_id=correlation_id,
                source="MasterOrchestrator"
            )
        )

        return pipeline_id

    async def cancel_pipeline(self, pipeline_id: str) -> bool:
        """
        Cancel a running pipeline.

        Moves the pipeline to 'cancelled' state and removes from active.

        Args:
            pipeline_id: ID of the pipeline to cancel.

        Returns:
            True if cancelled, False if not found or already finished.
        """
        if pipeline_id not in self.active_pipelines:
            return False

        pipeline = self.active_pipelines[pipeline_id]
        pipeline["status"] = "cancelled"
        pipeline["cancelled_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"[{pipeline_id}] Pipeline cancelled by user")

        # Cancel any active timeout monitors
        for key in list(self._timeout_tasks.keys()):
            if key.startswith(pipeline_id):
                self._cancel_step_timeout(pipeline_id, key.split(":")[1])

        await self._db_update_pipeline_status(pipeline_id, "cancelled")

        await self.event_bus.publish(
            Topics.ORCHESTRATOR_PIPELINE_FAILED,
            {"pipeline_id": pipeline_id, "reason": "cancelled"},
            correlation_id=pipeline.get("correlation_id"),
            source="MasterOrchestrator"
        )

        self.completed_pipelines[pipeline_id] = pipeline
        del self.active_pipelines[pipeline_id]
        return True

    async def _handle_sora_batch_completed(self, event: Event) -> None:
        payload = event.payload
        pipeline_id = payload.get("pipeline_id")

        if not pipeline_id or pipeline_id not in self.active_pipelines:
            return

        # Cancel sora_generation timeout since the step completed
        self._cancel_step_timeout(pipeline_id, "sora_generation")

        # If the batch status is "failed", treat it as a pipeline failure
        batch_status = payload.get("status")
        if batch_status == "failed":
            error = payload.get("error", "Sora batch generation failed")
            await self._fail_pipeline(pipeline_id, error)
            await self._db_update_pipeline_step(pipeline_id, "sora_generation", "failed", error=error)
            return

        pipeline = self.active_pipelines[pipeline_id]
        video_path = payload.get("stitched_video") or payload.get("video_path")
        pipeline["outputs"]["sora"] = {
            "stitched_video": video_path,
            "analysis": payload.get("analysis")
        }

        # Update step: sora_generation -> completed (ARCH-001)
        await self._db_update_pipeline_step(
            pipeline_id,
            "sora_generation",
            "completed",
            output={
                "stitched_video": video_path,
                "successful_parts": payload.get("successful_parts", 0),
                "failed_parts": payload.get("failed_parts", 0)
            }
        )

        # Update step: video_stitching -> completed (ARCH-001)
        # Stitching is performed as part of the Sora batch pipeline
        if video_path:
            await self._db_update_pipeline_step(
                pipeline_id,
                "video_stitching",
                "completed",
                output={"stitched_video": video_path}
            )

        # Update step: content_analysis -> completed (analysis done in Sora pipeline)
        await self._db_update_pipeline_step(
            pipeline_id,
            "content_analysis",
            "completed",
            output=payload.get("analysis") or {}
        )

        pipeline["status"] = "analyzing"
        pipeline["current_step"] = "content_analysis"

        logger.info(f"[{pipeline_id}] ✅ Sora generation complete, starting publishing")

        # Proceed to publishing
        video_path = payload.get("stitched_video") or payload.get("video_path")
        analysis = payload.get("analysis", {})
        config: PipelineConfig = pipeline["config"]

        # Validate video_path before proceeding to publishing.
        # If Sora returned 0 successful parts, video_path will be None.
        if not video_path:
            error = "No video produced from Sora generation (video_path is None)"
            logger.error(f"[{pipeline_id}] ❌ {error}")
            await self._fail_pipeline(pipeline_id, error)
            return

        pipeline["status"] = "publishing"
        pipeline["current_step"] = "publishing"
        pipeline["outputs"]["publish_jobs"] = []

        # Update database status (ARCH-001)
        await self._db_update_pipeline_status(
            pipeline_id,
            "publishing",
            {
                "stitched_video": video_path,
                "analysis_result": analysis
            }
        )

        # Update step: publishing -> running
        await self._db_update_pipeline_step(pipeline_id, "publishing", "running")

        # Start publishing timeout
        self._start_step_timeout(pipeline_id, "publishing")

        # ARCH-003: Auto-fill titles and descriptions from content analysis
        auto_fill_metadata = self._extract_platform_metadata(analysis)

        # ARCH-005: Create tracked offers for each platform
        tracked_offer_url = config.offer_url
        if config.offer_url:
            try:
                from services.offer_tracker import get_offer_tracker
                tracker = get_offer_tracker()
                tracked_offer_url = await tracker.create_tracked_link(
                    offer_url=config.offer_url,
                    campaign=f"pipeline-{pipeline_id[:8]}",
                    source="blotato",
                    metadata={"theme": config.theme, "num_parts": config.num_parts}
                )
                logger.info(f"[{pipeline_id}] Created tracked offer URL for ARCH-005")
            except Exception as e:
                logger.warning(f"[{pipeline_id}] Failed to create tracked offer: {e}")
                tracked_offer_url = config.offer_url

        # Publish to each platform
        for platform in config.publish_platforms:
            # ARCH-003: Inject platform-specific metadata
            platform_metadata = auto_fill_metadata.get(platform, auto_fill_metadata.get("default", {}))

            await self.event_bus.publish(
                Topics.PUBLISH_REQUESTED,
                {
                    "pipeline_id": pipeline_id,
                    "platform": platform,
                    "video_path": video_path,
                    "analysis": analysis,
                    "offer_url": tracked_offer_url,  # ARCH-005: Use tracked URL
                    # ARCH-003: Auto-filled metadata from content analysis
                    "title": platform_metadata.get("title"),
                    "description": platform_metadata.get("description"),
                    "hashtags": platform_metadata.get("hashtags"),
                    "hook": platform_metadata.get("hook"),
                    "cta": platform_metadata.get("cta"),
                    "viral_score": platform_metadata.get("viral_score"),
                    "content_type": platform_metadata.get("content_type"),
                },
                correlation_id=pipeline["correlation_id"],
                source="MasterOrchestrator"
            )
            pipeline["outputs"]["publish_jobs"].append({"platform": platform, "status": "requested"})

    async def _handle_sora_batch_failed(self, event: Event) -> None:
        payload = event.payload
        pipeline_id = payload.get("pipeline_id")

        if not pipeline_id or pipeline_id not in self.active_pipelines:
            return

        pipeline = self.active_pipelines[pipeline_id]
        pipeline["status"] = "failed"
        error = payload.get("error", "Unknown error")
        pipeline["error"] = error

        logger.error(f"[{pipeline_id}] ❌ Pipeline failed: {error}")

        # Update database (ARCH-001)
        await self._db_update_pipeline_status(pipeline_id, "failed", {"error": error})
        await self._db_update_pipeline_step(pipeline_id, "sora_generation", "failed", error=error)

        # Move to completed
        self.completed_pipelines[pipeline_id] = pipeline
        del self.active_pipelines[pipeline_id]

    async def _handle_publish_completed(self, event: Event) -> None:
        payload = event.payload
        pipeline_id = payload.get("pipeline_id")

        if not pipeline_id or pipeline_id not in self.active_pipelines:
            return

        pipeline = self.active_pipelines[pipeline_id]
        platform = payload.get("platform")

        # Update job status
        for job in pipeline["outputs"].get("publish_jobs", []):
            if job["platform"] == platform:
                job["status"] = "completed"
                break

        # Check if all complete
        all_complete = all(
            job["status"] in ["completed", "failed"]
            for job in pipeline["outputs"].get("publish_jobs", [])
        )

        if all_complete:
            # Cancel publishing timeout
            self._cancel_step_timeout(pipeline_id, "publishing")

            # Count successful publishes
            published_count = sum(
                1 for job in pipeline["outputs"].get("publish_jobs", [])
                if job["status"] == "completed"
            )

            # Update step: publishing -> completed (ARCH-001)
            await self._db_update_pipeline_step(
                pipeline_id,
                "publishing",
                "completed",
                output={"published_count": published_count}
            )
            await self._db_update_pipeline_status(
                pipeline_id,
                pipeline["status"],
                {"published_count": published_count}
            )

            config: PipelineConfig = pipeline["config"]
            if config.schedule_tweets:
                # Schedule Twitter campaign
                pipeline["status"] = "scheduling_tweets"
                pipeline["current_step"] = "twitter_campaign"

                # Update database (ARCH-001)
                await self._db_update_pipeline_status(pipeline_id, "scheduling_tweets")
                await self._db_update_pipeline_step(pipeline_id, "twitter_campaign", "running")

                # Start twitter_campaign timeout
                self._start_step_timeout(pipeline_id, "twitter_campaign")

                interval_minutes = int((24 * 60) / config.tweets_per_day)

                await self.event_bus.publish(
                    "twitter.campaign.schedule_requested",
                    {
                        "pipeline_id": pipeline_id,
                        "theme": config.theme,
                        "count": config.tweets_per_day,
                        "interval_minutes": interval_minutes,
                        "offer_url": config.offer_url
                    },
                    correlation_id=pipeline["correlation_id"],
                    source="MasterOrchestrator"
                )
            else:
                await self._complete_pipeline(pipeline_id)

    async def _handle_publish_failed(self, event: Event) -> None:
        payload = event.payload
        pipeline_id = payload.get("pipeline_id")
        
        if not pipeline_id or pipeline_id not in self.active_pipelines:
            return

        pipeline = self.active_pipelines[pipeline_id]
        platform = payload.get("platform")
        
        for job in pipeline["outputs"].get("publish_jobs", []):
            if job["platform"] == platform:
                job["status"] = "failed"
                job["error"] = payload.get("error", "Unknown error")
                break

        # Check if all complete (including failures)
        all_complete = all(
            job["status"] in ["completed", "failed"]
            for job in pipeline["outputs"].get("publish_jobs", [])
        )

        if all_complete:
            config: PipelineConfig = pipeline["config"]
            if config.schedule_tweets:
                # Continue to Twitter campaign even if some platforms failed
                pipeline["status"] = "scheduling_tweets"
            else:
                await self._complete_pipeline(pipeline_id)

    async def _handle_twitter_scheduled(self, event: Event) -> None:
        payload = event.payload
        pipeline_id = payload.get("pipeline_id")

        if not pipeline_id or pipeline_id not in self.active_pipelines:
            return

        # Cancel twitter_campaign timeout
        self._cancel_step_timeout(pipeline_id, "twitter_campaign")

        pipeline = self.active_pipelines[pipeline_id]
        tweets_scheduled = payload.get("tweets_scheduled", 0)
        pipeline["outputs"]["twitter"] = {
            "tweets_scheduled": tweets_scheduled
        }

        # Update step: twitter_campaign -> completed (ARCH-001)
        await self._db_update_pipeline_step(
            pipeline_id,
            "twitter_campaign",
            "completed",
            output={"tweets_scheduled": tweets_scheduled}
        )

        await self._complete_pipeline(pipeline_id)

    def _start_step_timeout(self, pipeline_id: str, step_name: str) -> None:
        """Start a timeout monitor for a pipeline step."""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return

        config: PipelineConfig = pipeline["config"]
        timeout_secs = config.step_timeouts.get(step_name, 300)

        # Cancel existing timeout for this pipeline if any
        task_key = f"{pipeline_id}:{step_name}"
        if task_key in self._timeout_tasks:
            self._timeout_tasks[task_key].cancel()

        async def _timeout_handler():
            try:
                await asyncio.sleep(timeout_secs)
                # If we get here, the step timed out
                if pipeline_id in self.active_pipelines:
                    p = self.active_pipelines[pipeline_id]
                    if p.get("current_step") == step_name:
                        retries = p.get("_retry_counts", {}).get(step_name, 0)
                        max_retries = config.max_retries

                        if retries < max_retries:
                            logger.warning(
                                f"[{pipeline_id}] Step '{step_name}' timed out after {timeout_secs}s, "
                                f"retrying ({retries + 1}/{max_retries})"
                            )
                            p.setdefault("_retry_counts", {})[step_name] = retries + 1
                            await self._retry_step(pipeline_id, step_name)
                        else:
                            logger.error(
                                f"[{pipeline_id}] Step '{step_name}' timed out after {timeout_secs}s, "
                                f"max retries ({max_retries}) exhausted"
                            )
                            await self._fail_pipeline(
                                pipeline_id,
                                f"Step '{step_name}' timed out after {timeout_secs}s "
                                f"(retries exhausted: {max_retries})"
                            )
            except asyncio.CancelledError:
                pass  # Timeout was cancelled because step completed
            finally:
                self._timeout_tasks.pop(task_key, None)

        self._timeout_tasks[task_key] = asyncio.create_task(_timeout_handler())

    def _cancel_step_timeout(self, pipeline_id: str, step_name: str) -> None:
        """Cancel a timeout monitor for a pipeline step."""
        task_key = f"{pipeline_id}:{step_name}"
        task = self._timeout_tasks.pop(task_key, None)
        if task and not task.done():
            task.cancel()

    async def _retry_step(self, pipeline_id: str, step_name: str) -> None:
        """Retry a failed/timed-out pipeline step."""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return

        config: PipelineConfig = pipeline["config"]

        logger.info(f"[{pipeline_id}] Retrying step: {step_name}")

        await self._db_update_pipeline_step(pipeline_id, step_name, "retrying")

        if step_name == "sora_generation":
            # Re-trigger Sora batch generation
            self._start_step_timeout(pipeline_id, "sora_generation")
            await self.event_bus.publish(
                Topics.SORA_BATCH_REQUESTED,
                {
                    "pipeline_id": pipeline_id,
                    "theme": config.theme,
                    "num_parts": config.num_parts,
                    "character": config.character,
                    "stitch": True,
                    "remove_watermark": True,
                    "retry": True
                },
                correlation_id=pipeline["correlation_id"],
                source="MasterOrchestrator"
            )
        elif step_name == "publishing":
            # Re-publish to platforms that haven't completed
            pending_jobs = [
                job for job in pipeline["outputs"].get("publish_jobs", [])
                if job["status"] not in ["completed"]
            ]
            self._start_step_timeout(pipeline_id, "publishing")
            for job in pending_jobs:
                job["status"] = "requested"
                analysis = pipeline["outputs"].get("sora", {}).get("analysis", {})
                auto_fill = self._extract_platform_metadata(analysis)
                platform_meta = auto_fill.get(job["platform"], auto_fill.get("default", {}))

                await self.event_bus.publish(
                    Topics.PUBLISH_REQUESTED,
                    {
                        "pipeline_id": pipeline_id,
                        "platform": job["platform"],
                        "video_path": pipeline["outputs"].get("sora", {}).get("stitched_video"),
                        "analysis": analysis,
                        "offer_url": config.offer_url,
                        "title": platform_meta.get("title"),
                        "description": platform_meta.get("description"),
                        "hashtags": platform_meta.get("hashtags"),
                        "retry": True
                    },
                    correlation_id=pipeline["correlation_id"],
                    source="MasterOrchestrator"
                )

    async def _fail_pipeline(self, pipeline_id: str, error: str) -> None:
        """Fail a pipeline with an error message."""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return

        pipeline["status"] = "failed"
        pipeline["error"] = error
        pipeline["failed_at"] = datetime.now(timezone.utc).isoformat()

        logger.error(f"[{pipeline_id}] Pipeline failed: {error}")

        # Cancel any active timeout monitors
        for key in list(self._timeout_tasks.keys()):
            if key.startswith(pipeline_id):
                self._cancel_step_timeout(pipeline_id, key.split(":")[1])

        await self._db_update_pipeline_status(pipeline_id, "failed", {"error": error})

        await self.event_bus.publish(
            "orchestrator.pipeline.failed",
            {"pipeline_id": pipeline_id, "error": error},
            correlation_id=pipeline.get("correlation_id"),
            source="MasterOrchestrator"
        )

        self.completed_pipelines[pipeline_id] = pipeline
        del self.active_pipelines[pipeline_id]

    async def _complete_pipeline(self, pipeline_id: str) -> None:
        """Mark pipeline as completed and persist final state."""
        pipeline = self.active_pipelines[pipeline_id]
        pipeline["status"] = "completed"
        pipeline["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Cancel any remaining timeout monitors
        for key in list(self._timeout_tasks.keys()):
            if key.startswith(pipeline_id):
                self._cancel_step_timeout(pipeline_id, key.split(":")[1])

        # Calculate total pipeline duration
        started_at = pipeline.get("started_at")
        if started_at:
            try:
                start_dt = datetime.fromisoformat(started_at)
                end_dt = datetime.fromisoformat(pipeline["completed_at"])
                pipeline["duration_seconds"] = (end_dt - start_dt).total_seconds()
            except (ValueError, TypeError):
                pass

        logger.info(f"[{pipeline_id}] 🎉 Pipeline completed successfully")

        # Update database with final state (ARCH-001)
        updates = {}
        if "twitter" in pipeline.get("outputs", {}):
            updates["tweets_scheduled"] = pipeline["outputs"]["twitter"].get("tweets_scheduled", 0)

        await self._db_update_pipeline_status(pipeline_id, "completed", updates)

        await self.event_bus.publish(
            Topics.ORCHESTRATOR_PIPELINE_COMPLETED,
            {"pipeline_id": pipeline_id, "theme": pipeline["config"].theme},
            correlation_id=pipeline["correlation_id"],
            source="MasterOrchestrator"
        )

        # Move to completed
        self.completed_pipelines[pipeline_id] = pipeline
        del self.active_pipelines[pipeline_id]

    async def _step_publish_to_platforms(self, video_path: str, analysis: Dict[str, Any], platforms: List[str]) -> Dict[str, Any]:
        """
        Legacy method for test compatibility.

        In the event-driven architecture, this is handled by event handlers,
        but kept for backward compatibility with tests.
        """
        # This method is not actually used in the event-driven flow
        # It exists for test mocking purposes only
        return {
            "results": [],
            "total": 0
        }

    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Get the status of a pipeline (synchronous for compatibility).

        Returns pipeline dict if found, otherwise dict with error.
        """
        if pipeline_id in self.active_pipelines:
            pipeline = self.active_pipelines[pipeline_id]
            # Ensure 'id' field is present for compatibility
            if "id" not in pipeline:
                pipeline["id"] = pipeline["pipeline_id"]
            return pipeline
        elif pipeline_id in self.completed_pipelines:
            pipeline = self.completed_pipelines[pipeline_id]
            # Ensure 'id' field is present for compatibility
            if "id" not in pipeline:
                pipeline["id"] = pipeline["pipeline_id"]
            return pipeline
        else:
            return {"error": "Pipeline not found"}

    async def list_pipelines(self, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """List pipelines from database if available, otherwise from memory."""
        if self.use_db and self._db_engine:
            return await self._db_list_pipelines(status, limit)

        # Fallback to in-memory
        all_pipelines = list(self.active_pipelines.values()) + list(self.completed_pipelines.values())

        if status:
            all_pipelines = [p for p in all_pipelines if p.get("status") == status]

        # Sort by started_at descending
        all_pipelines.sort(key=lambda p: p.get("started_at", ""), reverse=True)

        return all_pipelines[:limit]

    # ------------------------------------------------------------------
    # Method aliases for compatibility with different test suites
    # ------------------------------------------------------------------

    async def run_content_pipeline(self, **kwargs) -> str:
        """Alias for run_full_pipeline."""
        return await self.run_full_pipeline(**kwargs)

    def get_job_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Alias for get_pipeline_status."""
        return self.get_pipeline_status(pipeline_id)

    async def list_jobs(self, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Alias for list_pipelines."""
        return await self.list_pipelines(status=status, limit=limit)

    def list_active_pipelines(self) -> List[Dict[str, Any]]:
        """
        List currently active pipelines (synchronous version for compatibility).

        Returns list of active pipeline dictionaries.
        """
        return list(self.active_pipelines.values())

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """
        Get aggregate metrics for all pipelines (ARCH-008).

        Returns:
            Dict with pipeline counts, status breakdown, and timing.
        """
        active = list(self.active_pipelines.values())
        completed = list(self.completed_pipelines.values())
        all_pipelines = active + completed

        status_counts: Dict[str, int] = {}
        for p in all_pipelines:
            status = p.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_pipelines": len(all_pipelines),
            "active_pipelines": len(active),
            "completed_pipelines": len(completed),
            "status_breakdown": status_counts,
        }

    def get_pipeline_health(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Get health status of a pipeline including timeout and retry info.

        Returns:
            Dict with health metrics, active timeouts, and retry counts.
        """
        pipeline = self.active_pipelines.get(pipeline_id) or self.completed_pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}

        active_timeouts = [
            key.split(":")[1]
            for key in self._timeout_tasks
            if key.startswith(pipeline_id) and not self._timeout_tasks[key].done()
        ]

        return {
            "pipeline_id": pipeline_id,
            "status": pipeline.get("status"),
            "current_step": pipeline.get("current_step"),
            "active_timeouts": active_timeouts,
            "retry_counts": pipeline.get("_retry_counts", {}),
            "started_at": pipeline.get("started_at"),
            "duration_seconds": pipeline.get("duration_seconds"),
        }

    def _extract_platform_metadata(self, analysis: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Extract platform-specific metadata from content analysis (ARCH-003).

        Converts AI analysis into platform-optimized titles, descriptions,
        hashtags, and engagement metadata. Uses the full ContentAnalyzer
        output including pain_points, emotional_journey, CTA, viral_score,
        and target_audience to produce richer publishing payloads.

        Args:
            analysis: Content analysis dict from ContentAnalyzer (may be None)

        Returns:
            Dict mapping platform names to metadata dicts
        """
        if not analysis:
            analysis = {}

        # Extract common fields from analysis
        hook = analysis.get("detected_hook") or analysis.get("hook") or ""
        topics = analysis.get("topics", [])
        hashtags = analysis.get("hashtags", [])
        viral_score = analysis.get("viral_score") or analysis.get("pre_social_score", 0)
        cta_data = analysis.get("call_to_action", {})
        cta_text = cta_data.get("text", "") if isinstance(cta_data, dict) else ""
        content_type = analysis.get("content_type", "general")
        tone = analysis.get("tone", "")
        description = analysis.get("description") or analysis.get("viral_analysis") or ""
        pain_points = analysis.get("pain_points", [])
        target_audience = analysis.get("target_audience", {})
        pacing = analysis.get("pacing", "medium")

        # ARCH-003: Generate hashtags from topics when none provided
        if not hashtags and topics:
            hashtags = [
                topic.lower().replace(" ", "").replace("-", "")
                for topic in topics[:15]
            ]

        # Build base metadata shared across platforms
        base = {
            "title": hook or "Untitled",
            "description": description,
            "hashtags": hashtags,
            "hook": hook,
            "viral_score": viral_score,
            "cta": cta_text,
            "content_type": content_type,
            "tone": tone,
            "topics": topics,
            "pain_points": pain_points,
            "target_audience": target_audience,
            "pacing": pacing,
        }

        metadata = {"default": base.copy()}

        # TikTok: Short hook + heavy hashtags (max 10), FYP-optimized
        tiktok_hashtags = list(hashtags[:7])
        for tag in ["fyp", "viral", "foryou"]:
            if tag not in [h.lower() for h in tiktok_hashtags] and len(tiktok_hashtags) < 10:
                tiktok_hashtags.append(tag)
        metadata["tiktok"] = {
            **base,
            "title": analysis.get("title_tiktok") or hook,
            "hashtags": tiktok_hashtags,
            "description": hook,  # TikTok captions should be short
        }

        # Instagram: Longer caption, up to 30 hashtags, engagement-focused
        ig_hashtags = list(hashtags[:25])
        for tag in ["reels", "explore", "instagood", "trending", "viral"]:
            if tag not in [h.lower() for h in ig_hashtags] and len(ig_hashtags) < 30:
                ig_hashtags.append(tag)
        metadata["instagram"] = {
            **base,
            "title": analysis.get("title_instagram") or hook,
            "hashtags": ig_hashtags,
        }

        # YouTube: SEO-focused title + description with keywords
        yt_description = description
        if pain_points:
            yt_description += f"\n\nKey topics: {', '.join(pain_points[:3])}"
        if target_audience and target_audience.get("interests"):
            yt_description += f"\nFor: {', '.join(target_audience['interests'][:3])}"
        metadata["youtube"] = {
            **base,
            "title": analysis.get("title_youtube") or hook,
            "description": yt_description,
            "hashtags": hashtags[:15],
        }

        # Twitter/X: Very short, 3 hashtags max
        metadata["twitter"] = {
            **base,
            "title": hook[:200] if hook else "",
            "description": hook[:250] if hook else "",
            "hashtags": hashtags[:3],
        }

        # Threads: Conversation-starting format
        metadata["threads"] = {
            **base,
            "title": analysis.get("title_instagram") or hook,
            "hashtags": hashtags[:10],
        }

        # LinkedIn: Professional tone, insight-focused
        linkedin_desc = description
        if target_audience and target_audience.get("demographic"):
            linkedin_desc = f"{description}\n\n{target_audience['demographic']}"
        metadata["linkedin"] = {
            **base,
            "title": hook,
            "description": linkedin_desc,
            "hashtags": hashtags[:5],
            "tone": "professional",
        }

        # Pinterest: Visual discovery, keyword-rich
        metadata["pinterest"] = {
            **base,
            "title": hook[:100] if hook else "",
            "description": f"{description} {' '.join(topics[:3])}" if topics else description,
            "hashtags": hashtags[:20],
        }

        # Remaining platforms use default
        for platform in ["facebook", "bluesky"]:
            if platform not in metadata:
                metadata[platform] = base.copy()

        logger.debug(
            f"[ARCH-003] Extracted metadata for {len(metadata)} platforms "
            f"(viral_score={viral_score}, hook='{hook[:40]}...')"
        )
        return metadata

    # Database persistence methods (ARCH-001)

    async def _db_save_pipeline(self, pipeline_id: str, pipeline: Dict[str, Any]) -> None:
        """Save pipeline to database."""
        if not self.use_db or not self._db_engine:
            return

        try:
            from sqlalchemy import text

            config: PipelineConfig = pipeline["config"]

            with self._db_engine.connect() as conn:
                # Upsert pipeline
                conn.execute(text("""
                    INSERT INTO orchestrator_pipelines (
                        pipeline_id, theme, num_parts, character,
                        publish_platforms, schedule_tweets, tweets_per_day, offer_url,
                        status, correlation_id, started_at, metadata
                    ) VALUES (
                        :pipeline_id, :theme, :num_parts, :character,
                        :publish_platforms, :schedule_tweets, :tweets_per_day, :offer_url,
                        :status, :correlation_id, :started_at, :metadata
                    )
                    ON CONFLICT (pipeline_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata
                """), {
                    "pipeline_id": pipeline_id,
                    "theme": config.theme,
                    "num_parts": config.num_parts,
                    "character": config.character,
                    "publish_platforms": config.publish_platforms,
                    "schedule_tweets": config.schedule_tweets,
                    "tweets_per_day": config.tweets_per_day,
                    "offer_url": config.offer_url,
                    "status": pipeline["status"],
                    "correlation_id": pipeline["correlation_id"],
                    "started_at": pipeline["started_at"],
                    "metadata": "{}"  # Can be expanded with config.metadata
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save pipeline to DB: {e}")

    async def _db_update_pipeline_status(
        self,
        pipeline_id: str,
        status: str,
        updates: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update pipeline status and fields in database."""
        if not self.use_db or not self._db_engine:
            return

        try:
            from sqlalchemy import text

            with self._db_engine.connect() as conn:
                params = {
                    "pipeline_id": pipeline_id,
                    "status": status
                }

                update_parts = ["status = :status"]

                if updates:
                    if "stitched_video" in updates:
                        update_parts.append("stitched_video = :stitched_video")
                        params["stitched_video"] = updates["stitched_video"]

                    if "analysis_result" in updates:
                        update_parts.append("analysis_result = :analysis_result::jsonb")
                        import json
                        params["analysis_result"] = json.dumps(updates["analysis_result"])

                    if "published_count" in updates:
                        update_parts.append("published_count = :published_count")
                        params["published_count"] = updates["published_count"]

                    if "tweets_scheduled" in updates:
                        update_parts.append("tweets_scheduled = :tweets_scheduled")
                        params["tweets_scheduled"] = updates["tweets_scheduled"]

                    if "error" in updates:
                        update_parts.append("error = :error, failed_at = NOW()")
                        params["error"] = updates["error"]

                if status == "completed":
                    update_parts.append("completed_at = NOW()")
                elif status == "failed":
                    update_parts.append("failed_at = NOW()")

                query = f"""
                    UPDATE orchestrator_pipelines
                    SET {", ".join(update_parts)}
                    WHERE pipeline_id = :pipeline_id
                """

                conn.execute(text(query), params)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update pipeline status in DB: {e}")

    async def _db_add_pipeline_step(
        self,
        pipeline_id: str,
        step_name: str,
        step_order: int,
        status: str = "pending"
    ) -> None:
        """Add a pipeline step to database."""
        if not self.use_db or not self._db_engine:
            return

        try:
            from sqlalchemy import text

            with self._db_engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO orchestrator_pipeline_steps (
                        pipeline_id, step_name, step_order, status
                    ) VALUES (
                        :pipeline_id, :step_name, :step_order, :status
                    )
                """), {
                    "pipeline_id": pipeline_id,
                    "step_name": step_name,
                    "step_order": step_order,
                    "status": status
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to add pipeline step to DB: {e}")

    async def _db_update_pipeline_step(
        self,
        pipeline_id: str,
        step_name: str,
        status: str,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Update a pipeline step in database."""
        if not self.use_db or not self._db_engine:
            return

        try:
            from sqlalchemy import text
            import json

            with self._db_engine.connect() as conn:
                params = {
                    "pipeline_id": pipeline_id,
                    "step_name": step_name,
                    "status": status
                }

                update_parts = ["status = :status"]

                if status == "running" and not error:
                    update_parts.append("started_at = NOW()")
                elif status == "completed":
                    update_parts.append("completed_at = NOW()")
                elif status == "failed":
                    update_parts.append("failed_at = NOW()")

                if output:
                    update_parts.append("output = :output::jsonb")
                    params["output"] = json.dumps(output)

                if error:
                    update_parts.append("error = :error")
                    params["error"] = error

                query = f"""
                    UPDATE orchestrator_pipeline_steps
                    SET {", ".join(update_parts)}
                    WHERE pipeline_id = :pipeline_id AND step_name = :step_name
                """

                conn.execute(text(query), params)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update pipeline step in DB: {e}")

    async def _db_list_pipelines(self, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """List pipelines from database."""
        try:
            from sqlalchemy import text

            with self._db_engine.connect() as conn:
                query = """
                    SELECT
                        pipeline_id, theme, num_parts, character,
                        publish_platforms, schedule_tweets, tweets_per_day, offer_url,
                        status, started_at, completed_at, failed_at,
                        stitched_video, published_count, tweets_scheduled,
                        error, correlation_id
                    FROM orchestrator_pipelines
                """

                if status:
                    query += " WHERE status = :status"

                query += " ORDER BY started_at DESC LIMIT :limit"

                params = {"limit": limit}
                if status:
                    params["status"] = status

                result = conn.execute(text(query), params)

                pipelines = []
                for row in result:
                    pipelines.append({
                        "pipeline_id": row[0],
                        "theme": row[1],
                        "num_parts": row[2],
                        "character": row[3],
                        "publish_platforms": row[4],
                        "schedule_tweets": row[5],
                        "tweets_per_day": row[6],
                        "offer_url": row[7],
                        "status": row[8],
                        "started_at": row[9].isoformat() if row[9] else None,
                        "completed_at": row[10].isoformat() if row[10] else None,
                        "failed_at": row[11].isoformat() if row[11] else None,
                        "stitched_video": row[12],
                        "published_count": row[13],
                        "tweets_scheduled": row[14],
                        "error": row[15],
                        "correlation_id": row[16]
                    })

                return pipelines
        except Exception as e:
            logger.error(f"Failed to list pipelines from DB: {e}")
            return []

    async def cleanup_old_pipelines(self, days_old: int = 7) -> int:
        """
        Delete old completed pipelines beyond retention period (ARCH-001).

        Args:
            days_old: Delete pipelines completed more than N days ago

        Returns:
            Number of pipelines deleted
        """
        if not self.use_db or not self._db_engine:
            return 0

        try:
            from sqlalchemy import text

            with self._db_engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM orchestrator_pipelines
                    WHERE status IN ('completed', 'failed')
                    AND completed_at IS NOT NULL
                    AND completed_at < NOW() - INTERVAL '%s days'
                    RETURNING pipeline_id
                """ % days_old))

                deleted_count = len(result.fetchall())
                conn.commit()

                logger.info(f"Cleaned up {deleted_count} pipelines older than {days_old} days")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old pipelines: {e}")
            return 0

    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about all pipelines (ARCH-008).

        Returns:
            Dict with pipeline metrics and performance data
        """
        active = list(self.active_pipelines.values())
        completed = list(self.completed_pipelines.values())
        all_pipelines = active + completed

        if not all_pipelines:
            return {
                "total_pipelines": 0,
                "active_pipelines": 0,
                "completed_pipelines": 0,
                "status_breakdown": {},
                "average_duration_seconds": 0,
                "success_rate": 0,
                "total_videos_generated": 0,
                "total_posts_published": 0,
                "total_tweets_scheduled": 0
            }

        # Calculate duration statistics
        durations = []
        for p in completed:
            if p.get("duration_seconds"):
                durations.append(p["duration_seconds"])

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Calculate success rate
        success_count = sum(1 for p in all_pipelines if p.get("status") == "completed")
        success_rate = (success_count / len(all_pipelines) * 100) if all_pipelines else 0

        # Aggregate outputs
        total_posts = sum(p.get("outputs", {}).get("publish_jobs", {}) and
                          len([j for j in p["outputs"]["publish_jobs"] if j["status"] == "completed"])
                          or 0 for p in all_pipelines)
        total_tweets = sum(p.get("outputs", {}).get("twitter", {}).get("tweets_scheduled", 0)
                          for p in all_pipelines)

        status_counts = {}
        for p in all_pipelines:
            status = p.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_pipelines": len(all_pipelines),
            "active_pipelines": len(active),
            "completed_pipelines": len(completed),
            "status_breakdown": status_counts,
            "average_duration_seconds": round(avg_duration, 2),
            "success_rate": round(success_rate, 2),
            "total_videos_generated": len(completed),
            "total_posts_published": total_posts,
            "total_tweets_scheduled": total_tweets,
        }


# ============================================================================
# Module-level Convenience Functions
# ============================================================================

def get_orchestrator(event_bus: Optional[EventBus] = None, use_db: bool = True) -> MasterOrchestrator:
    """
    Get the singleton MasterOrchestrator instance.

    Args:
        event_bus: Optional EventBus instance (defaults to singleton)
        use_db: Whether to use database persistence (default: True)

    Returns:
        MasterOrchestrator singleton instance
    """
    return MasterOrchestrator.get_instance(event_bus, use_db)

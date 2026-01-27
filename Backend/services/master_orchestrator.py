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
from typing import Dict, Any, List, Optional
from uuid import uuid4
import os

from services.event_bus import EventBus, Event, Topics
from services.content_analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)


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
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.theme = theme
        self.num_parts = num_parts
        self.character = character
        self.publish_platforms = publish_platforms or ["tiktok", "instagram", "youtube"]
        self.schedule_tweets = schedule_tweets
        self.tweets_per_day = tweets_per_day
        self.offer_url = offer_url
        self.metadata = metadata or {}


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

        # In-memory cache for fast access
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}
        self.completed_pipelines: Dict[str, Dict[str, Any]] = {}

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

        # Start Sora video generation
        await self.event_bus.publish(
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

        pipeline["status"] = "generating_video"
        await self._db_update_pipeline_status(pipeline_id, "generating_video")

        return pipeline_id

    async def _handle_sora_batch_completed(self, event: Event) -> None:
        payload = event.payload
        pipeline_id = payload.get("pipeline_id")

        if not pipeline_id or pipeline_id not in self.active_pipelines:
            return

        pipeline = self.active_pipelines[pipeline_id]
        pipeline["outputs"]["sora"] = {
            "stitched_video": payload.get("stitched_video"),
            "analysis": payload.get("analysis")
        }

        # Update step: sora_generation -> completed (ARCH-001)
        await self._db_update_pipeline_step(
            pipeline_id,
            "sora_generation",
            "completed",
            output={
                "stitched_video": payload.get("stitched_video"),
                "successful_parts": payload.get("successful_parts", 0),
                "failed_parts": payload.get("failed_parts", 0)
            }
        )

        # Update step: content_analysis -> completed (assuming it's done in Sora pipeline)
        await self._db_update_pipeline_step(
            pipeline_id,
            "content_analysis",
            "completed",
            output=payload.get("analysis", {})
        )

        pipeline["status"] = "analyzing"
        pipeline["current_step"] = "content_analysis"

        logger.info(f"[{pipeline_id}] ✅ Sora generation complete, starting publishing")

        # Proceed to publishing
        video_path = payload.get("stitched_video")
        analysis = payload.get("analysis", {})
        config: PipelineConfig = pipeline["config"]

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

        # Publish to each platform
        for platform in config.publish_platforms:
            await self.event_bus.publish(
                Topics.PUBLISH_REQUESTED,
                {
                    "pipeline_id": pipeline_id,
                    "platform": platform,
                    "video_path": video_path,
                    "analysis": analysis,
                    "offer_url": config.offer_url
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

    async def _complete_pipeline(self, pipeline_id: str) -> None:
        """Mark pipeline as completed and persist final state."""
        pipeline = self.active_pipelines[pipeline_id]
        pipeline["status"] = "completed"
        pipeline["completed_at"] = datetime.now(timezone.utc).isoformat()

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

    async def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        if pipeline_id in self.active_pipelines:
            return self.active_pipelines[pipeline_id]
        elif pipeline_id in self.completed_pipelines:
            return self.completed_pipelines[pipeline_id]
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

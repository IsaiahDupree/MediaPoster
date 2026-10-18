"""
Generated Video Multi-Channel Pipeline (BM-011)
=================================================
Platform-agnostic pipeline: Generate video -> AI analyze -> Route to channels
with optional human-in-the-loop approval.

Workflow:
    1. Accept video (from Sora, AI, or upload)
    2. Analyze content with AI (ContentAnalyzer)
    3. If approval required, submit to approval queue and wait
    4. Route to selected channels via ChannelRouter
    5. Track all published URLs

Integrates with:
    - SoraGenerator (BM-010) for video generation
    - ContentAnalyzer for AI analysis
    - ChannelRouter (HITL-007) for platform routing
    - ApprovalWorkflow (HITL-001) for human approval gate
    - MasterOrchestrator (ARCH-001) for pipeline coordination
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    INITIALIZED = "initialized"
    GENERATING = "generating"
    ANALYZING = "analyzing"
    AWAITING_APPROVAL = "awaiting_approval"
    ROUTING = "routing"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class PublishResult:
    """Result of publishing to a single platform."""
    platform: str
    success: bool
    post_url: Optional[str] = None
    account_id: Optional[str] = None
    error: Optional[str] = None
    published_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "success": self.success,
            "post_url": self.post_url,
            "account_id": self.account_id,
            "error": self.error,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


@dataclass
class VideoPipelineJob:
    """A video publish pipeline job."""
    id: str = field(default_factory=lambda: f"vpipe-{uuid4().hex[:8]}")
    video_path: Optional[str] = None
    video_source: str = "upload"  # sora, ai, upload
    stage: PipelineStage = PipelineStage.INITIALIZED
    target_platforms: List[str] = field(default_factory=list)
    analysis: Optional[Dict[str, Any]] = None
    approval_id: Optional[str] = None
    approval_required: bool = False
    offer_url: Optional[str] = None
    publish_results: List[PublishResult] = field(default_factory=list)
    published_urls: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def successful_publishes(self) -> int:
        return sum(1 for r in self.publish_results if r.success)

    @property
    def failed_publishes(self) -> int:
        return sum(1 for r in self.publish_results if not r.success)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "video_path": self.video_path,
            "video_source": self.video_source,
            "stage": self.stage.value,
            "target_platforms": self.target_platforms,
            "analysis": self.analysis,
            "approval_id": self.approval_id,
            "approval_required": self.approval_required,
            "offer_url": self.offer_url,
            "publish_results": [r.to_dict() for r in self.publish_results],
            "published_urls": self.published_urls,
            "successful_publishes": self.successful_publishes,
            "failed_publishes": self.failed_publishes,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class VideoPublishPipeline:
    """
    Generated Video Multi-Channel Pipeline (BM-011).

    Orchestrates the full pipeline from video source through analysis,
    optional approval, and multi-platform publishing.
    """

    _instance = None

    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        self._jobs: Dict[str, VideoPipelineJob] = {}
        self._is_running: bool = False
        logger.info("VideoPublishPipeline initialized (BM-011)")

    @classmethod
    def get_instance(cls, event_bus=None) -> "VideoPublishPipeline":
        if cls._instance is None:
            cls._instance = cls(event_bus=event_bus)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    @property
    def event_bus(self):
        if self._event_bus is None:
            try:
                from services.event_bus import EventBus
                self._event_bus = EventBus.get_instance()
            except Exception:
                pass
        return self._event_bus

    async def start(self):
        """Start the pipeline and subscribe to events."""
        self._is_running = True
        if self.event_bus:
            self.event_bus.subscribe(
                "video.pipeline.requested", self._handle_pipeline_request
            )
            self.event_bus.subscribe(
                "approval.approved", self._handle_approval_response
            )
            self.event_bus.subscribe(
                "approval.rejected", self._handle_rejection_response
            )
        logger.info("VideoPublishPipeline started")

    async def stop(self):
        """Stop the pipeline."""
        self._is_running = False
        logger.info("VideoPublishPipeline stopped")

    async def run_pipeline(
        self,
        video_path: str,
        target_platforms: List[str],
        video_source: str = "upload",
        approval_required: bool = False,
        offer_url: Optional[str] = None,
        analysis_override: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VideoPipelineJob:
        """
        Run the full video publishing pipeline.

        Steps:
            1. Validate video exists
            2. Analyze content with AI
            3. If approval required, submit to approval queue
            4. Route to target platforms
            5. Collect results

        Args:
            video_path: Path to the video file
            target_platforms: List of platforms to publish to
            video_source: Source of video (sora, ai, upload)
            approval_required: Whether human approval is needed
            offer_url: Optional offer URL for tracking
            analysis_override: Skip analysis and use provided data
            metadata: Additional metadata

        Returns:
            VideoPipelineJob with results
        """
        job = VideoPipelineJob(
            video_path=video_path,
            video_source=video_source,
            target_platforms=target_platforms,
            approval_required=approval_required,
            offer_url=offer_url,
            metadata=metadata or {},
        )
        self._jobs[job.id] = job

        await self._emit_event("video.pipeline.started", {
            "job_id": job.id,
            "video_source": video_source,
            "platforms": target_platforms,
            "approval_required": approval_required,
        })

        try:
            # Step 1: Validate
            if not video_path:
                raise ValueError("video_path is required")

            # Step 2: Analyze
            job.stage = PipelineStage.ANALYZING
            if analysis_override:
                job.analysis = analysis_override
            else:
                job.analysis = await self._analyze_video(video_path)

            # Step 3: Approval gate
            if approval_required:
                job.stage = PipelineStage.AWAITING_APPROVAL
                job.approval_id = await self._submit_for_approval(job)
                await self._emit_event("video.pipeline.awaiting_approval", {
                    "job_id": job.id,
                    "approval_id": job.approval_id,
                })
                # Pipeline pauses here - resumed via _handle_approval_response
                return job

            # Step 4: Route and publish
            await self._route_and_publish(job)

        except Exception as e:
            job.stage = PipelineStage.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            logger.error(f"Pipeline {job.id} failed: {e}")

            await self._emit_event("video.pipeline.failed", {
                "job_id": job.id,
                "error": str(e),
            })

        return job

    async def _analyze_video(self, video_path: str) -> Dict[str, Any]:
        """Analyze video content using ContentAnalyzer."""
        try:
            from services.content_analyzer import ContentAnalyzer
            analyzer = ContentAnalyzer()
            # For video analysis, we'd extract transcript first
            # For now, use visual analysis as fallback
            result = analyzer.analyze_from_visuals(
                f"Video file: {os.path.basename(video_path)}",
                {"source": video_path},
            )
            return result
        except Exception as e:
            logger.warning(f"Content analysis failed, using defaults: {e}")
            return {
                "detected_hook": "",
                "hashtags": [],
                "topics": [],
                "viral_score": 50,
                "description": "",
            }

    async def _submit_for_approval(self, job: VideoPipelineJob) -> str:
        """Submit job to approval queue."""
        try:
            from services.approval_queue import ApprovalQueue, ApprovalPriority
            queue = ApprovalQueue()
            item_id = await queue.add_item(
                content_id=job.id,
                content_type="video",
                content_data={
                    "video_path": job.video_path,
                    "analysis": job.analysis,
                    "target_platforms": job.target_platforms,
                    "offer_url": job.offer_url,
                },
                priority=ApprovalPriority.HIGH,
            )
            return item_id
        except Exception as e:
            logger.warning(f"Approval submission failed: {e}")
            return f"approval-{job.id}"

    async def _route_and_publish(self, job: VideoPipelineJob):
        """Route video to target platforms."""
        job.stage = PipelineStage.ROUTING

        try:
            from services.channel_router import ChannelRouter
            router = ChannelRouter.get_instance()

            route_result = await router.route_content(
                video_path=job.video_path,
                platforms=job.target_platforms,
                analysis=job.analysis,
                offer_url=job.offer_url,
                metadata=job.metadata,
            )

            # Collect results from RouteResult object
            for platform, platform_result in route_result.platform_results.items():
                pr = PublishResult(
                    platform=platform,
                    success=platform_result.success,
                    post_url=platform_result.post_url,
                    account_id=platform_result.account_id,
                    error=platform_result.error,
                    published_at=datetime.now(timezone.utc) if platform_result.success else None,
                )
                job.publish_results.append(pr)
                if pr.post_url:
                    job.published_urls[pr.platform] = pr.post_url

        except ImportError:
            # ChannelRouter not yet available, publish directly via EventBus
            logger.info("ChannelRouter not available, using direct EventBus publishing")
            for platform in job.target_platforms:
                await self._emit_event("publish.requested", {
                    "job_id": job.id,
                    "platform": platform,
                    "video_path": job.video_path,
                    "analysis": job.analysis,
                    "offer_url": job.offer_url,
                })
                job.publish_results.append(PublishResult(
                    platform=platform,
                    success=True,  # Optimistic - actual result via events
                ))

        except Exception as e:
            logger.error(f"Routing failed: {e}")
            job.stage = PipelineStage.FAILED
            job.error = str(e)
            return

        # Mark complete
        job.stage = PipelineStage.COMPLETED
        job.completed_at = datetime.now(timezone.utc)

        await self._emit_event("video.pipeline.completed", {
            "job_id": job.id,
            "successful_publishes": job.successful_publishes,
            "failed_publishes": job.failed_publishes,
            "published_urls": job.published_urls,
        })

        logger.info(
            f"Pipeline {job.id} completed: "
            f"{job.successful_publishes}/{len(job.target_platforms)} published"
        )

    async def _handle_pipeline_request(self, event):
        """Handle incoming pipeline request from EventBus."""
        payload = event.payload
        await self.run_pipeline(
            video_path=payload.get("video_path", ""),
            target_platforms=payload.get("platforms", []),
            video_source=payload.get("video_source", "upload"),
            approval_required=payload.get("approval_required", False),
            offer_url=payload.get("offer_url"),
            metadata=payload.get("metadata"),
        )

    async def _handle_approval_response(self, event):
        """Handle approval from approval queue."""
        payload = event.payload
        approval_id = payload.get("approval_id", "")

        # Find the job with this approval_id
        job = None
        for j in self._jobs.values():
            if j.approval_id == approval_id:
                job = j
                break

        if not job:
            logger.warning(f"No job found for approval {approval_id}")
            return

        logger.info(f"Pipeline {job.id} approved, continuing to publish")
        await self._route_and_publish(job)

    async def _handle_rejection_response(self, event):
        """Handle rejection from approval queue."""
        payload = event.payload
        approval_id = payload.get("approval_id", "")

        job = None
        for j in self._jobs.values():
            if j.approval_id == approval_id:
                job = j
                break

        if not job:
            return

        job.stage = PipelineStage.REJECTED
        job.completed_at = datetime.now(timezone.utc)
        job.error = payload.get("reason", "Content rejected")

        await self._emit_event("video.pipeline.rejected", {
            "job_id": job.id,
            "reason": job.error,
        })

        logger.info(f"Pipeline {job.id} rejected: {job.error}")

    async def _emit_event(self, topic: str, payload: Dict[str, Any]):
        """Emit an event to the EventBus."""
        if self.event_bus:
            try:
                await self.event_bus.publish(
                    topic=topic,
                    payload=payload,
                    source="VideoPublishPipeline",
                )
            except Exception as e:
                logger.warning(f"Failed to emit event {topic}: {e}")

    # --- Query methods ---

    def get_job(self, job_id: str) -> Optional[VideoPipelineJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_jobs_by_stage(self, stage: PipelineStage) -> List[VideoPipelineJob]:
        """Get all jobs in a specific stage."""
        return [j for j in self._jobs.values() if j.stage == stage]

    def get_pending_approvals(self) -> List[VideoPipelineJob]:
        """Get all jobs awaiting approval."""
        return self.get_jobs_by_stage(PipelineStage.AWAITING_APPROVAL)

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        jobs = list(self._jobs.values())
        completed = [j for j in jobs if j.stage == PipelineStage.COMPLETED]
        failed = [j for j in jobs if j.stage == PipelineStage.FAILED]
        rejected = [j for j in jobs if j.stage == PipelineStage.REJECTED]
        awaiting = [j for j in jobs if j.stage == PipelineStage.AWAITING_APPROVAL]

        total_published = sum(j.successful_publishes for j in completed)
        total_urls = {}
        for j in completed:
            total_urls.update(j.published_urls)

        return {
            "total_jobs": len(jobs),
            "completed": len(completed),
            "failed": len(failed),
            "rejected": len(rejected),
            "awaiting_approval": len(awaiting),
            "total_published": total_published,
            "unique_urls": len(total_urls),
            "is_running": self._is_running,
        }


def get_video_publish_pipeline(event_bus=None) -> VideoPublishPipeline:
    """Get or create the VideoPublishPipeline singleton."""
    return VideoPublishPipeline.get_instance(event_bus=event_bus)

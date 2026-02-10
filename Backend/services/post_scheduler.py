"""
Post Scheduler Service
Background worker that publishes scheduled posts at their scheduled time.

Uses BackgroundPublisher to replicate the same verified flow as the frontend:
1. Media verification
2. Analysis/caption retrieval
3. Account verification
4. Full publish (Google Drive → Blotato → Platform)
5. URL polling
6. Posted content record storage

EVENT-DRIVEN (Phase 3):
- Emits scheduler.tick on each check cycle
- Emits schedule.due for posts ready to publish
- Emits publish.* events through the publish pipeline
- All events tracked by WorkflowManager for visibility
"""
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID
from sqlalchemy import create_engine, text
from loguru import logger
import httpx

# Event Bus integration
from services.event_bus import EventBus, Topics


def _sanitize_for_json(obj):
    """Recursively convert UUIDs and other non-JSON types to strings."""
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(item) for item in obj]
    return obj

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


class PostScheduler:
    """
    Background scheduler that:
    1. Periodically checks for posts due to be published
    2. Uses BackgroundPublisher for verified publish flow (same as frontend)
    3. Updates status and handles retries
    4. Polls for platform URLs and stores for analytics
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.blotato_api_key = os.getenv("BLOTATO_API_KEY")
        self.is_running = False
        self.check_interval = 60  # Check every 60 seconds
        self.max_retries = 3
        self.retry_delay_minutes = 5
        self._task: Optional[asyncio.Task] = None
        self._background_publisher = None
        self._check_count = 0

        # Event Bus integration
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("post-scheduler")

        # Deduplication guard
        from services.deduplication_guard import get_deduplication_guard
        self.dedup_guard = get_deduplication_guard()

        # Sleep mode integration
        self._sleep_service = None
        self._scheduled_wake_triggers: Dict[str, str] = {}  # post_id -> wake_trigger_id
    
    @property
    def background_publisher(self):
        """Lazy load background publisher"""
        if self._background_publisher is None:
            from services.background_publisher import get_background_publisher
            self._background_publisher = get_background_publisher()
        return self._background_publisher

    @property
    def sleep_service(self):
        """Lazy load sleep mode service"""
        if self._sleep_service is None:
            try:
                from services.sleep_mode_service import SleepModeService
                self._sleep_service = SleepModeService.get_instance()
            except Exception as e:
                logger.warning(f"Sleep mode service not available: {e}")
                self._sleep_service = None
        return self._sleep_service
        
    # =========================================================================
    # SCHEDULER CONTROL
    # =========================================================================
    
    async def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("📅 Post scheduler started - checking every 60 seconds")
        
        # Emit scheduler started event
        await self.event_bus.publish(
            Topics.SCHEDULER_STARTED,
            {
                "check_interval": self.check_interval,
                "max_retries": self.max_retries,
                "blotato_configured": bool(self.blotato_api_key)
            }
        )
        
    async def stop(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("📅 Post scheduler stopped")
        
        # Emit scheduler stopped event
        await self.event_bus.publish(
            Topics.SCHEDULER_STOPPED,
            {
                "total_checks": self._check_count,
                "stopped_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
    async def _run_loop(self):
        """Main scheduler loop with comprehensive logging and event emissions"""
        while self.is_running:
            self._check_count += 1
            now = datetime.now(timezone.utc)
            
            # Log scheduler status every loop
            logger.info("=" * 60)
            logger.info(f"[Scheduler] 🕐 Check #{self._check_count} at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            try:
                # Get counts before processing
                due_posts = self._get_due_posts(now)
                upcoming = self._get_upcoming_posts(5)
                
                logger.info(f"[Scheduler] 📊 Due now: {len(due_posts)} | Upcoming: {len(upcoming)}")
                
                # Emit scheduler tick event
                await self.event_bus.publish(
                    Topics.SCHEDULER_TICK,
                    {
                        "check_number": self._check_count,
                        "due_count": len(due_posts),
                        "upcoming_count": len(upcoming),
                        "timestamp": now.isoformat()
                    }
                )
                
                if due_posts:
                    logger.info(f"[Scheduler] 🚀 Processing {len(due_posts)} due posts...")
                    result = await self.process_due_posts()
                    logger.info(f"[Scheduler] ✅ Result: {result['success']} success, {result['failed']} failed")
                else:
                    logger.info("[Scheduler] 💤 No posts due right now")
                
                # Show next upcoming posts
                if upcoming:
                    logger.info("[Scheduler] ⏳ Next up:")
                    for p in upcoming[:3]:
                        scheduled = datetime.fromisoformat(str(p['scheduled_at']).replace('Z', '+00:00')) if p.get('scheduled_at') else now
                        diff = (scheduled - now).total_seconds()
                        mins = int(diff // 60)
                        secs = int(diff % 60)
                        logger.info(f"   • {p.get('title', 'Untitled')[:25]} | {p.get('platform')} | T-{mins}m {secs}s")

                # Schedule wake triggers for upcoming posts (5 minutes before)
                await self._schedule_wake_triggers_for_upcoming_posts(upcoming)

            except Exception as e:
                logger.error(f"[Scheduler] ❌ Error: {e}")
            
            logger.info(f"[Scheduler] 💤 Next check in {self.check_interval}s...")
            logger.info("=" * 60)
            
            await asyncio.sleep(self.check_interval)
    
    # =========================================================================
    # POST PROCESSING
    # =========================================================================
    
    async def process_due_posts(self) -> Dict[str, int]:
        """Find and publish all posts that are due"""
        now = datetime.now(timezone.utc)
        
        # Get posts due for publishing
        due_posts = self._get_due_posts(now)
        
        if not due_posts:
            return {"processed": 0, "success": 0, "failed": 0}
        
        logger.info(f"📤 Processing {len(due_posts)} due posts")
        
        success_count = 0
        failed_count = 0
        
        for post in due_posts:
            try:
                result = await self._publish_post(post)
                if result["success"]:
                    success_count += 1
                    self._mark_post_published(post["id"], result)
                else:
                    failed_count += 1
                    self._handle_post_failure(post, result.get("error", "Unknown error"))
            except Exception as e:
                failed_count += 1
                self._handle_post_failure(post, str(e))
                logger.error(f"Failed to publish post {post['id']}: {e}")
        
        logger.info(f"✅ Published: {success_count}, ❌ Failed: {failed_count}")
        
        return {
            "processed": len(due_posts),
            "success": success_count,
            "failed": failed_count
        }
    
    def _get_due_posts(self, now: datetime) -> List[Dict]:
        """Get all posts that are scheduled and due for publishing
        
        Uses atomic status update to prevent race conditions where multiple
        workers try to process the same post.
        """
        with self.engine.connect() as conn:
            # Atomically update status to 'publishing' and return those posts
            # This prevents multiple workers from processing the same post
            result = conn.execute(text("""
                UPDATE scheduled_posts
                SET status = 'publishing',
                    updated_at = NOW()
                WHERE id IN (
                    SELECT id
                    FROM scheduled_posts
                    WHERE status = 'scheduled'
                      AND scheduled_time <= :now
                    ORDER BY scheduled_time ASC
                    LIMIT 50
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING 
                    id, clip_id, content_variant_id, platform, 
                    platform_account_id, scheduled_time, status,
                    caption, title, hashtags, recommendation_reasoning,
                    media_path, blotato_account_id, account_username
            """), {"now": now})
            
            posts = []
            for row in result.fetchall():
                posts.append({
                    "id": row[0],
                    "content_id": row[1] or row[2],  # Use clip_id or content_variant_id
                    "platform": row[3],
                    "account_id": row[4] or row[12],  # platform_account_id or blotato_account_id
                    "scheduled_at": row[5],
                    "status": row[6],
                    "caption": row[7],           # Caption from scheduled_posts
                    "title": row[8],             # Title from scheduled_posts
                    "hashtags": row[9],          # Hashtags from scheduled_posts
                    "account_username": row[13] or (row[10] or "").replace("account: ", ""),
                    "media_path": row[11],       # Local file path for video
                    "blotato_account_id": row[12],  # Blotato account ID
                })
            
            return posts
    
    def _get_upcoming_posts(self, limit: int = 5) -> List[Dict]:
        """Get upcoming scheduled posts (not yet due)"""
        now = datetime.now(timezone.utc)
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, platform, scheduled_time, COALESCE(title, 'Untitled') as title
                FROM scheduled_posts
                WHERE status = 'scheduled'
                  AND scheduled_time > :now
                ORDER BY scheduled_time ASC
                LIMIT :limit
            """), {"now": now, "limit": limit})
            
            posts = []
            for row in result.fetchall():
                posts.append({
                    "id": row[0],
                    "platform": row[1],
                    "scheduled_at": row[2],
                    "title": row[3],
                })
            return posts

    async def _schedule_wake_triggers_for_upcoming_posts(self, upcoming_posts: List[Dict]) -> None:
        """
        Schedule wake triggers for upcoming posts (5 minutes before scheduled time)

        Args:
            upcoming_posts: List of upcoming scheduled posts
        """
        if not self.sleep_service:
            return  # Sleep mode not available

        from services.sleep_mode_service import WakeTriggerType

        now = datetime.now(timezone.utc)

        for post in upcoming_posts:
            post_id = str(post.get('id'))
            scheduled_at = post.get('scheduled_at')

            if not scheduled_at:
                continue

            # Parse scheduled time
            if isinstance(scheduled_at, str):
                scheduled_time = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            else:
                scheduled_time = scheduled_at

            # Calculate wake time (5 minutes before post)
            wake_time = scheduled_time - timedelta(minutes=5)

            # Only schedule if wake time is in the future
            if wake_time <= now:
                continue

            # Check if we already have a wake trigger for this post
            if post_id in self._scheduled_wake_triggers:
                # Already scheduled, skip
                continue

            # Schedule wake trigger
            try:
                trigger_id = self.sleep_service.schedule_wake(
                    wake_time=wake_time,
                    trigger_type=WakeTriggerType.SCHEDULED_POST,
                    metadata={
                        "post_id": post_id,
                        "platform": post.get('platform'),
                        "scheduled_time": scheduled_time.isoformat()
                    }
                )

                # Track the trigger
                self._scheduled_wake_triggers[post_id] = trigger_id

                logger.debug(
                    f"⏰ Scheduled wake for post {post_id[:8]}... at "
                    f"{wake_time.strftime('%H:%M:%S UTC')} (5min before post)"
                )

            except Exception as e:
                logger.warning(f"Failed to schedule wake for post {post_id}: {e}")

    # =========================================================================
    # PUBLISH LOGIC
    # =========================================================================
    
    async def _publish_post(self, post: Dict) -> Dict[str, Any]:
        """
        Publish a single scheduled post using BackgroundPublisher.
        
        This uses the SAME verified flow as the frontend:
        1. Media verification (with file existence check)
        2. Analysis/caption retrieval  
        3. Account verification
        4. Full publish (GDrive → Blotato → Platform)
        5. URL polling
        
        Emits events throughout the process for workflow tracking.
        
        DEDUPLICATION SAFEGUARDS:
        - Checks if already posted before publishing
        - Uses idempotency keys to prevent duplicate API calls
        - Locks post during publishing to prevent concurrent attempts
        
        BUG FIX: Media deletion handling
        - Verifies media file exists before publishing
        - Handles gracefully if file was deleted after scheduling
        """
        # Create correlation ID for this publish workflow
        correlation_id = str(uuid4())
        post_id = str(post["id"])
        media_id = str(post.get("content_id")) if post.get("content_id") else None
        platform = post.get("platform")
        account_id = str(post.get("account_id")) if post.get("account_id") else None
        
        # BUG FIX: Verify media file still exists (might have been deleted after scheduling)
        # This is a pre-check; BackgroundPublisher will also verify during publish
        media_path = post.get("media_path")
        if media_path:
            # Direct file path available (e.g. Sora videos) - verify on disk
            from pathlib import Path
            if not Path(media_path).exists():
                logger.error(f"❌ Media file not found on disk: {media_path}")
                return {"success": False, "error": f"File not found: {media_path}", "file_deleted": True}
            logger.info(f"✅ Media file verified on disk: {Path(media_path).name}")
        elif media_id:
            try:
                # Use BackgroundPublisher to verify media via DB (reuses same logic)
                publisher = self.background_publisher
                media_check = await publisher.verify_media(str(media_id))
                if not media_check.get("valid"):
                    error = media_check.get("error", "Media verification failed")
                    if media_check.get("file_deleted"):
                        logger.error(f"❌ Media file deleted after scheduling: {error}")
                        return {
                            "success": False,
                            "error": error,
                            "file_deleted": True
                        }
                    else:
                        logger.warning(f"⚠️ Media verification issue: {error}")
                        # Continue - might be transient issue
            except Exception as e:
                logger.warning(f"Could not verify media file existence: {e}")
                # Continue anyway - BackgroundPublisher will verify again during publish
        
        # SAFEGUARD 1: Check if already posted
        if media_id and self.dedup_guard.is_already_posted(media_id, platform, account_id):
            logger.warning(f"⚠️ DUPLICATE PREVENTED: {media_id} already posted to {platform}")
            return {
                "success": False,
                "error": "Content already posted to this platform",
                "duplicate_prevented": True
            }
        
        # SAFEGUARD 2: Try to acquire publish lock
        if not self.dedup_guard.prevent_concurrent_publish(post_id):
            logger.warning(f"⚠️ CONCURRENT PUBLISH PREVENTED: {post_id} already being processed")
            return {
                "success": False,
                "error": "Post already being published by another process",
                "concurrent_prevented": True
            }
        
        # SAFEGUARD 3: Check idempotency
        idempotency_key = self.dedup_guard.generate_idempotency_key(
            media_id,
            platform,
            account_id,
            post.get("scheduled_at")
        )
        
        existing = self.dedup_guard.check_idempotency(idempotency_key)
        if existing:
            if existing["status"] == "completed":
                logger.warning(f"⚠️ IDEMPOTENT: {idempotency_key} already completed")
                return {
                    "success": True,
                    "platform_post_id": existing["platform_post_id"],
                    "platform_url": existing["platform_url"],
                    "idempotent": True
                }
            elif existing["status"] == "in_progress":
                logger.warning(f"⚠️ IN PROGRESS: {idempotency_key} currently publishing")
                return {
                    "success": False,
                    "error": "Publish already in progress",
                    "in_progress": True
                }
        
        # Record publish attempt
        self.dedup_guard.record_publish_attempt(
            idempotency_key,
            post_id,
            media_id,
            platform,
            account_id,
            {"correlation_id": correlation_id}
        )
        
        # Emit schedule.due event
        await self.event_bus.publish(
            Topics.SCHEDULE_DUE,
            {
                "post_id": post_id,
                "media_id": media_id,
                "platform": platform,
                "account_id": account_id,
                "title": post.get("title"),
                "scheduled_at": str(post.get("scheduled_at")) if post.get("scheduled_at") else None
            },
            correlation_id=correlation_id
        )
        
        # Emit publish.started event
        await self.event_bus.publish(
            Topics.PUBLISH_STARTED,
            {
                "post_id": post_id,
                "media_id": media_id,
                "platform": platform,
                "step": "initializing"
            },
            correlation_id=correlation_id
        )
        
        # Check if Blotato is configured
        if not self.blotato_api_key:
            logger.warning("Blotato API key not configured, simulating publish")
            result = await self._simulate_publish(post)
            
            # Emit publish.completed event
            await self.event_bus.publish(
                Topics.PUBLISH_COMPLETED,
                {
                    "post_id": post_id,
                    "media_id": media_id,
                    "platform": platform,
                    "platform_url": result.get("platform_url"),
                    "simulated": True
                },
                correlation_id=correlation_id
            )
            
            # Record success in idempotency tracker
            self.dedup_guard.record_publish_success(
                idempotency_key,
                result.get("platform_post_id"),
                result.get("platform_url")
            )
            
            return result
        
        try:
            from services.background_publisher import PublishRequest, PublishStatus
            
            # Emit uploading event
            await self.event_bus.publish(
                Topics.PUBLISH_UPLOADING,
                {"post_id": post_id, "media_id": media_id, "target": "cloud_storage"},
                correlation_id=correlation_id
            )
            
            # Build publish request from scheduled post data
            request = PublishRequest(
                media_id=str(post["content_id"]) if post.get("content_id") else post_id,
                blotato_account_id=str(post["account_id"]),
                platform=post["platform"],
                username=post.get("account_username", "").replace("account: ", "") if post.get("account_username") else "",
                caption=post.get("caption"),
                title=post.get("title"),
                hashtags=self._parse_hashtags(post.get("hashtags")),
                poll_for_url=True,
                cleanup_storage=True,
                file_path_override=post.get("media_path"),  # Direct path for Sora/local videos
                caption_style=post.get("caption_style"),  # Auto-subtitle style
            )
            
            logger.info(f"📤 Publishing scheduled post {post['id']} via BackgroundPublisher...")
            
            # Use BackgroundPublisher for the full verified flow
            result = await self.background_publisher.publish(request)
            
            if result.success:
                # Emit publish.completed event - sanitize steps to avoid UUID serialization errors
                await self.event_bus.publish(
                    Topics.PUBLISH_COMPLETED,
                    {
                        "post_id": post_id,
                        "media_id": media_id,
                        "platform": platform,
                        "platform_url": result.platform_url,
                        "submission_id": result.post_submission_id,
                        "account_id": account_id,
                        "steps": _sanitize_for_json(result.steps)
                    },
                    correlation_id=correlation_id
                )
                
                # Record success in idempotency tracker
                self.dedup_guard.record_publish_success(
                    idempotency_key,
                    result.post_submission_id,
                    result.platform_url
                )
                
                return {
                    "success": True,
                    "platform_post_id": result.post_submission_id,
                    "platform_url": result.platform_url,
                    "verification": _sanitize_for_json(result.verification),
                    "steps": _sanitize_for_json(result.steps),
                    "correlation_id": correlation_id
                }
            else:
                # Emit publish.failed event - sanitize steps
                await self.event_bus.publish(
                    Topics.PUBLISH_FAILED,
                    {
                        "post_id": post_id,
                        "media_id": media_id,
                        "platform": platform,
                        "error": result.error or "Publish failed",
                        "account_id": account_id,
                        "steps": _sanitize_for_json(result.steps)
                    },
                    correlation_id=correlation_id
                )
                
                # Record failure in idempotency tracker
                self.dedup_guard.record_publish_failure(
                    idempotency_key,
                    result.error or "Publish failed"
                )
                
                return {
                    "success": False,
                    "error": result.error or "Publish failed",
                    "verification": _sanitize_for_json(result.verification),
                    "steps": _sanitize_for_json(result.steps),
                    "correlation_id": correlation_id
                }
                
        except Exception as e:
            logger.error(f"Scheduler publish error: {e}")
            
            # Record failure in idempotency tracker
            self.dedup_guard.record_publish_failure(idempotency_key, str(e))
            
            # Emit publish.failed event
            await self.event_bus.publish(
                Topics.PUBLISH_FAILED,
                {
                    "post_id": post_id,
                    "media_id": media_id,
                    "platform": platform,
                    "account_id": account_id,
                    "error": str(e)
                },
                correlation_id=correlation_id
            )
            
            return {"success": False, "error": str(e), "correlation_id": correlation_id}
    
    def _parse_hashtags(self, hashtags) -> List[str]:
        """Parse hashtags from various formats"""
        if not hashtags:
            return []
        if isinstance(hashtags, list):
            return hashtags
        if isinstance(hashtags, str):
            try:
                import json
                return json.loads(hashtags)
            except Exception:
                return [h.strip() for h in hashtags.split(",") if h.strip()]
        return []
    
    async def _simulate_publish(self, post: Dict) -> Dict[str, Any]:
        """Simulate publishing for testing when Blotato is not configured"""
        await asyncio.sleep(0.5)  # Simulate API latency
        
        return {
            "success": True,
            "platform_post_id": f"sim_{post['id']}_{datetime.now().timestamp()}",
            "platform_url": f"https://{post['platform']}.com/simulated/{post['id']}",
            "simulated": True
        }
    
    # =========================================================================
    # STATUS UPDATES
    # =========================================================================
    
    def _mark_post_published(self, post_id, result: Dict):
        """Mark a post as successfully published"""
        try:
            with self.engine.connect() as conn:
                # Convert post_id to string for UUID compatibility
                conn.execute(text("""
                    UPDATE scheduled_posts
                    SET 
                        status = 'posted',
                        platform_post_id = :platform_post_id,
                        platform_url = :platform_url,
                        published_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": str(post_id),
                    "platform_post_id": result.get("platform_post_id") or result.get("post_submission_id"),
                    "platform_url": result.get("platform_url")
                })
                conn.commit()
                logger.info(f"✅ Updated scheduled_posts status to 'posted' for {post_id}")
        except Exception as e:
            logger.error(f"❌ Failed to mark post {post_id} as published: {e}")
            
        logger.info(f"✅ Post {post_id} published: {result.get('platform_url')}")
        
        # Also create entry in posted_content for tracking
        self._create_posted_content_record(post_id, result)
    
    def _create_posted_content_record(self, post_id, result: Dict):
        """Create a record in posted_content table for analytics tracking"""
        with self.engine.connect() as conn:
            # Get the original post data - use correct column name platform_account_id
            post_data = conn.execute(text("""
                SELECT platform, platform_account_id, recommendation_reasoning, caption, hashtags
                FROM scheduled_posts WHERE id = :id
            """), {"id": str(post_id)}).fetchone()
            
            if post_data:
                # Handle hashtags - convert to proper format for JSONB column
                hashtags_raw = post_data[4]
                # Convert hashtags to PostgreSQL text[] format
                if hashtags_raw is None:
                    hashtags_array = []
                elif isinstance(hashtags_raw, str):
                    # Try to parse as JSON if it's a string
                    try:
                        import json
                        hashtags_array = json.loads(hashtags_raw) if hashtags_raw.startswith('[') else [hashtags_raw]
                    except:
                        hashtags_array = [hashtags_raw] if hashtags_raw else []
                elif isinstance(hashtags_raw, list):
                    hashtags_array = hashtags_raw
                else:
                    hashtags_array = []
                
                # Format as PostgreSQL array literal: {"tag1", "tag2"}
                pg_array = '{' + ','.join(f'"{h}"' for h in hashtags_array) + '}'
                
                conn.execute(text("""
                    INSERT INTO posted_content 
                    (platform, platform_post_id, platform_url, 
                     caption, posted_at)
                    VALUES 
                    (:platform, :platform_post_id, :platform_url,
                     :caption, NOW())
                """), {
                    "platform": post_data[0],
                    "platform_post_id": result.get("platform_post_id"),
                    "platform_url": result.get("platform_url"),
                    "caption": post_data[3],
                })
                conn.commit()
    
    def _handle_post_failure(self, post: Dict, error: str):
        """Handle a failed publish attempt"""
        post_id = str(post["id"])  # Convert UUID to string
        with self.engine.connect() as conn:
            # Get current retry count
            result = conn.execute(text("""
                SELECT COALESCE(retry_count, 0) as retry_count 
                FROM scheduled_posts WHERE id = :id
            """), {"id": post_id}).fetchone()
            
            current_retries = result[0] if result else 0
            
            if current_retries < self.max_retries:
                # Schedule retry
                next_retry = datetime.now(timezone.utc) + timedelta(minutes=self.retry_delay_minutes * (current_retries + 1))
                conn.execute(text("""
                    UPDATE scheduled_posts
                    SET 
                        retry_count = :retry_count,
                        next_retry_at = :next_retry,
                        last_error = :error,
                        error_message = :error,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": post_id,
                    "retry_count": current_retries + 1,
                    "next_retry": next_retry,
                    "error": error
                })
                conn.commit()
                logger.warning(f"⚠️ Post {post_id} failed, retry {current_retries + 1}/{self.max_retries} at {next_retry}")
                
                # Emit PUBLISH_RETRYING event
                try:
                    import asyncio
                    asyncio.create_task(self.event_bus.publish(Topics.PUBLISH_RETRYING, {
                        "post_id": str(post["id"]),
                        "media_id": post.get("content_id"),
                        "platform": post.get("platform"),
                        "retry_count": current_retries + 1,
                        "max_retries": self.max_retries,
                        "next_retry_at": next_retry.isoformat(),
                        "error": error,
                    }))
                    logger.info(f"[PubSub] Emitted PUBLISH_RETRYING for {post['id']}")
                except Exception as e:
                    logger.warning(f"[PubSub] Failed to emit PUBLISH_RETRYING: {e}")
            else:
                # Max retries reached, mark as failed
                conn.execute(text("""
                    UPDATE scheduled_posts
                    SET 
                        status = 'failed',
                        error_message = :error,
                        last_error = :error,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": post_id,
                    "error": f"Max retries exceeded. Last error: {error}"
                })
                conn.commit()
                logger.error(f"❌ Post {post_id} failed permanently after {self.max_retries} retries")
    
    # =========================================================================
    # STATUS & STATS
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics"""
        with self.engine.connect() as conn:
            # Get counts by status
            status_counts = conn.execute(text("""
                SELECT status, COUNT(*) as count
                FROM scheduled_posts
                GROUP BY status
            """)).fetchall()
            
            # Get upcoming posts
            upcoming = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts
                WHERE status = 'scheduled'
                  AND scheduled_time > NOW()
            """)).scalar() or 0
            
            # Get posts due now
            due_now = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts
                WHERE status = 'scheduled'
                  AND scheduled_time <= NOW()
            """)).scalar() or 0
            
            # Get recent failures
            recent_failures = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts
                WHERE status = 'failed'
                  AND updated_at > NOW() - INTERVAL '24 hours'
            """)).scalar() or 0
        
        return {
            "is_running": self.is_running,
            "check_interval_seconds": self.check_interval,
            "max_retries": self.max_retries,
            "blotato_configured": bool(self.blotato_api_key),
            "status_counts": {row[0]: row[1] for row in status_counts},
            "upcoming_posts": upcoming,
            "due_now": due_now,
            "recent_failures_24h": recent_failures
        }
    
    def get_queue(self, limit: int = 20) -> List[Dict]:
        """Get the upcoming post queue"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    id, COALESCE(title, 'Scheduled Post') as title, platform, COALESCE(account_username, platform_account_id::text) as account_username, 
                    scheduled_time, status, retry_count, last_error
                FROM scheduled_posts
                WHERE status IN ('scheduled', 'pending', 'failed')
                ORDER BY 
                    CASE WHEN status = 'failed' THEN 0 ELSE 1 END,
                    scheduled_time ASC
                LIMIT :limit
            """), {"limit": limit})
            
            queue = []
            for row in result.fetchall():
                queue.append({
                    "id": str(row[0]),
                    "title": row[1],
                    "platform": row[2],
                    "account_username": row[3],
                    "scheduled_at": str(row[4]) if row[4] else None,
                    "status": row[5],
                    "retry_count": row[6] or 0,
                    "last_error": row[7]
                })
            
            return queue


# Global scheduler instance
_scheduler: Optional[PostScheduler] = None


def get_scheduler() -> PostScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = PostScheduler()
    return _scheduler


async def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the global scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()

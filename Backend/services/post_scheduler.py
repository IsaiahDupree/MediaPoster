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
from uuid import uuid4
from sqlalchemy import create_engine, text
from loguru import logger
import httpx

# Event Bus integration
from services.event_bus import EventBus, Topics

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
    
    @property
    def background_publisher(self):
        """Lazy load background publisher"""
        if self._background_publisher is None:
            from services.background_publisher import get_background_publisher
            self._background_publisher = get_background_publisher()
        return self._background_publisher
        
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
        """Get all posts that are scheduled and due for publishing"""
        with self.engine.connect() as conn:
            # Fetch scheduled posts due for publishing
            # Uses actual column names from scheduled_posts table
            result = conn.execute(text("""
                SELECT 
                    id, clip_id, content_variant_id, platform, 
                    platform_account_id, scheduled_time, status
                FROM scheduled_posts
                WHERE status = 'scheduled'
                  AND scheduled_time <= :now
                ORDER BY scheduled_time ASC
                LIMIT 50
            """), {"now": now})
            
            posts = []
            for row in result.fetchall():
                posts.append({
                    "id": row[0],
                    "content_id": row[1] or row[2],  # Use clip_id or content_variant_id
                    "platform": row[3],
                    "account_id": row[4],
                    "scheduled_at": row[5],
                    "status": row[6],
                })
            
            return posts
    
    def _get_upcoming_posts(self, limit: int = 5) -> List[Dict]:
        """Get upcoming scheduled posts (not yet due)"""
        now = datetime.now(timezone.utc)
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, platform, scheduled_time
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
                })
            return posts
    
    # =========================================================================
    # PUBLISH LOGIC
    # =========================================================================
    
    async def _publish_post(self, post: Dict) -> Dict[str, Any]:
        """
        Publish a single scheduled post using BackgroundPublisher.
        
        This uses the SAME verified flow as the frontend:
        1. Media verification
        2. Analysis/caption retrieval  
        3. Account verification
        4. Full publish (GDrive → Blotato → Platform)
        5. URL polling
        
        Emits events throughout the process for workflow tracking.
        """
        # Create correlation ID for this publish workflow
        correlation_id = str(uuid4())
        post_id = str(post["id"])
        media_id = post.get("content_id")
        platform = post.get("platform")
        
        # Emit schedule.due event
        await self.event_bus.publish(
            Topics.SCHEDULE_DUE,
            {
                "post_id": post_id,
                "media_id": media_id,
                "platform": platform,
                "account_id": post.get("account_id"),
                "title": post.get("title"),
                "scheduled_at": str(post.get("scheduled_at"))
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
            
            # Emit completion event for simulated publish
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
                media_id=post["content_id"],
                blotato_account_id=str(post["account_id"]),
                platform=post["platform"],
                username=post.get("account_username", ""),
                caption=post.get("caption"),
                title=post.get("title"),
                hashtags=self._parse_hashtags(post.get("hashtags")),
                poll_for_url=True,
                cleanup_storage=True,
            )
            
            logger.info(f"📤 Publishing scheduled post {post['id']} via BackgroundPublisher...")
            
            # Use BackgroundPublisher for the full verified flow
            result = await self.background_publisher.publish(request)
            
            if result.success:
                # Emit publish.completed event
                await self.event_bus.publish(
                    Topics.PUBLISH_COMPLETED,
                    {
                        "post_id": post_id,
                        "media_id": media_id,
                        "platform": platform,
                        "platform_url": result.platform_url,
                        "submission_id": result.post_submission_id,
                        "steps": result.steps
                    },
                    correlation_id=correlation_id
                )
                
                return {
                    "success": True,
                    "platform_post_id": result.post_submission_id,
                    "platform_url": result.platform_url,
                    "verification": result.verification,
                    "steps": result.steps,
                    "correlation_id": correlation_id
                }
            else:
                # Emit publish.failed event
                await self.event_bus.publish(
                    Topics.PUBLISH_FAILED,
                    {
                        "post_id": post_id,
                        "media_id": media_id,
                        "platform": platform,
                        "error": result.error or "Publish failed",
                        "steps": result.steps
                    },
                    correlation_id=correlation_id
                )
                
                return {
                    "success": False,
                    "error": result.error or "Publish failed",
                    "verification": result.verification,
                    "steps": result.steps,
                    "correlation_id": correlation_id
                }
                
        except Exception as e:
            logger.error(f"Scheduler publish error: {e}")
            
            # Emit publish.failed event
            await self.event_bus.publish(
                Topics.PUBLISH_FAILED,
                {
                    "post_id": post_id,
                    "media_id": media_id,
                    "platform": platform,
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
            except:
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
    
    def _mark_post_published(self, post_id: int, result: Dict):
        """Mark a post as successfully published"""
        with self.engine.connect() as conn:
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
                "id": post_id,
                "platform_post_id": result.get("platform_post_id"),
                "platform_url": result.get("platform_url")
            })
            conn.commit()
            
        logger.info(f"✅ Post {post_id} published: {result.get('platform_url')}")
        
        # Also create entry in posted_content for tracking
        self._create_posted_content_record(post_id, result)
    
    def _create_posted_content_record(self, post_id: int, result: Dict):
        """Create a record in posted_content table for analytics tracking"""
        with self.engine.connect() as conn:
            # Get the original post data
            post_data = conn.execute(text("""
                SELECT platform, account_id, account_username, caption, hashtags
                FROM scheduled_posts WHERE id = :id
            """), {"id": post_id}).fetchone()
            
            if post_data:
                # Handle hashtags - convert to proper format for JSONB column
                hashtags_raw = post_data[4]
                if hashtags_raw is None:
                    hashtags_json = '[]'
                elif isinstance(hashtags_raw, str):
                    hashtags_json = hashtags_raw
                elif isinstance(hashtags_raw, list):
                    import json
                    hashtags_json = json.dumps(hashtags_raw)
                else:
                    hashtags_json = '[]'
                
                conn.execute(text("""
                    INSERT INTO posted_content 
                    (platform, platform_post_id, platform_url, account_id, 
                     account_username, caption, hashtags, status, posted_at)
                    VALUES 
                    (:platform, :platform_post_id, :platform_url, :account_id,
                     :account_username, :caption, :hashtags::jsonb, 'published', NOW())
                """), {
                    "platform": post_data[0],
                    "platform_post_id": result.get("platform_post_id"),
                    "platform_url": result.get("platform_url"),
                    "account_id": post_data[1],
                    "account_username": post_data[2],
                    "caption": post_data[3],
                    "hashtags": hashtags_json
                })
                conn.commit()
    
    def _handle_post_failure(self, post: Dict, error: str):
        """Handle a failed publish attempt"""
        with self.engine.connect() as conn:
            # Get current retry count
            result = conn.execute(text("""
                SELECT COALESCE(retry_count, 0) as retry_count 
                FROM scheduled_posts WHERE id = :id
            """), {"id": post["id"]}).fetchone()
            
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
                    "id": post["id"],
                    "retry_count": current_retries + 1,
                    "next_retry": next_retry,
                    "error": error
                })
                logger.warning(f"⚠️ Post {post['id']} failed, retry {current_retries + 1}/{self.max_retries} at {next_retry}")
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
                    "id": post["id"],
                    "error": f"Max retries exceeded. Last error: {error}"
                })
                logger.error(f"❌ Post {post['id']} failed permanently after {self.max_retries} retries")
            
            conn.commit()
    
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
                  AND scheduled_at > NOW()
            """)).scalar() or 0
            
            # Get posts due now
            due_now = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts
                WHERE status = 'scheduled'
                  AND scheduled_at <= NOW()
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
                    id, title, platform, account_username, 
                    scheduled_at, status, retry_count, last_error
                FROM scheduled_posts
                WHERE status IN ('scheduled', 'failed')
                ORDER BY 
                    CASE WHEN status = 'failed' THEN 0 ELSE 1 END,
                    scheduled_at ASC
                LIMIT :limit
            """), {"limit": limit})
            
            queue = []
            for row in result.fetchall():
                queue.append({
                    "id": row[0],
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

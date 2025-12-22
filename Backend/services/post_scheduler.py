"""
Post Scheduler Service
Background worker that publishes scheduled posts at their scheduled time
"""
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from loguru import logger
import httpx

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


class PostScheduler:
    """
    Background scheduler that:
    1. Periodically checks for posts due to be published
    2. Publishes via Blotato API
    3. Updates status and handles retries
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.blotato_api_key = os.getenv("BLOTATO_API_KEY")
        self.blotato_base_url = "https://api.blotato.com/v2"
        self.is_running = False
        self.check_interval = 60  # Check every 60 seconds
        self.max_retries = 3
        self.retry_delay_minutes = 5
        self._task: Optional[asyncio.Task] = None
        
    # =========================================================================
    # SCHEDULER CONTROL
    # =========================================================================
    
    def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("📅 Post scheduler started")
        
    def stop(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("📅 Post scheduler stopped")
        
    async def _run_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                await self.process_due_posts()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
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
            # Check both scheduled_posts table (new) and the schedule table
            result = conn.execute(text("""
                SELECT 
                    id, content_id, title, caption, platform, 
                    account_id, account_username, scheduled_at,
                    thumbnail_url, post_type, hashtags
                FROM scheduled_posts
                WHERE status = 'scheduled'
                  AND scheduled_at <= :now
                ORDER BY scheduled_at ASC
                LIMIT 50
            """), {"now": now})
            
            posts = []
            for row in result.fetchall():
                posts.append({
                    "id": row[0],
                    "content_id": row[1],
                    "title": row[2],
                    "caption": row[3],
                    "platform": row[4],
                    "account_id": row[5],
                    "account_username": row[6],
                    "scheduled_at": row[7],
                    "thumbnail_url": row[8],
                    "post_type": row[9],
                    "hashtags": row[10],
                })
            
            return posts
    
    # =========================================================================
    # PUBLISHING
    # =========================================================================
    
    async def _publish_post(self, post: Dict) -> Dict[str, Any]:
        """Publish a single post via Blotato API"""
        
        # Check if Blotato is configured
        if not self.blotato_api_key:
            logger.warning("Blotato API key not configured, simulating publish")
            return await self._simulate_publish(post)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare the post data for Blotato
                payload = {
                    "platform": post["platform"],
                    "caption": post["caption"] or "",
                    "account_id": post["account_id"],
                }
                
                # Add media URL if available
                if post.get("thumbnail_url"):
                    payload["media_url"] = post["thumbnail_url"]
                
                # Add hashtags
                if post.get("hashtags"):
                    if isinstance(post["hashtags"], list):
                        payload["hashtags"] = post["hashtags"]
                    elif isinstance(post["hashtags"], str):
                        payload["hashtags"] = [h.strip() for h in post["hashtags"].split(",")]
                
                response = await client.post(
                    f"{self.blotato_base_url}/posts",
                    headers={
                        "Authorization": f"Bearer {self.blotato_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    data = response.json()
                    return {
                        "success": True,
                        "platform_post_id": data.get("post_id") or data.get("id"),
                        "platform_url": data.get("url") or data.get("public_url"),
                        "response": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Blotato API error: {response.status_code} - {response.text}"
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "Blotato API timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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
                conn.execute(text("""
                    INSERT INTO posted_content 
                    (platform, platform_post_id, platform_url, account_id, 
                     account_username, caption, hashtags, status, posted_at)
                    VALUES 
                    (:platform, :platform_post_id, :platform_url, :account_id,
                     :account_username, :caption, :hashtags, 'published', NOW())
                """), {
                    "platform": post_data[0],
                    "platform_post_id": result.get("platform_post_id"),
                    "platform_url": result.get("platform_url"),
                    "account_id": post_data[1],
                    "account_username": post_data[2],
                    "caption": post_data[3],
                    "hashtags": post_data[4] if post_data[4] else "[]"
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

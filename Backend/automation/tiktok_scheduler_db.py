"""
TikTok Scheduler (Database Version) - Check-back periods with PostgreSQL storage.

Uses the social_media_posts and social_media_post_analytics tables.

Usage:
    from automation.tiktok_scheduler_db import TikTokSchedulerDB
    
    scheduler = TikTokSchedulerDB(db_url="postgresql://...")
    await scheduler.track_post("https://tiktok.com/@user/video/123")
    await scheduler.run_pending_checks()
"""

import os
import json
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

# Try to import asyncpg, fall back to sync version if not available
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    print("Warning: asyncpg not installed. Using sync mode.")


@dataclass
class CheckBackSchedule:
    """Default check-back schedule."""
    offset_hours: int
    name: str


DEFAULT_SCHEDULE = [
    CheckBackSchedule(1, "1 hour"),
    CheckBackSchedule(6, "6 hours"),
    CheckBackSchedule(12, "12 hours"),
    CheckBackSchedule(24, "1 day"),
    CheckBackSchedule(48, "2 days"),
    CheckBackSchedule(72, "3 days"),
    CheckBackSchedule(168, "1 week"),
    CheckBackSchedule(336, "2 weeks"),
    CheckBackSchedule(720, "30 days"),
]


class TikTokSchedulerDB:
    """
    Database-backed scheduler for tracking post performance.
    
    Uses:
    - social_media_posts: Track posts with check_schedule
    - social_media_post_analytics: Store metrics snapshots
    - tiktok-scraper7 API: Fetch current metrics
    """
    
    API_HOST = "tiktok-scraper7.p.rapidapi.com"
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        api_key: Optional[str] = None,
        schedule: Optional[List[CheckBackSchedule]] = None
    ):
        """
        Initialize database scheduler.
        
        Args:
            db_url: PostgreSQL connection URL
            api_key: RapidAPI key for tiktok-scraper7
            schedule: Custom check-back schedule
        """
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        self.schedule = schedule or DEFAULT_SCHEDULE
        self.pool = None
    
    async def connect(self):
        """Connect to database."""
        if not HAS_ASYNCPG:
            raise RuntimeError("asyncpg required for database mode")
        
        if not self.db_url:
            raise ValueError("DATABASE_URL required")
        
        self.pool = await asyncpg.create_pool(self.db_url)
        print("Connected to database")
    
    async def close(self):
        """Close database connection."""
        if self.pool:
            await self.pool.close()
    
    def _get_api_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.API_HOST
        }
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL."""
        if '/video/' in url:
            return url.split('/video/')[-1].split('?')[0]
        raise ValueError(f"Invalid TikTok video URL: {url}")
    
    def _fetch_video_info(self, url: str) -> Optional[Dict]:
        """Fetch video info from API (sync)."""
        try:
            response = requests.get(
                f"https://{self.API_HOST}/",
                headers=self._get_api_headers(),
                params={"url": url},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and "data" in data:
                    return data["data"]
            
            print(f"API error: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"Fetch error: {e}")
            return None
    
    def _calculate_schedule(self, posted_at: datetime) -> List[str]:
        """Calculate check schedule timestamps from posted time."""
        return [
            (posted_at + timedelta(hours=s.offset_hours)).isoformat()
            for s in self.schedule
        ]
    
    async def track_post(self, url: str, account_id: Optional[int] = None) -> Dict:
        """
        Start tracking a new post in the database.
        
        Args:
            url: TikTok video URL
            account_id: Optional account ID (will try to find/create if not provided)
            
        Returns:
            Post record dict
        """
        video_id = self._extract_video_id(url)
        
        # Fetch initial info from API
        info = self._fetch_video_info(url)
        if not info:
            raise ValueError(f"Could not fetch video info for {url}")
        
        author = info.get("author", {})
        now = datetime.now()
        schedule = self._calculate_schedule(now)
        
        async with self.pool.acquire() as conn:
            # Check if already tracking
            existing = await conn.fetchrow(
                "SELECT id FROM social_media_posts WHERE external_post_id = $1 AND platform = 'tiktok'",
                video_id
            )
            
            if existing:
                print(f"Already tracking: {video_id}")
                return {"id": existing['id'], "video_id": video_id, "already_exists": True}
            
            # Get or create account
            if not account_id:
                account = await conn.fetchrow(
                    "SELECT id FROM social_media_accounts WHERE platform = 'tiktok' AND username = $1",
                    author.get("unique_id", "unknown")
                )
                
                if account:
                    account_id = account['id']
                else:
                    # Create account
                    account_id = await conn.fetchval("""
                        INSERT INTO social_media_accounts 
                        (platform, username, display_name, profile_pic_url, external_id)
                        VALUES ('tiktok', $1, $2, $3, $4)
                        RETURNING id
                    """, 
                        author.get("unique_id", "unknown"),
                        author.get("nickname"),
                        author.get("avatar"),
                        author.get("id")
                    )
            
            # Insert post
            post_id = await conn.fetchval("""
                INSERT INTO social_media_posts 
                (account_id, platform, external_post_id, post_url, caption, 
                 media_type, duration, posted_at, check_schedule, next_check_at,
                 tracking_started_at, tracking_complete)
                VALUES ($1, 'tiktok', $2, $3, $4, $5, $6, $7, $8, $9, $10, FALSE)
                RETURNING id
            """,
                account_id,
                video_id,
                url,
                info.get("title", "")[:500],
                "video",
                info.get("duration"),
                datetime.fromtimestamp(info.get("create_time", 0)) if info.get("create_time") else now,
                json.dumps(schedule),
                datetime.fromisoformat(schedule[0]) if schedule else None,
                now
            )
            
            # Insert initial metrics
            await conn.execute("""
                INSERT INTO social_media_post_analytics 
                (post_id, snapshot_date, snapshot_hour, likes_count, comments_count, 
                 views_count, shares_count, saves_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                post_id,
                now.date(),
                now.hour,
                info.get("digg_count", 0),
                info.get("comment_count", 0),
                info.get("play_count", 0),
                info.get("share_count", 0),
                info.get("collect_count", 0)
            )
        
        print(f"Now tracking: {video_id}")
        print(f"  Author: @{author.get('unique_id')}")
        print(f"  Likes: {info.get('digg_count', 0)}, Views: {info.get('play_count', 0)}")
        print(f"  Next check: {schedule[0] if schedule else 'None'}")
        
        return {
            "id": post_id,
            "video_id": video_id,
            "author": author.get("unique_id"),
            "likes": info.get("digg_count", 0),
            "views": info.get("play_count", 0),
            "next_check": schedule[0] if schedule else None
        }
    
    async def check_post(self, post_id: int) -> Optional[Dict]:
        """
        Perform a check on a tracked post.
        
        Args:
            post_id: Database post ID
            
        Returns:
            Metrics dict if successful
        """
        async with self.pool.acquire() as conn:
            # Get post info
            post = await conn.fetchrow("""
                SELECT id, post_url, check_schedule, checks_completed, tracking_complete
                FROM social_media_posts WHERE id = $1
            """, post_id)
            
            if not post:
                print(f"Post not found: {post_id}")
                return None
            
            if post['tracking_complete']:
                print(f"Tracking complete for: {post_id}")
                return None
            
            # Fetch current metrics
            info = self._fetch_video_info(post['post_url'])
            if not info:
                print(f"Could not fetch metrics for post {post_id}")
                return None
            
            now = datetime.now()
            
            # Get previous metrics for comparison
            prev = await conn.fetchrow("""
                SELECT likes_count, views_count 
                FROM social_media_post_analytics 
                WHERE post_id = $1 ORDER BY snapshot_date DESC, snapshot_hour DESC LIMIT 1
            """, post_id)
            
            # Insert new metrics
            await conn.execute("""
                INSERT INTO social_media_post_analytics 
                (post_id, snapshot_date, snapshot_hour, likes_count, comments_count, 
                 views_count, shares_count, saves_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                post_id,
                now.date(),
                now.hour,
                info.get("digg_count", 0),
                info.get("comment_count", 0),
                info.get("play_count", 0),
                info.get("share_count", 0),
                info.get("collect_count", 0)
            )
            
            # Update post tracking status
            schedule = json.loads(post['check_schedule']) if post['check_schedule'] else []
            new_completed = (post['checks_completed'] or 0) + 1
            
            if new_completed >= len(schedule):
                # All checks done
                await conn.execute("""
                    UPDATE social_media_posts 
                    SET checks_completed = $1, tracking_complete = TRUE, next_check_at = NULL
                    WHERE id = $2
                """, new_completed, post_id)
            else:
                # Schedule next check
                next_check = datetime.fromisoformat(schedule[new_completed])
                await conn.execute("""
                    UPDATE social_media_posts 
                    SET checks_completed = $1, next_check_at = $2
                    WHERE id = $3
                """, new_completed, next_check, post_id)
            
            # Calculate deltas
            metrics = {
                "likes": info.get("digg_count", 0),
                "views": info.get("play_count", 0),
                "comments": info.get("comment_count", 0),
                "shares": info.get("share_count", 0)
            }
            
            if prev:
                delta_likes = metrics["likes"] - prev['likes_count']
                delta_views = metrics["views"] - prev['views_count']
                print(f"Check complete for post {post_id}:")
                print(f"  Likes: {metrics['likes']} (+{delta_likes})")
                print(f"  Views: {metrics['views']} (+{delta_views})")
            
            return metrics
    
    async def run_pending_checks(self) -> List[Dict]:
        """
        Run all pending checks that are due.
        
        Returns:
            List of check results
        """
        results = []
        
        async with self.pool.acquire() as conn:
            # Find posts needing checks
            pending = await conn.fetch("""
                SELECT id, external_post_id, post_url, next_check_at
                FROM social_media_posts
                WHERE platform = 'tiktok'
                AND tracking_complete = FALSE
                AND next_check_at IS NOT NULL
                AND next_check_at <= NOW()
                ORDER BY next_check_at ASC
                LIMIT 10
            """)
            
            print(f"Found {len(pending)} posts needing checks")
            
            for post in pending:
                print(f"\n--- Checking: {post['external_post_id']} ---")
                metrics = await self.check_post(post['id'])
                if metrics:
                    results.append({
                        "post_id": post['id'],
                        "video_id": post['external_post_id'],
                        "metrics": metrics
                    })
        
        return results
    
    async def get_post_analytics(self, post_id: int) -> Dict[str, Any]:
        """
        Get analytics summary for a tracked post.
        
        Args:
            post_id: Database post ID
            
        Returns:
            Analytics dictionary
        """
        async with self.pool.acquire() as conn:
            post = await conn.fetchrow("""
                SELECT p.*, a.username as author
                FROM social_media_posts p
                JOIN social_media_accounts a ON p.account_id = a.id
                WHERE p.id = $1
            """, post_id)
            
            if not post:
                return {"error": "Post not found"}
            
            # Get metrics history
            metrics = await conn.fetch("""
                SELECT snapshot_date, snapshot_hour, likes_count, comments_count, 
                       views_count, shares_count, saves_count
                FROM social_media_post_analytics
                WHERE post_id = $1
                ORDER BY snapshot_date, snapshot_hour
            """, post_id)
            
            if not metrics:
                return {"post_id": post_id, "error": "No metrics"}
            
            first = metrics[0]
            last = metrics[-1]
            
            return {
                "post_id": post_id,
                "video_id": post['external_post_id'],
                "author": post['author'],
                "url": post['post_url'],
                "caption": post['caption'][:100] if post['caption'] else None,
                "tracking_started": post['tracking_started_at'].isoformat() if post['tracking_started_at'] else None,
                "tracking_complete": post['tracking_complete'],
                "checks_completed": post['checks_completed'],
                "next_check": post['next_check_at'].isoformat() if post['next_check_at'] else None,
                "current_metrics": {
                    "likes": last['likes_count'],
                    "views": last['views_count'],
                    "comments": last['comments_count'],
                    "shares": last['shares_count'],
                    "saves": last['saves_count']
                },
                "initial_metrics": {
                    "likes": first['likes_count'],
                    "views": first['views_count'],
                    "comments": first['comments_count']
                },
                "growth": {
                    "likes": last['likes_count'] - first['likes_count'],
                    "views": last['views_count'] - first['views_count'],
                    "comments": last['comments_count'] - first['comments_count']
                },
                "total_snapshots": len(metrics)
            }
    
    async def list_tracked_posts(self, limit: int = 50) -> List[Dict]:
        """Get summary of all tracked posts."""
        async with self.pool.acquire() as conn:
            posts = await conn.fetch("""
                SELECT 
                    p.id, p.external_post_id, p.post_url, p.caption,
                    p.tracking_complete, p.checks_completed, p.next_check_at,
                    a.username,
                    (SELECT likes_count FROM social_media_post_analytics 
                     WHERE post_id = p.id ORDER BY snapshot_date DESC LIMIT 1) as current_likes,
                    (SELECT views_count FROM social_media_post_analytics 
                     WHERE post_id = p.id ORDER BY snapshot_date DESC LIMIT 1) as current_views
                FROM social_media_posts p
                JOIN social_media_accounts a ON p.account_id = a.id
                WHERE p.platform = 'tiktok' AND p.check_schedule IS NOT NULL
                ORDER BY p.tracking_started_at DESC
                LIMIT $1
            """, limit)
            
            return [dict(p) for p in posts]


# CLI interface
async def main():
    """Command-line interface for the database scheduler."""
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tiktok_scheduler_db.py track <url>    - Track a new post")
        print("  python tiktok_scheduler_db.py check          - Run pending checks")
        print("  python tiktok_scheduler_db.py list           - List tracked posts")
        print("  python tiktok_scheduler_db.py analytics <id> - Get post analytics")
        print()
        print("Requires: DATABASE_URL and RAPIDAPI_KEY environment variables")
        return
    
    scheduler = TikTokSchedulerDB()
    await scheduler.connect()
    
    try:
        command = sys.argv[1]
        
        if command == "track" and len(sys.argv) > 2:
            url = sys.argv[2]
            result = await scheduler.track_post(url)
            print(f"\nResult: {json.dumps(result, indent=2, default=str)}")
        
        elif command == "check":
            results = await scheduler.run_pending_checks()
            print(f"\nCompleted {len(results)} checks")
        
        elif command == "list":
            posts = await scheduler.list_tracked_posts()
            print(f"\nTracked Posts ({len(posts)}):")
            print("-" * 60)
            for p in posts:
                status = "✅" if p['tracking_complete'] else "🔄"
                print(f"{status} {p['external_post_id'][:15]}... | @{p['username']} | {p['current_likes'] or 0} likes")
        
        elif command == "analytics" and len(sys.argv) > 2:
            post_id = int(sys.argv[2])
            analytics = await scheduler.get_post_analytics(post_id)
            print(json.dumps(analytics, indent=2, default=str))
        
        else:
            print(f"Unknown command: {command}")
    
    finally:
        await scheduler.close()


if __name__ == "__main__":
    asyncio.run(main())

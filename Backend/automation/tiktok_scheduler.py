"""
TikTok Scheduler - Check-back periods for post metrics tracking.

Tracks post performance over time using the API for data extraction.

Usage:
    from automation.tiktok_scheduler import TikTokScheduler, CheckBackPeriod
    
    scheduler = TikTokScheduler(api_key="your_key")
    scheduler.track_post("https://tiktok.com/@user/video/123")
    scheduler.run_pending_checks()
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class CheckInterval(Enum):
    """Check-back period intervals."""
    HOUR_1 = timedelta(hours=1)
    HOUR_6 = timedelta(hours=6)
    HOUR_12 = timedelta(hours=12)
    DAY_1 = timedelta(days=1)
    DAY_2 = timedelta(days=2)
    DAY_3 = timedelta(days=3)
    WEEK_1 = timedelta(weeks=1)
    WEEK_2 = timedelta(weeks=2)
    MONTH_1 = timedelta(days=30)


@dataclass
class PostMetrics:
    """Metrics snapshot for a post."""
    timestamp: str
    likes: int
    comments: int
    shares: int
    views: int
    saves: int = 0
    
    @classmethod
    def from_api_response(cls, data: Dict) -> 'PostMetrics':
        """Create from tiktok-scraper7 API response."""
        return cls(
            timestamp=datetime.now().isoformat(),
            likes=data.get('digg_count', 0),
            comments=data.get('comment_count', 0),
            shares=data.get('share_count', 0),
            views=data.get('play_count', 0),
            saves=data.get('collect_count', 0)
        )


@dataclass
class TrackedPost:
    """A post being tracked over time."""
    url: str
    video_id: str
    author: str
    title: str
    created_at: str
    check_schedule: List[str]  # List of check intervals
    completed_checks: List[str]  # Timestamps of completed checks
    next_check: Optional[str]  # ISO timestamp of next check
    metrics_history: List[Dict]  # List of PostMetrics as dicts
    is_complete: bool = False


# Default check-back schedule
DEFAULT_SCHEDULE = [
    CheckInterval.HOUR_1,
    CheckInterval.HOUR_6,
    CheckInterval.HOUR_12,
    CheckInterval.DAY_1,
    CheckInterval.DAY_2,
    CheckInterval.DAY_3,
    CheckInterval.WEEK_1,
    CheckInterval.WEEK_2,
    CheckInterval.MONTH_1,
]


class TikTokScheduler:
    """
    Scheduler for tracking post performance over time.
    
    Uses tiktok-scraper7 API to fetch metrics at configured intervals.
    """
    
    API_HOST = "tiktok-scraper7.p.rapidapi.com"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        storage_path: Optional[str] = None,
        schedule: Optional[List[CheckInterval]] = None
    ):
        """
        Initialize scheduler.
        
        Args:
            api_key: RapidAPI key (or from RAPIDAPI_KEY env var)
            storage_path: Path to store tracking data
            schedule: Custom check-back schedule
        """
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set RAPIDAPI_KEY or pass api_key.")
        
        self.storage_path = Path(storage_path or "./tracked_posts")
        self.storage_path.mkdir(exist_ok=True)
        
        self.schedule = schedule or DEFAULT_SCHEDULE
        self.tracked_posts: Dict[str, TrackedPost] = {}
        
        # Load existing tracked posts
        self._load_tracked_posts()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.API_HOST
        }
    
    def _load_tracked_posts(self):
        """Load tracked posts from storage."""
        for file in self.storage_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    post = TrackedPost(**data)
                    self.tracked_posts[post.video_id] = post
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    def _save_post(self, post: TrackedPost):
        """Save post to storage."""
        filepath = self.storage_path / f"{post.video_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(post), f, indent=2)
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL."""
        # URL format: https://www.tiktok.com/@user/video/VIDEO_ID
        if '/video/' in url:
            return url.split('/video/')[-1].split('?')[0]
        raise ValueError(f"Invalid TikTok video URL: {url}")
    
    def _fetch_video_info(self, url: str) -> Optional[Dict]:
        """Fetch video info from API."""
        try:
            response = requests.get(
                f"https://{self.API_HOST}/",
                headers=self._get_headers(),
                params={"url": url},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and "data" in data:
                    return data["data"]
            
            print(f"API error: {response.status_code} - {response.text[:100]}")
            return None
            
        except Exception as e:
            print(f"Fetch error: {e}")
            return None
    
    def track_post(self, url: str) -> TrackedPost:
        """
        Start tracking a new post.
        
        Args:
            url: TikTok video URL
            
        Returns:
            TrackedPost object
        """
        video_id = self._extract_video_id(url)
        
        # Check if already tracking
        if video_id in self.tracked_posts:
            print(f"Already tracking: {video_id}")
            return self.tracked_posts[video_id]
        
        # Fetch initial info
        info = self._fetch_video_info(url)
        if not info:
            raise ValueError(f"Could not fetch video info for {url}")
        
        # Create initial metrics snapshot
        initial_metrics = PostMetrics.from_api_response(info)
        
        # Calculate check schedule
        now = datetime.now()
        schedule_times = [
            (now + interval.value).isoformat()
            for interval in self.schedule
        ]
        
        # Create tracked post
        post = TrackedPost(
            url=url,
            video_id=video_id,
            author=info.get("author", {}).get("unique_id", "unknown"),
            title=info.get("title", "")[:100],
            created_at=datetime.now().isoformat(),
            check_schedule=schedule_times,
            completed_checks=[now.isoformat()],
            next_check=schedule_times[0] if schedule_times else None,
            metrics_history=[asdict(initial_metrics)],
            is_complete=False
        )
        
        self.tracked_posts[video_id] = post
        self._save_post(post)
        
        print(f"Now tracking: {video_id}")
        print(f"  Author: @{post.author}")
        print(f"  Title: {post.title[:50]}...")
        print(f"  Initial metrics: {initial_metrics.likes} likes, {initial_metrics.views} views")
        print(f"  Next check: {post.next_check}")
        
        return post
    
    def check_post(self, video_id: str) -> Optional[PostMetrics]:
        """
        Perform a check on a tracked post.
        
        Args:
            video_id: Video ID to check
            
        Returns:
            PostMetrics if successful
        """
        if video_id not in self.tracked_posts:
            print(f"Not tracking: {video_id}")
            return None
        
        post = self.tracked_posts[video_id]
        
        if post.is_complete:
            print(f"Tracking complete for: {video_id}")
            return None
        
        # Fetch current metrics
        info = self._fetch_video_info(post.url)
        if not info:
            print(f"Could not fetch metrics for {video_id}")
            return None
        
        metrics = PostMetrics.from_api_response(info)
        
        # Update post
        post.metrics_history.append(asdict(metrics))
        post.completed_checks.append(datetime.now().isoformat())
        
        # Calculate next check
        remaining_checks = [
            t for t in post.check_schedule
            if t not in post.completed_checks
        ]
        
        if remaining_checks:
            post.next_check = remaining_checks[0]
        else:
            post.next_check = None
            post.is_complete = True
        
        self._save_post(post)
        
        # Calculate delta from last check
        if len(post.metrics_history) > 1:
            prev = post.metrics_history[-2]
            delta_likes = metrics.likes - prev['likes']
            delta_views = metrics.views - prev['views']
            print(f"Check complete for {video_id}:")
            print(f"  Likes: {metrics.likes} (+{delta_likes})")
            print(f"  Views: {metrics.views} (+{delta_views})")
        
        return metrics
    
    def run_pending_checks(self) -> List[Dict]:
        """
        Run all pending checks that are due.
        
        Returns:
            List of check results
        """
        now = datetime.now()
        results = []
        
        for video_id, post in self.tracked_posts.items():
            if post.is_complete:
                continue
            
            if post.next_check:
                next_check_time = datetime.fromisoformat(post.next_check)
                
                if now >= next_check_time:
                    print(f"\n--- Checking: {video_id} ---")
                    metrics = self.check_post(video_id)
                    if metrics:
                        results.append({
                            "video_id": video_id,
                            "metrics": asdict(metrics)
                        })
        
        print(f"\nCompleted {len(results)} checks")
        return results
    
    def get_post_analytics(self, video_id: str) -> Dict[str, Any]:
        """
        Get analytics summary for a tracked post.
        
        Args:
            video_id: Video ID
            
        Returns:
            Analytics dictionary
        """
        if video_id not in self.tracked_posts:
            return {"error": "Not tracking"}
        
        post = self.tracked_posts[video_id]
        history = post.metrics_history
        
        if len(history) < 2:
            return {
                "video_id": video_id,
                "author": post.author,
                "current": history[-1] if history else {},
                "growth": {},
                "checks_remaining": len([
                    t for t in post.check_schedule
                    if t not in post.completed_checks
                ])
            }
        
        first = history[0]
        last = history[-1]
        
        return {
            "video_id": video_id,
            "author": post.author,
            "title": post.title,
            "tracking_started": post.created_at,
            "total_checks": len(post.completed_checks),
            "current_metrics": last,
            "initial_metrics": first,
            "growth": {
                "likes": last['likes'] - first['likes'],
                "views": last['views'] - first['views'],
                "comments": last['comments'] - first['comments'],
                "shares": last['shares'] - first['shares'],
            },
            "growth_rate": {
                "likes_per_hour": self._calculate_hourly_rate(history, 'likes'),
                "views_per_hour": self._calculate_hourly_rate(history, 'views'),
            },
            "is_complete": post.is_complete,
            "next_check": post.next_check
        }
    
    def _calculate_hourly_rate(self, history: List[Dict], metric: str) -> float:
        """Calculate hourly growth rate for a metric."""
        if len(history) < 2:
            return 0.0
        
        first = history[0]
        last = history[-1]
        
        first_time = datetime.fromisoformat(first['timestamp'])
        last_time = datetime.fromisoformat(last['timestamp'])
        
        hours = (last_time - first_time).total_seconds() / 3600
        if hours == 0:
            return 0.0
        
        delta = last[metric] - first[metric]
        return round(delta / hours, 2)
    
    def list_tracked_posts(self) -> List[Dict]:
        """Get summary of all tracked posts."""
        summaries = []
        
        for video_id, post in self.tracked_posts.items():
            last_metrics = post.metrics_history[-1] if post.metrics_history else {}
            summaries.append({
                "video_id": video_id,
                "author": post.author,
                "title": post.title[:40],
                "current_likes": last_metrics.get('likes', 0),
                "current_views": last_metrics.get('views', 0),
                "is_complete": post.is_complete,
                "next_check": post.next_check
            })
        
        return summaries
    
    def stop_tracking(self, video_id: str):
        """Stop tracking a post."""
        if video_id in self.tracked_posts:
            post = self.tracked_posts[video_id]
            post.is_complete = True
            self._save_post(post)
            print(f"Stopped tracking: {video_id}")


class SchedulerDaemon:
    """
    Background daemon that runs the scheduler.
    
    Usage:
        daemon = SchedulerDaemon(scheduler)
        daemon.start()  # Runs in loop
    """
    
    def __init__(self, scheduler: TikTokScheduler, check_interval: int = 300):
        """
        Initialize daemon.
        
        Args:
            scheduler: TikTokScheduler instance
            check_interval: Seconds between check cycles (default 5 min)
        """
        self.scheduler = scheduler
        self.check_interval = check_interval
        self.running = False
    
    def start(self):
        """Start the daemon loop."""
        self.running = True
        print(f"Scheduler daemon started. Checking every {self.check_interval}s")
        
        while self.running:
            try:
                self.scheduler.run_pending_checks()
            except Exception as e:
                print(f"Error in check cycle: {e}")
            
            time.sleep(self.check_interval)
    
    def stop(self):
        """Stop the daemon."""
        self.running = False
        print("Scheduler daemon stopped")


# CLI interface
def main():
    """Command-line interface for the scheduler."""
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tiktok_scheduler.py track <url>    - Track a new post")
        print("  python tiktok_scheduler.py check          - Run pending checks")
        print("  python tiktok_scheduler.py list           - List tracked posts")
        print("  python tiktok_scheduler.py analytics <id> - Get post analytics")
        print("  python tiktok_scheduler.py daemon         - Run as background daemon")
        return
    
    scheduler = TikTokScheduler()
    command = sys.argv[1]
    
    if command == "track" and len(sys.argv) > 2:
        url = sys.argv[2]
        scheduler.track_post(url)
    
    elif command == "check":
        scheduler.run_pending_checks()
    
    elif command == "list":
        posts = scheduler.list_tracked_posts()
        print("\nTracked Posts:")
        print("-" * 60)
        for p in posts:
            status = "✅" if p['is_complete'] else "🔄"
            print(f"{status} {p['video_id'][:15]}... | @{p['author']} | {p['current_likes']} likes")
    
    elif command == "analytics" and len(sys.argv) > 2:
        video_id = sys.argv[2]
        analytics = scheduler.get_post_analytics(video_id)
        print(json.dumps(analytics, indent=2))
    
    elif command == "daemon":
        daemon = SchedulerDaemon(scheduler)
        try:
            daemon.start()
        except KeyboardInterrupt:
            daemon.stop()
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()

"""
Smart Posting Times Service
============================
ML-driven optimal scheduling based on YOUR engagement data.

Replaces fixed scheduling with data-driven optimal posting times.
Analyzes historical post performance to find when YOUR audience is
most active per platform per account.

How it works:
1. Pulls all published posts with engagement metrics from the DB
2. Buckets posts by hour-of-day and day-of-week per platform
3. Calculates weighted engagement scores per time slot
4. Applies Bayesian smoothing to handle sparse data
5. Returns ranked optimal posting windows per platform

Usage:
    service = SmartPostingTimesService()
    recommendations = await service.get_optimal_times("tiktok")
    # [{"hour": 19, "day": "wednesday", "score": 87.3, "confidence": 0.92}, ...]

    schedule = await service.generate_weekly_schedule()
    # Full week schedule with optimal times per platform
"""

import os
import math
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from loguru import logger


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class TimeSlotPerformance:
    """Performance data for a specific time slot."""
    hour: int                    # 0-23 (UTC or EST based on config)
    day_of_week: int             # 0=Monday, 6=Sunday
    day_name: str                # "monday", "tuesday", etc.
    platform: str
    post_count: int = 0
    avg_views: float = 0.0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_shares: float = 0.0
    avg_engagement_rate: float = 0.0
    avg_performance_score: float = 0.0
    composite_score: float = 0.0  # Weighted final score (0-100)
    confidence: float = 0.0       # How confident we are (0-1)


@dataclass
class OptimalWindow:
    """A recommended posting window."""
    platform: str
    hour_utc: int
    hour_est: int
    day_of_week: int
    day_name: str
    score: float               # 0-100
    confidence: float          # 0-1
    avg_engagement_rate: float
    sample_size: int
    rank: int = 0


@dataclass
class WeeklySlot:
    """A slot in the generated weekly schedule."""
    day_name: str
    day_of_week: int
    hour_est: int
    platform: str
    account_id: Optional[str] = None
    score: float = 0.0
    confidence: float = 0.0
    reason: str = ""


# ─── Default Priors (when no data exists) ────────────────────────────────────

# Based on industry research for each platform (hours in EST)
DEFAULT_BEST_HOURS_EST: Dict[str, List[int]] = {
    "tiktok":    [7, 10, 12, 19, 21],      # Morning commute, lunch, evening
    "instagram": [8, 11, 13, 17, 20],       # Mid-morning, lunch, post-work
    "youtube":   [9, 12, 15, 18],           # Late morning through evening
    "twitter":   [8, 12, 17, 21],           # Before work, lunch, after work, late
    "threads":   [9, 12, 18, 21],           # Similar to Twitter
    "linkedin":  [7, 10, 12, 17],           # Business hours peak
    "pinterest": [20, 21, 22, 14],          # Evening browsing peak
    "facebook":  [9, 13, 16, 19],           # Mid-day and evening
    "bluesky":   [10, 14, 19, 21],          # Tech crowd hours
}

# Day-of-week multipliers (1.0 = average)
DEFAULT_DAY_MULTIPLIERS: Dict[str, Dict[int, float]] = {
    "tiktok":    {0: 0.9, 1: 1.1, 2: 1.0, 3: 1.1, 4: 1.2, 5: 1.0, 6: 0.8},
    "instagram": {0: 0.9, 1: 1.0, 2: 1.1, 3: 1.0, 4: 1.1, 5: 1.0, 6: 0.9},
    "youtube":   {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.1, 4: 1.2, 5: 1.1, 6: 0.8},
    "twitter":   {0: 1.1, 1: 1.0, 2: 1.1, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.8},
    "linkedin":  {0: 1.0, 1: 1.2, 2: 1.1, 3: 1.0, 4: 0.8, 5: 0.3, 6: 0.3},
}

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ─── Service ─────────────────────────────────────────────────────────────────

class SmartPostingTimesService:
    """
    Analyzes historical engagement data to determine optimal posting times.
    Uses Bayesian smoothing to blend real data with industry priors.
    """

    # Weights for composite score calculation
    VIEW_WEIGHT = 0.3
    ENGAGEMENT_WEIGHT = 0.4   # likes + comments + shares
    SAVE_WEIGHT = 0.2
    VELOCITY_WEIGHT = 0.1     # How fast engagement accumulates

    # Minimum posts needed before data overrides priors
    MIN_POSTS_FOR_CONFIDENCE = 5
    BAYESIAN_STRENGTH = 3  # How strongly priors influence with sparse data

    def __init__(self):
        self.timezone_offset = int(os.getenv("POSTING_TIMEZONE_OFFSET", "-5"))  # EST default

    # ── Public API ───────────────────────────────────────────────────────

    async def get_optimal_times(
        self,
        platform: str,
        account_id: Optional[str] = None,
        lookback_days: int = 60,
        top_n: int = 10,
    ) -> List[OptimalWindow]:
        """
        Get ranked optimal posting times for a platform.

        Args:
            platform: Platform name (tiktok, instagram, etc.)
            account_id: Optional specific account to analyze
            lookback_days: How many days of history to analyze
            top_n: Number of top windows to return

        Returns:
            List of OptimalWindow sorted by score (best first)
        """
        # Pull historical data from DB
        posts = await self._fetch_post_performance(platform, account_id, lookback_days)

        if not posts:
            logger.info(f"[SmartTimes] No historical data for {platform}, using industry defaults")
            return self._generate_default_windows(platform, top_n)

        # Analyze time slot performance
        slot_data = self._analyze_time_slots(posts, platform)

        # Apply Bayesian smoothing
        smoothed = self._bayesian_smooth(slot_data, platform)

        # Rank and return top windows
        windows = self._rank_windows(smoothed, platform, top_n)

        logger.info(
            f"[SmartTimes] {platform}: analyzed {len(posts)} posts → "
            f"top window: {windows[0].day_name} {windows[0].hour_est}:00 EST "
            f"(score={windows[0].score:.1f}, confidence={windows[0].confidence:.2f})"
            if windows else f"[SmartTimes] {platform}: no windows found"
        )

        return windows

    async def get_all_platform_times(
        self, lookback_days: int = 60, top_n: int = 5
    ) -> Dict[str, List[OptimalWindow]]:
        """Get optimal times for all platforms."""
        platforms = list(DEFAULT_BEST_HOURS_EST.keys())
        results = {}
        for platform in platforms:
            results[platform] = await self.get_optimal_times(
                platform, lookback_days=lookback_days, top_n=top_n
            )
        return results

    async def generate_weekly_schedule(
        self,
        platforms: Optional[List[str]] = None,
        posts_per_day: int = 3,
        lookback_days: int = 60,
    ) -> List[WeeklySlot]:
        """
        Generate a full weekly posting schedule with optimal times.

        Args:
            platforms: Platforms to schedule for (default: all)
            posts_per_day: Target posts per day across all platforms
            lookback_days: Historical analysis window

        Returns:
            List of WeeklySlot representing the optimal weekly schedule
        """
        if not platforms:
            platforms = ["tiktok", "instagram", "youtube", "twitter", "threads"]

        # Get optimal windows for each platform
        all_windows = []
        for platform in platforms:
            windows = await self.get_optimal_times(platform, lookback_days=lookback_days, top_n=20)
            all_windows.extend(windows)

        # Sort all windows by score
        all_windows.sort(key=lambda w: w.score, reverse=True)

        # Greedily assign slots ensuring no time conflicts
        schedule: List[WeeklySlot] = []
        used_slots: set = set()  # (day, hour) tuples to avoid conflicts

        for window in all_windows:
            slot_key = (window.day_of_week, window.hour_est)
            if slot_key in used_slots:
                continue

            # Check daily limit
            day_posts = sum(1 for s in schedule if s.day_of_week == window.day_of_week)
            if day_posts >= posts_per_day:
                continue

            schedule.append(WeeklySlot(
                day_name=window.day_name,
                day_of_week=window.day_of_week,
                hour_est=window.hour_est,
                platform=window.platform,
                score=window.score,
                confidence=window.confidence,
                reason=f"Score {window.score:.0f} from {window.sample_size} posts" if window.sample_size > 0
                       else f"Score {window.score:.0f} (industry default)",
            ))
            used_slots.add(slot_key)

        # Sort by day then hour
        schedule.sort(key=lambda s: (s.day_of_week, s.hour_est))

        logger.info(f"[SmartTimes] Generated weekly schedule: {len(schedule)} slots across {len(platforms)} platforms")
        return schedule

    async def suggest_time_for_post(
        self,
        platform: str,
        preferred_day: Optional[int] = None,
        account_id: Optional[str] = None,
    ) -> Optional[OptimalWindow]:
        """
        Suggest the single best time for a specific post.

        Args:
            platform: Target platform
            preferred_day: Preferred day of week (0=Mon, 6=Sun), or None for any
            account_id: Specific account

        Returns:
            Best OptimalWindow or None
        """
        windows = await self.get_optimal_times(platform, account_id=account_id, top_n=20)
        if not windows:
            return None

        if preferred_day is not None:
            day_windows = [w for w in windows if w.day_of_week == preferred_day]
            return day_windows[0] if day_windows else windows[0]

        return windows[0]

    # ── Data Fetching ────────────────────────────────────────────────────

    async def _fetch_post_performance(
        self,
        platform: str,
        account_id: Optional[str],
        lookback_days: int,
    ) -> List[Dict[str, Any]]:
        """Fetch historical post performance from the database."""
        try:
            from sqlalchemy import create_engine, text

            db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
            engine = create_engine(db_url)

            cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

            query = """
                SELECT
                    sp.id,
                    sp.platform,
                    sp.account_id,
                    sp.published_at,
                    sp.status,
                    COALESCE(cms.views, 0) as views,
                    COALESCE(cms.likes, 0) as likes,
                    COALESCE(cms.comments, 0) as comments,
                    COALESCE(cms.shares, 0) as shares,
                    COALESCE(cms.saves, 0) as saves,
                    COALESCE(cms.engagement_rate, 0) as engagement_rate
                FROM scheduled_posts sp
                LEFT JOIN LATERAL (
                    SELECT * FROM content_metrics_snapshots cms2
                    WHERE cms2.scheduled_post_id = sp.id
                    ORDER BY cms2.snapshot_at DESC
                    LIMIT 1
                ) cms ON true
                WHERE sp.platform = :platform
                  AND sp.status = 'published'
                  AND sp.published_at IS NOT NULL
                  AND sp.published_at > :cutoff
            """
            params = {"platform": platform, "cutoff": cutoff}

            if account_id:
                query += " AND sp.account_id = :account_id"
                params["account_id"] = account_id

            query += " ORDER BY sp.published_at DESC"

            with engine.connect() as conn:
                result = conn.execute(text(query), params)
                rows = result.fetchall()

            posts = []
            for row in rows:
                published_at = row[3]
                if published_at:
                    posts.append({
                        "id": str(row[0]),
                        "platform": row[1],
                        "account_id": str(row[2]) if row[2] else None,
                        "published_at": published_at,
                        "hour_utc": published_at.hour,
                        "day_of_week": published_at.weekday(),
                        "views": row[5],
                        "likes": row[6],
                        "comments": row[7],
                        "shares": row[8],
                        "saves": row[9],
                        "engagement_rate": row[10],
                    })

            logger.info(f"[SmartTimes] Fetched {len(posts)} published posts for {platform} (last {lookback_days} days)")
            return posts

        except Exception as e:
            logger.error(f"[SmartTimes] DB fetch failed: {e}")
            return []

    # ── Analysis ─────────────────────────────────────────────────────────

    def _analyze_time_slots(
        self, posts: List[Dict[str, Any]], platform: str
    ) -> Dict[Tuple[int, int], TimeSlotPerformance]:
        """
        Bucket posts into (day_of_week, hour) slots and compute averages.
        """
        buckets: Dict[Tuple[int, int], List[Dict]] = defaultdict(list)

        for post in posts:
            # Convert UTC hour to local hour
            local_hour = (post["hour_utc"] + self.timezone_offset) % 24
            key = (post["day_of_week"], local_hour)
            buckets[key].append(post)

        slots = {}
        for (dow, hour), bucket_posts in buckets.items():
            n = len(bucket_posts)
            avg_views = sum(p["views"] for p in bucket_posts) / n
            avg_likes = sum(p["likes"] for p in bucket_posts) / n
            avg_comments = sum(p["comments"] for p in bucket_posts) / n
            avg_shares = sum(p["shares"] for p in bucket_posts) / n
            avg_saves = sum(p.get("saves", 0) for p in bucket_posts) / n
            avg_er = sum(p["engagement_rate"] for p in bucket_posts) / n

            # Composite score (weighted)
            engagement = avg_likes + avg_comments + avg_shares
            composite = (
                self.VIEW_WEIGHT * min(avg_views / 1000, 1.0) * 100
                + self.ENGAGEMENT_WEIGHT * min(engagement / 100, 1.0) * 100
                + self.SAVE_WEIGHT * min(avg_saves / 50, 1.0) * 100
            )

            slots[(dow, hour)] = TimeSlotPerformance(
                hour=hour,
                day_of_week=dow,
                day_name=DAY_NAMES[dow],
                platform=platform,
                post_count=n,
                avg_views=avg_views,
                avg_likes=avg_likes,
                avg_comments=avg_comments,
                avg_shares=avg_shares,
                avg_engagement_rate=avg_er,
                composite_score=composite,
                confidence=min(n / self.MIN_POSTS_FOR_CONFIDENCE, 1.0),
            )

        return slots

    def _bayesian_smooth(
        self,
        slot_data: Dict[Tuple[int, int], TimeSlotPerformance],
        platform: str,
    ) -> Dict[Tuple[int, int], TimeSlotPerformance]:
        """
        Apply Bayesian smoothing: blend actual data with industry priors.
        With few posts, priors dominate. With many posts, data dominates.
        """
        default_hours = set(DEFAULT_BEST_HOURS_EST.get(platform, []))
        day_mults = DEFAULT_DAY_MULTIPLIERS.get(platform, {})

        # Generate full grid (7 days × 24 hours)
        smoothed = {}
        for dow in range(7):
            for hour in range(24):
                key = (dow, hour)
                actual = slot_data.get(key)

                # Prior score: higher for known good hours
                prior_score = 50.0  # baseline
                if hour in default_hours:
                    prior_score = 75.0
                prior_score *= day_mults.get(dow, 1.0)

                if actual and actual.post_count > 0:
                    # Bayesian blend: (n * actual + k * prior) / (n + k)
                    n = actual.post_count
                    k = self.BAYESIAN_STRENGTH
                    blended_score = (n * actual.composite_score + k * prior_score) / (n + k)
                    confidence = min(n / self.MIN_POSTS_FOR_CONFIDENCE, 1.0)

                    smoothed[key] = TimeSlotPerformance(
                        hour=hour,
                        day_of_week=dow,
                        day_name=DAY_NAMES[dow],
                        platform=platform,
                        post_count=actual.post_count,
                        avg_views=actual.avg_views,
                        avg_likes=actual.avg_likes,
                        avg_comments=actual.avg_comments,
                        avg_shares=actual.avg_shares,
                        avg_engagement_rate=actual.avg_engagement_rate,
                        composite_score=blended_score,
                        confidence=confidence,
                    )
                else:
                    # Pure prior
                    smoothed[key] = TimeSlotPerformance(
                        hour=hour,
                        day_of_week=dow,
                        day_name=DAY_NAMES[dow],
                        platform=platform,
                        post_count=0,
                        composite_score=prior_score,
                        confidence=0.0,
                    )

        return smoothed

    def _rank_windows(
        self,
        smoothed: Dict[Tuple[int, int], TimeSlotPerformance],
        platform: str,
        top_n: int,
    ) -> List[OptimalWindow]:
        """Rank time slots and return top N optimal windows."""
        sorted_slots = sorted(
            smoothed.values(),
            key=lambda s: s.composite_score,
            reverse=True,
        )

        windows = []
        for rank, slot in enumerate(sorted_slots[:top_n], 1):
            utc_hour = (slot.hour - self.timezone_offset) % 24
            windows.append(OptimalWindow(
                platform=platform,
                hour_utc=utc_hour,
                hour_est=slot.hour,
                day_of_week=slot.day_of_week,
                day_name=slot.day_name,
                score=round(slot.composite_score, 1),
                confidence=round(slot.confidence, 2),
                avg_engagement_rate=round(slot.avg_engagement_rate, 4),
                sample_size=slot.post_count,
                rank=rank,
            ))

        return windows

    def _generate_default_windows(
        self, platform: str, top_n: int
    ) -> List[OptimalWindow]:
        """Generate default windows from industry data when no history exists."""
        default_hours = DEFAULT_BEST_HOURS_EST.get(platform, [12, 18])
        day_mults = DEFAULT_DAY_MULTIPLIERS.get(platform, {})

        windows = []
        for dow in range(7):
            mult = day_mults.get(dow, 1.0)
            for hour in default_hours:
                score = 70.0 * mult
                utc_hour = (hour - self.timezone_offset) % 24
                windows.append(OptimalWindow(
                    platform=platform,
                    hour_utc=utc_hour,
                    hour_est=hour,
                    day_of_week=dow,
                    day_name=DAY_NAMES[dow],
                    score=round(score, 1),
                    confidence=0.0,  # No real data
                    avg_engagement_rate=0.0,
                    sample_size=0,
                ))

        windows.sort(key=lambda w: w.score, reverse=True)
        for i, w in enumerate(windows[:top_n], 1):
            w.rank = i

        return windows[:top_n]

    # ── Heatmap Export ───────────────────────────────────────────────────

    async def get_heatmap_data(
        self,
        platform: str,
        lookback_days: int = 60,
    ) -> Dict[str, Any]:
        """
        Generate heatmap data for a platform (7 days × 24 hours).
        Returns a matrix of scores suitable for visualization.
        """
        posts = await self._fetch_post_performance(platform, None, lookback_days)

        if posts:
            slot_data = self._analyze_time_slots(posts, platform)
            smoothed = self._bayesian_smooth(slot_data, platform)
        else:
            # Pure priors
            smoothed = self._bayesian_smooth({}, platform)

        # Build matrix
        matrix = []
        for dow in range(7):
            row = []
            for hour in range(24):
                slot = smoothed.get((dow, hour))
                row.append({
                    "score": round(slot.composite_score, 1) if slot else 0,
                    "posts": slot.post_count if slot else 0,
                    "confidence": round(slot.confidence, 2) if slot else 0,
                })
            matrix.append(row)

        return {
            "platform": platform,
            "timezone": f"UTC{self.timezone_offset:+d}",
            "days": DAY_NAMES,
            "hours": list(range(24)),
            "data": matrix,
            "total_posts_analyzed": len(posts),
        }

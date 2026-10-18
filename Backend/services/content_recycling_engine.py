"""
Content Recycling Engine
=========================
Automatically identifies evergreen high-performing content and re-queues it
with fresh AI-generated captions on optimal schedules.

How it works:
1. Scans posted_content for high-performing evergreen posts
2. Applies cooldown rules (min days since last post, per-platform)
3. Generates fresh captions using AI Caption Variants
4. Re-queues into scheduled_posts with Smart Posting Times
5. Tracks recycling history to avoid audience fatigue

Usage:
    engine = ContentRecyclingEngine()
    candidates = await engine.find_recyclable_content(platform="tiktok", limit=5)
    recycled = await engine.recycle_content(candidates[0].content_id, platforms=["instagram", "threads"])
"""

import os
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from loguru import logger


# ─── Configuration ───────────────────────────────────────────────────────────

# Minimum engagement thresholds to qualify as "evergreen"
EVERGREEN_THRESHOLDS = {
    "tiktok":    {"min_views": 500,  "min_engagement_rate": 0.03, "min_likes": 20},
    "instagram": {"min_views": 300,  "min_engagement_rate": 0.04, "min_likes": 15},
    "youtube":   {"min_views": 200,  "min_engagement_rate": 0.03, "min_likes": 10},
    "twitter":   {"min_views": 100,  "min_engagement_rate": 0.02, "min_likes": 5},
    "threads":   {"min_views": 50,   "min_engagement_rate": 0.02, "min_likes": 5},
    "linkedin":  {"min_views": 100,  "min_engagement_rate": 0.03, "min_likes": 10},
    "pinterest": {"min_views": 100,  "min_engagement_rate": 0.02, "min_likes": 5},
    "facebook":  {"min_views": 200,  "min_engagement_rate": 0.02, "min_likes": 10},
    "bluesky":   {"min_views": 50,   "min_engagement_rate": 0.02, "min_likes": 3},
}

# Cooldown periods per platform (days before recycling same content)
PLATFORM_COOLDOWNS = {
    "tiktok": 14,
    "instagram": 21,
    "youtube": 30,
    "twitter": 7,
    "threads": 10,
    "linkedin": 30,
    "pinterest": 14,
    "facebook": 21,
    "bluesky": 10,
}

# Cross-platform cooldown: min days before same content appears on ANY platform
CROSS_PLATFORM_COOLDOWN = 3

# Maximum times a piece of content can be recycled
MAX_RECYCLE_COUNT = 5


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class RecyclableContent:
    """A piece of content eligible for recycling."""
    content_id: str
    media_id: Optional[str]
    media_path: Optional[str]
    original_platform: str
    original_caption: str
    original_hashtags: List[str]
    published_at: datetime
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float
    evergreen_score: float       # 0-100 composite quality score
    recycle_count: int           # How many times already recycled
    last_recycled_at: Optional[datetime]
    eligible_platforms: List[str]  # Platforms it can be recycled to


@dataclass
class RecycleResult:
    """Result of a content recycling operation."""
    content_id: str
    scheduled_post_ids: List[str]
    platforms: List[str]
    new_captions: Dict[str, str]   # platform -> caption
    scheduled_times: Dict[str, str]  # platform -> ISO time
    success: bool
    error: Optional[str] = None


# ─── Engine ──────────────────────────────────────────────────────────────────

class ContentRecyclingEngine:
    """
    Identifies high-performing evergreen content and re-queues it
    with fresh AI captions at optimal times.
    """

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

    # ── Public API ───────────────────────────────────────────────────────

    async def find_recyclable_content(
        self,
        platform: Optional[str] = None,
        limit: int = 10,
        min_age_days: int = 7,
        lookback_days: int = 180,
    ) -> List[RecyclableContent]:
        """
        Find content eligible for recycling.

        Args:
            platform: Filter by original platform (None = all)
            limit: Max candidates to return
            min_age_days: Content must be at least this old
            lookback_days: How far back to search

        Returns:
            List of RecyclableContent sorted by evergreen_score
        """
        posts = await self._fetch_high_performers(platform, min_age_days, lookback_days)

        # Score and filter
        candidates = []
        for post in posts:
            score = self._compute_evergreen_score(post)
            if score < 20:
                continue

            # Determine eligible platforms
            eligible = self._get_eligible_platforms(post)
            if not eligible:
                continue

            candidates.append(RecyclableContent(
                content_id=post["id"],
                media_id=post.get("media_id"),
                media_path=post.get("media_path"),
                original_platform=post["platform"],
                original_caption=post.get("caption", ""),
                original_hashtags=post.get("hashtags", []),
                published_at=post["published_at"],
                views=post.get("views", 0),
                likes=post.get("likes", 0),
                comments=post.get("comments", 0),
                shares=post.get("shares", 0),
                saves=post.get("saves", 0),
                engagement_rate=post.get("engagement_rate", 0),
                evergreen_score=score,
                recycle_count=post.get("recycle_count", 0),
                last_recycled_at=post.get("last_recycled_at"),
                eligible_platforms=eligible,
            ))

        # Sort by evergreen score (best first)
        candidates.sort(key=lambda c: c.evergreen_score, reverse=True)

        logger.info(
            f"[Recycler] Found {len(candidates)} recyclable candidates "
            f"from {len(posts)} high-performers"
            + (f" on {platform}" if platform else "")
        )

        return candidates[:limit]

    async def recycle_content(
        self,
        content_id: str,
        platforms: Optional[List[str]] = None,
        use_ai_captions: bool = True,
        use_smart_times: bool = True,
    ) -> RecycleResult:
        """
        Recycle a piece of content: generate fresh captions and schedule.

        Args:
            content_id: ID of the content to recycle
            platforms: Target platforms (None = all eligible)
            use_ai_captions: Generate AI caption variants
            use_smart_times: Use Smart Posting Times for scheduling

        Returns:
            RecycleResult with scheduled post details
        """
        try:
            # Fetch the original content
            original = await self._fetch_content_by_id(content_id)
            if not original:
                return RecycleResult(
                    content_id=content_id, scheduled_post_ids=[], platforms=[],
                    new_captions={}, scheduled_times={}, success=False,
                    error="Content not found"
                )

            # Determine target platforms
            eligible = self._get_eligible_platforms(original)
            if platforms:
                target_platforms = [p for p in platforms if p in eligible]
            else:
                target_platforms = eligible

            if not target_platforms:
                return RecycleResult(
                    content_id=content_id, scheduled_post_ids=[], platforms=[],
                    new_captions={}, scheduled_times={}, success=False,
                    error="No eligible platforms (cooldown not met or max recycles reached)"
                )

            # Generate fresh captions
            new_captions = {}
            if use_ai_captions and original.get("caption"):
                try:
                    from services.caption_variants_service import CaptionVariantsService
                    caption_svc = CaptionVariantsService()
                    new_captions = await caption_svc.generate_variants(
                        base_caption=original["caption"],
                        platforms=target_platforms,
                        context="Recycled evergreen content — make it feel fresh and new",
                        hashtags=original.get("hashtags", []),
                    )
                    logger.info(f"[Recycler] ✓ Generated {len(new_captions)} AI caption variants")
                except Exception as e:
                    logger.warning(f"[Recycler] AI caption generation failed: {e}")

            # Get optimal posting times
            scheduled_times = {}
            if use_smart_times:
                try:
                    from services.smart_posting_times import SmartPostingTimesService
                    time_svc = SmartPostingTimesService()
                    for plat in target_platforms:
                        window = await time_svc.suggest_time_for_post(platform=plat)
                        if window:
                            # Schedule for the next occurrence of this optimal window
                            sched_time = self._next_occurrence(window.day_of_week, window.hour_est)
                            scheduled_times[plat] = sched_time.isoformat()
                except Exception as e:
                    logger.warning(f"[Recycler] Smart times failed: {e}")

            # Create scheduled posts
            scheduled_ids = []
            for plat in target_platforms:
                caption = new_captions.get(plat, original.get("caption", ""))
                sched_time = scheduled_times.get(plat)

                post_id = await self._create_scheduled_post(
                    original=original,
                    platform=plat,
                    caption=caption,
                    scheduled_time=sched_time,
                )
                if post_id:
                    scheduled_ids.append(post_id)

            # Update recycle tracking
            await self._update_recycle_tracking(content_id, target_platforms)

            logger.success(
                f"[Recycler] ✓ Recycled content {content_id[:8]} → "
                f"{len(scheduled_ids)} posts on {target_platforms}"
            )

            return RecycleResult(
                content_id=content_id,
                scheduled_post_ids=scheduled_ids,
                platforms=target_platforms,
                new_captions=new_captions,
                scheduled_times=scheduled_times,
                success=True,
            )

        except Exception as e:
            logger.error(f"[Recycler] Recycle failed for {content_id}: {e}")
            return RecycleResult(
                content_id=content_id, scheduled_post_ids=[], platforms=[],
                new_captions={}, scheduled_times={}, success=False,
                error=str(e),
            )

    async def auto_recycle_batch(
        self,
        max_posts: int = 5,
        platforms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Automatically find and recycle the best evergreen content.
        Intended to be called by a cron/scheduler.

        Args:
            max_posts: Maximum number of posts to recycle
            platforms: Target platforms (None = all)

        Returns:
            Summary of recycling operations
        """
        candidates = await self.find_recyclable_content(limit=max_posts)

        results = []
        for candidate in candidates:
            result = await self.recycle_content(
                content_id=candidate.content_id,
                platforms=platforms,
            )
            results.append(result)

        successful = sum(1 for r in results if r.success)
        total_scheduled = sum(len(r.scheduled_post_ids) for r in results)

        summary = {
            "candidates_found": len(candidates),
            "recycled": successful,
            "failed": len(results) - successful,
            "total_posts_scheduled": total_scheduled,
            "details": [
                {
                    "content_id": r.content_id,
                    "success": r.success,
                    "platforms": r.platforms,
                    "error": r.error,
                }
                for r in results
            ],
        }

        logger.info(
            f"[Recycler] Batch complete: {successful}/{len(candidates)} recycled, "
            f"{total_scheduled} posts scheduled"
        )

        return summary

    async def get_recycling_stats(self) -> Dict[str, Any]:
        """Get overall recycling statistics."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                # Total posted content
                total = conn.execute(text(
                    "SELECT COUNT(*) FROM posted_content WHERE platform IS NOT NULL"
                )).scalar() or 0

                # Content with high engagement
                high_eng = conn.execute(text("""
                    SELECT COUNT(*) FROM posted_content
                    WHERE engagement_rate > 0.03 AND views > 100
                """)).scalar() or 0

                # Recycled posts (source = 'recycled')
                recycled = conn.execute(text("""
                    SELECT COUNT(*) FROM scheduled_posts
                    WHERE source = 'recycled'
                """)).scalar() or 0

                # Platform breakdown
                platform_counts = {}
                rows = conn.execute(text("""
                    SELECT platform, COUNT(*) FROM posted_content
                    GROUP BY platform ORDER BY COUNT(*) DESC
                """)).fetchall()
                for row in rows:
                    platform_counts[row[0]] = row[1]

            return {
                "total_published_content": total,
                "high_engagement_content": high_eng,
                "recycled_posts_created": recycled,
                "evergreen_ratio": round(high_eng / total, 2) if total > 0 else 0,
                "platform_breakdown": platform_counts,
            }

        except Exception as e:
            logger.error(f"[Recycler] Stats query failed: {e}")
            return {"error": str(e)}

    # ── Private: Data Fetching ───────────────────────────────────────────

    async def _fetch_high_performers(
        self,
        platform: Optional[str],
        min_age_days: int,
        lookback_days: int,
    ) -> List[Dict[str, Any]]:
        """Fetch published content that meets evergreen thresholds."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            cutoff_recent = datetime.now(timezone.utc) - timedelta(days=min_age_days)
            cutoff_old = datetime.now(timezone.utc) - timedelta(days=lookback_days)

            query = """
                SELECT
                    pc.id,
                    pc.platform,
                    pc.caption,
                    pc.media_path,
                    pc.published_at,
                    pc.posted_at,
                    COALESCE(pc.views, 0) as views,
                    COALESCE(pc.likes, 0) as likes,
                    COALESCE(pc.comments, 0) as comments,
                    COALESCE(pc.shares, 0) as shares,
                    COALESCE(pc.saves, 0) as saves,
                    COALESCE(pc.engagement_rate, 0) as engagement_rate,
                    sp.media_path as sp_media_path,
                    sp.hashtags as hashtags
                FROM posted_content pc
                LEFT JOIN scheduled_posts sp ON sp.id = pc.scheduled_post_id
                WHERE COALESCE(pc.published_at, pc.posted_at) < :cutoff_recent
                  AND COALESCE(pc.published_at, pc.posted_at) > :cutoff_old
                  AND pc.platform IS NOT NULL
            """
            params = {"cutoff_recent": cutoff_recent, "cutoff_old": cutoff_old}

            if platform:
                query += " AND pc.platform = :platform"
                params["platform"] = platform

            query += " ORDER BY pc.engagement_rate DESC, pc.views DESC LIMIT 100"

            with engine.connect() as conn:
                result = conn.execute(text(query), params)
                rows = result.fetchall()

            posts = []
            for row in rows:
                pub_at = row[4] or row[5]
                hashtags_raw = row[13]
                hashtags = []
                if hashtags_raw:
                    if isinstance(hashtags_raw, list):
                        hashtags = hashtags_raw
                    elif isinstance(hashtags_raw, str):
                        try:
                            hashtags = json.loads(hashtags_raw)
                        except Exception:
                            hashtags = [hashtags_raw]

                posts.append({
                    "id": str(row[0]),
                    "platform": row[1],
                    "caption": row[2] or "",
                    "media_path": row[3] or row[12],
                    "published_at": pub_at,
                    "views": row[6],
                    "likes": row[7],
                    "comments": row[8],
                    "shares": row[9],
                    "saves": row[10],
                    "engagement_rate": row[11],
                    "hashtags": hashtags,
                    "recycle_count": 0,
                    "last_recycled_at": None,
                })

            logger.debug(f"[Recycler] Fetched {len(posts)} candidate posts from DB")
            return posts

        except Exception as e:
            logger.error(f"[Recycler] DB fetch failed: {e}")
            return []

    async def _fetch_content_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single content item by ID."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        pc.id, pc.platform, pc.caption, pc.media_path,
                        pc.published_at, pc.posted_at,
                        COALESCE(pc.views, 0), COALESCE(pc.likes, 0),
                        COALESCE(pc.comments, 0), COALESCE(pc.shares, 0),
                        COALESCE(pc.saves, 0), COALESCE(pc.engagement_rate, 0),
                        sp.media_path, sp.hashtags
                    FROM posted_content pc
                    LEFT JOIN scheduled_posts sp ON sp.id = pc.scheduled_post_id
                    WHERE pc.id = :id
                """), {"id": content_id})
                row = result.fetchone()

            if not row:
                return None

            hashtags_raw = row[13]
            hashtags = []
            if hashtags_raw:
                if isinstance(hashtags_raw, list):
                    hashtags = hashtags_raw
                elif isinstance(hashtags_raw, str):
                    try:
                        hashtags = json.loads(hashtags_raw)
                    except Exception:
                        hashtags = [hashtags_raw]

            return {
                "id": str(row[0]),
                "platform": row[1],
                "caption": row[2] or "",
                "media_path": row[3] or row[12],
                "published_at": row[4] or row[5],
                "views": row[6],
                "likes": row[7],
                "comments": row[8],
                "shares": row[9],
                "saves": row[10],
                "engagement_rate": row[11],
                "hashtags": hashtags,
            }

        except Exception as e:
            logger.error(f"[Recycler] Fetch by ID failed: {e}")
            return None

    # ── Private: Scoring ─────────────────────────────────────────────────

    def _compute_evergreen_score(self, post: Dict[str, Any]) -> float:
        """
        Compute an evergreen quality score (0-100).

        Factors:
        - Engagement rate (40%)
        - View count relative to platform average (25%)
        - Save rate — high saves = evergreen (20%)
        - Comment quality — high comments = discussion-worthy (15%)
        """
        platform = post.get("platform", "tiktok")
        thresholds = EVERGREEN_THRESHOLDS.get(platform, EVERGREEN_THRESHOLDS["tiktok"])

        views = post.get("views", 0)
        likes = post.get("likes", 0)
        comments = post.get("comments", 0)
        saves = post.get("saves", 0)
        engagement_rate = post.get("engagement_rate", 0)

        # Check minimum thresholds
        if views < thresholds["min_views"]:
            return 0
        if likes < thresholds["min_likes"]:
            return 0

        # Engagement rate score (0-40)
        min_er = thresholds["min_engagement_rate"]
        er_score = min((engagement_rate / (min_er * 3)) * 40, 40)

        # View score (0-25)
        view_ratio = views / (thresholds["min_views"] * 5)
        view_score = min(view_ratio * 25, 25)

        # Save rate score (0-20) — saves indicate evergreen value
        save_rate = saves / views if views > 0 else 0
        save_score = min(save_rate * 500, 20)  # 4% save rate = max

        # Comment score (0-15) — comments indicate discussion value
        comment_rate = comments / views if views > 0 else 0
        comment_score = min(comment_rate * 300, 15)  # 5% comment rate = max

        total = er_score + view_score + save_score + comment_score

        # Penalty for already-recycled content
        recycle_count = post.get("recycle_count", 0)
        if recycle_count > 0:
            total *= max(0.5, 1.0 - (recycle_count * 0.15))

        return round(min(total, 100), 1)

    def _get_eligible_platforms(self, post: Dict[str, Any]) -> List[str]:
        """Determine which platforms this content can be recycled to."""
        original_platform = post.get("platform", "")
        recycle_count = post.get("recycle_count", 0)
        last_recycled = post.get("last_recycled_at")
        published_at = post.get("published_at")

        if recycle_count >= MAX_RECYCLE_COUNT:
            return []

        eligible = []
        now = datetime.now(timezone.utc)

        # Check cross-platform cooldown
        reference_time = last_recycled or published_at
        if reference_time:
            if isinstance(reference_time, str):
                reference_time = datetime.fromisoformat(reference_time)
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=timezone.utc)
            days_since = (now - reference_time).days
            if days_since < CROSS_PLATFORM_COOLDOWN:
                return []

        all_platforms = list(PLATFORM_COOLDOWNS.keys())
        for plat in all_platforms:
            cooldown = PLATFORM_COOLDOWNS.get(plat, 14)

            # If recycling to the same platform, use platform-specific cooldown
            if plat == original_platform:
                if published_at:
                    pub = published_at
                    if isinstance(pub, str):
                        pub = datetime.fromisoformat(pub)
                    if pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    if (now - pub).days < cooldown:
                        continue

            eligible.append(plat)

        return eligible

    # ── Private: Scheduling ──────────────────────────────────────────────

    async def _create_scheduled_post(
        self,
        original: Dict[str, Any],
        platform: str,
        caption: str,
        scheduled_time: Optional[str],
    ) -> Optional[str]:
        """Create a new scheduled_post entry for recycled content."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            post_id = str(uuid.uuid4())

            # Default to 24h from now if no smart time
            if not scheduled_time:
                sched = datetime.now(timezone.utc) + timedelta(hours=24)
                scheduled_time = sched.isoformat()

            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO scheduled_posts (
                        id, platform, caption, media_path,
                        scheduled_time, status, source,
                        recommendation_reasoning, is_ai_recommended,
                        created_at, updated_at
                    ) VALUES (
                        :id, :platform, :caption, :media_path,
                        :scheduled_time, 'scheduled', 'recycled',
                        :reasoning, true,
                        NOW(), NOW()
                    )
                """), {
                    "id": post_id,
                    "platform": platform,
                    "caption": caption,
                    "media_path": original.get("media_path"),
                    "scheduled_time": scheduled_time,
                    "reasoning": f"Recycled from {original['platform']} post {original['id'][:8]} "
                                 f"(evergreen score: views={original.get('views', 0)}, "
                                 f"engagement={original.get('engagement_rate', 0):.3f})",
                })
                conn.commit()

            logger.debug(f"[Recycler] Created scheduled post {post_id[:8]} for {platform}")
            return post_id

        except Exception as e:
            logger.error(f"[Recycler] Failed to create scheduled post: {e}")
            return None

    async def _update_recycle_tracking(
        self, content_id: str, platforms: List[str]
    ) -> None:
        """Update recycle count and timestamp on the original content."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                # Update metrics JSON with recycle info
                conn.execute(text("""
                    UPDATE posted_content
                    SET metrics = COALESCE(metrics, '{}'::jsonb) ||
                        jsonb_build_object(
                            'last_recycled_at', :now,
                            'recycle_count', COALESCE((metrics->>'recycle_count')::int, 0) + 1,
                            'recycled_to', :platforms
                        ),
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": content_id,
                    "now": datetime.now(timezone.utc).isoformat(),
                    "platforms": json.dumps(platforms),
                })
                conn.commit()

        except Exception as e:
            logger.warning(f"[Recycler] Failed to update recycle tracking: {e}")

    def _next_occurrence(self, day_of_week: int, hour_est: int) -> datetime:
        """Find the next occurrence of a specific day/hour."""
        import pytz
        est = pytz.timezone("US/Eastern")
        now_est = datetime.now(est)

        # Find next occurrence of this day of week
        days_ahead = day_of_week - now_est.weekday()
        if days_ahead < 0:
            days_ahead += 7
        elif days_ahead == 0 and now_est.hour >= hour_est:
            days_ahead += 7

        target = now_est.replace(hour=hour_est, minute=0, second=0, microsecond=0)
        target += timedelta(days=days_ahead)

        return target.astimezone(timezone.utc)

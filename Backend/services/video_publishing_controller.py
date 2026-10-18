"""
Video Publishing Controller
============================
Central control plane for all video/content publishing through Blotato.

Provides:
- Runtime-adjustable publishing config (DB-backed)
- Per-platform daily rate limits
- Global pause/resume
- Unified publish queue with priority ordering
- Daily counters with timezone-aware reset
- Event bus integration

Usage:
    controller = get_publishing_controller()
    
    # Check if we can publish
    if controller.can_publish("tiktok"):
        controller.mark_published("tiktok")
    
    # Add to queue
    controller.enqueue_video(video_url, caption, platform, account_id, ...)
    
    # Adjust limits at runtime
    controller.update_config(global_videos_per_day=6, platform_limits={"tiktok": 3})
"""
import os
import json
from datetime import datetime, timezone, timedelta, time as dt_time
from typing import Optional, List, Dict, Any
from uuid import uuid4
from dataclasses import dataclass, field, asdict
from sqlalchemy import create_engine, text
from loguru import logger

from services.event_bus import EventBus


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres"
)

# Default platform limits
DEFAULT_PLATFORM_LIMITS = {
    "tiktok": 4,
    "instagram": 3,
    "youtube": 2,
    "twitter": 4,
    "threads": 3,
    "bluesky": 2,
    "pinterest": 2,
    "linkedin": 1,
    "facebook": 2,
}

DEFAULT_POSTING_WINDOW = {
    "start": "08:00",
    "end": "23:00",
    "tz": "America/New_York",
}

DEFAULT_PRIORITY_ORDER = [
    "tiktok", "instagram", "youtube", "twitter",
    "threads", "bluesky", "pinterest", "linkedin", "facebook",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PublishingConfig:
    """Runtime publishing configuration."""
    id: int = 1
    global_enabled: bool = True
    global_videos_per_day: int = 8
    global_posts_per_day: int = 12
    platform_limits: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_PLATFORM_LIMITS))
    posting_windows: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_POSTING_WINDOW))
    min_interval_minutes: int = 30
    priority_order: List[str] = field(default_factory=lambda: list(DEFAULT_PRIORITY_ORDER))
    updated_at: Optional[datetime] = None
    updated_by: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "global_enabled": self.global_enabled,
            "global_videos_per_day": self.global_videos_per_day,
            "global_posts_per_day": self.global_posts_per_day,
            "platform_limits": self.platform_limits,
            "posting_windows": self.posting_windows,
            "min_interval_minutes": self.min_interval_minutes,
            "priority_order": self.priority_order,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }


@dataclass
class QueueItem:
    """A single item in the video publish queue."""
    id: str = field(default_factory=lambda: str(uuid4()))
    video_id: Optional[str] = None
    title: str = ""
    video_url: str = ""
    thumbnail_url: Optional[str] = None
    caption: str = ""
    hashtags: List[str] = field(default_factory=list)
    platform: str = ""
    account_id: str = ""
    account_username: str = ""
    status: str = "queued"  # queued, scheduled, publishing, published, failed, paused, cancelled
    priority: int = 5  # 1=highest, 10=lowest
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None
    blotato_submission_id: Optional[str] = None
    platform_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "video_id": self.video_id,
            "title": self.title,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "platform": self.platform,
            "account_id": self.account_id,
            "account_username": self.account_username,
            "status": self.status,
            "priority": self.priority,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "blotato_submission_id": self.blotato_submission_id,
            "platform_url": self.platform_url,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# VideoPublishingController
# =============================================================================

class VideoPublishingController:
    """
    Central control plane for Blotato video publishing.

    Sits between the PostScheduler and BlotatoService, providing:
    - DB-backed runtime config
    - Per-platform rate limiting
    - Unified queue management
    - Global pause/resume
    """

    _instance: Optional["VideoPublishingController"] = None

    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.event_bus = EventBus.get_instance()
        self._config_cache: Optional[PublishingConfig] = None
        self._daily_counters: Dict[str, int] = {}  # "platform" -> count today
        self._global_counter: int = 0
        self._counter_date: Optional[str] = None  # "YYYY-MM-DD"
        self._last_publish_times: Dict[str, datetime] = {}  # platform -> last publish time

        self._ensure_tables()
        self._load_config()
        self._load_daily_counters()

        logger.info("📤 VideoPublishingController initialized")

    @classmethod
    def get_instance(cls) -> "VideoPublishingController":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =========================================================================
    # Table Setup
    # =========================================================================

    def _ensure_tables(self):
        """Create DB tables if they don't exist."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS publishing_config (
                    id SERIAL PRIMARY KEY,
                    global_enabled BOOLEAN DEFAULT TRUE,
                    global_videos_per_day INTEGER DEFAULT 8,
                    global_posts_per_day INTEGER DEFAULT 12,
                    platform_limits JSONB DEFAULT '{}',
                    posting_windows JSONB DEFAULT '{}',
                    min_interval_minutes INTEGER DEFAULT 30,
                    priority_order JSONB DEFAULT '[]',
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_by TEXT DEFAULT 'system'
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS video_publish_queue (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    video_id TEXT,
                    title TEXT NOT NULL DEFAULT '',
                    video_url TEXT NOT NULL DEFAULT '',
                    thumbnail_url TEXT,
                    caption TEXT NOT NULL DEFAULT '',
                    hashtags JSONB DEFAULT '[]',
                    platform TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    account_username TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'queued',
                    priority INTEGER DEFAULT 5,
                    scheduled_for TIMESTAMPTZ,
                    published_at TIMESTAMPTZ,
                    blotato_submission_id TEXT,
                    platform_url TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            # Indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vpq_status ON video_publish_queue(status)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vpq_platform ON video_publish_queue(platform)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vpq_scheduled ON video_publish_queue(scheduled_for)
            """))
            # Seed default config if empty
            exists = conn.execute(text("SELECT COUNT(*) FROM publishing_config")).scalar()
            if exists == 0:
                conn.execute(text("""
                    INSERT INTO publishing_config
                        (global_enabled, global_videos_per_day, global_posts_per_day,
                         platform_limits, posting_windows, min_interval_minutes, priority_order)
                    VALUES
                        (TRUE, 8, 12, :plimits, :pwindows, 30, :porder)
                """), {
                    "plimits": json.dumps(DEFAULT_PLATFORM_LIMITS),
                    "pwindows": json.dumps(DEFAULT_POSTING_WINDOW),
                    "porder": json.dumps(DEFAULT_PRIORITY_ORDER),
                })
            conn.commit()

    # =========================================================================
    # Config Management
    # =========================================================================

    def _load_config(self) -> PublishingConfig:
        """Load config from DB into cache."""
        with self.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT * FROM publishing_config ORDER BY id LIMIT 1"
            )).fetchone()

        if row:
            self._config_cache = PublishingConfig(
                id=row[0],
                global_enabled=row[1],
                global_videos_per_day=row[2],
                global_posts_per_day=row[3],
                platform_limits=row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                posting_windows=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
                min_interval_minutes=row[6],
                priority_order=row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]"),
                updated_at=row[8],
                updated_by=row[9],
            )
        else:
            self._config_cache = PublishingConfig()

        return self._config_cache

    def get_config(self) -> PublishingConfig:
        """Get current publishing config (cached)."""
        if self._config_cache is None:
            self._load_config()
        return self._config_cache

    def update_config(self, **kwargs) -> PublishingConfig:
        """
        Update publishing config at runtime.

        Accepted kwargs:
            global_enabled, global_videos_per_day, global_posts_per_day,
            platform_limits, posting_windows, min_interval_minutes,
            priority_order, updated_by
        """
        config = self.get_config()
        set_clauses = []
        params = {}

        field_map = {
            "global_enabled": "global_enabled",
            "global_videos_per_day": "global_videos_per_day",
            "global_posts_per_day": "global_posts_per_day",
            "min_interval_minutes": "min_interval_minutes",
            "updated_by": "updated_by",
        }
        json_fields = {"platform_limits", "posting_windows", "priority_order"}

        for key, val in kwargs.items():
            if key in field_map:
                col = field_map[key]
                set_clauses.append(f"{col} = :{col}")
                params[col] = val
                setattr(config, key, val)
            elif key in json_fields:
                set_clauses.append(f"{key} = :{key}")
                params[key] = json.dumps(val) if not isinstance(val, str) else val
                setattr(config, key, val if not isinstance(val, str) else json.loads(val))

        if not set_clauses:
            return config

        set_clauses.append("updated_at = NOW()")
        sql = f"UPDATE publishing_config SET {', '.join(set_clauses)} WHERE id = :id"
        params["id"] = config.id

        with self.engine.connect() as conn:
            conn.execute(text(sql), params)
            conn.commit()

        self._load_config()
        logger.info(f"📤 Publishing config updated: {list(kwargs.keys())}")

        # Emit event
        try:
            import asyncio
            asyncio.get_event_loop().create_task(
                self.event_bus.publish("publishing.config.updated", {
                    "changes": list(kwargs.keys()),
                    "config": self._config_cache.to_dict(),
                })
            )
        except Exception:
            pass

        return self._config_cache

    def pause_all(self, updated_by: str = "api") -> PublishingConfig:
        """Pause all publishing globally."""
        return self.update_config(global_enabled=False, updated_by=updated_by)

    def resume_all(self, updated_by: str = "api") -> PublishingConfig:
        """Resume all publishing globally."""
        return self.update_config(global_enabled=True, updated_by=updated_by)

    # =========================================================================
    # Rate Limiting
    # =========================================================================

    def _load_daily_counters(self):
        """Load today's publish counts from DB."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if self._counter_date == today:
            return  # already loaded for today

        with self.engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT platform, COUNT(*) as cnt
                FROM video_publish_queue
                WHERE status = 'published'
                  AND published_at::date = CURRENT_DATE
                GROUP BY platform
            """)).fetchall()

        self._daily_counters = {row[0]: row[1] for row in rows}
        self._global_counter = sum(self._daily_counters.values())
        self._counter_date = today

    def can_publish(self, platform: str) -> bool:
        """
        Check if we're allowed to publish to this platform right now.

        Checks: global enabled, global daily limit, per-platform limit,
        minimum interval between posts.
        """
        config = self.get_config()

        # Global pause
        if not config.global_enabled:
            return False

        # Reload counters if new day
        self._load_daily_counters()

        # Global daily limit
        if self._global_counter >= config.global_videos_per_day:
            logger.debug(f"Global daily limit reached ({self._global_counter}/{config.global_videos_per_day})")
            return False

        # Per-platform limit
        platform_limit = config.platform_limits.get(platform)
        if platform_limit is not None:
            platform_count = self._daily_counters.get(platform, 0)
            if platform_count >= platform_limit:
                logger.debug(f"{platform} daily limit reached ({platform_count}/{platform_limit})")
                return False

        # Minimum interval
        last_time = self._last_publish_times.get(platform)
        if last_time and config.min_interval_minutes > 0:
            elapsed = (datetime.now(timezone.utc) - last_time).total_seconds() / 60
            if elapsed < config.min_interval_minutes:
                logger.debug(f"{platform} interval not met ({elapsed:.0f}m < {config.min_interval_minutes}m)")
                return False

        return True

    def mark_published(self, platform: str):
        """Record that a post was just published to a platform."""
        self._daily_counters[platform] = self._daily_counters.get(platform, 0) + 1
        self._global_counter += 1
        self._last_publish_times[platform] = datetime.now(timezone.utc)

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get today's publishing summary."""
        self._load_daily_counters()
        config = self.get_config()

        platform_details = {}
        for platform in config.priority_order:
            limit = config.platform_limits.get(platform, "unlimited")
            used = self._daily_counters.get(platform, 0)
            platform_details[platform] = {
                "published_today": used,
                "daily_limit": limit,
                "remaining": (limit - used) if isinstance(limit, int) else "unlimited",
            }

        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "global_enabled": config.global_enabled,
            "global_published": self._global_counter,
            "global_limit": config.global_videos_per_day,
            "global_remaining": max(0, config.global_videos_per_day - self._global_counter),
            "platforms": platform_details,
        }

    # =========================================================================
    # Queue Management
    # =========================================================================

    def enqueue_video(
        self,
        video_url: str,
        caption: str,
        platform: str,
        account_id: str,
        title: str = "",
        account_username: str = "",
        hashtags: Optional[List[str]] = None,
        priority: int = 5,
        scheduled_for: Optional[datetime] = None,
        video_id: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QueueItem:
        """Add a video to the publish queue."""
        # WATERMARK GUARD — block raw Sora videos at queue entry
        SAFE_PATH_MARKERS = ("/cleaned/", "/cleaned_", "/finals/")
        is_sora = "/sora-videos/" in video_url or "/sora_" in video_url
        is_safe = any(m in video_url for m in SAFE_PATH_MARKERS)
        if is_sora and not is_safe:
            raise ValueError(
                f"WATERMARK GUARD: Cannot queue raw Sora video '{video_url}'. "
                "Only cleaned or finals videos are allowed."
            )

        item_id = str(uuid4())
        now = datetime.now(timezone.utc)

        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO video_publish_queue
                    (id, video_id, title, video_url, thumbnail_url, caption, hashtags,
                     platform, account_id, account_username, status, priority,
                     scheduled_for, metadata, created_at, updated_at)
                VALUES
                    (:id, :video_id, :title, :video_url, :thumbnail_url, :caption, :hashtags,
                     :platform, :account_id, :account_username, 'queued', :priority,
                     :scheduled_for, :metadata, :created_at, :updated_at)
            """), {
                "id": item_id,
                "video_id": video_id,
                "title": title or caption[:60],
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "caption": caption,
                "hashtags": json.dumps(hashtags or []),
                "platform": platform,
                "account_id": account_id,
                "account_username": account_username,
                "priority": priority,
                "scheduled_for": scheduled_for,
                "metadata": json.dumps(metadata or {}),
                "created_at": now,
                "updated_at": now,
            })
            conn.commit()

        item = QueueItem(
            id=item_id,
            video_id=video_id,
            title=title or caption[:60],
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            caption=caption,
            hashtags=hashtags or [],
            platform=platform,
            account_id=account_id,
            account_username=account_username,
            priority=priority,
            scheduled_for=scheduled_for,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        logger.info(f"📤 Queued video for {platform}/@{account_username}: {title or caption[:40]}")
        return item

    def enqueue_bulk(self, items: List[Dict[str, Any]]) -> List[QueueItem]:
        """Add multiple videos to the queue at once."""
        results = []
        for item_data in items:
            item = self.enqueue_video(**item_data)
            results.append(item)
        return results

    def get_queue(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[QueueItem]:
        """Get queue items with optional filters."""
        conditions = []
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if platform:
            conditions.append("platform = :platform")
            params["platform"] = platform
        if status:
            conditions.append("status = :status")
            params["status"] = status

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with self.engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT id, video_id, title, video_url, thumbnail_url, caption, hashtags,
                       platform, account_id, account_username, status, priority,
                       scheduled_for, published_at, blotato_submission_id, platform_url,
                       error_message, retry_count, metadata, created_at, updated_at
                FROM video_publish_queue
                {where}
                ORDER BY
                    CASE status
                        WHEN 'publishing' THEN 0
                        WHEN 'queued' THEN 1
                        WHEN 'scheduled' THEN 2
                        WHEN 'paused' THEN 3
                        WHEN 'failed' THEN 4
                        WHEN 'published' THEN 5
                        WHEN 'cancelled' THEN 6
                        ELSE 7
                    END,
                    priority ASC,
                    scheduled_for ASC NULLS LAST,
                    created_at ASC
                LIMIT :limit OFFSET :offset
            """), params).fetchall()

        return [self._row_to_queue_item(r) for r in rows]

    def get_queue_item(self, item_id: str) -> Optional[QueueItem]:
        """Get a single queue item by ID."""
        with self.engine.connect() as conn:
            row = conn.execute(text("""
                SELECT id, video_id, title, video_url, thumbnail_url, caption, hashtags,
                       platform, account_id, account_username, status, priority,
                       scheduled_for, published_at, blotato_submission_id, platform_url,
                       error_message, retry_count, metadata, created_at, updated_at
                FROM video_publish_queue
                WHERE id = :id
            """), {"id": item_id}).fetchone()

        return self._row_to_queue_item(row) if row else None

    def update_queue_item(self, item_id: str, **kwargs) -> bool:
        """
        Update a queue item. Accepted fields:
        caption, hashtags, priority, scheduled_for, status, error_message, metadata
        """
        allowed = {
            "caption", "priority", "scheduled_for", "status",
            "error_message", "blotato_submission_id", "platform_url",
            "published_at", "retry_count", "title",
        }
        json_fields = {"hashtags", "metadata"}

        set_clauses = ["updated_at = NOW()"]
        params: Dict[str, Any] = {"id": item_id}

        for key, val in kwargs.items():
            if key in allowed:
                set_clauses.append(f"{key} = :{key}")
                params[key] = val
            elif key in json_fields:
                set_clauses.append(f"{key} = :{key}")
                params[key] = json.dumps(val) if not isinstance(val, str) else val

        sql = f"UPDATE video_publish_queue SET {', '.join(set_clauses)} WHERE id = :id"

        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()
            return result.rowcount > 0

    def pause_item(self, item_id: str) -> bool:
        """Pause a queued/scheduled item."""
        return self.update_queue_item(item_id, status="paused")

    def resume_item(self, item_id: str) -> bool:
        """Resume a paused item back to queued."""
        return self.update_queue_item(item_id, status="queued")

    def cancel_item(self, item_id: str) -> bool:
        """Cancel a queue item."""
        return self.update_queue_item(item_id, status="cancelled")

    def retry_item(self, item_id: str) -> bool:
        """Retry a failed item."""
        return self.update_queue_item(item_id, status="queued", retry_count=0, error_message=None)

    def delete_item(self, item_id: str) -> bool:
        """Permanently delete a queue item."""
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "DELETE FROM video_publish_queue WHERE id = :id"
            ), {"id": item_id})
            conn.commit()
            return result.rowcount > 0

    def reschedule_item(self, item_id: str, new_time: datetime) -> bool:
        """Reschedule a queue item to a new time."""
        return self.update_queue_item(item_id, scheduled_for=new_time, status="scheduled")

    def set_priority(self, item_id: str, priority: int) -> bool:
        """Change an item's priority (1=highest, 10=lowest)."""
        return self.update_queue_item(item_id, priority=max(1, min(10, priority)))

    # =========================================================================
    # Queue Processing — dequeue + publish via Blotato
    # =========================================================================

    async def process_next_item(self) -> Dict[str, Any]:
        """
        Atomically dequeue the next ready item and publish it via Blotato.

        Returns dict with success status and details.
        """
        from pathlib import Path

        # 1. Atomically claim next queued item
        with self.engine.connect() as conn:
            row = conn.execute(text("""
                UPDATE video_publish_queue
                SET status = 'publishing', updated_at = NOW()
                WHERE id = (
                    SELECT id FROM video_publish_queue
                    WHERE status = 'queued'
                      AND (scheduled_for IS NULL OR scheduled_for <= NOW())
                    ORDER BY priority ASC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, video_url, caption, title, hashtags,
                          platform, account_id, account_username, metadata
            """)).fetchone()
            conn.commit()

        if not row:
            return {"success": False, "reason": "no_items", "message": "No queued items ready"}

        item_id = str(row[0])
        video_url = row[1]
        caption = row[2] or ""
        title = row[3] or ""
        hashtags = row[4] if isinstance(row[4], list) else json.loads(row[4] or "[]")
        platform = row[5]
        account_id = row[6]
        account_username = row[7] or ""
        metadata = row[8] if isinstance(row[8], dict) else json.loads(row[8] or "{}")

        logger.info(f"📤 Processing queue item {item_id}: {title} → {platform}/@{account_username}")

        # 2. WATERMARK GUARD — reject raw Sora videos (last line of defense)
        SAFE_PATH_MARKERS = ("/cleaned/", "/cleaned_", "/finals/")
        is_sora_video = "/sora-videos/" in video_url or "/sora_" in video_url
        is_watermark_free = any(marker in video_url for marker in SAFE_PATH_MARKERS)

        if is_sora_video and not is_watermark_free:
            error_msg = (
                f"WATERMARK GUARD: Blocked raw Sora video '{video_url}'. "
                "Only cleaned/finals videos may be published."
            )
            logger.error(f"🚫 {error_msg}")
            self.update_queue_item(item_id, status="failed", error_message=error_msg)
            return {"success": False, "item_id": item_id, "reason": "watermark_blocked", "error": error_msg}

        # 3. Check rate limits
        if not self.can_publish(platform):
            self.update_queue_item(item_id, status="queued")
            return {"success": False, "reason": "rate_limited", "platform": platform}

        # 3. Publish via PublishService
        try:
            from services.publish_service import PublishService
            publish_svc = PublishService()

            file_path = Path(video_url)
            if not file_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_url}")

            # Build caption with hashtags
            full_caption = caption
            if hashtags:
                tag_str = " ".join(f"#{h}" if not h.startswith("#") else h for h in hashtags)
                if tag_str not in full_caption:
                    full_caption = f"{full_caption}\n\n{tag_str}"

            # Platform-specific target config
            target_config: Dict[str, Any] = {}
            if platform == "youtube":
                target_config = {
                    "title": title or caption[:100],
                    "privacyStatus": "public",
                    "shouldNotifySubscribers": True,
                    "isMadeForKids": False,
                }
            elif platform == "tiktok":
                target_config = {
                    "title": title[:150] if title else "",
                    "privacyLevel": "PUBLIC_TO_EVERYONE",
                    "isAiGenerated": True,
                }
            elif platform == "instagram":
                target_config = {"mediaType": "reel"}

            result = await publish_svc.full_publish_flow(
                file_path=file_path,
                account_id=account_id,
                platform=platform,
                text=full_caption,
                target_config=target_config,
            )

            if result.get("success"):
                self.update_queue_item(
                    item_id,
                    status="published",
                    published_at=datetime.now(timezone.utc),
                    blotato_submission_id=result.get("post_submission_id"),
                    platform_url=result.get("steps", {}).get("publish", {}).get("platform_url"),
                )
                self.mark_published(platform)
                logger.info(f"✅ Published {item_id} to {platform}: {result.get('post_submission_id')}")
                return {"success": True, "item_id": item_id, "platform": platform, "result": result}
            else:
                error = result.get("error", "Unknown error")
                self.update_queue_item(item_id, status="failed", error_message=error)
                logger.error(f"❌ Publish failed for {item_id}: {error}")
                return {"success": False, "item_id": item_id, "error": error}

        except Exception as e:
            error_msg = str(e)
            self.update_queue_item(item_id, status="failed", error_message=error_msg)
            logger.error(f"❌ Exception publishing {item_id}: {error_msg}")
            return {"success": False, "item_id": item_id, "error": error_msg}

    async def process_batch(self, max_items: int = 5) -> Dict[str, Any]:
        """Process up to max_items from the queue, respecting rate limits."""
        results = []
        for _ in range(max_items):
            result = await self.process_next_item()
            results.append(result)
            if result.get("reason") in ("no_items", "rate_limited"):
                break
        published = sum(1 for r in results if r.get("success"))
        failed = sum(1 for r in results if not r.get("success") and r.get("item_id"))
        return {
            "processed": len(results),
            "published": published,
            "failed": failed,
            "results": results,
        }

    # =========================================================================
    # Queue Stats
    # =========================================================================

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self.engine.connect() as conn:
            # By status
            status_rows = conn.execute(text("""
                SELECT status, COUNT(*) FROM video_publish_queue
                GROUP BY status
            """)).fetchall()

            # By platform (active only)
            platform_rows = conn.execute(text("""
                SELECT platform, COUNT(*) FROM video_publish_queue
                WHERE status IN ('queued', 'scheduled', 'publishing')
                GROUP BY platform
            """)).fetchall()

            # Upcoming 24h
            upcoming_24h = conn.execute(text("""
                SELECT COUNT(*) FROM video_publish_queue
                WHERE status IN ('queued', 'scheduled')
                  AND (scheduled_for IS NULL OR scheduled_for <= NOW() + INTERVAL '24 hours')
            """)).scalar() or 0

            # Next scheduled
            next_item = conn.execute(text("""
                SELECT id, title, platform, scheduled_for FROM video_publish_queue
                WHERE status IN ('queued', 'scheduled')
                ORDER BY
                    priority ASC,
                    scheduled_for ASC NULLS LAST,
                    created_at ASC
                LIMIT 1
            """)).fetchone()

        return {
            "by_status": {row[0]: row[1] for row in status_rows},
            "by_platform": {row[0]: row[1] for row in platform_rows},
            "upcoming_24h": upcoming_24h,
            "total_active": sum(
                row[1] for row in status_rows
                if row[0] in ("queued", "scheduled", "publishing")
            ),
            "next_item": {
                "id": str(next_item[0]),
                "title": next_item[1],
                "platform": next_item[2],
                "scheduled_for": next_item[3].isoformat() if next_item[3] else None,
            } if next_item else None,
        }

    def get_history(
        self,
        days: int = 7,
        platform: Optional[str] = None,
        limit: int = 100,
    ) -> List[QueueItem]:
        """Get published history."""
        conditions = ["status = 'published'"]
        params: Dict[str, Any] = {"days": days, "limit": limit}

        if platform:
            conditions.append("platform = :platform")
            params["platform"] = platform

        where = "WHERE " + " AND ".join(conditions)

        with self.engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT id, video_id, title, video_url, thumbnail_url, caption, hashtags,
                       platform, account_id, account_username, status, priority,
                       scheduled_for, published_at, blotato_submission_id, platform_url,
                       error_message, retry_count, metadata, created_at, updated_at
                FROM video_publish_queue
                {where}
                  AND published_at >= NOW() - MAKE_INTERVAL(days => :days)
                ORDER BY published_at DESC
                LIMIT :limit
            """), params).fetchall()

        return [self._row_to_queue_item(r) for r in rows]

    # =========================================================================
    # Full Status
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get full publishing status for dashboard."""
        return {
            "config": self.get_config().to_dict(),
            "daily_summary": self.get_daily_summary(),
            "queue_stats": self.get_queue_stats(),
        }

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _row_to_queue_item(self, row) -> QueueItem:
        """Convert a DB row to a QueueItem."""
        return QueueItem(
            id=str(row[0]),
            video_id=row[1],
            title=row[2] or "",
            video_url=row[3] or "",
            thumbnail_url=row[4],
            caption=row[5] or "",
            hashtags=row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]"),
            platform=row[7] or "",
            account_id=row[8] or "",
            account_username=row[9] or "",
            status=row[10] or "queued",
            priority=row[11] or 5,
            scheduled_for=row[12],
            published_at=row[13],
            blotato_submission_id=row[14],
            platform_url=row[15],
            error_message=row[16],
            retry_count=row[17] or 0,
            metadata=row[18] if isinstance(row[18], dict) else json.loads(row[18] or "{}"),
            created_at=row[19],
            updated_at=row[20],
        )


# =============================================================================
# Singleton Accessor
# =============================================================================

_controller: Optional[VideoPublishingController] = None


def get_publishing_controller() -> VideoPublishingController:
    """Get the global VideoPublishingController instance."""
    global _controller
    if _controller is None:
        _controller = VideoPublishingController()
    return _controller

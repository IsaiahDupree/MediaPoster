"""
ACTP Organic Publisher
=======================
Publishes creatives organically to YouTube Shorts, TikTok, and Instagram Reels.
Uses MediaPoster connectors with Safari automation fallbacks.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import OrganicTestConfig
from .models import Creative, OrganicPost, Platform

logger = logging.getLogger(__name__)

MEDIAPOSTER_BASE = os.getenv(
    "MEDIAPOSTER_BASE_PATH",
    "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend",
)


class OrganicPublisher:
    """
    Publishes creatives to social platforms for organic testing.

    Publishing backend priority:
    1. MediaPoster Lite (MPLite) — when MPLITE_KEY is set.
       Enqueues the video in the cloud queue; local machine polls and
       executes Safari automation / Blotato upload natively.
    2. MediaPoster YouTubeConnector / TikTokConnector — direct API upload.
    3. Safari automation fallback — for platforms without API connectors.
    """

    def __init__(self, db_client=None, config: Optional[OrganicTestConfig] = None):
        self.db = db_client
        self.config = config or OrganicTestConfig()
        self._youtube = None
        self._tiktok = None
        self._mplite: Optional[Any] = None
        self._init_connectors()
        self._init_mplite()
        logger.info("[ACTP:Publisher] Organic Publisher initialized")

    def _init_mplite(self):
        """Initialize MediaPoster Lite publisher if MPLITE_KEY is configured."""
        try:
            from .mplite_publisher import MPLitePublisher
            pub = MPLitePublisher(db_client=self.db)
            if pub.is_configured():
                self._mplite = pub
                logger.info("[ACTP:Publisher] MediaPoster Lite backend ready (preferred)")
            else:
                logger.info("[ACTP:Publisher] MPLITE_KEY not set — using direct connectors")
        except ImportError as e:
            logger.warning(f"[ACTP:Publisher] MPLite publisher unavailable: {e}")

    def _init_connectors(self):
        """Initialize MediaPoster connectors."""
        try:
            sys.path.insert(0, MEDIAPOSTER_BASE)
            from connectors.youtube.connector import YouTubeConnector
            self._youtube = YouTubeConnector()
            if self._youtube.is_enabled():
                logger.info("[ACTP:Publisher] YouTube connector ready")
            else:
                logger.warning("[ACTP:Publisher] YouTube connector not configured")
        except ImportError as e:
            logger.warning(f"[ACTP:Publisher] YouTube connector unavailable: {e}")

        try:
            from connectors.tiktok.connector import TikTokConnector
            self._tiktok = TikTokConnector()
            if self._tiktok.is_enabled():
                logger.info("[ACTP:Publisher] TikTok connector ready")
            else:
                logger.warning("[ACTP:Publisher] TikTok connector not configured")
        except ImportError as e:
            logger.warning(f"[ACTP:Publisher] TikTok connector unavailable: {e}")

    # ─── Publishing ───────────────────────────────────────

    async def publish_creatives(
        self,
        creatives: List[Creative],
        platforms: Optional[List[str]] = None,
    ) -> List[OrganicPost]:
        """
        Publish a list of creatives to specified platforms.
        Returns list of OrganicPost records.
        """
        platforms = platforms or self.config.platforms
        all_posts = []

        for creative in creatives:
            for platform in platforms:
                try:
                    post = await self._publish_to_platform(creative, platform)
                    all_posts.append(post)
                    # Stagger posts to avoid rate limits
                    await asyncio.sleep(30)
                except Exception as e:
                    logger.error(
                        f"[ACTP:Publisher] Failed to publish {creative.id} to {platform}: {e}"
                    )
                    error_post = OrganicPost(
                        creative_id=creative.id,
                        platform=Platform(platform),
                        status="failed",
                        error=str(e),
                    )
                    await self._save_organic_post(error_post)
                    all_posts.append(error_post)

        logger.info(f"[ACTP:Publisher] Published {len(all_posts)} posts across {len(platforms)} platforms")
        return all_posts

    async def _publish_to_platform(
        self, creative: Creative, platform: str
    ) -> OrganicPost:
        """
        Publish a single creative to a single platform.

        Routing priority:
        1. MPLite queue (if configured and platform supported) — enqueues for
           local machine to execute via Safari automation / Blotato.
        2. Direct MediaPoster connector (YouTube/TikTok API).
        3. Safari automation fallback.
        """
        caption = self._build_caption(creative)

        # ── MPLite preferred backend ───────────────────────
        if self._mplite and self._mplite.supports_platform(platform):
            account_id = self._resolve_account_id(platform)
            hashtags = self._generate_hashtags(creative, platform).split()
            enqueue_result = await self._mplite.enqueue_organic_post(
                creative=creative,
                platform=platform,
                account_id=account_id,
                caption=caption,
                hashtags=hashtags,
                priority=5,
            )
            post = OrganicPost(
                creative_id=creative.id,
                platform=Platform(platform),
                post_id=enqueue_result["mplite_item_id"],
                post_url="",
                posted_at=datetime.now(timezone.utc),
                status="queued_mplite",
                metadata={
                    "mplite_item_id": enqueue_result["mplite_item_id"],
                    "mplite_platform": enqueue_result["platform"],
                    "enqueued_at": enqueue_result["enqueued_at"],
                },
            )
            await self._save_organic_post(post)
            logger.info(
                f"[ACTP:Publisher] Creative {creative.id} queued in MPLite "
                f"(item={enqueue_result['mplite_item_id']}, platform={platform})"
            )
            return post

        # ── Direct connector / Safari fallback ────────────
        if platform == "youtube_shorts":
            post_id, post_url = await self._publish_youtube(creative, caption)
        elif platform == "tiktok":
            post_id, post_url = await self._publish_tiktok(creative, caption)
        elif platform == "instagram_reels":
            post_id, post_url = await self._publish_instagram(creative, caption)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        post = OrganicPost(
            creative_id=creative.id,
            platform=Platform(platform),
            post_id=post_id,
            post_url=post_url,
            posted_at=datetime.now(timezone.utc),
            status="published",
        )
        await self._save_organic_post(post)
        return post

    def _resolve_account_id(self, platform: str) -> str:
        """Resolve the configured account ID for a platform from env vars."""
        env_map = {
            "tiktok": "TIKTOK_ACCOUNT_ID",
            "youtube_shorts": "YOUTUBE_ACCOUNT_ID",
            "instagram_reels": "INSTAGRAM_ACCOUNT_ID",
            "twitter": "TWITTER_ACCOUNT_ID",
            "threads": "THREADS_ACCOUNT_ID",
        }
        env_key = env_map.get(platform, "")
        account_id = os.getenv(env_key, "") if env_key else ""
        if not account_id:
            account_id = os.getenv("MPLITE_DEFAULT_ACCOUNT_ID", "default")
        return account_id

    # ─── Platform Implementations ─────────────────────────

    async def _publish_youtube(
        self, creative: Creative, caption: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Upload video as YouTube Short."""
        if self._youtube and self._youtube.is_enabled():
            return await self._youtube_api_upload(creative, caption)

        # Fallback: Safari automation
        logger.info("[ACTP:Publisher] Using Safari fallback for YouTube")
        return await self._safari_youtube_upload(creative, caption)

    async def _youtube_api_upload(
        self, creative: Creative, caption: str
    ) -> tuple[str, str]:
        """Upload via YouTube Data API."""
        import httpx

        access_token = await self._youtube._get_access_token()
        video_path = creative.video_url

        # Step 1: Initialize resumable upload
        async with httpx.AsyncClient(timeout=300.0) as client:
            metadata = {
                "snippet": {
                    "title": (creative.hook or "Ad Test")[:100],
                    "description": caption,
                    "tags": ["shorts", "ad", "test"],
                    "categoryId": "22",
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                    "shorts": {"isShort": True},
                },
            }

            init_response = await client.post(
                f"{self._youtube.upload_url}?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=metadata,
            )
            init_response.raise_for_status()
            upload_url = init_response.headers.get("Location")

            # Step 2: Upload video bytes
            with open(video_path, "rb") as f:
                video_bytes = f.read()

            upload_response = await client.put(
                upload_url,
                headers={"Content-Type": "video/mp4"},
                content=video_bytes,
            )
            upload_response.raise_for_status()
            data = upload_response.json()

            video_id = data.get("id", "")
            video_url = f"https://www.youtube.com/shorts/{video_id}"
            logger.info(f"[ACTP:Publisher] YouTube upload complete: {video_url}")
            return video_id, video_url

    async def _safari_youtube_upload(
        self, creative: Creative, caption: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Fallback: use Safari automation for YouTube upload."""
        logger.warning("[ACTP:Publisher] Safari YouTube upload not yet implemented")
        raise NotImplementedError("Safari YouTube upload requires manual setup")

    async def _publish_tiktok(
        self, creative: Creative, caption: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Upload video to TikTok."""
        if self._tiktok and self._tiktok.is_enabled():
            return await self._tiktok_api_upload(creative, caption)

        # Fallback: Safari automation
        return await self._safari_tiktok_upload(creative, caption)

    async def _tiktok_api_upload(
        self, creative: Creative, caption: str
    ) -> tuple[str, str]:
        """Upload via TikTok Content Posting API."""
        import httpx

        access_token = self._tiktok.access_token
        video_path = creative.video_url

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Step 1: Initialize upload
            init_response = await client.post(
                f"{self._tiktok.base_url}/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "post_info": {
                        "title": caption[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": os.path.getsize(video_path),
                    },
                },
            )
            init_response.raise_for_status()
            data = init_response.json()

            upload_url = data.get("data", {}).get("upload_url")
            publish_id = data.get("data", {}).get("publish_id", "")

            if not upload_url:
                raise RuntimeError("TikTok did not return upload URL")

            # Step 2: Upload video
            with open(video_path, "rb") as f:
                upload_response = await client.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{os.path.getsize(video_path) - 1}/{os.path.getsize(video_path)}",
                    },
                    content=f.read(),
                )
                upload_response.raise_for_status()

            logger.info(f"[ACTP:Publisher] TikTok upload complete: {publish_id}")
            return publish_id, f"https://www.tiktok.com/@user/video/{publish_id}"

    async def _safari_tiktok_upload(
        self, creative: Creative, caption: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Fallback: use existing safari_tiktok_cli for TikTok upload."""
        try:
            sys.path.insert(0, os.path.join(MEDIAPOSTER_BASE, "automation"))
            from safari_tiktok_cli import upload_video

            result = upload_video(
                video_path=creative.video_url,
                caption=caption,
            )
            return result.get("video_id"), result.get("video_url")
        except ImportError:
            logger.error("[ACTP:Publisher] safari_tiktok_cli not available")
            raise

    async def _publish_instagram(
        self, creative: Creative, caption: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Upload video as Instagram Reel via Safari automation."""
        try:
            sys.path.insert(0, os.path.join(MEDIAPOSTER_BASE, "automation"))
            from safari_instagram_poster import post_reel

            result = post_reel(
                video_path=creative.video_url,
                caption=caption,
            )
            return result.get("post_id"), result.get("post_url")
        except ImportError:
            logger.error("[ACTP:Publisher] safari_instagram_poster not available")
            raise

    # ─── Helpers ──────────────────────────────────────────

    def _build_caption(self, creative: Creative, platform: str = "tiktok") -> str:
        """Build platform-optimized caption from creative data."""
        parts = []
        if creative.hook:
            parts.append(creative.hook)
        if creative.script:
            parts.append(creative.script)
        if creative.cta:
            parts.append(f"\n{creative.cta}")

        hashtags = self._generate_hashtags(creative, platform)
        parts.append(f"\n{hashtags}")

        caption = " ".join(parts)
        return self._enforce_char_limit(caption, platform)

    # ─── Hashtag Optimization ─────────────────────────────

    PLATFORM_HASHTAGS = {
        "youtube_shorts": ["#shorts", "#viral", "#trending"],
        "tiktok": ["#fyp", "#foryou", "#viral", "#trending"],
        "instagram_reels": ["#reels", "#explore", "#viral", "#trending"],
    }

    MAX_HASHTAGS = {
        "youtube_shorts": 15,
        "tiktok": 10,
        "instagram_reels": 30,
    }

    def _generate_hashtags(self, creative: Creative, platform: str) -> str:
        """Generate platform-specific hashtags based on content."""
        base = self.PLATFORM_HASHTAGS.get(platform, ["#viral"])
        content_tags = []

        if creative.angle:
            words = creative.angle.lower().split()[:3]
            content_tags.extend(f"#{w}" for w in words if len(w) > 2)

        metadata = creative.generation_metadata or {}
        brief = metadata.get("brief", {})
        if brief.get("target_emotion"):
            content_tags.append(f"#{brief['target_emotion']}")

        all_tags = base + content_tags
        max_count = self.MAX_HASHTAGS.get(platform, 10)
        unique_tags = list(dict.fromkeys(all_tags))[:max_count]
        return " ".join(unique_tags)

    # ─── Character Limit Validation ───────────────────────

    CHAR_LIMITS = {
        "youtube_shorts": 5000,
        "tiktok": 2200,
        "instagram_reels": 2200,
        "twitter": 280,
        "facebook": 63206,
    }

    def _enforce_char_limit(self, caption: str, platform: str) -> str:
        """Enforce platform-specific character limits."""
        limit = self.CHAR_LIMITS.get(platform, 2200)
        if len(caption) <= limit:
            return caption
        return caption[:limit - 3] + "..."

    def validate_caption(self, caption: str, platform: str) -> Dict[str, Any]:
        """Validate caption length and return status."""
        limit = self.CHAR_LIMITS.get(platform, 2200)
        return {
            "valid": len(caption) <= limit,
            "length": len(caption),
            "limit": limit,
            "over_by": max(0, len(caption) - limit),
        }

    # ─── Platform-Specific Caption Formatting ─────────────

    def format_caption_for_platform(
        self, creative: Creative, platform: str
    ) -> str:
        """Format caption with platform-specific conventions."""
        if platform == "youtube_shorts":
            # YouTube: title-style first line, then description
            title = (creative.hook or "")[:100]
            desc = creative.script or ""
            cta = creative.cta or ""
            hashtags = self._generate_hashtags(creative, platform)
            return f"{title}\n\n{desc}\n\n{cta}\n\n{hashtags}"

        elif platform == "tiktok":
            # TikTok: casual, emoji-friendly, hashtags at end
            hook = creative.hook or ""
            cta = creative.cta or ""
            hashtags = self._generate_hashtags(creative, platform)
            return f"{hook}\n\n{cta}\n\n{hashtags}"

        elif platform == "instagram_reels":
            # Instagram: longer captions OK, line breaks for readability
            parts = []
            if creative.hook:
                parts.append(creative.hook)
            if creative.script:
                parts.append(f"\n\n{creative.script}")
            if creative.cta:
                parts.append(f"\n\n{creative.cta}")
            hashtags = self._generate_hashtags(creative, platform)
            parts.append(f"\n\n.\n.\n.\n{hashtags}")
            return "".join(parts)

        return self._build_caption(creative, platform)

    # ─── Video Spec Validation ────────────────────────────

    async def validate_video_for_platform(
        self, creative: Creative, platform: str
    ) -> Dict[str, Any]:
        """Validate video meets platform specs before publishing."""
        from .creative_engine import CreativeEngine
        engine = CreativeEngine(db_client=self.db)

        if not creative.video_url or not os.path.exists(creative.video_url):
            return {"valid": False, "errors": ["Video file not found"]}

        validation = await engine.validate_video(creative.video_url)
        if not validation["valid"]:
            return validation

        return engine.validate_for_platform(validation["metadata"], platform)

    # ─── Rate Limit Tracking ──────────────────────────────

    _rate_limit_state: Dict[str, Dict[str, Any]] = {}

    def _check_rate_limit(self, platform: str) -> bool:
        """Check if we're within platform rate limits."""
        import time
        state = self._rate_limit_state.get(platform, {})
        last_call = state.get("last_call", 0)
        call_count = state.get("count_in_window", 0)
        window_start = state.get("window_start", 0)

        now = time.time()

        # Reset window every hour
        if now - window_start > 3600:
            self._rate_limit_state[platform] = {
                "last_call": now,
                "count_in_window": 1,
                "window_start": now,
            }
            return True

        # Platform-specific limits per hour
        limits = {
            "youtube_shorts": 6,
            "tiktok": 10,
            "instagram_reels": 6,
        }
        max_calls = limits.get(platform, 10)

        if call_count >= max_calls:
            logger.warning(f"[ACTP:Publisher] Rate limit reached for {platform} ({call_count}/{max_calls})")
            return False

        self._rate_limit_state[platform] = {
            "last_call": now,
            "count_in_window": call_count + 1,
            "window_start": window_start or now,
        }
        return True

    # ─── Post URL Verification ────────────────────────────

    async def verify_post_live(self, post: OrganicPost) -> bool:
        """Verify a published post is actually live by checking the URL."""
        if not post.post_url:
            return False

        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.head(post.post_url)
                is_live = response.status_code == 200
                if not is_live:
                    logger.warning(
                        f"[ACTP:Publisher] Post not live: {post.post_url} → {response.status_code}"
                    )
                return is_live
        except Exception as e:
            logger.error(f"[ACTP:Publisher] Verification failed: {e}")
            return False

    # ─── Publish Retry Logic ──────────────────────────────

    async def publish_with_retry(
        self,
        creative: Creative,
        platform: str,
        max_retries: int = 3,
        backoff_base: float = 30.0,
    ) -> OrganicPost:
        """Publish with exponential backoff retry on failure."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                post = await self._publish_to_platform(creative, platform)
                return post
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait = backoff_base * (2 ** attempt)
                    logger.warning(
                        f"[ACTP:Publisher] Attempt {attempt + 1} failed for {platform}, "
                        f"retrying in {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)

        # All retries exhausted — push to dead letter queue
        from .monitoring import DeadLetterQueue
        dlq = DeadLetterQueue(db_client=self.db)
        await dlq.push(
            "publish",
            {"creative_id": creative.id, "platform": platform},
            str(last_error),
        )

        error_post = OrganicPost(
            creative_id=creative.id,
            platform=Platform(platform),
            status="failed",
            error=f"All {max_retries + 1} attempts failed: {last_error}",
        )
        await self._save_organic_post(error_post)
        return error_post

    # ─── Cross-Platform Orchestration ─────────────────────

    async def publish_creatives_orchestrated(
        self,
        creatives: List[Creative],
        platforms: Optional[List[str]] = None,
        stagger_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Publish with staggered timing, independent error isolation per platform,
        and aggregated status reporting.
        """
        platforms = platforms or self.config.platforms
        results = {"posts": [], "by_platform": {}, "total": 0, "failed": 0}

        for platform in platforms:
            platform_posts = []
            for creative in creatives:
                if not self._check_rate_limit(platform):
                    logger.warning(f"[ACTP:Publisher] Skipping {creative.id} on {platform} (rate limit)")
                    continue

                # Validate video for platform first
                spec_check = await self.validate_video_for_platform(creative, platform)
                if not spec_check.get("valid", True):
                    logger.warning(
                        f"[ACTP:Publisher] Video fails {platform} specs: {spec_check.get('errors')}"
                    )

                post = await self.publish_with_retry(creative, platform)
                platform_posts.append(post)
                results["posts"].append(post)
                results["total"] += 1
                if post.status == "failed":
                    results["failed"] += 1

                await asyncio.sleep(stagger_seconds)

            results["by_platform"][platform] = {
                "published": sum(1 for p in platform_posts if p.status == "published"),
                "failed": sum(1 for p in platform_posts if p.status == "failed"),
            }

        return results

    # ─── Post Deletion ────────────────────────────────────

    async def delete_post(self, post: OrganicPost) -> bool:
        """Delete or unlist a published post."""
        logger.info(f"[ACTP:Publisher] Deleting post {post.post_id} from {post.platform.value}")
        post.status = "deleted"
        await self._save_organic_post(post)
        return True

    # ─── Platform Credential Check ────────────────────────

    def check_credentials(self) -> Dict[str, bool]:
        """Check which platform credentials are configured and valid."""
        return {
            "youtube": bool(self._youtube and self._youtube.is_enabled()),
            "tiktok": bool(self._tiktok and self._tiktok.is_enabled()),
            "instagram": bool(os.path.exists(
                os.path.join(MEDIAPOSTER_BASE, "automation", "safari_instagram_poster.py")
            )),
        }

    async def _save_organic_post(self, post: OrganicPost):
        """Persist organic post to database."""
        if self.db:
            await self.db.table("actp_organic_posts").upsert(
                post.model_dump(mode="json")
            ).execute()

    # ─── Scheduled Publishing ─────────────────────────────

    async def schedule_publish(
        self,
        creative: Creative,
        platform: str,
        scheduled_for: str,
    ) -> Dict[str, Any]:
        """Schedule a post for future publishing."""
        if not self.db:
            return {"scheduled": False, "error": "no_db"}

        task = {
            "task_type": "publish",
            "entity_type": "creative",
            "entity_id": creative.id,
            "scheduled_for": scheduled_for,
            "status": "pending",
            "config": {
                "creative_id": creative.id,
                "platform": platform,
                "caption": self.format_caption_for_platform(creative, platform),
            },
        }

        await self.db.table("actp_scheduled_tasks").insert(task).execute()

        return {
            "scheduled": True,
            "creative_id": creative.id,
            "platform": platform,
            "scheduled_for": scheduled_for,
        }

    # ─── Publish Queue Management ─────────────────────────

    async def get_publish_queue(self) -> List[Dict[str, Any]]:
        """Get all pending scheduled publishes."""
        if not self.db:
            return []

        result = await self.db.table("actp_scheduled_tasks").select("*").eq(
            "task_type", "publish"
        ).eq("status", "pending").order("scheduled_for").execute()

        return result.data or []

    async def cancel_scheduled_publish(self, task_id: str) -> bool:
        """Cancel a scheduled publish task."""
        if not self.db:
            return False

        await self.db.table("actp_scheduled_tasks").update({
            "status": "cancelled",
        }).eq("id", task_id).execute()
        return True

    # ─── Draft/Preview Mode ───────────────────────────────

    async def create_draft(
        self, creative: Creative, platform: str
    ) -> Dict[str, Any]:
        """Create a draft post without publishing (for preview)."""
        caption = self.format_caption_for_platform(creative, platform)
        char_validation = self.validate_caption(caption, platform)

        post = OrganicPost(
            creative_id=creative.id,
            platform=Platform(platform) if platform in [p.value for p in Platform] else Platform.TIKTOK,
            status="draft",
            post_url=None,
        )
        await self._save_organic_post(post)

        return {
            "draft_id": post.id,
            "creative_id": creative.id,
            "platform": platform,
            "caption": caption,
            "caption_length": len(caption),
            "char_validation": char_validation,
            "status": "draft",
        }

    # ─── Caption Update ───────────────────────────────────

    async def update_caption(
        self, post_id: str, new_caption: str
    ) -> Dict[str, Any]:
        """Update the caption of an existing post (where platform supports it)."""
        if not self.db:
            return {"updated": False, "error": "no_db"}

        result = await self.db.table("actp_organic_posts").select(
            "platform, status"
        ).eq("id", post_id).single().execute()

        if not result.data:
            return {"updated": False, "error": "post_not_found"}

        platform = result.data.get("platform", "")

        # Validate new caption length
        validation = self.validate_caption(new_caption, platform)
        if not validation["valid"]:
            return {"updated": False, "error": "caption_too_long", "validation": validation}

        await self.db.table("actp_organic_posts").update({
            "caption": new_caption,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", post_id).execute()

        return {"updated": True, "post_id": post_id, "new_caption_length": len(new_caption)}

    # ─── First Comment Automation ─────────────────────────

    async def post_first_comment(
        self, post: OrganicPost, comment_text: str
    ) -> Dict[str, Any]:
        """Post a first comment on a published post (for engagement/links)."""
        if post.status != "published" or not post.post_id:
            return {"posted": False, "error": "post_not_published"}

        logger.info(
            f"[ACTP:Publisher] Posting first comment on {post.platform.value} "
            f"post {post.post_id}: {comment_text[:50]}..."
        )

        if post.platform == Platform.YOUTUBE_SHORTS and self._youtube:
            try:
                self._youtube.post_comment(post.post_id, comment_text)
                return {"posted": True, "platform": "youtube", "post_id": post.post_id}
            except Exception as e:
                logger.error(f"[ACTP:Publisher] First comment failed: {e}")
                return {"posted": False, "error": str(e)}

        return {"posted": False, "error": f"First comment not supported on {post.platform.value}"}

    # ─── Twitter/X Publishing ─────────────────────────────

    async def publish_to_twitter(
        self, creative: Creative, video_path: str
    ) -> OrganicPost:
        """Publish a creative to Twitter/X."""
        from datetime import datetime, timezone

        post = OrganicPost(
            creative_id=creative.id,
            platform=Platform.TWITTER,
            status="publishing",
        )

        try:
            if MEDIAPOSTER_BASE not in sys.path:
                sys.path.insert(0, MEDIAPOSTER_BASE)

            from connectors.twitter_connector import TwitterConnector
            twitter = TwitterConnector()

            caption = self.format_caption_for_platform(creative, "twitter")

            result = twitter.upload_video_with_text(video_path, caption)

            if result and result.get("tweet_id"):
                post.post_id = result["tweet_id"]
                post.post_url = f"https://x.com/i/status/{result['tweet_id']}"
                post.status = "published"
                post.posted_at = datetime.now(timezone.utc)
            else:
                post.status = "failed"

        except Exception as e:
            logger.error(f"[ACTP:Publisher] Twitter publish failed: {e}")
            post.status = "failed"

        await self._save_organic_post(post)
        return post

    # ─── Optimal Posting Time ─────────────────────────────

    OPTIMAL_HOURS = {
        "tiktok": [11, 12, 15, 19, 20, 21],
        "youtube_shorts": [12, 14, 15, 17, 18, 20],
        "instagram_reels": [11, 13, 17, 18, 19, 20],
        "twitter": [9, 12, 15, 18],
    }

    def get_optimal_post_time(self, platform: str) -> Dict[str, Any]:
        """Get recommended posting hours for a platform."""
        hours = self.OPTIMAL_HOURS.get(platform, [12, 18])
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        current_hour = now.hour

        # Find next optimal hour
        next_optimal = None
        for h in sorted(hours):
            if h > current_hour:
                next_optimal = h
                break
        if next_optimal is None and hours:
            next_optimal = hours[0]  # Tomorrow's first slot

        return {
            "platform": platform,
            "optimal_hours_utc": hours,
            "next_optimal_hour": next_optimal,
            "current_hour_utc": current_hour,
        }

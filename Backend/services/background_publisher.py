"""
Background Publisher Service
Unified publishing flow that replicates the frontend media → post-content → posted-content flow.

This service handles:
1. Media validation and analysis verification
2. Account mapping (local → Blotato)
3. Caption/content retrieval from analysis data
4. Full publish flow (Google Drive → Blotato → Platform)
5. URL polling and verification
6. Posted content record storage for analytics

Can be used by:
- Scheduler (for scheduled posts)
- API endpoints (for immediate publishing)
- Background tasks
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from uuid import UUID
from loguru import logger
import httpx
from dataclasses import dataclass, field
from enum import Enum
from services.user_tracking_service import UserTrackingService, EventName


def _str(val):
    """Convert UUID or any value to string for JSON serialization."""
    if isinstance(val, UUID):
        return str(val)
    return val


class PublishStatus(Enum):
    """Publishing status states"""
    PENDING = "pending"
    VALIDATING = "validating"
    UPLOADING_STORAGE = "uploading_storage"
    UPLOADING_BLOTATO = "uploading_blotato"
    PUBLISHING = "publishing"
    POLLING_URL = "polling_url"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class PublishResult:
    """Result of a publish operation"""
    success: bool
    status: PublishStatus
    post_submission_id: Optional[str] = None
    platform_url: Optional[str] = None
    error: Optional[str] = None
    steps: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, bool] = field(default_factory=dict)


@dataclass
class PublishRequest:
    """Request for publishing content"""
    media_id: str
    blotato_account_id: str
    platform: str
    username: str
    caption: Optional[str] = None
    title: Optional[str] = None
    hashtags: Optional[List[str]] = None
    # Options
    poll_for_url: bool = True
    cleanup_storage: bool = True
    use_supabase: bool = False
    # Platform-specific config
    target_config: Optional[Dict] = None
    # Scheduling
    scheduled_time: Optional[datetime] = None


class BackgroundPublisher:
    """
    Background publishing service that replicates the frontend flow:
    
    1. /media/:id → Get media details and verify analysis exists
    2. /post-content/:id → Get captions, verify accounts
    3. /posted-content → Publish via full-publish, poll for URL, store record
    
    This ensures the scheduler uses the SAME verified process as manual publishing.
    """
    
    API_BASE = "http://localhost:5555"
    
    def __init__(self):
        self._publish_service = None
        # Initialize event bus
        from services.event_bus import EventBus
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("background-publisher")
    
    @property
    def publish_service(self):
        """Lazy load publish service"""
        if self._publish_service is None:
            from services.publish_service import get_publish_service
            self._publish_service = get_publish_service()
        return self._publish_service
    
    # =========================================================================
    # VERIFICATION STEPS
    # =========================================================================
    
    async def verify_media(self, media_id: str) -> Dict[str, Any]:
        """
        Step 1: Verify media exists and get file path
        Replicates: /media/:id page fetch
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.get(f"{self.API_BASE}/api/media-db/detail/{media_id}")
                if res.status_code != 200:
                    return {
                        "valid": False,
                        "error": f"Media not found: {media_id}"
                    }
                
                data = res.json()
                file_path = data.get("file_path")
                
                if not file_path:
                    return {
                        "valid": False,
                        "error": "No file path for media"
                    }
                
                # BUG FIX: Verify file exists with detailed error handling
                path = Path(file_path.strip())
                if not path.exists():
                    return {
                        "valid": False,
                        "error": f"Media file not found on disk: {file_path}. File may have been deleted after scheduling.",
                        "file_deleted": True,
                        "file_path": str(path)
                    }
                
                # Check file is readable
                if not path.is_file():
                    return {
                        "valid": False,
                        "error": f"Media path is not a file: {file_path}",
                        "invalid_path": True
                    }
                
                return {
                    "valid": True,
                    "media_id": media_id,
                    "filename": data.get("filename"),
                    "file_path": str(path),
                    "file_size_bytes": data.get("file_size") or path.stat().st_size,
                    "duration_sec": data.get("duration_sec"),
                    "has_transcript": bool(data.get("transcript")),
                    "has_analysis": bool(data.get("pre_social_score") or data.get("topics")),
                }
        except Exception as e:
            logger.error(f"Media verification failed: {e}")
            return {"valid": False, "error": str(e)}
    
    async def verify_analysis(self, media_id: str) -> Dict[str, Any]:
        """
        Step 2: Verify analysis exists and get platform content
        Replicates: /post-content/:id analysis fetch
        
        BUG FIX: Enhanced analysis completeness check
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.get(f"{self.API_BASE}/api/media-db/analysis/{media_id}")
                if res.status_code != 200:
                    return {
                        "valid": False,
                        "has_analysis": False,
                        "platform_content": [],
                        "completeness": "none",
                        "warnings": ["Analysis not found"]
                    }
                
                data = res.json()
                platform_content = data.get("platform_content", [])
                
                # BUG FIX: Check analysis completeness
                completeness_checks = {
                    "has_transcript": bool(data.get("transcript")),
                    "has_topics": bool(data.get("topics")) and len(data.get("topics", [])) > 0,
                    "has_platform_content": bool(platform_content) and len(platform_content) > 0,
                    "has_hooks": bool(data.get("hooks")) and len(data.get("hooks", [])) > 0,
                }
                
                completeness_score = sum(completeness_checks.values()) / len(completeness_checks)
                completeness_level = "complete" if completeness_score >= 0.75 else "partial" if completeness_score >= 0.5 else "incomplete"
                
                warnings = []
                if not completeness_checks["has_transcript"]:
                    warnings.append("Missing transcript")
                if not completeness_checks["has_topics"]:
                    warnings.append("Missing topics")
                if not completeness_checks["has_platform_content"]:
                    warnings.append("Missing platform_content")
                
                return {
                    "valid": True,
                    "has_analysis": data.get("has_analysis", False),
                    "transcript": data.get("transcript"),
                    "topics": data.get("topics", []),
                    "platform_content": platform_content,
                    "deep_analysis": data.get("deep_analysis"),
                    "suggested_caption": data.get("deep_analysis", {}).get("suggested_caption"),
                    "suggested_hashtags": data.get("deep_analysis", {}).get("suggested_hashtags", []),
                    "completeness": completeness_level,
                    "completeness_score": completeness_score,
                    "completeness_checks": completeness_checks,
                    "warnings": warnings
                }
        except Exception as e:
            logger.error(f"Analysis verification failed: {e}")
            return {"valid": False, "error": str(e), "platform_content": [], "completeness": "error"}
    
    async def verify_account(self, blotato_account_id: str, platform: str, username: str) -> Dict[str, Any]:
        """
        Step 3: Verify Blotato account exists and is valid
        Replicates: /post-content/:id account matching
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.get(f"{self.API_BASE}/api/blotato/accounts")
                if res.status_code != 200:
                    return {
                        "valid": False,
                        "error": "Failed to fetch Blotato accounts"
                    }
                
                data = res.json()
                # Handle both list response and dict with "accounts" key
                accounts = data if isinstance(data, list) else data.get("accounts", [])
                
                # Find matching account
                matching = None
                for acc in accounts:
                    if str(acc.get("id")) == str(blotato_account_id):
                        matching = acc
                        break
                
                if not matching:
                    # Try to find by username and platform
                    for acc in accounts:
                        if (acc.get("platform", "").lower() == platform.lower() and 
                            (acc.get("username", "").lower() == username.lower() or
                             acc.get("fullname", "").lower().find(username.lower()) >= 0)):
                            matching = acc
                            break
                
                if matching:
                    return {
                        "valid": True,
                        "blotato_account_id": str(matching.get("id")),
                        "platform": matching.get("platform"),
                        "username": matching.get("username"),
                        "fullname": matching.get("fullname"),
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"No Blotato account found for {username} ({platform})"
                    }
        except Exception as e:
            logger.error(f"Account verification failed: {e}")
            return {"valid": False, "error": str(e)}
    
    # =========================================================================
    # CAPTION GENERATION
    # =========================================================================
    
    def get_caption_for_platform(
        self,
        platform: str,
        analysis: Dict[str, Any],
        custom_caption: Optional[str] = None,
        custom_hashtags: Optional[List[str]] = None
    ) -> str:
        """
        Get or generate caption for a platform
        Replicates: /post-content/:id caption generation
        """
        if custom_caption:
            caption = custom_caption
        else:
            # Try to find in platform_content
            platform_content = analysis.get("platform_content", [])
            for pc in platform_content:
                if pc.get("platform", "").lower() == platform.lower():
                    caption = pc.get("description") or pc.get("caption") or pc.get("text")
                    if caption:
                        break
            else:
                # Fall back to suggested caption, but NOT raw transcript
                # Generate caption from hooks/topics if available
                hooks = analysis.get("hooks", [])
                topics = analysis.get("topics", [])
                
                if hooks and len(hooks) > 0:
                    # Use first hook as caption base
                    caption = hooks[0]
                    if topics:
                        caption += f" - {', '.join(topics[:2])}"
                elif topics and len(topics) > 0:
                    # Create caption from topics
                    caption = f"Discover: {', '.join(topics[:2])}"
                else:
                    # Generic fallback, NOT transcript
                    caption = analysis.get("suggested_caption") or "Check out this content!"
        
        # Add hashtags
        hashtags = custom_hashtags or []
        if not hashtags:
            hashtags = analysis.get("suggested_hashtags", [])
        if not hashtags and analysis.get("topics"):
            hashtags = [f"#{t.replace(' ', '')}" for t in analysis["topics"][:5]]
        
        # Platform-specific defaults
        if platform.lower() == "tiktok" and "#fyp" not in " ".join(hashtags).lower():
            hashtags.append("#fyp")
        
        if hashtags:
            hashtag_str = " ".join(hashtags) if hashtags else ""
            if hashtag_str and hashtag_str not in caption:
                caption = f"{caption}\n\n{hashtag_str}"
        
        return caption
    
    # =========================================================================
    # MAIN PUBLISH FLOW
    # =========================================================================
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Execute the full verified publish flow:
        
        1. Verify media exists and file is accessible
        2. Verify/fetch analysis data for captions
        3. Verify Blotato account
        4. Execute full publish (GDrive → Blotato → Platform)
        5. Poll for platform URL
        6. Store posted content record
        
        Returns:
            PublishResult with status, URLs, and verification details
        """
        from services.event_bus import Topics
        
        result = PublishResult(
            success=False,
            status=PublishStatus.PENDING,
            verification={},
            steps={}
        )
        
        # Emit publish requested event
        correlation_id = f"publish-{_str(request.media_id)}-{request.platform}"
        await self.event_bus.publish(
            Topics.PUBLISH_REQUESTED,
            {
                "media_id": _str(request.media_id),
                "platform": request.platform,
                "account_id": _str(request.blotato_account_id),
                "username": request.username
            },
            correlation_id=correlation_id
        )
        
        try:
            # ─────────────────────────────────────────────────────────────────
            # STEP 1: Verify Media
            # ─────────────────────────────────────────────────────────────────
            result.status = PublishStatus.VALIDATING
            logger.info(f"[Publish] Step 1/6: Verifying media {request.media_id}...")
            
            # Emit publish started event
            await self.event_bus.publish(
                Topics.PUBLISH_STARTED,
                {
                    "media_id": _str(request.media_id),
                    "platform": request.platform,
                    "status": "validating"
                },
                correlation_id=correlation_id
            )
            
            media_check = await self.verify_media(request.media_id)
            result.verification["media"] = media_check["valid"]
            result.steps["media_verification"] = media_check
            
            if not media_check["valid"]:
                result.error = media_check.get("error", "Media verification failed")
                result.status = PublishStatus.FAILED
                return result
            
            file_path = Path(media_check["file_path"])
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 2: Verify/Get Analysis
            # ─────────────────────────────────────────────────────────────────
            logger.info(f"[Publish] Step 2/6: Fetching analysis data...")
            
            analysis = await self.verify_analysis(request.media_id)
            result.verification["analysis"] = analysis.get("valid", False)
            result.steps["analysis_verification"] = {
                "has_analysis": analysis.get("has_analysis"),
                "has_transcript": bool(analysis.get("transcript")),
                "topics_count": len(analysis.get("topics", [])),
            }
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 3: Verify Account
            # ─────────────────────────────────────────────────────────────────
            logger.info(f"[Publish] Step 3/6: Verifying Blotato account...")
            
            account_check = await self.verify_account(
                request.blotato_account_id,
                request.platform,
                request.username
            )
            result.verification["account"] = account_check["valid"]
            result.steps["account_verification"] = account_check
            
            if not account_check["valid"]:
                result.error = account_check.get("error", "Account verification failed")
                result.status = PublishStatus.FAILED
                return result
            
            # Use verified account ID
            verified_account_id = account_check["blotato_account_id"]
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 4: Generate Caption
            # ─────────────────────────────────────────────────────────────────
            logger.info(f"[Publish] Step 4/6: Preparing caption...")
            
            caption = self.get_caption_for_platform(
                platform=request.platform,
                analysis=analysis,
                custom_caption=request.caption,
                custom_hashtags=request.hashtags
            )
            result.steps["caption"] = {
                "length": len(caption),
                "has_hashtags": "#" in caption
            }
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 5: Execute Full Publish Flow
            # ─────────────────────────────────────────────────────────────────
            result.status = PublishStatus.UPLOADING_STORAGE
            logger.info(f"[Publish] Step 5/6: Executing full publish flow...")
            
            # Emit uploading event
            await self.event_bus.publish(
                Topics.PUBLISH_UPLOADING,
                {
                    "media_id": _str(request.media_id),
                    "platform": request.platform,
                    "status": "uploading"
                },
                correlation_id=correlation_id
            )
            
            # Build target config
            target_config = request.target_config or {}
            platform_lower = request.platform.lower()
            
            if platform_lower == "tiktok":
                target_config.setdefault("privacy_level", "PUBLIC_TO_EVERYONE")
                target_config.setdefault("is_ai_generated", False)
                # TikTok requires a non-empty title
                target_config.setdefault("title", request.title or caption[:80] or "Check this out!")
            elif platform_lower == "instagram":
                target_config.setdefault("media_type", "reel")
            elif platform_lower == "youtube":
                target_config.setdefault("title", request.title or caption[:100] or "Video")
                target_config.setdefault("privacy_status", "public")
            elif platform_lower == "pinterest":
                # Pinterest also requires a title
                target_config.setdefault("title", request.title or caption[:80] or "Check this out!")
            
            # Use publish service for the heavy lifting
            publish_result = await self.publish_service.full_publish_with_url_tracking(
                file_path=file_path,
                account_id=verified_account_id,
                platform=platform_lower,
                text=caption,
                media_id=request.media_id,
                target_config=target_config,
                scheduled_time=request.scheduled_time.isoformat() if request.scheduled_time else None,
                cleanup_storage=request.cleanup_storage,
                use_supabase=request.use_supabase,
                poll_for_url=request.poll_for_url
            )
            
            result.steps["publish"] = publish_result.get("steps", {})
            
            if not publish_result.get("success"):
                result.error = publish_result.get("error", "Publish failed")
                result.status = PublishStatus.FAILED
                return result
            
            result.post_submission_id = publish_result.get("post_submission_id")
            result.platform_url = publish_result.get("public_url")
            
            # Update correlation_id to include post_submission_id for better tracking
            if result.post_submission_id:
                correlation_id = f"publish-{_str(request.media_id)}-{request.platform}-{result.post_submission_id}"
            
            # Emit upload completed event
            await self.event_bus.publish(
                Topics.PUBLISH_UPLOAD_COMPLETED,
                {
                    "media_id": _str(request.media_id),
                    "platform": request.platform,
                    "post_submission_id": result.post_submission_id
                },
                correlation_id=correlation_id
            )
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 6: Final Verification & Record
            # ─────────────────────────────────────────────────────────────────
            result.status = PublishStatus.POLLING_URL if request.poll_for_url else PublishStatus.SUCCESS
            logger.info(f"[Publish] Step 6/6: Final verification...")
            
            if request.poll_for_url and not result.platform_url:
                # Emit polling event
                await self.event_bus.publish(
                    Topics.PUBLISH_POLLING,
                    {
                        "media_id": _str(request.media_id),
                        "platform": request.platform,
                        "post_submission_id": result.post_submission_id
                    },
                    correlation_id=correlation_id
                )
            
            result.verification["published"] = True
            result.verification["url_obtained"] = bool(result.platform_url)
            
            # Success!
            result.success = True
            result.status = PublishStatus.SUCCESS
            
            # Emit publish completed event
            await self.event_bus.publish(
                Topics.PUBLISH_COMPLETED,
                {
                    "media_id": _str(request.media_id),
                    "platform": request.platform,
                    "post_submission_id": result.post_submission_id,
                    "platform_url": result.platform_url,
                    "account_id": request.blotato_account_id,
                    "username": request.username
                },
                correlation_id=correlation_id
            )

            # Track post published event (TRACK-004)
            try:
                tracking = UserTrackingService.get_instance()
                await tracking.track_core_value(
                    event_name=EventName.POST_PUBLISHED.value,
                    user_id="system",  # TODO: Get actual user_id from auth
                    properties={
                        "media_id": _str(request.media_id),
                        "platform": request.platform,
                        "post_url": result.platform_url,
                        "username": request.username,
                        "scheduled": False  # This is immediate publish
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to track post_published event: {e}")
            
            logger.success(
                f"[Publish] ✅ Successfully published to {request.platform}! "
                f"Submission: {result.post_submission_id}, URL: {result.platform_url or 'pending'}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[Publish] ❌ Publish failed with exception: {e}")
            result.error = str(e)
            result.status = PublishStatus.FAILED
            
            # Emit publish failed event
            await self.event_bus.publish(
                Topics.PUBLISH_FAILED,
                {
                    "media_id": _str(request.media_id),
                    "platform": request.platform,
                    "error": str(e),
                    "account_id": request.blotato_account_id
                },
                correlation_id=correlation_id
            )
            
            return result
    
    async def publish_batch(
        self,
        media_id: str,
        accounts: List[Dict[str, str]],
        caption_override: Optional[str] = None,
        sequential: bool = True
    ) -> Dict[str, PublishResult]:
        """
        Publish to multiple accounts (like the posted-content page does)
        
        Args:
            media_id: The media to publish
            accounts: List of {blotato_account_id, platform, username}
            caption_override: Optional caption to use for all
            sequential: If True, publish one at a time; if False, publish in parallel
            
        Returns:
            Dict mapping account_id to PublishResult
        """
        results = {}
        
        if sequential:
            for acc in accounts:
                request = PublishRequest(
                    media_id=media_id,
                    blotato_account_id=acc["blotato_account_id"],
                    platform=acc["platform"],
                    username=acc["username"],
                    caption=caption_override,
                )
                results[acc["blotato_account_id"]] = await self.publish(request)
        else:
            # Parallel publishing
            tasks = []
            for acc in accounts:
                request = PublishRequest(
                    media_id=media_id,
                    blotato_account_id=acc["blotato_account_id"],
                    platform=acc["platform"],
                    username=acc["username"],
                    caption=caption_override,
                )
                tasks.append((acc["blotato_account_id"], self.publish(request)))
            
            for account_id, task in tasks:
                results[account_id] = await task
        
        return results


# Singleton instance
_background_publisher: Optional[BackgroundPublisher] = None


def get_background_publisher() -> BackgroundPublisher:
    """Get singleton instance of BackgroundPublisher"""
    global _background_publisher
    if _background_publisher is None:
        _background_publisher = BackgroundPublisher()
    return _background_publisher

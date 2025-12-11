"""
Blotato API Router
FastAPI endpoints for Blotato social media publishing and AI video creation.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
import logging

from services.blotato_api import (
    BlotatoAPI,
    Platform,
    VideoStyle,
    VideoTemplate,
    TextToImageModel,
    ImageToVideoModel,
    TikTokPrivacy,
    YouTubePrivacy,
    PostContent,
    TwitterTarget,
    LinkedInTarget,
    FacebookTarget,
    InstagramTarget,
    TikTokTarget,
    PinterestTarget,
    ThreadsTarget,
    BlueskyTarget,
    YouTubeTarget,
    WebhookTarget,
    VOICE_IDS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/blotato", tags=["Blotato"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class PublishPostRequest(BaseModel):
    """Request to publish a post to a social platform"""
    account_id: str = Field(..., description="Blotato connected account ID")
    text: str = Field(..., description="Post text content")
    platform: str = Field(..., description="Target platform (twitter, instagram, tiktok, etc.)")
    media_urls: Optional[List[str]] = Field(default=[], description="List of media URLs")
    scheduled_time: Optional[datetime] = Field(default=None, description="ISO 8601 scheduled time")
    use_next_free_slot: bool = Field(default=False, description="Use next available slot")
    
    # Platform-specific options
    # Twitter/Bluesky/Threads
    additional_posts: Optional[List[dict]] = Field(default=None, description="Additional posts for threads")
    
    # LinkedIn
    linkedin_page_id: Optional[str] = Field(default=None, description="LinkedIn page ID")
    
    # Facebook
    facebook_page_id: Optional[str] = Field(default=None, description="Facebook page ID")
    facebook_media_type: Optional[Literal["video", "reel"]] = Field(default=None)
    
    # Instagram
    instagram_media_type: Optional[Literal["reel", "story"]] = Field(default=None)
    instagram_alt_text: Optional[str] = Field(default=None, description="Alt text for images")
    instagram_collaborators: Optional[List[str]] = Field(default=None, description="Collaborator handles")
    
    # TikTok
    tiktok_privacy: Optional[str] = Field(default="PUBLIC_TO_EVERYONE")
    tiktok_title: Optional[str] = Field(default=None)
    tiktok_auto_music: bool = Field(default=False)
    tiktok_is_draft: bool = Field(default=False)
    tiktok_disabled_comments: bool = Field(default=False)
    tiktok_disabled_duet: bool = Field(default=False)
    tiktok_disabled_stitch: bool = Field(default=False)
    tiktok_is_branded: bool = Field(default=False)
    tiktok_is_ai_generated: bool = Field(default=True)
    
    # Pinterest
    pinterest_board_id: Optional[str] = Field(default=None, description="Pinterest board ID")
    pinterest_title: Optional[str] = Field(default=None)
    pinterest_link: Optional[str] = Field(default=None)
    
    # Threads
    threads_reply_control: Optional[Literal["everyone", "accounts_you_follow", "mentioned_only"]] = None
    
    # YouTube
    youtube_title: Optional[str] = Field(default=None, description="Video title")
    youtube_privacy: Optional[Literal["private", "public", "unlisted"]] = Field(default="public")
    youtube_notify_subscribers: bool = Field(default=True)
    youtube_made_for_kids: bool = Field(default=False)
    youtube_synthetic_media: bool = Field(default=False)
    
    # Webhook
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL")


class UploadMediaRequest(BaseModel):
    """Request to upload media to Blotato"""
    url: str = Field(..., description="URL of media to upload (or base64 data)")


class CreateVideoRequest(BaseModel):
    """Request to create an AI video"""
    script: str = Field(..., description="Video script or description")
    style: str = Field(default="cinematic", description="Visual style")
    template: str = Field(default="base/pov/wakeup", description="Video template")
    
    # Template options
    first_scene_text: Optional[str] = Field(default=None, description="Custom first scene text")
    caption_position: Optional[Literal["top", "bottom", "middle"]] = Field(default="bottom")
    voice_id: Optional[str] = Field(default=None, description="ElevenLabs voice ID")
    voice_name: Optional[str] = Field(default=None, description="Voice name (e.g., 'brian', 'sarah')")
    
    # Slideshow scenes
    scenes: Optional[List[dict]] = Field(default=None, description="Scenes for slideshow template")
    
    # Animation options
    animate_first_image: bool = Field(default=False)
    animate_all: bool = Field(default=False)
    
    # Model options
    text_to_image_model: Optional[str] = Field(default=None)
    image_to_video_model: Optional[str] = Field(default=None)


class MultiPlatformPostRequest(BaseModel):
    """Request to post to multiple platforms"""
    account_ids: dict = Field(..., description="Platform to account ID mapping")
    text: str = Field(..., description="Post text")
    media_urls: Optional[List[str]] = Field(default=[])
    platforms: List[str] = Field(..., description="List of platforms to post to")
    scheduled_time: Optional[datetime] = Field(default=None)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class PostResponse(BaseModel):
    """Response from publishing a post"""
    success: bool
    post_submission_id: Optional[str] = None
    error: Optional[str] = None


class MediaUploadResponse(BaseModel):
    """Response from uploading media"""
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None


class VideoCreationResponse(BaseModel):
    """Response from creating a video"""
    success: bool
    video_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class VideoStatusResponse(BaseModel):
    """Response with video status"""
    success: bool
    video_id: Optional[str] = None
    status: Optional[str] = None
    media_url: Optional[str] = None
    image_urls: Optional[List[str]] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


class VoiceInfo(BaseModel):
    """Voice information"""
    key: str
    id: str
    name: str
    gender: str
    accent: str
    tags: List[str]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/health")
async def health_check():
    """Check Blotato API integration health"""
    import os
    api_key = os.getenv("BLOTATO_API_KEY")
    return {
        "status": "ok",
        "api_key_configured": bool(api_key),
        "api_key_length": len(api_key) if api_key else 0,
        "supported_platforms": [p.value for p in Platform],
        "supported_video_styles": [s.value for s in VideoStyle],
    }


# -------------------------------------------------------------------------
# POST ENDPOINTS
# -------------------------------------------------------------------------

@router.post("/posts", response_model=PostResponse)
async def publish_post(request: PublishPostRequest):
    """
    Publish a post to a social media platform.
    
    Supports: Twitter, LinkedIn, Facebook, Instagram, TikTok, 
              Pinterest, Threads, Bluesky, YouTube
    
    Rate Limit: 30 requests/minute
    """
    try:
        client = BlotatoAPI()
        
        # Parse platform
        try:
            platform = Platform(request.platform.lower())
        except ValueError:
            raise HTTPException(400, f"Unsupported platform: {request.platform}")
        
        # Create content
        content = PostContent(
            text=request.text,
            platform=platform,
            media_urls=request.media_urls or [],
            additional_posts=request.additional_posts,
        )
        
        # Create target based on platform
        if platform == Platform.TWITTER:
            target = TwitterTarget()
        elif platform == Platform.LINKEDIN:
            target = LinkedInTarget(page_id=request.linkedin_page_id)
        elif platform == Platform.FACEBOOK:
            if not request.facebook_page_id:
                raise HTTPException(400, "facebook_page_id is required for Facebook")
            target = FacebookTarget(
                page_id=request.facebook_page_id,
                media_type=request.facebook_media_type,
            )
        elif platform == Platform.INSTAGRAM:
            target = InstagramTarget(
                media_type=request.instagram_media_type,
                alt_text=request.instagram_alt_text,
                collaborators=request.instagram_collaborators,
            )
        elif platform == Platform.TIKTOK:
            target = TikTokTarget(
                privacy_level=TikTokPrivacy(request.tiktok_privacy),
                disabled_comments=request.tiktok_disabled_comments,
                disabled_duet=request.tiktok_disabled_duet,
                disabled_stitch=request.tiktok_disabled_stitch,
                is_branded_content=request.tiktok_is_branded,
                is_your_brand=request.tiktok_is_branded,
                is_ai_generated=request.tiktok_is_ai_generated,
                title=request.tiktok_title,
                auto_add_music=request.tiktok_auto_music,
                is_draft=request.tiktok_is_draft,
            )
        elif platform == Platform.PINTEREST:
            if not request.pinterest_board_id:
                raise HTTPException(400, "pinterest_board_id is required for Pinterest")
            target = PinterestTarget(
                board_id=request.pinterest_board_id,
                title=request.pinterest_title,
                link=request.pinterest_link,
            )
        elif platform == Platform.THREADS:
            target = ThreadsTarget(reply_control=request.threads_reply_control)
        elif platform == Platform.BLUESKY:
            target = BlueskyTarget()
        elif platform == Platform.YOUTUBE:
            if not request.youtube_title:
                raise HTTPException(400, "youtube_title is required for YouTube")
            target = YouTubeTarget(
                title=request.youtube_title,
                privacy_status=YouTubePrivacy(request.youtube_privacy),
                should_notify_subscribers=request.youtube_notify_subscribers,
                is_made_for_kids=request.youtube_made_for_kids,
                contains_synthetic_media=request.youtube_synthetic_media,
            )
        elif platform == Platform.WEBHOOK:
            if not request.webhook_url:
                raise HTTPException(400, "webhook_url is required for Webhook")
            target = WebhookTarget(url=request.webhook_url)
        else:
            raise HTTPException(400, f"Unsupported platform: {platform}")
        
        # Publish
        result = await client.publish_post(
            account_id=request.account_id,
            content=content,
            target=target,
            scheduled_time=request.scheduled_time,
            use_next_free_slot=request.use_next_free_slot,
        )
        
        return PostResponse(
            success=True,
            post_submission_id=result.get("postSubmissionId"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing post: {e}")
        return PostResponse(success=False, error=str(e))


@router.post("/posts/multi-platform")
async def publish_to_multiple_platforms(request: MultiPlatformPostRequest):
    """
    Publish the same content to multiple platforms.
    
    Returns results for each platform.
    """
    results = {}
    
    for platform_str in request.platforms:
        try:
            platform = Platform(platform_str.lower())
            account_id = request.account_ids.get(platform_str)
            
            if not account_id:
                results[platform_str] = {"success": False, "error": "No account_id provided"}
                continue
            
            # Create individual post request
            post_request = PublishPostRequest(
                account_id=account_id,
                text=request.text,
                platform=platform_str,
                media_urls=request.media_urls,
                scheduled_time=request.scheduled_time,
            )
            
            result = await publish_post(post_request)
            results[platform_str] = {
                "success": result.success,
                "post_submission_id": result.post_submission_id,
                "error": result.error,
            }
            
        except Exception as e:
            results[platform_str] = {"success": False, "error": str(e)}
    
    return {
        "total_platforms": len(request.platforms),
        "successful": sum(1 for r in results.values() if r.get("success")),
        "results": results,
    }


# -------------------------------------------------------------------------
# MEDIA ENDPOINTS
# -------------------------------------------------------------------------

@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_media(request: UploadMediaRequest):
    """
    Upload media to Blotato's servers.
    
    Note: Upload is optional - you can pass any publicly accessible URL
    directly when publishing a post.
    
    Rate Limit: 10 requests/minute
    Max File Size: 200MB
    """
    try:
        client = BlotatoAPI()
        result = await client.upload_media(request.url)
        
        return MediaUploadResponse(
            success=True,
            url=result.get("url"),
        )
        
    except Exception as e:
        logger.error(f"Error uploading media: {e}")
        return MediaUploadResponse(success=False, error=str(e))


# -------------------------------------------------------------------------
# VIDEO ENDPOINTS
# -------------------------------------------------------------------------

@router.post("/videos/create", response_model=VideoCreationResponse)
async def create_video(request: CreateVideoRequest):
    """
    Create an AI-generated video.
    
    Templates:
    - "empty" - Custom video with optional narration
    - "base/pov/wakeup" - POV style video
    - "base/slides/quotecard" - Quote card slideshow
    
    Rate Limit: 1 request/minute
    """
    try:
        client = BlotatoAPI()
        
        # Parse enums
        try:
            style = VideoStyle(request.style.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid style: {request.style}")
        
        try:
            template = VideoTemplate(request.template)
        except ValueError:
            raise HTTPException(400, f"Invalid template: {request.template}")
        
        # Build template options
        template_options = {}
        
        if request.first_scene_text:
            template_options["firstSceneText"] = request.first_scene_text
        if request.caption_position:
            template_options["captionPosition"] = request.caption_position
        if request.scenes:
            template_options["scenes"] = request.scenes
        
        # Handle voice
        if request.voice_id:
            template_options["voiceId"] = request.voice_id
        elif request.voice_name:
            voice_info = VOICE_IDS.get(request.voice_name.lower())
            if voice_info:
                template_options["voiceId"] = voice_info["id"]
        
        # Parse models
        text_to_image_model = None
        if request.text_to_image_model:
            try:
                text_to_image_model = TextToImageModel(request.text_to_image_model)
            except ValueError:
                pass  # Use default
        
        image_to_video_model = None
        if request.image_to_video_model:
            try:
                image_to_video_model = ImageToVideoModel(request.image_to_video_model)
            except ValueError:
                pass  # Use default
        
        result = await client.create_video(
            script=request.script,
            style=style,
            template=template,
            template_options=template_options if template_options else None,
            animate_first_image=request.animate_first_image,
            animate_all=request.animate_all,
            text_to_image_model=text_to_image_model,
            image_to_video_model=image_to_video_model,
        )
        
        item = result.get("item", {})
        return VideoCreationResponse(
            success=True,
            video_id=item.get("id"),
            status=item.get("status"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        return VideoCreationResponse(success=False, error=str(e))


@router.post("/videos/pov", response_model=VideoCreationResponse)
async def create_pov_video(
    script: str = Query(..., description="POV scenario (e.g., 'you wake up as a pharaoh')"),
    style: str = Query(default="cinematic"),
    first_scene_text: Optional[str] = Query(default=None),
    caption_position: Optional[str] = Query(default="bottom"),
    animate: bool = Query(default=False),
):
    """Create a POV (Point of View) style video."""
    request = CreateVideoRequest(
        script=script,
        style=style,
        template="base/pov/wakeup",
        first_scene_text=first_scene_text,
        caption_position=caption_position,
        animate_first_image=animate,
    )
    return await create_video(request)


@router.post("/videos/slideshow", response_model=VideoCreationResponse)
async def create_slideshow_video(
    scenes: List[dict],
    style: str = Query(default="cinematic"),
    caption_position: Optional[str] = Query(default="middle"),
):
    """
    Create a quote card slideshow video.
    
    Each scene should have:
    - prompt: Description of the quote/image
    - text (optional): Exact quote text
    - textToImagePrompt (optional): Custom image prompt
    """
    request = CreateVideoRequest(
        script="1",
        style=style,
        template="base/slides/quotecard",
        scenes=scenes,
        caption_position=caption_position,
    )
    return await create_video(request)


@router.post("/videos/narrated", response_model=VideoCreationResponse)
async def create_narrated_video(
    script: str = Query(..., description="Full video script"),
    style: str = Query(default="cinematic"),
    voice_name: str = Query(default="brian", description="Voice name"),
    caption_position: Optional[str] = Query(default="bottom"),
):
    """Create a narrated video with AI voice."""
    request = CreateVideoRequest(
        script=script,
        style=style,
        template="empty",
        voice_name=voice_name,
        caption_position=caption_position,
    )
    return await create_video(request)


@router.get("/videos/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """Get the status of a video creation."""
    try:
        client = BlotatoAPI()
        result = await client.get_video_status(video_id)
        
        item = result.get("item", {})
        return VideoStatusResponse(
            success=True,
            video_id=item.get("id"),
            status=item.get("status"),
            media_url=item.get("mediaUrl"),
            image_urls=item.get("imageUrls"),
            created_at=item.get("createdAt"),
        )
        
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        return VideoStatusResponse(success=False, error=str(e))


@router.delete("/videos/{video_id}")
async def delete_video(video_id: str):
    """Delete a video."""
    try:
        client = BlotatoAPI()
        result = await client.delete_video(video_id)
        return {"success": True, "video_id": result.get("id")}
    except Exception as e:
        logger.error(f"Error deleting video: {e}")
        return {"success": False, "error": str(e)}


@router.get("/videos/{video_id}/wait", response_model=VideoStatusResponse)
async def wait_for_video(
    video_id: str,
    timeout: int = Query(default=300, description="Timeout in seconds"),
    poll_interval: int = Query(default=10, description="Poll interval in seconds"),
):
    """Wait for a video to complete creation."""
    try:
        client = BlotatoAPI()
        result = await client.wait_for_video(
            video_id=video_id,
            timeout_seconds=timeout,
            poll_interval=poll_interval,
        )
        
        item = result.get("item", {})
        return VideoStatusResponse(
            success=True,
            video_id=item.get("id"),
            status=item.get("status"),
            media_url=item.get("mediaUrl"),
            image_urls=item.get("imageUrls"),
            created_at=item.get("createdAt"),
        )
        
    except Exception as e:
        logger.error(f"Error waiting for video: {e}")
        return VideoStatusResponse(success=False, error=str(e))


# -------------------------------------------------------------------------
# UTILITY ENDPOINTS
# -------------------------------------------------------------------------

@router.get("/voices")
async def get_available_voices(
    gender: Optional[str] = Query(default=None, description="Filter by gender"),
    accent: Optional[str] = Query(default=None, description="Filter by accent"),
    tags: Optional[str] = Query(default=None, description="Comma-separated tags"),
):
    """Get available AI voices for video narration."""
    voices = []
    
    tag_list = tags.split(",") if tags else None
    
    for key, info in VOICE_IDS.items():
        if gender and info.get("gender") != gender:
            continue
        if accent and info.get("accent") != accent:
            continue
        if tag_list:
            voice_tags = info.get("tags", [])
            if not any(tag.strip() in voice_tags for tag in tag_list):
                continue
        
        voices.append(VoiceInfo(
            key=key,
            id=info["id"],
            name=info["name"],
            gender=info["gender"],
            accent=info["accent"],
            tags=info["tags"],
        ))
    
    return {
        "total": len(voices),
        "voices": voices,
    }


@router.get("/platforms")
async def get_supported_platforms():
    """Get supported social media platforms with their specific requirements."""
    return {
        "platforms": [
            {
                "id": "twitter",
                "name": "Twitter/X",
                "max_text_length": 280,
                "max_media": 4,
                "supports_threads": True,
                "supports_video": True,
                "supports_scheduling": True,
            },
            {
                "id": "linkedin",
                "name": "LinkedIn",
                "max_text_length": 3000,
                "supports_pages": True,
                "supports_video": True,
                "supports_scheduling": True,
            },
            {
                "id": "facebook",
                "name": "Facebook",
                "max_text_length": 63206,
                "requires_page_id": True,
                "supports_reels": True,
                "supports_video": True,
                "supports_scheduling": True,
            },
            {
                "id": "instagram",
                "name": "Instagram",
                "max_text_length": 2200,
                "supports_reels": True,
                "supports_stories": True,
                "supports_carousels": True,
                "supports_collaborators": True,
                "supports_scheduling": True,
            },
            {
                "id": "tiktok",
                "name": "TikTok",
                "max_text_length": 2200,
                "privacy_options": ["SELF_ONLY", "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR"],
                "supports_drafts": True,
                "supports_scheduling": True,
            },
            {
                "id": "pinterest",
                "name": "Pinterest",
                "max_description_length": 800,
                "max_title_length": 100,
                "requires_board_id": True,
                "supports_links": True,
                "supports_scheduling": True,
            },
            {
                "id": "threads",
                "name": "Threads",
                "max_text_length": 500,
                "supports_threads": True,
                "supports_carousels": True,
                "reply_control_options": ["everyone", "accounts_you_follow", "mentioned_only"],
                "supports_scheduling": True,
            },
            {
                "id": "bluesky",
                "name": "Bluesky",
                "max_text_length": 300,
                "max_media": 4,
                "supports_threads": True,
                "supports_scheduling": True,
            },
            {
                "id": "youtube",
                "name": "YouTube",
                "max_title_length": 100,
                "max_description_length": 5000,
                "requires_title": True,
                "privacy_options": ["private", "public", "unlisted"],
                "supports_scheduling": True,
            },
        ]
    }


@router.get("/video-styles")
async def get_video_styles():
    """Get available video generation styles."""
    return {
        "styles": [
            {"id": s.value, "name": s.value.replace("_", " ").title()}
            for s in VideoStyle
        ]
    }


@router.get("/video-templates")
async def get_video_templates():
    """Get available video templates."""
    return {
        "templates": [
            {
                "id": "empty",
                "name": "Custom Video",
                "description": "Create a custom video with optional narration",
                "supports_voice": True,
                "supports_captions": True,
            },
            {
                "id": "base/pov/wakeup",
                "name": "POV Wakeup",
                "description": "Point-of-view style video (e.g., 'you wake up as a pharaoh')",
                "supports_custom_first_scene": True,
                "supports_captions": True,
            },
            {
                "id": "base/slides/quotecard",
                "name": "Quote Card Slideshow",
                "description": "Generate motivational quote slides with AI backgrounds",
                "supports_scenes": True,
                "supports_custom_text": True,
                "supports_captions": True,
            },
        ]
    }


@router.get("/ai-models")
async def get_ai_models():
    """Get available AI models for video generation."""
    return {
        "text_to_image_models": [
            {"id": m.value, "name": m.name.replace("_", " ")}
            for m in TextToImageModel
        ],
        "image_to_video_models": [
            {"id": m.value, "name": m.name.replace("_", " ")}
            for m in ImageToVideoModel
        ],
    }

"""
Blotato API Integration Service
Full integration with Blotato's social media publishing and AI video creation APIs.

API Documentation: https://help.blotato.com/api/api-reference
Base URL: https://backend.blotato.com/v2

Endpoints:
- POST /posts - Publish or schedule posts to social platforms
- POST /media - Upload media to Blotato's servers
- POST /videos/creations - Create AI-generated videos
- GET /videos/creations/:id - Get video creation status
- DELETE /videos/:id - Delete a video
"""

import os
import httpx
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class Platform(str, Enum):
    """Supported social media platforms"""
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    TIKTOK = "tiktok"
    THREADS = "threads"
    BLUESKY = "bluesky"
    YOUTUBE = "youtube"
    WEBHOOK = "webhook"


class VideoStyle(str, Enum):
    """Available video generation styles"""
    CINEMATIC = "cinematic"
    APOCALYPTIC = "apocalyptic"
    BAROQUE = "baroque"
    COMICBOOK = "comicbook"
    CYBERPUNK = "cyberpunk"
    DYSTOPIAN = "dystopian"
    FANTASY = "fantasy"
    FUTURISTIC = "futuristic"
    GOTHIC = "gothic"
    GRUNGE = "grunge"
    HORROR = "horror"
    KAWAII = "kawaii"
    MYSTICAL = "mystical"
    NOIR = "noir"
    PAINTERLY = "painterly"
    REALISTIC = "realistic"
    RETRO = "retro"
    SURREAL = "surreal"
    WHIMSICAL = "whimsical"


class VideoTemplate(str, Enum):
    """Available video templates"""
    EMPTY = "empty"
    POV_WAKEUP = "base/pov/wakeup"
    SLIDES_QUOTECARD = "base/slides/quotecard"


class TikTokPrivacy(str, Enum):
    """TikTok privacy levels"""
    SELF_ONLY = "SELF_ONLY"
    PUBLIC = "PUBLIC_TO_EVERYONE"
    MUTUAL_FOLLOW = "MUTUAL_FOLLOW_FRIENDS"
    FOLLOWERS = "FOLLOWER_OF_CREATOR"


class YouTubePrivacy(str, Enum):
    """YouTube privacy status"""
    PRIVATE = "private"
    PUBLIC = "public"
    UNLISTED = "unlisted"


class TextToImageModel(str, Enum):
    """Available text-to-image models"""
    FLUX_SCHNELL = "replicate/black-forest-labs/flux-schnell"
    FLUX_DEV = "replicate/black-forest-labs/flux-dev"
    FLUX_PRO = "replicate/black-forest-labs/flux-1.1-pro"
    FLUX_PRO_ULTRA = "replicate/black-forest-labs/flux-1.1-pro-ultra"
    RECRAFT_V3 = "replicate/recraft-ai/recraft-v3"
    IDEOGRAM_V2 = "replicate/ideogram-ai/ideogram-v2"
    LUMA_PHOTON = "replicate/luma/photon"
    GPT_IMAGE = "openai/gpt-image-1"


class ImageToVideoModel(str, Enum):
    """Available image-to-video models"""
    FRAMEPACK = "fal-ai/framepack"
    RUNWAY_GEN3 = "fal-ai/runway-gen3/turbo/image-to-video"
    LUMA_DREAM = "fal-ai/luma-dream-machine/image-to-video"
    KLING_1_5_PRO = "fal-ai/kling-video/v1.5/pro/image-to-video"
    KLING_1_6_PRO = "fal-ai/kling-video/v1.6/pro/image-to-video"
    MINIMAX = "fal-ai/minimax-video/image-to-video"
    MINIMAX_DIRECTOR = "fal-ai/minimax/video-01-director/image-to-video"
    HUNYUAN = "fal-ai/hunyuan-video-image-to-video"
    VEO2 = "fal-ai/veo2/image-to-video"


# =============================================================================
# VOICE IDS (ElevenLabs)
# =============================================================================

VOICE_IDS = {
    "alice": {"id": "elevenlabs/eleven_multilingual_v2/Xb7hH8MSUJpSbSDYk0k2", "name": "Alice", "gender": "female", "accent": "British", "tags": ["confident", "news"]},
    "aria": {"id": "elevenlabs/eleven_multilingual_v2/9BWtsMINqrJLrRacOk9x", "name": "Aria", "gender": "female", "accent": "American", "tags": ["expressive", "social media"]},
    "bill": {"id": "elevenlabs/eleven_multilingual_v2/pqHfZKP75CvOlQylNhV4", "name": "Bill", "gender": "male", "accent": "American", "tags": ["trustworthy", "narration"]},
    "brian": {"id": "elevenlabs/eleven_multilingual_v2/nPczCjzI2devNBz1zQrb", "name": "Brian", "gender": "male", "accent": "American", "tags": ["deep", "narration"]},
    "callum": {"id": "elevenlabs/eleven_multilingual_v2/N2lVS1w4EtoT3dr4eOWO", "name": "Callum", "gender": "male", "accent": "Transatlantic", "tags": ["intense", "characters"]},
    "charlie": {"id": "elevenlabs/eleven_multilingual_v2/IKne3meq5aSn9XLyUdCD", "name": "Charlie", "gender": "male", "accent": "Australian", "tags": ["natural", "conversational"]},
    "charlotte": {"id": "elevenlabs/eleven_multilingual_v2/XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "gender": "female", "accent": "Swedish", "tags": ["seductive", "characters"]},
    "chris": {"id": "elevenlabs/eleven_multilingual_v2/iP95p4xoKVk53GoZ742B", "name": "Chris", "gender": "male", "accent": "American", "tags": ["casual", "conversational"]},
    "daniel": {"id": "elevenlabs/eleven_multilingual_v2/onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "gender": "male", "accent": "British", "tags": ["authoritative", "news"]},
    "eric": {"id": "elevenlabs/eleven_multilingual_v2/cjVigY5qzO86Huf0OWal", "name": "Eric", "gender": "male", "accent": "American", "tags": ["friendly", "conversational"]},
    "george": {"id": "elevenlabs/eleven_multilingual_v2/JBFqnCBsd6RMkjVDRZzb", "name": "George", "gender": "male", "accent": "British", "tags": ["warm", "narration"]},
    "jessica": {"id": "elevenlabs/eleven_multilingual_v2/cgSgspJ2msm6clMCkdW9", "name": "Jessica", "gender": "female", "accent": "American", "tags": ["expressive", "conversational"]},
    "laura": {"id": "elevenlabs/eleven_multilingual_v2/FGY2WhTYpPnrIDTdsKH5", "name": "Laura", "gender": "female", "accent": "American", "tags": ["upbeat", "social media"]},
    "liam": {"id": "elevenlabs/eleven_multilingual_v2/TX3LPaxmHKxFdv7VOQHJ", "name": "Liam", "gender": "male", "accent": "American", "tags": ["articulate", "narration"]},
    "lily": {"id": "elevenlabs/eleven_multilingual_v2/pFZP5JQG7iQjIQuC4Bku", "name": "Lily", "gender": "female", "accent": "British", "tags": ["warm", "narration"]},
    "matilda": {"id": "elevenlabs/eleven_multilingual_v2/XrExE9yKIg1WjnnlVkGX", "name": "Matilda", "gender": "female", "accent": "American", "tags": ["friendly", "narration"]},
    "river": {"id": "elevenlabs/eleven_multilingual_v2/SAz9YHcvj6GT2YYXdXww", "name": "River", "gender": "non-binary", "accent": "American", "tags": ["confident", "social media"]},
    "roger": {"id": "elevenlabs/eleven_multilingual_v2/CwhRBWXzGAHq8TQ4Fs17", "name": "Roger", "gender": "male", "accent": "American", "tags": ["confident", "social media"]},
    "sarah": {"id": "elevenlabs/eleven_multilingual_v2/EXAVITQu4vr4xnSDxMaL", "name": "Sarah", "gender": "female", "accent": "American", "tags": ["soft", "news"]},
    "will": {"id": "elevenlabs/eleven_multilingual_v2/bIHbv24MWmeRgasZH58o", "name": "Will", "gender": "male", "accent": "American", "tags": ["friendly", "social media"]},
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PostContent:
    """Content for a social media post"""
    text: str
    platform: Platform
    media_urls: List[str] = None
    additional_posts: List[Dict[str, Any]] = None  # For threads
    
    def __post_init__(self):
        if self.media_urls is None:
            self.media_urls = []
    
    def to_dict(self) -> dict:
        data = {
            "text": self.text,
            "platform": self.platform.value,
            "mediaUrls": self.media_urls,
        }
        if self.additional_posts:
            data["additionalPosts"] = self.additional_posts
        return data


@dataclass
class TwitterTarget:
    """Twitter-specific target configuration"""
    target_type: str = "twitter"
    
    def to_dict(self) -> dict:
        return {"targetType": self.target_type}


@dataclass
class LinkedInTarget:
    """LinkedIn-specific target configuration"""
    target_type: str = "linkedin"
    page_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        data = {"targetType": self.target_type}
        if self.page_id:
            data["pageId"] = self.page_id
        return data


@dataclass
class FacebookTarget:
    """Facebook-specific target configuration"""
    target_type: str = "facebook"
    page_id: str = ""
    media_type: Optional[Literal["video", "reel"]] = None
    
    def to_dict(self) -> dict:
        data = {"targetType": self.target_type, "pageId": self.page_id}
        if self.media_type:
            data["mediaType"] = self.media_type
        return data


@dataclass
class InstagramTarget:
    """Instagram-specific target configuration"""
    target_type: str = "instagram"
    media_type: Optional[Literal["reel", "story"]] = None
    alt_text: Optional[str] = None
    collaborators: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        data = {"targetType": self.target_type}
        if self.media_type:
            data["mediaType"] = self.media_type
        if self.alt_text:
            data["altText"] = self.alt_text
        if self.collaborators:
            data["collaborators"] = self.collaborators
        return data


@dataclass
class TikTokTarget:
    """TikTok-specific target configuration"""
    target_type: str = "tiktok"
    privacy_level: TikTokPrivacy = TikTokPrivacy.PUBLIC
    disabled_comments: bool = False
    disabled_duet: bool = False
    disabled_stitch: bool = False
    is_branded_content: bool = False
    is_your_brand: bool = False
    is_ai_generated: bool = True
    title: Optional[str] = None
    auto_add_music: bool = False
    is_draft: bool = False
    image_cover_index: Optional[int] = None
    video_cover_timestamp: Optional[int] = None
    
    def to_dict(self) -> dict:
        data = {
            "targetType": self.target_type,
            "privacyLevel": self.privacy_level.value,
            "disabledComments": self.disabled_comments,
            "disabledDuet": self.disabled_duet,
            "disabledStitch": self.disabled_stitch,
            "isBrandedContent": self.is_branded_content,
            "isYourBrand": self.is_your_brand,
            "isAiGenerated": self.is_ai_generated,
        }
        if self.title:
            data["title"] = self.title
        if self.auto_add_music:
            data["autoAddMusic"] = self.auto_add_music
        if self.is_draft:
            data["isDraft"] = self.is_draft
        if self.image_cover_index is not None:
            data["imageCoverIndex"] = self.image_cover_index
        if self.video_cover_timestamp is not None:
            data["videoCoverTimestamp"] = self.video_cover_timestamp
        return data


@dataclass
class PinterestTarget:
    """Pinterest-specific target configuration"""
    target_type: str = "pinterest"
    board_id: str = ""
    title: Optional[str] = None
    alt_text: Optional[str] = None
    link: Optional[str] = None
    
    def to_dict(self) -> dict:
        data = {"targetType": self.target_type, "boardId": self.board_id}
        if self.title:
            data["title"] = self.title
        if self.alt_text:
            data["altText"] = self.alt_text
        if self.link:
            data["link"] = self.link
        return data


@dataclass
class ThreadsTarget:
    """Threads-specific target configuration"""
    target_type: str = "threads"
    reply_control: Optional[Literal["everyone", "accounts_you_follow", "mentioned_only"]] = None
    
    def to_dict(self) -> dict:
        data = {"targetType": self.target_type}
        if self.reply_control:
            data["replyControl"] = self.reply_control
        return data


@dataclass
class BlueskyTarget:
    """Bluesky-specific target configuration"""
    target_type: str = "bluesky"
    
    def to_dict(self) -> dict:
        return {"targetType": self.target_type}


@dataclass
class YouTubeTarget:
    """YouTube-specific target configuration"""
    target_type: str = "youtube"
    title: str = ""
    privacy_status: YouTubePrivacy = YouTubePrivacy.PUBLIC
    should_notify_subscribers: bool = True
    is_made_for_kids: bool = False
    contains_synthetic_media: bool = False
    
    def to_dict(self) -> dict:
        return {
            "targetType": self.target_type,
            "title": self.title,
            "privacyStatus": self.privacy_status.value,
            "shouldNotifySubscribers": self.should_notify_subscribers,
            "isMadeForKids": self.is_made_for_kids,
            "containsSyntheticMedia": self.contains_synthetic_media,
        }


@dataclass
class WebhookTarget:
    """Webhook target configuration"""
    target_type: str = "webhook"
    url: str = ""
    
    def to_dict(self) -> dict:
        return {"targetType": self.target_type, "url": self.url}


# =============================================================================
# BLOTATO API CLIENT
# =============================================================================

class BlotatoAPI:
    """
    Blotato API Client
    
    Full integration with Blotato's social media publishing and AI video creation APIs.
    
    Usage:
        client = BlotatoAPI(api_key="your-api-key")
        
        # Publish a post
        result = await client.publish_post(
            account_id="acc_123",
            content=PostContent(text="Hello world!", platform=Platform.TWITTER),
            target=TwitterTarget()
        )
        
        # Create AI video
        video = await client.create_video(
            script="you wake up as a pharaoh",
            style=VideoStyle.CINEMATIC,
            template=VideoTemplate.POV_WAKEUP
        )
    """
    
    BASE_URL = "https://backend.blotato.com/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BLOTATO_API_KEY")
        if not self.api_key:
            logger.warning("No Blotato API key provided. Set BLOTATO_API_KEY environment variable.")
    
    def _get_headers(self) -> dict:
        """Get request headers with authentication"""
        return {
            "Content-Type": "application/json",
            "blotato-api-key": self.api_key or "",
        }
    
    # =========================================================================
    # POST ENDPOINTS
    # =========================================================================
    
    async def publish_post(
        self,
        account_id: str,
        content: PostContent,
        target: Any,  # One of the target types
        scheduled_time: Optional[datetime] = None,
        use_next_free_slot: bool = False,
    ) -> Dict[str, Any]:
        """
        Publish or schedule a post to a social media platform.
        
        Args:
            account_id: The ID of the connected account for publishing
            content: The post content (text, media, platform)
            target: Platform-specific target configuration
            scheduled_time: Optional ISO 8601 timestamp for scheduling
            use_next_free_slot: Whether to use the next available slot
        
        Returns:
            dict with postSubmissionId
        
        Rate Limit: 30 requests/minute
        """
        payload = {
            "post": {
                "accountId": account_id,
                "content": content.to_dict(),
                "target": target.to_dict(),
            }
        }
        
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time.isoformat()
        elif use_next_free_slot:
            payload["useNextFreeSlot"] = True
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/posts",
                headers=self._get_headers(),
                json=payload
            )
            
            if response.status_code == 429:
                error_data = response.json()
                raise Exception(f"Rate limit exceeded: {error_data.get('message')}")
            
            response.raise_for_status()
            return response.json()
    
    async def publish_to_multiple_platforms(
        self,
        posts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Publish to multiple platforms at once.
        
        Args:
            posts: List of post configurations
        
        Returns:
            List of results for each post
        """
        results = []
        for post_config in posts:
            try:
                result = await self.publish_post(**post_config)
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        return results
    
    # =========================================================================
    # MEDIA ENDPOINTS
    # =========================================================================
    
    async def upload_media(self, url: str) -> Dict[str, Any]:
        """
        Upload media to Blotato's servers.
        
        Note: Upload is now optional - you can pass any publicly accessible URL
        directly into the mediaUrls parameter when publishing.
        
        Args:
            url: The URL of the media to upload (or base64 encoded data)
        
        Returns:
            dict with the new media URL hosted on Blotato
        
        Rate Limit: 10 requests/minute
        Max File Size: 200MB
        """
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.BASE_URL}/media",
                headers=self._get_headers(),
                json={"url": url}
            )
            
            if response.status_code == 429:
                error_data = response.json()
                raise Exception(f"Rate limit exceeded: {error_data.get('message')}")
            
            response.raise_for_status()
            return response.json()
    
    # =========================================================================
    # VIDEO CREATION ENDPOINTS
    # =========================================================================
    
    async def create_video(
        self,
        script: str,
        style: VideoStyle,
        template: VideoTemplate,
        template_options: Optional[Dict[str, Any]] = None,
        animate_first_image: bool = False,
        animate_all: bool = False,
        text_to_image_model: Optional[TextToImageModel] = None,
        image_to_video_model: Optional[ImageToVideoModel] = None,
    ) -> Dict[str, Any]:
        """
        Create an AI-generated video.
        
        Args:
            script: Script for the video (e.g., "you wake up as a pharaoh")
            style: Visual style (cinematic, cyberpunk, etc.)
            template: Video template to use
            template_options: Additional template-specific options
            animate_first_image: Whether to animate the first image
            animate_all: Whether to animate all images
            text_to_image_model: Model for generating images
            image_to_video_model: Model for generating video from images
        
        Returns:
            dict with video ID and status
        
        Rate Limit: 1 request/minute
        """
        template_data = {"id": template.value}
        if template_options:
            template_data.update(template_options)
        
        payload = {
            "script": script,
            "style": style.value,
            "template": template_data,
        }
        
        if animate_first_image:
            payload["animateFirstImage"] = True
        if animate_all:
            payload["animateAll"] = True
        if text_to_image_model:
            payload["textToImageModel"] = text_to_image_model.value
        if image_to_video_model:
            payload["imageToVideoModel"] = image_to_video_model.value
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.BASE_URL}/videos/creations",
                headers=self._get_headers(),
                json=payload
            )
            
            if response.status_code == 429:
                error_data = response.json()
                raise Exception(f"Rate limit exceeded: {error_data.get('message')}")
            
            response.raise_for_status()
            return response.json()
    
    async def create_pov_video(
        self,
        script: str,
        style: VideoStyle = VideoStyle.CINEMATIC,
        first_scene_text: Optional[str] = None,
        caption_position: Optional[Literal["top", "bottom", "middle"]] = "bottom",
        animate_first_image: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a POV (Point of View) style video.
        
        Args:
            script: Script describing the scenario (e.g., "you wake up as a pharaoh")
            style: Visual style
            first_scene_text: Optional custom text for first scene
            caption_position: Position of captions (top, bottom, middle, or None)
            animate_first_image: Whether to animate the first image
        
        Returns:
            dict with video ID and status
        """
        template_options = {}
        if first_scene_text:
            template_options["firstSceneText"] = first_scene_text
        if caption_position:
            template_options["captionPosition"] = caption_position
        
        return await self.create_video(
            script=script,
            style=style,
            template=VideoTemplate.POV_WAKEUP,
            template_options=template_options,
            animate_first_image=animate_first_image,
        )
    
    async def create_quote_slideshow(
        self,
        scenes: List[Dict[str, Any]],
        style: VideoStyle = VideoStyle.CINEMATIC,
        caption_position: Optional[Literal["top", "bottom", "middle"]] = "middle",
    ) -> Dict[str, Any]:
        """
        Create a quote card slideshow video.
        
        Args:
            scenes: List of scenes with prompt and optional text/textToImagePrompt
            style: Visual style
            caption_position: Position of captions
        
        Returns:
            dict with video ID and status
        
        Example scenes:
            [
                {"prompt": "inspiring quote about success"},
                {"prompt": "motivational quote", "text": "Never give up!"}
            ]
        """
        template_options = {
            "scenes": scenes,
        }
        if caption_position:
            template_options["captionPosition"] = caption_position
        
        return await self.create_video(
            script="1",  # Required but ignored for slideshows
            style=style,
            template=VideoTemplate.SLIDES_QUOTECARD,
            template_options=template_options,
        )
    
    async def create_narrated_video(
        self,
        script: str,
        style: VideoStyle = VideoStyle.CINEMATIC,
        voice_id: str = None,
        voice_name: str = "brian",
        caption_position: Optional[Literal["top", "bottom", "middle"]] = "bottom",
    ) -> Dict[str, Any]:
        """
        Create a narrated video with AI voice.
        
        Args:
            script: Full script for the video
            style: Visual style
            voice_id: ElevenLabs voice ID (or use voice_name)
            voice_name: Voice name from VOICE_IDS (e.g., "brian", "sarah")
            caption_position: Position of captions
        
        Returns:
            dict with video ID and status
        """
        if voice_id is None and voice_name:
            voice_info = VOICE_IDS.get(voice_name.lower())
            if voice_info:
                voice_id = voice_info["id"]
        
        template_options = {}
        if voice_id:
            template_options["voiceId"] = voice_id
        if caption_position:
            template_options["captionPosition"] = caption_position
        
        return await self.create_video(
            script=script,
            style=style,
            template=VideoTemplate.EMPTY,
            template_options=template_options,
        )
    
    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        Get the status of a video creation.
        
        Args:
            video_id: The video ID from create_video response
        
        Returns:
            dict with id, status, createdAt, mediaUrl, imageUrls
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.BASE_URL}/videos/creations/{video_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_video(self, video_id: str) -> Dict[str, Any]:
        """
        Delete a video.
        
        Args:
            video_id: The video ID to delete
        
        Returns:
            dict with deleted video ID
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.BASE_URL}/videos/{video_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def wait_for_video(
        self,
        video_id: str,
        timeout_seconds: int = 300,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for a video to complete creation.
        
        Args:
            video_id: The video ID to wait for
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between status checks
        
        Returns:
            dict with final video status including mediaUrl
        """
        import asyncio
        
        start_time = datetime.now()
        while True:
            status = await self.get_video_status(video_id)
            
            if status.get("item", {}).get("mediaUrl"):
                return status
            
            if status.get("item", {}).get("status") == "Failed":
                raise Exception(f"Video creation failed: {video_id}")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                raise Exception(f"Timeout waiting for video: {video_id}")
            
            await asyncio.sleep(poll_interval)
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    @staticmethod
    def get_available_voices() -> Dict[str, Dict[str, Any]]:
        """Get all available AI voices"""
        return VOICE_IDS
    
    @staticmethod
    def get_voice_by_characteristics(
        gender: Optional[str] = None,
        accent: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find voices matching characteristics.
        
        Args:
            gender: "male", "female", or "non-binary"
            accent: "American", "British", "Australian", etc.
            tags: List of tags like "narration", "social media", etc.
        
        Returns:
            List of matching voice info dicts
        """
        matches = []
        for voice_key, voice_info in VOICE_IDS.items():
            if gender and voice_info.get("gender") != gender:
                continue
            if accent and voice_info.get("accent") != accent:
                continue
            if tags:
                voice_tags = voice_info.get("tags", [])
                if not any(tag in voice_tags for tag in tags):
                    continue
            matches.append({**voice_info, "key": voice_key})
        return matches


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_blotato_client(api_key: Optional[str] = None) -> BlotatoAPI:
    """Get a configured Blotato API client"""
    return BlotatoAPI(api_key=api_key)


async def quick_post(
    account_id: str,
    text: str,
    platform: Platform,
    media_urls: List[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick helper to post to a platform.
    
    Args:
        account_id: Blotato account ID
        text: Post text
        platform: Target platform
        media_urls: Optional list of media URLs
        api_key: Optional API key (uses env var if not provided)
    
    Returns:
        Post submission result
    """
    client = BlotatoAPI(api_key=api_key)
    
    content = PostContent(
        text=text,
        platform=platform,
        media_urls=media_urls or []
    )
    
    # Create appropriate target
    target_map = {
        Platform.TWITTER: TwitterTarget(),
        Platform.LINKEDIN: LinkedInTarget(),
        Platform.THREADS: ThreadsTarget(),
        Platform.BLUESKY: BlueskyTarget(),
        Platform.INSTAGRAM: InstagramTarget(),
        Platform.TIKTOK: TikTokTarget(),
    }
    
    target = target_map.get(platform)
    if not target:
        raise ValueError(f"Unsupported platform for quick_post: {platform}")
    
    return await client.publish_post(
        account_id=account_id,
        content=content,
        target=target
    )

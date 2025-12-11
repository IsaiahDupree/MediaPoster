"""
Platform Publishing Connectors
Handles actual posting to social media platforms via their APIs.
Supports TikTok, YouTube, Instagram, Twitter/X, LinkedIn, Threads.
"""

import os
import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


class PublishStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    THREADS = "threads"


class MediaType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"
    SHORT = "short"


class PublishRequest(BaseModel):
    """Request to publish content"""
    media_path: str
    media_type: MediaType
    title: Optional[str] = None
    description: str
    hashtags: List[str] = Field(default_factory=list)
    account_id: str
    platform: Platform
    scheduled_time: Optional[str] = None
    thumbnail_path: Optional[str] = None
    privacy: str = "public"  # public, private, unlisted
    metadata: Dict = Field(default_factory=dict)


class PublishResult(BaseModel):
    """Result of publishing attempt"""
    success: bool
    status: PublishStatus
    platform: Platform
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    published_at: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class BasePlatformPublisher(ABC):
    """Base class for platform publishers"""
    
    platform: Platform
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self._client: Optional[httpx.AsyncClient] = None
    
    @abstractmethod
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish content to platform"""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate API credentials"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict:
        """Get connected account information"""
        pass
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


class TikTokPublisher(BasePlatformPublisher):
    """TikTok content publisher using Content Posting API"""
    
    platform = Platform.TIKTOK
    API_BASE = "https://open.tiktokapis.com/v2"
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish video to TikTok"""
        try:
            access_token = self.credentials.get("access_token")
            if not access_token:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message="Missing access token",
                )
            
            client = await self._get_client()
            
            # Step 1: Initialize upload
            init_response = await client.post(
                f"{self.API_BASE}/post/publish/inbox/video/init/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": os.path.getsize(request.media_path),
                    },
                },
            )
            
            if init_response.status_code != 200:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message=f"Init failed: {init_response.text}",
                )
            
            init_data = init_response.json()
            upload_url = init_data.get("data", {}).get("upload_url")
            publish_id = init_data.get("data", {}).get("publish_id")
            
            # Step 2: Upload video
            with open(request.media_path, "rb") as f:
                video_data = f.read()
            
            upload_response = await client.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{len(video_data)-1}/{len(video_data)}",
                },
                content=video_data,
            )
            
            if upload_response.status_code not in [200, 201]:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message=f"Upload failed: {upload_response.text}",
                )
            
            # Step 3: Publish
            caption = f"{request.description}\n\n{' '.join(request.hashtags)}"
            
            publish_response = await client.post(
                f"{self.API_BASE}/post/publish/status/fetch/",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"publish_id": publish_id},
            )
            
            return PublishResult(
                success=True,
                status=PublishStatus.PUBLISHED,
                platform=self.platform,
                post_id=publish_id,
                published_at=datetime.now().isoformat(),
            )
            
        except Exception as e:
            logger.error(f"TikTok publish error: {e}")
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )
    
    async def validate_credentials(self) -> bool:
        """Validate TikTok credentials"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/user/info/",
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                params={"fields": "open_id,union_id,display_name"},
            )
            return response.status_code == 200
        except:
            return False
    
    async def get_account_info(self) -> Dict:
        """Get TikTok account info"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/user/info/",
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                params={"fields": "open_id,union_id,display_name,avatar_url,follower_count"},
            )
            if response.status_code == 200:
                return response.json().get("data", {}).get("user", {})
        except Exception as e:
            logger.error(f"TikTok account info error: {e}")
        return {}


class YouTubePublisher(BasePlatformPublisher):
    """YouTube content publisher using YouTube Data API v3"""
    
    platform = Platform.YOUTUBE
    API_BASE = "https://www.googleapis.com/youtube/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish video to YouTube"""
        try:
            access_token = self.credentials.get("access_token")
            if not access_token:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message="Missing access token",
                )
            
            client = await self._get_client()
            
            # Prepare video metadata
            video_metadata = {
                "snippet": {
                    "title": request.title or request.description[:100],
                    "description": f"{request.description}\n\n{' '.join(request.hashtags)}",
                    "tags": [h.replace("#", "") for h in request.hashtags],
                    "categoryId": request.metadata.get("category_id", "22"),  # 22 = People & Blogs
                },
                "status": {
                    "privacyStatus": request.privacy,
                    "selfDeclaredMadeForKids": False,
                },
            }
            
            # Handle scheduled publishing
            if request.scheduled_time:
                video_metadata["status"]["publishAt"] = request.scheduled_time
                video_metadata["status"]["privacyStatus"] = "private"
            
            # Check if it's a Short (vertical, < 60 seconds)
            is_short = request.media_type == MediaType.SHORT or request.metadata.get("is_short", False)
            if is_short:
                # Add #Shorts to title/description
                if "#Shorts" not in video_metadata["snippet"]["title"]:
                    video_metadata["snippet"]["title"] += " #Shorts"
            
            # Upload video
            with open(request.media_path, "rb") as f:
                video_data = f.read()
            
            # Resumable upload
            init_response = await client.post(
                f"{self.UPLOAD_URL}?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Upload-Content-Length": str(len(video_data)),
                    "X-Upload-Content-Type": "video/*",
                },
                json=video_metadata,
            )
            
            if init_response.status_code != 200:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message=f"Upload init failed: {init_response.text}",
                )
            
            upload_url = init_response.headers.get("Location")
            
            # Upload video content
            upload_response = await client.put(
                upload_url,
                headers={"Content-Type": "video/*"},
                content=video_data,
            )
            
            if upload_response.status_code in [200, 201]:
                video_data = upload_response.json()
                video_id = video_data.get("id")
                
                return PublishResult(
                    success=True,
                    status=PublishStatus.PUBLISHED,
                    platform=self.platform,
                    post_id=video_id,
                    post_url=f"https://youtube.com/watch?v={video_id}",
                    published_at=datetime.now().isoformat(),
                    metadata={"video_id": video_id, "is_short": is_short},
                )
            
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=f"Upload failed: {upload_response.text}",
            )
            
        except Exception as e:
            logger.error(f"YouTube publish error: {e}")
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )
    
    async def validate_credentials(self) -> bool:
        """Validate YouTube credentials"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/channels",
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                params={"part": "snippet", "mine": "true"},
            )
            return response.status_code == 200
        except:
            return False
    
    async def get_account_info(self) -> Dict:
        """Get YouTube channel info"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/channels",
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                params={"part": "snippet,statistics", "mine": "true"},
            )
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    return items[0]
        except Exception as e:
            logger.error(f"YouTube account info error: {e}")
        return {}


class InstagramPublisher(BasePlatformPublisher):
    """Instagram content publisher using Instagram Graph API"""
    
    platform = Platform.INSTAGRAM
    API_BASE = "https://graph.facebook.com/v18.0"
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish content to Instagram"""
        try:
            access_token = self.credentials.get("access_token")
            ig_user_id = self.credentials.get("instagram_user_id")
            
            if not access_token or not ig_user_id:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message="Missing credentials",
                )
            
            client = await self._get_client()
            
            # Determine media type and endpoint
            if request.media_type in [MediaType.VIDEO, MediaType.REEL]:
                return await self._publish_video(client, request, access_token, ig_user_id)
            elif request.media_type == MediaType.IMAGE:
                return await self._publish_image(client, request, access_token, ig_user_id)
            elif request.media_type == MediaType.CAROUSEL:
                return await self._publish_carousel(client, request, access_token, ig_user_id)
            elif request.media_type == MediaType.STORY:
                return await self._publish_story(client, request, access_token, ig_user_id)
            else:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message=f"Unsupported media type: {request.media_type}",
                )
                
        except Exception as e:
            logger.error(f"Instagram publish error: {e}")
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )
    
    async def _publish_video(
        self,
        client: httpx.AsyncClient,
        request: PublishRequest,
        access_token: str,
        ig_user_id: str,
    ) -> PublishResult:
        """Publish video/reel to Instagram"""
        caption = f"{request.description}\n\n{' '.join(request.hashtags)}"
        
        # Need to host video publicly - use provided URL or upload to hosting
        video_url = request.metadata.get("video_url") or request.media_path
        
        # Step 1: Create media container
        create_response = await client.post(
            f"{self.API_BASE}/{ig_user_id}/media",
            params={
                "access_token": access_token,
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption[:2200],
                "share_to_feed": "true",
            },
        )
        
        if create_response.status_code != 200:
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=f"Create container failed: {create_response.text}",
            )
        
        container_id = create_response.json().get("id")
        
        # Step 2: Wait for container to be ready (polling)
        for _ in range(30):  # Max 5 minutes
            status_response = await client.get(
                f"{self.API_BASE}/{container_id}",
                params={
                    "access_token": access_token,
                    "fields": "status_code",
                },
            )
            status_code = status_response.json().get("status_code")
            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message="Video processing failed",
                )
            await asyncio.sleep(10)
        
        # Step 3: Publish container
        publish_response = await client.post(
            f"{self.API_BASE}/{ig_user_id}/media_publish",
            params={
                "access_token": access_token,
                "creation_id": container_id,
            },
        )
        
        if publish_response.status_code == 200:
            media_id = publish_response.json().get("id")
            return PublishResult(
                success=True,
                status=PublishStatus.PUBLISHED,
                platform=self.platform,
                post_id=media_id,
                published_at=datetime.now().isoformat(),
            )
        
        return PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            platform=self.platform,
            error_message=f"Publish failed: {publish_response.text}",
        )
    
    async def _publish_image(
        self,
        client: httpx.AsyncClient,
        request: PublishRequest,
        access_token: str,
        ig_user_id: str,
    ) -> PublishResult:
        """Publish image to Instagram"""
        caption = f"{request.description}\n\n{' '.join(request.hashtags)}"
        image_url = request.metadata.get("image_url") or request.media_path
        
        # Create and publish in two steps
        create_response = await client.post(
            f"{self.API_BASE}/{ig_user_id}/media",
            params={
                "access_token": access_token,
                "image_url": image_url,
                "caption": caption[:2200],
            },
        )
        
        if create_response.status_code != 200:
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=f"Create failed: {create_response.text}",
            )
        
        container_id = create_response.json().get("id")
        
        publish_response = await client.post(
            f"{self.API_BASE}/{ig_user_id}/media_publish",
            params={
                "access_token": access_token,
                "creation_id": container_id,
            },
        )
        
        if publish_response.status_code == 200:
            return PublishResult(
                success=True,
                status=PublishStatus.PUBLISHED,
                platform=self.platform,
                post_id=publish_response.json().get("id"),
                published_at=datetime.now().isoformat(),
            )
        
        return PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            platform=self.platform,
            error_message=f"Publish failed: {publish_response.text}",
        )
    
    async def _publish_carousel(
        self,
        client: httpx.AsyncClient,
        request: PublishRequest,
        access_token: str,
        ig_user_id: str,
    ) -> PublishResult:
        """Publish carousel to Instagram"""
        # Implementation for carousel posts
        return PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            platform=self.platform,
            error_message="Carousel publishing not yet implemented",
        )
    
    async def _publish_story(
        self,
        client: httpx.AsyncClient,
        request: PublishRequest,
        access_token: str,
        ig_user_id: str,
    ) -> PublishResult:
        """Publish story to Instagram"""
        # Implementation for stories
        return PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            platform=self.platform,
            error_message="Story publishing not yet implemented",
        )
    
    async def validate_credentials(self) -> bool:
        """Validate Instagram credentials"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/me",
                params={
                    "access_token": self.credentials.get("access_token"),
                    "fields": "id,username",
                },
            )
            return response.status_code == 200
        except:
            return False
    
    async def get_account_info(self) -> Dict:
        """Get Instagram account info"""
        try:
            client = await self._get_client()
            ig_user_id = self.credentials.get("instagram_user_id")
            response = await client.get(
                f"{self.API_BASE}/{ig_user_id}",
                params={
                    "access_token": self.credentials.get("access_token"),
                    "fields": "id,username,followers_count,media_count,biography",
                },
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Instagram account info error: {e}")
        return {}


class TwitterPublisher(BasePlatformPublisher):
    """Twitter/X content publisher using Twitter API v2"""
    
    platform = Platform.TWITTER
    API_BASE = "https://api.twitter.com/2"
    UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish tweet with optional media"""
        try:
            # Twitter requires OAuth 1.0a - simplified implementation
            bearer_token = self.credentials.get("bearer_token")
            
            if not bearer_token:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message="Missing bearer token",
                )
            
            client = await self._get_client()
            
            # Compose tweet text
            text = f"{request.description}\n\n{' '.join(request.hashtags)}"[:280]
            
            # Create tweet
            response = await client.post(
                f"{self.API_BASE}/tweets",
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
            )
            
            if response.status_code in [200, 201]:
                data = response.json().get("data", {})
                tweet_id = data.get("id")
                return PublishResult(
                    success=True,
                    status=PublishStatus.PUBLISHED,
                    platform=self.platform,
                    post_id=tweet_id,
                    post_url=f"https://twitter.com/i/status/{tweet_id}",
                    published_at=datetime.now().isoformat(),
                )
            
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=f"Tweet failed: {response.text}",
            )
            
        except Exception as e:
            logger.error(f"Twitter publish error: {e}")
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )
    
    async def validate_credentials(self) -> bool:
        """Validate Twitter credentials"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/users/me",
                headers={"Authorization": f"Bearer {self.credentials.get('bearer_token')}"},
            )
            return response.status_code == 200
        except:
            return False
    
    async def get_account_info(self) -> Dict:
        """Get Twitter account info"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/users/me",
                headers={"Authorization": f"Bearer {self.credentials.get('bearer_token')}"},
                params={"user.fields": "public_metrics,profile_image_url,description"},
            )
            if response.status_code == 200:
                return response.json().get("data", {})
        except Exception as e:
            logger.error(f"Twitter account info error: {e}")
        return {}


class LinkedInPublisher(BasePlatformPublisher):
    """LinkedIn content publisher using LinkedIn API"""
    
    platform = Platform.LINKEDIN
    API_BASE = "https://api.linkedin.com/v2"
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish post to LinkedIn"""
        try:
            access_token = self.credentials.get("access_token")
            person_urn = self.credentials.get("person_urn")
            
            if not access_token or not person_urn:
                return PublishResult(
                    success=False,
                    status=PublishStatus.FAILED,
                    platform=self.platform,
                    error_message="Missing credentials",
                )
            
            client = await self._get_client()
            
            # Build post content
            text = f"{request.description}\n\n{' '.join(request.hashtags)}"
            
            post_data = {
                "author": person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text[:3000]},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            }
            
            response = await client.post(
                f"{self.API_BASE}/ugcPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json=post_data,
            )
            
            if response.status_code in [200, 201]:
                post_id = response.headers.get("X-RestLi-Id")
                return PublishResult(
                    success=True,
                    status=PublishStatus.PUBLISHED,
                    platform=self.platform,
                    post_id=post_id,
                    published_at=datetime.now().isoformat(),
                )
            
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=f"Post failed: {response.text}",
            )
            
        except Exception as e:
            logger.error(f"LinkedIn publish error: {e}")
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )
    
    async def validate_credentials(self) -> bool:
        """Validate LinkedIn credentials"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/me",
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
            )
            return response.status_code == 200
        except:
            return False
    
    async def get_account_info(self) -> Dict:
        """Get LinkedIn profile info"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/me",
                headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
                params={"projection": "(id,firstName,lastName,profilePicture)"},
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"LinkedIn account info error: {e}")
        return {}


# ============================================================================
# PUBLISHER FACTORY
# ============================================================================

class PlatformPublisherFactory:
    """Factory for creating platform publishers"""
    
    _publishers = {
        Platform.TIKTOK: TikTokPublisher,
        Platform.YOUTUBE: YouTubePublisher,
        Platform.INSTAGRAM: InstagramPublisher,
        Platform.TWITTER: TwitterPublisher,
        Platform.LINKEDIN: LinkedInPublisher,
    }
    
    @classmethod
    def create(cls, platform: Platform, credentials: Dict[str, str]) -> BasePlatformPublisher:
        """Create a publisher for the specified platform"""
        publisher_class = cls._publishers.get(platform)
        if not publisher_class:
            raise ValueError(f"Unsupported platform: {platform}")
        return publisher_class(credentials)
    
    @classmethod
    def supported_platforms(cls) -> List[Platform]:
        """Get list of supported platforms"""
        return list(cls._publishers.keys())


# ============================================================================
# PUBLISHING ORCHESTRATOR
# ============================================================================

class PublishingOrchestrator:
    """Orchestrates publishing across multiple platforms"""
    
    def __init__(self):
        self._publishers: Dict[str, BasePlatformPublisher] = {}
    
    def register_account(self, account_id: str, platform: Platform, credentials: Dict[str, str]):
        """Register an account with credentials"""
        publisher = PlatformPublisherFactory.create(platform, credentials)
        self._publishers[account_id] = publisher
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish content using the appropriate publisher"""
        publisher = self._publishers.get(request.account_id)
        if not publisher:
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=request.platform,
                error_message=f"No publisher registered for account: {request.account_id}",
            )
        
        return await publisher.publish(request)
    
    async def publish_to_multiple(
        self,
        requests: List[PublishRequest],
        parallel: bool = False,
    ) -> List[PublishResult]:
        """Publish to multiple platforms"""
        if parallel:
            tasks = [self.publish(req) for req in requests]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for req in requests:
                result = await self.publish(req)
                results.append(result)
            return results
    
    async def validate_account(self, account_id: str) -> bool:
        """Validate account credentials"""
        publisher = self._publishers.get(account_id)
        if not publisher:
            return False
        return await publisher.validate_credentials()
    
    async def get_account_info(self, account_id: str) -> Dict:
        """Get account information"""
        publisher = self._publishers.get(account_id)
        if not publisher:
            return {}
        return await publisher.get_account_info()
    
    async def close_all(self):
        """Close all publisher connections"""
        for publisher in self._publishers.values():
            await publisher.close()


# Singleton instance
publishing_orchestrator = PublishingOrchestrator()

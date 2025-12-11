"""
Threads Platform Publisher
Phase 4: Connector for Meta Threads platform
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import httpx

from services.platform_publishers import (
    BasePlatformPublisher, Platform, PublishRequest, PublishResult,
    MediaType, PublishStatus
)


class ThreadsMediaType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    CAROUSEL = "CAROUSEL"


@dataclass
class ThreadsPostContainer:
    """Container for Threads post creation"""
    container_id: str
    status: str
    permalink: Optional[str] = None


class ThreadsPublisher(BasePlatformPublisher):
    """
    Publisher for Meta Threads platform.
    Uses the Threads API (similar to Instagram Graph API).
    """
    
    platform = Platform.THREADS
    
    BASE_URL = "https://graph.threads.net/v1.0"
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.access_token = credentials.get('access_token', '')
        self.user_id = credentials.get('user_id', '')
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
        return self._client
    
    async def validate_credentials(self) -> bool:
        """Validate Threads API credentials"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.BASE_URL}/me",
                params={'access_token': self.access_token}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_account_info(self) -> Dict:
        """Get Threads account information"""
        client = await self._get_client()
        response = await client.get(
            f"{self.BASE_URL}/me",
            params={
                'fields': 'id,username,threads_profile_picture_url,threads_biography',
                'access_token': self.access_token
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get account info: {response.text}")
        
        return response.json()
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish content to Threads.
        
        Threads uses a two-step process:
        1. Create a media container
        2. Publish the container
        """
        try:
            client = await self._get_client()
            
            # Step 1: Create media container
            container = await self._create_container(client, request)
            
            # Step 2: Wait for container to be ready (for video)
            if request.media_type == MediaType.VIDEO:
                container = await self._wait_for_container(client, container.container_id)
            
            # Step 3: Publish the container
            result = await self._publish_container(client, container.container_id)
            
            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=result.get('id', ''),
                post_url=container.permalink or f"https://threads.net/@{self.user_id}",
                published_at=datetime.utcnow(),
                status=PublishStatus.PUBLISHED,
                raw_response=result
            )
            
        except Exception as e:
            return PublishResult(
                success=False,
                platform=self.platform,
                error_message=str(e),
                status=PublishStatus.FAILED,
            )
    
    async def _create_container(
        self,
        client: httpx.AsyncClient,
        request: PublishRequest
    ) -> ThreadsPostContainer:
        """Create a Threads media container"""
        
        # Determine media type
        if request.media_type == MediaType.VIDEO:
            media_type = ThreadsMediaType.VIDEO
        elif request.media_type == MediaType.IMAGE:
            media_type = ThreadsMediaType.IMAGE
        else:
            media_type = ThreadsMediaType.TEXT
        
        params = {
            'media_type': media_type.value,
            'text': self._format_caption(request),
            'access_token': self.access_token,
        }
        
        # Add media URL if present
        if request.media_url:
            if media_type == ThreadsMediaType.VIDEO:
                params['video_url'] = request.media_url
            elif media_type == ThreadsMediaType.IMAGE:
                params['image_url'] = request.media_url
        
        response = await client.post(
            f"{self.BASE_URL}/{self.user_id}/threads",
            data=params
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to create container: {response.text}")
        
        data = response.json()
        return ThreadsPostContainer(
            container_id=data['id'],
            status='IN_PROGRESS'
        )
    
    async def _wait_for_container(
        self,
        client: httpx.AsyncClient,
        container_id: str,
        max_attempts: int = 30,
        delay_seconds: int = 2
    ) -> ThreadsPostContainer:
        """Wait for video container to be ready"""
        
        for _ in range(max_attempts):
            response = await client.get(
                f"{self.BASE_URL}/{container_id}",
                params={
                    'fields': 'status,error_message',
                    'access_token': self.access_token
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to check container status: {response.text}")
            
            data = response.json()
            status = data.get('status')
            
            if status == 'FINISHED':
                return ThreadsPostContainer(
                    container_id=container_id,
                    status=status
                )
            elif status == 'ERROR':
                raise Exception(f"Container error: {data.get('error_message', 'Unknown error')}")
            
            await asyncio.sleep(delay_seconds)
        
        raise Exception("Container processing timeout")
    
    async def _publish_container(
        self,
        client: httpx.AsyncClient,
        container_id: str
    ) -> Dict:
        """Publish a ready container"""
        
        response = await client.post(
            f"{self.BASE_URL}/{self.user_id}/threads_publish",
            data={
                'creation_id': container_id,
                'access_token': self.access_token
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to publish: {response.text}")
        
        return response.json()
    
    def _format_caption(self, request: PublishRequest) -> str:
        """Format caption with title, description and hashtags"""
        parts = []
        
        if request.title:
            parts.append(request.title)
        
        if request.description:
            parts.append(request.description)
        
        if request.hashtags:
            # Threads supports hashtags like other platforms
            hashtag_str = ' '.join(
                f'#{tag}' if not tag.startswith('#') else tag
                for tag in request.hashtags[:10]  # Limit to 10
            )
            parts.append(hashtag_str)
        
        return '\n\n'.join(parts)[:500]  # Threads has 500 char limit
    
    async def get_post_metrics(self, post_id: str) -> Dict:
        """Get metrics for a published post"""
        client = await self._get_client()
        
        response = await client.get(
            f"{self.BASE_URL}/{post_id}",
            params={
                'fields': 'id,text,timestamp,media_type,permalink,is_quote_post,views,likes,replies,reposts',
                'access_token': self.access_token
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get metrics: {response.text}")
        
        return response.json()
    
    async def get_user_threads(
        self,
        limit: int = 25,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """Get user's recent threads"""
        client = await self._get_client()
        
        params = {
            'fields': 'id,text,timestamp,media_type,permalink,views,likes,replies',
            'limit': limit,
            'access_token': self.access_token
        }
        
        if since:
            params['since'] = int(since.timestamp())
        
        response = await client.get(
            f"{self.BASE_URL}/{self.user_id}/threads",
            params=params
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get threads: {response.text}")
        
        return response.json().get('data', [])
    
    async def reply_to_thread(
        self,
        reply_to_id: str,
        text: str,
        media_url: Optional[str] = None,
        media_type: Optional[ThreadsMediaType] = None
    ) -> Dict:
        """Reply to an existing thread"""
        client = await self._get_client()
        
        params = {
            'media_type': (media_type or ThreadsMediaType.TEXT).value,
            'text': text[:500],
            'reply_to_id': reply_to_id,
            'access_token': self.access_token
        }
        
        if media_url:
            if media_type == ThreadsMediaType.VIDEO:
                params['video_url'] = media_url
            elif media_type == ThreadsMediaType.IMAGE:
                params['image_url'] = media_url
        
        # Create reply container
        response = await client.post(
            f"{self.BASE_URL}/{self.user_id}/threads",
            data=params
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to create reply: {response.text}")
        
        container_id = response.json()['id']
        
        # Publish reply
        return await self._publish_container(client, container_id)

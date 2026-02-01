"""
Microservices Client - Interface for calling external microservices.
Provides unified access to media-pipeline, content-intelligence, and other services.
"""
import os
import httpx
from typing import Optional, Dict, Any, List
from loguru import logger


class MicroservicesClient:
    """Client for calling MediaPoster ecosystem microservices."""
    
    def __init__(self):
        self.services = {
            "media": os.getenv("MEDIA_PIPELINE_URL", "http://localhost:6004"),
            "ai": os.getenv("CONTENT_INTEL_URL", "http://localhost:6006"),
            "safari": os.getenv("SAFARI_URL", "http://localhost:6001"),
            "remotion": os.getenv("REMOTION_URL", "http://localhost:6002"),
        }
        self.timeout = 30.0
        self._health_cache: Dict[str, bool] = {}
    
    async def _call(
        self,
        service: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST"
    ) -> Dict[str, Any]:
        """Make HTTP request to a service."""
        if service not in self.services:
            raise ValueError(f"Unknown service: {service}")
        
        url = f"{self.services[service]}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "POST":
                    response = await client.post(url, json=data)
                elif method.upper() == "GET":
                    response = await client.get(url, params=data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.warning(f"Service {service} not reachable at {url}")
            return {"status": "error", "error": f"Service {service} not available"}
        except Exception as e:
            logger.error(f"Error calling {service}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def health_check(self, service: str) -> bool:
        """Check if a service is healthy."""
        try:
            result = await self._call(service, "/health", method="GET")
            healthy = result.get("status") == "healthy"
            self._health_cache[service] = healthy
            return healthy
        except:
            self._health_cache[service] = False
            return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all services."""
        for service in self.services:
            await self.health_check(service)
        return self._health_cache.copy()
    
    # ==================== Media Pipeline API ====================
    
    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """Analyze a video file using media-pipeline service."""
        return await self._call("media", "/api/analyze", {"video_path": video_path})
    
    async def generate_thumbnails(
        self, 
        video_path: str, 
        count: int = 5
    ) -> Dict[str, Any]:
        """Generate thumbnails from video."""
        return await self._call("media", "/api/thumbnail/generate", {
            "video_path": video_path,
            "count": count
        })
    
    async def detect_format(self, file_path: str) -> Dict[str, Any]:
        """Detect media format."""
        return await self._call("media", "/api/format/detect", {"file_path": file_path})
    
    async def extract_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float
    ) -> Dict[str, Any]:
        """Extract a clip from video."""
        return await self._call("media", "/api/clip/extract", {
            "video_path": video_path,
            "start_time": start_time,
            "end_time": end_time
        })
    
    async def check_duplicate(self, file_path: str) -> Dict[str, Any]:
        """Check if content is a duplicate."""
        return await self._call("media", "/api/deduplicate/check", {"file_path": file_path})
    
    # ==================== Content Intelligence API ====================
    
    async def analyze_content(
        self,
        title: str = "",
        description: str = "",
        transcript: str = ""
    ) -> Dict[str, Any]:
        """Analyze content for insights."""
        return await self._call("ai", "/api/analyze/content", {
            "title": title,
            "description": description,
            "transcript": transcript
        })
    
    async def generate_titles(
        self,
        content: str,
        platform: str = "tiktok",
        style: str = "viral",
        count: int = 5
    ) -> List[str]:
        """Generate viral titles for content."""
        result = await self._call("ai", "/api/generate/title", {
            "content": content,
            "platform": platform,
            "style": style,
            "count": count
        })
        return result.get("titles", [])
    
    async def generate_caption(
        self,
        content: str,
        platform: str = "instagram",
        include_hashtags: bool = True
    ) -> Dict[str, Any]:
        """Generate caption with hashtags."""
        return await self._call("ai", "/api/generate/caption", {
            "content": content,
            "platform": platform,
            "include_hashtags": include_hashtags
        })
    
    async def score_fate(
        self,
        content_id: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """Calculate FATE score for content."""
        result = await self._call("ai", "/api/score/fate", {
            "content_id": content_id,
            "metrics": metrics or {}
        })
        return result.get("fate_score", {})
    
    async def classify_awareness(self, content: str) -> Dict[str, Any]:
        """Classify content awareness level."""
        return await self._call("ai", "/api/classify/awareness", {"content": content})
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        return await self._call("ai", "/api/analyze/sentiment", {"text": text})
    
    async def analyze_vision(self, image_path: str) -> Dict[str, Any]:
        """Analyze image content."""
        return await self._call("ai", "/api/vision/analyze", {"image_path": image_path})
    
    async def get_recommendations(
        self,
        content_id: str,
        recommendation_type: str = "similar",
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Get content recommendations."""
        result = await self._call("ai", "/api/recommend", {
            "content_id": content_id,
            "type": recommendation_type,
            "count": count
        })
        return result.get("recommendations", [])


# Singleton instance
_client: Optional[MicroservicesClient] = None


def get_microservices_client() -> MicroservicesClient:
    """Get the shared microservices client instance."""
    global _client
    if _client is None:
        _client = MicroservicesClient()
    return _client

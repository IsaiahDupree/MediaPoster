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
    
    async def detect_format(
        self, 
        file_path: str,
        transcript: str = "",
        visual_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Detect media format using FormatDetector."""
        return await self._call("media", "/api/format/detect", {
            "file_path": file_path,
            "transcript": transcript,
            "visual_analysis": visual_analysis or {}
        })
    
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
    
    async def transcribe(
        self,
        video_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe video/audio using Whisper."""
        return await self._call("media", "/api/transcribe", {
            "video_path": video_path,
            "language": language
        })
    
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
        content: str,
        content_id: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """Calculate FATE score for content text."""
        result = await self._call("ai", "/api/score/fate", {
            "content": content,
            "content_id": content_id or "",
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
    
    # ==================== New Media Pipeline Endpoints ====================
    
    async def orchestrate_plan(
        self,
        script: str,
        title: str = "Untitled",
        target_duration: int = 60
    ) -> Dict[str, Any]:
        """Create a clip plan from a script."""
        return await self._call("media", "/api/orchestrate/plan", {
            "script": script,
            "title": title,
            "target_duration": target_duration
        })
    
    async def generate_tts(
        self,
        text: str,
        voice: str = "default",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate text-to-speech audio."""
        return await self._call("media", "/api/tts/generate", {
            "text": text,
            "voice": voice,
            "output_path": output_path
        })
    
    async def search_music(
        self,
        query: str = "",
        mood: str = "",
        genre: str = "",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search for music tracks."""
        return await self._call("media", "/api/music/search", {
            "query": query,
            "mood": mood,
            "genre": genre,
            "limit": limit
        })
    
    async def search_sfx(
        self,
        query: str,
        category: str = "",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for sound effects."""
        return await self._call("media", "/api/sfx/search", {
            "query": query,
            "category": category,
            "limit": limit
        })
    
    async def render_video(
        self,
        timeline: Dict[str, Any],
        output_path: str,
        format: str = "mp4"
    ) -> Dict[str, Any]:
        """Render a video from a timeline."""
        return await self._call("media", "/api/render/video", {
            "timeline": timeline,
            "output_path": output_path,
            "format": format
        })
    
    async def analyze_audio(self, video_path: str) -> Dict[str, Any]:
        """Analyze audio from a video file."""
        return await self._call("media", "/api/audio/analyze", {"video_path": video_path})
    
    # ==================== New Content Intelligence Endpoints ====================
    
    async def create_narrative_plan(
        self,
        goal: str,
        duration_days: int = 30,
        platforms: List[str] = None
    ) -> Dict[str, Any]:
        """Create a narrative content plan."""
        return await self._call("ai", "/api/narrative/plan", {
            "goal": goal,
            "duration_days": duration_days,
            "platforms": platforms or ["instagram", "tiktok"]
        })
    
    async def generate_hypothesis(
        self,
        content_type: str,
        metric: str = "engagement",
        historical_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a content experiment hypothesis."""
        return await self._call("ai", "/api/experiments/hypothesis", {
            "content_type": content_type,
            "metric": metric,
            "historical_data": historical_data or {}
        })
    
    async def analyze_competitor(
        self,
        handle: str,
        platform: str = "instagram"
    ) -> Dict[str, Any]:
        """Analyze competitor content."""
        return await self._call("ai", "/api/competitor/analyze", {
            "handle": handle,
            "platform": platform
        })
    
    async def detect_trends(
        self,
        platform: str = "tiktok",
        category: str = "",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Detect current trends."""
        return await self._call("ai", "/api/trends/detect", {
            "platform": platform,
            "category": category,
            "limit": limit
        })
    
    async def generate_brief(
        self,
        topic: str,
        format: str = "short_video",
        platform: str = "instagram"
    ) -> Dict[str, Any]:
        """Generate a content brief."""
        return await self._call("ai", "/api/brief/generate", {
            "topic": topic,
            "format": format,
            "platform": platform
        })
    
    async def predict_engagement(
        self,
        title: str,
        description: str = "",
        platform: str = "instagram"
    ) -> Dict[str, Any]:
        """Predict engagement for content."""
        return await self._call("ai", "/api/engagement/predict", {
            "title": title,
            "description": description,
            "platform": platform
        })
    
    # ==================== Latest Media Pipeline Endpoints ====================
    
    async def scrape_instagram(self, username: str) -> Dict[str, Any]:
        """Scrape Instagram profile/posts data."""
        return await self._call("media", "/api/scrape/instagram", {"username": username})
    
    async def get_workers_status(self) -> Dict[str, Any]:
        """Get status of background workers."""
        return await self._call("media", "/api/workers/status", method="GET")
    
    async def remove_background(
        self,
        file_path: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Remove background from video/image."""
        return await self._call("media", "/api/matting/remove-bg", {
            "file_path": file_path,
            "output_path": output_path
        })
    
    # ==================== Latest Content Intelligence Endpoints ====================
    
    async def dm_outreach(
        self,
        prospects: List[str],
        message_template: str,
        platform: str = "instagram"
    ) -> Dict[str, Any]:
        """Send DM outreach campaign."""
        return await self._call("ai", "/api/dm/outreach", {
            "prospects": prospects,
            "message_template": message_template,
            "platform": platform
        })
    
    async def configure_auto_reply(
        self,
        platform: str = "instagram",
        rules: List[Dict[str, Any]] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Configure auto-reply for inbox."""
        return await self._call("ai", "/api/inbox/auto-reply", {
            "platform": platform,
            "rules": rules or [],
            "enabled": enabled
        })
    
    async def generate_hashtags(
        self,
        content: str,
        platform: str = "instagram",
        count: int = 30
    ) -> Dict[str, Any]:
        """Generate relevant hashtags for content."""
        return await self._call("ai", "/api/hashtags/generate", {
            "content": content,
            "platform": platform,
            "count": count
        })
    
    # ==================== External Repo Integrations ====================
    
    # Media Pipeline - TTS & Remotion
    async def generate_indextts2(
        self,
        text: str,
        voice_reference: Optional[str] = None,
        emotion: str = "neutral"
    ) -> Dict[str, Any]:
        """Generate TTS using IndexTTS2."""
        return await self._call("media", "/api/tts/indextts2", {
            "text": text,
            "voice_reference": voice_reference,
            "emotion": emotion
        })
    
    async def render_remotion(
        self,
        brief: Dict[str, Any],
        template: str = "BriefComposition"
    ) -> Dict[str, Any]:
        """Render video using Remotion."""
        return await self._call("media", "/api/remotion/render", {
            "brief": brief,
            "template": template
        })
    
    async def generate_remotion_brief(
        self,
        script: str,
        title: str = "Untitled",
        style: str = "default"
    ) -> Dict[str, Any]:
        """Generate a video brief for Remotion."""
        return await self._call("media", "/api/remotion/brief", {
            "script": script,
            "title": title,
            "style": style
        })
    
    # Content Intelligence - CRM & Safari
    async def create_crm_lead(
        self,
        username: str,
        platform: str = "instagram",
        source: str = "dm"
    ) -> Dict[str, Any]:
        """Create a lead in Local EverReach CRM."""
        return await self._call("ai", "/api/crm/leads", {
            "username": username,
            "platform": platform,
            "source": source
        })
    
    async def get_relationship_score(self, username: str) -> Dict[str, Any]:
        """Get relationship score for a lead."""
        return await self._call("ai", "/api/crm/relationship-score", {
            "username": username
        })
    
    async def safari_publish(
        self,
        platform: str,
        content: str,
        media_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish content via Safari Automation."""
        return await self._call("ai", "/api/safari/publish", {
            "platform": platform,
            "content": content,
            "media_path": media_path
        })
    
    async def safari_dm(
        self,
        recipient: str,
        message: str,
        platform: str = "instagram"
    ) -> Dict[str, Any]:
        """Send DM via Safari Automation."""
        return await self._call("ai", "/api/safari/dm", {
            "platform": platform,
            "recipient": recipient,
            "message": message
        })


# Singleton instance
_client: Optional[MicroservicesClient] = None


def get_microservices_client() -> MicroservicesClient:
    """Get the shared microservices client instance."""
    global _client
    if _client is None:
        _client = MicroservicesClient()
    return _client

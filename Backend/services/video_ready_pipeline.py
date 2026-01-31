"""
Video Ready Pipeline
====================
Handles the complete flow when a video is ready:
1. Receive alert (webhook, SSE, or polling)
2. AI analyze the video (transcribe + vision + generate caption)
3. Publish to YouTube and TikTok via Blotato

Usage:
    from services.video_ready_pipeline import VideoReadyPipeline
    
    pipeline = VideoReadyPipeline()
    
    # When video is ready (e.g., Sora generation complete)
    result = await pipeline.process_video_ready(
        video_path="/path/to/video.mp4",
        source="sora",
        publish_to=["youtube", "tiktok"]
    )
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from dataclasses import dataclass

from services.blotato_service import BlotatoService, BlotatoPlatform


@dataclass
class VideoReadyEvent:
    """Event when a video becomes ready for processing"""
    video_path: str
    source: str  # "sora", "upload", "import", "safari"
    metadata: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class AnalysisResult:
    """Result from AI analysis"""
    transcript: str
    summary: str
    suggested_caption: str
    hashtags: List[str]
    virality_score: float
    duration_seconds: float
    detected_topics: List[str]


class VideoReadyPipeline:
    """
    Complete pipeline for processing videos when they're ready.
    
    Flow:
    1. Video Ready Alert → 
    2. AI Analysis (transcribe + vision + caption) → 
    3. Publish to platforms (YouTube, TikTok, etc.)
    """
    
    # Default account IDs for publishing
    DEFAULT_ACCOUNTS = {
        "youtube": 228,      # UCnDBsELI2OlaEl5yxA77HNA - Isaiah Dupree
        "tiktok": 710,       # isaiah_dupree
        "instagram": 807,    # the_isaiah_dupree
        "threads": 173,      # the_isaiah_dupree_
    }
    
    def __init__(self):
        self.blotato = BlotatoService.get_instance()
        self._openai_client = None
        logger.info("VideoReadyPipeline initialized")
    
    @property
    def openai_client(self):
        """Lazy load OpenAI client"""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._openai_client
    
    async def process_video_ready(
        self,
        video_path: str,
        source: str = "unknown",
        publish_to: List[str] = None,
        custom_caption: str = None,
        auto_publish: bool = True,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - process a video that's ready.
        
        Args:
            video_path: Path to the video file
            source: Where the video came from (sora, upload, etc.)
            publish_to: List of platforms ["youtube", "tiktok", "instagram"]
            custom_caption: Override AI-generated caption
            auto_publish: Whether to automatically publish after analysis
            metadata: Additional metadata (prompt used, character, etc.)
            
        Returns:
            Dict with analysis results and publish status
        """
        logger.info(f"🎬 Processing video ready: {video_path}")
        logger.info(f"   Source: {source}")
        logger.info(f"   Publish to: {publish_to}")
        
        result = {
            "video_path": video_path,
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": None,
            "publish_results": [],
            "status": "processing"
        }
        
        # Validate video exists
        if not Path(video_path).exists():
            result["status"] = "error"
            result["error"] = f"Video file not found: {video_path}"
            return result
        
        # Step 1: AI Analysis
        try:
            logger.info("📊 Step 1/2: Running AI analysis...")
            analysis = await self.analyze_video(video_path, metadata)
            result["analysis"] = {
                "transcript": analysis.transcript,
                "summary": analysis.summary,
                "suggested_caption": analysis.suggested_caption,
                "hashtags": analysis.hashtags,
                "virality_score": analysis.virality_score,
                "duration_seconds": analysis.duration_seconds,
                "detected_topics": analysis.detected_topics
            }
            logger.info(f"   ✅ Analysis complete - virality score: {analysis.virality_score}")
        except Exception as e:
            logger.error(f"   ❌ Analysis failed: {e}")
            result["status"] = "analysis_failed"
            result["error"] = str(e)
            return result
        
        # Step 2: Publish to platforms
        if auto_publish and publish_to:
            logger.info(f"📤 Step 2/2: Publishing to {publish_to}...")
            
            caption = custom_caption or analysis.suggested_caption
            
            for platform in publish_to:
                try:
                    pub_result = await self.publish_to_platform(
                        video_path=video_path,
                        platform=platform,
                        caption=caption,
                        hashtags=analysis.hashtags
                    )
                    result["publish_results"].append({
                        "platform": platform,
                        "success": pub_result.get("success", False),
                        "post_id": pub_result.get("post_id"),
                        "url": pub_result.get("url"),
                        "error": pub_result.get("error")
                    })
                    logger.info(f"   ✅ Published to {platform}")
                except Exception as e:
                    logger.error(f"   ❌ Failed to publish to {platform}: {e}")
                    result["publish_results"].append({
                        "platform": platform,
                        "success": False,
                        "error": str(e)
                    })
        
        result["status"] = "completed"
        logger.info(f"✅ Video processing complete: {video_path}")
        
        return result
    
    async def analyze_video(
        self,
        video_path: str,
        metadata: Dict[str, Any] = None
    ) -> AnalysisResult:
        """
        AI analyze video - transcribe, summarize, generate caption.
        
        Uses OpenAI Whisper for transcription and GPT-4 for analysis.
        """
        metadata = metadata or {}
        
        # Get video duration
        duration = await self._get_video_duration(video_path)
        
        # Transcribe with Whisper
        transcript = await self._transcribe_video(video_path)
        
        # Generate analysis and caption with GPT-4
        analysis_prompt = f"""Analyze this video for social media publishing.

Video Source: {metadata.get('source', 'unknown')}
Original Prompt (if AI-generated): {metadata.get('prompt', 'N/A')}
Duration: {duration:.1f} seconds

Transcript:
{transcript if transcript else '[No speech detected]'}

Please provide:
1. A brief summary (1-2 sentences)
2. A viral-optimized caption for TikTok/YouTube Shorts (under 150 chars, engaging, with call-to-action)
3. 5 relevant hashtags
4. A virality score (0-100) based on content potential
5. Main topics/themes detected

Format your response as JSON:
{{
    "summary": "...",
    "caption": "...",
    "hashtags": ["...", "..."],
    "virality_score": 75,
    "topics": ["...", "..."]
}}"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": analysis_prompt}],
            response_format={"type": "json_object"}
        )
        
        import json
        analysis_data = json.loads(response.choices[0].message.content)
        
        return AnalysisResult(
            transcript=transcript,
            summary=analysis_data.get("summary", ""),
            suggested_caption=analysis_data.get("caption", ""),
            hashtags=analysis_data.get("hashtags", []),
            virality_score=analysis_data.get("virality_score", 50),
            duration_seconds=duration,
            detected_topics=analysis_data.get("topics", [])
        )
    
    async def _transcribe_video(self, video_path: str) -> str:
        """Transcribe video using OpenAI Whisper"""
        try:
            with open(video_path, "rb") as video_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=video_file,
                    response_format="text"
                )
            return response
        except Exception as e:
            logger.warning(f"Transcription failed: {e}")
            return ""
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds"""
        try:
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0
    
    async def publish_to_platform(
        self,
        video_path: str,
        platform: str,
        caption: str,
        hashtags: List[str] = None,
        account_id: int = None
    ) -> Dict[str, Any]:
        """
        Publish video to a platform via Blotato.
        
        Args:
            video_path: Path to video file
            platform: "youtube", "tiktok", "instagram", etc.
            caption: Caption text
            hashtags: List of hashtags to append
            account_id: Override default account
            
        Returns:
            Dict with success status, post_id, url
        """
        # Get account ID
        if account_id is None:
            account_id = self.DEFAULT_ACCOUNTS.get(platform.lower())
        
        if not account_id:
            return {"success": False, "error": f"No account configured for {platform}"}
        
        # Build full caption with hashtags
        full_caption = caption
        if hashtags:
            hashtag_str = " ".join(f"#{h.lstrip('#')}" for h in hashtags)
            full_caption = f"{caption}\n\n{hashtag_str}"
        
        # Upload video to Blotato and publish
        try:
            # First, upload the video to get a media_id
            media_id = await self._upload_to_blotato(video_path)
            
            # Then publish
            result = await self.blotato.publish_content(
                media_id=media_id,
                account_id=account_id,
                caption=full_caption
            )
            
            return {
                "success": result.get("success", False),
                "post_id": result.get("result", {}).get("post_id"),
                "url": result.get("result", {}).get("url"),
                "platform": platform,
                "account_id": account_id
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _upload_to_blotato(self, video_path: str) -> str:
        """Upload video to Blotato and return media_id"""
        import httpx
        
        api_key = os.getenv("BLOTATO_API_KEY")
        if not api_key:
            raise ValueError("BLOTATO_API_KEY not configured")
        
        async with httpx.AsyncClient() as client:
            with open(video_path, "rb") as f:
                files = {"file": (Path(video_path).name, f, "video/mp4")}
                response = await client.post(
                    "https://api.blotato.com/v2/media/upload",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files=files,
                    timeout=120  # Videos can take a while to upload
                )
                response.raise_for_status()
                data = response.json()
                return data.get("media_id") or data.get("id")


# === Webhook Handler for Video Ready Events ===

class VideoReadyWebhookHandler:
    """
    Handles incoming webhooks/events when videos are ready.
    
    Can be triggered by:
    - Safari Automation telemetry (WebSocket on 7071)
    - C2 API events (SSE on 9100)
    - Direct webhook calls
    - File system watcher
    """
    
    def __init__(self):
        self.pipeline = VideoReadyPipeline()
        self._handlers = {}
    
    async def handle_sora_video_ready(
        self,
        video_path: str,
        prompt: str = None,
        character: str = None
    ) -> Dict[str, Any]:
        """
        Handle Sora video generation complete event.
        
        Called when Safari Automation finishes generating a Sora video.
        """
        logger.info(f"🎬 Sora video ready: {video_path}")
        
        return await self.pipeline.process_video_ready(
            video_path=video_path,
            source="sora",
            publish_to=["youtube", "tiktok"],
            metadata={
                "prompt": prompt,
                "character": character,
                "generator": "sora.chatgpt.com"
            }
        )
    
    async def handle_watermark_removal_complete(
        self,
        video_path: str,
        original_path: str = None
    ) -> Dict[str, Any]:
        """
        Handle watermark removal complete event.
        
        Called when a video has been cleaned of watermarks.
        """
        logger.info(f"🎬 Clean video ready: {video_path}")
        
        return await self.pipeline.process_video_ready(
            video_path=video_path,
            source="watermark_removal",
            publish_to=["youtube", "tiktok"],
            metadata={
                "original_path": original_path,
                "cleaned": True
            }
        )
    
    async def handle_generic_video_ready(
        self,
        video_path: str,
        platforms: List[str] = None,
        caption: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle any video ready event.
        """
        return await self.pipeline.process_video_ready(
            video_path=video_path,
            source=metadata.get("source", "unknown") if metadata else "unknown",
            publish_to=platforms or ["youtube", "tiktok"],
            custom_caption=caption,
            metadata=metadata
        )


# === FastAPI Integration ===

def create_webhook_router():
    """Create FastAPI router for video ready webhooks"""
    from fastapi import APIRouter, HTTPException, BackgroundTasks
    from pydantic import BaseModel
    from typing import Optional
    
    router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
    handler = VideoReadyWebhookHandler()
    
    class VideoReadyPayload(BaseModel):
        video_path: str
        source: str = "unknown"
        platforms: List[str] = ["youtube", "tiktok"]
        caption: Optional[str] = None
        prompt: Optional[str] = None
        character: Optional[str] = None
        auto_publish: bool = True
    
    @router.post("/video-ready")
    async def video_ready_webhook(
        payload: VideoReadyPayload,
        background_tasks: BackgroundTasks
    ):
        """
        Webhook endpoint for video ready events.
        
        Called when a video is ready for processing.
        Processing happens in background.
        """
        # Process in background to return quickly
        background_tasks.add_task(
            handler.handle_generic_video_ready,
            video_path=payload.video_path,
            platforms=payload.platforms,
            caption=payload.caption,
            metadata={
                "source": payload.source,
                "prompt": payload.prompt,
                "character": payload.character
            }
        )
        
        return {
            "accepted": True,
            "message": "Video queued for processing",
            "video_path": payload.video_path
        }
    
    @router.post("/sora-ready")
    async def sora_ready_webhook(
        payload: VideoReadyPayload,
        background_tasks: BackgroundTasks
    ):
        """
        Webhook for Sora video generation complete.
        """
        background_tasks.add_task(
            handler.handle_sora_video_ready,
            video_path=payload.video_path,
            prompt=payload.prompt,
            character=payload.character
        )
        
        return {
            "accepted": True,
            "message": "Sora video queued for analysis and publishing"
        }
    
    return router

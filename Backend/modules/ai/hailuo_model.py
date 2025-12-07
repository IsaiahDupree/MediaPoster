"""
Hailuo/Minimax AI video generation implementation
High-quality human motion and cinematic videos
"""
from typing import Optional, List, Dict, Any
import time
import requests
from loguru import logger

from .video_model_interface import (
    VideoModelInterface,
    VideoGenerationRequest,
    VideoGenerationJob,
    VideoStatus
)


class HailuoVideoModel(VideoModelInterface):
    """Hailuo/Minimax implementation - high quality human motion"""
    
    SUPPORTED_RESOLUTIONS = [
        (1920, 1080),  # 1080p
        (1280, 720),   # 720p
        (720, 1280),   # Portrait
        (1024, 1024),  # Square
    ]
    MAX_DURATION = 10
    MIN_DURATION = 5
    
    def __init__(self, api_key: Optional[str] = None, model: str = "hailuo-02-pro"):
        """
        Initialize Hailuo/Minimax client
        
        Args:
            api_key: Minimax API key (uses env var if not provided)
            model: Model version (hailuo-02, hailuo-02-pro)
        """
        import os
        self.api_key = api_key or os.getenv("HAILUO_API_KEY") or os.getenv("MINIMAX_API_KEY")
        if not self.api_key:
            logger.warning("HAILUO_API_KEY/MINIMAX_API_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        self.model = model
        self.base_url = "https://api.minimaxi.chat/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_video(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create video generation job"""
        logger.info(f"Creating Hailuo video ({self.model}): {request.prompt[:50]}...")
        
        if self.mock_mode:
            return self._create_mock_job(request)
        
        # Validate duration
        duration = max(self.MIN_DURATION, min(request.duration_seconds, self.MAX_DURATION))
        
        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "duration": duration,
        }
        
        if request.input_image:
            payload["first_frame_image"] = request.input_image
        
        if request.seed:
            payload["seed"] = request.seed
        
        # Hailuo-specific features
        if request.additional_params:
            if "voice_id" in request.additional_params:
                payload["voice_id"] = request.additional_params["voice_id"]
            if "lip_sync" in request.additional_params:
                payload["lip_sync"] = request.additional_params["lip_sync"]
            if "camera_motion" in request.additional_params:
                payload["camera_control"] = request.additional_params["camera_motion"]
        
        try:
            response = requests.post(
                f"{self.base_url}/video/generation",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=data["task_id"],
                status=self._map_status(data.get("status", "pending")),
                progress=0,
                metadata={"provider": "hailuo", "model": self.model}
            )
        except Exception as e:
            logger.error(f"Hailuo API error: {e}")
            raise
    
    def get_status(self, job_id: str) -> VideoGenerationJob:
        """Get job status"""
        if self.mock_mode:
            return self._get_mock_status(job_id)
        
        try:
            response = requests.get(
                f"{self.base_url}/video/generation/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=job_id,
                status=self._map_status(data.get("status", "pending")),
                progress=data.get("progress", 0),
                video_url=data.get("video_url"),
                thumbnail_url=data.get("cover_image_url"),
                error_message=data.get("error_message"),
                metadata={"provider": "hailuo", "model": self.model}
            )
        except Exception as e:
            logger.error(f"Error getting Hailuo status: {e}")
            raise
    
    def download_video(self, job_id: str, output_path: str) -> str:
        """Download completed video"""
        job = self.get_status(job_id)
        
        if job.status != VideoStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not completed yet")
        
        if not job.video_url:
            raise ValueError(f"No video URL for job {job_id}")
        
        logger.info(f"Downloading Hailuo video from {job.video_url}")
        
        response = requests.get(job.video_url, stream=True, timeout=120)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.success(f"Video downloaded to {output_path}")
        return output_path
    
    def list_jobs(self, limit: int = 20) -> List[VideoGenerationJob]:
        """List recent jobs"""
        if self.mock_mode:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/video/generations",
                headers=self.headers,
                params={"limit": limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                VideoGenerationJob(
                    job_id=job["task_id"],
                    status=self._map_status(job.get("status", "pending")),
                    progress=job.get("progress", 0),
                    video_url=job.get("video_url"),
                    metadata={"provider": "hailuo"}
                )
                for job in data.get("data", [])
            ]
        except Exception as e:
            logger.error(f"Error listing Hailuo jobs: {e}")
            return []
    
    def delete_video(self, job_id: str) -> bool:
        """Delete video from storage"""
        if self.mock_mode:
            return True
        
        try:
            response = requests.delete(
                f"{self.base_url}/video/generation/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error deleting Hailuo video: {e}")
            return False
    
    def get_supported_resolutions(self) -> List[tuple]:
        """Get supported resolutions"""
        return self.SUPPORTED_RESOLUTIONS
    
    def get_max_duration(self) -> int:
        """Get max duration"""
        return self.MAX_DURATION
    
    def supports_image_input(self) -> bool:
        """Supports image-to-video"""
        return True
    
    def supports_remix(self) -> bool:
        """Supports remix/variations"""
        return False
    
    def supports_lip_sync(self) -> bool:
        """Special Hailuo feature: lip sync for voiceovers"""
        return True
    
    def _map_status(self, hailuo_status: str) -> VideoStatus:
        """Map Hailuo status to standard status"""
        status_map = {
            "pending": VideoStatus.QUEUED,
            "processing": VideoStatus.IN_PROGRESS,
            "running": VideoStatus.IN_PROGRESS,
            "completed": VideoStatus.COMPLETED,
            "success": VideoStatus.COMPLETED,
            "failed": VideoStatus.FAILED,
            "error": VideoStatus.FAILED,
        }
        return status_map.get(hailuo_status.lower(), VideoStatus.QUEUED)
    
    def _create_mock_job(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create mock job for testing"""
        import hashlib
        job_id = hashlib.md5(request.prompt.encode()).hexdigest()[:16]
        
        return VideoGenerationJob(
            job_id=f"hailuo_mock_{job_id}",
            status=VideoStatus.QUEUED,
            progress=0,
            metadata={"provider": "hailuo", "model": self.model, "mock": True}
        )
    
    def _get_mock_status(self, job_id: str) -> VideoGenerationJob:
        """Get mock status"""
        return VideoGenerationJob(
            job_id=job_id,
            status=VideoStatus.COMPLETED,
            progress=100,
            video_url=f"https://hailuo.example.com/videos/{job_id}.mp4",
            thumbnail_url=f"https://hailuo.example.com/thumbnails/{job_id}.jpg",
            metadata={"provider": "hailuo", "mock": True}
        )

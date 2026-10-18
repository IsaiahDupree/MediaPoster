"""
Kling AI video generation implementation
Supports up to 2 minute videos at 1080p
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


class KlingVideoModel(VideoModelInterface):
    """Kling 2.1 implementation - up to 2 minute videos"""
    
    SUPPORTED_RESOLUTIONS = [
        (1920, 1080),  # 1080p
        (1280, 720),   # 720p
        (720, 1280),   # Portrait 720p
        (1080, 1920),  # Portrait 1080p
    ]
    MAX_DURATION = 120  # 2 minutes
    MIN_DURATION = 5
    
    def __init__(self, api_key: Optional[str] = None, model: str = "kling-2.1"):
        """
        Initialize Kling client
        
        Args:
            api_key: Kling API key (uses env var if not provided)
            model: Model version (kling-2.1, kling-1.6)
        """
        import os
        self.api_key = api_key or os.getenv("KLING_API_KEY")
        if not self.api_key:
            logger.warning("KLING_API_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        self.model = model
        self.base_url = "https://api.klingai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_video(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create video generation job"""
        logger.info(f"Creating Kling video ({self.model}): {request.prompt[:50]}...")
        
        if self.mock_mode:
            return self._create_mock_job(request)
        
        # Validate and adjust resolution
        width, height = request.width, request.height
        if (width, height) not in self.SUPPORTED_RESOLUTIONS:
            logger.warning(f"Unsupported resolution {width}x{height}, using 1920x1080")
            width, height = 1920, 1080
        
        # Validate duration
        duration = max(self.MIN_DURATION, min(request.duration_seconds, self.MAX_DURATION))
        
        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "duration": duration,
            "resolution": f"{width}x{height}",
            "fps": 30,
        }
        
        if request.input_image:
            payload["image_url"] = request.input_image
            payload["mode"] = "image_to_video"
        else:
            payload["mode"] = "text_to_video"
        
        if request.seed:
            payload["seed"] = request.seed
        
        if request.additional_params:
            if "negative_prompt" in request.additional_params:
                payload["negative_prompt"] = request.additional_params["negative_prompt"]
            if "cfg_scale" in request.additional_params:
                payload["cfg_scale"] = request.additional_params["cfg_scale"]
        
        try:
            response = requests.post(
                f"{self.base_url}/videos/generations",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=data["task_id"],
                status=self._map_status(data["status"]),
                progress=data.get("progress", 0),
                metadata={"provider": "kling", "model": self.model}
            )
        except Exception as e:
            logger.error(f"Kling API error: {e}")
            raise
    
    def get_status(self, job_id: str) -> VideoGenerationJob:
        """Get job status"""
        if self.mock_mode:
            return self._get_mock_status(job_id)
        
        try:
            response = requests.get(
                f"{self.base_url}/videos/generations/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            video_url = None
            if data.get("videos") and len(data["videos"]) > 0:
                video_url = data["videos"][0].get("url")
            
            return VideoGenerationJob(
                job_id=data["task_id"],
                status=self._map_status(data["status"]),
                progress=data.get("progress", 0),
                video_url=video_url,
                thumbnail_url=data.get("thumbnail_url"),
                error_message=data.get("error_message"),
                metadata={"provider": "kling", "model": self.model}
            )
        except Exception as e:
            logger.error(f"Error getting Kling status: {e}")
            raise
    
    def download_video(self, job_id: str, output_path: str) -> str:
        """Download completed video"""
        job = self.get_status(job_id)
        
        if job.status != VideoStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not completed yet")
        
        if not job.video_url:
            raise ValueError(f"No video URL for job {job_id}")
        
        logger.info(f"Downloading Kling video from {job.video_url}")
        
        response = requests.get(job.video_url, stream=True, timeout=300)
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
                f"{self.base_url}/videos/generations",
                headers=self.headers,
                params={"limit": limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                VideoGenerationJob(
                    job_id=job["task_id"],
                    status=self._map_status(job["status"]),
                    progress=job.get("progress", 0),
                    video_url=job.get("videos", [{}])[0].get("url") if job.get("videos") else None,
                    metadata={"provider": "kling"}
                )
                for job in data.get("data", [])
            ]
        except Exception as e:
            logger.error(f"Error listing Kling jobs: {e}")
            return []
    
    def delete_video(self, job_id: str) -> bool:
        """Delete video from Kling storage"""
        if self.mock_mode:
            return True
        
        try:
            response = requests.delete(
                f"{self.base_url}/videos/generations/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error deleting Kling video: {e}")
            return False
    
    def get_supported_resolutions(self) -> List[tuple]:
        """Get supported resolutions"""
        return self.SUPPORTED_RESOLUTIONS
    
    def get_max_duration(self) -> int:
        """Get max duration - 2 minutes!"""
        return self.MAX_DURATION
    
    def supports_image_input(self) -> bool:
        """Supports image input"""
        return True
    
    def supports_remix(self) -> bool:
        """Supports remix/variations"""
        return True
    
    def _map_status(self, kling_status: str) -> VideoStatus:
        """Map Kling status to standard status"""
        status_map = {
            "pending": VideoStatus.QUEUED,
            "processing": VideoStatus.IN_PROGRESS,
            "running": VideoStatus.IN_PROGRESS,
            "completed": VideoStatus.COMPLETED,
            "succeeded": VideoStatus.COMPLETED,
            "failed": VideoStatus.FAILED,
            "error": VideoStatus.FAILED,
        }
        return status_map.get(kling_status.lower(), VideoStatus.QUEUED)
    
    def _create_mock_job(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create mock job for testing"""
        import hashlib
        job_id = hashlib.md5(request.prompt.encode()).hexdigest()[:16]
        
        return VideoGenerationJob(
            job_id=f"kling_mock_{job_id}",
            status=VideoStatus.QUEUED,
            progress=0,
            metadata={"provider": "kling", "model": self.model, "mock": True, "max_duration": self.MAX_DURATION}
        )
    
    def _get_mock_status(self, job_id: str) -> VideoGenerationJob:
        """Get mock status"""
        return VideoGenerationJob(
            job_id=job_id,
            status=VideoStatus.COMPLETED,
            progress=100,
            video_url=f"https://kling.example.com/videos/{job_id}.mp4",
            thumbnail_url=f"https://kling.example.com/thumbnails/{job_id}.jpg",
            metadata={"provider": "kling", "mock": True}
        )

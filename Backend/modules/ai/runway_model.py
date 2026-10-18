"""
Runway Gen-3 Alpha Turbo video generation implementation
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


class RunwayVideoModel(VideoModelInterface):
    """Runway Gen-3 Alpha Turbo implementation"""
    
    SUPPORTED_RESOLUTIONS = [
        (1280, 768),   # 16:10
        (768, 1280),   # 10:16 (portrait)
    ]
    MAX_DURATION = 10
    MIN_DURATION = 5
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Runway client
        
        Args:
            api_key: Runway API key (uses env var if not provided)
        """
        import os
        self.api_key = api_key or os.getenv("RUNWAY_API_KEY")
        if not self.api_key:
            logger.warning("RUNWAY_API_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        self.base_url = "https://api.runwayml.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_video(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create video generation job"""
        logger.info(f"Creating Runway video: {request.prompt[:50]}...")
        
        if self.mock_mode:
            return self._create_mock_job(request)
        
        # Validate resolution
        if (request.width, request.height) not in self.SUPPORTED_RESOLUTIONS:
            logger.warning(f"Unsupported resolution {request.width}x{request.height}, using default 1280x768")
            request.width = 1280
            request.height = 768
        
        # Validate duration
        duration = max(self.MIN_DURATION, min(request.duration_seconds, self.MAX_DURATION))
        
        payload = {
            "prompt": request.prompt,
            "duration": duration,
            "resolution": f"{request.width}x{request.height}",
        }
        
        if request.input_image:
            payload["image"] = request.input_image
        
        if request.seed:
            payload["seed"] = request.seed
        
        try:
            response = requests.post(
                f"{self.base_url}/generations",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=data["id"],
                status=self._map_status(data["status"]),
                progress=data.get("progress"),
                metadata={"provider": "runway", "model": "gen3-alpha-turbo"}
            )
        except Exception as e:
            logger.error(f"Runway API error: {e}")
            raise
    
    def get_status(self, job_id: str) -> VideoGenerationJob:
        """Get job status"""
        if self.mock_mode:
            return self._get_mock_status(job_id)
        
        try:
            response = requests.get(
                f"{self.base_url}/generations/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=data["id"],
                status=self._map_status(data["status"]),
                progress=data.get("progress"),
                video_url=data.get("output", {}).get("url"),
                thumbnail_url=data.get("thumbnail"),
                error_message=data.get("error"),
                metadata={"provider": "runway"}
            )
        except Exception as e:
            logger.error(f"Error getting Runway status: {e}")
            raise
    
    def download_video(self, job_id: str, output_path: str) -> str:
        """Download completed video"""
        job = self.get_status(job_id)
        
        if job.status != VideoStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not completed yet")
        
        if not job.video_url:
            raise ValueError(f"No video URL for job {job_id}")
        
        logger.info(f"Downloading Runway video from {job.video_url}")
        
        response = requests.get(job.video_url, stream=True)
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
                f"{self.base_url}/generations",
                headers=self.headers,
                params={"limit": limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                VideoGenerationJob(
                    job_id=job["id"],
                    status=self._map_status(job["status"]),
                    progress=job.get("progress"),
                    video_url=job.get("output", {}).get("url"),
                    metadata={"provider": "runway"}
                )
                for job in data.get("generations", [])
            ]
        except Exception as e:
            logger.error(f"Error listing Runway jobs: {e}")
            return []
    
    def delete_video(self, job_id: str) -> bool:
        """Delete video from Runway storage"""
        if self.mock_mode:
            return True
        
        try:
            response = requests.delete(
                f"{self.base_url}/generations/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error deleting Runway video: {e}")
            return False
    
    def get_supported_resolutions(self) -> List[tuple]:
        """Get supported resolutions"""
        return self.SUPPORTED_RESOLUTIONS
    
    def get_max_duration(self) -> int:
        """Get max duration"""
        return self.MAX_DURATION
    
    def supports_image_input(self) -> bool:
        """Supports image input"""
        return True
    
    def supports_remix(self) -> bool:
        """Supports remix/variations"""
        return False
    
    def _map_status(self, runway_status: str) -> VideoStatus:
        """Map Runway status to standard status"""
        status_map = {
            "pending": VideoStatus.QUEUED,
            "running": VideoStatus.IN_PROGRESS,
            "completed": VideoStatus.COMPLETED,
            "failed": VideoStatus.FAILED,
        }
        return status_map.get(runway_status.lower(), VideoStatus.QUEUED)
    
    def _create_mock_job(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create mock job for testing"""
        import hashlib
        job_id = hashlib.md5(request.prompt.encode()).hexdigest()[:16]
        
        return VideoGenerationJob(
            job_id=f"runway_mock_{job_id}",
            status=VideoStatus.QUEUED,
            progress=0,
            metadata={"provider": "runway", "model": "gen3-alpha-turbo", "mock": True}
        )
    
    def _get_mock_status(self, job_id: str) -> VideoGenerationJob:
        """Get mock status"""
        return VideoGenerationJob(
            job_id=job_id,
            status=VideoStatus.COMPLETED,
            progress=100,
            video_url=f"https://runway.example.com/videos/{job_id}.mp4",
            thumbnail_url=f"https://runway.example.com/thumbnails/{job_id}.jpg",
            metadata={"provider": "runway", "mock": True}
        )

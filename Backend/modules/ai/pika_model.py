"""
Pika 1.5 video generation implementation
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


class PikaVideoModel(VideoModelInterface):
    """Pika 1.5 implementation"""
    
    SUPPORTED_ASPECT_RATIOS = {
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "1:1": (1024, 1024),
        "4:3": (1024, 768),
        "3:4": (768, 1024),
    }
    MAX_DURATION = 10
    MIN_DURATION = 3
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Pika client
        
        Args:
            api_key: Pika API key (uses env var if not provided)
        """
        import os
        self.api_key = api_key or os.getenv("PIKA_API_KEY")
        if not self.api_key:
            logger.warning("PIKA_API_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        self.base_url = "https://api.pika.art/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_video(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create video generation job"""
        logger.info(f"Creating Pika video: {request.prompt[:50]}...")
        
        if self.mock_mode:
            return self._create_mock_job(request)
        
        # Find closest aspect ratio
        aspect_ratio = self._get_aspect_ratio(request.width, request.height)
        
        # Validate duration
        duration = max(self.MIN_DURATION, min(request.duration_seconds, self.MAX_DURATION))
        
        payload = {
            "prompt": request.prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "motion": 3,  # Default motion level (1-5)
        }
        
        if request.input_image:
            payload["image_url"] = request.input_image
        
        if request.seed:
            payload["seed"] = request.seed
        
        # Add camera controls from additional params
        if request.additional_params:
            if "camera_motion" in request.additional_params:
                payload["camera"] = request.additional_params["camera_motion"]
            if "negative_prompt" in request.additional_params:
                payload["negative_prompt"] = request.additional_params["negative_prompt"]
        
        try:
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=data["job_id"],
                status=self._map_status(data["status"]),
                progress=data.get("progress", 0),
                metadata={"provider": "pika", "model": "pika-1.5"}
            )
        except Exception as e:
            logger.error(f"Pika API error: {e}")
            raise
    
    def get_status(self, job_id: str) -> VideoGenerationJob:
        """Get job status"""
        if self.mock_mode:
            return self._get_mock_status(job_id)
        
        try:
            response = requests.get(
                f"{self.base_url}/jobs/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=data["job_id"],
                status=self._map_status(data["status"]),
                progress=data.get("progress", 0),
                video_url=data.get("video_url"),
                thumbnail_url=data.get("thumbnail_url"),
                error_message=data.get("error"),
                metadata={"provider": "pika"}
            )
        except Exception as e:
            logger.error(f"Error getting Pika status: {e}")
            raise
    
    def download_video(self, job_id: str, output_path: str) -> str:
        """Download completed video"""
        job = self.get_status(job_id)
        
        if job.status != VideoStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not completed yet")
        
        if not job.video_url:
            raise ValueError(f"No video URL for job {job_id}")
        
        logger.info(f"Downloading Pika video from {job.video_url}")
        
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
                f"{self.base_url}/jobs",
                headers=self.headers,
                params={"limit": limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                VideoGenerationJob(
                    job_id=job["job_id"],
                    status=self._map_status(job["status"]),
                    progress=job.get("progress", 0),
                    video_url=job.get("video_url"),
                    metadata={"provider": "pika"}
                )
                for job in data.get("jobs", [])
            ]
        except Exception as e:
            logger.error(f"Error listing Pika jobs: {e}")
            return []
    
    def delete_video(self, job_id: str) -> bool:
        """Delete video from Pika storage"""
        if self.mock_mode:
            return True
        
        try:
            response = requests.delete(
                f"{self.base_url}/jobs/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error deleting Pika video: {e}")
            return False
    
    def get_supported_resolutions(self) -> List[tuple]:
        """Get supported resolutions"""
        return list(self.SUPPORTED_ASPECT_RATIOS.values())
    
    def get_max_duration(self) -> int:
        """Get max duration"""
        return self.MAX_DURATION
    
    def supports_image_input(self) -> bool:
        """Supports image input"""
        return True
    
    def supports_remix(self) -> bool:
        """Supports remix/variations"""
        return True
    
    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """Get closest supported aspect ratio"""
        target_ratio = width / height
        
        closest = "16:9"
        min_diff = float('inf')
        
        for ratio_name, (w, h) in self.SUPPORTED_ASPECT_RATIOS.items():
            ratio = w / h
            diff = abs(ratio - target_ratio)
            if diff < min_diff:
                min_diff = diff
                closest = ratio_name
        
        return closest
    
    def _map_status(self, pika_status: str) -> VideoStatus:
        """Map Pika status to standard status"""
        status_map = {
            "queued": VideoStatus.QUEUED,
            "processing": VideoStatus.IN_PROGRESS,
            "completed": VideoStatus.COMPLETED,
            "failed": VideoStatus.FAILED,
        }
        return status_map.get(pika_status.lower(), VideoStatus.QUEUED)
    
    def _create_mock_job(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create mock job for testing"""
        import hashlib
        job_id = hashlib.md5(request.prompt.encode()).hexdigest()[:16]
        
        return VideoGenerationJob(
            job_id=f"pika_mock_{job_id}",
            status=VideoStatus.QUEUED,
            progress=0,
            metadata={"provider": "pika", "model": "pika-1.5", "mock": True}
        )
    
    def _get_mock_status(self, job_id: str) -> VideoGenerationJob:
        """Get mock status"""
        return VideoGenerationJob(
            job_id=job_id,
            status=VideoStatus.COMPLETED,
            progress=100,
            video_url=f"https://pika.example.com/videos/{job_id}.mp4",
            thumbnail_url=f"https://pika.example.com/thumbnails/{job_id}.jpg",
            metadata={"provider": "pika", "mock": True}
        )

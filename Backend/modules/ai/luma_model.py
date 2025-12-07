"""
Luma Dream Machine video generation implementation
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


class LumaVideoModel(VideoModelInterface):
    """Luma Dream Machine implementation"""
    
    SUPPORTED_RESOLUTIONS = [
        (1280, 720),   # 720p standard
    ]
    MAX_DURATION = 5
    MIN_DURATION = 5  # Luma only supports 5s videos
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Luma client
        
        Args:
            api_key: Luma API key (uses env var if not provided)
        """
        import os
        self.api_key = api_key or os.getenv("LUMA_API_KEY")
        if not self.api_key:
            logger.warning("LUMA_API_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        self.base_url = "https://api.lumalabs.ai/dream-machine/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_video(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create video generation job"""
        logger.info(f"Creating Luma video: {request.prompt[:50]}...")
        
        if self.mock_mode:
            return self._create_mock_job(request)
        
        payload = {
            "prompt": request.prompt,
            "keyframes": {
                "frame0": {
                    "type": "generation"
                }
            }
        }
        
        # If image input provided, use it as first keyframe
        if request.input_image:
            payload["keyframes"]["frame0"] = {
                "type": "image",
                "url": request.input_image
            }
        
        # Add end keyframe if specified in additional params
        if request.additional_params and "end_image" in request.additional_params:
            payload["keyframes"]["frame1"] = {
                "type": "image",
                "url": request.additional_params["end_image"]
            }
        
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
                status=self._map_status(data["state"]),
                progress=self._calculate_progress(data["state"]),
                metadata={"provider": "luma", "model": "dream-machine"}
            )
        except Exception as e:
            logger.error(f"Luma API error: {e}")
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
                status=self._map_status(data["state"]),
                progress=self._calculate_progress(data["state"]),
                video_url=data.get("assets", {}).get("video"),
                thumbnail_url=data.get("assets", {}).get("thumbnail"),
                error_message=data.get("failure_reason"),
                metadata={"provider": "luma"}
            )
        except Exception as e:
            logger.error(f"Error getting Luma status: {e}")
            raise
    
    def download_video(self, job_id: str, output_path: str) -> str:
        """Download completed video"""
        job = self.get_status(job_id)
        
        if job.status != VideoStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not completed yet")
        
        if not job.video_url:
            raise ValueError(f"No video URL for job {job_id}")
        
        logger.info(f"Downloading Luma video from {job.video_url}")
        
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
                    job_id=gen["id"],
                    status=self._map_status(gen["state"]),
                    progress=self._calculate_progress(gen["state"]),
                    video_url=gen.get("assets", {}).get("video"),
                    metadata={"provider": "luma"}
                )
                for gen in data.get("generations", [])
            ]
        except Exception as e:
            logger.error(f"Error listing Luma jobs: {e}")
            return []
    
    def delete_video(self, job_id: str) -> bool:
        """Delete video from Luma storage"""
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
            logger.error(f"Error deleting Luma video: {e}")
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
    
    def _calculate_progress(self, state: str) -> int:
        """Calculate progress percentage from state"""
        progress_map = {
            "queued": 0,
            "dreaming": 50,
            "completed": 100,
            "failed": 0,
        }
        return progress_map.get(state.lower(), 0)
    
    def _map_status(self, luma_state: str) -> VideoStatus:
        """Map Luma state to standard status"""
        status_map = {
            "queued": VideoStatus.QUEUED,
            "dreaming": VideoStatus.IN_PROGRESS,
            "completed": VideoStatus.COMPLETED,
            "failed": VideoStatus.FAILED,
        }
        return status_map.get(luma_state.lower(), VideoStatus.QUEUED)
    
    def _create_mock_job(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create mock job for testing"""
        import hashlib
        job_id = hashlib.md5(request.prompt.encode()).hexdigest()[:16]
        
        return VideoGenerationJob(
            job_id=f"luma_mock_{job_id}",
            status=VideoStatus.QUEUED,
            progress=0,
            metadata={"provider": "luma", "model": "dream-machine", "mock": True}
        )
    
    def _get_mock_status(self, job_id: str) -> VideoGenerationJob:
        """Get mock status"""
        return VideoGenerationJob(
            job_id=job_id,
            status=VideoStatus.COMPLETED,
            progress=100,
            video_url=f"https://luma.example.com/videos/{job_id}.mp4",
            thumbnail_url=f"https://luma.example.com/thumbnails/{job_id}.jpg",
            metadata={"provider": "luma", "mock": True}
        )

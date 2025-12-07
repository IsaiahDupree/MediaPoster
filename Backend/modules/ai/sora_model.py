"""
OpenAI Sora video generation implementation
"""
from typing import Optional, List
import time
from loguru import logger
from openai import OpenAI

from .video_model_interface import (
    VideoModelInterface,
    VideoGenerationRequest,
    VideoGenerationJob,
    VideoStatus
)


class SoraVideoModel(VideoModelInterface):
    """OpenAI Sora video generation implementation"""
    
    SUPPORTED_RESOLUTIONS = [
        (1280, 720),   # 720p
        (1920, 1080),  # 1080p
    ]
    
    MAX_DURATION = 20  # seconds
    MIN_DURATION = 2
    
    def __init__(self, api_key: Optional[str] = None, model: str = "sora-2"):
        """
        Initialize Sora client
        
        Args:
            api_key: OpenAI API key (uses env var if not provided)
            model: "sora-2" (fast) or "sora-2-pro" (high quality)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Sora video model initialized: {model}")
    
    def create_video(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """Create video generation job"""
        logger.info(f"Creating Sora video: {request.prompt[:50]}...")
        
        # Validate resolution
        if (request.width, request.height) not in self.SUPPORTED_RESOLUTIONS:
            logger.warning(f"Unsupported resolution {request.width}x{request.height}, using 1280x720")
            request.width, request.height = 1280, 720
        
        # Validate duration
        if request.duration_seconds > self.MAX_DURATION:
            logger.warning(f"Duration {request.duration_seconds}s exceeds max {self.MAX_DURATION}s")
            request.duration_seconds = self.MAX_DURATION
        elif request.duration_seconds < self.MIN_DURATION:
            request.duration_seconds = self.MIN_DURATION
        
        # Prepare parameters
        params = {
            'model': request.model or self.model,
            'prompt': request.prompt,
            'size': f"{request.width}x{request.height}",
            'seconds': str(request.duration_seconds)
        }
        
        # Add optional image reference
        if request.input_image:
            # TODO: Handle image file upload
            logger.warning("Image input not yet implemented")
        
        # Create job
        try:
            video = self.client.videos.create(**params)
            
            logger.success(f"Sora job created: {video.id}")
            
            return VideoGenerationJob(
                job_id=video.id,
                status=self._map_status(video.status),
                progress=getattr(video, 'progress', 0),
                metadata={
                    'model': video.model,
                    'size': video.size,
                    'seconds': video.seconds,
                    'created_at': video.created_at
                }
            )
        except Exception as e:
            logger.error(f"Sora job creation failed: {e}")
            return VideoGenerationJob(
                job_id="",
                status=VideoStatus.FAILED,
                error_message=str(e)
            )
    
    def get_status(self, job_id: str) -> VideoGenerationJob:
        """Get job status"""
        try:
            video = self.client.videos.retrieve(job_id)
            
            # Extract URL if completed
            video_url = None
            if video.status == "completed":
                # URL will be available via download_content
                video_url = f"sora://{job_id}"  # Placeholder, actual download via API
            
            return VideoGenerationJob(
                job_id=video.id,
                status=self._map_status(video.status),
                progress=getattr(video, 'progress', None),
                video_url=video_url,
                metadata={
                    'model': video.model,
                    'created_at': video.created_at
                }
            )
        except Exception as e:
            logger.error(f"Failed to get status for {job_id}: {e}")
            return VideoGenerationJob(
                job_id=job_id,
                status=VideoStatus.FAILED,
                error_message=str(e)
            )
    
    def download_video(self, job_id: str, output_path: str) -> str:
        """Download completed video"""
        logger.info(f"Downloading Sora video {job_id} to {output_path}")
        
        try:
            content = self.client.videos.download_content(job_id, variant="video")
            content.write_to_file(output_path)
            
            logger.success(f"Downloaded to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    def create_and_wait(
        self, 
        request: VideoGenerationRequest,
        poll_interval: int = 10,
        max_wait: int = 600
    ) -> VideoGenerationJob:
        """
        Create video and wait for completion
        
        Args:
            request: Video generation request
            poll_interval: Seconds between status checks
            max_wait: Maximum wait time in seconds
            
        Returns:
            Completed job
        """
        job = self.create_video(request)
        
        if job.status == VideoStatus.FAILED:
            return job
        
        logger.info(f"Waiting for job {job.job_id} to complete...")
        
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait:
            job = self.get_status(job.job_id)
            
            if job.status == VideoStatus.COMPLETED:
                logger.success(f"Job completed in {int(time.time() - start_time)}s")
                return job
            elif job.status == VideoStatus.FAILED:
                logger.error(f"Job failed: {job.error_message}")
                return job
            
            if job.progress is not None:
                logger.info(f"Progress: {job.progress}%")
            
            time.sleep(poll_interval)
        
        logger.warning(f"Job timed out after {max_wait}s")
        job.error_message = f"Timeout after {max_wait}s"
        return job
    
    def list_jobs(self, limit: int = 20) -> List[VideoGenerationJob]:
        """List recent jobs"""
        try:
            videos = self.client.videos.list(limit=limit)
            
            jobs = []
            for video in videos.data:
                jobs.append(VideoGenerationJob(
                    job_id=video.id,
                    status=self._map_status(video.status),
                    progress=getattr(video, 'progress', None),
                    metadata={'created_at': video.created_at}
                ))
            
            return jobs
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
    
    def delete_video(self, job_id: str) -> bool:
        """Delete video from Sora storage"""
        try:
            self.client.videos.delete(job_id)
            logger.info(f"Deleted video {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {job_id}: {e}")
            return False
    
    def get_supported_resolutions(self) -> List[tuple]:
        """Get supported resolutions"""
        return self.SUPPORTED_RESOLUTIONS.copy()
    
    def get_max_duration(self) -> int:
        """Get max duration"""
        return self.MAX_DURATION
    
    def supports_image_input(self) -> bool:
        """Supports image input"""
        return True
    
    def supports_remix(self) -> bool:
        """Supports remix/variations"""
        return True
    
    def remix_video(self, job_id: str, prompt: str) -> VideoGenerationJob:
        """
        Create a remix of an existing video
        
        Args:
            job_id: Original video job ID
            prompt: Modification prompt
            
        Returns:
            New job for remixed video
        """
        logger.info(f"Remixing video {job_id}: {prompt[:50]}...")
        
        try:
            # Note: Using the REST API directly for remix
            # The Python SDK might not have this yet
            import requests
            
            response = requests.post(
                f"https://api.openai.com/v1/videos/{job_id}/remix",
                headers={
                    "Authorization": f"Bearer {self.client.api_key}",
                    "Content-Type": "application/json"
                },
                json={"prompt": prompt}
            )
            
            response.raise_for_status()
            data = response.json()
            
            return VideoGenerationJob(
                job_id=data['id'],
                status=self._map_status(data['status']),
                metadata=data
            )
        except Exception as e:
            logger.error(f"Remix failed: {e}")
            return VideoGenerationJob(
                job_id="",
                status=VideoStatus.FAILED,
                error_message=str(e)
            )
    
    def _map_status(self, sora_status: str) -> VideoStatus:
        """Map Sora status to standard status"""
        status_map = {
            'queued': VideoStatus.QUEUED,
            'in_progress': VideoStatus.IN_PROGRESS,
            'completed': VideoStatus.COMPLETED,
            'failed': VideoStatus.FAILED
        }
        return status_map.get(sora_status, VideoStatus.IN_PROGRESS)


# Example usage
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize Sora
    sora = SoraVideoModel(model="sora-2")
    
    # Create video request
    request = VideoGenerationRequest(
        prompt="A serene lake at sunset with mountains in the background",
        model="sora-2",
        width=1280,
        height=720,
        duration_seconds=8
    )
    
    # Generate video
    job = sora.create_and_wait(request, max_wait=300)
    
    if job.status == VideoStatus.COMPLETED:
        # Download
        sora.download_video(job.job_id, "output.mp4")
        logger.success("Video generated successfully!")
    else:
        logger.error(f"Generation failed: {job.error_message}")

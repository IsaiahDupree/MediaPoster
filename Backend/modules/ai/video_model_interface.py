"""
Base interface for video generation models
Allows swapping between Sora, RunwayML, and other providers
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class VideoStatus(Enum):
    """Standardized status across all providers"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VideoGenerationRequest:
    """Standardized video generation request"""
    prompt: str
    model: str
    width: int = 1280
    height: int = 720
    duration_seconds: int = 8
    input_image: Optional[str] = None  # Path or URL
    seed: Optional[int] = None
    additional_params: Optional[Dict[str, Any]] = None


@dataclass
class VideoGenerationJob:
    """Standardized job object"""
    job_id: str
    status: VideoStatus
    progress: Optional[int] = None  # 0-100
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VideoModelInterface(ABC):
    """
    Base interface that all video generation models must implement
    Allows easy swapping between Sora, RunwayML, Pika, etc.
    """
    
    @abstractmethod
    def create_video(self, request: VideoGenerationRequest) -> VideoGenerationJob:
        """
        Start a video generation job
        
        Args:
            request: Standardized video generation request
            
        Returns:
            VideoGenerationJob with job_id and initial status
        """
        pass
    
    @abstractmethod
    def get_status(self, job_id: str) -> VideoGenerationJob:
        """
        Check job status
        
        Args:
            job_id: Job identifier
            
        Returns:
            Current job status
        """
        pass
    
    @abstractmethod
    def download_video(self, job_id: str, output_path: str) -> str:
        """
        Download completed video
        
        Args:
            job_id: Job identifier
            output_path: Local file path to save video
            
        Returns:
            Path to downloaded file
        """
        pass
    
    @abstractmethod
    def list_jobs(self, limit: int = 20) -> List[VideoGenerationJob]:
        """
        List recent jobs
        
        Args:
            limit: Max number of jobs to return
            
        Returns:
            List of jobs
        """
        pass
    
    @abstractmethod
    def delete_video(self, job_id: str) -> bool:
        """
        Delete a video from provider storage
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_supported_resolutions(self) -> List[tuple]:
        """
        Get list of supported (width, height) tuples
        
        Returns:
            List of supported resolutions
        """
        pass
    
    @abstractmethod
    def get_max_duration(self) -> int:
        """
        Get maximum video duration in seconds
        
        Returns:
            Max duration
        """
        pass
    
    @abstractmethod
    def supports_image_input(self) -> bool:
        """Check if model supports image input"""
        pass
    
    @abstractmethod
    def supports_remix(self) -> bool:
        """Check if model supports remixing/variations"""
        pass

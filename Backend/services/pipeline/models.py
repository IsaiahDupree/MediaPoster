"""
Pipeline Models
===============
Data models for media factory pipeline orchestration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any, List
from uuid import UUID, uuid4


class PipelineStage(str, Enum):
    """Pipeline stages."""
    BRIEF = "brief"  # Content brief generation
    SCRIPT = "script"  # Script + shot plan generation
    TTS = "tts"  # Text-to-speech generation
    MUSIC = "music"  # Music bed generation
    VISUALS = "visuals"  # Visual assets (matting, b-roll, memes)
    REMOTION = "remotion"  # Video composition and rendering
    PUBLISH = "publish"  # Multi-platform publishing


class PipelineStatus(str, Enum):
    """Pipeline status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StageStatus:
    """Status of a pipeline stage."""
    stage: PipelineStage
    status: str  # "pending", "running", "completed", "failed", "skipped"
    progress: float = 0.0  # 0.0-1.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None  # Stage output (e.g., script.json path, audio_path, etc.)


@dataclass
class PipelineRequest:
    """Pipeline execution request."""
    brief_id: Optional[str] = None  # Use existing brief
    brief_data: Optional[Dict[str, Any]] = None  # Or provide brief data directly
    pipeline_id: Optional[str] = None
    correlation_id: Optional[str] = None
    stages: Optional[List[PipelineStage]] = None  # Which stages to run (default: all)
    skip_stages: Optional[List[PipelineStage]] = None  # Which stages to skip
    
    def __post_init__(self):
        """Generate IDs if not provided."""
        if self.pipeline_id is None:
            self.pipeline_id = str(uuid4())
        if self.correlation_id is None:
            self.correlation_id = str(uuid4())
        if self.stages is None:
            self.stages = [
                PipelineStage.BRIEF,
                PipelineStage.SCRIPT,
                PipelineStage.TTS,
                PipelineStage.REMOTION,
                PipelineStage.PUBLISH
            ]


@dataclass
class PipelineStatus:
    """Pipeline execution status."""
    pipeline_id: str
    status: PipelineStatus
    stages: Dict[PipelineStage, StageStatus] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    final_output: Optional[Dict[str, Any]] = None  # Final video path, URLs, etc.
    
    def get_progress(self) -> float:
        """Get overall pipeline progress (0.0-1.0)."""
        if not self.stages:
            return 0.0
        
        total_progress = sum(stage.progress for stage in self.stages.values())
        return total_progress / len(self.stages)
    
    def get_current_stage(self) -> Optional[PipelineStage]:
        """Get the currently running stage."""
        for stage, status in self.stages.items():
            if status.status == "running":
                return stage
        return None


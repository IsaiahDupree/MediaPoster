"""
Video Orchestrator Service
==========================
Sora-first video generation with Director/SceneCrafter/Assessor workflow.

Supports long-form video creation (up to 5 minutes) by:
1. Breaking scripts into manageable clips
2. Generating via Sora API (with fallback providers)
3. Assessing quality and retrying failures
4. Assembling final timeline

Usage:
    from services.video_orchestrator import VideoOrchestrator
    
    orchestrator = VideoOrchestrator()
    plan = await orchestrator.create_clip_plan(script, brief)
    await orchestrator.execute_plan(plan.id)
"""

from .models import (
    # Enums
    ProviderName,
    ClipRunStatus,
    AssessmentVerdict,
    OrchestratorRole,
    ClipState,
    PlanStatus,
    RenderStatus,
    BibleKind,
    
    # Core Models
    VideoProject,
    VideoBible,
    ContentBrief,
    VideoScript,
    ClipPlan,
    Scene,
    ClipPlanClip,
    ClipRun,
    VideoAsset,
    Assessment,
    RepairAttempt,
    FinalRender,
    
    # Schemas
    NarrationConfig,
    VisualIntent,
    ProviderHints,
    AcceptanceCheck,
    AcceptanceCriteria,
    PacingConstraints,
    RetryPolicy,
    PlanConstraints,
    RepairInstruction,
)

from .schemas import (
    # Request/Response schemas
    CreateProjectRequest,
    CreateBriefRequest,
    CreateClipPlanRequest,
    ClipPlanResponse,
    ClipRunResponse,
    AssessmentResponse,
    RenderResponse,
)

__all__ = [
    # Enums
    "ProviderName",
    "ClipRunStatus",
    "AssessmentVerdict",
    "OrchestratorRole",
    "ClipState",
    "PlanStatus",
    "RenderStatus",
    "BibleKind",
    
    # Core Models
    "VideoProject",
    "VideoBible",
    "ContentBrief",
    "VideoScript",
    "ClipPlan",
    "Scene",
    "ClipPlanClip",
    "ClipRun",
    "VideoAsset",
    "Assessment",
    "RepairAttempt",
    "FinalRender",
    
    # Config Models
    "NarrationConfig",
    "VisualIntent",
    "ProviderHints",
    "AcceptanceCheck",
    "AcceptanceCriteria",
    "PacingConstraints",
    "RetryPolicy",
    "PlanConstraints",
    "RepairInstruction",
    
    # Schemas
    "CreateProjectRequest",
    "CreateBriefRequest",
    "CreateClipPlanRequest",
    "ClipPlanResponse",
    "ClipRunResponse",
    "AssessmentResponse",
    "RenderResponse",
]

"""
Video Generation Pipeline API Endpoints

REST API for Sora video generation pipeline:
- Preview pipeline estimates
- Execute full pipeline
- Beat extraction
- Audio mixing
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger

from services.video_generation import (
    TrendItemV1,
    ContentBriefV1,
    PipelineConfig,
    run_full_pipeline,
    preview_pipeline,
    make_auto_shot_plan,
    estimate_auto_plan_cost,
    select_format,
    get_available_formats,
    make_story_ir,
)
from services.sfx_library import (
    extract_beats_from_script,
    load_manifest,
    audio_events_to_cue_sheet,
    mix_audio_bus_sync,
)


router = APIRouter(prefix="/api/video-pipeline", tags=["video-pipeline"])


# Request/Response Models

class TrendInput(BaseModel):
    """Trend data input."""
    hook: str = Field(description="Hook text from trend")
    angle: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None


class BriefInput(BaseModel):
    """Content brief input."""
    topic: str
    target_audience: str = Field(alias="targetAudience")
    tone: str = "engaging"
    platform: str = "tiktok"
    duration_hint_s: int = Field(default=30, alias="durationHintS")
    
    class Config:
        populate_by_name = True


class PipelinePreviewRequest(BaseModel):
    """Request for pipeline preview."""
    trend: TrendInput
    brief: BriefInput
    format_pack_id: Optional[str] = Field(None, alias="formatPackId")
    
    class Config:
        populate_by_name = True


class PipelinePreviewResponse(BaseModel):
    """Response for pipeline preview."""
    format: dict
    story_ir: dict = Field(alias="storyIR")
    shot_plan: dict = Field(alias="shotPlan")
    estimates: dict
    
    class Config:
        populate_by_name = True


class PipelineExecuteRequest(BaseModel):
    """Request for pipeline execution."""
    trend: TrendInput
    brief: BriefInput
    format_pack_id: Optional[str] = Field(None, alias="formatPackId")
    dry_run: bool = Field(default=True, alias="dryRun")
    skip_sora: bool = Field(default=False, alias="skipSora")
    reference_file_ids: Optional[List[str]] = Field(None, alias="referenceFileIds")
    
    class Config:
        populate_by_name = True


class PipelineExecuteResponse(BaseModel):
    """Response for pipeline execution."""
    status: str
    job_id: Optional[str] = Field(None, alias="jobId")
    artifacts_dir: Optional[str] = Field(None, alias="artifactsDir")
    cost_estimate: Optional[dict] = Field(None, alias="costEstimate")
    error: Optional[str] = None
    
    class Config:
        populate_by_name = True


class BeatExtractRequest(BaseModel):
    """Request for beat extraction."""
    script: str
    fps: int = 30
    wpm: int = 165
    use_markers: bool = Field(default=False, alias="useMarkers")
    
    class Config:
        populate_by_name = True


class BeatExtractResponse(BaseModel):
    """Response for beat extraction."""
    beats: List[dict]
    estimated_total_frames: int = Field(alias="estimatedTotalFrames")
    fps: int
    wpm: int
    
    class Config:
        populate_by_name = True


class AudioMixRequest(BaseModel):
    """Request for audio mixing."""
    base_audio_path: str = Field(alias="baseAudioPath")
    sfx_events: List[dict] = Field(alias="sfxEvents")
    fps: int = 30
    manifest_path: Optional[str] = Field(None, alias="manifestPath")
    sfx_root_dir: Optional[str] = Field(None, alias="sfxRootDir")
    output_path: str = Field(alias="outputPath")
    
    class Config:
        populate_by_name = True


# Endpoints

@router.get("/formats")
async def list_formats():
    """List available format packs."""
    formats = get_available_formats()
    return {
        "formats": [
            {
                "id": f.id,
                "label": f.label,
                "soraBeatTypes": [bt.value for bt in f.render_strategy.sora_beat_types],
                "nativeBeatTypes": [bt.value for bt in f.render_strategy.native_beat_types],
            }
            for f in formats
        ]
    }


@router.post("/preview", response_model=PipelinePreviewResponse)
async def preview_video_pipeline(request: PipelinePreviewRequest):
    """
    Preview pipeline without execution.
    
    Returns estimates and plan for the video generation.
    """
    try:
        # Convert to internal types
        trend = TrendItemV1(
            hook=request.trend.hook,
            angle=request.trend.angle,
            tags=request.trend.tags,
            source=request.trend.source or "api",
        )
        
        brief = ContentBriefV1(
            topic=request.brief.topic,
            target_audience=request.brief.target_audience,
            tone=request.brief.tone,
            platform=request.brief.platform,
            duration_hint_s=request.brief.duration_hint_s,
        )
        
        # Run preview
        result = await preview_pipeline(
            trend=trend,
            brief=brief,
            format_pack_id=request.format_pack_id,
        )
        
        return PipelinePreviewResponse(
            format=result["format"],
            story_ir=result["storyIR"],
            shot_plan=result["shotPlan"],
            estimates=result["estimates"],
        )
    
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=PipelineExecuteResponse)
async def execute_video_pipeline(
    request: PipelineExecuteRequest,
    background_tasks: BackgroundTasks,
):
    """
    Execute the video generation pipeline.
    
    For dry_run=True, returns estimates without generating.
    For dry_run=False, runs full Sora generation.
    """
    try:
        # Convert to internal types
        trend = TrendItemV1(
            hook=request.trend.hook,
            angle=request.trend.angle,
            tags=request.trend.tags,
            source=request.trend.source or "api",
        )
        
        brief = ContentBriefV1(
            topic=request.brief.topic,
            target_audience=request.brief.target_audience,
            tone=request.brief.tone,
            platform=request.brief.platform,
            duration_hint_s=request.brief.duration_hint_s,
        )
        
        # Create config
        config = PipelineConfig(
            dry_run=request.dry_run,
            skip_sora=request.skip_sora,
        )
        
        # Run pipeline
        result = await run_full_pipeline(
            trend=trend,
            brief=brief,
            config=config,
            format_pack_id=request.format_pack_id,
            reference_file_ids=request.reference_file_ids,
        )
        
        return PipelineExecuteResponse(
            status=result.status,
            artifacts_dir=result.artifacts_dir,
            cost_estimate=result.cost_estimate,
            error=result.error,
        )
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/beats/extract", response_model=BeatExtractResponse)
async def extract_beats(request: BeatExtractRequest):
    """
    Extract narrative beats from a script.
    
    Returns beats with frame timing based on WPM.
    """
    try:
        if request.use_markers:
            from services.sfx_library import extract_beats_with_markers
            result = extract_beats_with_markers(
                script=request.script,
                fps=request.fps,
                wpm=request.wpm,
            )
        else:
            result = extract_beats_from_script(
                script=request.script,
                fps=request.fps,
                wpm=request.wpm,
            )
        
        return BeatExtractResponse(
            beats=[b.model_dump(by_alias=True) for b in result.beats],
            estimated_total_frames=result.estimated_total_frames,
            fps=result.fps,
            wpm=result.wpm,
        )
    
    except Exception as e:
        logger.error(f"Beat extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shot-plan")
async def generate_shot_plan(request: PipelinePreviewRequest):
    """
    Generate an auto shot plan from trend + brief.
    
    Returns detailed shot plan with per-beat shot types.
    """
    try:
        trend = TrendItemV1(
            hook=request.trend.hook,
            angle=request.trend.angle,
            tags=request.trend.tags,
            source=request.trend.source or "api",
        )
        
        brief = ContentBriefV1(
            topic=request.brief.topic,
            target_audience=request.brief.target_audience,
            tone=request.brief.tone,
            platform=request.brief.platform,
            duration_hint_s=request.brief.duration_hint_s,
        )
        
        # Select format
        if request.format_pack_id:
            from services.video_generation import get_format_by_id
            format_pack = get_format_by_id(request.format_pack_id)
            if not format_pack:
                raise HTTPException(status_code=404, detail="Format not found")
        else:
            selection = select_format(trend, brief)
            format_pack = selection["format"]
        
        # Generate IR
        story_ir = make_story_ir(trend, brief)
        
        # Generate shot plan
        shot_plan = make_auto_shot_plan(story_ir, format_pack)
        cost = estimate_auto_plan_cost(shot_plan)
        
        return {
            "format": {"id": format_pack.id, "label": format_pack.label},
            "shotPlan": shot_plan,
            "costEstimate": cost,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Shot plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio/mix")
async def mix_audio(request: AudioMixRequest):
    """
    Mix base audio with SFX events into an audio bus.
    
    Requires FFmpeg installed.
    """
    try:
        from services.sfx_library.types import AudioEvents, SfxAudioEvent
        
        # Build audio events
        events = AudioEvents(
            fps=request.fps,
            events=[
                SfxAudioEvent(
                    type="sfx",
                    sfx_id=ev.get("sfxId") or ev.get("sfx_id"),
                    frame=ev.get("frame", 0),
                    volume=ev.get("volume", 1.0),
                )
                for ev in request.sfx_events
            ],
        )
        
        # Load manifest
        manifest_path = request.manifest_path or "assets/sfx/manifest.json"
        sfx_root = request.sfx_root_dir or "assets/sfx"
        
        try:
            manifest = load_manifest(manifest_path)
        except Exception:
            raise HTTPException(status_code=404, detail="SFX manifest not found")
        
        # Create cue sheet
        cue_sheet = audio_events_to_cue_sheet(
            events=events,
            base_audio_path=request.base_audio_path,
            sfx_root_dir=sfx_root,
            manifest=manifest,
        )
        
        # Mix audio
        output_path = mix_audio_bus_sync(
            cue_sheet=cue_sheet,
            manifest=manifest,
            sfx_root_dir=sfx_root,
            output_path=request.output_path,
        )
        
        return {
            "status": "success",
            "outputPath": output_path,
            "cueCount": len(cue_sheet.cues),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio mix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

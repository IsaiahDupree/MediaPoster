"""
AI Analysis API Endpoints - Phase 1
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from pathlib import Path
import uuid
import json
import os
import tempfile
import urllib.request
import urllib.parse
from loguru import logger

from database.connection import get_db
from database.models import OriginalVideo, ProcessingJob
from modules.ai_analysis import ContentAnalyzer
from config.platform_limits import get_platform_limits, PLATFORM_LIMITS, DEFAULT_PROMPT_SETTINGS
from services.event_bus import EventBus, Topics

router = APIRouter()


# ─── Standalone File Analysis (no DB required) ────────────────────────────────

class AnalyzeFileRequest(BaseModel):
    file_path: Optional[str] = None
    url: Optional[str] = None
    transcribe: bool = True
    analyze_frames: bool = True
    fate_score: bool = True
    metadata: Optional[Dict[str, Any]] = None


class AnalyzeFileResponse(BaseModel):
    success: bool
    source: str
    transcript: str = ""
    topics: List[str] = []
    hooks: List[str] = []
    detected_hook: Optional[str] = None
    tone: str = ""
    pacing: str = ""
    pre_social_score: float = 0.0
    viral_analysis: str = ""
    pain_points: List[str] = []
    emotional_drivers: List[str] = []
    emotional_journey: Dict[str, Any] = {}
    call_to_action: Dict[str, Any] = {}
    scene_structure: List[Dict[str, Any]] = []
    content_type: str = ""
    target_audience: Dict[str, Any] = {}
    music_suggestion: Dict[str, Any] = {}
    key_moments: Dict[str, Any] = {}
    visual_summary: str = ""
    fate_scores: Dict[str, float] = {}
    transcription_language: Optional[str] = None
    transcription_duration_sec: Optional[float] = None
    transcription_word_count: Optional[int] = None
    words_per_minute: Optional[float] = None
    analysis_source: str = ""
    error: Optional[str] = None


@router.post("/analyze-file", response_model=AnalyzeFileResponse)
async def analyze_file(request: AnalyzeFileRequest):
    """
    Standalone video analysis — no database required.

    Accepts either a local file path or a URL to a video file.
    Runs the full pipeline synchronously and returns all results immediately:
      - Whisper transcription (Groq)
      - Content analysis: topics, hooks, tone, viral score, scene structure (Groq Llama)
      - Frame visual analysis (GPT-4o Mini)
      - FATE persuasion scoring (rule-based, free)

    Request body:
        file_path: absolute path to a local video file
        url:       public URL to a video file (will be downloaded to /tmp)
        transcribe:     run Whisper transcription (default true)
        analyze_frames: run GPT-4o Mini frame analysis (default true)
        fate_score:     run FATE persuasion scoring (default true)
        metadata:       optional dict passed to content analyzer (duration, title, etc.)

    Example:
        POST /api/analysis/analyze-file
        {
            "file_path": "/Volumes/My Passport/MediaPoster/workspace1/iphone_import/video.MOV",
            "transcribe": true,
            "analyze_frames": true,
            "fate_score": true
        }

    Or from another local server:
        POST http://localhost:5555/api/analysis/analyze-file
        { "url": "http://localhost:8080/media/video.mp4" }
    """
    if not request.file_path and not request.url:
        raise HTTPException(status_code=400, detail="Provide either 'file_path' or 'url'")

    # ── Resolve video path ────────────────────────────────────────────────────
    video_path = None
    tmp_file = None

    if request.file_path:
        video_path = os.path.expanduser(request.file_path)
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"File not found: {video_path}")
        if not os.path.isfile(video_path):
            raise HTTPException(status_code=400, detail=f"Path is not a file: {video_path}")
        source = video_path
    else:
        # Download URL to a temp file
        try:
            parsed = urllib.parse.urlparse(request.url)
            suffix = Path(parsed.path).suffix or ".mp4"
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_file.close()
            logger.info(f"[analyze-file] Downloading {request.url} → {tmp_file.name}")
            urllib.request.urlretrieve(request.url, tmp_file.name)
            video_path = tmp_file.name
            source = request.url
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download URL: {e}")

    try:
        result = await _run_standalone_analysis(
            video_path=video_path,
            source=source,
            transcribe=request.transcribe,
            analyze_frames=request.analyze_frames,
            fate_score=request.fate_score,
            metadata=request.metadata or {},
        )
        return result
    finally:
        if tmp_file and os.path.exists(tmp_file.name):
            try:
                os.unlink(tmp_file.name)
            except Exception:
                pass


async def _run_standalone_analysis(
    video_path: str,
    source: str,
    transcribe: bool,
    analyze_frames: bool,
    fate_score: bool,
    metadata: dict,
) -> AnalyzeFileResponse:
    """Run the full analysis pipeline on a file path, return structured results."""

    transcript = ""
    visual_summary = ""
    analysis = {}
    fate_scores = {}
    transcription_meta = {}
    analysis_source = "none"
    error_notes = []

    # ── Step 1: Transcription ─────────────────────────────────────────────────
    if transcribe:
        try:
            from services.whisper_transcriber import WhisperTranscriber
            transcriber = WhisperTranscriber()
            logger.info(f"[analyze-file] Step 1/3: Transcribing {Path(video_path).name}")
            result = transcriber.transcribe_video(video_path)
            transcript = result.get("text", "")
            transcription_meta = {
                "language": result.get("language"),
                "duration": result.get("duration"),
                "segments": result.get("segments", []),
                "words": result.get("words", []),
            }
            if transcript:
                logger.info(f"[analyze-file] Transcript: {len(transcript)} chars")
            else:
                logger.warning(f"[analyze-file] No transcript returned (no audio?)")
                error_notes.append("No audio stream or empty transcript")
        except Exception as e:
            logger.error(f"[analyze-file] Transcription failed: {e}")
            error_notes.append(f"Transcription error: {e}")

    # ── Step 2: Frame visual analysis ─────────────────────────────────────────
    if analyze_frames:
        try:
            from services.thumbnail_generator import ThumbnailGenerator
            from services.frame_analyzer import FrameAnalyzer
            logger.info(f"[analyze-file] Step 2/3: Analyzing frames")
            thumb_gen = ThumbnailGenerator()
            frames = thumb_gen.extract_frames(video_path, num_frames=5)
            if frames:
                frame_analyzer = FrameAnalyzer()
                visual_result = frame_analyzer.analyze_frames(frames)
                visual_summary = visual_result.get("visual_summary", "")
                logger.info(f"[analyze-file] Visual summary: {len(visual_summary)} chars")
            else:
                logger.warning(f"[analyze-file] No frames extracted")
                error_notes.append("No frames could be extracted")
        except Exception as e:
            logger.error(f"[analyze-file] Frame analysis failed: {e}")
            error_notes.append(f"Frame analysis error: {e}")

    # ── Step 3: Content analysis (transcript → Groq Llama) ────────────────────
    try:
        from services.content_analyzer import ContentAnalyzer as CA
        analyzer = CA()
        analysis_metadata = {**metadata}
        if visual_summary:
            analysis_metadata["visual_context"] = visual_summary

        if transcript and len(transcript.strip()) > 10:
            logger.info(f"[analyze-file] Step 3/3: Content analysis (transcript)")
            analysis = analyzer.analyze_transcript(transcript, video_metadata=analysis_metadata)
            analysis_source = "transcript"
        elif visual_summary and len(visual_summary.strip()) > 20:
            logger.info(f"[analyze-file] Step 3/3: Content analysis (visuals fallback)")
            analysis = analyzer.analyze_from_visuals(visual_summary, video_metadata=analysis_metadata)
            analysis_source = "visuals"
        else:
            logger.warning(f"[analyze-file] No content to analyze")
            error_notes.append("No transcript or visual content available for analysis")
    except Exception as e:
        logger.error(f"[analyze-file] Content analysis failed: {e}")
        error_notes.append(f"Content analysis error: {e}")

    # ── Step 4: FATE scoring ──────────────────────────────────────────────────
    if fate_score and transcript:
        try:
            from services.fate_scorer import get_fate_scorer
            scorer = get_fate_scorer()
            fate_scores = scorer.score_all(transcript)
            logger.info(f"[analyze-file] FATE: F={fate_scores.get('F', 0):.2f} A={fate_scores.get('A', 0):.2f} T={fate_scores.get('T', 0):.2f} E={fate_scores.get('E', 0):.2f}")
        except Exception as e:
            logger.error(f"[analyze-file] FATE scoring failed: {e}")
            error_notes.append(f"FATE scoring error: {e}")

    # ── Compute words per minute ──────────────────────────────────────────────
    words_per_minute = None
    word_count = len(transcription_meta.get("words", [])) or (len(transcript.split()) if transcript else 0)
    duration = transcription_meta.get("duration")
    if word_count and duration and duration > 0:
        words_per_minute = round((word_count / duration) * 60, 1)

    # ── Build response ────────────────────────────────────────────────────────
    hooks = analysis.get("hooks", [])
    detected_hook = analysis.get("detected_hook") or (hooks[0] if hooks else None)

    return AnalyzeFileResponse(
        success=True,
        source=source,
        transcript=transcript,
        topics=analysis.get("topics", []),
        hooks=hooks,
        detected_hook=detected_hook,
        tone=analysis.get("tone", ""),
        pacing=analysis.get("pacing", ""),
        pre_social_score=float(analysis.get("pre_social_score", 0)),
        viral_analysis=analysis.get("viral_analysis", ""),
        pain_points=analysis.get("pain_points", []),
        emotional_drivers=analysis.get("emotional_drivers", []),
        emotional_journey=analysis.get("emotional_journey", {}),
        call_to_action=analysis.get("call_to_action", {}),
        scene_structure=analysis.get("scene_structure", []),
        content_type=analysis.get("content_type", ""),
        target_audience=analysis.get("target_audience", {}),
        music_suggestion=analysis.get("music_suggestion", {}),
        key_moments=analysis.get("key_moments", {}),
        visual_summary=visual_summary,
        fate_scores=fate_scores,
        transcription_language=transcription_meta.get("language"),
        transcription_duration_sec=transcription_meta.get("duration"),
        transcription_word_count=word_count or None,
        words_per_minute=words_per_minute,
        analysis_source=analysis_source,
        error="; ".join(error_notes) if error_notes else None,
    )


class AnalysisRequest(BaseModel):
    transcribe: bool = True
    analyze_vision: bool = True
    analyze_audio: bool = True
    max_frames: int = 15


class AnalysisResponse(BaseModel):
    job_id: uuid.UUID
    video_id: uuid.UUID
    status: str
    message: str


class GenerateCaptionsRequest(BaseModel):
    platform: str = "tiktok"
    tone: str = "engaging"
    style: Optional[str] = None
    include_hashtags: bool = True
    include_hook: bool = True
    custom_prompt: Optional[str] = None


@router.post("/full-analysis/{video_id}", response_model=AnalysisResponse)
async def start_full_analysis(
    video_id: uuid.UUID,
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start comprehensive AI analysis for a video
    
    Includes:
    - Whisper transcription
    - Frame extraction and GPT-4 Vision analysis
    - Audio characteristic analysis
    """
    from sqlalchemy import select
    
    # Get video from database
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Create processing job
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="ai_analysis",
        status="queued",
        config_json={
            'transcribe': request.transcribe,
            'analyze_vision': request.analyze_vision,
            'analyze_audio': request.analyze_audio,
            'max_frames': request.max_frames
        }
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Emit ANALYSIS_REQUESTED event
    try:
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.ANALYSIS_REQUESTED, {
            "job_id": str(job.job_id),
            "video_id": str(video_id),
            "transcribe": request.transcribe,
            "analyze_vision": request.analyze_vision,
        })
        logger.info(f"[PubSub] Emitted ANALYSIS_REQUESTED for {job.job_id}")
    except Exception as e:
        logger.warning(f"[PubSub] Failed to emit analysis event: {e}")
    
    # Start analysis in background
    background_tasks.add_task(
        run_analysis,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path),
        config=request.dict()
    )
    
    return AnalysisResponse(
        job_id=job.job_id,
        video_id=video_id,
        status="queued",
        message="Analysis started. Check job status for progress."
    )


@router.post("/transcribe/{video_id}")
async def transcribe_video(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Transcribe video audio with Whisper"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="transcription",
        status="queued"
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    background_tasks.add_task(
        run_transcription_only,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path)
    )
    
    return {"job_id": str(job.job_id), "status": "queued"}


@router.get("/results")
async def list_analysis_results(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all videos with analysis results"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo)
        .filter(OriginalVideo.analysis_data.isnot(None))
        .limit(limit)
        .offset(offset)
        .order_by(OriginalVideo.created_at.desc())
    )
    videos = list(result.scalars().all())
    
    return {
        "total": len(videos),
        "videos": [
            {
                "video_id": str(v.video_id),
                "video_name": v.file_name,
                "has_analysis": v.analysis_data is not None,
                "analysis_keys": list(v.analysis_data.keys()) if v.analysis_data else []
            }
            for v in videos
        ]
    }


@router.get("/results/{video_id}")
async def get_analysis_results(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get analysis results for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analysis_data:
        raise HTTPException(status_code=404, detail="No analysis data available")
    
    return {
        "video_id": str(video_id),
        "video_name": video.file_name,
        "analysis": video.analysis_data
    }


@router.get("/transcript/{video_id}")
async def get_transcript(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get transcript for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analysis_data or 'transcript' not in video.analysis_data:
        raise HTTPException(status_code=404, detail="Transcript not available")
    
    return {
        "video_id": str(video_id),
        "transcript": video.analysis_data['transcript']
    }


@router.post("/generate-captions/{media_id}")
async def generate_captions(
    media_id: str,
    request: GenerateCaptionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered captions for a media item using transcript and analysis data.
    
    Args:
        media_id: UUID of the media item
        request: Generation parameters including platform, tone, style
        
    Returns:
        Generated captions for each platform with hashtags and hooks
    """
    from sqlalchemy import select, text
    
    logger.info(f"[GenerateCaptions] 🚀 Starting caption generation for media_id={media_id}")
    logger.info(f"[GenerateCaptions] 📋 Request: platform={request.platform}, tone={request.tone}, style={request.style}")
    logger.info(f"[GenerateCaptions] 📋 Custom prompt: {request.custom_prompt}")
    
    # Try to find media in the videos table (media-db)
    transcript = ""
    topics = []
    hooks = []
    title = ""
    
    try:
        # First, get the video metadata
        video_result = await db.execute(
            text("SELECT id, file_name FROM videos WHERE id = :media_id"),
            {"media_id": media_id}
        )
        video_row = video_result.fetchone()
        
        if video_row:
            # Video found in videos table - get analysis from video_analysis table
            title = video_row[1] or ''
            logger.info(f"[GenerateCaptions] 📄 Found video: {title}")
            
            # Get analysis data from video_analysis table
            analysis_result = await db.execute(
                text("SELECT transcript, topics, hooks FROM video_analysis WHERE video_id = :media_id"),
                {"media_id": media_id}
            )
            analysis_row = analysis_result.fetchone()
            
            if analysis_row:
                transcript = analysis_row[0] or ''
                # Handle PostgreSQL arrays - they come as lists or None
                topics_raw = analysis_row[1]
                hooks_raw = analysis_row[2]
                topics = list(topics_raw) if topics_raw else []
                hooks = list(hooks_raw) if hooks_raw else []
                logger.info(f"[GenerateCaptions] 📝 Transcript length: {len(transcript)} chars")
                logger.info(f"[GenerateCaptions] 🏷️ Topics ({len(topics)}): {topics}")
                logger.info(f"[GenerateCaptions] 🎣 Hooks ({len(hooks)}): {hooks}")
            else:
                logger.warning(f"[GenerateCaptions] ⚠️ No analysis data found for video_id={media_id}")
        else:
            # Try original_videos table as fallback
            logger.warning(f"[GenerateCaptions] ⚠️ Media not found in videos table, trying original_videos")
            result = await db.execute(
                select(OriginalVideo).filter(OriginalVideo.video_id == uuid.UUID(media_id))
            )
            media = result.scalar_one_or_none()
            
            if media:
                title = media.file_name or ''
                transcript = media.transcript or ''
                topics = media.topics or []
                hooks = media.hooks if hasattr(media, 'hooks') else []
                
                # Also check analysis_data for hooks
                if media.analysis_data:
                    hooks_from_data = media.analysis_data.get('hooks', [])
                    if hooks_from_data:
                        hooks = hooks_from_data
                
                logger.info(f"[GenerateCaptions] 📄 Found original video: {title}")
                logger.info(f"[GenerateCaptions] 📝 Transcript length: {len(transcript)} chars")
                logger.info(f"[GenerateCaptions] 🏷️ Topics: {topics}")
                logger.info(f"[GenerateCaptions] 🎣 Hooks: {hooks}")
            else:
                logger.error(f"[GenerateCaptions] ❌ Media not found: {media_id}")
                raise HTTPException(status_code=404, detail="Media not found")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GenerateCaptions] ❌ Database query error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if not title:
        logger.error(f"[GenerateCaptions] ❌ Media not found: {media_id}")
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Use AI to generate creative title and description from analysis context
    original_filename = title
    import re
    is_filename = re.match(r'^(IMG_|VID_|MOV_|\d+\.)', title, re.IGNORECASE) or title.endswith('.MOV') or title.endswith('.mp4')
    
    # Get platform limits for title generation (20% of max)
    from config.platform_limits import get_platform_limits
    platform_limits = get_platform_limits(request.platform)
    title_target = platform_limits.title_target  # 20% buffer already applied (80% of max)
    
    # ALWAYS generate a new AI title when regenerate is called
    # This is a regeneration endpoint - user expects new content each time
    logger.info(f"[GenerateCaptions] 🔄 REGENERATION requested - will always generate new AI title")
    logger.info(f"[GenerateCaptions] 📊 Context available: transcript={len(transcript) if transcript else 0} chars, topics={len(topics) if topics else 0}, hooks={len(hooks) if hooks else 0}")
    
    # Always try to generate with AI, even with minimal context
    if True:  # Always attempt AI generation for regeneration
        try:
            from openai import OpenAI
            import os
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Build rich context for AI - use whatever is available
            context_parts = []
            if topics:
                context_parts.append(f"Main Topics: {', '.join(topics[:5])}")
            if hooks:
                context_parts.append(f"Key Hooks: {'; '.join(hooks[:3])}")
            if transcript:
                context_parts.append(f"Content Summary: {transcript[:500]}")
            
            # If no context available, use filename as hint
            if not context_parts and original_filename:
                context_parts.append(f"Original filename hint: {original_filename}")
            
            context = "\n".join(context_parts) if context_parts else "General engaging content"
            
            # Generate creative title using AI with platform-specific limit (20% of max)
            # Use higher temperature (0.95) to ensure variety on each regeneration
            title_prompt = f"""Based on this video analysis, create a FRESH, NEW, catchy, viral-worthy title for {request.platform}.
REQUIREMENTS:
- Maximum {title_target} characters (strict limit)
- Punchy and attention-grabbing
- NO quotes, NO hashtags, NO emojis
- Make people want to click and watch
- Optimized for {request.platform} audience
- BE CREATIVE - this is a REGENERATION request, generate something DIFFERENT each time

Analysis Context:
{context}

Generate ONLY the title, no quotes, no explanation. Make it unique and fresh!"""

            logger.info(f"[GenerateCaptions] 🤖 Calling OpenAI to generate NEW title (target: {title_target} chars for {request.platform})...")
            
            title_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are a viral content title expert for {request.platform}. Create short, punchy, UNIQUE titles under {title_target} characters. Each regeneration should produce a DIFFERENT title."},
                    {"role": "user", "content": title_prompt}
                ],
                max_tokens=60,
                temperature=0.95  # Higher temperature for more variety on regeneration
            )
            
            ai_title = title_response.choices[0].message.content.strip().strip('"').strip("'")
            logger.info(f"[GenerateCaptions] 🎯 Raw AI title response: '{ai_title}'")
            
            # Enforce platform-specific limit - accept any non-empty title
            if ai_title and len(ai_title) > 3:
                if len(ai_title) > title_target:
                    ai_title = ai_title[:title_target - 3] + "..."
                title = ai_title
                logger.info(f"[GenerateCaptions] ✨ NEW AI Generated title ({len(title)}/{title_target} chars): {title}")
            else:
                logger.warning(f"[GenerateCaptions] ⚠️ AI returned short/empty title: '{ai_title}'")
            
        except Exception as e:
            logger.error(f"[GenerateCaptions] ❌ AI title generation failed: {e}", exc_info=True)
            # Fallback: generate a creative title from available data
            import random
            prefixes = ["The Truth About", "Why You Need", "How I", "What Happens When", "The Secret to", "You Won't Believe"]
            if topics and len(topics) > 0:
                fallback_title = f"{random.choice(prefixes)} {topics[0]}"
            elif hooks and len(hooks) > 0:
                fallback_title = hooks[0][:title_target]
            else:
                fallback_title = f"{random.choice(prefixes)} This"
            if len(fallback_title) > title_target:
                fallback_title = fallback_title[:title_target - 3] + "..."
            title = fallback_title
            logger.info(f"[GenerateCaptions] 🏷️ Fallback title: {title}")
    
    # Generate captions using AI or templates (will generate platform-specific titles/descriptions)
    generation_result = await _generate_platform_captions(
        title=title,
        transcript=transcript,
        topics=topics,
        hooks=hooks,
        platform=request.platform,
        tone=request.tone,
        style=request.style,
        custom_prompt=request.custom_prompt,
        include_hashtags=request.include_hashtags,
        include_hook=request.include_hook
    )
    
    # Extract results from generation
    generated_captions = generation_result["captions"]
    clean_descriptions = generation_result["platform_descriptions"]
    generated_hashtags = generation_result.get("hashtags", [])
    
    logger.info(f"[GenerateCaptions] ✅ Generated captions successfully")
    logger.info(f"[GenerateCaptions] 📤 TikTok caption: {generated_captions.get('tiktok', '')[:100]}...")
    logger.info(f"[GenerateCaptions] 📝 Instagram description length: {len(clean_descriptions.get('instagram', ''))} chars")
    
    # Build platform-specific titles (use generated title for all platforms)
    platform_titles = {p: title for p in generated_captions.keys()}
    
    # Use the clean descriptions from AI (without hashtags mixed in)
    # These are the comprehensive descriptions targeting 80% of max chars
    platform_descriptions = clean_descriptions.copy()
    
    # Fallback: if a platform doesn't have a clean description, extract from caption
    for platform_key in generated_captions.keys():
        if platform_key not in platform_descriptions or not platform_descriptions[platform_key]:
            caption = generated_captions[platform_key]
            # Extract description by removing hashtags
            desc = caption.split('#')[0].strip() if '#' in caption else caption
            # Remove leading emojis
            import re
            desc = re.sub(r'^[\U0001F300-\U0001F9FF\s]+', '', desc).strip()
            platform_descriptions[platform_key] = desc
    
    return {
        "success": True,
        "media_id": media_id,
        "title": title,  # Generic title (for backward compatibility)
        "platform_titles": platform_titles,  # Platform-specific titles
        "platform_descriptions": platform_descriptions,  # Clean descriptions (80% of max, no hashtags)
        "transcript_available": len(transcript) > 0,
        "captions": generated_captions,  # Full captions with hashtags
        "hashtags": generated_hashtags  # Separate hashtags array
    }


def truncate_to_limit(text: str, max_chars: int, add_ellipsis: bool = True) -> str:
    """Truncate text to fit within character limit"""
    if len(text) <= max_chars:
        return text
    if add_ellipsis and max_chars > 3:
        return text[:max_chars - 3].rsplit(' ', 1)[0] + "..."
    return text[:max_chars]


async def _generate_platform_captions(
    title: str,
    transcript: str,
    topics: List[str],
    hooks: List[str],
    platform: str,
    tone: str,
    style: Optional[str],
    custom_prompt: Optional[str],
    include_hashtags: bool,
    include_hook: bool
) -> Dict[str, str]:
    """Generate captions for all platforms using AI based on content analysis.
    
    Enforces platform-specific character limits with 20% buffer for safety.
    """
    
    logger.info(f"[_generate_platform_captions] 🎯 Generating for tone={tone}, style={style}")
    
    # Get platform limits for all platforms we'll generate for
    platforms_to_generate = ["tiktok", "instagram", "youtube", "twitter", "threads", "pinterest", "linkedin", "bluesky", "facebook"]
    platform_limits = {p: get_platform_limits(p) for p in platforms_to_generate}
    
    # Build context from available data - use MORE content for better descriptions
    topics_str = ', '.join(topics[:8]) if topics else ""
    hooks_str = '; '.join(hooks[:5]) if hooks else ""
    transcript_snippet = transcript[:2000] if transcript else ""  # More transcript for context
    
    # Generate UNIQUE descriptions for EACH platform using AI
    # Each platform gets its own AI call with platform-specific requirements
    platform_descriptions = {}
    
    # Platform-specific character limits (targeting 80% of max = 20% buffer)
    main_platforms = ['tiktok', 'instagram', 'youtube']
    
    try:
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Build rich context
        context = f"""
Video Title: {title}
Topics: {topics_str}
Key Hooks: {hooks_str}
Content: {transcript_snippet}
Tone: {tone}
"""
        
        # Generate unique description for EACH main platform
        for plat in main_platforms:
            plat_limit = platform_limits.get(plat, platform_limits.get('tiktok'))
            desc_target = plat_limit.description_target  # Already 80% of max
            
            # Platform-specific prompts for variety
            platform_style = {
                'tiktok': "punchy, trend-aware, Gen-Z friendly with energy and personality. Use conversational hooks.",
                'instagram': "aesthetic, lifestyle-focused, inspirational. Encourage saves and shares with a strong CTA.",
                'youtube': "detailed, value-packed, SEO-friendly. Explain what viewers will learn and why they should watch."
            }
            
            # Calculate appropriate length guidance - be aggressive about length
            min_chars = int(desc_target * 0.5)  # At least 50% of target for expansion trigger
            
            desc_prompt = f"""Write a {desc_target}-character description for {plat.upper()}.

⚠️ CRITICAL LENGTH REQUIREMENT: Your response MUST be between {min_chars} and {desc_target} characters.
Descriptions under {min_chars} characters will be REJECTED. Count your characters carefully.

STYLE: {platform_style.get(plat, 'engaging and compelling')}

REQUIRED STRUCTURE (write 2-4 sentences for EACH section):

**SECTION 1 - HOOK (100-150 chars):**
Start with an attention-grabbing opening that stops scrollers.

**SECTION 2 - VALUE PROPOSITION (200-400 chars):**
Explain what viewers will learn, discover, or experience. Be specific about the benefits.

**SECTION 3 - STORY/CONTEXT (300-500 chars):**
Add personal touch, backstory, or relatable context from the video content below.

**SECTION 4 - KEY INSIGHTS (200-400 chars):**
Share specific takeaways, tips, or insights from the content.

**SECTION 5 - CALL TO ACTION (100-200 chars):**
Encourage engagement - comments, saves, shares, follows.

VIDEO CONTENT TO REFERENCE:
Topics: {topics_str}
Key Points: {hooks_str}
Transcript: {transcript_snippet[:1500] if transcript_snippet else 'General lifestyle/personal content'}

OUTPUT RULES:
- Write ONLY the description text (no section headers)
- NO hashtags (they're added separately)
- NO title repetition
- Aim for EXACTLY {desc_target} characters
- Each section should flow naturally into the next"""

            logger.info(f"[_generate_platform_captions] 🤖 Generating {desc_target}-char description for {plat} (min: {min_chars})...")
            
            # Calculate max_tokens - need more tokens for longer output
            # Roughly 1 token = 4 chars, so target/3 gives buffer
            required_tokens = max(800, int(desc_target / 2.5))
            
            # Try up to 2 times to get a description of adequate length
            desc_text = ""
            for attempt in range(2):
                desc_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"You are a {plat} copywriter. Write LONG descriptions. Target: {desc_target} characters minimum."},
                        {"role": "user", "content": desc_prompt + (f"\n\n⚠️ RETRY: Your previous response was only {len(desc_text)} characters. You MUST write at least {min_chars} characters this time." if attempt > 0 else "")}
                    ],
                    max_tokens=required_tokens,
                    temperature=0.8 + (attempt * 0.1)  # Slightly higher temp on retry
                )
                
                desc_text = desc_response.choices[0].message.content.strip()
                
                # Remove any markdown headers the model might have added
                import re
                desc_text = re.sub(r'\*\*[^*]+\*\*:?\s*', '', desc_text)
                desc_text = re.sub(r'^\s*\d+\.\s*', '', desc_text, flags=re.MULTILINE)
                desc_text = desc_text.strip()
                
                if len(desc_text) >= min_chars * 0.6:  # Accept if at least 60% of minimum
                    break
                logger.warning(f"[_generate_platform_captions] ⚠️ {plat} attempt {attempt+1}: {len(desc_text)} chars (need {min_chars}), retrying...")
            
            # Enforce limit
            if len(desc_text) > desc_target:
                desc_text = truncate_to_limit(desc_text, desc_target)
            
            # Always try to expand descriptions to target length using available content
            target_len = int(desc_target * 0.7)  # Target 70% of max
            
            if len(desc_text) < target_len:
                logger.info(f"[_generate_platform_captions] 📈 {plat} expanding from {len(desc_text)} to target {target_len} chars...")
                
                # Build expansion content - order matters (most valuable first)
                expansion_parts = []
                
                # 1. Add transcript content (most valuable - actual video content)
                if transcript_snippet and len(transcript_snippet) > 50:
                    expansion_parts.append(f"\n\n📝 From the video: \"{transcript_snippet[:600]}...\"")
                
                # 2. Add hooks (key talking points)
                if hooks:
                    for hook in hooks[:3]:
                        if hook and len(hook) > 10:
                            expansion_parts.append(f"\n\n💡 {hook}")
                
                # 3. Add topic context
                if topics and len(topics) > 0:
                    expansion_parts.append(f"\n\n🎯 Topics covered: {', '.join(topics[:5])}")
                
                # 4. Engagement prompts
                expansion_parts.extend([
                    "\n\n💬 What do you think? Drop your thoughts in the comments!",
                    "\n\n📌 Save this post - you'll want to come back to it later.",
                    "\n\n👥 Tag someone who needs to see this!",
                    "\n\n🔔 Follow for more content like this every day!",
                    "\n\n❤️ Double tap if this resonates with you!",
                ])
                
                # Add content until we reach target
                for part in expansion_parts:
                    if len(desc_text) >= target_len:
                        break
                    desc_text = desc_text + part
                
                # Truncate if over limit
                if len(desc_text) > desc_target:
                    desc_text = truncate_to_limit(desc_text, desc_target)
                
                logger.info(f"[_generate_platform_captions] ✅ {plat} expanded to: {len(desc_text)}/{desc_target} chars")
            
            platform_descriptions[plat] = desc_text
            logger.info(f"[_generate_platform_captions] ✅ {plat}: {len(desc_text)}/{desc_target} chars (min: {min_chars}) - '{desc_text[:80]}...'")
        
    except Exception as e:
        logger.error(f"[_generate_platform_captions] ❌ AI description generation failed: {e}")
        # Fallback to basic descriptions with variation
        fallback_templates = {
            'tiktok': f"You need to see this! Discover how {topics[0] if topics else 'this'} can change everything.",
            'instagram': f"This changed my perspective on {topics[0] if topics else 'everything'}. Save this for later!",
            'youtube': f"In this video, learn valuable insights about {topics[0] if topics else 'this topic'} that could transform your approach."
        }
        for plat in main_platforms:
            platform_descriptions[plat] = fallback_templates.get(plat, "Watch to discover valuable insights.")
    
    # Use tiktok description as default fallback
    description_text = platform_descriptions.get('tiktok', '')
    
    logger.info(f"[_generate_platform_captions] 📄 Title: {title[:50]}...")
    for plat, desc in platform_descriptions.items():
        logger.info(f"[_generate_platform_captions] 📝 {plat}: {desc[:60]}...")
    
    # Determine tone modifiers
    is_humorous = tone == 'funny' or (style and 'funny' in style.lower()) or (custom_prompt and 'funny' in custom_prompt.lower())
    is_professional = tone == 'professional' or (style and 'professional' in style.lower())
    is_casual = tone == 'casual' or (style and 'casual' in style.lower())
    is_engaging = tone == 'engaging' or not (is_humorous or is_professional or is_casual)
    
    logger.info(f"[_generate_platform_captions] 🎭 Tone detection: humorous={is_humorous}, professional={is_professional}, casual={is_casual}, engaging={is_engaging}")
    
    # Generate hashtags based on topics
    base_hashtags = []
    if topics:
        base_hashtags = [f"#{t.replace(' ', '').lower()}" for t in topics[:5]]
    
    # Platform-specific generation using UNIQUE descriptions per platform
    # NOTE: Descriptions should NOT include the title - title is separate
    captions = {}
    
    # Get platform-specific descriptions (each is unique)
    tiktok_desc = platform_descriptions.get('tiktok', description_text)
    instagram_desc = platform_descriptions.get('instagram', description_text)
    youtube_desc = platform_descriptions.get('youtube', description_text)
    
    # TikTok caption - uses unique TikTok description
    if is_humorous:
        tiktok_caption = f"😂 {tiktok_desc}\n\n" if tiktok_desc else ""
        tiktok_caption += f"#fyp #viral #comedy {' '.join(base_hashtags[:3])}"
    elif is_professional:
        tiktok_caption = f"📊 {tiktok_desc}\n\n" if tiktok_desc else ""
        tiktok_caption += f"#business #professional {' '.join(base_hashtags[:3])}"
    elif is_casual:
        tiktok_caption = f"👋 {tiktok_desc}\n\n" if tiktok_desc else ""
        tiktok_caption += f"#fyp #foryou {' '.join(base_hashtags[:3])}"
    else:
        tiktok_caption = f"🔥 {tiktok_desc}\n\n" if tiktok_desc else ""
        tiktok_caption += f"#fyp #viral {' '.join(base_hashtags[:3])}"
    
    captions['tiktok'] = tiktok_caption.strip()
    
    # Instagram caption - uses unique Instagram description
    if is_humorous:
        instagram_caption = f"😂 {instagram_desc}\n\n" if instagram_desc else ""
        instagram_caption += f"Tag someone who needs to see this! 👇\n\n#reels #funny {' '.join(base_hashtags[:5])}"
    elif is_professional:
        instagram_caption = f"{instagram_desc}\n\n" if instagram_desc else ""
        instagram_caption += f"What are your thoughts? Share below.\n\n#professional {' '.join(base_hashtags[:5])}"
    elif is_casual:
        instagram_caption = f"✨ {instagram_desc}\n\n" if instagram_desc else ""
        instagram_caption += f"#reels #mood {' '.join(base_hashtags[:5])}"
    else:
        instagram_caption = f"✨ {instagram_desc}\n\n" if instagram_desc else ""
        instagram_caption += f"#reels #explore {' '.join(base_hashtags[:5])}"
    
    captions['instagram'] = instagram_caption.strip()
    
    # YouTube caption - uses unique YouTube description
    if is_humorous:
        youtube_caption = f"{youtube_desc} 😂\n\n" if youtube_desc else ""
        youtube_caption += f"Don't forget to like and subscribe for more!\n\nTopics: {topics_str}"
    elif is_professional:
        youtube_caption = f"{youtube_desc}\n\n" if youtube_desc else ""
        youtube_caption += f"For more professional content, subscribe to our channel.\n\nTopics: {topics_str}"
    elif is_casual:
        youtube_caption = f"{youtube_desc}\n\n" if youtube_desc else ""
        youtube_caption += f"Thanks for watching! 💜\n\nTopics: {topics_str}"
    else:
        youtube_caption = f"{youtube_desc}\n\n" if youtube_desc else ""
        youtube_caption += f"Topics: {topics_str}"
    
    captions['youtube'] = youtube_caption.strip()
    
    # Generate for additional platforms with proper limits
    # NOTE: All descriptions should NOT include the title - title is separate
    
    # Twitter/X - description only (short platform)
    twitter_limit = platform_limits['twitter']
    twitter_caption = ""
    if description_text:
        twitter_caption = truncate_to_limit(description_text, twitter_limit.description_target - 40)
    if include_hashtags and base_hashtags:
        twitter_caption += f" {' '.join(base_hashtags[:2])}"
    captions['twitter'] = truncate_to_limit(twitter_caption.strip(), twitter_limit.description_target)
    
    # Threads - description only
    threads_limit = platform_limits['threads']
    threads_caption = ""
    if description_text:
        threads_caption = f"✨ {truncate_to_limit(description_text, threads_limit.description_target - 50)}\n\n"
    if include_hashtags and base_hashtags:
        threads_caption += ' '.join(base_hashtags[:3])
    captions['threads'] = truncate_to_limit(threads_caption.strip(), threads_limit.description_target)
    
    # Pinterest - description only
    pinterest_limit = platform_limits['pinterest']
    pinterest_title = truncate_to_limit(title, pinterest_limit.title_target)
    pinterest_desc = description_text if description_text else f"Discover insights about {topics[0] if topics else 'this topic'}"
    captions['pinterest'] = truncate_to_limit(pinterest_desc, pinterest_limit.description_target)
    captions['pinterest_title'] = pinterest_title
    
    # LinkedIn - description only
    linkedin_limit = platform_limits['linkedin']
    linkedin_caption = ""
    if description_text:
        linkedin_caption = f"{description_text}\n\n"
    linkedin_caption += "What are your thoughts? Share in the comments below."
    if include_hashtags and base_hashtags:
        linkedin_caption += f"\n\n{' '.join(base_hashtags[:5])}"
    captions['linkedin'] = truncate_to_limit(linkedin_caption.strip(), linkedin_limit.description_target)
    
    # Bluesky - description only
    bluesky_limit = platform_limits['bluesky']
    bluesky_caption = ""
    if description_text:
        bluesky_caption = truncate_to_limit(description_text, bluesky_limit.description_target - 30)
    captions['bluesky'] = truncate_to_limit(bluesky_caption.strip(), bluesky_limit.description_target)
    
    # Facebook - description only
    facebook_limit = platform_limits['facebook']
    facebook_caption = ""
    if description_text:
        facebook_caption = f"{description_text}\n\n"
    if include_hashtags and base_hashtags:
        facebook_caption += ' '.join(base_hashtags[:3])
    captions['facebook'] = truncate_to_limit(facebook_caption.strip(), facebook_limit.description_target)
    
    # Enforce limits on previously generated captions
    captions['tiktok'] = truncate_to_limit(captions['tiktok'], platform_limits['tiktok'].description_target)
    captions['instagram'] = truncate_to_limit(captions['instagram'], platform_limits['instagram'].description_target)
    captions['youtube'] = truncate_to_limit(captions['youtube'], platform_limits['youtube'].description_target)
    
    # Log character counts for debugging
    for p, caption in captions.items():
        if p in platform_limits:
            limit = platform_limits[p].description_target
            logger.info(f"[_generate_platform_captions] 📏 {p}: {len(caption)}/{limit} chars")
    
    # Return both captions (with hashtags) and clean descriptions (without hashtags)
    return {
        "captions": captions,
        "platform_descriptions": platform_descriptions,  # Clean descriptions from AI
        "hashtags": base_hashtags
    }


# Background task functions
async def run_analysis(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path,
    config: dict
):
    """Run complete analysis in background"""
    from database.connection import async_session_maker
    from sqlalchemy import select, update
    from datetime import datetime
    
    async with async_session_maker() as session:
        try:
            # Update job status
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await session.commit()
            
            # Run analysis
            analyzer = ContentAnalyzer()
            analysis = analyzer.analyze_video_complete(
                video_path,
                extract_frames=True,
                analyze_vision=config['analyze_vision'],
                transcribe_audio=config['transcribe'],
                analyze_audio=config['analyze_audio'],
                max_frames=config['max_frames']
            )
            
            # Save analysis to video record
            await session.execute(
                update(OriginalVideo)
                .where(OriginalVideo.video_id == video_id)
                .values(analysis_data=analysis)
            )
            
            # Update job status
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    progress_percent=100
                )
            )
            await session.commit()
            
        except Exception as e:
            # Update job with error
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(
                    status="failed",
                    error_message=str(e)
                )
            )
            await session.commit()
            raise


async def run_transcription_only(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path
):
    """Run transcription only"""
    from database.connection import async_session_maker
    from sqlalchemy import update
    from datetime import datetime
    from modules.ai_analysis import WhisperService
    
    async with async_session_maker() as session:
        try:
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await session.commit()
            
            whisper = WhisperService()
            transcript = whisper.transcribe_video(video_path)
            
            # Save to video
            result = await session.execute(
                select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
            )
            video = result.scalar_one()
            
            if video.analysis_data:
                video.analysis_data['transcript'] = transcript
            else:
                video.analysis_data = {'transcript': transcript}
            
            await session.commit()
            
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="completed", completed_at=datetime.utcnow(), progress_percent=100)
            )
            await session.commit()
            
        except Exception as e:
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="failed", error_message=str(e))
            )
            await session.commit()

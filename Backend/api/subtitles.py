"""
Subtitles API
=============
Endpoints for auto-subtitle management: styles, transcription, and preview.
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])


# ─── Models ──────────────────────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    video_path: str
    style: str = "tiktok_bold"


class TranscribeResponse(BaseModel):
    success: bool
    output_path: Optional[str] = None
    transcript: Optional[str] = None
    word_count: Optional[int] = None
    duration: Optional[float] = None
    language: Optional[str] = None
    style: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


class StyleInfo(BaseModel):
    name: str
    description: str


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/styles")
async def get_styles():
    """List available subtitle style presets."""
    from services.subtitle_service import AutoSubtitleService
    styles = AutoSubtitleService.get_available_styles()
    default = os.getenv("DEFAULT_CAPTION_STYLE", "tiktok_bold")
    return {
        "styles": [{"name": k, "description": v} for k, v in styles.items()],
        "default": default,
    }


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_video(req: TranscribeRequest):
    """
    Transcribe a video and burn in styled captions.
    Returns the path to the captioned video.
    """
    from services.subtitle_service import AutoSubtitleService

    video_path = Path(req.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {req.video_path}")

    service = AutoSubtitleService()
    result = await service.process_video(video_path, style=req.style)

    if result.skipped:
        return TranscribeResponse(
            success=True,
            output_path=str(video_path),
            skipped=True,
            skip_reason=result.skip_reason,
            style=req.style,
        )

    if not result.success:
        return TranscribeResponse(success=False, error=result.error)

    return TranscribeResponse(
        success=True,
        output_path=str(result.output_path),
        transcript=result.transcription.text if result.transcription else None,
        word_count=len(result.transcription.words) if result.transcription else None,
        duration=result.transcription.duration if result.transcription else None,
        language=result.transcription.language if result.transcription else None,
        style=req.style,
    )


@router.post("/transcribe-only")
async def transcribe_only(req: TranscribeRequest):
    """
    Transcribe a video WITHOUT burning in captions.
    Returns just the transcript and word timings.
    """
    from services.subtitle_service import AutoSubtitleService

    video_path = Path(req.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {req.video_path}")

    service = AutoSubtitleService()
    transcription = await service.transcribe(video_path)

    if not transcription:
        raise HTTPException(status_code=500, detail="Transcription failed")

    return {
        "success": True,
        "text": transcription.text,
        "language": transcription.language,
        "duration": transcription.duration,
        "word_count": len(transcription.words),
        "words": [
            {"word": w.word, "start": w.start, "end": w.end}
            for w in transcription.words
        ],
    }


@router.get("/default-style")
async def get_default_style():
    """Get the current default subtitle style."""
    return {"default_style": os.getenv("DEFAULT_CAPTION_STYLE", "tiktok_bold")}

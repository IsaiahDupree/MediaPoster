"""
Caption/Subtitle Generation API
================================
Generate SRT and WebVTT captions from transcriptions.

Features:
- Generate SRT format captions
- Generate WebVTT format captions
- Configurable line length and duration
- Works with any transcription provider
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from loguru import logger

from services.transcription import TranscriptionService
from services.transcription_adapter import (
    TranscriptionAdapter,
    TranscriptionResult,
    generate_srt,
    generate_vtt
)


router = APIRouter(prefix="/api/captions", tags=["Captions"])


class TranscriptionInput(BaseModel):
    """Input for caption generation from existing transcription"""
    transcription: Dict[str, Any] = Field(..., description="Transcription result (from any provider)")
    provider: str = Field(default="openai", description="Provider that generated the transcription")


class CaptionGenerateRequest(BaseModel):
    """Request to generate captions from video"""
    video_path: str = Field(..., description="Path to video file")
    format: str = Field(default="srt", description="Caption format (srt or vtt)")
    max_chars_per_line: int = Field(default=42, description="Maximum characters per caption line")
    max_duration: float = Field(default=7.0, description="Maximum duration for a single caption (seconds)")


@router.post("/generate")
async def generate_captions_from_video(request: CaptionGenerateRequest):
    """
    Generate captions from video file

    This endpoint:
    1. Transcribes the video using Whisper
    2. Generates SRT or WebVTT captions

    Args:
        video_path: Path to video file
        format: Caption format (srt or vtt)
        max_chars_per_line: Maximum characters per line
        max_duration: Maximum caption duration

    Returns:
        Caption file content as text
    """
    try:
        # Validate format
        if request.format not in ["srt", "vtt"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {request.format}. Must be 'srt' or 'vtt'"
            )

        # Transcribe video
        logger.info(f"Transcribing video: {request.video_path}")
        transcription_service = TranscriptionService()

        if not transcription_service.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="Transcription service not configured (missing OpenAI API key)"
            )

        transcription_response = transcription_service.transcribe_video(
            request.video_path,
            response_format="verbose_json"
        )

        if "error" in transcription_response:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {transcription_response['error']}"
            )

        # Adapt transcription to unified format
        adapter = TranscriptionAdapter()
        transcription = adapter.adapt(transcription_response, provider="openai")

        # Generate captions
        if request.format == "srt":
            captions = generate_srt(
                transcription,
                max_chars_per_line=request.max_chars_per_line,
                max_duration=request.max_duration
            )
        else:  # vtt
            captions = generate_vtt(
                transcription,
                max_chars_per_line=request.max_chars_per_line,
                max_duration=request.max_duration
            )

        logger.info(f"Generated {request.format.upper()} captions for {request.video_path}")

        return PlainTextResponse(
            content=captions,
            media_type=f"text/{request.format}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating captions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/from-transcription")
async def generate_captions_from_transcription(
    request: TranscriptionInput,
    format: str = Query(default="srt", description="Caption format (srt or vtt)"),
    max_chars_per_line: int = Query(default=42, description="Maximum characters per line"),
    max_duration: float = Query(default=7.0, description="Maximum caption duration")
):
    """
    Generate captions from existing transcription data

    Use this endpoint if you already have transcription data and just need
    to convert it to SRT or WebVTT format.

    Args:
        request: Transcription data and provider
        format: Caption format (srt or vtt)
        max_chars_per_line: Maximum characters per line
        max_duration: Maximum caption duration

    Returns:
        Caption file content as text
    """
    try:
        # Validate format
        if format not in ["srt", "vtt"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {format}. Must be 'srt' or 'vtt'"
            )

        # Adapt transcription to unified format
        adapter = TranscriptionAdapter()
        transcription = adapter.adapt(request.transcription, provider=request.provider)

        # Generate captions
        if format == "srt":
            captions = generate_srt(
                transcription,
                max_chars_per_line=max_chars_per_line,
                max_duration=max_duration
            )
        else:  # vtt
            captions = generate_vtt(
                transcription,
                max_chars_per_line=max_chars_per_line,
                max_duration=max_duration
            )

        logger.info(f"Generated {format.upper()} captions from {request.provider} transcription")

        return PlainTextResponse(
            content=captions,
            media_type=f"text/{format}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating captions from transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_supported_formats():
    """
    Get list of supported caption formats

    Returns information about each format including:
    - File extension
    - MIME type
    - Common use cases
    """
    return {
        "success": True,
        "formats": {
            "srt": {
                "name": "SubRip",
                "extension": ".srt",
                "mime_type": "text/srt",
                "description": "Most widely supported subtitle format",
                "use_cases": ["YouTube", "Vimeo", "Local video players"]
            },
            "vtt": {
                "name": "WebVTT",
                "extension": ".vtt",
                "mime_type": "text/vtt",
                "description": "Web-native subtitle format with styling support",
                "use_cases": ["HTML5 video", "Web players", "Modern browsers"]
            }
        }
    }

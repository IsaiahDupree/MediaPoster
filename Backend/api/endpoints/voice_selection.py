"""
Voice Selection API (VC-007)
=============================
Backend API for voice selection UI component.

Endpoints:
- GET /api/voices - List available voices
- GET /api/voices/{voice_id} - Get voice details
- POST /api/voices/preview - Preview voice with sample text
- GET /api/voices/categories - Get voice categories
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from loguru import logger

from services.voice.modal_voice_service import get_modal_voice_service
from services.voice.voice_profile_service import VoiceProfileService
from database.connection import get_db_context


router = APIRouter(prefix="/api/voices", tags=["Voice Selection"])


class VoicePreviewRequest(BaseModel):
    """Request to preview a voice"""
    voice_reference_url: str = Field(..., description="Voice reference audio URL")
    sample_text: str = Field(
        default="Hello, this is a voice preview.",
        description="Text to synthesize for preview"
    )
    emotion: Optional[str] = Field(default="neutral", description="Emotion preset")


class VoiceInfo(BaseModel):
    """Voice information for selection UI"""
    voice_id: str
    name: str
    description: Optional[str] = None
    category: str = "custom"  # custom, celebrity, professional, etc.
    reference_url: str
    sample_audio_url: Optional[str] = None
    tags: List[str] = []
    language: str = "en"
    gender: Optional[str] = None
    age_range: Optional[str] = None
    accent: Optional[str] = None


@router.get("/")
async def list_voices(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List available voice options.

    Args:
        category: Filter by category (optional)
        limit: Max results
        offset: Pagination offset

    Returns:
        {
            "voices": [...],
            "total": 42,
            "categories": [...]
        }
    """
    try:
        # In production, this would query the voice_profiles table
        # For now, return example voices

        example_voices = [
            VoiceInfo(
                voice_id="voice_001",
                name="Professional Male",
                description="Clear, professional male voice",
                category="professional",
                reference_url="/voices/refs/prof_male.mp3",
                tags=["business", "corporate", "explainer"],
                gender="male",
                age_range="30-45"
            ),
            VoiceInfo(
                voice_id="voice_002",
                name="Friendly Female",
                description="Warm, friendly female voice",
                category="professional",
                reference_url="/voices/refs/friendly_female.mp3",
                tags=["welcoming", "tutorial", "educational"],
                gender="female",
                age_range="25-35"
            ),
            VoiceInfo(
                voice_id="voice_003",
                name="Energetic Host",
                description="High-energy presenter voice",
                category="entertainment",
                reference_url="/voices/refs/energetic.mp3",
                tags=["podcast", "youtube", "dynamic"],
                gender="male",
                age_range="20-30"
            )
        ]

        # Filter by category if specified
        if category:
            example_voices = [v for v in example_voices if v.category == category]

        # Pagination
        total = len(example_voices)
        voices = example_voices[offset:offset + limit]

        return {
            "voices": [v.model_dump() for v in voices],
            "total": total,
            "limit": limit,
            "offset": offset,
            "categories": ["professional", "entertainment", "custom"]
        }

    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_voice_categories() -> Dict[str, Any]:
    """
    Get available voice categories.

    Returns:
        {
            "categories": [
                {"id": "professional", "name": "Professional", "count": 12},
                ...
            ]
        }
    """
    return {
        "categories": [
            {"id": "professional", "name": "Professional", "count": 15},
            {"id": "entertainment", "name": "Entertainment", "count": 8},
            {"id": "educational", "name": "Educational", "count": 10},
            {"id": "custom", "name": "Custom Voices", "count": 5}
        ]
    }


@router.get("/{voice_id}")
async def get_voice_details(voice_id: str) -> VoiceInfo:
    """
    Get detailed information about a voice.

    Args:
        voice_id: Voice identifier

    Returns:
        VoiceInfo with full details
    """
    # In production, query from database
    # For now, return example

    example = VoiceInfo(
        voice_id=voice_id,
        name="Professional Male",
        description="Clear, professional male voice ideal for business content",
        category="professional",
        reference_url=f"/voices/refs/{voice_id}.mp3",
        sample_audio_url=f"/voices/samples/{voice_id}_sample.mp3",
        tags=["business", "corporate", "explainer"],
        language="en",
        gender="male",
        age_range="30-45",
        accent="neutral"
    )

    return example


@router.post("/preview")
async def preview_voice(request: VoicePreviewRequest) -> Dict[str, Any]:
    """
    Generate preview audio with a voice.

    Args:
        request: Preview request with voice ref and sample text

    Returns:
        {
            "audio_url": "...",
            "duration_seconds": 3.2,
            "text": "..."
        }
    """
    try:
        voice_service = get_modal_voice_service()

        if not voice_service.is_configured():
            # Return mock response for development
            return {
                "audio_url": f"/voices/previews/mock_preview.mp3",
                "duration_seconds": 2.5,
                "text": request.sample_text,
                "mock": True,
                "message": "Modal voice service not configured. This is a mock response."
            }

        # Set emotion if specified
        options = {}
        if request.emotion:
            options = voice_service.set_emotion({}, request.emotion, intensity=1.0)

        # Generate preview
        result = await voice_service.clone_voice(
            text=request.sample_text,
            voice_reference_url=request.voice_reference_url,
            options=options
        )

        return {
            "audio_url": result.get("audio_url"),
            "duration_seconds": result.get("duration_seconds"),
            "text": request.sample_text
        }

    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def get_voice_tags() -> Dict[str, Any]:
    """
    Get all available voice tags for filtering.

    Returns:
        {
            "tags": ["business", "casual", "energetic", ...]
        }
    """
    return {
        "tags": [
            "business",
            "casual",
            "energetic",
            "calm",
            "professional",
            "friendly",
            "authoritative",
            "youthful",
            "mature",
            "tutorial",
            "storytelling",
            "podcast",
            "explainer",
            "documentary",
            "commercial"
        ]
    }

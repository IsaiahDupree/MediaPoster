"""
Voice Cloning API
=================
API endpoints for voice cloning and TTS generation.

Features:
- VC-002: Voice Reference Management
- VC-003: Voice Clone API Client
- VC-006: Voice Generation
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from services.voice.voice_profile_service import VoiceProfileService
from services.voice.generation_service import VoiceGenerationService
from services.exceptions import ServiceError

router = APIRouter(prefix="/api/voice", tags=["Voice Cloning"])


# =====================================================
# Request/Response Models
# =====================================================

class CreateVoiceProfileRequest(BaseModel):
    """Request to create voice profile"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    reference_urls: Optional[List[str]] = None
    is_default: bool = False


class UpdateVoiceProfileRequest(BaseModel):
    """Request to update voice profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    default_speed: Optional[float] = Field(None, ge=0.5, le=2.0)
    default_emotion: Optional[str] = None
    is_default: Optional[bool] = None


class AddReferenceAudioRequest(BaseModel):
    """Request to add reference audio"""
    audio_url: str
    analyze_quality: bool = True


class GenerateAudioRequest(BaseModel):
    """Request to generate audio from text"""
    text: str = Field(..., min_length=1, max_length=5000)
    voice_profile_id: Optional[UUID] = None
    options: Optional[Dict[str, Any]] = None


class BatchGenerateRequest(BaseModel):
    """Request to generate batch audio"""
    texts: List[str] = Field(..., min_items=1, max_items=20)
    voice_profile_id: Optional[UUID] = None
    options: Optional[Dict[str, Any]] = None


class VoiceProfileResponse(BaseModel):
    """Voice profile response"""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    reference_urls: List[str]
    embedding_id: Optional[str]
    quality_score: Optional[float]
    default_speed: float
    default_emotion: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VoiceGenerationResponse(BaseModel):
    """Voice generation response"""
    id: UUID
    user_id: UUID
    voice_profile_id: Optional[UUID]
    input_text: str
    options: Dict[str, Any]
    output_url: Optional[str]
    duration_seconds: Optional[float]
    status: str
    processing_time_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# =====================================================
# Voice Profile Endpoints
# =====================================================

@router.post("/profiles", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_voice_profile(
    request: CreateVoiceProfileRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new voice profile.

    Requires:
    - name: Profile name
    - reference_urls: Optional list of reference audio URLs
    """
    # TODO: Get user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder

    try:
        service = VoiceProfileService(db)
        profile = await service.create_profile(
            user_id=user_id,
            name=request.name,
            description=request.description,
            reference_urls=request.reference_urls,
            is_default=request.is_default
        )

        return profile

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/profiles", response_model=List[VoiceProfileResponse])
async def list_voice_profiles(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all voice profiles for the current user.

    Query params:
    - active_only: Only return active profiles (default: true)
    """
    # TODO: Get user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        service = VoiceProfileService(db)
        profiles = await service.get_user_profiles(user_id, active_only=active_only)
        return profiles

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/profiles/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get voice profile by ID."""
    try:
        service = VoiceProfileService(db)
        profile = await service.get_profile(profile_id)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice profile {profile_id} not found"
            )

        return profile

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/profiles/{profile_id}", response_model=VoiceProfileResponse)
async def update_voice_profile(
    profile_id: UUID,
    request: UpdateVoiceProfileRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update voice profile."""
    try:
        service = VoiceProfileService(db)
        profile = await service.update_profile(
            profile_id=profile_id,
            name=request.name,
            description=request.description,
            default_speed=request.default_speed,
            default_emotion=request.default_emotion,
            is_default=request.is_default
        )

        return profile

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete voice profile."""
    try:
        service = VoiceProfileService(db)
        deleted = await service.delete_profile(profile_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice profile {profile_id} not found"
            )

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/profiles/{profile_id}/reference")
async def add_reference_audio(
    profile_id: UUID,
    request: AddReferenceAudioRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Add reference audio to voice profile.

    Optionally analyzes audio quality.
    """
    try:
        service = VoiceProfileService(db)
        result = await service.add_reference_audio(
            profile_id=profile_id,
            audio_url=request.audio_url,
            analyze_quality=request.analyze_quality
        )

        return result

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# =====================================================
# Voice Generation Endpoints
# =====================================================

@router.post("/generate", response_model=VoiceGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_audio(
    request: GenerateAudioRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate audio from text using voice cloning.

    Options:
    - speed: 0.5 to 2.0 (default: 1.0)
    - pitch: -50.0 to 50.0 (default: 0)
    - emotion: neutral, happy, serious, excited (default: neutral)
    - stability: 0.0 to 1.0 (default: 0.5)
    """
    # TODO: Get user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        service = VoiceGenerationService(db)
        generation = await service.generate_audio(
            user_id=user_id,
            text=request.text,
            voice_profile_id=request.voice_profile_id,
            options=request.options
        )

        return generation

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/generate/batch", response_model=List[VoiceGenerationResponse])
async def generate_batch_audio(
    request: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate multiple audio files in batch."""
    # TODO: Get user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        service = VoiceGenerationService(db)
        generations = await service.generate_batch(
            user_id=user_id,
            texts=request.texts,
            voice_profile_id=request.voice_profile_id,
            options=request.options
        )

        return generations

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/generate/{generation_id}", response_model=VoiceGenerationResponse)
async def get_generation(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get voice generation by ID."""
    try:
        service = VoiceGenerationService(db)
        generation = await service.get_generation(generation_id)

        if not generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generation {generation_id} not found"
            )

        return generation

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/history", response_model=List[VoiceGenerationResponse])
async def get_generation_history(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get voice generation history.

    Query params:
    - limit: Max results (default: 50)
    - offset: Pagination offset
    - status: Filter by status (pending, processing, completed, failed)
    """
    # TODO: Get user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        service = VoiceGenerationService(db)
        generations = await service.get_user_generations(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status
        )

        return generations

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/usage")
async def get_usage_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get voice generation usage statistics.

    Returns:
    - total_generations: Total number of generations
    - completed_count: Successfully completed
    - failed_count: Failed generations
    - total_audio_seconds: Total audio duration
    - total_cost_credits: Total cost
    """
    # TODO: Get user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    try:
        service = VoiceGenerationService(db)
        stats = await service.get_usage_stats(user_id)
        return stats

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

"""
Voice Cloning Quality Assessment API

Endpoints for assessing audio quality for voice cloning training data.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from loguru import logger
import tempfile
import os

from services.voice_cloning_quality_assessor import (
    VoiceCloningQualityAssessor,
    VoiceQualityMetrics
)

router = APIRouter()


class QualityAssessmentResponse(BaseModel):
    """Response model for quality assessment"""
    overall_score: float
    suitability_for_cloning: str
    snr_db: Optional[float] = None
    background_noise_level_db: Optional[float] = None
    speech_clarity_score: float
    mean_volume_db: Optional[float] = None
    volume_consistency: float
    silence_percentage: float
    speech_percentage: float
    duration_seconds: float
    transcript_length_words: int = 0
    words_per_minute: float = 0.0
    has_distortion: bool
    has_clipping: bool
    recommendations: list[str]
    issues: list[str]
    sample_rate_hz: Optional[int] = None
    bitrate_kbps: Optional[int] = None
    channels: int


@router.post("/assess", response_model=QualityAssessmentResponse)
async def assess_audio_quality(
    file: UploadFile = File(...),
    transcript: Optional[str] = Form(None)
):
    """
    Assess audio quality for voice cloning training data.
    
    Upload an audio or video file to get a comprehensive quality assessment.
    
    **Quality Metrics Assessed:**
    - Signal-to-Noise Ratio (SNR)
    - Background noise levels
    - Speech clarity and consistency
    - Frequency response in voice range
    - Volume consistency
    - Silence detection
    - Distortion and clipping
    - Transcript alignment (if provided)
    
    **Returns:**
    - Overall score (0.0 to 1.0)
    - Suitability rating (poor/fair/good/excellent)
    - Detailed metrics
    - Recommendations for improvement
    - Critical issues identified
    """
    try:
        # Save uploaded file to temp location
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / f"voice_assess_{file.filename}"
        
        logger.info(f"Assessing audio quality for: {file.filename}")
        
        # Write uploaded file
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Initialize assessor
        assessor = VoiceCloningQualityAssessor()
        
        # Assess quality
        metrics = assessor.assess_audio_quality(
            audio_path=temp_file,
            transcript=transcript
        )
        
        # Cleanup temp file
        try:
            temp_file.unlink()
        except:
            pass
        
        # Convert to response model
        return QualityAssessmentResponse(
            overall_score=metrics.overall_score,
            suitability_for_cloning=metrics.suitability_for_cloning,
            snr_db=metrics.snr_db,
            background_noise_level_db=metrics.background_noise_level_db,
            speech_clarity_score=metrics.speech_clarity_score,
            mean_volume_db=metrics.mean_volume_db,
            volume_consistency=metrics.volume_consistency,
            silence_percentage=metrics.silence_percentage,
            speech_percentage=metrics.speech_percentage,
            duration_seconds=metrics.duration_seconds,
            transcript_length_words=metrics.transcript_length_words,
            words_per_minute=metrics.words_per_minute,
            has_distortion=metrics.has_distortion,
            has_clipping=metrics.has_clipping,
            recommendations=metrics.recommendations,
            issues=metrics.issues,
            sample_rate_hz=metrics.sample_rate_hz,
            bitrate_kbps=metrics.bitrate_kbps,
            channels=metrics.channels
        )
        
    except Exception as e:
        logger.error(f"Quality assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assess audio quality: {str(e)}"
        )


@router.post("/assess-batch")
async def assess_batch_quality(
    files: list[UploadFile] = File(...),
    transcript: Optional[str] = Form(None)
):
    """
    Assess quality of multiple audio files for voice cloning.
    
    Useful for evaluating a collection of training samples.
    
    Returns a list of assessments with summary statistics.
    """
    try:
        assessor = VoiceCloningQualityAssessor()
        assessments = []
        temp_files = []
        
        for file in files:
            try:
                # Save to temp
                temp_dir = Path(tempfile.gettempdir())
                temp_file = temp_dir / f"voice_assess_{file.filename}"
                temp_files.append(temp_file)
                
                with open(temp_file, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                # Assess
                metrics = assessor.assess_audio_quality(
                    audio_path=temp_file,
                    transcript=transcript
                )
                
                assessments.append({
                    "filename": file.filename,
                    "overall_score": metrics.overall_score,
                    "suitability": metrics.suitability_for_cloning,
                    "duration_seconds": metrics.duration_seconds,
                    "snr_db": metrics.snr_db,
                    "issues": metrics.issues,
                    "recommendations": metrics.recommendations
                })
                
            except Exception as e:
                logger.error(f"Failed to assess {file.filename}: {e}")
                assessments.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        # Cleanup
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass
        
        # Calculate summary statistics
        valid_assessments = [a for a in assessments if "error" not in a]
        if valid_assessments:
            avg_score = sum(a["overall_score"] for a in valid_assessments) / len(valid_assessments)
            total_duration = sum(a["duration_seconds"] for a in valid_assessments)
            
            summary = {
                "total_files": len(assessments),
                "valid_files": len(valid_assessments),
                "average_score": avg_score,
                "total_duration_seconds": total_duration,
                "total_duration_minutes": total_duration / 60.0
            }
        else:
            summary = {
                "total_files": len(assessments),
                "valid_files": 0
            }
        
        return {
            "summary": summary,
            "assessments": assessments
        }
        
    except Exception as e:
        logger.error(f"Batch assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assess batch: {str(e)}"
        )


@router.get("/requirements")
async def get_quality_requirements():
    """
    Get quality requirements and thresholds for voice cloning training data.
    
    Returns the criteria used for assessment.
    """
    return {
        "minimum_requirements": {
            "duration_seconds": 30.0,
            "recommended_duration_seconds": 300.0,
            "ideal_duration_seconds": 1800.0,
            "min_snr_db": 20.0,
            "excellent_snr_db": 35.0,
            "max_silence_percentage": 20.0,
            "max_background_noise_db": -30.0,
            "min_words_per_minute": 100,
            "max_words_per_minute": 200
        },
        "audio_specs": {
            "recommended_sample_rate_hz": 22050,
            "minimum_sample_rate_hz": 16000,
            "preferred_channels": 1,
            "voice_fundamental_range_hz": {
                "min": 85,
                "max": 255
            },
            "voice_harmonics_max_hz": 8000
        },
        "quality_thresholds": {
            "excellent": 0.8,
            "good": 0.65,
            "fair": 0.5,
            "poor": 0.0
        },
        "recommendations": [
            "Record in a quiet environment with minimal background noise",
            "Use a high-quality microphone",
            "Maintain consistent distance from microphone",
            "Avoid clipping and distortion",
            "Record at least 5 minutes of speech for good results",
            "Use mono audio channel",
            "Sample rate should be at least 22.05 kHz",
            "Minimize silence and pauses",
            "Ensure transcript accurately matches audio"
        ]
    }


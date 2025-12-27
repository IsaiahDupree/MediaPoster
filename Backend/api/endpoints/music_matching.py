"""
Music Matching API Endpoints
Automatic background music suggestion and matching for video content.
Part of Auto Music Matching feature (Phase 1)
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import os
from pathlib import Path

from database.connection import get_db
from services.music_selector import MusicSelector, MusicMatch, MusicTrack

router = APIRouter(prefix="/api/music", tags=["Music Matching"])


class MusicSuggestionRequest(BaseModel):
    """Request for music suggestion"""
    refresh: bool = False  # Force re-calculation
    top_n: int = 5  # Number of alternatives


class MusicSuggestionResponse(BaseModel):
    """Response with music suggestion"""
    success: bool
    media_id: str
    suggested_music: Optional[Dict[str, Any]] = None
    alternatives: List[Dict[str, Any]] = []
    analysis_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ShuffleResponse(BaseModel):
    """Response for shuffle request"""
    success: bool
    media_id: str
    new_suggestion: Optional[Dict[str, Any]] = None
    remaining_alternatives: int = 0
    error: Optional[str] = None


# Global music selector instance
_music_selector: Optional[MusicSelector] = None

def get_music_selector() -> MusicSelector:
    """Get singleton MusicSelector instance"""
    global _music_selector
    if _music_selector is None:
        _music_selector = MusicSelector()
        _music_selector.load_music_library()
    return _music_selector


@router.get("/health")
async def health_check():
    """Health check for music matching service"""
    selector = get_music_selector()
    library = selector.load_music_library()
    return {
        "status": "healthy",
        "service": "music_matching",
        "library_tracks": len(library)
    }


@router.get("/library")
async def list_music_library():
    """List all available music tracks in library"""
    selector = get_music_selector()
    library = selector.load_music_library()
    return {
        "success": True,
        "total_tracks": len(library),
        "tracks": [track.to_dict() for track in library]
    }


@router.post("/suggest/{media_id}")
async def suggest_music(
    media_id: str,
    request: MusicSuggestionRequest = MusicSuggestionRequest(),
    db: AsyncSession = Depends(get_db)
) -> MusicSuggestionResponse:
    """
    Suggest best matching background music for a video.
    
    Returns top match with alternatives and reasoning.
    Results are cached in video_analysis table.
    """
    logger.info(f"[MusicMatching] Suggesting music for media_id: {media_id}")
    
    # Check if we have cached suggestion (unless refresh requested)
    if not request.refresh:
        try:
            result = await db.execute(text("""
                SELECT suggested_music_id, music_match_score, music_match_reasoning, 
                       music_alternatives, music_matched_at
                FROM video_analysis 
                WHERE video_id = :media_id::uuid
                  AND suggested_music_id IS NOT NULL
            """), {"media_id": media_id})
            cached = result.fetchone()
            
            if cached and cached[0]:
                logger.info(f"[MusicMatching] Returning cached suggestion: {cached[0]}")
                selector = get_music_selector()
                library = selector.load_music_library()
                
                # Find the track details
                track = next((t for t in library if t.id == cached[0]), None)
                
                return MusicSuggestionResponse(
                    success=True,
                    media_id=media_id,
                    suggested_music={
                        "music_id": cached[0],
                        "title": track.file_name if track else cached[0],
                        "duration": track.duration if track else 0,
                        "preview_url": f"/api/music/preview/{cached[0]}",
                        "match_score": float(cached[1]) if cached[1] else 0,
                        "reasoning": cached[2] or ""
                    } if track else None,
                    alternatives=cached[3] or [],
                    analysis_summary={"cached": True, "matched_at": str(cached[4])}
                )
        except Exception as e:
            logger.warning(f"[MusicMatching] Cache check failed: {e}")
    
    # Fetch video analysis data
    try:
        result = await db.execute(text("""
            SELECT va.transcript, va.topics, va.tone, va.deep_analysis,
                   v.duration_sec, v.file_name
            FROM video_analysis va
            JOIN videos v ON v.id = va.video_id
            WHERE va.video_id = :media_id::uuid
        """), {"media_id": media_id})
        row = result.fetchone()
        
        if not row:
            # Try just videos table
            result = await db.execute(text("""
                SELECT duration_sec, file_name FROM videos WHERE id = :media_id::uuid
            """), {"media_id": media_id})
            video_row = result.fetchone()
            
            if not video_row:
                raise HTTPException(status_code=404, detail=f"Video not found: {media_id}")
            
            # Use defaults for unanalyzed video
            transcript = ""
            topics = []
            tone = "neutral"
            duration = video_row[0] or 30
        else:
            transcript = row[0] or ""
            topics = row[1] or []
            tone = row[2] or "neutral"
            deep_analysis = row[3] or {}
            duration = row[4] or 30
            
            # Extract additional context from deep_analysis
            if isinstance(deep_analysis, dict):
                if not topics and deep_analysis.get("topics"):
                    topics = deep_analysis["topics"]
                if not tone and deep_analysis.get("tone"):
                    tone = deep_analysis["tone"]
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MusicMatching] Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Get music suggestions
    selector = get_music_selector()
    
    try:
        matches = await selector.select_music_for_clip(
            duration=duration,
            transcript=transcript,
            topics=topics,
            top_n=request.top_n
        )
        
        if not matches:
            return MusicSuggestionResponse(
                success=True,
                media_id=media_id,
                suggested_music=None,
                alternatives=[],
                error="No compatible music found in library"
            )
        
        # Best match
        best_match = matches[0]
        
        # Alternatives (excluding best)
        alternatives = [
            {
                "music_id": m.track.id,
                "title": m.track.file_name,
                "score": round(m.compatibility_score, 2),
                "reasoning": m.reasoning
            }
            for m in matches[1:]
        ]
        
        # Store in database
        try:
            await db.execute(text("""
                UPDATE video_analysis SET
                    suggested_music_id = :music_id,
                    music_match_score = :score,
                    music_match_reasoning = :reasoning,
                    music_alternatives = :alternatives,
                    music_matched_at = NOW()
                WHERE video_id = :media_id::uuid
            """), {
                "media_id": media_id,
                "music_id": best_match.track.id,
                "score": best_match.compatibility_score,
                "reasoning": best_match.reasoning,
                "alternatives": json.dumps(alternatives)
            })
            await db.commit()
            logger.info(f"[MusicMatching] Stored suggestion: {best_match.track.id}")
        except Exception as e:
            logger.warning(f"[MusicMatching] Failed to cache: {e}")
        
        # Get clip analysis for summary
        analysis = await selector.analyze_clip(
            duration=duration,
            transcript=transcript,
            topics=topics
        )
        
        return MusicSuggestionResponse(
            success=True,
            media_id=media_id,
            suggested_music={
                "music_id": best_match.track.id,
                "title": best_match.track.file_name,
                "artist": "MediaPoster Library",
                "duration": best_match.track.duration,
                "genre": best_match.track.genre,
                "tempo": best_match.track.tempo,
                "energy_level": best_match.track.energy_level,
                "preview_url": f"/api/music/preview/{best_match.track.id}",
                "match_score": round(best_match.compatibility_score, 2),
                "reasoning": best_match.reasoning
            },
            alternatives=alternatives,
            analysis_summary={
                "detected_mood": analysis.mood,
                "energy_level": round(analysis.energy_level, 2),
                "content_type": analysis.content_type,
                "topics": analysis.topics[:5] if analysis.topics else [],
                "video_duration": duration
            }
        )
        
    except ValueError as e:
        logger.error(f"[MusicMatching] Validation error: {e}")
        return MusicSuggestionResponse(
            success=False,
            media_id=media_id,
            error=str(e)
        )
    except Exception as e:
        logger.error(f"[MusicMatching] Music selection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shuffle/{media_id}")
async def shuffle_music(
    media_id: str,
    exclude_ids: List[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db)
) -> ShuffleResponse:
    """
    Get next best music alternative, excluding already seen tracks.
    """
    logger.info(f"[MusicMatching] Shuffle for media_id: {media_id}, excluding: {exclude_ids}")
    
    # Get current alternatives from cache
    try:
        result = await db.execute(text("""
            SELECT music_alternatives, suggested_music_id
            FROM video_analysis 
            WHERE video_id = :media_id::uuid
        """), {"media_id": media_id})
        row = result.fetchone()
        
        if not row or not row[0]:
            # No cached alternatives, generate fresh
            response = await suggest_music(
                media_id, 
                MusicSuggestionRequest(refresh=True, top_n=10),
                db
            )
            if response.alternatives:
                return ShuffleResponse(
                    success=True,
                    media_id=media_id,
                    new_suggestion=response.alternatives[0] if response.alternatives else None,
                    remaining_alternatives=len(response.alternatives) - 1
                )
            return ShuffleResponse(
                success=False,
                media_id=media_id,
                error="No alternatives available"
            )
        
        alternatives = row[0]
        current_id = row[1]
        
        # Add current to exclude list
        all_excluded = set(exclude_ids)
        if current_id:
            all_excluded.add(current_id)
        
        # Find next available alternative
        available = [a for a in alternatives if a.get("music_id") not in all_excluded]
        
        if not available:
            return ShuffleResponse(
                success=True,
                media_id=media_id,
                new_suggestion=None,
                remaining_alternatives=0,
                error="No more alternatives available"
            )
        
        # Get best available
        next_music = available[0]
        
        # Update the suggested music to the shuffled one
        await db.execute(text("""
            UPDATE video_analysis SET
                suggested_music_id = :music_id,
                music_match_score = :score,
                music_match_reasoning = :reasoning,
                music_matched_at = NOW()
            WHERE video_id = :media_id::uuid
        """), {
            "media_id": media_id,
            "music_id": next_music["music_id"],
            "score": next_music.get("score", 0),
            "reasoning": next_music.get("reasoning", "")
        })
        await db.commit()
        
        # Get full track details
        selector = get_music_selector()
        library = selector.load_music_library()
        track = next((t for t in library if t.id == next_music["music_id"]), None)
        
        return ShuffleResponse(
            success=True,
            media_id=media_id,
            new_suggestion={
                "music_id": next_music["music_id"],
                "title": track.file_name if track else next_music["music_id"],
                "duration": track.duration if track else 0,
                "genre": track.genre if track else "unknown",
                "preview_url": f"/api/music/preview/{next_music['music_id']}",
                "match_score": next_music.get("score", 0),
                "reasoning": next_music.get("reasoning", "")
            },
            remaining_alternatives=len(available) - 1
        )
        
    except Exception as e:
        logger.error(f"[MusicMatching] Shuffle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{music_id}")
async def preview_music(music_id: str):
    """
    Stream audio preview of a music track.
    """
    selector = get_music_selector()
    library = selector.load_music_library()
    
    track = next((t for t in library if t.id == music_id), None)
    if not track:
        raise HTTPException(status_code=404, detail=f"Music track not found: {music_id}")
    
    # Check if file exists
    file_path = Path(track.file_path)
    if not file_path.exists():
        # Try relative to music library
        music_dir = Path(os.getenv("MUSIC_LIBRARY_PATH", "./music"))
        file_path = music_dir / track.file_name
        
        if not file_path.exists():
            # Return placeholder response for demo tracks
            raise HTTPException(
                status_code=404, 
                detail=f"Music file not found. Track '{music_id}' is a demo placeholder."
            )
    
    def iterfile():
        with open(file_path, "rb") as f:
            yield from f
    
    return StreamingResponse(
        iterfile(),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={track.file_name}",
            "Accept-Ranges": "bytes"
        }
    )


@router.get("/track/{music_id}")
async def get_track_details(music_id: str):
    """Get details of a specific music track"""
    selector = get_music_selector()
    library = selector.load_music_library()
    
    track = next((t for t in library if t.id == music_id), None)
    if not track:
        raise HTTPException(status_code=404, detail=f"Music track not found: {music_id}")
    
    return {
        "success": True,
        "track": track.to_dict()
    }


@router.delete("/suggestion/{media_id}")
async def clear_music_suggestion(
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Clear music suggestion for a video (user chose no music)"""
    try:
        await db.execute(text("""
            UPDATE video_analysis SET
                suggested_music_id = NULL,
                music_match_score = NULL,
                music_match_reasoning = NULL,
                music_alternatives = NULL,
                music_matched_at = NULL
            WHERE video_id = :media_id::uuid
        """), {"media_id": media_id})
        await db.commit()
        
        return {"success": True, "media_id": media_id, "message": "Music suggestion cleared"}
    except Exception as e:
        logger.error(f"[MusicMatching] Clear failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

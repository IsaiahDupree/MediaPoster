"""
Music Library API Endpoints (MUSIC-001)
========================================
REST API for managing music tracks in the library.

Endpoints:
- POST /api/music/import - Import a music track
- GET /api/music/search - Search tracks with filters
- GET /api/music/{track_id} - Get track by ID
- GET /api/music/trending - Get trending tracks
- POST /api/music/{track_id}/use - Record track usage
- GET /api/music/stats - Library statistics
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from uuid import UUID
from loguru import logger

from services.music_library import get_music_library


router = APIRouter(prefix="/api/music", tags=["Music Library"])


# =====================================================
# REQUEST/RESPONSE MODELS
# =====================================================

class ImportTrackRequest(BaseModel):
    """Request to import a music track"""
    workspace_id: UUID
    file_path: str
    title: str
    source: str = Field(..., description="suno, soundcloud, social_platform, or local")
    duration_seconds: float

    # Optional metadata
    artist: Optional[str] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None

    # Audio properties
    sample_rate: Optional[int] = None
    bitrate: Optional[int] = None
    channels: int = 2
    file_format: Optional[str] = None

    # Musical metadata
    tempo_bpm: Optional[float] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None
    genre: Optional[str] = None
    subgenre: Optional[str] = None

    # Mood & Energy
    mood: Optional[str] = None
    energy_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    valence: Optional[float] = Field(None, ge=0.0, le=1.0)
    danceability: Optional[float] = Field(None, ge=0.0, le=1.0)
    instrumentalness: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Tags
    tags: Optional[List[str]] = None
    moods: Optional[List[str]] = None
    use_cases: Optional[List[str]] = None
    suitable_for_content_types: Optional[List[str]] = None
    recommended_video_pacing: Optional[str] = None

    # Licensing
    license_type: Optional[str] = None
    attribution_required: bool = False
    commercial_use_allowed: bool = True
    license_url: Optional[str] = None

    # Platform metadata
    platform: Optional[str] = None
    platform_popularity: Optional[int] = None
    is_trending: bool = False
    trending_rank: Optional[int] = None

    # Import metadata
    imported_from: Optional[str] = None
    import_batch_id: Optional[UUID] = None
    skip_duplicate_check: bool = False


class SearchTracksRequest(BaseModel):
    """Request to search music tracks"""
    workspace_id: UUID

    # Search filters
    mood: Optional[str] = None
    genre: Optional[str] = None
    source: Optional[str] = None
    platform: Optional[str] = None
    is_trending: Optional[bool] = None

    # Range filters
    tempo_min: Optional[float] = None
    tempo_max: Optional[float] = None
    energy_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    energy_max: Optional[float] = Field(None, ge=0.0, le=1.0)
    duration_min: Optional[float] = None
    duration_max: Optional[float] = None

    # Tag filters
    tags: Optional[List[str]] = None
    content_type: Optional[str] = None

    # Licensing
    commercial_use_only: bool = False
    attribution_not_required: bool = False

    # Quality
    min_quality_rating: Optional[float] = None
    is_curated_only: bool = False

    # Pagination
    limit: int = Field(50, le=200)
    offset: int = 0

    # Sorting
    sort_by: str = "created_at"
    sort_desc: bool = True


# =====================================================
# ENDPOINTS
# =====================================================

@router.post("/import")
async def import_track(request: ImportTrackRequest):
    """
    Import a music track into the library

    Features:
    - Auto-deduplication via checksum
    - Rich metadata support
    - Trending music tracking
    - Licensing information

    Returns:
        Track ID (existing if duplicate, new otherwise)
    """
    try:
        library = get_music_library()

        # Convert tempo range to tuple
        tempo_range = None
        if request.tempo_min is not None and request.tempo_max is not None:
            tempo_range = (request.tempo_min, request.tempo_max)

        track_id = await library.import_track(
            workspace_id=request.workspace_id,
            file_path=request.file_path,
            title=request.title,
            source=request.source,
            duration_seconds=request.duration_seconds,
            artist=request.artist,
            source_id=request.source_id,
            source_url=request.source_url,
            # Audio properties
            sample_rate=request.sample_rate,
            bitrate=request.bitrate,
            channels=request.channels,
            file_format=request.file_format,
            # Musical metadata
            tempo_bpm=request.tempo_bpm,
            key=request.key,
            time_signature=request.time_signature,
            genre=request.genre,
            subgenre=request.subgenre,
            # Mood & Energy
            mood=request.mood,
            energy_level=request.energy_level,
            valence=request.valence,
            danceability=request.danceability,
            instrumentalness=request.instrumentalness,
            # Tags
            tags=request.tags,
            moods=request.moods,
            use_cases=request.use_cases,
            suitable_for_content_types=request.suitable_for_content_types,
            recommended_video_pacing=request.recommended_video_pacing,
            # Licensing
            license_type=request.license_type,
            attribution_required=request.attribution_required,
            commercial_use_allowed=request.commercial_use_allowed,
            license_url=request.license_url,
            # Platform
            platform=request.platform,
            platform_popularity=request.platform_popularity,
            is_trending=request.is_trending,
            trending_rank=request.trending_rank,
            # Import
            imported_from=request.imported_from,
            import_batch_id=request.import_batch_id,
            skip_duplicate_check=request.skip_duplicate_check
        )

        return {
            "success": True,
            "track_id": str(track_id),
            "message": "Track imported successfully"
        }

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing track: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_tracks(
    workspace_id: UUID = Query(...),
    mood: Optional[str] = None,
    genre: Optional[str] = None,
    source: Optional[str] = None,
    platform: Optional[str] = None,
    is_trending: Optional[bool] = None,
    tempo_min: Optional[float] = None,
    tempo_max: Optional[float] = None,
    energy_min: Optional[float] = Query(None, ge=0.0, le=1.0),
    energy_max: Optional[float] = Query(None, ge=0.0, le=1.0),
    duration_min: Optional[float] = None,
    duration_max: Optional[float] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    content_type: Optional[str] = None,
    commercial_use_only: bool = False,
    attribution_not_required: bool = False,
    min_quality_rating: Optional[float] = None,
    is_curated_only: bool = False,
    limit: int = Query(50, le=200),
    offset: int = 0,
    sort_by: str = "created_at",
    sort_desc: bool = True
):
    """
    Search music tracks with filters

    Filters:
    - Mood, genre, source, platform
    - Tempo range (BPM)
    - Energy level range
    - Duration range
    - Tags (AND logic)
    - Content type suitability
    - Licensing requirements
    - Quality rating

    Sorting:
    - created_at, title, tempo_bpm, energy_level, times_used, trending_rank
    """
    try:
        library = get_music_library()

        # Parse tags
        tags_list = None
        if tags:
            tags_list = [t.strip() for t in tags.split(",")]

        # Parse tempo range
        tempo_range = None
        if tempo_min is not None and tempo_max is not None:
            tempo_range = (tempo_min, tempo_max)

        tracks = await library.search_tracks(
            workspace_id=workspace_id,
            mood=mood,
            genre=genre,
            source=source,
            platform=platform,
            is_trending=is_trending,
            tempo_range=tempo_range,
            energy_min=energy_min,
            energy_max=energy_max,
            duration_min=duration_min,
            duration_max=duration_max,
            tags=tags_list,
            content_type=content_type,
            commercial_use_only=commercial_use_only,
            attribution_not_required=attribution_not_required,
            min_quality_rating=min_quality_rating,
            is_curated_only=is_curated_only,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc
        )

        return {
            "success": True,
            "count": len(tracks),
            "tracks": tracks,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(tracks) == limit
            }
        }

    except Exception as e:
        logger.error(f"Error searching tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{track_id}")
async def get_track(track_id: UUID):
    """Get a specific track by ID"""
    try:
        library = get_music_library()
        track = await library.get_track_by_id(track_id)

        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        return {
            "success": True,
            "track": track
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting track: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending/list")
async def get_trending_tracks(
    workspace_id: UUID = Query(...),
    platform: Optional[str] = None,
    limit: int = Query(20, le=100)
):
    """
    Get trending music tracks

    Args:
        workspace_id: Workspace ID
        platform: Filter by platform (tiktok, instagram, youtube, etc.)
        limit: Max results

    Returns:
        List of trending tracks sorted by trending_rank
    """
    try:
        library = get_music_library()
        tracks = await library.get_trending_tracks(
            workspace_id=workspace_id,
            platform=platform,
            limit=limit
        )

        return {
            "success": True,
            "count": len(tracks),
            "tracks": tracks,
            "platform": platform
        }

    except Exception as e:
        logger.error(f"Error getting trending tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{track_id}/use")
async def record_track_usage(track_id: UUID):
    """
    Record that a track was used

    Increments times_used counter and updates last_used_at timestamp.
    """
    try:
        library = get_music_library()
        await library.record_usage(track_id)

        return {
            "success": True,
            "message": "Usage recorded"
        }

    except Exception as e:
        logger.error(f"Error recording usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_library_stats(workspace_id: UUID = Query(...)):
    """
    Get music library statistics

    Returns:
    - Total tracks
    - Breakdown by source
    - Breakdown by mood
    - Breakdown by genre
    - Trending count
    - Most used tracks
    """
    try:
        library = get_music_library()

        # Get all tracks
        all_tracks = await library.search_tracks(
            workspace_id=workspace_id,
            limit=10000  # Get all
        )

        # Calculate stats
        total_tracks = len(all_tracks)

        # Source breakdown
        sources = {}
        moods = {}
        genres = {}
        trending_count = 0

        for track in all_tracks:
            # Source
            source = track.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

            # Mood
            mood = track.get("mood")
            if mood:
                moods[mood] = moods.get(mood, 0) + 1

            # Genre
            genre = track.get("genre")
            if genre:
                genres[genre] = genres.get(genre, 0) + 1

            # Trending
            if track.get("is_trending"):
                trending_count += 1

        # Most used
        most_used = sorted(all_tracks, key=lambda t: t.get("times_used", 0), reverse=True)[:10]

        return {
            "success": True,
            "stats": {
                "total_tracks": total_tracks,
                "trending_count": trending_count,
                "sources": sources,
                "top_moods": dict(sorted(moods.items(), key=lambda x: x[1], reverse=True)[:10]),
                "top_genres": dict(sorted(genres.items(), key=lambda x: x[1], reverse=True)[:10]),
                "most_used_tracks": [
                    {
                        "id": t["id"],
                        "title": t["title"],
                        "artist": t.get("artist"),
                        "times_used": t.get("times_used", 0)
                    }
                    for t in most_used
                ]
            }
        }

    except Exception as e:
        logger.error(f"Error getting library stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# MUSIC MATCHING & SUGGESTIONS (MUSIC-002, MUSIC-003)
# =====================================================

from services.music_matcher import get_music_matcher


class MatchMusicRequest(BaseModel):
    """Request to match music to video content"""
    workspace_id: UUID
    video_duration: float = Field(..., description="Video duration in seconds")
    video_mood: Optional[str] = Field(None, description="Video mood (energetic, calm, dramatic, etc.)")
    video_energy: Optional[float] = Field(None, ge=0.0, le=1.0, description="Video energy level")
    video_pacing: Optional[str] = Field(None, description="Video pacing (slow, medium, fast)")
    content_type: Optional[str] = Field(None, description="Content type (shorts, reels, explainer)")
    genre_preference: Optional[str] = None
    exclude_tracks: Optional[List[UUID]] = None
    limit: int = Field(10, ge=1, le=50)


@router.post("/match")
async def match_music_to_video(request: MatchMusicRequest):
    """
    Match music to video content (MUSIC-002)

    Analyzes video characteristics and returns ranked music matches
    from the library based on mood, energy, pacing, and other factors.

    **Example:**
    ```json
    {
      "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
      "video_duration": 45.0,
      "video_mood": "energetic",
      "video_energy": 0.8,
      "video_pacing": "fast",
      "content_type": "shorts",
      "limit": 10
    }
    ```

    **Response includes:**
    - Ranked list of compatible tracks
    - Compatibility scores (0.0-1.0)
    - Score breakdown for transparency
    """
    try:
        matcher = get_music_matcher()

        matches = await matcher.match_music_to_video(
            workspace_id=request.workspace_id,
            video_duration=request.video_duration,
            video_mood=request.video_mood,
            video_energy=request.video_energy,
            video_pacing=request.video_pacing,
            content_type=request.content_type,
            genre_preference=request.genre_preference,
            exclude_tracks=request.exclude_tracks,
            limit=request.limit
        )

        return {
            "success": True,
            "matches": matches,
            "total_matches": len(matches)
        }

    except Exception as e:
        logger.error(f"Error matching music: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest/{track_id}")
async def suggest_alternative_tracks(
    track_id: UUID,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    limit: int = Query(5, ge=1, le=20, description="Max alternatives to return")
):
    """
    Suggest alternative tracks (MUSIC-003)

    GET /api/music/suggest/{track_id}?workspace_id=xxx&limit=5

    Finds tracks similar to the specified track based on:
    - Mood compatibility
    - Energy level
    - Tempo/pacing
    - Genre
    - Duration

    **Use cases:**
    - User wants alternatives to current background music
    - A/B testing different music options
    - Avoiding repetition across videos
    """
    try:
        matcher = get_music_matcher()

        alternatives = await matcher.suggest_alternatives(
            workspace_id=workspace_id,
            current_track_id=track_id,
            limit=limit
        )

        return {
            "success": True,
            "current_track_id": str(track_id),
            "alternatives": alternatives,
            "total_alternatives": len(alternatives)
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error suggesting alternatives: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

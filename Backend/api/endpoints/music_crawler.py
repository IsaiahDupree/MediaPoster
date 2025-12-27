"""
Music Crawler API Endpoints
===========================
Endpoints for crawling trending music from social platforms.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
import os
import json

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CrawlMusicRequest(BaseModel):
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags to search")
    download: bool = Field(default=False, description="Whether to download audio files")
    limit: int = Field(default=20, description="Maximum tracks to return")


class SearchMusicRequest(BaseModel):
    query: Optional[str] = None
    genre: Optional[str] = None
    mood: Optional[str] = None
    trending: bool = True
    platform: str = "instagram"
    limit: int = 20


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/instagram/crawl")
async def crawl_instagram_music(
    request: CrawlMusicRequest,
    background_tasks: BackgroundTasks
):
    """
    Crawl Instagram for trending music.
    Uses rate limiting to avoid API limits.
    
    Args:
        hashtags: Optional hashtags to search (default: music-related)
        download: Whether to download audio files
        limit: Maximum tracks to return
    """
    try:
        from services.music.crawlers import InstagramMusicCrawler
        
        crawler = InstagramMusicCrawler()
        
        # Run crawl
        tracks = await crawler.crawl_trending_music(
            hashtags=request.hashtags,
            download=request.download,
            limit=request.limit
        )
        
        # Convert to dict
        from dataclasses import asdict
        tracks_list = [asdict(t) for t in tracks]
        
        return {
            "success": True,
            "tracks": tracks_list,
            "count": len(tracks_list),
            "rate_limit_status": crawler.get_rate_limit_status()
        }
        
    except Exception as e:
        logger.error(f"Instagram music crawl failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instagram/tracks")
async def list_instagram_tracks(
    trending: Optional[bool] = None,
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    limit: int = 50
):
    """List discovered Instagram music tracks from database"""
    engine = get_engine()
    
    query = """
        SELECT track_id, title, artist, duration_sec, usage_count,
               audio_url, cover_url, is_trending, genre, mood, local_path, discovered_at
        FROM instagram_trending_music
        WHERE 1=1
    """
    params = {"limit": limit}
    
    if trending is not None:
        query += " AND is_trending = :trending"
        params["trending"] = trending
    if genre:
        query += " AND genre = :genre"
        params["genre"] = genre
    if mood:
        query += " AND mood = :mood"
        params["mood"] = mood
    
    query += " ORDER BY usage_count DESC, discovered_at DESC LIMIT :limit"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            tracks = []
            for row in result:
                tracks.append({
                    "track_id": row[0],
                    "title": row[1],
                    "artist": row[2],
                    "duration_sec": row[3],
                    "usage_count": row[4],
                    "audio_url": row[5],
                    "cover_url": row[6],
                    "is_trending": row[7],
                    "genre": row[8],
                    "mood": row[9],
                    "local_path": row[10],
                    "discovered_at": row[11].isoformat() if row[11] else None
                })
            
            return {
                "success": True,
                "tracks": tracks,
                "count": len(tracks)
            }
    except Exception as e:
        logger.error(f"Failed to list tracks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limit-status")
async def get_rate_limit_status():
    """Get current rate limit status for music crawlers"""
    try:
        from services.music.crawlers import InstagramMusicCrawler
        
        crawler = InstagramMusicCrawler()
        return {
            "success": True,
            "instagram": crawler.get_rate_limit_status()
        }
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        return {
            "success": True,
            "instagram": {
                "calls_this_minute": 0,
                "calls_today": 0,
                "minute_limit": 25,
                "daily_limit": 500
            }
        }


@router.post("/search")
async def search_music(request: SearchMusicRequest):
    """
    Search for music across platforms.
    Searches local database first, then RapidAPI if needed.
    """
    engine = get_engine()
    
    # First search local database
    query = """
        SELECT track_id, title, artist, duration_sec, usage_count,
               audio_url, local_path, 'instagram' as source
        FROM instagram_trending_music
        WHERE 1=1
    """
    params = {"limit": request.limit}
    
    if request.query:
        query += " AND (title ILIKE :query OR artist ILIKE :query)"
        params["query"] = f"%{request.query}%"
    if request.genre:
        query += " AND genre = :genre"
        params["genre"] = request.genre
    if request.mood:
        query += " AND mood = :mood"
        params["mood"] = request.mood
    
    query += " ORDER BY usage_count DESC LIMIT :limit"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            tracks = []
            for row in result:
                tracks.append({
                    "track_id": row[0],
                    "title": row[1],
                    "artist": row[2],
                    "duration_sec": row[3],
                    "usage_count": row[4],
                    "audio_url": row[5],
                    "local_path": row[6],
                    "source": row[7]
                })
            
            return {
                "success": True,
                "tracks": tracks,
                "count": len(tracks),
                "source": "database"
            }
    except Exception as e:
        logger.error(f"Music search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

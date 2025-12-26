"""
Trends & Analytics API Endpoints
================================
Standalone system for tracking external trends from social media and app stores.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
import logging

from database.connection import get_supabase
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trends", tags=["Trends & Analytics"])


# =============================================================================
# MODELS
# =============================================================================

class TrendHashtag(BaseModel):
    platform: str
    hashtag: str
    rank: Optional[int] = None
    post_count: Optional[int] = None
    view_count: Optional[int] = None
    growth_rate: Optional[float] = None
    category: Optional[str] = None
    region: str = "global"


class TrendSound(BaseModel):
    platform: str
    sound_id: Optional[str] = None
    sound_name: str
    artist_name: Optional[str] = None
    rank: Optional[int] = None
    usage_count: Optional[int] = None
    growth_rate: Optional[float] = None
    region: str = "global"


class TrendTopic(BaseModel):
    platform: str
    topic: str
    rank: Optional[int] = None
    mention_count: Optional[int] = None
    sentiment_score: Optional[float] = None
    growth_rate: Optional[float] = None
    category: Optional[str] = None
    region: str = "global"


class TrackedCompetitor(BaseModel):
    platform: str
    username: str
    display_name: Optional[str] = None
    notes: Optional[str] = None


class AppRanking(BaseModel):
    store: str  # apple, google
    app_id: str
    app_name: str
    developer: Optional[str] = None
    category: str
    chart_type: str  # free, paid, grossing
    rank: int
    rating: Optional[float] = None
    region: str = "US"


# =============================================================================
# HASHTAG TRENDS
# =============================================================================

@router.get("/hashtags")
async def get_trending_hashtags(
    platform: Optional[str] = None,
    region: str = "global",
    limit: int = Query(default=50, le=100),
    hours: int = Query(default=24, le=168)
):
    """Get trending hashtags across platforms."""
    supabase = get_supabase()
    
    query = supabase.table("trend_hashtags").select("*")
    
    if platform:
        query = query.eq("platform", platform)
    
    query = query.eq("region", region)
    query = query.gte("snapshot_at", (datetime.utcnow() - timedelta(hours=hours)).isoformat())
    query = query.order("rank", desc=False)
    query = query.limit(limit)
    
    result = query.execute()
    return {"hashtags": result.data, "count": len(result.data)}


@router.post("/hashtags")
async def add_hashtag_trend(hashtag: TrendHashtag):
    """Add a new hashtag trend snapshot."""
    supabase = get_supabase()
    
    result = supabase.table("trend_hashtags").insert({
        "platform": hashtag.platform,
        "hashtag": hashtag.hashtag,
        "rank": hashtag.rank,
        "post_count": hashtag.post_count,
        "view_count": hashtag.view_count,
        "growth_rate": hashtag.growth_rate,
        "category": hashtag.category,
        "region": hashtag.region,
        "snapshot_at": datetime.utcnow().isoformat()
    }).execute()
    
    # Emit TREND_RAW_INGESTED event
    try:
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.TREND_RAW_INGESTED, {
            "type": "hashtag",
            "platform": hashtag.platform,
            "hashtag": hashtag.hashtag,
            "rank": hashtag.rank,
            "growth_rate": hashtag.growth_rate,
        })
        logger.info(f"[PubSub] Emitted TREND_RAW_INGESTED for {hashtag.hashtag}")
    except Exception as e:
        logger.warning(f"[PubSub] Failed to emit trend event: {e}")
    
    return {"success": True, "data": result.data}


@router.get("/hashtags/{platform}/top")
async def get_top_hashtags(
    platform: str,
    limit: int = Query(default=20, le=50)
):
    """Get top hashtags for a specific platform."""
    supabase = get_supabase()
    
    result = supabase.table("trend_hashtags").select("*") \
        .eq("platform", platform) \
        .gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat()) \
        .order("rank", desc=False) \
        .limit(limit) \
        .execute()
    
    return {"platform": platform, "hashtags": result.data}


# =============================================================================
# SOUND TRENDS
# =============================================================================

@router.get("/sounds")
async def get_trending_sounds(
    platform: Optional[str] = None,
    region: str = "global",
    limit: int = Query(default=50, le=100)
):
    """Get trending sounds/audio."""
    supabase = get_supabase()
    
    query = supabase.table("trend_sounds").select("*")
    
    if platform:
        query = query.eq("platform", platform)
    
    query = query.eq("region", region)
    query = query.gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat())
    query = query.order("rank", desc=False)
    query = query.limit(limit)
    
    result = query.execute()
    return {"sounds": result.data, "count": len(result.data)}


@router.post("/sounds")
async def add_sound_trend(sound: TrendSound):
    """Add a new sound trend snapshot."""
    supabase = get_supabase()
    
    result = supabase.table("trend_sounds").insert({
        "platform": sound.platform,
        "sound_id": sound.sound_id,
        "sound_name": sound.sound_name,
        "artist_name": sound.artist_name,
        "rank": sound.rank,
        "usage_count": sound.usage_count,
        "growth_rate": sound.growth_rate,
        "region": sound.region,
        "snapshot_at": datetime.utcnow().isoformat()
    }).execute()
    
    # Emit TREND_RAW_INGESTED event for sound
    try:
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.TREND_RAW_INGESTED, {
            "type": "sound",
            "platform": sound.platform,
            "sound_name": sound.sound_name,
            "rank": sound.rank,
            "usage_count": sound.usage_count,
        })
        logger.info(f"[PubSub] Emitted TREND_RAW_INGESTED for sound {sound.sound_name}")
    except Exception as e:
        logger.warning(f"[PubSub] Failed to emit sound trend event: {e}")
    
    return {"success": True, "data": result.data}


# =============================================================================
# TOPIC TRENDS
# =============================================================================

@router.get("/topics")
async def get_trending_topics(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get trending topics/keywords."""
    supabase = get_supabase()
    
    query = supabase.table("trend_topics").select("*")
    
    if platform:
        query = query.eq("platform", platform)
    if category:
        query = query.eq("category", category)
    
    query = query.gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat())
    query = query.order("rank", desc=False)
    query = query.limit(limit)
    
    result = query.execute()
    return {"topics": result.data, "count": len(result.data)}


@router.post("/topics")
async def add_topic_trend(topic: TrendTopic):
    """Add a new topic trend snapshot."""
    supabase = get_supabase()
    
    result = supabase.table("trend_topics").insert({
        "platform": topic.platform,
        "topic": topic.topic,
        "rank": topic.rank,
        "mention_count": topic.mention_count,
        "sentiment_score": topic.sentiment_score,
        "growth_rate": topic.growth_rate,
        "category": topic.category,
        "region": topic.region,
        "snapshot_at": datetime.utcnow().isoformat()
    }).execute()
    
    # Emit TREND_RAW_INGESTED event for topic
    try:
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.TREND_RAW_INGESTED, {
            "type": "topic",
            "platform": topic.platform,
            "topic": topic.topic,
            "rank": topic.rank,
            "mention_count": topic.mention_count,
        })
        logger.info(f"[PubSub] Emitted TREND_RAW_INGESTED for topic {topic.topic}")
    except Exception as e:
        logger.warning(f"[PubSub] Failed to emit topic trend event: {e}")
    
    return {"success": True, "data": result.data}


# =============================================================================
# CREATOR TRENDS
# =============================================================================

@router.get("/creators")
async def get_trending_creators(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get trending creators/influencers."""
    supabase = get_supabase()
    
    query = supabase.table("trend_creators").select("*")
    
    if platform:
        query = query.eq("platform", platform)
    if category:
        query = query.eq("content_category", category)
    
    query = query.gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat())
    query = query.order("rank", desc=False)
    query = query.limit(limit)
    
    result = query.execute()
    return {"creators": result.data, "count": len(result.data)}


# =============================================================================
# FORMAT TRENDS
# =============================================================================

@router.get("/formats")
async def get_trending_formats(
    platform: Optional[str] = None,
    limit: int = Query(default=20, le=50)
):
    """Get trending video formats/styles."""
    supabase = get_supabase()
    
    query = supabase.table("trend_formats").select("*")
    
    if platform:
        query = query.eq("platform", platform)
    
    query = query.gte("snapshot_at", (datetime.utcnow() - timedelta(hours=48)).isoformat())
    query = query.order("rank", desc=False)
    query = query.limit(limit)
    
    result = query.execute()
    return {"formats": result.data, "count": len(result.data)}


# =============================================================================
# APP STORE RANKINGS
# =============================================================================

@router.get("/appstore/rankings")
async def get_app_rankings(
    store: Optional[str] = None,  # apple, google
    category: Optional[str] = None,
    chart_type: str = "free",  # free, paid, grossing
    region: str = "US",
    limit: int = Query(default=50, le=100)
):
    """Get app store rankings."""
    supabase = get_supabase()
    
    query = supabase.table("appstore_rankings").select("*")
    
    if store:
        query = query.eq("store", store)
    if category:
        query = query.eq("category", category)
    
    query = query.eq("chart_type", chart_type)
    query = query.eq("region", region)
    query = query.gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat())
    query = query.order("rank", desc=False)
    query = query.limit(limit)
    
    result = query.execute()
    return {"rankings": result.data, "count": len(result.data)}


@router.post("/appstore/rankings")
async def add_app_ranking(ranking: AppRanking):
    """Add a new app ranking snapshot."""
    supabase = get_supabase()
    
    result = supabase.table("appstore_rankings").insert({
        "store": ranking.store,
        "app_id": ranking.app_id,
        "app_name": ranking.app_name,
        "developer": ranking.developer,
        "category": ranking.category,
        "chart_type": ranking.chart_type,
        "rank": ranking.rank,
        "rating": ranking.rating,
        "region": ranking.region,
        "snapshot_at": datetime.utcnow().isoformat()
    }).execute()
    
    return {"success": True, "data": result.data}


@router.get("/appstore/categories")
async def get_app_categories(store: str = "apple"):
    """Get available app store categories."""
    categories = {
        "apple": [
            "social", "photo_video", "entertainment", "music", "games",
            "productivity", "utilities", "lifestyle", "health_fitness",
            "education", "business", "finance", "news", "shopping"
        ],
        "google": [
            "social", "video_players", "entertainment", "music_audio", "games",
            "productivity", "tools", "lifestyle", "health_fitness",
            "education", "business", "finance", "news_magazines", "shopping"
        ]
    }
    return {"store": store, "categories": categories.get(store, [])}


# =============================================================================
# COMPETITOR TRACKING
# =============================================================================

@router.get("/competitors")
async def get_tracked_competitors():
    """Get all tracked competitors."""
    supabase = get_supabase()
    
    result = supabase.table("tracked_competitors").select("*") \
        .eq("is_active", True) \
        .order("created_at", desc=True) \
        .execute()
    
    return {"competitors": result.data, "count": len(result.data)}


@router.post("/competitors")
async def add_competitor(competitor: TrackedCompetitor):
    """Add a new competitor to track."""
    supabase = get_supabase()
    
    result = supabase.table("tracked_competitors").insert({
        "platform": competitor.platform,
        "username": competitor.username,
        "display_name": competitor.display_name,
        "notes": competitor.notes,
        "is_active": True
    }).execute()
    
    return {"success": True, "data": result.data}


@router.delete("/competitors/{competitor_id}")
async def remove_competitor(competitor_id: str):
    """Remove a tracked competitor."""
    supabase = get_supabase()
    
    result = supabase.table("tracked_competitors").update({
        "is_active": False
    }).eq("id", competitor_id).execute()
    
    return {"success": True}


@router.get("/competitors/{competitor_id}/history")
async def get_competitor_history(
    competitor_id: str,
    days: int = Query(default=30, le=90)
):
    """Get historical snapshots for a competitor."""
    supabase = get_supabase()
    
    result = supabase.table("competitor_snapshots").select("*") \
        .eq("competitor_id", competitor_id) \
        .gte("snapshot_at", (datetime.utcnow() - timedelta(days=days)).isoformat()) \
        .order("snapshot_at", desc=True) \
        .execute()
    
    return {"history": result.data, "count": len(result.data)}


# =============================================================================
# ALERTS & NOTIFICATIONS
# =============================================================================

@router.get("/alerts")
async def get_trend_alerts(
    unread_only: bool = True,
    limit: int = Query(default=20, le=50)
):
    """Get trend alerts."""
    try:
        supabase = get_supabase()
        
        query = supabase.table("trend_alerts").select("*")
        
        if unread_only:
            query = query.eq("is_read", False)
        
        query = query.eq("is_dismissed", False)
        query = query.order("created_at", desc=True)
        query = query.limit(limit)
        
        result = query.execute()
        return {"alerts": result.data, "count": len(result.data)}
    except Exception as e:
        # Return empty list if table doesn't exist or other error
        return {"alerts": [], "count": 0, "error": str(e)}


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    supabase = get_supabase()
    
    result = supabase.table("trend_alerts").update({
        "is_read": True
    }).eq("id", alert_id).execute()
    
    return {"success": True}


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str):
    """Dismiss an alert."""
    supabase = get_supabase()
    
    result = supabase.table("trend_alerts").update({
        "is_dismissed": True
    }).eq("id", alert_id).execute()
    
    return {"success": True}


# =============================================================================
# INDUSTRY BENCHMARKS
# =============================================================================

@router.get("/benchmarks")
async def get_industry_benchmarks(
    platform: Optional[str] = None,
    category: Optional[str] = None
):
    """Get industry benchmarks for comparison."""
    supabase = get_supabase()
    
    query = supabase.table("industry_benchmarks").select("*")
    
    if platform:
        query = query.eq("platform", platform)
    if category:
        query = query.eq("category", category)
    
    query = query.order("snapshot_at", desc=True)
    query = query.limit(100)
    
    result = query.execute()
    return {"benchmarks": result.data, "count": len(result.data)}


# =============================================================================
# AGGREGATED VIEWS
# =============================================================================

@router.get("/overview")
async def get_trends_overview():
    """Get a summary overview of all trends."""
    supabase = get_supabase()
    
    # Get counts from each trend type
    hashtags = supabase.table("trend_hashtags").select("id", count="exact") \
        .gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat()) \
        .execute()
    
    sounds = supabase.table("trend_sounds").select("id", count="exact") \
        .gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat()) \
        .execute()
    
    topics = supabase.table("trend_topics").select("id", count="exact") \
        .gte("snapshot_at", (datetime.utcnow() - timedelta(hours=24)).isoformat()) \
        .execute()
    
    alerts = supabase.table("trend_alerts").select("id", count="exact") \
        .eq("is_read", False) \
        .execute()
    
    return {
        "overview": {
            "trending_hashtags": hashtags.count or 0,
            "trending_sounds": sounds.count or 0,
            "trending_topics": topics.count or 0,
            "unread_alerts": alerts.count or 0,
            "last_updated": datetime.utcnow().isoformat()
        }
    }


@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported platforms for trends."""
    return {
        "social_platforms": [
            {"id": "tiktok", "name": "TikTok", "icon": "🎵", "supports": ["hashtags", "sounds", "creators", "topics"]},
            {"id": "instagram", "name": "Instagram", "icon": "📸", "supports": ["hashtags", "sounds", "creators"]},
            {"id": "youtube", "name": "YouTube", "icon": "▶️", "supports": ["topics", "creators", "formats"]},
            {"id": "twitter", "name": "X / Twitter", "icon": "𝕏", "supports": ["hashtags", "topics"]},
            {"id": "threads", "name": "Threads", "icon": "🧵", "supports": ["topics"]},
            {"id": "linkedin", "name": "LinkedIn", "icon": "💼", "supports": ["topics", "creators"]},
        ],
        "app_stores": [
            {"id": "apple", "name": "Apple App Store", "icon": "🍎"},
            {"id": "google", "name": "Google Play Store", "icon": "🤖"},
        ]
    }


# =============================================================================
# RAPIDAPI TREND FETCHING
# =============================================================================

import httpx
import os

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

RAPIDAPI_SOURCES = {
    "tiktok": {
        "host": "tiktok-scraper2.p.rapidapi.com",
        "trending_endpoint": "/trending/feed",
        "hashtag_endpoint": "/hashtag/posts"
    },
    "instagram": {
        "host": "instagram-looter2.p.rapidapi.com",
        "trending_endpoint": "/v1/explore",
        "hashtag_endpoint": "/v1/hashtag"
    },
    "twitter": {
        "host": "twitter154.p.rapidapi.com",
        "trending_endpoint": "/trends/",
        "hashtag_endpoint": "/search/search"
    },
    "youtube": {
        "host": "youtube-search-and-download.p.rapidapi.com",
        "trending_endpoint": "/trending",
        "hashtag_endpoint": "/search"
    },
    "threads": {
        "host": "threads-api4.p.rapidapi.com",
        "trending_endpoint": "/api/explore",
        "hashtag_endpoint": "/api/hashtag"
    }
}


@router.post("/fetch/{platform}")
async def fetch_trends_from_source(platform: str):
    """
    Trigger a live fetch of trends from RapidAPI source.
    Stores results in database for caching.
    """
    if not RAPIDAPI_KEY:
        return {
            "success": False,
            "error": "RAPIDAPI_KEY not configured",
            "message": "Set RAPIDAPI_KEY environment variable to enable trend fetching"
        }
    
    if platform not in RAPIDAPI_SOURCES:
        return {
            "success": False,
            "error": f"Unknown platform: {platform}",
            "supported": list(RAPIDAPI_SOURCES.keys())
        }
    
    source = RAPIDAPI_SOURCES[platform]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": source["host"]
            }
            
            # Fetch trending content
            response = await client.get(
                f"https://{source['host']}{source['trending_endpoint']}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Process and store trends based on platform
                trends_saved = await _process_platform_trends(platform, data)
                
                return {
                    "success": True,
                    "platform": platform,
                    "trends_saved": trends_saved,
                    "fetched_at": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"RapidAPI {platform} error: {response.status_code} - {response.text[:200]}")
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}",
                    "platform": platform
                }
                
    except Exception as e:
        logger.error(f"Error fetching {platform} trends: {e}")
        return {
            "success": False,
            "error": str(e),
            "platform": platform
        }


async def _process_platform_trends(platform: str, data: dict) -> int:
    """Process and store trends from RapidAPI response."""
    supabase = get_supabase()
    saved_count = 0
    
    try:
        if platform == "tiktok":
            # TikTok trending response structure
            items = data.get("data", {}).get("items", []) or data.get("items", [])
            for i, item in enumerate(items[:50]):
                try:
                    # Extract hashtags from description
                    desc = item.get("desc", "") or item.get("description", "")
                    hashtags = [tag.strip("#") for tag in desc.split() if tag.startswith("#")]
                    
                    for tag in hashtags[:3]:  # Top 3 hashtags per video
                        supabase.table("trend_hashtags").upsert({
                            "platform": "tiktok",
                            "hashtag": tag.lower(),
                            "rank": i + 1,
                            "view_count": item.get("stats", {}).get("playCount", 0),
                            "region": "global",
                            "snapshot_at": datetime.utcnow().isoformat()
                        }, on_conflict="platform,hashtag,region").execute()
                        saved_count += 1
                        
                    # Extract audio
                    music = item.get("music", {})
                    if music.get("title"):
                        supabase.table("trend_sounds").upsert({
                            "platform": "tiktok",
                            "sound_id": str(music.get("id", "")),
                            "sound_name": music.get("title", ""),
                            "artist_name": music.get("authorName", ""),
                            "rank": i + 1,
                            "usage_count": music.get("playCount", 0),
                            "region": "global",
                            "snapshot_at": datetime.utcnow().isoformat()
                        }, on_conflict="platform,sound_id,region").execute()
                        saved_count += 1
                except Exception as e:
                    logger.warning(f"Error processing TikTok item: {e}")
                    
        elif platform == "instagram":
            items = data.get("data", {}).get("items", []) or data.get("items", [])
            for i, item in enumerate(items[:50]):
                try:
                    caption = item.get("caption", {}).get("text", "") if isinstance(item.get("caption"), dict) else ""
                    hashtags = [tag.strip("#") for tag in caption.split() if tag.startswith("#")]
                    
                    for tag in hashtags[:3]:
                        supabase.table("trend_hashtags").upsert({
                            "platform": "instagram",
                            "hashtag": tag.lower(),
                            "rank": i + 1,
                            "view_count": item.get("play_count", item.get("view_count", 0)),
                            "post_count": item.get("like_count", 0),
                            "region": "global",
                            "snapshot_at": datetime.utcnow().isoformat()
                        }, on_conflict="platform,hashtag,region").execute()
                        saved_count += 1
                except Exception as e:
                    logger.warning(f"Error processing Instagram item: {e}")
                    
        elif platform == "twitter":
            trends = data.get("trends", []) or data.get("data", [])
            for i, trend in enumerate(trends[:50]):
                try:
                    name = trend.get("name", "") or trend.get("query", "")
                    if name.startswith("#"):
                        supabase.table("trend_hashtags").upsert({
                            "platform": "twitter",
                            "hashtag": name.strip("#").lower(),
                            "rank": i + 1,
                            "post_count": trend.get("tweet_volume", 0),
                            "region": "global",
                            "snapshot_at": datetime.utcnow().isoformat()
                        }, on_conflict="platform,hashtag,region").execute()
                    else:
                        supabase.table("trend_topics").upsert({
                            "platform": "twitter",
                            "topic": name,
                            "rank": i + 1,
                            "mention_count": trend.get("tweet_volume", 0),
                            "region": "global",
                            "snapshot_at": datetime.utcnow().isoformat()
                        }, on_conflict="platform,topic,region").execute()
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Error processing Twitter trend: {e}")
                    
        elif platform == "youtube":
            items = data.get("contents", []) or data.get("items", [])
            for i, item in enumerate(items[:50]):
                try:
                    title = item.get("title", "") or item.get("video", {}).get("title", "")
                    supabase.table("trend_topics").upsert({
                        "platform": "youtube",
                        "topic": title[:100],
                        "rank": i + 1,
                        "mention_count": item.get("viewCount", 0),
                        "region": "global",
                        "snapshot_at": datetime.utcnow().isoformat()
                    }, on_conflict="platform,topic,region").execute()
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Error processing YouTube item: {e}")
                    
    except Exception as e:
        logger.error(f"Error processing {platform} trends: {e}")
    
    logger.info(f"Saved {saved_count} trends from {platform}")
    return saved_count


@router.get("/sources/status")
async def get_sources_status():
    """Get status of all RapidAPI sources."""
    return {
        "sources": [
            {
                "platform": platform,
                "host": config["host"],
                "configured": bool(RAPIDAPI_KEY),
                "endpoints": {
                    "trending": config["trending_endpoint"],
                    "hashtag": config["hashtag_endpoint"]
                }
            }
            for platform, config in RAPIDAPI_SOURCES.items()
        ],
        "api_key_configured": bool(RAPIDAPI_KEY)
    }

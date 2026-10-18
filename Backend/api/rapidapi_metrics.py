"""
Multi-API Metrics Service for Instagram & LinkedIn
Uses multiple RapidAPI endpoints with intelligent load balancing to avoid rate limits.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import httpx
import os
import logging
import random
from collections import defaultdict

router = APIRouter(prefix="/api/rapidapi-metrics", tags=["RapidAPI Metrics"])
logger = logging.getLogger(__name__)

# ============================================================================
# API CONFIGURATION - Multiple APIs for redundancy
# ============================================================================

class APIProvider(str, Enum):
    INSTAGRAM_LOOTER2 = "instagram-looter2"
    INSTAGRAM_SCRAPER = "instagram-scraper-2022"
    INSTAGRAM_BULK = "instagram-bulk-profile-scrapper"
    LINKEDIN_SCRAPER = "linkedin-profile-scraper"
    LINKEDIN_DATA = "linkedin-data-scraper"


# API configurations with endpoints and rate limits
API_CONFIGS: Dict[str, Dict] = {
    APIProvider.INSTAGRAM_LOOTER2: {
        "host": "instagram-looter2.p.rapidapi.com",
        "base_url": "https://instagram-looter2.p.rapidapi.com",
        "rate_limit_per_second": 10,
        "monthly_limit": 15000,  # Free tier
        "endpoints": {
            "profile": "/profile",
            "profile_v2": "/profile2",
            "web_profile": "/web-profile",
            "user_feeds": "/user-feeds",
            "user_feeds_v2": "/user-feeds2",
            "reels": "/reels",
            "user_tags": "/user-tags",
            "post": "/post",
            "post_download": "/post-dl",
            "user_id": "/id",
            "media_id": "/id-media",
            "search_users": "/search",
            "hashtag_feeds": "/tag-feeds",
            "location_feeds": "/location-feeds",
        },
        "platform": "instagram",
    },
    APIProvider.INSTAGRAM_SCRAPER: {
        "host": "instagram-scraper-2022.p.rapidapi.com",
        "base_url": "https://instagram-scraper-2022.p.rapidapi.com",
        "rate_limit_per_second": 5,
        "monthly_limit": 10000,
        "endpoints": {
            "profile": "/ig/info_username/",
            "user_feeds": "/ig/posts_username/",
            "reels": "/ig/reels/",
            "post": "/ig/post_info/",
        },
        "platform": "instagram",
    },
    APIProvider.INSTAGRAM_BULK: {
        "host": "instagram-bulk-profile-scrapper.p.rapidapi.com",
        "base_url": "https://instagram-bulk-profile-scrapper.p.rapidapi.com",
        "rate_limit_per_second": 3,
        "monthly_limit": 5000,
        "endpoints": {
            "profile": "/clients/api/ig/ig_profile",
            "user_feeds": "/clients/api/ig/ig_posts",
        },
        "platform": "instagram",
    },
    APIProvider.LINKEDIN_SCRAPER: {
        "host": "linkedin-profile-scraper-api.p.rapidapi.com",
        "base_url": "https://linkedin-profile-scraper-api.p.rapidapi.com",
        "rate_limit_per_second": 2,
        "monthly_limit": 5000,
        "endpoints": {
            "profile": "/profile",
            "company": "/company",
            "posts": "/posts",
        },
        "platform": "linkedin",
    },
    APIProvider.LINKEDIN_DATA: {
        "host": "linkedin-data-scraper.p.rapidapi.com",
        "base_url": "https://linkedin-data-scraper.p.rapidapi.com",
        "rate_limit_per_second": 3,
        "monthly_limit": 8000,
        "endpoints": {
            "profile": "/profile-details",
            "company": "/company-details",
            "posts": "/profile-posts",
        },
        "platform": "linkedin",
    },
}

# ============================================================================
# USAGE TRACKING & LOAD BALANCING
# ============================================================================

# Track API usage for load balancing
_api_usage: Dict[str, Dict] = defaultdict(lambda: {
    "calls_today": 0,
    "calls_this_month": 0,
    "last_call": None,
    "errors": 0,
    "last_error": None,
})

# Track backfill jobs
_backfill_jobs: Dict[str, Dict] = {}


class APIUsageStats(BaseModel):
    provider: str
    calls_today: int
    calls_this_month: int
    monthly_limit: int
    usage_percent: float
    status: str
    last_call: Optional[str]
    errors: int


class BackfillJob(BaseModel):
    job_id: str
    platform: str
    accounts: List[str]
    status: str
    progress: float
    started_at: str
    completed_at: Optional[str]
    total_accounts: int
    processed_accounts: int
    metrics_collected: int
    errors: List[str]


class MetricsResult(BaseModel):
    username: str
    platform: str
    follower_count: int
    following_count: int
    post_count: int
    engagement_rate: Optional[float]
    avg_likes: Optional[float]
    avg_comments: Optional[float]
    recent_posts: List[Dict]
    fetched_at: str
    api_provider: str


# ============================================================================
# INTELLIGENT API SELECTION
# ============================================================================

def select_best_api(platform: str, endpoint_type: str) -> Optional[APIProvider]:
    """
    Select the best API provider based on:
    1. Platform match
    2. Available quota
    3. Error rate
    4. Rate limiting
    """
    candidates = []
    
    for provider, config in API_CONFIGS.items():
        if config["platform"] != platform:
            continue
        if endpoint_type not in config["endpoints"]:
            continue
            
        usage = _api_usage[provider]
        monthly_limit = config["monthly_limit"]
        usage_percent = (usage["calls_this_month"] / monthly_limit) * 100 if monthly_limit > 0 else 100
        
        # Skip if over 90% usage
        if usage_percent >= 90:
            continue
            
        # Calculate score (lower is better)
        score = usage_percent + (usage["errors"] * 5)
        
        candidates.append((provider, score))
    
    if not candidates:
        return None
        
    # Sort by score and return best
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


async def call_api(provider: APIProvider, endpoint: str, params: Dict) -> Dict:
    """Make an API call with rate limiting and error tracking"""
    config = API_CONFIGS[provider]
    usage = _api_usage[provider]
    
    # Check rate limit
    if usage["last_call"]:
        last_call = datetime.fromisoformat(usage["last_call"])
        min_interval = 1 / config["rate_limit_per_second"]
        elapsed = (datetime.now() - last_call).total_seconds()
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
    
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", ""),
        "X-RapidAPI-Host": config["host"],
    }
    
    url = f"{config['base_url']}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
            # Update usage
            usage["calls_today"] += 1
            usage["calls_this_month"] += 1
            usage["last_call"] = datetime.now().isoformat()
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                usage["errors"] += 1
                usage["last_error"] = "Rate limited"
                raise HTTPException(status_code=429, detail="API rate limit exceeded")
            else:
                usage["errors"] += 1
                usage["last_error"] = f"HTTP {response.status_code}"
                raise HTTPException(status_code=response.status_code, detail="API error")
                
    except httpx.TimeoutException:
        usage["errors"] += 1
        usage["last_error"] = "Timeout"
        raise HTTPException(status_code=504, detail="API timeout")
    except Exception as e:
        usage["errors"] += 1
        usage["last_error"] = str(e)
        raise


# ============================================================================
# INSTAGRAM METRICS ENDPOINTS
# ============================================================================

@router.get("/instagram/profile/{username}", response_model=MetricsResult)
async def get_instagram_profile(username: str):
    """
    Fetch Instagram profile metrics using the best available API.
    Automatically rotates between APIs to avoid rate limits.
    """
    provider = select_best_api("instagram", "profile")
    if not provider:
        raise HTTPException(status_code=503, detail="No API providers available")
    
    config = API_CONFIGS[provider]
    endpoint = config["endpoints"]["profile"]
    
    # Different APIs have different parameter formats
    if provider == APIProvider.INSTAGRAM_LOOTER2:
        params = {"username": username}
    elif provider == APIProvider.INSTAGRAM_SCRAPER:
        endpoint = f"{endpoint}{username}"
        params = {}
    else:
        params = {"username": username}
    
    data = await call_api(provider, endpoint, params)
    
    # Normalize response format
    return normalize_instagram_profile(data, username, provider)


@router.get("/instagram/posts/{username}")
async def get_instagram_posts(
    username: str,
    limit: int = Query(default=12, le=50),
    cursor: Optional[str] = None
):
    """
    Fetch recent posts for an Instagram account.
    Returns engagement metrics for each post.
    """
    provider = select_best_api("instagram", "user_feeds")
    if not provider:
        raise HTTPException(status_code=503, detail="No API providers available")
    
    config = API_CONFIGS[provider]
    endpoint = config["endpoints"]["user_feeds"]
    
    params = {"username": username, "amount": limit}
    if cursor:
        params["end_cursor"] = cursor
    
    data = await call_api(provider, endpoint, params)
    
    return {
        "username": username,
        "posts": normalize_posts(data, provider),
        "next_cursor": data.get("end_cursor"),
        "fetched_at": datetime.now().isoformat(),
        "api_provider": provider,
    }


@router.get("/instagram/post/{media_id}")
async def get_instagram_post_metrics(media_id: str):
    """
    Fetch metrics for a specific Instagram post.
    Can use media ID or URL.
    """
    provider = select_best_api("instagram", "post")
    if not provider:
        raise HTTPException(status_code=503, detail="No API providers available")
    
    config = API_CONFIGS[provider]
    endpoint = config["endpoints"]["post"]
    
    # Detect if it's a URL or ID
    if "instagram.com" in media_id:
        params = {"url": media_id}
    else:
        params = {"id": media_id}
    
    data = await call_api(provider, endpoint, params)
    
    return normalize_post_metrics(data, provider)


# ============================================================================
# LINKEDIN METRICS ENDPOINTS
# ============================================================================

@router.get("/linkedin/profile/{profile_id}")
async def get_linkedin_profile(profile_id: str):
    """
    Fetch LinkedIn profile metrics.
    profile_id can be vanity URL or URN.
    """
    provider = select_best_api("linkedin", "profile")
    if not provider:
        raise HTTPException(status_code=503, detail="No API providers available")
    
    config = API_CONFIGS[provider]
    endpoint = config["endpoints"]["profile"]
    
    params = {"profile_id": profile_id}
    data = await call_api(provider, endpoint, params)
    
    return normalize_linkedin_profile(data, profile_id, provider)


@router.get("/linkedin/posts/{profile_id}")
async def get_linkedin_posts(
    profile_id: str,
    limit: int = Query(default=10, le=50)
):
    """
    Fetch recent posts for a LinkedIn profile.
    """
    provider = select_best_api("linkedin", "posts")
    if not provider:
        raise HTTPException(status_code=503, detail="No API providers available")
    
    config = API_CONFIGS[provider]
    endpoint = config["endpoints"]["posts"]
    
    params = {"profile_id": profile_id, "count": limit}
    data = await call_api(provider, endpoint, params)
    
    return {
        "profile_id": profile_id,
        "posts": data.get("posts", []),
        "fetched_at": datetime.now().isoformat(),
        "api_provider": provider,
    }


# ============================================================================
# BACKFILL ENDPOINTS
# ============================================================================

@router.post("/backfill/start")
async def start_backfill(
    background_tasks: BackgroundTasks,
    platform: str = Query(..., regex="^(instagram|linkedin)$"),
    accounts: List[str] = Query(...),
    days_back: int = Query(default=30, le=90),
):
    """
    Start a background job to backfill metrics for multiple accounts.
    Intelligently distributes requests across multiple APIs.
    """
    import uuid
    job_id = str(uuid.uuid4())
    
    job = {
        "job_id": job_id,
        "platform": platform,
        "accounts": accounts,
        "days_back": days_back,
        "status": "running",
        "progress": 0.0,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "total_accounts": len(accounts),
        "processed_accounts": 0,
        "metrics_collected": 0,
        "errors": [],
    }
    
    _backfill_jobs[job_id] = job
    
    # Start background task
    background_tasks.add_task(run_backfill_job, job_id)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": f"Backfill started for {len(accounts)} {platform} accounts",
        "estimated_time_minutes": len(accounts) * 2,  # ~2 min per account
    }


@router.get("/backfill/status/{job_id}", response_model=BackfillJob)
async def get_backfill_status(job_id: str):
    """Get the status of a backfill job"""
    if job_id not in _backfill_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _backfill_jobs[job_id]


@router.get("/backfill/jobs")
async def list_backfill_jobs():
    """List all backfill jobs"""
    return list(_backfill_jobs.values())


async def run_backfill_job(job_id: str):
    """Background task to run backfill"""
    job = _backfill_jobs[job_id]
    platform = job["platform"]
    accounts = job["accounts"]
    
    for i, account in enumerate(accounts):
        try:
            # Select API with load balancing
            provider = select_best_api(platform, "profile")
            if not provider:
                job["errors"].append(f"No API available for {account}")
                continue
            
            # Fetch profile
            if platform == "instagram":
                await get_instagram_profile(account)
                await asyncio.sleep(1)  # Rate limit buffer
                await get_instagram_posts(account, limit=30)
            else:
                await get_linkedin_profile(account)
                await asyncio.sleep(1)
                await get_linkedin_posts(account, limit=20)
            
            job["processed_accounts"] += 1
            job["metrics_collected"] += 1
            job["progress"] = (i + 1) / len(accounts) * 100
            
            # Delay between accounts to avoid rate limits
            await asyncio.sleep(3)
            
        except Exception as e:
            job["errors"].append(f"{account}: {str(e)}")
            logger.error(f"Backfill error for {account}: {e}")
    
    job["status"] = "completed"
    job["completed_at"] = datetime.now().isoformat()


# ============================================================================
# API USAGE MONITORING
# ============================================================================

@router.get("/usage")
async def get_api_usage() -> List[APIUsageStats]:
    """
    Get usage statistics for all API providers.
    Use this to monitor rate limits and plan API calls.
    """
    stats = []
    for provider, config in API_CONFIGS.items():
        usage = _api_usage[provider]
        monthly_limit = config["monthly_limit"]
        usage_percent = (usage["calls_this_month"] / monthly_limit * 100) if monthly_limit > 0 else 0
        
        status = "healthy"
        if usage_percent >= 90:
            status = "critical"
        elif usage_percent >= 70:
            status = "warning"
        elif usage["errors"] > 5:
            status = "degraded"
        
        stats.append(APIUsageStats(
            provider=provider,
            calls_today=usage["calls_today"],
            calls_this_month=usage["calls_this_month"],
            monthly_limit=monthly_limit,
            usage_percent=round(usage_percent, 1),
            status=status,
            last_call=usage["last_call"],
            errors=usage["errors"],
        ))
    
    return stats


@router.post("/usage/reset")
async def reset_usage_counters():
    """Reset daily usage counters (for testing)"""
    for provider in API_CONFIGS:
        _api_usage[provider]["calls_today"] = 0
    return {"status": "reset", "message": "Daily counters reset"}


# ============================================================================
# DATA NORMALIZATION HELPERS
# ============================================================================

def normalize_instagram_profile(data: Dict, username: str, provider: str) -> MetricsResult:
    """Normalize Instagram profile data from different APIs"""
    
    # Instagram Looter2 format
    if provider == APIProvider.INSTAGRAM_LOOTER2:
        user = data.get("data", data)
        return MetricsResult(
            username=username,
            platform="instagram",
            follower_count=user.get("follower_count", 0),
            following_count=user.get("following_count", 0),
            post_count=user.get("media_count", 0),
            engagement_rate=user.get("engagement_rate"),
            avg_likes=user.get("avg_likes"),
            avg_comments=user.get("avg_comments"),
            recent_posts=[],
            fetched_at=datetime.now().isoformat(),
            api_provider=provider,
        )
    
    # Generic fallback
    return MetricsResult(
        username=username,
        platform="instagram",
        follower_count=data.get("followers", data.get("follower_count", 0)),
        following_count=data.get("following", data.get("following_count", 0)),
        post_count=data.get("posts", data.get("media_count", 0)),
        engagement_rate=None,
        avg_likes=None,
        avg_comments=None,
        recent_posts=[],
        fetched_at=datetime.now().isoformat(),
        api_provider=provider,
    )


def normalize_linkedin_profile(data: Dict, profile_id: str, provider: str) -> Dict:
    """Normalize LinkedIn profile data"""
    return {
        "profile_id": profile_id,
        "platform": "linkedin",
        "name": data.get("name", ""),
        "headline": data.get("headline", ""),
        "follower_count": data.get("followers", 0),
        "connection_count": data.get("connections", 0),
        "post_count": data.get("posts_count", 0),
        "fetched_at": datetime.now().isoformat(),
        "api_provider": provider,
    }


def normalize_posts(data: Dict, provider: str) -> List[Dict]:
    """Normalize posts data from different APIs"""
    posts = data.get("items", data.get("data", []))
    
    normalized = []
    for post in posts[:50]:  # Limit to 50
        normalized.append({
            "id": post.get("id", post.get("pk")),
            "shortcode": post.get("shortcode", post.get("code")),
            "type": post.get("media_type", post.get("type")),
            "like_count": post.get("like_count", post.get("likes", 0)),
            "comment_count": post.get("comment_count", post.get("comments", 0)),
            "view_count": post.get("view_count", post.get("views", 0)),
            "caption": post.get("caption", {}).get("text", ""),
            "timestamp": post.get("taken_at", post.get("timestamp")),
            "thumbnail_url": post.get("thumbnail_url", post.get("display_url")),
        })
    
    return normalized


def normalize_post_metrics(data: Dict, provider: str) -> Dict:
    """Normalize single post metrics"""
    return {
        "id": data.get("id", data.get("pk")),
        "shortcode": data.get("shortcode", data.get("code")),
        "like_count": data.get("like_count", 0),
        "comment_count": data.get("comment_count", 0),
        "view_count": data.get("view_count", 0),
        "share_count": data.get("share_count", 0),
        "save_count": data.get("save_count", 0),
        "reach": data.get("reach", 0),
        "impressions": data.get("impressions", 0),
        "engagement_rate": data.get("engagement_rate", 0),
        "caption": data.get("caption", {}).get("text", ""),
        "timestamp": data.get("taken_at"),
        "api_provider": provider,
        "fetched_at": datetime.now().isoformat(),
    }

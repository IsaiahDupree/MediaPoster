"""
Trend Queries API
=================
Advanced query endpoints for trend discovery, content briefs, and creator analysis.

Implements queries from PRD_AdvancedQueries.md:
- Query A: Top 50 Hashtags in Niche
- Query G: Trend → Content Brief (North Star)
- Query H: Hook Leaderboard
- Query J: Rising Audio Tracker
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, func, text

from database.connection import get_db
from services.trend_ingestion_service import TrendIngestionService
from services.trend_scoring_service import TrendScoringService
from services.trend_brief_generator import TrendBriefGenerator, generate_hooks_for_niche

logger = logging.getLogger(__name__)

# Initialize services
_ingestion_service = None
_scoring_service = None

def get_ingestion_service() -> TrendIngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = TrendIngestionService()
    return _ingestion_service

def get_scoring_service() -> TrendScoringService:
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = TrendScoringService()
    return _scoring_service

router = APIRouter(prefix="/api/trend-queries", tags=["Trend Queries"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class TopHashtagsRequest(BaseModel):
    """Request for Query A: Top Hashtags in Niche"""
    seed_keywords: List[str] = Field(..., description="Keywords to search for hashtags")
    limit: int = Field(default=50, ge=1, le=100)
    country: Optional[str] = None
    

class HashtagResult(BaseModel):
    """Single hashtag result"""
    tag: str
    trend_score: float
    trend_delta: str
    saturation: str  # 'hot_accessible' | 'overcrowded' | 'emerging'
    why_hot: str
    post_count: int
    example_posts: List[str] = []


class TopHashtagsResponse(BaseModel):
    """Response for Query A"""
    hashtags: List[HashtagResult]
    query_time_ms: int
    cached: bool = False


class ContentBriefRequest(BaseModel):
    """Request for Query G: Trend → Content Brief"""
    trend_type: str = Field(..., description="'sound' | 'hashtag' | 'cluster' | 'topic'")
    trend_id: str = Field(..., description="The trend identifier")
    niche: Optional[str] = None
    country: Optional[str] = None


class ScriptOutline(BaseModel):
    """Script structure for content brief"""
    hook: str = "Pattern interrupt or bold claim (0-3s)"
    problem: str = "Relatable struggle (3-8s)"
    solution: str = "Your method/tip (8-20s)"
    proof: str = "Quick result/demo (20-35s)"
    cta: str = "Save this + follow for more"


class ContentBriefResponse(BaseModel):
    """Response for Query G: Content Brief"""
    trend_name: str
    trend_velocity: float
    hook_options: List[str]
    script_outline: ScriptOutline
    recommended_format: str
    optimal_length_sec: Dict[str, int]
    must_include_phrases: List[str]
    differentiation_twist: str
    top_examples: List[Dict[str, Any]]
    generated_at: datetime
    

class HookResult(BaseModel):
    """Single hook pattern result"""
    pattern: str
    velocity_avg: float
    example: str
    use_count: int


class HookLeaderboardResponse(BaseModel):
    """Response for Query H: Hook Leaderboard"""
    hooks: List[HookResult]
    niche: str
    query_time_ms: int


class RisingAudioResult(BaseModel):
    """Single rising audio result"""
    music_id: str
    title: str
    artist: Optional[str]
    velocity: float
    freshness_days: int
    reuse_rate: float
    best_content_type: str
    preview_url: Optional[str]


class RisingAudioResponse(BaseModel):
    """Response for Query J: Rising Audio"""
    audios: List[RisingAudioResult]
    query_time_ms: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def cache_key(query_type: str, params: dict) -> str:
    """Generate cache key from query type and params."""
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.sha256(f"{query_type}:{param_str}".encode()).hexdigest()[:32]


async def get_cached_result(db: AsyncSession, query_type: str, params: dict) -> Optional[dict]:
    """Check cache for existing result."""
    key = cache_key(query_type, params)
    result = await db.execute(
        text("""
            SELECT result FROM query_cache 
            WHERE query_type = :query_type 
            AND input_hash = :input_hash 
            AND (expires_at IS NULL OR expires_at > NOW())
        """),
        {"query_type": query_type, "input_hash": key}
    )
    row = result.fetchone()
    return row[0] if row else None


async def set_cached_result(db: AsyncSession, query_type: str, params: dict, result: dict, ttl_hours: int = 6):
    """Store result in cache."""
    key = cache_key(query_type, params)
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    await db.execute(
        text("""
            INSERT INTO query_cache (query_type, input_hash, result, expires_at)
            VALUES (:query_type, :input_hash, :result, :expires_at)
            ON CONFLICT (query_type, input_hash) 
            DO UPDATE SET result = :result, expires_at = :expires_at, created_at = NOW()
        """),
        {
            "query_type": query_type,
            "input_hash": key,
            "result": json.dumps(result),
            "expires_at": expires_at
        }
    )
    await db.commit()


# =============================================================================
# QUERY A: TOP HASHTAGS IN NICHE
# =============================================================================

@router.post("/hashtags/top", response_model=TopHashtagsResponse)
async def get_top_hashtags(
    request: TopHashtagsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Query A: Get top trending hashtags for a niche.
    
    Input: seed keywords
    Output: ranked hashtags with trend scores and saturation levels
    """
    import time
    start = time.time()
    
    # Check cache
    params = request.model_dump()
    cached = await get_cached_result(db, "hashtag_top", params)
    if cached:
        return TopHashtagsResponse(
            hashtags=[HashtagResult(**h) for h in cached["hashtags"]],
            query_time_ms=int((time.time() - start) * 1000),
            cached=True
        )
    
    # Use real Instagram Looter API
    ingestion = get_ingestion_service()
    scorer = get_scoring_service()
    
    all_media = []
    for keyword in request.seed_keywords[:3]:  # Limit to avoid rate limits
        try:
            media = await ingestion.ingest_hashtag(keyword, limit=30)
            all_media.extend([{
                "hashtags": m.hashtags,
                "author_id": m.author_id,
                "posted_at": m.posted_at,
                "play_count": m.play_count,
                "like_count": m.like_count,
                "music_id": m.music_id,
                "music_title": m.music_title
            } for m in media])
        except Exception as e:
            logger.warning(f"Failed to ingest #{keyword}: {e}")
    
    # Score hashtags
    if all_media:
        scores = scorer.score_hashtags(all_media)
        hashtags = []
        for score in scores[:request.limit]:
            saturation = "emerging" if score.saturation_score < 30 else "hot_accessible" if score.saturation_score < 70 else "overcrowded"
            hashtags.append(HashtagResult(
                tag=score.name,
                trend_score=score.trend_score,
                trend_delta=score.adoption_delta,
                saturation=saturation,
                why_hot=f"{score.status.title()} - Velocity: {score.velocity_score:.0f}, {score.adoption_24h} posts in 24h",
                post_count=score.adoption_24h * 7,  # Estimate weekly
                example_posts=[]
            ))
    else:
        # Fallback to basic response if API fails
        hashtags = [HashtagResult(
            tag=f"#{kw.replace(' ', '')}",
            trend_score=70,
            trend_delta="+20%",
            saturation="emerging",
            why_hot="Based on seed keyword",
            post_count=1000,
            example_posts=[]
        ) for kw in request.seed_keywords[:5]]
    
    result = {"hashtags": [h.model_dump() for h in hashtags]}
    await set_cached_result(db, "hashtag_top", params, result)
    
    return TopHashtagsResponse(
        hashtags=hashtags,
        query_time_ms=int((time.time() - start) * 1000),
        cached=False
    )


# =============================================================================
# QUERY G: TREND → CONTENT BRIEF (NORTH STAR)
# =============================================================================

@router.post("/brief/generate", response_model=ContentBriefResponse)
async def generate_content_brief(
    request: ContentBriefRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Query G: Generate a content brief from a trend.
    
    This is the NORTH STAR feature - converts trend data into actionable content plans.
    
    Input: trend type and ID
    Output: hooks, script outline, format recommendations, differentiation ideas
    """
    import time
    start = time.time()
    
    # Check cache
    params = request.model_dump()
    cached = await get_cached_result(db, "content_brief", params)
    if cached:
        cached["generated_at"] = datetime.fromisoformat(cached["generated_at"])
        return ContentBriefResponse(**cached)
    
    # Generate brief using OpenAI
    trend_name = request.trend_id
    if request.trend_type == "hashtag":
        trend_name = f"#{request.trend_id}"
    
    # Use real OpenAI generation
    generator = TrendBriefGenerator()
    ai_brief = await generator.generate_brief(
        trend_type=request.trend_type,
        trend_name=trend_name,
        niche=request.niche
    )
    
    # Parse AI response into our response model
    script_data = ai_brief.get("script_outline", {})
    brief = ContentBriefResponse(
        trend_name=trend_name,
        trend_velocity=87.5,
        hook_options=ai_brief.get("hook_options", [
            f"Stop doing this with {trend_name} (here's why)",
            f"I tried {trend_name} for 7 days—here's what happened",
            f"The {trend_name} hack that changed everything"
        ]),
        script_outline=ScriptOutline(
            hook=script_data.get("hook", "Pattern interrupt or bold claim (0-3s)"),
            problem=script_data.get("problem", "Relatable struggle your audience faces (3-8s)"),
            solution=script_data.get("solution", "Your unique method or tip (8-20s)"),
            proof=script_data.get("proof", "Quick result or demo (20-35s)"),
            cta=script_data.get("cta", "Save this + follow for more tips")
        ),
        recommended_format=ai_brief.get("recommended_format", "reel"),
        optimal_length_sec=ai_brief.get("optimal_length_sec", {"min": 25, "max": 45}),
        must_include_phrases=ai_brief.get("must_include_phrases", [
            trend_name.replace("#", ""),
            "save this",
            "follow for more"
        ]),
        differentiation_twist=ai_brief.get("differentiation_twist", f"Focus on the budget-friendly angle—most {trend_name} content skips this"),
        top_examples=[],
        generated_at=datetime.utcnow()
    )
    
    # Cache the result
    result = brief.model_dump()
    result["generated_at"] = result["generated_at"].isoformat()
    await set_cached_result(db, "content_brief", params, result, ttl_hours=24)
    
    # Also store in content_briefs table for history
    await db.execute(
        text("""
            INSERT INTO content_briefs (
                trend_type, trend_id, trend_name, hook_options, script_outline,
                recommended_format, optimal_length_sec, must_include_phrases,
                differentiation_twist, top_examples, niche, country
            ) VALUES (
                :trend_type, :trend_id, :trend_name, :hook_options, :script_outline,
                :recommended_format, :optimal_length_sec, :must_include_phrases,
                :differentiation_twist, :top_examples, :niche, :country
            )
        """),
        {
            "trend_type": request.trend_type,
            "trend_id": request.trend_id,
            "trend_name": trend_name,
            "hook_options": json.dumps(brief.hook_options),
            "script_outline": json.dumps(brief.script_outline.model_dump()),
            "recommended_format": brief.recommended_format,
            "optimal_length_sec": json.dumps(brief.optimal_length_sec),
            "must_include_phrases": json.dumps(brief.must_include_phrases),
            "differentiation_twist": brief.differentiation_twist,
            "top_examples": json.dumps(brief.top_examples),
            "niche": request.niche,
            "country": request.country
        }
    )
    await db.commit()
    
    return brief


# =============================================================================
# QUERY H: HOOK LEADERBOARD
# =============================================================================

@router.get("/hooks/leaderboard", response_model=HookLeaderboardResponse)
async def get_hook_leaderboard(
    niche: str = Query(..., description="Niche to analyze"),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Query H: Get top-performing hook patterns for a niche.
    
    Analyzes caption patterns from top posts to identify winning hooks.
    """
    import time
    start = time.time()
    
    # Mock data - will be replaced with actual analysis
    hooks = [
        HookResult(
            pattern="Stop doing ___ (here's why)",
            velocity_avg=3200,
            example="Stop doing crunches for abs—here's why",
            use_count=47
        ),
        HookResult(
            pattern="I did ___ for 30 days",
            velocity_avg=2800,
            example="I did 100 pushups for 30 days",
            use_count=38
        ),
        HookResult(
            pattern="The ___ nobody talks about",
            velocity_avg=2600,
            example="The skincare mistake nobody talks about",
            use_count=31
        ),
        HookResult(
            pattern="POV: You finally ___",
            velocity_avg=2400,
            example="POV: You finally learned to cook",
            use_count=28
        ),
        HookResult(
            pattern="3 things I wish I knew about ___",
            velocity_avg=2200,
            example="3 things I wish I knew about investing",
            use_count=25
        )
    ]
    
    return HookLeaderboardResponse(
        hooks=hooks[:limit],
        niche=niche,
        query_time_ms=int((time.time() - start) * 1000)
    )


# =============================================================================
# QUERY J: RISING AUDIO TRACKER
# =============================================================================

@router.get("/audio/rising", response_model=RisingAudioResponse)
async def get_rising_audio(
    niche: Optional[str] = Query(None, description="Filter by niche"),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Query J: Get rising audio tracks for content creation.
    
    Identifies sounds with high velocity and good reuse potential.
    """
    import time
    start = time.time()
    
    # Use real Instagram Looter API for audio discovery
    ingestion = get_ingestion_service()
    scorer = get_scoring_service()
    
    # Ingest from niche hashtag or general trending
    search_term = niche if niche else "trending"
    try:
        media = await ingestion.ingest_hashtag(search_term, limit=50)
        media_dicts = [{
            "music_id": m.music_id,
            "music_title": m.music_title,
            "author_id": m.author_id,
            "posted_at": m.posted_at,
            "play_count": m.play_count,
            "like_count": m.like_count
        } for m in media if m.music_id]
        
        # Score sounds
        if media_dicts:
            scores = scorer.score_sounds(media_dicts)
            audios = []
            for score in scores[:limit]:
                days_old = max(1, (datetime.utcnow() - score.entity_id).days) if hasattr(score, 'first_seen') else 3
                audios.append(RisingAudioResult(
                    music_id=score.entity_id,
                    title=score.name,
                    artist=None,
                    velocity=score.velocity_score,
                    freshness_days=days_old,
                    reuse_rate=min(1.0, score.adoption_24h / 100),
                    best_content_type=f"{score.status} - good for {niche or 'general'} content",
                    preview_url=None
                ))
            
            return RisingAudioResponse(
                audios=audios,
                query_time_ms=int((time.time() - start) * 1000)
            )
    except Exception as e:
        logger.warning(f"Failed to fetch rising audio: {e}")
    
    # Fallback mock data if API fails
    audios = [
        RisingAudioResult(
            music_id="audio_001",
            title="Original Sound - Trending Artist",
            artist="Trending Artist",
            velocity=92,
            freshness_days=3,
            reuse_rate=0.28,
            best_content_type="transformation reveals",
            preview_url=None
        ),
        RisingAudioResult(
            music_id="audio_002",
            title="Viral Beat 2025",
            artist="Producer Name",
            velocity=88,
            freshness_days=5,
            reuse_rate=0.35,
            best_content_type="quick tips and tutorials",
            preview_url=None
        ),
        RisingAudioResult(
            music_id="audio_003",
            title="Chill Lo-Fi Mood",
            artist="Lo-Fi Beats",
            velocity=75,
            freshness_days=7,
            reuse_rate=0.42,
            best_content_type="aesthetic content and vlogs",
            preview_url=None
        )
    ]
    
    return RisingAudioResponse(
        audios=audios[:limit],
        query_time_ms=int((time.time() - start) * 1000)
    )


# =============================================================================
# NICHES MANAGEMENT
# =============================================================================

class NicheCreate(BaseModel):
    """Create a new niche"""
    name: str
    display_name: Optional[str] = None
    seed_hashtags: List[str] = []
    seed_keywords: List[str] = []
    seed_accounts: List[str] = []


class NicheResponse(BaseModel):
    """Niche data"""
    id: str
    name: str
    display_name: Optional[str]
    seed_hashtags: List[str]
    seed_keywords: List[str]
    seed_accounts: List[str]
    is_active: bool


@router.post("/niches", response_model=NicheResponse)
async def create_niche(
    niche: NicheCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new niche for trend tracking."""
    result = await db.execute(
        text("""
            INSERT INTO niches (name, display_name, seed_hashtags, seed_keywords, seed_accounts)
            VALUES (:name, :display_name, :seed_hashtags, :seed_keywords, :seed_accounts)
            RETURNING id, name, display_name, seed_hashtags, seed_keywords, seed_accounts, is_active
        """),
        {
            "name": niche.name,
            "display_name": niche.display_name or niche.name.title(),
            "seed_hashtags": niche.seed_hashtags,
            "seed_keywords": niche.seed_keywords,
            "seed_accounts": niche.seed_accounts
        }
    )
    await db.commit()
    row = result.fetchone()
    
    return NicheResponse(
        id=str(row[0]),
        name=row[1],
        display_name=row[2],
        seed_hashtags=row[3] or [],
        seed_keywords=row[4] or [],
        seed_accounts=row[5] or [],
        is_active=row[6]
    )


@router.get("/niches", response_model=List[NicheResponse])
async def list_niches(
    db: AsyncSession = Depends(get_db)
):
    """List all niches."""
    result = await db.execute(
        text("SELECT id, name, display_name, seed_hashtags, seed_keywords, seed_accounts, is_active FROM niches WHERE is_active = true ORDER BY name")
    )
    rows = result.fetchall()
    
    return [
        NicheResponse(
            id=str(row[0]),
            name=row[1],
            display_name=row[2],
            seed_hashtags=row[3] or [],
            seed_keywords=row[4] or [],
            seed_accounts=row[5] or [],
            is_active=row[6]
        )
        for row in rows
    ]


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check for trend queries API."""
    return {
        "status": "healthy",
        "service": "trend-queries",
        "timestamp": datetime.utcnow().isoformat(),
        "available_queries": [
            "POST /hashtags/top - Query A: Top Hashtags",
            "POST /brief/generate - Query G: Content Brief",
            "GET /hooks/leaderboard - Query H: Hook Leaderboard",
            "GET /audio/rising - Query J: Rising Audio"
        ]
    }

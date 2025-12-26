"""
Trends API Endpoints
TrendTok-style trending content discovery for Instagram
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime

from services.event_bus import EventBus, Topics
from services.keyword_extraction_service import get_keyword_service
from services.trending_keywords_service import get_trending_keywords_service
from services.instagram.trend_crawler import get_trend_crawler
from services.instagram.velocity_engine import get_velocity_engine
from services.instagram.trend_cards_library import get_trend_cards_library

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class TrendingAudioResponse(BaseModel):
    audio_id: str
    title: str
    artist: str
    usage_count: int
    velocity_7d: float
    trending_score: float
    audio_url: Optional[str] = None  # Backend stream URL when available
    cover_url: Optional[str] = None  # Album/cover art URL


class TrendingHashtagResponse(BaseModel):
    tag: str
    media_count: int
    velocity_7d: float
    trending_score: float
    category: Optional[str]


class TrendingFormatResponse(BaseModel):
    name: str
    description: str
    format_type: str
    velocity_7d: float
    trending_score: float


class TrendCardResponse(BaseModel):
    id: str
    name: str
    description: str
    format_type: str
    velocity_7d: float
    trending_score: float
    region: Optional[str]


class CrawlJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class VelocityCalculationResponse(BaseModel):
    audio_updated: int
    hashtag_updated: int
    format_updated: int


# =============================================================================
# TRENDING CONTENT ENDPOINTS
# =============================================================================

@router.get("/audio")
async def get_trending_audio(
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    region: Optional[str] = Query(None, description="Region filter (e.g., USA, Canada)")
):
    """
    Get trending audio tracks on Instagram.
    
    Returns top audio tracks ranked by velocity and usage.
    If audio files are stored locally, includes stream URLs.
    """
    try:
        from services.audio_service import get_audio_service
        
        engine = get_velocity_engine()
        trending_audio = engine.get_trending_audio(limit, region)
        audio_service = get_audio_service()
        
        # Enhance with stored audio URLs
        enhanced_audio = []
        for audio in trending_audio:
            audio_data = dict(audio)
            # Check if we have this audio stored locally
            stored_path = audio_service.get_stored_audio_path(audio.get("audio_id", ""))
            if stored_path:
                audio_data["audio_url"] = f"/api/audio/stream/{audio.get('audio_id')}"
            enhanced_audio.append(TrendingAudioResponse(**audio_data))
        
        return {
            "count": len(enhanced_audio),
            "region": region,
            "audio": enhanced_audio
        }
    except Exception as e:
        logger.error(f"Error fetching trending audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hashtags")
async def get_trending_hashtags(
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    region: Optional[str] = Query(None, description="Region filter")
):
    """
    Get trending hashtags on Instagram.
    
    Returns top hashtags ranked by velocity and usage.
    """
    try:
        engine = get_velocity_engine()
        trending_hashtags = engine.get_trending_hashtags(limit, region)
        
        return {
            "count": len(trending_hashtags),
            "region": region,
            "hashtags": [
                TrendingHashtagResponse(**hashtag)
                for hashtag in trending_hashtags
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching trending hashtags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_trending_formats(
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    region: Optional[str] = Query(None, description="Region filter")
):
    """
    Get trending content formats on Instagram.
    
    Returns top content format templates ranked by velocity.
    """
    try:
        engine = get_velocity_engine()
        trending_formats = engine.get_trending_formats(limit, region)
        
        return {
            "count": len(trending_formats),
            "region": region,
            "formats": [
                TrendingFormatResponse(**format_data)
                for format_data in trending_formats
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching trending formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords")
async def get_trending_keywords(
    limit: int = Query(20, ge=1, le=100, description="Number of results per category")
):
    """
    Get trending keywords extracted from top-performing content.
    
    Returns keywords grouped by type:
    - hooks: Opening phrases ("POV:", "Nobody talks about...")
    - formats: Content format markers ("3 things...", "Day in the life")
    - hashtags: Trending hashtags
    - phrases: Common n-grams from captions
    - engagement: Engagement bait phrases
    """
    try:
        from services.competitor_service import get_competitor_service
        
        # Get captions from competitor content for analysis
        service = get_competitor_service()
        accounts = service.get_stored_accounts()
        
        all_captions = []
        
        # Fetch recent content from tracked competitors
        for username in accounts[:5]:  # Limit to 5 accounts
            reels = await service.fetch_user_reels(username, count=20)
            posts = await service.fetch_user_posts(username, count=20)
            
            for content in reels + posts:
                if content.caption:
                    all_captions.append({
                        "caption": content.caption,
                        "play_count": content.play_count or 0,
                        "like_count": content.like_count or 0
                    })
        
        # Extract keywords
        keyword_service = get_keyword_service()
        keywords = keyword_service.get_trending_keywords(all_captions, limit=limit)
        
        # Convert to JSON-serializable format
        result = {}
        for category, items in keywords.items():
            result[category] = [
                {
                    "keyword": item.keyword,
                    "type": item.keyword_type,
                    "frequency": item.frequency,
                    "avg_engagement": item.avg_engagement,
                    "examples": item.examples[:2] if item.examples else []
                }
                for item in items
            ]
        
        return {
            "total_captions_analyzed": len(all_captions),
            "keywords": result
        }
        
    except Exception as e:
        logger.error(f"Error fetching trending keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/niches/search")
async def search_niche(
    query: str = Query(..., description="Niche to search for (e.g., 'entrepreneur', 'fitness')"),
):
    """
    Search Instagram for a niche using RapidAPI.
    
    Returns related hashtags, top accounts, and places for the niche.
    """
    try:
        from services.niche_search_service import get_niche_search_service
        service = get_niche_search_service()
        
        niche_data = await service.discover_niche(query)
        
        return {
            "niche": niche_data.niche_name,
            "hashtags": niche_data.related_hashtags,
            "accounts": niche_data.top_accounts,
            "places": niche_data.places,
            "searched_at": niche_data.searched_at.isoformat() if niche_data.searched_at else None
        }
        
    except Exception as e:
        logger.error(f"Error searching niche: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/niches/discover")
async def discover_niches(
    niches: List[str] = Query(..., description="List of niches to discover")
):
    """
    Discover multiple niches at once.
    
    Returns aggregated data for each niche including hashtags, accounts, and places.
    """
    try:
        from services.niche_search_service import get_niche_search_service
        service = get_niche_search_service()
        
        results = await service.search_multiple_niches(niches)
        
        return {
            "count": len(results),
            "niches": [
                {
                    "niche": r.niche_name,
                    "hashtags": r.related_hashtags,
                    "accounts": r.top_accounts,
                    "places": r.places
                }
                for r in results
            ]
        }
        
    except Exception as e:
        logger.error(f"Error discovering niches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/niches")
async def get_trending_niches(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    region: Optional[str] = Query(None, description="Region filter")
):
    """
    Get trending content niches on Instagram.
    
    Returns top content niches/categories ranked by growth.
    Niches are derived from hashtag clusters and content patterns.
    """
    try:
        from sqlalchemy import create_engine, text
        import os
        
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        # Get niches from hashtag categories and trend cards
        niches = []
        
        with engine.connect() as conn:
            # Get top hashtag categories as niches
            result = conn.execute(text("""
                SELECT 
                    COALESCE(category, 'General') as name,
                    'Hashtag Category' as category,
                    COUNT(*) as post_count,
                    AVG(COALESCE(velocity_7d, 0)) as growth
                FROM ig_hashtags 
                WHERE category IS NOT NULL AND category != ''
                GROUP BY category
                ORDER BY AVG(COALESCE(trending_score, 0)) DESC
                LIMIT :limit
            """), {"limit": limit})
            
            for row in result:
                niches.append({
                    "name": row.name,
                    "category": row.category,
                    "post_count": row.post_count,
                    "growth": float(row.growth) if row.growth else 0.0
                })
            
            # If we don't have enough from hashtags, add from trend cards
            if len(niches) < limit:
                remaining = limit - len(niches)
                cards_result = conn.execute(text("""
                    SELECT 
                        name,
                        'Content Format' as category,
                        1 as post_count,
                        COALESCE(velocity_7d, 0) as growth
                    FROM trend_cards
                    WHERE velocity_7d > 0
                    ORDER BY trending_score DESC
                    LIMIT :limit
                """), {"limit": remaining})
                
                for row in cards_result:
                    niches.append({
                        "name": row.name,
                        "category": row.category,
                        "post_count": row.post_count,
                        "growth": float(row.growth) if row.growth else 0.0
                    })
        
        return {
            "count": len(niches),
            "region": region,
            "niches": niches
        }
    except Exception as e:
        logger.error(f"Error fetching trending niches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TREND CARDS ENDPOINTS
# =============================================================================

@router.get("/cards")
async def get_trend_cards():
    """
    Get all trend card templates.
    
    Returns the complete library of content format templates.
    """
    try:
        library = get_trend_cards_library()
        cards = library.get_all_cards()
        
        return {
            "count": len(cards),
            "cards": [
                TrendCardResponse(**card)
                for card in cards
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching trend cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cards/{format_type}")
async def get_trend_card_by_type(format_type: str):
    """
    Get a specific trend card by format type.
    
    Args:
        format_type: Format type (e.g., 'pov', 'tutorial', 'hook_style')
    """
    try:
        library = get_trend_cards_library()
        card = library.get_card_by_format_type(format_type)
        
        if not card:
            raise HTTPException(status_code=404, detail=f"Trend card not found: {format_type}")
        
        return TrendCardResponse(**card)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trend card {format_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cards/match")
async def match_content_to_cards(
    caption: str = Query(..., description="Content caption"),
    hashtags: List[str] = Query([], description="Content hashtags")
):
    """
    Match content to trend cards based on caption and hashtags.
    
    Returns matching trend cards with confidence scores.
    """
    try:
        library = get_trend_cards_library()
        matches = library.match_content_to_cards(caption, hashtags)
        
        return {
            "count": len(matches),
            "matches": matches
        }
    except Exception as e:
        logger.error(f"Error matching content to cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cards/seed")
async def seed_trend_cards():
    """
    Seed the database with initial trend card templates.
    
    Only needs to be run once during setup.
    """
    try:
        library = get_trend_cards_library()
        count = library.seed_initial_cards()
        
        return {
            "status": "success",
            "cards_seeded": count,
            "message": f"Seeded {count} trend cards"
        }
    except Exception as e:
        logger.error(f"Error seeding trend cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CRAWLING & CALCULATION ENDPOINTS
# =============================================================================

@router.post("/crawl/start")
async def start_trend_crawl(
    background_tasks: BackgroundTasks,
    reels_per_account: int = Query(50, ge=10, le=100, description="Reels to fetch per account")
):
    """
    Start a trend crawl of seed accounts.
    
    Crawls seed accounts to gather trend data in the background.
    """
    import uuid
    job_id = str(uuid.uuid4())
    
    async def crawl_task():
        try:
            # Emit crawl started event
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.TREND_SYNC_PROVIDER, {
                "job_id": job_id,
                "provider": "instagram",
                "reels_per_account": reels_per_account,
                "timestamp": datetime.now().isoformat()
            })
            
            crawler = get_trend_crawler()
            result = await crawler.crawl_all_seeds(reels_per_account)
            logger.info(f"Crawl job {job_id} completed: {result}")
            
            # Emit crawl completed event
            await event_bus.publish(Topics.TREND_RAW_INGESTED, {
                "job_id": job_id,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Crawl job {job_id} failed: {e}")
    
    background_tasks.add_task(crawl_task)
    
    return CrawlJobResponse(
        job_id=job_id,
        status="started",
        message=f"Crawling seed accounts with {reels_per_account} reels each"
    )


@router.post("/velocity/calculate")
async def calculate_velocities(
    lookback_days: int = Query(7, ge=1, le=30, description="Days to look back for comparison")
):
    """
    Calculate velocity (growth rate) for all trends.
    
    Compares current usage to historical data to determine growth.
    """
    try:
        engine = get_velocity_engine()
        result = engine.calculate_all_velocities(lookback_days)
        
        return VelocityCalculationResponse(**result)
    except Exception as e:
        logger.error(f"Error calculating velocities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scores/calculate")
async def calculate_trending_scores():
    """
    Calculate trending scores for all entities.
    
    Combines velocity, usage, and recency into a single trending score.
    """
    try:
        engine = get_velocity_engine()
        result = engine.calculate_trending_scores()
        
        return {
            "status": "success",
            "audio_updated": result["audio_updated"],
            "hashtag_updated": result["hashtag_updated"],
            "format_updated": result["format_updated"]
        }
    except Exception as e:
        logger.error(f"Error calculating trending scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/run")
async def run_full_pipeline(background_tasks: BackgroundTasks):
    """
    Run the complete trend discovery pipeline.
    
    1. Crawl seed accounts
    2. Calculate velocities
    3. Calculate trending scores
    
    Runs in the background and can take several minutes.
    """
    import uuid
    job_id = str(uuid.uuid4())
    
    async def pipeline_task():
        try:
            logger.info(f"Pipeline {job_id} started")
            
            # Step 1: Crawl
            crawler = get_trend_crawler()
            crawl_result = await crawler.crawl_all_seeds(50)
            logger.info(f"Crawl complete: {crawl_result}")
            
            # Step 2: Calculate velocities
            engine = get_velocity_engine()
            velocity_result = engine.calculate_all_velocities(7)
            logger.info(f"Velocities calculated: {velocity_result}")
            
            # Step 3: Calculate trending scores
            score_result = engine.calculate_trending_scores()
            logger.info(f"Trending scores calculated: {score_result}")
            
            logger.info(f"Pipeline {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline {job_id} failed: {e}")
    
    background_tasks.add_task(pipeline_task)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "Full trend discovery pipeline started",
        "steps": [
            "1. Crawling seed accounts",
            "2. Calculating velocities",
            "3. Calculating trending scores"
        ]
    }


@router.get("/stats")
async def get_trend_stats():
    """
    Get overall trend statistics.
    
    Returns counts and summary data for the trend system.
    """
    try:
        from sqlalchemy import create_engine, text
        import os
        
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Count entities
            audio_count = conn.execute(text("SELECT COUNT(*) FROM ig_audio")).scalar()
            hashtag_count = conn.execute(text("SELECT COUNT(*) FROM ig_hashtags")).scalar()
            format_count = conn.execute(text("SELECT COUNT(*) FROM trend_cards")).scalar()
            observation_count = conn.execute(text("SELECT COUNT(*) FROM trend_observations")).scalar()
            
            # Count trending entities
            trending_audio = conn.execute(text(
                "SELECT COUNT(*) FROM ig_audio WHERE trending_score > 0"
            )).scalar()
            trending_hashtags = conn.execute(text(
                "SELECT COUNT(*) FROM ig_hashtags WHERE trending_score > 0"
            )).scalar()
            trending_formats = conn.execute(text(
                "SELECT COUNT(*) FROM trend_cards WHERE trending_score > 0"
            )).scalar()
        
        return {
            "total_audio": audio_count,
            "total_hashtags": hashtag_count,
            "total_formats": format_count,
            "total_observations": observation_count,
            "trending_audio": trending_audio,
            "trending_hashtags": trending_hashtags,
            "trending_formats": trending_formats
        }
    except Exception as e:
        logger.error(f"Error fetching trend stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/velocity")
async def get_velocity_scores(
    trend_type: Optional[str] = Query(None, description="Filter by type: hashtag, sound, keyword"),
    sort_by: str = Query("trending_score", description="Sort by: trending_score, acceleration, velocity_7d"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get trends with velocity scores.
    
    Velocity = rate of change over time
    Acceleration = how fast velocity is increasing
    Trending Score = combined score factoring in volume + velocity + acceleration
    """
    try:
        from services.trend_velocity_service import get_trend_velocity_service
        service = get_trend_velocity_service()
        
        if sort_by == "acceleration":
            trends = service.get_top_accelerating(trend_type, limit)
        else:
            trends = service.get_top_trending(trend_type, limit)
        
        return {
            "count": len(trends),
            "sort_by": sort_by,
            "trends": [t.model_dump() for t in trends]
        }
    except Exception as e:
        logger.error(f"Error fetching velocity scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brief/{trend_type}/{trend_id}")
async def generate_trend_brief(
    trend_type: str,
    trend_id: str,
    trend_name: str = Query(..., description="Display name of the trend")
):
    """
    Generate an AI-powered brief for a specific trend.
    
    Returns:
    - Summary of the trend
    - Why it's trending
    - Content ideas
    - Example hooks
    - Target audience
    - Best posting time
    """
    try:
        from services.trend_brief_service import get_trend_brief_service
        from services.trend_velocity_service import get_trend_velocity_service
        
        brief_service = get_trend_brief_service()
        velocity_service = get_trend_velocity_service()
        
        # Get velocity data for context
        velocity_data = None
        velocities = velocity_service.get_top_trending(trend_type, 100)
        for v in velocities:
            if v.trend_id == trend_id:
                velocity_data = v.model_dump()
                break
        
        brief = await brief_service.generate_brief(
            trend_type=trend_type,
            trend_id=trend_id,
            trend_name=trend_name,
            velocity_data=velocity_data
        )
        
        if not brief:
            raise HTTPException(status_code=500, detail="Failed to generate brief")
        
        return brief.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefs")
async def get_trend_briefs(
    trend_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(20, ge=1, le=50)
):
    """Get all cached trend briefs"""
    try:
        from services.trend_brief_service import get_trend_brief_service
        service = get_trend_brief_service()
        
        briefs = service.get_all_briefs(trend_type, limit)
        
        return {
            "count": len(briefs),
            "briefs": [b.model_dump() for b in briefs]
        }
    except Exception as e:
        logger.error(f"Error fetching briefs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TRENDING KEYWORDS ENDPOINTS
# =============================================================================

@router.get("/trending-keywords")
async def get_trending_keywords(
    keyword_type: Optional[str] = Query(None, description="Filter by type: hook, cta, phrase"),
    niche: Optional[str] = Query(None, description="Filter by niche"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get trending keywords extracted from competitor content.
    Keywords include hooks, CTAs, and viral phrases.
    """
    try:
        service = get_trending_keywords_service()
        keywords = service.get_trending_keywords(keyword_type, niche, limit)
        
        return {
            "count": len(keywords),
            "keywords": keywords
        }
    except Exception as e:
        logger.error(f"Error fetching trending keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-keywords/hooks")
async def get_trending_hooks(limit: int = Query(10, ge=1, le=50)):
    """Get top trending hook phrases."""
    try:
        service = get_trending_keywords_service()
        hooks = service.get_hooks(limit)
        
        return {
            "count": len(hooks),
            "hooks": hooks
        }
    except Exception as e:
        logger.error(f"Error fetching hooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-keywords/ctas")
async def get_trending_ctas(limit: int = Query(10, ge=1, le=50)):
    """Get top trending call-to-action phrases."""
    try:
        service = get_trending_keywords_service()
        ctas = service.get_ctas(limit)
        
        return {
            "count": len(ctas),
            "ctas": ctas
        }
    except Exception as e:
        logger.error(f"Error fetching CTAs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trending-keywords/extract")
async def extract_keywords_from_competitors(background_tasks: BackgroundTasks):
    """
    Extract trending keywords from all competitor content.
    Processes captions to identify hooks, CTAs, and viral phrases.
    """
    try:
        service = get_trending_keywords_service()
        result = service.process_competitor_data()
        
        return result
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawler/populate-hashtags")
async def populate_hashtags_from_competitors():
    """
    Populate trending hashtags from competitor content.
    Extracts hashtags from downloaded content and calculates trends.
    """
    from pathlib import Path
    import json
    import re
    from collections import Counter
    
    accounts_dir = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts")
    if not accounts_dir.exists():
        return {"status": "no_data", "hashtags": []}
    
    hashtag_counter = Counter()
    hashtag_engagement = {}
    
    for account_dir in accounts_dir.iterdir():
        if not account_dir.is_dir() or account_dir.name.startswith('.'):
            continue
        
        # Process download_manifest.json (primary source)
        manifest_file = account_dir / "download_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file) as f:
                    manifest = json.load(f)
                videos = manifest.get("videos", {})
                for shortcode, data in videos.items():
                    if isinstance(data, dict):
                        caption = data.get("caption", "")
                        engagement = data.get("views", 0)
                        tags = re.findall(r'#(\w+)', caption)
                        for tag in tags:
                            tag_lower = tag.lower()
                            hashtag_counter[tag_lower] += 1
                            if tag_lower not in hashtag_engagement:
                                hashtag_engagement[tag_lower] = []
                            hashtag_engagement[tag_lower].append(engagement)
            except Exception as e:
                logger.error(f"Error processing manifest: {e}")
        
        # Process reels
        reels_file = account_dir / "reels" / "reels.json"
        if reels_file.exists():
            try:
                with open(reels_file) as f:
                    reels = json.load(f)
                for reel in reels:
                    caption = reel.get("caption", "")
                    engagement = reel.get("play_count", 0) + reel.get("like_count", 0)
                    tags = re.findall(r'#(\w+)', caption)
                    for tag in tags:
                        tag_lower = tag.lower()
                        hashtag_counter[tag_lower] += 1
                        if tag_lower not in hashtag_engagement:
                            hashtag_engagement[tag_lower] = []
                        hashtag_engagement[tag_lower].append(engagement)
            except Exception as e:
                logger.error(f"Error processing reels: {e}")
        
        # Process posts
        posts_file = account_dir / "posts" / "posts.json"
        if posts_file.exists():
            try:
                with open(posts_file) as f:
                    posts = json.load(f)
                for post in posts:
                    caption = post.get("caption", "")
                    engagement = post.get("like_count", 0) + post.get("comment_count", 0)
                    tags = re.findall(r'#(\w+)', caption)
                    for tag in tags:
                        tag_lower = tag.lower()
                        hashtag_counter[tag_lower] += 1
                        if tag_lower not in hashtag_engagement:
                            hashtag_engagement[tag_lower] = []
                        hashtag_engagement[tag_lower].append(engagement)
            except Exception as e:
                logger.error(f"Error processing posts: {e}")
    
    # Build trending hashtags list
    trending_hashtags = []
    for tag, count in hashtag_counter.most_common(50):
        avg_engagement = sum(hashtag_engagement.get(tag, [0])) / max(1, len(hashtag_engagement.get(tag, [1])))
        trending_hashtags.append({
            "tag": f"#{tag}",
            "media_count": count,
            "avg_engagement": round(avg_engagement),
            "trending_score": round(count * 10 + avg_engagement / 100, 1)
        })
    
    # Sort by trending score
    trending_hashtags.sort(key=lambda x: x["trending_score"], reverse=True)
    
    # Save to file
    output_path = accounts_dir.parent / "learnings" / "trending_hashtags.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump({
            "updated_at": __import__('datetime').datetime.now().isoformat(),
            "total": len(trending_hashtags),
            "hashtags": trending_hashtags
        }, f, indent=2)
    
    return {
        "status": "success",
        "hashtags_extracted": len(trending_hashtags),
        "top_hashtags": trending_hashtags[:10]
    }

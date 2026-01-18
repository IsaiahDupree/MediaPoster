"""
Twitter Campaign API Endpoints
Manage automated Twitter campaigns for Everreach, BlankLogo, and Apple App Kit
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from services.twitter_campaign_service import get_campaign_service
from services.twitter_campaign_scheduler import (
    get_twitter_campaign_scheduler,
    start_twitter_campaign_scheduler,
    stop_twitter_campaign_scheduler
)

router = APIRouter(prefix="/api/twitter-campaign", tags=["Twitter Campaign"])


# =============================================================================
# MODELS
# =============================================================================

class GenerateTweetsRequest(BaseModel):
    product_slug: Optional[str] = None  # If None, generate for all products
    count: int = 20


class ScheduleTweetsRequest(BaseModel):
    tweets: List[dict]
    start_time: Optional[str] = None
    interval_minutes: int = 24


class UpdateStyleRequest(BaseModel):
    sample_tweets: List[str] = []
    tone_keywords: List[str] = []
    avoid_words: List[str] = []
    style_description: str = ""


# =============================================================================
# SCHEDULER ENDPOINTS
# =============================================================================

@router.post("/scheduler/start")
async def start_scheduler():
    """Start the Twitter campaign scheduler."""
    try:
        scheduler = await start_twitter_campaign_scheduler()
        return {
            "status": "started",
            "message": "Twitter campaign scheduler is now running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the Twitter campaign scheduler."""
    try:
        await stop_twitter_campaign_scheduler()
        return {
            "status": "stopped",
            "message": "Twitter campaign scheduler has been stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status."""
    scheduler = get_twitter_campaign_scheduler()
    return {
        "is_running": scheduler.is_running,
        "check_count": scheduler._check_count,
        "last_daily_generation": str(scheduler._last_daily_generation) if scheduler._last_daily_generation else None
    }


# =============================================================================
# CAMPAIGN ENDPOINTS
# =============================================================================

@router.post("/generate")
async def generate_tweets(request: GenerateTweetsRequest, background_tasks: BackgroundTasks):
    """Generate tweets for one or all products."""
    service = get_campaign_service()
    
    if request.product_slug:
        product = service.get_product_by_slug(request.product_slug)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {request.product_slug}")
        
        tweets = service.generate_batch_tweets(product, count=request.count)
    else:
        # Generate for all products
        products = service.get_products()
        tweets = []
        for product in products:
            batch = service.generate_batch_tweets(product, count=request.count // len(products))
            tweets.extend(batch)
    
    return {
        "generated": len(tweets),
        "tweets": tweets
    }


@router.post("/schedule")
async def schedule_tweets(request: ScheduleTweetsRequest):
    """Schedule tweets for posting."""
    service = get_campaign_service()
    
    start_time = None
    if request.start_time:
        start_time = datetime.fromisoformat(request.start_time)
    
    scheduled_ids = service.schedule_tweets(
        tweets=request.tweets,
        start_time=start_time,
        interval_minutes=request.interval_minutes
    )
    
    return {
        "scheduled": len(scheduled_ids),
        "ids": scheduled_ids
    }


@router.post("/run-daily")
async def run_daily_campaign(background_tasks: BackgroundTasks):
    """Run the daily campaign generation and scheduling."""
    service = get_campaign_service()
    
    async def run_campaign():
        return await service.run_daily_campaign()
    
    # Run in background
    import asyncio
    result = await service.run_daily_campaign()
    
    return {
        "status": "completed",
        "result": result
    }


@router.post("/process-due")
async def process_due_tweets():
    """Process all tweets that are due for posting."""
    service = get_campaign_service()
    result = await service.process_due_tweets()
    return result


# =============================================================================
# PRODUCT ENDPOINTS
# =============================================================================

@router.get("/products")
async def get_products():
    """Get all campaign products."""
    service = get_campaign_service()
    products = service.get_products()
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "description": p.description,
                "website_url": p.website_url,
                "tagline": p.tagline,
                "key_features": p.key_features,
                "target_audience": p.target_audience,
                "voice_style": p.voice_style
            }
            for p in products
        ]
    }


@router.get("/products/{slug}")
async def get_product(slug: str):
    """Get a specific product."""
    service = get_campaign_service()
    product = service.get_product_by_slug(slug)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {slug}")
    
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "website_url": product.website_url,
        "tagline": product.tagline,
        "key_features": product.key_features,
        "target_audience": product.target_audience,
        "voice_style": product.voice_style
    }


@router.get("/products/{slug}/cycle")
async def get_product_cycle(slug: str):
    """Get the current campaign cycle for a product."""
    service = get_campaign_service()
    product = service.get_product_by_slug(slug)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {slug}")
    
    cycle = service.get_campaign_cycle(product.id)
    return {
        "product_slug": slug,
        "cycle": cycle
    }


# =============================================================================
# STYLE ENDPOINTS
# =============================================================================

@router.get("/style")
async def get_user_style():
    """Get the current user writing style."""
    service = get_campaign_service()
    style = service.get_user_style()
    return style


@router.put("/style")
async def update_user_style(request: UpdateStyleRequest):
    """Update the user writing style."""
    service = get_campaign_service()
    
    style_data = {
        "sample_tweets": request.sample_tweets,
        "tone_keywords": request.tone_keywords,
        "avoid_words": request.avoid_words,
        "style_description": request.style_description,
        "generated_style_prompt": ""  # Will be generated
    }
    
    service.update_user_style('default', style_data)
    
    return {"status": "updated", "style": style_data}


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics/tweets")
async def get_posted_tweets(
    product_slug: Optional[str] = None,
    days: int = 7,
    limit: int = 100
):
    """Get posted tweets with analytics."""
    service = get_campaign_service()
    tweets = service.get_posted_tweets(
        product_slug=product_slug,
        days=days,
        limit=limit
    )
    return {
        "tweets": tweets,
        "count": len(tweets)
    }


@router.get("/analytics/summary")
async def get_analytics_summary(product_slug: Optional[str] = None):
    """Get performance summary by awareness stage and content type."""
    service = get_campaign_service()
    summary = service.get_performance_summary(product_slug)
    return summary


@router.get("/analytics/scheduled")
async def get_scheduled_tweets(limit: int = 50):
    """Get upcoming scheduled tweets."""
    from sqlalchemy import create_engine, text
    import os
    
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"))
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT st.id, st.tweet_text, st.awareness_stage, st.content_type,
                   st.scheduled_time, st.status, cp.slug as product_slug
            FROM scheduled_tweets st
            JOIN campaign_products cp ON st.product_id = cp.id
            WHERE st.status = 'scheduled'
            ORDER BY st.scheduled_time ASC
            LIMIT :limit
        """), {"limit": limit})
        
        tweets = []
        for row in result.fetchall():
            tweets.append({
                "id": str(row[0]),
                "tweet_text": row[1],
                "awareness_stage": row[2],
                "content_type": row[3],
                "scheduled_time": str(row[4]) if row[4] else None,
                "status": row[5],
                "product_slug": row[6]
            })
        
        return {
            "scheduled_tweets": tweets,
            "count": len(tweets)
        }

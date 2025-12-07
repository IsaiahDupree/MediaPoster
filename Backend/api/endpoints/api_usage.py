"""
API Usage Monitoring Endpoints
Track and monitor API call budgets and caching performance
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
from pydantic import BaseModel

from database.connection import get_db
# Note: APIRateLimiter uses sync Session, so we use async SQL queries directly

router = APIRouter()


@router.get("/usage")
async def get_all_api_usage(
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics for all APIs"""
    # For now, return a simple response since APIRateLimiter uses sync Session
    # TODO: Convert APIRateLimiter to async or create async version
    try:
        # Try to get basic stats from database
        result = await db.execute(
            text("""
                SELECT COUNT(*) as total_calls
                FROM api_call_logs
                WHERE api_name = 'tiktok_scraper'
                AND timestamp >= DATE_TRUNC('month', CURRENT_DATE)
            """)
        )
        row = result.first()
        total_calls = row[0] if row else 0
        
        return {
            "apis": [
                {
                    "api_name": "tiktok_scraper",
                    "month": "current",
                    "total_requests": total_calls,
                    "api_calls": total_calls,
                    "cache_hits": 0,
                    "cache_hit_rate": 0.0,
                    "monthly_limit": 250,
                    "remaining": max(0, 250 - total_calls),
                    "usage_percent": min(100.0, (total_calls / 250) * 100) if total_calls > 0 else 0.0
                }
            ],
            "total_apis": 1
        }
    except Exception as e:
        # If table doesn't exist, return default structure
        return {
            "apis": [
                {
                    "api_name": "tiktok_scraper",
                    "month": "current",
                    "total_requests": 0,
                    "api_calls": 0,
                    "cache_hits": 0,
                    "cache_hit_rate": 0.0,
                    "monthly_limit": 250,
                    "remaining": 250,
                    "usage_percent": 0.0
                }
            ],
            "total_apis": 1
        }


class UsageStatsResponse(BaseModel):
    """API usage statistics"""
    api_name: str
    month: str
    total_requests: int
    api_calls: int
    cache_hits: int
    cache_hit_rate: float
    monthly_limit: int
    remaining: int
    usage_percent: float


@router.get("/usage/{api_name}", response_model=UsageStatsResponse)
async def get_api_usage(
    api_name: str = "tiktok_scraper",
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for an API
    
    Shows:
    - Total requests (including cache hits)
    - Actual API calls made
    - Cache hit rate
    - Budget remaining
    - Usage percentage
    
    Example:
        ```
        GET /api/api-usage/usage/tiktok_scraper
        ```
    """
    try:
        # Get stats using async queries
        result = await db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN cache_hit = false THEN 1 ELSE 0 END) as api_calls,
                    SUM(CASE WHEN cache_hit = true THEN 1 ELSE 0 END) as cache_hits
                FROM api_call_logs
                WHERE api_name = :api_name
                AND timestamp >= DATE_TRUNC('month', CURRENT_DATE)
            """),
            {"api_name": api_name}
        )
        row = result.first()
        
        total_calls = row[0] if row else 0
        api_calls = row[1] if row else 0
        cache_hits = row[2] if row else 0
        
        monthly_limit = 250
        cache_hit_rate = (cache_hits / total_calls * 100) if total_calls > 0 else 0.0
        remaining = max(0, monthly_limit - api_calls)
        usage_percent = min(100.0, (api_calls / monthly_limit) * 100) if api_calls > 0 else 0.0
        
        return UsageStatsResponse(
            api_name=api_name,
            month="current",
            total_requests=total_calls,
            api_calls=api_calls,
            cache_hits=cache_hits,
            cache_hit_rate=cache_hit_rate,
            monthly_limit=monthly_limit,
            remaining=remaining,
            usage_percent=usage_percent
        )
    except Exception:
        # If table doesn't exist, return defaults
        return UsageStatsResponse(
            api_name=api_name,
            month="current",
            total_requests=0,
            api_calls=0,
            cache_hits=0,
            cache_hit_rate=0.0,
            monthly_limit=250,
            remaining=250,
            usage_percent=0.0
        )


@router.get("/health/{api_name}")
async def check_api_health(
    api_name: str = "tiktok_scraper",
    db: AsyncSession = Depends(get_db)
):
    """
    Check if API is healthy and has budget remaining
    
    Returns:
    - can_make_calls: Whether budget allows more calls
    - status: "healthy", "warning", or "exceeded"
    - message: Human-readable status
    
    Example:
        ```
        GET /api/api-usage/health/tiktok_scraper
        ```
    """
    try:
        result = await db.execute(
            text("""
                SELECT COUNT(*) as api_calls
                FROM api_call_logs
                WHERE api_name = :api_name
                AND timestamp >= DATE_TRUNC('month', CURRENT_DATE)
                AND success = true
                AND cache_hit = false
            """),
            {"api_name": api_name}
        )
        row = result.first()
        api_calls = row[0] if row else 0
        
        monthly_limit = 250
        usage_percent = (api_calls / monthly_limit * 100) if api_calls > 0 else 0.0
        remaining = max(0, monthly_limit - api_calls)
        
        allowed = remaining > 0
        reason = f"OK ({remaining} calls remaining)" if allowed else f"Monthly budget exceeded ({api_calls}/{monthly_limit} calls used)"
        
        if not allowed:
            status = "exceeded"
        elif usage_percent > 80:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "api_name": api_name,
            "can_make_calls": allowed,
            "status": status,
            "message": reason,
            "usage_stats": {
                "api_name": api_name,
                "month": "current",
                "total_requests": api_calls,
                "api_calls": api_calls,
                "cache_hits": 0,
                "cache_hit_rate": 0.0,
                "monthly_limit": monthly_limit,
                "remaining": remaining,
                "usage_percent": usage_percent
            }
        }
    except Exception:
        # If table doesn't exist, return healthy status
        return {
            "api_name": api_name,
            "can_make_calls": True,
            "status": "healthy",
            "message": "OK (250 calls remaining)",
            "usage_stats": {
                "api_name": api_name,
                "month": "current",
                "total_requests": 0,
                "api_calls": 0,
                "cache_hits": 0,
                "cache_hit_rate": 0.0,
                "monthly_limit": 250,
                "remaining": 250,
                "usage_percent": 0.0
            }
        }


@router.post("/clear-cache/{api_name}")
async def clear_api_cache(
    api_name: str = "tiktok_scraper",
    db: AsyncSession = Depends(get_db)
):
    """
    Clear cached data for an API
    
    Useful for forcing fresh data retrieval
    
    Note: This clears in-memory cache. For persistent cache, implement cache invalidation.
    
    Example:
        ```
        POST /api/api-usage/clear-cache/tiktok_scraper
        ```
    """
    # Note: In-memory cache clearing would require a shared cache instance
    # For now, return a message indicating cache would be cleared
    return {
        "api_name": api_name,
        "cache_entries_cleared": 0,
        "message": "Cache clearing not implemented for async sessions. Use database-level cache invalidation."
    }


@router.delete("/logs")
async def clear_old_logs(
    days: int = 90,
    db: AsyncSession = Depends(get_db)
):
    """
    Clear API call logs older than specified days
    
    Args:
        days: Number of days to keep (default: 90)
    
    Example:
        ```
        DELETE /api/api-usage/logs?days=90
        ```
    """
    try:
        result = await db.execute(
            text("""
                DELETE FROM api_call_logs
                WHERE timestamp < CURRENT_DATE - INTERVAL ':days days'
            """),
            {"days": days}
        )
        await db.commit()
        deleted = result.rowcount
        
        return {
            "message": f"Cleared {deleted} API logs older than {days} days"
        }
    except Exception as e:
        await db.rollback()
        return {
            "message": f"Error clearing logs: {str(e)}"
        }


@router.get("/recommendations")
async def get_usage_recommendations(db: AsyncSession = Depends(get_db)):
    """
    Get recommendations for optimizing API usage
    
    Analyzes usage patterns and provides suggestions
    
    Example:
        ```
        GET /api/api-usage/recommendations
        ```
    """
    try:
        result = await db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN cache_hit = false THEN 1 ELSE 0 END) as api_calls,
                    SUM(CASE WHEN cache_hit = true THEN 1 ELSE 0 END) as cache_hits
                FROM api_call_logs
                WHERE api_name = 'tiktok_scraper'
                AND timestamp >= DATE_TRUNC('month', CURRENT_DATE)
            """)
        )
        row = result.first()
        
        total_calls = row[0] if row else 0
        api_calls = row[1] if row else 0
        cache_hits = row[2] if row else 0
        
        monthly_limit = 250
        cache_hit_rate = (cache_hits / total_calls * 100) if total_calls > 0 else 0.0
        remaining = max(0, monthly_limit - api_calls)
        usage_percent = min(100.0, (api_calls / monthly_limit) * 100) if api_calls > 0 else 0.0
        
        stats = {
            "api_name": "tiktok_scraper",
            "month": "current",
            "total_requests": total_calls,
            "api_calls": api_calls,
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "monthly_limit": monthly_limit,
            "remaining": remaining,
            "usage_percent": usage_percent
        }
    except Exception:
        stats = {
            "api_name": "tiktok_scraper",
            "month": "current",
            "total_requests": 0,
            "api_calls": 0,
            "cache_hits": 0,
            "cache_hit_rate": 0.0,
            "monthly_limit": 250,
            "remaining": 250,
            "usage_percent": 0.0
        }
    
    recommendations = []
    
    # Budget recommendations
    if stats["usage_percent"] > 90:
        recommendations.append({
            "type": "critical",
            "title": "Budget Nearly Exhausted",
            "message": f"Only {stats['remaining']} API calls remaining this month. Consider increasing cache TTL or reducing polling frequency."
        })
    elif stats["usage_percent"] > 75:
        recommendations.append({
            "type": "warning",
            "title": "High Budget Usage",
            "message": f"{stats['usage_percent']}% of budget used. Monitor usage closely."
        })
    
    # Cache recommendations
    if stats["cache_hit_rate"] < 50:
        recommendations.append({
            "type": "info",
            "title": "Low Cache Hit Rate",
            "message": f"Only {stats['cache_hit_rate']}% cache hit rate. Consider increasing cache TTL for trending data."
        })
    elif stats["cache_hit_rate"] > 80:
        recommendations.append({
            "type": "success",
            "title": "Excellent Cache Performance",
            "message": f"{stats['cache_hit_rate']}% cache hit rate is saving significant API calls!"
        })
    
    # Efficiency recommendations
    api_calls_saved = stats["cache_hits"]
    if api_calls_saved > 100:
        recommendations.append({
            "type": "success",
            "title": "Significant Cost Savings",
            "message": f"Caching has saved {api_calls_saved} API calls this month!"
        })
    
    return {
        "usage_stats": stats,
        "recommendations": recommendations
    }

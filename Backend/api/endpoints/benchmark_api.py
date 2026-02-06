"""
Performance Benchmark API Endpoints
Compare user's Instagram metrics against competitors and industry averages.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from loguru import logger

from services.benchmark_service import get_benchmark_service

router = APIRouter(prefix="/api/benchmark", tags=["Performance Benchmarks"])


class RunBenchmarkRequest(BaseModel):
    """Request to run a benchmark comparison"""
    followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    avg_views: Optional[float] = None
    avg_likes: Optional[float] = None
    posting_frequency: Optional[float] = None  # posts per week
    follower_growth_pct: Optional[float] = None  # 30-day %


@router.get("/health")
async def health_check():
    """Health check for benchmark service"""
    return {
        "status": "healthy",
        "service": "performance-benchmarks",
    }


@router.post("/run")
async def run_benchmark(request: RunBenchmarkRequest = RunBenchmarkRequest()):
    """
    Run a performance benchmark comparison.
    
    Compares your metrics against:
    - Tracked competitor averages
    - Industry benchmarks for your account tier
    
    Pass your metrics for a personalized comparison.
    If no metrics provided, returns competitor-only analysis.
    """
    service = get_benchmark_service()

    user_metrics = {}
    if request.followers is not None:
        user_metrics["followers"] = request.followers
    if request.engagement_rate is not None:
        user_metrics["engagement_rate"] = request.engagement_rate
    if request.avg_views is not None:
        user_metrics["avg_views"] = request.avg_views
    if request.avg_likes is not None:
        user_metrics["avg_likes"] = request.avg_likes
    if request.posting_frequency is not None:
        user_metrics["posting_frequency"] = request.posting_frequency
    if request.follower_growth_pct is not None:
        user_metrics["follower_growth_pct"] = request.follower_growth_pct

    try:
        result = await service.run_benchmark(user_metrics=user_metrics or None)
        return {
            "status": "completed",
            "result": result.model_dump(),
        }
    except Exception as e:
        logger.error(f"Error running benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_benchmark():
    """Get the most recent benchmark results"""
    service = get_benchmark_service()
    result = service.get_latest_benchmark()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No benchmarks found. POST /api/benchmark/run first.",
        )

    return result.model_dump()


@router.get("/industry-averages")
async def get_industry_averages(
    followers: int = 0,
):
    """
    Get industry average benchmarks for a given follower count tier.
    
    Tiers:
    - micro: < 15K followers
    - small: 15K - 100K
    - medium: 100K - 500K
    - large: 500K+
    """
    service = get_benchmark_service()
    tier = service._get_account_tier(followers) if followers > 0 else "small"

    from services.benchmark_service import INDUSTRY_BENCHMARKS

    averages = {}
    for metric, tiers in INDUSTRY_BENCHMARKS.items():
        averages[metric] = tiers.get(tier, tiers.get("default", 0))

    return {
        "tier": tier,
        "follower_range": {
            "micro": "< 15K",
            "small": "15K - 100K",
            "medium": "100K - 500K",
            "large": "500K+",
        }.get(tier, "unknown"),
        "benchmarks": averages,
    }

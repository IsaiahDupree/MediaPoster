"""
Metrics Scheduler API
Configure check-back periods and view line graph data for content metrics.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from services.metrics_scheduler import (
    get_scheduler,
    SyncInterval,
    run_scheduled_sync,
    start_scheduler_loop,
)

router = APIRouter(prefix="/api/metrics-scheduler", tags=["Metrics Scheduler"])


# ============================================================================
# MODELS
# ============================================================================

class PlatformConfigUpdate(BaseModel):
    """Update configuration for a platform"""
    enabled: Optional[bool] = None
    interval: Optional[str] = None  # hourly, 4h, 6h, 12h, daily, weekly


class SchedulerStatus(BaseModel):
    """Current scheduler status"""
    is_running: bool
    platforms: Dict[str, Dict[str, Any]]
    next_syncs: List[Dict[str, Any]]
    recent_syncs: List[Dict[str, Any]]


class LineGraphDataPoint(BaseModel):
    """Single data point for line graph"""
    timestamp: str
    value: float


class LineGraphData(BaseModel):
    """Data for rendering line graphs"""
    metric: str
    post_id: str
    platform: str
    title: str
    data_points: List[LineGraphDataPoint]
    current_value: float
    total_change: float
    percent_change: float
    avg_daily_change: float
    min_value: float
    max_value: float
    trend: str  # up, down, stable


class MultiMetricLineGraph(BaseModel):
    """Multiple metrics for a single post"""
    post_id: str
    platform: str
    title: str
    metrics: Dict[str, LineGraphData]


# ============================================================================
# SCHEDULER ENDPOINTS
# ============================================================================

@router.get("/status", response_model=SchedulerStatus)
async def get_scheduler_status():
    """Get current scheduler status and configuration"""
    scheduler = get_scheduler()
    configs = scheduler.get_all_configs()
    
    # Get next syncs sorted by time
    next_syncs = []
    for platform, config in configs.items():
        if config.get("enabled") and config.get("next_sync"):
            next_syncs.append({
                "platform": platform,
                "next_sync": config["next_sync"],
                "interval": config["interval"],
            })
    next_syncs.sort(key=lambda x: x["next_sync"])
    
    return SchedulerStatus(
        is_running=scheduler.is_running,
        platforms=configs,
        next_syncs=next_syncs[:5],
        recent_syncs=scheduler.get_sync_history(limit=10),
    )


@router.put("/platform/{platform}")
async def update_platform_config(platform: str, config: PlatformConfigUpdate):
    """Update sync configuration for a specific platform"""
    scheduler = get_scheduler()
    
    if platform not in scheduler.configs:
        raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    if config.enabled is not None:
        scheduler.enable_platform(platform, config.enabled)
    
    if config.interval:
        try:
            interval = SyncInterval(config.interval)
            scheduler.set_interval(platform, interval)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Must be one of: hourly, 4h, 6h, 12h, daily, weekly"
            )
    
    return {
        "platform": platform,
        "config": scheduler.get_all_configs()[platform],
    }


@router.post("/sync-now")
async def trigger_sync_now(
    background_tasks: BackgroundTasks,
    platform: Optional[str] = None
):
    """Manually trigger a sync immediately"""
    scheduler = get_scheduler()
    
    if platform:
        if platform not in scheduler.configs:
            raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
        # Set next sync to now to trigger immediately
        scheduler.configs[platform].next_sync = datetime.utcnow()
        platforms = [platform]
    else:
        # Trigger all platforms
        for p in scheduler.configs.values():
            p.next_sync = datetime.utcnow()
        platforms = list(scheduler.configs.keys())
    
    # Run sync in background
    background_tasks.add_task(run_scheduled_sync)
    
    return {
        "message": f"Sync triggered for: {', '.join(platforms)}",
        "platforms": platforms,
    }


@router.get("/history")
async def get_sync_history(
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Get sync history"""
    scheduler = get_scheduler()
    return {
        "history": scheduler.get_sync_history(platform=platform, limit=limit),
    }


@router.get("/intervals")
async def get_available_intervals():
    """Get list of available sync intervals"""
    return {
        "intervals": [
            {"value": "hourly", "label": "Every hour", "seconds": 3600},
            {"value": "4h", "label": "Every 4 hours", "seconds": 14400},
            {"value": "6h", "label": "Every 6 hours", "seconds": 21600},
            {"value": "12h", "label": "Every 12 hours", "seconds": 43200},
            {"value": "daily", "label": "Once per day", "seconds": 86400},
            {"value": "weekly", "label": "Once per week", "seconds": 604800},
        ],
        "recommended": {
            "instagram": "4h",
            "tiktok": "4h",
            "youtube": "6h",
            "facebook": "6h",
            "linkedin": "12h",
            "twitter": "4h",
            "threads": "6h",
            "bluesky": "6h",
            "pinterest": "daily",
        }
    }


# ============================================================================
# LINE GRAPH DATA ENDPOINTS
# ============================================================================

@router.get("/line-graph/{post_id}", response_model=MultiMetricLineGraph)
async def get_line_graph_data(
    post_id: str,
    days: int = Query(30, ge=1, le=365),
    metrics: List[str] = Query(default=["views", "likes", "comments", "shares"])
):
    """
    Get line graph data for a specific post.
    Returns time-series data for multiple metrics.
    """
    from api.content_growth import metrics_history, generate_mock_history
    
    # Get or generate history
    if post_id not in metrics_history:
        metrics_history[post_id] = generate_mock_history(post_id, days)
    
    history = metrics_history[post_id][-days:]
    
    if not history:
        raise HTTPException(status_code=404, detail="No metrics data found")
    
    # Build line graph data for each metric
    metric_data = {}
    
    for metric in metrics:
        values = [getattr(h, metric, 0) for h in history]
        timestamps = [h.timestamp.isoformat() for h in history]
        
        if not values:
            continue
        
        current = values[-1]
        start = values[0]
        total_change = current - start
        percent_change = ((current - start) / max(start, 1)) * 100
        avg_daily = total_change / max(len(values), 1)
        
        # Determine trend
        if len(values) >= 7:
            recent_avg = sum(values[-7:]) / 7
            earlier_avg = sum(values[:7]) / 7
            if recent_avg > earlier_avg * 1.1:
                trend = "up"
            elif recent_avg < earlier_avg * 0.9:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        metric_data[metric] = LineGraphData(
            metric=metric,
            post_id=post_id,
            platform="unknown",  # Would be fetched from DB
            title=f"Post {post_id[:8]}",
            data_points=[
                LineGraphDataPoint(timestamp=ts, value=val)
                for ts, val in zip(timestamps, values)
            ],
            current_value=current,
            total_change=total_change,
            percent_change=round(percent_change, 2),
            avg_daily_change=round(avg_daily, 2),
            min_value=min(values),
            max_value=max(values),
            trend=trend,
        )
    
    return MultiMetricLineGraph(
        post_id=post_id,
        platform="unknown",
        title=f"Post {post_id[:8]}",
        metrics=metric_data,
    )


@router.get("/line-graph-aggregate")
async def get_aggregate_line_graph(
    platform: Optional[str] = None,
    metric: str = Query("views", description="Metric to aggregate"),
    days: int = Query(30, ge=1, le=365),
    aggregation: str = Query("sum", description="sum, avg, max"),
):
    """
    Get aggregated line graph data across all posts.
    Shows total views/likes/etc. per day across all content.
    """
    from api.content_growth import metrics_history, generate_mock_history
    
    # In production, fetch all posts for the platform from DB
    # For now, use mock data
    
    # Generate sample post IDs
    import random
    sample_posts = [f"post-{i}" for i in range(5)]
    
    # Aggregate data by date
    daily_data: Dict[str, List[float]] = {}
    
    for post_id in sample_posts:
        if post_id not in metrics_history:
            metrics_history[post_id] = generate_mock_history(post_id, days)
        
        for snapshot in metrics_history[post_id][-days:]:
            date_key = snapshot.timestamp.strftime("%Y-%m-%d")
            value = getattr(snapshot, metric, 0)
            
            if date_key not in daily_data:
                daily_data[date_key] = []
            daily_data[date_key].append(value)
    
    # Calculate aggregated values
    result_data = []
    for date_key in sorted(daily_data.keys()):
        values = daily_data[date_key]
        if aggregation == "sum":
            agg_value = sum(values)
        elif aggregation == "avg":
            agg_value = sum(values) / len(values) if values else 0
        elif aggregation == "max":
            agg_value = max(values) if values else 0
        else:
            agg_value = sum(values)
        
        result_data.append({
            "date": date_key,
            "value": round(agg_value, 2),
            "count": len(values),
        })
    
    # Calculate summary stats
    values = [d["value"] for d in result_data]
    
    return {
        "metric": metric,
        "aggregation": aggregation,
        "platform": platform or "all",
        "days": days,
        "data": result_data,
        "summary": {
            "total": sum(values),
            "average": sum(values) / len(values) if values else 0,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "trend": "up" if len(values) >= 2 and values[-1] > values[0] else "down",
        }
    }


@router.get("/compare-posts")
async def compare_posts_line_graph(
    post_ids: List[str] = Query(..., description="Post IDs to compare"),
    metric: str = Query("views"),
    days: int = Query(30, ge=1, le=365),
):
    """
    Get line graph data for comparing multiple posts side by side.
    """
    from api.content_growth import metrics_history, generate_mock_history
    
    comparison = []
    
    for post_id in post_ids[:5]:  # Max 5 posts
        if post_id not in metrics_history:
            metrics_history[post_id] = generate_mock_history(post_id, days)
        
        history = metrics_history[post_id][-days:]
        
        data_points = [
            {
                "date": h.timestamp.strftime("%m/%d"),
                "timestamp": h.timestamp.isoformat(),
                "value": getattr(h, metric, 0),
            }
            for h in history
        ]
        
        values = [d["value"] for d in data_points]
        
        comparison.append({
            "post_id": post_id,
            "label": f"Post {post_id[:8]}",
            "color": [
                "#8B5CF6",  # violet
                "#EC4899",  # pink
                "#3B82F6",  # blue
                "#10B981",  # emerald
                "#F59E0B",  # amber
            ][len(comparison) % 5],
            "data": data_points,
            "current": values[-1] if values else 0,
            "growth": round(((values[-1] - values[0]) / max(values[0], 1)) * 100, 1) if values else 0,
        })
    
    return {
        "metric": metric,
        "days": days,
        "posts": comparison,
    }

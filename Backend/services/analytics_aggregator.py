from uuid import UUID
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel

class ContentRollup(BaseModel):
    content_id: UUID
    total_views: int = 0
    total_impressions: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_saves: int = 0
    total_clicks: int = 0
    avg_watch_time_seconds: float = 0.0
    global_sentiment: float = 0.0
    best_platform: Optional[str] = None
    last_updated_at: datetime

async def aggregate_metrics_for_content(content_id: UUID) -> ContentRollup:
    """
    Compute aggregated metrics (rollups) for a single content item
    across all its platform variants.
    """
    # TODO: Fetch all latest metrics snapshots for this content_id from DB
    # For now, mock the data
    
    mock_metrics = [
        {"platform": "instagram", "views": 1000, "likes": 50, "sentiment": 0.8},
        {"platform": "tiktok", "views": 5000, "likes": 200, "sentiment": 0.5},
        {"platform": "linkedin", "views": 200, "likes": 10, "sentiment": 0.9},
    ]
    
    rollup = ContentRollup(
        content_id=content_id,
        last_updated_at=datetime.now()
    )
    
    total_sentiment_weighted = 0.0
    total_interactions = 0
    
    best_platform_score = -1.0
    
    for m in mock_metrics:
        rollup.total_views += m["views"]
        rollup.total_likes += m["likes"]
        
        # Simple weighted sentiment
        interactions = m["likes"] # + comments + shares...
        total_interactions += interactions
        total_sentiment_weighted += m["sentiment"] * interactions
        
        # Determine best platform (simple view-based score for now)
        score = m["views"] # Could be engagement rate, etc.
        if score > best_platform_score:
            best_platform_score = score
            rollup.best_platform = m["platform"]
            
    if total_interactions > 0:
        rollup.global_sentiment = total_sentiment_weighted / total_interactions
        
    # TODO: Save rollup to DB
    print(f"Computed rollup for {content_id}: {rollup.total_views} views, Best: {rollup.best_platform}")
    
    return rollup

async def run_nightly_aggregation():
    """
    Job to update rollups for all active content
    """
    # TODO: Fetch all content IDs that need updating
    content_ids = [UUID("12345678-1234-5678-1234-567812345678")]
    
    for cid in content_ids:
        await aggregate_metrics_for_content(cid)

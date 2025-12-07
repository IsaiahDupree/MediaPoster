from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.connection import get_db

router = APIRouter()

@router.get("/widgets")
async def get_dashboard_widgets(db: AsyncSession = Depends(get_db)):
    """Get all dashboard widget data in one call"""
    
    # Recent top-performing content
    recent_content_query = text("""
        SELECT 
            ci.id,
            ci.title,
            ci.thumbnail_url,
            ci.created_at,
            COALESCE(cr.total_views, 0) as total_views,
            COALESCE(cr.total_likes, 0) as total_likes,
            COALESCE(cr.total_comments, 0) as total_comments,
            CASE 
                WHEN COALESCE(cr.total_views, 0) > 0 
                THEN ((COALESCE(cr.total_likes, 0) + 
                       COALESCE(cr.total_comments, 0)) * 100.0 / 
                      COALESCE(cr.total_views, 0))
                ELSE 0
            END as engagement_rate
        FROM content_items ci
        LEFT JOIN content_rollups cr ON ci.id = cr.content_id
        WHERE ci.created_at >= NOW() - INTERVAL '7 days'
        ORDER BY engagement_rate DESC NULLS LAST
        LIMIT 5
    """)
    
    # Segment summary
    segments_query = text("""
        SELECT 
            s.id,
            s.name,
            s.description,
            COUNT(DISTINCT sm.person_id) as member_count
        FROM segments s
        LEFT JOIN segment_members sm ON s.id = sm.segment_id
        GROUP BY s.id, s.name, s.description
        ORDER BY member_count DESC
        LIMIT 5
    """)
    
    # Execute queries
    recent_content_result = await db.execute(recent_content_query)
    segments_result = await db.execute(segments_query)
    
    recent_content = [
        {
            "id": row.id,
            "title": row.title or "Untitled",
            "thumbnail_url": row.thumbnail_url,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "total_views": int(row.total_views) if row.total_views else 0,
            "total_likes": int(row.total_likes) if row.total_likes else 0,
            "engagement_rate": float(row.engagement_rate) if row.engagement_rate else 0
        }
        for row in recent_content_result
    ]
    
    segments = [
        {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "member_count": int(row.member_count) if row.member_count else 0
        }
        for row in segments_result
    ]
    
    # AI Alerts/Insights (mock for now, can be enhanced later)
    ai_alerts = [
        {
            "type": "opportunity",
            "title": "High engagement on recent content",
            "action": "Your last 5 posts averaged 5.2% engagement - keep it up!",
            "priority": "low",
            "icon": "trending-up"
        },
        {
            "type": "insight",
            "title": f"{len(segments)} active segments",
            "action": "Generate content briefs for your top segments",
            "priority": "medium",
            "icon": "users"
        }
    ]
    
    # Add dynamic alerts based on data
    if recent_content:
        avg_engagement = sum(item["engagement_rate"] for item in recent_content) / len(recent_content)
        if avg_engagement > 5:
            ai_alerts.insert(0, {
                "type": "success",
                "title": f"Engagement up to {avg_engagement:.1f}%",
                "action": "Your content is resonating well with your audience",
                "priority": "high",
                "icon": "check-circle"
            })
    
    return {
        "recent_content": recent_content,
        "upcoming_posts": [],  # Will implement when calendar/scheduling is ready
        "segments": segments,
        "ai_alerts": ai_alerts
    }


@router.get("/north-star")
async def get_north_star_metrics(db: AsyncSession = Depends(get_db)):
    """Get North Star metrics for dashboard"""
    
    # Weekly Engaged Reach
    engaged_reach_query = text("""
        SELECT COUNT(DISTINCT person_id) as reach
        FROM person_events
        WHERE occurred_at >= NOW() - INTERVAL '7 days'
        AND event_type IN ('comment', 'like', 'share', 'click')
    """)
    
    # Content Leverage Score (variants per content item)
    leverage_query = text("""
        SELECT COALESCE(AVG(variant_count), 0) as leverage_score
        FROM (
            SELECT content_id, COUNT(*) as variant_count
            FROM content_variants
            GROUP BY content_id
        ) as counts
    """)
    
    # Warm Lead Flow
    warm_leads_query = text("""
        SELECT COUNT(*) as warm_leads
        FROM person_insights
        WHERE warmth_score >= 70
        AND last_active_at >= NOW() - INTERVAL '7 days'
    """)
    
    # Execute queries
    engaged_reach_result = await db.execute(engaged_reach_query)
    leverage_result = await db.execute(leverage_query)
    warm_leads_result = await db.execute(warm_leads_query)
    
    engaged_reach = engaged_reach_result.scalar() or 0
    leverage_score = leverage_result.scalar() or 0
    warm_leads = warm_leads_result.scalar() or 0
    
    return {
        "weekly_engaged_reach": int(engaged_reach),
        "content_leverage_score": float(leverage_score),
        "warm_lead_flow": int(warm_leads),
        "trends": {
            "engaged_reach_trend": "+18%",  # Mock - calculate from historical data
            "leverage_trend": "stable",
            "warm_leads_trend": "+5"
        }
    }

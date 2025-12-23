"""
Trend Opportunities API
========================
Endpoints for managing trend opportunities that feed into Narrative Builder & Experiments.
Trends act as "opportunity signals" that trigger new content slots, experiment hypotheses,
and scheduling priority changes.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import text
import logging
import uuid
import json

from database import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class TrendItemCreate(BaseModel):
    source: str = Field(..., description="tiktok, instagram, youtube, appstore, playstore")
    entity_type: str = Field(..., description="topic, keyword, sound, hashtag, creator, app")
    entity_id: str
    entity_key: str
    display_name: Optional[str] = None
    region: str = "US"
    language: str = "en"
    platform: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    velocity: Optional[float] = None
    acceleration: Optional[float] = None
    rank: Optional[int] = None
    volume: Optional[int] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class OpportunityScore(BaseModel):
    """The scoring model for trend opportunities."""
    velocity_score: float = 0
    acceleration_score: float = 0
    relevance_to_brand: float = 0
    content_fit: float = 0
    monetization_fit: float = 0
    fatigue_penalty: float = 0
    competition_penalty: float = 0
    risk_penalty: float = 0
    
    @property
    def total_score(self) -> float:
        """Calculate OpportunityScore using weighted formula."""
        raw_score = (
            0.35 * self.velocity_score +
            0.20 * self.acceleration_score +
            0.20 * self.relevance_to_brand +
            0.15 * self.content_fit +
            0.10 * self.monetization_fit
        )
        penalties = self.fatigue_penalty + self.competition_penalty + self.risk_penalty
        return max(0, min(100, raw_score - penalties))


class OpportunityCreate(BaseModel):
    cluster_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    scores: OpportunityScore
    why: Dict[str, Any] = Field(default_factory=dict)
    matching_asset_ids: List[str] = Field(default_factory=list)
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)
    window_hours: int = 48
    priority: str = "medium"


class TrendBriefCreate(BaseModel):
    opportunity_id: str
    title: str
    summary: Optional[str] = None
    trend_context: Dict[str, Any] = Field(default_factory=dict)
    hook_options: List[Dict[str, Any]] = Field(default_factory=list)
    caption_options: List[Dict[str, Any]] = Field(default_factory=list)
    format_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_assets: List[Dict[str, Any]] = Field(default_factory=list)
    experiment_hypotheses: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# HELPER: Ensure tables exist
# =============================================================================

async def ensure_trend_tables():
    """Create trend tables if they don't exist."""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # Check if trend_opportunities exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'trend_opportunities'
            )
        """)).fetchone()
        
        if not result[0]:
            # Create minimal tables for now (full schema from migration)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trend_items (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source VARCHAR(50) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(255) NOT NULL,
                    entity_key VARCHAR(255) NOT NULL,
                    display_name VARCHAR(500),
                    region VARCHAR(10) DEFAULT 'US',
                    platform VARCHAR(50),
                    timestamp_bucket TIMESTAMPTZ DEFAULT NOW(),
                    metrics JSONB DEFAULT '{}'::jsonb,
                    velocity DECIMAL(10,4),
                    acceleration DECIMAL(10,4),
                    rank INTEGER,
                    volume BIGINT,
                    context JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trend_opportunities (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    workspace_id UUID,
                    cluster_id UUID,
                    title VARCHAR(500),
                    description TEXT,
                    opportunity_score DECIMAL(5,2),
                    velocity_score DECIMAL(5,2),
                    acceleration_score DECIMAL(5,2),
                    relevance_to_brand DECIMAL(5,2),
                    content_fit DECIMAL(5,2),
                    monetization_fit DECIMAL(5,2),
                    fatigue_penalty DECIMAL(5,2) DEFAULT 0,
                    competition_penalty DECIMAL(5,2) DEFAULT 0,
                    risk_penalty DECIMAL(5,2) DEFAULT 0,
                    why JSONB DEFAULT '{}'::jsonb,
                    matching_asset_ids UUID[] DEFAULT '{}',
                    recommended_actions JSONB DEFAULT '[]'::jsonb,
                    status VARCHAR(20) DEFAULT 'new',
                    window_start TIMESTAMPTZ DEFAULT NOW(),
                    window_end TIMESTAMPTZ,
                    priority VARCHAR(10) DEFAULT 'medium',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trend_briefs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    workspace_id UUID,
                    opportunity_id UUID,
                    title VARCHAR(500),
                    summary TEXT,
                    trend_context JSONB DEFAULT '{}'::jsonb,
                    hook_options JSONB DEFAULT '[]'::jsonb,
                    caption_options JSONB DEFAULT '[]'::jsonb,
                    format_recommendations JSONB DEFAULT '[]'::jsonb,
                    recommended_assets JSONB DEFAULT '[]'::jsonb,
                    experiment_hypotheses JSONB DEFAULT '[]'::jsonb,
                    status VARCHAR(20) DEFAULT 'draft',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ
                )
            """))
            
            conn.commit()
            logger.info("Created trend tables")
    except Exception as e:
        logger.error(f"Error ensuring trend tables: {e}")
    finally:
        conn.close()


# =============================================================================
# TREND ITEMS ENDPOINTS
# =============================================================================

@router.get("/trends/items")
async def list_trend_items(
    source: Optional[str] = None,
    entity_type: Optional[str] = None,
    min_velocity: Optional[float] = None,
    hours: int = 24,
    limit: int = 50
):
    """List recent trend items with optional filtering."""
    await ensure_trend_tables()
    conn = get_db_connection()
    if not conn:
        return {"items": [], "count": 0}
    
    try:
        query = """
            SELECT id, source, entity_type, entity_id, entity_key, display_name,
                   region, platform, timestamp_bucket, metrics, velocity,
                   acceleration, rank, volume, context, created_at
            FROM trend_items
            WHERE created_at > NOW() - INTERVAL ':hours hours'
        """
        params = {"hours": hours, "limit": limit}
        
        if source:
            query += " AND source = :source"
            params["source"] = source
        
        if entity_type:
            query += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type
        
        if min_velocity:
            query += " AND velocity >= :min_velocity"
            params["min_velocity"] = min_velocity
        
        query += " ORDER BY velocity DESC NULLS LAST LIMIT :limit"
        
        # Fix the interval syntax
        query = query.replace("':hours hours'", f"'{hours} hours'")
        
        result = conn.execute(text(query), params).fetchall()
        
        items = []
        for row in result:
            items.append({
                "id": str(row[0]),
                "source": row[1],
                "entity_type": row[2],
                "entity_id": row[3],
                "entity_key": row[4],
                "display_name": row[5],
                "region": row[6],
                "platform": row[7],
                "timestamp_bucket": row[8].isoformat() if row[8] else None,
                "metrics": row[9] or {},
                "velocity": float(row[10]) if row[10] else None,
                "acceleration": float(row[11]) if row[11] else None,
                "rank": row[12],
                "volume": row[13],
                "context": row[14] or {},
                "created_at": row[15].isoformat() if row[15] else None
            })
        
        return {"items": items, "count": len(items)}
    
    except Exception as e:
        logger.error(f"Error listing trend items: {e}")
        return {"items": [], "count": 0, "error": str(e)}
    finally:
        conn.close()


@router.post("/trends/items")
async def create_trend_item(item: TrendItemCreate):
    """Create or update a trend item."""
    await ensure_trend_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        item_id = str(uuid.uuid4())
        
        conn.execute(text("""
            INSERT INTO trend_items (id, source, entity_type, entity_id, entity_key,
                                     display_name, region, platform, metrics,
                                     velocity, acceleration, rank, volume, context)
            VALUES (:id, :source, :entity_type, :entity_id, :entity_key,
                    :display_name, :region, :platform, :metrics::jsonb,
                    :velocity, :acceleration, :rank, :volume, :context::jsonb)
            ON CONFLICT (source, entity_type, entity_key, timestamp_bucket) 
            DO UPDATE SET
                velocity = EXCLUDED.velocity,
                acceleration = EXCLUDED.acceleration,
                rank = EXCLUDED.rank,
                volume = EXCLUDED.volume,
                metrics = EXCLUDED.metrics,
                context = EXCLUDED.context
        """), {
            "id": item_id,
            "source": item.source,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "entity_key": item.entity_key,
            "display_name": item.display_name,
            "region": item.region,
            "platform": item.platform or item.source,
            "metrics": json.dumps(item.metrics),
            "velocity": item.velocity,
            "acceleration": item.acceleration,
            "rank": item.rank,
            "volume": item.volume,
            "context": json.dumps(item.context)
        })
        conn.commit()
        
        return {"id": item_id, "entity_key": item.entity_key, "message": "Trend item created"}
    
    except Exception as e:
        logger.error(f"Error creating trend item: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# =============================================================================
# OPPORTUNITIES ENDPOINTS
# =============================================================================

@router.get("/trends/opportunities")
async def list_opportunities(
    status: str = "new",
    min_score: Optional[float] = None,
    priority: Optional[str] = None,
    limit: int = 20
):
    """List trend opportunities."""
    await ensure_trend_tables()
    conn = get_db_connection()
    if not conn:
        return {"opportunities": [], "count": 0}
    
    try:
        query = """
            SELECT id, cluster_id, title, description, opportunity_score,
                   velocity_score, acceleration_score, relevance_to_brand,
                   content_fit, monetization_fit, fatigue_penalty, competition_penalty,
                   risk_penalty, why, matching_asset_ids, recommended_actions,
                   status, window_start, window_end, priority, created_at
            FROM trend_opportunities
            WHERE status = :status
        """
        params = {"status": status, "limit": limit}
        
        if min_score:
            query += " AND opportunity_score >= :min_score"
            params["min_score"] = min_score
        
        if priority:
            query += " AND priority = :priority"
            params["priority"] = priority
        
        query += " ORDER BY opportunity_score DESC LIMIT :limit"
        
        result = conn.execute(text(query), params).fetchall()
        
        opportunities = []
        for row in result:
            opportunities.append({
                "id": str(row[0]),
                "cluster_id": str(row[1]) if row[1] else None,
                "title": row[2],
                "description": row[3],
                "opportunity_score": float(row[4]) if row[4] else 0,
                "scores": {
                    "velocity": float(row[5]) if row[5] else 0,
                    "acceleration": float(row[6]) if row[6] else 0,
                    "relevance_to_brand": float(row[7]) if row[7] else 0,
                    "content_fit": float(row[8]) if row[8] else 0,
                    "monetization_fit": float(row[9]) if row[9] else 0,
                    "fatigue_penalty": float(row[10]) if row[10] else 0,
                    "competition_penalty": float(row[11]) if row[11] else 0,
                    "risk_penalty": float(row[12]) if row[12] else 0
                },
                "why": row[13] or {},
                "matching_asset_ids": [str(a) for a in (row[14] or [])],
                "recommended_actions": row[15] or [],
                "status": row[16],
                "window_start": row[17].isoformat() if row[17] else None,
                "window_end": row[18].isoformat() if row[18] else None,
                "priority": row[19],
                "created_at": row[20].isoformat() if row[20] else None
            })
        
        return {"opportunities": opportunities, "count": len(opportunities)}
    
    except Exception as e:
        logger.error(f"Error listing opportunities: {e}")
        return {"opportunities": [], "count": 0, "error": str(e)}
    finally:
        conn.close()


@router.post("/trends/opportunities")
async def create_opportunity(opp: OpportunityCreate):
    """Create a new trend opportunity."""
    await ensure_trend_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        opp_id = str(uuid.uuid4())
        total_score = opp.scores.total_score
        window_end = datetime.now() + timedelta(hours=opp.window_hours)
        
        conn.execute(text("""
            INSERT INTO trend_opportunities (
                id, cluster_id, title, description, opportunity_score,
                velocity_score, acceleration_score, relevance_to_brand,
                content_fit, monetization_fit, fatigue_penalty, competition_penalty,
                risk_penalty, why, matching_asset_ids, recommended_actions,
                window_end, priority
            ) VALUES (
                :id, :cluster_id, :title, :description, :opportunity_score,
                :velocity_score, :acceleration_score, :relevance_to_brand,
                :content_fit, :monetization_fit, :fatigue_penalty, :competition_penalty,
                :risk_penalty, :why::jsonb, :matching_asset_ids::uuid[], :recommended_actions::jsonb,
                :window_end, :priority
            )
        """), {
            "id": opp_id,
            "cluster_id": opp.cluster_id,
            "title": opp.title,
            "description": opp.description,
            "opportunity_score": total_score,
            "velocity_score": opp.scores.velocity_score,
            "acceleration_score": opp.scores.acceleration_score,
            "relevance_to_brand": opp.scores.relevance_to_brand,
            "content_fit": opp.scores.content_fit,
            "monetization_fit": opp.scores.monetization_fit,
            "fatigue_penalty": opp.scores.fatigue_penalty,
            "competition_penalty": opp.scores.competition_penalty,
            "risk_penalty": opp.scores.risk_penalty,
            "why": json.dumps(opp.why),
            "matching_asset_ids": "{" + ",".join(opp.matching_asset_ids) + "}" if opp.matching_asset_ids else "{}",
            "recommended_actions": json.dumps(opp.recommended_actions),
            "window_end": window_end,
            "priority": opp.priority
        })
        conn.commit()
        
        logger.info(f"Created opportunity {opp_id}: {opp.title} (score: {total_score})")
        
        return {
            "id": opp_id,
            "title": opp.title,
            "opportunity_score": total_score,
            "priority": opp.priority,
            "window_end": window_end.isoformat(),
            "message": "Opportunity created"
        }
    
    except Exception as e:
        logger.error(f"Error creating opportunity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.patch("/trends/opportunities/{opp_id}/action")
async def action_opportunity(opp_id: str, actioned_by: str = "user"):
    """Mark an opportunity as actioned."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        conn.execute(text("""
            UPDATE trend_opportunities 
            SET status = 'actioned', actioned_at = NOW(), actioned_by = :actioned_by
            WHERE id = :id
        """), {"id": opp_id, "actioned_by": actioned_by})
        conn.commit()
        
        return {"id": opp_id, "status": "actioned", "actioned_by": actioned_by}
    
    except Exception as e:
        logger.error(f"Error actioning opportunity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.patch("/trends/opportunities/{opp_id}/dismiss")
async def dismiss_opportunity(opp_id: str):
    """Dismiss an opportunity."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        conn.execute(text("""
            UPDATE trend_opportunities SET status = 'dismissed', updated_at = NOW()
            WHERE id = :id
        """), {"id": opp_id})
        conn.commit()
        
        return {"id": opp_id, "status": "dismissed"}
    
    except Exception as e:
        logger.error(f"Error dismissing opportunity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# =============================================================================
# TREND BRIEFS ENDPOINTS
# =============================================================================

@router.get("/trends/briefs")
async def list_briefs(status: str = "draft", limit: int = 20):
    """List trend briefs."""
    await ensure_trend_tables()
    conn = get_db_connection()
    if not conn:
        return {"briefs": [], "count": 0}
    
    try:
        result = conn.execute(text("""
            SELECT id, opportunity_id, title, summary, trend_context,
                   hook_options, caption_options, format_recommendations,
                   recommended_assets, experiment_hypotheses, status, created_at
            FROM trend_briefs
            WHERE status = :status
            ORDER BY created_at DESC LIMIT :limit
        """), {"status": status, "limit": limit}).fetchall()
        
        briefs = []
        for row in result:
            briefs.append({
                "id": str(row[0]),
                "opportunity_id": str(row[1]) if row[1] else None,
                "title": row[2],
                "summary": row[3],
                "trend_context": row[4] or {},
                "hook_options": row[5] or [],
                "caption_options": row[6] or [],
                "format_recommendations": row[7] or [],
                "recommended_assets": row[8] or [],
                "experiment_hypotheses": row[9] or [],
                "status": row[10],
                "created_at": row[11].isoformat() if row[11] else None
            })
        
        return {"briefs": briefs, "count": len(briefs)}
    
    except Exception as e:
        logger.error(f"Error listing briefs: {e}")
        return {"briefs": [], "count": 0, "error": str(e)}
    finally:
        conn.close()


@router.post("/trends/briefs")
async def create_brief(brief: TrendBriefCreate):
    """Create a trend brief from an opportunity."""
    await ensure_trend_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        brief_id = str(uuid.uuid4())
        
        conn.execute(text("""
            INSERT INTO trend_briefs (
                id, opportunity_id, title, summary, trend_context,
                hook_options, caption_options, format_recommendations,
                recommended_assets, experiment_hypotheses, expires_at
            ) VALUES (
                :id, :opportunity_id, :title, :summary, :trend_context::jsonb,
                :hook_options::jsonb, :caption_options::jsonb, :format_recommendations::jsonb,
                :recommended_assets::jsonb, :experiment_hypotheses::jsonb,
                NOW() + INTERVAL '48 hours'
            )
        """), {
            "id": brief_id,
            "opportunity_id": brief.opportunity_id,
            "title": brief.title,
            "summary": brief.summary,
            "trend_context": json.dumps(brief.trend_context),
            "hook_options": json.dumps(brief.hook_options),
            "caption_options": json.dumps(brief.caption_options),
            "format_recommendations": json.dumps(brief.format_recommendations),
            "recommended_assets": json.dumps(brief.recommended_assets),
            "experiment_hypotheses": json.dumps(brief.experiment_hypotheses)
        })
        conn.commit()
        
        return {"id": brief_id, "title": brief.title, "message": "Brief created"}
    
    except Exception as e:
        logger.error(f"Error creating brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# =============================================================================
# SCORING ENDPOINT
# =============================================================================

@router.post("/trends/score")
async def calculate_opportunity_score(
    velocity: float = 0,
    acceleration: float = 0,
    relevance_to_brand: float = 0,
    content_fit: float = 0,
    monetization_fit: float = 0,
    fatigue_penalty: float = 0,
    competition_penalty: float = 0,
    risk_penalty: float = 0
):
    """Calculate opportunity score using the weighted formula."""
    score = OpportunityScore(
        velocity_score=velocity,
        acceleration_score=acceleration,
        relevance_to_brand=relevance_to_brand,
        content_fit=content_fit,
        monetization_fit=monetization_fit,
        fatigue_penalty=fatigue_penalty,
        competition_penalty=competition_penalty,
        risk_penalty=risk_penalty
    )
    
    return {
        "opportunity_score": score.total_score,
        "formula": "0.35*velocity + 0.20*acceleration + 0.20*relevance + 0.15*content_fit + 0.10*monetization - penalties",
        "components": {
            "velocity_weighted": 0.35 * velocity,
            "acceleration_weighted": 0.20 * acceleration,
            "relevance_weighted": 0.20 * relevance_to_brand,
            "content_fit_weighted": 0.15 * content_fit,
            "monetization_weighted": 0.10 * monetization_fit,
            "total_penalties": fatigue_penalty + competition_penalty + risk_penalty
        }
    }


# =============================================================================
# SEED DEMO DATA
# =============================================================================

@router.post("/trends/seed-demo-data")
async def seed_demo_data():
    """Seed demo trend opportunities for testing."""
    await ensure_trend_tables()
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Create demo trend items
        demo_items = [
            {
                "source": "tiktok",
                "entity_type": "hashtag",
                "entity_id": "mealprep2025",
                "entity_key": "mealprep2025",
                "display_name": "#mealprep2025",
                "velocity": 85.5,
                "acceleration": 12.3,
                "rank": 15,
                "volume": 2500000
            },
            {
                "source": "tiktok",
                "entity_type": "sound",
                "entity_id": "original_sound_12345",
                "entity_key": "viral_motivation_sound",
                "display_name": "Viral Motivation Sound",
                "velocity": 92.0,
                "acceleration": 18.5,
                "rank": 8,
                "volume": 5000000
            },
            {
                "source": "instagram",
                "entity_type": "topic",
                "entity_id": "ai_productivity",
                "entity_key": "ai_productivity",
                "display_name": "AI Productivity Tools",
                "velocity": 78.0,
                "acceleration": 15.0,
                "rank": 22,
                "volume": 1800000
            }
        ]
        
        for item in demo_items:
            item_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO trend_items (id, source, entity_type, entity_id, entity_key,
                                         display_name, velocity, acceleration, rank, volume)
                VALUES (:id, :source, :entity_type, :entity_id, :entity_key,
                        :display_name, :velocity, :acceleration, :rank, :volume)
            """), {"id": item_id, **item})
        
        # Create demo opportunities
        demo_opportunities = [
            {
                "title": "AI Productivity Trend Rising",
                "description": "AI productivity tools trending across TikTok and Instagram. Cross-surface signal detected.",
                "opportunity_score": 82.5,
                "velocity_score": 85,
                "acceleration_score": 75,
                "relevance_to_brand": 90,
                "content_fit": 80,
                "monetization_fit": 70,
                "priority": "high",
                "why": {"reasons": ["Cross-platform trend", "High brand relevance", "Existing content matches"], "platforms": ["tiktok", "instagram"]},
                "recommended_actions": [
                    {"type": "post", "platform": "tiktok", "priority": "high", "window": "48h"},
                    {"type": "experiment", "hypothesis": "AI tool hooks outperform generic productivity hooks"}
                ]
            },
            {
                "title": "Meal Prep Content Surge",
                "description": "#mealprep2025 hashtag velocity spiking. Good fit for health/wellness content.",
                "opportunity_score": 75.0,
                "velocity_score": 85,
                "acceleration_score": 60,
                "relevance_to_brand": 70,
                "content_fit": 75,
                "monetization_fit": 80,
                "priority": "medium",
                "why": {"reasons": ["Seasonal trend", "High engagement niche"], "platforms": ["tiktok"]},
                "recommended_actions": [
                    {"type": "post", "platform": "tiktok", "priority": "medium"}
                ]
            }
        ]
        
        for opp in demo_opportunities:
            opp_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO trend_opportunities (
                    id, title, description, opportunity_score, velocity_score,
                    acceleration_score, relevance_to_brand, content_fit, monetization_fit,
                    priority, why, recommended_actions, window_end
                ) VALUES (
                    :id, :title, :description, :opportunity_score, :velocity_score,
                    :acceleration_score, :relevance_to_brand, :content_fit, :monetization_fit,
                    :priority, :why::jsonb, :recommended_actions::jsonb, NOW() + INTERVAL '48 hours'
                )
            """), {
                "id": opp_id,
                **{k: v if k not in ['why', 'recommended_actions'] else json.dumps(v) for k, v in opp.items()}
            })
        
        conn.commit()
        
        return {
            "message": "Demo data seeded",
            "items_created": len(demo_items),
            "opportunities_created": len(demo_opportunities)
        }
    
    except Exception as e:
        logger.error(f"Error seeding demo data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

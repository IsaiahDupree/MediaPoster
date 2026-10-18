"""
Closed-Loop Content System API - SQLAlchemy Version
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
    return _engine

router = APIRouter(prefix="/api/content-loop", tags=["Content Loop"])


# Models
class ContentItemCreate(BaseModel):
    title: str
    source_type: str = "UGC"
    format_type: Optional[str] = None
    duration_sec: Optional[int] = None
    hook_text: Optional[str] = None

class PostingCreate(BaseModel):
    content_item_id: str
    platform: str
    account_id: Optional[int] = None
    caption_text: Optional[str] = None
    hashtags: Optional[List[str]] = None

class PlaybookRuleCreate(BaseModel):
    rule_type: str
    rule_text: str
    platform: Optional[str] = None
    confidence_score: float = 50.0

class ContentSlotCreate(BaseModel):
    slot_date: str
    platform: str
    slot_type: str
    objective: str = "reach"

class InsightCreate(BaseModel):
    insight_type: str  # 'pattern', 'winner', 'loser', 'improvement'
    title: str
    description: str
    platform: Optional[str] = None
    source_type: Optional[str] = None
    confidence_score: float = 0.5
    recommended_actions: Optional[Dict] = None


# Content Items
@router.get("/content-items")
def list_content_items(
    source_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    engine = get_engine()
    query = "SELECT * FROM content_items WHERE 1=1"
    params = {}
    
    if source_type:
        query += " AND source_type = :source_type"
        params["source_type"] = source_type
    
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(r._mapping) for r in result]
    
    return {"items": rows, "count": len(rows)}


@router.post("/content-items")
def create_content_item(item: ContentItemCreate):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO content_items (title, source_type, format_type, duration_sec, hook_text)
            VALUES (:title, :source_type, :format_type, :duration_sec, :hook_text)
            RETURNING id, title, source_type, created_at
        """), {
            "title": item.title,
            "source_type": item.source_type,
            "format_type": item.format_type,
            "duration_sec": item.duration_sec,
            "hook_text": item.hook_text
        })
        conn.commit()
        row = result.fetchone()
    
    return dict(row._mapping)


# Postings
@router.get("/postings")
def list_postings(
    platform: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    engine = get_engine()
    query = "SELECT * FROM postings WHERE 1=1"
    params = {}
    
    if platform:
        query += " AND platform = :platform"
        params["platform"] = platform
    
    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(r._mapping) for r in result]
    
    return {"postings": rows, "count": len(rows)}


@router.post("/postings")
def create_posting(posting: PostingCreate):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO postings (content_item_id, platform, account_id, caption_text, hashtags, status)
            VALUES (CAST(:content_item_id AS uuid), :platform, :account_id, :caption_text, :hashtags, 'draft')
            RETURNING id, platform, status, created_at
        """), {
            "content_item_id": posting.content_item_id,
            "platform": posting.platform,
            "account_id": posting.account_id,
            "caption_text": posting.caption_text,
            "hashtags": posting.hashtags
        })
        conn.commit()
        row = result.fetchone()
    
    return dict(row._mapping)


@router.patch("/postings/{posting_id}/status")
def update_posting_status(posting_id: str, status: str):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE postings SET status = :status,
            posted_at = CASE WHEN :status = 'posted' THEN NOW() ELSE posted_at END
            WHERE id = CAST(:posting_id AS uuid)
            RETURNING id, status, posted_at
        """), {"posting_id": posting_id, "status": status})
        conn.commit()
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Posting not found")
    return dict(row._mapping)


# Metric Snapshots
class MetricSnapshotCreate(BaseModel):
    posting_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0

@router.post("/metrics/snapshot")
def create_metric_snapshot(snapshot: MetricSnapshotCreate):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO metric_snapshots (posting_id, views, likes, comments, shares, saves)
            VALUES (CAST(:posting_id AS uuid), :views, :likes, :comments, :shares, :saves)
            RETURNING id, posting_id, captured_at
        """), {
            "posting_id": snapshot.posting_id,
            "views": snapshot.views,
            "likes": snapshot.likes,
            "comments": snapshot.comments,
            "shares": snapshot.shares,
            "saves": snapshot.saves
        })
        conn.commit()
        row = result.fetchone()
    
    return dict(row._mapping)


@router.get("/postings/{posting_id}/metrics")
def get_posting_metrics(posting_id: str):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM metric_snapshots 
            WHERE posting_id = CAST(:posting_id AS uuid)
            ORDER BY captured_at
        """), {"posting_id": posting_id})
        rows = [dict(r._mapping) for r in result]
    
    return {"posting_id": posting_id, "snapshots": rows}


# Review Windows
@router.get("/review-windows")
def list_review_windows(platform: Optional[str] = None):
    engine = get_engine()
    query = "SELECT * FROM review_windows WHERE is_active = true"
    params = {}
    
    if platform:
        query += " AND platform = :platform"
        params["platform"] = platform
    
    query += " ORDER BY platform, start_hour"
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(r._mapping) for r in result]
    
    return {"windows": rows}


# Reviews
class ReviewCreate(BaseModel):
    posting_id: str
    window_id: str
    auto_score: Optional[float] = None
    human_score: Optional[float] = None
    label: str = "pending"
    notes: Optional[str] = None

@router.get("/reviews")
def list_reviews(label: Optional[str] = None, limit: int = 50):
    engine = get_engine()
    query = "SELECT * FROM reviews WHERE 1=1"
    params = {}
    
    if label:
        query += " AND label = :label"
        params["label"] = label
    
    query += " ORDER BY reviewed_at DESC LIMIT :limit"
    params["limit"] = limit
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(r._mapping) for r in result]
    
    return {"reviews": rows}


@router.post("/reviews")
def create_review(review: ReviewCreate):
    engine = get_engine()
    
    with engine.connect() as conn:
        # Use final_score column name based on schema
        result = conn.execute(text("""
            INSERT INTO reviews (posting_id, window_id, auto_score, label, notes)
            VALUES (CAST(:posting_id AS uuid), CAST(:window_id AS uuid), :auto_score, :label, :notes)
            RETURNING id, posting_id, window_id, label, reviewed_at
        """), {
            "posting_id": review.posting_id,
            "window_id": review.window_id,
            "auto_score": review.auto_score,
            "label": review.label,
            "notes": review.notes
        })
        conn.commit()
        row = result.fetchone()
    
    return dict(row._mapping)


# Playbook Rules
@router.get("/playbook")
def get_playbook_rules(min_confidence: float = 0):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM playbook_rules 
            WHERE confidence_score >= :min_confidence
            ORDER BY confidence_score DESC
        """), {"min_confidence": min_confidence})
        rows = [dict(r._mapping) for r in result]
    
    return {"rules": rows}


@router.post("/playbook")
def create_playbook_rule(rule: PlaybookRuleCreate):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO playbook_rules (rule_type, rule_text, platform, confidence_score)
            VALUES (:rule_type, :rule_text, :platform, :confidence_score)
            RETURNING id, rule_type, rule_text, confidence_score
        """), {
            "rule_type": rule.rule_type,
            "rule_text": rule.rule_text,
            "platform": rule.platform,
            "confidence_score": rule.confidence_score
        })
        conn.commit()
        row = result.fetchone()
    
    return dict(row._mapping)


# Content Slots
@router.get("/slots")
def get_content_slots(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    engine = get_engine()
    
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM content_slots
            WHERE slot_date BETWEEN :start_date AND :end_date
            ORDER BY slot_date, slot_time
        """), {"start_date": start_date, "end_date": end_date})
        rows = [dict(r._mapping) for r in result]
    
    return {"slots": rows}


@router.post("/slots")
def create_content_slot(slot: ContentSlotCreate):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO content_slots (slot_date, platform, slot_type, objective)
            VALUES (:slot_date, :platform, :slot_type, :objective)
            RETURNING id, slot_date, platform, slot_type, objective
        """), {
            "slot_date": slot.slot_date,
            "platform": slot.platform,
            "slot_type": slot.slot_type,
            "objective": slot.objective
        })
        conn.commit()
        row = result.fetchone()
    
    return dict(row._mapping)


@router.post("/slots/{slot_id}/assign")
def assign_content_to_slot(slot_id: str, content_item_id: str):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE content_slots SET assigned_content_id = CAST(:content_id AS uuid), is_filled = true
            WHERE id = CAST(:slot_id AS uuid)
            RETURNING id, slot_date, platform, is_filled
        """), {"slot_id": slot_id, "content_id": content_item_id})
        conn.commit()
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Slot not found")
    return dict(row._mapping)


# Insights
@router.get("/insights")
def get_insights(limit: int = 20):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM insights
            WHERE is_active = true
            ORDER BY confidence_score DESC
            LIMIT :limit
        """), {"limit": limit})
        rows = [dict(r._mapping) for r in result]
    
    return {"insights": rows}


@router.post("/insights")
def create_insight(insight: InsightCreate):
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO insights (
                insight_type, title, description, platform,
                source_type, confidence_score, recommended_actions, is_active
            ) VALUES (
                :insight_type, :title, :description, :platform,
                :source_type, :confidence_score, :recommended_actions, true
            ) RETURNING *
        """), {
            "insight_type": insight.insight_type,
            "title": insight.title,
            "description": insight.description,
            "platform": insight.platform,
            "source_type": insight.source_type,
            "confidence_score": insight.confidence_score,
            "recommended_actions": json.dumps(insight.recommended_actions) if insight.recommended_actions else None
        })
        conn.commit()
        row = result.fetchone()
    
    return dict(row._mapping)


# Dashboard
@router.get("/dashboard")
def get_loop_dashboard():
    engine = get_engine()
    
    with engine.connect() as conn:
        # Category performance
        cat_result = conn.execute(text("""
            SELECT source_type, COUNT(*) as total_posts
            FROM content_items
            GROUP BY source_type
        """))
        category_perf = [dict(r._mapping) for r in cat_result]
        
        # Today's slots
        slots_result = conn.execute(text("""
            SELECT * FROM content_slots WHERE slot_date = CURRENT_DATE
        """))
        todays_slots = [dict(r._mapping) for r in slots_result]
        
        # Top playbook rules
        rules_result = conn.execute(text("""
            SELECT * FROM playbook_rules ORDER BY confidence_score DESC LIMIT 5
        """))
        top_rules = [dict(r._mapping) for r in rules_result]
    
    return {
        "category_performance": category_perf,
        "attention_needed": [],
        "todays_slots": todays_slots,
        "top_playbook_rules": top_rules
    }

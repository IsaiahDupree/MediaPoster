"""
Comment Engagement & Automation API with Pub/Sub Architecture
==============================================================
Endpoints for managing comments, comment automation rules, and tracking
interactions for the People/Audience system.

Pub/Sub Events:
- comment.received - New comment detected
- comment.analyzed - Sentiment/intent analyzed
- comment.replied - Auto-reply sent
- comment.flagged - Comment flagged for review
- fan.identified - Top fan identified
- fan.engagement_updated - Fan engagement score updated
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import logging
import uuid
import os
import json
import asyncio

# EventBus import for pub/sub
try:
    from services.event_bus import EventBus, Topics
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False
    Topics = None

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/engagement", tags=["Comment Engagement"])


# =============================================================================
# PUB/SUB EVENT TOPICS
# =============================================================================

class CommentTopics:
    """Event topics for comment pub/sub.
    
    Now uses standard Topics class when available for consistency.
    """
    COMMENT_RECEIVED = Topics.COMMENT_RECEIVED if Topics else "comment.received"
    COMMENT_ANALYZED = Topics.COMMENT_ANALYZED if Topics else "comment.analyzed"
    COMMENT_REPLIED = Topics.COMMENT_REPLIED if Topics else "comment.replied"
    COMMENT_FLAGGED = Topics.COMMENT_FLAGGED if Topics else "comment.flagged"
    COMMENT_HIDDEN = "comment.hidden"
    COMMENT_LIKED = "comment.liked"
    
class FanTopics:
    """Event topics for fan/audience tracking."""
    FAN_IDENTIFIED = Topics.FAN_IDENTIFIED if Topics else "fan.identified"
    FAN_ENGAGEMENT_UPDATED = "fan.engagement_updated"
    FAN_TIER_CHANGED = Topics.FAN_TIER_CHANGED if Topics else "fan.tier_changed"
    TOP_FAN_ALERT = Topics.TOP_FAN_ALERT if Topics else "fan.top_fan_alert"

class AutomationTopics:
    """Event topics for automation."""
    RULE_TRIGGERED = "automation.rule_triggered"
    REPLY_QUEUED = "automation.reply_queued"
    REPLY_SENT = "automation.reply_sent"
    REPLY_FAILED = "automation.reply_failed"


async def publish_event(topic: str, payload: Dict[str, Any], correlation_id: str = None):
    """Publish event to EventBus if available."""
    if HAS_EVENT_BUS:
        try:
            bus = EventBus.get_instance()
            await bus.publish(topic, payload, correlation_id=correlation_id)
        except Exception as e:
            logger.warning(f"Failed to publish event {topic}: {e}")


# =============================================================================
# MODELS
# =============================================================================

class CommentCreate(BaseModel):
    platform: str
    post_id: str
    comment_id: str
    author_id: str
    author_username: str
    author_display_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    text: str
    like_count: int = 0
    reply_count: int = 0
    is_reply: bool = False
    parent_comment_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutomationRule(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str  # 'keyword', 'sentiment', 'question', 'mention', 'first_comment'
    trigger_conditions: Dict[str, Any]
    action_type: str  # 'reply', 'like', 'flag', 'hide', 'notify'
    action_config: Dict[str, Any]
    platforms: List[str] = ['all']
    is_active: bool = True
    priority: int = 50


class AutoReply(BaseModel):
    comment_id: str
    reply_text: str
    delay_seconds: int = 0


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

def ensure_tables():
    """Create engagement tables if they don't exist."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # Fan/Audience tracking table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audience_members (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    
                    -- Identity
                    platform VARCHAR(50) NOT NULL,
                    platform_user_id VARCHAR(255) NOT NULL,
                    username VARCHAR(255),
                    display_name VARCHAR(255),
                    avatar_url TEXT,
                    profile_url TEXT,
                    
                    -- Engagement metrics
                    total_comments INTEGER DEFAULT 0,
                    total_likes INTEGER DEFAULT 0,
                    total_shares INTEGER DEFAULT 0,
                    total_interactions INTEGER DEFAULT 0,
                    engagement_score DECIMAL(10,4) DEFAULT 0,
                    
                    -- Fan classification
                    fan_tier VARCHAR(20) DEFAULT 'casual',  -- casual, engaged, superfan, top_fan
                    is_top_fan BOOLEAN DEFAULT FALSE,
                    first_interaction_at TIMESTAMPTZ,
                    last_interaction_at TIMESTAMPTZ,
                    
                    -- Sentiment tracking
                    avg_sentiment DECIMAL(5,4) DEFAULT 0,
                    positive_interactions INTEGER DEFAULT 0,
                    negative_interactions INTEGER DEFAULT 0,
                    
                    -- Metadata
                    notes TEXT,
                    tags TEXT[] DEFAULT '{}',
                    metadata JSONB DEFAULT '{}'::jsonb,
                    
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    UNIQUE(platform, platform_user_id)
                )
            """))
            
            # Comments table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tracked_comments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    
                    -- Comment identity
                    platform VARCHAR(50) NOT NULL,
                    post_id VARCHAR(255) NOT NULL,
                    comment_id VARCHAR(255) NOT NULL,
                    
                    -- Author info (linked to audience_members)
                    author_id VARCHAR(255),
                    author_username VARCHAR(255),
                    author_display_name VARCHAR(255),
                    author_avatar_url TEXT,
                    audience_member_id UUID REFERENCES audience_members(id),
                    
                    -- Content
                    text TEXT NOT NULL,
                    like_count INTEGER DEFAULT 0,
                    reply_count INTEGER DEFAULT 0,
                    
                    -- Threading
                    is_reply BOOLEAN DEFAULT FALSE,
                    parent_comment_id VARCHAR(255),
                    
                    -- Analysis
                    sentiment_score DECIMAL(5,4),
                    sentiment_label VARCHAR(20),
                    intent_type VARCHAR(50),  -- question, praise, complaint, suggestion, spam
                    keywords TEXT[] DEFAULT '{}',
                    
                    -- Status
                    status VARCHAR(20) DEFAULT 'new',  -- new, reviewed, replied, flagged, hidden
                    auto_replied BOOLEAN DEFAULT FALSE,
                    replied_at TIMESTAMPTZ,
                    reply_text TEXT,
                    
                    -- Metadata
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    UNIQUE(platform, comment_id)
                )
            """))
            
            # Automation rules table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS comment_automation_rules (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    
                    -- Trigger configuration
                    trigger_type VARCHAR(50) NOT NULL,
                    trigger_conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
                    
                    -- Action configuration
                    action_type VARCHAR(50) NOT NULL,
                    action_config JSONB NOT NULL DEFAULT '{}'::jsonb,
                    
                    -- Targeting
                    platforms TEXT[] DEFAULT '{}'::text[],
                    
                    -- Status
                    is_active BOOLEAN DEFAULT TRUE,
                    priority INTEGER DEFAULT 50,
                    
                    -- Stats
                    times_triggered INTEGER DEFAULT 0,
                    last_triggered_at TIMESTAMPTZ,
                    
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            # Automation queue table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS automation_queue (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    
                    rule_id UUID REFERENCES comment_automation_rules(id),
                    comment_id UUID REFERENCES tracked_comments(id),
                    
                    action_type VARCHAR(50) NOT NULL,
                    action_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    
                    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
                    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
                    executed_at TIMESTAMPTZ,
                    error_message TEXT,
                    
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            # Create indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_audience_platform_user 
                ON audience_members(platform, platform_user_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_audience_engagement 
                ON audience_members(engagement_score DESC)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_audience_fan_tier 
                ON audience_members(fan_tier)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tracked_comments_platform 
                ON tracked_comments(platform, post_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tracked_comments_status 
                ON tracked_comments(status)
            """))
            
            conn.commit()
            logger.info("Comment engagement tables ensured")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")


# =============================================================================
# COMMENT ANALYSIS
# =============================================================================

async def analyze_comment(text: str) -> Dict[str, Any]:
    """Analyze comment for sentiment, intent, and keywords."""
    # In production, this would call an LLM or sentiment API
    text_lower = text.lower()
    
    # Simple sentiment analysis
    positive_words = ['love', 'amazing', 'great', 'awesome', 'best', 'thank', 'perfect', '❤️', '🔥', '😍']
    negative_words = ['hate', 'terrible', 'worst', 'bad', 'awful', 'disappointed', 'sucks']
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        sentiment_score = min(0.9, 0.3 + (positive_count * 0.15))
        sentiment_label = 'positive'
    elif negative_count > positive_count:
        sentiment_score = max(-0.9, -0.3 - (negative_count * 0.15))
        sentiment_label = 'negative'
    else:
        sentiment_score = 0
        sentiment_label = 'neutral'
    
    # Intent detection
    if '?' in text:
        intent_type = 'question'
    elif any(word in text_lower for word in ['please', 'can you', 'how do', 'tutorial']):
        intent_type = 'request'
    elif any(word in text_lower for word in ['love', 'amazing', 'great', 'best']):
        intent_type = 'praise'
    elif any(word in text_lower for word in ['hate', 'terrible', 'fix', 'bug', 'broken']):
        intent_type = 'complaint'
    else:
        intent_type = 'general'
    
    # Extract keywords (simple approach)
    words = text.split()
    keywords = [w for w in words if len(w) > 4 and w.isalpha()][:5]
    
    return {
        'sentiment_score': sentiment_score,
        'sentiment_label': sentiment_label,
        'intent_type': intent_type,
        'keywords': keywords
    }


async def calculate_fan_tier(member: Dict[str, Any]) -> str:
    """Calculate fan tier based on engagement metrics."""
    total = member.get('total_interactions', 0)
    engagement = member.get('engagement_score', 0)
    
    if total >= 50 or engagement >= 100:
        return 'top_fan'
    elif total >= 20 or engagement >= 50:
        return 'superfan'
    elif total >= 5 or engagement >= 10:
        return 'engaged'
    else:
        return 'casual'


# =============================================================================
# API ENDPOINTS - COMMENTS
# =============================================================================

@router.post("/comments/ingest")
async def ingest_comment(comment: CommentCreate, background_tasks: BackgroundTasks):
    """
    Ingest a new comment and trigger analysis + automation.
    
    Publishes: comment.received, comment.analyzed
    """
    ensure_tables()
    engine = get_engine()
    comment_uuid = str(uuid.uuid4())
    
    try:
        with engine.connect() as conn:
            # Upsert audience member
            member_result = conn.execute(text("""
                INSERT INTO audience_members (platform, platform_user_id, username, display_name, avatar_url)
                VALUES (:platform, :user_id, :username, :display_name, :avatar_url)
                ON CONFLICT (platform, platform_user_id) 
                DO UPDATE SET 
                    username = EXCLUDED.username,
                    display_name = EXCLUDED.display_name,
                    avatar_url = EXCLUDED.avatar_url,
                    total_comments = audience_members.total_comments + 1,
                    total_interactions = audience_members.total_interactions + 1,
                    last_interaction_at = NOW(),
                    updated_at = NOW()
                RETURNING id, total_interactions, engagement_score
            """), {
                'platform': comment.platform,
                'user_id': comment.author_id,
                'username': comment.author_username,
                'display_name': comment.author_display_name,
                'avatar_url': comment.author_avatar_url
            })
            member_row = member_result.fetchone()
            member_id = str(member_row[0]) if member_row else None
            
            # Insert comment
            conn.execute(text("""
                INSERT INTO tracked_comments (
                    id, platform, post_id, comment_id, author_id, author_username,
                    author_display_name, author_avatar_url, audience_member_id,
                    text, like_count, reply_count, is_reply, parent_comment_id, metadata
                ) VALUES (
                    :id, :platform, :post_id, :comment_id, :author_id, :username,
                    :display_name, :avatar_url, :member_id,
                    :text, :like_count, :reply_count, :is_reply, :parent_id, :metadata
                )
                ON CONFLICT (platform, comment_id) DO UPDATE SET
                    like_count = EXCLUDED.like_count,
                    reply_count = EXCLUDED.reply_count,
                    updated_at = NOW()
            """), {
                'id': comment_uuid,
                'platform': comment.platform,
                'post_id': comment.post_id,
                'comment_id': comment.comment_id,
                'author_id': comment.author_id,
                'username': comment.author_username,
                'display_name': comment.author_display_name,
                'avatar_url': comment.author_avatar_url,
                'member_id': member_id,
                'text': comment.text,
                'like_count': comment.like_count,
                'reply_count': comment.reply_count,
                'is_reply': comment.is_reply,
                'parent_id': comment.parent_comment_id,
                'metadata': json.dumps(comment.metadata)
            })
            conn.commit()
        
        # Publish comment received event
        await publish_event(CommentTopics.COMMENT_RECEIVED, {
            'comment_id': comment_uuid,
            'platform': comment.platform,
            'author': comment.author_username,
            'text_preview': comment.text[:100]
        }, correlation_id=comment_uuid)
        
        # Queue background analysis
        background_tasks.add_task(process_comment, comment_uuid, comment.text)
        
        return {
            'id': comment_uuid,
            'audience_member_id': member_id,
            'status': 'received',
            'message': 'Comment ingested and queued for analysis'
        }
        
    except Exception as e:
        logger.error(f"Error ingesting comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_comment(comment_id: str, text: str):
    """Background task to analyze comment and check automation rules."""
    engine = get_engine()
    
    try:
        # Analyze comment
        analysis = await analyze_comment(text)
        
        with engine.connect() as conn:
            # Update comment with analysis
            conn.execute(text("""
                UPDATE tracked_comments SET
                    sentiment_score = :sentiment_score,
                    sentiment_label = :sentiment_label,
                    intent_type = :intent_type,
                    keywords = :keywords,
                    updated_at = NOW()
                WHERE id = :id
            """), {
                'id': comment_id,
                'sentiment_score': analysis['sentiment_score'],
                'sentiment_label': analysis['sentiment_label'],
                'intent_type': analysis['intent_type'],
                'keywords': analysis['keywords']
            })
            
            # Update audience member sentiment
            conn.execute(text("""
                UPDATE audience_members am SET
                    avg_sentiment = (am.avg_sentiment * am.total_interactions + :sentiment) / (am.total_interactions + 1),
                    positive_interactions = am.positive_interactions + CASE WHEN :sentiment > 0.3 THEN 1 ELSE 0 END,
                    negative_interactions = am.negative_interactions + CASE WHEN :sentiment < -0.3 THEN 1 ELSE 0 END,
                    engagement_score = am.engagement_score + CASE 
                        WHEN :sentiment > 0.3 THEN 2 
                        WHEN :sentiment < -0.3 THEN 0.5 
                        ELSE 1 
                    END
                FROM tracked_comments tc
                WHERE tc.id = :comment_id AND am.id = tc.audience_member_id
            """), {
                'comment_id': comment_id,
                'sentiment': analysis['sentiment_score']
            })
            
            conn.commit()
        
        # Publish analysis event
        await publish_event(CommentTopics.COMMENT_ANALYZED, {
            'comment_id': comment_id,
            'sentiment': analysis['sentiment_label'],
            'intent': analysis['intent_type']
        }, correlation_id=comment_id)
        
        # Check automation rules
        await check_automation_rules(comment_id, text, analysis)
        
    except Exception as e:
        logger.error(f"Error processing comment {comment_id}: {e}")


async def check_automation_rules(comment_id: str, text: str, analysis: Dict[str, Any]):
    """Check if comment triggers any automation rules."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            rules = conn.execute(text("""
                SELECT id, trigger_type, trigger_conditions, action_type, action_config
                FROM comment_automation_rules
                WHERE is_active = TRUE
                ORDER BY priority DESC
            """)).fetchall()
            
            for rule in rules:
                rule_id, trigger_type, conditions, action_type, action_config = rule
                conditions = conditions if isinstance(conditions, dict) else json.loads(conditions or '{}')
                action_config = action_config if isinstance(action_config, dict) else json.loads(action_config or '{}')
                
                triggered = False
                
                # Check trigger conditions
                if trigger_type == 'keyword':
                    keywords = conditions.get('keywords', [])
                    if any(kw.lower() in text.lower() for kw in keywords):
                        triggered = True
                        
                elif trigger_type == 'sentiment':
                    target_sentiment = conditions.get('sentiment', 'positive')
                    if analysis['sentiment_label'] == target_sentiment:
                        triggered = True
                        
                elif trigger_type == 'question':
                    if analysis['intent_type'] == 'question':
                        triggered = True
                        
                elif trigger_type == 'first_comment':
                    # Check if this is user's first comment
                    count = conn.execute(text("""
                        SELECT COUNT(*) FROM tracked_comments tc
                        JOIN tracked_comments tc2 ON tc.audience_member_id = tc2.audience_member_id
                        WHERE tc.id = :comment_id
                    """), {'comment_id': comment_id}).scalar()
                    if count == 1:
                        triggered = True
                
                if triggered:
                    # Queue the action
                    conn.execute(text("""
                        INSERT INTO automation_queue (rule_id, comment_id, action_type, action_payload)
                        VALUES (:rule_id, :comment_id, :action_type, :payload)
                    """), {
                        'rule_id': str(rule_id),
                        'comment_id': comment_id,
                        'action_type': action_type,
                        'payload': json.dumps(action_config)
                    })
                    
                    # Update rule stats
                    conn.execute(text("""
                        UPDATE comment_automation_rules SET
                            times_triggered = times_triggered + 1,
                            last_triggered_at = NOW()
                        WHERE id = :id
                    """), {'id': str(rule_id)})
                    
                    conn.commit()
                    
                    await publish_event(AutomationTopics.RULE_TRIGGERED, {
                        'rule_id': str(rule_id),
                        'comment_id': comment_id,
                        'action_type': action_type
                    }, correlation_id=comment_id)
                    
    except Exception as e:
        logger.error(f"Error checking automation rules: {e}")


@router.get("/comments")
async def list_comments(
    platform: Optional[str] = None,
    post_id: Optional[str] = None,
    status: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    """Get tracked comments with filtering."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            query = """
                SELECT tc.*, am.fan_tier, am.engagement_score as author_engagement
                FROM tracked_comments tc
                LEFT JOIN audience_members am ON tc.audience_member_id = am.id
                WHERE 1=1
            """
            params = {'limit': limit, 'offset': offset}
            
            if platform:
                query += " AND tc.platform = :platform"
                params['platform'] = platform
            if post_id:
                query += " AND tc.post_id = :post_id"
                params['post_id'] = post_id
            if status:
                query += " AND tc.status = :status"
                params['status'] = status
            if sentiment:
                query += " AND tc.sentiment_label = :sentiment"
                params['sentiment'] = sentiment
            
            query += " ORDER BY tc.created_at DESC LIMIT :limit OFFSET :offset"
            
            result = conn.execute(text(query), params).fetchall()
            
            comments = []
            for row in result:
                comments.append({
                    'id': str(row[0]),
                    'platform': row[1],
                    'post_id': row[2],
                    'comment_id': row[3],
                    'author': {
                        'id': row[4],
                        'username': row[5],
                        'display_name': row[6],
                        'avatar_url': row[7],
                        'fan_tier': row[-2] if len(row) > 20 else None,
                        'engagement_score': float(row[-1]) if row[-1] else 0
                    },
                    'text': row[9],
                    'like_count': row[10],
                    'reply_count': row[11],
                    'is_reply': row[12],
                    'sentiment': {
                        'score': float(row[14]) if row[14] else None,
                        'label': row[15]
                    },
                    'intent_type': row[16],
                    'status': row[18],
                    'created_at': row[22].isoformat() if row[22] else None
                })
            
            return {'comments': comments, 'count': len(comments)}
            
    except Exception as e:
        logger.error(f"Error listing comments: {e}")
        return {'comments': [], 'count': 0, 'error': str(e)}


# =============================================================================
# API ENDPOINTS - AUTOMATION RULES
# =============================================================================

@router.post("/automation/rules")
async def create_automation_rule(rule: AutomationRule):
    """Create a new comment automation rule."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO comment_automation_rules 
                (name, description, trigger_type, trigger_conditions, action_type, action_config, platforms, is_active, priority)
                VALUES (:name, :desc, :trigger_type, :conditions, :action_type, :action_config, :platforms, :is_active, :priority)
                RETURNING id
            """), {
                'name': rule.name,
                'desc': rule.description,
                'trigger_type': rule.trigger_type,
                'conditions': json.dumps(rule.trigger_conditions),
                'action_type': rule.action_type,
                'action_config': json.dumps(rule.action_config),
                'platforms': rule.platforms,
                'is_active': rule.is_active,
                'priority': rule.priority
            })
            rule_id = str(result.fetchone()[0])
            conn.commit()
            
            return {'id': rule_id, 'status': 'created'}
            
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/rules")
async def list_automation_rules():
    """Get all automation rules."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, description, trigger_type, trigger_conditions,
                       action_type, action_config, platforms, is_active, priority,
                       times_triggered, last_triggered_at, created_at
                FROM comment_automation_rules
                ORDER BY priority DESC, created_at DESC
            """)).fetchall()
            
            rules = [
                {
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'trigger_type': row[3],
                    'trigger_conditions': row[4] if isinstance(row[4], dict) else json.loads(row[4] or '{}'),
                    'action_type': row[5],
                    'action_config': row[6] if isinstance(row[6], dict) else json.loads(row[6] or '{}'),
                    'platforms': row[7],
                    'is_active': row[8],
                    'priority': row[9],
                    'times_triggered': row[10],
                    'last_triggered_at': row[11].isoformat() if row[11] else None,
                    'created_at': row[12].isoformat() if row[12] else None
                }
                for row in result
            ]
            
            return {'rules': rules, 'count': len(rules)}
            
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        return {'rules': [], 'count': 0}


@router.patch("/automation/rules/{rule_id}")
async def update_automation_rule(rule_id: str, updates: Dict[str, Any]):
    """Update an automation rule."""
    ensure_tables()
    engine = get_engine()
    
    allowed_fields = ['name', 'description', 'trigger_conditions', 'action_config', 'is_active', 'priority']
    
    try:
        with engine.connect() as conn:
            set_clauses = []
            params = {'rule_id': rule_id}
            
            for field in allowed_fields:
                if field in updates:
                    if field in ['trigger_conditions', 'action_config']:
                        set_clauses.append(f"{field} = :{field}::jsonb")
                        params[field] = json.dumps(updates[field])
                    else:
                        set_clauses.append(f"{field} = :{field}")
                        params[field] = updates[field]
            
            if not set_clauses:
                return {'message': 'No valid fields to update'}
            
            set_clauses.append("updated_at = NOW()")
            
            conn.execute(text(f"""
                UPDATE comment_automation_rules SET {', '.join(set_clauses)} WHERE id = :rule_id
            """), params)
            conn.commit()
            
            return {'id': rule_id, 'status': 'updated'}
            
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(rule_id: str):
    """Delete an automation rule."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM comment_automation_rules WHERE id = :id"), {'id': rule_id})
            conn.commit()
            return {'status': 'deleted'}
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# API ENDPOINTS - AUDIENCE/FANS
# =============================================================================

@router.get("/audience")
async def list_audience(
    platform: Optional[str] = None,
    fan_tier: Optional[str] = None,
    min_engagement: Optional[float] = None,
    sort_by: str = 'engagement_score',
    limit: int = Query(50, le=200),
    offset: int = 0
):
    """Get audience members (fans) with filtering."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            query = """
                SELECT id, platform, platform_user_id, username, display_name, avatar_url,
                       total_comments, total_likes, total_shares, total_interactions,
                       engagement_score, fan_tier, is_top_fan, first_interaction_at,
                       last_interaction_at, avg_sentiment, positive_interactions,
                       negative_interactions, tags, created_at
                FROM audience_members
                WHERE 1=1
            """
            params = {'limit': limit, 'offset': offset}
            
            if platform:
                query += " AND platform = :platform"
                params['platform'] = platform
            if fan_tier:
                query += " AND fan_tier = :fan_tier"
                params['fan_tier'] = fan_tier
            if min_engagement:
                query += " AND engagement_score >= :min_engagement"
                params['min_engagement'] = min_engagement
            
            # Sort
            if sort_by == 'engagement_score':
                query += " ORDER BY engagement_score DESC"
            elif sort_by == 'total_interactions':
                query += " ORDER BY total_interactions DESC"
            elif sort_by == 'last_interaction':
                query += " ORDER BY last_interaction_at DESC"
            else:
                query += " ORDER BY created_at DESC"
            
            query += " LIMIT :limit OFFSET :offset"
            
            result = conn.execute(text(query), params).fetchall()
            
            members = [
                {
                    'id': str(row[0]),
                    'platform': row[1],
                    'platform_user_id': row[2],
                    'username': row[3],
                    'display_name': row[4],
                    'avatar_url': row[5],
                    'stats': {
                        'total_comments': row[6],
                        'total_likes': row[7],
                        'total_shares': row[8],
                        'total_interactions': row[9]
                    },
                    'engagement_score': float(row[10]) if row[10] else 0,
                    'fan_tier': row[11],
                    'is_top_fan': row[12],
                    'first_interaction_at': row[13].isoformat() if row[13] else None,
                    'last_interaction_at': row[14].isoformat() if row[14] else None,
                    'sentiment': {
                        'average': float(row[15]) if row[15] else 0,
                        'positive_count': row[16],
                        'negative_count': row[17]
                    },
                    'tags': row[18] or []
                }
                for row in result
            ]
            
            return {'audience': members, 'count': len(members)}
            
    except Exception as e:
        logger.error(f"Error listing audience: {e}")
        return {'audience': [], 'count': 0, 'error': str(e)}


@router.get("/audience/top-fans")
async def get_top_fans(
    platform: Optional[str] = None,
    limit: int = Query(20, le=100)
):
    """Get top fans across all platforms."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            query = """
                SELECT id, platform, platform_user_id, username, display_name, avatar_url,
                       total_comments, total_interactions, engagement_score, fan_tier,
                       first_interaction_at, last_interaction_at, avg_sentiment
                FROM audience_members
                WHERE fan_tier IN ('top_fan', 'superfan')
            """
            params = {'limit': limit}
            
            if platform:
                query += " AND platform = :platform"
                params['platform'] = platform
            
            query += " ORDER BY engagement_score DESC LIMIT :limit"
            
            result = conn.execute(text(query), params).fetchall()
            
            top_fans = [
                {
                    'id': str(row[0]),
                    'platform': row[1],
                    'platform_user_id': row[2],
                    'username': row[3],
                    'display_name': row[4],
                    'avatar_url': row[5],
                    'total_comments': row[6],
                    'total_interactions': row[7],
                    'engagement_score': float(row[8]) if row[8] else 0,
                    'fan_tier': row[9],
                    'member_since': row[10].isoformat() if row[10] else None,
                    'last_seen': row[11].isoformat() if row[11] else None,
                    'sentiment': float(row[12]) if row[12] else 0
                }
                for row in result
            ]
            
            return {'top_fans': top_fans, 'count': len(top_fans)}
            
    except Exception as e:
        logger.error(f"Error getting top fans: {e}")
        return {'top_fans': [], 'count': 0}


@router.get("/audience/stats")
async def get_audience_stats():
    """Get overall audience statistics."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_members,
                    COUNT(*) FILTER (WHERE fan_tier = 'top_fan') as top_fans,
                    COUNT(*) FILTER (WHERE fan_tier = 'superfan') as superfans,
                    COUNT(*) FILTER (WHERE fan_tier = 'engaged') as engaged,
                    COUNT(*) FILTER (WHERE fan_tier = 'casual') as casual,
                    SUM(total_interactions) as total_interactions,
                    AVG(engagement_score) as avg_engagement,
                    AVG(avg_sentiment) as avg_sentiment
                FROM audience_members
            """)).fetchone()
            
            platform_breakdown = conn.execute(text("""
                SELECT platform, COUNT(*), AVG(engagement_score)
                FROM audience_members
                GROUP BY platform
            """)).fetchall()
            
            return {
                'total_members': result[0] or 0,
                'by_tier': {
                    'top_fan': result[1] or 0,
                    'superfan': result[2] or 0,
                    'engaged': result[3] or 0,
                    'casual': result[4] or 0
                },
                'total_interactions': result[5] or 0,
                'avg_engagement': float(result[6]) if result[6] else 0,
                'avg_sentiment': float(result[7]) if result[7] else 0,
                'by_platform': [
                    {'platform': row[0], 'count': row[1], 'avg_engagement': float(row[2]) if row[2] else 0}
                    for row in platform_breakdown
                ]
            }
            
    except Exception as e:
        logger.error(f"Error getting audience stats: {e}")
        return {'total_members': 0, 'by_tier': {}, 'error': str(e)}


@router.post("/audience/{member_id}/update-tier")
async def recalculate_fan_tier(member_id: str):
    """Recalculate fan tier for an audience member."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # Get member stats
            result = conn.execute(text("""
                SELECT total_interactions, engagement_score, fan_tier
                FROM audience_members WHERE id = :id
            """), {'id': member_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Member not found")
            
            new_tier = await calculate_fan_tier({
                'total_interactions': result[0],
                'engagement_score': float(result[1]) if result[1] else 0
            })
            
            old_tier = result[2]
            
            if new_tier != old_tier:
                conn.execute(text("""
                    UPDATE audience_members SET 
                        fan_tier = :tier,
                        is_top_fan = :is_top,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    'id': member_id,
                    'tier': new_tier,
                    'is_top': new_tier == 'top_fan'
                })
                conn.commit()
                
                await publish_event(FanTopics.FAN_TIER_CHANGED, {
                    'member_id': member_id,
                    'old_tier': old_tier,
                    'new_tier': new_tier
                })
                
                if new_tier == 'top_fan':
                    await publish_event(FanTopics.TOP_FAN_ALERT, {
                        'member_id': member_id,
                        'message': 'New top fan identified!'
                    })
            
            return {'member_id': member_id, 'old_tier': old_tier, 'new_tier': new_tier}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# API ENDPOINTS - INBOX (Combined Comments View)
# =============================================================================

@router.get("/inbox")
async def get_inbox(
    status: str = 'new',
    platform: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """Get inbox of comments requiring attention."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            query = """
                SELECT tc.*, am.username as author_handle, am.fan_tier, am.engagement_score
                FROM tracked_comments tc
                LEFT JOIN audience_members am ON tc.audience_member_id = am.id
                WHERE tc.status = :status
            """
            params = {'status': status, 'limit': limit}
            
            if platform:
                query += " AND tc.platform = :platform"
                params['platform'] = platform
            
            query += " ORDER BY am.engagement_score DESC NULLS LAST, tc.created_at DESC LIMIT :limit"
            
            result = conn.execute(text(query), params).fetchall()
            
            # Prioritize top fans
            inbox = []
            for row in result:
                inbox.append({
                    'id': str(row[0]),
                    'platform': row[1],
                    'post_id': row[2],
                    'comment_id': row[3],
                    'author': {
                        'username': row[5],
                        'display_name': row[6],
                        'avatar_url': row[7],
                        'fan_tier': row[-2] if len(row) > 20 else None,
                        'engagement_score': float(row[-1]) if row[-1] else 0
                    },
                    'text': row[9],
                    'sentiment': row[15],
                    'intent': row[16],
                    'status': row[18],
                    'created_at': row[22].isoformat() if row[22] else None
                })
            
            return {'inbox': inbox, 'count': len(inbox)}
            
    except Exception as e:
        logger.error(f"Error getting inbox: {e}")
        return {'inbox': [], 'count': 0}

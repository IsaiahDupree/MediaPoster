"""
Instagram Automation API Endpoints
Comment and engagement automation based on Riona-AI-Agent patterns
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from services.instagram.comment_automation import (
    InstagramCommentAutomation,
    CommentTarget,
    get_instagram_automation
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/instagram/automation", tags=["Instagram Automation"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CommentRequest(BaseModel):
    """Request to post a comment"""
    post_url: str
    post_username: Optional[str] = ""
    post_caption: Optional[str] = ""
    hashtags: Optional[List[str]] = []
    comment_text: Optional[str] = None  # If None, AI generates
    account_username: str  # Which account to use


class CommentResponse(BaseModel):
    """Response from comment attempt"""
    success: bool
    post_url: str
    comment_text: str
    method_used: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


class EngagementSessionRequest(BaseModel):
    """Request to start an engagement session"""
    account_username: str
    hashtags: Optional[List[str]] = None
    target_usernames: Optional[List[str]] = None
    max_posts: int = 10
    actions: Optional[List[str]] = ["like", "comment"]


class EngagementSessionResponse(BaseModel):
    """Response from engagement session"""
    session_id: str
    account_username: str
    started_at: str
    posts_interacted: int
    comments_posted: int
    likes_given: int
    follows_sent: int
    errors: List[str]


class AICommentRequest(BaseModel):
    """Request to generate an AI comment"""
    post_caption: str
    post_username: str
    hashtags: Optional[List[str]] = []
    brand_voice: Optional[str] = "friendly"
    brand_topics: Optional[List[str]] = []


class AICommentResponse(BaseModel):
    """Response with generated AI comment"""
    comment: str
    generated_at: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/comment", response_model=CommentResponse)
async def post_comment(request: CommentRequest):
    """
    Post a comment on an Instagram post.
    
    If comment_text is not provided, AI generates a contextual comment.
    """
    try:
        automation = get_instagram_automation(request.account_username)
        
        target = CommentTarget(
            post_url=request.post_url,
            username=request.post_username,
            caption=request.post_caption,
            hashtags=request.hashtags or []
        )
        
        result = await automation.comment_on_post(
            target=target,
            comment_text=request.comment_text
        )
        
        return CommentResponse(
            success=result.success,
            post_url=result.post_url,
            comment_text=result.comment_text,
            method_used=result.method_used,
            error=result.error,
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Comment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-comment", response_model=AICommentResponse)
async def generate_ai_comment(request: AICommentRequest):
    """
    Generate an AI comment without posting it.
    
    Useful for previewing/approving comments before posting.
    """
    try:
        # Use a default automation instance for generation
        automation = get_instagram_automation("_generator")
        
        brand_context = None
        if request.brand_voice or request.brand_topics:
            brand_context = {
                "voice": request.brand_voice,
                "topics": request.brand_topics or []
            }
        
        comment = await automation.generate_ai_comment(
            post_caption=request.post_caption,
            post_username=request.post_username,
            hashtags=request.hashtags or [],
            brand_context=brand_context
        )
        
        return AICommentResponse(
            comment=comment,
            generated_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"AI comment generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/start", response_model=EngagementSessionResponse)
async def start_engagement_session(
    request: EngagementSessionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start an automated engagement session.
    
    Runs in background, engaging with posts based on hashtags or target users.
    """
    try:
        automation = get_instagram_automation(request.account_username)
        
        session = await automation.run_engagement_session(
            hashtags=request.hashtags,
            target_usernames=request.target_usernames,
            max_posts=request.max_posts,
            actions=request.actions
        )
        
        return EngagementSessionResponse(
            session_id=session.session_id,
            account_username=session.account_username,
            started_at=session.started_at,
            posts_interacted=session.posts_interacted,
            comments_posted=session.comments_posted,
            likes_given=session.likes_given,
            follows_sent=session.follows_sent,
            errors=session.errors
        )
    except Exception as e:
        logger.error(f"Session start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_interaction_history(
    account_username: Optional[str] = None,
    interaction_type: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    Get engagement interaction history.
    """
    import os
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT * FROM engagement_interactions
            WHERE 1=1
        """
        params = []
        
        if account_username:
            query += " AND account_username = %s"
            params.append(account_username)
        
        if interaction_type:
            query += " AND interaction_type = %s"
            params.append(interaction_type)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        
        return {
            "success": True,
            "interactions": [dict(row) for row in rows],
            "count": len(rows)
        }
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        return {
            "success": False,
            "interactions": [],
            "error": str(e)
        }
    finally:
        if conn:
            conn.close()


@router.get("/status")
async def get_automation_status():
    """
    Get status of Instagram automation service.
    """
    from services.instagram.comment_automation import _automation_instances
    
    return {
        "success": True,
        "active_accounts": list(_automation_instances.keys()),
        "riona_source": "Backend/external_libs/riona-ai-agent",
        "features": [
            "AI-generated contextual comments",
            "Human-like typing patterns",
            "Session persistence with cookies",
            "Engagement history tracking"
        ]
    }

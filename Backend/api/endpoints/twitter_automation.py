"""
Twitter/X Automation API Endpoints
DM and engagement automation
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from services.twitter.dm_automation import (
    TwitterDMAutomation,
    DMTarget,
    get_twitter_dm_automation
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/twitter/automation", tags=["Twitter Automation"])


class DMRequest(BaseModel):
    target_username: str
    context: Optional[str] = None
    message_text: Optional[str] = None
    tone: str = "professional"
    goal: str = "network"
    account_username: str


class DMResponse(BaseModel):
    success: bool
    username: str
    message_text: str
    method_used: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


class DMSessionRequest(BaseModel):
    account_username: str
    targets: List[dict]
    delay_between: float = 60.0
    goal: str = "network"


class DMSessionResponse(BaseModel):
    session_id: str
    account_username: str
    started_at: str
    messages_sent: int
    conversations_opened: int
    errors: List[str]


class AIMessageRequest(BaseModel):
    recipient_username: str
    context: Optional[str] = None
    tone: str = "professional"
    goal: str = "network"


class AIMessageResponse(BaseModel):
    message: str
    generated_at: str


@router.post("/dm", response_model=DMResponse)
async def send_dm(request: DMRequest):
    """Send a DM to a Twitter/X user."""
    try:
        automation = get_twitter_dm_automation(request.account_username)
        
        target = DMTarget(
            username=request.target_username,
            context=request.context
        )
        
        result = await automation.send_dm(
            target=target,
            message_text=request.message_text,
            tone=request.tone,
            goal=request.goal
        )
        
        return DMResponse(
            success=result.success,
            username=result.username,
            message_text=result.message_text,
            method_used=result.method_used,
            error=result.error,
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"DM failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-message", response_model=AIMessageResponse)
async def generate_ai_message(request: AIMessageRequest):
    """Generate an AI message without sending it."""
    try:
        automation = get_twitter_dm_automation("_generator")
        
        message = await automation.generate_ai_message(
            recipient_username=request.recipient_username,
            context=request.context,
            tone=request.tone,
            goal=request.goal
        )
        
        return AIMessageResponse(
            message=message,
            generated_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"AI message generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/start", response_model=DMSessionResponse)
async def start_dm_session(request: DMSessionRequest):
    """Start a DM session to multiple users."""
    try:
        automation = get_twitter_dm_automation(request.account_username)
        
        targets = [
            DMTarget(username=t.get("username"), context=t.get("context"))
            for t in request.targets
        ]
        
        session = await automation.run_dm_session(
            targets=targets,
            delay_between=request.delay_between,
            goal=request.goal
        )
        
        return DMSessionResponse(
            session_id=session.session_id,
            account_username=session.account_username,
            started_at=session.started_at,
            messages_sent=session.messages_sent,
            conversations_opened=session.conversations_opened,
            errors=session.errors
        )
    except Exception as e:
        logger.error(f"Session start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_dm_history(
    account_username: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get Twitter DM history."""
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
            WHERE interaction_type = 'dm'
            AND platform = 'twitter'
        """
        params = []
        
        if account_username:
            query += " AND account_username = %s"
            params.append(account_username)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        
        return {
            "success": True,
            "messages": [dict(row) for row in rows],
            "count": len(rows)
        }
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        return {"success": False, "messages": [], "error": str(e)}
    finally:
        if conn:
            conn.close()


@router.get("/status")
async def get_automation_status():
    """Get status of Twitter DM automation service."""
    from services.twitter.dm_automation import _dm_instances
    
    return {
        "success": True,
        "platform": "twitter",
        "active_accounts": list(_dm_instances.keys()),
        "features": [
            "AI-generated professional DMs",
            "Human-like timing patterns",
            "Session-based bulk messaging",
            "Message history tracking"
        ]
    }

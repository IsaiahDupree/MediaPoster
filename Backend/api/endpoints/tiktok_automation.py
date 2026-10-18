"""
TikTok Automation API Endpoints
DM and engagement automation
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from services.tiktok.dm_automation import (
    TikTokDMAutomation,
    DMTarget,
    get_tiktok_dm_automation
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tiktok/automation", tags=["TikTok Automation"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DMRequest(BaseModel):
    """Request to send a DM"""
    target_username: str
    context: Optional[str] = None
    message_text: Optional[str] = None
    tone: str = "friendly"
    goal: str = "engage"
    account_username: str


class DMResponse(BaseModel):
    """Response from DM attempt"""
    success: bool
    username: str
    message_text: str
    method_used: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


class DMSessionRequest(BaseModel):
    """Request to start a DM session"""
    account_username: str
    targets: List[dict]  # List of {username, context}
    delay_between: float = 30.0
    goal: str = "engage"


class DMSessionResponse(BaseModel):
    """Response from DM session"""
    session_id: str
    account_username: str
    started_at: str
    messages_sent: int
    conversations_opened: int
    errors: List[str]


class AIMessageRequest(BaseModel):
    """Request to generate an AI message"""
    recipient_username: str
    context: Optional[str] = None
    tone: str = "friendly"
    goal: str = "engage"


class AIMessageResponse(BaseModel):
    """Response with generated AI message"""
    message: str
    generated_at: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/dm", response_model=DMResponse)
async def send_dm(request: DMRequest):
    """
    Send a DM to a TikTok user.
    
    If message_text is not provided, AI generates a contextual message.
    """
    try:
        automation = get_tiktok_dm_automation(request.account_username)
        
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
    """
    Generate an AI message without sending it.
    """
    try:
        automation = get_tiktok_dm_automation("_generator")
        
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
    """
    Start a DM session to multiple users.
    """
    try:
        automation = get_tiktok_dm_automation(request.account_username)
        
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
    """
    Get TikTok DM history.
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
            WHERE interaction_type = 'dm'
            AND platform = 'tiktok'
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
        return {
            "success": False,
            "messages": [],
            "error": str(e)
        }
    finally:
        if conn:
            conn.close()


@router.get("/status")
async def get_automation_status():
    """
    Get status of TikTok DM automation service.
    """
    from services.tiktok.dm_automation import _dm_instances
    
    return {
        "success": True,
        "platform": "tiktok",
        "active_accounts": list(_dm_instances.keys()),
        "features": [
            "AI-generated contextual DMs",
            "Human-like timing patterns",
            "Session-based bulk messaging",
            "Message history tracking"
        ]
    }

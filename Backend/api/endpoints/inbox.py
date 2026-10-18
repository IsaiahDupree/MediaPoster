"""
API Endpoints for Community Inbox
Unified message aggregation and AI-powered reply suggestions.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

router = APIRouter(prefix="/inbox", tags=["Community Inbox"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class MessageFilters(BaseModel):
    """Filters for message queries."""
    status: Optional[str] = None
    platform: Optional[str] = None
    message_type: Optional[str] = None
    priority: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    """Request to update message status."""
    status: str = Field(..., description="New status: unread, read, replied, archived, spam")


class AssignMessageRequest(BaseModel):
    """Request to assign message to user."""
    assigned_to: str = Field(..., description="User to assign message to")


class AddTagsRequest(BaseModel):
    """Request to add tags to message."""
    tags: List[str] = Field(..., description="Tags to add")


class ReplyRequest(BaseModel):
    """Request to send a reply."""
    content: str = Field(..., description="Reply content")
    is_ai_generated: bool = Field(default=False)


class SavedReplyRequest(BaseModel):
    """Request to create/update saved reply."""
    name: str = Field(..., description="Reply name")
    content: str = Field(..., description="Reply template content")
    category: str = Field(default="general")
    variables: List[str] = Field(default=[])
    platforms: List[str] = Field(default=[])


class ContentIdeaRequest(BaseModel):
    """Request to create content idea from message."""
    title: str = Field(..., description="Idea title")
    description: str = Field(default="")
    content_type: str = Field(default="video")
    platforms: List[str] = Field(default=[])


# =============================================================================
# MESSAGE ENDPOINTS
# =============================================================================

@router.get("/messages")
async def get_messages(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    message_type: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0
):
    """Get inbox messages with filters."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        messages = inbox.get_messages(
            status=status,
            platform=platform,
            message_type=message_type,
            priority=priority,
            limit=limit,
            offset=offset
        )
        
        return {
            "messages": [m.to_dict() for m in messages],
            "count": len(messages),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/unread/count")
async def get_unread_count(platform: Optional[str] = None):
    """Get count of unread messages."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        count = inbox.get_unread_count(platform=platform)
        
        return {"unread_count": count, "platform": platform}
        
    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/{message_id}")
async def get_message(message_id: str):
    """Get a specific message."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        message = inbox.get_message(message_id)
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return message.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/messages/{message_id}/status")
async def update_message_status(message_id: str, request: UpdateStatusRequest):
    """Update message status."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        success = inbox.update_status(message_id, request.status)
        
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {"success": True, "status": request.status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/messages/{message_id}/assign")
async def assign_message(message_id: str, request: AssignMessageRequest):
    """Assign message to a user."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        success = inbox.assign_message(message_id, request.assigned_to)
        
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {"success": True, "assigned_to": request.assigned_to}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/{message_id}/tags")
async def add_message_tags(message_id: str, request: AddTagsRequest):
    """Add tags to a message."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        success = inbox.add_tags(message_id, request.tags)
        
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {"success": True, "tags_added": request.tags}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI SUGGESTIONS ENDPOINTS
# =============================================================================

@router.get("/messages/{message_id}/ai-suggestions")
async def get_ai_suggestions(message_id: str, num_suggestions: int = 3):
    """Get AI-generated reply suggestions for a message."""
    try:
        from services.inbox import get_inbox_service
        from services.inbox.ai_reply_service import get_ai_reply_service
        
        inbox = get_inbox_service()
        ai = get_ai_reply_service()
        
        message = inbox.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        suggestions = await ai.generate_suggestions(
            message_content=message.content,
            sender_username=message.sender_username,
            platform=message.platform,
            message_type=message.message_type,
            context={
                "post_caption": message.post_caption,
                "sender_follower_count": message.sender_follower_count
            },
            num_suggestions=num_suggestions
        )
        
        return {
            "message_id": message_id,
            "suggestions": [
                {
                    "content": s.content,
                    "tone": s.tone,
                    "intent": s.intent,
                    "confidence": s.confidence
                }
                for s in suggestions
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get AI suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/{message_id}/ai-generate")
async def generate_ai_reply(message_id: str, tone: str = "friendly"):
    """Generate a single AI reply with specified tone."""
    try:
        from services.inbox import get_inbox_service
        from services.inbox.ai_reply_service import get_ai_reply_service
        
        inbox = get_inbox_service()
        ai = get_ai_reply_service()
        
        message = inbox.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        suggestions = await ai.generate_suggestions(
            message_content=message.content,
            sender_username=message.sender_username,
            platform=message.platform,
            message_type=message.message_type,
            num_suggestions=1
        )
        
        if suggestions:
            return {
                "message_id": message_id,
                "generated_reply": suggestions[0].content,
                "tone": suggestions[0].tone
            }
        
        return {"message_id": message_id, "generated_reply": None}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate AI reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-sentiment")
async def analyze_message_sentiment(content: str):
    """Analyze sentiment and intent of a message."""
    try:
        from services.inbox.ai_reply_service import get_ai_reply_service
        
        ai = get_ai_reply_service()
        analysis = await ai.analyze_sentiment(content)
        
        return {"content": content, "analysis": analysis}
        
    except Exception as e:
        logger.error(f"Failed to analyze sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SAVED REPLIES ENDPOINTS
# =============================================================================

@router.get("/saved-replies")
async def get_saved_replies(category: Optional[str] = None):
    """Get all saved reply templates."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        replies = inbox.get_saved_replies(category=category)
        
        return {
            "saved_replies": [r.to_dict() for r in replies],
            "count": len(replies)
        }
        
    except Exception as e:
        logger.error(f"Failed to get saved replies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/saved-replies")
async def create_saved_reply(request: SavedReplyRequest):
    """Create a new saved reply template."""
    try:
        from services.inbox import get_inbox_service, SavedReply
        
        inbox = get_inbox_service()
        
        reply = SavedReply(
            name=request.name,
            content=request.content,
            category=request.category,
            variables=request.variables,
            platforms=request.platforms
        )
        
        created = inbox.create_saved_reply(reply)
        return {"success": True, "saved_reply": created.to_dict()}
        
    except Exception as e:
        logger.error(f"Failed to create saved reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/saved-replies/{reply_id}/use")
async def use_saved_reply(reply_id: str, variables: Optional[Dict[str, str]] = None):
    """Use a saved reply, replacing variables."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        content = inbox.use_saved_reply(reply_id, variables or {})
        
        if not content:
            raise HTTPException(status_code=404, detail="Saved reply not found")
        
        return {"content": content, "reply_id": reply_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to use saved reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CONTENT IDEAS ENDPOINTS
# =============================================================================

@router.post("/messages/{message_id}/to-idea")
async def create_idea_from_message(message_id: str, request: ContentIdeaRequest):
    """Create a content idea from a message."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        
        # Verify message exists
        message = inbox.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        idea = inbox.create_content_idea(
            message_id=message_id,
            title=request.title,
            description=request.description,
            content_type=request.content_type,
            platforms=request.platforms
        )
        
        return {"success": True, "content_idea": idea.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create content idea: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content-ideas")
async def get_content_ideas(status: Optional[str] = None):
    """Get content ideas generated from inbox messages."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        ideas = inbox.get_content_ideas(status=status)
        
        return {
            "content_ideas": [i.to_dict() for i in ideas],
            "count": len(ideas)
        }
        
    except Exception as e:
        logger.error(f"Failed to get content ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATS ENDPOINTS
# =============================================================================

@router.get("/stats")
async def get_inbox_stats():
    """Get inbox statistics."""
    try:
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        stats = inbox.get_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PLATFORM SYNC ENDPOINTS
# =============================================================================

@router.post("/sync/{platform}")
async def sync_platform(platform: str, account_id: Optional[int] = None):
    """
    Sync messages from a platform.
    
    Supported platforms: instagram, tiktok, twitter
    """
    try:
        if platform == "instagram":
            from services.inbox.platform_connectors import get_instagram_connector
            connector = get_instagram_connector()
        elif platform == "tiktok":
            from services.inbox.platform_connectors import get_tiktok_connector
            connector = get_tiktok_connector()
        elif platform == "twitter":
            from services.inbox.platform_connectors import get_twitter_connector
            connector = get_twitter_connector()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
        
        result = await connector.sync_to_inbox(account_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Platform sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all_platforms():
    """Sync messages from all platforms."""
    try:
        results = {}
        
        # Instagram
        try:
            from services.inbox.platform_connectors import get_instagram_connector
            ig = get_instagram_connector()
            results["instagram"] = await ig.sync_to_inbox()
        except Exception as e:
            results["instagram"] = {"success": False, "error": str(e)}
        
        # TikTok
        try:
            from services.inbox.platform_connectors import get_tiktok_connector
            tt = get_tiktok_connector()
            results["tiktok"] = await tt.sync_to_inbox()
        except Exception as e:
            results["tiktok"] = {"success": False, "error": str(e)}
        
        # Twitter
        try:
            from services.inbox.platform_connectors import get_twitter_connector
            tw = get_twitter_connector()
            results["twitter"] = await tw.sync_to_inbox()
        except Exception as e:
            results["twitter"] = {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Sync all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

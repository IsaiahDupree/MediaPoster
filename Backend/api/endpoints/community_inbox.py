"""
Community Inbox API (INBOX-005)
================================
Unified inbox for managing comments and DMs across all platforms.

Endpoints:
- GET /api/inbox/messages - List all inbox messages
- GET /api/inbox/messages/{message_id} - Get single message
- PUT /api/inbox/messages/{message_id} - Update message (mark read, respond, etc.)
- POST /api/inbox/messages/{message_id}/respond - Send response
- POST /api/inbox/fetch - Manually trigger comment fetch
- GET /api/inbox/conversations - List conversations
- GET /api/inbox/stats - Get inbox statistics
- GET /api/inbox/templates - Get response templates
- POST /api/inbox/templates - Create response template
- GET /api/inbox/rules - Get auto-reply rules
- POST /api/inbox/rules - Create auto-reply rule
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import async_session_maker
from database.models import (
    CommunityInboxMessage,
    InboxConversation,
    InboxAutoReplyRule,
    InboxAnalytics,
    InboxResponseTemplate
)
from services.comment_fetcher_service import get_comment_fetcher
from loguru import logger

router = APIRouter(prefix="/api/inbox", tags=["Community Inbox"])


# ==================== Request/Response Models ====================

class InboxMessageResponse(BaseModel):
    """Response model for inbox message"""
    id: str
    platform: str
    message_type: str
    author_handle: str
    author_name: Optional[str]
    text: str
    sentiment_label: Optional[str]
    response_status: str
    created_at_platform: Optional[datetime]
    created_at: datetime
    conversation_id: Optional[str]
    is_qualified_lead: bool
    priority: str

    class Config:
        from_attributes = True


class InboxMessageDetail(InboxMessageResponse):
    """Detailed inbox message with all fields"""
    source_url: Optional[str]
    author_profile_url: Optional[str]
    media_urls: Optional[List[str]]
    sentiment_score: Optional[float]
    emotion_tags: Optional[List[str]]
    intent: Optional[str]
    response_text: Optional[str]
    responded_at: Optional[datetime]
    platform_data: Optional[Dict[str, Any]]


class RespondToMessageRequest(BaseModel):
    """Request to respond to a message"""
    response_text: str = Field(..., min_length=1, max_length=5000)
    response_method: str = Field(default="manual", pattern="^(manual|ai_suggested|auto_rule|template)$")
    close_conversation: bool = False


class UpdateMessageRequest(BaseModel):
    """Request to update a message"""
    response_status: Optional[str] = Field(None, pattern="^(unanswered|pending|responded|closed|escalated|ignored)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    is_spam: Optional[bool] = None
    is_hidden: Optional[bool] = None
    assigned_to_user_id: Optional[str] = None


class CreateResponseTemplateRequest(BaseModel):
    """Request to create a response template"""
    name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = None
    template_text: str = Field(..., min_length=1, max_length=5000)
    platforms: Optional[List[str]] = None


class CreateAutoReplyRuleRequest(BaseModel):
    """Request to create an auto-reply rule"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    platforms: List[str] = Field(..., min_items=1)
    message_types: List[str] = Field(..., min_items=1)
    keyword_triggers: Optional[List[str]] = None
    keyword_match_type: str = Field(default="contains", pattern="^(exact|contains|starts_with|regex)$")
    sentiment_filter: Optional[str] = Field(None, pattern="^(positive|neutral|negative|any)$")
    reply_template: str = Field(..., min_length=1, max_length=5000)
    max_uses_per_day: Optional[int] = None
    priority: int = Field(default=0, ge=0, le=100)


# ==================== Endpoints ====================

@router.get("/messages", response_model=Dict[str, Any])
async def list_inbox_messages(
    workspace_id: str = Query(..., description="Workspace UUID"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    response_status: Optional[str] = Query(None, description="Filter by response status"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    is_qualified_lead: Optional[bool] = Query(None, description="Filter by qualified leads"),
    unread_only: bool = Query(False, description="Show only unread messages"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List inbox messages with filters

    Returns paginated list of messages with filters for platform,
    message type, response status, sentiment, and more.
    """
    async with async_session_maker() as session:
        # Build query
        query = select(CommunityInboxMessage).where(
            CommunityInboxMessage.workspace_id == workspace_id
        )

        # Apply filters
        if platform:
            query = query.where(CommunityInboxMessage.platform == platform)

        if message_type:
            query = query.where(CommunityInboxMessage.message_type == message_type)

        if response_status:
            query = query.where(CommunityInboxMessage.response_status == response_status)

        if sentiment:
            query = query.where(CommunityInboxMessage.sentiment_label == sentiment)

        if priority:
            query = query.where(CommunityInboxMessage.priority == priority)

        if is_qualified_lead is not None:
            query = query.where(CommunityInboxMessage.is_qualified_lead == is_qualified_lead)

        if unread_only:
            query = query.where(CommunityInboxMessage.read_at.is_(None))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(desc(CommunityInboxMessage.created_at_platform))
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await session.execute(query)
        messages = result.scalars().all()

        return {
            "messages": [
                InboxMessageResponse.from_orm(msg).dict()
                for msg in messages
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }


@router.get("/messages/{message_id}", response_model=InboxMessageDetail)
async def get_inbox_message(message_id: str):
    """Get detailed inbox message by ID"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(CommunityInboxMessage).where(
                CommunityInboxMessage.id == message_id
            )
        )
        message = result.scalar_one_or_none()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Mark as read
        if message.read_at is None:
            message.read_at = datetime.now(timezone.utc)
            await session.commit()

        return InboxMessageDetail.from_orm(message)


@router.put("/messages/{message_id}")
async def update_inbox_message(
    message_id: str,
    update: UpdateMessageRequest
):
    """Update inbox message (mark read, change status, assign, etc.)"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(CommunityInboxMessage).where(
                CommunityInboxMessage.id == message_id
            )
        )
        message = result.scalar_one_or_none()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Update fields
        if update.response_status is not None:
            message.response_status = update.response_status

            if update.response_status == "closed":
                message.closed_at = datetime.now(timezone.utc)

        if update.priority is not None:
            message.priority = update.priority

        if update.is_spam is not None:
            message.is_spam = update.is_spam

        if update.is_hidden is not None:
            message.is_hidden = update.is_hidden

        if update.assigned_to_user_id is not None:
            message.assigned_to_user_id = update.assigned_to_user_id
            message.assigned_at = datetime.now(timezone.utc)

        await session.commit()

        return {"success": True, "message": "Message updated"}


@router.post("/messages/{message_id}/respond")
async def respond_to_message(
    message_id: str,
    response: RespondToMessageRequest
):
    """
    Send response to an inbox message

    Note: This records the response in the database.
    Actual platform posting requires Safari automation or platform API.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(CommunityInboxMessage).where(
                CommunityInboxMessage.id == message_id
            )
        )
        message = result.scalar_one_or_none()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Update message with response
        message.response_text = response.response_text
        message.response_method = response.response_method
        message.responded_at = datetime.now(timezone.utc)
        message.response_status = "closed" if response.close_conversation else "responded"

        # Calculate response time
        if message.created_at_platform:
            delta = datetime.now(timezone.utc) - message.created_at_platform
            message.response_time_minutes = int(delta.total_seconds() / 60)

        if response.close_conversation:
            message.closed_at = datetime.now(timezone.utc)

        await session.commit()

        logger.info(
            f"✓ Response recorded for message {message_id[:8]} | "
            f"Platform: {message.platform} | "
            f"Method: {response.response_method}"
        )

        return {
            "success": True,
            "message": "Response recorded",
            "message_id": message_id,
            "response_time_minutes": message.response_time_minutes
        }


@router.post("/fetch")
async def trigger_comment_fetch(
    workspace_id: str = Query(..., description="Workspace UUID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to fetch back")
):
    """Manually trigger comment fetching"""
    fetcher = get_comment_fetcher()

    results = await fetcher.fetch_recent_comments(
        workspace_id=workspace_id,
        hours=hours
    )

    return {
        "success": True,
        "results": results,
        "total_comments": sum(results.values())
    }


@router.get("/conversations")
async def list_conversations(
    workspace_id: str = Query(..., description="Workspace UUID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List inbox conversations"""
    async with async_session_maker() as session:
        query = select(InboxConversation).where(
            InboxConversation.workspace_id == workspace_id
        )

        if status:
            query = query.where(InboxConversation.status == status)

        if platform:
            query = query.where(InboxConversation.platform == platform)

        # Get total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(desc(InboxConversation.last_message_at))
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        conversations = result.scalars().all()

        return {
            "conversations": [
                {
                    "id": str(conv.id),
                    "conversation_id": conv.conversation_id,
                    "platform": conv.platform,
                    "author_handle": conv.author_handle,
                    "message_count": conv.message_count,
                    "status": conv.status,
                    "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None
                }
                for conv in conversations
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.get("/stats")
async def get_inbox_stats(
    workspace_id: str = Query(..., description="Workspace UUID")
):
    """Get inbox statistics"""
    async with async_session_maker() as session:
        # Total messages
        total_result = await session.execute(
            select(func.count(CommunityInboxMessage.id)).where(
                CommunityInboxMessage.workspace_id == workspace_id
            )
        )
        total_messages = total_result.scalar() or 0

        # Unread messages
        unread_result = await session.execute(
            select(func.count(CommunityInboxMessage.id)).where(
                and_(
                    CommunityInboxMessage.workspace_id == workspace_id,
                    CommunityInboxMessage.read_at.is_(None)
                )
            )
        )
        unread = unread_result.scalar() or 0

        # Unanswered messages
        unanswered_result = await session.execute(
            select(func.count(CommunityInboxMessage.id)).where(
                and_(
                    CommunityInboxMessage.workspace_id == workspace_id,
                    CommunityInboxMessage.response_status == "unanswered"
                )
            )
        )
        unanswered = unanswered_result.scalar() or 0

        # Qualified leads
        leads_result = await session.execute(
            select(func.count(CommunityInboxMessage.id)).where(
                and_(
                    CommunityInboxMessage.workspace_id == workspace_id,
                    CommunityInboxMessage.is_qualified_lead == True
                )
            )
        )
        qualified_leads = leads_result.scalar() or 0

        # Sentiment distribution
        positive_result = await session.execute(
            select(func.count(CommunityInboxMessage.id)).where(
                and_(
                    CommunityInboxMessage.workspace_id == workspace_id,
                    CommunityInboxMessage.sentiment_label == "positive"
                )
            )
        )
        positive = positive_result.scalar() or 0

        neutral_result = await session.execute(
            select(func.count(CommunityInboxMessage.id)).where(
                and_(
                    CommunityInboxMessage.workspace_id == workspace_id,
                    CommunityInboxMessage.sentiment_label == "neutral"
                )
            )
        )
        neutral = neutral_result.scalar() or 0

        negative_result = await session.execute(
            select(func.count(CommunityInboxMessage.id)).where(
                and_(
                    CommunityInboxMessage.workspace_id == workspace_id,
                    CommunityInboxMessage.sentiment_label == "negative"
                )
            )
        )
        negative = negative_result.scalar() or 0

        # Platform breakdown
        platform_result = await session.execute(
            select(
                CommunityInboxMessage.platform,
                func.count(CommunityInboxMessage.id)
            ).where(
                CommunityInboxMessage.workspace_id == workspace_id
            ).group_by(CommunityInboxMessage.platform)
        )
        platforms = {row[0]: row[1] for row in platform_result}

        return {
            "total_messages": total_messages,
            "unread": unread,
            "unanswered": unanswered,
            "qualified_leads": qualified_leads,
            "sentiment": {
                "positive": positive,
                "neutral": neutral,
                "negative": negative
            },
            "by_platform": platforms
        }


@router.get("/templates")
async def list_response_templates(
    workspace_id: str = Query(..., description="Workspace UUID"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """List response templates"""
    async with async_session_maker() as session:
        query = select(InboxResponseTemplate).where(
            InboxResponseTemplate.workspace_id == workspace_id
        )

        if category:
            query = query.where(InboxResponseTemplate.category == category)

        query = query.order_by(InboxResponseTemplate.name)

        result = await session.execute(query)
        templates = result.scalars().all()

        return {
            "templates": [
                {
                    "id": str(tmpl.id),
                    "name": tmpl.name,
                    "category": tmpl.category,
                    "template_text": tmpl.template_text,
                    "platforms": tmpl.platforms,
                    "use_count": tmpl.use_count
                }
                for tmpl in templates
            ]
        }


@router.post("/templates")
async def create_response_template(
    workspace_id: str = Query(..., description="Workspace UUID"),
    template: CreateResponseTemplateRequest = None
):
    """Create a response template"""
    async with async_session_maker() as session:
        new_template = InboxResponseTemplate(
            id=uuid4(),
            workspace_id=workspace_id,
            name=template.name,
            category=template.category,
            template_text=template.template_text,
            platforms=template.platforms
        )

        session.add(new_template)
        await session.commit()

        return {
            "success": True,
            "template_id": str(new_template.id),
            "message": "Template created"
        }


@router.get("/rules")
async def list_auto_reply_rules(
    workspace_id: str = Query(..., description="Workspace UUID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List auto-reply rules"""
    async with async_session_maker() as session:
        query = select(InboxAutoReplyRule).where(
            InboxAutoReplyRule.workspace_id == workspace_id
        )

        if is_active is not None:
            query = query.where(InboxAutoReplyRule.is_active == is_active)

        query = query.order_by(desc(InboxAutoReplyRule.priority))

        result = await session.execute(query)
        rules = result.scalars().all()

        return {
            "rules": [
                {
                    "id": str(rule.id),
                    "name": rule.name,
                    "is_active": rule.is_active,
                    "platforms": rule.platforms,
                    "message_types": rule.message_types,
                    "keyword_triggers": rule.keyword_triggers,
                    "reply_template": rule.reply_template,
                    "priority": rule.priority,
                    "uses_today": rule.uses_today,
                    "max_uses_per_day": rule.max_uses_per_day
                }
                for rule in rules
            ]
        }


@router.post("/rules")
async def create_auto_reply_rule(
    workspace_id: str = Query(..., description="Workspace UUID"),
    rule: CreateAutoReplyRuleRequest = None
):
    """Create an auto-reply rule"""
    async with async_session_maker() as session:
        new_rule = InboxAutoReplyRule(
            id=uuid4(),
            workspace_id=workspace_id,
            name=rule.name,
            description=rule.description,
            platforms=rule.platforms,
            message_types=rule.message_types,
            keyword_triggers=rule.keyword_triggers,
            keyword_match_type=rule.keyword_match_type,
            sentiment_filter=rule.sentiment_filter,
            reply_template=rule.reply_template,
            max_uses_per_day=rule.max_uses_per_day,
            priority=rule.priority
        )

        session.add(new_rule)
        await session.commit()

        return {
            "success": True,
            "rule_id": str(new_rule.id),
            "message": "Auto-reply rule created"
        }

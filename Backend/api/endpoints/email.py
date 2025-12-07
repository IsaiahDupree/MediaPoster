"""
Email API endpoints
Send emails, manage campaigns, and track email events
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os

from database.connection import get_db
from database.models import OutboundMessage, Person
from services.email_service import EmailServiceProvider

router = APIRouter()


@router.get("/status")
async def get_esp_status():
    """Get ESP configuration status"""
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    enabled = bool(smtp_user and smtp_password)
    
    return {
        "enabled": enabled,
        "configured": enabled,
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "from_email": os.getenv("FROM_EMAIL", smtp_user),
        "from_name": os.getenv("FROM_NAME", "MediaPoster"),
        "message": "Email service is ready" if enabled else "Configure SMTP_USER and SMTP_PASSWORD env variables to enable email"
    }


class SendEmailRequest(BaseModel):
    person_id: UUID
    subject: str
    body_html: str
    body_text: Optional[str] = None
    segment_id: Optional[UUID] = None
    goal_type: Optional[str] = None
    variant: str = "A"


class SendSegmentEmailRequest(BaseModel):
    segment_id: UUID
    subject: str
    body_template: str
    goal_type: str
    variant: str = "A"
    personalization_data: Optional[Dict[str, Any]] = None


class EmailEventRequest(BaseModel):
    message_id: UUID
    event_type: str  # opened, clicked, replied, bounced, unsubscribed
    metadata: Optional[Dict[str, Any]] = None


@router.post("/send")
async def send_email(
    request: SendEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send email to a single person"""
    esp = EmailServiceProvider(db)
    
    try:
        message = await esp.send_email(
            person_id=request.person_id,
            subject=request.subject,
            body_html=request.body_html,
            body_text=request.body_text,
            segment_id=request.segment_id,
            goal_type=request.goal_type,
            variant=request.variant
        )
        
        return {
            "status": "success",
            "message_id": str(message.id),
            "sent_at": message.sent_at.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.post("/send-segment")
async def send_segment_email(
    request: SendSegmentEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send email campaign to entire segment"""
    esp = EmailServiceProvider(db)
    
    try:
        stats = await esp.send_to_segment(
            segment_id=request.segment_id,
            subject=request.subject,
            body_template=request.body_template,
            goal_type=request.goal_type,
            variant=request.variant,
            personalization_data=request.personalization_data
        )
        
        return {
            "status": "success",
            **stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send segment email: {str(e)}")


@router.post("/event")
async def record_email_event(
    request: EmailEventRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Record email event (webhook endpoint)
    Called by email service provider when events occur
    """
    esp = EmailServiceProvider(db)
    
    try:
        event = await esp.record_email_event(
            message_id=request.message_id,
            event_type=request.event_type,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "event_id": str(event.id)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record event: {str(e)}")


@router.get("/tracking/open/{message_id}")
async def track_email_open(
    message_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Tracking pixel endpoint for email opens
    Returns transparent 1x1 pixel
    """
    esp = EmailServiceProvider(db)
    
    try:
        await esp.record_email_event(
            message_id=message_id,
            event_type='opened'
        )
    except Exception as e:
        # Silently fail - don't break the pixel
        pass
    
    # Return 1x1 transparent GIF
    from fastapi.responses import Response
    
    pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    return Response(content=pixel, media_type="image/gif")


@router.get("/messages/{message_id}")
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get outbound message details"""
    result = await db.execute(
        select(OutboundMessage).where(OutboundMessage.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {
        "id": str(message.id),
        "person_id": str(message.person_id),
        "subject": message.subject,
        "channel": message.channel,
        "sent_at": message.sent_at.isoformat() if message.sent_at else None,
        "opened_at": message.opened_at.isoformat() if message.opened_at else None,
        "clicked_at": message.clicked_at.isoformat() if message.clicked_at else None,
        "replied_at": message.replied_at.isoformat() if message.replied_at else None
    }


@router.get("/person/{person_id}/messages")
async def get_person_messages(
    person_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get all messages sent to a person"""
    result = await db.execute(
        select(OutboundMessage)
        .where(OutboundMessage.person_id == person_id)
        .order_by(OutboundMessage.sent_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    return {
        "person_id": str(person_id),
        "total": len(messages),
        "messages": [
            {
                "id": str(m.id),
                "subject": m.subject,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "opened": bool(m.opened_at),
                "clicked": bool(m.clicked_at)
            }
            for m in messages
        ]
    }

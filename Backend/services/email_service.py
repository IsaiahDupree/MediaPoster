"""
Email Service Provider Integration (Phase 7)
Handles outbound email sending, template rendering, and event tracking
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4
from loguru import logger
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Person, Segment, OutboundMessage, PersonEvent


class EmailServiceProvider:
    """Email Service Provider for sending personalized emails"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "MediaPoster")
        self.enabled = bool(self.smtp_user and self.smtp_password)
    
    async def send_email(
        self,
        person_id: UUID,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        segment_id: Optional[UUID] = None,
        goal_type: Optional[str] = None,
        variant: str = "A",
        metadata: Optional[Dict[str, Any]] = None
    ) -> OutboundMessage:
        """
        Send email to a person
        
        Args:
            person_id: Person UUID
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body (optional, will strip HTML if not provided)
            segment_id: Optional segment this email is for
            goal_type: Campaign goal (nurture, launch, etc.)
            variant: A/B test variant
            metadata: Additional tracking metadata
            
        Returns:
            OutboundMessage record
        """
        if not self.enabled:
            logger.warning("ESP not configured, email will be recorded but not sent")
        
        # Get person email
        result = await self.db.execute(
            select(Person).where(Person.id == person_id)
        )
        person = result.scalar_one_or_none()
        
        if not person or not person.primary_email:
            raise ValueError(f"Person {person_id} has no email address")
        
        # Create outbound message record
        message = OutboundMessage(
            person_id=person_id,
            segment_id=segment_id,
            channel='email',
            goal_type=goal_type,
            variant=variant,
            subject=subject,
            body=body_html,
            sent_at=datetime.utcnow(),
            message_metadata=metadata or {}
        )
        self.db.add(message)
        await self.db.flush()
        
        # Send via SMTP if configured
        if self.enabled:
            try:
                self._send_smtp(
                    to_email=person.primary_email,
                    to_name=person.full_name,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    tracking_id=str(message.id)
                )
                logger.info(f"Email sent to {person.primary_email}: {subject}")
            except Exception as e:
                logger.error(f"Failed to send email to {person.primary_email}: {e}")
                message.message_metadata['send_error'] = str(e)
        
        await self.db.commit()
        return message
    
    async def send_to_segment(
        self,
        segment_id: UUID,
        subject: str,
        body_template: str,
        goal_type: str,
        variant: str = "A",
        personalization_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """
        Send email to all people in a segment
        
        Args:
            segment_id: Segment UUID
            subject: Email subject (supports {{variables}})
            body_template: HTML template (supports {{variables}})
            goal_type: Campaign goal
            variant: A/B variant
            personalization_data: Data for template rendering
            
        Returns:
            Stats dict with sent/failed counts
        """
        # Get segment members
        from database.models import SegmentMember
        
        result = await self.db.execute(
            select(Person)
            .join(SegmentMember, SegmentMember.person_id == Person.id)
            .where(SegmentMember.segment_id == segment_id)
        )
        people = result.scalars().all()
        
        logger.info(f"Sending email to {len(people)} people in segment {segment_id}")
        
        sent = 0
        failed = 0
        
        for person in people:
            try:
                # Render personalized template
                context = {
                    'person': person,
                    'full_name': person.full_name or 'there',
                    **(personalization_data or {})
                }
                
                rendered_subject = Template(subject).render(**context)
                rendered_body = Template(body_template).render(**context)
                
                await self.send_email(
                    person_id=person.id,
                    subject=rendered_subject,
                    body_html=rendered_body,
                    segment_id=segment_id,
                    goal_type=goal_type,
                    variant=variant
                )
                sent += 1
                
            except Exception as e:
                logger.error(f"Failed to send to person {person.id}: {e}")
                failed += 1
        
        return {
            "sent": sent,
            "failed": failed,
            "total": len(people)
        }
    
    def _send_smtp(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        body_html: str,
        body_text: Optional[str],
        tracking_id: str
    ):
        """Send email via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
        msg['Subject'] = subject
        
        # Add tracking pixel
        tracking_pixel = f'<img src="https://track.example.com/open/{tracking_id}" width="1" height="1" />'
        body_html_tracked = body_html + tracking_pixel
        
        # Plain text part
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        
        # HTML part
        msg.attach(MIMEText(body_html_tracked, 'html'))
        
        # Send
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
    
    async def record_email_event(
        self,
        message_id: UUID,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PersonEvent:
        """
        Record email event (opened, clicked, replied, etc.)
        
        Args:
            message_id: OutboundMessage UUID
            event_type: Event type (opened, clicked, replied, bounced, unsubscribed)
            metadata: Event metadata
            
        Returns:
            PersonEvent record
        """
        # Get message
        result = await self.db.execute(
            select(OutboundMessage).where(OutboundMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        # Update message timestamps
        now = datetime.utcnow()
        if event_type == 'opened' and not message.opened_at:
            message.opened_at = now
        elif event_type == 'clicked' and not message.clicked_at:
            message.clicked_at = now
        elif event_type == 'replied' and not message.replied_at:
            message.replied_at = now
        
        # Create person event
        event = PersonEvent(
            person_id=message.person_id,
            channel='email',
            event_type=f"email_{event_type}",
            platform_id=str(message_id),
            content_excerpt=message.subject,
            traffic_type='organic',  # Email is typically organic
            event_metadata={
                'message_id': str(message_id),
                'segment_id': str(message.segment_id) if message.segment_id else None,
                'goal_type': message.goal_type,
                'variant': message.variant,
                **(metadata or {})
            },
            occurred_at=now
        )
        self.db.add(event)
        
        await self.db.commit()
        
        logger.info(f"Recorded email event: {event_type} for message {message_id}")
        return event

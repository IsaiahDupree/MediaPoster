"""
People Graph Ingestion Service
Processes engagement data from platforms and builds the person graph
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Person, Identity, PersonEvent, PersonInsight
)


class PeopleIngestionService:
    """Service for ingesting people data from platform engagement"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_person_by_identity(
        self,
        channel: str,
        handle: str,
        **person_data
    ) -> Person:
        """
        Get existing person by identity or create new one
        
        Args:
            channel: Platform channel (instagram, facebook, etc.)
            handle: Platform handle/username
            **person_data: Optional person attributes (full_name, email, etc.)
            
        Returns:
            Person instance
        """
        # Check if identity exists
        result = await self.db.execute(
            select(Identity).where(
                Identity.channel == channel,
                Identity.handle == handle
            )
        )
        identity = result.scalar_one_or_none()
        
        if identity:
            # Update last_seen
            identity.last_seen_at = datetime.utcnow()
            await self.db.commit()
            
            # Return existing person
            result = await self.db.execute(
                select(Person).where(Person.id == identity.person_id)
            )
            return result.scalar_one()
        
        # Create new person
        person = Person(
            full_name=person_data.get('full_name'),
            primary_email=person_data.get('primary_email'),
            company=person_data.get('company'),
            role=person_data.get('role')
        )
        self.db.add(person)
        await self.db.flush()
        
        # Create identity
        identity = Identity(
            person_id=person.id,
            channel=channel,
            handle=handle,
            extra=person_data.get('extra', {}),
            is_verified=person_data.get('is_verified', False),
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow()
        )
        self.db.add(identity)
        
        # Create empty insights
        insights = PersonInsight(
            person_id=person.id,
            interests=[],
            tone_preferences=[],
            channel_preferences={},
            activity_state='active',
            last_active_at=datetime.utcnow(),
            warmth_score=0.5
        )
        self.db.add(insights)
        
        await self.db.commit()
        logger.info(f"Created new person via {channel}:{handle}")
        
        return person
    
    async def record_event(
        self,
        person_id: UUID,
        channel: str,
        event_type: str,
        platform_id: Optional[str] = None,
        content_excerpt: Optional[str] = None,
        sentiment: Optional[float] = None,
        traffic_type: str = 'organic',
        metadata: Optional[Dict[str, Any]] = None
    ) -> PersonEvent:
        """
        Record a person event
        
        Args:
            person_id: Person UUID
            channel: Platform channel
            event_type: Event type (commented, liked, shared, etc.)
            platform_id: Platform-specific content ID
            content_excerpt: Comment text or content snippet
            sentiment: Sentiment score (-1 to 1)
            traffic_type: 'organic' or 'paid'
            metadata: Additional event data
            
        Returns:
            PersonEvent instance
        """
        event = PersonEvent(
            person_id=person_id,
            channel=channel,
            event_type=event_type,
            platform_id=platform_id,
            content_excerpt=content_excerpt,
            sentiment=sentiment,
            traffic_type=traffic_type,
            event_metadata=metadata or {},
            occurred_at=datetime.utcnow()
        )
        self.db.add(event)
        
        # Update person insights last_active
        result = await self.db.execute(
            select(PersonInsight).where(PersonInsight.person_id == person_id)
        )
        insights = result.scalar_one_or_none()
        if insights:
            insights.last_active_at = datetime.utcnow()
            insights.activity_state = 'active'
        
        await self.db.commit()
        return event
    
    async def ingest_comment(
        self,
        channel: str,
        handle: str,
        platform_post_id: str,
        comment_text: str,
        comment_id: str,
        traffic_type: str = 'organic',
        **user_data
    ) -> PersonEvent:
        """
        Ingest a comment event
        
        Args:
            channel: Platform (instagram, facebook, etc.)
            handle: Commenter handle
            platform_post_id: Post ID being commented on
            comment_text: Comment content
            comment_id: Comment ID
            traffic_type: organic/paid
            **user_data: Additional user info (full_name, profile_pic, etc.)
            
        Returns:
            PersonEvent for the comment
        """
        # Get or create person
        person = await self.get_or_create_person_by_identity(
            channel=channel,
            handle=handle,
            full_name=user_data.get('full_name'),
            extra=user_data
        )
        
        # Record event
        event = await self.record_event(
            person_id=person.id,
            channel=channel,
            event_type='commented',
            platform_id=platform_post_id,
            content_excerpt=comment_text,
            traffic_type=traffic_type,
            metadata={
                'comment_id': comment_id,
                'user_data': user_data
            }
        )
        
        logger.debug(f"Ingested comment from {handle} on {channel}")
        return event
    
    async def ingest_like(
        self,
        channel: str,
        handle: str,
        platform_post_id: str,
        traffic_type: str = 'organic',
        **user_data
    ) -> PersonEvent:
        """Ingest a like/reaction event"""
        person = await self.get_or_create_person_by_identity(
            channel=channel,
            handle=handle,
            full_name=user_data.get('full_name'),
            extra=user_data
        )
        
        event = await self.record_event(
            person_id=person.id,
            channel=channel,
            event_type='liked',
            platform_id=platform_post_id,
            traffic_type=traffic_type,
            metadata={'user_data': user_data}
        )
        
        return event
    
    async def ingest_share(
        self,
        channel: str,
        handle: str,
        platform_post_id: str,
        traffic_type: str = 'organic',
        **user_data
    ) -> PersonEvent:
        """Ingest a share event"""
        person = await self.get_or_create_person_by_identity(
            channel=channel,
            handle=handle,
            full_name=user_data.get('full_name'),
            extra=user_data
        )
        
        event = await self.record_event(
            person_id=person.id,
            channel=channel,
            event_type='shared',
            platform_id=platform_post_id,
            traffic_type=traffic_type,
            metadata={'user_data': user_data}
        )
        
        return event

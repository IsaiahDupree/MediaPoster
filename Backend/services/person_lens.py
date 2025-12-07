"""
Person Lens Computer
Analyzes person events and computes insights (interests, tone, activity state, warmth score)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from collections import Counter
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Person, PersonEvent, PersonInsight


class PersonLensComputer:
    """Computes person insights from their event history"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def compute_lens_for_person(self, person_id: UUID) -> PersonInsight:
        """
        Compute full lens for a person based on their events
        
        Args:
            person_id: Person UUID
            
        Returns:
            Updated PersonInsight
        """
        # Get person's events (last 90 days)
        since = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(PersonEvent)
            .where(
                PersonEvent.person_id == person_id,
                PersonEvent.occurred_at >= since
            )
            .order_by(PersonEvent.occurred_at.desc())
        )
        events = list(result.scalars().all())  # Convert to list immediately
        
        if not events:
            logger.debug(f"No recent events for person {person_id}")
            return None
        
        # Compute components
        interests = await self._extract_interests(events)
        tone_prefs = await self._analyze_tone(events)
        channel_prefs = await self._compute_channel_preferences(events)
        activity_state = await self._determine_activity_state(events)
        warmth_score = await self._calculate_warmth_score(events)
        
        # Update or create insights
        result = await self.db.execute(
            select(PersonInsight).where(PersonInsight.person_id == person_id)
        )
        insights = result.scalar_one_or_none()
        
        if not insights:
            insights = PersonInsight(person_id=person_id)
            self.db.add(insights)
        
        # Update fields
        insights.interests = interests
        insights.tone_preferences = tone_prefs
        insights.channel_preferences = channel_prefs
        insights.activity_state = activity_state
        insights.warmth_score = warmth_score
        insights.last_active_at = events[0].occurred_at
        insights.updated_at = datetime.utcnow()
        
        await self.db.commit()
        logger.info(f"Updated lens for person {person_id}: {activity_state}, warmth={warmth_score:.2f}")
        
        return insights
    
    async def _extract_interests(self, events: List[PersonEvent]) -> List[str]:
        """Extract top interests from event content"""
        # Simple keyword extraction from comments
        # TODO: Use NLP/LLM for better topic extraction
        words = []
        for event in events:
            if event.content_excerpt:
                # Basic tokenization
                words.extend(event.content_excerpt.lower().split())
        
        # Filter common words and get top topics
        stopwords = {'the', 'a', 'an', 'this', 'that', 'is', 'it', 'to', 'and', 'or', 'of', 'in', 'on'}
        filtered = [w for w in words if len(w) > 3 and w not in stopwords]
        
        counter = Counter(filtered)
        top_interests = [word for word, count in counter.most_common(10)]
        
        return top_interests
    
    async def _analyze_tone(self, events: List[PersonEvent]) -> Dict[str, float]:
        """Analyze communication tone from events"""
        # Simple heuristics - TODO: Use LLM for better analysis
        tones = {
            'casual': 0.0,
            'formal': 0.0,
            'enthusiastic': 0.0,
            'technical': 0.0
        }
        
        for event in events:
            if not event.content_excerpt:
                continue
            
            text = event.content_excerpt.lower()
            
            # Simple markers
            if any(marker in text for marker in ['lol', '!', '😊', '❤️', 'love']):
                tones['enthusiastic'] += 1
            if any(marker in text for marker in ['api', 'code', 'function', 'system']):
                tones['technical'] += 1
            if len(text) > 100 and '.' in text:
                tones['formal'] += 1
            else:
                tones['casual'] += 1
        
        # Normalize
        total = sum(tones.values()) or 1
        return {k: v / total for k, v in tones.items()}
    
    async def _compute_channel_preferences(self, events: List[PersonEvent]) -> Dict[str, float]:
        """Compute channel preference scores"""
        channel_counts = Counter(event.channel for event in events)
        total = sum(channel_counts.values()) or 1
        
        return {
            channel: count / total
            for channel, count in channel_counts.most_common()
        }
    
    async def _determine_activity_state(self, events: List[PersonEvent]) -> str:
        """Determine current activity state"""
        if not events:
            return 'dormant'
        
        last_event = events[0].occurred_at
        days_ago = (datetime.utcnow() - last_event).days
        
        if days_ago <= 7:
            return 'active'
        elif days_ago <= 30:
            return 'warming'
        elif days_ago <= 90:
            return 'cool'
        else:
            return 'dormant'
    
    async def _calculate_warmth_score(self, events: List[PersonEvent]) -> float:
        """
        Calculate warmth score (0-1) based on recency, frequency, and engagement depth
        
        Uses RFM-like scoring:
        - Recency: how recently they engaged
        - Frequency: how often they engage
        - Depth: comments > likes > other actions
        """
        if not events:
            return 0.0
        
        # Recency score (0-1)
        last_event = events[0].occurred_at
        days_ago = (datetime.utcnow() - last_event).days
        recency_score = max(0, 1 - (days_ago / 90))  # Decay over 90 days
        
        # Frequency score (0-1)
        # Events per week, capped at 5
        weeks = 12  # Last 90 days
        frequency = len(events) / weeks
        frequency_score = min(1.0, frequency / 5)
        
        # Depth score (0-1)
        # Comments worth more than likes
        depth_weights = {
            'commented': 1.0,
            'shared': 0.8,
            'saved': 0.6,
            'liked': 0.3,
            'viewed': 0.1
        }
        
        total_depth = sum(depth_weights.get(e.event_type, 0.1) for e in events)
        max_depth = len(events)  # All comments would be max
        depth_score = total_depth / max_depth if max_depth > 0 else 0
        
        # Weighted average
        warmth = (
            recency_score * 0.4 +
            frequency_score * 0.3 +
            depth_score * 0.3
        )
        
        return round(warmth, 3)
    
    async def recompute_all_active_people(self) -> int:
        """
        Recompute lens for all recently active people
        
        Returns:
            Number of people updated
        """
        # Get people with events in last 90 days
        since = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(PersonEvent.person_id)
            .where(PersonEvent.occurred_at >= since)
            .distinct()
        )
        person_ids = [row[0] for row in list(result.fetchall())]  # Convert to list immediately
        
        logger.info(f"Recomputing lens for {len(person_ids)} active people")
        
        updated = 0
        for person_id in person_ids:
            try:
                await self.compute_lens_for_person(person_id)
                updated += 1
            except Exception as e:
                logger.error(f"Failed to compute lens for {person_id}: {e}")
        
        logger.success(f"Updated {updated}/{len(person_ids)} person lenses")
        return updated

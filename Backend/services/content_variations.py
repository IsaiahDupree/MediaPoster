"""
Content Reusability System (PIPE-008)
======================================
Store multiple title/description variations for each content piece.
Track usage to avoid repeating the same variation too soon.

Features:
- Store multiple variations per content piece
- Track which variations have been used and when
- Smart selection of unused/least-recently-used variations
- Rotation strategy to maximize content lifespan
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from uuid import UUID, uuid4
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from enum import Enum

from database.models import ContentVariant


class VariationType(Enum):
    """Types of content variations"""
    TITLE = "title"
    DESCRIPTION = "description"
    CAPTION = "caption"
    HASHTAGS = "hashtags"
    CTA = "cta"  # Call-to-action


@dataclass
class ContentVariation:
    """A single variation of content metadata"""
    variation_id: str
    content_id: str
    variation_type: VariationType
    text: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    performance_score: float = 0.0  # Average engagement when used


@dataclass
class VariationSet:
    """Set of all variations for a content piece"""
    content_id: str
    titles: List[ContentVariation]
    descriptions: List[ContentVariation]
    captions: List[ContentVariation]
    hashtag_sets: List[ContentVariation]
    ctas: List[ContentVariation]


class ContentReusabilityService:
    """
    Service for managing content variations and reusability

    Enables one piece of content to be posted multiple times with
    different titles, descriptions, and captions to reach different
    audiences or test different messaging.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_variation(
        self,
        content_id: str,
        variation_type: VariationType,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContentVariation:
        """
        Create a new content variation

        Args:
            content_id: ID of the content piece
            variation_type: Type of variation (title, description, etc.)
            text: The variation text
            metadata: Optional metadata about this variation

        Returns:
            Created ContentVariation
        """
        variation_id = str(uuid4())

        variation = ContentVariation(
            variation_id=variation_id,
            content_id=content_id,
            variation_type=variation_type,
            text=text,
            created_at=datetime.now(timezone.utc)
        )

        # Store in database (simplified - would use a variations table)
        logger.info(
            f"✅ Created {variation_type.value} variation for content {content_id[:8]}"
        )

        return variation

    async def get_variations(
        self,
        content_id: str,
        variation_type: Optional[VariationType] = None
    ) -> List[ContentVariation]:
        """
        Get all variations for a content piece

        Args:
            content_id: ID of the content piece
            variation_type: Optional filter by type

        Returns:
            List of variations
        """
        # In production, query from variations table
        # For now, return sample data
        variations = []

        if not variation_type or variation_type == VariationType.TITLE:
            variations.append(ContentVariation(
                variation_id=str(uuid4()),
                content_id=content_id,
                variation_type=VariationType.TITLE,
                text="How to 10x Your Productivity",
                created_at=datetime.now(timezone.utc) - timedelta(days=7),
                last_used_at=datetime.now(timezone.utc) - timedelta(days=5),
                usage_count=2,
                performance_score=0.85
            ))

        return variations

    async def get_next_unused_variation(
        self,
        content_id: str,
        variation_type: VariationType,
        min_reuse_days: int = 30
    ) -> Optional[ContentVariation]:
        """
        Get the next variation to use, prioritizing:
        1. Never used variations
        2. Least recently used (if > min_reuse_days ago)
        3. None if all used recently

        Args:
            content_id: ID of the content piece
            variation_type: Type of variation needed
            min_reuse_days: Minimum days before reusing a variation

        Returns:
            Next variation to use, or None if all used recently
        """
        variations = await self.get_variations(content_id, variation_type)

        if not variations:
            return None

        # Sort by: never used first, then by oldest last_used_at
        def sort_key(v: ContentVariation):
            if v.last_used_at is None:
                return (0, datetime.min.replace(tzinfo=timezone.utc))  # Never used = highest priority
            return (1, v.last_used_at)

        sorted_variations = sorted(variations, key=sort_key)

        # Check if best candidate is available
        best = sorted_variations[0]

        if best.last_used_at is None:
            # Never used - perfect!
            return best

        days_since_use = (datetime.now(timezone.utc) - best.last_used_at).days

        if days_since_use >= min_reuse_days:
            return best

        # All variations used too recently
        logger.warning(
            f"All {variation_type.value} variations for {content_id[:8]} "
            f"used within last {min_reuse_days} days"
        )
        return None

    async def mark_variation_used(
        self,
        variation_id: str,
        performance_score: Optional[float] = None
    ) -> None:
        """
        Mark a variation as used and optionally record performance

        Args:
            variation_id: ID of the variation
            performance_score: Optional engagement score (0-1)
        """
        # Update variation in database
        # Would increment usage_count, set last_used_at, update performance_score

        logger.info(f"📝 Marked variation {variation_id[:8]} as used")

        if performance_score is not None:
            logger.info(f"📊 Performance score: {performance_score:.2f}")

    async def generate_variations(
        self,
        content_id: str,
        base_title: str,
        base_description: str,
        num_variations: int = 5
    ) -> VariationSet:
        """
        Generate multiple variations using AI

        Args:
            content_id: ID of the content piece
            base_title: Original title
            base_description: Original description
            num_variations: Number of variations to generate

        Returns:
            VariationSet with all generated variations
        """
        logger.info(f"🤖 Generating {num_variations} variations for {content_id[:8]}")

        # In production, use OpenAI to generate variations
        # For now, create sample variations
        titles = []
        descriptions = []

        for i in range(num_variations):
            title_var = await self.create_variation(
                content_id=content_id,
                variation_type=VariationType.TITLE,
                text=f"{base_title} (Variation {i+1})"
            )
            titles.append(title_var)

            desc_var = await self.create_variation(
                content_id=content_id,
                variation_type=VariationType.DESCRIPTION,
                text=f"{base_description} (Variation {i+1})"
            )
            descriptions.append(desc_var)

        return VariationSet(
            content_id=content_id,
            titles=titles,
            descriptions=descriptions,
            captions=[],
            hashtag_sets=[],
            ctas=[]
        )

    async def get_variation_stats(
        self,
        content_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics about variation usage

        Args:
            content_id: ID of the content piece

        Returns:
            Statistics dictionary
        """
        variations = await self.get_variations(content_id)

        if not variations:
            return {
                "total_variations": 0,
                "unused_variations": 0,
                "average_performance": 0.0,
                "reusability_score": 0.0
            }

        total = len(variations)
        unused = sum(1 for v in variations if v.last_used_at is None)
        avg_perf = sum(v.performance_score for v in variations) / total

        # Reusability score: % of unused variations
        reusability_score = (unused / total) * 100 if total > 0 else 0

        return {
            "total_variations": total,
            "unused_variations": unused,
            "average_performance": avg_perf,
            "reusability_score": reusability_score,
            "most_used": max(variations, key=lambda v: v.usage_count).variation_id,
            "best_performing": max(variations, key=lambda v: v.performance_score).variation_id
        }

    async def suggest_repost_timing(
        self,
        content_id: str,
        min_reuse_days: int = 30
    ) -> Optional[datetime]:
        """
        Suggest when content can be reposted with a new variation

        Args:
            content_id: ID of the content piece
            min_reuse_days: Minimum days before reusing

        Returns:
            Suggested repost date, or None if can repost now
        """
        # Check if any unused variations exist
        next_var = await self.get_next_unused_variation(
            content_id,
            VariationType.TITLE,
            min_reuse_days
        )

        if next_var:
            # Can repost now!
            return None

        # All used - find the oldest used date
        variations = await self.get_variations(content_id)

        if not variations:
            return None

        oldest_use = min(
            (v.last_used_at for v in variations if v.last_used_at is not None),
            default=None
        )

        if oldest_use:
            # Suggest reposting min_reuse_days after oldest use
            return oldest_use + timedelta(days=min_reuse_days)

        return None

    async def bulk_create_variations(
        self,
        content_ids: List[str],
        num_variations: int = 5
    ) -> Dict[str, VariationSet]:
        """
        Generate variations for multiple content pieces

        Args:
            content_ids: List of content IDs
            num_variations: Number of variations per piece

        Returns:
            Dictionary mapping content_id to VariationSet
        """
        results = {}

        for content_id in content_ids:
            try:
                variation_set = await self.generate_variations(
                    content_id=content_id,
                    base_title="Content Title",  # Would fetch from DB
                    base_description="Content Description",
                    num_variations=num_variations
                )
                results[content_id] = variation_set

            except Exception as e:
                logger.error(f"Failed to generate variations for {content_id}: {e}")

        logger.success(f"✅ Generated variations for {len(results)}/{len(content_ids)} content pieces")

        return results

    async def cleanup_old_variations(
        self,
        days_unused: int = 90
    ) -> int:
        """
        Clean up variations that haven't been used in X days

        Args:
            days_unused: Days of inactivity before cleanup

        Returns:
            Number of variations cleaned up
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_unused)

        # In production, delete from database
        cleaned_count = 0

        logger.info(f"🧹 Cleaned up {cleaned_count} variations unused for {days_unused}+ days")

        return cleaned_count


# Singleton instance
_service_instance: Optional[ContentReusabilityService] = None


def get_content_reusability_service(db: AsyncSession) -> ContentReusabilityService:
    """Get or create the content reusability service instance"""
    return ContentReusabilityService(db)

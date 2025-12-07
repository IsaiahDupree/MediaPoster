"""
Content Metrics Aggregation Service (Phase 4)
Polls platform adapters for metrics and aggregates across variants
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContentVariant, ContentMetric, ContentRollup
from connectors import registry


class ContentMetricsService:
    """Service for aggregating content metrics across platforms"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def poll_metrics_for_variant(
        self,
        variant: ContentVariant
    ) -> Optional[ContentMetric]:
        """
        Poll current metrics for a variant from its platform adapter
        
        Args:
            variant: ContentVariant to poll metrics for
            
        Returns:
            ContentMetric snapshot or None if adapter unavailable
        """
        if not variant.platform_post_id:
            logger.debug(f"Variant {variant.id} not yet published, skipping")
            return None
        
        # Get adapter for this platform
        adapters = registry.get_adapters_for_platform(variant.platform)
        if not adapters:
            logger.warning(f"No enabled adapter for platform: {variant.platform}")
            return None
        
        adapter = adapters[0]
        
        try:
            # Fetch metrics from platform
            snapshot = await adapter.fetch_metrics(
                platform=variant.platform,
                platform_post_id=variant.platform_post_id
            )
            
            if not snapshot:
                logger.debug(f"No metrics returned for variant {variant.id}")
                return None
            
            # Create metric record
            metric = ContentMetric(
                variant_id=variant.id,
                snapshot_at=snapshot.snapshot_at or datetime.utcnow(),
                views=snapshot.views,
                impressions=snapshot.impressions,
                reach=snapshot.reach,
                likes=snapshot.likes,
                comments=snapshot.comments,
                shares=snapshot.shares,
                saves=snapshot.saves,
                clicks=snapshot.clicks,
                watch_time_seconds=snapshot.watch_time_seconds,
                sentiment_score=None,  # Computed separately
                traffic_type='paid' if variant.is_paid else 'organic',
                raw_metadata=snapshot.raw_payload
            )
            
            self.db.add(metric)
            await self.db.commit()
            
            logger.info(f"Polled metrics for variant {variant.id}: {metric.views} views, {metric.likes} likes")
            return metric
            
        except Exception as e:
            logger.error(f"Error polling metrics for variant {variant.id}: {e}")
            return None
    
    async def poll_metrics_for_content(
        self,
        content_id: UUID
    ) -> List[ContentMetric]:
        """
        Poll metrics for all variants of a content item
        
        Args:
            content_id: Content UUID
            
        Returns:
            List of new metric snapshots
        """
        # Get all published variants
        result = await self.db.execute(
            select(ContentVariant).where(
                ContentVariant.content_id == content_id,
                ContentVariant.published_at.isnot(None)
            )
        )
        variants = result.scalars().all()
        
        logger.info(f"Polling metrics for {len(variants)} variants of content {content_id}")
        
        metrics = []
        for variant in variants:
            metric = await self.poll_metrics_for_variant(variant)
            if metric:
                metrics.append(metric)
        
        # Trigger rollup recomputation
        await self.recompute_rollup(content_id)
        
        return metrics
    
    async def recompute_rollup(self, content_id: UUID) -> ContentRollup:
        """
        Recompute aggregated rollup for a content item
        
        Args:
            content_id: Content UUID
            
        Returns:
            Updated ContentRollup
        """
        # Get latest metrics for each variant
        result = await self.db.execute(
            select(ContentMetric.variant_id, func.max(ContentMetric.snapshot_at))
            .join(ContentVariant, ContentMetric.variant_id == ContentVariant.id)
            .where(ContentVariant.content_id == content_id)
            .group_by(ContentMetric.variant_id)
        )
        latest_by_variant = {row[0]: row[1] for row in result.fetchall()}
        
        # Get those latest metrics
        latest_metrics = []
        for variant_id, snapshot_at in latest_by_variant.items():
            result = await self.db.execute(
                select(ContentMetric).where(
                    ContentMetric.variant_id == variant_id,
                    ContentMetric.snapshot_at == snapshot_at
                )
            )
            metric = result.scalar_one_or_none()
            if metric:
                latest_metrics.append(metric)
        
        if not latest_metrics:
            logger.debug(f"No metrics to aggregate for content {content_id}")
            return None
        
        # Aggregate totals
        total_views = sum(m.views or 0 for m in latest_metrics)
        total_impressions = sum(m.impressions or 0 for m in latest_metrics)
        total_likes = sum(m.likes or 0 for m in latest_metrics)
        total_comments = sum(m.comments or 0 for m in latest_metrics)
        total_shares = sum(m.shares or 0 for m in latest_metrics)
        total_saves = sum(m.saves or 0 for m in latest_metrics)
        total_clicks = sum(m.clicks or 0 for m in latest_metrics)
        
        # Average watch time
        watch_times = [m.watch_time_seconds for m in latest_metrics if m.watch_time_seconds]
        avg_watch_time = sum(watch_times) / len(watch_times) if watch_times else None
        
        # Find best performing platform
        platform_views = {}
        for metric in latest_metrics:
            result = await self.db.execute(
                select(ContentVariant).where(ContentVariant.id == metric.variant_id)
            )
            variant = result.scalar_one()
            platform_views[variant.platform] = platform_views.get(variant.platform, 0) + (metric.views or 0)
        
        best_platform = max(platform_views.items(), key=lambda x: x[1])[0] if platform_views else None
        
        # Update or create rollup
        result = await self.db.execute(
            select(ContentRollup).where(ContentRollup.content_id == content_id)
        )
        rollup = result.scalar_one_or_none()
        
        if not rollup:
            rollup = ContentRollup(content_id=content_id)
            self.db.add(rollup)
        
        rollup.total_views = total_views
        rollup.total_impressions = total_impressions
        rollup.total_likes = total_likes
        rollup.total_comments = total_comments
        rollup.total_shares = total_shares
        rollup.total_saves = total_saves
        rollup.total_clicks = total_clicks
        rollup.avg_watch_time_seconds = avg_watch_time
        rollup.best_platform = best_platform
        rollup.last_updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.success(f"Recomputed rollup for content {content_id}: {total_views} total views across {len(latest_metrics)} platforms")
        return rollup
    
    async def poll_all_recent_content(self, hours: int = 48) -> Dict[str, int]:
        """
        Poll metrics for all content published in the last N hours
        
        Args:
            hours: Look back window
            
        Returns:
            Stats dict
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get recent variants
        result = await self.db.execute(
            select(ContentVariant.content_id)
            .where(ContentVariant.published_at >= since)
            .distinct()
        )
        content_ids = [row[0] for row in result.fetchall()]
        
        logger.info(f"Polling metrics for {len(content_ids)} recent content items")
        
        metrics_collected = 0
        rollups_updated = 0
        
        for content_id in content_ids:
            try:
                metrics = await self.poll_metrics_for_content(content_id)
                metrics_collected += len(metrics)
                if metrics:
                    rollups_updated += 1
            except Exception as e:
                logger.error(f"Error polling content {content_id}: {e}")
        
        return {
            'content_items': len(content_ids),
            'metrics_collected': metrics_collected,
            'rollups_updated': rollups_updated
        }

"""
Analytics Refresh Handler
=========================
Event-driven service that automatically refreshes analytics when content is published.

Subscribes to:
- publish.completed - Triggers analytics refresh for the published account
- publish.failed - Logs failure (no refresh needed)

Emits:
- analytics.refresh.requested - When refresh is triggered
- analytics.updated - When refresh completes
"""

import logging
import asyncio
from typing import Dict, Any
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)


class AnalyticsRefreshHandler:
    """
    Handles automatic analytics refresh on publish events.
    """
    
    def __init__(self):
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("analytics-refresh-handler")
        self._subscribed = False
    
    def subscribe(self):
        """Subscribe to publish events"""
        if self._subscribed:
            return
        
        # Subscribe to publish completion events
        # Note: subscribe() expects async handlers
        async def handle_completed(event):
            await self._handle_publish_completed(event)
        
        async def handle_failed(event):
            await self._handle_publish_failed(event)
        
        self.event_bus.subscribe(Topics.PUBLISH_COMPLETED, handle_completed)
        self.event_bus.subscribe(Topics.PUBLISH_FAILED, handle_failed)
        self._subscribed = True
        logger.info("📊 AnalyticsRefreshHandler subscribed to publish events")
    
    async def _handle_publish_completed(self, event):
        """Handle publish.completed event - trigger analytics refresh"""
        try:
            payload = event.payload
            account_id = payload.get("account_id")
            platform = payload.get("platform")
            media_id = payload.get("media_id")
            
            if not account_id or not platform:
                logger.warning(f"Publish completed event missing account_id or platform: {payload}")
                return
            
            logger.info(f"📊 Triggering analytics refresh for account {account_id} ({platform}) after publish")
            
            # Emit analytics refresh requested event
            # The metrics fetch worker will handle this and emit metrics.updated when done
            await self.event_bus.publish(
                Topics.METRICS_FETCH_REQUESTED,
                {
                    "account_id": account_id,
                    "platform": platform,
                    "trigger": "publish_completed",
                    "media_id": media_id,
                    "platform_url": payload.get("platform_url")
                },
                correlation_id=event.correlation_id
            )
            
            # Also emit a direct analytics.updated event after a short delay
            # This ensures frontend gets notified even if metrics fetch worker is slow
            asyncio.create_task(self._emit_analytics_updated_delayed(account_id, platform, event.correlation_id))
            
        except Exception as e:
            logger.error(f"Error handling publish.completed event: {e}")
    
    async def _emit_analytics_updated_delayed(self, account_id: str, platform: str, correlation_id: str):
        """Emit analytics.updated event after a delay to allow metrics fetch to complete"""
        await asyncio.sleep(3)  # Wait 3 seconds for metrics fetch
        await self.event_bus.publish(
            "analytics.updated",  # Custom topic for frontend
            {
                "account_id": account_id,
                "platform": platform,
                "trigger": "publish_completed"
            },
            correlation_id=correlation_id
        )
    
    async def _handle_publish_failed(self, event):
        """Handle publish.failed event - log but don't refresh"""
        try:
            payload = event.payload
            account_id = payload.get("account_id")
            platform = payload.get("platform")
            error = payload.get("error")
            
            logger.info(f"📊 Publish failed for account {account_id} ({platform}): {error}")
            # Don't refresh analytics on failure
            
        except Exception as e:
            logger.error(f"Error handling publish.failed event: {e}")


# Singleton instance
_analytics_refresh_handler: AnalyticsRefreshHandler = None


def get_analytics_refresh_handler() -> AnalyticsRefreshHandler:
    """Get singleton instance of AnalyticsRefreshHandler"""
    global _analytics_refresh_handler
    if _analytics_refresh_handler is None:
        _analytics_refresh_handler = AnalyticsRefreshHandler()
        _analytics_refresh_handler.subscribe()
    return _analytics_refresh_handler


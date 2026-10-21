"""
Twitter Offer Scheduler - Post offers every 2 hours using Safari automation
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, List
from loguru import logger

from services.event_bus import EventBus


class TwitterOfferScheduler:
    """
    Posts about offers every 2 hours (12 posts/day) using Safari automation.
    
    Strategy:
    - Generate AI-powered tweets about offers
    - Use SafariTwitterPoster for reliable posting
    - Rotate through different awareness stages
    - Track success/failure for optimization
    """
    
    POST_INTERVAL_HOURS = 2
    POSTS_PER_DAY = 12
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus.get_instance()
        self.running = False
        self.posts_today = 0
        self.last_post_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self._poster = None  # Lazy-loaded SafariTwitterPoster
        
    def _get_poster(self):
        """Lazy load SafariTwitterPoster to avoid import issues."""
        if self._poster is None:
            try:
                from automation.safari_twitter_poster import SafariTwitterPoster
                self._poster = SafariTwitterPoster(use_x_domain=True)
            except ImportError as e:
                logger.error(f"Failed to import SafariTwitterPoster: {e}")
        return self._poster
        
    async def start(self):
        raise RuntimeError("script_hub_required: legacy Twitter offer scheduler is disabled; use ScriptHub and Airtime.")
        
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("🛑 Twitter Offer Scheduler stopped")
        
    async def _posting_loop(self):
        raise RuntimeError("script_hub_required: legacy Twitter offer scheduler is disabled; use ScriptHub and Airtime.")
                
    async def _post_offer(self):
        raise RuntimeError("script_hub_required: legacy Twitter offer scheduler is disabled; use ScriptHub and Airtime.")
            
    def _get_current_offer(self) -> Dict:
        """Get current offer to promote."""
        # Rotate through offers
        offers = [
            {
                "name": "Blotato",
                "url": "https://blotato.com",
                "tagline": "Post to all platforms with one click"
            },
            {
                "name": "AI Automation Course",
                "url": "https://example.com/course",
                "tagline": "Learn to automate your content creation"
            }
        ]
        return offers[self.posts_today % len(offers)]
    
    async def _generate_offer_tweet(self, service, offer: Dict) -> str:
        raise RuntimeError("script_hub_required: legacy Twitter copy generation is disabled; use ScriptHub.")
    
    async def _post_to_twitter(self, text: str) -> bool:
        return False
    
    async def _post_to_twitter_fallback(self, text: str) -> bool:
        return False
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "posts_today": self.posts_today,
            "last_post_at": self.last_post_at.isoformat() if self.last_post_at else None,
            "next_post_in_hours": self.POST_INTERVAL_HOURS
        }

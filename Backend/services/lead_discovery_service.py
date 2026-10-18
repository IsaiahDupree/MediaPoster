"""
Lead Discovery Service
======================
Finds new contacts to message across platforms.

Discovery methods:
- Hashtag search (find people posting about relevant topics)
- Competitor followers (people following similar accounts)
- Engagement scraping (people commenting on niche content)
- Profile bio keyword matching
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger
from openai import OpenAI
import os

from services.dm_warmth_system import DMWarmthManager, DMContact, ContactSource
from services.event_bus import EventBus


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


@dataclass
class LeadCriteria:
    """Criteria for qualifying leads."""
    platforms: List[str] = field(default_factory=lambda: ["tiktok", "instagram", "twitter"])
    
    # Target keywords in bio
    bio_keywords: List[str] = field(default_factory=lambda: [
        "entrepreneur", "founder", "building", "startup", "creator",
        "content creator", "coach", "consultant", "agency", "freelance",
        "solopreneur", "side hustle", "business owner"
    ])
    
    # Hashtags to search
    target_hashtags: List[str] = field(default_factory=lambda: [
        "entrepreneur", "startup", "contentcreator", "solopreneur",
        "sidehustle", "buildingpublic", "creatoreconomy"
    ])
    
    # Competitor accounts to scrape followers from
    competitor_accounts: Dict[str, List[str]] = field(default_factory=lambda: {
        "instagram": ["garyvee", "alexhormozi", "thefutur"],
        "tiktok": ["garyvee", "alexhormozi"],
        "twitter": ["garyvee", "alexhormozi", "naval"]
    })
    
    # Minimum follower count (filter bots)
    min_followers: int = 100
    max_followers: int = 100000  # Sweet spot for engagement
    
    # Engagement quality
    min_engagement_rate: float = 0.02  # 2%


class LeadDiscoveryService:
    """
    Discovers and qualifies new leads for DM outreach.
    
    Uses Safari automation to scrape profiles and AI to qualify.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus.get_instance()
        self.warmth_manager = DMWarmthManager.get_instance(self.event_bus)
        self.criteria = LeadCriteria()
        
        # OpenAI for lead qualification
        self._openai = None
        
        logger.info("🔍 LeadDiscoveryService initialized")
        
    def _get_openai(self):
        if self._openai is None and OPENAI_API_KEY:
            self._openai = OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
        
    async def discover_from_hashtag(self, platform: str, hashtag: str, limit: int = 20) -> List[str]:
        """
        Discover leads from hashtag search.
        Returns list of usernames found.
        """
        logger.info(f"🔍 Discovering leads from #{hashtag} on {platform}...")
        
        usernames = []
        
        try:
            if platform == "instagram":
                from automation.safari_instagram_scraper import SafariInstagramScraper
                scraper = SafariInstagramScraper()
                # Scrape hashtag feed
                posts = await scraper.scrape_hashtag(hashtag, limit=limit)
                usernames = [p.get("username") for p in posts if p.get("username")]
                
            elif platform == "tiktok":
                # TikTok hashtag discovery
                from automation.tiktok_engagement import TikTokEngagement
                tiktok = TikTokEngagement()
                posts = await tiktok.search_hashtag(hashtag, limit=limit)
                usernames = [p.get("author") for p in posts if p.get("author")]
                
            elif platform == "twitter":
                # Twitter search
                from automation.safari_twitter_poster import SafariTwitterPoster
                # Would need Twitter search implementation
                pass
                
        except Exception as e:
            logger.error(f"Hashtag discovery error: {e}")
            
        # Add to warmth manager
        if usernames:
            self.warmth_manager.discover_leads_from_hashtag(platform, hashtag, usernames)
            
        return usernames
        
    async def discover_from_competitors(self, platform: str, competitor: str, limit: int = 50) -> List[str]:
        """
        Discover leads from competitor follower lists.
        """
        logger.info(f"🎯 Discovering leads from @{competitor}'s followers on {platform}...")
        
        followers = []
        
        try:
            if platform == "instagram":
                # Would need follower scraping implementation
                pass
            elif platform == "tiktok":
                # TikTok follower discovery
                pass
            elif platform == "twitter":
                # Twitter follower lists
                pass
                
        except Exception as e:
            logger.error(f"Competitor discovery error: {e}")
            
        if followers:
            self.warmth_manager.discover_leads_from_competitors(platform, competitor, followers)
            
        return followers
        
    async def discover_from_engagement(self, platform: str, post_url: str) -> List[str]:
        """
        Discover leads from people engaging with a specific post.
        """
        logger.info(f"💬 Discovering leads from engagement on {post_url}...")
        
        engagers = []
        
        try:
            if platform == "instagram":
                from automation.safari_instagram_scraper import SafariInstagramScraper
                scraper = SafariInstagramScraper()
                comments = await scraper.scrape_post_comments(post_url)
                engagers = [c.get("username") for c in comments if c.get("username")]
                
            elif platform == "tiktok":
                from automation.tiktok_engagement import TikTokEngagement
                tiktok = TikTokEngagement()
                comments = await tiktok.get_video_comments(post_url)
                engagers = [c.get("author") for c in comments if c.get("author")]
                
        except Exception as e:
            logger.error(f"Engagement discovery error: {e}")
            
        # Add as contacts
        for username in engagers:
            self.warmth_manager.record_engagement(platform, username, "comment")
            
        return engagers
        
    async def qualify_lead(self, contact_id: str) -> Dict[str, Any]:
        """
        Use AI to qualify a lead based on their profile.
        Updates fit_score and fit_signals.
        """
        contact = self.warmth_manager.get_contact(contact_id)
        if not contact:
            return {"error": "Contact not found"}
            
        # Get profile info (would need scraping)
        profile_info = {
            "username": contact.username,
            "bio": contact.bio or "",
            "follower_count": contact.follower_count,
            "building": contact.building or "",
            "platform": contact.platform
        }
        
        # Use AI to qualify
        openai = self._get_openai()
        if not openai:
            # Fallback to keyword matching
            fit_score = self._keyword_qualify(profile_info)
            fit_signals = self._extract_signals(profile_info)
        else:
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a lead qualification expert. Analyze this social media profile and determine if they're a good fit for:
- Content creation services
- Video editing automation tools
- Social media growth strategies

Return JSON with:
- fit_score: 0-100 (how likely to be interested)
- fit_signals: list of relevant signals found
- qualification: "hot", "warm", "cool", or "cold"
- reasoning: brief explanation"""
                        },
                        {
                            "role": "user",
                            "content": f"Profile: {profile_info}"
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                
                import json
                result = json.loads(response.choices[0].message.content)
                fit_score = result.get("fit_score", 50)
                fit_signals = result.get("fit_signals", [])
                
            except Exception as e:
                logger.error(f"AI qualification error: {e}")
                fit_score = self._keyword_qualify(profile_info)
                fit_signals = self._extract_signals(profile_info)
                
        # Update contact
        self.warmth_manager.update_fit_score(contact_id, fit_score, fit_signals)
        
        return {
            "contact_id": contact_id,
            "username": contact.username,
            "fit_score": fit_score,
            "fit_signals": fit_signals,
            "warmth": contact.calculate_current_warmth()
        }
        
    def _keyword_qualify(self, profile: Dict) -> float:
        """Simple keyword-based qualification."""
        bio = (profile.get("bio", "") or "").lower()
        building = (profile.get("building", "") or "").lower()
        text = f"{bio} {building}"
        
        score = 30  # Base score
        
        for keyword in self.criteria.bio_keywords:
            if keyword.lower() in text:
                score += 10
                
        # Cap at 100
        return min(100, score)
        
    def _extract_signals(self, profile: Dict) -> List[str]:
        """Extract fit signals from profile."""
        signals = []
        bio = (profile.get("bio", "") or "").lower()
        
        if "entrepreneur" in bio or "founder" in bio:
            signals.append("entrepreneur")
        if "creator" in bio or "content" in bio:
            signals.append("content_creator")
        if "coach" in bio or "consultant" in bio:
            signals.append("service_provider")
        if "building" in bio or "startup" in bio:
            signals.append("builder")
            
        return signals
        
    async def run_discovery_cycle(self) -> Dict[str, int]:
        """
        Run a full discovery cycle across all platforms.
        Called periodically to find new leads.
        """
        results = {platform: 0 for platform in self.criteria.platforms}
        
        for platform in self.criteria.platforms:
            # Hashtag discovery
            for hashtag in self.criteria.target_hashtags[:3]:  # Limit to 3 per cycle
                try:
                    leads = await self.discover_from_hashtag(platform, hashtag, limit=10)
                    results[platform] += len(leads)
                    await asyncio.sleep(5)  # Rate limiting
                except Exception as e:
                    logger.error(f"Discovery cycle error for {platform}/{hashtag}: {e}")
                    
        total = sum(results.values())
        logger.info(f"🔍 Discovery cycle complete: {total} new leads found")
        
        return results
        
    def get_discovery_stats(self) -> Dict:
        """Get discovery statistics."""
        return {
            "criteria": {
                "platforms": self.criteria.platforms,
                "hashtag_count": len(self.criteria.target_hashtags),
                "competitor_count": sum(len(v) for v in self.criteria.competitor_accounts.values())
            },
            "warmth_stats": self.warmth_manager.get_stats()
        }

"""
DM Warmth System - Contact scoring with exponential time decay
==============================================================
Inspired by EverReach CRM - tracks relationship "warmth" that decays over time.

Features:
- Warmth score (0-100) with exponential decay
- 10 DMs per hour per platform (TikTok, Instagram, Twitter)
- Automatic lead discovery from engagement
- Prioritized outreach based on warmth + fit signals
"""
import math
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from loguru import logger

from services.event_bus import EventBus


# Constants
PLATFORMS = ["tiktok", "instagram", "twitter"]
DMS_PER_HOUR_PER_PLATFORM = 10
TOTAL_DMS_PER_HOUR = DMS_PER_HOUR_PER_PLATFORM * len(PLATFORMS)  # 30/hour

# Decay constants (warmth halves every X days without contact)
WARMTH_HALF_LIFE_DAYS = 14  # Warmth halves every 2 weeks without contact
WARMTH_DECAY_CONSTANT = math.log(2) / (WARMTH_HALF_LIFE_DAYS * 24 * 60 * 60)  # Per second


class ContactSource(str, Enum):
    """How we discovered this contact."""
    COMMENT_ENGAGEMENT = "comment_engagement"     # They commented on our content
    FOLLOWER = "follower"                         # They followed us
    MENTION = "mention"                           # They mentioned us
    DM_INBOUND = "dm_inbound"                     # They DMed us first
    HASHTAG_DISCOVERY = "hashtag_discovery"       # Found via hashtag search
    COMPETITOR_FOLLOWER = "competitor_follower"   # Follows our competitors
    MANUAL_ADD = "manual_add"                     # Manually added
    LEAD_SCRAPE = "lead_scrape"                   # From lead discovery scrape


class WarmthTier(str, Enum):
    """Warmth tiers for prioritization."""
    HOT = "hot"           # 80-100: High engagement, recent contact
    WARM = "warm"         # 50-79: Moderate engagement
    COOL = "cool"         # 20-49: Some history but cooling
    COLD = "cold"         # 0-19: Dormant or new
    
    
@dataclass
class DMContact:
    """A contact in the DM outreach system."""
    id: str = field(default_factory=lambda: str(uuid4()))
    platform: str = "instagram"
    username: str = ""
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    
    # Discovery
    source: ContactSource = ContactSource.MANUAL_ADD
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Context (from profile/interactions)
    bio: Optional[str] = None
    follower_count: int = 0
    building: Optional[str] = None       # What they're building
    struggles: Optional[str] = None      # Their pain points
    interests: List[str] = field(default_factory=list)
    
    # Warmth tracking
    base_warmth: float = 50.0            # Starting warmth (0-100)
    last_interaction_at: Optional[datetime] = None
    interaction_count: int = 0
    
    # Message tracking
    last_dm_sent_at: Optional[datetime] = None
    last_dm_received_at: Optional[datetime] = None
    total_dms_sent: int = 0
    total_dms_received: int = 0
    
    # Fit signals
    fit_score: float = 0.0               # How well they fit our ICP (0-100)
    fit_signals: List[str] = field(default_factory=list)
    
    # Status
    is_active: bool = True
    opted_out: bool = False
    
    def calculate_current_warmth(self) -> float:
        """Calculate current warmth with exponential decay."""
        if self.last_interaction_at is None:
            # No interaction yet, use base warmth with decay from discovery
            reference_time = self.discovered_at
            base = self.base_warmth * 0.5  # New contacts start at half base
        else:
            reference_time = self.last_interaction_at
            base = self.base_warmth
            
        now = datetime.now(timezone.utc)
        seconds_elapsed = (now - reference_time).total_seconds()
        
        # Exponential decay: W(t) = W0 * e^(-λt)
        decay_factor = math.exp(-WARMTH_DECAY_CONSTANT * seconds_elapsed)
        current_warmth = base * decay_factor
        
        return max(0, min(100, current_warmth))
    
    def get_warmth_tier(self) -> WarmthTier:
        """Get warmth tier based on current warmth."""
        warmth = self.calculate_current_warmth()
        if warmth >= 80:
            return WarmthTier.HOT
        elif warmth >= 50:
            return WarmthTier.WARM
        elif warmth >= 20:
            return WarmthTier.COOL
        else:
            return WarmthTier.COLD
            
    def boost_warmth(self, amount: float = 20.0):
        """Boost warmth after an interaction."""
        current = self.calculate_current_warmth()
        self.base_warmth = min(100, current + amount)
        self.last_interaction_at = datetime.now(timezone.utc)
        self.interaction_count += 1
        
    def get_priority_score(self) -> float:
        """
        Calculate outreach priority score.
        Higher = should DM sooner.
        
        Factors:
        - Current warmth (prefer warm contacts)
        - Fit score (prefer high fit)
        - Time since last DM (prefer not too recent)
        - Received DMs (prefer responsive contacts)
        """
        warmth = self.calculate_current_warmth()
        fit = self.fit_score
        
        # Time since last DM (bonus for contacts we haven't messaged recently)
        if self.last_dm_sent_at:
            hours_since_dm = (datetime.now(timezone.utc) - self.last_dm_sent_at).total_seconds() / 3600
            recency_bonus = min(50, hours_since_dm)  # Max 50 points after 50 hours
        else:
            recency_bonus = 50  # Never messaged = high priority
            
        # Response ratio bonus
        if self.total_dms_sent > 0:
            response_ratio = self.total_dms_received / self.total_dms_sent
            response_bonus = response_ratio * 30  # Up to 30 points for responsive contacts
        else:
            response_bonus = 15  # Unknown response rate
            
        # Weighted score
        score = (
            warmth * 0.3 +           # 30% weight on warmth
            fit * 0.3 +              # 30% weight on fit
            recency_bonus * 0.25 +   # 25% weight on not messaging too often
            response_bonus * 0.15    # 15% weight on responsiveness
        )
        
        return score
        
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "platform": self.platform,
            "username": self.username,
            "display_name": self.display_name,
            "current_warmth": round(self.calculate_current_warmth(), 1),
            "warmth_tier": self.get_warmth_tier().value,
            "priority_score": round(self.get_priority_score(), 1),
            "fit_score": self.fit_score,
            "interaction_count": self.interaction_count,
            "last_interaction_at": self.last_interaction_at.isoformat() if self.last_interaction_at else None,
            "last_dm_sent_at": self.last_dm_sent_at.isoformat() if self.last_dm_sent_at else None,
            "source": self.source.value
        }


class DMWarmthManager:
    """
    Manages DM outreach with warmth scoring.
    
    Responsibilities:
    - Track contacts and their warmth scores
    - Prioritize who to DM next
    - Discover new leads from engagement
    - Rate limit DMs (10/hr per platform)
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None):
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        cls._instance = None
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus.get_instance()
        
        # Contact storage (in production, this would be database-backed)
        self.contacts: Dict[str, DMContact] = {}  # id -> contact
        self.username_index: Dict[str, str] = {}  # platform:username -> id
        
        # Rate limiting
        self.dms_sent_this_hour: Dict[str, int] = {p: 0 for p in PLATFORMS}
        self.hour_started_at: datetime = datetime.now(timezone.utc)
        
        # Lead discovery queue
        self.lead_discovery_queue: List[Dict] = []
        
        logger.info("🔥 DMWarmthManager initialized")
        
    def _check_hour_reset(self):
        """Reset hourly counters if needed."""
        now = datetime.now(timezone.utc)
        if (now - self.hour_started_at).total_seconds() >= 3600:
            self.dms_sent_this_hour = {p: 0 for p in PLATFORMS}
            self.hour_started_at = now
            
    def add_contact(self, contact: DMContact) -> str:
        """Add or update a contact."""
        key = f"{contact.platform}:{contact.username}"
        
        if key in self.username_index:
            # Update existing contact
            existing_id = self.username_index[key]
            existing = self.contacts[existing_id]
            # Preserve history, update fields
            contact.id = existing_id
            contact.interaction_count = existing.interaction_count
            contact.total_dms_sent = existing.total_dms_sent
            contact.total_dms_received = existing.total_dms_received
            contact.base_warmth = existing.base_warmth
            
        self.contacts[contact.id] = contact
        self.username_index[key] = contact.id
        
        return contact.id
        
    def get_contact(self, contact_id: str) -> Optional[DMContact]:
        """Get contact by ID."""
        return self.contacts.get(contact_id)
        
    def get_contact_by_username(self, platform: str, username: str) -> Optional[DMContact]:
        """Get contact by platform and username."""
        key = f"{platform}:{username}"
        contact_id = self.username_index.get(key)
        return self.contacts.get(contact_id) if contact_id else None
        
    def get_next_dm_targets(self, platform: str, count: int = 5) -> List[DMContact]:
        """
        Get the next contacts to DM on a platform.
        Sorted by priority score (highest first).
        """
        self._check_hour_reset()
        
        # Check rate limit
        remaining = DMS_PER_HOUR_PER_PLATFORM - self.dms_sent_this_hour[platform]
        count = min(count, remaining)
        
        if count <= 0:
            logger.warning(f"Rate limit reached for {platform} this hour")
            return []
            
        # Get active contacts for this platform
        candidates = [
            c for c in self.contacts.values()
            if c.platform == platform 
            and c.is_active 
            and not c.opted_out
            and (c.last_dm_sent_at is None or 
                 (datetime.now(timezone.utc) - c.last_dm_sent_at).total_seconds() > 3600)  # Min 1hr between DMs
        ]
        
        # Sort by priority score
        candidates.sort(key=lambda c: c.get_priority_score(), reverse=True)
        
        return candidates[:count]
        
    def record_dm_sent(self, contact_id: str, message_text: Optional[str] = None):
        """Record that a DM was sent to a contact."""
        self._check_hour_reset()
        
        contact = self.contacts.get(contact_id)
        if not contact:
            return
            
        contact.last_dm_sent_at = datetime.now(timezone.utc)
        contact.total_dms_sent += 1
        contact.boost_warmth(10)  # Small warmth boost for outreach
        
        self.dms_sent_this_hour[contact.platform] += 1
        
        logger.info(f"📤 DM sent to @{contact.username} on {contact.platform} "
                   f"(warmth: {contact.calculate_current_warmth():.1f})")
        
    def record_dm_received(self, contact_id: str, message_text: Optional[str] = None):
        """Record that a DM was received from a contact."""
        contact = self.contacts.get(contact_id)
        if not contact:
            return
            
        contact.last_dm_received_at = datetime.now(timezone.utc)
        contact.total_dms_received += 1
        contact.boost_warmth(25)  # Larger warmth boost for response
        
        logger.info(f"📥 DM received from @{contact.username} on {contact.platform} "
                   f"(warmth: {contact.calculate_current_warmth():.1f})")
        
    def record_engagement(self, platform: str, username: str, engagement_type: str):
        """
        Record engagement (comment, like, follow) and potentially add as contact.
        This is how we discover new leads.
        """
        contact = self.get_contact_by_username(platform, username)
        
        if contact:
            # Existing contact - boost warmth
            boost_amounts = {
                "comment": 15,
                "like": 5,
                "follow": 20,
                "reply": 10,
                "share": 25
            }
            contact.boost_warmth(boost_amounts.get(engagement_type, 10))
        else:
            # New contact - add to discovery queue for lead qualification
            self.lead_discovery_queue.append({
                "platform": platform,
                "username": username,
                "engagement_type": engagement_type,
                "discovered_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Auto-add as contact with low initial warmth
            source_map = {
                "comment": ContactSource.COMMENT_ENGAGEMENT,
                "follow": ContactSource.FOLLOWER,
                "mention": ContactSource.MENTION,
                "dm": ContactSource.DM_INBOUND
            }
            
            new_contact = DMContact(
                platform=platform,
                username=username,
                source=source_map.get(engagement_type, ContactSource.COMMENT_ENGAGEMENT),
                base_warmth=30.0  # Start cool, needs qualification
            )
            self.add_contact(new_contact)
            logger.info(f"🆕 New lead discovered: @{username} on {platform} via {engagement_type}")
            
    def discover_leads_from_hashtag(self, platform: str, hashtag: str, usernames: List[str]):
        """Add leads discovered from hashtag search."""
        for username in usernames:
            if not self.get_contact_by_username(platform, username):
                contact = DMContact(
                    platform=platform,
                    username=username,
                    source=ContactSource.HASHTAG_DISCOVERY,
                    base_warmth=20.0  # Cold leads
                )
                self.add_contact(contact)
                
        logger.info(f"📍 Added {len(usernames)} leads from #{hashtag} on {platform}")
        
    def discover_leads_from_competitors(self, platform: str, competitor: str, follower_usernames: List[str]):
        """Add leads from competitor follower lists."""
        added = 0
        for username in follower_usernames:
            if not self.get_contact_by_username(platform, username):
                contact = DMContact(
                    platform=platform,
                    username=username,
                    source=ContactSource.COMPETITOR_FOLLOWER,
                    base_warmth=25.0,
                    fit_signals=[f"follows_{competitor}"]
                )
                self.add_contact(contact)
                added += 1
                
        logger.info(f"🎯 Added {added} leads from @{competitor}'s followers on {platform}")
        
    def update_fit_score(self, contact_id: str, fit_score: float, fit_signals: List[str] = None):
        """Update a contact's fit score based on qualification."""
        contact = self.contacts.get(contact_id)
        if contact:
            contact.fit_score = fit_score
            if fit_signals:
                contact.fit_signals.extend(fit_signals)
                
    def get_stats(self) -> Dict:
        """Get current DM system stats."""
        self._check_hour_reset()
        
        platform_stats = {}
        for platform in PLATFORMS:
            contacts = [c for c in self.contacts.values() if c.platform == platform]
            platform_stats[platform] = {
                "total_contacts": len(contacts),
                "hot": len([c for c in contacts if c.get_warmth_tier() == WarmthTier.HOT]),
                "warm": len([c for c in contacts if c.get_warmth_tier() == WarmthTier.WARM]),
                "cool": len([c for c in contacts if c.get_warmth_tier() == WarmthTier.COOL]),
                "cold": len([c for c in contacts if c.get_warmth_tier() == WarmthTier.COLD]),
                "dms_sent_this_hour": self.dms_sent_this_hour[platform],
                "dms_remaining_this_hour": DMS_PER_HOUR_PER_PLATFORM - self.dms_sent_this_hour[platform]
            }
            
        return {
            "total_contacts": len(self.contacts),
            "leads_in_queue": len(self.lead_discovery_queue),
            "platforms": platform_stats,
            "hour_started_at": self.hour_started_at.isoformat()
        }
        
    def get_warming_contacts(self, limit: int = 20) -> List[Dict]:
        """Get contacts sorted by priority for dashboard display."""
        contacts = list(self.contacts.values())
        contacts.sort(key=lambda c: c.get_priority_score(), reverse=True)
        return [c.to_dict() for c in contacts[:limit]]

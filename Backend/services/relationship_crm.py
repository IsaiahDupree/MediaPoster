"""
Relationship-First CRM Service
Implements the Relationship-First DM Automation System (PRD v2.0)

Philosophy: Optimize for trust momentum and relationship health, not aggressive closing.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import uuid4
from loguru import logger
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


# =============================================================================
# ENUMS
# =============================================================================

class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    THREADS = "threads"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"


class PipelineStage(str, Enum):
    """8-stage trust-building pipeline."""
    FIRST_TOUCH = "first_touch"           # They engage / you engage
    CONTEXT_CAPTURED = "context_captured" # You know their situation
    MICRO_WIN = "micro_win"               # You helped in a tangible way
    CADENCE_ESTABLISHED = "cadence"       # Light ongoing touch
    TRUST_SIGNALS = "trust_signals"       # They ask opinions / refer / share personal
    FIT_IDENTIFIED = "fit_identified"     # A solvable problem appears repeatedly
    PERMISSIONED_OFFER = "offer"          # Only after consent
    POST_WIN = "post_win"                 # Keep helping after purchase


class MessageLane(str, Enum):
    """Intent lanes for messaging."""
    FRIENDSHIP = "A"   # No business
    SERVICE = "B"      # Value-first
    OFFER = "C"        # Permission-based


class ActionType(str, Enum):
    """Types of relationship actions."""
    RESOURCE = "resource"
    INTRO = "intro"
    QUICK_AUDIT = "quick_audit"
    CELEBRATION = "celebration"
    CHECK_IN = "check_in"
    FOLLOW_UP = "follow_up"
    TEMPLATE = "template"
    ADVICE = "advice"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ValueLogEntry:
    """Log of value delivered to a contact."""
    id: str = field(default_factory=lambda: str(uuid4()))
    date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    action_type: str = "resource"
    description: str = ""
    lane: str = "B"  # A, B, or C
    impact_score: int = 1  # 1-5 scale


@dataclass
class ContactContext:
    """Context about what the contact is working on."""
    building: str = ""           # What are they working on right now?
    struggles: str = ""          # What's hard for them lately?
    values: str = ""             # What do they care about?
    win_30d: str = ""            # What would a win look like in 30 days?
    preferred_cadence: str = "weekly"  # daily|weekly|monthly
    do_not_do: List[str] = field(default_factory=list)  # e.g., ["hate calls"]
    notes: str = ""


@dataclass
class RelationshipScores:
    """Relationship health scoring components."""
    recency_days: int = 0
    resonance: str = "low"       # low|medium|high
    need_clarity: bool = False
    value_delivered_count: int = 0
    promises_kept_rate: float = 1.0
    consent_level: str = "none"  # none|updates|offers|all
    trust_signals: List[str] = field(default_factory=list)
    
    def calculate_health_score(self) -> int:
        """
        Calculate relationship health score (0-100).
        
        Weights:
        - Recency: 20%
        - Resonance: 20%
        - Need Clarity: 15%
        - Value Delivered: 20%
        - Reliability: 15%
        - Consent: 10%
        """
        score = 0
        
        # Recency (20%) - lower is better
        if self.recency_days <= 3:
            score += 20
        elif self.recency_days <= 7:
            score += 15
        elif self.recency_days <= 14:
            score += 10
        elif self.recency_days <= 30:
            score += 5
        
        # Resonance (20%)
        resonance_scores = {"high": 20, "medium": 12, "low": 5}
        score += resonance_scores.get(self.resonance, 5)
        
        # Need Clarity (15%)
        if self.need_clarity:
            score += 15
        
        # Value Delivered (20%)
        value_score = min(20, self.value_delivered_count * 4)
        score += value_score
        
        # Reliability (15%)
        score += int(self.promises_kept_rate * 15)
        
        # Consent (10%)
        consent_scores = {"all": 10, "offers": 8, "updates": 5, "none": 0}
        score += consent_scores.get(self.consent_level, 0)
        
        return min(100, max(0, score))


@dataclass
class Contact:
    """
    Complete relationship profile for a contact.
    Implements RF-002: Context Cards.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    platform: str = "instagram"
    username: str = ""
    
    # Identity
    name: str = ""
    timezone: str = "America/New_York"
    how_we_met: str = ""
    first_contact_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Context
    context: ContactContext = field(default_factory=ContactContext)
    
    # Scores
    scores: RelationshipScores = field(default_factory=RelationshipScores)
    
    # Pipeline
    pipeline_stage: str = PipelineStage.FIRST_TOUCH.value
    last_touch: Optional[datetime] = None
    next_action: str = ""
    next_action_date: Optional[datetime] = None
    
    # Value log
    value_log: List[ValueLogEntry] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    
    @property
    def relationship_health(self) -> int:
        """Get current relationship health score."""
        return self.scores.calculate_health_score()
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "platform": self.platform,
            "username": self.username,
            "name": self.name,
            "timezone": self.timezone,
            "how_we_met": self.how_we_met,
            "first_contact_date": self.first_contact_date.isoformat() if self.first_contact_date else None,
            "context": asdict(self.context),
            "scores": asdict(self.scores),
            "relationship_health": self.relationship_health,
            "pipeline_stage": self.pipeline_stage,
            "last_touch": self.last_touch.isoformat() if self.last_touch else None,
            "next_action": self.next_action,
            "next_action_date": self.next_action_date.isoformat() if self.next_action_date else None,
            "value_log": [asdict(v) for v in self.value_log[-10:]],  # Last 10 entries
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# RELATIONSHIP CRM SERVICE
# =============================================================================

class RelationshipCRM:
    """
    Relationship-First CRM Service.
    
    Core philosophy: Optimize for trust momentum, not close rate.
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self._ensure_tables()
        self.contacts: Dict[str, Contact] = {}
        logger.info("✅ RelationshipCRM initialized")
    
    def _ensure_tables(self):
        """Create database tables if they don't exist."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS relationship_contacts (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    username TEXT NOT NULL,
                    name TEXT,
                    data JSONB NOT NULL DEFAULT '{}',
                    relationship_health INTEGER DEFAULT 0,
                    pipeline_stage TEXT DEFAULT 'first_touch',
                    last_touch TIMESTAMP,
                    next_action TEXT,
                    next_action_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(platform, username)
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS relationship_value_log (
                    id TEXT PRIMARY KEY,
                    contact_id TEXT NOT NULL REFERENCES relationship_contacts(id),
                    action_type TEXT NOT NULL,
                    description TEXT,
                    lane TEXT DEFAULT 'B',
                    impact_score INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS relationship_interactions (
                    id TEXT PRIMARY KEY,
                    contact_id TEXT NOT NULL REFERENCES relationship_contacts(id),
                    platform TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    message_text TEXT,
                    lane TEXT,
                    sentiment TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_contacts_health 
                ON relationship_contacts(relationship_health DESC)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_contacts_next_action 
                ON relationship_contacts(next_action_date)
            """))
            
            conn.commit()
        
        logger.info("✅ Relationship CRM tables created")
    
    # -------------------------------------------------------------------------
    # CONTACT MANAGEMENT
    # -------------------------------------------------------------------------
    
    def create_contact(
        self,
        platform: str,
        username: str,
        name: str = "",
        how_we_met: str = "",
        context: Optional[Dict] = None
    ) -> Contact:
        """Create a new contact."""
        contact = Contact(
            platform=platform,
            username=username,
            name=name,
            how_we_met=how_we_met
        )
        
        if context:
            contact.context = ContactContext(**context)
        
        # Save to database
        self._save_contact(contact)
        self.contacts[contact.id] = contact
        
        logger.info(f"📝 Created contact: @{username} on {platform}")
        return contact
    
    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Get contact by ID."""
        if contact_id in self.contacts:
            return self.contacts[contact_id]
        
        # Load from database
        return self._load_contact(contact_id)
    
    def get_contact_by_username(self, platform: str, username: str) -> Optional[Contact]:
        """Get contact by platform and username."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id FROM relationship_contacts 
                WHERE platform = :platform AND username = :username
            """), {"platform": platform, "username": username}).fetchone()
            
            if result:
                return self.get_contact(result[0])
        
        return None
    
    def update_contact(self, contact_id: str, updates: Dict) -> Optional[Contact]:
        """Update contact fields."""
        contact = self.get_contact(contact_id)
        if not contact:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
        
        contact.updated_at = datetime.now(timezone.utc)
        self._save_contact(contact)
        
        return contact
    
    def update_context(self, contact_id: str, context_updates: Dict) -> Optional[Contact]:
        """Update contact context (what they're working on, struggles, etc.)."""
        contact = self.get_contact(contact_id)
        if not contact:
            return None
        
        for key, value in context_updates.items():
            if hasattr(contact.context, key):
                setattr(contact.context, key, value)
        
        # Mark that we have clarity on their needs
        if any(k in context_updates for k in ["building", "struggles", "win_30d"]):
            contact.scores.need_clarity = True
        
        contact.updated_at = datetime.now(timezone.utc)
        self._save_contact(contact)
        
        return contact
    
    def _save_contact(self, contact: Contact):
        """Save contact to database."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO relationship_contacts 
                (id, platform, username, name, data, relationship_health, 
                 pipeline_stage, last_touch, next_action, next_action_date, created_at, updated_at)
                VALUES (:id, :platform, :username, :name, :data, :health,
                        :stage, :last_touch, :next_action, :next_action_date, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    name = :name,
                    data = :data,
                    relationship_health = :health,
                    pipeline_stage = :stage,
                    last_touch = :last_touch,
                    next_action = :next_action,
                    next_action_date = :next_action_date,
                    updated_at = :updated_at
            """), {
                "id": contact.id,
                "platform": contact.platform,
                "username": contact.username,
                "name": contact.name,
                "data": json.dumps(contact.to_dict()),
                "health": contact.relationship_health,
                "stage": contact.pipeline_stage,
                "last_touch": contact.last_touch,
                "next_action": contact.next_action,
                "next_action_date": contact.next_action_date,
                "created_at": contact.created_at,
                "updated_at": contact.updated_at
            })
            conn.commit()
    
    def _load_contact(self, contact_id: str) -> Optional[Contact]:
        """Load contact from database."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT data FROM relationship_contacts WHERE id = :id
            """), {"id": contact_id}).fetchone()
            
            if result:
                data = result[0] if isinstance(result[0], dict) else json.loads(result[0])
                contact = self._dict_to_contact(data)
                self.contacts[contact.id] = contact
                return contact
        
        return None
    
    def _dict_to_contact(self, data: Dict) -> Contact:
        """Convert dictionary to Contact object."""
        contact = Contact(
            id=data.get("id", str(uuid4())),
            platform=data.get("platform", "instagram"),
            username=data.get("username", ""),
            name=data.get("name", ""),
            timezone=data.get("timezone", "America/New_York"),
            how_we_met=data.get("how_we_met", ""),
            pipeline_stage=data.get("pipeline_stage", PipelineStage.FIRST_TOUCH.value),
            next_action=data.get("next_action", ""),
            tags=data.get("tags", [])
        )
        
        if data.get("context"):
            contact.context = ContactContext(**data["context"])
        
        if data.get("scores"):
            contact.scores = RelationshipScores(**data["scores"])
        
        return contact
    
    # -------------------------------------------------------------------------
    # VALUE TRACKING
    # -------------------------------------------------------------------------
    
    def log_value_delivered(
        self,
        contact_id: str,
        action_type: str,
        description: str,
        lane: str = "B",
        impact_score: int = 1
    ) -> bool:
        """
        Log value delivered to a contact.
        
        This is core to the 3:1 rule: For every 1 offer touch, 
        do 3 relationship/value touches.
        """
        contact = self.get_contact(contact_id)
        if not contact:
            return False
        
        entry = ValueLogEntry(
            action_type=action_type,
            description=description,
            lane=lane,
            impact_score=impact_score
        )
        
        # Add to contact's value log
        contact.value_log.append(entry)
        contact.scores.value_delivered_count += 1
        contact.last_touch = datetime.now(timezone.utc)
        contact.updated_at = datetime.now(timezone.utc)
        
        # Progress pipeline if appropriate
        if contact.pipeline_stage == PipelineStage.CONTEXT_CAPTURED.value:
            contact.pipeline_stage = PipelineStage.MICRO_WIN.value
        
        # Save to database
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO relationship_value_log 
                (id, contact_id, action_type, description, lane, impact_score)
                VALUES (:id, :contact_id, :action_type, :description, :lane, :impact_score)
            """), {
                "id": entry.id,
                "contact_id": contact_id,
                "action_type": action_type,
                "description": description,
                "lane": lane,
                "impact_score": impact_score
            })
            conn.commit()
        
        self._save_contact(contact)
        logger.info(f"💝 Value logged for @{contact.username}: {action_type}")
        
        return True
    
    def get_value_log(self, contact_id: str, limit: int = 20) -> List[Dict]:
        """Get value log for a contact."""
        with self.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT id, action_type, description, lane, impact_score, created_at
                FROM relationship_value_log
                WHERE contact_id = :contact_id
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"contact_id": contact_id, "limit": limit}).fetchall()
            
            return [
                {
                    "id": r[0],
                    "action_type": r[1],
                    "description": r[2],
                    "lane": r[3],
                    "impact_score": r[4],
                    "created_at": r[5].isoformat() if r[5] else None
                }
                for r in results
            ]
    
    # -------------------------------------------------------------------------
    # PIPELINE MANAGEMENT
    # -------------------------------------------------------------------------
    
    def advance_pipeline(self, contact_id: str, to_stage: Optional[str] = None) -> Optional[Contact]:
        """
        Advance contact to next pipeline stage.
        Implements RF-003: Relationship Pipeline Stages.
        """
        contact = self.get_contact(contact_id)
        if not contact:
            return None
        
        stages = list(PipelineStage)
        current_idx = next(
            (i for i, s in enumerate(stages) if s.value == contact.pipeline_stage),
            0
        )
        
        if to_stage:
            # Move to specific stage
            contact.pipeline_stage = to_stage
        elif current_idx < len(stages) - 1:
            # Move to next stage
            contact.pipeline_stage = stages[current_idx + 1].value
        
        contact.updated_at = datetime.now(timezone.utc)
        self._save_contact(contact)
        
        logger.info(f"📈 @{contact.username} advanced to: {contact.pipeline_stage}")
        return contact
    
    def record_trust_signal(self, contact_id: str, signal: str) -> Optional[Contact]:
        """
        Record a trust signal from the contact.
        
        Trust signals indicate deepening relationship:
        - asked_opinion: They asked for your opinion
        - referred_friend: They referred someone to you
        - shared_personal: They shared personal updates
        - thanked: They expressed gratitude
        """
        contact = self.get_contact(contact_id)
        if not contact:
            return None
        
        if signal not in contact.scores.trust_signals:
            contact.scores.trust_signals.append(signal)
        
        # If we have multiple trust signals, advance to trust_signals stage
        if len(contact.scores.trust_signals) >= 2:
            if contact.pipeline_stage in [
                PipelineStage.MICRO_WIN.value, 
                PipelineStage.CADENCE_ESTABLISHED.value
            ]:
                contact.pipeline_stage = PipelineStage.TRUST_SIGNALS.value
        
        contact.updated_at = datetime.now(timezone.utc)
        self._save_contact(contact)
        
        return contact
    
    # -------------------------------------------------------------------------
    # RELATIONSHIP HEALTH QUERIES
    # -------------------------------------------------------------------------
    
    def get_needs_care(self, limit: int = 20) -> List[Contact]:
        """
        Get contacts who need care (score 40-59).
        These should be re-warmed gently.
        """
        with self.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT id FROM relationship_contacts
                WHERE relationship_health BETWEEN 40 AND 59
                ORDER BY relationship_health ASC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            return [self.get_contact(r[0]) for r in results if r[0]]
    
    def get_healthy_relationships(self, limit: int = 20) -> List[Contact]:
        """
        Get contacts with healthy relationships (score 80+).
        These are ripe for nurturing and light collaboration.
        """
        with self.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT id FROM relationship_contacts
                WHERE relationship_health >= 80
                ORDER BY relationship_health DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            return [self.get_contact(r[0]) for r in results if r[0]]
    
    def get_due_for_action(self) -> List[Contact]:
        """Get contacts with actions due today or overdue."""
        with self.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT id FROM relationship_contacts
                WHERE next_action_date <= NOW()
                AND next_action IS NOT NULL
                AND next_action != ''
                ORDER BY next_action_date ASC
            """)).fetchall()
            
            return [self.get_contact(r[0]) for r in results if r[0]]
    
    def get_pipeline_summary(self) -> Dict[str, int]:
        """Get count of contacts by pipeline stage."""
        with self.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT pipeline_stage, COUNT(*) as count
                FROM relationship_contacts
                GROUP BY pipeline_stage
            """)).fetchall()
            
            return {r[0]: r[1] for r in results}
    
    # -------------------------------------------------------------------------
    # RECENCY UPDATES
    # -------------------------------------------------------------------------
    
    def record_interaction(
        self,
        contact_id: str,
        direction: str,  # "inbound" or "outbound"
        message_text: str = "",
        lane: str = "A",
        sentiment: str = "neutral"
    ) -> Optional[Contact]:
        """
        Record an interaction with a contact.
        Updates recency and resonance scores.
        """
        contact = self.get_contact(contact_id)
        if not contact:
            return None
        
        # Update recency
        contact.last_touch = datetime.now(timezone.utc)
        contact.scores.recency_days = 0
        
        # Update resonance based on message depth
        if len(message_text) > 100 or sentiment in ["positive", "personal"]:
            contact.scores.resonance = "high"
        elif len(message_text) > 30:
            contact.scores.resonance = "medium"
        
        # Progress from first_touch if this is inbound
        if direction == "inbound" and contact.pipeline_stage == PipelineStage.FIRST_TOUCH.value:
            contact.pipeline_stage = PipelineStage.CONTEXT_CAPTURED.value
        
        # Log to database
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO relationship_interactions
                (id, contact_id, platform, direction, message_text, lane, sentiment)
                VALUES (:id, :contact_id, :platform, :direction, :message_text, :lane, :sentiment)
            """), {
                "id": str(uuid4()),
                "contact_id": contact_id,
                "platform": contact.platform,
                "direction": direction,
                "message_text": message_text[:500],  # Truncate
                "lane": lane,
                "sentiment": sentiment
            })
            conn.commit()
        
        contact.updated_at = datetime.now(timezone.utc)
        self._save_contact(contact)
        
        return contact


# =============================================================================
# SINGLETON
# =============================================================================

_crm_instance: Optional[RelationshipCRM] = None

def get_relationship_crm() -> RelationshipCRM:
    """Get singleton instance of RelationshipCRM."""
    global _crm_instance
    if _crm_instance is None:
        _crm_instance = RelationshipCRM()
    return _crm_instance

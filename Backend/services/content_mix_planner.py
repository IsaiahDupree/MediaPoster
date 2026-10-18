"""
Content Mix Planner Service
Long-term content scheduling with mixed content types (UGC, Carousel, AI-generated, Animated)
"""
import os
import json
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from loguru import logger
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


class ContentType(str, Enum):
    """Content types that can be mixed in a schedule"""
    UGC_CAPTION = "ugc_caption"           # User-generated content with AI captions
    CAROUSEL = "carousel"                  # Multi-image carousel posts
    AI_GENERATED = "ai_generated"          # Fully AI-generated video content
    ANIMATED = "animated"                  # Animated/motion graphics content
    RAW_UGC = "raw_ugc"                   # Raw user-generated content as-is


class ScheduleDuration(str, Enum):
    """Predefined schedule durations"""
    ONE_WEEK = "1_week"
    TWO_WEEKS = "2_weeks"
    ONE_MONTH = "1_month"
    TWO_MONTHS = "2_months"
    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    ONE_YEAR = "1_year"
    CUSTOM = "custom"


@dataclass
class ContentMix:
    """Configuration for content type distribution"""
    ugc_caption_percentage: float = 40.0      # UGC with AI-generated captions
    carousel_percentage: float = 20.0          # Carousel posts
    ai_generated_percentage: float = 20.0      # AI-generated videos
    animated_percentage: float = 10.0          # Animated content
    raw_ugc_percentage: float = 10.0           # Raw UGC as-is
    
    def validate(self) -> bool:
        """Ensure percentages sum to 100"""
        total = (
            self.ugc_caption_percentage +
            self.carousel_percentage +
            self.ai_generated_percentage +
            self.animated_percentage +
            self.raw_ugc_percentage
        )
        return 99.0 <= total <= 101.0  # Allow small rounding errors
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScheduleConfig:
    """Configuration for long-term schedule generation"""
    duration: ScheduleDuration = ScheduleDuration.TWO_MONTHS
    custom_days: Optional[int] = None
    posts_per_day: int = 2
    platforms: List[str] = field(default_factory=lambda: ["tiktok", "instagram"])
    content_mix: ContentMix = field(default_factory=ContentMix)
    posting_times: List[str] = field(default_factory=lambda: ["09:00", "18:00"])
    pillar_weights: Dict[str, float] = field(default_factory=dict)
    goal_id: Optional[str] = None
    
    def get_total_days(self) -> int:
        """Get total days for the schedule"""
        duration_map = {
            ScheduleDuration.ONE_WEEK: 7,
            ScheduleDuration.TWO_WEEKS: 14,
            ScheduleDuration.ONE_MONTH: 30,
            ScheduleDuration.TWO_MONTHS: 60,
            ScheduleDuration.THREE_MONTHS: 90,
            ScheduleDuration.SIX_MONTHS: 180,
            ScheduleDuration.ONE_YEAR: 365,
        }
        if self.duration == ScheduleDuration.CUSTOM and self.custom_days:
            return self.custom_days
        return duration_map.get(self.duration, 60)


@dataclass
class ScheduledSlot:
    """A single scheduled content slot"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = None
    time: str = "12:00"
    platform: str = "tiktok"
    content_type: ContentType = ContentType.UGC_CAPTION
    pillar: Optional[str] = None
    content_id: Optional[str] = None
    content_title: Optional[str] = None
    status: str = "planned"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "platform": self.platform,
            "content_type": self.content_type.value if isinstance(self.content_type, ContentType) else self.content_type,
            "pillar": self.pillar,
            "content_id": self.content_id,
            "content_title": self.content_title,
            "status": self.status
        }


@dataclass
class LongTermPlan:
    """A complete long-term content plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Content Plan"
    start_date: date = None
    end_date: date = None
    config: ScheduleConfig = field(default_factory=ScheduleConfig)
    slots: List[ScheduledSlot] = field(default_factory=list)
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_posts(self) -> int:
        return len(self.slots)
    
    @property
    def content_type_distribution(self) -> Dict[str, int]:
        dist = {}
        for slot in self.slots:
            ct = slot.content_type.value if isinstance(slot.content_type, ContentType) else slot.content_type
            dist[ct] = dist.get(ct, 0) + 1
        return dist
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "total_posts": self.total_posts,
            "total_days": (self.end_date - self.start_date).days + 1 if self.end_date and self.start_date else 0,
            "content_type_distribution": self.content_type_distribution,
            "config": {
                "duration": self.config.duration.value,
                "posts_per_day": self.config.posts_per_day,
                "platforms": self.config.platforms,
                "content_mix": self.config.content_mix.to_dict(),
                "posting_times": self.config.posting_times
            },
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "slots": [s.to_dict() for s in self.slots]
        }


class ContentMixPlanner:
    """
    Service for generating long-term content schedules with mixed content types.
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        logger.info("ContentMixPlanner initialized")
    
    async def generate_plan(
        self,
        config: ScheduleConfig,
        start_date: Optional[date] = None,
        name: Optional[str] = None
    ) -> LongTermPlan:
        """
        Generate a long-term content plan based on configuration.
        
        Args:
            config: Schedule configuration with content mix and duration
            start_date: Starting date (defaults to tomorrow)
            name: Optional plan name
        
        Returns:
            LongTermPlan with all scheduled slots
        """
        if start_date is None:
            start_date = date.today() + timedelta(days=1)
        
        total_days = config.get_total_days()
        end_date = start_date + timedelta(days=total_days - 1)
        
        plan_name = name or f"{config.duration.value.replace('_', ' ').title()} Content Plan"
        
        logger.info(f"[ContentMixPlanner] Generating {total_days}-day plan: {start_date} to {end_date}")
        
        # Create plan
        plan = LongTermPlan(
            name=plan_name,
            start_date=start_date,
            end_date=end_date,
            config=config,
            status="draft"
        )
        
        # Load available content from database
        available_content = await self._load_available_content()
        
        # Load pillars if goal_id provided
        pillars = []
        if config.goal_id:
            pillars = await self._load_pillars(config.goal_id)
        
        # Generate slots for each day
        slots = []
        content_type_counts = {ct: 0 for ct in ContentType}
        
        for day_offset in range(total_days):
            current_date = start_date + timedelta(days=day_offset)
            
            # Generate posts for this day
            for post_idx in range(config.posts_per_day):
                # Determine content type based on mix percentages
                content_type = self._select_content_type(
                    config.content_mix,
                    content_type_counts,
                    total_days * config.posts_per_day
                )
                content_type_counts[content_type] += 1
                
                # Select platform (rotate through platforms)
                platform = config.platforms[post_idx % len(config.platforms)]
                
                # Select posting time
                posting_time = config.posting_times[post_idx % len(config.posting_times)]
                
                # Select pillar (rotate through pillars)
                pillar = None
                if pillars:
                    pillar = pillars[len(slots) % len(pillars)].get("name")
                
                # Try to match content from available pool
                content_id, content_title = self._match_content(
                    content_type,
                    available_content,
                    pillar
                )
                
                slot = ScheduledSlot(
                    date=current_date,
                    time=posting_time,
                    platform=platform,
                    content_type=content_type,
                    pillar=pillar,
                    content_id=content_id,
                    content_title=content_title,
                    status="planned"
                )
                slots.append(slot)
        
        plan.slots = slots
        
        # Save plan to database
        await self._save_plan(plan)
        
        logger.info(f"[ContentMixPlanner] Plan generated: {plan.total_posts} posts across {total_days} days")
        logger.info(f"[ContentMixPlanner] Content distribution: {plan.content_type_distribution}")
        
        return plan
    
    def _select_content_type(
        self,
        mix: ContentMix,
        current_counts: Dict[ContentType, int],
        total_target: int
    ) -> ContentType:
        """Select next content type based on mix percentages and current distribution"""
        
        # Calculate target counts for each type
        targets = {
            ContentType.UGC_CAPTION: mix.ugc_caption_percentage / 100 * total_target,
            ContentType.CAROUSEL: mix.carousel_percentage / 100 * total_target,
            ContentType.AI_GENERATED: mix.ai_generated_percentage / 100 * total_target,
            ContentType.ANIMATED: mix.animated_percentage / 100 * total_target,
            ContentType.RAW_UGC: mix.raw_ugc_percentage / 100 * total_target,
        }
        
        # Find type that's most under-represented
        max_deficit = -999999
        selected = ContentType.UGC_CAPTION
        
        for ct, target in targets.items():
            if target > 0:  # Only consider types with non-zero percentage
                deficit = target - current_counts[ct]
                if deficit > max_deficit:
                    max_deficit = deficit
                    selected = ct
        
        return selected
    
    def _match_content(
        self,
        content_type: ContentType,
        available_content: List[Dict],
        pillar: Optional[str]
    ) -> tuple:
        """Try to match available content to a slot"""
        # For now, return None - content will be assigned later or created
        # This can be enhanced to actually match content from the pool
        
        if content_type == ContentType.UGC_CAPTION:
            # Look for analyzed videos
            for content in available_content:
                if content.get("type") == "video" and content.get("has_analysis"):
                    return content.get("id"), content.get("title")
        
        return None, f"[{content_type.value}] - To be created/assigned"
    
    async def _load_available_content(self) -> List[Dict]:
        """Load available content from database"""
        content = []
        
        with self.engine.connect() as conn:
            # Load analyzed videos
            result = conn.execute(text("""
                SELECT v.id, v.file_name, va.pre_social_score, va.topics
                FROM videos v
                LEFT JOIN video_analysis va ON va.video_id = v.id
                WHERE va.pre_social_score IS NOT NULL
                ORDER BY va.pre_social_score DESC
                LIMIT 500
            """))
            
            for row in result:
                content.append({
                    "id": str(row[0]),
                    "title": row[1],
                    "type": "video",
                    "has_analysis": True,
                    "score": row[2],
                    "topics": row[3]
                })
        
        return content
    
    async def _load_pillars(self, goal_id: str) -> List[Dict]:
        """Load pillars for a goal"""
        pillars = []
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT name, description, target_percentage
                FROM narrative_pillars
                WHERE goal_id = :goal_id AND is_active = TRUE
            """), {"goal_id": goal_id})
            
            for row in result:
                pillars.append({
                    "name": row[0],
                    "description": row[1],
                    "target_percentage": row[2]
                })
        
        return pillars
    
    async def _save_plan(self, plan: LongTermPlan):
        """Save plan to database"""
        with self.engine.connect() as conn:
            # Insert plan
            conn.execute(text("""
                INSERT INTO content_mix_plans (
                    id, name, start_date, end_date, total_posts,
                    config, content_distribution, status, created_at
                ) VALUES (
                    :id, :name, :start_date, :end_date, :total_posts,
                    :config, :distribution, :status, :created_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    total_posts = EXCLUDED.total_posts,
                    config = EXCLUDED.config,
                    content_distribution = EXCLUDED.content_distribution,
                    status = EXCLUDED.status,
                    updated_at = NOW()
            """), {
                "id": plan.id,
                "name": plan.name,
                "start_date": plan.start_date,
                "end_date": plan.end_date,
                "total_posts": plan.total_posts,
                "config": json.dumps(plan.config.content_mix.to_dict()),
                "distribution": json.dumps(plan.content_type_distribution),
                "status": plan.status,
                "created_at": plan.created_at
            })
            
            # Insert slots
            for slot in plan.slots:
                conn.execute(text("""
                    INSERT INTO content_mix_slots (
                        id, plan_id, scheduled_date, scheduled_time,
                        platform, content_type, pillar, content_id, content_title, status
                    ) VALUES (
                        :id, :plan_id, :date, :time,
                        :platform, :content_type, :pillar, :content_id, :content_title, :status
                    )
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": slot.id,
                    "plan_id": plan.id,
                    "date": slot.date,
                    "time": slot.time,
                    "platform": slot.platform,
                    "content_type": slot.content_type.value if isinstance(slot.content_type, ContentType) else slot.content_type,
                    "pillar": slot.pillar,
                    "content_id": slot.content_id,
                    "content_title": slot.content_title,
                    "status": slot.status
                })
            
            conn.commit()
    
    async def get_plan(self, plan_id: str) -> Optional[LongTermPlan]:
        """Load a plan from database"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, start_date, end_date, total_posts, config, status, created_at
                FROM content_mix_plans WHERE id = :id
            """), {"id": plan_id})
            
            row = result.fetchone()
            if not row:
                return None
            
            # Load slots
            slots_result = conn.execute(text("""
                SELECT id, scheduled_date, scheduled_time, platform, content_type,
                       pillar, content_id, content_title, status
                FROM content_mix_slots WHERE plan_id = :plan_id
                ORDER BY scheduled_date, scheduled_time
            """), {"plan_id": plan_id})
            
            slots = []
            for slot_row in slots_result:
                slots.append(ScheduledSlot(
                    id=str(slot_row[0]),
                    date=slot_row[1],
                    time=slot_row[2],
                    platform=slot_row[3],
                    content_type=ContentType(slot_row[4]) if slot_row[4] else ContentType.UGC_CAPTION,
                    pillar=slot_row[5],
                    content_id=slot_row[6],
                    content_title=slot_row[7],
                    status=slot_row[8]
                ))
            
            plan = LongTermPlan(
                id=str(row[0]),
                name=row[1],
                start_date=row[2],
                end_date=row[3],
                status=row[6],
                created_at=row[7],
                slots=slots
            )
            
            return plan
    
    async def list_plans(self, limit: int = 20) -> List[Dict]:
        """List all content mix plans"""
        plans = []
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, start_date, end_date, total_posts, 
                       content_distribution, status, created_at
                FROM content_mix_plans
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit})
            
            for row in result:
                plans.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "start_date": row[2].isoformat() if row[2] else None,
                    "end_date": row[3].isoformat() if row[3] else None,
                    "total_posts": row[4],
                    "content_distribution": json.loads(row[5]) if row[5] else {},
                    "status": row[6],
                    "created_at": row[7].isoformat() if row[7] else None
                })
        
        return plans
    
    async def update_slot(self, slot_id: str, updates: Dict) -> bool:
        """Update a single slot"""
        with self.engine.connect() as conn:
            set_clauses = []
            params = {"id": slot_id}
            
            for key, value in updates.items():
                if key in ["content_id", "content_title", "status", "platform", "content_type", "pillar"]:
                    set_clauses.append(f"{key} = :{key}")
                    params[key] = value
            
            if not set_clauses:
                return False
            
            query = f"UPDATE content_mix_slots SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = :id"
            conn.execute(text(query), params)
            conn.commit()
            
            return True
    
    async def approve_plan(self, plan_id: str) -> Dict:
        """Approve a plan and create scheduled posts"""
        plan = await self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        
        created = 0
        
        with self.engine.connect() as conn:
            for slot in plan.slots:
                if slot.content_id:
                    # Create scheduled post
                    scheduled_at = datetime.combine(slot.date, datetime.strptime(slot.time, "%H:%M").time())
                    
                    conn.execute(text("""
                        INSERT INTO scheduled_posts (
                            clip_id, title, platform, scheduled_time, scheduled_at, 
                            status, source, is_ai_recommended
                        ) VALUES (
                            CAST(:content_id AS uuid), :title, :platform, :scheduled_time, 
                            :scheduled_at, 'scheduled', 'content_mix_planner', TRUE
                        )
                    """), {
                        "content_id": slot.content_id,
                        "title": slot.content_title,
                        "platform": slot.platform,
                        "scheduled_time": scheduled_at,
                        "scheduled_at": scheduled_at
                    })
                    created += 1
            
            # Update plan status
            conn.execute(text("""
                UPDATE content_mix_plans SET status = 'approved', updated_at = NOW()
                WHERE id = :id
            """), {"id": plan_id})
            
            conn.commit()
        
        logger.info(f"[ContentMixPlanner] Plan approved: {created} posts scheduled")
        
        return {"approved": True, "posts_scheduled": created}


# Singleton
_planner_instance = None

def get_content_mix_planner() -> ContentMixPlanner:
    """Get or create planner singleton"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = ContentMixPlanner()
    return _planner_instance

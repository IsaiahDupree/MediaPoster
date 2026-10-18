"""
Narrative Goals Service
=======================
Service for managing narrative goals and content pillars for AI narrative scheduling.

NAR-001: Narrative Goals System
NAR-002: Narrative Pillars System

This service manages:
- Narrative goals (high-level storytelling objectives)
- Narrative pillars (content themes supporting goals)
- Target percentages and constraints per pillar
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4
from loguru import logger
from sqlalchemy import create_engine, text
import os

from services.event_bus import EventBus, Topics


class NarrativeGoalsService:
    """
    Narrative Goals Service

    Manages narrative goals and pillars for strategic content planning.
    Goals define the overarching story the creator wants to tell, while
    pillars are the content themes that support those goals.

    Usage:
        service = NarrativeGoalsService.get_instance()
        await service.start()

        # Create a narrative goal
        goal = await service.create_goal(
            workspace_id="abc123",
            goal_statement="Position myself as the go-to expert for DIY electronics",
            primary_cta="Waitlist",
            target_audience="Beginner makers aged 25-45"
        )

        # Add pillars to the goal
        pillar = await service.create_pillar(
            goal_id=goal["id"],
            name="Pain Points",
            pillar_type="value",
            target_percentage=20.0
        )
    """

    _instance: Optional["NarrativeGoalsService"] = None

    def __init__(self):
        """Initialize narrative goals service"""
        if NarrativeGoalsService._instance is not None:
            raise RuntimeError("Use NarrativeGoalsService.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("narrative-goals-service")

        # Database connection
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        self.engine = create_engine(self.database_url)

        logger.info("📖 Narrative Goals Service initialized")

    @classmethod
    def get_instance(cls) -> "NarrativeGoalsService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the narrative goals service"""
        # Create tables if they don't exist
        await self._ensure_tables_exist()

        await self.event_bus.publish(
            Topics.SYSTEM_STARTUP,
            {
                "service": "narrative_goals_service",
                "started_at": datetime.now(timezone.utc).isoformat()
            }
        )

        logger.success("✓ Narrative Goals Service started")

    async def stop(self) -> None:
        """Stop the narrative goals service"""
        logger.info("🛑 Narrative Goals Service stopped")

    async def _ensure_tables_exist(self) -> None:
        """Ensure narrative_goals, narrative_pillars, and scheduling_constraints tables exist"""
        try:
            with self.engine.connect() as conn:
                # Create narrative_goals table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS narrative_goals (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        workspace_id UUID,

                        -- Core Goal Definition
                        goal_statement TEXT NOT NULL,
                        primary_cta TEXT NOT NULL,
                        target_audience TEXT,

                        -- Time Horizon
                        time_horizon TEXT DEFAULT 'next_7_days',
                        start_date DATE,
                        end_date DATE,

                        -- Success Metrics
                        target_followers INTEGER,
                        target_engagement_rate FLOAT,
                        target_conversions INTEGER,

                        -- Status
                        status TEXT DEFAULT 'active',

                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """))

                # Create narrative_pillars table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS narrative_pillars (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        goal_id UUID REFERENCES narrative_goals(id) ON DELETE CASCADE,

                        name TEXT NOT NULL,
                        description TEXT,
                        color TEXT,
                        pillar_type TEXT NOT NULL,
                        keywords TEXT[],

                        target_percentage FLOAT,
                        min_posts_per_week INTEGER,
                        max_posts_per_week INTEGER,
                        priority INTEGER DEFAULT 5,
                        is_active BOOLEAN DEFAULT TRUE,

                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """))

                # Create scheduling_constraints table (NAR-003)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS scheduling_constraints (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        goal_id UUID REFERENCES narrative_goals(id) ON DELETE CASCADE,

                        enabled_platforms TEXT[] DEFAULT ARRAY['tiktok', 'instagram'],
                        max_posts_per_day INTEGER DEFAULT 3,
                        min_posts_per_day INTEGER DEFAULT 1,
                        posting_windows JSONB,
                        blackout_dates DATE[],
                        timezone TEXT DEFAULT 'America/New_York',

                        min_pre_social_score INTEGER DEFAULT 60,
                        require_analysis BOOLEAN DEFAULT TRUE,
                        max_same_pillar_consecutive INTEGER DEFAULT 2,

                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """))

                conn.commit()
                logger.debug("✓ Narrative tables ensured")

        except Exception as e:
            logger.error(f"Error ensuring tables: {e}")

    async def create_goal(
        self,
        workspace_id: str,
        goal_statement: str,
        primary_cta: str,
        target_audience: Optional[str] = None,
        time_horizon: str = "next_7_days",
        target_followers: Optional[int] = None,
        target_engagement_rate: Optional[float] = None,
        target_conversions: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new narrative goal

        Args:
            workspace_id: Workspace ID
            goal_statement: The narrative goal statement
            primary_cta: Primary call-to-action (Follow, Waitlist, Purchase, etc.)
            target_audience: Target audience description
            time_horizon: Time horizon (next_7_days, next_30_days, next_90_days)
            target_followers: Target follower count
            target_engagement_rate: Target engagement rate
            target_conversions: Target conversion count

        Returns:
            Created goal dictionary
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO narrative_goals (
                            workspace_id, goal_statement, primary_cta, target_audience,
                            time_horizon, target_followers, target_engagement_rate,
                            target_conversions, status
                        ) VALUES (
                            :workspace_id, :goal_statement, :primary_cta, :target_audience,
                            :time_horizon, :target_followers, :target_engagement_rate,
                            :target_conversions, 'active'
                        )
                        RETURNING id, created_at
                    """),
                    {
                        "workspace_id": workspace_id,
                        "goal_statement": goal_statement,
                        "primary_cta": primary_cta,
                        "target_audience": target_audience,
                        "time_horizon": time_horizon,
                        "target_followers": target_followers,
                        "target_engagement_rate": target_engagement_rate,
                        "target_conversions": target_conversions
                    }
                )

                row = result.fetchone()
                conn.commit()

                goal = {
                    "id": str(row[0]),
                    "workspace_id": workspace_id,
                    "goal_statement": goal_statement,
                    "primary_cta": primary_cta,
                    "target_audience": target_audience,
                    "time_horizon": time_horizon,
                    "target_followers": target_followers,
                    "target_engagement_rate": target_engagement_rate,
                    "target_conversions": target_conversions,
                    "status": "active",
                    "created_at": row[1].isoformat()
                }

                # Emit event
                await self.event_bus.publish(
                    Topics.CONTENT_GENERATED,  # Using existing topic
                    {
                        "event": "narrative_goal_created",
                        "goal_id": goal["id"],
                        "goal_statement": goal_statement
                    }
                )

                logger.info(f"📖 Narrative goal created: {goal['id'][:8]}")

                return goal

        except Exception as e:
            logger.error(f"Error creating goal: {e}")
            raise

    async def create_pillar(
        self,
        goal_id: str,
        name: str,
        pillar_type: str,
        target_percentage: float,
        description: Optional[str] = None,
        color: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        min_posts_per_week: Optional[int] = None,
        max_posts_per_week: Optional[int] = None,
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Create a narrative pillar for a goal

        Args:
            goal_id: Goal ID to associate with
            name: Pillar name (e.g., "Pain Points", "Social Proof")
            pillar_type: Type - 'value', 'proof', or 'cta'
            target_percentage: Target percentage of content (0-100)
            description: Pillar description
            color: Color code for UI
            keywords: List of keywords for classification
            min_posts_per_week: Minimum posts per week
            max_posts_per_week: Maximum posts per week
            priority: Priority level (1-10)

        Returns:
            Created pillar dictionary
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO narrative_pillars (
                            goal_id, name, description, color, pillar_type,
                            keywords, target_percentage, min_posts_per_week,
                            max_posts_per_week, priority, is_active
                        ) VALUES (
                            :goal_id, :name, :description, :color, :pillar_type,
                            :keywords, :target_percentage, :min_posts_per_week,
                            :max_posts_per_week, :priority, TRUE
                        )
                        RETURNING id, created_at
                    """),
                    {
                        "goal_id": goal_id,
                        "name": name,
                        "description": description,
                        "color": color,
                        "pillar_type": pillar_type,
                        "keywords": keywords or [],
                        "target_percentage": target_percentage,
                        "min_posts_per_week": min_posts_per_week,
                        "max_posts_per_week": max_posts_per_week,
                        "priority": priority
                    }
                )

                row = result.fetchone()
                conn.commit()

                pillar = {
                    "id": str(row[0]),
                    "goal_id": goal_id,
                    "name": name,
                    "description": description,
                    "color": color,
                    "pillar_type": pillar_type,
                    "keywords": keywords or [],
                    "target_percentage": target_percentage,
                    "min_posts_per_week": min_posts_per_week,
                    "max_posts_per_week": max_posts_per_week,
                    "priority": priority,
                    "is_active": True,
                    "created_at": row[1].isoformat()
                }

                logger.info(f"📊 Narrative pillar created: {name} ({target_percentage}%)")

                return pillar

        except Exception as e:
            logger.error(f"Error creating pillar: {e}")
            raise

    async def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get a narrative goal by ID"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT * FROM narrative_goals
                        WHERE id = :goal_id
                    """),
                    {"goal_id": goal_id}
                )

                row = result.fetchone()
                if not row:
                    return None

                return dict(row._mapping)

        except Exception as e:
            logger.error(f"Error getting goal: {e}")
            return None

    async def get_pillars_for_goal(self, goal_id: str) -> List[Dict[str, Any]]:
        """Get all pillars for a goal"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT * FROM narrative_pillars
                        WHERE goal_id = :goal_id
                        ORDER BY priority DESC, target_percentage DESC
                    """),
                    {"goal_id": goal_id}
                )

                pillars = [dict(row._mapping) for row in result]
                return pillars

        except Exception as e:
            logger.error(f"Error getting pillars: {e}")
            return []

    async def create_default_pillars(self, goal_id: str) -> List[Dict[str, Any]]:
        """
        Create default narrative pillars for a goal

        Creates the standard content mix:
        - 20% Pain Points (Value)
        - 15% Social Proof (Proof)
        - 25% Process/How-To (Value)
        - 15% Personality (Value)
        - 10% Product/Service (CTA)
        - 10% Promotion/CTA (CTA)
        - 5% Education (Value)
        """
        default_pillars = [
            {
                "name": "Pain Points",
                "pillar_type": "value",
                "target_percentage": 20.0,
                "description": "Address audience struggles and pain points",
                "color": "#FF6B6B"
            },
            {
                "name": "Social Proof",
                "pillar_type": "proof",
                "target_percentage": 15.0,
                "description": "Testimonials, results, credibility",
                "color": "#4ECDC4"
            },
            {
                "name": "Process/How-To",
                "pillar_type": "value",
                "target_percentage": 25.0,
                "description": "Educational content and tutorials",
                "color": "#45B7D1"
            },
            {
                "name": "Personality",
                "pillar_type": "value",
                "target_percentage": 15.0,
                "description": "Behind-the-scenes and personal content",
                "color": "#96CEB4"
            },
            {
                "name": "Product/Service",
                "pillar_type": "cta",
                "target_percentage": 10.0,
                "description": "Direct product/service showcases",
                "color": "#FFEAA7"
            },
            {
                "name": "Promotion/CTA",
                "pillar_type": "cta",
                "target_percentage": 10.0,
                "description": "Calls-to-action and promotions",
                "color": "#DDA15E"
            },
            {
                "name": "Education",
                "pillar_type": "value",
                "target_percentage": 5.0,
                "description": "Industry knowledge and insights",
                "color": "#BC6C25"
            }
        ]

        created_pillars = []
        for pillar_data in default_pillars:
            pillar = await self.create_pillar(
                goal_id=goal_id,
                name=pillar_data["name"],
                pillar_type=pillar_data["pillar_type"],
                target_percentage=pillar_data["target_percentage"],
                description=pillar_data["description"],
                color=pillar_data["color"]
            )
            created_pillars.append(pillar)

        logger.success(f"✓ Created {len(created_pillars)} default pillars")
        return created_pillars

    async def create_constraints(
        self,
        goal_id: str,
        enabled_platforms: Optional[List[str]] = None,
        max_posts_per_day: int = 3,
        min_posts_per_day: int = 1,
        posting_windows: Optional[Dict[str, Any]] = None,
        blackout_dates: Optional[List[str]] = None,
        timezone: str = "America/New_York",
        min_pre_social_score: int = 60,
        require_analysis: bool = True,
        max_same_pillar_consecutive: int = 2
    ) -> Dict[str, Any]:
        """
        Create scheduling constraints for a goal (NAR-003)

        Args:
            goal_id: Goal ID to associate with
            enabled_platforms: List of enabled platforms
            max_posts_per_day: Maximum posts per day
            min_posts_per_day: Minimum posts per day
            posting_windows: Posting time windows (JSONB)
            blackout_dates: Dates to avoid posting
            timezone: Timezone for scheduling
            min_pre_social_score: Minimum pre-social score required
            require_analysis: Whether to require content analysis
            max_same_pillar_consecutive: Max consecutive posts from same pillar

        Returns:
            Created constraints dictionary
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO scheduling_constraints (
                            goal_id, enabled_platforms, max_posts_per_day,
                            min_posts_per_day, posting_windows, blackout_dates,
                            timezone, min_pre_social_score, require_analysis,
                            max_same_pillar_consecutive
                        ) VALUES (
                            :goal_id, :enabled_platforms, :max_posts_per_day,
                            :min_posts_per_day, :posting_windows::jsonb, :blackout_dates,
                            :timezone, :min_pre_social_score, :require_analysis,
                            :max_same_pillar_consecutive
                        )
                        RETURNING id, created_at
                    """),
                    {
                        "goal_id": goal_id,
                        "enabled_platforms": enabled_platforms or ["tiktok", "instagram"],
                        "max_posts_per_day": max_posts_per_day,
                        "min_posts_per_day": min_posts_per_day,
                        "posting_windows": str(posting_windows) if posting_windows else None,
                        "blackout_dates": blackout_dates or [],
                        "timezone": timezone,
                        "min_pre_social_score": min_pre_social_score,
                        "require_analysis": require_analysis,
                        "max_same_pillar_consecutive": max_same_pillar_consecutive
                    }
                )

                row = result.fetchone()
                conn.commit()

                constraints = {
                    "id": str(row[0]),
                    "goal_id": goal_id,
                    "enabled_platforms": enabled_platforms or ["tiktok", "instagram"],
                    "max_posts_per_day": max_posts_per_day,
                    "min_posts_per_day": min_posts_per_day,
                    "posting_windows": posting_windows,
                    "blackout_dates": blackout_dates or [],
                    "timezone": timezone,
                    "min_pre_social_score": min_pre_social_score,
                    "require_analysis": require_analysis,
                    "max_same_pillar_consecutive": max_same_pillar_consecutive,
                    "created_at": row[1].isoformat()
                }

                logger.info(f"⚙️ Scheduling constraints created for goal {goal_id[:8]}")

                return constraints

        except Exception as e:
            logger.error(f"Error creating constraints: {e}")
            raise

    async def get_constraints_for_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get scheduling constraints for a goal"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT * FROM scheduling_constraints
                        WHERE goal_id = :goal_id
                        ORDER BY created_at DESC
                        LIMIT 1
                    """),
                    {"goal_id": goal_id}
                )

                row = result.fetchone()
                if not row:
                    return None

                return dict(row._mapping)

        except Exception as e:
            logger.error(f"Error getting constraints: {e}")
            return None


def get_narrative_goals_service() -> NarrativeGoalsService:
    """Get narrative goals service singleton"""
    return NarrativeGoalsService.get_instance()

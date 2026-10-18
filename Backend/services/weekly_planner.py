"""
Weekly Planner Service (AUTO-008)
=================================
Automatically generates next week's content plan based on learnings from previous weeks.

Features:
- Analyzes last 7-30 days of performance data
- Identifies winning templates, topics, formats, posting times
- Generates optimized weekly plan
- Incorporates template leaderboard and bandit allocation
- Learns from experiment results
- Maintains content diversity while optimizing for performance

Integration:
- Runs weekly (configurable schedule)
- Integrates with Template Leaderboard
- Integrates with Bandit Allocator
- Integrates with Experiment results
- Creates scheduled_posts for next week
"""

import os
import asyncio
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone, time
from loguru import logger
from sqlalchemy import create_engine, text
from dataclasses import dataclass, field
from collections import Counter, defaultdict

from services.event_bus import EventBus, Topics


@dataclass
class LearningWeights:
    """Weights for different learning signals"""
    template_performance: float = 0.35
    topic_performance: float = 0.25
    time_slot_performance: float = 0.20
    format_performance: float = 0.15
    experiment_insights: float = 0.05


@dataclass
class WeeklyPlanConfig:
    """Configuration for weekly plan generation"""
    posts_per_day: int = 2
    platforms: List[str] = field(default_factory=lambda: ["tiktok", "instagram"])
    default_posting_times: List[str] = field(default_factory=lambda: ["09:00", "18:00"])
    learning_window_days: int = 30  # Look back 30 days
    min_data_points: int = 10       # Minimum posts to analyze
    diversity_factor: float = 0.3   # 30% reserved for exploration


@dataclass
class WeeklyPlan:
    """Generated weekly plan"""
    id: str
    start_date: datetime
    end_date: datetime
    slots: List[Dict[str, Any]]
    learnings: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WeeklyPlanner:
    """
    Generates optimized weekly content plans based on historical performance.

    Workflow:
    1. Analyze last 30 days of content performance
    2. Extract winning patterns (templates, topics, times, formats)
    3. Get bandit allocation from BanditAllocator
    4. Get experiment learnings
    5. Generate balanced weekly plan (70% exploit, 30% explore)
    6. Create scheduled_posts with proper attribution
    7. Log plan and learnings
    """

    _instance: Optional["WeeklyPlanner"] = None

    def __init__(self):
        if WeeklyPlanner._instance is not None:
            raise RuntimeError("Use WeeklyPlanner.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("weekly-planner")

        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        )
        self.engine = create_engine(self.database_url)

        # Configuration
        self.config = WeeklyPlanConfig()
        self.weights = LearningWeights()
        self.check_interval = int(os.getenv("WEEKLY_PLANNER_INTERVAL", "86400"))  # Check daily

        # State
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._last_plan_date: Optional[datetime] = None

        WeeklyPlanner._instance = self
        logger.info("✓ WeeklyPlanner initialized")

    @classmethod
    def get_instance(cls) -> "WeeklyPlanner":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the weekly planner service"""
        if self._is_running:
            logger.warning("⚠️  WeeklyPlanner already running")
            return

        self._is_running = True

        # Start planning loop
        self._task = asyncio.create_task(self._planning_loop())

        await self.event_bus.publish(
            Topics.SERVICE_STARTED,
            {"service": "weekly_planner"}
        )

        logger.success("🚀 WeeklyPlanner started")

    async def stop(self) -> None:
        """Stop the weekly planner service"""
        self._is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self.event_bus.publish(
            Topics.SERVICE_STOPPED,
            {"service": "weekly_planner"}
        )

        logger.info("🛑 WeeklyPlanner stopped")

    async def _planning_loop(self) -> None:
        """Main planning loop - runs weekly"""
        logger.info("🔍 Weekly planning loop started")

        while self._is_running:
            try:
                # Check if it's time to generate a new plan
                should_generate = await self._should_generate_plan()

                if should_generate:
                    logger.info("📅 Generating new weekly plan...")
                    plan = await self.generate_weekly_plan()

                    if plan:
                        logger.success(f"✓ Generated weekly plan with {len(plan.slots)} slots")
                        self._last_plan_date = datetime.now(timezone.utc)

                # Check daily, but only generate weekly
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in weekly planning loop: {e}")
                await asyncio.sleep(self.check_interval)

        logger.info("🛑 Weekly planning loop stopped")

    async def _should_generate_plan(self) -> bool:
        """Check if we should generate a new plan"""
        # Generate on Sundays or if no plan generated yet
        now = datetime.now(timezone.utc)

        if self._last_plan_date is None:
            return True

        # Generate weekly on Sundays
        days_since_last = (now - self._last_plan_date).days
        is_sunday = now.weekday() == 6

        return is_sunday and days_since_last >= 6

    async def generate_weekly_plan(
        self,
        start_date: Optional[datetime] = None,
        config: Optional[WeeklyPlanConfig] = None
    ) -> Optional[WeeklyPlan]:
        """
        Generate a weekly content plan based on learnings.

        Args:
            start_date: Start date for plan (defaults to next Monday)
            config: Plan configuration (uses default if not provided)

        Returns:
            WeeklyPlan with slots and learnings
        """
        try:
            config = config or self.config

            # Default to next Monday
            if not start_date:
                now = datetime.now(timezone.utc)
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                start_date = now + timedelta(days=days_until_monday)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

            end_date = start_date + timedelta(days=7)

            # Step 1: Analyze historical performance
            logger.info("📊 Analyzing historical performance...")
            learnings = await self._analyze_performance(config.learning_window_days)

            if not learnings.get("total_posts") or learnings["total_posts"] < config.min_data_points:
                logger.warning(f"⚠️  Insufficient data: only {learnings.get('total_posts', 0)} posts in last {config.learning_window_days} days")
                return None

            # Step 2: Get bandit allocation
            logger.info("🎰 Getting bandit allocation...")
            allocation = await self._get_bandit_allocation()

            # Step 3: Get experiment learnings
            logger.info("🧪 Getting experiment learnings...")
            experiment_learnings = await self._get_experiment_learnings()

            # Step 4: Generate slots
            logger.info("📅 Generating weekly slots...")
            slots = await self._generate_slots(
                start_date=start_date,
                end_date=end_date,
                learnings=learnings,
                allocation=allocation,
                experiment_learnings=experiment_learnings,
                config=config
            )

            # Step 5: Create plan
            plan = WeeklyPlan(
                id=f"plan-{start_date.strftime('%Y%m%d')}",
                start_date=start_date,
                end_date=end_date,
                slots=slots,
                learnings=learnings,
                metadata={
                    "allocation": allocation,
                    "experiment_learnings": experiment_learnings,
                    "config": {
                        "posts_per_day": config.posts_per_day,
                        "platforms": config.platforms,
                        "learning_window_days": config.learning_window_days
                    }
                }
            )

            # Step 6: Save to database
            await self._save_plan(plan)

            # Step 7: Emit event
            await self.event_bus.publish(
                Topics.WEEKLY_PLAN_GENERATED,
                {
                    "plan_id": plan.id,
                    "start_date": plan.start_date.isoformat(),
                    "end_date": plan.end_date.isoformat(),
                    "slot_count": len(plan.slots),
                    "learnings_summary": {
                        "total_posts_analyzed": learnings.get("total_posts", 0),
                        "top_template": learnings.get("top_templates", [None])[0],
                        "top_topic": learnings.get("top_topics", [None])[0]
                    }
                }
            )

            logger.success(f"✓ Weekly plan generated: {len(slots)} slots")
            return plan

        except Exception as e:
            logger.error(f"❌ Error generating weekly plan: {e}")
            return None

    async def _analyze_performance(self, lookback_days: int) -> Dict[str, Any]:
        """Analyze historical performance to extract learnings"""
        try:
            with self.engine.connect() as conn:
                # Get all posts from last N days with metrics
                result = conn.execute(text("""
                    SELECT
                        pc.id as template_id,
                        pc.title as topic,
                        pc.platform as content_type,
                        'general' as awareness_level,
                        EXTRACT(HOUR FROM pc.posted_at) as post_hour,
                        pc.views,
                        pc.likes,
                        pc.comments,
                        pc.shares,
                        pc.engagement_rate,
                        pc.platform
                    FROM posted_content pc
                    WHERE
                        pc.posted_at >= NOW() - INTERVAL :days DAY
                        AND pc.views > 0
                    ORDER BY pc.engagement_rate DESC NULLS LAST
                """), {"days": f"{lookback_days} days"})

                posts = list(result)

                if not posts:
                    return {"total_posts": 0}

                # Aggregate metrics by different dimensions
                template_performance = defaultdict(list)
                topic_performance = defaultdict(list)
                time_performance = defaultdict(list)
                format_performance = defaultdict(list)
                awareness_performance = defaultdict(list)

                for row in posts:
                    template_id = str(row[0]) if row[0] else "unknown"
                    topic = row[1] or "unknown"
                    content_type = row[2] or "unknown"
                    awareness = row[3] or "unknown"
                    hour = int(row[4]) if row[4] else 12
                    views = row[5] or 0
                    engagement_rate = float(row[9]) if row[9] else 0.0

                    # Score = weighted combination of views and engagement
                    score = (views / 1000) * 0.4 + engagement_rate * 0.6

                    template_performance[template_id].append(score)
                    topic_performance[topic].append(score)
                    time_performance[hour].append(score)
                    format_performance[content_type].append(score)
                    awareness_performance[awareness].append(score)

                # Calculate averages and rankings
                def rank_by_avg(perf_dict: dict) -> List[Tuple[str, float]]:
                    averages = {k: sum(v)/len(v) for k, v in perf_dict.items() if v}
                    return sorted(averages.items(), key=lambda x: x[1], reverse=True)

                top_templates = rank_by_avg(template_performance)
                top_topics = rank_by_avg(topic_performance)
                top_times = rank_by_avg(time_performance)
                top_formats = rank_by_avg(format_performance)
                top_awareness = rank_by_avg(awareness_performance)

                learnings = {
                    "total_posts": len(posts),
                    "lookback_days": lookback_days,
                    "top_templates": [t[0] for t in top_templates[:10]],
                    "template_scores": dict(top_templates[:10]),
                    "top_topics": [t[0] for t in top_topics[:10]],
                    "topic_scores": dict(top_topics[:10]),
                    "best_posting_hours": [int(t[0]) for t in top_times[:5]],
                    "time_scores": dict(top_times[:5]),
                    "top_formats": [t[0] for t in top_formats[:5]],
                    "format_scores": dict(top_formats[:5]),
                    "top_awareness_levels": [t[0] for t in top_awareness[:5]],
                    "awareness_scores": dict(top_awareness[:5])
                }

                logger.info(f"📊 Analyzed {len(posts)} posts. Top template: {learnings['top_templates'][0] if learnings['top_templates'] else 'none'}")

                return learnings

        except Exception as e:
            logger.error(f"❌ Error analyzing performance: {e}")
            return {"total_posts": 0, "error": str(e)}

    async def _get_bandit_allocation(self) -> Dict[str, float]:
        """Get current bandit allocation from BanditAllocator service"""
        try:
            # Try to import and use BanditAllocator
            from services.bandit_allocator import BanditAllocator

            allocator = BanditAllocator.get_instance()
            allocation = allocator.get_allocation()

            return allocation if allocation else {}

        except Exception as e:
            logger.warning(f"⚠️  Could not get bandit allocation: {e}")
            # Return default 70/20/10 split
            return {
                "exploit": 0.70,
                "explore": 0.20,
                "experiment": 0.10
            }

    async def _get_experiment_learnings(self) -> Dict[str, Any]:
        """Get learnings from recent experiments"""
        try:
            with self.engine.connect() as conn:
                # Get recent completed experiments with winners
                result = conn.execute(text("""
                    SELECT
                        e.id,
                        e.name,
                        h.statement,
                        h.status,
                        h.result_summary,
                        ew.winning_variant,
                        ew.improvement_percent
                    FROM experiments e
                    JOIN hypotheses h ON h.experiment_id = e.id
                    LEFT JOIN experiment_winners ew ON ew.experiment_id = e.id
                    WHERE
                        e.status = 'completed'
                        AND e.completed_at >= NOW() - INTERVAL '30 days'
                        AND h.status IN ('pass', 'fail')
                    ORDER BY e.completed_at DESC
                    LIMIT 10
                """))

                learnings = {
                    "total_experiments": 0,
                    "passed_hypotheses": [],
                    "failed_hypotheses": [],
                    "key_insights": []
                }

                for row in result:
                    learnings["total_experiments"] += 1

                    hypothesis = {
                        "experiment_id": str(row[0]),
                        "experiment_name": row[1],
                        "statement": row[2],
                        "status": row[3],
                        "summary": row[4] if row[4] else {},
                        "winning_variant": row[5],
                        "improvement": float(row[6]) if row[6] else 0
                    }

                    if row[3] == "pass":
                        learnings["passed_hypotheses"].append(hypothesis)
                    else:
                        learnings["failed_hypotheses"].append(hypothesis)

                return learnings

        except Exception as e:
            logger.warning(f"⚠️  Could not get experiment learnings: {e}")
            return {"total_experiments": 0}

    async def _generate_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        learnings: Dict[str, Any],
        allocation: Dict[str, float],
        experiment_learnings: Dict[str, Any],
        config: WeeklyPlanConfig
    ) -> List[Dict[str, Any]]:
        """Generate individual slots for the week"""
        slots = []

        # Get posting times (use learnings or defaults)
        best_hours = learnings.get("best_posting_hours", [9, 18])
        if len(best_hours) < config.posts_per_day:
            best_hours = config.default_posting_times

        # Get top templates and topics
        top_templates = learnings.get("top_templates", [])
        top_topics = learnings.get("top_topics", [])
        top_formats = learnings.get("top_formats", ["ugc"])
        top_awareness = learnings.get("top_awareness_levels", ["problem_aware"])

        # Calculate slot distribution
        total_slots = config.posts_per_day * 7
        exploit_count = int(total_slots * allocation.get("exploit", 0.70))
        explore_count = int(total_slots * allocation.get("explore", 0.20))
        experiment_count = total_slots - exploit_count - explore_count

        slot_idx = 0
        current_date = start_date

        while current_date < end_date:
            for post_num in range(config.posts_per_day):
                # Determine slot type
                if slot_idx < exploit_count:
                    slot_type = "exploit"
                elif slot_idx < exploit_count + explore_count:
                    slot_type = "explore"
                else:
                    slot_type = "experiment"

                # Get posting time
                hour = best_hours[post_num] if post_num < len(best_hours) else 12
                scheduled_at = current_date.replace(hour=hour, minute=0)

                # Select template/topic based on slot type
                if slot_type == "exploit" and top_templates:
                    template_id = top_templates[slot_idx % len(top_templates)]
                    topic = top_topics[slot_idx % len(top_topics)] if top_topics else None
                elif slot_type == "explore" and len(top_templates) > 5:
                    # Explore lower-ranked templates
                    template_id = top_templates[5 + (slot_idx % (len(top_templates) - 5))]
                    topic = top_topics[5 + (slot_idx % (len(top_topics) - 5))] if len(top_topics) > 5 else None
                else:
                    # Experiment or fallback
                    template_id = None
                    topic = None

                # Select platform (alternate)
                platform = config.platforms[slot_idx % len(config.platforms)]

                # Select format and awareness
                content_type = top_formats[slot_idx % len(top_formats)] if top_formats else "ugc"
                awareness_level = top_awareness[slot_idx % len(top_awareness)] if top_awareness else "problem_aware"

                slot = {
                    "scheduled_at": scheduled_at.isoformat(),
                    "platform": platform,
                    "template_id": template_id,
                    "topic": topic,
                    "content_type": content_type,
                    "awareness_level": awareness_level,
                    "origin_type": slot_type,
                    "status": "pending"
                }

                slots.append(slot)
                slot_idx += 1

            current_date += timedelta(days=1)

        return slots

    async def _save_plan(self, plan: WeeklyPlan) -> None:
        """Save plan and create scheduled_posts"""
        try:
            with self.engine.connect() as conn:
                # Save plan metadata
                conn.execute(text("""
                    INSERT INTO weekly_plans
                    (id, start_date, end_date, learnings, metadata, created_at)
                    VALUES
                    (:id, :start_date, :end_date, :learnings, :metadata, :created_at)
                    ON CONFLICT (id) DO UPDATE
                    SET learnings = EXCLUDED.learnings,
                        metadata = EXCLUDED.metadata
                """), {
                    "id": plan.id,
                    "start_date": plan.start_date,
                    "end_date": plan.end_date,
                    "learnings": json.dumps(plan.learnings),
                    "metadata": json.dumps(plan.metadata),
                    "created_at": plan.created_at
                })

                # Create scheduled_posts
                for slot in plan.slots:
                    conn.execute(text("""
                        INSERT INTO scheduled_posts
                        (id, scheduled_at, platform, template_id, topic, content_type,
                         awareness_level, origin_type, status, weekly_plan_id)
                        VALUES
                        (gen_random_uuid(), :scheduled_at, :platform, :template_id, :topic,
                         :content_type, :awareness_level, :origin_type, :status, :plan_id)
                    """), {
                        "scheduled_at": slot["scheduled_at"],
                        "platform": slot["platform"],
                        "template_id": slot.get("template_id"),
                        "topic": slot.get("topic"),
                        "content_type": slot["content_type"],
                        "awareness_level": slot["awareness_level"],
                        "origin_type": slot["origin_type"],
                        "status": slot["status"],
                        "plan_id": plan.id
                    })

                conn.commit()
                logger.info(f"✓ Saved weekly plan {plan.id} with {len(plan.slots)} slots")

        except Exception as e:
            logger.error(f"❌ Error saving plan: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "is_running": self._is_running,
            "check_interval": self.check_interval,
            "last_plan_date": self._last_plan_date.isoformat() if self._last_plan_date else None,
            "config": {
                "posts_per_day": self.config.posts_per_day,
                "platforms": self.config.platforms,
                "learning_window_days": self.config.learning_window_days,
                "diversity_factor": self.config.diversity_factor
            }
        }

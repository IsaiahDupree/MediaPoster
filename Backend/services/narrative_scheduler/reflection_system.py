"""
Reflection System for Narrative Scheduling

Analyzes weekly performance and generates learnings
for continuous improvement of content strategy.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from sqlalchemy import create_engine, text

from .models import Learning, PerformanceMetrics, WeeklyPlan

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


@dataclass
class PillarInsight:
    """Insight about a specific pillar's performance"""
    pillar_name: str
    posts_count: int
    avg_views: float
    avg_engagement: float
    performance_vs_average: float  # percentage above/below average
    verdict: str  # "exceeded", "met", "underperformed"
    insight: str
    recommendation: str


@dataclass 
class WeeklyReflection:
    """Complete weekly reflection report"""
    schedule_id: str
    week_start: date
    week_end: date
    
    # Goal Progress
    goal_statement: str
    goal_progress_pct: float
    goal_on_track: bool
    
    # Overall Metrics
    total_posts: int
    total_views: int
    total_engagement: int
    avg_engagement_rate: float
    
    # Pillar Analysis
    pillar_insights: List[PillarInsight] = field(default_factory=list)
    top_performing_pillar: Optional[str] = None
    underperforming_pillar: Optional[str] = None
    
    # Learnings
    learnings: List[Learning] = field(default_factory=list)
    
    # Recommendations for next week
    recommendations: List[str] = field(default_factory=list)
    pillar_adjustments: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "goal_statement": self.goal_statement,
            "goal_progress_pct": self.goal_progress_pct,
            "goal_on_track": self.goal_on_track,
            "total_posts": self.total_posts,
            "total_views": self.total_views,
            "total_engagement": self.total_engagement,
            "avg_engagement_rate": self.avg_engagement_rate,
            "pillar_insights": [
                {
                    "pillar": p.pillar_name,
                    "posts": p.posts_count,
                    "avg_views": p.avg_views,
                    "avg_engagement": p.avg_engagement,
                    "vs_average": p.performance_vs_average,
                    "verdict": p.verdict,
                    "insight": p.insight,
                    "recommendation": p.recommendation
                } for p in self.pillar_insights
            ],
            "top_performing_pillar": self.top_performing_pillar,
            "underperforming_pillar": self.underperforming_pillar,
            "learnings": [l.to_dict() for l in self.learnings],
            "recommendations": self.recommendations,
            "pillar_adjustments": self.pillar_adjustments
        }


class ReflectionSystem:
    """
    Analyzes schedule performance and generates learnings.
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
    
    async def generate_weekly_reflection(
        self,
        schedule_id: str
    ) -> WeeklyReflection:
        """
        Generate a comprehensive reflection for a completed schedule.
        
        Args:
            schedule_id: The weekly schedule to analyze
            
        Returns:
            WeeklyReflection with insights and learnings
        """
        logger.info(f"[Reflection] Generating reflection for schedule {schedule_id}")
        
        # Load schedule and performance data
        schedule_data = await self._load_schedule_data(schedule_id)
        performance_data = await self._load_performance_data(schedule_id)
        goal_data = await self._load_goal_data(schedule_data.get("goal_id"))
        
        # Analyze pillar performance
        pillar_insights = await self._analyze_pillar_performance(
            schedule_id, 
            performance_data
        )
        
        # Determine top/bottom performers
        sorted_pillars = sorted(
            pillar_insights, 
            key=lambda p: p.avg_engagement, 
            reverse=True
        )
        
        top_pillar = sorted_pillars[0].pillar_name if sorted_pillars else None
        bottom_pillar = sorted_pillars[-1].pillar_name if sorted_pillars else None
        
        # Generate learnings
        learnings = await self._generate_learnings(
            schedule_id,
            pillar_insights,
            performance_data
        )
        
        # Generate recommendations
        recommendations, pillar_adjustments = await self._generate_recommendations(
            pillar_insights,
            goal_data,
            performance_data
        )
        
        # Assess goal progress
        goal_progress = self._assess_goal_progress(goal_data, performance_data)
        
        reflection = WeeklyReflection(
            schedule_id=schedule_id,
            week_start=schedule_data.get("week_start", date.today()),
            week_end=schedule_data.get("week_end", date.today()),
            goal_statement=goal_data.get("goal_statement", "Build engagement"),
            goal_progress_pct=goal_progress.get("progress", 0),
            goal_on_track=goal_progress.get("on_track", False),
            total_posts=performance_data.get("total_posts", 0),
            total_views=performance_data.get("total_views", 0),
            total_engagement=performance_data.get("total_engagement", 0),
            avg_engagement_rate=performance_data.get("avg_engagement_rate", 0),
            pillar_insights=pillar_insights,
            top_performing_pillar=top_pillar,
            underperforming_pillar=bottom_pillar,
            learnings=learnings,
            recommendations=recommendations,
            pillar_adjustments=pillar_adjustments
        )
        
        # Save reflection to database
        await self._save_reflection(reflection)
        
        # Save learnings to database
        await self._save_learnings(learnings)
        
        logger.info(f"[Reflection] Generated {len(learnings)} learnings, {len(recommendations)} recommendations")
        
        return reflection
    
    async def _load_schedule_data(self, schedule_id: str) -> Dict[str, Any]:
        """Load schedule data from database"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, goal_id, week_start, week_end, total_posts, 
                       pillar_distribution, platform_distribution, status
                FROM weekly_schedules WHERE id = :id
            """), {"id": schedule_id})
            
            row = result.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "goal_id": str(row[1]) if row[1] else None,
                    "week_start": row[2],
                    "week_end": row[3],
                    "total_posts": row[4],
                    "pillar_distribution": json.loads(row[5]) if row[5] else {},
                    "platform_distribution": json.loads(row[6]) if row[6] else {},
                    "status": row[7]
                }
        
        return {}
    
    async def _load_performance_data(self, schedule_id: str) -> Dict[str, Any]:
        """Load performance metrics for scheduled posts"""
        with self.engine.connect() as conn:
            # Get posts from this schedule
            result = conn.execute(text("""
                SELECT ss.pillar, ss.video_id,
                       pc.views, pc.likes, pc.comments, pc.shares
                FROM schedule_slots ss
                LEFT JOIN posted_content pc ON pc.content_id::text = ss.video_id::text
                WHERE ss.schedule_id = :schedule_id
            """), {"schedule_id": schedule_id})
            
            posts = list(result)
            
            if not posts:
                return {
                    "total_posts": 0,
                    "total_views": 0,
                    "total_engagement": 0,
                    "avg_engagement_rate": 0,
                    "pillar_metrics": {}
                }
            
            # Aggregate metrics
            total_views = sum(p[2] or 0 for p in posts)
            total_likes = sum(p[3] or 0 for p in posts)
            total_comments = sum(p[4] or 0 for p in posts)
            total_shares = sum(p[5] or 0 for p in posts)
            total_engagement = total_likes + total_comments + total_shares
            
            avg_engagement = (total_engagement / total_views * 100) if total_views > 0 else 0
            
            # Per-pillar metrics
            pillar_metrics = {}
            for post in posts:
                pillar = post[0] or "Uncategorized"
                if pillar not in pillar_metrics:
                    pillar_metrics[pillar] = {
                        "posts": 0,
                        "views": 0,
                        "engagement": 0
                    }
                
                pillar_metrics[pillar]["posts"] += 1
                pillar_metrics[pillar]["views"] += post[2] or 0
                pillar_metrics[pillar]["engagement"] += (post[3] or 0) + (post[4] or 0) + (post[5] or 0)
            
            return {
                "total_posts": len(posts),
                "total_views": total_views,
                "total_engagement": total_engagement,
                "avg_engagement_rate": avg_engagement,
                "pillar_metrics": pillar_metrics
            }
    
    async def _load_goal_data(self, goal_id: Optional[str]) -> Dict[str, Any]:
        """Load goal data"""
        if not goal_id:
            return {"goal_statement": "Build engagement", "primary_cta": "follow"}
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT goal_text, cta_type, audience_description
                FROM narrative_goals WHERE id = :id
            """), {"id": goal_id})
            
            row = result.fetchone()
            if row:
                return {
                    "goal_statement": row[0] or "Build engagement",
                    "primary_cta": row[1] or "follow",
                    "target_audience": row[2] or ""
                }
        
        return {"goal_statement": "Build engagement", "primary_cta": "follow"}
    
    async def _analyze_pillar_performance(
        self,
        schedule_id: str,
        performance_data: Dict[str, Any]
    ) -> List[PillarInsight]:
        """Analyze each pillar's performance"""
        insights = []
        
        pillar_metrics = performance_data.get("pillar_metrics", {})
        avg_engagement = performance_data.get("avg_engagement_rate", 0)
        
        for pillar_name, metrics in pillar_metrics.items():
            posts = metrics.get("posts", 0)
            views = metrics.get("views", 0)
            engagement = metrics.get("engagement", 0)
            
            avg_views = views / posts if posts > 0 else 0
            pillar_engagement = (engagement / views * 100) if views > 0 else 0
            
            # Compare to average
            vs_average = ((pillar_engagement - avg_engagement) / avg_engagement * 100) if avg_engagement > 0 else 0
            
            # Determine verdict
            if vs_average > 20:
                verdict = "exceeded"
                insight = f"{pillar_name} significantly outperformed average"
                recommendation = f"Consider increasing {pillar_name} allocation"
            elif vs_average < -20:
                verdict = "underperformed"
                insight = f"{pillar_name} underperformed compared to other pillars"
                recommendation = f"Review {pillar_name} content quality or reduce allocation"
            else:
                verdict = "met"
                insight = f"{pillar_name} performed as expected"
                recommendation = f"Maintain current {pillar_name} strategy"
            
            insights.append(PillarInsight(
                pillar_name=pillar_name,
                posts_count=posts,
                avg_views=avg_views,
                avg_engagement=pillar_engagement,
                performance_vs_average=vs_average,
                verdict=verdict,
                insight=insight,
                recommendation=recommendation
            ))
        
        return insights
    
    async def _generate_learnings(
        self,
        schedule_id: str,
        pillar_insights: List[PillarInsight],
        performance_data: Dict[str, Any]
    ) -> List[Learning]:
        """Generate learnings from performance analysis"""
        learnings = []
        
        # Pillar-based learnings
        for insight in pillar_insights:
            if insight.verdict == "exceeded":
                learnings.append(Learning(
                    learning_type="pillar_performance",
                    insight=insight.insight,
                    confidence=0.85,
                    action=insight.recommendation,
                    source_schedule_id=schedule_id
                ))
            elif insight.verdict == "underperformed":
                learnings.append(Learning(
                    learning_type="pillar_performance",
                    insight=insight.insight,
                    confidence=0.75,
                    action=insight.recommendation,
                    source_schedule_id=schedule_id
                ))
        
        # Overall engagement learning
        avg_engagement = performance_data.get("avg_engagement_rate", 0)
        if avg_engagement > 5:
            learnings.append(Learning(
                learning_type="overall_performance",
                insight=f"Week achieved {avg_engagement:.1f}% engagement rate - above industry average",
                confidence=0.9,
                action="Continue current content mix strategy",
                source_schedule_id=schedule_id
            ))
        elif avg_engagement < 2:
            learnings.append(Learning(
                learning_type="overall_performance",
                insight=f"Week achieved only {avg_engagement:.1f}% engagement - below target",
                confidence=0.8,
                action="Review content quality, timing, and hook effectiveness",
                source_schedule_id=schedule_id
            ))
        
        return learnings
    
    async def _generate_recommendations(
        self,
        pillar_insights: List[PillarInsight],
        goal_data: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> tuple[List[str], Dict[str, float]]:
        """Generate recommendations for next week"""
        recommendations = []
        pillar_adjustments = {}
        
        for insight in pillar_insights:
            if insight.verdict == "exceeded":
                # Increase by 10%
                pillar_adjustments[insight.pillar_name] = 1.10
                recommendations.append(
                    f"Increase {insight.pillar_name} content by 10% - outperformed by {insight.performance_vs_average:.0f}%"
                )
            elif insight.verdict == "underperformed":
                # Decrease by 10%
                pillar_adjustments[insight.pillar_name] = 0.90
                recommendations.append(
                    f"Reduce {insight.pillar_name} by 10% or improve content quality"
                )
        
        # Goal-based recommendations
        primary_cta = goal_data.get("primary_cta", "follow")
        if primary_cta == "waitlist" or primary_cta == "purchase":
            recommendations.append(
                "Consider adding stronger CTAs to Process/How-To content"
            )
        
        if not recommendations:
            recommendations.append("Schedule performed as expected - maintain current strategy")
        
        return recommendations, pillar_adjustments
    
    def _assess_goal_progress(
        self,
        goal_data: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess progress toward goal"""
        # Simplified assessment based on engagement
        avg_engagement = performance_data.get("avg_engagement_rate", 0)
        
        # Consider 4%+ as on track
        on_track = avg_engagement >= 4.0
        progress = min(avg_engagement / 4.0 * 100, 100)
        
        return {
            "on_track": on_track,
            "progress": progress
        }
    
    async def _save_reflection(self, reflection: WeeklyReflection):
        """Save reflection to database"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO schedule_performance (
                    schedule_id, week_start, week_end, total_posts, total_views,
                    total_likes, total_comments, avg_engagement_rate,
                    goal_progress_pct, pillar_performance
                ) VALUES (
                    :schedule_id, :week_start, :week_end, :total_posts, :total_views,
                    0, 0, :avg_engagement, :goal_progress, :pillar_perf
                )
                ON CONFLICT (schedule_id) DO UPDATE SET
                    total_views = EXCLUDED.total_views,
                    avg_engagement_rate = EXCLUDED.avg_engagement_rate,
                    goal_progress_pct = EXCLUDED.goal_progress_pct,
                    pillar_performance = EXCLUDED.pillar_performance
            """), {
                "schedule_id": reflection.schedule_id,
                "week_start": reflection.week_start,
                "week_end": reflection.week_end,
                "total_posts": reflection.total_posts,
                "total_views": reflection.total_views,
                "avg_engagement": reflection.avg_engagement_rate,
                "goal_progress": reflection.goal_progress_pct,
                "pillar_perf": json.dumps({
                    p.pillar_name: {
                        "posts": p.posts_count,
                        "avg_views": p.avg_views,
                        "avg_engagement": p.avg_engagement,
                        "verdict": p.verdict
                    } for p in reflection.pillar_insights
                })
            })
            conn.commit()
    
    async def _save_learnings(self, learnings: List[Learning]):
        """Save learnings to database"""
        with self.engine.connect() as conn:
            for learning in learnings:
                conn.execute(text("""
                    INSERT INTO learnings (
                        id, learning_type, insight, confidence, action,
                        source_schedule_id, applied
                    ) VALUES (
                        :id, :type, :insight, :confidence, :action,
                        :source_id, FALSE
                    )
                """), {
                    "id": learning.id,
                    "type": learning.learning_type,
                    "insight": learning.insight,
                    "confidence": learning.confidence,
                    "action": learning.action,
                    "source_id": learning.source_schedule_id
                })
            conn.commit()
    
    async def get_accumulated_learnings(
        self,
        goal_id: Optional[str] = None,
        min_confidence: float = 0.7,
        unapplied_only: bool = True
    ) -> List[Learning]:
        """Get accumulated learnings for planning"""
        with self.engine.connect() as conn:
            query = """
                SELECT id, learning_type, insight, confidence, action, 
                       source_schedule_id, applied
                FROM learnings
                WHERE confidence >= :min_confidence
            """
            params = {"min_confidence": min_confidence}
            
            if unapplied_only:
                query += " AND applied = FALSE"
            
            query += " ORDER BY confidence DESC, created_at DESC LIMIT 10"
            
            result = conn.execute(text(query), params)
            
            learnings = []
            for row in result:
                learnings.append(Learning(
                    id=str(row[0]),
                    learning_type=row[1],
                    insight=row[2],
                    confidence=row[3],
                    action=row[4],
                    source_schedule_id=str(row[5]) if row[5] else "",
                    applied=row[6]
                ))
            
            return learnings

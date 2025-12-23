"""
AI Reasoning Engine for Narrative Scheduling

This module provides the core AI logic for:
1. Analyzing available content against narrative goals
2. Classifying videos into pillars
3. Generating reasoned scheduling decisions
4. Creating transparent justifications
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass

from .models import (
    NarrativeGoal,
    NarrativePillar,
    SchedulingConstraints,
    VideoCandidate,
    ScheduledSlot,
    ReasoningStep,
    WeeklyPlan,
    PerformanceMetrics,
    Learning,
)

logger = logging.getLogger(__name__)


class NarrativeReasoningEngine:
    """
    AI Reasoning Engine that generates justified content schedules
    based on narrative goals, pillars, and constraints.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.reasoning_chain: List[ReasoningStep] = []
        self.step_counter = 0
    
    def _add_reasoning_step(
        self, 
        thought: str, 
        decision: str, 
        confidence: float = 0.8,
        data: Optional[Dict] = None
    ) -> ReasoningStep:
        """Add a step to the reasoning chain"""
        self.step_counter += 1
        step = ReasoningStep(
            step_number=self.step_counter,
            thought=thought,
            decision=decision,
            confidence=confidence,
            data_referenced=data
        )
        self.reasoning_chain.append(step)
        logger.info(f"[Reasoning Step {self.step_counter}] {thought} -> {decision}")
        return step
    
    async def generate_weekly_plan(
        self,
        goal: NarrativeGoal,
        pillars: List[NarrativePillar],
        constraints: SchedulingConstraints,
        available_videos: List[VideoCandidate],
        previous_performance: Optional[PerformanceMetrics] = None,
        learnings: Optional[List[Learning]] = None,
    ) -> WeeklyPlan:
        """
        Generate a complete 7-day content plan with full reasoning.
        
        This is the main entry point for the reasoning engine.
        """
        self.reasoning_chain = []
        self.step_counter = 0
        
        logger.info(f"[NarrativeEngine] Starting plan generation for goal: {goal.goal_statement[:50]}...")
        
        # Phase 1: Context Analysis
        self._add_reasoning_step(
            thought=f"Analyzing narrative goal: '{goal.goal_statement}'. Primary CTA is '{goal.primary_cta}' targeting '{goal.target_audience}'.",
            decision="Load goal context and success metrics for planning",
            data={"goal_id": goal.id, "primary_cta": goal.primary_cta}
        )
        
        # Phase 2: Pillar Analysis
        active_pillars = [p for p in pillars if p.is_active]
        pillar_summary = {p.name: p.target_percentage for p in active_pillars}
        
        self._add_reasoning_step(
            thought=f"Active pillars: {list(pillar_summary.keys())}. Target mix: {pillar_summary}",
            decision=f"Use {len(active_pillars)} pillars for content categorization",
            data={"pillars": pillar_summary}
        )
        
        # Phase 3: Constraint Analysis
        total_slots = self._calculate_total_slots(constraints)
        
        self._add_reasoning_step(
            thought=f"Constraints: {constraints.max_posts_per_day} max/day across {constraints.enabled_platforms}. Min score: {constraints.min_pre_social_score}.",
            decision=f"Planning for {total_slots} total posts over 7 days",
            data={"total_slots": total_slots, "platforms": constraints.enabled_platforms}
        )
        
        # Phase 4: Previous Performance Analysis (if available)
        if previous_performance:
            self._analyze_previous_performance(previous_performance, active_pillars)
        
        # Phase 5: Apply Learnings (if available)
        if learnings:
            self._apply_learnings(learnings)
        
        # Phase 6: Classify Available Content
        classified_videos = await self._classify_videos(available_videos, active_pillars)
        
        # Phase 7: Select Videos
        selected_videos = self._select_videos(
            classified_videos, 
            active_pillars, 
            constraints, 
            total_slots,
            previous_performance
        )
        
        # Phase 8: Generate Schedule
        schedule = self._generate_schedule(
            selected_videos, 
            constraints, 
            active_pillars
        )
        
        # Phase 9: Generate Justification
        justification = self._generate_justification(
            goal, 
            schedule, 
            active_pillars,
            previous_performance
        )
        
        # Create the weekly plan
        week_start = date.today()
        week_end = week_start + timedelta(days=6)
        
        plan = WeeklyPlan(
            goal_id=goal.id,
            week_start=week_start,
            week_end=week_end,
            scheduled_slots=schedule,
            reasoning_chain=self.reasoning_chain,
            total_posts=len(schedule),
            pillar_distribution=self._calculate_pillar_distribution(schedule),
            platform_distribution=self._calculate_platform_distribution(schedule),
            justification_summary=justification,
            status="draft"
        )
        
        logger.info(f"[NarrativeEngine] Plan generated: {plan.total_posts} posts, {len(self.reasoning_chain)} reasoning steps")
        
        return plan
    
    def _calculate_total_slots(self, constraints: SchedulingConstraints) -> int:
        """Calculate total posting slots for 7 days"""
        avg_per_day = (constraints.max_posts_per_day + constraints.min_posts_per_day) // 2
        return avg_per_day * 7
    
    def _analyze_previous_performance(
        self, 
        performance: PerformanceMetrics,
        pillars: List[NarrativePillar]
    ):
        """Analyze previous week's performance and add reasoning"""
        avg_engagement = performance.avg_engagement_rate
        
        # Find top and bottom performing pillars
        pillar_perf = performance.pillar_performance
        if pillar_perf:
            sorted_pillars = sorted(
                pillar_perf.items(),
                key=lambda x: x[1].get('avg_engagement', 0),
                reverse=True
            )
            
            if sorted_pillars:
                top_pillar = sorted_pillars[0]
                bottom_pillar = sorted_pillars[-1]
                
                self._add_reasoning_step(
                    thought=f"Previous week: {performance.total_views} views, {avg_engagement:.1f}% avg engagement. Top pillar: {top_pillar[0]} ({top_pillar[1].get('avg_engagement', 0):.1f}%), Bottom: {bottom_pillar[0]} ({bottom_pillar[1].get('avg_engagement', 0):.1f}%)",
                    decision=f"Increase {top_pillar[0]} allocation, review {bottom_pillar[0]} strategy",
                    confidence=0.85,
                    data={"previous_performance": performance.to_dict()}
                )
    
    def _apply_learnings(self, learnings: List[Learning]):
        """Apply accumulated learnings to planning"""
        applicable = [l for l in learnings if not l.applied and l.confidence > 0.7]
        
        if applicable:
            learning_summary = [l.insight for l in applicable[:3]]
            
            self._add_reasoning_step(
                thought=f"Applying {len(applicable)} learnings from previous schedules: {learning_summary}",
                decision="Incorporate learnings into content selection and scheduling",
                confidence=0.9,
                data={"learnings": [l.to_dict() for l in applicable]}
            )
    
    async def _classify_videos(
        self, 
        videos: List[VideoCandidate],
        pillars: List[NarrativePillar]
    ) -> List[VideoCandidate]:
        """Classify videos into pillars based on analysis"""
        classified = []
        
        for video in videos:
            # Use keywords and analysis to classify
            pillar, confidence = self._match_to_pillar(video, pillars)
            
            video.primary_pillar = pillar.name if pillar else None
            video.pillar_confidence = confidence
            classified.append(video)
        
        # Log classification summary
        pillar_counts = {}
        for v in classified:
            if v.primary_pillar:
                pillar_counts[v.primary_pillar] = pillar_counts.get(v.primary_pillar, 0) + 1
        
        self._add_reasoning_step(
            thought=f"Classified {len(classified)} videos into pillars: {pillar_counts}",
            decision="Proceed with video selection from classified pool",
            data={"classification_summary": pillar_counts}
        )
        
        return classified
    
    def _match_to_pillar(
        self, 
        video: VideoCandidate, 
        pillars: List[NarrativePillar]
    ) -> Tuple[Optional[NarrativePillar], float]:
        """Match a video to the most appropriate pillar"""
        best_pillar = None
        best_score = 0.0
        
        # Combine video metadata for matching
        video_text = " ".join([
            video.title or "",
            video.transcript or "",
            " ".join(video.topics or []),
            " ".join(video.hooks or []),
        ]).lower()
        
        for pillar in pillars:
            score = 0.0
            keyword_matches = 0
            
            for keyword in pillar.keywords:
                if keyword.lower() in video_text:
                    keyword_matches += 1
            
            if pillar.keywords:
                score = keyword_matches / len(pillar.keywords)
            
            if score > best_score:
                best_score = score
                best_pillar = pillar
        
        return best_pillar, min(best_score * 100, 100)
    
    def _select_videos(
        self,
        classified_videos: List[VideoCandidate],
        pillars: List[NarrativePillar],
        constraints: SchedulingConstraints,
        total_slots: int,
        previous_performance: Optional[PerformanceMetrics] = None
    ) -> List[VideoCandidate]:
        """Select videos based on pillar targets and quality scores"""
        selected = []
        
        # Calculate target posts per pillar
        pillar_targets = {}
        for pillar in pillars:
            target_posts = int((pillar.target_percentage / 100) * total_slots)
            pillar_targets[pillar.name] = max(pillar.min_posts_per_week, min(target_posts, pillar.max_posts_per_week))
        
        self._add_reasoning_step(
            thought=f"Target posts per pillar: {pillar_targets}. Total needed: {sum(pillar_targets.values())}",
            decision="Select top-scoring videos for each pillar",
            data={"pillar_targets": pillar_targets}
        )
        
        # Filter by minimum score
        eligible = [v for v in classified_videos if (v.pre_social_score or 0) >= constraints.min_pre_social_score]
        
        self._add_reasoning_step(
            thought=f"{len(eligible)}/{len(classified_videos)} videos meet minimum score threshold of {constraints.min_pre_social_score}",
            decision="Proceed with eligible videos only",
            data={"eligible_count": len(eligible)}
        )
        
        # Select top videos for each pillar
        pillar_selections = {p.name: [] for p in pillars}
        
        for pillar in pillars:
            pillar_videos = [v for v in eligible if v.primary_pillar == pillar.name]
            pillar_videos.sort(key=lambda v: v.pre_social_score or 0, reverse=True)
            
            target = pillar_targets.get(pillar.name, 0)
            for video in pillar_videos[:target]:
                video.is_selected = True
                video.selection_reason = f"Top scorer in {pillar.name} pillar (score: {video.pre_social_score})"
                pillar_selections[pillar.name].append(video)
                selected.append(video)
        
        # Log selection reasoning
        selection_summary = {k: len(v) for k, v in pillar_selections.items()}
        
        self._add_reasoning_step(
            thought=f"Selected {len(selected)} videos across pillars: {selection_summary}",
            decision="Finalize video selection for scheduling",
            confidence=0.9,
            data={"selections": selection_summary}
        )
        
        return selected
    
    def _generate_schedule(
        self,
        selected_videos: List[VideoCandidate],
        constraints: SchedulingConstraints,
        pillars: List[NarrativePillar]
    ) -> List[ScheduledSlot]:
        """Generate the actual schedule with dates and times"""
        schedule = []
        
        # Get posting windows
        windows = constraints.posting_windows or {
            "tiktok": ["12:00", "18:00"],
            "instagram": ["09:00", "17:00"],
            "youtube": ["14:00"]
        }
        
        # Distribute videos across 7 days
        videos_per_day = max(1, len(selected_videos) // 7)
        
        current_date = date.today()
        video_index = 0
        
        for day in range(7):
            day_date = current_date + timedelta(days=day)
            
            if day_date in constraints.blackout_dates:
                continue
            
            # Alternate platforms for the day
            day_platforms = constraints.enabled_platforms.copy()
            
            for slot in range(min(videos_per_day, constraints.max_posts_per_day)):
                if video_index >= len(selected_videos):
                    break
                
                video = selected_videos[video_index]
                platform = day_platforms[slot % len(day_platforms)]
                
                # Get posting time
                platform_windows = windows.get(platform, ["12:00"])
                post_time = platform_windows[slot % len(platform_windows)]
                
                scheduled_slot = ScheduledSlot(
                    video_id=video.id,
                    video_title=video.title,
                    platform=platform,
                    scheduled_date=day_date,
                    scheduled_time=post_time,
                    pillar=video.primary_pillar or "Uncategorized",
                    selection_reason=video.selection_reason or "Selected for schedule",
                    expected_engagement=self._estimate_engagement(video)
                )
                
                schedule.append(scheduled_slot)
                video_index += 1
        
        self._add_reasoning_step(
            thought=f"Generated schedule with {len(schedule)} posts over 7 days",
            decision="Schedule complete and ready for review",
            confidence=0.95,
            data={"schedule_count": len(schedule)}
        )
        
        return schedule
    
    def _estimate_engagement(self, video: VideoCandidate) -> float:
        """Estimate expected engagement based on video score"""
        base_rate = 3.0  # Base engagement rate
        
        if video.pre_social_score:
            # Higher scores get higher expected engagement
            score_bonus = (video.pre_social_score - 60) * 0.05
            return round(base_rate + score_bonus, 2)
        
        return base_rate
    
    def _calculate_pillar_distribution(self, schedule: List[ScheduledSlot]) -> Dict[str, int]:
        """Calculate pillar distribution in schedule"""
        dist = {}
        for slot in schedule:
            dist[slot.pillar] = dist.get(slot.pillar, 0) + 1
        return dist
    
    def _calculate_platform_distribution(self, schedule: List[ScheduledSlot]) -> Dict[str, int]:
        """Calculate platform distribution in schedule"""
        dist = {}
        for slot in schedule:
            dist[slot.platform] = dist.get(slot.platform, 0) + 1
        return dist
    
    def _generate_justification(
        self,
        goal: NarrativeGoal,
        schedule: List[ScheduledSlot],
        pillars: List[NarrativePillar],
        previous_performance: Optional[PerformanceMetrics] = None
    ) -> str:
        """Generate a human-readable justification summary"""
        pillar_dist = self._calculate_pillar_distribution(schedule)
        platform_dist = self._calculate_platform_distribution(schedule)
        
        lines = [
            f"## Schedule Justification",
            f"",
            f"### Goal Alignment",
            f"This schedule is designed to achieve: **{goal.goal_statement}**",
            f"",
            f"Primary call-to-action: **{goal.primary_cta}**",
            f"Target audience: {goal.target_audience}",
            f"",
            f"### Content Distribution",
        ]
        
        for pillar_name, count in pillar_dist.items():
            pct = (count / len(schedule)) * 100 if schedule else 0
            lines.append(f"- **{pillar_name}**: {count} posts ({pct:.0f}%)")
        
        lines.extend([
            f"",
            f"### Platform Strategy",
        ])
        
        for platform, count in platform_dist.items():
            lines.append(f"- **{platform.title()}**: {count} posts")
        
        if previous_performance:
            lines.extend([
                f"",
                f"### Based on Previous Performance",
                f"- Last week's engagement: {previous_performance.avg_engagement_rate:.1f}%",
                f"- Adjustments made based on learnings"
            ])
        
        return "\n".join(lines)
    
    async def generate_reflection(
        self,
        plan: WeeklyPlan,
        performance: PerformanceMetrics,
        goal: NarrativeGoal
    ) -> Dict[str, Any]:
        """
        Generate a reflection on schedule performance.
        
        This analyzes what worked, what didn't, and generates learnings.
        """
        reflection = {
            "period": f"{performance.week_start} to {performance.week_end}",
            "goal_assessment": self._assess_goal_progress(goal, performance),
            "pillar_analysis": self._analyze_pillar_performance(performance),
            "learnings": self._generate_learnings(performance, plan),
            "next_week_adjustments": self._suggest_adjustments(performance, plan)
        }
        
        return reflection
    
    def _assess_goal_progress(
        self, 
        goal: NarrativeGoal, 
        performance: PerformanceMetrics
    ) -> Dict[str, Any]:
        """Assess progress toward narrative goal"""
        assessment = {
            "goal": goal.goal_statement,
            "on_track": True,
            "progress": 0.0
        }
        
        # Check different success metrics
        if goal.target_followers and performance.followers_gained:
            progress = (performance.followers_gained / goal.target_followers) * 100
            assessment["followers_target"] = goal.target_followers
            assessment["followers_achieved"] = performance.followers_gained
            assessment["progress"] = progress
            assessment["on_track"] = progress >= 80
        
        if goal.target_conversions and performance.conversions:
            progress = (performance.conversions / goal.target_conversions) * 100
            assessment["conversions_target"] = goal.target_conversions
            assessment["conversions_achieved"] = performance.conversions
            assessment["progress"] = progress
            assessment["on_track"] = progress >= 80
        
        return assessment
    
    def _analyze_pillar_performance(
        self, 
        performance: PerformanceMetrics
    ) -> List[Dict[str, Any]]:
        """Analyze each pillar's performance"""
        analysis = []
        
        avg_engagement = performance.avg_engagement_rate
        
        for pillar_name, data in performance.pillar_performance.items():
            pillar_engagement = data.get('avg_engagement', 0)
            
            verdict = "ON_TARGET"
            if pillar_engagement > avg_engagement * 1.2:
                verdict = "EXCEEDED"
            elif pillar_engagement < avg_engagement * 0.8:
                verdict = "UNDERPERFORMED"
            
            analysis.append({
                "pillar": pillar_name,
                "posts": data.get('posts', 0),
                "avg_views": data.get('avg_views', 0),
                "avg_engagement": pillar_engagement,
                "verdict": verdict,
                "insight": self._generate_pillar_insight(pillar_name, verdict, data)
            })
        
        return analysis
    
    def _generate_pillar_insight(
        self, 
        pillar: str, 
        verdict: str, 
        data: Dict
    ) -> str:
        """Generate insight for a pillar's performance"""
        if verdict == "EXCEEDED":
            return f"{pillar} content resonated strongly with audience. Consider increasing allocation."
        elif verdict == "UNDERPERFORMED":
            return f"{pillar} content needs adjustment. Review format, messaging, or timing."
        else:
            return f"{pillar} performed as expected. Maintain current strategy."
    
    def _generate_learnings(
        self,
        performance: PerformanceMetrics,
        plan: WeeklyPlan
    ) -> List[Learning]:
        """Generate learnings from schedule performance"""
        learnings = []
        
        # Pillar-based learnings
        for pillar_name, data in performance.pillar_performance.items():
            avg_engagement = data.get('avg_engagement', 0)
            
            if avg_engagement > performance.avg_engagement_rate * 1.3:
                learnings.append(Learning(
                    learning_type="pillar_performance",
                    insight=f"{pillar_name} significantly outperformed average",
                    confidence=0.85,
                    action=f"Increase {pillar_name} allocation by 10%",
                    source_schedule_id=plan.id
                ))
            elif avg_engagement < performance.avg_engagement_rate * 0.7:
                learnings.append(Learning(
                    learning_type="pillar_performance",
                    insight=f"{pillar_name} underperformed significantly",
                    confidence=0.80,
                    action=f"Review {pillar_name} content quality and messaging",
                    source_schedule_id=plan.id
                ))
        
        return learnings
    
    def _suggest_adjustments(
        self,
        performance: PerformanceMetrics,
        plan: WeeklyPlan
    ) -> List[str]:
        """Suggest adjustments for next week's plan"""
        adjustments = []
        
        # Analyze pillar performance
        for pillar_name, data in performance.pillar_performance.items():
            avg_engagement = data.get('avg_engagement', 0)
            
            if avg_engagement > performance.avg_engagement_rate * 1.2:
                current_pct = (plan.pillar_distribution.get(pillar_name, 0) / plan.total_posts) * 100
                adjustments.append(f"Increase {pillar_name} from {current_pct:.0f}% to {min(current_pct + 10, 50):.0f}%")
            elif avg_engagement < performance.avg_engagement_rate * 0.8:
                current_pct = (plan.pillar_distribution.get(pillar_name, 0) / plan.total_posts) * 100
                adjustments.append(f"Reduce {pillar_name} from {current_pct:.0f}% to {max(current_pct - 10, 10):.0f}%")
        
        if not adjustments:
            adjustments.append("Maintain current strategy - performance is on target")
        
        return adjustments

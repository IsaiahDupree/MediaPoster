"""
Content Brief Generator Service (Phase 5)
Generates strategic content briefs using segment insights and AI
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
import os

from database.models import Segment, SegmentInsight, ContentItem, ContentVariant


class ContentBriefGenerator:
    """Generates data-driven content briefs for segments"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.openai_enabled = bool(os.getenv("OPENAI_API_KEY"))
    
    async def generate_organic_brief(
        self,
        segment_id: UUID,
        campaign_goal: str,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate organic content brief for a segment
        
        Args:
            segment_id: Segment UUID
            campaign_goal: Goal (educate, nurture, launch, reactivation)
            time_window_days: Look back window for performance data
            
        Returns:
            Brief dict with strategy, hooks, formats, expected performance
        """
        # Get segment insights
        result = await self.db.execute(
            select(SegmentInsight).where(
                SegmentInsight.segment_id == segment_id,
                SegmentInsight.traffic_type == 'organic'
            )
        )
        insights = result.scalar_one_or_none()
        
        if not insights:
            raise ValueError(f"No organic insights found for segment {segment_id}")
        
        # Get segment name
        result = await self.db.execute(
            select(Segment).where(Segment.id == segment_id)
        )
        segment = result.scalar_one()
        
        # Get top performing content for this segment
        top_content = await self._get_top_performing_content(segment_id, 'organic', time_window_days)
        
        # Build brief structure
        brief = {
            "segment_name": segment.name,
            "created_at": datetime.utcnow().isoformat(),
            "traffic_type": "organic",
            "campaign_goal": campaign_goal,
            
            "segment_snapshot": {
                "who_they_are": self._describe_audience(insights),
                "what_they_care_about": insights.top_topics or [],
                "preferred_platforms": self._rank_platforms(insights.top_platforms or {}),
                "engagement_style": insights.engagement_style or {}
            },
            
            "content_strategy": {
                "hero_topics": insights.top_topics[:5] if insights.top_topics else [],
                "recommended_formats": self._rank_platforms(insights.top_formats or {}),
                "angle_ideas": self._generate_angles(campaign_goal, insights),
                "emotional_levers": self._suggest_emotional_levers(campaign_goal)
            },
            
            "platform_recommendations": {
                "primary_platforms": list((insights.top_platforms or {}).keys())[:3],
                "format_per_platform": self._match_formats_to_platforms(insights),
                "best_times": insights.best_times or {}
            },
            
            "expected_performance": {
                "expected_reach": self._format_range(insights.expected_reach_range),
                "expected_engagement_rate": self._format_range(insights.expected_engagement_rate_range),
                "confidence": "medium",  # Based on data recency/volume
                "based_on": f"Last {time_window_days} days of performance data"
            },
            
            "hook_templates": await self._generate_hook_templates(
                insights, campaign_goal, top_content
            ),
            
            "cta_recommendations": self._suggest_ctas(campaign_goal, insights.engagement_style or {})
        }
        
        return brief
    
    async def generate_paid_brief(
        self,
        segment_id: UUID,
        campaign_goal: str,
        budget_range: Optional[Dict[str, float]] = None,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate paid ads content brief for a segment
        
        Args:
            segment_id: Segment UUID
            campaign_goal: Goal type
            budget_range: Optional budget constraints
            time_window_days: Look back window
            
        Returns:
            Brief dict with ad strategy, audiences, creative guidance, budget
        """
        # Get paid insights
        result = await self.db.execute(
            select(SegmentInsight).where(
                SegmentInsight.segment_id == segment_id,
                SegmentInsight.traffic_type == 'paid'
            )
        )
        insights = result.scalar_one_or_none()
        
        if not insights:
            raise ValueError(f"No paid insights found for segment {segment_id}")
        
        result = await self.db.execute(
            select(Segment).where(Segment.id == segment_id)
        )
        segment = result.scalar_one()
        
        top_content = await self._get_top_performing_content(segment_id, 'paid', time_window_days)
        
        brief = {
            "segment_name": segment.name,
            "created_at": datetime.utcnow().isoformat(),
            "traffic_type": "paid",
            "campaign_goal": campaign_goal,
            
            "audience_targeting": {
                "segment_characteristics": self._describe_audience(insights),
                "recommended_interests": insights.top_topics[:10] if insights.top_topics else [],
                "best_platforms": list((insights.top_platforms or {}).keys())[:3]
            },
            
            "creative_strategy": {
                "proven_formats": self._rank_platforms(insights.top_formats or {}),
                "hook_patterns": self._analyze_successful_hooks(top_content),
                "visual_elements": self._suggest_visual_elements(insights),
                "copy_length": self._suggest_copy_length(insights)
            },
            
            "testing_matrix": {
                "variables_to_test": ["hook", "visual", "cta"],
                "recommended_variants": 3,
                "test_budget_split": "33% / 33% / 34%",
                "winner_criteria": "CTR + Cost per result"
            },
            
            "budget_guidance": {
                "suggested_budget": budget_range or {"min": 50, "max": 500},
                "expected_ctr_range": "1.5% - 3.5%",  # TODO: Pull from actual data
                "expected_cpc_range": "$0.50 - $2.00",
                "frequency_cap": "3 impressions per person per 7 days"
            },
            
            "performance_benchmarks": {
                "historical_ctr": "2.1%",  # TODO: Calculate from metrics
                "historical_cpc": "$1.20",
                "best_performing_objective": campaign_goal
            },
            
            "creative_templates": await self._generate_ad_creative_ideas(
                insights, campaign_goal, top_content
            )
        }
        
        return brief
    
    # Helper methods
    
    def _describe_audience(self, insights: SegmentInsight) -> str:
        """Generate natural language description of audience"""
        topics = insights.top_topics[:3] if insights.top_topics else []
        platforms = list((insights.top_platforms or {}).keys())[:2]
        
        description = f"Audience interested in {', '.join(topics)}" if topics else "Engaged audience"
        if platforms:
            description += f", primarily active on {' and '.join(platforms)}"
        
        return description
    
    def _rank_platforms(self, platform_dict: Dict[str, float]) -> List[Dict[str, Any]]:
        """Rank platforms by score"""
        return [
            {"platform": platform, "score": score}
            for platform, score in sorted(platform_dict.items(), key=lambda x: x[1], reverse=True)
        ]
    
    def _generate_angles(self, goal: str, insights: SegmentInsight) -> List[str]:
        """Generate content angle ideas based on goal"""
        angle_map = {
            "educate": ["How-to guides", "Behind-the-scenes", "Myth busting", "Case studies"],
            "nurture": ["Success stories", "Tips & tricks", "Community highlights", "Value previews"],
            "launch": ["First look", "Problem → Solution", "Transformation stories", "Limited offer"],
            "reactivation": ["What's new", "Missed opportunities", "Exclusive comeback", "Win-back offer"]
        }
        return angle_map.get(goal, ["Educational", "Entertaining", "Inspirational"])
    
    def _suggest_emotional_levers(self, goal: str) -> List[str]:
        """Suggest emotional triggers for goal"""
        lever_map = {
            "educate": ["Curiosity", "Relief", "Confidence"],
            "nurture": ["Hope", "Belonging", "Progress"],
            "launch": ["FOMO", "Excitement", "Exclusivity"],
            "reactivation": ["Nostalgia", "Second chance", "Renewed value"]
        }
        return lever_map.get(goal, ["Interest", "Trust", "Value"])
    
    def _match_formats_to_platforms(self, insights: SegmentInsight) -> Dict[str, List[str]]:
        """Match content formats to platforms"""
        formats = insights.top_formats or {}
        platforms = insights.top_platforms or {}
        
        # Simple heuristics
        mapping = {}
        if "instagram" in platforms:
            mapping["instagram"] = ["reels", "carousels", "stories"]
        if "tiktok" in platforms:
            mapping["tiktok"] = ["short videos", "trends"]
        if "youtube" in platforms:
            mapping["youtube"] = ["long form", "tutorials", "vlogs"]
        if "linkedin" in platforms:
            mapping["linkedin"] = ["text posts", "carousels", "documents"]
        
        return mapping
    
    def _format_range(self, range_str: Optional[str]) -> str:
        """Format postgres range to human readable"""
        if not range_str:
            return "No historical data"
        return range_str  # TODO: Parse and format nicely
    
    async def _generate_hook_templates(
        self,
        insights: SegmentInsight,
        goal: str,
        top_content: List[ContentItem]
    ) -> List[str]:
        """Generate hook templates (TODO: Use AI)"""
        # Simple templates for now
        topics = insights.top_topics[:3] if insights.top_topics else ["your topic"]
        
        templates = [
            f"How to {topics[0]} in [X] simple steps",
            f"The truth about {topics[0] if topics else 'this topic'} that nobody tells you",
            f"I tried {topics[0] if topics else 'this'} for 30 days - here's what happened",
            f"Stop doing {topics[0] if topics else 'this'} wrong - do this instead",
            f"The only {topics[0] if topics else 'guide'} you need in 2025"
        ]
        
        return templates[:5]
    
    def _suggest_ctas(self, goal: str, engagement_style: Dict[str, Any]) -> List[str]:
        """Suggest CTAs based on goal and engagement style"""
        cta_map = {
            "educate": ["Learn more", "Read the guide", "Watch the tutorial"],
            "nurture": ["Join the community", "Get updates", "Try it free"],
            "launch": ["Get early access", "Pre-order now", "Join the waitlist"],
            "reactivation": ["Welcome back", "Claim your offer", "See what's new"]
        }
        return cta_map.get(goal, ["Click to learn more", "Get started", "Join now"])
    
    async def _get_top_performing_content(
        self,
        segment_id: UUID,
        traffic_type: str,
        days: int
    ) -> List[ContentItem]:
        """Get top performing content for segment"""
        # TODO: Implement actual segment-content performance linking
        # For now, return empty list
        return []
    
    def _analyze_successful_hooks(self, top_content: List[ContentItem]) -> List[str]:
        """Analyze hooks from successful content"""
        # TODO: Extract and analyze hooks from top content
        return ["Pattern 1: Question-based", "Pattern 2: Bold statement", "Pattern 3: Story opening"]
    
    def _suggest_visual_elements(self, insights: SegmentInsight) -> List[str]:
        """Suggest visual elements for ads"""
        return ["Faces/people", "Product in use", "Before/after", "Text overlay"]
    
    def _suggest_copy_length(self, insights: SegmentInsight) -> str:
        """Suggest ad copy length"""
        # TODO: Analyze from historical data
        return "Short (50-75 words) for feed, Long (100-150) for detail-oriented audiences"
    
    async def _generate_ad_creative_ideas(
        self,
        insights: SegmentInsight,
        goal: str,
        top_content: List[ContentItem]
    ) -> List[Dict[str, str]]:
        """Generate ad creative concepts"""
        topics = insights.top_topics[:3] if insights.top_topics else ["your offering"]
        
        return [
            {
                "concept": f"Problem/Solution: {topics[0]}",
                "hook": f"Struggling with {topics[0]}? Here's the fix.",
                "visual": "Split screen: problem vs solution",
                "cta": "Learn how"
            },
            {
                "concept": "Social proof",
                "hook": f"Join 10,000+ who mastered {topics[0]}",
                "visual": "Customer testimonial or results",
                "cta": "Get started"
            },
            {
                "concept": "Value proposition",
                "hook": f"{topics[0]} made simple",
                "visual": "Product/service in action",
                "cta": "Try now"
            }
        ]

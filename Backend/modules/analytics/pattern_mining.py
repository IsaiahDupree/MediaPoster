"""
Pattern Mining Engine - Extract insights from video analysis data
Analyzes hooks, visuals, CTAs, and retention to find winning patterns
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy import func, and_, desc
from loguru import logger

from database.models.video_analysis import (
    Video, VideoSegment, VideoFrame, VideoTag, 
    VideoPerformanceCheckback, VideoWord
)


@dataclass
class Pattern:
    """A discovered performance pattern"""
    pattern_type: str  # hook, cta, visual, timing
    title: str
    description: str
    impact_metric: str  # retention, engagement, cta_response
    impact_value: float  # Numeric improvement
    confidence: float  # 0-1
    sample_size: int
    examples: List[str]  # Video IDs
    recommendation: str


@dataclass
class Insight:
    """Actionable insight derived from patterns"""
    insight_type: str  # pattern, warning, opportunity, experiment
    title: str
    description: str
    nsm_affected: str  # engaged_reach, cls, warm_leads
    action_buttons: List[Dict[str, str]]
    confidence: float


class PatternMiningEngine:
    """Mine video analysis data for performance patterns"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.min_sample_size = 3
    
    def analyze_hook_patterns(self) -> List[Pattern]:
        """
        Find best-performing hook characteristics
        
        Analyzes:
        - Hook type (pain, curiosity, aspirational, etc.)
        - Visual type (talking head, screen record)
        - Voice tone
        - On-screen text presence
        
        Returns:
            List of hook patterns with performance data
        """
        logger.info("Analyzing hook patterns...")
        
        # Query hook segments with performance
        query = self.db.query(
            VideoSegment.hook_type,
            VideoFrame.shot_type,
            VideoTag.voice_tone,
            func.count(VideoSegment.id).label('count'),
            func.avg(VideoPerformanceCheckback.avg_watch_pct).label('avg_retention'),
            func.avg(VideoPerformanceCheckback.engagement_rate).label('avg_engagement')
        ).join(
            VideoFrame, 
            and_(
                VideoFrame.segment_id == VideoSegment.id,
                VideoFrame.frame_time_s < 3  # First 3 seconds
            )
        ).join(
            VideoTag,
            VideoTag.video_id == VideoSegment.video_id
        ).join(
            VideoPerformanceCheckback,
            and_(
                VideoPerformanceCheckback.video_id == VideoSegment.video_id,
                VideoPerformanceCheckback.checkback_hours == 24
            )
        ).filter(
            VideoSegment.segment_type == 'hook',
            VideoSegment.hook_type.isnot(None)
        ).group_by(
            VideoSegment.hook_type,
            VideoFrame.shot_type,
            VideoTag.voice_tone
        ).having(
            func.count(VideoSegment.id) >= self.min_sample_size
        ).order_by(
            desc('avg_retention')
        )
        
        results = query.all()
        
        patterns = []
        overall_avg_retention = self._get_overall_avg_retention()
        
        for result in results:
            if result.avg_retention > overall_avg_retention:
                improvement = ((result.avg_retention - overall_avg_retention) / overall_avg_retention) * 100
                
                pattern = Pattern(
                    pattern_type='hook',
                    title=f"{result.hook_type.replace('_', ' ').title()} + {result.shot_type.replace('_', ' ').title()}",
                    description=f"Hooks with {result.hook_type} type and {result.shot_type} visual have {improvement:+.0f}% higher retention",
                    impact_metric='retention',
                    impact_value=improvement,
                    confidence=min(result.count / 10, 1.0),  # More samples = higher confidence
                    sample_size=result.count,
                    examples=[],  # TODO: Fetch example video IDs
                    recommendation=f"Use {result.hook_type} hooks with {result.shot_type} framing in your next videos"
                )
                patterns.append(pattern)
        
        logger.success(f"Found {len(patterns)} hook patterns")
        return patterns
    
    def analyze_cta_effectiveness(self) -> List[Pattern]:
        """
        Find best CTA structures
        
        Analyzes:
        - CTA type (conversion, engagement, open-loop)
        - CTA mechanic (comment keyword, link, etc.)
        - CTA timing (when in video)
        
        Returns:
            List of CTA patterns
        """
        logger.info("Analyzing CTA effectiveness...")
        
        # Query CTA segments with keyword response rates
        query = self.db.query(
            VideoSegment.cta_type,
            VideoSegment.cta_mechanic,
            func.count(VideoSegment.id).label('count'),
            func.avg(
                func.cast(VideoPerformanceCheckback.keyword_response_count, func.Float()) / 
                func.nullif(VideoPerformanceCheckback.views, 0)
            ).label('avg_cta_rate'),
            func.sum(VideoPerformanceCheckback.link_clicks).label('total_clicks')
        ).join(
            VideoPerformanceCheckback,
            and_(
                VideoPerformanceCheckback.video_id == VideoSegment.video_id,
                VideoPerformanceCheckback.checkback_hours == 24
            )
        ).filter(
            VideoSegment.segment_type == 'cta',
            VideoSegment.cta_type.isnot(None)
        ).group_by(
            VideoSegment.cta_type,
            VideoSegment.cta_mechanic
        ).having(
            func.count(VideoSegment.id) >= self.min_sample_size
        ).order_by(
            desc('avg_cta_rate')
        )
        
        results = query.all()
        
        patterns = []
        overall_avg_cta = self._get_overall_avg_cta_rate()
        
        for result in results:
            if result.avg_cta_rate and result.avg_cta_rate > overall_avg_cta:
                multiplier = result.avg_cta_rate / overall_avg_cta if overall_avg_cta > 0 else 1
                
                pattern = Pattern(
                    pattern_type='cta',
                    title=f"{result.cta_type.replace('_', ' ').title()} CTA via {result.cta_mechanic.replace('_', ' ')}",
                    description=f"CTAs using {result.cta_mechanic} have {multiplier:.1f}x higher response rate",
                    impact_metric='cta_response',
                    impact_value=(multiplier - 1) * 100,
                    confidence=min(result.count / 10, 1.0),
                    sample_size=result.count,
                    examples=[],
                    recommendation=f"Use {result.cta_mechanic} for your CTAs instead of links"
                )
                patterns.append(pattern)
        
        logger.success(f"Found {len(patterns)} CTA patterns")
        return patterns
    
    def analyze_retention_drops(self) -> List[Pattern]:
        """
        Find what causes retention drops
        
        Analyzes correlation between:
        - Visual changes (face → no face, clean → cluttered)
        - Content complexity
        - Pacing changes
        
        Returns:
            List of retention drop patterns
        """
        logger.info("Analyzing retention drop patterns...")
        
        # This is complex - would need to analyze retention_curve JSON
        # and correlate with frame changes
        
        # Simplified: Find common characteristics of low-retention videos
        query = self.db.query(
            VideoFrame.shot_type,
            VideoFrame.visual_clutter_score,
            VideoFrame.face_detected,
            func.count(VideoFrame.id).label('count'),
            func.avg(VideoPerformanceCheckback.avg_watch_pct).label('avg_retention')
        ).join(
            VideoPerformanceCheckback,
            and_(
                VideoPerformanceCheckback.video_id == VideoFrame.video_id,
                VideoPerformanceCheckback.checkback_hours == 24
            )
        ).filter(
            VideoFrame.frame_time_s.between(3, 10)  # Context/early body section
        ).group_by(
            VideoFrame.shot_type,
            VideoFrame.visual_clutter_score,
            VideoFrame.face_detected
        ).having(
            func.count(VideoFrame.id) >= self.min_sample_size
        )
        
        results = query.all()
        
        overall_avg = self._get_overall_avg_retention()
        
        patterns = []
        for result in results:
            if result.avg_retention < overall_avg * 0.9:  # 10% below average
                drop = ((overall_avg - result.avg_retention) / overall_avg) * 100
                
                visual_desc = "cluttered screen" if result.visual_clutter_score > 0.6 else "clean visual"
                face_desc = "with face" if result.face_detected else "without face"
                
                pattern = Pattern(
                    pattern_type='visual',
                    title=f"Performance Warning: {result.shot_type.replace('_', ' ').title()}",
                    description=f"{result.shot_type} {visual_desc} {face_desc} underperforms by {drop:.0f}%",
                    impact_metric='retention',
                    impact_value=-drop,
                    confidence=min(result.count / 10, 1.0),
                    sample_size=result.count,
                    examples=[],
                    recommendation=f"Avoid {result.shot_type} with high clutter and no face in first 10 seconds"
                )
                patterns.append(pattern)
        
        logger.success(f"Found {len(patterns)} retention drop patterns")
        return patterns
    
    def analyze_posting_timing(self) -> List[Pattern]:
        """
        Find best posting times
        
        Analyzes:
        - Day of week performance
        - Time of day performance
        - Posting consistency
        
        Returns:
            List of timing patterns
        """
        logger.info("Analyzing posting timing patterns...")
        
        # Get posts with their publish times and performance
        posts = self.db.query(
            Video,
            VideoPerformanceCheckback
        ).join(
            VideoPerformanceCheckback,
            and_(
                VideoPerformanceCheckback.video_id == Video.id,
                VideoPerformanceCheckback.checkback_hours == 24
            )
        ).filter(
            Video.created_at.isnot(None)
        ).all()
        
        # Group by day of week and hour
        day_hour_performance = {}
        
        for video, checkback in posts:
            day_of_week = video.created_at.strftime('%A')
            hour = video.created_at.hour
            
            key = (day_of_week, hour // 3 * 3)  # 3-hour buckets
            
            if key not in day_hour_performance:
                day_hour_performance[key] = []
            
            # Use Content Leverage Score as metric
            engagement = (
                checkback.comments + checkback.saves + 
                checkback.shares + checkback.profile_taps
            )
            day_hour_performance[key].append(engagement)
        
        # Find best performing time slots
        patterns = []
        overall_avg_engagement = sum(
            sum(values) for values in day_hour_performance.values()
        ) / sum(len(values) for values in day_hour_performance.values()) if day_hour_performance else 0
        
        for (day, hour), engagements in day_hour_performance.items():
            if len(engagements) >= self.min_sample_size:
                avg_engagement = sum(engagements) / len(engagements)
                
                if avg_engagement > overall_avg_engagement * 1.2:  # 20% above average
                    improvement = ((avg_engagement - overall_avg_engagement) / overall_avg_engagement) * 100
                    
                    pattern = Pattern(
                        pattern_type='timing',
                        title=f"Optimal Time: {day} {hour}:00-{hour+3}:00",
                        description=f"Posts on {day} between {hour}:00-{hour+3}:00 perform {improvement:.0f}% better",
                        impact_metric='engagement',
                        impact_value=improvement,
                        confidence=min(len(engagements) / 10, 1.0),
                        sample_size=len(engagements),
                        examples=[],
                        recommendation=f"Schedule more posts for {day} {hour}:00-{hour+3}:00"
                    )
                    patterns.append(pattern)
        
        logger.success(f"Found {len(patterns)} timing patterns")
        return patterns
    
    def generate_insights(self) -> List[Insight]:
        """
        Generate actionable insights from all patterns
        
        Returns:
            List of insights with recommendations
        """
        logger.info("Generating insights...")
        
        insights = []
        
        # Analyze all pattern types
        hook_patterns = self.analyze_hook_patterns()
        cta_patterns = self.analyze_cta_effectiveness()
        retention_patterns = self.analyze_retention_drops()
        timing_patterns = self.analyze_posting_timing()
        
        # Convert patterns to insights
        for pattern in hook_patterns[:3]:  # Top 3
            insight = Insight(
                insight_type='pattern',
                title=f"🎯 {pattern.title}",
                description=f"{pattern.description}. Based on {pattern.sample_size} videos.",
                nsm_affected='content_leverage_score',
                action_buttons=[
                    {'label': 'Generate hook ideas', 'action': 'generate_hooks', 'params': {'type': pattern.pattern_type}},
                    {'label': 'See examples', 'action': 'show_examples', 'params': {'pattern_id': pattern.pattern_type}}
                ],
                confidence=pattern.confidence
            )
            insights.append(insight)
        
        for pattern in cta_patterns[:2]:  # Top 2
            insight = Insight(
                insight_type='pattern',
                title=f"💡 {pattern.title}",
                description=f"{pattern.description}. {pattern.recommendation}.",
                nsm_affected='warm_lead_flow',
                action_buttons=[
                    {'label': 'Apply to scheduled posts', 'action': 'apply_cta_pattern'},
                    {'label': 'Regenerate CTA', 'action': 'regenerate_cta'}
                ],
                confidence=pattern.confidence
            )
            insights.append(insight)
        
        for pattern in retention_patterns[:2]:  # Top 2 warnings
            insight = Insight(
                insight_type='warning',
                title=f"⚠️ {pattern.title}",
                description=f"{pattern.description}. {pattern.recommendation}.",
                nsm_affected='engaged_reach',
                action_buttons=[
                    {'label': 'See underperforming posts', 'action': 'filter_posts', 'params': {'pattern': 'low_retention'}}
                ],
                confidence=pattern.confidence
            )
            insights.append(insight)
        
        for pattern in timing_patterns[:1]:  # Top 1
            insight = Insight(
                insight_type='opportunity',
                title=f"⏰ {pattern.title}",
                description=f"{pattern.description}. Consider scheduling more content in this window.",
                nsm_affected='content_leverage_score',
                action_buttons=[
                    {'label': 'Auto-schedule to this window', 'action': 'auto_schedule', 'params': {'timing': 'optimal'}}
                ],
                confidence=pattern.confidence
            )
            insights.append(insight)
        
        logger.success(f"Generated {len(insights)} insights")
        return insights
    
    def _get_overall_avg_retention(self) -> float:
        """Get overall average retention across all videos"""
        result = self.db.query(
            func.avg(VideoPerformanceCheckback.avg_watch_pct)
        ).filter(
            VideoPerformanceCheckback.checkback_hours == 24
        ).scalar()
        
        return result or 0.0
    
    def _get_overall_avg_cta_rate(self) -> float:
        """Get overall average CTA response rate"""
        result = self.db.query(
            func.avg(
                func.cast(VideoPerformanceCheckback.keyword_response_count, func.Float()) / 
                func.nullif(VideoPerformanceCheckback.views, 0)
            )
        ).filter(
            VideoPerformanceCheckback.checkback_hours == 24,
            VideoPerformanceCheckback.keyword_response_count > 0
        ).scalar()
        
        return result or 0.0


# Example usage
if __name__ == '__main__':
    from database.database import get_db
    
    db = next(get_db())
    engine = PatternMiningEngine(db)
    
    logger.info("\n" + "="*80)
    logger.info("PATTERN MINING ENGINE TEST")
    logger.info("="*80 + "\n")
    
    insights = engine.generate_insights()
    
    if insights:
        logger.info(f"\nGenerated {len(insights)} insights:\n")
        
        for i, insight in enumerate(insights, 1):
            logger.info(f"{i}. {insight.title}")
            logger.info(f"   {insight.description}")
            logger.info(f"   NSM affected: {insight.nsm_affected}")
            logger.info(f"   Confidence: {insight.confidence:.0%}")
            logger.info(f"   Actions: {[btn['label'] for btn in insight.action_buttons]}")
            logger.info("")
    else:
        logger.warning("No insights generated - need more video analysis data")
    
    logger.info("="*80)

"""
North Star Metrics calculation and analytics backend
"""
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from database.models.video_analysis import Video, VideoSegment, VideoPerformanceCheckback


@dataclass
class NorthStarMetrics:
    """North Star Metrics for organic growth"""
    weekly_engaged_reach: int
    content_leverage_score: float
    warm_lead_flow: int
    
    # Comparisons
    weekly_engaged_reach_change: float  # % vs last week
    content_leverage_score_change: float
    warm_lead_flow_change: float
    
    # Trends
    weekly_engaged_reach_trend: List[Dict[str, Any]]
    content_leverage_score_trend: List[Dict[str, Any]]
    warm_lead_flow_trend: List[Dict[str, Any]]


class NorthStarMetricsCalculator:
    """Calculate and track North Star Metrics"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def calculate_weekly_engaged_reach(
        self, 
        start_date: Optional[datetime] = None
    ) -> int:
        """
        NSM #1: Weekly Engaged Reach
        
        Unique people who meaningfully engaged
        (comments + saves + shares + profile_taps + link_clicks, de-duped)
        
        Args:
            start_date: Start of week (defaults to last 7 days)
            
        Returns:
            Engaged reach count
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        
        # Query checkbacks from the week
        result = self.db.query(
            func.sum(VideoPerformanceCheckback.comments).label('comments'),
            func.sum(VideoPerformanceCheckback.saves).label('saves'),
            func.sum(VideoPerformanceCheckback.shares).label('shares'),
            func.sum(VideoPerformanceCheckback.profile_taps).label('profile_taps'),
            func.sum(VideoPerformanceCheckback.link_clicks).label('link_clicks')
        ).filter(
            VideoPerformanceCheckback.checked_at >= start_date,
            VideoPerformanceCheckback.checkback_hours == 24  # Use 24h checkback
        ).first()
        
        if not result:
            return 0
        
        # Sum unique engagements (simplified - in reality need de-duping)
        engaged_reach = (
            (result.comments or 0) +
            (result.saves or 0) +
            (result.shares or 0) +
            (result.profile_taps or 0) +
            (result.link_clicks or 0)
        )
        
        return int(engaged_reach)
    
    def calculate_content_leverage_score(
        self, 
        start_date: Optional[datetime] = None,
        days: int = 30
    ) -> float:
        """
        NSM #2: Content Leverage Score
        
        Meaningful engagements per post
        (comments + saves + shares + profile_taps) / posts_published
        
        Args:
            start_date: Start date
            days: Number of days to analyze
            
        Returns:
            Content Leverage Score
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get post count and engagement totals
        result = self.db.query(
            func.count(VideoPerformanceCheckback.id).label('posts'),
            func.sum(VideoPerformanceCheckback.comments).label('comments'),
            func.sum(VideoPerformanceCheckback.saves).label('saves'),
            func.sum(VideoPerformanceCheckback.shares).label('shares'),
            func.sum(VideoPerformanceCheckback.profile_taps).label('profile_taps')
        ).filter(
            VideoPerformanceCheckback.checked_at >= start_date,
            VideoPerformanceCheckback.checkback_hours == 24
        ).first()
        
        if not result or not result.posts:
            return 0.0
        
        engagements = (
            (result.comments or 0) +
            (result.saves or 0) +
            (result.shares or 0) +
            (result.profile_taps or 0)
        )
        
        cls = engagements / result.posts
        return round(cls, 2)
    
    def calculate_warm_lead_flow(
        self, 
        start_date: Optional[datetime] = None
    ) -> int:
        """
        NSM #3: Warm Lead Flow
        
        Actions moving people toward funnel
        link_clicks + DM_starts + email_signups
        
        Args:
            start_date: Start of week
            
        Returns:
            Warm lead count
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        
        result = self.db.query(
            func.sum(VideoPerformanceCheckback.link_clicks).label('link_clicks')
            # TODO: Add DM tracking, email signup tracking
        ).filter(
            VideoPerformanceCheckback.checked_at >= start_date,
            VideoPerformanceCheckback.checkback_hours == 24
        ).first()
        
        if not result:
            return 0
        
        warm_leads = result.link_clicks or 0
        # TODO: Add DM_starts, email_signups when available
        
        return int(warm_leads)
    
    def get_all_metrics(self) -> NorthStarMetrics:
        """Get all North Star Metrics with trends"""
        
        # Current week
        this_week_start = datetime.utcnow() - timedelta(days=7)
        last_week_start = datetime.utcnow() - timedelta(days=14)
        
        # Calculate current metrics
        weekly_engaged_reach = self.calculate_weekly_engaged_reach(this_week_start)
        content_leverage_score = self.calculate_content_leverage_score(days=30)
        warm_lead_flow = self.calculate_warm_lead_flow(this_week_start)
        
        # Calculate previous period for comparison
        prev_engaged_reach = self.calculate_weekly_engaged_reach(last_week_start)
        prev_cls = self.calculate_content_leverage_score(
            start_date=datetime.utcnow() - timedelta(days=60), 
            days=30
        )
        prev_warm_leads = self.calculate_warm_lead_flow(last_week_start)
        
        # Calculate % changes
        engaged_reach_change = self._percent_change(prev_engaged_reach, weekly_engaged_reach)
        cls_change = self._percent_change(prev_cls, content_leverage_score)
        warm_lead_change = self._percent_change(prev_warm_leads, warm_lead_flow)
        
        # Generate trends (last 8 weeks)
        engaged_reach_trend = self._generate_trend('engaged_reach', weeks=8)
        cls_trend = self._generate_trend('cls', weeks=8)
        warm_lead_trend = self._generate_trend('warm_leads', weeks=8)
        
        return NorthStarMetrics(
            weekly_engaged_reach=weekly_engaged_reach,
            content_leverage_score=content_leverage_score,
            warm_lead_flow=warm_lead_flow,
            weekly_engaged_reach_change=engaged_reach_change,
            content_leverage_score_change=cls_change,
            warm_lead_flow_change=warm_lead_change,
            weekly_engaged_reach_trend=engaged_reach_trend,
            content_leverage_score_trend=cls_trend,
            warm_lead_flow_trend=warm_lead_trend
        )
    
    def _percent_change(self, old_value: float, new_value: float) -> float:
        """Calculate percent change"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        
        change = ((new_value - old_value) / old_value) * 100
        return round(change, 1)
    
    def _generate_trend(self, metric: str, weeks: int = 8) -> List[Dict[str, Any]]:
        """Generate weekly trend data"""
        trend = []
        
        for week in range(weeks, 0, -1):
            week_start = datetime.utcnow() - timedelta(days=week*7)
            week_end = week_start + timedelta(days=7)
            
            if metric == 'engaged_reach':
                value = self.calculate_weekly_engaged_reach(week_start)
            elif metric == 'cls':
                value = self.calculate_content_leverage_score(week_start, days=7)
            elif metric == 'warm_leads':
                value = self.calculate_warm_lead_flow(week_start)
            else:
                value = 0
            
            trend.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'value': value
            })
        
        return trend


# Example usage
if __name__ == '__main__':
    from database.database import get_db
    
    db = next(get_db())
    calculator = NorthStarMetricsCalculator(db)
    
    metrics = calculator.get_all_metrics()
    
    print("North Star Metrics")
    print("==================")
    print(f"\nWeekly Engaged Reach: {metrics.weekly_engaged_reach:,}")
    print(f"  Change: {metrics.weekly_engaged_reach_change:+.1f}%")
    
    print(f"\nContent Leverage Score: {metrics.content_leverage_score}")
    print(f"  Change: {metrics.content_leverage_score_change:+.1f}%")
    
    print(f"\nWarm Lead Flow: {metrics.warm_lead_flow:,}")
    print(f"  Change: {metrics.warm_lead_flow_change:+.1f}%")
    
    print("\nTrends:")
    print(f"  Engaged Reach: {len(metrics.weekly_engaged_reach_trend)} weeks")
    print(f"  CLS: {len(metrics.content_leverage_score_trend)} weeks")
    print(f"  Warm Leads: {len(metrics.warm_lead_flow_trend)} weeks")

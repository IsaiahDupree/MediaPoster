"""
Optimal Timing Service
SS-007: Suggests optimal posting times based on audience engagement patterns
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import statistics

class DayOfWeek(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class TimeSlot:
    """Represents a posting time slot with engagement score"""
    hour: int  # 0-23
    day_of_week: DayOfWeek
    engagement_score: float  # 0-100
    avg_views: int
    avg_likes: int
    sample_size: int


@dataclass
class OptimalTimeRecommendation:
    """Recommendation for optimal posting time"""
    datetime: datetime
    platform: str
    confidence: float  # 0-1
    expected_engagement: float
    reason: str


class OptimalTimingService:
    """
    Analyzes historical engagement data to suggest optimal posting times.
    Uses platform-specific patterns and user's historical performance.
    """
    
    # Default engagement patterns by platform (hour -> relative score)
    # Based on general social media research
    DEFAULT_PATTERNS = {
        'tiktok': {
            # Peak times: 7-9am, 12-3pm, 7-11pm
            7: 75, 8: 85, 9: 80,
            12: 90, 13: 95, 14: 85, 15: 80,
            19: 100, 20: 98, 21: 95, 22: 85, 23: 70,
            # Off-peak
            0: 30, 1: 20, 2: 15, 3: 10, 4: 15, 5: 25, 6: 50,
            10: 65, 11: 70, 16: 70, 17: 75, 18: 85,
        },
        'instagram': {
            # Peak times: 6-9am, 12-2pm, 5-9pm
            6: 70, 7: 85, 8: 90, 9: 80,
            12: 95, 13: 90, 14: 75,
            17: 85, 18: 95, 19: 100, 20: 90, 21: 75,
            # Off-peak
            0: 25, 1: 15, 2: 10, 3: 10, 4: 15, 5: 40,
            10: 60, 11: 70, 15: 65, 16: 75, 22: 55, 23: 40,
        },
        'youtube': {
            # Peak times: 12-4pm, 7-10pm (weekdays), flexible weekends
            12: 80, 13: 85, 14: 90, 15: 95, 16: 85,
            19: 95, 20: 100, 21: 90, 22: 75,
            # Off-peak
            0: 35, 1: 25, 2: 20, 3: 15, 4: 15, 5: 20, 6: 30,
            7: 45, 8: 55, 9: 60, 10: 65, 11: 70,
            17: 75, 18: 85, 23: 50,
        },
        'twitter': {
            # Peak times: 8-10am, 12-1pm, 5-6pm
            8: 90, 9: 95, 10: 85,
            12: 100, 13: 85,
            17: 95, 18: 90,
            # Off-peak
            0: 30, 1: 20, 2: 15, 3: 10, 4: 15, 5: 25, 6: 45, 7: 70,
            11: 75, 14: 70, 15: 65, 16: 75, 19: 70, 20: 60, 21: 50, 22: 40, 23: 35,
        },
        'linkedin': {
            # Peak times: 7-8am, 12pm, 5-6pm (business hours)
            7: 90, 8: 95, 9: 80,
            12: 100,
            17: 95, 18: 85,
            # Off-peak (very low on weekends)
            0: 10, 1: 5, 2: 5, 3: 5, 4: 5, 5: 15, 6: 50,
            10: 70, 11: 75, 13: 70, 14: 65, 15: 60, 16: 70,
            19: 50, 20: 35, 21: 25, 22: 15, 23: 10,
        },
        'threads': {
            # Similar to Instagram
            6: 65, 7: 80, 8: 85, 9: 75,
            12: 90, 13: 85, 14: 70,
            17: 80, 18: 90, 19: 100, 20: 95, 21: 80,
            0: 25, 1: 15, 2: 10, 3: 10, 4: 15, 5: 35,
            10: 55, 11: 65, 15: 60, 16: 70, 22: 60, 23: 45,
        },
    }
    
    # Weekend modifiers (multiply score by this)
    WEEKEND_MODIFIERS = {
        'tiktok': 1.1,      # Better on weekends
        'instagram': 1.15,  # Much better on weekends
        'youtube': 1.2,     # Great on weekends
        'twitter': 0.85,    # Slightly worse
        'linkedin': 0.3,    # Much worse on weekends
        'threads': 1.1,     # Better on weekends
    }

    def __init__(self):
        self.historical_data: Dict[str, List[TimeSlot]] = {}
        self.user_timezone: str = 'America/New_York'
    
    def set_timezone(self, timezone: str):
        """Set user's timezone for recommendations"""
        self.user_timezone = timezone
    
    def add_historical_data(
        self,
        platform: str,
        posted_at: datetime,
        views: int,
        likes: int,
        comments: int = 0,
        shares: int = 0
    ):
        """Add historical post performance data"""
        if platform not in self.historical_data:
            self.historical_data[platform] = []
        
        # Calculate engagement score
        engagement = self._calculate_engagement(views, likes, comments, shares)
        
        slot = TimeSlot(
            hour=posted_at.hour,
            day_of_week=DayOfWeek(posted_at.weekday()),
            engagement_score=engagement,
            avg_views=views,
            avg_likes=likes,
            sample_size=1
        )
        self.historical_data[platform].append(slot)
    
    def _calculate_engagement(
        self,
        views: int,
        likes: int,
        comments: int = 0,
        shares: int = 0
    ) -> float:
        """Calculate weighted engagement score"""
        if views == 0:
            return 0
        
        # Weighted engagement rate
        engagement_rate = (
            (likes * 1.0) + 
            (comments * 2.0) + 
            (shares * 3.0)
        ) / views * 100
        
        # Normalize to 0-100 scale (assuming 10% is excellent)
        return min(100, engagement_rate * 10)
    
    def get_platform_score(self, platform: str, hour: int, day: DayOfWeek) -> float:
        """Get engagement score for a specific time slot"""
        platform_lower = platform.lower()
        
        # Get base score from default patterns
        if platform_lower in self.DEFAULT_PATTERNS:
            base_score = self.DEFAULT_PATTERNS[platform_lower].get(hour, 50)
        else:
            base_score = 50
        
        # Apply weekend modifier
        is_weekend = day in (DayOfWeek.SATURDAY, DayOfWeek.SUNDAY)
        if is_weekend and platform_lower in self.WEEKEND_MODIFIERS:
            base_score *= self.WEEKEND_MODIFIERS[platform_lower]
        
        # Blend with historical data if available
        if platform_lower in self.historical_data:
            historical_slots = [
                s for s in self.historical_data[platform_lower]
                if s.hour == hour and s.day_of_week == day
            ]
            if historical_slots:
                historical_avg = statistics.mean(s.engagement_score for s in historical_slots)
                # Weight: 70% historical, 30% default
                base_score = (historical_avg * 0.7) + (base_score * 0.3)
        
        return min(100, max(0, base_score))
    
    def get_optimal_times(
        self,
        platform: str,
        start_date: Optional[datetime] = None,
        num_slots: int = 5,
        min_gap_hours: int = 4
    ) -> List[OptimalTimeRecommendation]:
        """
        Get optimal posting times for the next week.
        
        Args:
            platform: Target platform
            start_date: Starting date (default: now)
            num_slots: Number of time slots to return
            min_gap_hours: Minimum hours between recommendations
        
        Returns:
            List of optimal time recommendations sorted by score
        """
        start = start_date or datetime.utcnow()
        recommendations = []
        
        # Score all time slots for the next 7 days
        all_slots: List[Tuple[datetime, float]] = []
        
        for day_offset in range(7):
            check_date = start + timedelta(days=day_offset)
            day_of_week = DayOfWeek(check_date.weekday())
            
            for hour in range(24):
                slot_time = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # Skip past times
                if slot_time <= start:
                    continue
                
                score = self.get_platform_score(platform, hour, day_of_week)
                all_slots.append((slot_time, score))
        
        # Sort by score descending
        all_slots.sort(key=lambda x: x[1], reverse=True)
        
        # Select top slots with minimum gap
        selected_times: List[datetime] = []
        
        for slot_time, score in all_slots:
            # Check gap from all selected times
            too_close = False
            for selected in selected_times:
                gap = abs((slot_time - selected).total_seconds() / 3600)
                if gap < min_gap_hours:
                    too_close = True
                    break
            
            if not too_close:
                selected_times.append(slot_time)
                
                # Determine confidence based on score and data availability
                confidence = score / 100
                if platform.lower() in self.historical_data:
                    sample_size = len(self.historical_data[platform.lower()])
                    if sample_size > 20:
                        confidence = min(0.95, confidence * 1.2)
                    elif sample_size > 5:
                        confidence = min(0.85, confidence * 1.1)
                
                recommendations.append(OptimalTimeRecommendation(
                    datetime=slot_time,
                    platform=platform,
                    confidence=confidence,
                    expected_engagement=score,
                    reason=self._generate_reason(slot_time, platform, score)
                ))
                
                if len(recommendations) >= num_slots:
                    break
        
        return recommendations
    
    def _generate_reason(self, slot_time: datetime, platform: str, score: float) -> str:
        """Generate human-readable reason for recommendation"""
        hour = slot_time.hour
        day_name = slot_time.strftime('%A')
        
        reasons = []
        
        # Time of day context
        if 6 <= hour < 12:
            reasons.append("morning audience engagement")
        elif 12 <= hour < 17:
            reasons.append("afternoon peak activity")
        elif 17 <= hour < 21:
            reasons.append("evening prime time")
        else:
            reasons.append("late night engaged users")
        
        # Platform-specific
        platform_lower = platform.lower()
        if platform_lower == 'tiktok' and 19 <= hour <= 22:
            reasons.append("TikTok peak discovery hours")
        elif platform_lower == 'linkedin' and hour in (7, 8, 12, 17, 18):
            reasons.append("business hours optimal for LinkedIn")
        elif platform_lower in ('instagram', 'threads') and slot_time.weekday() >= 5:
            reasons.append("weekend browsing spike")
        
        # Score context
        if score >= 90:
            reasons.append("historically top-performing slot")
        elif score >= 75:
            reasons.append("strong engagement expected")
        
        return f"Recommended for {day_name}: " + ", ".join(reasons[:2])
    
    def get_best_time_today(self, platform: str) -> Optional[OptimalTimeRecommendation]:
        """Get single best remaining time slot for today"""
        recommendations = self.get_optimal_times(
            platform=platform,
            start_date=datetime.utcnow(),
            num_slots=1,
            min_gap_hours=0
        )
        
        if recommendations:
            # Filter to only today
            today = datetime.utcnow().date()
            for rec in recommendations:
                if rec.datetime.date() == today:
                    return rec
        
        return None
    
    def get_weekly_schedule(
        self,
        platform: str,
        posts_per_day: int = 2,
        preferred_hours: Optional[List[int]] = None
    ) -> List[OptimalTimeRecommendation]:
        """
        Generate an optimal weekly posting schedule.
        
        Args:
            platform: Target platform
            posts_per_day: Number of posts per day
            preferred_hours: Optional list of preferred hours to consider
        
        Returns:
            List of recommendations for the week
        """
        all_recommendations = []
        start = datetime.utcnow()
        
        for day_offset in range(7):
            day_start = (start + timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            # Get best times for this day
            day_recs = self.get_optimal_times(
                platform=platform,
                start_date=day_start,
                num_slots=posts_per_day * 2,  # Get more to filter
                min_gap_hours=4
            )
            
            # Filter to this day and apply preferred hours
            day_only = [
                r for r in day_recs 
                if r.datetime.date() == day_start.date()
            ]
            
            if preferred_hours:
                day_only = [
                    r for r in day_only
                    if r.datetime.hour in preferred_hours
                ] or day_only  # Fallback if no matches
            
            all_recommendations.extend(day_only[:posts_per_day])
        
        return sorted(all_recommendations, key=lambda r: r.datetime)


# Singleton instance for app-wide use
optimal_timing_service = OptimalTimingService()

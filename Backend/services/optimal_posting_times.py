"""
Optimal Posting Times Service
Calculates best times to post based on historical performance
Phase 4: Publishing & Scheduling
"""
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class OptimalPostingTimesService:
    """
    Analyzes historical post performance to recommend optimal posting times
    """
    
    async def get_optimal_times(
        self,
        db: AsyncSession,
        platform: str,
        account_id: Optional[str] = None,
        days_back: int = 90
    ) -> Dict[str, any]:
        """
        Get optimal posting times for a platform
        
        Returns:
        - Best hours of day (0-23)
        - Best days of week (0-6, Monday=0)
        - Performance scores for each time slot
        """
        try:
            # Get historical posts and their performance
            query = text("""
                SELECT 
                    EXTRACT(HOUR FROM smp.posted_at) as hour,
                    EXTRACT(DOW FROM smp.posted_at) as day_of_week,
                    sma.views_count,
                    sma.likes_count,
                    sma.comments_count,
                    sma.engagement_rate,
                    smp.posted_at
                FROM social_media_posts smp
                JOIN social_media_post_analytics sma ON smp.id = sma.post_id
                JOIN social_media_accounts sa ON smp.account_id = sa.id
                WHERE sa.platform = :platform
                AND smp.posted_at >= CURRENT_DATE - INTERVAL ':days_back days'
                AND sma.snapshot_date = (
                    SELECT MAX(snapshot_date)
                    FROM social_media_post_analytics
                    WHERE post_id = smp.id
                )
                AND (:account_id IS NULL OR sa.id = :account_id::uuid)
            """)
            
            result = await db.execute(query, {
                'platform': platform,
                'account_id': account_id,
                'days_back': days_back
            })
            rows = result.fetchall()
            
            if not rows:
                # Return default optimal times if no data
                return self._get_default_optimal_times(platform)
            
            # Analyze performance by hour and day
            hour_performance = defaultdict(lambda: {'count': 0, 'total_engagement': 0, 'total_views': 0})
            day_performance = defaultdict(lambda: {'count': 0, 'total_engagement': 0, 'total_views': 0})
            
            for row in rows:
                hour = int(row.hour) if row.hour is not None else 12
                day = int(row.day_of_week) if row.day_of_week is not None else 1
                engagement = float(row.engagement_rate or 0)
                views = int(row.views_count or 0)
                
                hour_performance[hour]['count'] += 1
                hour_performance[hour]['total_engagement'] += engagement
                hour_performance[hour]['total_views'] += views
                
                day_performance[day]['count'] += 1
                day_performance[day]['total_engagement'] += engagement
                day_performance[day]['total_views'] += views
            
            # Calculate average performance
            best_hours = []
            for hour in range(24):
                if hour_performance[hour]['count'] > 0:
                    avg_engagement = hour_performance[hour]['total_engagement'] / hour_performance[hour]['count']
                    avg_views = hour_performance[hour]['total_views'] / hour_performance[hour]['count']
                    score = (avg_engagement * 0.6) + (avg_views / 1000 * 0.4)  # Weighted score
                    best_hours.append({
                        'hour': hour,
                        'score': score,
                        'avg_engagement': avg_engagement,
                        'avg_views': avg_views,
                        'post_count': hour_performance[hour]['count']
                    })
            
            # Sort by score
            best_hours.sort(key=lambda x: x['score'], reverse=True)
            
            # Get best days
            best_days = []
            for day in range(7):
                if day_performance[day]['count'] > 0:
                    avg_engagement = day_performance[day]['total_engagement'] / day_performance[day]['count']
                    avg_views = day_performance[day]['total_views'] / day_performance[day]['count']
                    score = (avg_engagement * 0.6) + (avg_views / 1000 * 0.4)
                    best_days.append({
                        'day': day,
                        'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day],
                        'score': score,
                        'avg_engagement': avg_engagement,
                        'avg_views': avg_views,
                        'post_count': day_performance[day]['count']
                    })
            
            best_days.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'platform': platform,
                'best_hours': best_hours[:5],  # Top 5 hours
                'best_days': best_days[:3],  # Top 3 days
                'all_hour_scores': {h['hour']: h['score'] for h in best_hours},
                'all_day_scores': {d['day']: d['score'] for d in best_days},
                'data_points': len(rows)
            }
            
        except Exception as e:
            logger.error(f"Error calculating optimal posting times: {e}")
            return self._get_default_optimal_times(platform)
    
    def _get_default_optimal_times(self, platform: str) -> Dict[str, any]:
        """
        Return default optimal times based on platform best practices
        """
        # Platform-specific defaults based on industry research
        defaults = {
            'instagram': {
                'best_hours': [11, 14, 17, 20],  # 11am, 2pm, 5pm, 8pm
                'best_days': [1, 2, 3, 4, 5]  # Tuesday-Saturday
            },
            'tiktok': {
                'best_hours': [9, 12, 19, 21],  # 9am, 12pm, 7pm, 9pm
                'best_days': [0, 1, 2, 3, 4, 5, 6]  # All days
            },
            'youtube': {
                'best_hours': [14, 15, 16, 20],  # 2pm, 3pm, 4pm, 8pm
                'best_days': [1, 2, 3, 4, 5]  # Tuesday-Saturday
            },
            'facebook': {
                'best_hours': [9, 13, 15, 19],  # 9am, 1pm, 3pm, 7pm
                'best_days': [1, 2, 3, 4, 5]  # Tuesday-Saturday
            },
            'twitter': {
                'best_hours': [8, 12, 17, 20],  # 8am, 12pm, 5pm, 8pm
                'best_days': [0, 1, 2, 3, 4, 5, 6]  # All days
            }
        }
        
        platform_defaults = defaults.get(platform.lower(), defaults['instagram'])
        
        return {
            'platform': platform,
            'best_hours': [
                {'hour': h, 'score': 0.7, 'avg_engagement': 5.0, 'avg_views': 1000, 'post_count': 0}
                for h in platform_defaults['best_hours']
            ],
            'best_days': [
                {
                    'day': d,
                    'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][d],
                    'score': 0.7,
                    'avg_engagement': 5.0,
                    'avg_views': 1000,
                    'post_count': 0
                }
                for d in platform_defaults['best_days']
            ],
            'all_hour_scores': {h: 0.7 for h in platform_defaults['best_hours']},
            'all_day_scores': {d: 0.7 for d in platform_defaults['best_days']},
            'data_points': 0,
            'is_default': True
        }
    
    async def get_recommended_time(
        self,
        db: AsyncSession,
        platform: str,
        preferred_date: datetime,
        account_id: Optional[str] = None
    ) -> datetime:
        """
        Get recommended posting time for a specific date and platform
        
        Returns the best time on that date based on historical performance
        """
        optimal = await self.get_optimal_times(db, platform, account_id)
        
        # Get the best hour for the day of week
        day_of_week = preferred_date.weekday()
        day_score = optimal['all_day_scores'].get(day_of_week, 0.5)
        
        # Find best hour
        if optimal['best_hours']:
            best_hour = optimal['best_hours'][0]['hour']
        else:
            # Default to afternoon
            best_hour = 14
        
        # Create recommended datetime
        recommended = preferred_date.replace(
            hour=best_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        return recommended







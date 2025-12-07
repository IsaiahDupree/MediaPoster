"""
AI-Powered Coaching Service
Provides personalized content recommendations and coaching
Phase 3: Pre/Post Social Score + Coaching
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class CoachingService:
    """
    AI-powered coaching service that provides:
    - Content brief recommendations
    - Script suggestions
    - Performance insights
    - Strategy recommendations
    """
    
    async def get_coaching_recommendations(
        self,
        db: AsyncSession,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get personalized coaching recommendations
        
        Args:
            db: Database session
            user_id: User ID
            context: Optional context (goal_id, recent_performance, etc.)
            
        Returns:
            Dict with coaching recommendations
        """
        try:
            recommendations = {
                'content_briefs': [],
                'script_suggestions': [],
                'performance_insights': [],
                'strategy_recommendations': []
            }
            
            # 1. Analyze recent performance
            performance_insights = await self._analyze_performance(db, user_id)
            recommendations['performance_insights'] = performance_insights
            
            # 2. Generate content brief recommendations
            content_briefs = await self._generate_content_briefs(
                db, user_id, performance_insights
            )
            recommendations['content_briefs'] = content_briefs
            
            # 3. Generate script suggestions
            script_suggestions = await self._generate_script_suggestions(
                db, user_id, performance_insights
            )
            recommendations['script_suggestions'] = script_suggestions
            
            # 4. Strategy recommendations
            strategy = await self._generate_strategy_recommendations(
                db, user_id, performance_insights
            )
            recommendations['strategy_recommendations'] = strategy
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating coaching recommendations: {e}")
            raise
    
    async def _analyze_performance(
        self,
        db: AsyncSession,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze user's recent performance to identify patterns
        """
        insights = []
        
        try:
            # Get top performing content
            query = text("""
                SELECT 
                    smp.platform,
                    smp.media_type,
                    smp.caption,
                    sma.views_count,
                    sma.likes_count,
                    sma.comments_count,
                    sma.engagement_rate,
                    smp.posted_at
                FROM social_media_posts smp
                JOIN social_media_accounts sa ON smp.account_id = sa.id
                JOIN social_media_post_analytics sma ON smp.id = sma.post_id
                WHERE sa.user_id = :user_id
                AND sma.snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
                AND sma.snapshot_date = (
                    SELECT MAX(snapshot_date)
                    FROM social_media_post_analytics
                    WHERE post_id = smp.id
                )
                ORDER BY sma.engagement_rate DESC
                LIMIT 10
            """)
            
            result = await db.execute(query, {'user_id': user_id})
            top_posts = result.fetchall()
            
            if top_posts:
                # Analyze patterns
                avg_engagement = sum(float(p.engagement_rate or 0) for p in top_posts) / len(top_posts)
                
                insights.append({
                    'type': 'performance',
                    'title': 'Top Performing Content',
                    'description': f'Your top 10 posts average {avg_engagement:.1f}% engagement',
                    'action': 'Create more content similar to your top performers',
                    'priority': 'high'
                })
                
                # Platform analysis
                platforms = {}
                for post in top_posts:
                    platform = post.platform
                    if platform not in platforms:
                        platforms[platform] = {'count': 0, 'total_engagement': 0}
                    platforms[platform]['count'] += 1
                    platforms[platform]['total_engagement'] += float(post.engagement_rate or 0)
                
                best_platform = max(platforms.items(), key=lambda x: x[1]['total_engagement'] / x[1]['count'])
                insights.append({
                    'type': 'platform',
                    'title': 'Best Performing Platform',
                    'description': f'{best_platform[0].capitalize()} is your strongest platform',
                    'action': f'Focus more content on {best_platform[0]}',
                    'priority': 'medium'
                })
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
        
        return insights
    
    async def _generate_content_briefs(
        self,
        db: AsyncSession,
        user_id: str,
        performance_insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate content brief recommendations
        """
        briefs = []
        
        try:
            # Based on performance insights, suggest content briefs
            if performance_insights:
                best_platform_insight = next(
                    (i for i in performance_insights if i['type'] == 'platform'),
                    None
                )
                
                if best_platform_insight:
                    platform = best_platform_insight['description'].split()[0].lower()
                    
                    briefs.append({
                        'title': f'Create {platform.capitalize()} Content Series',
                        'description': f'Based on your strong performance on {platform}, create a 5-part series',
                        'format': '9:16 vertical video',
                        'topics': ['Hook in first 3 seconds', 'Educational value', 'Strong CTA'],
                        'estimated_engagement': '5-8%'
                    })
            
            # Default brief if no insights
            if not briefs:
                briefs.append({
                    'title': 'Educational Tutorial Series',
                    'description': 'Create a series teaching your audience something valuable',
                    'format': '9:16 vertical video',
                    'topics': ['Problem-solution format', 'Step-by-step guide', 'Visual demonstrations'],
                    'estimated_engagement': '4-6%'
                })
            
        except Exception as e:
            logger.error(f"Error generating content briefs: {e}")
        
        return briefs
    
    async def _generate_script_suggestions(
        self,
        db: AsyncSession,
        user_id: str,
        performance_insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate script suggestions based on performance
        """
        suggestions = []
        
        try:
            # Get top performing hooks/captions
            query = text("""
                SELECT 
                    smp.caption,
                    sma.engagement_rate
                FROM social_media_posts smp
                JOIN social_media_accounts sa ON smp.account_id = sa.id
                JOIN social_media_post_analytics sma ON smp.id = sma.post_id
                WHERE sa.user_id = :user_id
                AND smp.caption IS NOT NULL
                AND sma.snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY sma.engagement_rate DESC
                LIMIT 5
            """)
            
            result = await db.execute(query, {'user_id': user_id})
            top_captions = result.fetchall()
            
            if top_captions:
                # Analyze hook patterns
                hooks = []
                for caption in top_captions:
                    if caption.caption:
                        first_sentence = caption.caption.split('.')[0] if '.' in caption.caption else caption.caption[:50]
                        hooks.append({
                            'hook': first_sentence,
                            'engagement_rate': float(caption.engagement_rate or 0)
                        })
                
                suggestions.append({
                    'type': 'hook',
                    'title': 'High-Performing Hook Patterns',
                    'examples': hooks[:3],
                    'recommendation': 'Start your next videos with similar hook patterns'
                })
            
            # Script structure suggestions
            suggestions.append({
                'type': 'structure',
                'title': 'Optimal Script Structure',
                'structure': [
                    'Hook (0-3s): Grab attention immediately',
                    'Problem (3-10s): Identify the pain point',
                    'Solution (10-45s): Provide value',
                    'CTA (45-60s): Clear call to action'
                ],
                'recommendation': 'Follow this structure for maximum engagement'
            })
            
        except Exception as e:
            logger.error(f"Error generating script suggestions: {e}")
        
        return suggestions
    
    async def _generate_strategy_recommendations(
        self,
        db: AsyncSession,
        user_id: str,
        performance_insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate high-level strategy recommendations
        """
        strategies = []
        
        try:
            # Posting frequency analysis
            query = text("""
                SELECT 
                    COUNT(*) as post_count,
                    DATE_TRUNC('week', smp.posted_at) as week
                FROM social_media_posts smp
                JOIN social_media_accounts sa ON smp.account_id = sa.id
                WHERE sa.user_id = :user_id
                AND smp.posted_at >= CURRENT_DATE - INTERVAL '8 weeks'
                GROUP BY week
                ORDER BY week DESC
            """)
            
            result = await db.execute(query, {'user_id': user_id})
            weekly_posts = result.fetchall()
            
            if weekly_posts:
                avg_weekly = sum(p.post_count for p in weekly_posts) / len(weekly_posts) if weekly_posts else 0
                
                if avg_weekly < 3:
                    strategies.append({
                        'title': 'Increase Posting Frequency',
                        'description': f'You\'re posting {avg_weekly:.1f} times per week. Aim for 3-5 posts per week for better growth.',
                        'action': 'Schedule 3-5 posts per week',
                        'priority': 'high'
                    })
                elif avg_weekly >= 5:
                    strategies.append({
                        'title': 'Maintain Consistent Posting',
                        'description': f'Great! You\'re posting {avg_weekly:.1f} times per week. Keep it up!',
                        'action': 'Continue current posting schedule',
                        'priority': 'low'
                    })
            
            # Best time to post
            strategies.append({
                'title': 'Optimize Posting Times',
                'description': 'Post when your audience is most active (check analytics for peak hours)',
                'action': 'Schedule posts during peak engagement hours',
                'priority': 'medium'
            })
            
        except Exception as e:
            logger.error(f"Error generating strategy recommendations: {e}")
        
        return strategies







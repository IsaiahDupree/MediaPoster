"""
Post-Social Score Calculation Service
Calculates normalized performance scores for published content
Phase 3: Pre/Post Social Score + Coaching
"""
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PostSocialScoreCalculator:
    """
    Calculates post-social scores with normalization:
    - Follower count normalization
    - Platform behavior normalization
    - Time-since-posting normalization
    - Percentile ranking ("Top X% of your Reels")
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
    
    # Platform-specific engagement rate baselines (per 1000 followers)
    PLATFORM_BASELINES = {
        'instagram': {
            'reel': {'views_per_1k': 500, 'engagement_rate': 0.05},
            'post': {'views_per_1k': 200, 'engagement_rate': 0.03},
            'story': {'views_per_1k': 300, 'engagement_rate': 0.02}
        },
        'tiktok': {
            'video': {'views_per_1k': 800, 'engagement_rate': 0.08},
            'short': {'views_per_1k': 600, 'engagement_rate': 0.06}
        },
        'youtube': {
            'short': {'views_per_1k': 400, 'engagement_rate': 0.04},
            'video': {'views_per_1k': 100, 'engagement_rate': 0.02}
        },
        'facebook': {
            'video': {'views_per_1k': 150, 'engagement_rate': 0.02},
            'post': {'views_per_1k': 100, 'engagement_rate': 0.015}
        },
        'twitter': {
            'tweet': {'views_per_1k': 200, 'engagement_rate': 0.01}
        }
    }
    
    # Time decay factors (engagement typically peaks in first 24-48 hours)
    TIME_DECAY_FACTORS = {
        '0-6h': 1.0,      # Peak engagement period
        '6-24h': 0.9,     # High engagement
        '24-48h': 0.7,    # Moderate engagement
        '48-72h': 0.5,    # Declining engagement
        '72h+': 0.3       # Long-tail engagement
    }
    
    async def calculate_post_social_score(
        self,
        db: AsyncSession,
        post_id: int,
        platform: str,
        media_type: str,
        follower_count: int,
        posted_at: datetime,
        current_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate normalized post-social score for a published post
        
        Args:
            db: Database session
            post_id: Post ID
            platform: Platform name (instagram, tiktok, etc.)
            media_type: Media type (reel, video, post, etc.)
            follower_count: Account follower count at time of posting
            posted_at: When the post was published
            current_metrics: Current metrics dict with views, likes, comments, shares, etc.
            
        Returns:
            Dict with:
            - post_social_score: Normalized score (0-100)
            - raw_score: Unnormalized score
            - percentile_rank: Top X% of user's content
            - normalization_factors: Breakdown of normalization
        """
        try:
            # Get current metrics
            views = current_metrics.get('views', 0) or 0
            likes = current_metrics.get('likes', 0) or 0
            likes = likes or 0
            comments = current_metrics.get('comments', 0) or 0
            comments = comments or 0
            shares = current_metrics.get('shares', 0) or 0
            shares = shares or 0
            saves = current_metrics.get('saves', 0) or 0
            saves = saves or 0
            
            # Calculate raw engagement
            total_engagement = likes + comments + shares + saves
            raw_engagement_rate = (total_engagement / views * 100) if views > 0 else 0
            
            # 1. Follower Count Normalization
            follower_normalized_score = self._normalize_by_followers(
                views, likes, comments, shares, saves,
                follower_count, platform, media_type
            )
            
            # 2. Platform Behavior Normalization
            platform_normalized_score = self._normalize_by_platform(
                raw_engagement_rate, platform, media_type
            )
            
            # 3. Time-Since-Posting Normalization
            time_normalized_score = self._normalize_by_time(
                total_engagement, posted_at
            )
            
            # 4. Calculate weighted final score
            final_score = (
                follower_normalized_score * 0.40 +  # 40% weight
                platform_normalized_score * 0.35 +  # 35% weight
                time_normalized_score * 0.25        # 25% weight
            )
            
            # Clamp to 0-100
            final_score = max(0, min(100, final_score))
            
            # 5. Calculate percentile rank ("Top X% of your Reels")
            percentile_rank = await self._calculate_percentile_rank(
                db, post_id, platform, media_type, final_score
            )
            
            return {
                'post_social_score': round(final_score, 1),
                'raw_score': round(follower_normalized_score, 1),
                'percentile_rank': percentile_rank,
                'normalization_factors': {
                    'follower_normalized': round(follower_normalized_score, 1),
                    'platform_normalized': round(platform_normalized_score, 1),
                    'time_normalized': round(time_normalized_score, 1),
                    'follower_count': follower_count,
                    'time_since_posting_hours': self._hours_since_posting(posted_at)
                },
                'metrics': {
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'shares': shares,
                    'saves': saves,
                    'total_engagement': total_engagement,
                    'engagement_rate': round(raw_engagement_rate, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating post-social score for post {post_id}: {e}")
            raise
    
    def _normalize_by_followers(
        self,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        saves: int,
        follower_count: int,
        platform: str,
        media_type: str
    ) -> float:
        """
        Normalize metrics by follower count
        
        Accounts for the fact that larger accounts typically get more views/engagement
        """
        if follower_count == 0:
            return 0.0
        
        # Get platform baseline
        baseline = self.PLATFORM_BASELINES.get(platform, {}).get(media_type, {})
        expected_views_per_1k = baseline.get('views_per_1k', 200)
        expected_engagement_rate = baseline.get('engagement_rate', 0.03)
        
        # Calculate expected metrics for this follower count
        expected_views = (follower_count / 1000) * expected_views_per_1k
        expected_engagement = expected_views * expected_engagement_rate
        
        # Calculate actual metrics
        actual_views = views
        actual_engagement = likes + (comments * 2) + (shares * 3) + (saves * 2)  # Weighted engagement
        
        # Normalize: ratio of actual to expected
        views_ratio = (actual_views / expected_views) if expected_views > 0 else 0
        engagement_ratio = (actual_engagement / expected_engagement) if expected_engagement > 0 else 0
        
        # Combined score (views 30%, engagement 70%)
        normalized_score = (views_ratio * 0.3 + engagement_ratio * 0.7) * 100
        
        return max(0, min(100, normalized_score))
    
    def _normalize_by_platform(
        self,
        engagement_rate: float,
        platform: str,
        media_type: str
    ) -> float:
        """
        Normalize engagement rate by platform behavior
        
        Different platforms have different typical engagement rates
        """
        baseline = self.PLATFORM_BASELINES.get(platform, {}).get(media_type, {})
        expected_rate = baseline.get('engagement_rate', 0.03) * 100  # Convert to percentage
        
        if expected_rate == 0:
            return 0.0
        
        # Score based on how much above/below baseline
        ratio = engagement_rate / expected_rate
        
        # Scale: 1.0x baseline = 50 points, 2.0x = 100 points, 0.5x = 25 points
        score = min(100, max(0, (ratio - 0.5) * 100))
        
        return score
    
    def _normalize_by_time(
        self,
        total_engagement: int,
        posted_at: datetime
    ) -> float:
        """
        Normalize by time since posting
        
        Engagement typically peaks in first 24-48 hours
        """
        hours_since = self._hours_since_posting(posted_at)
        
        # Determine time bucket
        if hours_since < 6:
            decay_factor = self.TIME_DECAY_FACTORS['0-6h']
        elif hours_since < 24:
            decay_factor = self.TIME_DECAY_FACTORS['6-24h']
        elif hours_since < 48:
            decay_factor = self.TIME_DECAY_FACTORS['24-48h']
        elif hours_since < 72:
            decay_factor = self.TIME_DECAY_FACTORS['48-72h']
        else:
            decay_factor = self.TIME_DECAY_FACTORS['72h+']
        
        # Base score on engagement, adjusted by time
        # Higher engagement in early hours = better score
        base_score = min(100, total_engagement / 100)  # Rough scaling
        time_adjusted_score = base_score * (1.0 / decay_factor)  # Invert decay (earlier = better)
        
        return min(100, time_adjusted_score)
    
    def _hours_since_posting(self, posted_at: datetime) -> float:
        """Calculate hours since posting"""
        if not posted_at:
            return 0.0
        delta = datetime.now() - posted_at
        return delta.total_seconds() / 3600
    
    async def _calculate_percentile_rank(
        self,
        db: AsyncSession,
        post_id: int,
        platform: str,
        media_type: str,
        score: float
    ) -> Dict[str, Any]:
        """
        Calculate percentile rank: "Top X% of your Reels"
        
        Compares this post's score to all other posts from the same account
        """
        try:
            # Get all posts from same account/platform/media_type
            query = text("""
                WITH post_scores AS (
                    SELECT 
                        smp.id,
                        smp.account_id,
                        COALESCE(
                            (SELECT post_social_score 
                             FROM post_metrics 
                             WHERE post_id = smp.id 
                             ORDER BY snapshot_at DESC 
                             LIMIT 1),
                            0
                        ) as score
                    FROM social_media_posts smp
                    WHERE smp.platform = :platform
                    AND smp.media_type = :media_type
                    AND smp.account_id = (
                        SELECT account_id 
                        FROM social_media_posts 
                        WHERE id = :post_id
                    )
                )
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(*) FILTER (WHERE score < :current_score) as posts_below,
                    COUNT(*) FILTER (WHERE score = :current_score) as posts_equal
                FROM post_scores
            """)
            
            result = await db.execute(query, {
                'platform': platform,
                'media_type': media_type,
                'post_id': post_id,
                'current_score': score
            })
            
            row = result.first()
            if not row or row.total_posts == 0:
                return {
                    'percentile': 100,
                    'rank': 1,
                    'total_posts': 0,
                    'description': 'No comparison data'
                }
            
            total_posts = row.total_posts
            posts_below = row.posts_below
            posts_equal = row.posts_equal
            
            # Calculate percentile: (posts below + 0.5 * posts equal) / total
            percentile = ((posts_below + (posts_equal * 0.5)) / total_posts) * 100
            rank = total_posts - posts_below  # Higher score = lower rank number
            
            # Generate description
            if percentile >= 90:
                description = f"Top 10% of your {media_type}s"
            elif percentile >= 75:
                description = f"Top 25% of your {media_type}s"
            elif percentile >= 50:
                description = f"Top 50% of your {media_type}s"
            else:
                description = f"Bottom 50% of your {media_type}s"
            
            return {
                'percentile': round(100 - percentile, 1),  # Invert: higher percentile = better
                'rank': rank,
                'total_posts': total_posts,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Error calculating percentile rank: {e}")
            return {
                'percentile': 50,
                'rank': 0,
                'total_posts': 0,
                'description': 'Unable to calculate'
            }


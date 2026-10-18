"""
Performance Tracker
Fetch and track post metrics from platforms
"""
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime, timedelta
import statistics

from modules.publishing import BlotatoClient


class PerformanceTracker:
    """Track post performance metrics"""
    
    METRIC_THRESHOLDS = {
        'tiktok': {
            'viral': {'views': 100000, 'engagement_rate': 0.10},
            'good': {'views': 10000, 'engagement_rate': 0.05},
            'poor': {'views': 1000, 'engagement_rate': 0.02}
        },
        'instagram': {
            'viral': {'views': 50000, 'engagement_rate': 0.08},
            'good': {'views': 5000, 'engagement_rate': 0.04},
            'poor': {'views': 500, 'engagement_rate': 0.01}
        },
        'youtube': {
            'viral': {'views': 100000, 'engagement_rate': 0.08},
            'good': {'views': 10000, 'engagement_rate': 0.04},
            'poor': {'views': 1000, 'engagement_rate': 0.01}
        }
    }
    
    def __init__(self, blotato_client: Optional[BlotatoClient] = None):
        """
        Initialize performance tracker
        
        Args:
            blotato_client: Blotato client for API access
        """
        self.blotato = blotato_client or BlotatoClient()
        logger.info("Performance tracker initialized")
    
    def fetch_post_metrics(self, post_id: str) -> Optional[Dict]:
        """
        Fetch metrics for a post
        
        Args:
            post_id: Blotato post ID
            
        Returns:
            Metrics dictionary
        """
        logger.info(f"Fetching metrics for post {post_id}")
        
        try:
            status = self.blotato.get_post_status(post_id)
            if not status:
                return None
            
            metrics = {
                'post_id': post_id,
                'fetched_at': datetime.utcnow().isoformat(),
                'platforms': {}
            }
            
            # Extract platform-specific metrics
            for platform, data in status.get('platforms', {}).items():
                platform_metrics = self._extract_platform_metrics(platform, data)
                if platform_metrics:
                    metrics['platforms'][platform] = platform_metrics
            
            # Calculate aggregates
            metrics['total_views'] = sum(
                p.get('views', 0) for p in metrics['platforms'].values()
            )
            metrics['total_likes'] = sum(
                p.get('likes', 0) for p in metrics['platforms'].values()
            )
            metrics['total_comments'] = sum(
                p.get('comments', 0) for p in metrics['platforms'].values()
            )
            metrics['total_shares'] = sum(
                p.get('shares', 0) for p in metrics['platforms'].values()
            )
            
            # Calculate engagement rate
            total_engagement = (
                metrics['total_likes'] + 
                metrics['total_comments'] + 
                metrics['total_shares']
            )
            if metrics['total_views'] > 0:
                metrics['engagement_rate'] = total_engagement / metrics['total_views']
            else:
                metrics['engagement_rate'] = 0.0
            
            logger.success(f"✓ Fetched metrics: {metrics['total_views']} views")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return None
    
    def _extract_platform_metrics(self, platform: str, data: Dict) -> Dict:
        """Extract metrics from platform data"""
        metrics = {
            'platform': platform,
            'url': data.get('url'),
            'status': data.get('status', 'unknown'),
            'views': data.get('views', 0),
            'likes': data.get('likes', 0),
            'comments': data.get('comments', 0),
            'shares': data.get('shares', 0),
            'saves': data.get('saves', 0),
        }
        
        # Calculate platform engagement rate
        engagement = metrics['likes'] + metrics['comments'] + metrics['shares']
        if metrics['views'] > 0:
            metrics['engagement_rate'] = engagement / metrics['views']
        else:
            metrics['engagement_rate'] = 0.0
        
        return metrics
    
    def classify_performance(
        self,
        metrics: Dict,
        platform: Optional[str] = None
    ) -> str:
        """
        Classify post performance
        
        Args:
            metrics: Post metrics
            platform: Specific platform (None for overall)
            
        Returns:
            'viral', 'good', 'average', or 'poor'
        """
        if platform:
            platform_metrics = metrics['platforms'].get(platform, {})
            views = platform_metrics.get('views', 0)
            engagement_rate = platform_metrics.get('engagement_rate', 0)
            thresholds = self.METRIC_THRESHOLDS.get(platform, self.METRIC_THRESHOLDS['tiktok'])
        else:
            views = metrics.get('total_views', 0)
            engagement_rate = metrics.get('engagement_rate', 0)
            # Use TikTok thresholds for overall
            thresholds = self.METRIC_THRESHOLDS['tiktok']
        
        # Check against thresholds
        if (views >= thresholds['viral']['views'] and 
            engagement_rate >= thresholds['viral']['engagement_rate']):
            return 'viral'
        elif (views >= thresholds['good']['views'] and 
              engagement_rate >= thresholds['good']['engagement_rate']):
            return 'good'
        elif (views >= thresholds['poor']['views'] and 
              engagement_rate >= thresholds['poor']['engagement_rate']):
            return 'average'
        else:
            return 'poor'
    
    def track_multiple_posts(
        self,
        post_ids: List[str]
    ) -> List[Dict]:
        """Track metrics for multiple posts"""
        logger.info(f"Tracking {len(post_ids)} posts")
        
        results = []
        for post_id in post_ids:
            metrics = self.fetch_post_metrics(post_id)
            if metrics:
                metrics['classification'] = self.classify_performance(metrics)
                results.append(metrics)
        
        logger.success(f"✓ Tracked {len(results)} posts")
        return results
    
    def calculate_statistics(
        self,
        metrics_list: List[Dict]
    ) -> Dict:
        """Calculate aggregate statistics"""
        if not metrics_list:
            return {}
        
        views = [m['total_views'] for m in metrics_list]
        engagement_rates = [m['engagement_rate'] for m in metrics_list]
        
        # Count classifications
        classifications = {}
        for m in metrics_list:
            classification = m.get('classification', 'unknown')
            classifications[classification] = classifications.get(classification, 0) + 1
        
        return {
            'total_posts': len(metrics_list),
            'total_views': sum(views),
            'avg_views': statistics.mean(views) if views else 0,
            'median_views': statistics.median(views) if views else 0,
            'max_views': max(views) if views else 0,
            'min_views': min(views) if views else 0,
            'avg_engagement_rate': statistics.mean(engagement_rates) if engagement_rates else 0,
            'classifications': classifications,
            'viral_percentage': (classifications.get('viral', 0) / len(metrics_list) * 100) if metrics_list else 0
        }


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("PERFORMANCE TRACKER")
    print("="*60)
    print("\nTracks post metrics from Blotato/platforms.")
    print("For testing, use test_phase5.py")

"""
Post Monitor
Orchestrates post-publish monitoring and optimization
"""
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime, timedelta
from pathlib import Path

from .performance_tracker import PerformanceTracker
from .content_optimizer import ContentOptimizer


class PostMonitor:
    """Monitor published posts and optimize performance"""
    
    CHECK_INTERVALS = {
        'immediate': timedelta(hours=1),    # 1 hour after posting
        'early': timedelta(hours=24),       # 24 hours
        'mid': timedelta(days=3),           # 3 days
        'final': timedelta(days=7)          # 7 days
    }
    
    def __init__(self):
        """Initialize post monitor"""
        self.tracker = PerformanceTracker()
        self.optimizer = ContentOptimizer()
        
        logger.info("Post monitor initialized")
    
    def check_post_performance(
        self,
        post_id: str,
        post_age_hours: float
    ) -> Dict:
        """
        Check post performance and determine actions
        
        Args:
            post_id: Blotato post ID
            post_age_hours: Hours since posting
            
        Returns:
            Performance report with recommended actions
        """
        logger.info(f"Checking post {post_id} (age: {post_age_hours:.1f}h)")
        
        # Fetch metrics
        metrics = self.tracker.fetch_post_metrics(post_id)
        if not metrics:
            return {'error': 'Could not fetch metrics'}
        
        # Classify performance
        classification = self.tracker.classify_performance(metrics)
        
        # Determine check stage
        stage = self._get_check_stage(post_age_hours)
        
        # Generate recommendations
        actions = self._recommend_actions(
            metrics,
            classification,
            stage,
            post_age_hours
        )
        
        report = {
            'post_id': post_id,
            'post_age_hours': post_age_hours,
            'stage': stage,
            'metrics': metrics,
            'classification': classification,
            'actions': actions,
            'checked_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Performance: {classification.upper()}")
        logger.info(f"Actions: {len(actions)} recommended")
        
        return report
    
    def _get_check_stage(self, post_age_hours: float) -> str:
        """Determine which check stage we're in"""
        age = timedelta(hours=post_age_hours)
        
        if age <= self.CHECK_INTERVALS['immediate']:
            return 'immediate'
        elif age <= self.CHECK_INTERVALS['early']:
            return 'early'
        elif age <= self.CHECK_INTERVALS['mid']:
            return 'mid'
        else:
            return 'final'
    
    def _recommend_actions(
        self,
        metrics: Dict,
        classification: str,
        stage: str,
        post_age_hours: float
    ) -> List[Dict]:
        """Recommend actions based on performance"""
        actions = []
        
        # Viral posts - celebrate and analyze
        if classification == 'viral':
            actions.append({
                'type': 'celebrate',
                'priority': 'high',
                'action': 'Viral success! Analyze what worked',
                'details': 'Extract patterns from this high performer'
            })
        
        # Good posts - monitor and potentially boost
        elif classification == 'good':
            actions.append({
                'type': 'monitor',
                'priority': 'medium',
                'action': 'Continue monitoring',
                'details': 'Post is performing well'
            })
        
        # Poor performers - consider removal after grace period
        elif classification == 'poor':
            if stage == 'final' and post_age_hours >= 48:  # 48 hours minimum
                actions.append({
                    'type': 'consider_removal',
                    'priority': 'low',
                    'action': 'Consider removing post',
                    'details': f'Low performance after {post_age_hours:.0f}h',
                    'views': metrics.get('total_views', 0)
                })
            else:
                actions.append({
                    'type': 'wait',
                    'priority': 'low',
                    'action': 'Wait for more data',
                    'details': 'Too early to judge'
                })
        
        # Check for declining engagement
        engagement_rate = metrics.get('engagement_rate', 0)
        if engagement_rate < 0.01 and metrics.get('total_views', 0) > 100:
            actions.append({
                'type': 'analyze',
                'priority': 'medium',
                'action': 'Low engagement despite views',
                'details': 'Content may not be resonating'
            })
        
        return actions
    
    def monitor_all_posts(
        self,
        posts: List[Dict],
        auto_remove_threshold: Optional[int] = None
    ) -> Dict:
        """
        Monitor multiple posts
        
        Args:
            posts: List of posts with 'post_id' and 'published_at'
            auto_remove_threshold: Auto-remove if views below this (None = no auto-remove)
            
        Returns:
            Monitoring report
        """
        logger.info(f"Monitoring {len(posts)} posts")
        
        reports = []
        removal_candidates = []
        
        for post in posts:
            post_id = post.get('post_id')
            published_at = post.get('published_at')
            
            if not post_id or not published_at:
                continue
            
            # Calculate age
            published_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            age_hours = (datetime.utcnow() - published_time.replace(tzinfo=None)).total_seconds() / 3600
            
            # Check performance
            report = self.check_post_performance(post_id, age_hours)
            reports.append(report)
            
            # Check for auto-removal
            if auto_remove_threshold:
                views = report['metrics'].get('total_views', 0)
                if (age_hours >= 48 and 
                    views < auto_remove_threshold and 
                    report['classification'] == 'poor'):
                    removal_candidates.append({
                        'post_id': post_id,
                        'views': views,
                        'age_hours': age_hours
                    })
        
        # Generate summary
        classifications = {}
        for report in reports:
            classification = report.get('classification', 'unknown')
            classifications[classification] = classifications.get(classification, 0) + 1
        
        summary = {
            'total_posts': len(reports),
            'classifications': classifications,
            'removal_candidates': removal_candidates,
            'viral_posts': [r for r in reports if r.get('classification') == 'viral'],
            'poor_posts': [r for r in reports if r.get('classification') == 'poor'],
            'checked_at': datetime.utcnow().isoformat()
        }
        
        logger.success(f"✓ Monitoring complete:")
        logger.info(f"   Viral: {classifications.get('viral', 0)}")
        logger.info(f"   Good: {classifications.get('good', 0)}")
        logger.info(f"   Poor: {classifications.get('poor', 0)}")
        
        if removal_candidates:
            logger.warning(f"   Removal candidates: {len(removal_candidates)}")
        
        return {
            'summary': summary,
            'reports': reports
        }
    
    def generate_insights_report(
        self,
        posts_data: List[Dict]
    ) -> Dict:
        """
        Generate comprehensive insights report
        
        Args:
            posts_data: Historical post data with metrics
            
        Returns:
            Insights and recommendations
        """
        logger.info("Generating insights report")
        
        # Get performance stats
        metrics_list = [p.get('metrics') for p in posts_data if p.get('metrics')]
        stats = self.tracker.calculate_statistics(metrics_list)
        
        # Analyze patterns
        insights = self.optimizer.analyze_patterns(posts_data)
        
        # Identify low performers
        low_performers = self.optimizer.identify_low_performers(posts_data)
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'statistics': stats,
            'insights': insights,
            'low_performers': len(low_performers),
            'recommendations': insights.get('recommendations', [])
        }
        
        logger.success("✓ Insights report generated")
        return report
    
    def should_remove_post(
        self,
        post_report: Dict,
        min_age_hours: float = 48.0,
        min_views_threshold: int = 100
    ) -> bool:
        """
        Determine if post should be removed
        
        Args:
            post_report: Post performance report
            min_age_hours: Minimum age before removal
            min_views_threshold: Minimum views threshold
            
        Returns:
            True if should remove
        """
        age = post_report.get('post_age_hours', 0)
        views = post_report.get('metrics', {}).get('total_views', 0)
        classification = post_report.get('classification', 'unknown')
        
        # Criteria for removal
        if (age >= min_age_hours and 
            views < min_views_threshold and 
            classification == 'poor'):
            return True
        
        return False


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("POST MONITOR")
    print("="*60)
    print("\nMonitors published posts and provides insights.")
    print("For testing, use test_phase5.py")

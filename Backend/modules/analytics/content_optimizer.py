"""
Content Optimizer
Analyze what works and optimize future content
"""
from typing import Dict, List, Optional
from loguru import logger
import statistics


class ContentOptimizer:
    """Optimize content based on performance data"""
    
    def __init__(self):
        """Initialize content optimizer"""
        logger.info("Content optimizer initialized")
    
    def analyze_patterns(
        self,
        posts_data: List[Dict]
    ) -> Dict:
        """
        Analyze performance patterns
        
        Args:
            posts_data: List of post data with metrics and metadata
            
        Returns:
            Analysis results with insights
        """
        logger.info(f"Analyzing patterns in {len(posts_data)} posts")
        
        if not posts_data:
            return {}
        
        insights = {
            'best_times': self._analyze_posting_times(posts_data),
            'best_platforms': self._analyze_platforms(posts_data),
            'best_templates': self._analyze_templates(posts_data),
            'best_hooks': self._analyze_hooks(posts_data),
            'best_durations': self._analyze_durations(posts_data),
            'hashtag_performance': self._analyze_hashtags(posts_data)
        }
        
        # Generate recommendations
        insights['recommendations'] = self._generate_recommendations(insights)
        
        logger.success("✓ Pattern analysis complete")
        return insights
    
    def _analyze_posting_times(self, posts_data: List[Dict]) -> Dict:
        """Analyze best posting times"""
        # Group by hour of day
        hourly_performance = {}
        
        for post in posts_data:
            metrics = post.get('metrics', {})
            timestamp = post.get('published_at')
            
            if timestamp and metrics:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour = dt.hour
                
                if hour not in hourly_performance:
                    hourly_performance[hour] = []
                
                hourly_performance[hour].append(metrics.get('total_views', 0))
        
        # Calculate averages
        hourly_avg = {
            hour: statistics.mean(views) 
            for hour, views in hourly_performance.items()
        }
        
        # Find best hours
        if hourly_avg:
            best_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)[:3]
            return {
                'best_hours': [h for h, _ in best_hours],
                'hourly_averages': hourly_avg
            }
        
        return {}
    
    def _analyze_platforms(self, posts_data: List[Dict]) -> Dict:
        """Analyze platform performance"""
        platform_stats = {}
        
        for post in posts_data:
            metrics = post.get('metrics', {})
            for platform, platform_metrics in metrics.get('platforms', {}).items():
                if platform not in platform_stats:
                    platform_stats[platform] = {
                        'views': [],
                        'engagement_rates': []
                    }
                
                platform_stats[platform]['views'].append(platform_metrics.get('views', 0))
                platform_stats[platform]['engagement_rates'].append(
                    platform_metrics.get('engagement_rate', 0)
                )
        
        # Calculate averages
        results = {}
        for platform, stats in platform_stats.items():
            results[platform] = {
                'avg_views': statistics.mean(stats['views']) if stats['views'] else 0,
                'avg_engagement': statistics.mean(stats['engagement_rates']) if stats['engagement_rates'] else 0,
                'total_posts': len(stats['views'])
            }
        
        # Rank platforms
        ranked = sorted(
            results.items(),
            key=lambda x: x[1]['avg_views'],
            reverse=True
        )
        
        return {
            'by_platform': results,
            'best_platform': ranked[0][0] if ranked else None
        }
    
    def _analyze_templates(self, posts_data: List[Dict]) -> Dict:
        """Analyze template performance"""
        template_stats = {}
        
        for post in posts_data:
            template = post.get('metadata', {}).get('template', 'unknown')
            metrics = post.get('metrics', {})
            
            if template not in template_stats:
                template_stats[template] = []
            
            template_stats[template].append(metrics.get('total_views', 0))
        
        # Calculate averages
        results = {
            template: {
                'avg_views': statistics.mean(views),
                'count': len(views)
            }
            for template, views in template_stats.items()
        }
        
        # Find best
        if results:
            best = max(results.items(), key=lambda x: x[1]['avg_views'])
            return {
                'by_template': results,
                'best_template': best[0]
            }
        
        return {}
    
    def _analyze_hooks(self, posts_data: List[Dict]) -> Dict:
        """Analyze hook effectiveness"""
        hook_performance = []
        
        for post in posts_data:
            hook = post.get('metadata', {}).get('hook_text')
            metrics = post.get('metrics', {})
            
            if hook:
                hook_performance.append({
                    'hook': hook,
                    'views': metrics.get('total_views', 0),
                    'engagement_rate': metrics.get('engagement_rate', 0)
                })
        
        # Sort by views
        hook_performance.sort(key=lambda x: x['views'], reverse=True)
        
        return {
            'top_hooks': hook_performance[:5],
            'avg_views_with_hooks': statistics.mean([h['views'] for h in hook_performance]) if hook_performance else 0
        }
    
    def _analyze_durations(self, posts_data: List[Dict]) -> Dict:
        """Analyze optimal clip duration"""
        duration_buckets = {
            '10-15s': [],
            '15-30s': [],
            '30-45s': [],
            '45-60s': []
        }
        
        for post in posts_data:
            duration = post.get('metadata', {}).get('duration', 0)
            metrics = post.get('metrics', {})
            views = metrics.get('total_views', 0)
            
            if 10 <= duration < 15:
                duration_buckets['10-15s'].append(views)
            elif 15 <= duration < 30:
                duration_buckets['15-30s'].append(views)
            elif 30 <= duration < 45:
                duration_buckets['30-45s'].append(views)
            elif 45 <= duration <= 60:
                duration_buckets['45-60s'].append(views)
        
        # Calculate averages
        results = {
            bucket: statistics.mean(views) if views else 0
            for bucket, views in duration_buckets.items()
        }
        
        # Find best
        if results:
            best = max(results.items(), key=lambda x: x[1])
            return {
                'by_duration': results,
                'best_duration': best[0]
            }
        
        return {}
    
    def _analyze_hashtags(self, posts_data: List[Dict]) -> Dict:
        """Analyze hashtag performance"""
        hashtag_stats = {}
        
        for post in posts_data:
            hashtags = post.get('metadata', {}).get('hashtags', [])
            metrics = post.get('metrics', {})
            views = metrics.get('total_views', 0)
            
            for hashtag in hashtags:
                if hashtag not in hashtag_stats:
                    hashtag_stats[hashtag] = []
                hashtag_stats[hashtag].append(views)
        
        # Calculate averages
        results = {
            hashtag: statistics.mean(views)
            for hashtag, views in hashtag_stats.items()
            if len(views) >= 2  # Minimum 2 occurrences
        }
        
        # Sort by performance
        sorted_hashtags = sorted(results.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'top_hashtags': sorted_hashtags[:10],
            'all_hashtags': results
        }
    
    def _generate_recommendations(self, insights: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Best time
        best_times = insights.get('best_times', {}).get('best_hours', [])
        if best_times:
            recommendations.append(
                f"Post between {best_times[0]}:00-{best_times[0]+1}:00 UTC for best performance"
            )
        
        # Best platform
        best_platform = insights.get('best_platforms', {}).get('best_platform')
        if best_platform:
            recommendations.append(
                f"Prioritize {best_platform.title()} - it performs best"
            )
        
        # Best template
        best_template = insights.get('best_templates', {}).get('best_template')
        if best_template:
            recommendations.append(
                f"Use '{best_template}' template more often"
            )
        
        # Best duration
        best_duration = insights.get('best_durations', {}).get('best_duration')
        if best_duration:
            recommendations.append(
                f"Keep clips in {best_duration} range"
            )
        
        # Top hashtags
        top_hashtags = insights.get('hashtag_performance', {}).get('top_hashtags', [])
        if top_hashtags:
            top_3 = [h for h, _ in top_hashtags[:3]]
            recommendations.append(
                f"Use these hashtags: {', '.join(top_3)}"
            )
        
        return recommendations
    
    def identify_low_performers(
        self,
        posts_data: List[Dict],
        threshold_percentile: float = 25.0
    ) -> List[Dict]:
        """
        Identify posts in bottom percentile
        
        Args:
            posts_data: List of posts with metrics
            threshold_percentile: Percentile threshold (25 = bottom 25%)
            
        Returns:
            List of low-performing posts
        """
        if not posts_data:
            return []
        
        # Extract views
        posts_with_views = [
            (post, post.get('metrics', {}).get('total_views', 0))
            for post in posts_data
        ]
        
        views = [v for _, v in posts_with_views]
        
        # Calculate threshold
        sorted_views = sorted(views)
        threshold_index = int(len(sorted_views) * (threshold_percentile / 100.0))
        threshold_views = sorted_views[threshold_index] if sorted_views else 0
        
        # Filter low performers
        low_performers = [
            post for post, view_count in posts_with_views
            if view_count <= threshold_views
        ]
        
        logger.info(f"Identified {len(low_performers)} low performers (< {threshold_views} views)")
        
        return low_performers


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CONTENT OPTIMIZER")
    print("="*60)
    print("\nAnalyzes what works and provides recommendations.")
    print("For testing, use test_phase5.py")

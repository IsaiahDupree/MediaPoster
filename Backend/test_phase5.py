#!/usr/bin/env python3
"""
Phase 5 Testing - Content Monitor & Analytics
Test performance tracking and optimization
"""
import sys
from pathlib import Path
from loguru import logger
import json
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from modules.analytics import PerformanceTracker, ContentOptimizer, PostMonitor


def test_performance_tracker():
    """Test performance tracking"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Performance Tracker")
    logger.info("="*60)
    
    logger.info("\nRequires: Blotato post ID from Phase 4")
    
    post_id = input("\nEnter Blotato post ID (or skip): ").strip()
    if not post_id:
        logger.warning("Skipped")
        return
    
    try:
        tracker = PerformanceTracker()
        
        logger.info("\nFetching metrics...")
        metrics = tracker.fetch_post_metrics(post_id)
        
        if metrics:
            logger.success("\n✓ Metrics fetched!")
            logger.info(f"   Total views: {metrics['total_views']:,}")
            logger.info(f"   Total likes: {metrics['total_likes']:,}")
            logger.info(f"   Total comments: {metrics['total_comments']:,}")
            logger.info(f"   Engagement rate: {metrics['engagement_rate']:.2%}")
            
            # Show per-platform
            logger.info("\n📱 Per Platform:")
            for platform, data in metrics['platforms'].items():
                logger.info(f"   {platform.title()}:")
                logger.info(f"      Views: {data['views']:,}")
                logger.info(f"      Likes: {data['likes']:,}")
                logger.info(f"      Engagement: {data['engagement_rate']:.2%}")
            
            # Classify
            classification = tracker.classify_performance(metrics)
            logger.info(f"\n🏆 Classification: {classification.upper()}")
            
        else:
            logger.error("Could not fetch metrics")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def test_content_optimizer():
    """Test content optimization"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Content Optimizer")
    logger.info("="*60)
    
    logger.info("\nThis analyzes historical post data to find patterns.")
    logger.info("Requires: JSON file with post history")
    
    data_path_str = input("\nEnter post data JSON path (or skip): ").strip()
    if not data_path_str:
        logger.warning("Skipped - using sample data")
        # Use sample data
        posts_data = _generate_sample_data()
    else:
        data_path = Path(data_path_str).expanduser()
        if not data_path.exists():
            logger.error("File not found")
            return
        
        with open(data_path) as f:
            posts_data = json.load(f)
    
    try:
        optimizer = ContentOptimizer()
        
        logger.info(f"\nAnalyzing {len(posts_data)} posts...")
        insights = optimizer.analyze_patterns(posts_data)
        
        # Show insights
        logger.success("\n✓ Analysis complete!")
        
        if insights.get('best_platforms'):
            best_platform = insights['best_platforms'].get('best_platform')
            logger.info(f"\n🏆 Best platform: {best_platform}")
        
        if insights.get('best_durations'):
            best_duration = insights['best_durations'].get('best_duration')
            logger.info(f"⏱️  Best duration: {best_duration}")
        
        if insights.get('best_templates'):
            best_template = insights['best_templates'].get('best_template')
            logger.info(f"🎨 Best template: {best_template}")
        
        # Show recommendations
        recommendations = insights.get('recommendations', [])
        if recommendations:
            logger.info("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"   {i}. {rec}")
        
        # Identify low performers
        logger.info("\nIdentifying low performers...")
        low_performers = optimizer.identify_low_performers(posts_data)
        logger.info(f"Found {len(low_performers)} in bottom 25%")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def test_post_monitor():
    """Test post monitoring"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Post Monitor")
    logger.info("="*60)
    
    logger.info("\nMonitors posts and recommends actions.")
    
    post_id = input("\nEnter Blotato post ID (or skip): ").strip()
    if not post_id:
        logger.warning("Skipped")
        return
    
    # Get post age
    age_str = input("Hours since posting [24]: ").strip()
    age_hours = float(age_str) if age_str else 24.0
    
    try:
        monitor = PostMonitor()
        
        logger.info(f"\nChecking post (age: {age_hours:.1f}h)...")
        report = monitor.check_post_performance(post_id, age_hours)
        
        if 'error' in report:
            logger.error(report['error'])
            return
        
        logger.success("\n✓ Monitoring report:")
        logger.info(f"   Stage: {report['stage']}")
        logger.info(f"   Classification: {report['classification'].upper()}")
        logger.info(f"   Views: {report['metrics']['total_views']:,}")
        logger.info(f"   Engagement: {report['metrics']['engagement_rate']:.2%}")
        
        # Show actions
        actions = report.get('actions', [])
        if actions:
            logger.info("\n🎯 Recommended Actions:")
            for action in actions:
                priority = action.get('priority', 'low')
                icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
                logger.info(f"   {icon} {action['action']}")
                logger.info(f"      {action['details']}")
        
        # Should remove?
        if monitor.should_remove_post(report):
            logger.warning("\n⚠️  This post is a candidate for removal")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def _generate_sample_data() -> List[Dict]:
    """Generate sample post data for testing"""
    sample_posts = []
    
    for i in range(10):
        post = {
            'post_id': f'sample_{i}',
            'published_at': (datetime.utcnow() - timedelta(days=i)).isoformat() + 'Z',
            'metadata': {
                'template': ['viral_basic', 'clean', 'maximum'][i % 3],
                'duration': 15 + (i * 5),
                'hook_text': f'Sample hook {i}',
                'hashtags': ['#fyp', '#viral', '#test']
            },
            'metrics': {
                'total_views': 1000 + (i * 500),
                'total_likes': 50 + (i * 25),
                'total_comments': 10 + (i * 5),
                'total_shares': 5 + (i * 2),
                'engagement_rate': 0.05 + (i * 0.01),
                'platforms': {
                    'tiktok': {
                        'views': 500 + (i * 250),
                        'likes': 25 + (i * 12),
                        'engagement_rate': 0.05
                    }
                }
            }
        }
        sample_posts.append(post)
    
    return sample_posts


def main():
    """Main menu"""
    print("\n" + "="*60)
    print("   MediaPoster - Phase 5 Testing")
    print("   (Content Monitor & Analytics)")
    print("="*60)
    print("\nChoose a test:")
    print("  1. Performance Tracker")
    print("  2. Content Optimizer")
    print("  3. Post Monitor (recommended)")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice (0-3): ").strip()
    print()
    
    if choice == '0':
        logger.info("Goodbye!")
        return
    
    elif choice == '1':
        test_performance_tracker()
    
    elif choice == '2':
        test_content_optimizer()
    
    elif choice == '3':
        test_post_monitor()
    
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    main()

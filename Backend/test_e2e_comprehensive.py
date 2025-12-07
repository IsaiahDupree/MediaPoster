"""
Comprehensive End-to-End Test Suite
Tests complete workflow: Video → Clip → Post → URL → Analytics
"""
import os
import sys
import time
from dotenv import load_dotenv
from loguru import logger
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.monitoring.post_tracker import PostTracker
from modules.analytics.youtube_analytics import YouTubeAnalytics
from modules.analytics.sentiment_analyzer import SentimentAnalyzer

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"


class E2ETestSuite:
    """Comprehensive end-to-end testing"""
    
    def __init__(self):
        self.blotato_headers = {
            'blotato-api-key': API_KEY,
            'Content-Type': 'application/json'
        }
        self.results = {}
    
    def test_video_to_post_workflow(self):
        """Test complete workflow: Upload → Post → Track → Get URL"""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Video Upload → Post → URL Retrieval")
        logger.info("="*80 + "\n")
        
        # Step 1: Upload video
        logger.info("Step 1/4: Upload Media")
        media_url = self._upload_test_video()
        if not media_url:
            self.results['video_upload'] = 'FAILED'
            return False
        self.results['video_upload'] = 'PASSED'
        
        # Step 2: Create post
        logger.info("\nStep 2/4: Create Post")
        submission_id = self._create_youtube_post(media_url)
        if not submission_id:
            self.results['post_creation'] = 'FAILED'
            return False
        self.results['post_creation'] = 'PASSED'
        
        # Step 3: Track status
        logger.info("\nStep 3/4: Track Status Until Published")
        platform_url = self._track_until_published(submission_id)
        if not platform_url:
            self.results['status_tracking'] = 'FAILED'
            return False
        self.results['status_tracking'] = 'PASSED'
        
        # Step 4: Verify URL
        logger.info("\nStep 4/4: Verify Published URL")
        if self._verify_url(platform_url):
            self.results['url_verification'] = 'PASSED'
            self.results['platform_url'] = platform_url
            logger.success(f"✅ Workflow complete! URL: {platform_url}")
            return True
        else:
            self.results['url_verification'] = 'FAILED'
            return False
    
    def test_multi_platform_posting(self):
        """Test posting to multiple platforms"""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Multi-Platform Posting")
        logger.info("="*80 + "\n")
        
        # Upload media once
        media_url = self._upload_test_video()
        if not media_url:
            return False
        
        platforms = {
            'youtube': '228',
            'instagram': '807',
            'twitter': '571',
            'tiktok': '710',
            'threads': '243'
        }
        
        results = {}
        
        for platform, account_id in platforms.items():
            logger.info(f"\nTesting {platform.upper()} (ID: {account_id})")
            
            try:
                submission_id = self._create_platform_post(platform, account_id, media_url)
                if submission_id:
                    results[platform] = 'POSTED'
                    logger.success(f"  ✅ {platform} posted: {submission_id[:8]}...")
                else:
                    results[platform] = 'FAILED'
                    logger.error(f"  ❌ {platform} failed")
            except Exception as e:
                results[platform] = f'ERROR: {str(e)[:50]}'
                logger.error(f"  ❌ {platform} error: {e}")
        
        self.results['multi_platform'] = results
        
        success_count = sum(1 for v in results.values() if v == 'POSTED')
        logger.info(f"\n{success_count}/{len(platforms)} platforms successful")
        
        return success_count > 0
    
    def test_analytics_collection(self):
        """Test analytics collection for a published post"""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Analytics Collection")
        logger.info("="*80 + "\n")
        
        # Need a published YouTube URL (from previous test or manual)
        test_url = self.results.get('platform_url') or "https://www.youtube.com/watch?v=Q1Mhzw7nXDY"
        
        logger.info(f"Testing with URL: {test_url}")
        
        # Test YouTube analytics
        youtube = YouTubeAnalytics()
        
        logger.info("\nCollecting video stats...")
        stats = youtube.get_video_stats(test_url)
        
        if stats:
            logger.success("✅ Video stats collected")
            logger.info(f"  Views: {stats['views']}")
            logger.info(f"  Likes: {stats['likes']}")
            logger.info(f"  Comments: {stats['comments_count']}")
            self.results['analytics_stats'] = 'PASSED'
        else:
            logger.error("❌ Stats collection failed")
            self.results['analytics_stats'] = 'FAILED'
            return False
        
        # Test comment collection
        logger.info("\nCollecting comments...")
        comments = youtube.get_comments(test_url, max_results=10)
        
        if comments:
            logger.success(f"✅ Collected {len(comments)} comments")
            self.results['analytics_comments'] = 'PASSED'
        else:
            logger.warning("⚠️  No comments found")
            self.results['analytics_comments'] = 'SKIPPED'
        
        # Test sentiment analysis
        if comments:
            logger.info("\nAnalyzing sentiment...")
            sentiment = SentimentAnalyzer()
            
            comment_texts = [c['text'] for c in comments]
            overall = sentiment.get_overall_sentiment(comment_texts)
            
            logger.success("✅ Sentiment analyzed")
            logger.info(f"  Overall Score: {overall['sentiment_score']:.2f}")
            logger.info(f"  Positive: {overall['positive_pct']:.1f}%")
            logger.info(f"  Negative: {overall['negative_pct']:.1f}%")
            logger.info(f"  Neutral: {overall['neutral_pct']:.1f}%")
            self.results['analytics_sentiment'] = 'PASSED'
        
        return True
    
    def _upload_test_video(self):
        """Upload test video to Blotato"""
        test_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
        
        try:
            response = requests.post(
                f"{BASE_URL}/media",
                json={'url': test_url},
                headers=self.blotato_headers,
                timeout=60
            )
            
            if response.status_code == 201:
                url = response.json().get('url')
                logger.success(f"✅ Media uploaded")
                return url
            else:
                logger.error(f"❌ Upload failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            return None
    
    def _create_youtube_post(self, media_url):
        """Create YouTube post"""
        payload = {
            'post': {
                'accountId': '228',
                'content': {
                    'text': 'E2E Test Video - Automated Testing',
                    'mediaUrls': [media_url],
                    'platform': 'youtube',
                    'title': 'E2E Test Video'
                },
                'target': {
                    'targetType': 'youtube',
                    'title': 'E2E Test Video',
                    'privacyStatus': 'unlisted',
                    'shouldNotifySubscribers': False
                }
            }
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/posts",
                json=payload,
                headers=self.blotato_headers,
                timeout=30
            )
            
            if response.status_code == 201:
                submission_id = response.json().get('postSubmissionId')
                logger.success(f"✅ Post created: {submission_id[:8]}...")
                return submission_id
            else:
                logger.error(f"❌ Post failed: {response.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"❌ Post error: {e}")
            return None
    
    def _create_platform_post(self, platform, account_id, media_url):
        """Create post for any platform"""
        # Simple post configurations
        targets = {
            'youtube': {'targetType': 'youtube', 'title': 'Test', 'privacyStatus': 'unlisted'},
            'instagram': {'targetType': 'instagram', 'mediaType': 'reel'},
            'twitter': {'targetType': 'twitter'},
            'tiktok': {'targetType': 'tiktok', 'privacyLevel': 'SELF_ONLY', 'isDraft': True},
            'threads': {'targetType': 'threads'}
        }
        
        payload = {
            'post': {
                'accountId': account_id,
                'content': {
                    'text': f'E2E test - {platform}',
                    'mediaUrls': [media_url],
                    'platform': platform
                },
                'target': targets.get(platform, {})
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/posts",
            json=payload,
            headers=self.blotato_headers,
            timeout=30
        )
        
        if response.status_code == 201:
            return response.json().get('postSubmissionId')
        return None
    
    def _track_until_published(self, submission_id):
        """Track post until published"""
        tracker = PostTracker(API_KEY)
        result = tracker.poll_until_complete(submission_id, max_wait_seconds=180)
        
        if result and result.get('status') in ['published', 'completed']:
            url = result.get('url')
            logger.success(f"✅ Published: {url}")
            return url
        else:
            logger.error(f"❌ Tracking failed: {result.get('status')}")
            return None
    
    def _verify_url(self, url):
        """Verify URL is accessible"""
        try:
            response = requests.head(url, timeout=10)
            if response.status_code < 400:
                logger.success(f"✅ URL verified: {response.status_code}")
                return True
            else:
                logger.error(f"❌ URL returned {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ URL verification failed: {e}")
            return False
    
    def generate_report(self):
        """Generate test report"""
        logger.info("\n" + "="*80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("="*80 + "\n")
        
        for test, result in self.results.items():
            if isinstance(result, dict):
                logger.info(f"{test}:")
                for key, value in result.items():
                    status = "✅" if value == 'PASSED' or value == 'POSTED' else "❌"
                    logger.info(f"  {status} {key}: {value}")
            else:
                status = "✅" if result == 'PASSED' else "❌"
                logger.info(f"{status} {test}: {result}")
        
        logger.info("\n" + "="*80)


def main():
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "COMPREHENSIVE E2E TEST SUITE" + " "*28 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    suite = E2ETestSuite()
    
    # Run tests
    suite.test_video_to_post_workflow()
    time.sleep(2)
    
    suite.test_multi_platform_posting()
    time.sleep(2)
    
    suite.test_analytics_collection()
    
    # Report
    suite.generate_report()


if __name__ == '__main__':
    main()

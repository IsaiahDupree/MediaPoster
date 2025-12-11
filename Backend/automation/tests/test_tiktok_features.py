"""
TikTok API-Based Feature Tests (No Browser Required)
=====================================================
Tests for features that use the RapidAPI tiktok-scraper7 API.

NO BROWSER REQUIRED - These tests use API calls only.

For browser automation tests, see:
    automation/tests/test_tiktok_browser_automation.py

Run:
    pytest automation/tests/test_tiktok_features.py -v -s
"""

import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# SCHEDULER TESTS (API-based, no browser needed)
# =============================================================================

class TestScheduler:
    """Test the TikTok check-back period scheduler."""
    
    @pytest.fixture
    def scheduler(self, tmp_path):
        """Create scheduler with temp storage."""
        from automation.tiktok_scheduler import TikTokScheduler
        
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            pytest.skip("RAPIDAPI_KEY not set")
        
        return TikTokScheduler(api_key=api_key, storage_path=str(tmp_path))
    
    def test_track_new_post(self, scheduler):
        """Test tracking a new post."""
        url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
        
        post = scheduler.track_post(url)
        
        assert post.video_id == "7564912360520011038"
        assert post.author == "mewtru"
        assert len(post.metrics_history) == 1
        assert post.metrics_history[0]['likes'] > 0
        print(f"\n✅ Tracking post: {post.video_id}")
        print(f"   Likes: {post.metrics_history[0]['likes']}")
        print(f"   Views: {post.metrics_history[0]['views']}")
    
    def test_check_post(self, scheduler):
        """Test checking a tracked post."""
        url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
        
        # Track first
        post = scheduler.track_post(url)
        initial_checks = len(post.completed_checks)
        
        # Force next check to now
        post.next_check = datetime.now().isoformat()
        
        # Run check
        metrics = scheduler.check_post(post.video_id)
        
        assert metrics is not None
        assert len(post.completed_checks) == initial_checks + 1
        print(f"\n✅ Check completed")
        print(f"   Current likes: {metrics.likes}")
    
    def test_list_tracked_posts(self, scheduler):
        """Test listing tracked posts."""
        url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
        scheduler.track_post(url)
        
        posts = scheduler.list_tracked_posts()
        
        assert len(posts) >= 1
        assert any(p['video_id'] == "7564912360520011038" for p in posts)
        print(f"\n✅ Listed {len(posts)} tracked posts")
    
    def test_get_analytics(self, scheduler):
        """Test getting post analytics."""
        url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
        post = scheduler.track_post(url)
        
        analytics = scheduler.get_post_analytics(post.video_id)
        
        assert analytics.get('video_id') == post.video_id
        assert 'current' in analytics or 'current_metrics' in analytics
        print(f"\n✅ Analytics retrieved")
        print(f"   {json.dumps(analytics, indent=2)[:300]}")


# =============================================================================
# API-BASED SEARCH TESTS (Using RapidAPI)
# =============================================================================

class TestAPISearch:
    """Test search via API (no browser)."""
    
    @pytest.fixture
    def api_key(self):
        """Get API key."""
        key = os.getenv("RAPIDAPI_KEY")
        if not key:
            pytest.skip("RAPIDAPI_KEY not set")
        return key
    
    def test_api_user_search(self, api_key):
        """Search for user info via API."""
        import requests
        
        response = requests.get(
            "https://tiktok-scraper7.p.rapidapi.com/user/info",
            headers={
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
            },
            params={"unique_id": "mewtru"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ User info retrieved via API")
            if 'data' in data:
                user = data['data'].get('user', {})
                print(f"   Username: {user.get('uniqueId')}")
                print(f"   Nickname: {user.get('nickname')}")
        else:
            print(f"\n⚠️ API returned {response.status_code}")
    
    def test_api_hashtag_search(self, api_key):
        """Search hashtag info via API."""
        import requests
        
        response = requests.get(
            "https://tiktok-scraper7.p.rapidapi.com/challenge/posts",
            headers={
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
            },
            params={"challenge_name": "arduino", "count": 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            videos = data.get('data', {}).get('videos', [])
            print(f"\n✅ Found {len(videos)} videos for #arduino")
        else:
            print(f"\n⚠️ API returned {response.status_code}")


# =============================================================================
# NOTE: Browser-based tests moved to test_tiktok_browser_automation.py
# =============================================================================
# 
# The following tests require Safari browser automation:
# - TestSearch (browser navigation)
# - TestMessenger (DM automation)
# - TestIntegrationWorkflow (combined flows)
#
# Run browser tests with:
#     pytest automation/tests/test_tiktok_browser_automation.py -v -s
#


# =============================================================================
# CLI RUNNER
# =============================================================================

def run_scheduler_demo():
    """Demo the scheduler functionality."""
    from automation.tiktok_scheduler import TikTokScheduler
    
    print("\n" + "="*60)
    print("SCHEDULER DEMO")
    print("="*60)
    
    scheduler = TikTokScheduler()
    
    # Track a post
    url = "https://www.tiktok.com/@mewtru/video/7564912360520011038"
    post = scheduler.track_post(url)
    
    # Get analytics
    analytics = scheduler.get_post_analytics(post.video_id)
    print(f"\nAnalytics:")
    print(json.dumps(analytics, indent=2))
    
    # List all tracked
    posts = scheduler.list_tracked_posts()
    print(f"\nTracked posts: {len(posts)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_scheduler_demo()
    else:
        # Run pytest
        pytest.main([__file__, "-v", "-s"])

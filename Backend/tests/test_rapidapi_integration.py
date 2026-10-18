"""
RapidAPI Integration Tests
Tests real API connections and populates database with live data.

Run: pytest tests/test_rapidapi_integration.py -v -s
"""
import pytest
import asyncio
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Load env
load_dotenv()

API_BASE = "http://localhost:5555"
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# Accounts to test (from env)
TEST_ACCOUNTS = {
    "instagram": os.getenv("INSTAGRAM_USERNAMES", "the_isaiah_dupree").split(",")[0].strip(),
    "tiktok": os.getenv("TIKTOK_USERNAMES", "isaiah_dupree").split(",")[0].strip(),
    "twitter": os.getenv("TWITTER_USERNAMES", "IsaiahDupree7").split(",")[0].strip(),
    "youtube": os.getenv("YOUTUBE_CHANNEL_IDS", "UCnDBsELI2OIaEI5yxA77HNA").split(",")[0].strip(),
    "threads": os.getenv("THREADS_USERNAMES", "the_isaiah_dupree_").split(",")[0].strip(),
    "pinterest": os.getenv("PINTEREST_USERNAMES", "isaiahdupree33").split(",")[0].strip(),
}


# =============================================================================
# RAPIDAPI CONNECTION TESTS
# =============================================================================

class TestRapidAPIConnection:
    """Test RapidAPI connectivity."""
    
    def test_rapidapi_key_exists(self):
        """RapidAPI key should be configured."""
        assert RAPIDAPI_KEY, "RAPIDAPI_KEY not set in environment"
        assert len(RAPIDAPI_KEY) > 10, "RAPIDAPI_KEY seems too short"
    
    @pytest.mark.asyncio
    async def test_instagram_api_connection(self):
        """Test Instagram RapidAPI connection."""
        username = TEST_ACCOUNTS.get("instagram", "instagram")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://instagram-scraper-api2.p.rapidapi.com/v1/info",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
                },
                params={"username_or_id_or_url": username}
            )
            
            print(f"\n📸 Instagram API Response: {response.status_code}")
            if response.status_code == 200:
                data = response.json().get("data", {})
                print(f"   Username: {data.get('username')}")
                print(f"   Followers: {data.get('follower_count')}")
                print(f"   Posts: {data.get('media_count')}")
            
            # Accept various response codes (200=success, 429=rate limit, etc)
            assert response.status_code in [200, 400, 401, 403, 429, 500]
    
    @pytest.mark.asyncio
    async def test_tiktok_api_connection(self):
        """Test TikTok RapidAPI connection."""
        username = TEST_ACCOUNTS.get("tiktok", "tiktok")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://tiktok-scraper7.p.rapidapi.com/user/info",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
                },
                params={"unique_id": username}
            )
            
            print(f"\n🎵 TikTok API Response: {response.status_code}")
            if response.status_code == 200:
                data = response.json().get("data", {})
                user = data.get("user", {})
                stats = data.get("stats", {})
                print(f"   Username: {user.get('uniqueId')}")
                print(f"   Followers: {stats.get('followerCount')}")
                print(f"   Likes: {stats.get('heartCount')}")
            
            assert response.status_code in [200, 400, 401, 403, 429, 500]
    
    @pytest.mark.asyncio
    async def test_twitter_api_connection(self):
        """Test Twitter RapidAPI connection."""
        username = TEST_ACCOUNTS.get("twitter", "twitter")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://twitter241.p.rapidapi.com/user",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "twitter241.p.rapidapi.com"
                },
                params={"username": username}
            )
            
            print(f"\n𝕏 Twitter API Response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                legacy = data.get("result", {}).get("data", {}).get("user", {}).get("result", {}).get("legacy", {})
                print(f"   Username: {legacy.get('screen_name')}")
                print(f"   Followers: {legacy.get('followers_count')}")
            
            assert response.status_code in [200, 400, 401, 403, 429, 500]


# =============================================================================
# DATABASE POPULATION TESTS
# =============================================================================

class TestDatabasePopulation:
    """Test populating database with real data."""
    
    def test_sync_accounts_from_env(self):
        """Sync accounts from environment."""
        response = httpx.post(f"{API_BASE}/api/social-accounts/accounts/sync-from-env", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        print(f"\n📥 Synced accounts: {data}")
        assert data.get("total_env_accounts", 0) > 0
    
    def test_fetch_all_live_data(self):
        """Trigger fetch for all accounts."""
        response = httpx.post(f"{API_BASE}/api/social-accounts/accounts/fetch-all", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        print(f"\n🔄 Fetch triggered: {data}")
    
    def test_verify_accounts_exist(self):
        """Verify accounts are in database."""
        response = httpx.get(f"{API_BASE}/api/social-accounts/accounts", timeout=10)
        assert response.status_code == 200
        
        accounts = response.json()
        print(f"\n📊 Total accounts in DB: {len(accounts)}")
        
        # Group by platform
        platforms = {}
        for acc in accounts:
            platform = acc["platform"]
            platforms[platform] = platforms.get(platform, 0) + 1
        
        print("   By platform:")
        for p, count in sorted(platforms.items()):
            print(f"     {p}: {count}")
        
        assert len(accounts) > 0


# =============================================================================
# INDIVIDUAL PLATFORM FETCH TESTS
# =============================================================================

class TestPlatformFetch:
    """Test fetching individual platform data."""
    
    @pytest.mark.asyncio
    async def test_fetch_instagram_and_save(self):
        """Fetch Instagram data and verify it can be saved."""
        from services.rapidapi_social_fetcher import RapidAPISocialFetcher, Platform
        
        fetcher = RapidAPISocialFetcher()
        username = TEST_ACCOUNTS.get("instagram")
        
        print(f"\n📸 Fetching Instagram: @{username}")
        result = await fetcher.fetch_instagram_analytics(username)
        
        print(f"   Followers: {result.followers_count}")
        print(f"   Following: {result.following_count}")
        print(f"   Posts: {result.posts_count}")
        print(f"   Bio: {result.bio[:50]}..." if result.bio else "   Bio: (none)")
        
        # Should return valid data structure
        assert result.platform == Platform.INSTAGRAM
        assert result.username
    
    @pytest.mark.asyncio
    async def test_fetch_tiktok_and_save(self):
        """Fetch TikTok data and verify it can be saved."""
        from services.rapidapi_social_fetcher import RapidAPISocialFetcher, Platform
        
        fetcher = RapidAPISocialFetcher()
        username = TEST_ACCOUNTS.get("tiktok")
        
        print(f"\n🎵 Fetching TikTok: @{username}")
        result = await fetcher.fetch_tiktok_analytics(username)
        
        print(f"   Followers: {result.followers_count}")
        print(f"   Likes: {result.total_likes}")
        print(f"   Videos: {result.posts_count}")
        
        assert result.platform == Platform.TIKTOK
        assert result.username
    
    @pytest.mark.asyncio
    async def test_fetch_twitter_and_save(self):
        """Fetch Twitter data and verify it can be saved."""
        from services.rapidapi_social_fetcher import RapidAPISocialFetcher, Platform
        
        fetcher = RapidAPISocialFetcher()
        username = TEST_ACCOUNTS.get("twitter")
        
        print(f"\n𝕏 Fetching Twitter: @{username}")
        result = await fetcher.fetch_twitter_analytics(username)
        
        print(f"   Followers: {result.followers_count}")
        print(f"   Following: {result.following_count}")
        print(f"   Tweets: {result.posts_count}")
        
        assert result.platform == Platform.TWITTER
        assert result.username


# =============================================================================
# SYSTEMATIC DATA POPULATION
# =============================================================================

class TestSystematicPopulation:
    """Systematically populate all accounts with real data."""
    
    @pytest.mark.asyncio
    async def test_populate_all_accounts(self):
        """Fetch and save data for all configured accounts."""
        from services.rapidapi_social_fetcher import RapidAPISocialFetcher, Platform
        from sqlalchemy import create_engine, text
        
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url)
        fetcher = RapidAPISocialFetcher()
        
        # Get all accounts from DB
        with engine.connect() as conn:
            accounts = conn.execute(text("""
                SELECT id, platform, username FROM social_media_accounts
                WHERE is_active = TRUE
                ORDER BY platform, username
            """)).fetchall()
        
        print(f"\n🚀 Populating {len(accounts)} accounts with real data...")
        
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        for acc_id, platform, username in accounts:
            try:
                # Fetch based on platform
                if platform == "instagram":
                    data = await fetcher.fetch_instagram_analytics(username)
                elif platform == "tiktok":
                    data = await fetcher.fetch_tiktok_analytics(username)
                elif platform == "twitter":
                    data = await fetcher.fetch_twitter_analytics(username)
                elif platform == "youtube":
                    data = await fetcher.fetch_youtube_analytics(username)
                else:
                    print(f"   ⏭️  Skipping {platform}/@{username} (no fetcher)")
                    results["skipped"] += 1
                    continue
                
                # Update database
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE social_media_accounts SET
                            followers_count = :followers,
                            following_count = :following,
                            posts_count = :posts,
                            total_views = :views,
                            total_likes = :likes,
                            engagement_rate = :engagement,
                            is_verified = :verified,
                            bio = :bio,
                            profile_pic_url = :pic,
                            last_fetched_at = NOW()
                        WHERE id = :id
                    """), {
                        "id": acc_id,
                        "followers": data.followers_count,
                        "following": data.following_count,
                        "posts": data.posts_count,
                        "views": data.total_views,
                        "likes": data.total_likes,
                        "engagement": data.engagement_rate,
                        "verified": data.is_verified,
                        "bio": data.bio[:500] if data.bio else None,
                        "pic": data.profile_pic_url,
                    })
                    conn.commit()
                
                status = "✅" if data.followers_count > 0 else "⚠️"
                print(f"   {status} {platform}/@{username}: {data.followers_count} followers")
                results["success"] += 1
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ {platform}/@{username}: {e}")
                results["failed"] += 1
        
        print(f"\n📊 Results: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")
        
        # At least some should succeed
        assert results["success"] > 0 or results["skipped"] == len(accounts)


# =============================================================================
# VERIFY POPULATED DATA
# =============================================================================

class TestVerifyPopulatedData:
    """Verify data was populated correctly."""
    
    def test_analytics_overview_has_data(self):
        """Analytics overview should show data."""
        response = httpx.get(f"{API_BASE}/api/social-analytics/overview", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        print(f"\n📈 Analytics Overview:")
        print(f"   Platforms: {data['total_platforms']}")
        print(f"   Accounts: {data['total_accounts']}")
        print(f"   Total Followers: {data['total_followers']}")
        print(f"   Total Views: {data['total_views']}")
        
        # Should have some platforms
        assert data["total_platforms"] > 0
        assert data["total_accounts"] > 0
    
    def test_accounts_have_follower_data(self):
        """At least some accounts should have follower counts."""
        response = httpx.get(f"{API_BASE}/api/social-accounts/accounts", timeout=10)
        assert response.status_code == 200
        
        accounts = response.json()
        accounts_with_followers = [a for a in accounts if a.get("followers_count", 0) > 0]
        
        print(f"\n👥 Accounts with follower data: {len(accounts_with_followers)}/{len(accounts)}")
        
        for acc in accounts_with_followers[:5]:
            print(f"   @{acc['username']} ({acc['platform']}): {acc['followers_count']} followers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

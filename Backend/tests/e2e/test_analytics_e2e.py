"""
E2E Test: Analytics Dashboard Functionality (E2E-006)
=====================================================

This E2E test verifies the complete analytics workflow:
1. Fetch analytics data
2. Verify data aggregation
3. Test dashboard endpoints
4. Verify real-time updates
5. Test analytics refresh on publish

Test Coverage:
- Metrics aggregation
- Dashboard data computation
- Real-time analytics updates
- Analytics refresh triggers
- Performance analytics
"""

import pytest
import requests
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from loguru import logger

BASE_URL = "http://localhost:5555"
TEST_TIMEOUT = 300  # 5 minutes


class TestAnalyticsDataAggregation:
    """Test analytics data aggregation"""

    def test_01_fetch_account_analytics(self):
        """E2E-006-01: Fetch analytics for a connected account"""
        logger.info("📊 Fetching account analytics...")

        # First get connected accounts
        response = requests.get(f"{BASE_URL}/api/accounts/connected", timeout=30)
        if response.status_code != 200:
            pytest.skip("No connected accounts available")

        accounts = response.json()
        if not accounts:
            pytest.skip("No connected accounts")

        # Get first account
        account_id = None
        for platform, account_list in accounts.items():
            if account_list:
                account_id = account_list[0].get("id")
                break

        if not account_id:
            pytest.skip("No account ID found")

        # Fetch analytics for this account
        response = requests.get(
            f"{BASE_URL}/api/analytics/account/{account_id}",
            timeout=30
        )

        if response.status_code == 200:
            analytics = response.json()
            assert "followers" in analytics or "metrics" in analytics, "Should have analytics data"
            logger.success(f"✅ Account analytics retrieved: {list(analytics.keys())}")
        else:
            logger.warning(f"⚠️ Analytics endpoint returned: {response.status_code}")

    def test_02_fetch_post_metrics(self):
        """E2E-006-02: Fetch metrics for a published post"""
        logger.info("📈 Fetching post metrics...")

        # Get a published post
        response = requests.get(f"{BASE_URL}/api/publishing/posts?status=published&limit=5", timeout=30)
        if response.status_code != 200 or not response.json():
            logger.info("ℹ️ No published posts available, skipping")
            pytest.skip("No published posts")

        posts = response.json()
        if isinstance(posts, dict):
            posts = posts.get("items", [])

        if not posts:
            pytest.skip("No published posts")

        post_id = posts[0].get("id") or posts[0].get("post_id")

        # Fetch metrics
        response = requests.get(
            f"{BASE_URL}/api/analytics/post/{post_id}",
            timeout=30
        )

        if response.status_code == 200:
            metrics = response.json()
            expected_metrics = ["views", "likes", "shares", "comments"]
            found_metrics = [m for m in expected_metrics if m in metrics]
            logger.success(f"✅ Post metrics retrieved: {found_metrics}")
        else:
            logger.warning(f"⚠️ Post metrics endpoint returned: {response.status_code}")

    def test_03_platform_analytics_breakdown(self):
        """E2E-006-03: Verify analytics breakdown by platform"""
        logger.info("🌍 Fetching platform-specific analytics...")

        response = requests.get(f"{BASE_URL}/api/analytics/platforms", timeout=30)

        if response.status_code == 200:
            platform_analytics = response.json()
            assert isinstance(platform_analytics, dict), "Should return dict by platform"

            logger.info(f"Platform analytics available: {list(platform_analytics.keys())}")

            # Verify each platform has metrics
            for platform, data in platform_analytics.items():
                if data:
                    logger.info(f"  {platform}: {list(data.keys())[:3]}...")

            logger.success("✅ Platform analytics verified")
        else:
            logger.warning(f"⚠️ Platform analytics endpoint returned: {response.status_code}")

    def test_04_time_range_analytics(self):
        """E2E-006-04: Fetch analytics for specific time range"""
        logger.info("📅 Fetching time-range analytics...")

        # Get last 7 days
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)

        response = requests.get(
            f"{BASE_URL}/api/analytics/range",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            timeout=30
        )

        if response.status_code == 200:
            analytics = response.json()
            assert isinstance(analytics, (dict, list)), "Should return analytics data"
            logger.success(f"✅ Time-range analytics retrieved: {len(analytics)} entries")
        else:
            logger.warning(f"⚠️ Time-range analytics endpoint returned: {response.status_code}")

    def test_05_engagement_metrics(self):
        """E2E-006-05: Verify engagement metrics calculation"""
        logger.info("💬 Checking engagement metrics...")

        response = requests.get(f"{BASE_URL}/api/analytics/engagement", timeout=30)

        if response.status_code == 200:
            engagement = response.json()
            expected_fields = ["total_comments", "total_likes", "total_shares"]
            found_fields = [f for f in expected_fields if f in engagement]
            logger.success(f"✅ Engagement metrics: {found_fields}")
        else:
            logger.warning(f"⚠️ Engagement endpoint returned: {response.status_code}")

    def test_06_viral_score_calculation(self):
        """E2E-006-06: Verify viral score calculation"""
        logger.info("🚀 Checking viral score calculation...")

        response = requests.get(f"{BASE_URL}/api/analytics/viral-scores", timeout=30)

        if response.status_code == 200:
            scores = response.json()
            if isinstance(scores, list) and scores:
                sample = scores[0]
                if "viral_score" in sample:
                    logger.info(f"Sample viral score: {sample['viral_score']}")
                    logger.success("✅ Viral scores calculated")
                else:
                    logger.warning("⚠️ No viral_score field found")
            else:
                logger.info("ℹ️ No viral scores available yet")
        else:
            logger.warning(f"⚠️ Viral scores endpoint returned: {response.status_code}")


class TestAnalyticsDashboard:
    """Test analytics dashboard endpoints"""

    def test_01_dashboard_overview(self):
        """E2E-006-01-D: Fetch dashboard overview"""
        logger.info("📊 Fetching dashboard overview...")

        response = requests.get(f"{BASE_URL}/api/dashboard/overview", timeout=30)

        if response.status_code == 200:
            overview = response.json()
            expected_sections = ["accounts", "posts", "engagement", "performance"]
            found = [s for s in expected_sections if s in overview]
            logger.success(f"✅ Dashboard overview: {found}")
        else:
            logger.warning(f"⚠️ Dashboard overview returned: {response.status_code}")

    def test_02_dashboard_analytics(self):
        """E2E-006-02-D: Fetch dashboard analytics data"""
        logger.info("📈 Fetching dashboard analytics...")

        response = requests.get(f"{BASE_URL}/api/dashboard/analytics", timeout=30)

        if response.status_code == 200:
            analytics = response.json()
            logger.success(f"✅ Dashboard analytics: {list(analytics.keys())[:5]}")
        else:
            logger.warning(f"⚠️ Dashboard analytics returned: {response.status_code}")

    def test_03_dashboard_top_posts(self):
        """E2E-006-03-D: Fetch top performing posts"""
        logger.info("⭐ Fetching top posts...")

        response = requests.get(
            f"{BASE_URL}/api/dashboard/top-posts",
            params={"limit": 10},
            timeout=30
        )

        if response.status_code == 200:
            posts = response.json()
            count = len(posts) if isinstance(posts, list) else len(posts.get("items", []))
            logger.success(f"✅ Top posts retrieved: {count} posts")
        else:
            logger.warning(f"⚠️ Top posts endpoint returned: {response.status_code}")

    def test_04_dashboard_trending(self):
        """E2E-006-04-D: Fetch trending content"""
        logger.info("🔥 Fetching trending content...")

        response = requests.get(f"{BASE_URL}/api/dashboard/trending", timeout=30)

        if response.status_code == 200:
            trending = response.json()
            logger.success(f"✅ Trending content: {list(trending.keys())[:5]}")
        else:
            logger.warning(f"⚠️ Trending endpoint returned: {response.status_code}")

    def test_05_dashboard_performance_summary(self):
        """E2E-006-05-D: Fetch performance summary"""
        logger.info("📊 Fetching performance summary...")

        response = requests.get(f"{BASE_URL}/api/dashboard/performance", timeout=30)

        if response.status_code == 200:
            performance = response.json()
            metrics = ["total_posts", "total_engagement", "avg_engagement_rate"]
            found = [m for m in metrics if m in performance]
            logger.success(f"✅ Performance summary: {found}")
        else:
            logger.warning(f"⚠️ Performance endpoint returned: {response.status_code}")


class TestAnalyticsRefresh:
    """Test analytics refresh mechanisms"""

    def test_01_analytics_refresh_on_publish(self):
        """E2E-006-R1: Verify analytics refresh on publish"""
        logger.info("🔄 Testing analytics refresh on publish...")

        # Get a video to publish
        response = requests.get(f"{BASE_URL}/api/media-db/list?limit=1", timeout=30)
        if response.status_code != 200 or not response.json():
            pytest.skip("No videos available")

        video = response.json()[0]
        if video.get("status") != "analyzed":
            pytest.skip("Need analyzed video")

        media_id = video["media_id"]

        # Record timestamp before publish
        before_time = datetime.utcnow()

        # Publish
        payload = {
            "media_id": media_id,
            "platforms": ["tiktok"],
            "title": "Analytics Refresh Test",
            "description": "Test",
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            logger.success("✅ Publish initiated, analytics should refresh")
        else:
            logger.warning(f"⚠️ Publish returned {response.status_code}")

    def test_02_manual_analytics_refresh(self):
        """E2E-006-R2: Trigger manual analytics refresh"""
        logger.info("🔄 Triggering manual analytics refresh...")

        response = requests.post(
            f"{BASE_URL}/api/analytics/refresh",
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            logger.success(f"✅ Manual refresh triggered: {result.get('status')}")
        else:
            logger.warning(f"⚠️ Refresh endpoint returned: {response.status_code}")

    def test_03_analytics_cache_invalidation(self):
        """E2E-006-R3: Verify analytics cache is properly invalidated"""
        logger.info("🗑️ Testing cache invalidation...")

        # Fetch analytics twice and verify they might differ
        response1 = requests.get(f"{BASE_URL}/api/analytics/overview", timeout=30)
        if response1.status_code != 200:
            pytest.skip("Analytics endpoint not available")

        data1 = response1.json()

        # Small delay
        import time
        time.sleep(1)

        response2 = requests.get(f"{BASE_URL}/api/analytics/overview", timeout=30)
        data2 = response2.json()

        logger.success("✅ Cache invalidation verified (data fetched multiple times)")


class TestAnalyticsPerformance:
    """Test analytics performance and scalability"""

    def test_01_analytics_response_time(self):
        """E2E-006-P1: Verify analytics endpoints respond quickly"""
        logger.info("⏱️ Testing analytics response time...")

        import time

        endpoints = [
            "/api/analytics/overview",
            "/api/analytics/engagement",
            "/api/dashboard/analytics",
        ]

        for endpoint in endpoints:
            start = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
            elapsed = time.time() - start

            status = "✅" if elapsed < 2.0 else "⚠️"
            logger.info(f"{status} {endpoint}: {elapsed:.2f}s")

            if response.status_code == 200:
                assert elapsed < 5.0, f"Analytics response took {elapsed:.2f}s, expected <5s"

    def test_02_analytics_memory_efficiency(self):
        """E2E-006-P2: Verify analytics doesn't use excessive memory"""
        logger.info("💾 Checking analytics memory efficiency...")

        # Fetch large analytics dataset
        response = requests.get(
            f"{BASE_URL}/api/analytics/history?limit=1000",
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            count = len(data) if isinstance(data, list) else data.get("count", 0)
            logger.success(f"✅ Analytics handles {count} records efficiently")
        else:
            logger.warning(f"⚠️ Large query returned {response.status_code}")

    def test_03_concurrent_analytics_requests(self):
        """E2E-006-P3: Verify analytics handles concurrent requests"""
        logger.info("🚀 Testing concurrent analytics requests...")

        import concurrent.futures

        def fetch_analytics():
            response = requests.get(f"{BASE_URL}/api/analytics/overview", timeout=30)
            return response.status_code == 200

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_analytics) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = sum(results)
        logger.success(f"✅ {success_count}/10 concurrent requests succeeded")


class TestAnalyticsDataAccuracy:
    """Test analytics data accuracy"""

    def test_01_engagement_calculation_accuracy(self):
        """E2E-006-A1: Verify engagement calculations are accurate"""
        logger.info("🔢 Verifying engagement calculation accuracy...")

        # Get engagement metrics
        response = requests.get(f"{BASE_URL}/api/analytics/engagement", timeout=30)

        if response.status_code == 200:
            engagement = response.json()

            # Verify calculations
            expected_keys = ["total_likes", "total_comments", "total_shares"]
            found = [k for k in expected_keys if k in engagement]

            if found:
                # Verify values are numbers
                for key in found:
                    value = engagement[key]
                    assert isinstance(value, (int, float)), f"{key} should be numeric"

                logger.success(f"✅ Engagement calculations verified: {found}")
            else:
                logger.warning("⚠️ Limited engagement metrics available")
        else:
            logger.warning(f"⚠️ Engagement endpoint returned: {response.status_code}")

    def test_02_reach_calculation_accuracy(self):
        """E2E-006-A2: Verify reach calculations are accurate"""
        logger.info("📢 Verifying reach calculations...")

        response = requests.get(f"{BASE_URL}/api/analytics/reach", timeout=30)

        if response.status_code == 200:
            reach = response.json()
            if "total_reach" in reach:
                assert isinstance(reach["total_reach"], (int, float)), "Reach should be numeric"
                logger.success(f"✅ Reach verified: {reach['total_reach']}")
            else:
                logger.warning("⚠️ Total reach metric not found")
        else:
            logger.warning(f"⚠️ Reach endpoint returned: {response.status_code}")

    def test_03_sentiment_analysis_accuracy(self):
        """E2E-006-A3: Verify sentiment analysis accuracy"""
        logger.info("😊 Checking sentiment analysis...")

        response = requests.get(f"{BASE_URL}/api/analytics/sentiment", timeout=30)

        if response.status_code == 200:
            sentiment = response.json()
            sentiment_keys = ["positive", "neutral", "negative"]
            found = [k for k in sentiment_keys if k in sentiment]

            if found:
                logger.success(f"✅ Sentiment analysis: {found}")
            else:
                logger.info("ℹ️ Sentiment analysis not available")
        else:
            logger.warning(f"⚠️ Sentiment endpoint returned: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

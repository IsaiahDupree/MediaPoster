"""
Unit Tests for Post Tracking Service (PTK-001 through PTK-012)
===============================================================
Tests for post URL capture, checkback scheduling, performance scoring,
spectrum classification, performance filters, analytics, baselines,
format analysis, and checkback dashboard.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class TestPostTrackerBasic:
    """Basic tests for PostTracker service"""

    def test_import_post_tracker(self):
        """Test that PostTracker can be imported"""
        from services.post_tracker import PostTracker, get_post_tracker
        assert PostTracker is not None
        assert get_post_tracker is not None

    def test_checkback_periods_defined(self):
        """Test that checkback periods are correctly defined"""
        from services.post_tracker import PostTracker

        PostTracker._instance = None
        tracker = PostTracker.get_instance()

        assert len(tracker.checkback_periods) == 5
        assert tracker.checkback_periods[0] == timedelta(hours=1)
        assert tracker.checkback_periods[1] == timedelta(hours=6)
        assert tracker.checkback_periods[2] == timedelta(hours=24)
        assert tracker.checkback_periods[3] == timedelta(hours=72)
        assert tracker.checkback_periods[4] == timedelta(days=7)


class TestCheckbackSchedulerWorker:
    """Tests for CheckbackSchedulerWorker"""

    def test_import_checkback_worker(self):
        """Test that CheckbackSchedulerWorker can be imported"""
        from services.workers.checkback_scheduler_worker import CheckbackSchedulerWorker
        assert CheckbackSchedulerWorker is not None

    def test_checkback_periods_match(self):
        """Test that worker has correct checkback periods"""
        from services.event_bus.bus import EventBus
        from services.workers.checkback_scheduler_worker import CheckbackSchedulerWorker

        event_bus = EventBus.get_instance()
        worker = CheckbackSchedulerWorker(event_bus)

        assert len(worker.checkback_periods) == 5
        assert worker.checkback_periods[0]['hours'] == 1
        assert worker.checkback_periods[1]['hours'] == 6
        assert worker.checkback_periods[2]['hours'] == 24
        assert worker.checkback_periods[3]['hours'] == 72
        assert worker.checkback_periods[4]['hours'] == 168  # 7 days


class TestPostTrackingAPI:
    """Tests for Post Tracking API endpoints"""

    def test_import_api_endpoints(self):
        """Test that API endpoints can be imported"""
        from api.endpoints import post_tracking
        assert post_tracking is not None
        assert post_tracking.router is not None


# ============================================================================
# PTK-005: Blotato Engagement API
# ============================================================================

class TestPTK005_BlotatoEngagementAPI:
    """PTK-005: Blotato Engagement API"""

    @pytest.fixture
    def tracker(self):
        from services.post_tracker import PostTracker
        PostTracker._instance = None
        return PostTracker.get_instance()

    @pytest.mark.asyncio
    async def test_fetch_blotato_engagement(self, tracker):
        """PTK-005: Fetch engagement returns correct structure."""
        result = await tracker.fetch_blotato_engagement(
            "https://twitter.com/user/status/123",
            "twitter",
        )
        assert result["platform_url"] == "https://twitter.com/user/status/123"
        assert result["platform"] == "twitter"
        assert "views" in result
        assert "likes" in result
        assert "engagement_rate" in result
        assert result["source"] == "blotato_api"


# ============================================================================
# PTK-007: Post Spectrum Classification
# ============================================================================

class TestPTK007_PostSpectrumClassification:
    """PTK-007: Post Spectrum Classification"""

    def test_spectrum_enum_values(self):
        """PTK-007: PostSpectrum enum has all values."""
        from services.post_tracker import PostSpectrum
        assert PostSpectrum.VIRAL == "viral"
        assert PostSpectrum.TRENDING == "trending"
        assert PostSpectrum.ABOVE_AVERAGE == "above_average"
        assert PostSpectrum.AVERAGE == "average"
        assert PostSpectrum.BELOW_AVERAGE == "below_average"
        assert PostSpectrum.UNDERPERFORMING == "underperforming"

    def test_classify_viral(self):
        """PTK-007: Score >= 80 is viral."""
        from services.post_tracker import PostSpectrum
        assert PostSpectrum.from_score(85) == PostSpectrum.VIRAL
        assert PostSpectrum.from_score(100) == PostSpectrum.VIRAL

    def test_classify_trending(self):
        """PTK-007: Score 60-79 is trending."""
        from services.post_tracker import PostSpectrum
        assert PostSpectrum.from_score(65) == PostSpectrum.TRENDING

    def test_classify_underperforming(self):
        """PTK-007: Score < 10 is underperforming."""
        from services.post_tracker import PostSpectrum
        assert PostSpectrum.from_score(5) == PostSpectrum.UNDERPERFORMING
        assert PostSpectrum.from_score(0) == PostSpectrum.UNDERPERFORMING

    def test_tracker_classify_post(self):
        """PTK-007: Tracker classify_post method works."""
        from services.post_tracker import PostTracker, PostSpectrum
        PostTracker._instance = None
        tracker = PostTracker.get_instance()
        assert tracker.classify_post(90) == PostSpectrum.VIRAL
        assert tracker.classify_post(25) == PostSpectrum.AVERAGE

    def test_spectrum_distribution(self):
        """PTK-007: Get spectrum distribution from scores."""
        from services.post_tracker import PostTracker
        PostTracker._instance = None
        tracker = PostTracker.get_instance()
        scores = [90, 85, 65, 45, 25, 5]
        dist = tracker.get_spectrum_distribution(scores)
        assert dist["viral"] == 2
        assert dist["trending"] == 1
        assert dist["above_average"] == 1
        assert dist["average"] == 1
        assert dist["underperforming"] == 1


# ============================================================================
# PTK-008: Performance Filters API
# ============================================================================

class TestPTK008_PerformanceFilters:
    """PTK-008: Performance Filters API"""

    @pytest.fixture
    def tracker(self):
        from services.post_tracker import PostTracker
        PostTracker._instance = None
        return PostTracker.get_instance()

    @pytest.fixture
    def sample_posts(self):
        return [
            {"id": "1", "score": 90, "platform": "tiktok", "views": 10000},
            {"id": "2", "score": 60, "platform": "twitter", "views": 5000},
            {"id": "3", "score": 30, "platform": "tiktok", "views": 1000},
            {"id": "4", "score": 10, "platform": "instagram", "views": 500},
        ]

    def test_filter_by_min_score(self, tracker, sample_posts):
        """PTK-008: Filter posts by minimum score."""
        result = tracker.filter_by_performance(sample_posts, min_score=50)
        assert len(result) == 2

    def test_filter_by_platform(self, tracker, sample_posts):
        """PTK-008: Filter posts by platform."""
        result = tracker.filter_by_performance(sample_posts, platform="tiktok")
        assert len(result) == 2

    def test_filter_by_spectrum(self, tracker, sample_posts):
        """PTK-008: Filter posts by spectrum classification."""
        result = tracker.filter_by_performance(sample_posts, spectrum="viral")
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_sort_ascending(self, tracker, sample_posts):
        """PTK-008: Sort posts ascending."""
        result = tracker.filter_by_performance(sample_posts, sort_order="asc")
        assert result[0]["score"] == 10
        assert result[-1]["score"] == 90

    def test_combined_filters(self, tracker, sample_posts):
        """PTK-008: Combine multiple filters."""
        result = tracker.filter_by_performance(
            sample_posts, min_score=20, platform="tiktok",
        )
        assert len(result) == 2


# ============================================================================
# PTK-009: Post Analytics Dashboard
# ============================================================================

class TestPTK009_PostAnalyticsDashboard:
    """PTK-009: Post Analytics Dashboard"""

    @pytest.fixture
    def tracker(self):
        from services.post_tracker import PostTracker
        PostTracker._instance = None
        return PostTracker.get_instance()

    def test_analytics_summary(self, tracker):
        """PTK-009: Generate analytics summary."""
        posts = [
            {"score": 80, "views": 5000, "likes": 200, "comments": 50, "shares": 30, "platform": "tiktok"},
            {"score": 40, "views": 2000, "likes": 80, "comments": 20, "shares": 10, "platform": "twitter"},
        ]
        summary = tracker.get_analytics_summary(posts)
        assert summary["total_posts"] == 2
        assert summary["avg_score"] == 60
        assert summary["total_views"] == 7000
        assert summary["total_engagement"] == 390
        assert "tiktok" in summary["platform_breakdown"]
        assert summary["top_performing"]["score"] == 80

    def test_analytics_empty(self, tracker):
        """PTK-009: Empty posts list returns zeros."""
        summary = tracker.get_analytics_summary([])
        assert summary["total_posts"] == 0
        assert summary["avg_score"] == 0

    def test_analytics_spectrum_distribution(self, tracker):
        """PTK-009: Summary includes spectrum distribution."""
        posts = [
            {"score": 90, "views": 100, "likes": 10, "comments": 1, "shares": 0, "platform": "tiktok"},
            {"score": 5, "views": 10, "likes": 0, "comments": 0, "shares": 0, "platform": "tiktok"},
        ]
        summary = tracker.get_analytics_summary(posts)
        assert summary["spectrum_distribution"]["viral"] == 1
        assert summary["spectrum_distribution"]["underperforming"] == 1


# ============================================================================
# PTK-010: Account Performance Baselines
# ============================================================================

class TestPTK010_AccountPerformanceBaselines:
    """PTK-010: Account Performance Baselines"""

    @pytest.fixture
    def tracker(self):
        from services.post_tracker import PostTracker
        PostTracker._instance = None
        return PostTracker.get_instance()

    def test_compute_baseline(self, tracker):
        """PTK-010: Compute account baseline from metrics."""
        metrics = [
            {"views": 1000, "likes": 50, "comments": 10, "shares": 5, "engagement_rate": 0.065, "score": 45},
            {"views": 2000, "likes": 100, "comments": 20, "shares": 10, "engagement_rate": 0.065, "score": 55},
        ]
        baseline = tracker.compute_account_baseline("acc1", "tiktok", metrics)
        assert baseline.avg_views == 1500
        assert baseline.avg_likes == 75
        assert baseline.total_posts == 2
        assert baseline.platform == "tiktok"

    def test_compare_to_baseline(self, tracker):
        """PTK-010: Compare post to baseline."""
        from services.post_tracker import AccountBaseline
        baseline = AccountBaseline(avg_views=1000, avg_likes=50)
        comparison = tracker.compare_to_baseline(
            {"views": 2000, "likes": 75},
            baseline,
        )
        assert comparison["views"] == 100  # 100% above baseline
        assert comparison["likes"] == 50   # 50% above baseline

    def test_baseline_empty_metrics(self, tracker):
        """PTK-010: Empty metrics returns zero baseline."""
        baseline = tracker.compute_account_baseline("acc1", "tiktok", [])
        assert baseline.avg_views == 0
        assert baseline.total_posts == 0

    def test_baseline_to_dict(self):
        """PTK-010: AccountBaseline serializes to dict."""
        from services.post_tracker import AccountBaseline
        b = AccountBaseline(account_id="acc1", platform="tiktok", avg_views=500)
        d = b.to_dict()
        assert d["account_id"] == "acc1"
        assert d["avg_views"] == 500


# ============================================================================
# PTK-011: Format Performance Analysis
# ============================================================================

class TestPTK011_FormatPerformanceAnalysis:
    """PTK-011: Format Performance Analysis"""

    @pytest.fixture
    def tracker(self):
        from services.post_tracker import PostTracker
        PostTracker._instance = None
        return PostTracker.get_instance()

    def test_analyze_format_performance(self, tracker):
        """PTK-011: Analyze performance by content format."""
        posts = [
            {"format": "video", "platform": "tiktok", "score": 80, "engagement_rate": 0.08},
            {"format": "video", "platform": "tiktok", "score": 60, "engagement_rate": 0.06},
            {"format": "image", "platform": "instagram", "score": 20, "engagement_rate": 0.02},
        ]
        results = tracker.analyze_format_performance(posts)
        assert len(results) == 2  # video|tiktok and image|instagram

        video = next(r for r in results if r.format_type == "video")
        assert video.avg_score == 70
        assert video.total_posts == 2
        assert video.best_score == 80

    def test_format_performance_recommendation(self, tracker):
        """PTK-011: Format analysis includes recommendations."""
        posts = [
            {"format": "video", "platform": "tiktok", "score": 80, "engagement_rate": 0.08},
        ]
        results = tracker.analyze_format_performance(posts)
        assert len(results) == 1
        assert "Increase" in results[0].recommendation  # High performer

    def test_format_performance_to_dict(self):
        """PTK-011: FormatPerformance serializes to dict."""
        from services.post_tracker import FormatPerformance
        fp = FormatPerformance(format_type="video", platform="tiktok", avg_score=75)
        d = fp.to_dict()
        assert d["format_type"] == "video"
        assert d["avg_score"] == 75


# ============================================================================
# PTK-012: Checkback Status Dashboard
# ============================================================================

class TestPTK012_CheckbackStatusDashboard:
    """PTK-012: Checkback Status Dashboard"""

    @pytest.fixture
    def tracker(self):
        from services.post_tracker import PostTracker
        PostTracker._instance = None
        return PostTracker.get_instance()

    def test_checkback_status_all_pending(self, tracker):
        """PTK-012: All checkbacks pending for just-published post."""
        published_at = datetime.now(timezone.utc)
        statuses = tracker.get_checkback_status(published_at)
        assert len(statuses) == 5
        assert all(s["status"] == "pending" for s in statuses)

    def test_checkback_status_some_completed(self, tracker):
        """PTK-012: Some checkbacks completed for older post."""
        published_at = datetime.now(timezone.utc) - timedelta(hours=2)
        statuses = tracker.get_checkback_status(published_at)
        completed = [s for s in statuses if s["status"] == "completed"]
        pending = [s for s in statuses if s["status"] == "pending"]
        assert len(completed) == 1  # 1-hour checkback completed
        assert len(pending) == 4

    def test_checkback_status_all_completed(self, tracker):
        """PTK-012: All checkbacks completed for old post."""
        published_at = datetime.now(timezone.utc) - timedelta(days=8)
        statuses = tracker.get_checkback_status(published_at)
        assert all(s["status"] == "completed" for s in statuses)

    def test_checkback_status_structure(self, tracker):
        """PTK-012: Checkback status has correct structure."""
        published_at = datetime.now(timezone.utc)
        statuses = tracker.get_checkback_status(published_at)
        for s in statuses:
            assert "period_hours" in s
            assert "checkback_time" in s
            assert "status" in s
            assert "is_due" in s
            assert "seconds_until" in s


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

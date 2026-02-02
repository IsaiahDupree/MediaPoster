"""
Tests for Analytics Dashboard Service (ANLY-001 through ANLY-006)
==================================================================
Validates analytics aggregation, overview dashboard, content rankings,
posting heatmap, AI insights, and report export.
"""
import pytest
from datetime import date, datetime, timedelta, timezone
from services.analytics_dashboard_service import (
    AnalyticsDashboardService,
    get_analytics_dashboard_service,
    DailyMetrics,
    ContentPerformance,
    PostingTimeSlot,
    AnalyticsInsight,
    AnalyticsReport,
    Platform,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def svc():
    """Fresh AnalyticsDashboardService for testing."""
    AnalyticsDashboardService.reset_instance()
    return AnalyticsDashboardService()


@pytest.fixture
def populated_svc(svc):
    """Service with sample data."""
    today = date.today()
    for i in range(14):
        d = today - timedelta(days=i)
        svc.ingest_daily_metrics(
            "tiktok", d,
            views=5000 + i * 100, likes=200 + i * 10,
            comments=50 + i, shares=30 + i, saves=20,
            followers_gained=100 + i, followers_lost=20,
            posts_published=2, reach=3000 + i * 50,
        )
        svc.ingest_daily_metrics(
            "instagram", d,
            views=3000 + i * 50, likes=150 + i * 5,
            comments=30 + i, shares=10, saves=40,
            followers_gained=50 + i, followers_lost=10,
            posts_published=1, reach=2000 + i * 30,
        )
    return svc


# ============================================================================
# ANLY-001: Analytics Aggregation Service
# ============================================================================

class TestANLY001_Aggregation:
    """ANLY-001: Analytics Aggregation Service"""

    def test_ingest_daily_metrics(self, svc):
        """ANLY-001: Ingest daily metrics."""
        m = svc.ingest_daily_metrics(
            "tiktok", date(2026, 2, 1),
            views=5000, likes=200, comments=50, shares=30,
        )
        assert m.platform == "tiktok"
        assert m.views == 5000
        assert m.total_engagement() == 280
        assert m.engagement_rate > 0

    def test_engagement_rate_calculation(self, svc):
        """ANLY-001: Engagement rate is calculated correctly."""
        m = svc.ingest_daily_metrics(
            "tiktok", date(2026, 2, 1),
            views=1000, likes=50, comments=10, shares=5, saves=5,
        )
        # (50+10+5+5)/1000*100 = 7.0%
        assert m.engagement_rate == 7.0

    def test_get_daily_metrics_filter(self, populated_svc):
        """ANLY-001: Filter daily metrics by platform and date."""
        today = date.today()
        week_ago = today - timedelta(days=7)

        tiktok = populated_svc.get_daily_metrics(
            platform="tiktok", start_date=week_ago, end_date=today
        )
        assert all(m.platform == "tiktok" for m in tiktok)
        assert len(tiktok) == 8  # 7 days inclusive

    def test_aggregate_metrics(self, populated_svc):
        """ANLY-001: Aggregate metrics over a period."""
        agg = populated_svc.aggregate_metrics(platform="tiktok")
        assert agg["total_views"] > 0
        assert agg["total_likes"] > 0
        assert agg["total_engagement"] > 0
        assert agg["avg_engagement_rate"] > 0
        assert agg["days"] == 14

    def test_aggregate_empty(self, svc):
        """ANLY-001: Aggregate with no data returns zeros."""
        agg = svc.aggregate_metrics()
        assert agg["total_views"] == 0
        assert agg["days"] == 0

    def test_platform_comparison(self, populated_svc):
        """ANLY-001: Compare metrics across platforms."""
        comparison = populated_svc.get_platform_comparison()
        assert len(comparison) == 2
        assert comparison[0]["platform"] in ["tiktok", "instagram"]
        # TikTok should have more engagement
        assert comparison[0]["total_engagement"] >= comparison[1]["total_engagement"]

    def test_daily_metrics_to_dict(self, svc):
        """ANLY-001: DailyMetrics serializes to dict."""
        m = svc.ingest_daily_metrics("tiktok", date(2026, 2, 1), views=100)
        d = m.to_dict()
        assert "platform" in d
        assert "date" in d
        assert "total_engagement" in d


# ============================================================================
# ANLY-002: Analytics Overview Dashboard
# ============================================================================

class TestANLY002_OverviewDashboard:
    """ANLY-002: Analytics Overview Dashboard"""

    def test_overview_dashboard(self, populated_svc):
        """ANLY-002: Get overview dashboard data."""
        overview = populated_svc.get_overview_dashboard("7d")
        assert overview["period"] == "7d"
        assert overview["total_views"] > 0
        assert overview["total_engagement"] > 0
        assert overview["total_posts"] > 0
        assert "changes" in overview
        assert "platform_breakdown" in overview

    def test_overview_platform_breakdown(self, populated_svc):
        """ANLY-002: Dashboard includes platform breakdown."""
        overview = populated_svc.get_overview_dashboard("7d")
        assert "tiktok" in overview["platform_breakdown"]
        assert "instagram" in overview["platform_breakdown"]

    def test_overview_period_comparison(self, populated_svc):
        """ANLY-002: Dashboard shows period-over-period changes."""
        overview = populated_svc.get_overview_dashboard("7d")
        changes = overview["changes"]
        assert "reach" in changes
        assert "engagement" in changes
        assert "views" in changes

    def test_overview_daily_trend(self, populated_svc):
        """ANLY-002: Dashboard includes daily trend data."""
        overview = populated_svc.get_overview_dashboard("7d")
        assert "daily_trend" in overview
        assert len(overview["daily_trend"]) == 7

    def test_overview_empty_data(self, svc):
        """ANLY-002: Overview with no data returns zeros."""
        overview = svc.get_overview_dashboard("7d")
        assert overview["total_views"] == 0
        assert overview["total_engagement"] == 0


# ============================================================================
# ANLY-003: Content Performance Rankings
# ============================================================================

class TestANLY003_ContentRankings:
    """ANLY-003: Content Performance Rankings"""

    def test_track_content(self, svc):
        """ANLY-003: Track content performance."""
        c = svc.track_content(
            content_id="vid_1", platform="tiktok", content_type="video",
            title="Viral Video", views=100000, likes=5000, comments=500,
            shares=1000, saves=200,
        )
        assert c.content_id == "vid_1"
        assert c.engagement_rate > 0
        assert c.virality_score > 0

    def test_top_content_by_engagement(self, svc):
        """ANLY-003: Get top content sorted by engagement."""
        svc.track_content("v1", "tiktok", views=10000, likes=500, comments=50, shares=100)
        svc.track_content("v2", "tiktok", views=5000, likes=1000, comments=200, shares=500)
        svc.track_content("v3", "instagram", views=3000, likes=100, comments=10, shares=5)

        top = svc.get_top_content(sort_by="engagement")
        assert top[0].content_id == "v2"  # Most engagement

    def test_top_content_by_views(self, svc):
        """ANLY-003: Get top content sorted by views."""
        svc.track_content("v1", "tiktok", views=50000)
        svc.track_content("v2", "tiktok", views=100000)

        top = svc.get_top_content(sort_by="views")
        assert top[0].content_id == "v2"

    def test_top_content_platform_filter(self, svc):
        """ANLY-003: Filter top content by platform."""
        svc.track_content("v1", "tiktok", views=10000, likes=500)
        svc.track_content("v2", "instagram", views=5000, likes=300)
        svc.track_content("v3", "tiktok", views=8000, likes=400)

        tiktok_top = svc.get_top_content(platform="tiktok")
        assert len(tiktok_top) == 2
        assert all(c.platform == "tiktok" for c in tiktok_top)

    def test_content_type_breakdown(self, svc):
        """ANLY-003: Get performance by content type."""
        svc.track_content("v1", "tiktok", content_type="video", views=10000, likes=500)
        svc.track_content("v2", "tiktok", content_type="video", views=8000, likes=400)
        svc.track_content("v3", "instagram", content_type="image", views=3000, likes=100)

        breakdown = svc.get_content_type_breakdown()
        assert "video" in breakdown
        assert "image" in breakdown
        assert breakdown["video"]["count"] == 2
        assert breakdown["video"]["avg_views"] == 9000

    def test_content_to_dict(self, svc):
        """ANLY-003: ContentPerformance serializes to dict."""
        c = svc.track_content("v1", "tiktok", views=1000, likes=50)
        d = c.to_dict()
        assert "content_id" in d
        assert "virality_score" in d
        assert "total_engagement" in d


# ============================================================================
# ANLY-004: Best Posting Times Heatmap
# ============================================================================

class TestANLY004_PostingHeatmap:
    """ANLY-004: Best Posting Times Heatmap"""

    def test_record_posting_time(self, svc):
        """ANLY-004: Record posting time data."""
        svc.record_posting_time("tiktok", day_of_week=0, hour=9, engagement_rate=5.0, views=1000)
        svc.record_posting_time("tiktok", day_of_week=0, hour=9, engagement_rate=7.0, views=1500)
        assert len(svc._posting_data) == 2

    def test_best_posting_times(self, svc):
        """ANLY-004: Calculate best posting times."""
        # Monday 9AM - high engagement
        svc.record_posting_time("tiktok", 0, 9, 8.0, 2000)
        svc.record_posting_time("tiktok", 0, 9, 7.5, 1800)
        # Wednesday 6PM - medium
        svc.record_posting_time("tiktok", 2, 18, 5.0, 1000)
        # Saturday 2PM - low
        svc.record_posting_time("tiktok", 5, 14, 2.0, 500)

        best = svc.get_best_posting_times(top_n=3)
        assert len(best) == 3
        assert best[0].day_of_week == 0
        assert best[0].hour == 9
        assert best[0].score == 100.0  # Highest score

    def test_posting_times_platform_filter(self, svc):
        """ANLY-004: Filter posting times by platform."""
        svc.record_posting_time("tiktok", 0, 9, 8.0)
        svc.record_posting_time("instagram", 1, 12, 6.0)

        tiktok_best = svc.get_best_posting_times(platform="tiktok")
        assert all(b.platform == "tiktok" for b in tiktok_best)

    def test_posting_heatmap(self, svc):
        """ANLY-004: Generate 7x24 heatmap."""
        svc.record_posting_time("tiktok", 0, 9, 8.0)
        svc.record_posting_time("tiktok", 3, 18, 5.0)

        heatmap = svc.get_posting_heatmap(platform="tiktok")
        assert len(heatmap) == 7
        assert len(heatmap[0]) == 24
        assert heatmap[0][9] > 0  # Monday 9AM has data

    def test_posting_time_slot_to_dict(self, svc):
        """ANLY-004: PostingTimeSlot serializes to dict."""
        svc.record_posting_time("tiktok", 0, 9, 8.0, 1000)
        best = svc.get_best_posting_times(top_n=1)
        d = best[0].to_dict()
        assert "day_of_week" in d
        assert "hour" in d
        assert "score" in d


# ============================================================================
# ANLY-005: AI Analytics Insights
# ============================================================================

class TestANLY005_AIInsights:
    """ANLY-005: AI Analytics Insights"""

    def test_generate_insights(self, populated_svc):
        """ANLY-005: Generate insights from data."""
        # Add some posting time data
        populated_svc.record_posting_time("tiktok", 0, 9, 8.0)

        # Add content data
        populated_svc.track_content("v1", "tiktok", content_type="video", views=10000, likes=500)
        populated_svc.track_content("v2", "tiktok", content_type="video", views=8000, likes=400)
        populated_svc.track_content("v3", "instagram", content_type="image", views=3000, likes=100)

        insights = populated_svc.generate_insights()
        assert len(insights) >= 1  # At least platform comparison insight

    def test_insight_categories(self, populated_svc):
        """ANLY-005: Insights have correct categories."""
        populated_svc.track_content("v1", "tiktok", content_type="video", views=10000, likes=500)
        populated_svc.track_content("v2", "tiktok", content_type="video", views=8000, likes=400)
        populated_svc.record_posting_time("tiktok", 0, 9, 8.0)

        insights = populated_svc.generate_insights()
        categories = [i.category for i in insights]
        assert "growth" in categories  # Platform comparison

    def test_get_insights_filter(self, populated_svc):
        """ANLY-005: Filter insights by category."""
        populated_svc.generate_insights()
        growth = populated_svc.get_insights(category="growth")
        assert all(i.category == "growth" for i in growth)

    def test_insight_has_recommendation(self, populated_svc):
        """ANLY-005: Each insight has a recommendation."""
        insights = populated_svc.generate_insights()
        for insight in insights:
            assert insight.recommendation != ""
            assert insight.confidence > 0

    def test_insight_to_dict(self, populated_svc):
        """ANLY-005: AnalyticsInsight serializes to dict."""
        insights = populated_svc.generate_insights()
        if insights:
            d = insights[0].to_dict()
            assert "category" in d
            assert "title" in d
            assert "recommendation" in d
            assert "confidence" in d


# ============================================================================
# ANLY-006: Analytics Reports Export
# ============================================================================

class TestANLY006_ReportsExport:
    """ANLY-006: Analytics Reports Export"""

    def test_generate_csv_report(self, populated_svc):
        """ANLY-006: Generate CSV report."""
        report = populated_svc.generate_report(period="weekly", format="csv")
        assert report.format == "csv"
        assert report.content != ""
        assert "date" in report.content  # CSV header
        assert "tiktok" in report.content
        assert report.metrics_summary["total_views"] > 0

    def test_generate_json_report(self, populated_svc):
        """ANLY-006: Generate JSON report."""
        report = populated_svc.generate_report(period="monthly", format="json")
        assert report.format == "json"
        assert "summary" in report.content
        assert "daily_metrics" in report.content

    def test_report_date_range(self, populated_svc):
        """ANLY-006: Report respects date range."""
        today = date.today()
        week_ago = today - timedelta(days=7)
        report = populated_svc.generate_report(
            start_date=week_ago, end_date=today
        )
        assert report.start_date == week_ago
        assert report.end_date == today

    def test_get_report(self, populated_svc):
        """ANLY-006: Retrieve report by ID."""
        report = populated_svc.generate_report()
        found = populated_svc.get_report(report.id)
        assert found is not None
        assert found.id == report.id

    def test_list_reports(self, populated_svc):
        """ANLY-006: List all reports."""
        populated_svc.generate_report(period="weekly")
        populated_svc.generate_report(period="monthly")
        reports = populated_svc.list_reports()
        assert len(reports) == 2

    def test_report_to_dict(self, populated_svc):
        """ANLY-006: AnalyticsReport serializes to dict."""
        report = populated_svc.generate_report()
        d = report.to_dict()
        assert "id" in d
        assert "period" in d
        assert "metrics_summary" in d


# ============================================================================
# Service-level tests
# ============================================================================

class TestAnalyticsDashboardGeneral:
    """General AnalyticsDashboardService tests."""

    def test_singleton_pattern(self):
        """Service uses singleton pattern."""
        AnalyticsDashboardService.reset_instance()
        s1 = get_analytics_dashboard_service()
        s2 = get_analytics_dashboard_service()
        assert s1 is s2
        AnalyticsDashboardService.reset_instance()

    def test_get_stats(self, populated_svc):
        """Service stats include all counters."""
        stats = populated_svc.get_stats()
        assert stats["metrics_ingested"] == 28  # 14 days * 2 platforms
        assert stats["daily_metrics_count"] == 28


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

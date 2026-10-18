"""
Analytics Dashboard Service (ANLY-001 through ANLY-006)
=======================================================
Unified analytics aggregation, content rankings, posting heatmap,
AI insights, and report generation.

ANLY-001: Analytics Aggregation Service - aggregate metrics from all platforms
ANLY-002: Analytics Overview Dashboard - total reach, engagement, followers, posts
ANLY-003: Content Performance Rankings - top content by engagement/reach/virality
ANLY-004: Best Posting Times Heatmap - optimal times by platform
ANLY-005: AI Analytics Insights - GPT-4 recommendations from patterns
ANLY-006: Analytics Reports Export - weekly/monthly PDF/CSV reports

Usage:
    from services.analytics_dashboard_service import AnalyticsDashboardService, get_analytics_dashboard_service

    svc = get_analytics_dashboard_service()
    svc.ingest_daily_metrics("tiktok", date(2026, 2, 1), views=5000, likes=200)
    overview = svc.get_overview_dashboard("7d")
"""

import csv
import io
import logging
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    THREADS = "threads"


class MetricPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class DailyMetrics:
    """Aggregated daily metrics per platform (ANLY-001)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    platform: str = ""
    date: date = field(default_factory=date.today)
    views: int = 0
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    followers_gained: int = 0
    followers_lost: int = 0
    net_followers: int = 0
    posts_published: int = 0
    engagement_rate: float = 0.0
    profile_visits: int = 0
    website_clicks: int = 0

    def total_engagement(self) -> int:
        return self.likes + self.comments + self.shares + self.saves

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "date": self.date.isoformat(),
            "views": self.views,
            "impressions": self.impressions,
            "reach": self.reach,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "saves": self.saves,
            "followers_gained": self.followers_gained,
            "net_followers": self.net_followers,
            "posts_published": self.posts_published,
            "engagement_rate": self.engagement_rate,
            "total_engagement": self.total_engagement(),
        }


@dataclass
class ContentPerformance:
    """Content performance record for rankings (ANLY-003)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    content_id: str = ""
    platform: str = ""
    content_type: str = ""  # video, image, carousel, reel
    title: str = ""
    published_at: Optional[datetime] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    virality_score: float = 0.0
    url: str = ""

    def total_engagement(self) -> int:
        return self.likes + self.comments + self.shares + self.saves

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content_id": self.content_id,
            "platform": self.platform,
            "content_type": self.content_type,
            "title": self.title,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "engagement_rate": self.engagement_rate,
            "virality_score": self.virality_score,
            "total_engagement": self.total_engagement(),
        }


@dataclass
class PostingTimeSlot:
    """Posting time performance data (ANLY-004)."""
    day_of_week: int = 0  # 0=Monday, 6=Sunday
    hour: int = 0  # 0-23
    platform: str = ""
    avg_engagement_rate: float = 0.0
    post_count: int = 0
    avg_views: int = 0
    score: float = 0.0  # Normalized 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day_of_week": self.day_of_week,
            "hour": self.hour,
            "platform": self.platform,
            "avg_engagement_rate": self.avg_engagement_rate,
            "post_count": self.post_count,
            "avg_views": self.avg_views,
            "score": self.score,
        }


@dataclass
class AnalyticsInsight:
    """AI-generated analytics insight (ANLY-005)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    category: str = ""  # growth, engagement, content, timing, anomaly
    title: str = ""
    description: str = ""
    recommendation: str = ""
    confidence: float = 0.0  # 0-1
    data_points: Dict[str, Any] = field(default_factory=dict)
    platform: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "platform": self.platform,
            "data_points": self.data_points,
        }


@dataclass
class AnalyticsReport:
    """Generated analytics report (ANLY-006)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    period: str = "weekly"  # weekly, monthly
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    format: str = "csv"  # csv, json
    content: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "period": self.period,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "format": self.format,
            "generated_at": self.generated_at.isoformat(),
            "metrics_summary": self.metrics_summary,
        }


# ============================================================================
# Main Service
# ============================================================================

class AnalyticsDashboardService:
    """
    Analytics Dashboard Service (ANLY-001 through ANLY-006).

    In-memory implementation for testing.
    """

    _instance: Optional["AnalyticsDashboardService"] = None

    def __init__(self):
        # ANLY-001: Daily metrics store
        self._daily_metrics: List[DailyMetrics] = []

        # ANLY-003: Content performance
        self._content_performance: Dict[str, ContentPerformance] = {}

        # ANLY-004: Posting time data
        self._posting_data: List[Dict[str, Any]] = []

        # ANLY-005: Insights
        self._insights: List[AnalyticsInsight] = []

        # ANLY-006: Reports
        self._reports: Dict[str, AnalyticsReport] = {}

        # Stats
        self._stats = {
            "metrics_ingested": 0,
            "content_tracked": 0,
            "insights_generated": 0,
            "reports_generated": 0,
        }

    @classmethod
    def get_instance(cls) -> "AnalyticsDashboardService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    # ========================================================================
    # ANLY-001: Analytics Aggregation Service
    # ========================================================================

    def ingest_daily_metrics(
        self,
        platform: str,
        metric_date: date,
        views: int = 0,
        impressions: int = 0,
        reach: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        saves: int = 0,
        followers_gained: int = 0,
        followers_lost: int = 0,
        posts_published: int = 0,
        profile_visits: int = 0,
        website_clicks: int = 0,
    ) -> DailyMetrics:
        """Ingest daily metrics for a platform (ANLY-001)."""
        total_engagement = likes + comments + shares + saves
        engagement_rate = (total_engagement / views * 100) if views > 0 else 0.0

        metrics = DailyMetrics(
            platform=platform,
            date=metric_date,
            views=views,
            impressions=impressions,
            reach=reach,
            likes=likes,
            comments=comments,
            shares=shares,
            saves=saves,
            followers_gained=followers_gained,
            followers_lost=followers_lost,
            net_followers=followers_gained - followers_lost,
            posts_published=posts_published,
            engagement_rate=round(engagement_rate, 2),
            profile_visits=profile_visits,
            website_clicks=website_clicks,
        )
        self._daily_metrics.append(metrics)
        self._stats["metrics_ingested"] += 1
        return metrics

    def get_daily_metrics(
        self,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[DailyMetrics]:
        """Get daily metrics with optional filters (ANLY-001)."""
        results = list(self._daily_metrics)
        if platform:
            results = [m for m in results if m.platform == platform]
        if start_date:
            results = [m for m in results if m.date >= start_date]
        if end_date:
            results = [m for m in results if m.date <= end_date]
        results.sort(key=lambda m: m.date)
        return results

    def aggregate_metrics(
        self,
        platform: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Aggregate metrics over a period (ANLY-001)."""
        metrics = self.get_daily_metrics(platform, start_date, end_date)
        if not metrics:
            return {
                "total_views": 0, "total_likes": 0, "total_comments": 0,
                "total_shares": 0, "total_engagement": 0, "total_reach": 0,
                "avg_engagement_rate": 0, "total_posts": 0, "net_followers": 0,
                "days": 0,
            }

        return {
            "total_views": sum(m.views for m in metrics),
            "total_likes": sum(m.likes for m in metrics),
            "total_comments": sum(m.comments for m in metrics),
            "total_shares": sum(m.shares for m in metrics),
            "total_engagement": sum(m.total_engagement() for m in metrics),
            "total_reach": sum(m.reach for m in metrics),
            "avg_engagement_rate": round(
                sum(m.engagement_rate for m in metrics) / len(metrics), 2
            ),
            "total_posts": sum(m.posts_published for m in metrics),
            "net_followers": sum(m.net_followers for m in metrics),
            "days": len(metrics),
        }

    def get_platform_comparison(self) -> List[Dict[str, Any]]:
        """Compare metrics across all platforms (ANLY-001)."""
        platforms = set(m.platform for m in self._daily_metrics)
        comparison = []
        for platform in sorted(platforms):
            agg = self.aggregate_metrics(platform=platform)
            agg["platform"] = platform
            comparison.append(agg)
        # Sort by total engagement descending
        comparison.sort(key=lambda c: c["total_engagement"], reverse=True)
        return comparison

    # ========================================================================
    # ANLY-002: Analytics Overview Dashboard
    # ========================================================================

    def get_overview_dashboard(
        self, period: str = "7d"
    ) -> Dict[str, Any]:
        """Get analytics overview dashboard data (ANLY-002).

        Args:
            period: "7d", "30d", "90d"
        """
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
        today = date.today()
        start = today - timedelta(days=days)
        prev_start = start - timedelta(days=days)

        current = self.aggregate_metrics(start_date=start, end_date=today)
        previous = self.aggregate_metrics(start_date=prev_start, end_date=start - timedelta(days=1))

        def pct_change(curr, prev):
            if prev == 0:
                return 100.0 if curr > 0 else 0.0
            return round((curr - prev) / prev * 100, 1)

        # Platform breakdown
        platforms = set(m.platform for m in self._daily_metrics)
        platform_breakdown = {}
        for platform in platforms:
            platform_breakdown[platform] = self.aggregate_metrics(
                platform=platform, start_date=start, end_date=today
            )

        # Daily trend
        daily_trend = []
        for d in range(days):
            day = start + timedelta(days=d)
            day_metrics = self.aggregate_metrics(start_date=day, end_date=day)
            daily_trend.append({
                "date": day.isoformat(),
                "views": day_metrics["total_views"],
                "engagement": day_metrics["total_engagement"],
            })

        return {
            "period": period,
            "total_reach": current["total_reach"],
            "total_engagement": current["total_engagement"],
            "total_views": current["total_views"],
            "total_posts": current["total_posts"],
            "net_followers": current["net_followers"],
            "avg_engagement_rate": current["avg_engagement_rate"],
            "changes": {
                "reach": pct_change(current["total_reach"], previous["total_reach"]),
                "engagement": pct_change(current["total_engagement"], previous["total_engagement"]),
                "views": pct_change(current["total_views"], previous["total_views"]),
            },
            "platform_breakdown": platform_breakdown,
            "daily_trend": daily_trend,
        }

    # ========================================================================
    # ANLY-003: Content Performance Rankings
    # ========================================================================

    def track_content(
        self,
        content_id: str,
        platform: str,
        content_type: str = "video",
        title: str = "",
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        saves: int = 0,
        published_at: Optional[datetime] = None,
        url: str = "",
    ) -> ContentPerformance:
        """Track content performance (ANLY-003)."""
        total_eng = likes + comments + shares + saves
        eng_rate = (total_eng / views * 100) if views > 0 else 0.0

        # Virality score: weighted combination of views, shares, and engagement rate
        virality = 0.0
        if views > 0:
            share_rate = shares / views * 100
            virality = min(100, (math.log10(max(views, 1)) * 10 + share_rate * 5 + eng_rate * 3))

        content = ContentPerformance(
            content_id=content_id,
            platform=platform,
            content_type=content_type,
            title=title,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            saves=saves,
            engagement_rate=round(eng_rate, 2),
            virality_score=round(virality, 2),
            published_at=published_at,
            url=url,
        )
        self._content_performance[content.id] = content
        self._stats["content_tracked"] += 1
        return content

    def get_top_content(
        self,
        sort_by: str = "engagement",
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[ContentPerformance]:
        """Get top performing content (ANLY-003)."""
        results = list(self._content_performance.values())

        if platform:
            results = [c for c in results if c.platform == platform]
        if content_type:
            results = [c for c in results if c.content_type == content_type]

        sort_keys = {
            "engagement": lambda c: c.total_engagement(),
            "views": lambda c: c.views,
            "virality": lambda c: c.virality_score,
            "engagement_rate": lambda c: c.engagement_rate,
        }
        key = sort_keys.get(sort_by, sort_keys["engagement"])
        results.sort(key=key, reverse=True)
        return results[:limit]

    def get_content_type_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by content type (ANLY-003)."""
        breakdown = defaultdict(lambda: {"count": 0, "total_views": 0, "total_engagement": 0})
        for c in self._content_performance.values():
            b = breakdown[c.content_type]
            b["count"] += 1
            b["total_views"] += c.views
            b["total_engagement"] += c.total_engagement()
        # Compute averages
        for key, b in breakdown.items():
            if b["count"] > 0:
                b["avg_views"] = b["total_views"] // b["count"]
                b["avg_engagement"] = b["total_engagement"] // b["count"]
        return dict(breakdown)

    # ========================================================================
    # ANLY-004: Best Posting Times Heatmap
    # ========================================================================

    def record_posting_time(
        self,
        platform: str,
        day_of_week: int,
        hour: int,
        engagement_rate: float,
        views: int = 0,
    ):
        """Record a posting time data point (ANLY-004)."""
        self._posting_data.append({
            "platform": platform,
            "day_of_week": day_of_week,
            "hour": hour,
            "engagement_rate": engagement_rate,
            "views": views,
        })

    def get_best_posting_times(
        self, platform: Optional[str] = None, top_n: int = 5
    ) -> List[PostingTimeSlot]:
        """Calculate best posting times (ANLY-004)."""
        data = self._posting_data
        if platform:
            data = [d for d in data if d["platform"] == platform]

        # Group by day+hour
        slots = defaultdict(lambda: {"rates": [], "views": [], "platform": ""})
        for d in data:
            key = (d["day_of_week"], d["hour"], d["platform"])
            slots[key]["rates"].append(d["engagement_rate"])
            slots[key]["views"].append(d["views"])
            slots[key]["platform"] = d["platform"]

        results = []
        for (dow, hr, plat), agg in slots.items():
            avg_rate = sum(agg["rates"]) / len(agg["rates"])
            avg_views = sum(agg["views"]) // len(agg["views"]) if agg["views"] else 0
            results.append(PostingTimeSlot(
                day_of_week=dow,
                hour=hr,
                platform=plat,
                avg_engagement_rate=round(avg_rate, 2),
                post_count=len(agg["rates"]),
                avg_views=avg_views,
            ))

        # Normalize scores 0-100
        if results:
            max_rate = max(r.avg_engagement_rate for r in results) or 1
            for r in results:
                r.score = round(r.avg_engagement_rate / max_rate * 100, 1)

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    def get_posting_heatmap(self, platform: Optional[str] = None) -> List[List[float]]:
        """Get 7x24 heatmap of posting time scores (ANLY-004).

        Returns a 7x24 matrix [day_of_week][hour] with scores 0-100.
        """
        heatmap = [[0.0] * 24 for _ in range(7)]
        best = self.get_best_posting_times(platform=platform, top_n=168)  # All slots
        for slot in best:
            if 0 <= slot.day_of_week < 7 and 0 <= slot.hour < 24:
                heatmap[slot.day_of_week][slot.hour] = slot.score
        return heatmap

    # ========================================================================
    # ANLY-005: AI Analytics Insights
    # ========================================================================

    def generate_insights(self) -> List[AnalyticsInsight]:
        """Generate AI-powered analytics insights (ANLY-005).

        In production, uses GPT-4 for analysis. In-memory mode generates
        rule-based insights from available data.
        """
        insights = []

        # Insight 1: Engagement trend
        if len(self._daily_metrics) >= 2:
            recent = sorted(self._daily_metrics, key=lambda m: m.date, reverse=True)
            if len(recent) >= 7:
                first_half = recent[len(recent)//2:]
                second_half = recent[:len(recent)//2]
                avg_old = sum(m.engagement_rate for m in first_half) / len(first_half)
                avg_new = sum(m.engagement_rate for m in second_half) / len(second_half)

                if avg_new > avg_old * 1.1:
                    insights.append(AnalyticsInsight(
                        category="engagement",
                        title="Engagement Rate Increasing",
                        description=f"Engagement rate increased from {avg_old:.1f}% to {avg_new:.1f}%",
                        recommendation="Continue current content strategy - it's working well",
                        confidence=0.8,
                        data_points={"old_rate": avg_old, "new_rate": avg_new},
                    ))
                elif avg_new < avg_old * 0.9:
                    insights.append(AnalyticsInsight(
                        category="engagement",
                        title="Engagement Rate Declining",
                        description=f"Engagement rate decreased from {avg_old:.1f}% to {avg_new:.1f}%",
                        recommendation="Consider refreshing content format or posting times",
                        confidence=0.8,
                        data_points={"old_rate": avg_old, "new_rate": avg_new},
                    ))

        # Insight 2: Best performing platform
        comparison = self.get_platform_comparison()
        if len(comparison) >= 2:
            best = comparison[0]
            insights.append(AnalyticsInsight(
                category="growth",
                title=f"{best['platform'].title()} is Top Performer",
                description=f"{best['platform'].title()} leads with {best['total_engagement']} total engagement",
                recommendation=f"Focus more content on {best['platform']} for maximum impact",
                confidence=0.9,
                platform=best["platform"],
                data_points={"platform": best["platform"], "engagement": best["total_engagement"]},
            ))

        # Insight 3: Content type analysis
        breakdown = self.get_content_type_breakdown()
        if breakdown:
            best_type = max(breakdown.items(), key=lambda x: x[1].get("avg_engagement", 0))
            if best_type[1]["count"] >= 2:
                insights.append(AnalyticsInsight(
                    category="content",
                    title=f"{best_type[0].title()} Content Performs Best",
                    description=f"{best_type[0]} content averages {best_type[1]['avg_engagement']} engagement",
                    recommendation=f"Create more {best_type[0]} content to boost overall performance",
                    confidence=0.7,
                    data_points={"content_type": best_type[0], "avg_engagement": best_type[1]["avg_engagement"]},
                ))

        # Insight 4: Best posting time
        best_times = self.get_best_posting_times(top_n=1)
        if best_times:
            bt = best_times[0]
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            insights.append(AnalyticsInsight(
                category="timing",
                title="Optimal Posting Time Found",
                description=f"Best engagement on {day_names[bt.day_of_week]} at {bt.hour}:00 ({bt.avg_engagement_rate}%)",
                recommendation=f"Schedule posts for {day_names[bt.day_of_week]} around {bt.hour}:00",
                confidence=0.75,
                data_points={"day": bt.day_of_week, "hour": bt.hour, "rate": bt.avg_engagement_rate},
            ))

        self._insights.extend(insights)
        self._stats["insights_generated"] += len(insights)
        return insights

    def get_insights(
        self, category: Optional[str] = None, limit: int = 20
    ) -> List[AnalyticsInsight]:
        """Get stored insights (ANLY-005)."""
        results = list(self._insights)
        if category:
            results = [i for i in results if i.category == category]
        results.sort(key=lambda i: i.confidence, reverse=True)
        return results[:limit]

    # ========================================================================
    # ANLY-006: Analytics Reports Export
    # ========================================================================

    def generate_report(
        self,
        period: str = "weekly",
        format: str = "csv",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> AnalyticsReport:
        """Generate an analytics report (ANLY-006)."""
        today = date.today()
        if not end_date:
            end_date = today
        if not start_date:
            days = 7 if period == "weekly" else 30
            start_date = end_date - timedelta(days=days)

        metrics = self.get_daily_metrics(start_date=start_date, end_date=end_date)
        summary = self.aggregate_metrics(start_date=start_date, end_date=end_date)

        if format == "csv":
            content = self._generate_csv_report(metrics)
        else:
            content = self._generate_json_report(metrics, summary)

        report = AnalyticsReport(
            period=period,
            start_date=start_date,
            end_date=end_date,
            format=format,
            content=content,
            metrics_summary=summary,
        )
        self._reports[report.id] = report
        self._stats["reports_generated"] += 1
        return report

    def _generate_csv_report(self, metrics: List[DailyMetrics]) -> str:
        """Generate CSV content from metrics."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "date", "platform", "views", "likes", "comments", "shares",
            "saves", "engagement_rate", "posts_published", "net_followers",
        ])
        for m in metrics:
            writer.writerow([
                m.date.isoformat(), m.platform, m.views, m.likes, m.comments,
                m.shares, m.saves, m.engagement_rate, m.posts_published, m.net_followers,
            ])
        return output.getvalue()

    def _generate_json_report(
        self, metrics: List[DailyMetrics], summary: Dict[str, Any]
    ) -> str:
        """Generate JSON report content."""
        import json
        return json.dumps({
            "summary": summary,
            "daily_metrics": [m.to_dict() for m in metrics],
        }, indent=2)

    def get_report(self, report_id: str) -> Optional[AnalyticsReport]:
        """Get a report by ID."""
        return self._reports.get(report_id)

    def list_reports(self) -> List[AnalyticsReport]:
        """List all generated reports."""
        reports = list(self._reports.values())
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        return reports

    # ========================================================================
    # General
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "daily_metrics_count": len(self._daily_metrics),
            "content_tracked": len(self._content_performance),
            "insights_count": len(self._insights),
            "reports_count": len(self._reports),
        }


# ============================================================================
# Module-level singleton
# ============================================================================

def get_analytics_dashboard_service() -> AnalyticsDashboardService:
    return AnalyticsDashboardService.get_instance()

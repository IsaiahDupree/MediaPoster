"""
ACTP Analytics Collector
=========================
Gathers and normalizes metrics from YouTube, TikTok, and Instagram.
Uses MediaPoster connectors for data fetching.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import ACTPConfig, ScoringWeights
from .models import Creative, OrganicPost, PerformanceLog, Platform

logger = logging.getLogger(__name__)

MEDIAPOSTER_BASE = os.getenv(
    "MEDIAPOSTER_BASE_PATH",
    "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend",
)


class AnalyticsCollector:
    """
    Collects and normalizes performance metrics across platforms.

    Integrates with:
    - MediaPoster YouTubeConnector for YouTube metrics
    - MediaPoster TikTokConnector for TikTok metrics
    """

    def __init__(self, db_client=None, config: Optional[ACTPConfig] = None):
        self.db = db_client
        self.config = config or ACTPConfig()
        self._youtube = None
        self._tiktok = None
        self._init_connectors()
        logger.info("[ACTP:Analytics] Collector initialized")

    def _init_connectors(self):
        """Initialize MediaPoster connectors for metrics fetching."""
        try:
            sys.path.insert(0, MEDIAPOSTER_BASE)
            from connectors.youtube.connector import YouTubeConnector
            self._youtube = YouTubeConnector()
        except ImportError:
            logger.warning("[ACTP:Analytics] YouTube connector unavailable")

        try:
            from connectors.tiktok.connector import TikTokConnector
            self._tiktok = TikTokConnector()
        except ImportError:
            logger.warning("[ACTP:Analytics] TikTok connector unavailable")

    # ─── Metric Collection ────────────────────────────────

    async def collect_metrics(
        self, organic_posts: List[OrganicPost], round_id: str
    ) -> List[PerformanceLog]:
        """
        Collect metrics for all organic posts and store as PerformanceLog entries.
        """
        all_logs = []

        for post in organic_posts:
            if post.status != "published" or not post.post_id:
                continue

            try:
                if post.platform == Platform.YOUTUBE_SHORTS:
                    metrics = await self._collect_youtube_metrics(post)
                elif post.platform == Platform.TIKTOK:
                    metrics = await self._collect_tiktok_metrics(post)
                elif post.platform == Platform.INSTAGRAM_REELS:
                    metrics = await self._collect_instagram_metrics(post)
                else:
                    continue

                # Store individual metric entries
                for metric_type, value in metrics.items():
                    log = PerformanceLog(
                        creative_id=post.creative_id,
                        round_id=round_id,
                        metric_type=metric_type,
                        value=float(value),
                        platform=post.platform,
                        raw_data=metrics,
                    )
                    await self._save_performance_log(log)
                    all_logs.append(log)

                # Update post metrics
                post.metrics = metrics
                await self._update_organic_post(post)

                logger.info(
                    f"[ACTP:Analytics] Collected {len(metrics)} metrics for "
                    f"{post.platform.value}:{post.post_id}"
                )
            except Exception as e:
                logger.error(
                    f"[ACTP:Analytics] Failed collecting {post.platform.value}:{post.post_id}: {e}"
                )

        return all_logs

    async def _collect_youtube_metrics(self, post: OrganicPost) -> Dict[str, Any]:
        """Fetch YouTube video statistics via existing connector."""
        if not self._youtube or not self._youtube.is_enabled():
            raise RuntimeError("YouTube connector not available")

        from connectors.base import ContentVariant
        variant = ContentVariant(
            content_id=post.post_id,
            platform="youtube",
            variant_type="video",
        )
        snapshots = await self._youtube.fetch_metrics_for_variant(variant)

        metrics = {}
        for snap in snapshots:
            metrics.update(snap.metrics if hasattr(snap, 'metrics') else {})

        # Normalize to standard keys
        return {
            "views": int(metrics.get("viewCount", metrics.get("views", 0))),
            "likes": int(metrics.get("likeCount", metrics.get("likes", 0))),
            "comments": int(metrics.get("commentCount", metrics.get("comments", 0))),
            "shares": int(metrics.get("shareCount", metrics.get("shares", 0))),
            "watch_time_seconds": float(metrics.get("averageViewDuration", 0)),
            "impressions": int(metrics.get("impressions", metrics.get("views", 0))),
            "ctr": float(metrics.get("clickThroughRate", 0)),
        }

    async def _collect_tiktok_metrics(self, post: OrganicPost) -> Dict[str, Any]:
        """Fetch TikTok video statistics via existing connector."""
        if not self._tiktok or not self._tiktok.is_enabled():
            raise RuntimeError("TikTok connector not available")

        from connectors.base import ContentVariant
        variant = ContentVariant(
            content_id=post.post_id,
            platform="tiktok",
            variant_type="video",
        )
        snapshots = await self._tiktok.fetch_metrics_for_variant(variant)

        metrics = {}
        for snap in snapshots:
            metrics.update(snap.metrics if hasattr(snap, 'metrics') else {})

        return {
            "views": int(metrics.get("video_views", metrics.get("views", 0))),
            "likes": int(metrics.get("likes", 0)),
            "comments": int(metrics.get("comments", 0)),
            "shares": int(metrics.get("shares", 0)),
            "reach": int(metrics.get("reach", 0)),
            "completion_rate": float(metrics.get("average_time_watched", 0)) / max(
                float(metrics.get("video_duration", 1)), 1
            ),
        }

    async def _collect_instagram_metrics(self, post: OrganicPost) -> Dict[str, Any]:
        """Fetch Instagram Reels metrics (via Meta Graph API or scraping)."""
        # Instagram metrics require Meta Graph API with instagram_basic + instagram_manage_insights
        import httpx
        access_token = os.getenv("META_ACCESS_TOKEN")
        if not access_token:
            raise RuntimeError("META_ACCESS_TOKEN not set for Instagram metrics")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://graph.facebook.com/v18.0/{post.post_id}/insights",
                params={
                    "metric": "plays,likes,comments,shares,saved,reach",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            data = response.json()

        metrics = {}
        for entry in data.get("data", []):
            name = entry.get("name", "")
            value = entry.get("values", [{}])[0].get("value", 0)
            metrics[name] = value

        return {
            "views": int(metrics.get("plays", 0)),
            "likes": int(metrics.get("likes", 0)),
            "comments": int(metrics.get("comments", 0)),
            "shares": int(metrics.get("shares", 0)),
            "saves": int(metrics.get("saved", 0)),
            "reach": int(metrics.get("reach", 0)),
        }

    # ─── Score Calculation ────────────────────────────────

    def calculate_organic_score(
        self,
        metrics: Dict[str, Any],
        platform: Platform,
        post_age_hours: float = 24.0,
    ) -> float:
        """
        Calculate a normalized organic quality score (0-100).

        Factors:
        - Engagement rate (likes + comments + shares / views)
        - View velocity (views per hour)
        - Completion rate (platform-specific)
        """
        weights = self.config.scoring
        raw_views = metrics.get("views", 0)
        if raw_views == 0:
            return 0.0
        views = max(raw_views, 1)
        likes = metrics.get("likes", 0)
        comments = metrics.get("comments", 0)
        shares = metrics.get("shares", 0)

        # Engagement rate (0-100 scale)
        engagement_rate = ((likes + comments * 2 + shares * 3) / views) * 100
        engagement_score = min(engagement_rate * 10, 100)  # Cap at 100

        # View velocity (views per hour, normalized)
        view_velocity = views / max(post_age_hours, 1)
        velocity_score = min(view_velocity / 10, 100)  # 1000 views/hr = 100

        # Completion rate (platform-specific)
        if platform == Platform.TIKTOK:
            completion = metrics.get("completion_rate", 0.5) * 100
        elif platform == Platform.YOUTUBE_SHORTS:
            watch_time = metrics.get("watch_time_seconds", 0)
            completion = min((watch_time / 15) * 100, 100)  # Assume 15s video
        else:
            completion = 50.0  # Default

        completion_score = min(completion, 100)

        # Weighted composite
        score = (
            engagement_score * weights.organic_engagement_rate
            + velocity_score * weights.organic_view_velocity
            + completion_score * weights.organic_completion_rate
        )

        return round(min(score, 100), 2)

    def calculate_ad_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate ad performance score (0-100).

        Factors:
        - CTR (click-through rate)
        - CPC efficiency (lower is better)
        - Hook rate (3-second views / impressions)
        - Hold rate (ThruPlay / 3-second views)
        """
        weights = self.config.scoring
        impressions = max(metrics.get("impressions", 0), 1)
        clicks = metrics.get("clicks", 0)
        spend = metrics.get("spend_cents", 0) / 100.0
        three_sec_views = metrics.get("three_second_views", 0)
        thru_plays = metrics.get("thru_plays", 0)
        conversions = metrics.get("conversions", 0)

        # CTR score (2%+ = excellent)
        ctr = (clicks / impressions) * 100
        ctr_score = min(ctr * 50, 100)

        # CPC efficiency (lower CPC = higher score)
        cpc = spend / max(clicks, 1)
        cpc_score = max(100 - (cpc * 20), 0)  # $5 CPC = 0, $0 = 100

        # Hook rate (3s views / impressions)
        hook_rate = (three_sec_views / impressions) * 100
        hook_score = min(hook_rate * 2, 100)

        # Hold rate (ThruPlay / 3s views)
        hold_rate = (thru_plays / max(three_sec_views, 1)) * 100
        hold_score = min(hold_rate * 2, 100)

        # Conversion score
        conv_rate = (conversions / impressions) * 100
        conv_score = min(conv_rate * 100, 100)

        score = (
            ctr_score * weights.ad_ctr
            + cpc_score * weights.ad_cpc_efficiency
            + hook_score * weights.ad_hook_rate
            + hold_score * weights.ad_hold_rate
            + conv_score * weights.ad_conversion_rate
        )

        return round(min(score, 100), 2)

    # ─── Database Operations ──────────────────────────────

    async def _save_performance_log(self, log: PerformanceLog):
        if self.db:
            await self.db.table("actp_performance_logs").insert(
                log.model_dump(mode="json")
            ).execute()

    async def _update_organic_post(self, post: OrganicPost):
        if self.db:
            await self.db.table("actp_organic_posts").update(
                {"metrics": post.metrics}
            ).eq("id", post.id).execute()

    # ─── Metric Snapshots ─────────────────────────────────

    SNAPSHOT_HOURS = [1, 3, 6, 12, 24, 48]

    async def capture_snapshot(
        self, creative_id: str, platform: str, metrics: Dict[str, Any], hours_since_post: float
    ):
        """Store a metric snapshot at a specific hour mark."""
        if not self.db:
            return

        # Find closest snapshot hour
        closest = min(self.SNAPSHOT_HOURS, key=lambda h: abs(h - hours_since_post))
        if abs(closest - hours_since_post) > 1:
            return  # Not close enough to a snapshot hour

        await self.db.table("actp_metric_snapshots").upsert({
            "creative_id": creative_id,
            "platform": platform,
            "snapshot_hour": closest,
            "metrics": metrics,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

    async def get_snapshots(self, creative_id: str) -> List[Dict[str, Any]]:
        """Get all metric snapshots for a creative (time-series data)."""
        if not self.db:
            return []
        result = await self.db.table("actp_metric_snapshots").select("*").eq(
            "creative_id", creative_id
        ).order("snapshot_hour").execute()
        return result.data or []

    # ─── Engagement Decay Curve ───────────────────────────

    async def calculate_decay_curve(self, creative_id: str) -> Dict[str, Any]:
        """
        Calculate engagement rate decay over time.
        Returns decay rate, half-life, and chart-ready data points.
        """
        snapshots = await self.get_snapshots(creative_id)
        if len(snapshots) < 2:
            return {"creative_id": creative_id, "data_points": [], "decay_rate": 0}

        data_points = []
        for snap in snapshots:
            m = snap.get("metrics", {})
            views = max(m.get("views", 0), 1)
            engagement = (m.get("likes", 0) + m.get("comments", 0) * 2 + m.get("shares", 0) * 3) / views
            data_points.append({
                "hour": snap["snapshot_hour"],
                "views": views,
                "engagement_rate": round(engagement * 100, 3),
            })

        # Simple decay rate: (first_rate - last_rate) / first_rate
        if data_points[0]["engagement_rate"] > 0:
            decay_rate = (
                data_points[0]["engagement_rate"] - data_points[-1]["engagement_rate"]
            ) / data_points[0]["engagement_rate"]
        else:
            decay_rate = 0

        # Estimate half-life (hours until engagement drops to 50%)
        half_life = None
        initial = data_points[0]["engagement_rate"]
        for dp in data_points[1:]:
            if dp["engagement_rate"] <= initial * 0.5:
                half_life = dp["hour"]
                break

        return {
            "creative_id": creative_id,
            "data_points": data_points,
            "decay_rate": round(decay_rate, 3),
            "half_life_hours": half_life,
            "initial_engagement": data_points[0]["engagement_rate"],
            "final_engagement": data_points[-1]["engagement_rate"],
        }

    # ─── View Velocity Curve ──────────────────────────────

    async def calculate_velocity_curve(self, creative_id: str) -> Dict[str, Any]:
        """Track views per hour as time-series for velocity analysis."""
        snapshots = await self.get_snapshots(creative_id)
        if len(snapshots) < 2:
            return {"creative_id": creative_id, "data_points": [], "peak_velocity": 0}

        data_points = []
        prev_views = 0
        prev_hour = 0
        peak_velocity = 0
        peak_hour = 0

        for snap in snapshots:
            views = snap.get("metrics", {}).get("views", 0)
            hour = snap["snapshot_hour"]
            delta_hours = max(hour - prev_hour, 1)
            velocity = (views - prev_views) / delta_hours

            if velocity > peak_velocity:
                peak_velocity = velocity
                peak_hour = hour

            data_points.append({
                "hour": hour,
                "total_views": views,
                "velocity_per_hour": round(velocity, 1),
            })
            prev_views = views
            prev_hour = hour

        return {
            "creative_id": creative_id,
            "data_points": data_points,
            "peak_velocity": round(peak_velocity, 1),
            "peak_hour": peak_hour,
        }

    # ─── Creative-to-Creative Comparison ──────────────────

    async def compare_creatives(
        self, creative_ids: List[str], round_id: str
    ) -> Dict[str, Any]:
        """Compare metrics between multiple creatives side by side."""
        comparisons = []

        for cid in creative_ids:
            if not self.db:
                continue

            # Get latest metrics
            logs = await self.db.table("actp_performance_logs").select("*").eq(
                "creative_id", cid
            ).eq("round_id", round_id).order("measured_at", desc=True).limit(20).execute()

            metrics = {}
            for log in (logs.data or []):
                if log["metric_type"] not in metrics:
                    metrics[log["metric_type"]] = log["value"]

            # Get creative details
            creative = await self.db.table("actp_creatives").select(
                "hook, angle, organic_score, ad_score, is_winner"
            ).eq("id", cid).single().execute()

            comparisons.append({
                "creative_id": cid,
                "hook": (creative.data or {}).get("hook"),
                "angle": (creative.data or {}).get("angle"),
                "organic_score": (creative.data or {}).get("organic_score"),
                "ad_score": (creative.data or {}).get("ad_score"),
                "is_winner": (creative.data or {}).get("is_winner"),
                "metrics": metrics,
            })

        # Calculate deltas between first two
        deltas = {}
        if len(comparisons) >= 2:
            a_metrics = comparisons[0].get("metrics", {})
            b_metrics = comparisons[1].get("metrics", {})
            all_keys = set(list(a_metrics.keys()) + list(b_metrics.keys()))
            for key in all_keys:
                va = a_metrics.get(key, 0)
                vb = b_metrics.get(key, 0)
                deltas[key] = {
                    "a": va, "b": vb,
                    "delta": round(va - vb, 2),
                    "winner": "a" if va > vb else "b" if vb > va else "tie",
                }

        return {
            "creatives": comparisons,
            "deltas": deltas,
            "count": len(comparisons),
        }

    # ─── Metric Data Export ───────────────────────────────

    async def export_metrics(
        self,
        campaign_id: Optional[str] = None,
        round_id: Optional[str] = None,
        creative_id: Optional[str] = None,
        format: str = "json",
    ) -> Any:
        """Export metrics as JSON or CSV for a campaign/round/creative."""
        if not self.db:
            return {"data": [], "format": format}

        query = self.db.table("actp_performance_logs").select("*")
        if creative_id:
            query = query.eq("creative_id", creative_id)
        if round_id:
            query = query.eq("round_id", round_id)

        query = query.order("measured_at", desc=True).limit(10000)
        result = await query.execute()
        rows = result.data or []

        if format == "csv":
            import csv
            import io
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return {"data": output.getvalue(), "format": "csv", "row_count": len(rows)}

        return {"data": rows, "format": "json", "row_count": len(rows)}

    # ─── Aggregate Metrics ────────────────────────────────

    async def aggregate_round_metrics(self, round_id: str) -> Dict[str, Any]:
        """Compute aggregate stats for a round: avg score, total views, total spend."""
        if not self.db:
            return {}

        creatives = await self.db.table("actp_creatives").select(
            "organic_score, ad_score, is_winner"
        ).eq("round_id", round_id).execute()

        scores = [c["organic_score"] for c in (creatives.data or []) if c.get("organic_score")]
        ad_scores = [c["ad_score"] for c in (creatives.data or []) if c.get("ad_score")]

        logs = await self.db.table("actp_performance_logs").select(
            "metric_type, value"
        ).eq("round_id", round_id).execute()

        total_views = sum(
            l["value"] for l in (logs.data or []) if l["metric_type"] == "views"
        )

        ads = await self.db.table("actp_ad_deployments").select(
            "spend_cents"
        ).eq("round_id", round_id).execute()
        total_spend = sum(a.get("spend_cents", 0) for a in (ads.data or []))

        return {
            "round_id": round_id,
            "creative_count": len(creatives.data or []),
            "winner_count": sum(1 for c in (creatives.data or []) if c.get("is_winner")),
            "avg_organic_score": round(sum(scores) / max(len(scores), 1), 2),
            "avg_ad_score": round(sum(ad_scores) / max(len(ad_scores), 1), 2),
            "max_organic_score": max(scores) if scores else 0,
            "total_views": total_views,
            "total_spend_cents": total_spend,
        }

    async def aggregate_campaign_metrics(self, campaign_id: str) -> Dict[str, Any]:
        """Compute campaign-level aggregate stats for dashboard."""
        if not self.db:
            return {}

        rounds = await self.db.table("actp_rounds").select(
            "id, round_number, status"
        ).eq("campaign_id", campaign_id).order("round_number").execute()

        round_summaries = []
        for r in (rounds.data or []):
            summary = await self.aggregate_round_metrics(r["id"])
            summary["round_number"] = r["round_number"]
            summary["status"] = r["status"]
            round_summaries.append(summary)

        total_spend = sum(r.get("total_spend_cents", 0) for r in round_summaries)
        all_scores = [r["avg_organic_score"] for r in round_summaries if r.get("avg_organic_score")]

        # Trend direction
        trend = "stable"
        if len(all_scores) >= 2:
            if all_scores[-1] > all_scores[0]:
                trend = "improving"
            elif all_scores[-1] < all_scores[0]:
                trend = "declining"

        return {
            "campaign_id": campaign_id,
            "rounds": round_summaries,
            "total_rounds": len(round_summaries),
            "total_spend_cents": total_spend,
            "score_trend": trend,
            "best_round": max(round_summaries, key=lambda r: r.get("avg_organic_score", 0)) if round_summaries else None,
        }

    # ─── Metric Anomaly Detection ─────────────────────────

    def detect_anomalies(self, metrics_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect unusual metric patterns that may indicate bot traffic or API errors."""
        anomalies = []

        if len(metrics_series) < 3:
            return anomalies

        values = [m.get("value", 0) for m in metrics_series]
        sorted_vals = sorted(values)
        median = sorted_vals[len(sorted_vals) // 2]
        deviations = sorted([abs(v - median) for v in values])
        mad = deviations[len(deviations) // 2] or 1  # median absolute deviation

        for i, m in enumerate(metrics_series):
            v = m.get("value", 0)
            # Modified z-score using MAD (threshold 3.5 is standard)
            modified_z = 0.6745 * abs(v - median) / mad
            if modified_z > 3.5:
                anomalies.append({
                    "index": i,
                    "value": v,
                    "z_score": round(modified_z, 2),
                    "type": "spike" if v > median else "drop",
                    "metric_type": m.get("metric_type"),
                    "measured_at": m.get("measured_at"),
                })

            # Sudden zero after positive values
            if i > 0 and v == 0 and values[i - 1] > 100:
                anomalies.append({
                    "index": i,
                    "value": v,
                    "type": "sudden_zero",
                    "previous_value": values[i - 1],
                    "metric_type": m.get("metric_type"),
                })

        return anomalies

    # ─── ROAS Calculation ─────────────────────────────────

    def calculate_roas(
        self, revenue_cents: int, spend_cents: int
    ) -> Dict[str, Any]:
        """Calculate return on ad spend per creative."""
        if spend_cents <= 0:
            return {
                "roas": 0,
                "profit_cents": revenue_cents,
                "break_even": revenue_cents > 0,
            }

        roas = revenue_cents / spend_cents
        return {
            "roas": round(roas, 2),
            "revenue_cents": revenue_cents,
            "spend_cents": spend_cents,
            "profit_cents": revenue_cents - spend_cents,
            "break_even": revenue_cents >= spend_cents,
            "roas_pct": round(roas * 100, 1),
        }

    # ─── Metric Validation & Dedup ────────────────────────

    def validate_metric(self, metric_type: str, value: float) -> bool:
        """Validate a metric value is within expected ranges."""
        ranges = {
            "views": (0, 1_000_000_000),
            "likes": (0, 100_000_000),
            "comments": (0, 10_000_000),
            "shares": (0, 10_000_000),
            "ctr": (0, 100),
            "completion_rate": (0, 1),
            "watch_time_seconds": (0, 86400),
            "impressions": (0, 1_000_000_000),
        }
        low, high = ranges.get(metric_type, (0, float("inf")))
        return low <= value <= high

    # ─── Scheduled Collection ─────────────────────────────

    COLLECTION_INTERVALS_HOURS = [1, 3, 6, 12, 24, 48]

    async def schedule_collection(
        self, campaign_id: str, round_id: str
    ) -> Dict[str, Any]:
        """Schedule metric collection at predefined intervals."""
        if not self.db:
            return {"scheduled": False}

        now = datetime.now(timezone.utc)
        tasks = []
        for hours in self.COLLECTION_INTERVALS_HOURS:
            from datetime import timedelta
            run_at = now + timedelta(hours=hours)
            task = {
                "task_type": "metric_collection",
                "entity_type": "round",
                "entity_id": round_id,
                "scheduled_for": run_at.isoformat(),
                "status": "pending",
                "config": {
                    "campaign_id": campaign_id,
                    "round_id": round_id,
                    "hours_since_post": hours,
                },
            }
            tasks.append(task)

        await self.db.table("actp_scheduled_tasks").insert(tasks).execute()

        return {
            "scheduled": True,
            "round_id": round_id,
            "collection_count": len(tasks),
            "intervals_hours": self.COLLECTION_INTERVALS_HOURS,
        }

    # ─── Performance Report Generation ────────────────────

    async def generate_report(
        self, campaign_id: str
    ) -> Dict[str, Any]:
        """Generate a comprehensive performance report for a campaign."""
        campaign_agg = await self.aggregate_campaign_metrics(campaign_id)

        if not self.db:
            return {"campaign_id": campaign_id, "error": "no_db"}

        # Get winners
        winners = await self.db.table("actp_creatives").select(
            "id, hook, angle, organic_score, ad_score"
        ).eq("campaign_id", campaign_id).eq("is_winner", True).execute()

        # Get ad deployments
        ads = await self.db.table("actp_ad_deployments").select(
            "spend_cents, metrics, platform, status"
        ).eq("campaign_id", campaign_id).execute()

        total_ad_spend = sum(a.get("spend_cents", 0) for a in (ads.data or []))
        active_ads = sum(1 for a in (ads.data or []) if a.get("status") == "active")

        return {
            "campaign_id": campaign_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": campaign_agg,
            "winners": winners.data or [],
            "ad_overview": {
                "total_deployments": len(ads.data or []),
                "active": active_ads,
                "total_spend_cents": total_ad_spend,
                "total_spend_usd": round(total_ad_spend / 100, 2),
            },
            "score_trend": campaign_agg.get("score_trend", "unknown"),
            "best_round": campaign_agg.get("best_round"),
        }

    # ─── Geographic Performance Breakdown ─────────────────

    async def get_geo_breakdown(self, creative_id: str) -> Dict[str, Any]:
        """Get geographic performance breakdown for a creative."""
        if not self.db:
            return {"creative_id": creative_id, "geo": []}

        logs = await self.db.table("actp_performance_logs").select(
            "value, metadata"
        ).eq("creative_id", creative_id).eq("metric_type", "geo_views").execute()

        geo_data = {}
        for log in (logs.data or []):
            meta = log.get("metadata") or {}
            country = meta.get("country", "unknown")
            geo_data[country] = geo_data.get(country, 0) + log.get("value", 0)

        sorted_geo = sorted(geo_data.items(), key=lambda x: -x[1])

        return {
            "creative_id": creative_id,
            "geo": [{"country": k, "views": v} for k, v in sorted_geo],
            "top_country": sorted_geo[0][0] if sorted_geo else None,
        }

    # ─── Device Type Breakdown ────────────────────────────

    async def get_device_breakdown(self, creative_id: str) -> Dict[str, Any]:
        """Get device type breakdown for a creative."""
        if not self.db:
            return {"creative_id": creative_id, "devices": []}

        logs = await self.db.table("actp_performance_logs").select(
            "value, metadata"
        ).eq("creative_id", creative_id).eq("metric_type", "device_views").execute()

        device_data = {}
        for log in (logs.data or []):
            meta = log.get("metadata") or {}
            device = meta.get("device", "unknown")
            device_data[device] = device_data.get(device, 0) + log.get("value", 0)

        return {
            "creative_id": creative_id,
            "devices": [{"device": k, "views": v} for k, v in sorted(device_data.items(), key=lambda x: -x[1])],
        }

    # ─── Traffic Source Breakdown ─────────────────────────

    async def get_traffic_source_breakdown(self, creative_id: str) -> Dict[str, Any]:
        """Get traffic source breakdown for a creative."""
        if not self.db:
            return {"creative_id": creative_id, "sources": []}

        logs = await self.db.table("actp_performance_logs").select(
            "value, metadata"
        ).eq("creative_id", creative_id).eq("metric_type", "traffic_source").execute()

        source_data = {}
        for log in (logs.data or []):
            meta = log.get("metadata") or {}
            source = meta.get("source", "unknown")
            source_data[source] = source_data.get(source, 0) + log.get("value", 0)

        return {
            "creative_id": creative_id,
            "sources": [{"source": k, "views": v} for k, v in sorted(source_data.items(), key=lambda x: -x[1])],
        }

    # ─── Peak Engagement Time Detection ───────────────────

    async def detect_peak_engagement_time(self, creative_id: str) -> Dict[str, Any]:
        """Detect the hour of day when a creative gets the most engagement."""
        snapshots = await self.get_snapshots(creative_id)
        if len(snapshots) < 2:
            return {"creative_id": creative_id, "peak_hour": None}

        # Use velocity as proxy for engagement intensity
        prev_eng = 0
        prev_hour = 0
        best_delta = 0
        best_hour = 0

        for snap in snapshots:
            m = snap.get("metrics", {})
            eng = m.get("likes", 0) + m.get("comments", 0) + m.get("shares", 0)
            hour = snap["snapshot_hour"]
            delta_hours = max(hour - prev_hour, 1)
            velocity = (eng - prev_eng) / delta_hours

            if velocity > best_delta:
                best_delta = velocity
                best_hour = hour

            prev_eng = eng
            prev_hour = hour

        return {
            "creative_id": creative_id,
            "peak_hour": best_hour,
            "peak_engagement_velocity": round(best_delta, 1),
        }

    # ─── Audience Retention Curve ─────────────────────────

    async def get_retention_curve(self, creative_id: str) -> Dict[str, Any]:
        """
        Get audience retention curve data.
        Shows what percentage of viewers are still watching at each second.
        """
        if not self.db:
            return {"creative_id": creative_id, "curve": []}

        logs = await self.db.table("actp_performance_logs").select(
            "value, metadata"
        ).eq("creative_id", creative_id).eq("metric_type", "retention").order(
            "measured_at", desc=True
        ).limit(1).execute()

        if not (logs.data or []):
            return {"creative_id": creative_id, "curve": []}

        meta = (logs.data[0].get("metadata") or {})
        curve = meta.get("retention_curve", [])

        # Find drop-off points
        drop_offs = []
        for i in range(1, len(curve)):
            drop = curve[i - 1] - curve[i]
            if drop > 10:  # > 10% drop
                drop_offs.append({"second": i, "drop_pct": round(drop, 1)})

        return {
            "creative_id": creative_id,
            "curve": curve,
            "avg_retention": round(sum(curve) / max(len(curve), 1), 1) if curve else 0,
            "drop_off_points": drop_offs,
        }

    # ─── Comment Keyword Extraction ───────────────────────

    def extract_comment_keywords(
        self, comments: List[str], top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """Extract most frequent keywords from post comments."""
        import re
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "me", "him", "her", "us", "them", "my", "your",
            "his", "its", "our", "their", "and", "but", "or", "not", "no",
            "so", "to", "of", "in", "on", "at", "for", "with", "about",
            "from", "up", "out", "if", "just", "very", "too", "also",
        }

        word_counts: Dict[str, int] = {}
        for comment in comments:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', comment.lower())
            for w in words:
                if w not in stop_words:
                    word_counts[w] = word_counts.get(w, 0) + 1

        sorted_words = sorted(word_counts.items(), key=lambda x: -x[1])[:top_n]
        return [{"keyword": w, "count": c} for w, c in sorted_words]

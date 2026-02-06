"""
Performance Benchmark Service
Compares user's Instagram metrics against competitors and industry averages.
Generates actionable recommendations based on performance gaps.
"""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel
import openai

from services.competitor_service import get_competitor_service, COMPETITOR_RESEARCH_DIR

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class MetricComparison(BaseModel):
    """Single metric comparison"""
    metric: str
    user_value: float
    competitor_avg: float
    industry_avg: float
    delta_vs_competitors: float  # positive = user outperforms
    delta_vs_industry: float
    status: str  # 'above', 'below', 'at_par'
    percentile: Optional[float] = None  # 0-100


class BenchmarkResult(BaseModel):
    """Complete benchmark comparison"""
    comparisons: List[MetricComparison]
    competitor_breakdown: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    overall_score: float  # 0-100
    generated_at: str


# Industry averages for Instagram (2024-2026 benchmarks)
INDUSTRY_BENCHMARKS = {
    "engagement_rate": {
        "micro": 3.86,     # < 15K followers
        "small": 2.39,     # 15K - 100K
        "medium": 1.87,    # 100K - 500K
        "large": 1.62,     # 500K+
        "default": 2.5,
    },
    "avg_views_per_reel": {
        "micro": 5000,
        "small": 15000,
        "medium": 50000,
        "large": 200000,
        "default": 15000,
    },
    "posting_frequency_per_week": {
        "micro": 4,
        "small": 5,
        "medium": 7,
        "large": 10,
        "default": 5,
    },
    "follower_growth_monthly_pct": {
        "micro": 3.0,
        "small": 2.0,
        "medium": 1.5,
        "large": 1.0,
        "default": 2.0,
    },
    "comment_rate": {
        "default": 0.5,
    },
    "save_rate": {
        "default": 1.2,
    },
}


class BenchmarkService:
    """
    Compares user performance against competitors and industry benchmarks.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        self.competitor_service = get_competitor_service()
        self.storage_path = COMPETITOR_RESEARCH_DIR / "learnings" / "benchmarks"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._supabase = None

    def _get_supabase(self):
        if self._supabase is None and HAS_SUPABASE:
            try:
                url = os.environ.get('SUPABASE_URL', 'http://127.0.0.1:54321')
                key = os.environ.get('SUPABASE_ANON_KEY', os.environ.get('SUPABASE_KEY', ''))
                if key:
                    self._supabase = create_client(url, key)
            except Exception as e:
                logger.warning(f"Supabase not available for benchmarks: {e}")
        return self._supabase

    def _get_account_tier(self, followers: int) -> str:
        """Determine account tier based on follower count"""
        if followers < 15000:
            return "micro"
        elif followers < 100000:
            return "small"
        elif followers < 500000:
            return "medium"
        return "large"

    def _get_industry_avg(self, metric: str, tier: str) -> float:
        """Get industry average for a metric at a given tier"""
        benchmarks = INDUSTRY_BENCHMARKS.get(metric, {})
        return benchmarks.get(tier, benchmarks.get("default", 0))

    def _gather_competitor_metrics(self) -> List[Dict[str, Any]]:
        """Gather metrics from all tracked competitor accounts"""
        accounts_dir = COMPETITOR_RESEARCH_DIR / "accounts"
        if not accounts_dir.exists():
            return []

        metrics = []

        for account_dir in accounts_dir.iterdir():
            if not account_dir.is_dir() or account_dir.name.startswith("."):
                continue

            username = account_dir.name
            profile_path = account_dir / "profile.json"
            analysis_path = account_dir / "analysis" / "learnings.json"

            account_metrics = {"username": username}

            # Load profile
            if profile_path.exists():
                try:
                    with open(profile_path) as f:
                        profile = json.load(f)
                    account_metrics["followers"] = profile.get("followers_count", 0)
                    account_metrics["following"] = profile.get("following_count", 0)
                    account_metrics["media_count"] = profile.get("media_count", 0)
                except Exception:
                    pass

            # Load analysis
            if analysis_path.exists():
                try:
                    with open(analysis_path) as f:
                        analysis = json.load(f)
                    account_metrics["avg_engagement"] = analysis.get("avg_engagement_rate", 0)
                    account_metrics["total_content_analyzed"] = analysis.get("total_content_analyzed", 0)
                    patterns = analysis.get("posting_patterns", {})
                    account_metrics["total_reels"] = patterns.get("total_reels", 0)
                    account_metrics["total_posts"] = patterns.get("total_posts", 0)
                except Exception:
                    pass

            # Load content for view metrics
            content = self.competitor_service.load_stored_content(username)
            if content:
                views = [c.play_count for c in content if c.play_count and c.play_count > 0]
                likes = [c.like_count for c in content if c.like_count and c.like_count > 0]
                comments = [c.comment_count for c in content if c.comment_count and c.comment_count > 0]

                if views:
                    account_metrics["avg_views"] = sum(views) / len(views)
                if likes:
                    account_metrics["avg_likes"] = sum(likes) / len(likes)
                if comments:
                    account_metrics["avg_comments"] = sum(comments) / len(comments)

                followers = account_metrics.get("followers", 0)
                if followers > 0 and likes:
                    account_metrics["engagement_rate"] = (
                        (sum(likes) / len(likes) + sum(comments) / len(comments))
                        / followers * 100
                    )

            if len(account_metrics) > 1:  # More than just username
                metrics.append(account_metrics)

        return metrics

    async def run_benchmark(
        self,
        user_metrics: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkResult:
        """
        Run a full benchmark comparison.

        Args:
            user_metrics: User's own performance data. Keys:
                - followers: int
                - engagement_rate: float (%)
                - avg_views: float
                - avg_likes: float
                - posting_frequency: float (posts/week)
                - follower_growth_pct: float (30-day %)
        """
        competitor_metrics = self._gather_competitor_metrics()

        if not competitor_metrics:
            logger.warning("No competitor data available for benchmarking")
            return BenchmarkResult(
                comparisons=[],
                competitor_breakdown=[],
                recommendations=[{"metric": "data", "action": "Add and analyze competitors first", "priority": "high"}],
                overall_score=0,
                generated_at=datetime.now().isoformat(),
            )

        user = user_metrics or {}
        user_followers = user.get("followers", 0)
        tier = self._get_account_tier(user_followers) if user_followers > 0 else "small"

        comparisons = []

        # --- Engagement Rate ---
        user_er = user.get("engagement_rate", 0)
        comp_ers = [m.get("engagement_rate", 0) for m in competitor_metrics if m.get("engagement_rate")]
        comp_avg_er = sum(comp_ers) / len(comp_ers) if comp_ers else 0
        industry_er = self._get_industry_avg("engagement_rate", tier)

        comparisons.append(MetricComparison(
            metric="engagement_rate",
            user_value=round(user_er, 2),
            competitor_avg=round(comp_avg_er, 2),
            industry_avg=round(industry_er, 2),
            delta_vs_competitors=round(user_er - comp_avg_er, 2),
            delta_vs_industry=round(user_er - industry_er, 2),
            status="above" if user_er > comp_avg_er else ("at_par" if abs(user_er - comp_avg_er) < 0.3 else "below"),
        ))

        # --- Avg Views ---
        user_views = user.get("avg_views", 0)
        comp_views = [m.get("avg_views", 0) for m in competitor_metrics if m.get("avg_views")]
        comp_avg_views = sum(comp_views) / len(comp_views) if comp_views else 0
        industry_views = self._get_industry_avg("avg_views_per_reel", tier)

        comparisons.append(MetricComparison(
            metric="avg_views_per_reel",
            user_value=round(user_views),
            competitor_avg=round(comp_avg_views),
            industry_avg=round(industry_views),
            delta_vs_competitors=round(user_views - comp_avg_views),
            delta_vs_industry=round(user_views - industry_views),
            status="above" if user_views > comp_avg_views else ("at_par" if abs(user_views - comp_avg_views) < comp_avg_views * 0.1 else "below"),
        ))

        # --- Avg Likes ---
        user_likes = user.get("avg_likes", 0)
        comp_likes = [m.get("avg_likes", 0) for m in competitor_metrics if m.get("avg_likes")]
        comp_avg_likes = sum(comp_likes) / len(comp_likes) if comp_likes else 0

        comparisons.append(MetricComparison(
            metric="avg_likes_per_post",
            user_value=round(user_likes),
            competitor_avg=round(comp_avg_likes),
            industry_avg=0,
            delta_vs_competitors=round(user_likes - comp_avg_likes),
            delta_vs_industry=0,
            status="above" if user_likes > comp_avg_likes else ("at_par" if abs(user_likes - comp_avg_likes) < comp_avg_likes * 0.1 else "below"),
        ))

        # --- Posting Frequency ---
        user_freq = user.get("posting_frequency", 0)
        industry_freq = self._get_industry_avg("posting_frequency_per_week", tier)

        comparisons.append(MetricComparison(
            metric="posting_frequency_per_week",
            user_value=round(user_freq, 1),
            competitor_avg=0,  # Hard to determine from static data
            industry_avg=round(industry_freq, 1),
            delta_vs_competitors=0,
            delta_vs_industry=round(user_freq - industry_freq, 1),
            status="above" if user_freq >= industry_freq else "below",
        ))

        # --- Follower Growth ---
        user_growth = user.get("follower_growth_pct", 0)
        industry_growth = self._get_industry_avg("follower_growth_monthly_pct", tier)

        comparisons.append(MetricComparison(
            metric="follower_growth_monthly_pct",
            user_value=round(user_growth, 2),
            competitor_avg=0,
            industry_avg=round(industry_growth, 2),
            delta_vs_competitors=0,
            delta_vs_industry=round(user_growth - industry_growth, 2),
            status="above" if user_growth >= industry_growth else "below",
        ))

        # Overall score
        scores = []
        for c in comparisons:
            if c.competitor_avg > 0:
                ratio = c.user_value / c.competitor_avg if c.competitor_avg else 0
                scores.append(min(ratio * 50, 100))
            elif c.industry_avg > 0:
                ratio = c.user_value / c.industry_avg if c.industry_avg else 0
                scores.append(min(ratio * 50, 100))
        overall = sum(scores) / len(scores) if scores else 0

        # Generate recommendations
        recommendations = await self._generate_recommendations(comparisons, competitor_metrics)

        result = BenchmarkResult(
            comparisons=comparisons,
            competitor_breakdown=competitor_metrics,
            recommendations=recommendations,
            overall_score=round(overall, 1),
            generated_at=datetime.now().isoformat(),
        )

        self._save_result(result)
        return result

    async def _generate_recommendations(
        self,
        comparisons: List[MetricComparison],
        competitor_metrics: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate AI recommendations based on benchmark gaps"""
        if not self.api_key:
            return self._basic_recommendations(comparisons)

        try:
            client = openai.OpenAI(api_key=self.api_key)

            comp_data = [
                {"metric": c.metric, "user": c.user_value, "competitor_avg": c.competitor_avg,
                 "industry_avg": c.industry_avg, "status": c.status}
                for c in comparisons
            ]

            prompt = f"""Based on these Instagram performance benchmarks, generate specific recommendations:

METRICS:
{json.dumps(comp_data, indent=2)}

COMPETITOR ACCOUNTS ANALYZED: {len(competitor_metrics)}

Generate 5-7 specific, actionable recommendations as JSON array:
[
    {{
        "metric": "which metric this addresses",
        "status": "above|below|at_par",
        "action": "specific actionable recommendation",
        "priority": "high|medium|low",
        "expected_impact": "what improvement to expect"
    }}
]

Focus on the biggest gaps first. Be specific (e.g., "Post 2 more reels per week" not "post more").
Return ONLY valid JSON array."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an Instagram growth expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            return json.loads(result_text)

        except Exception as e:
            logger.error(f"Error generating benchmark recommendations: {e}")
            return self._basic_recommendations(comparisons)

    def _basic_recommendations(self, comparisons: List[MetricComparison]) -> List[Dict[str, Any]]:
        """Fallback recommendations without AI"""
        recs = []
        for c in comparisons:
            if c.status == "below":
                recs.append({
                    "metric": c.metric,
                    "status": "below",
                    "action": f"Improve {c.metric.replace('_', ' ')} — currently {c.user_value}, competitor avg is {c.competitor_avg}",
                    "priority": "high",
                    "expected_impact": f"Close the gap of {abs(c.delta_vs_competitors)}"
                })
        return recs

    def _save_result(self, result: BenchmarkResult):
        """Save benchmark result to local files and Supabase."""
        try:
            path = self.storage_path / "latest_benchmark.json"
            with open(path, "w") as f:
                json.dump(result.model_dump(), f, indent=2, default=str)
            logger.info(f"Saved benchmark to {path}")
        except Exception as e:
            logger.error(f"Error saving benchmark: {e}")

        # Persist to Supabase
        sb = self._get_supabase()
        if not sb:
            return
        try:
            # Extract user/competitor values from comparisons
            user_er = next((c.user_value for c in result.comparisons if c.metric == 'engagement_rate'), None)
            user_views = next((c.user_value for c in result.comparisons if c.metric == 'avg_views_per_reel'), None)
            user_likes = next((c.user_value for c in result.comparisons if c.metric == 'avg_likes_per_post'), None)
            user_freq = next((c.user_value for c in result.comparisons if c.metric == 'posting_frequency_per_week'), None)
            comp_er = next((c.competitor_avg for c in result.comparisons if c.metric == 'engagement_rate'), None)
            comp_views = next((c.competitor_avg for c in result.comparisons if c.metric == 'avg_views_per_reel'), None)
            comp_likes = next((c.competitor_avg for c in result.comparisons if c.metric == 'avg_likes_per_post'), None)

            sb.table('performance_benchmarks').insert({
                'user_engagement_rate': user_er,
                'user_avg_views': user_views,
                'user_avg_likes': user_likes,
                'user_posting_frequency': user_freq,
                'competitor_engagement_rate': comp_er,
                'competitor_avg_views': comp_views,
                'competitor_avg_likes': comp_likes,
                'competitor_breakdown': json.dumps(result.competitor_breakdown, default=str),
                'deltas': json.dumps({c.metric: {'value': c.delta_vs_competitors, 'status': c.status} for c in result.comparisons}, default=str),
                'recommendations': json.dumps(result.recommendations, default=str),
            }).execute()
            logger.info("Persisted benchmark to Supabase")
        except Exception as e:
            logger.warning(f"Failed to persist benchmark to Supabase: {e}")

    def get_latest_benchmark(self) -> Optional[BenchmarkResult]:
        """Load most recent benchmark"""
        path = self.storage_path / "latest_benchmark.json"
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return BenchmarkResult(**data)
        except Exception as e:
            logger.error(f"Error loading benchmark: {e}")
            return None


# Singleton
_benchmark_service: Optional[BenchmarkService] = None


def get_benchmark_service() -> BenchmarkService:
    """Get singleton benchmark service"""
    global _benchmark_service
    if _benchmark_service is None:
        _benchmark_service = BenchmarkService()
    return _benchmark_service

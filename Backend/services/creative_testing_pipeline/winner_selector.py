"""
ACTP Winner Selector
=====================
Scoring and ranking algorithms to pick winners from organic and ad test rounds.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .analytics_collector import AnalyticsCollector
from .config import ACTPConfig
from .models import (
    AdDeployment,
    Creative,
    OrganicPost,
    Platform,
    WinnerSelection,
)

logger = logging.getLogger(__name__)

# Minimum thresholds before making decisions
MIN_ORGANIC_VIEWS = 100
MIN_AD_IMPRESSIONS = 1000


class WinnerSelector:
    """
    Selects winning creatives from test rounds based on performance metrics.

    Two modes:
    - Organic: scores by engagement rate, view velocity, completion rate
    - Ad: scores by CTR, CPC, hook rate, hold rate, conversion rate
    """

    def __init__(self, db_client=None, config: Optional[ACTPConfig] = None):
        self.db = db_client
        self.config = config or ACTPConfig()
        self._analytics = AnalyticsCollector(db_client=db_client, config=config)
        logger.info("[ACTP:Winner] Selector initialized")

    # ─── Organic Winner Selection ─────────────────────────

    async def select_organic_winners(
        self,
        creatives: List[Creative],
        organic_posts: List[OrganicPost],
        round_id: str,
        top_n: Optional[int] = None,
    ) -> List[WinnerSelection]:
        """
        Score and rank creatives based on organic performance.
        Returns top N winners with scores and reasons.
        """
        top_n = top_n or self.config.iteration.winner_count

        # Build creative → posts mapping
        posts_by_creative: Dict[str, List[OrganicPost]] = {}
        for post in organic_posts:
            posts_by_creative.setdefault(post.creative_id, []).append(post)

        scored: List[Tuple[Creative, float, str]] = []

        for creative in creatives:
            posts = posts_by_creative.get(creative.id, [])
            if not posts:
                scored.append((creative, 0.0, "No organic posts"))
                continue

            # Aggregate metrics across platforms
            total_views = 0
            platform_scores = []
            reasons = []

            for post in posts:
                if post.status != "published" or not post.metrics:
                    continue
                views = post.metrics.get("views", 0)
                total_views += views

                if views < MIN_ORGANIC_VIEWS:
                    continue

                post_age_hours = 24.0  # Default
                if post.posted_at:
                    delta = datetime.now(timezone.utc) - post.posted_at
                    post_age_hours = max(delta.total_seconds() / 3600, 1)

                score = self._analytics.calculate_organic_score(
                    post.metrics, post.platform, post_age_hours
                )
                platform_scores.append(score)
                reasons.append(
                    f"{post.platform.value}: {score:.1f} "
                    f"({views} views, {post.metrics.get('likes', 0)} likes)"
                )

            if not platform_scores:
                if total_views > 0:
                    scored.append((creative, 0.0, f"Insufficient views ({total_views})"))
                else:
                    scored.append((creative, 0.0, "No metrics collected"))
                continue

            # Average across platforms
            avg_score = sum(platform_scores) / len(platform_scores)
            reason = " | ".join(reasons)
            scored.append((creative, avg_score, reason))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Select top N
        winners = []
        for rank, (creative, score, reason) in enumerate(scored[:top_n], 1):
            selection = WinnerSelection(
                round_id=round_id,
                creative_id=creative.id,
                rank=rank,
                score=score,
                selection_reason=reason,
            )

            # Update creative
            creative.organic_score = score
            creative.is_winner = True
            await self._update_creative(creative)
            await self._save_winner(selection)
            winners.append(selection)

            logger.info(
                f"[ACTP:Winner] Organic #{rank}: {creative.id} "
                f"(score={score:.1f}, hook='{creative.hook}')"
            )

        # Log non-winners
        for creative, score, reason in scored[top_n:]:
            logger.info(f"[ACTP:Winner] Non-winner: {creative.id} (score={score:.1f})")

        return winners

    # ─── Ad Winner Selection ──────────────────────────────

    async def select_ad_winners(
        self,
        creatives: List[Creative],
        ad_deployments: List[AdDeployment],
        round_id: str,
        top_n: Optional[int] = None,
    ) -> List[WinnerSelection]:
        """
        Score and rank creatives based on ad performance.
        Returns top N winners with scores and reasons.
        """
        top_n = top_n or self.config.iteration.winner_count

        # Build creative → deployments mapping
        ads_by_creative: Dict[str, List[AdDeployment]] = {}
        for ad in ad_deployments:
            ads_by_creative.setdefault(ad.creative_id, []).append(ad)

        scored: List[Tuple[Creative, float, str]] = []

        for creative in creatives:
            ads = ads_by_creative.get(creative.id, [])
            if not ads:
                scored.append((creative, 0.0, "No ad deployments"))
                continue

            ad_scores = []
            reasons = []

            for ad in ads:
                if not ad.metrics:
                    continue

                impressions = ad.metrics.get("impressions", 0)
                if impressions < MIN_AD_IMPRESSIONS:
                    continue

                score = self._analytics.calculate_ad_score(ad.metrics)
                ad_scores.append(score)

                ctr = (ad.metrics.get("clicks", 0) / max(impressions, 1)) * 100
                cpc = ad.spend_cents / max(ad.metrics.get("clicks", 1), 1) / 100
                reasons.append(
                    f"{ad.platform.value}: {score:.1f} "
                    f"(CTR={ctr:.2f}%, CPC=${cpc:.2f})"
                )

            if not ad_scores:
                scored.append((creative, 0.0, "Insufficient impressions"))
                continue

            avg_score = sum(ad_scores) / len(ad_scores)
            reason = " | ".join(reasons)
            scored.append((creative, avg_score, reason))

        scored.sort(key=lambda x: x[1], reverse=True)

        winners = []
        for rank, (creative, score, reason) in enumerate(scored[:top_n], 1):
            selection = WinnerSelection(
                round_id=round_id,
                creative_id=creative.id,
                rank=rank,
                score=score,
                selection_reason=reason,
            )

            creative.ad_score = score
            creative.is_winner = True
            await self._update_creative(creative)
            await self._save_winner(selection)
            winners.append(selection)

            logger.info(
                f"[ACTP:Winner] Ad #{rank}: {creative.id} "
                f"(score={score:.1f}, angle='{creative.angle}')"
            )

        return winners

    # ─── Statistical Checks ───────────────────────────────

    def has_sufficient_data(
        self, posts: List[OrganicPost], min_views: int = MIN_ORGANIC_VIEWS
    ) -> bool:
        """Check if enough data has been collected for reliable decisions."""
        total_views = sum(
            p.metrics.get("views", 0)
            for p in posts
            if p.status == "published" and p.metrics
        )
        return total_views >= min_views

    def has_sufficient_ad_data(
        self, ads: List[AdDeployment], min_impressions: int = MIN_AD_IMPRESSIONS
    ) -> bool:
        """Check if enough ad data for reliable decisions."""
        total_impressions = sum(
            a.metrics.get("impressions", 0) for a in ads if a.metrics
        )
        return total_impressions >= min_impressions

    # ─── Database Operations ──────────────────────────────

    async def _update_creative(self, creative: Creative):
        if self.db:
            await self.db.table("actp_creatives").update({
                "organic_score": creative.organic_score,
                "ad_score": creative.ad_score,
                "is_winner": creative.is_winner,
            }).eq("id", creative.id).execute()

    async def _save_winner(self, selection: WinnerSelection):
        if self.db:
            await self.db.table("actp_winner_selections").insert(
                selection.model_dump(mode="json")
            ).execute()

    # ─── Tie-Breaking Rules ───────────────────────────────

    def break_tie(
        self,
        creative_a: Creative,
        creative_b: Creative,
        posts_a: List[OrganicPost],
        posts_b: List[OrganicPost],
    ) -> Creative:
        """
        Break a tie between two creatives with equal scores.
        Priority: shares > comments > views > recency.
        """
        def engagement_depth(posts: List[OrganicPost]) -> tuple:
            shares = sum(p.metrics.get("shares", 0) for p in posts if p.metrics)
            comments = sum(p.metrics.get("comments", 0) for p in posts if p.metrics)
            views = sum(p.metrics.get("views", 0) for p in posts if p.metrics)
            return (shares, comments, views)

        depth_a = engagement_depth(posts_a)
        depth_b = engagement_depth(posts_b)

        if depth_a > depth_b:
            return creative_a
        elif depth_b > depth_a:
            return creative_b

        # Final tiebreak: newer creative wins
        if creative_a.created_at and creative_b.created_at:
            return creative_a if creative_a.created_at > creative_b.created_at else creative_b
        return creative_a

    # ─── Winner Disqualification ──────────────────────────

    async def disqualify_winner(
        self, creative_id: str, round_id: str, reason: str
    ) -> Optional[WinnerSelection]:
        """Disqualify a winner and promote the next-ranked creative."""
        if not self.db:
            return None

        # Remove winner flag
        await self.db.table("actp_creatives").update({
            "is_winner": False,
        }).eq("id", creative_id).execute()

        # Mark winner selection as disqualified
        await self.db.table("actp_winner_selections").update({
            "selection_reason": f"DISQUALIFIED: {reason}",
        }).eq("creative_id", creative_id).eq("round_id", round_id).execute()

        # Promote next in line
        result = await self.db.table("actp_winner_selections").select("*").eq(
            "round_id", round_id
        ).order("rank").execute()

        selections = result.data or []
        non_disqualified = [
            s for s in selections
            if not (s.get("selection_reason") or "").startswith("DISQUALIFIED")
        ]

        if non_disqualified:
            # Re-rank
            for i, sel in enumerate(non_disqualified, 1):
                await self.db.table("actp_winner_selections").update({
                    "rank": i,
                }).eq("id", sel["id"]).execute()

            logger.info(
                f"[ACTP:Winner] Disqualified {creative_id}, "
                f"promoted {non_disqualified[0]['creative_id']} to #1"
            )

        return None

    # ─── Winner Recalculation ─────────────────────────────

    async def recalculate_winners(
        self,
        round_id: str,
        creatives: List[Creative],
        posts: List[OrganicPost],
        top_n: int = 3,
    ) -> List[WinnerSelection]:
        """
        Recalculate winners when new metric data arrives.
        Clears old selections and re-scores.
        """
        if self.db:
            # Clear old winners for this round
            await self.db.table("actp_winner_selections").delete().eq(
                "round_id", round_id
            ).execute()

            # Reset winner flags
            for c in creatives:
                c.is_winner = False
                c.organic_score = None
                await self._update_creative(c)

        # Re-run selection
        return await self.select_organic_winners(round_id, creatives, posts, top_n)

    # ─── Bayesian Confidence Scoring ──────────────────────

    def bayesian_confidence(
        self, successes: int, total: int, prior_alpha: float = 1.0, prior_beta: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate Bayesian confidence interval for a conversion/engagement rate.
        Uses Beta-Binomial conjugate prior.
        """
        alpha = prior_alpha + successes
        beta = prior_beta + (total - successes)

        mean = alpha / (alpha + beta)
        # 95% credible interval approximation
        variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
        std = variance ** 0.5
        lower = max(0, mean - 1.96 * std)
        upper = min(1, mean + 1.96 * std)

        return {
            "mean": round(mean, 4),
            "lower_95": round(lower, 4),
            "upper_95": round(upper, 4),
            "std": round(std, 4),
            "confidence": round(1 - (upper - lower), 4),
            "samples": total,
        }

    def score_with_confidence(
        self, creative: Creative, posts: List[OrganicPost]
    ) -> Dict[str, Any]:
        """Score a creative with Bayesian confidence bounds."""
        total_views = sum(
            p.metrics.get("views", 0) for p in posts if p.metrics
        )
        total_engagements = sum(
            p.metrics.get("likes", 0) + p.metrics.get("comments", 0) + p.metrics.get("shares", 0)
            for p in posts if p.metrics
        )

        conf = self.bayesian_confidence(total_engagements, max(total_views, 1))

        return {
            "creative_id": creative.id,
            "engagement_rate": conf["mean"],
            "confidence_interval": (conf["lower_95"], conf["upper_95"]),
            "confidence_level": conf["confidence"],
            "total_views": total_views,
            "total_engagements": total_engagements,
        }

    # ─── Multi-Armed Bandit Exploration ───────────────────

    def thompson_sampling_score(
        self, creatives_with_metrics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Thompson Sampling for exploration/exploitation balance.
        Each creative is scored by sampling from its Beta distribution.
        """
        import random

        scored = []
        for item in creatives_with_metrics:
            views = item.get("views", 0)
            engagements = item.get("engagements", 0)

            alpha = 1 + engagements
            beta = 1 + (views - engagements)

            # Sample from Beta distribution
            sample = random.betavariate(max(alpha, 0.01), max(beta, 0.01))

            scored.append({
                "creative_id": item.get("creative_id"),
                "thompson_score": round(sample, 4),
                "alpha": alpha,
                "beta": beta,
                "mean": round(alpha / (alpha + beta), 4),
            })

        scored.sort(key=lambda x: x["thompson_score"], reverse=True)
        return scored

    # ─── Historical Winner Patterns ───────────────────────

    async def extract_winning_patterns(
        self, campaign_id: str
    ) -> List[Dict[str, Any]]:
        """Extract patterns from all winners across campaign rounds."""
        if not self.db:
            return []

        winners = await self.db.table("actp_creatives").select(
            "hook, cta, angle, generation_source, organic_score, ad_score, generation_metadata"
        ).eq("campaign_id", campaign_id).eq("is_winner", True).execute()

        patterns = []
        hook_counts: Dict[str, int] = {}
        angle_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}

        for w in (winners.data or []):
            hook = (w.get("hook") or "")[:50]
            angle = w.get("angle") or ""
            source = w.get("generation_source") or ""

            if hook:
                hook_counts[hook] = hook_counts.get(hook, 0) + 1
            if angle:
                angle_counts[angle] = angle_counts.get(angle, 0) + 1
            if source:
                source_counts[source] = source_counts.get(source, 0) + 1

        # Top patterns
        for hook, count in sorted(hook_counts.items(), key=lambda x: -x[1])[:5]:
            patterns.append({"type": "hook", "value": hook, "frequency": count})
        for angle, count in sorted(angle_counts.items(), key=lambda x: -x[1])[:5]:
            patterns.append({"type": "angle", "value": angle, "frequency": count})
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            patterns.append({"type": "source", "value": source, "frequency": count})

        # Persist patterns
        for pattern in patterns:
            if self.db:
                await self.db.table("actp_winning_patterns").insert({
                    "campaign_id": campaign_id,
                    "pattern_type": pattern["type"],
                    "pattern_data": pattern,
                    "score": pattern["frequency"],
                }).execute()

        return patterns

    # ─── Score Calibration ────────────────────────────────

    async def calibrate_scores(
        self, campaign_id: str
    ) -> Dict[str, Any]:
        """
        Calibrate scores across rounds so they're comparable.
        Normalizes by round-specific metrics distribution.
        """
        if not self.db:
            return {"calibrated": False}

        rounds = await self.db.table("actp_rounds").select("id").eq(
            "campaign_id", campaign_id
        ).execute()

        round_stats = {}
        for r in (rounds.data or []):
            creatives = await self.db.table("actp_creatives").select(
                "organic_score"
            ).eq("round_id", r["id"]).execute()

            scores = [c["organic_score"] for c in (creatives.data or []) if c.get("organic_score")]
            if scores:
                round_stats[r["id"]] = {
                    "mean": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores),
                    "count": len(scores),
                }

        return {
            "calibrated": True,
            "campaign_id": campaign_id,
            "round_stats": round_stats,
        }

    # ─── Elimination Round Logic ──────────────────────────

    def eliminate_bottom_performers(
        self,
        creatives: List[Creative],
        elimination_pct: float = 0.5,
    ) -> tuple:
        """
        Eliminate bottom-performing creatives.
        Returns (survivors, eliminated).
        """
        if not creatives:
            return [], []

        sorted_creatives = sorted(
            creatives,
            key=lambda c: c.organic_score or 0,
            reverse=True,
        )

        cutoff = max(1, int(len(sorted_creatives) * (1 - elimination_pct)))
        survivors = sorted_creatives[:cutoff]
        eliminated = sorted_creatives[cutoff:]

        logger.info(
            f"[ACTP:Winner] Eliminated {len(eliminated)}/{len(creatives)} "
            f"(kept top {cutoff})"
        )

        return survivors, eliminated

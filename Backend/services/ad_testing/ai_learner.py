"""
Ad AI Learner (AD-006)
=======================
AI-powered analysis of ad test results to identify winning patterns,
generate insights, and suggest next tests.

Uses OpenAI for deep analysis when API key is available.
Falls back to heuristic pattern detection otherwise.

Capabilities:
    - Analyse campaign results and find winning patterns
    - Generate insight summaries for stakeholders
    - Suggest next A/B test iterations
    - Build audience-level performance profiles

Usage:
    learner = get_ai_learner()
    results = learner.analyze_results(campaign_id)
    suggestions = learner.generate_next_test_suggestions(campaign_id)
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AdAILearner:
    """
    AI-powered ad test result analyser (AD-006).

    Integrates with MetaAdsPerformanceTracker (AD-005) for metrics data
    and uses OpenAI for deep analysis with heuristic fallback.
    """

    _instance: Optional["AdAILearner"] = None

    def __init__(self) -> None:
        self._openai_client: Optional[Any] = None
        self._model = "gpt-4o-mini"
        self._performance_tracker = None
        self._campaign_deployer = None
        self._init_dependencies()
        logger.info("[AD-006] AdAILearner initialized")

    def _init_dependencies(self) -> None:
        """Initialise OpenAI and sibling AD services."""
        # OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI

                self._openai_client = OpenAI(api_key=api_key)
                logger.info(f"[AD-006] OpenAI client ready (model={self._model})")
            except ImportError:
                logger.warning("[AD-006] openai package not installed")
            except Exception as exc:
                logger.error(f"[AD-006] OpenAI init error: {exc}")
        else:
            logger.info("[AD-006] No OPENAI_API_KEY - using heuristic analysis")

        # Performance tracker
        try:
            from services.ad_testing.performance_tracker import get_performance_tracker

            self._performance_tracker = get_performance_tracker()
        except Exception as exc:
            logger.warning(f"[AD-006] Could not load PerformanceTracker: {exc}")

        # Campaign deployer
        try:
            from services.ad_testing.campaign_deployer import get_campaign_deployer

            self._campaign_deployer = get_campaign_deployer()
        except Exception as exc:
            logger.warning(f"[AD-006] Could not load CampaignDeployer: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_results(self, campaign_id: str) -> Dict[str, Any]:
        """
        Analyse campaign results and return structured insights.

        Args:
            campaign_id: The campaign to analyse.

        Returns:
            Dict with winning_patterns, insights, recommendations,
            and overall_grade.
        """
        metrics = self._get_campaign_metrics(campaign_id)
        if not metrics or metrics.get("status") == "no_data":
            logger.warning(f"[AD-006] No data for campaign {campaign_id}")
            return {
                "campaign_id": campaign_id,
                "winning_patterns": [],
                "insights": ["No performance data available yet."],
                "recommendations": ["Collect more data before analysis."],
                "overall_grade": "N/A",
            }

        ad_breakdown = metrics.get("ad_breakdown", [])

        # Identify winning patterns
        winning_patterns = self.identify_winning_patterns(ad_breakdown)

        # Generate insights
        if self._openai_client and len(ad_breakdown) >= 2:
            try:
                ai_result = self._ai_analyze(campaign_id, metrics, winning_patterns)
                return ai_result
            except Exception as exc:
                logger.error(f"[AD-006] AI analysis failed, using heuristics: {exc}")

        # Heuristic analysis
        return self._heuristic_analyze(campaign_id, metrics, winning_patterns)

    def identify_winning_patterns(
        self, metrics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify winning patterns from a list of ad metrics.

        Args:
            metrics: List of per-ad metrics dicts (from PerformanceTracker).

        Returns:
            List of pattern dicts with pattern_type, description, confidence,
            and supporting_ads.
        """
        if not metrics:
            return []

        patterns: List[Dict[str, Any]] = []

        # Filter ads with enough data
        valid = [m for m in metrics if m.get("impressions", 0) >= 10]
        if not valid:
            return []

        # --- Pattern: Best CTR ---
        sorted_by_ctr = sorted(valid, key=lambda x: x.get("ctr", 0), reverse=True)
        if sorted_by_ctr:
            best = sorted_by_ctr[0]
            avg_ctr = sum(m.get("ctr", 0) for m in valid) / len(valid)
            if best.get("ctr", 0) > avg_ctr * 1.2:
                patterns.append(
                    {
                        "pattern_type": "high_ctr",
                        "description": (
                            f"Ad {best['ad_id']} has CTR {best['ctr']:.2f}% "
                            f"vs avg {avg_ctr:.2f}%"
                        ),
                        "confidence": min(0.9, best["ctr"] / max(avg_ctr, 0.01)),
                        "supporting_ads": [best["ad_id"]],
                        "metric_value": best["ctr"],
                    }
                )

        # --- Pattern: Best ROAS ---
        sorted_by_roas = sorted(valid, key=lambda x: x.get("roas", 0), reverse=True)
        if sorted_by_roas:
            best = sorted_by_roas[0]
            if best.get("roas", 0) > 1.0:
                patterns.append(
                    {
                        "pattern_type": "high_roas",
                        "description": (
                            f"Ad {best['ad_id']} achieves {best['roas']:.2f}x ROAS"
                        ),
                        "confidence": min(0.95, best["roas"] / 3.0),
                        "supporting_ads": [best["ad_id"]],
                        "metric_value": best["roas"],
                    }
                )

        # --- Pattern: Best hook rate ---
        sorted_by_hook = sorted(
            valid, key=lambda x: x.get("hook_rate", 0), reverse=True
        )
        if sorted_by_hook:
            best = sorted_by_hook[0]
            avg_hook = sum(m.get("hook_rate", 0) for m in valid) / len(valid)
            if best.get("hook_rate", 0) > avg_hook * 1.15:
                patterns.append(
                    {
                        "pattern_type": "strong_hook",
                        "description": (
                            f"Ad {best['ad_id']} hook rate {best['hook_rate']:.2%} "
                            f"vs avg {avg_hook:.2%}"
                        ),
                        "confidence": min(0.85, best["hook_rate"] / max(avg_hook, 0.01)),
                        "supporting_ads": [best["ad_id"]],
                        "metric_value": best["hook_rate"],
                    }
                )

        # --- Pattern: Best hold rate ---
        sorted_by_hold = sorted(
            valid, key=lambda x: x.get("hold_rate", 0), reverse=True
        )
        if sorted_by_hold:
            best = sorted_by_hold[0]
            if best.get("hold_rate", 0) > 0.25:
                patterns.append(
                    {
                        "pattern_type": "strong_hold",
                        "description": (
                            f"Ad {best['ad_id']} hold rate {best['hold_rate']:.2%}"
                        ),
                        "confidence": min(0.85, best["hold_rate"] * 2),
                        "supporting_ads": [best["ad_id"]],
                        "metric_value": best["hold_rate"],
                    }
                )

        # --- Pattern: Under-performer ---
        worst_ctr = sorted_by_ctr[-1] if sorted_by_ctr else None
        if worst_ctr and avg_ctr > 0 and worst_ctr.get("ctr", 0) < avg_ctr * 0.5:
            patterns.append(
                {
                    "pattern_type": "underperformer",
                    "description": (
                        f"Ad {worst_ctr['ad_id']} CTR {worst_ctr['ctr']:.2f}% "
                        f"is well below avg {avg_ctr:.2f}%"
                    ),
                    "confidence": 0.8,
                    "supporting_ads": [worst_ctr["ad_id"]],
                    "metric_value": worst_ctr["ctr"],
                }
            )

        logger.info(
            f"[AD-006] Identified {len(patterns)} patterns from {len(valid)} ads"
        )
        return patterns

    def generate_next_test_suggestions(
        self, campaign_id: str
    ) -> List[Dict[str, Any]]:
        """
        Suggest next A/B tests based on current campaign performance.

        Args:
            campaign_id: The campaign to generate suggestions for.

        Returns:
            List of suggestion dicts with test_type, description,
            hypothesis, and priority.
        """
        metrics = self._get_campaign_metrics(campaign_id)
        if not metrics or metrics.get("status") == "no_data":
            return [
                {
                    "test_type": "initial",
                    "description": "Run initial broad test with 3-5 hook variations",
                    "hypothesis": "Different hooks will produce measurably different CTRs",
                    "priority": "high",
                }
            ]

        ad_breakdown = metrics.get("ad_breakdown", [])
        patterns = self.identify_winning_patterns(ad_breakdown)

        # Use AI if available
        if self._openai_client and patterns:
            try:
                return self._ai_suggest_tests(campaign_id, metrics, patterns)
            except Exception as exc:
                logger.error(f"[AD-006] AI suggestion failed: {exc}")

        # Heuristic suggestions
        return self._heuristic_suggestions(metrics, patterns)

    def get_audience_insights(self, campaign_id: str) -> Dict[str, Any]:
        """
        Generate audience-level insights for a campaign.

        Args:
            campaign_id: The campaign to analyse.

        Returns:
            Dict with audience segments, best performers, and recommendations.
        """
        metrics = self._get_campaign_metrics(campaign_id)
        if not metrics or metrics.get("status") == "no_data":
            return {
                "campaign_id": campaign_id,
                "segments": [],
                "best_segment": None,
                "recommendations": ["Not enough data for audience insights."],
            }

        # Group ads by audience (using campaign deployer data)
        audience_performance: Dict[str, Dict[str, Any]] = {}

        if self._campaign_deployer:
            campaign = self._campaign_deployer.get_campaign(campaign_id)
            if campaign:
                for ad_set_id in campaign.get("ad_sets", []):
                    ad_set = self._campaign_deployer.get_ad_set(ad_set_id)
                    if ad_set:
                        audience = ad_set.get("audience", {})
                        audience_name = audience.get("name", "unknown")

                        # Aggregate metrics for ads in this ad set
                        ad_ids = ad_set.get("ads", [])
                        segment_metrics = {"impressions": 0, "clicks": 0, "spend_cents": 0}
                        for ad_id in ad_ids:
                            ad_m = self._get_ad_metrics(ad_id)
                            if ad_m:
                                segment_metrics["impressions"] += ad_m.get("impressions", 0)
                                segment_metrics["clicks"] += ad_m.get("clicks", 0)
                                segment_metrics["spend_cents"] += int(
                                    ad_m.get("spend", 0) * 100
                                )

                        ctr = (
                            segment_metrics["clicks"]
                            / segment_metrics["impressions"]
                            * 100
                            if segment_metrics["impressions"] > 0
                            else 0
                        )
                        audience_performance[audience_name] = {
                            "audience": audience,
                            "impressions": segment_metrics["impressions"],
                            "clicks": segment_metrics["clicks"],
                            "ctr": round(ctr, 2),
                            "spend": round(segment_metrics["spend_cents"] / 100, 2),
                        }

        segments = list(audience_performance.values())
        best_segment = max(segments, key=lambda s: s.get("ctr", 0)) if segments else None

        recommendations = []
        if best_segment and best_segment.get("ctr", 0) > 0:
            recommendations.append(
                f"Scale budget toward '{best_segment['audience'].get('name', 'unknown')}' "
                f"segment (CTR: {best_segment['ctr']:.2f}%)"
            )
        if len(segments) < 3:
            recommendations.append("Test additional audience segments for broader coverage")

        return {
            "campaign_id": campaign_id,
            "segments": segments,
            "best_segment": best_segment,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # AI-powered analysis
    # ------------------------------------------------------------------

    def _ai_analyze(
        self,
        campaign_id: str,
        metrics: Dict[str, Any],
        patterns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use OpenAI to generate deep campaign analysis."""
        system_prompt = (
            "You are a senior Meta Ads performance analyst. "
            "Analyse campaign data and provide actionable insights. "
            "Return ONLY valid JSON with keys: winning_patterns (array), "
            "insights (array of strings), recommendations (array of strings), "
            "overall_grade (string: A/B/C/D/F)."
        )

        user_prompt = (
            f"Analyse this Meta ad campaign:\n\n"
            f"Campaign ID: {campaign_id}\n"
            f"Total impressions: {metrics.get('impressions', 0)}\n"
            f"Total clicks: {metrics.get('clicks', 0)}\n"
            f"CTR: {metrics.get('ctr', 0):.2f}%\n"
            f"ROAS: {metrics.get('roas', 0):.2f}x\n"
            f"Spend: ${metrics.get('spend', 0):.2f}\n"
            f"Ad count: {metrics.get('ad_count', 0)}\n\n"
            f"Detected patterns: {json.dumps(patterns, indent=2)}\n\n"
            f"Ad breakdown summary:\n"
        )

        for ad in metrics.get("ad_breakdown", [])[:10]:
            user_prompt += (
                f"  - {ad['ad_id']}: CTR={ad.get('ctr', 0):.2f}%, "
                f"ROAS={ad.get('roas', 0):.2f}x, "
                f"hook_rate={ad.get('hook_rate', 0):.2%}, "
                f"hold_rate={ad.get('hold_rate', 0):.2%}\n"
            )

        user_prompt += "\nProvide analysis with actionable recommendations."

        response = self._openai_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        result["campaign_id"] = campaign_id
        logger.info(
            f"[AD-006] AI analysis complete for {campaign_id}: "
            f"grade={result.get('overall_grade', 'N/A')}"
        )
        return result

    def _ai_suggest_tests(
        self,
        campaign_id: str,
        metrics: Dict[str, Any],
        patterns: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use OpenAI to suggest next A/B tests."""
        system_prompt = (
            "You are a Meta Ads testing strategist. "
            "Suggest the next 3-5 A/B tests based on campaign data. "
            "Return ONLY valid JSON: {\"suggestions\": [{\"test_type\": ..., "
            "\"description\": ..., \"hypothesis\": ..., \"priority\": \"high\"|\"medium\"|\"low\"}, ...]}"
        )

        user_prompt = (
            f"Current campaign {campaign_id} metrics:\n"
            f"CTR: {metrics.get('ctr', 0):.2f}%, ROAS: {metrics.get('roas', 0):.2f}x\n"
            f"Patterns found: {json.dumps([p['description'] for p in patterns])}\n\n"
            "What A/B tests should we run next?"
        )

        response = self._openai_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        suggestions = result.get("suggestions", [])
        logger.info(f"[AD-006] AI suggested {len(suggestions)} next tests")
        return suggestions

    # ------------------------------------------------------------------
    # Heuristic fallbacks
    # ------------------------------------------------------------------

    def _heuristic_analyze(
        self,
        campaign_id: str,
        metrics: Dict[str, Any],
        patterns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate analysis using heuristic rules."""
        insights: List[str] = []
        recommendations: List[str] = []

        ctr = metrics.get("ctr", 0)
        roas = metrics.get("roas", 0)
        ad_count = metrics.get("ad_count", 0)

        # CTR insights
        if ctr > 2.0:
            insights.append(f"Strong CTR at {ctr:.2f}% - above industry average")
        elif ctr > 0.8:
            insights.append(f"Average CTR at {ctr:.2f}% - room for improvement")
        elif ctr > 0:
            insights.append(f"Low CTR at {ctr:.2f}% - hooks need improvement")
            recommendations.append("Test new hooks with stronger emotional triggers")

        # ROAS insights
        if roas > 3.0:
            insights.append(f"Excellent ROAS at {roas:.2f}x - scale this campaign")
            recommendations.append("Increase budget by 20-30% on winning ads")
        elif roas > 1.0:
            insights.append(f"Positive ROAS at {roas:.2f}x - optimise for growth")
        elif roas > 0:
            insights.append(f"Below-breakeven ROAS at {roas:.2f}x")
            recommendations.append("Pause underperforming ads and reallocate budget")

        # Pattern-based insights
        for pattern in patterns:
            if pattern["pattern_type"] == "strong_hook":
                recommendations.append(
                    f"Iterate on the hook from {pattern['supporting_ads'][0]} "
                    f"(hook rate: {pattern['metric_value']:.2%})"
                )
            elif pattern["pattern_type"] == "underperformer":
                recommendations.append(
                    f"Consider pausing {pattern['supporting_ads'][0]} - "
                    f"significantly underperforming"
                )

        # Grade
        if ctr > 2.0 and roas > 3.0:
            grade = "A"
        elif ctr > 1.0 and roas > 1.5:
            grade = "B"
        elif ctr > 0.5 and roas > 1.0:
            grade = "C"
        elif ctr > 0:
            grade = "D"
        else:
            grade = "F"

        return {
            "campaign_id": campaign_id,
            "winning_patterns": patterns,
            "insights": insights,
            "recommendations": recommendations,
            "overall_grade": grade,
        }

    def _heuristic_suggestions(
        self,
        metrics: Dict[str, Any],
        patterns: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate test suggestions using heuristic rules."""
        suggestions: List[Dict[str, Any]] = []

        ctr = metrics.get("ctr", 0)
        hook_patterns = [p for p in patterns if p["pattern_type"] == "strong_hook"]
        hold_patterns = [p for p in patterns if p["pattern_type"] == "strong_hold"]

        # Always suggest hook testing
        if ctr < 1.5:
            suggestions.append(
                {
                    "test_type": "hook_variation",
                    "description": "Test 3-5 new hook variations with different emotional angles",
                    "hypothesis": "Stronger hooks will improve CTR above current baseline",
                    "priority": "high",
                }
            )

        # Audience expansion
        if metrics.get("ad_count", 0) > 3:
            suggestions.append(
                {
                    "test_type": "audience_expansion",
                    "description": "Test winning creatives with new audience segments",
                    "hypothesis": "Best creatives will perform well in adjacent audiences",
                    "priority": "medium",
                }
            )

        # CTA testing
        suggestions.append(
            {
                "test_type": "cta_variation",
                "description": "Test different CTAs on the best-performing ad",
                "hypothesis": "CTA wording impacts conversion rate independently of creative",
                "priority": "medium",
            }
        )

        # Format testing
        if not hold_patterns:
            suggestions.append(
                {
                    "test_type": "format_variation",
                    "description": "Test shorter video formats (15s vs 30s) to improve hold rate",
                    "hypothesis": "Shorter videos will have higher completion rates",
                    "priority": "low",
                }
            )

        return suggestions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_campaign_metrics(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve campaign metrics from the performance tracker."""
        if self._performance_tracker:
            return self._performance_tracker.get_campaign_metrics(campaign_id)
        logger.warning("[AD-006] No performance tracker available")
        return None

    def _get_ad_metrics(self, ad_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve ad metrics from the performance tracker."""
        if self._performance_tracker:
            return self._performance_tracker.get_ad_metrics(ad_id)
        return None


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_ai_learner_instance: Optional[AdAILearner] = None


def get_ai_learner() -> AdAILearner:
    """Get or create the singleton AdAILearner instance."""
    global _ai_learner_instance
    if _ai_learner_instance is None:
        _ai_learner_instance = AdAILearner()
    return _ai_learner_instance

"""
Content Recommendation
======================
Fuses live "what's trending right now in this niche" (trend_detection.py)
with this account's own historical top-performers (content_intelligence.py)
into a single "what should I post next" recommendation, optionally scoped to
a Brand's voice/audience.

Neither input is required to have data: a fresh account with no posting
history still gets a trend-only recommendation; a niche-less brand still
gets a history-only recommendation. Only truly empty of both degrades to a
plain "not enough data yet" response.
"""
import json
import os
from typing import Any, Dict, List, Optional

from loguru import logger

from services.content_intelligence import ContentIntelligenceEngine
from services.trend_detection import TrendDetectionService


class ContentRecommendationService:
    def __init__(self):
        self.trends = TrendDetectionService()
        self.intel = ContentIntelligenceEngine()

    async def recommend_next_content(
        self,
        niche: Optional[str] = None,
        brand_voice: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None,
        available_minutes: Optional[int] = None,
        primary_goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        `niche` is optional — without it, this degrades to a purely
        historical-performance recommendation (no live trend signal).
        `primary_goal` (e.g. "audience_growth", "revenue") shapes the GPT
        synthesis reasoning/format toward that outcome; ignored by the
        deterministic fallback, which just surfaces the strongest signal.
        """
        trending: Dict[str, Any] = {"trending": [], "niche": niche}
        if niche:
            try:
                trending = await self.trends.get_trending_for_niche(niche, limit=8)
            except Exception as e:
                logger.warning(f"[Recommend] trend lookup failed for niche={niche!r}: {e}")

        patterns = await self.intel.analyze_patterns(lookback_days=90)
        if "error" in patterns:
            logger.warning(f"[Recommend] historical pattern analysis unavailable: {patterns['error']}")
            patterns = {}

        return await self._synthesize(
            trending=trending,
            patterns=patterns,
            brand_voice=brand_voice,
            target_audience=target_audience,
            available_minutes=available_minutes,
            primary_goal=primary_goal,
        )

    async def _synthesize(
        self,
        *,
        trending: Dict[str, Any],
        patterns: Dict[str, Any],
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str],
        available_minutes: Optional[int],
        primary_goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        top_trends = trending.get("trending", [])[:5]
        top_topics = patterns.get("top_topics", [])[:5]
        top_hooks = patterns.get("top_hooks", [])[:5]
        top_tones = patterns.get("top_tones", [])[:5]

        sources = {
            "trend_count": len(top_trends),
            "historical_post_count": patterns.get("total_posts_analyzed", 0),
        }

        if not top_trends and not top_topics:
            return {
                "recommendation": None,
                "reasoning": "No trend data and no historical performance data available yet.",
                "sources": sources,
            }

        try:
            rec = await self._gpt_synthesize(
                top_trends, top_topics, top_hooks, top_tones,
                brand_voice, target_audience, available_minutes, primary_goal,
            )
        except Exception as e:
            logger.warning(f"[Recommend] GPT synthesis failed, falling back to top signal: {e}")
            rec = self._deterministic_fallback(top_trends, top_topics, top_hooks, top_tones)

        return {"recommendation": rec, "sources": sources}

    @staticmethod
    async def _gpt_synthesize(
        top_trends: List[Dict[str, Any]],
        top_topics: List[Dict[str, Any]],
        top_hooks: List[Dict[str, Any]],
        top_tones: List[Dict[str, Any]],
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str],
        available_minutes: Optional[int],
        primary_goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        voice_desc = json.dumps(brand_voice) if brand_voice else "no specific voice configured"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a content strategist. Recommend exactly ONE piece of content to
post next, fusing what's trending right now with what has historically
performed well for this specific creator. Favor genuine overlap between the
two signals when it exists; when it doesn't, say so plainly in `reasoning`
rather than forcing a connection that isn't there.

Brand voice: {voice_desc}
Target audience: {target_audience or 'not specified'}
Available time to produce today: {available_minutes if available_minutes is not None else 'not specified'} minutes
Creator's primary goal: {primary_goal or 'not specified'} — weight the angle,
format, and CTA implied by `reasoning` toward this goal specifically (e.g.
audience_growth favors broad-hook discoverable formats; revenue/leads favor a
clear product/offer tie-in; authority favors depth/credibility over reach).

Return JSON: {{"topic": str, "angle": str, "format": str, "platform": str,
"hook": str, "reasoning": str, "cites_trend": bool, "cites_history": bool,
"confidence": 0.0-1.0}}""",
                },
                {
                    "role": "user",
                    "content": (
                        f"Currently trending in this niche: {json.dumps(top_trends)}\n"
                        f"This account's historically top-performing topics: {json.dumps(top_topics)}\n"
                        f"Top-performing hook types: {json.dumps(top_hooks)}\n"
                        f"Top-performing tones: {json.dumps(top_tones)}"
                    ),
                },
            ],
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    @staticmethod
    def _deterministic_fallback(
        top_trends: List[Dict[str, Any]],
        top_topics: List[Dict[str, Any]],
        top_hooks: List[Dict[str, Any]],
        top_tones: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """No-AI-provider fallback: surface the single strongest available signal."""
        if top_trends:
            t = top_trends[0]
            return {
                "topic": t["identifier"],
                "angle": t.get("description", ""),
                "format": "short-form video",
                "platform": t.get("platform", ""),
                "hook": None,
                "reasoning": f"Highest-scoring live trend (score={t.get('score', 0)}).",
                "cites_trend": True,
                "cites_history": False,
                "confidence": t.get("score", 0.5),
            }
        t = top_topics[0]
        return {
            "topic": t["name"],
            "angle": None,
            "format": None,
            "platform": None,
            "hook": top_hooks[0]["name"] if top_hooks else None,
            "reasoning": (
                f"Highest average-engagement topic historically "
                f"({t['avg_engagement']} avg engagement over {t['post_count']} posts)."
            ),
            "cites_trend": False,
            "cites_history": True,
            "confidence": min(t["post_count"] / 10, 1.0),
        }


_service: Optional[ContentRecommendationService] = None


def get_content_recommendation_service() -> ContentRecommendationService:
    global _service
    if _service is None:
        _service = ContentRecommendationService()
    return _service

"""
Automated Trend Detection
===========================
Monitors trending sounds, hashtags, and topics across TikTok, Instagram,
and Twitter via RapidAPI. Filters for niche relevance, scores trends,
and generates content briefs for hot opportunities.

Components:
1. TrendScanner       — Platform-specific trend data fetchers
2. NicheFilter        — GPT + keyword relevance filtering
3. TrendScorer        — Composite ranking (velocity × volume × niche fit)
4. TrendBriefGen      — Auto-generate briefs for high-score trends
5. AlertSystem        — macOS notification for time-sensitive trends

Usage:
    detector = TrendDetectionService()
    
    # Full scan cycle (cron every 2 hours)
    results = await detector.run_scan_cycle()
    
    # Get current hot trends
    trends = await detector.get_trends(status="hot", limit=10)
    
    # Generate brief for a specific trend
    brief = await detector.generate_trend_brief(trend_id)
"""

import os
import json
import uuid
import httpx
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from loguru import logger


# ─── Creator Niche Config ────────────────────────────────────────────────────

CREATOR_NICHE = {
    "primary_topics": [
        "relationships", "dating", "self-improvement", "masculinity",
        "motivation", "love", "marriage",
    ],
    "secondary_topics": [
        "lifestyle", "fitness", "mental health", "entrepreneurship",
        "productivity", "confidence", "communication",
    ],
    "brand_keywords": [
        "love", "dating tips", "relationship advice", "grow", "mindset",
        "self love", "attachment", "boundaries", "red flags", "green flags",
        "toxic", "healthy relationship", "emotional intelligence",
    ],
    "exclude_topics": [
        "politics", "religion", "explicit", "gore", "gambling",
    ],
}

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")


class TrendDetectionService:
    """Full trend detection pipeline."""

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 1. TREND SCANNERS — Platform-specific data fetchers
    # ═══════════════════════════════════════════════════════════════════════

    async def scan_tiktok_for_niche(self, niche: str, count: int = 20) -> List[Dict[str, Any]]:
        """Search TikTok for real videos matching `niche` via RapidAPI's
        /feed/search. Used by get_trending_for_niche() instead of
        scan_tiktok_trending(): that method's endpoint
        (/trending/hashtags) does not exist on this API (confirmed 404 with a
        valid key), and its fallback is a hardcoded single-tenant topic list
        that would be wrong for an arbitrary caller-supplied niche. No
        fallback here — a missing key or a failed call means TikTok
        contributes nothing to this call, not hardcoded off-topic content.
        """
        if not RAPIDAPI_KEY:
            logger.warning(f"[Trends] No RAPIDAPI_KEY set, skipping TikTok search for niche={niche!r}")
            return []

        trends: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://tiktok-scraper7.p.rapidapi.com/feed/search",
                    params={"keywords": niche, "count": count},
                    headers={
                        "X-RapidAPI-Key": RAPIDAPI_KEY,
                        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    videos = (data.get("data") or {}).get("videos", [])
                    for v in videos:
                        title = (v.get("title") or "").strip()
                        if not title:
                            continue
                        trends.append({
                            "source_platform": "tiktok",
                            "trend_type": "video",
                            "trend_identifier": title[:80],
                            "trend_description": title,
                            "volume_raw": v.get("play_count", 0),
                        })
            logger.info(f"[Trends] TikTok search for {niche!r}: {len(trends)} videos found")
        except Exception as e:
            logger.warning(f"[Trends] TikTok search failed for niche={niche!r}: {e}")

        return trends

    async def scan_tiktok_trending(self) -> List[Dict[str, Any]]:
        """Scan TikTok for trending hashtags via RapidAPI.

        KNOWN BROKEN: /trending/hashtags does not exist on this API (confirmed
        404 with a valid key) — only used by the pre-existing single-tenant
        run_scan_cycle() pipeline. get_trending_for_niche() uses
        scan_tiktok_for_niche() instead, which hits a real, verified endpoint.
        Left as-is here since fixing run_scan_cycle()'s TikTok strategy changes
        what that separate cron pipeline stores/alerts on — a bigger decision
        than the niche-query bug this method exists to avoid.
        """
        trends = []
        if not RAPIDAPI_KEY:
            logger.warning("[Trends] No RAPIDAPI_KEY set, using fallback")
            return await self._fallback_tiktok_trends()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # TikTok trending hashtags
                resp = await client.get(
                    "https://tiktok-scraper7.p.rapidapi.com/trending/hashtags",
                    headers={
                        "X-RapidAPI-Key": RAPIDAPI_KEY,
                        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    hashtags = data.get("data", data.get("hashtags", []))
                    if isinstance(hashtags, list):
                        for h in hashtags[:30]:
                            name = h.get("name", h.get("hashtag", "")) if isinstance(h, dict) else str(h)
                            views = h.get("view_count", h.get("views", 0)) if isinstance(h, dict) else 0
                            trends.append({
                                "source_platform": "tiktok",
                                "trend_type": "hashtag",
                                "trend_identifier": f"#{name}" if not name.startswith("#") else name,
                                "trend_description": f"Trending TikTok hashtag: {name}",
                                "volume_raw": views,
                            })

            logger.info(f"[Trends] TikTok scan: {len(trends)} hashtags found")

        except Exception as e:
            logger.warning(f"[Trends] TikTok scan failed: {e}")
            trends = await self._fallback_tiktok_trends()

        return trends

    async def scan_google_trends_for_niche(self, niche: str) -> List[Dict[str, Any]]:
        """Real Google Trends interest signal for `niche`, via
        interest_over_time() (the modern /trends/api/explore + widgetdata
        flow). Used by get_trending_for_niche() instead of
        scan_google_trends(): that method's trending_searches() call hits
        Google's old hottrends/visualize/internal/data endpoint, which is
        dead — confirmed 404 directly from Google, a known pytrends/Google
        API deprecation, not a transient outage. interest_over_time() is
        confirmed live and working.
        """
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload([niche], timeframe="now 7-d")
            df = pytrends.interest_over_time()
            if df is None or df.empty or niche not in df.columns:
                logger.info(f"[Trends] Google Trends: no interest data for niche={niche!r}")
                return []

            current = float(df[niche].iloc[-1])
            baseline = float(df[niche].mean())
            rising = baseline > 0 and current > baseline * 1.1
            logger.info(
                f"[Trends] Google Trends for {niche!r}: current={current:.0f} 7d_avg={baseline:.0f} "
                f"{'(rising)' if rising else ''}"
            )
            return [{
                "source_platform": "google",
                "trend_type": "topic",
                "trend_identifier": niche,
                "trend_description": (
                    f"Google Trends interest for '{niche}': current={current:.0f}, "
                    f"7-day avg={baseline:.0f}{' — rising' if rising else ''}"
                ),
                "volume_raw": int(current),
            }]

        except ImportError:
            logger.debug("[Trends] pytrends not installed, skipping Google Trends")
        except Exception as e:
            logger.warning(f"[Trends] Google Trends scan failed for niche={niche!r}: {e}")

        return []

    async def scan_google_trends(self) -> List[Dict[str, Any]]:
        """Scan Google Trends for rising topics in niche.

        KNOWN BROKEN: trending_searches() hits Google's old hottrends/
        visualize/internal/data endpoint, which returns 404 (dead, not an
        outage) — only used by the pre-existing single-tenant
        run_scan_cycle() pipeline. get_trending_for_niche() uses
        scan_google_trends_for_niche() instead, which hits interest_over_time(),
        confirmed live. Left as-is here for the same reason as
        scan_tiktok_trending(): fixing run_scan_cycle()'s Google Trends
        strategy is a separate decision from the niche-query bug this
        method exists to avoid.
        """
        trends = []
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360)
            # Check trending searches
            trending = pytrends.trending_searches(pn="united_states")
            if trending is not None and not trending.empty:
                for idx, row in trending.head(20).iterrows():
                    topic = row[0] if len(row) > 0 else str(row)
                    trends.append({
                        "source_platform": "google",
                        "trend_type": "topic",
                        "trend_identifier": str(topic),
                        "trend_description": f"Google trending search: {topic}",
                        "volume_raw": 0,
                    })

            logger.info(f"[Trends] Google scan: {len(trends)} topics found")

        except ImportError:
            logger.debug("[Trends] pytrends not installed, skipping Google Trends")
        except Exception as e:
            logger.warning(f"[Trends] Google Trends scan failed: {e}")

        return trends

    async def _fallback_tiktok_trends(self) -> List[Dict[str, Any]]:
        """Niche-specific trending topics when API unavailable."""
        niche_trends = [
            "relationship advice", "dating in 2025", "green flags",
            "emotional intelligence", "attachment styles", "self improvement",
            "healthy boundaries", "communication tips", "masculine energy",
            "feminine energy", "love language", "situationship",
        ]
        return [
            {
                "source_platform": "tiktok",
                "trend_type": "topic",
                "trend_identifier": f"#{t.replace(' ', '')}",
                "trend_description": f"Niche trending topic: {t}",
                "volume_raw": 0,
            }
            for t in niche_trends
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # 2. NICHE RELEVANCE FILTER — GPT + keyword matching
    # ═══════════════════════════════════════════════════════════════════════

    async def filter_by_niche(
        self, raw_trends: List[Dict[str, Any]], niche: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Two-stage filter:
        1. Fast keyword matching
        2. GPT relevance scoring for ambiguous ones

        `niche` overrides the module-level CREATOR_NICHE config for this call only
        — used by get_trending_for_niche() to score against an arbitrary,
        caller-supplied niche instead of the hardcoded single-tenant config.
        run_scan_cycle() calls this with no `niche` arg, so its behavior is unchanged.
        """
        niche_cfg = niche or CREATOR_NICHE
        all_keywords = (
            niche_cfg.get("primary_topics", [])
            + niche_cfg.get("secondary_topics", [])
            + niche_cfg.get("brand_keywords", [])
        )
        exclude = niche_cfg.get("exclude_topics", [])

        filtered = []
        ambiguous = []

        for trend in raw_trends:
            identifier = (trend.get("trend_identifier") or "").lower()
            description = (trend.get("trend_description") or "").lower()
            text = f"{identifier} {description}"

            # Exclude check
            if any(ex.lower() in text for ex in exclude):
                continue

            # Keyword match
            keyword_match = any(kw.lower() in text for kw in all_keywords)
            if keyword_match:
                trend["niche_relevance"] = 0.8
                filtered.append(trend)
            else:
                ambiguous.append(trend)

        # GPT filter for ambiguous trends (batch)
        if ambiguous:
            gpt_scored = await self._gpt_niche_score(ambiguous[:15], niche_cfg)
            for trend in gpt_scored:
                if trend.get("niche_relevance", 0) >= 0.5:
                    filtered.append(trend)

        logger.info(f"[Trends] Niche filter: {len(filtered)}/{len(raw_trends)} relevant")
        return filtered

    async def _gpt_niche_score(
        self, trends: List[Dict[str, Any]], niche: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Use GPT to score niche relevance of ambiguous trends."""
        niche_cfg = niche or CREATOR_NICHE
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            trend_texts = [
                f"{t.get('trend_identifier', '')} - {t.get('trend_description', '')}"
                for t in trends
            ]

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a social media trend analyst. The creator's niche is:
Primary: {', '.join(niche_cfg.get('primary_topics', []))}
Secondary: {', '.join(niche_cfg.get('secondary_topics', []))}

Score each trend's relevance to this niche from 0.0 to 1.0.
Return JSON: {{"scores": [{{"index": 0, "relevance": 0.8, "reason": "..."}}]}}""",
                    },
                    {"role": "user", "content": f"Score these trends:\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(trend_texts))},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            scores = result.get("scores", [])

            for score_entry in scores:
                idx = score_entry.get("index", 0)
                if 0 <= idx < len(trends):
                    trends[idx]["niche_relevance"] = score_entry.get("relevance", 0.3)

        except Exception as e:
            logger.warning(f"[Trends] GPT niche scoring failed: {e}")
            for t in trends:
                t.setdefault("niche_relevance", 0.3)

        return trends

    # ═══════════════════════════════════════════════════════════════════════
    # 3. TREND SCORER — Composite ranking
    # ═══════════════════════════════════════════════════════════════════════

    def score_trend(self, trend: Dict[str, Any]) -> float:
        """
        Composite score:
        - velocity (growth speed): 0.3 weight
        - volume (current size): 0.2 weight
        - niche_fit: 0.3 weight
        - freshness: 0.2 weight
        """
        volume_raw = trend.get("volume_raw", 0)
        # Normalize volume to 0-1 (log scale)
        import math
        volume_score = min(1.0, math.log10(max(volume_raw, 1)) / 8) if volume_raw > 0 else 0.3

        niche_relevance = trend.get("niche_relevance", 0.5)
        velocity = trend.get("velocity_score", 0.5)
        freshness = 0.8  # Default high for new detections

        composite = (
            velocity * 0.3
            + volume_score * 0.2
            + niche_relevance * 0.3
            + freshness * 0.2
        )

        trend["velocity_score"] = velocity
        trend["volume_score"] = round(volume_score, 3)
        trend["composite_score"] = round(composite, 3)

        return composite

    # ═══════════════════════════════════════════════════════════════════════
    # 4. FULL SCAN CYCLE — Run as cron
    # ═══════════════════════════════════════════════════════════════════════

    async def run_scan_cycle(self) -> Dict[str, Any]:
        """
        Full trend detection cycle:
        1. Scan all platforms
        2. Filter by niche
        3. Score and rank
        4. Store new trends
        5. Alert on high-score trends
        """
        # 1. Scan
        all_trends = []
        tiktok = await self.scan_tiktok_trending()
        all_trends.extend(tiktok)
        google = await self.scan_google_trends()
        all_trends.extend(google)

        # 2. Filter
        relevant = await self.filter_by_niche(all_trends)

        # 3. Score
        for trend in relevant:
            self.score_trend(trend)

        # Sort by composite score
        relevant.sort(key=lambda t: t.get("composite_score", 0), reverse=True)

        # 4. Store
        stored = 0
        alerted = 0
        from sqlalchemy import create_engine, text
        engine = create_engine(self.db_url)

        with engine.connect() as conn:
            for trend in relevant[:20]:
                # Check if already detected
                existing = conn.execute(text("""
                    SELECT id FROM detected_trends
                    WHERE trend_identifier = :identifier AND source_platform = :platform
                """), {
                    "identifier": trend["trend_identifier"],
                    "platform": trend["source_platform"],
                }).fetchone()

                if existing:
                    # Update last_seen
                    conn.execute(text("""
                        UPDATE detected_trends SET
                            last_seen_at = NOW(),
                            composite_score = GREATEST(composite_score, :score)
                        WHERE id = :id
                    """), {"id": str(existing[0]), "score": trend.get("composite_score", 0)})
                else:
                    # Insert new
                    trend_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO detected_trends (
                            id, source_platform, trend_type, trend_identifier,
                            trend_description, velocity_score, volume_score,
                            niche_relevance, composite_score, status
                        ) VALUES (
                            :id, :platform, :type, :identifier,
                            :description, :velocity, :volume,
                            :niche, :composite, 'emerging'
                        )
                    """), {
                        "id": trend_id,
                        "platform": trend["source_platform"],
                        "type": trend.get("trend_type", "topic"),
                        "identifier": trend["trend_identifier"],
                        "description": trend.get("trend_description", ""),
                        "velocity": trend.get("velocity_score", 0.5),
                        "volume": trend.get("volume_score", 0),
                        "niche": trend.get("niche_relevance", 0.5),
                        "composite": trend.get("composite_score", 0),
                    })
                    stored += 1

                    # Alert for high-score trends
                    if trend.get("composite_score", 0) >= 0.7:
                        await self._send_alert(trend)
                        alerted += 1

            conn.commit()

        # 5. Update trend statuses
        await self._update_trend_statuses()

        logger.success(
            f"[Trends] ✓ Scan complete | Scanned: {len(all_trends)} | "
            f"Relevant: {len(relevant)} | New: {stored} | Alerted: {alerted}"
        )

        return {
            "scanned": len(all_trends),
            "relevant": len(relevant),
            "new_stored": stored,
            "alerted": alerted,
            "top_trends": [
                {
                    "identifier": t["trend_identifier"],
                    "platform": t["source_platform"],
                    "score": t.get("composite_score", 0),
                    "niche_fit": t.get("niche_relevance", 0),
                }
                for t in relevant[:5]
            ],
        }

    # ═══════════════════════════════════════════════════════════════════════
    # 5. TREND BRIEF GENERATOR
    # ═══════════════════════════════════════════════════════════════════════

    async def generate_trend_brief(self, trend_id: str) -> Dict[str, Any]:
        """Generate a content brief for a specific trend."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT trend_identifier, trend_description, source_platform,
                           trend_type, composite_score, niche_relevance
                    FROM detected_trends WHERE id = :id
                """), {"id": trend_id}).fetchone()

            if not row:
                return {"error": "Trend not found"}

            identifier, description, platform = row[0], row[1], row[2]
            trend_type, score, niche = row[3], row[4], row[5]

            # Generate brief via GPT
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a viral content strategist. A trend has been detected that's relevant to the creator's niche (relationships, dating, self-improvement, motivation).

Create a content brief that rides this trend. Return JSON:
{{
    "topic": "specific content idea leveraging this trend",
    "hook": "scroll-stopping first line",
    "sora_prompt": "detailed Sora video generation prompt (~50 words, cinematic, emotional)",
    "caption_draft": "ready-to-post caption with hashtags incorporating the trend",
    "urgency": "high/medium/low",
    "window_hours": estimated hours before trend peaks,
    "reasoning": "why this angle works"
}}""",
                    },
                    {
                        "role": "user",
                        "content": f"Trend: {identifier}\nDescription: {description}\nPlatform: {platform}\nType: {trend_type}\nScore: {score}",
                    },
                ],
                temperature=0.8,
                response_format={"type": "json_object"},
            )

            brief = json.loads(response.choices[0].message.content)

            # Store
            brief_id = str(uuid.uuid4())
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO trend_briefs (id, trend_id, sora_prompt, suggested_caption, urgency, window_hours)
                    VALUES (:id, :trend_id, :sora, :caption, :urgency, :window)
                """), {
                    "id": brief_id,
                    "trend_id": trend_id,
                    "sora": brief.get("sora_prompt", ""),
                    "caption": brief.get("caption_draft", ""),
                    "urgency": brief.get("urgency", "medium"),
                    "window": brief.get("window_hours", 24),
                })
                conn.execute(text("UPDATE detected_trends SET brief_generated = true WHERE id = :id"), {"id": trend_id})
                conn.commit()

            logger.success(f"[Trends] ✓ Brief generated for trend: {identifier}")
            return {"brief_id": brief_id, "trend_id": trend_id, **brief}

        except Exception as e:
            logger.error(f"[Trends] Brief generation failed: {e}")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 6. QUERIES
    # ═══════════════════════════════════════════════════════════════════════

    async def get_trends(
        self,
        status: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get detected trends with filters."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            query = """SELECT id, source_platform, trend_type, trend_identifier,
                              trend_description, velocity_score, volume_score,
                              niche_relevance, composite_score, status,
                              first_detected_at, last_seen_at, brief_generated, alerted
                       FROM detected_trends WHERE composite_score >= :min_score"""
            params: Dict[str, Any] = {"min_score": min_score, "limit": limit}
            if status:
                query += " AND status = :status"
                params["status"] = status
            query += " ORDER BY composite_score DESC LIMIT :limit"

            with engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "source_platform": r[1],
                    "trend_type": r[2],
                    "trend_identifier": r[3],
                    "trend_description": r[4],
                    "velocity_score": r[5],
                    "volume_score": r[6],
                    "niche_relevance": r[7],
                    "composite_score": r[8],
                    "status": r[9],
                    "first_detected_at": r[10].isoformat() if r[10] else None,
                    "last_seen_at": r[11].isoformat() if r[11] else None,
                    "brief_generated": r[12],
                    "alerted": r[13],
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"[Trends] Get trends failed: {e}")
            return []

    async def update_niche_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update the niche relevance configuration."""
        global CREATOR_NICHE
        if "primary_topics" in config:
            CREATOR_NICHE["primary_topics"] = config["primary_topics"]
        if "secondary_topics" in config:
            CREATOR_NICHE["secondary_topics"] = config["secondary_topics"]
        if "brand_keywords" in config:
            CREATOR_NICHE["brand_keywords"] = config["brand_keywords"]
        if "exclude_topics" in config:
            CREATOR_NICHE["exclude_topics"] = config["exclude_topics"]
        return {"niche_config": CREATOR_NICHE}

    @staticmethod
    def _ad_hoc_niche_config(niche: str) -> Dict[str, Any]:
        """Build a niche config for an arbitrary caller-supplied niche string.

        Unlike CREATOR_NICHE (a hand-curated keyword list for one hardcoded
        brand), an arbitrary niche has no pre-built keyword list — the niche
        string itself is passed straight through as both the GPT-facing topic
        description and the keyword-match term. exclude_topics still applies
        globally (politics/religion/explicit/gore/gambling stay excluded
        regardless of niche).
        """
        return {
            "primary_topics": [niche],
            "secondary_topics": [],
            "brand_keywords": [niche],
            "exclude_topics": CREATOR_NICHE.get("exclude_topics", []),
        }

    async def get_trending_for_niche(self, niche: str, limit: int = 15) -> Dict[str, Any]:
        """Live, on-demand "what's trending right now" for an arbitrary niche.

        No DB persistence and no dependency on the single-tenant CREATOR_NICHE
        global — every call is scoped to the `niche` argument. Combines:
        - TikTok + Google Trends raw scans (scan_tiktok_for_niche/scan_google_trends_for_niche)
        - keyword+GPT relevance filtering against THIS niche (not CREATOR_NICHE)
        - composite scoring (score_trend)
        - Instagram niche-discovery signal (hashtags/accounts) from
          niche_search_service, a separate real RapidAPI-backed source
        """
        niche = niche.strip()
        if not niche:
            raise ValueError("niche must be a non-empty string")

        niche_cfg = self._ad_hoc_niche_config(niche)

        raw_trends: List[Dict[str, Any]] = []
        raw_trends.extend(await self.scan_tiktok_for_niche(niche))
        raw_trends.extend(await self.scan_google_trends_for_niche(niche))

        relevant = await self.filter_by_niche(raw_trends, niche=niche_cfg)
        for trend in relevant:
            self.score_trend(trend)
        relevant.sort(key=lambda t: t.get("composite_score", 0), reverse=True)

        instagram_context: Dict[str, Any] = {"hashtags": [], "accounts": []}
        try:
            from services.niche_search_service import get_niche_search_service
            ig_data = await get_niche_search_service().discover_niche(niche)
            instagram_context = {
                "hashtags": ig_data.related_hashtags[:10],
                "accounts": ig_data.top_accounts[:10],
            }
        except Exception as e:
            logger.warning(f"[Trends] Instagram niche discovery failed for {niche!r}: {e}")

        return {
            "niche": niche,
            "trending": [
                {
                    "identifier": t["trend_identifier"],
                    "platform": t["source_platform"],
                    "type": t.get("trend_type", "topic"),
                    "description": t.get("trend_description", ""),
                    "score": t.get("composite_score", 0),
                    "niche_fit": t.get("niche_relevance", 0),
                }
                for t in relevant[:limit]
            ],
            "instagram_context": instagram_context,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Private Helpers ──────────────────────────────────────────────────

    async def _update_trend_statuses(self) -> None:
        """Update trend statuses based on age and last-seen."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                # Emerging → hot (seen multiple times)
                conn.execute(text("""
                    UPDATE detected_trends SET status = 'hot'
                    WHERE status = 'emerging'
                      AND last_seen_at > first_detected_at + INTERVAL '2 hours'
                      AND composite_score >= 0.6
                """))
                # Hot → peaked (not seen recently)
                conn.execute(text("""
                    UPDATE detected_trends SET status = 'peaked', peak_at = last_seen_at
                    WHERE status = 'hot'
                      AND last_seen_at < NOW() - INTERVAL '12 hours'
                """))
                # Peaked → declining
                conn.execute(text("""
                    UPDATE detected_trends SET status = 'declining'
                    WHERE status = 'peaked'
                      AND last_seen_at < NOW() - INTERVAL '48 hours'
                """))
                conn.commit()
        except Exception as e:
            logger.warning(f"[Trends] Status update failed: {e}")

    async def _send_alert(self, trend: Dict[str, Any]) -> None:
        """Send macOS notification for high-score trend."""
        try:
            identifier = trend.get("trend_identifier", "Unknown")
            score = trend.get("composite_score", 0)
            subprocess.run([
                "osascript", "-e",
                f'display notification "Score: {score:.2f} — {identifier}" '
                f'with title "🔥 Trending Alert" subtitle "MediaPoster Trend Detection"'
            ], timeout=5)
            logger.info(f"[Trends] Alert sent: {identifier} (score={score:.2f})")
        except Exception as e:
            logger.debug(f"[Trends] Alert failed: {e}")

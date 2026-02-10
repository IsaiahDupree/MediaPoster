"""
Closed-Loop Content Intelligence
==================================
Self-improving content system: tracks what works → analyzes patterns →
generates data-backed briefs → feeds the content pipeline → measures → learns.

Components:
1. PerformanceTracker — AI-tags post attributes + computes performance index
2. PatternAnalyzer   — Discovers winning/losing patterns across all content
3. BriefGenerator    — Creates GPT-powered content briefs + Sora prompts

Usage:
    intel = ContentIntelligenceEngine()
    
    # Tag a post's attributes via AI
    attrs = await intel.tag_post(post_id)
    
    # Analyze patterns across all content
    patterns = await intel.analyze_patterns(lookback_days=90)
    
    # Generate data-backed content briefs
    briefs = await intel.generate_briefs(count=7)
    
    # Get weekly intelligence report
    report = await intel.weekly_report()
"""

import os
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from loguru import logger


# ─── Constants ───────────────────────────────────────────────────────────────

TOPIC_CATEGORIES = [
    "relationship_advice", "self_improvement", "motivation", "humor",
    "lifestyle", "tech", "productivity", "finance", "health_fitness",
    "education", "entertainment", "behind_the_scenes", "trending_reaction",
    "storytelling", "controversial_take",
]

HOOK_TYPES = [
    "question", "bold_claim", "story", "controversy", "listicle",
    "statistic", "challenge", "confession", "prediction", "how_to",
]

EMOTIONAL_TONES = [
    "inspirational", "funny", "provocative", "educational",
    "vulnerable", "confident", "urgent", "nostalgic", "relatable",
]

VISUAL_STYLES = [
    "talking_head", "cinematic", "text_overlay", "montage",
    "screen_recording", "voiceover", "split_screen", "reaction",
]


class ContentIntelligenceEngine:
    """Full closed-loop content intelligence system."""

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 1. PERFORMANCE TRACKER — AI-tag posts + compute scores
    # ═══════════════════════════════════════════════════════════════════════

    async def tag_post(self, post_id: str) -> Dict[str, Any]:
        """
        Use GPT to extract content attributes from a post's caption/title.
        Stores results in content_attributes table.
        """
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            # Fetch post data
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT pc.id, pc.platform, pc.caption, pc.title,
                           sp.media_path, sp.content_id
                    FROM posted_content pc
                    LEFT JOIN scheduled_posts sp ON sp.id = pc.scheduled_post_id
                    WHERE pc.id = :id
                """), {"id": post_id}).fetchone()

            if not row:
                return {"error": "Post not found"}

            caption = row[2] or row[3] or ""
            platform = row[1] or "unknown"

            if not caption.strip():
                return {"error": "No caption to analyze"}

            # AI attribute extraction
            attributes = await self._ai_extract_attributes(caption, platform)

            # Store in DB
            attr_id = str(uuid.uuid4())
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO content_attributes (
                        id, post_id, platform, topic_category, hook_type,
                        emotional_tone, visual_style, caption_structure,
                        ai_confidence, created_at
                    ) VALUES (
                        :id, :post_id, :platform, :topic, :hook,
                        :tone, :style, :structure, :confidence, NOW()
                    )
                """), {
                    "id": attr_id,
                    "post_id": post_id,
                    "platform": platform,
                    "topic": attributes.get("topic_category"),
                    "hook": attributes.get("hook_type"),
                    "tone": attributes.get("emotional_tone"),
                    "style": attributes.get("visual_style"),
                    "structure": attributes.get("caption_structure"),
                    "confidence": attributes.get("confidence", 0.8),
                })
                conn.commit()

            logger.info(f"[Intel] Tagged post {post_id[:8]}: {attributes.get('topic_category')} / {attributes.get('hook_type')}")
            return {"post_id": post_id, "attributes": attributes}

        except Exception as e:
            logger.error(f"[Intel] Tag post failed: {e}")
            return {"error": str(e)}

    async def tag_untagged_posts(self, limit: int = 20) -> Dict[str, Any]:
        """Tag all posts that haven't been analyzed yet."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT pc.id FROM posted_content pc
                    LEFT JOIN content_attributes ca ON ca.post_id = pc.id
                    WHERE ca.id IS NULL AND pc.caption IS NOT NULL AND pc.caption != ''
                    ORDER BY COALESCE(pc.published_at, pc.posted_at) DESC
                    LIMIT :limit
                """), {"limit": limit}).fetchall()

            tagged = 0
            errors = 0
            for row in rows:
                result = await self.tag_post(str(row[0]))
                if "error" in result:
                    errors += 1
                else:
                    tagged += 1

            return {"tagged": tagged, "errors": errors, "total_untagged": len(rows)}

        except Exception as e:
            logger.error(f"[Intel] Batch tagging failed: {e}")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 2. PATTERN ANALYZER — Discover what works
    # ═══════════════════════════════════════════════════════════════════════

    async def analyze_patterns(self, lookback_days: int = 90) -> Dict[str, Any]:
        """
        Analyze performance patterns across all tagged content.
        Returns winning topics, hooks, tones, and platform-specific insights.
        """
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)
            cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

            with engine.connect() as conn:
                # Join attributes with performance data
                rows = conn.execute(text("""
                    SELECT
                        ca.topic_category, ca.hook_type, ca.emotional_tone,
                        ca.visual_style, ca.caption_structure, ca.platform,
                        COALESCE(pc.views, 0) as views,
                        COALESCE(pc.likes, 0) as likes,
                        COALESCE(pc.comments, 0) as comments,
                        COALESCE(pc.shares, 0) as shares,
                        COALESCE(pc.saves, 0) as saves,
                        COALESCE(pc.engagement_rate, 0) as engagement_rate
                    FROM content_attributes ca
                    JOIN posted_content pc ON pc.id = ca.post_id
                    WHERE ca.created_at > :cutoff
                """), {"cutoff": cutoff}).fetchall()

            if not rows:
                return await self._fallback_patterns()

            # Aggregate by dimension
            topic_stats = defaultdict(lambda: {"views": 0, "engagement": 0, "count": 0})
            hook_stats = defaultdict(lambda: {"views": 0, "engagement": 0, "count": 0})
            tone_stats = defaultdict(lambda: {"views": 0, "engagement": 0, "count": 0})
            platform_stats = defaultdict(lambda: defaultdict(lambda: {"views": 0, "engagement": 0, "count": 0}))

            for r in rows:
                topic, hook, tone, style, structure, platform = r[0], r[1], r[2], r[3], r[4], r[5]
                views, likes, comments, shares, saves, er = r[6], r[7], r[8], r[9], r[10], r[11]
                total_engagement = likes + comments + shares

                if topic:
                    topic_stats[topic]["views"] += views
                    topic_stats[topic]["engagement"] += total_engagement
                    topic_stats[topic]["count"] += 1

                if hook:
                    hook_stats[hook]["views"] += views
                    hook_stats[hook]["engagement"] += total_engagement
                    hook_stats[hook]["count"] += 1

                if tone:
                    tone_stats[tone]["views"] += views
                    tone_stats[tone]["engagement"] += total_engagement
                    tone_stats[tone]["count"] += 1

                if topic and platform:
                    platform_stats[platform][topic]["views"] += views
                    platform_stats[platform][topic]["engagement"] += total_engagement
                    platform_stats[platform][topic]["count"] += 1

            def rank(stats_dict):
                ranked = []
                for key, data in stats_dict.items():
                    avg_eng = data["engagement"] / data["count"] if data["count"] > 0 else 0
                    ranked.append({
                        "name": key,
                        "avg_engagement": round(avg_eng, 1),
                        "total_views": data["views"],
                        "post_count": data["count"],
                    })
                return sorted(ranked, key=lambda x: x["avg_engagement"], reverse=True)

            # Store insights
            insights = {
                "lookback_days": lookback_days,
                "total_posts_analyzed": len(rows),
                "top_topics": rank(topic_stats)[:10],
                "top_hooks": rank(hook_stats)[:10],
                "top_tones": rank(tone_stats)[:10],
                "underperforming": rank(topic_stats)[-3:] if len(topic_stats) > 3 else [],
                "platform_specific": {
                    plat: {
                        "best_topic": rank(topics)[0]["name"] if topics else None,
                        "topics": rank(topics)[:5],
                    }
                    for plat, topics in platform_stats.items()
                },
            }

            # Persist top insights to DB
            await self._store_insights(insights, lookback_days)

            logger.success(f"[Intel] ✓ Analyzed {len(rows)} posts | Top topic: {insights['top_topics'][0]['name'] if insights['top_topics'] else 'N/A'}")
            return insights

        except Exception as e:
            logger.error(f"[Intel] Pattern analysis failed: {e}")
            return {"error": str(e)}

    async def _fallback_patterns(self) -> Dict[str, Any]:
        """Return industry-default patterns when no data exists yet."""
        return {
            "lookback_days": 0,
            "total_posts_analyzed": 0,
            "note": "No tagged content yet. Tag posts first with tag_untagged_posts().",
            "top_topics": [
                {"name": "relationship_advice", "avg_engagement": 0, "total_views": 0, "post_count": 0},
                {"name": "self_improvement", "avg_engagement": 0, "total_views": 0, "post_count": 0},
                {"name": "motivation", "avg_engagement": 0, "total_views": 0, "post_count": 0},
            ],
            "top_hooks": [
                {"name": "question", "avg_engagement": 0, "total_views": 0, "post_count": 0},
                {"name": "bold_claim", "avg_engagement": 0, "total_views": 0, "post_count": 0},
            ],
            "top_tones": [
                {"name": "provocative", "avg_engagement": 0, "total_views": 0, "post_count": 0},
                {"name": "relatable", "avg_engagement": 0, "total_views": 0, "post_count": 0},
            ],
        }

    # ═══════════════════════════════════════════════════════════════════════
    # 3. BRIEF GENERATOR — Data-backed content briefs + Sora prompts
    # ═══════════════════════════════════════════════════════════════════════

    async def generate_briefs(self, count: int = 7) -> List[Dict[str, Any]]:
        """
        Generate data-backed content briefs using GPT + performance patterns.
        Each brief includes topic, hook, key points, Sora prompt, and caption draft.
        """
        # Get current patterns
        patterns = await self.analyze_patterns(lookback_days=90)

        # Build context for GPT
        top_topics = [t["name"] for t in patterns.get("top_topics", [])[:5]]
        top_hooks = [h["name"] for h in patterns.get("top_hooks", [])[:5]]
        top_tones = [t["name"] for t in patterns.get("top_tones", [])[:5]]

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a viral content strategist. Generate {count} content briefs optimized for social media.

PERFORMANCE DATA (what works best for this creator):
- Top topics: {', '.join(top_topics) if top_topics else 'relationship advice, self improvement, motivation'}
- Top hook types: {', '.join(top_hooks) if top_hooks else 'question, bold claim, story'}
- Top emotional tones: {', '.join(top_tones) if top_tones else 'provocative, relatable, inspirational'}

Return a JSON array of briefs. Each brief must have:
- topic: specific topic idea (not generic)
- hook: the exact first line/hook (compelling, scroll-stopping)
- key_points: array of 3-4 talking points
- target_emotion: one of [{', '.join(EMOTIONAL_TONES)}]
- suggested_style: one of [{', '.join(VISUAL_STYLES)}]
- sora_prompt: a detailed Sora video generation prompt (describe the scene, mood, visuals, ~50 words)
- caption_draft: ready-to-post caption with hashtags
- hashtags: array of 5-8 hashtags
- confidence: 0.0-1.0 how likely this will perform well
- reasoning: why this should work based on the data"""
                    },
                    {
                        "role": "user",
                        "content": f"Generate {count} fresh, diverse content briefs that lean into what works. Mix up topics but favor the top performers. Each should feel specific and actionable, not generic.",
                    },
                ],
                temperature=0.9,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            briefs = result.get("briefs", result.get("content_briefs", []))

            if not isinstance(briefs, list):
                briefs = [result]

            # Store briefs in DB
            stored_briefs = []
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                for brief in briefs[:count]:
                    brief_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO content_briefs (
                            id, topic, hook, key_points, target_emotion,
                            suggested_style, sora_prompt, caption_draft,
                            hashtags, confidence, reasoning, status, created_at
                        ) VALUES (
                            :id, :topic, :hook, :key_points, :emotion,
                            :style, :sora_prompt, :caption,
                            :hashtags, :confidence, :reasoning, 'draft', NOW()
                        )
                    """), {
                        "id": brief_id,
                        "topic": brief.get("topic", ""),
                        "hook": brief.get("hook", ""),
                        "key_points": json.dumps(brief.get("key_points", [])),
                        "emotion": brief.get("target_emotion", ""),
                        "style": brief.get("suggested_style", ""),
                        "sora_prompt": brief.get("sora_prompt", ""),
                        "caption": brief.get("caption_draft", ""),
                        "hashtags": brief.get("hashtags", []),
                        "confidence": brief.get("confidence", 0.5),
                        "reasoning": brief.get("reasoning", ""),
                    })

                    stored_briefs.append({
                        "id": brief_id,
                        **brief,
                    })
                conn.commit()

            logger.success(f"[Intel] ✓ Generated {len(stored_briefs)} content briefs")
            return stored_briefs

        except Exception as e:
            logger.error(f"[Intel] Brief generation failed: {e}")
            return [{"error": str(e)}]

    async def get_briefs(
        self, status: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List stored content briefs."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            query = "SELECT id, topic, hook, key_points, target_emotion, suggested_style, sora_prompt, caption_draft, hashtags, confidence, reasoning, status, created_at FROM content_briefs WHERE 1=1"
            params: Dict[str, Any] = {"limit": limit}
            if status:
                query += " AND status = :status"
                params["status"] = status
            query += " ORDER BY created_at DESC LIMIT :limit"

            with engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "topic": r[1],
                    "hook": r[2],
                    "key_points": json.loads(r[3]) if r[3] else [],
                    "target_emotion": r[4],
                    "suggested_style": r[5],
                    "sora_prompt": r[6],
                    "caption_draft": r[7],
                    "hashtags": r[8] or [],
                    "confidence": r[9],
                    "reasoning": r[10],
                    "status": r[11],
                    "created_at": r[12].isoformat() if r[12] else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"[Intel] Get briefs failed: {e}")
            return []

    async def update_brief_status(self, brief_id: str, status: str) -> Dict[str, Any]:
        """Update a brief's status (draft → approved → produced → published)."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE content_briefs SET status = :status WHERE id = :id
                """), {"id": brief_id, "status": status})
                conn.commit()

            return {"brief_id": brief_id, "status": status}
        except Exception as e:
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 4. WEEKLY REPORT — AI-summarized intelligence
    # ═══════════════════════════════════════════════════════════════════════

    async def weekly_report(self) -> Dict[str, Any]:
        """Generate an AI-summarized weekly intelligence report."""
        patterns = await self.analyze_patterns(lookback_days=7)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a social media analytics expert. Write a concise weekly performance report with actionable recommendations. Be specific and data-driven.",
                    },
                    {
                        "role": "user",
                        "content": f"""Weekly content intelligence data:
{json.dumps(patterns, indent=2, default=str)}

Write a 3-section report:
1. **This Week's Performance** — Key metrics and standouts
2. **What's Working** — Patterns driving engagement
3. **Action Items** — 3-5 specific things to do next week

Keep it under 500 words. Be direct and specific.""",
                    },
                ],
                temperature=0.7,
            )

            report_text = response.choices[0].message.content

            return {
                "report": report_text,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data": patterns,
            }

        except Exception as e:
            logger.error(f"[Intel] Weekly report failed: {e}")
            return {"error": str(e), "data": patterns}

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    async def _ai_extract_attributes(
        self, caption: str, platform: str
    ) -> Dict[str, Any]:
        """Use GPT to extract content attributes from caption text."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Analyze this social media caption and classify it.
Return JSON with:
- topic_category: one of [{', '.join(TOPIC_CATEGORIES)}]
- hook_type: one of [{', '.join(HOOK_TYPES)}]
- emotional_tone: one of [{', '.join(EMOTIONAL_TONES)}]
- visual_style: best guess from [{', '.join(VISUAL_STYLES)}]
- caption_structure: one of [short_punchy, long_story, cta_heavy, listicle, question_based]
- confidence: 0.0-1.0 how confident you are in the classification""",
                    },
                    {"role": "user", "content": f"Platform: {platform}\nCaption: {caption}"},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.warning(f"[Intel] AI attribute extraction failed: {e}")
            return {
                "topic_category": "entertainment",
                "hook_type": "bold_claim",
                "emotional_tone": "relatable",
                "visual_style": "talking_head",
                "caption_structure": "short_punchy",
                "confidence": 0.3,
            }

    async def _store_insights(self, insights: Dict, lookback_days: int) -> None:
        """Persist top insights to content_insights table."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            now = datetime.now(timezone.utc)
            period_start = (now - timedelta(days=lookback_days)).date()
            period_end = now.date()

            with engine.connect() as conn:
                for topic in insights.get("top_topics", [])[:5]:
                    conn.execute(text("""
                        INSERT INTO content_insights (
                            id, insight_type, attribute_key, attribute_value,
                            avg_engagement, sample_size, confidence,
                            period_start, period_end, created_at
                        ) VALUES (
                            :id, 'winning_pattern', 'topic', :value,
                            :avg_eng, :sample, 0.8, :start, :end, NOW()
                        )
                    """), {
                        "id": str(uuid.uuid4()),
                        "value": topic["name"],
                        "avg_eng": topic["avg_engagement"],
                        "sample": topic["post_count"],
                        "start": period_start,
                        "end": period_end,
                    })
                conn.commit()

        except Exception as e:
            logger.warning(f"[Intel] Store insights failed: {e}")

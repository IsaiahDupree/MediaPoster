"""
ACTP Iteration Engine
======================
Generates next-round variations from winning creatives.
Extracts winning elements and creates new angles for testing.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from .config import ACTPConfig, IterationConfig
from .models import Creative, TestCampaign, TestRound, WinnerSelection

logger = logging.getLogger(__name__)


class IterationEngine:
    """
    Generates new creative variations from winners for the next test round.

    Strategies:
    - hook_swap: Keep winning body/CTA, test new hooks
    - cta_swap: Keep winning hook/body, test new CTAs
    - ai_remix: AI-generated novel combinations from winning patterns
    """

    def __init__(self, db_client=None, config: Optional[ACTPConfig] = None):
        self.db = db_client
        self.config = config or ACTPConfig()
        self._openai_client = None
        self._init_openai()
        logger.info("[ACTP:Iteration] Engine initialized")

    def _init_openai(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return
        try:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=api_key)
        except ImportError:
            pass

    # ─── Winning Element Extraction ───────────────────────

    def extract_winning_elements(
        self, winners: List[WinnerSelection], creatives: List[Creative]
    ) -> Dict[str, Any]:
        """
        Analyze winners to extract the elements that contributed to success.
        Returns structured data about winning hooks, CTAs, angles, styles.
        """
        creative_map = {c.id: c for c in creatives}

        elements = {
            "hooks": [],
            "ctas": [],
            "angles": [],
            "scripts": [],
            "styles": [],
            "scores": [],
        }

        for winner in sorted(winners, key=lambda w: w.score, reverse=True):
            creative = creative_map.get(winner.creative_id)
            if not creative:
                continue

            if creative.hook:
                elements["hooks"].append({
                    "text": creative.hook,
                    "score": winner.score,
                    "creative_id": creative.id,
                })
            if creative.cta:
                elements["ctas"].append({
                    "text": creative.cta,
                    "score": winner.score,
                    "creative_id": creative.id,
                })
            if creative.angle:
                elements["angles"].append({
                    "text": creative.angle,
                    "score": winner.score,
                    "creative_id": creative.id,
                })
            if creative.script:
                elements["scripts"].append({
                    "text": creative.script,
                    "score": winner.score,
                    "creative_id": creative.id,
                })

            metadata = creative.generation_metadata or {}
            brief = metadata.get("brief", {})
            if brief.get("style"):
                elements["styles"].append(brief["style"])

            elements["scores"].append({
                "creative_id": creative.id,
                "organic_score": creative.organic_score,
                "ad_score": creative.ad_score,
                "rank": winner.rank,
            })

        logger.info(
            f"[ACTP:Iteration] Extracted elements from {len(winners)} winners: "
            f"{len(elements['hooks'])} hooks, {len(elements['ctas'])} CTAs, "
            f"{len(elements['angles'])} angles"
        )
        return elements

    # ─── Variation Generation ─────────────────────────────

    async def generate_next_round_briefs(
        self,
        winning_elements: Dict[str, Any],
        campaign: TestCampaign,
        strategies: Optional[List[str]] = None,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate briefs for the next round based on winning elements.
        Applies configured strategies to create variations.
        """
        strategies = strategies or self.config.iteration.strategies
        briefs = []

        for strategy in strategies:
            if strategy == "hook_swap":
                new_briefs = await self._hook_swap(winning_elements, campaign, count)
                briefs.extend(new_briefs)
            elif strategy == "cta_swap":
                new_briefs = await self._cta_swap(winning_elements, campaign, count)
                briefs.extend(new_briefs)
            elif strategy == "ai_remix":
                new_briefs = await self._ai_remix(winning_elements, campaign, count)
                briefs.extend(new_briefs)

        # Deduplicate and cap at count
        seen_hooks = set()
        unique_briefs = []
        for brief in briefs:
            hook = brief.get("hook", "").lower().strip()
            if hook not in seen_hooks:
                seen_hooks.add(hook)
                unique_briefs.append(brief)

        logger.info(
            f"[ACTP:Iteration] Generated {len(unique_briefs)} unique briefs "
            f"from {len(strategies)} strategies"
        )
        return unique_briefs[:count]

    async def _hook_swap(
        self,
        elements: Dict[str, Any],
        campaign: TestCampaign,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Generate variations by keeping the best body/CTA and swapping hooks."""
        if not self._openai_client or not elements.get("hooks"):
            return []

        best_cta = elements["ctas"][0]["text"] if elements.get("ctas") else ""
        best_script = elements["scripts"][0]["text"] if elements.get("scripts") else ""
        winning_hooks = [h["text"] for h in elements["hooks"][:3]]

        prompt = f"""You are a direct-response ad creative expert.

These hooks performed best in organic testing:
{json.dumps(winning_hooks, indent=2)}

Best performing CTA: {best_cta}
Best performing script: {best_script}
Offer: {campaign.offer_name or 'N/A'}

Generate {count} NEW hooks that follow the same patterns/style as the winners but test different angles.
Each hook must be different from the originals and under 15 words.

Return a JSON object with a "hooks" array of strings.
Return ONLY valid JSON."""

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            new_hooks = data.get("hooks", [])

            briefs = []
            for hook in new_hooks[:count]:
                briefs.append({
                    "hook": hook,
                    "cta": best_cta,
                    "angle": f"hook_swap: {hook[:50]}",
                    "script": best_script,
                    "strategy": "hook_swap",
                })
            return briefs
        except Exception as e:
            logger.error(f"[ACTP:Iteration] Hook swap failed: {e}")
            return []

    async def _cta_swap(
        self,
        elements: Dict[str, Any],
        campaign: TestCampaign,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Generate variations by keeping the best hook/body and swapping CTAs."""
        if not self._openai_client or not elements.get("ctas"):
            return []

        best_hook = elements["hooks"][0]["text"] if elements.get("hooks") else ""
        best_script = elements["scripts"][0]["text"] if elements.get("scripts") else ""
        winning_ctas = [c["text"] for c in elements["ctas"][:3]]

        prompt = f"""You are a direct-response ad creative expert.

These CTAs performed best:
{json.dumps(winning_ctas, indent=2)}

Best performing hook: {best_hook}
Offer: {campaign.offer_name or 'N/A'}
Offer URL: {campaign.offer_url or 'N/A'}

Generate {count} NEW CTAs that test different urgency levels, value propositions, and action words.
Each must be under 10 words and drive immediate action.

Return a JSON object with a "ctas" array of strings.
Return ONLY valid JSON."""

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            new_ctas = data.get("ctas", [])

            briefs = []
            for cta in new_ctas[:count]:
                briefs.append({
                    "hook": best_hook,
                    "cta": cta,
                    "angle": f"cta_swap: {cta[:50]}",
                    "script": best_script,
                    "strategy": "cta_swap",
                })
            return briefs
        except Exception as e:
            logger.error(f"[ACTP:Iteration] CTA swap failed: {e}")
            return []

    async def _ai_remix(
        self,
        elements: Dict[str, Any],
        campaign: TestCampaign,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Use AI to generate entirely new creative combinations from winning patterns."""
        if not self._openai_client:
            return []

        prompt = f"""You are an elite performance marketer and creative strategist.

Analyze these winning ad elements and generate {count} completely NEW creative briefs
that combine the winning patterns in novel ways.

WINNING HOOKS: {json.dumps([h['text'] for h in elements.get('hooks', [])[:5]])}
WINNING CTAS: {json.dumps([c['text'] for c in elements.get('ctas', [])[:5]])}
WINNING ANGLES: {json.dumps([a['text'] for a in elements.get('angles', [])[:5]])}
TOP SCORES: {json.dumps(elements.get('scores', [])[:3])}

Offer: {campaign.offer_name or 'N/A'}
Target Audience: {json.dumps(campaign.target_audience or {})}
Mode: {campaign.mode}

For each brief, provide:
- hook: Attention-grabbing opening (under 15 words)
- body: Main message building desire (under 30 words)
- cta: Action-driving close (under 10 words)
- script: Full voiceover script (under 50 words)
- visual_direction: What to show visually
- angle: The core angle being tested
- style: ugc, cinematic, explainer, testimonial, or before_after

Return a JSON object with a "briefs" array.
Return ONLY valid JSON."""

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            briefs = data.get("briefs", [])

            for brief in briefs:
                brief["strategy"] = "ai_remix"

            return briefs[:count]
        except Exception as e:
            logger.error(f"[ACTP:Iteration] AI remix failed: {e}")
            return []

    # ─── Lineage Tracking ─────────────────────────────────

    async def get_creative_lineage(self, creative_id: str) -> Dict[str, Any]:
        """Get the full genealogy tree for a creative."""
        if not self.db:
            return {"creative_id": creative_id, "children": [], "depth": 0}

        # Get the creative
        result = await self.db.table("actp_creatives").select("*").eq(
            "id", creative_id
        ).single().execute()

        if not result.data:
            return {"creative_id": creative_id, "children": [], "depth": 0}

        creative = result.data

        # Find all descendants
        children_result = await self.db.table("actp_creatives").select("*").eq(
            "parent_creative_id", creative_id
        ).execute()

        children = []
        for child in (children_result.data or []):
            child_lineage = await self.get_creative_lineage(child["id"])
            children.append(child_lineage)

        return {
            "creative_id": creative_id,
            "hook": creative.get("hook"),
            "angle": creative.get("angle"),
            "organic_score": creative.get("organic_score"),
            "ad_score": creative.get("ad_score"),
            "is_winner": creative.get("is_winner"),
            "generation_source": creative.get("generation_source"),
            "children": children,
            "depth": 0,
        }

    # ─── Diminishing Returns Detection ────────────────────

    async def detect_diminishing_returns(
        self, campaign_id: str
    ) -> Dict[str, Any]:
        """
        Detect if iteration is yielding diminishing improvements.
        Compares top scores across consecutive rounds.
        """
        if not self.db:
            return {"diminishing": False, "reason": "no_db"}

        rounds = await self.db.table("actp_rounds").select(
            "id, round_number"
        ).eq("campaign_id", campaign_id).order("round_number").execute()

        round_top_scores = []
        for r in (rounds.data or []):
            creatives = await self.db.table("actp_creatives").select(
                "organic_score"
            ).eq("round_id", r["id"]).order("organic_score", desc=True).limit(1).execute()

            top = (creatives.data or [{}])[0].get("organic_score", 0) if creatives.data else 0
            round_top_scores.append({
                "round_number": r["round_number"],
                "top_score": top or 0,
            })

        if len(round_top_scores) < 3:
            return {
                "diminishing": False,
                "reason": "insufficient_rounds",
                "scores": round_top_scores,
            }

        # Check if last 3 rounds show declining improvement
        recent = round_top_scores[-3:]
        deltas = [
            recent[i + 1]["top_score"] - recent[i]["top_score"]
            for i in range(len(recent) - 1)
        ]

        avg_delta = sum(deltas) / len(deltas)
        is_diminishing = avg_delta < 1.0  # Less than 1 point improvement

        return {
            "diminishing": is_diminishing,
            "avg_improvement": round(avg_delta, 2),
            "recent_deltas": deltas,
            "scores": round_top_scores,
            "recommendation": "pivot_angle" if is_diminishing else "continue",
        }

    # ─── Max Lineage Depth Enforcement ────────────────────

    MAX_LINEAGE_DEPTH = 5

    async def get_lineage_depth(self, creative_id: str) -> int:
        """Get the depth of a creative's lineage chain."""
        if not self.db:
            return 0

        depth = 0
        current_id = creative_id

        while current_id and depth < self.MAX_LINEAGE_DEPTH + 1:
            result = await self.db.table("actp_creatives").select(
                "parent_creative_id"
            ).eq("id", current_id).single().execute()

            parent_id = (result.data or {}).get("parent_creative_id")
            if not parent_id:
                break
            depth += 1
            current_id = parent_id

        return depth

    async def can_iterate(self, creative_id: str) -> Dict[str, Any]:
        """Check if a creative can be iterated (hasn't exceeded max lineage depth)."""
        depth = await self.get_lineage_depth(creative_id)
        allowed = depth < self.MAX_LINEAGE_DEPTH

        return {
            "creative_id": creative_id,
            "current_depth": depth,
            "max_depth": self.MAX_LINEAGE_DEPTH,
            "can_iterate": allowed,
            "reason": None if allowed else f"Max lineage depth ({self.MAX_LINEAGE_DEPTH}) reached",
        }

    # ─── Angle Exhaustion Detection ───────────────────────

    async def detect_angle_exhaustion(
        self, campaign_id: str
    ) -> Dict[str, Any]:
        """Detect if all angles have been exhausted and new ones are needed."""
        if not self.db:
            return {"exhausted": False}

        creatives = await self.db.table("actp_creatives").select(
            "angle, organic_score, is_winner"
        ).eq("campaign_id", campaign_id).execute()

        angle_stats: Dict[str, Dict] = {}
        for c in (creatives.data or []):
            angle = c.get("angle") or "unknown"
            if angle not in angle_stats:
                angle_stats[angle] = {"count": 0, "winners": 0, "avg_score": 0, "scores": []}
            angle_stats[angle]["count"] += 1
            if c.get("is_winner"):
                angle_stats[angle]["winners"] += 1
            if c.get("organic_score"):
                angle_stats[angle]["scores"].append(c["organic_score"])

        for angle, stats in angle_stats.items():
            scores = stats["scores"]
            stats["avg_score"] = round(sum(scores) / max(len(scores), 1), 2)
            del stats["scores"]

        # Exhausted if all angles tested 3+ times with declining scores
        exhausted_angles = [
            a for a, s in angle_stats.items()
            if s["count"] >= 3 and s["avg_score"] < 40
        ]

        total_angles = len(angle_stats)
        pct_exhausted = len(exhausted_angles) / max(total_angles, 1)

        return {
            "exhausted": pct_exhausted > 0.7,
            "total_angles": total_angles,
            "exhausted_angles": exhausted_angles,
            "pct_exhausted": round(pct_exhausted * 100, 1),
            "angle_stats": angle_stats,
            "recommendation": "new_angles_needed" if pct_exhausted > 0.7 else "continue",
        }

    # ─── Cross-Campaign Learning ──────────────────────────

    async def get_cross_campaign_insights(
        self, current_campaign_id: str
    ) -> Dict[str, Any]:
        """Pull winning patterns from other campaigns to inform iteration."""
        if not self.db:
            return {"insights": []}

        # Get winners from all campaigns except current
        winners = await self.db.table("actp_creatives").select(
            "hook, cta, angle, organic_score, campaign_id"
        ).eq("is_winner", True).neq(
            "campaign_id", current_campaign_id
        ).order("organic_score", desc=True).limit(50).execute()

        # Aggregate by angle
        angle_performance: Dict[str, list] = {}
        for w in (winners.data or []):
            angle = w.get("angle") or "unknown"
            if angle not in angle_performance:
                angle_performance[angle] = []
            angle_performance[angle].append(w.get("organic_score", 0))

        insights = []
        for angle, scores in sorted(
            angle_performance.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True
        )[:10]:
            insights.append({
                "angle": angle,
                "avg_score": round(sum(scores) / len(scores), 2),
                "win_count": len(scores),
            })

        return {
            "insights": insights,
            "source_campaigns": len(set(
                w["campaign_id"] for w in (winners.data or [])
            )),
        }

    # ─── Variation Diversity Scoring ──────────────────────

    def score_variation_diversity(
        self, variations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Score how diverse a set of variations is.
        Penalizes too-similar variations.
        """
        if len(variations) < 2:
            return {"diversity_score": 100, "unique_hooks": len(variations)}

        hooks = [v.get("hook", "") for v in variations]
        angles = [v.get("angle", "") for v in variations]
        styles = [v.get("style", "") for v in variations]

        unique_hooks = len(set(hooks))
        unique_angles = len(set(angles))
        unique_styles = len(set(styles))

        total = len(variations)
        hook_diversity = unique_hooks / total
        angle_diversity = unique_angles / total
        style_diversity = unique_styles / total

        overall = (hook_diversity * 0.5 + angle_diversity * 0.3 + style_diversity * 0.2) * 100

        return {
            "diversity_score": round(overall, 1),
            "unique_hooks": unique_hooks,
            "unique_angles": unique_angles,
            "unique_styles": unique_styles,
            "total_variations": total,
            "recommendation": "good" if overall >= 70 else "needs_more_variety",
        }

    # ─── Iteration Cooldown ───────────────────────────────

    # ─── Visual Style Iteration ───────────────────────────

    VISUAL_STYLES = ["ugc", "cinematic", "explainer", "testimonial", "before_after", "documentary", "animation", "talking_head"]

    def generate_style_variants(
        self, winner: Creative, exclude_styles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Generate briefs that iterate on visual style while keeping winning hook/CTA."""
        exclude = set(exclude_styles or [])
        current_meta = winner.generation_metadata or {}
        current_style = (current_meta.get("brief") or {}).get("style", "ugc")
        exclude.add(current_style)

        variants = []
        for style in self.VISUAL_STYLES:
            if style in exclude:
                continue
            brief = {
                "hook": winner.hook or "",
                "cta": winner.cta or "",
                "angle": winner.angle or "",
                "script": winner.script or "",
                "style": style,
                "visual_direction": f"Same message as winner, but in {style} format",
                "strategy": "style_swap",
                "parent_creative_id": winner.id,
            }
            variants.append(brief)

        return variants[:4]  # Max 4 style variants per winner

    # ─── Script Length Variants ───────────────────────────

    SCRIPT_LENGTH_TARGETS = {
        "ultra_short": {"words": 10, "duration_hint": "5s"},
        "short": {"words": 25, "duration_hint": "15s"},
        "medium": {"words": 50, "duration_hint": "30s"},
        "long": {"words": 100, "duration_hint": "60s"},
    }

    async def generate_script_length_variants(
        self, winner: Creative, lengths: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Generate script variants at different lengths from a winning creative."""
        if not self._openai_client:
            return []

        target_lengths = lengths or ["ultra_short", "short", "medium"]
        current_words = len((winner.script or "").split())
        variants = []

        for length_key in target_lengths:
            spec = self.SCRIPT_LENGTH_TARGETS[length_key]
            if abs(current_words - spec["words"]) < 5:
                continue  # Skip if already this length

            prompt = f"""Rewrite this ad script to be approximately {spec['words']} words ({spec['duration_hint']} video).
Keep the same hook concept and CTA. Adjust pacing accordingly.

Original script: {winner.script or winner.hook}
Hook: {winner.hook}
CTA: {winner.cta}

Return JSON: {{\"script\": \"...\", \"hook\": \"...\", \"cta\": \"...\"}}"""

            try:
                response = self._openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                data = json.loads(response.choices[0].message.content)
                data["strategy"] = "script_length_variant"
                data["length_key"] = length_key
                data["target_words"] = spec["words"]
                data["duration_hint"] = spec["duration_hint"]
                data["parent_creative_id"] = winner.id
                data["angle"] = winner.angle or ""
                variants.append(data)
            except Exception as e:
                logger.error(f"[ACTP:Iteration] Script length variant failed: {e}")

        return variants

    # ─── Pacing Variation ─────────────────────────────────

    PACING_STYLES = {
        "fast": {"cuts_per_second": 2.0, "hook_duration": 1.5, "description": "Quick cuts, high energy"},
        "medium": {"cuts_per_second": 1.0, "hook_duration": 2.5, "description": "Balanced pacing"},
        "slow": {"cuts_per_second": 0.5, "hook_duration": 4.0, "description": "Deliberate, calm pacing"},
        "pattern_interrupt": {"cuts_per_second": 3.0, "hook_duration": 1.0, "description": "Jarring fast open, then slow"},
    }

    def generate_pacing_variants(self, winner: Creative) -> List[Dict[str, Any]]:
        """Generate pacing variation configs for a winning creative."""
        current_meta = winner.generation_metadata or {}
        current_pacing = (current_meta.get("brief") or {}).get("pacing", "medium")

        variants = []
        for pacing_key, spec in self.PACING_STYLES.items():
            if pacing_key == current_pacing:
                continue
            variants.append({
                "hook": winner.hook or "",
                "cta": winner.cta or "",
                "angle": winner.angle or "",
                "script": winner.script or "",
                "style": (current_meta.get("brief") or {}).get("style", "ugc"),
                "pacing": pacing_key,
                "cuts_per_second": spec["cuts_per_second"],
                "hook_duration_seconds": spec["hook_duration"],
                "visual_direction": f"{spec['description']} version of winning creative",
                "strategy": "pacing_variant",
                "parent_creative_id": winner.id,
            })

        return variants[:3]

    # ─── Music / Audio Swap ───────────────────────────────

    AUDIO_SWAP_OPTIONS = {
        "no_music": {"music": None, "sfx": False, "description": "Voice only, no background"},
        "lo_fi": {"music": "lo_fi_beats", "sfx": False, "description": "Chill lo-fi background"},
        "energetic": {"music": "upbeat_electronic", "sfx": True, "description": "High energy with SFX"},
        "cinematic": {"music": "cinematic_swell", "sfx": False, "description": "Dramatic orchestral"},
        "trending": {"music": "trending_tiktok_sound", "sfx": False, "description": "Current trending audio"},
    }

    def generate_audio_swap_variants(self, winner: Creative) -> List[Dict[str, Any]]:
        """Generate audio/music swap variants for a winning creative."""
        current_meta = winner.generation_metadata or {}
        current_audio = (current_meta.get("brief") or {}).get("music", "no_music")

        variants = []
        for audio_key, spec in self.AUDIO_SWAP_OPTIONS.items():
            if audio_key == current_audio:
                continue
            variants.append({
                "hook": winner.hook or "",
                "cta": winner.cta or "",
                "angle": winner.angle or "",
                "script": winner.script or "",
                "style": (current_meta.get("brief") or {}).get("style", "ugc"),
                "music": spec["music"],
                "sfx": spec["sfx"],
                "audio_description": spec["description"],
                "visual_direction": f"Same visuals as winner, swap audio to: {spec['description']}",
                "strategy": "audio_swap",
                "parent_creative_id": winner.id,
            })

        return variants[:3]

    COOLDOWN_HOURS = 24

    async def check_iteration_cooldown(
        self, campaign_id: str
    ) -> Dict[str, Any]:
        """Check if enough time has passed since the last iteration."""
        if not self.db:
            return {"can_iterate": True, "cooldown_remaining_hours": 0}

        from datetime import datetime, timezone

        rounds = await self.db.table("actp_rounds").select(
            "created_at"
        ).eq("campaign_id", campaign_id).order("created_at", desc=True).limit(1).execute()

        if not (rounds.data or []):
            return {"can_iterate": True, "cooldown_remaining_hours": 0}

        last_created = rounds.data[0].get("created_at")
        if not last_created:
            return {"can_iterate": True, "cooldown_remaining_hours": 0}

        from datetime import datetime as dt
        if isinstance(last_created, str):
            last_dt = dt.fromisoformat(last_created.replace("Z", "+00:00"))
        else:
            last_dt = last_created

        now = dt.now(timezone.utc)
        elapsed = (now - last_dt).total_seconds() / 3600
        remaining = max(0, self.COOLDOWN_HOURS - elapsed)

        return {
            "can_iterate": remaining <= 0,
            "cooldown_remaining_hours": round(remaining, 1),
            "last_round_created": str(last_created),
            "hours_elapsed": round(elapsed, 1),
        }

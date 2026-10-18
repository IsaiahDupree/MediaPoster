"""
Trend-Aware Sora Prompt Library
================================
Curated, trend-aligned Sora prompts for @isaiahdupree character.
Updated monthly based on real TikTok/Reels/Shorts trend research.

Each prompt set includes:
- Sora-optimized video prompts (single or multi-part)
- Suggested caption / hook text
- Trend source reference
- Best platform targets
- Suggested audio (for post-production overlay)
"""

import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# =============================================================================
# CHARACTER DEFINITION
# =============================================================================

ISAIAH_CHARACTER = {
    "sora_handle": "@isaiahdupree",
    "visual_description": (
        "Isaiah, a charismatic Black man in his late 20s with a warm smile, "
        "wearing a casual hoodie and gold chain, expressive and humorous"
    ),
    "brand_pillars": [
        "content creation & automation",
        "personal branding",
        "tech entrepreneurship",
        "authentic storytelling",
        "humor & relatability",
    ],
    "default_style": "cinematic 4K, portrait 9:16",
}


# =============================================================================
# TREND PROMPT DATACLASS
# =============================================================================

@dataclass
class TrendPrompt:
    """A single trend-aligned Sora prompt."""
    id: str
    title: str
    trend_name: str
    trend_source: str  # e.g. "TikTok Feb 2026 Week 2"
    category: str  # single, series_part_1, series_part_2, series_part_3
    sora_prompt: str
    caption: str
    hashtags: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=lambda: ["tiktok", "instagram", "youtube_shorts"])
    suggested_audio: Optional[str] = None
    duration_seconds: int = 15
    aspect_ratio: str = "9:16"
    series_id: Optional[str] = None  # Groups multi-part series together
    month: str = ""  # e.g. "2026-02"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "trend_name": self.trend_name,
            "trend_source": self.trend_source,
            "category": self.category,
            "sora_prompt": self.sora_prompt,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "platforms": self.platforms,
            "suggested_audio": self.suggested_audio,
            "duration_seconds": self.duration_seconds,
            "aspect_ratio": self.aspect_ratio,
            "series_id": self.series_id,
            "month": self.month,
        }


# =============================================================================
# FEBRUARY 2026 TREND PROMPTS
# =============================================================================

FEBRUARY_2026_PROMPTS: List[TrendPrompt] = [
    # ─────────────────────────────────────────────────────────────
    # 1. ASKING THE UNIVERSE FOR A SIGN (AI Sky Trend)
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-universe-sign",
        title="Universe Sign — Build the App",
        trend_name="Asking the Universe for a Sign",
        trend_source="TikTok Feb 2026 Week 2",
        category="single",
        sora_prompt=(
            "@isaiahdupree standing on a city rooftop at golden hour, wearing a casual "
            "hoodie and gold chain, looking up at the sky with a hopeful, searching "
            "expression. Cinematic 4K, warm amber light, camera slowly tilts up from "
            "his face toward the sky. The clouds above begin to form into the words "
            '"BUILD THE APP" in bold natural cloud formations. Dramatic lighting, '
            "soft lens flare, aspirational mood. Portrait 9:16."
        ),
        caption="Asked the universe for a sign about what to do next weekend… 🌤️",
        hashtags=["#universesign", "#techcreator", "#buildtheapp", "#manifestation", "#fyp"],
        suggested_audio="Heaven Must Be Missing an Angel — Tavares",
        duration_seconds=12,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 2. REALITY TV EDIT — Creator Life (3-Part Series)
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-reality-tv-1",
        title="Reality TV Creator — The Setup",
        trend_name="Reality TV Edit",
        trend_source="TikTok Feb 2026 Week 2",
        category="series_part_1",
        series_id="feb26-reality-tv",
        sora_prompt=(
            "@isaiahdupree sitting in a modern home office with multiple monitors, "
            "dramatic shadows, cinematic camera slowly pushing in on his face as he "
            "stares at code on screen. Expression shifts from focused to shocked. "
            "Moody lighting, over-the-top dramatic atmosphere like a reality TV "
            "confessional. Portrait 9:16, cinematic 4K."
        ),
        caption='The code was compiling. Nobody was prepared for what happened next… 🎬',
        hashtags=["#realitytvtrend", "#creatorlife", "#codingdrama", "#devlife", "#fyp"],
        suggested_audio="Dramatic reality TV sting / Keeping Up tension music",
        duration_seconds=8,
        month="2026-02",
    ),
    TrendPrompt(
        id="feb26-reality-tv-2",
        title="Reality TV Creator — The Cliffhanger",
        trend_name="Reality TV Edit",
        trend_source="TikTok Feb 2026 Week 2",
        category="series_part_2",
        series_id="feb26-reality-tv",
        sora_prompt=(
            "@isaiahdupree standing in a sleek kitchen, mid-conversation, suddenly "
            "freezes mid-sentence. Camera zooms in dramatically on his face. Freeze "
            "frame. Warm tones, reality TV aesthetic, text overlay space at bottom. "
            "Cinematic 4K, portrait 9:16."
        ),
        caption='"Coming up... does Isaiah ship the feature?" ⏸️',
        hashtags=["#realitytvtrend", "#cliffhanger", "#devlife", "#tobecontinued", "#fyp"],
        suggested_audio="Record scratch + dramatic pause SFX",
        duration_seconds=8,
        month="2026-02",
    ),
    TrendPrompt(
        id="feb26-reality-tv-3",
        title="Reality TV Creator — The Confessional",
        trend_name="Reality TV Edit",
        trend_source="TikTok Feb 2026 Week 2",
        category="series_part_3",
        series_id="feb26-reality-tv",
        sora_prompt=(
            "@isaiahdupree sitting in a chair against a plain background, speaking "
            "directly to camera with exaggerated serious energy, hands gesturing "
            "emphatically. Soft studio lighting, documentary interview style, "
            "confessional booth aesthetic. Portrait 9:16, cinematic 4K."
        ),
        caption='"I trusted the process… and the process betrayed me." 🎤',
        hashtags=["#realitytvtrend", "#confessional", "#creatorlife", "#fyp"],
        suggested_audio="Confessional background ambient",
        duration_seconds=8,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 3. EUPHORIA GLAM TRANSITION
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-euphoria-glam",
        title="Euphoria Glam — Late Night Glow Up",
        trend_name="Euphoria Glam Transition",
        trend_source="TikTok Feb 2026 Week 1",
        category="single",
        sora_prompt=(
            "@isaiahdupree in a dark room with neon purple and blue lighting, looking "
            "down. He slowly raises his head to reveal his face with dramatic lighting "
            "— editorial glow, subtle shimmer on cheekbones, intense eye contact. "
            "Euphoria TV show aesthetic, moody, beautiful chaos. Camera pulls back "
            "slowly. 4K cinematic, shallow depth of field, hazy atmospheric lighting. "
            "Portrait 9:16."
        ),
        caption="The glow up hit different at 2am 💜",
        hashtags=["#euphoria", "#glamtransition", "#leftbehind", "#aesthetic", "#fyp"],
        suggested_audio="Left Behind — Labrinth",
        duration_seconds=12,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 4. GROUP CONSENSUS (Slow-Mo Debate)
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-group-consensus",
        title="Group Consensus — Should You Learn to Code?",
        trend_name="Group Consensus",
        trend_source="TikTok Feb 2026 Week 1",
        category="single",
        sora_prompt=(
            "@isaiahdupree entering frame from the left in slow motion, dramatic "
            "lighting, wearing a casual hoodie and gold chain. He points at camera "
            "with intense conviction while speaking. Modern minimalist background. "
            "Cinematic slow motion, 0.5x speed, confident energy, stylish and bold. "
            "4K portrait 9:16."
        ),
        caption=(
            '"Should you learn to code in 2026?"\n'
            "Person 1: Absolutely, it's a career investment\n"
            "@isaiahdupree: Just let AI do it all, go to the beach 🏖️\n"
            "Person 3: Learn to code AND go to the beach... on a boat you built from code"
        ),
        hashtags=["#groupconsensus", "#learntocode", "#tech", "#debate", "#fyp"],
        suggested_audio="I Love Rock N Roll — Joan Jett",
        duration_seconds=12,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 5. AUTOMATION FLEX — Serialized Tech Content (3-Part)
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-automation-1",
        title="Automation Flex — The Discovery",
        trend_name="Serialized AI Content",
        trend_source="Sprout Social 2026 Trends — Serialized Content + AI Mainstream",
        category="series_part_1",
        series_id="feb26-automation-flex",
        sora_prompt=(
            "@isaiahdupree walking through a futuristic corridor filled with floating "
            "holographic screens and data visualizations, wearing a hoodie and gold "
            "chain. He pauses, touches one of the holograms, and it expands. Cool blue "
            "and white lighting, sci-fi tech aesthetic, cinematic camera tracking shot. "
            "Confident energy. Portrait 9:16, 4K."
        ),
        caption="When the automation hits and everything just... works ✅🔥 — Part 1/3",
        hashtags=["#automation", "#techcreator", "#ai", "#futuristic", "#fyp", "#part1"],
        duration_seconds=12,
        month="2026-02",
    ),
    TrendPrompt(
        id="feb26-automation-2",
        title="Automation Flex — The Build",
        trend_name="Serialized AI Content",
        trend_source="Sprout Social 2026 Trends — Serialized Content + AI Mainstream",
        category="series_part_2",
        series_id="feb26-automation-flex",
        sora_prompt=(
            "@isaiahdupree sitting at a sleek glass desk, holographic interfaces "
            "floating around him, hands moving through the air manipulating code and "
            "schedules. Intense focus, dramatic lighting shifts from cool blue to warm "
            "gold. Fast camera movement, montage energy. Futuristic workspace. "
            "Portrait 9:16, 4K."
        ),
        caption="Building the system that builds the system 🧠⚡ — Part 2/3",
        hashtags=["#automation", "#techcreator", "#building", "#coding", "#fyp", "#part2"],
        duration_seconds=12,
        month="2026-02",
    ),
    TrendPrompt(
        id="feb26-automation-3",
        title="Automation Flex — The Payoff",
        trend_name="Serialized AI Content",
        trend_source="Sprout Social 2026 Trends — Serialized Content + AI Mainstream",
        category="series_part_3",
        series_id="feb26-automation-flex",
        sora_prompt=(
            "@isaiahdupree leaning back in his chair with a satisfied smile as all "
            "the holographic screens around him turn green with checkmarks. He folds "
            "his arms and nods. Golden hour lighting floods the room. Camera slowly "
            "pulls back to reveal the massive scale of the operation. Triumphant, "
            "aspirational mood, cinematic 4K. Portrait 9:16."
        ),
        caption="The future of content is automated 🚀 — Part 3/3",
        hashtags=["#automation", "#techcreator", "#success", "#payoff", "#fyp", "#part3"],
        duration_seconds=12,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 6. BLACK HISTORY MONTH — Builder's Legacy (3-Part)
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-bhm-legacy-1",
        title="Builder's Legacy — The Foundation",
        trend_name="Black History Month — Authentic Storytelling",
        trend_source="Cultural moment + Sprout 2026 Trend #6 Authenticity",
        category="series_part_1",
        series_id="feb26-bhm-legacy",
        sora_prompt=(
            "@isaiahdupree standing in front of a wall of vintage photographs and "
            "newspaper clippings about Black innovators and inventors. He reaches out "
            "and touches one photo. The photo comes to life with golden light emanating "
            "from it. Warm tones, reverent and powerful mood, cinematic documentary "
            "style. 4K, shallow depth of field. Portrait 9:16."
        ),
        caption="They built the foundation. We build the future. 🖤✊ — Part 1/3",
        hashtags=["#BlackHistoryMonth", "#BHM", "#BuildersLegacy", "#innovation", "#fyp"],
        duration_seconds=12,
        month="2026-02",
    ),
    TrendPrompt(
        id="feb26-bhm-legacy-2",
        title="Builder's Legacy — The Parallel",
        trend_name="Black History Month — Authentic Storytelling",
        trend_source="Cultural moment + Sprout 2026 Trend #6 Authenticity",
        category="series_part_2",
        series_id="feb26-bhm-legacy",
        sora_prompt=(
            "@isaiahdupree sitting at a workstation building something, intercut with "
            "split-screen showing historical Black inventors and creators working on "
            "their inventions. Same energy, different eras. Warm golden lighting, "
            "powerful montage, aspirational and emotional. Cinematic 4K. Portrait 9:16."
        ),
        caption="Same vision. Different century. Same fire. 🔥 — Part 2/3",
        hashtags=["#BlackHistoryMonth", "#BHM", "#legacy", "#builders", "#fyp"],
        duration_seconds=12,
        month="2026-02",
    ),
    TrendPrompt(
        id="feb26-bhm-legacy-3",
        title="Builder's Legacy — The Future",
        trend_name="Black History Month — Authentic Storytelling",
        trend_source="Cultural moment + Sprout 2026 Trend #6 Authenticity",
        category="series_part_3",
        series_id="feb26-bhm-legacy",
        sora_prompt=(
            "@isaiahdupree looking directly at camera, a confident knowing smile. "
            "Behind him, a timeline of innovation stretches into the future with "
            "glowing nodes. He turns and walks toward the future. Dramatic lighting, "
            "golden and blue tones, epic and inspiring mood. Camera follows him from "
            "behind as he walks forward. Cinematic 4K. Portrait 9:16."
        ),
        caption="History isn't just behind us. We're writing it right now. ✊🚀 — Part 3/3",
        hashtags=["#BlackHistoryMonth", "#BHM", "#future", "#innovation", "#fyp"],
        duration_seconds=12,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 7. KEY & PEELE AUDIO — "Shut Up Mom" (Relatable Humor)
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-key-peele",
        title="Shut Up Mom — IDE Edition",
        trend_name="Key & Peele Audio Trend",
        trend_source="TikTok Feb 2026 Week 2",
        category="single",
        sora_prompt=(
            "@isaiahdupree sitting at a desk with a laptop, rolling his eyes "
            "dramatically and waving his hand dismissively at the screen. Exaggerated "
            "bratty energy, comedic timing. Modern home office, warm natural lighting, "
            "slightly over-the-top performance. Portrait 9:16, 4K."
        ),
        caption=(
            'Me when my IDE tells me to "save before running" '
            'for the 400th time today 🙄\n'
            '"Silence from you"'
        ),
        hashtags=["#keyandpeele", "#silencefromyou", "#devlife", "#coding", "#relatable", "#fyp"],
        suggested_audio="Key & Peele — 'Shut up mom, silence from you'",
        duration_seconds=8,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 8. WHAT YEAR WERE YOU BORN? (Generational Humor)
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-birth-year-dino",
        title="What Year Were You Born? — Dinosaur Edit",
        trend_name="What Year Were You Born?",
        trend_source="NapoleonCat TikTok Trends Feb 2026",
        category="single",
        sora_prompt=(
            "@isaiahdupree wearing a prehistoric caveman outfit in a Jurassic-style "
            "jungle landscape, confused expression, dramatic lighting, cinematic "
            "comedy. Dinosaurs visible in the background. Absurd and humorous tone. "
            "4K, portrait 9:16."
        ),
        caption='When they said "2003" I aged 40 years instantly 🦕',
        hashtags=["#whatyearwereyouborn", "#dinosaur", "#gen z", "#aging", "#fyp"],
        suggested_audio="Dramatic aging sound effect / Original sound",
        duration_seconds=8,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 9. VALENTINE'S DAY — Self-Love / Brand-Love
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-valentine-code",
        title="Valentine's — My One True Love",
        trend_name="Valentine's Day Content",
        trend_source="February cultural moment",
        category="single",
        sora_prompt=(
            "@isaiahdupree sitting at a candlelit dinner table for two, dressed up "
            "nicely with gold chain visible. Across from him sits a glowing laptop "
            "with code on screen, a single rose in a vase between them. He gazes at "
            "the laptop lovingly, chin resting on his hand. Romantic restaurant "
            "ambiance, warm golden lighting, cinematic 4K, humorous yet aesthetic. "
            "Portrait 9:16."
        ),
        caption="My valentine never crashes (okay, sometimes) 💻❤️",
        hashtags=["#valentinesday", "#myvalentine", "#devlife", "#codeislove", "#fyp"],
        suggested_audio="Romantic instrumental / Let's Get It On parody",
        duration_seconds=12,
        month="2026-02",
    ),

    # ─────────────────────────────────────────────────────────────
    # 10. SUPER BOWL ENERGY — Halftime Show Parody
    # ─────────────────────────────────────────────────────────────
    TrendPrompt(
        id="feb26-superbowl-halftime",
        title="Super Bowl Halftime — Deploy to Production",
        trend_name="Super Bowl Content",
        trend_source="TikTok Feb 2026 Week 1 — Super Bowl Prep",
        category="single",
        sora_prompt=(
            "@isaiahdupree on a massive illuminated stage, dramatic spotlights, fog "
            "machines, and pyrotechnics behind him. He's standing confidently with arms "
            "spread wide as if performing for a stadium crowd. Epic scale, cinematic "
            "wide shot pulling back to reveal the stage. Concert / halftime show "
            "energy. 4K, portrait 9:16."
        ),
        caption='POV: You finally deployed to production on a Friday and nothing broke 🏟️🔥',
        hashtags=["#superbowl", "#halftime", "#deploytoproduction", "#devlife", "#fyp"],
        suggested_audio="Epic stadium crowd roar / Halftime instrumental",
        duration_seconds=12,
        month="2026-02",
    ),
]


# =============================================================================
# PROMPT LIBRARY SERVICE
# =============================================================================

class TrendPromptLibrary:
    """
    Manages trend-aware Sora prompts.
    Provides filtering, random selection, and AI-powered custom generation.
    """

    def __init__(self):
        self._prompts: Dict[str, List[TrendPrompt]] = {
            "2026-02": FEBRUARY_2026_PROMPTS,
        }
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=api_key) if api_key and OpenAI else None
        logger.info(f"📚 TrendPromptLibrary loaded: {sum(len(v) for v in self._prompts.values())} prompts")

    def get_current_month(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def get_prompts(
        self,
        month: Optional[str] = None,
        category: Optional[str] = None,
        series_id: Optional[str] = None,
        trend_name: Optional[str] = None,
    ) -> List[TrendPrompt]:
        """Get prompts with optional filters."""
        month = month or self.get_current_month()
        prompts = self._prompts.get(month, [])

        if category:
            prompts = [p for p in prompts if p.category == category]
        if series_id:
            prompts = [p for p in prompts if p.series_id == series_id]
        if trend_name:
            prompts = [p for p in prompts if trend_name.lower() in p.trend_name.lower()]

        return prompts

    def get_singles(self, month: Optional[str] = None) -> List[TrendPrompt]:
        """Get only standalone (non-series) prompts."""
        return self.get_prompts(month=month, category="single")

    def get_series(self, month: Optional[str] = None) -> Dict[str, List[TrendPrompt]]:
        """Get all series grouped by series_id."""
        month = month or self.get_current_month()
        prompts = self._prompts.get(month, [])
        series: Dict[str, List[TrendPrompt]] = {}
        for p in prompts:
            if p.series_id:
                series.setdefault(p.series_id, []).append(p)
        # Sort each series by category name (part_1, part_2, part_3)
        for sid in series:
            series[sid].sort(key=lambda x: x.category)
        return series

    def get_random_prompt(self, month: Optional[str] = None) -> Optional[TrendPrompt]:
        """Get a random single prompt."""
        singles = self.get_singles(month)
        return random.choice(singles) if singles else None

    def get_random_series(self, month: Optional[str] = None) -> Optional[List[TrendPrompt]]:
        """Get a random complete series."""
        series = self.get_series(month)
        if not series:
            return None
        series_id = random.choice(list(series.keys()))
        return series[series_id]

    def get_prompt_by_id(self, prompt_id: str) -> Optional[TrendPrompt]:
        """Look up a specific prompt by ID."""
        for month_prompts in self._prompts.values():
            for p in month_prompts:
                if p.id == prompt_id:
                    return p
        return None

    def list_trends(self, month: Optional[str] = None) -> List[Dict[str, Any]]:
        """List unique trends available for a given month."""
        month = month or self.get_current_month()
        prompts = self._prompts.get(month, [])
        seen = {}
        for p in prompts:
            if p.trend_name not in seen:
                seen[p.trend_name] = {
                    "trend_name": p.trend_name,
                    "trend_source": p.trend_source,
                    "prompt_count": 0,
                    "has_series": False,
                    "prompt_ids": [],
                }
            seen[p.trend_name]["prompt_count"] += 1
            seen[p.trend_name]["prompt_ids"].append(p.id)
            if p.series_id:
                seen[p.trend_name]["has_series"] = True
        return list(seen.values())

    async def generate_custom_trend_prompt(
        self,
        trend_description: str,
        character: str = "@isaiahdupree",
        style: str = "cinematic 4K",
    ) -> str:
        """Use OpenAI to generate a custom Sora prompt based on a trend description."""
        if not self.openai_client:
            return (
                f"{character} in a trendy scene inspired by: {trend_description}. "
                f"{ISAIAH_CHARACTER['visual_description']}, {style}, portrait 9:16."
            )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You write Sora AI video generation prompts. The main character is "
                            f"{character}: {ISAIAH_CHARACTER['visual_description']}. "
                            f"Brand pillars: {', '.join(ISAIAH_CHARACTER['brand_pillars'])}. "
                            f"Output ONLY the Sora prompt — no explanation, no quotes. "
                            f"Include specific camera movements, lighting, mood. "
                            f"Always end with 'Portrait 9:16, {style}.' "
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Create a Sora video prompt for {character} that taps into "
                            f"this trending concept: {trend_description}"
                        ),
                    },
                ],
                temperature=0.9,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Custom trend prompt generation failed: {e}")
            return (
                f"{character} in a trendy scene inspired by: {trend_description}. "
                f"{ISAIAH_CHARACTER['visual_description']}, {style}, portrait 9:16."
            )


# =============================================================================
# SINGLETON
# =============================================================================

_library_instance: Optional[TrendPromptLibrary] = None


def get_trend_prompt_library() -> TrendPromptLibrary:
    """Get singleton instance."""
    global _library_instance
    if _library_instance is None:
        _library_instance = TrendPromptLibrary()
    return _library_instance

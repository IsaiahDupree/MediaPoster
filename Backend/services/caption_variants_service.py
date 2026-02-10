"""
AI Caption Variants Service
============================
Rewrites captions in platform-native tone using GPT-4o-mini.

Instead of posting the same caption everywhere, this service generates
platform-optimized variants:
  - TikTok: casual, punchy, emoji-heavy, trending hashtags
  - Instagram: storytelling, hashtag-rich, CTA-driven
  - YouTube: SEO-optimized, keyword-rich description
  - Twitter/X: concise, witty, thread-friendly
  - LinkedIn: professional, thought-leadership tone
  - Threads: conversational, community-building
  - Pinterest: SEO keywords, aspirational
  - Facebook: relatable, shareable
  - Bluesky: authentic, decentralized-community vibe

Usage:
    service = CaptionVariantsService()
    variants = await service.generate_variants("My base caption", platforms=["tiktok", "instagram", "twitter"])
    # variants["tiktok"] = "no cap this changed everything 🤯 ..."
    # variants["instagram"] = "I never expected this to happen... (story) #viral #fyp ..."
    # variants["twitter"] = "This changed everything. Here's why 🧵"
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from loguru import logger


# ─── Platform Tone Definitions ──────────────────────────────────────────────

PLATFORM_TONES: Dict[str, Dict[str, Any]] = {
    "tiktok": {
        "tone": "casual, Gen-Z friendly, punchy, uses slang and emojis",
        "style": "Short hook → value → CTA. Use trending phrases. Heavy emoji use.",
        "max_length": 2200,
        "max_hashtags": 8,
        "hashtag_note": "Use trending + niche hashtags. Always include #fyp",
        "example": "no cap this changed my whole workflow 🤯\n\nhere's what happened...\n\n#fyp #viral #tech",
    },
    "instagram": {
        "tone": "aspirational, storytelling, community-focused, emoji-accented",
        "style": "Hook line → micro-story → CTA → hashtag block (separate paragraph). Longer captions OK.",
        "max_length": 2200,
        "max_hashtags": 25,
        "hashtag_note": "Mix of popular + niche hashtags in a separate block at the end",
        "example": "I never thought this would work...\n\nBut after 30 days of testing, the results speak for themselves 📈\n\nSave this for later ⬇️\n\n#reels #viral #productivity #techlife",
    },
    "youtube": {
        "tone": "SEO-optimized, informative, keyword-rich",
        "style": "Title-worthy hook → detailed description with keywords → timestamps if relevant → CTA to subscribe",
        "max_length": 5000,
        "max_hashtags": 10,
        "hashtag_note": "Use 3-5 SEO-focused hashtags. Hashtags appear above title on Shorts.",
        "example": "How I Automated My Entire Social Media Workflow\n\nIn this video I break down the exact system...\n\n🔔 Subscribe for more tech content\n\n#Shorts #Tech #Automation",
    },
    "twitter": {
        "tone": "concise, witty, provocative, thread-starter",
        "style": "One strong take or insight. Can hint at a thread. Use 1-2 emojis max. No hashtag spam.",
        "max_length": 280,
        "max_hashtags": 2,
        "hashtag_note": "Maximum 1-2 hashtags, woven naturally into the text",
        "example": "I automated my entire social media workflow.\n\nHere's what I learned after 10,000 posts 🧵",
    },
    "linkedin": {
        "tone": "professional, thought-leadership, insightful, data-driven",
        "style": "Bold opening statement → professional insight → lesson learned → CTA. Line breaks for readability.",
        "max_length": 3000,
        "max_hashtags": 5,
        "hashtag_note": "Professional/industry hashtags only",
        "example": "Most creators are doing social media wrong.\n\nAfter managing 22 accounts across 9 platforms, I discovered...\n\nHere are 3 lessons:\n\n1. ...\n2. ...\n3. ...\n\nWhat's your take? 👇\n\n#ContentStrategy #SocialMedia #CreatorEconomy",
    },
    "threads": {
        "tone": "conversational, community-building, authentic, casual",
        "style": "Quick thought or observation. Like texting a friend. Can ask questions to spark replies.",
        "max_length": 500,
        "max_hashtags": 5,
        "hashtag_note": "Optional, keep minimal",
        "example": "just automated all my social posting and honestly... why didn't I do this sooner?\n\nwhat tools are you all using? curious 👀",
    },
    "pinterest": {
        "tone": "aspirational, SEO-heavy, solution-oriented, evergreen",
        "style": "Keyword-rich title → descriptive text with search terms → CTA to save/pin",
        "max_length": 500,
        "max_hashtags": 15,
        "hashtag_note": "SEO keyword hashtags for discoverability",
        "example": "Social Media Automation Tips | How to Schedule Posts Across 9 Platforms\n\nSave this pin for your content strategy toolkit 📌\n\n#SocialMediaTips #ContentPlanning #Automation",
    },
    "facebook": {
        "tone": "relatable, shareable, community-engaging, warm",
        "style": "Relatable hook → story/insight → question or share prompt",
        "max_length": 5000,
        "max_hashtags": 5,
        "hashtag_note": "Minimal hashtags, focus on organic reach",
        "example": "Anyone else feel like they spend more time posting content than creating it? 😅\n\nI finally found a solution that saves me 10+ hours a week...\n\nWho else needs this? Tag a friend! 👇",
    },
    "bluesky": {
        "tone": "authentic, indie/alt-tech, community-aware, thoughtful",
        "style": "Genuine thought, not polished marketing speak. The decentralized crowd values authenticity.",
        "max_length": 300,
        "max_hashtags": 3,
        "hashtag_note": "Optional, organic only",
        "example": "built a system that auto-posts to all my social accounts and honestly the hardest part was dealing with each platform's quirks\n\nopen source soon maybe?",
    },
}


# ─── Service ─────────────────────────────────────────────────────────────────

class CaptionVariantsService:
    """
    Generates platform-optimized caption variants using GPT-4o-mini.
    Rewrites a base caption into the native tone and format of each platform.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("CAPTION_VARIANT_MODEL", "gpt-4o-mini")
        self._cache: Dict[str, Dict[str, str]] = {}  # hash -> {platform: caption}

    async def generate_variants(
        self,
        base_caption: str,
        platforms: Optional[List[str]] = None,
        context: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Generate platform-specific caption variants from a base caption.

        Args:
            base_caption: The original caption text
            platforms: List of target platforms (default: all 9)
            context: Optional additional context about the content
            hashtags: Optional base hashtags to include

        Returns:
            Dict mapping platform name → optimized caption
        """
        if not platforms:
            platforms = list(PLATFORM_TONES.keys())

        # Check cache
        cache_key = self._cache_key(base_caption, platforms)
        if cache_key in self._cache:
            logger.debug(f"[CaptionVariants] Cache hit for {len(platforms)} platforms")
            return self._cache[cache_key]

        # Generate all variants in a single GPT call for efficiency
        variants = await self._generate_batch(base_caption, platforms, context, hashtags)
        self._cache[cache_key] = variants
        return variants

    async def generate_single(
        self,
        base_caption: str,
        platform: str,
        context: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
    ) -> str:
        """Generate a caption variant for a single platform."""
        variants = await self.generate_variants(
            base_caption, platforms=[platform], context=context, hashtags=hashtags
        )
        return variants.get(platform, base_caption)

    async def _generate_batch(
        self,
        base_caption: str,
        platforms: List[str],
        context: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Call GPT to generate all platform variants in one request."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            # Build platform instructions
            platform_instructions = []
            for p in platforms:
                tone_info = PLATFORM_TONES.get(p)
                if not tone_info:
                    continue
                platform_instructions.append(
                    f"**{p}** (max {tone_info['max_length']} chars, {tone_info['max_hashtags']} hashtags):\n"
                    f"  Tone: {tone_info['tone']}\n"
                    f"  Style: {tone_info['style']}\n"
                    f"  Hashtags: {tone_info['hashtag_note']}\n"
                    f"  Example: {tone_info['example']}"
                )

            platform_block = "\n\n".join(platform_instructions)
            hashtag_note = f"\nBase hashtags to adapt: {', '.join(hashtags)}" if hashtags else ""
            context_note = f"\nContent context: {context}" if context else ""

            system_prompt = (
                "You are an expert social media copywriter who adapts content for different platforms. "
                "You understand the native culture, tone, and algorithm preferences of each platform. "
                "You NEVER sound generic — each variant should feel like it was written by a native of that platform. "
                "Return valid JSON with platform names as keys and caption strings as values. Nothing else."
            )

            user_prompt = (
                f"Rewrite this caption for each platform in its NATIVE tone and format:\n\n"
                f"BASE CAPTION:\n{base_caption}\n"
                f"{context_note}{hashtag_note}\n\n"
                f"PLATFORM GUIDELINES:\n{platform_block}\n\n"
                f"Return JSON with keys: {json.dumps(platforms)}\n"
                f"Each value should be the full, ready-to-post caption for that platform. "
                f"Respect each platform's character limit. Include appropriate hashtags."
            )

            logger.info(f"[CaptionVariants] Generating variants for {len(platforms)} platforms...")

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.85,
                response_format={"type": "json_object"},
                max_tokens=4000,
            )

            result = json.loads(response.choices[0].message.content)

            # Validate and enforce limits
            variants = {}
            for p in platforms:
                caption = result.get(p, base_caption)
                tone_info = PLATFORM_TONES.get(p, {})
                max_len = tone_info.get("max_length", 2200)

                if len(caption) > max_len:
                    caption = caption[:max_len - 3] + "..."

                variants[p] = caption

            logger.success(
                f"[CaptionVariants] ✓ Generated {len(variants)} variants "
                f"(tokens: {response.usage.total_tokens if response.usage else '?'})"
            )
            return variants

        except Exception as e:
            logger.error(f"[CaptionVariants] GPT generation failed: {e}")
            # Fallback: return base caption for all platforms
            return {p: base_caption for p in platforms}

    def _cache_key(self, caption: str, platforms: List[str]) -> str:
        """Generate a cache key from caption + platforms."""
        raw = f"{caption}|{'|'.join(sorted(platforms))}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def get_supported_platforms() -> List[str]:
        """Return list of supported platforms."""
        return list(PLATFORM_TONES.keys())

    @staticmethod
    def get_platform_info(platform: str) -> Optional[Dict[str, Any]]:
        """Get tone/style info for a specific platform."""
        return PLATFORM_TONES.get(platform)

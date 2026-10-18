"""
Platform Character Limits Configuration

This module defines character limits for each social media platform.
All limits include a 20% buffer for safety (target = 80% of max).

Sources:
- https://sociality.io/blog/social-media-character-limits/
- https://support.buffer.com/article/588-character-limits-for-each-social-network
- Platform documentation (2024-2025)
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PlatformLimits:
    """Character limits for a single platform"""
    platform: str
    title_max: int
    title_target: int  # 80% of max (20% buffer)
    description_max: int
    description_target: int  # 80% of max (20% buffer)
    hashtags_max: int
    hashtags_recommended: int
    bio_max: Optional[int] = None
    comment_max: Optional[int] = None
    
    @classmethod
    def from_max(cls, platform: str, title_max: int, description_max: int, 
                 hashtags_max: int = 30, hashtags_recommended: int = 5,
                 bio_max: int = None, comment_max: int = None):
        """Create limits with automatic 20% buffer calculation"""
        return cls(
            platform=platform,
            title_max=title_max,
            title_target=int(title_max * 0.8),
            description_max=description_max,
            description_target=int(description_max * 0.8),
            hashtags_max=hashtags_max,
            hashtags_recommended=hashtags_recommended,
            bio_max=bio_max,
            comment_max=comment_max,
        )


# Platform-specific limits (with 20% buffer built into targets)
PLATFORM_LIMITS: Dict[str, PlatformLimits] = {
    # Instagram
    "instagram": PlatformLimits.from_max(
        platform="instagram",
        title_max=100,  # No separate title, but for Reels
        description_max=2200,  # Caption limit
        hashtags_max=30,
        hashtags_recommended=5,  # 3-5 recommended
        bio_max=150,
        comment_max=2200,
    ),
    
    # TikTok
    "tiktok": PlatformLimits.from_max(
        platform="tiktok",
        title_max=100,  # Video title
        description_max=4000,  # Caption limit (was 2200, now 4000)
        hashtags_max=100,  # In caption
        hashtags_recommended=5,
        bio_max=80,
        comment_max=150,
    ),
    
    # YouTube
    "youtube": PlatformLimits.from_max(
        platform="youtube",
        title_max=100,  # 100 chars, but 70 visible in search
        description_max=5000,  # Full description
        hashtags_max=15,
        hashtags_recommended=3,
        bio_max=1000,  # Channel description
        comment_max=10000,
    ),
    
    # YouTube Shorts
    "youtube_shorts": PlatformLimits.from_max(
        platform="youtube_shorts",
        title_max=100,
        description_max=157,  # Shorter for Shorts
        hashtags_max=15,
        hashtags_recommended=3,
    ),
    
    # Twitter/X
    "twitter": PlatformLimits.from_max(
        platform="twitter",
        title_max=280,  # Tweet is the title
        description_max=280,  # Same as title for regular tweets
        hashtags_max=10,
        hashtags_recommended=2,  # 1-2 recommended
        bio_max=160,
        comment_max=280,
    ),
    
    # Threads
    "threads": PlatformLimits.from_max(
        platform="threads",
        title_max=500,  # Text post limit
        description_max=500,
        hashtags_max=10,
        hashtags_recommended=3,
        bio_max=150,
        comment_max=500,
    ),
    
    # Facebook
    "facebook": PlatformLimits.from_max(
        platform="facebook",
        title_max=80,  # Optimal engagement at 80 chars
        description_max=63206,  # Max limit, but 80 chars optimal
        hashtags_max=30,
        hashtags_recommended=3,
        bio_max=101,
        comment_max=8000,
    ),
    
    # LinkedIn
    "linkedin": PlatformLimits.from_max(
        platform="linkedin",
        title_max=100,  # Post headline
        description_max=3000,  # Post text limit
        hashtags_max=30,
        hashtags_recommended=5,
        bio_max=2600,  # Summary section
        comment_max=1250,
    ),
    
    # Pinterest
    "pinterest": PlatformLimits.from_max(
        platform="pinterest",
        title_max=100,  # Pin title (40 visible in feed)
        description_max=500,  # Pin description (200 recommended)
        hashtags_max=20,
        hashtags_recommended=5,
        bio_max=160,
        comment_max=500,
    ),
    
    # Bluesky
    "bluesky": PlatformLimits.from_max(
        platform="bluesky",
        title_max=300,  # Post limit
        description_max=300,
        hashtags_max=10,
        hashtags_recommended=3,
        bio_max=256,
        comment_max=300,
    ),
}

# Aliases for common variations
PLATFORM_LIMITS["x"] = PLATFORM_LIMITS["twitter"]
PLATFORM_LIMITS["ig"] = PLATFORM_LIMITS["instagram"]
PLATFORM_LIMITS["fb"] = PLATFORM_LIMITS["facebook"]
PLATFORM_LIMITS["yt"] = PLATFORM_LIMITS["youtube"]
PLATFORM_LIMITS["yt_shorts"] = PLATFORM_LIMITS["youtube_shorts"]
PLATFORM_LIMITS["tt"] = PLATFORM_LIMITS["tiktok"]
PLATFORM_LIMITS["li"] = PLATFORM_LIMITS["linkedin"]
PLATFORM_LIMITS["pin"] = PLATFORM_LIMITS["pinterest"]
PLATFORM_LIMITS["bsky"] = PLATFORM_LIMITS["bluesky"]


def get_platform_limits(platform: str) -> PlatformLimits:
    """Get limits for a platform, with fallback to generic limits"""
    platform_lower = platform.lower().strip()
    
    if platform_lower in PLATFORM_LIMITS:
        return PLATFORM_LIMITS[platform_lower]
    
    # Fallback to conservative generic limits
    return PlatformLimits.from_max(
        platform=platform_lower,
        title_max=100,
        description_max=500,
        hashtags_max=10,
        hashtags_recommended=5,
    )


def get_all_platforms() -> Dict[str, PlatformLimits]:
    """Get all platform limits (excluding aliases)"""
    return {
        k: v for k, v in PLATFORM_LIMITS.items()
        if k not in ["x", "ig", "fb", "yt", "yt_shorts", "tt", "li", "pin", "bsky"]
    }


# Default prompt generation settings
DEFAULT_PROMPT_SETTINGS = {
    "voice": "conversational",  # conversational, professional, casual, humorous, inspirational
    "tone": "engaging",  # engaging, informative, persuasive, friendly, authoritative
    "style": "concise",  # concise, detailed, storytelling, listicle, question-based
    "emoji_usage": "moderate",  # none, minimal, moderate, heavy
    "hashtag_style": "relevant",  # relevant, trending, branded, mixed
    "cta_style": "soft",  # none, soft, direct, urgency
    "language": "en",
    "custom_instructions": "",
}


# Prompt templates for different styles
PROMPT_TEMPLATES = {
    "conversational": "Write in a friendly, conversational tone as if talking to a friend.",
    "professional": "Write in a professional, polished tone suitable for business audiences.",
    "casual": "Write in a relaxed, casual tone with everyday language.",
    "humorous": "Write with humor and wit, keeping it light and entertaining.",
    "inspirational": "Write in an uplifting, motivational tone that inspires action.",
}

TONE_MODIFIERS = {
    "engaging": "Make it attention-grabbing and encourage interaction.",
    "informative": "Focus on providing value and useful information.",
    "persuasive": "Convince the reader to take action or consider a viewpoint.",
    "friendly": "Be warm, approachable, and relatable.",
    "authoritative": "Establish expertise and credibility on the topic.",
}

STYLE_MODIFIERS = {
    "concise": "Keep it short and to the point. Every word should count.",
    "detailed": "Provide comprehensive information with context.",
    "storytelling": "Tell a compelling story that draws the reader in.",
    "listicle": "Use numbered points or bullet-style format.",
    "question-based": "Start with or include thought-provoking questions.",
}

CTA_TEMPLATES = {
    "none": "",
    "soft": "Gently encourage engagement without being pushy.",
    "direct": "Include a clear call-to-action telling users exactly what to do.",
    "urgency": "Create urgency with time-sensitive language.",
}

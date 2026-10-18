"""
Platform Matching Engine (PIPE-004)
====================================
Intelligently match video content to optimal social media platforms
based on content analysis, format, duration, and platform requirements.

Features:
- Multi-criteria matching (format, duration, aspect ratio, content type)
- Platform-specific scoring and ranking
- Recommendations with confidence scores
- Format adaptation suggestions
- Audience alignment scoring
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class Platform(str, Enum):
    """Social media platforms"""
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE_LONG = "youtube_long"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    THREADS = "threads"


class AspectRatio(str, Enum):
    """Video aspect ratios"""
    VERTICAL = "9:16"  # 1080x1920
    SQUARE = "1:1"  # 1080x1080
    HORIZONTAL = "16:9"  # 1920x1080
    STORY = "9:16"  # Same as vertical but for stories


class ContentType(str, Enum):
    """Content types"""
    TALKING_HEAD = "talking_head"
    BROLL = "broll"
    TUTORIAL = "tutorial"
    VLOG = "vlog"
    PRODUCT_DEMO = "product_demo"
    COMEDY = "comedy"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    NEWS = "news"
    REVIEW = "review"


@dataclass
class PlatformRequirements:
    """Platform-specific requirements and preferences"""
    platform: Platform
    min_duration: int  # seconds
    max_duration: int  # seconds
    preferred_aspect_ratios: List[AspectRatio]
    preferred_content_types: List[ContentType]
    supports_text_overlay: bool = True
    supports_captions: bool = True
    supports_hashtags: bool = True
    max_hashtags: int = 30
    requires_vertical: bool = False
    audience_skew: str = ""  # "young", "professional", "general"
    best_for_niches: List[str] = field(default_factory=list)


@dataclass
class PlatformMatch:
    """A platform match recommendation"""
    platform: Platform
    confidence_score: float  # 0-1 overall confidence
    format_score: float  # 0-1 format compatibility
    duration_score: float  # 0-1 duration fit
    content_score: float  # 0-1 content type fit
    audience_score: float  # 0-1 audience alignment
    recommendations: List[str] = field(default_factory=list)
    required_adaptations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "platform": self.platform.value,
            "confidence_score": round(self.confidence_score, 3),
            "format_score": round(self.format_score, 3),
            "duration_score": round(self.duration_score, 3),
            "content_score": round(self.content_score, 3),
            "audience_score": round(self.audience_score, 3),
            "recommendations": self.recommendations,
            "required_adaptations": self.required_adaptations,
            "metadata": self.metadata
        }


class PlatformMatcher:
    """
    Platform Matching Engine (PIPE-004)

    Analyzes video content and recommends optimal social media platforms
    based on format, duration, content type, and audience alignment.

    Usage:
        matcher = PlatformMatcher()

        # Match a single video
        matches = matcher.match_video(
            duration=45,
            aspect_ratio="9:16",
            content_type="tutorial",
            niche="fitness"
        )

        # Get top recommendation
        best_match = matches[0]
        print(f"Best platform: {best_match.platform.value}")
        print(f"Confidence: {best_match.confidence_score}")
    """

    def __init__(self):
        """Initialize Platform Matcher with platform requirements"""
        self.platform_requirements = self._load_platform_requirements()
        logger.info("📊 Platform Matcher initialized with requirements for {} platforms".format(
            len(self.platform_requirements)
        ))

    def _load_platform_requirements(self) -> Dict[Platform, PlatformRequirements]:
        """Load platform-specific requirements and preferences"""
        return {
            Platform.TIKTOK: PlatformRequirements(
                platform=Platform.TIKTOK,
                min_duration=5,
                max_duration=180,  # 3 minutes (extended)
                preferred_aspect_ratios=[AspectRatio.VERTICAL],
                preferred_content_types=[
                    ContentType.COMEDY,
                    ContentType.EDUCATIONAL,
                    ContentType.ENTERTAINMENT,
                    ContentType.TUTORIAL
                ],
                requires_vertical=True,
                audience_skew="young",
                best_for_niches=["fitness", "food", "comedy", "tech", "education", "diy"]
            ),
            Platform.INSTAGRAM_REELS: PlatformRequirements(
                platform=Platform.INSTAGRAM_REELS,
                min_duration=3,
                max_duration=90,
                preferred_aspect_ratios=[AspectRatio.VERTICAL, AspectRatio.SQUARE],
                preferred_content_types=[
                    ContentType.TUTORIAL,
                    ContentType.PRODUCT_DEMO,
                    ContentType.VLOG,
                    ContentType.ENTERTAINMENT
                ],
                audience_skew="young",
                best_for_niches=["fashion", "beauty", "fitness", "food", "travel", "lifestyle"]
            ),
            Platform.INSTAGRAM_FEED: PlatformRequirements(
                platform=Platform.INSTAGRAM_FEED,
                min_duration=3,
                max_duration=60,
                preferred_aspect_ratios=[AspectRatio.SQUARE, AspectRatio.VERTICAL],
                preferred_content_types=[
                    ContentType.PRODUCT_DEMO,
                    ContentType.VLOG,
                    ContentType.TUTORIAL
                ],
                audience_skew="general",
                best_for_niches=["fashion", "beauty", "food", "art", "design", "lifestyle"]
            ),
            Platform.INSTAGRAM_STORY: PlatformRequirements(
                platform=Platform.INSTAGRAM_STORY,
                min_duration=1,
                max_duration=60,
                preferred_aspect_ratios=[AspectRatio.STORY],
                preferred_content_types=[
                    ContentType.VLOG,
                    ContentType.TALKING_HEAD,
                    ContentType.ENTERTAINMENT
                ],
                requires_vertical=True,
                audience_skew="young",
                best_for_niches=["lifestyle", "personal_brand", "behind_scenes"]
            ),
            Platform.YOUTUBE_SHORTS: PlatformRequirements(
                platform=Platform.YOUTUBE_SHORTS,
                min_duration=1,
                max_duration=60,
                preferred_aspect_ratios=[AspectRatio.VERTICAL],
                preferred_content_types=[
                    ContentType.TUTORIAL,
                    ContentType.EDUCATIONAL,
                    ContentType.COMEDY,
                    ContentType.REVIEW
                ],
                requires_vertical=True,
                audience_skew="general",
                best_for_niches=["tech", "education", "gaming", "music", "comedy"]
            ),
            Platform.YOUTUBE_LONG: PlatformRequirements(
                platform=Platform.YOUTUBE_LONG,
                min_duration=120,  # 2 minutes
                max_duration=36000,  # 10 hours
                preferred_aspect_ratios=[AspectRatio.HORIZONTAL],
                preferred_content_types=[
                    ContentType.TUTORIAL,
                    ContentType.EDUCATIONAL,
                    ContentType.REVIEW,
                    ContentType.VLOG
                ],
                audience_skew="general",
                best_for_niches=["tech", "education", "gaming", "business", "health"]
            ),
            Platform.TWITTER: PlatformRequirements(
                platform=Platform.TWITTER,
                min_duration=1,
                max_duration=140,
                preferred_aspect_ratios=[AspectRatio.HORIZONTAL, AspectRatio.SQUARE],
                preferred_content_types=[
                    ContentType.NEWS,
                    ContentType.COMEDY,
                    ContentType.ENTERTAINMENT
                ],
                max_hashtags=5,
                audience_skew="general",
                best_for_niches=["news", "tech", "sports", "comedy", "politics"]
            ),
            Platform.LINKEDIN: PlatformRequirements(
                platform=Platform.LINKEDIN,
                min_duration=15,
                max_duration=600,  # 10 minutes
                preferred_aspect_ratios=[AspectRatio.HORIZONTAL, AspectRatio.SQUARE],
                preferred_content_types=[
                    ContentType.EDUCATIONAL,
                    ContentType.TUTORIAL,
                    ContentType.TALKING_HEAD
                ],
                audience_skew="professional",
                best_for_niches=["business", "tech", "professional_development", "leadership"]
            ),
            Platform.FACEBOOK: PlatformRequirements(
                platform=Platform.FACEBOOK,
                min_duration=1,
                max_duration=7200,  # 2 hours
                preferred_aspect_ratios=[AspectRatio.HORIZONTAL, AspectRatio.SQUARE],
                preferred_content_types=[
                    ContentType.VLOG,
                    ContentType.TUTORIAL,
                    ContentType.ENTERTAINMENT
                ],
                audience_skew="general",
                best_for_niches=["family", "lifestyle", "news", "local_business"]
            ),
            Platform.THREADS: PlatformRequirements(
                platform=Platform.THREADS,
                min_duration=1,
                max_duration=90,
                preferred_aspect_ratios=[AspectRatio.VERTICAL, AspectRatio.SQUARE],
                preferred_content_types=[
                    ContentType.TALKING_HEAD,
                    ContentType.COMEDY,
                    ContentType.ENTERTAINMENT
                ],
                audience_skew="young",
                best_for_niches=["tech", "news", "lifestyle", "comedy"]
            )
        }

    def match_video(
        self,
        duration: int,
        aspect_ratio: str,
        content_type: str,
        niche: Optional[str] = None,
        target_audience: Optional[str] = None,
        has_text_overlay: bool = False,
        quality_score: float = 7.0,
        top_n: int = 5
    ) -> List[PlatformMatch]:
        """
        Match video to optimal platforms

        Args:
            duration: Video duration in seconds
            aspect_ratio: Aspect ratio (e.g., "9:16", "16:9", "1:1")
            content_type: Content type (e.g., "tutorial", "vlog")
            niche: Content niche (e.g., "fitness", "tech")
            target_audience: Target audience (e.g., "young", "professional")
            has_text_overlay: Whether video has text overlays
            quality_score: Video quality score (1-10)
            top_n: Number of top matches to return

        Returns:
            List of PlatformMatch objects, sorted by confidence score
        """
        matches = []

        for platform, requirements in self.platform_requirements.items():
            match = self._score_platform(
                platform=platform,
                requirements=requirements,
                duration=duration,
                aspect_ratio=aspect_ratio,
                content_type=content_type,
                niche=niche,
                target_audience=target_audience,
                has_text_overlay=has_text_overlay,
                quality_score=quality_score
            )
            matches.append(match)

        # Sort by confidence score (descending)
        matches.sort(key=lambda x: x.confidence_score, reverse=True)

        # Return top N
        return matches[:top_n]

    def _score_platform(
        self,
        platform: Platform,
        requirements: PlatformRequirements,
        duration: int,
        aspect_ratio: str,
        content_type: str,
        niche: Optional[str],
        target_audience: Optional[str],
        has_text_overlay: bool,
        quality_score: float
    ) -> PlatformMatch:
        """Score a single platform for compatibility"""

        # Calculate individual scores
        duration_score = self._score_duration(duration, requirements)
        format_score = self._score_format(aspect_ratio, requirements)
        content_score = self._score_content_type(content_type, requirements)
        audience_score = self._score_audience(target_audience, niche, requirements)

        # Calculate overall confidence score (weighted average)
        confidence_score = (
            0.30 * format_score +      # Format is critical
            0.25 * duration_score +    # Duration is important
            0.25 * content_score +     # Content fit matters
            0.20 * audience_score      # Audience alignment
        )

        # Quality boost (high quality videos get a small bonus)
        if quality_score >= 8.0:
            confidence_score *= 1.05

        # Cap at 1.0
        confidence_score = min(1.0, confidence_score)

        # Generate recommendations and required adaptations
        recommendations = self._generate_recommendations(
            platform, requirements, duration, aspect_ratio, content_type, has_text_overlay
        )
        required_adaptations = self._generate_adaptations(
            requirements, aspect_ratio, duration
        )

        return PlatformMatch(
            platform=platform,
            confidence_score=confidence_score,
            format_score=format_score,
            duration_score=duration_score,
            content_score=content_score,
            audience_score=audience_score,
            recommendations=recommendations,
            required_adaptations=required_adaptations,
            metadata={
                "quality_score": quality_score,
                "has_text_overlay": has_text_overlay
            }
        )

    def _score_duration(self, duration: int, requirements: PlatformRequirements) -> float:
        """Score duration compatibility"""
        if requirements.min_duration <= duration <= requirements.max_duration:
            # Perfect fit
            return 1.0
        elif duration < requirements.min_duration:
            # Too short - penalty based on how much shorter
            ratio = duration / requirements.min_duration
            return max(0.0, ratio)
        else:
            # Too long - penalty based on how much longer
            ratio = requirements.max_duration / duration
            return max(0.0, ratio)

    def _score_format(self, aspect_ratio: str, requirements: PlatformRequirements) -> float:
        """Score format/aspect ratio compatibility"""
        # Normalize aspect ratio string
        aspect_ratio = aspect_ratio.strip()

        # Check if exact match
        for preferred in requirements.preferred_aspect_ratios:
            if aspect_ratio == preferred.value:
                return 1.0

        # Check if vertical when required
        if requirements.requires_vertical:
            if aspect_ratio in ["9:16", "9_16", "vertical"]:
                return 1.0
            else:
                return 0.3  # Severe penalty for wrong orientation

        # Partial match - close enough
        if aspect_ratio in ["9:16", "9_16", "vertical"] and AspectRatio.VERTICAL in requirements.preferred_aspect_ratios:
            return 0.9
        if aspect_ratio in ["1:1", "1_1", "square"] and AspectRatio.SQUARE in requirements.preferred_aspect_ratios:
            return 0.9
        if aspect_ratio in ["16:9", "16_9", "horizontal"] and AspectRatio.HORIZONTAL in requirements.preferred_aspect_ratios:
            return 0.9

        # No match
        return 0.4

    def _score_content_type(self, content_type: str, requirements: PlatformRequirements) -> float:
        """Score content type compatibility"""
        try:
            content_enum = ContentType(content_type.lower())
        except ValueError:
            # Unknown content type - use neutral score
            return 0.6

        if content_enum in requirements.preferred_content_types:
            return 1.0

        # Partial match for related types
        related_types = {
            ContentType.TUTORIAL: [ContentType.EDUCATIONAL],
            ContentType.EDUCATIONAL: [ContentType.TUTORIAL],
            ContentType.VLOG: [ContentType.ENTERTAINMENT, ContentType.TALKING_HEAD],
            ContentType.PRODUCT_DEMO: [ContentType.TUTORIAL, ContentType.REVIEW]
        }

        if content_enum in related_types:
            for related in related_types[content_enum]:
                if related in requirements.preferred_content_types:
                    return 0.8

        return 0.5

    def _score_audience(
        self,
        target_audience: Optional[str],
        niche: Optional[str],
        requirements: PlatformRequirements
    ) -> float:
        """Score audience alignment"""
        score = 0.7  # Base score

        # Audience skew alignment
        if target_audience:
            if target_audience.lower() == requirements.audience_skew:
                score += 0.2
            elif requirements.audience_skew == "general":
                score += 0.1  # General platforms work for any audience

        # Niche alignment
        if niche and requirements.best_for_niches:
            if niche.lower() in [n.lower() for n in requirements.best_for_niches]:
                score += 0.2

        return min(1.0, score)

    def _generate_recommendations(
        self,
        platform: Platform,
        requirements: PlatformRequirements,
        duration: int,
        aspect_ratio: str,
        content_type: str,
        has_text_overlay: bool
    ) -> List[str]:
        """Generate platform-specific recommendations"""
        recommendations = []

        # Duration recommendations
        optimal_duration = (requirements.min_duration + requirements.max_duration) / 2
        if duration < optimal_duration * 0.5:
            recommendations.append(f"Consider extending to {int(optimal_duration)}s for better engagement")
        elif duration > optimal_duration * 1.5:
            recommendations.append(f"Consider shortening to {int(optimal_duration)}s for this platform")

        # Text overlay recommendations
        if requirements.supports_text_overlay and not has_text_overlay:
            recommendations.append("Add text overlays/captions for better engagement")

        # Hashtag recommendations
        if requirements.supports_hashtags:
            recommendations.append(f"Use up to {requirements.max_hashtags} relevant hashtags")

        # Platform-specific tips
        if platform == Platform.TIKTOK:
            recommendations.append("Use trending sounds and effects")
            recommendations.append("Hook viewers in first 3 seconds")
        elif platform == Platform.YOUTUBE_LONG:
            recommendations.append("Create chapters for better navigation")
            recommendations.append("Design compelling thumbnail")
        elif platform == Platform.LINKEDIN:
            recommendations.append("Include professional insights")
            recommendations.append("Add captions for sound-off viewing")

        return recommendations

    def _generate_adaptations(
        self,
        requirements: PlatformRequirements,
        aspect_ratio: str,
        duration: int
    ) -> List[str]:
        """Generate required adaptations"""
        adaptations = []

        # Format adaptations
        preferred_ar = requirements.preferred_aspect_ratios[0].value if requirements.preferred_aspect_ratios else None
        if preferred_ar and aspect_ratio != preferred_ar:
            adaptations.append(f"Convert aspect ratio to {preferred_ar}")

        # Duration adaptations
        if duration > requirements.max_duration:
            adaptations.append(f"Trim video to {requirements.max_duration}s or less")
        elif duration < requirements.min_duration:
            adaptations.append(f"Extend video to at least {requirements.min_duration}s")

        return adaptations

    def batch_match(
        self,
        videos: List[Dict[str, Any]],
        top_n: int = 5
    ) -> Dict[str, List[PlatformMatch]]:
        """
        Batch match multiple videos

        Args:
            videos: List of video dictionaries with keys: duration, aspect_ratio, content_type, etc.
            top_n: Number of top matches per video

        Returns:
            Dictionary mapping video_id to list of PlatformMatch objects
        """
        results = {}

        for video in videos:
            video_id = video.get('id', video.get('video_id', 'unknown'))
            matches = self.match_video(
                duration=video.get('duration', 0),
                aspect_ratio=video.get('aspect_ratio', '16:9'),
                content_type=video.get('content_type', 'entertainment'),
                niche=video.get('niche'),
                target_audience=video.get('target_audience'),
                has_text_overlay=video.get('has_text_overlay', False),
                quality_score=video.get('quality_score', 7.0),
                top_n=top_n
            )
            results[video_id] = matches

        logger.success(f"✓ Batch matched {len(videos)} videos to platforms")

        return results

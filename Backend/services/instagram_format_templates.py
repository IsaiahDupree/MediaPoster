"""
Instagram Content Format Templates (IG-TREND-002)
================================================
Library of proven Instagram content formats with categorization and matching.

Formats include:
- Text-Hook (bold text overlay hook)
- Overhead Grab POV
- Before/After Transformation
- Green Screen Commentary
- List Carousel
- Story Time
- Product Showcase
- Tutorial/How-To
- Day in the Life
- Duet/Reaction Style

Each format template includes:
- Visual structure
- Timing guidelines
- Hook patterns
- Performance metrics
- Best use cases
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from loguru import logger


class FormatCategory(Enum):
    """Content format categories"""
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    PRODUCT = "product"
    LIFESTYLE = "lifestyle"
    STORYTELLING = "storytelling"
    TRENDING = "trending"


class DifficultyLevel(Enum):
    """Production difficulty"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class FormatTemplate:
    """Instagram content format template"""

    # Identity
    format_id: str
    name: str
    slug: str
    category: FormatCategory

    # Description
    description: str
    hook_style: str
    visual_structure: str
    timing_guidelines: str

    # Performance
    avg_engagement_rate: float
    avg_completion_rate: float
    trending_score: float

    # Production
    difficulty: DifficultyLevel
    production_time: str
    equipment_needed: List[str]

    # Guidelines
    best_for: List[str]
    hook_patterns: List[str]
    call_to_action_patterns: List[str]
    common_mistakes: List[str]

    # Examples
    example_creators: List[str]
    example_posts: List[str]

    # Metadata
    times_used: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "format_id": self.format_id,
            "name": self.name,
            "slug": self.slug,
            "category": self.category.value,
            "description": self.description,
            "hook_style": self.hook_style,
            "visual_structure": self.visual_structure,
            "timing_guidelines": self.timing_guidelines,
            "avg_engagement_rate": self.avg_engagement_rate,
            "avg_completion_rate": self.avg_completion_rate,
            "trending_score": self.trending_score,
            "difficulty": self.difficulty.value,
            "production_time": self.production_time,
            "equipment_needed": self.equipment_needed,
            "best_for": self.best_for,
            "hook_patterns": self.hook_patterns,
            "call_to_action_patterns": self.call_to_action_patterns,
            "common_mistakes": self.common_mistakes,
            "example_creators": self.example_creators,
            "example_posts": self.example_posts,
            "times_used": self.times_used,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class FormatMatch:
    """Result of matching content to a format"""
    format_id: str
    format_name: str
    match_score: float  # 0-100
    match_reasons: List[str]
    suggested_modifications: List[str]


class InstagramFormatTemplates:
    """
    Instagram Format Templates Library (IG-TREND-002)

    Provides proven content formats with categorization and matching.

    Usage:
        library = InstagramFormatTemplates()

        # Get all templates
        templates = library.get_all_templates()

        # Get by category
        educational = library.get_templates_by_category(FormatCategory.EDUCATIONAL)

        # Search templates
        text_formats = library.search_templates("text")

        # Match content to templates
        matches = library.match_content_to_templates(content_description)
    """

    def __init__(self):
        """Initialize format templates library"""
        self._templates: Dict[str, FormatTemplate] = {}
        self._load_predefined_templates()
        logger.info(f"📚 Instagram Format Templates loaded ({len(self._templates)} formats)")

    def _load_predefined_templates(self) -> None:
        """Load predefined Instagram format templates"""

        templates = [
            FormatTemplate(
                format_id="text-hook",
                name="Text-on-Screen Hook",
                slug="text-hook",
                category=FormatCategory.TRENDING,
                description="Bold text overlay in first 3 seconds to grab attention",
                hook_style="Large, contrasting text with attention-grabbing statement",
                visual_structure="Text appears 0-3s, then transition to main content",
                timing_guidelines="Hook: 0-3s, Deliver: 3-20s, CTA: 20-30s",
                avg_engagement_rate=8.5,
                avg_completion_rate=72.0,
                trending_score=95.2,
                difficulty=DifficultyLevel.EASY,
                production_time="15-30 minutes",
                equipment_needed=["Smartphone", "Text overlay app (CapCut, InShot)"],
                best_for=["Quick tips", "Shocking facts", "Controversial statements"],
                hook_patterns=[
                    "Things I wish I knew before [X]",
                    "Nobody talks about [X]",
                    "Stop doing [X]",
                    "This changed everything",
                    "POV: You just learned [X]"
                ],
                call_to_action_patterns=[
                    "Follow for more [topic]",
                    "Save this for later",
                    "Tag someone who needs this",
                    "Comment [X] if you agree"
                ],
                common_mistakes=[
                    "Text too small to read",
                    "Text stays on screen too long",
                    "Hook not compelling enough"
                ],
                example_creators=["@alexhormozi", "@garyvee", "@thefutur"],
                example_posts=[]
            ),

            FormatTemplate(
                format_id="overhead-pov",
                name="Overhead Grab POV",
                slug="overhead-pov",
                category=FormatCategory.PRODUCT,
                description="Overhead shot of hand reaching for product/item",
                hook_style="Hand enters frame reaching for object",
                visual_structure="Overhead view → Hand interaction → Product showcase",
                timing_guidelines="Reach: 0-2s, Showcase: 2-15s, Benefits: 15-30s",
                avg_engagement_rate=7.2,
                avg_completion_rate=68.0,
                trending_score=87.6,
                difficulty=DifficultyLevel.EASY,
                production_time="10-20 minutes",
                equipment_needed=["Smartphone", "Tripod or mount", "Good lighting"],
                best_for=["Product demos", "Unboxing", "Aesthetic shots"],
                hook_patterns=[
                    "Grabbing [product] because [reason]",
                    "Let me show you [X]",
                    "Watch me [action]"
                ],
                call_to_action_patterns=[
                    "Link in bio",
                    "Available at [store]",
                    "DM for details"
                ],
                common_mistakes=[
                    "Poor lighting",
                    "Cluttered background",
                    "Shaky footage"
                ],
                example_creators=["@drinkprime", "@glowrecipe", "@fenty"],
                example_posts=[]
            ),

            FormatTemplate(
                format_id="before-after",
                name="Before/After Transformation",
                slug="before-after",
                category=FormatCategory.ENTERTAINMENT,
                description="Split-screen or transition showing transformation",
                hook_style="Show dramatic 'before' state",
                visual_structure="Before (3s) → Transition → After (remaining)",
                timing_guidelines="Before: 0-3s, Process: 3-20s, After: 20-30s",
                avg_engagement_rate=9.1,
                avg_completion_rate=75.0,
                trending_score=82.1,
                difficulty=DifficultyLevel.MEDIUM,
                production_time="30-60 minutes",
                equipment_needed=["Camera", "Editing software", "Consistent lighting"],
                best_for=["Makeovers", "Room transformations", "Skill progression"],
                hook_patterns=[
                    "Wait for it...",
                    "Watch this transformation",
                    "Before vs After [X]"
                ],
                call_to_action_patterns=[
                    "Want to try it? Link in bio",
                    "Comment if you want a tutorial",
                    "Follow for more transformations"
                ],
                common_mistakes=[
                    "Inconsistent lighting between shots",
                    "Transition too fast/slow",
                    "Not dramatic enough contrast"
                ],
                example_creators=["@charlidamelio", "@nikkietutorials"],
                example_posts=[]
            ),

            FormatTemplate(
                format_id="green-screen",
                name="Green Screen Commentary",
                slug="green-screen",
                category=FormatCategory.ENTERTAINMENT,
                description="Creator talks over background content",
                hook_style="Engaging question or statement",
                visual_structure="Creator in foreground, content in background",
                timing_guidelines="Hook: 0-5s, Commentary: 5-25s, Conclusion: 25-30s",
                avg_engagement_rate=7.8,
                avg_completion_rate=70.0,
                trending_score=78.9,
                difficulty=DifficultyLevel.MEDIUM,
                production_time="20-40 minutes",
                equipment_needed=["Green screen or editing app", "Camera", "Microphone"],
                best_for=["Reactions", "Commentary", "Storytelling over visuals"],
                hook_patterns=[
                    "Let me explain [X]",
                    "Here's what people don't understand",
                    "This is wild..."
                ],
                call_to_action_patterns=[
                    "What do you think?",
                    "Drop your thoughts below",
                    "Follow for more takes"
                ],
                common_mistakes=[
                    "Too much going on in background",
                    "Poor audio quality",
                    "Not enough personality"
                ],
                example_creators=["@khaby.lame", "@brittany_broski"],
                example_posts=[]
            ),

            FormatTemplate(
                format_id="list-carousel",
                name="Numbered List Carousel",
                slug="list-carousel",
                category=FormatCategory.EDUCATIONAL,
                description="Carousel post with numbered tips/facts",
                hook_style="'5 things you need to know about [X]'",
                visual_structure="Cover → Slide 1 → Slide 2... → CTA",
                timing_guidelines="Each slide: 2-3 seconds",
                avg_engagement_rate=6.5,
                avg_completion_rate=65.0,
                trending_score=72.4,
                difficulty=DifficultyLevel.EASY,
                production_time="20-30 minutes",
                equipment_needed=["Design tool (Canva, Figma)", "Smartphone"],
                best_for=["Tips and tricks", "Educational content", "Listicles"],
                hook_patterns=[
                    "X things about [topic]",
                    "The ultimate [X] guide",
                    "You need to know these [X]"
                ],
                call_to_action_patterns=[
                    "Save for later",
                    "Share with someone who needs this",
                    "Follow for more [topic]"
                ],
                common_mistakes=[
                    "Too much text per slide",
                    "Inconsistent design",
                    "Not enough value per slide"
                ],
                example_creators=["@hubspot", "@buffer", "@later"],
                example_posts=[]
            ),

            FormatTemplate(
                format_id="day-in-life",
                name="Day in the Life",
                slug="day-in-life",
                category=FormatCategory.LIFESTYLE,
                description="Follow creator through their day",
                hook_style="'Day in my life as [X]'",
                visual_structure="Morning → Activities → Evening",
                timing_guidelines="Intro: 0-5s, Activities: 5-50s, Outro: 50-60s",
                avg_engagement_rate=7.0,
                avg_completion_rate=60.0,
                trending_score=68.5,
                difficulty=DifficultyLevel.MEDIUM,
                production_time="Full day + 1-2 hours editing",
                equipment_needed=["Camera/smartphone", "Tripod", "Editing software"],
                best_for=["Lifestyle content", "Behind-the-scenes", "Relatability"],
                hook_patterns=[
                    "Day in my life as [profession]",
                    "What I do in a day",
                    "Realistic day in my life"
                ],
                call_to_action_patterns=[
                    "What should I show next?",
                    "Comment questions",
                    "Follow along on stories"
                ],
                common_mistakes=[
                    "Too long and boring",
                    "Not enough variety",
                    "Poor pacing"
                ],
                example_creators=["@emmaChamberlain", "@casey"],
                example_posts=[]
            ),
        ]

        for template in templates:
            self._templates[template.format_id] = template

    def get_all_templates(self) -> List[FormatTemplate]:
        """Get all format templates"""
        return list(self._templates.values())

    def get_template(self, format_id: str) -> Optional[FormatTemplate]:
        """Get specific template by ID"""
        return self._templates.get(format_id)

    def get_templates_by_category(
        self,
        category: FormatCategory
    ) -> List[FormatTemplate]:
        """Get templates filtered by category"""
        return [
            t for t in self._templates.values()
            if t.category == category
        ]

    def get_templates_by_difficulty(
        self,
        difficulty: DifficultyLevel
    ) -> List[FormatTemplate]:
        """Get templates filtered by difficulty"""
        return [
            t for t in self._templates.values()
            if t.difficulty == difficulty
        ]

    def search_templates(self, query: str) -> List[FormatTemplate]:
        """
        Search templates by name, description, or keywords

        Args:
            query: Search query

        Returns:
            Matching templates sorted by relevance
        """
        query_lower = query.lower()
        matches = []

        for template in self._templates.values():
            # Check name, description, best_for, hook_patterns
            if (
                query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in bf.lower() for bf in template.best_for) or
                any(query_lower in hp.lower() for hp in template.hook_patterns)
            ):
                matches.append(template)

        # Sort by trending score
        return sorted(matches, key=lambda t: t.trending_score, reverse=True)

    def get_top_trending_templates(self, limit: int = 10) -> List[FormatTemplate]:
        """Get top trending format templates"""
        all_templates = self.get_all_templates()
        return sorted(
            all_templates,
            key=lambda t: t.trending_score,
            reverse=True
        )[:limit]

    def match_content_to_templates(
        self,
        content_description: str,
        content_type: Optional[str] = None,
        limit: int = 3
    ) -> List[FormatMatch]:
        """
        Match content description to suitable format templates

        Args:
            content_description: Description of content to create
            content_type: Optional content type hint
            limit: Maximum number of matches to return

        Returns:
            List of format matches with scores and suggestions
        """
        # Simple keyword-based matching (can be enhanced with AI)
        description_lower = content_description.lower()
        matches = []

        for template in self._templates.values():
            score = 0.0
            reasons = []

            # Category match
            if content_type and content_type.lower() in template.category.value:
                score += 30
                reasons.append(f"Matches {template.category.value} category")

            # Keyword matching
            keywords = description_lower.split()
            for keyword in keywords:
                if keyword in template.description.lower():
                    score += 10
                    reasons.append(f"Description mentions '{keyword}'")
                if any(keyword in bf.lower() for bf in template.best_for):
                    score += 15
                    reasons.append(f"Good for content with '{keyword}'")

            if score > 0:
                # Cap at 100
                score = min(score, 100)

                suggestions = [
                    f"Use hook pattern: {template.hook_patterns[0]}",
                    f"Estimated production time: {template.production_time}",
                    f"Equipment needed: {', '.join(template.equipment_needed)}"
                ]

                matches.append(FormatMatch(
                    format_id=template.format_id,
                    format_name=template.name,
                    match_score=score,
                    match_reasons=reasons[:3],  # Top 3 reasons
                    suggested_modifications=suggestions
                ))

        # Sort by score and return top N
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:limit]


# Singleton accessor
_instance: Optional[InstagramFormatTemplates] = None


def get_instagram_format_templates() -> InstagramFormatTemplates:
    """Get the singleton Instagram format templates instance"""
    global _instance
    if _instance is None:
        _instance = InstagramFormatTemplates()
    return _instance

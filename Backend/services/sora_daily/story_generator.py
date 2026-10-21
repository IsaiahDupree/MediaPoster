"""
Story Generator for Sora Daily Automation
Generates prompts for singles and 3-part movies with @isaiahdupree character.
"""

import os
import random
from typing import Dict, List, Optional
from loguru import logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


STORY_THEMES = [
    "day_in_life",
    "challenge",
    "discovery",
    "adventure",
    "creation",
    "connection",
    "transformation",
    "humor",
    "inspiration",
    "mystery",
    "celebration",
    "reflection",
    "growth",
    "surprise",
    "journey"
]

VISUAL_STYLES = [
    "cinematic 4K",
    "vibrant colors",
    "soft lighting",
    "dramatic shadows",
    "golden hour",
    "urban aesthetic",
    "natural beauty",
    "modern minimalist",
    "warm tones",
    "cool tones"
]

LOCATIONS = [
    "modern city skyline",
    "cozy coffee shop",
    "creative studio",
    "rooftop at sunset",
    "peaceful park",
    "busy street",
    "home office",
    "art gallery",
    "beach at golden hour",
    "mountain overlook"
]


class StoryGenerator:
    """
    Generates story prompts for Sora video generation.
    
    Creates prompts for:
    - Single standalone videos (trending topics)
    - 3-part story movies (@isaiahdupree character arcs)
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key and OpenAI else None
        logger.info("✅ StoryGenerator initialized")
    
    def get_random_theme(self) -> str:
        """Get a random story theme."""
        return random.choice(STORY_THEMES)
    
    def get_random_style(self) -> str:
        """Get a random visual style."""
        return random.choice(VISUAL_STYLES)
    
    def get_random_location(self) -> str:
        """Get a random location."""
        return random.choice(LOCATIONS)
    
    async def generate_single_prompt(
        self,
        theme: str = None,
        trend: str = None,
        character: str = "@isaiahdupree"
    ) -> str:
        raise RuntimeError("script_hub_required: legacy Sora generation is disabled; use ScriptHub.")
    
    async def generate_movie_prompt(
        self,
        part: int,
        theme: str = None,
        trend: str = None,
        character: str = "@isaiahdupree"
    ) -> str:
        raise RuntimeError("script_hub_required: legacy Sora generation is disabled; use ScriptHub.")
    
    def _generate_template_prompt(
        self,
        theme: str,
        style: str,
        location: str,
        character: str
    ) -> str:
        """Generate a template-based prompt."""
        templates = {
            "day_in_life": f"{character} starting their morning routine in a {location}, {style}, camera slowly pans across the scene, natural lighting",
            "challenge": f"{character} facing a difficult decision, intense close-up shot, {style}, dramatic pause, {location} background",
            "discovery": f"{character} finding something unexpected in a {location}, reaction shot, {style}, wonder and excitement",
            "adventure": f"{character} embarking on a journey, wide establishing shot of {location}, {style}, sense of movement and purpose",
            "creation": f"{character} in the flow of creative work, hands-on activity, {style}, focused energy in {location}",
            "connection": f"{character} having a meaningful moment, eye contact, {style}, warm atmosphere in {location}",
            "transformation": f"{character} experiencing a breakthrough moment, {style}, lighting shift, empowering mood",
            "humor": f"{character} in a playful, comedic situation, {style}, lighthearted energy, {location}",
            "inspiration": f"{character} looking out at the horizon, contemplative mood, {style}, {location}, golden hour lighting",
            "mystery": f"{character} discovering a hidden secret, suspenseful atmosphere, {style}, shadows and intrigue"
        }
        
        base = templates.get(theme, templates["day_in_life"])
        return base
    
    def _generate_movie_template(
        self,
        part: int,
        theme: str,
        style: str,
        character: str
    ) -> str:
        """Generate a template-based movie part prompt."""
        if part == 1:
            return f"{character} at the beginning of a {theme} journey, establishing shot, {style}, sense of anticipation, morning light"
        elif part == 2:
            return f"{character} in the midst of {theme}, facing challenges, {style}, dynamic camera movement, heightened emotion, midday intensity"
        else:
            return f"{character} reaching the conclusion of {theme}, triumphant moment, {style}, golden hour resolution, satisfying closure"
    
    async def generate_trend_prompt(
        self,
        trend_name: Optional[str] = None,
        character: str = "@isaiahdupree"
    ) -> Dict:
        raise RuntimeError("script_hub_required: legacy Sora generation is disabled; use ScriptHub.")

    async def generate_trend_series(
        self,
        trend_name: Optional[str] = None,
        series_id: Optional[str] = None,
        character: str = "@isaiahdupree"
    ) -> Dict:
        raise RuntimeError("script_hub_required: legacy Sora generation is disabled; use ScriptHub.")

    async def generate_story_arc(
        self,
        theme: str = None,
        trend: str = None,
        character: str = "@isaiahdupree"
    ) -> Dict:
        raise RuntimeError("script_hub_required: legacy Sora generation is disabled; use ScriptHub.")


# =============================================================================
# SINGLETON
# =============================================================================

_story_gen_instance: Optional[StoryGenerator] = None

def get_story_generator() -> StoryGenerator:
    """Get singleton instance of StoryGenerator."""
    global _story_gen_instance
    if _story_gen_instance is None:
        _story_gen_instance = StoryGenerator()
    return _story_gen_instance

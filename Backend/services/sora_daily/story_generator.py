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
        """
        Generate a prompt for a single standalone video.
        
        Args:
            theme: Story theme
            trend: Optional trending topic to incorporate
            character: Sora character to use
        
        Returns:
            Sora-optimized video prompt
        """
        theme = theme or self.get_random_theme()
        style = self.get_random_style()
        location = self.get_random_location()
        
        if self.client and trend:
            # Use AI to incorporate trend
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""Create a Sora video prompt featuring {character}.

Requirements:
- Theme: {theme}
- Trending topic to incorporate: {trend}
- Visual style: {style}
- Location: {location}
- Duration: 10-20 seconds
- Must be visually engaging
- Include specific camera movements
- Describe lighting and mood

Output ONLY the prompt, no explanation."""
                        },
                        {
                            "role": "user",
                            "content": "Generate the Sora prompt."
                        }
                    ],
                    temperature=0.9,
                    max_tokens=300
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"AI prompt generation failed: {e}")
        
        # Fallback to template-based prompt
        return self._generate_template_prompt(theme, style, location, character)
    
    async def generate_movie_prompt(
        self,
        part: int,
        theme: str = None,
        trend: str = None,
        character: str = "@isaiahdupree"
    ) -> str:
        """
        Generate a prompt for a 3-part movie.
        
        Args:
            part: Part number (1, 2, or 3)
            theme: Story theme
            trend: Optional trending topic
            character: Sora character
        
        Returns:
            Sora-optimized video prompt for the specific part
        """
        theme = theme or self.get_random_theme()
        style = self.get_random_style()
        
        part_descriptions = {
            1: "Setup/Hook - Introduce the character and situation, create intrigue",
            2: "Conflict/Development - Show the challenge or journey, build tension",
            3: "Resolution/CTA - Conclude the story, show transformation or success"
        }
        
        part_desc = part_descriptions.get(part, part_descriptions[1])
        
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""Create Part {part} of a 3-part Sora video series featuring {character}.

Story Theme: {theme}
Part Purpose: {part_desc}
Visual Style: {style}
{f'Trending Topic: {trend}' if trend else ''}

Requirements:
- 10-20 seconds of footage
- Continuous visual flow
- Specific camera movements
- Clear emotional tone
- Works as part of series

Output ONLY the prompt, no explanation."""
                        },
                        {
                            "role": "user",
                            "content": f"Generate Part {part} prompt."
                        }
                    ],
                    temperature=0.8,
                    max_tokens=300
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"AI movie prompt generation failed: {e}")
        
        # Fallback
        return self._generate_movie_template(part, theme, style, character)
    
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
        """
        Generate a prompt using the curated trend library.
        
        Args:
            trend_name: Optional filter for a specific trend
            character: Sora character
        
        Returns:
            Dict with prompt metadata and sora_prompt
        """
        try:
            from services.sora_daily.trend_prompts import get_trend_prompt_library
            library = get_trend_prompt_library()
            
            if trend_name:
                matches = library.get_prompts(trend_name=trend_name)
                singles = [p for p in matches if p.category == "single"]
                prompt = random.choice(singles) if singles else library.get_random_prompt()
            else:
                prompt = library.get_random_prompt()
            
            if prompt:
                return {
                    "source": "trend_library",
                    "prompt_id": prompt.id,
                    "trend_name": prompt.trend_name,
                    "sora_prompt": prompt.sora_prompt,
                    "caption": prompt.caption,
                    "hashtags": prompt.hashtags,
                    "suggested_audio": prompt.suggested_audio,
                    "platforms": prompt.platforms,
                }
        except ImportError:
            logger.warning("Trend library not available, falling back to AI generation")
        except Exception as e:
            logger.error(f"Trend prompt lookup failed: {e}")
        
        # Fallback to standard AI generation
        sora_prompt = await self.generate_single_prompt(trend=trend_name, character=character)
        return {
            "source": "ai_generated",
            "prompt_id": None,
            "trend_name": trend_name,
            "sora_prompt": sora_prompt,
            "caption": None,
            "hashtags": [],
            "suggested_audio": None,
            "platforms": ["tiktok", "instagram", "youtube_shorts"],
        }

    async def generate_trend_series(
        self,
        trend_name: Optional[str] = None,
        series_id: Optional[str] = None,
        character: str = "@isaiahdupree"
    ) -> Dict:
        """
        Generate a 3-part series from the curated trend library.
        
        Args:
            trend_name: Optional filter for a specific trend
            series_id: Optional specific series ID
            character: Sora character
        
        Returns:
            Dict with series metadata and all part prompts
        """
        try:
            from services.sora_daily.trend_prompts import get_trend_prompt_library
            library = get_trend_prompt_library()
            
            if series_id:
                parts = library.get_prompts(series_id=series_id)
            elif trend_name:
                all_series = library.get_series()
                # Find series matching the trend
                parts = []
                for sid, series_parts in all_series.items():
                    if any(trend_name.lower() in p.trend_name.lower() for p in series_parts):
                        parts = series_parts
                        break
            else:
                series_parts = library.get_random_series()
                parts = series_parts if series_parts else []
            
            if parts:
                return {
                    "source": "trend_library",
                    "series_id": parts[0].series_id,
                    "trend_name": parts[0].trend_name,
                    "character": character,
                    "parts": [
                        {
                            "part": i + 1,
                            "prompt_id": p.id,
                            "title": p.title,
                            "sora_prompt": p.sora_prompt,
                            "caption": p.caption,
                            "hashtags": p.hashtags,
                            "suggested_audio": p.suggested_audio,
                        }
                        for i, p in enumerate(parts)
                    ],
                }
        except ImportError:
            logger.warning("Trend library not available, falling back to AI generation")
        except Exception as e:
            logger.error(f"Trend series lookup failed: {e}")
        
        # Fallback to standard AI story arc generation
        arc = await self.generate_story_arc(trend=trend_name, character=character)
        arc["source"] = "ai_generated"
        return arc

    async def generate_story_arc(
        self,
        theme: str = None,
        trend: str = None,
        character: str = "@isaiahdupree"
    ) -> Dict:
        """
        Generate a complete 3-part story arc.
        
        Returns:
            Dict with story metadata and all 3 prompts
        """
        theme = theme or self.get_random_theme()
        
        prompts = []
        for part in range(1, 4):
            prompt = await self.generate_movie_prompt(part, theme, trend, character)
            prompts.append(prompt)
        
        return {
            "theme": theme,
            "trend": trend,
            "character": character,
            "parts": [
                {"part": 1, "purpose": "Setup/Hook", "prompt": prompts[0]},
                {"part": 2, "purpose": "Conflict/Development", "prompt": prompts[1]},
                {"part": 3, "purpose": "Resolution/CTA", "prompt": prompts[2]}
            ]
        }


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

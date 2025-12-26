"""
Trend Brief Generator - OpenAI Integration
Generates content briefs from trend data using GPT-4.
"""
import os
import json
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class TrendBriefGenerator:
    """
    Generates content briefs using OpenAI GPT-4.
    
    Takes trend data (hashtag, sound, or topic) and generates:
    - Hook options (3 variations)
    - Script outline (hook, problem, solution, proof, CTA)
    - Format recommendations
    - Differentiation ideas
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = "gpt-4o-mini"  # Fast and cost-effective
        
    async def generate_brief(
        self,
        trend_type: str,
        trend_name: str,
        niche: Optional[str] = None,
        top_examples: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Generate a content brief from trend data."""
        
        if not self.api_key:
            logger.warning("OpenAI API key not set, using template generation")
            return self._generate_template_brief(trend_type, trend_name, niche)
        
        # Build context from examples
        examples_context = ""
        if top_examples:
            examples_context = "\n\nTop performing examples:\n"
            for i, ex in enumerate(top_examples[:5], 1):
                examples_context += f"{i}. {ex.get('caption', '')[:100]}... ({ex.get('plays', 0):,} plays)\n"
        
        prompt = f"""You are a social media content strategist. Generate a content brief for a creator who wants to make content about the {trend_type}: "{trend_name}".

Niche: {niche or 'general'}
{examples_context}

Generate a JSON response with:
1. "hook_options": 3 attention-grabbing hooks (first 3 seconds of video)
2. "script_outline": {{
   "hook": "What to say/show in first 3 seconds",
   "problem": "Relatable struggle to present (3-8 seconds)",
   "solution": "Your method/tip (8-20 seconds)", 
   "proof": "Quick result or demo (20-35 seconds)",
   "cta": "Call to action"
}}
3. "recommended_format": "reel" or "carousel" or "post"
4. "optimal_length_sec": {{"min": number, "max": number}}
5. "must_include_phrases": list of 3-5 phrases that work well
6. "differentiation_twist": unique angle to stand out

Respond ONLY with valid JSON, no markdown."""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                # Parse JSON from response
                brief = json.loads(content.strip())
                brief["generated_at"] = datetime.utcnow().isoformat()
                brief["trend_name"] = trend_name
                brief["trend_type"] = trend_type
                
                logger.info(f"✅ Generated AI brief for {trend_name}")
                return brief
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            return self._generate_template_brief(trend_type, trend_name, niche)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._generate_template_brief(trend_type, trend_name, niche)
    
    def _generate_template_brief(
        self,
        trend_type: str,
        trend_name: str,
        niche: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback template-based brief generation."""
        clean_name = trend_name.replace("#", "")
        
        return {
            "trend_name": trend_name,
            "trend_type": trend_type,
            "hook_options": [
                f"Stop making this {clean_name} mistake (here's why)",
                f"I tried {clean_name} for 7 days—here's what happened",
                f"The {clean_name} hack that changed everything"
            ],
            "script_outline": {
                "hook": f"Bold claim or question about {clean_name} (0-3s)",
                "problem": f"Common struggle with {clean_name} (3-8s)",
                "solution": f"Your unique approach to {clean_name} (8-20s)",
                "proof": "Quick result or demonstration (20-35s)",
                "cta": "Save this + follow for more tips"
            },
            "recommended_format": "reel",
            "optimal_length_sec": {"min": 25, "max": 45},
            "must_include_phrases": [clean_name, "save this", "follow for more"],
            "differentiation_twist": f"Focus on the budget-friendly or beginner angle—most {clean_name} content skips this",
            "generated_at": datetime.utcnow().isoformat()
        }


async def generate_hooks_for_niche(niche: str, count: int = 10) -> List[Dict]:
    """Generate hook patterns for a specific niche."""
    generator = TrendBriefGenerator()
    
    if not generator.api_key:
        # Return common hook templates
        return [
            {"pattern": "Stop doing ___ (here's why)", "example": f"Stop doing {niche} wrong"},
            {"pattern": "I did ___ for 30 days", "example": f"I did {niche} for 30 days"},
            {"pattern": "The ___ nobody talks about", "example": f"The {niche} secret nobody talks about"},
            {"pattern": "POV: You finally ___", "example": f"POV: You finally mastered {niche}"},
            {"pattern": "3 things I wish I knew about ___", "example": f"3 things I wish I knew about {niche}"},
        ]
    
    prompt = f"""Generate {count} high-performing hook patterns for {niche} content on social media.

For each hook, provide:
1. "pattern": The template (use ___ for placeholders)
2. "example": A specific example for {niche}
3. "why_works": Brief explanation of psychological trigger

Respond with a JSON array."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {generator.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 1500
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content.strip())
    except Exception as e:
        logger.error(f"Failed to generate hooks: {e}")
        return []

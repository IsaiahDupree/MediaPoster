"""
Script Generation
==================
Expands a topic/angle (typically the output of content_recommendation.py's
recommend_next_content()) into a full, copy-pasteable production packet:
hook, main talking points, proof/demo, CTA, a full spoken script, and a
simple shot-by-shot visual plan.

Unlike trend/recommendation, there is no sensible non-AI substitute for
"write me a script" -- a deterministic template would just be a worse,
generic version of the same job an LLM already does well. When no AI
provider is configured (or the call fails), this raises rather than
returning a fabricated script.
"""
import json
import os
from typing import Any, Dict, Optional

from loguru import logger


class ScriptGenerationUnavailable(RuntimeError):
    """Raised when no AI provider is configured or the generation call fails.

    Deliberately not swallowed into a fallback -- see module docstring.
    """


class ScriptGenerationService:
    async def generate_script(
        self,
        topic: str,
        angle: Optional[str] = None,
        content_format: Optional[str] = None,
        platform: Optional[str] = None,
        hook: Optional[str] = None,
        reasoning: Optional[str] = None,
        brand_voice: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None,
        available_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        `topic` is required; everything else is optional context, typically
        carried straight over from a recommend_next_content() result
        (topic/angle/format/platform/hook/reasoning have the same names).
        `available_minutes` scales the script's depth: a 5-minute budget gets
        a single quick take, a 60-minute budget gets a full multi-shot
        tutorial structure.
        """
        topic = (topic or "").strip()
        if not topic:
            raise ValueError("topic must be a non-empty string")

        try:
            return await self._gpt_generate(
                topic, angle, content_format, platform, hook, reasoning,
                brand_voice, target_audience, available_minutes,
            )
        except Exception as e:
            logger.error(f"[Script] generation failed for topic={topic!r}: {e}")
            raise ScriptGenerationUnavailable(str(e)) from e

    @staticmethod
    async def _gpt_generate(
        topic: str,
        angle: Optional[str],
        content_format: Optional[str],
        platform: Optional[str],
        hook: Optional[str],
        reasoning: Optional[str],
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str],
        available_minutes: Optional[int],
    ) -> Dict[str, Any]:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        voice_desc = json.dumps(brand_voice) if brand_voice else "no specific voice configured"
        minutes_desc = f"{available_minutes} minutes" if available_minutes is not None else "not specified"

        context_lines = [f"Topic: {topic}"]
        if angle:
            context_lines.append(f"Angle: {angle}")
        if content_format:
            context_lines.append(f"Format: {content_format}")
        if platform:
            context_lines.append(f"Platform: {platform}")
        if hook:
            context_lines.append(f"Suggested hook to build from: {hook}")
        if reasoning:
            context_lines.append(f"Why this topic was recommended: {reasoning}")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a short-form content scriptwriter. Turn the given topic into a
complete, copy-pasteable production packet a creator can record from
immediately -- no further ideation needed on their end.

Brand voice: {voice_desc}
Target audience: {target_audience or 'not specified'}
Available time to record + edit: {minutes_desc} -- scale the script's length
and shot count to genuinely fit this budget (a 5-minute budget should be
recordable as ONE quick take with 0-1 cuts; a 60-minute budget can be a full
multi-shot tutorial).

Return JSON exactly matching this shape:
{{
  "hook": "the exact opening line, scroll-stopping, said aloud",
  "context": "1-2 sentences setting up why this matters, said aloud right after the hook",
  "main_points": ["point 1", "point 2", "..."],
  "proof_or_demo": "the concrete proof/demo/example that makes this credible, said aloud",
  "cta": "the exact closing call-to-action line, said aloud",
  "full_spoken_script": "the ENTIRE script as continuous prose, ready to read aloud top to bottom -- hook through CTA, matching the available time budget",
  "visual_plan": {{
    "opening_visual": "what's on screen during the hook",
    "shots": [
      {{"timestamp": "0:00-0:05", "narration": "matching spoken words for this beat", "visual": "what's on screen", "on_screen_text": "any overlay text, or null"}}
    ],
    "b_roll": ["b-roll idea 1", "b-roll idea 2"]
  }},
  "estimated_recording_minutes": number,
  "estimated_editing_minutes": number
}}""",
                },
                {
                    "role": "user",
                    "content": "\n".join(context_lines),
                },
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)


_service: Optional[ScriptGenerationService] = None


def get_script_generation_service() -> ScriptGenerationService:
    global _service
    if _service is None:
        _service = ScriptGenerationService()
    return _service

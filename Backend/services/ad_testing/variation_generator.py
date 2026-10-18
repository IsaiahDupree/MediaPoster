"""
Ad Variation Generator (AD-002)
================================
Generates multiple ad creative variations from extracted transcript elements.

Strategies:
    - hook_swap: Same body, different hooks
    - cta_swap: Same body, different CTAs
    - matrix: All combinations of hooks x CTAs x pain_points
    - ai_remix: AI-generated novel combinations

Each variation contains: id, headline, body, cta, hook, target_audience, platform.

Usage:
    generator = get_variation_generator()
    variations = generator.generate_variations(elements, strategy="matrix")
"""

import itertools
import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Default platforms for ad variations
DEFAULT_PLATFORMS = ["facebook", "instagram"]

# Default audience segments
DEFAULT_AUDIENCES = [
    {"name": "broad", "age_min": 18, "age_max": 65, "interests": []},
    {"name": "young_adults", "age_min": 18, "age_max": 34, "interests": ["social media"]},
    {"name": "professionals", "age_min": 25, "age_max": 54, "interests": ["business"]},
]


def _make_variation_id() -> str:
    """Generate a unique variation ID."""
    return f"var-{uuid4().hex[:8]}"


class AdVariationGenerator:
    """
    Generates ad creative variations from extracted elements (AD-002).

    Supports multiple strategies for producing test-ready ad creatives.
    """

    _instance: Optional["AdVariationGenerator"] = None

    def __init__(self) -> None:
        self._openai_client: Optional[Any] = None
        self._model = "gpt-4o-mini"
        self._init_openai()
        logger.info("[AD-002] AdVariationGenerator initialized")

    def _init_openai(self) -> None:
        """Initialize OpenAI client for ai_remix strategy."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.info("[AD-002] OPENAI_API_KEY not set - ai_remix strategy unavailable")
            return
        try:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=api_key)
            logger.info(f"[AD-002] OpenAI client ready for ai_remix (model={self._model})")
        except ImportError:
            logger.warning("[AD-002] openai package not installed")
        except Exception as exc:
            logger.error(f"[AD-002] OpenAI init error: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_variations(
        self,
        elements: Dict[str, List[str]],
        strategy: str = "matrix",
        platforms: Optional[List[str]] = None,
        audiences: Optional[List[Dict[str, Any]]] = None,
        max_variations: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Generate ad variations from extracted elements.

        Args:
            elements: Dict from TranscriptElementExtractor.extract_elements().
                      Expected keys: hooks, pain_points, benefits, ctas, social_proofs.
            strategy: One of "hook_swap", "cta_swap", "matrix", "ai_remix".
            platforms: Target platforms (default: facebook, instagram).
            audiences: Target audience dicts (default: broad/young_adults/professionals).
            max_variations: Maximum number of variations to generate.

        Returns:
            List of variation dicts, each with:
                id, headline, body, cta, hook, target_audience, platform, strategy.
        """
        platforms = platforms or DEFAULT_PLATFORMS
        audiences = audiences or DEFAULT_AUDIENCES

        hooks = elements.get("hooks", []) or ["Check this out"]
        pain_points = elements.get("pain_points", []) or [""]
        benefits = elements.get("benefits", []) or [""]
        ctas = elements.get("ctas", []) or ["Learn more"]
        social_proofs = elements.get("social_proofs", []) or [""]

        strategy_map = {
            "hook_swap": self._strategy_hook_swap,
            "cta_swap": self._strategy_cta_swap,
            "matrix": self._strategy_matrix,
            "ai_remix": self._strategy_ai_remix,
        }

        handler = strategy_map.get(strategy)
        if handler is None:
            logger.error(f"[AD-002] Unknown strategy '{strategy}', falling back to matrix")
            handler = self._strategy_matrix

        raw_variations = handler(
            hooks=hooks,
            pain_points=pain_points,
            benefits=benefits,
            ctas=ctas,
            social_proofs=social_proofs,
        )

        # Expand across platforms and audiences, then cap
        variations = self._expand_variations(raw_variations, platforms, audiences)
        variations = variations[:max_variations]

        logger.info(
            f"[AD-002] Generated {len(variations)} variations "
            f"(strategy={strategy}, platforms={platforms})"
        )
        return variations

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _strategy_hook_swap(
        self,
        hooks: List[str],
        pain_points: List[str],
        benefits: List[str],
        ctas: List[str],
        social_proofs: List[str],
    ) -> List[Dict[str, Any]]:
        """Keep the same body; vary only the hook."""
        base_body = pain_points[0] if pain_points[0] else (benefits[0] if benefits else "")
        base_cta = ctas[0]

        variations: List[Dict[str, Any]] = []
        for hook in hooks:
            variations.append(
                {
                    "id": _make_variation_id(),
                    "headline": hook,
                    "body": base_body,
                    "cta": base_cta,
                    "hook": hook,
                    "strategy": "hook_swap",
                }
            )
        return variations

    def _strategy_cta_swap(
        self,
        hooks: List[str],
        pain_points: List[str],
        benefits: List[str],
        ctas: List[str],
        social_proofs: List[str],
    ) -> List[Dict[str, Any]]:
        """Keep the same body and hook; vary only the CTA."""
        base_hook = hooks[0]
        base_body = pain_points[0] if pain_points[0] else (benefits[0] if benefits else "")

        variations: List[Dict[str, Any]] = []
        for cta in ctas:
            variations.append(
                {
                    "id": _make_variation_id(),
                    "headline": base_hook,
                    "body": base_body,
                    "cta": cta,
                    "hook": base_hook,
                    "strategy": "cta_swap",
                }
            )
        return variations

    def _strategy_matrix(
        self,
        hooks: List[str],
        pain_points: List[str],
        benefits: List[str],
        ctas: List[str],
        social_proofs: List[str],
    ) -> List[Dict[str, Any]]:
        """Generate all combinations of hooks x CTAs x pain_points."""
        # Limit individual dimensions to keep output reasonable
        h = hooks[:5]
        c = ctas[:5]
        p = pain_points[:3] if pain_points[0] else [""]

        variations: List[Dict[str, Any]] = []
        for hook, cta, pain in itertools.product(h, c, p):
            body_parts = [pain] if pain else []
            if benefits:
                body_parts.append(benefits[0])
            if social_proofs and social_proofs[0]:
                body_parts.append(social_proofs[0])

            body = " ".join(part for part in body_parts if part)

            variations.append(
                {
                    "id": _make_variation_id(),
                    "headline": hook,
                    "body": body,
                    "cta": cta,
                    "hook": hook,
                    "strategy": "matrix",
                }
            )
        return variations

    def _strategy_ai_remix(
        self,
        hooks: List[str],
        pain_points: List[str],
        benefits: List[str],
        ctas: List[str],
        social_proofs: List[str],
    ) -> List[Dict[str, Any]]:
        """Use AI to generate novel creative combinations."""
        if not self._openai_client:
            logger.warning(
                "[AD-002] ai_remix requires OpenAI - falling back to matrix strategy"
            )
            return self._strategy_matrix(hooks, pain_points, benefits, ctas, social_proofs)

        try:
            return self._ai_remix_generate(hooks, pain_points, benefits, ctas, social_proofs)
        except Exception as exc:
            logger.error(f"[AD-002] AI remix failed, falling back to matrix: {exc}")
            return self._strategy_matrix(hooks, pain_points, benefits, ctas, social_proofs)

    def _ai_remix_generate(
        self,
        hooks: List[str],
        pain_points: List[str],
        benefits: List[str],
        ctas: List[str],
        social_proofs: List[str],
    ) -> List[Dict[str, Any]]:
        """Call OpenAI to generate novel ad variations."""
        system_prompt = (
            "You are an elite Meta Ads creative strategist. "
            "Given raw ad elements, create novel high-converting ad variations. "
            "Return ONLY valid JSON: {\"variations\": [{\"headline\": ..., \"body\": ..., "
            "\"cta\": ..., \"hook\": ...}, ...]}. Generate 5-8 variations."
        )

        user_prompt = (
            "Create novel Meta ad variations from these elements:\n\n"
            f"HOOKS: {json.dumps(hooks[:5])}\n"
            f"PAIN POINTS: {json.dumps(pain_points[:5])}\n"
            f"BENEFITS: {json.dumps(benefits[:5])}\n"
            f"CTAs: {json.dumps(ctas[:5])}\n"
            f"SOCIAL PROOF: {json.dumps(social_proofs[:3])}\n\n"
            "Create unique combinations that would perform well as Meta ads. "
            "Mix and remix elements creatively. Each variation needs: headline, body, cta, hook."
        )

        response = self._openai_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw = json.loads(response.choices[0].message.content)
        ai_variations = raw.get("variations", [])

        variations: List[Dict[str, Any]] = []
        for v in ai_variations:
            variations.append(
                {
                    "id": _make_variation_id(),
                    "headline": v.get("headline", ""),
                    "body": v.get("body", ""),
                    "cta": v.get("cta", "Learn more"),
                    "hook": v.get("hook", v.get("headline", "")),
                    "strategy": "ai_remix",
                }
            )

        logger.info(f"[AD-002] AI remix generated {len(variations)} novel variations")
        return variations

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _expand_variations(
        self,
        raw_variations: List[Dict[str, Any]],
        platforms: List[str],
        audiences: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Expand raw variations across platforms and audiences."""
        expanded: List[Dict[str, Any]] = []
        for var in raw_variations:
            for platform in platforms:
                for audience in audiences:
                    expanded.append(
                        {
                            **var,
                            "id": _make_variation_id(),
                            "platform": platform,
                            "target_audience": audience,
                        }
                    )
        return expanded


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_variation_generator_instance: Optional[AdVariationGenerator] = None


def get_variation_generator() -> AdVariationGenerator:
    """Get or create the singleton AdVariationGenerator instance."""
    global _variation_generator_instance
    if _variation_generator_instance is None:
        _variation_generator_instance = AdVariationGenerator()
    return _variation_generator_instance

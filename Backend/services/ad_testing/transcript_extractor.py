"""
Transcript Element Extractor (AD-001)
======================================
Wraps ContentAnalyzer to extract ad-specific elements from video transcripts.

Extracts:
    - Hooks: Attention-grabbing opening lines
    - Pain points: Problems the audience resonates with
    - Benefits: Value propositions and outcomes
    - CTAs: Calls to action
    - Social proofs: Testimonials, stats, authority signals

Uses OpenAI gpt-4o-mini for extraction with graceful fallback to
heuristic-based extraction when API keys are unavailable.

Usage:
    extractor = get_extractor()
    elements = extractor.extract_elements(transcript)
    hooks = extractor.extract_hooks(transcript)
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Heuristic patterns for fallback extraction (no API key required)
# ---------------------------------------------------------------------------
HOOK_PATTERNS = [
    r"(?i)^(did you know|here'?s? (?:the|a|why)|stop scrolling|wait|"
    r"you won'?t believe|imagine|what if|the secret|nobody tells you|"
    r"i need to tell you|listen up|this changed|this is why|"
    r"most people don'?t|the truth about|are you still|"
    r"don'?t (?:make this mistake|skip this)|breaking)[^.!?]*[.!?]",
]

PAIN_PATTERNS = [
    r"(?i)(struggling with|tired of|frustrated|sick of|hate when|"
    r"can'?t (?:figure out|seem to|stop)|the problem is|"
    r"it'?s so hard|nothing works|wasting (?:time|money)|"
    r"losing (?:sleep|money|time)|if you'?re like me)[^.!?]*[.!?]",
]

CTA_PATTERNS = [
    r"(?i)(click (?:the link|below|here)|follow (?:for more|me)|"
    r"subscribe|comment (?:below|your)|share this|"
    r"link in (?:bio|description)|dm me|sign up|"
    r"grab (?:yours|it|this)|try (?:it|this)|get (?:started|yours)|"
    r"check (?:it out|the link|this out)|don'?t miss|"
    r"save this|tag (?:someone|a friend))[^.!?]*[.!?]",
]

BENEFIT_PATTERNS = [
    r"(?i)(you'?ll (?:get|see|feel|notice|love|save)|"
    r"this (?:helps|saves|gives|makes)|"
    r"(?:save|earn|grow|boost|increase|double|triple)[^.!?]{5,40}|"
    r"in (?:just|only) \d+|results in|"
    r"the (?:best|fastest|easiest|simplest) way)[^.!?]*[.!?]",
]

SOCIAL_PROOF_PATTERNS = [
    r"(?i)(\d+[\+k]?\s*(?:people|customers|users|followers|clients)|"
    r"(?:as seen (?:on|in)|featured (?:on|in))|"
    r"(?:testimonial|review|case study)|"
    r"(?:doctor|expert|scientist|study|research)\s+(?:says?|shows?|proves?|confirms?)|"
    r"rated \d|stars?\s*(?:on|rating)|best[-\s]?seller)[^.!?]*[.!?]",
]


def _heuristic_extract(text: str, patterns: List[str]) -> List[str]:
    """Extract matches from text using regex patterns."""
    results: List[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            cleaned = match.group(0).strip()
            if cleaned and cleaned not in results and len(cleaned) > 10:
                results.append(cleaned)
    return results


class TranscriptElementExtractor:
    """
    Extracts ad-specific creative elements from video transcripts (AD-001).

    Uses OpenAI gpt-4o-mini for AI-powered extraction. Falls back to
    regex-based heuristics when no API key is available.
    """

    _instance: Optional["TranscriptElementExtractor"] = None

    def __init__(self) -> None:
        self._openai_client: Optional[Any] = None
        self._model = "gpt-4o-mini"
        self._init_openai()
        logger.info("[AD-001] TranscriptElementExtractor initialized")

    # ------------------------------------------------------------------
    # OpenAI initialisation
    # ------------------------------------------------------------------

    def _init_openai(self) -> None:
        """Initialise OpenAI client if an API key is available."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "[AD-001] OPENAI_API_KEY not set - falling back to heuristic extraction"
            )
            return
        try:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=api_key)
            logger.info(f"[AD-001] OpenAI client ready (model={self._model})")
        except ImportError:
            logger.warning(
                "[AD-001] openai package not installed - falling back to heuristic extraction"
            )
        except Exception as exc:
            logger.error(f"[AD-001] OpenAI init error: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_elements(self, transcript: str) -> Dict[str, List[str]]:
        """
        Extract all ad-specific elements from a transcript.

        Args:
            transcript: The full video transcript text.

        Returns:
            Dict with keys: hooks, pain_points, benefits, ctas, social_proofs.
            Each value is a list of extracted strings.
        """
        if not transcript or not transcript.strip():
            logger.warning("[AD-001] Empty transcript provided")
            return {
                "hooks": [],
                "pain_points": [],
                "benefits": [],
                "ctas": [],
                "social_proofs": [],
            }

        # Try AI extraction first
        if self._openai_client:
            try:
                return self._ai_extract_all(transcript)
            except Exception as exc:
                logger.error(f"[AD-001] AI extraction failed, using heuristics: {exc}")

        # Fallback to heuristic extraction
        return self._heuristic_extract_all(transcript)

    def extract_hooks(self, transcript: str) -> List[str]:
        """Extract attention-grabbing hooks from transcript."""
        if self._openai_client:
            try:
                return self._ai_extract_category(transcript, "hooks")
            except Exception as exc:
                logger.error(f"[AD-001] AI hook extraction failed: {exc}")
        return _heuristic_extract(transcript, HOOK_PATTERNS)

    def extract_pain_points(self, transcript: str) -> List[str]:
        """Extract pain points the audience resonates with."""
        if self._openai_client:
            try:
                return self._ai_extract_category(transcript, "pain_points")
            except Exception as exc:
                logger.error(f"[AD-001] AI pain-point extraction failed: {exc}")
        return _heuristic_extract(transcript, PAIN_PATTERNS)

    def extract_ctas(self, transcript: str) -> List[str]:
        """Extract calls to action from transcript."""
        if self._openai_client:
            try:
                return self._ai_extract_category(transcript, "ctas")
            except Exception as exc:
                logger.error(f"[AD-001] AI CTA extraction failed: {exc}")
        return _heuristic_extract(transcript, CTA_PATTERNS)

    def extract_benefits(self, transcript: str) -> List[str]:
        """Extract benefit / value-proposition statements from transcript."""
        if self._openai_client:
            try:
                return self._ai_extract_category(transcript, "benefits")
            except Exception as exc:
                logger.error(f"[AD-001] AI benefits extraction failed: {exc}")
        return _heuristic_extract(transcript, BENEFIT_PATTERNS)

    def extract_social_proofs(self, transcript: str) -> List[str]:
        """Extract social proof signals from transcript."""
        if self._openai_client:
            try:
                return self._ai_extract_category(transcript, "social_proofs")
            except Exception as exc:
                logger.error(f"[AD-001] AI social-proof extraction failed: {exc}")
        return _heuristic_extract(transcript, SOCIAL_PROOF_PATTERNS)

    # ------------------------------------------------------------------
    # AI-powered extraction
    # ------------------------------------------------------------------

    def _ai_extract_all(self, transcript: str) -> Dict[str, List[str]]:
        """Use OpenAI to extract all ad elements at once."""
        system_prompt = (
            "You are an expert direct-response copywriter and ad creative strategist. "
            "Given a video transcript, extract the following ad creative elements. "
            "Return ONLY valid JSON with these keys: hooks, pain_points, benefits, ctas, social_proofs. "
            "Each value must be a JSON array of strings. "
            "If a category has no matches, return an empty array. "
            "Extract 2-5 items per category when available."
        )

        user_prompt = (
            f"Extract ad creative elements from this transcript:\n\n"
            f"---\n{transcript[:4000]}\n---\n\n"
            "Return JSON with: hooks (attention-grabbing openers), "
            "pain_points (audience problems), benefits (value propositions), "
            "ctas (calls to action), social_proofs (testimonials/stats/authority)."
        )

        response = self._openai_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        # Normalise keys
        normalised: Dict[str, List[str]] = {
            "hooks": result.get("hooks", []),
            "pain_points": result.get("pain_points", []),
            "benefits": result.get("benefits", []),
            "ctas": result.get("ctas", []),
            "social_proofs": result.get("social_proofs", []),
        }

        total = sum(len(v) for v in normalised.values())
        logger.info(f"[AD-001] AI extracted {total} elements from transcript")
        return normalised

    def _ai_extract_category(self, transcript: str, category: str) -> List[str]:
        """Extract a single category of elements using AI."""
        category_descriptions = {
            "hooks": "attention-grabbing opening lines or hooks",
            "pain_points": "problems, frustrations, or pain points the audience has",
            "benefits": "benefits, value propositions, or positive outcomes",
            "ctas": "calls to action (things telling the viewer what to do next)",
            "social_proofs": "social proof elements (testimonials, stats, authority signals)",
        }

        description = category_descriptions.get(category, category)

        response = self._openai_client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert ad copywriter. Extract specific elements "
                        "from transcripts. Return ONLY a JSON object with a single key "
                        f'"{category}" containing an array of strings.'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Extract all {description} from this transcript:\n\n"
                        f"---\n{transcript[:4000]}\n---\n\n"
                        f'Return JSON: {{"{category}": [...]}}'
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)
        items = result.get(category, [])
        logger.info(f"[AD-001] AI extracted {len(items)} {category}")
        return items

    # ------------------------------------------------------------------
    # Heuristic fallback
    # ------------------------------------------------------------------

    def _heuristic_extract_all(self, transcript: str) -> Dict[str, List[str]]:
        """Extract elements using regex-based heuristics (no API key needed)."""
        elements = {
            "hooks": _heuristic_extract(transcript, HOOK_PATTERNS),
            "pain_points": _heuristic_extract(transcript, PAIN_PATTERNS),
            "benefits": _heuristic_extract(transcript, BENEFIT_PATTERNS),
            "ctas": _heuristic_extract(transcript, CTA_PATTERNS),
            "social_proofs": _heuristic_extract(transcript, SOCIAL_PROOF_PATTERNS),
        }

        # If the first sentence looks like a hook, add it
        sentences = re.split(r"[.!?]+", transcript.strip())
        if sentences and len(sentences[0].strip()) > 10:
            first = sentences[0].strip() + "."
            if first not in elements["hooks"]:
                elements["hooks"].insert(0, first)

        total = sum(len(v) for v in elements.values())
        logger.info(f"[AD-001] Heuristic extracted {total} elements from transcript")
        return elements


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_extractor_instance: Optional[TranscriptElementExtractor] = None


def get_extractor() -> TranscriptElementExtractor:
    """Get or create the singleton TranscriptElementExtractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = TranscriptElementExtractor()
    return _extractor_instance

"""
YTP-014: A/B Testing for AI Prompts
Tests different AI prompt variations to optimize content quality.
"""
import logging
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PromptVariant:
    """A prompt variant for A/B testing."""
    variant_id: str
    name: str
    prompt_template: str
    weight: float = 1.0
    active: bool = True


@dataclass
class ABTestResult:
    """Result of using a prompt variant."""
    variant_id: str
    test_id: str
    content_quality_score: float = 0.0
    engagement_score: float = 0.0
    completion_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromptABTestingService:
    """
    A/B testing service for AI prompts.

    Manages prompt variants, selects variants for testing,
    and tracks results to determine winning prompts.
    """

    def __init__(self):
        self._variants: Dict[str, List[PromptVariant]] = defaultdict(list)
        self._results: Dict[str, List[ABTestResult]] = defaultdict(list)
        self._active_tests: Dict[str, str] = {}  # test_id -> variant_id

    def register_variants(
        self,
        test_name: str,
        variants: List[PromptVariant],
    ) -> None:
        """Register prompt variants for a test."""
        self._variants[test_name] = variants
        logger.info("Registered %d variants for test '%s'", len(variants), test_name)

    def select_variant(self, test_name: str) -> Optional[PromptVariant]:
        """
        Select a variant using weighted random selection.

        Args:
            test_name: Name of the A/B test

        Returns:
            Selected PromptVariant, or None if no variants registered
        """
        variants = [v for v in self._variants.get(test_name, []) if v.active]
        if not variants:
            return None

        weights = [v.weight for v in variants]
        selected = random.choices(variants, weights=weights, k=1)[0]
        return selected

    def record_result(
        self,
        test_name: str,
        result: ABTestResult,
    ) -> None:
        """Record the result of using a prompt variant."""
        self._results[test_name].append(result)

    def get_variant_stats(self, test_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for each variant in a test.

        Returns:
            Dict mapping variant_id to stats
        """
        stats: Dict[str, Dict[str, Any]] = {}
        results = self._results.get(test_name, [])

        for variant in self._variants.get(test_name, []):
            variant_results = [r for r in results if r.variant_id == variant.variant_id]

            if variant_results:
                avg_quality = sum(r.content_quality_score for r in variant_results) / len(variant_results)
                avg_engagement = sum(r.engagement_score for r in variant_results) / len(variant_results)
            else:
                avg_quality = 0
                avg_engagement = 0

            stats[variant.variant_id] = {
                "name": variant.name,
                "trials": len(variant_results),
                "avg_quality_score": avg_quality,
                "avg_engagement_score": avg_engagement,
                "active": variant.active,
            }

        return stats

    def get_winner(self, test_name: str) -> Optional[str]:
        """
        Determine the winning variant based on results.

        Returns the variant_id with the highest average quality score,
        or None if not enough data.
        """
        stats = self.get_variant_stats(test_name)
        if not stats:
            return None

        # Need at least 10 trials per variant
        qualified = {
            vid: s for vid, s in stats.items()
            if s["trials"] >= 10
        }

        if not qualified:
            return None

        winner = max(qualified.items(), key=lambda x: x[1]["avg_quality_score"])
        return winner[0]

"""
Auto-Curator Service
====================
Automatically approve/deny content based on configurable rules and thresholds.

CUR-005: Auto-Curation Rules
- Analyzes content sentiment, quality, and brand safety
- Applies threshold-based rules to auto-approve or auto-reject
- Target: 40-60% auto-curated
- Performance: <5s per video

Features:
- Sentiment threshold filtering
- Quality score thresholds
- Brand safety checks
- Platform-specific rules
- Configurable approval/rejection rules
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
from loguru import logger


class CurationDecision(Enum):
    """Auto-curation decision types"""
    APPROVE = "approve"
    REJECT = "reject"
    MANUAL_REVIEW = "manual_review"


@dataclass
class CurationRule:
    """A curation rule with conditions and actions"""
    rule_id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    decision: CurationDecision
    priority: int = 0
    enabled: bool = True


@dataclass
class CurationResult:
    """Result of auto-curation analysis"""
    decision: CurationDecision
    confidence: float
    matched_rules: List[str]
    reasons: List[str]
    scores: Dict[str, float]
    processing_time_ms: float


class AutoCurator:
    """
    Auto-Curator Service

    Automatically curates content based on configurable rules.

    Usage:
        curator = AutoCurator()

        # Add rules
        curator.add_rule(CurationRule(
            rule_id="high_quality",
            name="High Quality Content",
            description="Auto-approve high quality content",
            conditions={
                "sentiment_score": {"min": 0.7},
                "quality_score": {"min": 0.8}
            },
            decision=CurationDecision.APPROVE,
            priority=10
        ))

        # Curate content
        result = curator.curate(content_analysis)
    """

    def __init__(self):
        """Initialize auto-curator with default rules"""
        self.rules: List[CurationRule] = []
        self._setup_default_rules()

        logger.info("🎯 Auto-Curator initialized")

    def _setup_default_rules(self) -> None:
        """Set up default curation rules"""

        # High quality auto-approve rules
        self.add_rule(CurationRule(
            rule_id="excellent_content",
            name="Excellent Content",
            description="Auto-approve excellent content (high sentiment + quality)",
            conditions={
                "sentiment_score": {"min": 0.75},
                "quality_score": {"min": 0.8},
                "brand_safety_score": {"min": 0.9}
            },
            decision=CurationDecision.APPROVE,
            priority=10
        ))

        self.add_rule(CurationRule(
            rule_id="good_viral_potential",
            name="Good Viral Potential",
            description="Auto-approve content with strong viral indicators",
            conditions={
                "viral_score": {"min": 0.7},
                "sentiment_score": {"min": 0.6},
                "quality_score": {"min": 0.6}
            },
            decision=CurationDecision.APPROVE,
            priority=8
        ))

        # Auto-reject rules
        self.add_rule(CurationRule(
            rule_id="poor_quality",
            name="Poor Quality",
            description="Auto-reject poor quality content",
            conditions={
                "quality_score": {"max": 0.3}
            },
            decision=CurationDecision.REJECT,
            priority=9
        ))

        self.add_rule(CurationRule(
            rule_id="negative_sentiment",
            name="Negative Sentiment",
            description="Auto-reject highly negative content",
            conditions={
                "sentiment_score": {"max": 0.2}
            },
            decision=CurationDecision.REJECT,
            priority=9
        ))

        self.add_rule(CurationRule(
            rule_id="brand_safety_violation",
            name="Brand Safety Violation",
            description="Auto-reject content that violates brand safety",
            conditions={
                "brand_safety_score": {"max": 0.5}
            },
            decision=CurationDecision.REJECT,
            priority=10
        ))

        # Manual review fallback
        self.add_rule(CurationRule(
            rule_id="manual_review_fallback",
            name="Manual Review Fallback",
            description="Send ambiguous content to manual review",
            conditions={},  # Matches everything
            decision=CurationDecision.MANUAL_REVIEW,
            priority=0
        ))

    def add_rule(self, rule: CurationRule) -> None:
        """
        Add a curation rule

        Args:
            rule: Curation rule to add
        """
        # Remove existing rule with same ID
        self.rules = [r for r in self.rules if r.rule_id != rule.rule_id]

        # Add new rule
        self.rules.append(rule)

        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

        logger.debug(f"Added curation rule: {rule.name} (priority: {rule.priority})")

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a curation rule

        Args:
            rule_id: ID of rule to remove

        Returns:
            True if removed, False if not found
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]

        removed = len(self.rules) < original_count
        if removed:
            logger.debug(f"Removed curation rule: {rule_id}")

        return removed

    def get_rule(self, rule_id: str) -> Optional[CurationRule]:
        """Get a rule by ID"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def list_rules(self) -> List[CurationRule]:
        """Get all rules (sorted by priority)"""
        return self.rules.copy()

    def evaluate_condition(
        self,
        condition_key: str,
        condition_value: Dict[str, Any],
        scores: Dict[str, float]
    ) -> bool:
        """
        Evaluate a single condition

        Args:
            condition_key: Score key (e.g., "sentiment_score")
            condition_value: Condition spec (e.g., {"min": 0.7, "max": 0.9})
            scores: Actual scores to check

        Returns:
            True if condition passes
        """
        if condition_key not in scores:
            return False

        actual_value = scores[condition_key]

        # Check min threshold
        if "min" in condition_value:
            if actual_value < condition_value["min"]:
                return False

        # Check max threshold
        if "max" in condition_value:
            if actual_value > condition_value["max"]:
                return False

        # Check equals
        if "equals" in condition_value:
            if actual_value != condition_value["equals"]:
                return False

        return True

    def evaluate_rule(self, rule: CurationRule, scores: Dict[str, float]) -> bool:
        """
        Evaluate if a rule matches the given scores

        Args:
            rule: Rule to evaluate
            scores: Content scores

        Returns:
            True if all conditions pass
        """
        if not rule.enabled:
            return False

        # Empty conditions = always match (fallback rule)
        if not rule.conditions:
            return True

        # All conditions must pass
        for condition_key, condition_value in rule.conditions.items():
            if not self.evaluate_condition(condition_key, condition_value, scores):
                return False

        return True

    def curate(
        self,
        content_analysis: Dict[str, Any],
        platform: Optional[str] = None
    ) -> CurationResult:
        """
        Curate content based on analysis

        Args:
            content_analysis: Content analysis with scores
            platform: Target platform (optional, for platform-specific rules)

        Returns:
            Curation result with decision, confidence, and reasoning
        """
        import time
        start_time = time.time()

        # Extract scores from analysis
        scores = {
            "sentiment_score": content_analysis.get("sentiment_score", 0.5),
            "quality_score": content_analysis.get("quality_score", 0.5),
            "viral_score": content_analysis.get("viral_score", 0.5),
            "brand_safety_score": content_analysis.get("brand_safety_score", 1.0),
            "engagement_prediction": content_analysis.get("engagement_prediction", 0.5)
        }

        # Apply rules in priority order
        matched_rules = []
        reasons = []
        decision = CurationDecision.MANUAL_REVIEW

        for rule in self.rules:
            if self.evaluate_rule(rule, scores):
                matched_rules.append(rule.rule_id)
                reasons.append(f"{rule.name}: {rule.description}")
                decision = rule.decision

                # First match wins (highest priority)
                break

        # Calculate confidence based on score distances from thresholds
        confidence = self._calculate_confidence(scores, matched_rules)

        processing_time_ms = (time.time() - start_time) * 1000

        result = CurationResult(
            decision=decision,
            confidence=confidence,
            matched_rules=matched_rules,
            reasons=reasons,
            scores=scores,
            processing_time_ms=processing_time_ms
        )

        logger.info(
            f"Curated content | Decision: {decision.value} | "
            f"Confidence: {confidence:.2f} | Time: {processing_time_ms:.1f}ms"
        )

        return result

    def _calculate_confidence(
        self,
        scores: Dict[str, float],
        matched_rules: List[str]
    ) -> float:
        """
        Calculate confidence in curation decision

        Higher confidence when scores are far from thresholds.
        Lower confidence when scores are near decision boundaries.

        Args:
            scores: Content scores
            matched_rules: Rules that matched

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not matched_rules:
            return 0.5  # Neutral confidence for fallback

        # Get the matched rule
        rule = self.get_rule(matched_rules[0])
        if not rule:
            return 0.5

        # Calculate distance from thresholds
        distances = []

        for condition_key, condition_value in rule.conditions.items():
            if condition_key not in scores:
                continue

            actual_value = scores[condition_key]

            if "min" in condition_value:
                threshold = condition_value["min"]
                distance = actual_value - threshold
                distances.append(abs(distance))

            if "max" in condition_value:
                threshold = condition_value["max"]
                distance = threshold - actual_value
                distances.append(abs(distance))

        if not distances:
            return 0.7  # Default confidence if no thresholds

        # Average distance = confidence
        # Map [0, 0.5] to [0.5, 1.0]
        avg_distance = sum(distances) / len(distances)
        confidence = 0.5 + (min(avg_distance, 0.5) / 0.5) * 0.5

        return round(confidence, 2)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get auto-curator statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "approve_rules": sum(1 for r in self.rules if r.decision == CurationDecision.APPROVE),
            "reject_rules": sum(1 for r in self.rules if r.decision == CurationDecision.REJECT),
            "manual_review_rules": sum(
                1 for r in self.rules if r.decision == CurationDecision.MANUAL_REVIEW
            )
        }


# Singleton instance
_auto_curator: Optional[AutoCurator] = None


def get_auto_curator() -> AutoCurator:
    """Get singleton auto-curator instance"""
    global _auto_curator
    if _auto_curator is None:
        _auto_curator = AutoCurator()
    return _auto_curator

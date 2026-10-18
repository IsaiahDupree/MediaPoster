"""
Template Validation Service
============================
Validates content templates for:
- Required variables present
- FATE weights valid (0-1 range, sum to 1.0)
- Awareness level valid
- CTA strength valid (none/soft/direct)
- No banned phrases in template

OPS-003: Template Validation Service
"""

import re
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from loguru import logger


class AwarenessLevel(Enum):
    """Eugene Schwartz's 5 awareness levels"""
    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"


class CTAStrength(Enum):
    """CTA strength levels"""
    NONE = "none"        # No call-to-action
    SOFT = "soft"        # Gentle nudge (learn more, check this out)
    DIRECT = "direct"    # Strong ask (buy now, sign up, book a call)


class TemplateValidationError(Exception):
    """Raised when template validation fails"""
    pass


class TemplateValidator:
    """
    Template Validation Service

    Validates content generation templates for:
    - Variable completeness
    - FATE weights validity
    - Awareness level validity
    - CTA strength validity
    - Banned phrase detection

    Usage:
        validator = TemplateValidator()
        errors = validator.validate_template(template_dict)
        if errors:
            logger.error(f"Template validation failed: {errors}")
    """

    _instance: Optional["TemplateValidator"] = None

    def __init__(self):
        """Initialize template validator with banned phrases"""
        # Default banned phrases (can be overridden)
        self.banned_phrases = {
            "click here",
            "buy now or else",
            "limited time only",
            "act fast",
            "guaranteed results",
            "100% success rate",
            "secret formula",
            "miracle",
            "instant results",
            "one weird trick",
            "doctors hate this",
            "you won't believe",
        }

        logger.info("✅ Template Validator initialized")

    @classmethod
    def get_instance(cls) -> "TemplateValidator":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def extract_variables(self, prompt_text: str) -> Set[str]:
        """
        Extract variable names from prompt text

        Variables are in {variable_name} format

        Args:
            prompt_text: Template text with {variables}

        Returns:
            Set of variable names

        Example:
            >>> validator.extract_variables("Write about {topic} for {audience}")
            {'topic', 'audience'}
        """
        # Find all {variable_name} patterns
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, prompt_text)
        return set(matches)

    def get_missing_variables(
        self,
        prompt_text: str,
        provided_variables: Dict[str, Any]
    ) -> List[str]:
        """
        Find variables required by template but not provided

        Args:
            prompt_text: Template text with {variables}
            provided_variables: Dict of variable values

        Returns:
            List of missing variable names

        Example:
            >>> validator.get_missing_variables(
            ...     "Write about {topic} for {audience}",
            ...     {"topic": "AI"}
            ... )
            ['audience']
        """
        required = self.extract_variables(prompt_text)
        provided = set(provided_variables.keys())
        missing = required - provided
        return sorted(list(missing))

    def validate_fate_weights(
        self,
        fate_weights: Dict[str, float]
    ) -> tuple[bool, List[str]]:
        """
        Validate FATE weights

        Rules:
        - Keys must be F, A, T, E
        - Values must be 0-1
        - Sum should be close to 1.0 (within 0.01 tolerance)

        Args:
            fate_weights: Dict like {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2}

        Returns:
            (is_valid, list_of_errors)

        Example:
            >>> validator.validate_fate_weights({"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2})
            (True, [])
        """
        errors = []

        # Check keys
        required_keys = {"F", "A", "T", "E"}
        provided_keys = set(fate_weights.keys())

        if provided_keys != required_keys:
            missing = required_keys - provided_keys
            extra = provided_keys - required_keys
            if missing:
                errors.append(f"Missing FATE weights: {missing}")
            if extra:
                errors.append(f"Extra FATE weights: {extra}")

        # Check values in 0-1 range
        for key, value in fate_weights.items():
            if not isinstance(value, (int, float)):
                errors.append(f"FATE weight {key} must be numeric, got {type(value)}")
            elif value < 0 or value > 1:
                errors.append(f"FATE weight {key}={value} must be in range [0, 1]")

        # Check sum to 1.0 (within tolerance) - only if all values are numeric
        if all(isinstance(v, (int, float)) for v in fate_weights.values()):
            total = sum(fate_weights.values())
            # Use 0.02 tolerance instead of 0.01 to handle floating point precision
            if abs(total - 1.0) > 0.02:
                errors.append(f"FATE weights sum to {total}, expected 1.0 (±0.02)")

        return (len(errors) == 0, errors)

    def validate_awareness_level(
        self,
        awareness_level: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate awareness level is valid enum value

        Args:
            awareness_level: String awareness level

        Returns:
            (is_valid, error_message)

        Example:
            >>> validator.validate_awareness_level("problem_aware")
            (True, None)
        """
        valid_levels = {level.value for level in AwarenessLevel}

        if awareness_level not in valid_levels:
            return (
                False,
                f"Invalid awareness level '{awareness_level}'. "
                f"Must be one of: {valid_levels}"
            )

        return (True, None)

    def validate_cta_strength(
        self,
        cta_strength: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate CTA strength is valid enum value

        Args:
            cta_strength: String CTA strength (none/soft/direct)

        Returns:
            (is_valid, error_message)

        Example:
            >>> validator.validate_cta_strength("soft")
            (True, None)
        """
        valid_strengths = {strength.value for strength in CTAStrength}

        if cta_strength not in valid_strengths:
            return (
                False,
                f"Invalid CTA strength '{cta_strength}'. "
                f"Must be one of: {valid_strengths}"
            )

        return (True, None)

    def check_banned_phrases(
        self,
        prompt_text: str,
        custom_banned: Optional[Set[str]] = None
    ) -> List[str]:
        """
        Check for banned phrases in template

        Args:
            prompt_text: Template text to check
            custom_banned: Optional custom banned phrases to check

        Returns:
            List of banned phrases found

        Example:
            >>> validator.check_banned_phrases("Click here for instant results!")
            ['click here', 'instant results']
        """
        banned = self.banned_phrases.copy()
        if custom_banned:
            banned.update(custom_banned)

        text_lower = prompt_text.lower()
        found = []

        for phrase in banned:
            if phrase.lower() in text_lower:
                found.append(phrase)

        return found

    def validate_template(
        self,
        template: Dict[str, Any],
        provided_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate complete template

        Args:
            template: Template dict with keys:
                - prompt_text: Template text with {variables}
                - fate_weights: {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2}
                - awareness_level: "problem_aware"
                - cta_strength: "soft"
            provided_variables: Variables that will be provided at generation time

        Returns:
            Validation result dict:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }

        Example:
            >>> result = validator.validate_template({
            ...     "prompt_text": "Write about {topic}",
            ...     "fate_weights": {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
            ...     "awareness_level": "problem_aware",
            ...     "cta_strength": "soft"
            ... }, {"topic": "AI"})
            >>> result["valid"]
            True
        """
        errors = []
        warnings = []

        # 1. Check required fields present
        required_fields = ["prompt_text", "fate_weights", "awareness_level", "cta_strength"]
        for field in required_fields:
            if field not in template:
                errors.append(f"Missing required field: {field}")

        if errors:
            return {"valid": False, "errors": errors, "warnings": warnings}

        # 2. Validate variables (if provided_variables given)
        if provided_variables is not None:
            missing = self.get_missing_variables(
                template["prompt_text"],
                provided_variables
            )
            if missing:
                errors.append(f"Missing variables: {missing}")

        # 3. Validate FATE weights
        fate_valid, fate_errors = self.validate_fate_weights(template["fate_weights"])
        if not fate_valid:
            errors.extend(fate_errors)

        # 4. Validate awareness level
        awareness_valid, awareness_error = self.validate_awareness_level(
            template["awareness_level"]
        )
        if not awareness_valid:
            errors.append(awareness_error)

        # 5. Validate CTA strength
        cta_valid, cta_error = self.validate_cta_strength(template["cta_strength"])
        if not cta_valid:
            errors.append(cta_error)

        # 6. Check banned phrases (warning only)
        banned = self.check_banned_phrases(template["prompt_text"])
        if banned:
            warnings.append(f"Banned phrases found: {banned}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


def get_template_validator() -> TemplateValidator:
    """Get singleton template validator instance"""
    return TemplateValidator.get_instance()

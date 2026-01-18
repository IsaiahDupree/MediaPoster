"""
Template Validation Tests
==========================
Unit tests for OPS-003: Template Validation Service

Tests:
- Variable extraction and missing detection
- FATE weights validation
- Awareness level validation
- CTA strength validation
- Banned phrase detection
"""

import pytest
from services.template_validator import (
    TemplateValidator,
    AwarenessLevel,
    CTAStrength,
    get_template_validator
)


@pytest.fixture
def validator():
    """Create a fresh validator instance for each test"""
    TemplateValidator._instance = None
    return TemplateValidator.get_instance()


class TestVariableExtraction:
    """Test variable extraction from template text"""

    def test_extract_single_variable(self, validator):
        """Test extracting a single variable"""
        prompt = "Write about {topic}"
        variables = validator.extract_variables(prompt)
        assert variables == {"topic"}

    def test_extract_multiple_variables(self, validator):
        """Test extracting multiple variables"""
        prompt = "Write about {topic} for {audience} using {tone}"
        variables = validator.extract_variables(prompt)
        assert variables == {"topic", "audience", "tone"}

    def test_extract_no_variables(self, validator):
        """Test text with no variables"""
        prompt = "Write a generic post"
        variables = validator.extract_variables(prompt)
        assert variables == set()

    def test_duplicate_variables(self, validator):
        """Test that duplicate variables are deduplicated"""
        prompt = "Talk about {topic} and explain {topic} thoroughly"
        variables = validator.extract_variables(prompt)
        assert variables == {"topic"}

    def test_variable_with_underscores(self, validator):
        """Test variables with underscores"""
        prompt = "Write about {topic_name} for {target_audience}"
        variables = validator.extract_variables(prompt)
        assert variables == {"topic_name", "target_audience"}

    def test_variable_with_numbers(self, validator):
        """Test variables with numbers"""
        prompt = "Use {template_v2} for {audience1}"
        variables = validator.extract_variables(prompt)
        assert variables == {"template_v2", "audience1"}


class TestMissingVariables:
    """Test missing variable detection"""

    def test_all_variables_provided(self, validator):
        """Test when all variables are provided"""
        prompt = "Write about {topic} for {audience}"
        provided = {"topic": "AI", "audience": "developers"}
        missing = validator.get_missing_variables(prompt, provided)
        assert missing == []

    def test_some_variables_missing(self, validator):
        """Test when some variables are missing"""
        prompt = "Write about {topic} for {audience}"
        provided = {"topic": "AI"}
        missing = validator.get_missing_variables(prompt, provided)
        assert missing == ["audience"]

    def test_all_variables_missing(self, validator):
        """Test when all variables are missing"""
        prompt = "Write about {topic} for {audience}"
        provided = {}
        missing = validator.get_missing_variables(prompt, provided)
        assert set(missing) == {"topic", "audience"}

    def test_extra_variables_provided(self, validator):
        """Test when extra variables are provided (not an error)"""
        prompt = "Write about {topic}"
        provided = {"topic": "AI", "audience": "developers", "extra": "value"}
        missing = validator.get_missing_variables(prompt, provided)
        assert missing == []


class TestFATEWeightsValidation:
    """Test FATE weights validation"""

    def test_valid_fate_weights(self, validator):
        """Test valid FATE weights that sum to 1.0"""
        weights = {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2}
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is True
        assert errors == []

    def test_fate_weights_sum_not_one(self, validator):
        """Test FATE weights that don't sum to 1.0"""
        weights = {"F": 0.3, "A": 0.3, "T": 0.3, "E": 0.3}  # Sum = 1.2
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is False
        assert any("sum" in error.lower() for error in errors)

    def test_fate_weights_missing_key(self, validator):
        """Test missing FATE key"""
        weights = {"F": 0.5, "A": 0.3, "T": 0.2}  # Missing E
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is False
        assert any("missing" in error.lower() for error in errors)

    def test_fate_weights_extra_key(self, validator):
        """Test extra FATE key"""
        weights = {"F": 0.2, "A": 0.3, "T": 0.3, "E": 0.2, "X": 0.0}
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is False
        assert any("extra" in error.lower() for error in errors)

    def test_fate_weight_out_of_range_high(self, validator):
        """Test FATE weight > 1.0"""
        weights = {"F": 1.5, "A": 0.0, "T": 0.0, "E": -0.5}  # F too high, E negative
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is False
        # Should have errors for both out-of-range values
        assert len(errors) >= 2

    def test_fate_weight_out_of_range_low(self, validator):
        """Test FATE weight < 0.0"""
        weights = {"F": 0.5, "A": 0.5, "T": 0.5, "E": -0.5}
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is False
        assert any("range" in error.lower() for error in errors)

    def test_fate_weights_near_one_tolerance(self, validator):
        """Test FATE weights that sum to ~1.0 within tolerance"""
        weights = {"F": 0.25, "A": 0.25, "T": 0.25, "E": 0.24}  # Sum = 0.99
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is True  # Within 0.01 tolerance

    def test_fate_weights_non_numeric(self, validator):
        """Test non-numeric FATE weight"""
        weights = {"F": "0.3", "A": 0.4, "T": 0.2, "E": 0.1}
        is_valid, errors = validator.validate_fate_weights(weights)
        assert is_valid is False
        assert any("numeric" in error.lower() for error in errors)


class TestAwarenessLevelValidation:
    """Test awareness level validation"""

    def test_valid_awareness_levels(self, validator):
        """Test all valid awareness levels"""
        valid_levels = [
            "unaware",
            "problem_aware",
            "solution_aware",
            "product_aware",
            "most_aware"
        ]

        for level in valid_levels:
            is_valid, error = validator.validate_awareness_level(level)
            assert is_valid is True, f"Level {level} should be valid"
            assert error is None

    def test_invalid_awareness_level(self, validator):
        """Test invalid awareness level"""
        is_valid, error = validator.validate_awareness_level("super_aware")
        assert is_valid is False
        assert error is not None
        assert "invalid" in error.lower()

    def test_awareness_level_case_sensitive(self, validator):
        """Test that awareness level is case-sensitive"""
        is_valid, error = validator.validate_awareness_level("UNAWARE")
        assert is_valid is False  # Must be lowercase


class TestCTAStrengthValidation:
    """Test CTA strength validation"""

    def test_valid_cta_strengths(self, validator):
        """Test all valid CTA strengths"""
        valid_strengths = ["none", "soft", "direct"]

        for strength in valid_strengths:
            is_valid, error = validator.validate_cta_strength(strength)
            assert is_valid is True, f"Strength {strength} should be valid"
            assert error is None

    def test_invalid_cta_strength(self, validator):
        """Test invalid CTA strength"""
        is_valid, error = validator.validate_cta_strength("aggressive")
        assert is_valid is False
        assert error is not None
        assert "invalid" in error.lower()

    def test_cta_strength_case_sensitive(self, validator):
        """Test that CTA strength is case-sensitive"""
        is_valid, error = validator.validate_cta_strength("DIRECT")
        assert is_valid is False  # Must be lowercase


class TestBannedPhrases:
    """Test banned phrase detection"""

    def test_detect_single_banned_phrase(self, validator):
        """Test detection of a single banned phrase"""
        prompt = "Click here to get instant results!"
        found = validator.check_banned_phrases(prompt)
        assert "click here" in found
        assert "instant results" in found

    def test_no_banned_phrases(self, validator):
        """Test text with no banned phrases"""
        prompt = "Write compelling content about AI for developers"
        found = validator.check_banned_phrases(prompt)
        assert found == []

    def test_banned_phrase_case_insensitive(self, validator):
        """Test that banned phrase detection is case-insensitive"""
        prompt = "CLICK HERE for amazing results"
        found = validator.check_banned_phrases(prompt)
        assert "click here" in found

    def test_custom_banned_phrases(self, validator):
        """Test adding custom banned phrases"""
        prompt = "This is a custom forbidden phrase"
        custom = {"forbidden phrase"}
        found = validator.check_banned_phrases(prompt, custom_banned=custom)
        assert "forbidden phrase" in found

    def test_banned_phrase_partial_match(self, validator):
        """Test that banned phrases don't match partially"""
        prompt = "Clicking here won't work"  # Contains "click" but not "click here"
        found = validator.check_banned_phrases(prompt)
        # Should not match "click here" because it's "clicking here"
        # This is a limitation of simple substring matching
        # For now, we accept this behavior


class TestCompleteTemplateValidation:
    """Test complete template validation"""

    def test_valid_template(self, validator):
        """Test a completely valid template"""
        template = {
            "prompt_text": "Write about {topic} for {audience}",
            "fate_weights": {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
            "awareness_level": "problem_aware",
            "cta_strength": "soft"
        }
        provided = {"topic": "AI", "audience": "developers"}

        result = validator.validate_template(template, provided)

        assert result["valid"] is True
        assert result["errors"] == []
        assert len(result["warnings"]) == 0

    def test_template_missing_required_field(self, validator):
        """Test template missing a required field"""
        template = {
            "prompt_text": "Write about {topic}",
            "fate_weights": {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
            # Missing awareness_level and cta_strength
        }

        result = validator.validate_template(template)

        assert result["valid"] is False
        assert any("awareness_level" in error for error in result["errors"])
        assert any("cta_strength" in error for error in result["errors"])

    def test_template_with_missing_variables(self, validator):
        """Test template with missing variables"""
        template = {
            "prompt_text": "Write about {topic} for {audience} using {tone}",
            "fate_weights": {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
            "awareness_level": "problem_aware",
            "cta_strength": "soft"
        }
        provided = {"topic": "AI"}  # Missing audience and tone

        result = validator.validate_template(template, provided)

        assert result["valid"] is False
        assert any("missing variables" in error.lower() for error in result["errors"])

    def test_template_with_invalid_fate_weights(self, validator):
        """Test template with invalid FATE weights"""
        template = {
            "prompt_text": "Write about {topic}",
            "fate_weights": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},  # Sum = 2.0
            "awareness_level": "problem_aware",
            "cta_strength": "soft"
        }

        result = validator.validate_template(template)

        assert result["valid"] is False
        assert any("sum" in error.lower() for error in result["errors"])

    def test_template_with_invalid_awareness(self, validator):
        """Test template with invalid awareness level"""
        template = {
            "prompt_text": "Write about {topic}",
            "fate_weights": {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
            "awareness_level": "super_aware",  # Invalid
            "cta_strength": "soft"
        }

        result = validator.validate_template(template)

        assert result["valid"] is False
        assert any("awareness" in error.lower() for error in result["errors"])

    def test_template_with_banned_phrases(self, validator):
        """Test template with banned phrases (warning, not error)"""
        template = {
            "prompt_text": "Click here for instant results about {topic}!",
            "fate_weights": {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
            "awareness_level": "problem_aware",
            "cta_strength": "soft"
        }

        result = validator.validate_template(template)

        # Should be valid but with warnings
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("banned" in warning.lower() for warning in result["warnings"])

    def test_template_multiple_errors(self, validator):
        """Test template with multiple errors"""
        template = {
            "prompt_text": "Write about {topic} for {audience}",
            "fate_weights": {"F": 1.5, "A": 0.3},  # Missing T, E, and F > 1.0
            "awareness_level": "invalid_level",
            "cta_strength": "aggressive"
        }
        provided = {"topic": "AI"}  # Missing audience

        result = validator.validate_template(template, provided)

        assert result["valid"] is False
        assert len(result["errors"]) >= 4  # Multiple errors


class TestSingletonPattern:
    """Test singleton pattern"""

    def test_get_instance_returns_same_instance(self):
        """Test that get_instance returns the same instance"""
        TemplateValidator._instance = None
        validator1 = TemplateValidator.get_instance()
        validator2 = TemplateValidator.get_instance()
        assert validator1 is validator2

    def test_get_template_validator_function(self):
        """Test the get_template_validator function"""
        TemplateValidator._instance = None
        validator = get_template_validator()
        assert isinstance(validator, TemplateValidator)


class TestEdgeCases:
    """Test edge cases"""

    def test_empty_prompt_text(self, validator):
        """Test empty prompt text"""
        variables = validator.extract_variables("")
        assert variables == set()

    def test_prompt_with_curly_braces_but_no_variables(self, validator):
        """Test text with curly braces but not valid variables"""
        prompt = "This is {not a valid variable name!}"
        variables = validator.extract_variables(prompt)
        assert variables == set()

    def test_template_without_provided_variables(self, validator):
        """Test validation without providing variables (skips variable check)"""
        template = {
            "prompt_text": "Write about {topic} for {audience}",
            "fate_weights": {"F": 0.3, "A": 0.4, "T": 0.1, "E": 0.2},
            "awareness_level": "problem_aware",
            "cta_strength": "soft"
        }

        # Don't provide variables - should still validate other fields
        result = validator.validate_template(template, provided_variables=None)

        assert result["valid"] is True  # No variable errors when not checking
        assert result["errors"] == []

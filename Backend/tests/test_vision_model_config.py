"""
Test Vision Model Configuration
Tests that the vision analysis model is properly configurable via ModelRegistry
"""
import pytest
import os
from unittest.mock import patch, MagicMock

# Test imports
from config.model_registry import ModelRegistry, TaskType, ModelConfig


class TestVisionModelConfiguration:
    """Test suite for configurable vision model"""
    
    def test_vision_analysis_task_exists(self):
        """VISION_ANALYSIS task type should exist in registry"""
        assert TaskType.VISION_ANALYSIS is not None
        assert TaskType.VISION_ANALYSIS.value == "vision_analysis"
    
    def test_default_vision_model_is_gpt4o_mini(self):
        """Default vision model should be gpt-4o-mini (cheaper)"""
        config = ModelRegistry.get_model_config(TaskType.VISION_ANALYSIS)
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.api_key_env == "OPENAI_API_KEY"
    
    def test_vision_model_has_correct_costs(self):
        """Vision model should have correct cost configuration"""
        config = ModelRegistry.get_model_config(TaskType.VISION_ANALYSIS)
        # GPT-4o-mini costs: $0.15 input, $0.60 output per MTok
        assert config.cost_input == 0.15
        assert config.cost_output == 0.60
    
    def test_environment_override_works(self):
        """Should be able to override vision model via environment variable"""
        with patch.dict(os.environ, {"VISION_ANALYSIS_MODEL": "openai:gpt-4o"}):
            config = ModelRegistry.get_model_config(TaskType.VISION_ANALYSIS)
            assert config.model == "gpt-4o"
    
    def test_environment_override_gemini(self):
        """Should be able to switch to Gemini via environment variable"""
        with patch.dict(os.environ, {"VISION_ANALYSIS_MODEL": "google:gemini-2.0-flash"}):
            config = ModelRegistry.get_model_config(TaskType.VISION_ANALYSIS)
            assert config.provider == "google"
            assert config.model == "gemini-2.0-flash"
    
    def test_all_task_types_have_configs(self):
        """All task types should have model configurations"""
        for task in TaskType:
            config = ModelRegistry.get_model_config(task)
            assert config is not None
            assert config.provider in ["openai", "groq", "anthropic", "google", "local"]
            assert config.model is not None
            assert config.api_key_env is not None


class TestVisionModelCostCalculation:
    """Test cost calculations for vision analysis"""
    
    def test_cost_per_image_gpt4o_mini(self):
        """Calculate approximate cost per image with GPT-4o-mini"""
        config = ModelRegistry.get_model_config(TaskType.VISION_ANALYSIS)
        
        # Typical image analysis: ~500 input tokens, ~2000 output tokens
        input_tokens = 500
        output_tokens = 2000
        
        input_cost = (input_tokens / 1_000_000) * config.cost_input
        output_cost = (output_tokens / 1_000_000) * config.cost_output
        total_cost = input_cost + output_cost
        
        # Should be very cheap: ~$0.0013 per image
        assert total_cost < 0.01  # Less than 1 cent per image
        print(f"Cost per image with {config.model}: ${total_cost:.6f}")
    
    def test_batch_500_videos_cost(self):
        """Calculate cost for analyzing 500 videos"""
        config = ModelRegistry.get_model_config(TaskType.VISION_ANALYSIS)
        
        # Per video estimate
        input_tokens = 500
        output_tokens = 2000
        
        cost_per_video = ((input_tokens / 1_000_000) * config.cost_input + 
                         (output_tokens / 1_000_000) * config.cost_output)
        
        batch_cost = cost_per_video * 500
        
        # Should be under $1 for 500 videos with gpt-4o-mini
        print(f"Cost for 500 videos with {config.model}: ${batch_cost:.2f}")
        assert batch_cost < 5.0  # Less than $5 for 500 videos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for ModelRegistry
"""
import os
import pytest
from config.model_registry import (
    ModelRegistry,
    ModelConfig,
    TaskType,
    get_transcription_config,
    get_analysis_config,
    get_vision_config
)


class TestModelRegistry:
    """Test ModelRegistry functionality"""
    
    def test_get_model_config_default(self):
        """Test getting default model configuration"""
        config = ModelRegistry.get_model_config(TaskType.TRANSCRIPTION)
        
        assert config is not None
        assert config.provider == "groq"
        assert config.model == "whisper-large-v3"
        assert config.api_key_env == "GROQ_API_KEY"
        assert config.cost_input == 0.0
        assert config.cost_output == 0.0
    
    def test_get_model_config_all_tasks(self):
        """Test that all tasks have configurations"""
        for task in TaskType:
            config = ModelRegistry.get_model_config(task)
            assert config is not None
            assert config.provider in ["openai", "groq", "anthropic", "google", "local"]
            assert config.model != ""
            assert config.api_key_env != ""
    
    def test_get_model_config_env_override(self, monkeypatch):
        """Test environment variable override"""
        # Set environment override
        monkeypatch.setenv("TRANSCRIPTION_MODEL", "openai:whisper-1")
        
        config = ModelRegistry.get_model_config(TaskType.TRANSCRIPTION)
        
        assert config.provider == "openai"
        assert config.model == "whisper-1"
        assert config.api_key_env == "OPENAI_API_KEY"
    
    def test_parse_env_config_valid(self):
        """Test parsing valid environment config"""
        config = ModelRegistry._parse_env_config(
            TaskType.CONTENT_ANALYSIS,
            "anthropic:claude-3-5-sonnet"
        )
        
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet"
        assert config.api_key_env == "ANTHROPIC_API_KEY"
    
    def test_parse_env_config_invalid_format(self):
        """Test parsing invalid environment config"""
        with pytest.raises(ValueError, match="Invalid format"):
            ModelRegistry._parse_env_config(
                TaskType.CONTENT_ANALYSIS,
                "invalid-format"
            )
    
    def test_get_api_key(self, monkeypatch):
        """Test getting API key from environment"""
        config = ModelConfig(
            provider="groq",
            model="whisper-large-v3",
            api_key_env="GROQ_API_KEY"
        )
        
        # Set API key in environment
        monkeypatch.setenv("GROQ_API_KEY", "test_key_123")
        
        api_key = ModelRegistry.get_api_key(config)
        assert api_key == "test_key_123"
    
    def test_get_api_key_missing(self):
        """Test getting API key when not set"""
        config = ModelConfig(
            provider="groq",
            model="whisper-large-v3",
            api_key_env="NONEXISTENT_KEY"
        )
        
        api_key = ModelRegistry.get_api_key(config)
        assert api_key is None
    
    def test_list_tasks(self):
        """Test listing all tasks"""
        tasks = ModelRegistry.list_tasks()
        
        assert len(tasks) > 0
        assert TaskType.TRANSCRIPTION in tasks
        assert TaskType.CONTENT_ANALYSIS in tasks
        assert TaskType.FRAME_ANALYSIS in tasks
    
    def test_get_task_summary(self):
        """Test getting task summary"""
        summary = ModelRegistry.get_task_summary()
        
        assert "AI Model Configuration:" in summary
        assert "transcription:" in summary
        assert "content_analysis:" in summary
        assert "groq" in summary or "openai" in summary
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        transcription_config = get_transcription_config()
        assert transcription_config.provider == "groq"
        assert transcription_config.model == "whisper-large-v3"
        
        analysis_config = get_analysis_config()
        assert analysis_config.provider == "groq"
        assert analysis_config.model == "llama-3.3-70b-versatile"
        
        vision_config = get_vision_config()
        assert vision_config.provider == "openai"
        assert vision_config.model == "gpt-4o-mini"


class TestModelConfig:
    """Test ModelConfig dataclass"""
    
    def test_model_config_creation(self):
        """Test creating ModelConfig"""
        config = ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
            cost_input=0.15,
            cost_output=0.60,
            max_tokens=1024,
            temperature=0.5
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.api_key_env == "OPENAI_API_KEY"
        assert config.cost_input == 0.15
        assert config.cost_output == 0.60
        assert config.max_tokens == 1024
        assert config.temperature == 0.5
    
    def test_model_config_defaults(self):
        """Test ModelConfig default values"""
        config = ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY"
        )
        
        assert config.cost_input == 0.0
        assert config.cost_output == 0.0
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
    
    def test_model_config_invalid_provider(self):
        """Test ModelConfig with invalid provider"""
        with pytest.raises(ValueError, match="Unknown provider"):
            ModelConfig(
                provider="invalid_provider",
                model="some-model",
                api_key_env="SOME_KEY"
            )


class TestTaskType:
    """Test TaskType enum"""
    
    def test_task_type_values(self):
        """Test TaskType enum values"""
        assert TaskType.TRANSCRIPTION.value == "transcription"
        assert TaskType.CONTENT_ANALYSIS.value == "content_analysis"
        assert TaskType.FRAME_ANALYSIS.value == "frame_analysis"
        assert TaskType.THUMBNAIL_GENERATION.value == "thumbnail_generation"
        assert TaskType.HASHTAG_GENERATION.value == "hashtag_generation"
    
    def test_task_type_iteration(self):
        """Test iterating over TaskType"""
        tasks = list(TaskType)
        assert len(tasks) >= 11  # At least 11 tasks defined
        assert TaskType.TRANSCRIPTION in tasks
        assert TaskType.EMBEDDINGS in tasks

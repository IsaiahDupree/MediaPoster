"""
Model Registry - Centralized AI model configuration
Provides unified model selection across all services
"""
import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict
from loguru import logger


class TaskType(str, Enum):
    """All AI tasks in the system"""
    TRANSCRIPTION = "transcription"
    CONTENT_ANALYSIS = "content_analysis"
    FRAME_ANALYSIS = "frame_analysis"
    THUMBNAIL_GENERATION = "thumbnail_generation"
    HASHTAG_GENERATION = "hashtag_generation"
    COMMENT_GENERATION = "comment_generation"
    DM_GENERATION = "dm_generation"
    SUMMARIZATION = "summarization"
    EMBEDDINGS = "embeddings"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    TOPIC_EXTRACTION = "topic_extraction"


@dataclass
class ModelConfig:
    """Configuration for a specific AI model"""
    provider: str  # "openai", "groq", "anthropic", "google"
    model: str
    api_key_env: str
    cost_input: float = 0.0  # per MTok
    cost_output: float = 0.0  # per MTok
    max_tokens: int = 4096
    temperature: float = 0.7
    
    def __post_init__(self):
        """Validate configuration"""
        if self.provider not in ["openai", "groq", "anthropic", "google", "local"]:
            raise ValueError(f"Unknown provider: {self.provider}")


class ModelRegistry:
    """
    Central registry for all AI models
    
    Usage:
        config = ModelRegistry.get_model_config(TaskType.TRANSCRIPTION)
        print(f"Using {config.provider}/{config.model}")
    
    Environment Override:
        TRANSCRIPTION_MODEL=groq:whisper-large-v3
        CONTENT_ANALYSIS_MODEL=anthropic:claude-3-5-sonnet
    """
    
    # Default model configurations per task
    MODELS: Dict[TaskType, ModelConfig] = {
        TaskType.TRANSCRIPTION: ModelConfig(
            provider="groq",
            model="whisper-large-v3",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0
        ),
        
        TaskType.CONTENT_ANALYSIS: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=2048,
            temperature=0.7
        ),
        
        TaskType.FRAME_ANALYSIS: ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
            cost_input=0.15,
            cost_output=0.60,
            max_tokens=1024,
            temperature=0.5
        ),
        
        TaskType.THUMBNAIL_GENERATION: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=512,
            temperature=0.8
        ),
        
        TaskType.HASHTAG_GENERATION: ModelConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=256,
            temperature=0.7
        ),
        
        TaskType.COMMENT_GENERATION: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=512,
            temperature=0.8
        ),
        
        TaskType.DM_GENERATION: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=512,
            temperature=0.8
        ),
        
        TaskType.SUMMARIZATION: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=1024,
            temperature=0.5
        ),
        
        TaskType.EMBEDDINGS: ModelConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key_env="OPENAI_API_KEY",
            cost_input=0.02,
            cost_output=0.0,
            max_tokens=8191
        ),
        
        TaskType.SENTIMENT_ANALYSIS: ModelConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=256,
            temperature=0.3
        ),
        
        TaskType.TOPIC_EXTRACTION: ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            cost_input=0.0,
            cost_output=0.0,
            max_tokens=512,
            temperature=0.5
        )
    }
    
    @classmethod
    def get_model_config(cls, task: TaskType) -> ModelConfig:
        """
        Get model configuration for a task
        
        Checks environment variable first for override:
        TRANSCRIPTION_MODEL=groq:whisper-large-v3
        
        Args:
            task: TaskType enum value
        
        Returns:
            ModelConfig for the task
        """
        # Check for environment override
        env_key = f"{task.value.upper()}_MODEL"
        env_value = os.getenv(env_key)
        
        if env_value:
            try:
                config = cls._parse_env_config(task, env_value)
                logger.info(f"Using environment override for {task.value}: {config.provider}/{config.model}")
                return config
            except Exception as e:
                logger.warning(f"Failed to parse {env_key}={env_value}: {e}, using default")
        
        # Return default from registry
        config = cls.MODELS.get(task)
        if not config:
            raise ValueError(f"No model configured for task: {task}")
        
        return config
    
    @classmethod
    def _parse_env_config(cls, task: TaskType, config_str: str) -> ModelConfig:
        """
        Parse model config from environment variable
        
        Format: "provider:model"
        Example: "openai:gpt-4o-mini" or "groq:llama-3.3-70b-versatile"
        
        Args:
            task: TaskType enum value
            config_str: Configuration string from environment
        
        Returns:
            ModelConfig parsed from string
        """
        if ":" not in config_str:
            raise ValueError(f"Invalid format: {config_str}. Expected 'provider:model'")
        
        provider, model = config_str.split(":", 1)
        provider = provider.lower()
        
        # Determine API key environment variable
        api_key_env = f"{provider.upper()}_API_KEY"
        
        # Get cost info from default config if available
        default_config = cls.MODELS.get(task)
        cost_input = default_config.cost_input if default_config else 0.0
        cost_output = default_config.cost_output if default_config else 0.0
        max_tokens = default_config.max_tokens if default_config else 4096
        temperature = default_config.temperature if default_config else 0.7
        
        return ModelConfig(
            provider=provider,
            model=model,
            api_key_env=api_key_env,
            cost_input=cost_input,
            cost_output=cost_output,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    @classmethod
    def get_api_key(cls, config: ModelConfig) -> Optional[str]:
        """
        Get API key for a model configuration
        
        Args:
            config: ModelConfig instance
        
        Returns:
            API key from environment or None
        """
        return os.getenv(config.api_key_env)
    
    @classmethod
    def list_tasks(cls) -> list:
        """List all available tasks"""
        return list(cls.MODELS.keys())
    
    @classmethod
    def get_task_summary(cls) -> str:
        """Get summary of all configured tasks"""
        lines = ["AI Model Configuration:"]
        for task, config in cls.MODELS.items():
            lines.append(f"  {task.value}: {config.provider}/{config.model}")
        return "\n".join(lines)


# Convenience functions
def get_transcription_config() -> ModelConfig:
    """Get transcription model configuration"""
    return ModelRegistry.get_model_config(TaskType.TRANSCRIPTION)


def get_analysis_config() -> ModelConfig:
    """Get content analysis model configuration"""
    return ModelRegistry.get_model_config(TaskType.CONTENT_ANALYSIS)


def get_vision_config() -> ModelConfig:
    """Get frame/vision analysis model configuration"""
    return ModelRegistry.get_model_config(TaskType.FRAME_ANALYSIS)

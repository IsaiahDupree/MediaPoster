"""
AI Model Configuration
Centralized configuration for AI model selection across different tasks and services
"""
import os
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class TranscriptionProvider(str, Enum):
    """Available transcription providers"""
    OPENAI = "openai"
    GROQ = "groq"
    DEEPGRAM = "deepgram"
    ASSEMBLYAI = "assemblyai"
    LOCAL = "local"


class AnalysisProvider(str, Enum):
    """Available analysis providers"""
    OPENAI = "openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    LOCAL = "local"


@dataclass
class ProviderConfig:
    """Configuration for a specific AI provider"""
    api_key_env: str
    base_url: str
    models: Dict[str, str]
    rate_limits: Optional[Dict[str, int]] = None
    cost_per_token: Optional[Dict[str, float]] = None


class AIModelConfig:
    """
    Centralized AI model configuration
    
    Usage:
        from config.ai_models import AIModelConfig
        
        # Get current transcription provider
        provider = AIModelConfig.get_transcription_provider()
        
        # Get model for specific task
        model = AIModelConfig.get_model_for_task("transcription", "batch_analysis")
    """
    
    # Default providers (can be overridden by environment variables)
    DEFAULT_TRANSCRIPTION_PROVIDER = TranscriptionProvider.GROQ
    DEFAULT_ANALYSIS_PROVIDER = AnalysisProvider.GROQ
    
    # Fallback providers (if primary fails)
    TRANSCRIPTION_FALLBACK = TranscriptionProvider.OPENAI
    ANALYSIS_FALLBACK = AnalysisProvider.ANTHROPIC
    
    # Provider configurations
    PROVIDERS: Dict[str, ProviderConfig] = {
        "openai": ProviderConfig(
            api_key_env="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
            models={
                "transcription": "whisper-1",
                "analysis": "gpt-4o",  # Best quality/cost ratio
                "analysis_best": "gpt-4-turbo-preview",  # Highest quality
                "analysis_fast": "gpt-4o-mini",  # Fast and cheap
                "analysis_budget": "gpt-3.5-turbo",  # Budget option
                "embeddings": "text-embedding-3-small",
                "vision": "gpt-4o"  # Multimodal
            },
            rate_limits={
                "transcription": 50,  # RPM
                "analysis": 500  # RPM
            },
            cost_per_token={
                "transcription": 0.006 / 60,  # $0.006 per minute
                "gpt-4o_input": 5.0 / 1_000_000,  # $5 per MTok
                "gpt-4o_output": 15.0 / 1_000_000,
                "gpt-4o-mini_input": 0.15 / 1_000_000,  # $0.15 per MTok
                "gpt-4o-mini_output": 0.60 / 1_000_000,
                "gpt-4-turbo_input": 10.0 / 1_000_000,  # $10 per MTok
                "gpt-4-turbo_output": 30.0 / 1_000_000,
                "gpt-3.5-turbo_input": 0.50 / 1_000_000,  # $0.50 per MTok
                "gpt-3.5-turbo_output": 1.50 / 1_000_000
            }
        ),
        "groq": ProviderConfig(
            api_key_env="GROQ_API_KEY",
            base_url="https://api.groq.com/openai/v1",
            models={
                "transcription": "whisper-large-v3",
                "analysis": "llama-3.1-70b-versatile",  # Best balance
                "analysis_best": "llama-3.1-405b-reasoning",  # Highest quality
                "analysis_fast": "llama-3.1-8b-instant",  # Fastest
                "analysis_budget": "mixtral-8x7b-32768"  # Good multilingual
            },
            rate_limits={
                "transcription": 20,  # RPM
                "analysis": 30  # RPM
            },
            cost_per_token={
                "transcription": 0.0,  # Currently free
                "analysis_input": 0.0,
                "analysis_output": 0.0
            }
        ),
        "anthropic": ProviderConfig(
            api_key_env="ANTHROPIC_API_KEY",
            base_url="https://api.anthropic.com/v1",
            models={
                "analysis": "claude-3-5-sonnet-20241022",  # Best reasoning
                "analysis_best": "claude-3-opus-20240229",  # Highest quality (expensive)
                "analysis_fast": "claude-3-haiku-20240307"  # Fast and cheap
            },
            rate_limits={
                "analysis": 50  # RPM
            },
            cost_per_token={
                "claude-3-5-sonnet_input": 3.0 / 1_000_000,  # $3 per MTok
                "claude-3-5-sonnet_output": 15.0 / 1_000_000,
                "claude-3-opus_input": 15.0 / 1_000_000,  # $15 per MTok
                "claude-3-opus_output": 75.0 / 1_000_000,
                "claude-3-haiku_input": 0.25 / 1_000_000,  # $0.25 per MTok
                "claude-3-haiku_output": 1.25 / 1_000_000
            }
        ),
        "google": ProviderConfig(
            api_key_env="GOOGLE_API_KEY",
            base_url="https://generativelanguage.googleapis.com/v1",
            models={
                "analysis": "gemini-1.5-flash",  # Best value, 1M context
                "analysis_best": "gemini-1.5-pro",  # Highest quality, 2M context
                "analysis_fast": "gemini-1.5-flash-8b"  # Fastest, cheapest
            },
            rate_limits={
                "analysis": 1000  # RPM
            },
            cost_per_token={
                "gemini-1.5-flash_input": 0.075 / 1_000_000,  # $0.075 per MTok (≤128K)
                "gemini-1.5-flash_output": 0.30 / 1_000_000,
                "gemini-1.5-flash_input_large": 0.15 / 1_000_000,  # >128K
                "gemini-1.5-flash_output_large": 0.60 / 1_000_000,
                "gemini-1.5-pro_input": 1.25 / 1_000_000,  # $1.25 per MTok (≤128K)
                "gemini-1.5-pro_output": 5.0 / 1_000_000,
                "gemini-1.5-pro_input_large": 2.50 / 1_000_000,  # >128K
                "gemini-1.5-pro_output_large": 10.0 / 1_000_000,
                "gemini-1.5-flash-8b_input": 0.0375 / 1_000_000,  # $0.0375 per MTok
                "gemini-1.5-flash-8b_output": 0.15 / 1_000_000
            }
        ),
        "deepgram": ProviderConfig(
            api_key_env="DEEPGRAM_API_KEY",
            base_url="https://api.deepgram.com/v1",
            models={
                "transcription": "nova-2",  # Best for real-time, streaming
                "transcription_whisper": "whisper-cloud",  # Hosted Whisper
                "transcription_base": "base"  # Budget option
            },
            rate_limits={
                "transcription": 1000  # RPM
            },
            cost_per_token={
                "nova-2": 0.0043 / 60,  # $0.0043 per minute
                "whisper-cloud": 0.0125 / 60,  # $0.0125 per minute
                "base": 0.0036 / 60  # $0.0036 per minute
            }
        ),
        "assemblyai": ProviderConfig(
            api_key_env="ASSEMBLYAI_API_KEY",
            base_url="https://api.assemblyai.com/v2",
            models={
                "transcription": "universal-1"  # Feature-rich transcription
            },
            rate_limits={
                "transcription": 100  # Concurrent requests
            },
            cost_per_token={
                "transcription": 0.00025  # $0.00025 per second = $0.015/min
            }
        ),
        "mistral": ProviderConfig(
            api_key_env="MISTRAL_API_KEY",
            base_url="https://api.mistral.ai/v1",
            models={
                "analysis": "mistral-large-latest",  # Best quality
                "analysis_fast": "mistral-small-latest"  # Budget option
            },
            rate_limits={
                "analysis": 60  # RPM
            },
            cost_per_token={
                "mistral-large_input": 2.0 / 1_000_000,  # $2 per MTok
                "mistral-large_output": 6.0 / 1_000_000,
                "mistral-small_input": 0.20 / 1_000_000,  # $0.20 per MTok
                "mistral-small_output": 0.60 / 1_000_000
            }
        ),
        "local": ProviderConfig(
            api_key_env="",
            base_url="http://localhost:11434",  # Ollama default
            models={
                "transcription": "whisper-large-v3",
                "analysis": "llama3.1:70b",
                "analysis_fast": "llama3.1:8b"
            },
            rate_limits=None,  # No limits for local
            cost_per_token={
                "transcription": 0.0,
                "analysis_input": 0.0,
                "analysis_output": 0.0
            }
        )
    }
    
    @classmethod
    def get_transcription_provider(cls) -> TranscriptionProvider:
        """Get configured transcription provider from environment or default"""
        provider = os.getenv("TRANSCRIPTION_PROVIDER", cls.DEFAULT_TRANSCRIPTION_PROVIDER.value)
        return TranscriptionProvider(provider)
    
    @classmethod
    def get_analysis_provider(cls) -> AnalysisProvider:
        """Get configured analysis provider from environment or default"""
        provider = os.getenv("ANALYSIS_PROVIDER", cls.DEFAULT_ANALYSIS_PROVIDER.value)
        return AnalysisProvider(provider)
    
    @classmethod
    def get_provider_config(cls, provider: str) -> ProviderConfig:
        """Get configuration for a specific provider"""
        return cls.PROVIDERS.get(provider)
    
    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        """Get API key for a provider from environment"""
        config = cls.get_provider_config(provider)
        if not config or not config.api_key_env:
            return None
        return os.getenv(config.api_key_env)
    
    @classmethod
    def get_model_for_task(cls, task_type: str, service_type: str = "default") -> tuple[str, str]:
        """
        Get provider and model for a specific task
        
        Args:
            task_type: "transcription" or "analysis"
            service_type: "batch_analysis", "live_streaming", "deep_analysis", etc.
        
        Returns:
            Tuple of (provider_name, model_name)
        """
        if task_type == "transcription":
            provider = cls._get_transcription_provider_for_service(service_type)
            config = cls.get_provider_config(provider.value)
            model = config.models.get("transcription")
            return provider.value, model
        
        elif task_type == "analysis":
            provider = cls._get_analysis_provider_for_service(service_type)
            config = cls.get_provider_config(provider.value)
            
            # Choose fast or regular model based on service type
            if service_type in ["quick_scoring", "batch_analysis"]:
                model = config.models.get("analysis_fast", config.models.get("analysis"))
            else:
                model = config.models.get("analysis")
            
            return provider.value, model
        
        raise ValueError(f"Unknown task type: {task_type}")
    
    @classmethod
    def _get_transcription_provider_for_service(cls, service_type: str) -> TranscriptionProvider:
        """Select transcription provider based on service requirements"""
        
        # High-priority/real-time tasks
        if service_type == "live_streaming":
            return TranscriptionProvider.DEEPGRAM  # Streaming support
        
        # Batch processing (cost-sensitive)
        elif service_type == "batch_analysis":
            return TranscriptionProvider.GROQ  # Free, fast
        
        # High-accuracy required
        elif service_type == "legal_transcript":
            return TranscriptionProvider.OPENAI  # Most reliable
        
        # Default
        return cls.get_transcription_provider()
    
    @classmethod
    def _get_analysis_provider_for_service(cls, service_type: str) -> AnalysisProvider:
        """Select analysis provider based on service requirements"""
        
        # Complex reasoning tasks
        if service_type == "deep_analysis":
            return AnalysisProvider.ANTHROPIC  # Claude best for reasoning
        
        # Large context (full video transcripts)
        elif service_type == "long_form_analysis":
            return AnalysisProvider.GOOGLE  # 1M token context
        
        # Fast, simple analysis
        elif service_type == "quick_scoring":
            return AnalysisProvider.GROQ  # Fastest, free
        
        # Batch processing
        elif service_type == "batch_analysis":
            return AnalysisProvider.GROQ  # Free
        
        # Default
        return cls.get_analysis_provider()
    
    @classmethod
    def estimate_cost(cls, provider: str, task_type: str, tokens: int) -> float:
        """
        Estimate cost for a task
        
        Args:
            provider: Provider name
            task_type: "transcription" or "analysis_input" or "analysis_output"
            tokens: Number of tokens (or seconds for transcription)
        
        Returns:
            Estimated cost in USD
        """
        config = cls.get_provider_config(provider)
        if not config or not config.cost_per_token:
            return 0.0
        
        cost_per_token = config.cost_per_token.get(task_type, 0.0)
        return tokens * cost_per_token


# Convenience functions
def get_transcription_config() -> tuple[str, str, str]:
    """Get transcription provider, model, and API key"""
    provider = AIModelConfig.get_transcription_provider()
    config = AIModelConfig.get_provider_config(provider.value)
    api_key = AIModelConfig.get_api_key(provider.value)
    model = config.models.get("transcription")
    return provider.value, model, api_key


def get_analysis_config(service_type: str = "default") -> tuple[str, str, str]:
    """Get analysis provider, model, and API key"""
    provider, model = AIModelConfig.get_model_for_task("analysis", service_type)
    api_key = AIModelConfig.get_api_key(provider)
    return provider, model, api_key

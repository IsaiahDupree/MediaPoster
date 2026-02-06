"""
AI Providers Module
====================
Configurable AI providers for various services.

Supports:
- OpenAI (GPT-4, GPT-4o-mini)
- Anthropic (Claude)

Configuration via environment variables:
    AI_PROVIDER=openai|anthropic
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-ant-...
    AI_MODEL=gpt-4o-mini

Usage:
    from services.ai_providers import get_ai_provider, AIProvider

    provider = get_ai_provider()
    response = await provider.analyze_transcript(transcript)

Note:
    MockAIProvider is available in tests/ only.
    Import from tests or services.ai_providers.mock_provider directly for testing.
"""

from .base import AIProvider, AIProviderConfig
from .openai_provider import OpenAIProvider

__all__ = [
    'AIProvider',
    'AIProviderConfig',
    'OpenAIProvider',
    'NotConfiguredError',
    'get_ai_provider',
]


class NotConfiguredError(RuntimeError):
    """Raised when a provider is requested but not configured."""
    pass


def get_ai_provider(provider_name: str = None) -> AIProvider:
    """
    Get configured AI provider based on environment or parameter.

    Args:
        provider_name: Override provider (openai, anthropic)

    Returns:
        Configured AIProvider instance

    Raises:
        NotConfiguredError: If the requested provider is not configured
    """
    import os

    provider = provider_name or os.getenv("AI_PROVIDER", "openai")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise NotConfiguredError(
                "OpenAI provider not configured: OPENAI_API_KEY environment variable is required"
            )
        return OpenAIProvider()
    elif provider == "mock":
        raise NotConfiguredError(
            "Mock AI provider is not allowed in production. "
            "Set AI_PROVIDER=openai and configure OPENAI_API_KEY."
        )
    else:
        raise NotConfiguredError(
            f"Unknown AI provider '{provider}'. Supported providers: openai"
        )

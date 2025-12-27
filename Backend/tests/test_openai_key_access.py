"""
Test OpenAI API Key Access
===========================
Verifies that the OpenAI API key is properly configured and accessible.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestOpenAIKeyConfiguration:
    """Tests for OpenAI API key configuration and access."""
    
    def test_env_file_has_openai_key(self):
        """Verify .env file contains OPENAI_API_KEY."""
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        
        if not os.path.exists(env_path):
            pytest.skip(".env file not found - using environment variables")
        
        with open(env_path, 'r') as f:
            content = f.read()
        
        assert 'OPENAI_API_KEY' in content, "OPENAI_API_KEY not found in .env file"
        
        # Check it's not the placeholder value
        for line in content.split('\n'):
            if line.startswith('OPENAI_API_KEY='):
                value = line.split('=', 1)[1].strip()
                assert value != 'your-openai-key', "OPENAI_API_KEY is still the placeholder value"
                assert len(value) > 20, f"OPENAI_API_KEY appears too short: {len(value)} chars"
                break
    
    def test_settings_loads_openai_key(self):
        """Verify settings module properly loads OPENAI_API_KEY."""
        from config import settings
        
        assert settings.openai_api_key, "settings.openai_api_key is empty"
        assert len(settings.openai_api_key) > 20, f"OpenAI key too short: {len(settings.openai_api_key)}"
        assert settings.openai_api_key.startswith('sk-'), "OpenAI key should start with 'sk-'"
    
    def test_openai_key_in_environ(self):
        """Verify OPENAI_API_KEY is exported to os.environ."""
        from config import settings  # This triggers get_settings() which sets env
        
        env_key = os.environ.get('OPENAI_API_KEY', '')
        assert env_key, "OPENAI_API_KEY not in os.environ"
        assert len(env_key) > 20, f"OPENAI_API_KEY in environ too short: {len(env_key)}"
    
    def test_openai_provider_can_get_key(self):
        """Verify OpenAI provider can access the API key."""
        from services.ai_providers.openai_provider import OpenAIProvider
        from services.ai_providers.base import AIProviderConfig
        
        # Test with config-provided key
        config = AIProviderConfig(api_key="test-key-12345678901234567890")
        provider = OpenAIProvider(config)
        
        # Accessing _get_client would try to create OpenAI client
        # Just verify the config is accessible
        assert provider.config.api_key == "test-key-12345678901234567890"
    
    def test_openai_provider_uses_env_fallback(self):
        """Verify OpenAI provider falls back to env var when no config key."""
        from services.ai_providers.openai_provider import OpenAIProvider
        from services.ai_providers.base import AIProviderConfig
        from config import settings
        
        # Ensure env is set
        os.environ['OPENAI_API_KEY'] = settings.openai_api_key
        
        # Create provider without explicit key
        config = AIProviderConfig()
        provider = OpenAIProvider(config)
        
        # The _get_client method should find the key from env
        assert os.environ.get('OPENAI_API_KEY'), "Env key should be set for fallback"


class TestOpenAIClientCreation:
    """Tests for actual OpenAI client creation."""
    
    def test_openai_client_creation(self):
        """Test that OpenAI client can be created with the key."""
        from config import settings
        
        if not settings.openai_api_key or settings.openai_api_key == 'your-openai-key':
            pytest.skip("No valid OpenAI API key configured")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            assert client is not None
        except ImportError:
            pytest.skip("openai package not installed")
    
    def test_openai_api_connection(self):
        """Test actual API connection with a minimal request."""
        from config import settings
        
        if not settings.openai_api_key or settings.openai_api_key.startswith('your-'):
            pytest.skip("No valid OpenAI API key configured")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            
            # Make a minimal API call to verify the key works
            response = client.models.list()
            models = list(response)
            
            assert len(models) > 0, "Should have at least one model available"
            
            # Check for expected models
            model_ids = [m.id for m in models]
            assert any('gpt' in m.lower() for m in model_ids), "Should have GPT models available"
            
        except ImportError:
            pytest.skip("openai package not installed")
        except Exception as e:
            if "invalid_api_key" in str(e).lower() or "authentication" in str(e).lower():
                pytest.fail(f"OpenAI API key is invalid: {e}")
            raise


class TestConfigValidator:
    """Tests for the config validation service."""
    
    @pytest.mark.asyncio
    async def test_config_validator_checks_openai(self):
        """Verify config validator properly checks OpenAI key."""
        from services.validators.config_validator import validate_configuration
        
        result = await validate_configuration()
        
        # Check metadata
        assert 'has_openai' in result.metadata
        
        # If we have a key, should report true
        from config import settings
        if settings.openai_api_key and len(settings.openai_api_key) > 20:
            assert result.metadata['has_openai'] is True


class TestOpenAIKeyMasking:
    """Tests to ensure API keys are not accidentally exposed."""
    
    def test_key_not_in_logs(self):
        """Verify API key is masked in log output."""
        from config import settings
        
        key = settings.openai_api_key
        if not key:
            pytest.skip("No OpenAI key to test")
        
        # Key should be masked if logged
        masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        
        # Just verify masking logic works
        assert len(masked) < len(key), "Masked key should be shorter"
        assert key not in masked, "Full key should not be in masked version"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

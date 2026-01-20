"""
Unit tests for AIClient
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from config.model_registry import ModelConfig, TaskType
from services.ai_client import AIClient, create_client_for_task


class TestAIClient:
    """Test AIClient functionality"""
    
    def test_init_openai_client(self, monkeypatch):
        """Test initializing OpenAI client"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")

        config = ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY"
        )

        with patch('openai.OpenAI') as mock_openai:
            client = AIClient(config)

            assert client.config == config
            mock_openai.assert_called_once_with(api_key="test_key")
    
    def test_init_groq_client(self, monkeypatch):
        """Test initializing Groq client"""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")

        config = ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY"
        )

        with patch('groq.Groq') as mock_groq:
            client = AIClient(config)

            assert client.config == config
            mock_groq.assert_called_once_with(api_key="test_key")
    
    def test_init_missing_api_key(self):
        """Test initializing without API key"""
        config = ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="NONEXISTENT_KEY"
        )
        
        with pytest.raises(ValueError, match="not found in environment"):
            AIClient(config)
    
    def test_init_unknown_provider(self, monkeypatch):
        """Test initializing with unknown provider"""
        monkeypatch.setenv("UNKNOWN_API_KEY", "test_key")

        # Should raise during validation in ModelConfig __post_init__
        with pytest.raises(ValueError, match="Unknown provider"):
            config = ModelConfig(
                provider="unknown",
                model="some-model",
                api_key_env="UNKNOWN_API_KEY"
            )
    
    def test_chat_completion_openai(self, monkeypatch):
        """Test chat completion with OpenAI"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")

        config = ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
            temperature=0.7,
            max_tokens=1024
        )

        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response

        with patch('openai.OpenAI', return_value=mock_client):
            client = AIClient(config)

            messages = [{"role": "user", "content": "Test message"}]
            response = client.chat_completion(messages)

            assert response == "Test response"
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["model"] == "gpt-4o-mini"
            assert call_args[1]["messages"] == messages
            assert call_args[1]["temperature"] == 0.7
            assert call_args[1]["max_tokens"] == 1024
    
    def test_chat_completion_groq(self, monkeypatch):
        """Test chat completion with Groq"""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")
        
        config = ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY"
        )
        
        # Mock Groq client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Groq response"
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('groq.Groq', return_value=mock_client):
            client = AIClient(config)

            messages = [{"role": "user", "content": "Test"}]
            response = client.chat_completion(messages)

            assert response == "Groq response"
    
    def test_chat_completion_custom_params(self, monkeypatch):
        """Test chat completion with custom parameters"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        
        config = ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
            temperature=0.7,
            max_tokens=1024
        )
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('openai.OpenAI', return_value=mock_client):
            client = AIClient(config)

            # Override temperature and max_tokens
            response = client.chat_completion(
                [{"role": "user", "content": "Test"}],
                temperature=0.5,
                max_tokens=512
            )

            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["temperature"] == 0.5
            assert call_args[1]["max_tokens"] == 512
    
    def test_transcribe_openai(self, monkeypatch, tmp_path):
        """Test transcription with OpenAI"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        
        config = ModelConfig(
            provider="openai",
            model="whisper-1",
            api_key_env="OPENAI_API_KEY"
        )
        
        # Create test audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test transcript"
        mock_response.language = "en"
        mock_response.duration = 10.5
        mock_response.segments = []
        mock_client.audio.transcriptions.create.return_value = mock_response
        
        with patch('openai.OpenAI', return_value=mock_client):
            client = AIClient(config)

            result = client.transcribe(str(audio_file))

            assert result["text"] == "Test transcript"
            assert result["language"] == "en"
            assert result["duration"] == 10.5
            assert result["segments"] == []
    
    def test_transcribe_groq(self, monkeypatch, tmp_path):
        """Test transcription with Groq"""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")
        
        config = ModelConfig(
            provider="groq",
            model="whisper-large-v3",
            api_key_env="GROQ_API_KEY"
        )
        
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Groq transcript"
        mock_response.language = "en"
        mock_response.duration = 15.0
        mock_client.audio.transcriptions.create.return_value = mock_response
        
        with patch('groq.Groq', return_value=mock_client):
            client = AIClient(config)

            result = client.transcribe(str(audio_file))

            assert result["text"] == "Groq transcript"
    
    def test_transcribe_unsupported_provider(self, monkeypatch):
        """Test transcription with unsupported provider"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")

        config = ModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet",
            api_key_env="ANTHROPIC_API_KEY"
        )

        # Mock anthropic module since it may not be installed
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic = MagicMock(return_value=MagicMock())
        sys.modules['anthropic'] = mock_anthropic_module

        try:
            client = AIClient(config)

            with pytest.raises(NotImplementedError, match="Transcription not supported"):
                client.transcribe("/fake/path.mp3")
        finally:
            # Clean up
            if 'anthropic' in sys.modules:
                del sys.modules['anthropic']
    
    def test_vision_analysis_openai(self, monkeypatch, tmp_path):
        """Test vision analysis with OpenAI"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        
        config = ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY"
        )
        
        # Create test image file
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b"fake image data")
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Image analysis result"
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('openai.OpenAI', return_value=mock_client):
            client = AIClient(config)

            result = client.vision_analysis(str(image_file), "Analyze this image")

            assert result == "Image analysis result"
    
    def test_embeddings_openai(self, monkeypatch):
        """Test embeddings with OpenAI"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        
        config = ModelConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key_env="OPENAI_API_KEY"
        )
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_item1 = MagicMock()
        mock_item1.embedding = [0.1, 0.2, 0.3]
        mock_item2 = MagicMock()
        mock_item2.embedding = [0.4, 0.5, 0.6]
        mock_response.data = [mock_item1, mock_item2]
        mock_client.embeddings.create.return_value = mock_response
        
        with patch('openai.OpenAI', return_value=mock_client):
            client = AIClient(config)

            texts = ["Text 1", "Text 2"]
            embeddings = client.embeddings(texts)

            assert len(embeddings) == 2
            assert embeddings[0] == [0.1, 0.2, 0.3]
            assert embeddings[1] == [0.4, 0.5, 0.6]
    
    def test_embeddings_unsupported_provider(self, monkeypatch):
        """Test embeddings with unsupported provider"""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")
        
        config = ModelConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY"
        )
        
        with patch('groq.Groq'):
            client = AIClient(config)

            with pytest.raises(NotImplementedError, match="Embeddings not supported"):
                client.embeddings(["Test"])


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_create_client_for_task(self, monkeypatch):
        """Test creating client for a task"""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")
        
        with patch('groq.Groq'):
            client = create_client_for_task(TaskType.CONTENT_ANALYSIS)

            assert client is not None
            assert client.config.provider == "groq"
            assert client.config.model == "llama-3.3-70b-versatile"

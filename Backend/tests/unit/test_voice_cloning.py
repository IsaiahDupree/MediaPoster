"""
Unit Tests: Voice Cloning System
=================================
Tests for voice profiles, generation, and Modal API integration.

Features tested:
- VC-002: Voice Reference Management
- VC-003: Voice Clone API Client
- VC-004: Voice Clone Database Schema
- VC-006: Voice Generation Service
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from services.voice.voice_profile_service import VoiceProfileService
from services.voice.generation_service import VoiceGenerationService
from services.voice.modal_voice_service import ModalVoiceService
from services.exceptions import ServiceError


# =====================================================
# Fixtures
# =====================================================

@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def user_id():
    """Test user ID"""
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def voice_profile_data():
    """Sample voice profile data"""
    return {
        "id": uuid4(),
        "user_id": UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Test Voice",
        "description": "Test voice profile",
        "reference_urls": ["https://example.com/audio.wav"],
        "embedding_id": "emb_123",
        "quality_score": 0.85,
        "default_speed": 1.0,
        "default_emotion": "neutral",
        "is_default": True,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


# =====================================================
# ModalVoiceService Tests
# =====================================================

class TestModalVoiceService:
    """Test Modal voice service API client"""

    def test_is_configured_with_env(self, monkeypatch):
        """Test configuration check with environment variables"""
        monkeypatch.setenv("MODAL_VOICE_ENDPOINT", "https://api.modal.com")
        monkeypatch.setenv("MODAL_VOICE_API_KEY", "test_key")

        service = ModalVoiceService()
        assert service.is_configured() is True

    def test_is_configured_without_env(self):
        """Test configuration check without environment variables"""
        service = ModalVoiceService()
        # Should still initialize but not be configured
        assert hasattr(service, 'endpoint_url')

    @pytest.mark.asyncio
    async def test_clone_voice_not_configured(self):
        """Test clone_voice raises error when not configured"""
        service = ModalVoiceService(endpoint_url=None, api_key=None)

        with pytest.raises(ValueError, match="not configured"):
            await service.clone_voice(
                text="Test text",
                voice_reference_url="https://example.com/audio.wav"
            )

    @pytest.mark.asyncio
    async def test_clone_voice_success(self):
        """Test successful voice cloning"""
        service = ModalVoiceService(
            endpoint_url="https://api.modal.com",
            api_key="test_key"
        )

        mock_response = {
            "audio_url": "https://example.com/generated.wav",
            "duration_seconds": 10.5,
            "processing_time_ms": 1500,
            "job_id": "job_123"
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.raise_for_status = Mock()
            mock_post.return_value.json = Mock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await service.clone_voice(
                text="Hello world",
                voice_reference_url="https://example.com/ref.wav",
                options={"speed": 1.2}
            )

            assert result["audio_url"] == mock_response["audio_url"]
            assert result["duration_seconds"] == 10.5


# =====================================================
# VoiceProfileService Tests
# =====================================================

class TestVoiceProfileService:
    """Test voice profile service"""

    @pytest.mark.asyncio
    async def test_create_profile_basic(self, mock_db, user_id):
        """Test creating basic voice profile"""
        service = VoiceProfileService(mock_db)

        # Mock the database response
        mock_db.add = Mock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        profile = await service.create_profile(
            user_id=user_id,
            name="My Voice",
            description="Test profile"
        )

        assert profile.name == "My Voice"
        assert profile.user_id == user_id
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_with_references(self, mock_db, user_id):
        """Test creating profile with reference audio"""
        service = VoiceProfileService(mock_db)
        service.modal_service = Mock()
        service.modal_service.is_configured = Mock(return_value=False)

        mock_db.add = Mock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        profile = await service.create_profile(
            user_id=user_id,
            name="My Voice",
            reference_urls=["https://example.com/audio.wav"]
        )

        assert profile.name == "My Voice"
        assert "https://example.com/audio.wav" in (profile.reference_urls or [])


# =====================================================
# VoiceGenerationService Tests
# =====================================================

class TestVoiceGenerationService:
    """Test voice generation service"""

    @pytest.mark.asyncio
    async def test_generate_audio_no_profile(self, mock_db, user_id):
        """Test generation fails when no default profile exists"""
        service = VoiceGenerationService(mock_db)

        # Mock no default profile found
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ServiceError, match="No default voice profile"):
            await service.generate_audio(
                user_id=user_id,
                text="Test text"
            )

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, mock_db, user_id):
        """Test getting usage statistics"""
        service = VoiceGenerationService(mock_db)

        # Mock database result
        mock_row = Mock()
        mock_row.total_generations = 10
        mock_row.completed_count = 8
        mock_row.failed_count = 2
        mock_row.total_audio_seconds = 120.5
        mock_row.total_cost_credits = 2.4

        mock_result = Mock()
        mock_result.one = Mock(return_value=mock_row)
        mock_db.execute = AsyncMock(return_value=mock_result)

        stats = await service.get_usage_stats(user_id)

        assert stats["total_generations"] == 10
        assert stats["completed_count"] == 8
        assert stats["failed_count"] == 2
        assert stats["total_audio_seconds"] == 120.5
        assert stats["total_cost_credits"] == 2.4


# =====================================================
# Integration Tests (with real DB - requires setup)
# =====================================================

@pytest.mark.integration
class TestVoiceCloningIntegration:
    """Integration tests for voice cloning (requires database)"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, db_session, user_id):
        """Test complete workflow: create profile → generate audio"""
        # This would require actual database setup
        # Skip for now if no test database configured
        pytest.skip("Requires test database")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Video Provider Tests
====================
Unit tests for video provider adapters.

Run tests:
    pytest tests/test_video_providers.py -v
"""

import asyncio
import pytest
from datetime import datetime
from uuid import uuid4
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# BASE CLASSES TESTS
# =============================================================================

class TestProviderEnums:
    """Test provider enum definitions."""
    
    def test_provider_name_values(self):
        """Test ProviderName enum values."""
        from services.video_providers.base import ProviderName
        
        assert ProviderName.SORA.value == "sora"
        assert ProviderName.RUNWAY.value == "runway"
        assert ProviderName.MOCK.value == "mock"
    
    def test_clip_status_values(self):
        """Test ClipStatus enum values."""
        from services.video_providers.base import ClipStatus
        
        assert ClipStatus.QUEUED.value == "queued"
        assert ClipStatus.RUNNING.value == "running"
        assert ClipStatus.SUCCEEDED.value == "succeeded"
        assert ClipStatus.FAILED.value == "failed"
    
    def test_asset_kind_values(self):
        """Test AssetKind enum values."""
        from services.video_providers.base import AssetKind
        
        assert AssetKind.VIDEO_MP4.value == "video_mp4"
        assert AssetKind.IMAGE_PNG.value == "image_png"


class TestProviderConfig:
    """Test ProviderConfig dataclass."""
    
    def test_default_config(self):
        """Test default ProviderConfig values."""
        from services.video_providers.base import ProviderConfig, ProviderName
        
        config = ProviderConfig()
        
        assert config.provider == ProviderName.SORA
        assert config.model == "sora-2"
        assert config.default_size == "1280x720"
        assert config.default_seconds == 8
        assert config.timeout == 300
    
    def test_custom_config(self):
        """Test custom ProviderConfig."""
        from services.video_providers.base import ProviderConfig, ProviderName
        
        config = ProviderConfig(
            provider=ProviderName.MOCK,
            model="sora-2-pro",
            default_seconds=12
        )
        
        assert config.provider == ProviderName.MOCK
        assert config.model == "sora-2-pro"
        assert config.default_seconds == 12


class TestCreateClipInput:
    """Test CreateClipInput dataclass."""
    
    def test_creation(self):
        """Test CreateClipInput creation."""
        from services.video_providers.base import CreateClipInput
        
        input = CreateClipInput(
            clip_id="test-123",
            prompt="A cat playing piano",
            seconds=8,
            model="sora-2"
        )
        
        assert input.clip_id == "test-123"
        assert input.prompt == "A cat playing piano"
        assert input.seconds == 8
    
    def test_to_dict(self):
        """Test CreateClipInput serialization."""
        from services.video_providers.base import CreateClipInput
        
        input = CreateClipInput(
            clip_id="test",
            prompt="Test prompt",
            seconds=12,
            size="720x1280"
        )
        
        data = input.to_dict()
        
        assert data["clip_id"] == "test"
        assert data["prompt"] == "Test prompt"
        assert data["seconds"] == 12
        assert data["size"] == "720x1280"
    
    def test_with_references(self):
        """Test CreateClipInput with references."""
        from services.video_providers.base import CreateClipInput, ProviderReference
        
        input = CreateClipInput(
            clip_id="test",
            prompt="Test",
            references=[
                ProviderReference(type="image", url="https://example.com/img.png", weight=0.8)
            ]
        )
        
        assert len(input.references) == 1
        assert input.references[0].type == "image"


class TestProviderGeneration:
    """Test ProviderGeneration dataclass."""
    
    def test_creation(self):
        """Test ProviderGeneration creation."""
        from services.video_providers.base import ProviderGeneration, ProviderName, ClipStatus
        
        gen = ProviderGeneration(
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipStatus.QUEUED
        )
        
        assert gen.provider == ProviderName.SORA
        assert gen.provider_generation_id == "gen_123"
        assert gen.status == ClipStatus.QUEUED
    
    def test_is_complete(self):
        """Test is_complete property."""
        from services.video_providers.base import ProviderGeneration, ProviderName, ClipStatus
        
        # Not complete
        gen = ProviderGeneration(
            provider=ProviderName.MOCK,
            provider_generation_id="test",
            status=ClipStatus.RUNNING
        )
        assert gen.is_complete is False
        
        # Complete (succeeded)
        gen.status = ClipStatus.SUCCEEDED
        assert gen.is_complete is True
        
        # Complete (failed)
        gen.status = ClipStatus.FAILED
        assert gen.is_complete is True
    
    def test_is_success(self):
        """Test is_success property."""
        from services.video_providers.base import ProviderGeneration, ProviderName, ClipStatus
        
        gen = ProviderGeneration(
            provider=ProviderName.MOCK,
            provider_generation_id="test",
            status=ClipStatus.RUNNING
        )
        assert gen.is_success is False
        
        gen.status = ClipStatus.SUCCEEDED
        assert gen.is_success is True
        
        gen.status = ClipStatus.FAILED
        assert gen.is_success is False
    
    def test_get_video_url(self):
        """Test get_video_url method."""
        from services.video_providers.base import (
            ProviderGeneration, ProviderName, ClipStatus, AssetOutput, AssetKind
        )
        
        gen = ProviderGeneration(
            provider=ProviderName.MOCK,
            provider_generation_id="test",
            status=ClipStatus.SUCCEEDED,
            download_url="https://example.com/video.mp4"
        )
        
        assert gen.get_video_url() == "https://example.com/video.mp4"
        
        # Test with outputs list
        gen2 = ProviderGeneration(
            provider=ProviderName.MOCK,
            provider_generation_id="test2",
            status=ClipStatus.SUCCEEDED,
            outputs=[
                AssetOutput(kind=AssetKind.VIDEO_MP4, url="https://example.com/from_outputs.mp4")
            ]
        )
        
        assert gen2.get_video_url() == "https://example.com/from_outputs.mp4"
    
    def test_to_dict(self):
        """Test ProviderGeneration serialization."""
        from services.video_providers.base import ProviderGeneration, ProviderName, ClipStatus
        
        gen = ProviderGeneration(
            provider=ProviderName.SORA,
            provider_generation_id="gen_abc",
            status=ClipStatus.SUCCEEDED,
            prompt="Test prompt",
            model="sora-2",
            seconds=8
        )
        
        data = gen.to_dict()
        
        assert data["provider"] == "sora"
        assert data["provider_generation_id"] == "gen_abc"
        assert data["status"] == "succeeded"
        assert data["prompt"] == "Test prompt"


# =============================================================================
# MOCK PROVIDER TESTS
# =============================================================================

class TestMockProvider:
    """Test MockVideoProvider."""
    
    def test_provider_name(self):
        """Test mock provider name."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import ProviderName
        
        provider = MockVideoProvider()
        assert provider.name == ProviderName.MOCK
    
    @pytest.mark.asyncio
    async def test_create_clip(self):
        """Test create_clip returns generation."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import CreateClipInput, ClipStatus
        
        provider = MockVideoProvider(simulate_delay=0)
        
        input = CreateClipInput(
            clip_id="test-clip",
            prompt="A sunset over mountains",
            seconds=8,
            model="sora-2"
        )
        
        gen = await provider.create_clip(input)
        
        assert gen.provider_generation_id.startswith("mock_gen_")
        assert gen.status == ClipStatus.QUEUED
        assert gen.prompt == "A sunset over mountains"
        assert gen.seconds == 8
    
    @pytest.mark.asyncio
    async def test_get_generation_progresses(self):
        """Test get_generation progresses through steps."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import CreateClipInput, ClipStatus
        
        provider = MockVideoProvider(simulate_delay=0, processing_steps=3)
        
        input = CreateClipInput(clip_id="test", prompt="Test", seconds=4)
        gen = await provider.create_clip(input)
        gen_id = gen.provider_generation_id
        
        # First poll - running
        gen = await provider.get_generation(gen_id)
        assert gen.status == ClipStatus.RUNNING
        
        # Second poll - still running
        gen = await provider.get_generation(gen_id)
        assert gen.status == ClipStatus.RUNNING
        
        # Third poll - succeeded
        gen = await provider.get_generation(gen_id)
        assert gen.status == ClipStatus.SUCCEEDED
        assert gen.download_url is not None
    
    @pytest.mark.asyncio
    async def test_wait_for_completion(self):
        """Test wait_for_completion returns completed generation."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import CreateClipInput, ClipStatus
        
        provider = MockVideoProvider(simulate_delay=0, processing_steps=2)
        
        input = CreateClipInput(clip_id="test", prompt="Test", seconds=8)
        gen = await provider.create_clip(input)
        
        completed = await provider.wait_for_completion(
            gen.provider_generation_id,
            poll_interval=0,
            timeout=5.0
        )
        
        assert completed.status == ClipStatus.SUCCEEDED
        assert completed.is_complete is True
    
    @pytest.mark.asyncio
    async def test_remix_clip(self):
        """Test remix_clip creates new generation."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import CreateClipInput, RemixClipInput, ClipStatus
        
        provider = MockVideoProvider(simulate_delay=0)
        
        # Create original
        input = CreateClipInput(clip_id="orig", prompt="Original", seconds=8)
        orig = await provider.create_clip(input)
        
        # Remix
        remix_input = RemixClipInput(
            source_generation_id=orig.provider_generation_id,
            prompt_delta="Add more color"
        )
        remix = await provider.remix_clip(remix_input)
        
        assert remix.provider_generation_id.startswith("mock_remix_")
        assert remix.status == ClipStatus.QUEUED
        assert remix.prompt == "Add more color"
    
    @pytest.mark.asyncio
    async def test_download_content(self):
        """Test download_content returns bytes."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import CreateClipInput, ClipStatus
        
        provider = MockVideoProvider(simulate_delay=0, processing_steps=1)
        
        input = CreateClipInput(clip_id="test", prompt="Test", seconds=4)
        gen = await provider.create_clip(input)
        
        # Complete generation
        completed = await provider.wait_for_completion(gen.provider_generation_id)
        
        content = await provider.download_content(completed)
        
        assert isinstance(content, bytes)
        assert len(content) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check returns status."""
        from services.video_providers.mock_provider import MockVideoProvider
        
        provider = MockVideoProvider()
        
        health = await provider.health_check()
        
        assert health["provider"] == "mock"
        assert health["status"] == "available"
    
    @pytest.mark.asyncio
    async def test_failure_simulation(self):
        """Test simulated failures."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import CreateClipInput, ClipStatus
        
        # 100% failure rate
        provider = MockVideoProvider(simulate_delay=0, failure_rate=1.0)
        
        input = CreateClipInput(clip_id="test", prompt="Test", seconds=4)
        gen = await provider.create_clip(input)
        
        assert gen.status == ClipStatus.FAILED
        assert gen.error is not None
    
    def test_reset(self):
        """Test reset clears state."""
        from services.video_providers.mock_provider import MockVideoProvider
        
        provider = MockVideoProvider()
        provider._generations["test"] = "dummy"
        provider._generation_progress["test"] = 1
        
        provider.reset()
        
        assert len(provider._generations) == 0
        assert len(provider._generation_progress) == 0


# =============================================================================
# SORA PROVIDER TESTS
# =============================================================================

class TestSoraProvider:
    """Test SoraProvider (without actual API calls)."""
    
    def test_provider_name(self):
        """Test Sora provider name."""
        from services.video_providers.sora_provider import SoraProvider
        from services.video_providers.base import ProviderName
        
        provider = SoraProvider()
        assert provider.name == ProviderName.SORA
    
    def test_validate_model(self):
        """Test model validation."""
        from services.video_providers.sora_provider import SoraProvider
        
        provider = SoraProvider()
        
        assert provider._validate_model("sora-2") == "sora-2"
        assert provider._validate_model("sora-2-pro") == "sora-2-pro"
        assert provider._validate_model("invalid") == "sora-2"  # Falls back
    
    def test_validate_size(self):
        """Test size validation."""
        from services.video_providers.sora_provider import SoraProvider
        
        provider = SoraProvider()
        
        assert provider._validate_size("1280x720") == "1280x720"
        assert provider._validate_size("720x1280") == "720x1280"
        assert provider._validate_size("invalid") == "1280x720"  # Falls back
    
    def test_validate_seconds(self):
        """Test seconds validation."""
        from services.video_providers.sora_provider import SoraProvider
        
        provider = SoraProvider()
        
        assert provider._validate_seconds(4) == 4
        assert provider._validate_seconds(8) == 8
        assert provider._validate_seconds(12) == 12
        assert provider._validate_seconds(3) == 4  # Rounds up
        assert provider._validate_seconds(7) == 8  # Rounds
        assert provider._validate_seconds(15) == 12  # Caps
    
    def test_parse_status(self):
        """Test status parsing."""
        from services.video_providers.sora_provider import SoraProvider
        from services.video_providers.base import ClipStatus
        
        provider = SoraProvider()
        
        assert provider._parse_status("queued") == ClipStatus.QUEUED
        assert provider._parse_status("in_progress") == ClipStatus.RUNNING
        assert provider._parse_status("processing") == ClipStatus.RUNNING
        assert provider._parse_status("completed") == ClipStatus.SUCCEEDED
        assert provider._parse_status("failed") == ClipStatus.FAILED
    
    def test_parse_generation_response(self):
        """Test response parsing."""
        from services.video_providers.sora_provider import SoraProvider
        from services.video_providers.base import ClipStatus
        
        provider = SoraProvider()
        
        # Minimal response
        data = {
            "id": "video_123",
            "status": "completed",
            "download_url": "https://example.com/video.mp4"
        }
        
        gen = provider._parse_generation_response(
            data,
            fallback_prompt="Test prompt",
            fallback_model="sora-2",
            fallback_size="1280x720",
            fallback_seconds=8
        )
        
        assert gen.provider_generation_id == "video_123"
        assert gen.status == ClipStatus.SUCCEEDED
        assert gen.download_url == "https://example.com/video.mp4"
        assert gen.prompt == "Test prompt"
    
    def test_parse_generation_response_with_assets(self):
        """Test response parsing with assets structure."""
        from services.video_providers.sora_provider import SoraProvider
        from services.video_providers.base import ClipStatus
        
        provider = SoraProvider()
        
        # Response with assets structure
        data = {
            "id": "video_456",
            "status": "completed",
            "assets": {
                "video": {"download_url": "https://example.com/v.mp4"},
                "thumbnail": {"url": "https://example.com/thumb.jpg"}
            }
        }
        
        gen = provider._parse_generation_response(data)
        
        assert gen.download_url == "https://example.com/v.mp4"
        assert gen.thumbnail_url == "https://example.com/thumb.jpg"
    
    def test_parse_generation_response_with_error(self):
        """Test response parsing with error."""
        from services.video_providers.sora_provider import SoraProvider
        from services.video_providers.base import ClipStatus
        
        provider = SoraProvider()
        
        data = {
            "id": "video_err",
            "status": "failed",
            "error": {
                "code": "content_policy",
                "message": "Content policy violation"
            }
        }
        
        gen = provider._parse_generation_response(data)
        
        assert gen.status == ClipStatus.FAILED
        assert gen.error is not None
        assert gen.error.code == "content_policy"
        assert "policy" in gen.error.message.lower()


# =============================================================================
# FACTORY TESTS
# =============================================================================

class TestProviderFactory:
    """Test get_video_provider factory."""
    
    def test_get_mock_provider(self):
        """Test getting mock provider."""
        from services.video_providers import get_video_provider, ProviderName
        from services.video_providers.mock_provider import MockVideoProvider
        
        provider = get_video_provider(ProviderName.MOCK)
        
        assert isinstance(provider, MockVideoProvider)
        assert provider.name == ProviderName.MOCK
    
    def test_get_sora_provider(self):
        """Test getting Sora provider."""
        from services.video_providers import get_video_provider, ProviderName
        from services.video_providers.sora_provider import SoraProvider
        
        provider = get_video_provider(ProviderName.SORA)
        
        assert isinstance(provider, SoraProvider)
        assert provider.name == ProviderName.SORA
    
    def test_runway_not_implemented(self):
        """Test Runway raises NotImplementedError."""
        from services.video_providers import get_video_provider, ProviderName
        
        with pytest.raises(NotImplementedError):
            get_video_provider(ProviderName.RUNWAY)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestProviderIntegration:
    """Integration tests for provider workflow."""
    
    @pytest.mark.asyncio
    async def test_full_generation_workflow(self):
        """Test complete generation workflow with mock."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import CreateClipInput, ClipStatus
        
        provider = MockVideoProvider(simulate_delay=0, processing_steps=2)
        
        # 1. Create clip
        input = CreateClipInput(
            clip_id="workflow-test",
            prompt="A beautiful landscape with mountains",
            seconds=8,
            model="sora-2",
            size="1280x720"
        )
        
        gen = await provider.create_clip(input)
        assert gen.status == ClipStatus.QUEUED
        gen_id = gen.provider_generation_id
        
        # 2. Wait for completion
        completed = await provider.wait_for_completion(gen_id, poll_interval=0)
        assert completed.status == ClipStatus.SUCCEEDED
        assert completed.download_url is not None
        
        # 3. Download content
        content = await provider.download_content(completed)
        assert len(content) > 0
    
    @pytest.mark.asyncio
    async def test_remix_workflow(self):
        """Test remix workflow with mock."""
        from services.video_providers.mock_provider import MockVideoProvider
        from services.video_providers.base import (
            CreateClipInput, RemixClipInput, ClipStatus
        )
        
        provider = MockVideoProvider(simulate_delay=0, processing_steps=1)
        
        # 1. Create original
        orig_input = CreateClipInput(
            clip_id="original",
            prompt="A person walking",
            seconds=8
        )
        orig = await provider.create_clip(orig_input)
        orig_complete = await provider.wait_for_completion(orig.provider_generation_id)
        
        # 2. Remix
        remix_input = RemixClipInput(
            source_generation_id=orig_complete.provider_generation_id,
            prompt_delta="Add sunset lighting"
        )
        remix = await provider.remix_clip(remix_input)
        
        # 3. Complete remix
        remix_complete = await provider.wait_for_completion(remix.provider_generation_id)
        
        assert remix_complete.status == ClipStatus.SUCCEEDED
        assert remix_complete.prompt == "Add sunset lighting"


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

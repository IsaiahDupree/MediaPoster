"""
Unit Tests for Reply Suggestions Service
=========================================
Tests for INBOX-004: AI Reply Suggestions
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from services.reply_suggestions import (
    ReplySuggestionsService,
    MessageType,
    SentimentType,
    ReplySuggestion
)


class TestReplySuggestionsCore:
    """Test core reply suggestions functionality"""

    @pytest.fixture
    def service(self):
        """Create reply suggestions service instance"""
        # Reset singleton
        ReplySuggestionsService._instance = None
        return ReplySuggestionsService.get_instance()

    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service is not None
        assert service.ai_client is not None
        assert service.brand_voice is not None
        assert "tone" in service.brand_voice

    def test_singleton_pattern(self, service):
        """Test singleton pattern enforced"""
        service2 = ReplySuggestionsService.get_instance()
        assert service is service2

    @pytest.mark.asyncio
    async def test_sentiment_classification_positive(self, service):
        """Test positive sentiment classification"""
        sentiment = await service._classify_sentiment("Love this video! Amazing content!")
        assert sentiment == SentimentType.POSITIVE

    @pytest.mark.asyncio
    async def test_sentiment_classification_negative(self, service):
        """Test negative sentiment classification"""
        sentiment = await service._classify_sentiment("This is terrible and disappointing")
        assert sentiment == SentimentType.NEGATIVE

    @pytest.mark.asyncio
    async def test_sentiment_classification_question(self, service):
        """Test question detection"""
        sentiment = await service._classify_sentiment("How do I do this?")
        assert sentiment == SentimentType.QUESTION

    @pytest.mark.asyncio
    async def test_sentiment_classification_neutral(self, service):
        """Test neutral sentiment classification"""
        sentiment = await service._classify_sentiment("Noted.")
        assert sentiment == SentimentType.NEUTRAL


class TestContextBuilding:
    """Test context string building"""

    @pytest.fixture
    def service(self):
        ReplySuggestionsService._instance = None
        return ReplySuggestionsService.get_instance()

    def test_build_context_no_context(self, service):
        """Test context building with no context"""
        context_str = service._build_context_string(None)
        assert "No additional context" in context_str

    def test_build_context_with_post_title(self, service):
        """Test context building with post title"""
        context = {"post_title": "5 Tips for Productivity"}
        context_str = service._build_context_string(context)
        assert "5 Tips for Productivity" in context_str

    def test_build_context_with_multiple_fields(self, service):
        """Test context building with multiple fields"""
        context = {
            "post_title": "Product Launch",
            "user_name": "@testuser",
            "post_description": "New feature announcement"
        }
        context_str = service._build_context_string(context)
        assert "Product Launch" in context_str
        assert "@testuser" in context_str
        assert "New feature announcement" in context_str


class TestLinkDetection:
    """Test link detection in replies"""

    @pytest.fixture
    def service(self):
        ReplySuggestionsService._instance = None
        return ReplySuggestionsService.get_instance()

    def test_detect_http_link(self, service):
        """Test HTTP link detection"""
        text = "Check out http://example.com for more info"
        assert service._contains_link(text) is True

    def test_detect_https_link(self, service):
        """Test HTTPS link detection"""
        text = "Visit https://example.com"
        assert service._contains_link(text) is True

    def test_detect_www_link(self, service):
        """Test www link detection"""
        text = "Go to www.example.com"
        assert service._contains_link(text) is True

    def test_detect_link_in_bio(self, service):
        """Test 'link in bio' detection"""
        text = "Check the link in bio!"
        assert service._contains_link(text) is True

    def test_no_link_detected(self, service):
        """Test no link in clean text"""
        text = "Thanks for your comment!"
        assert service._contains_link(text) is False


class TestSuggestionGeneration:
    """Test AI suggestion generation"""

    @pytest.fixture
    def service(self):
        ReplySuggestionsService._instance = None
        return ReplySuggestionsService.get_instance()

    @pytest.mark.asyncio
    async def test_generate_suggestions_success(self, service):
        """Test successful suggestion generation"""
        # Mock AI response
        mock_response = [
            {
                "text": "Thanks so much! Really appreciate your support 🙏",
                "tone": "friendly",
                "confidence": 0.9,
                "reasoning": "Genuine appreciation for positive feedback"
            },
            {
                "text": "Thank you! Glad you enjoyed it.",
                "tone": "professional",
                "confidence": 0.8,
                "reasoning": "Professional acknowledgment"
            },
            {
                "text": "You're awesome! Thanks for watching! ✨",
                "tone": "enthusiastic",
                "confidence": 0.85,
                "reasoning": "Matching enthusiastic energy"
            }
        ]

        with patch.object(service, '_generate_with_ai', new_callable=AsyncMock, return_value=mock_response):
            suggestions = await service.generate_suggestions(
                message="Love this video!",
                message_type=MessageType.COMMENT,
                platform="instagram"
            )

            assert len(suggestions) == 3
            assert all(isinstance(s, ReplySuggestion) for s in suggestions)
            assert suggestions[0].confidence == 0.9  # Sorted by confidence
            assert suggestions[0].tone == "friendly"

    @pytest.mark.asyncio
    async def test_generate_suggestions_with_link_warning(self, service):
        """Test DM suggestion with link triggers permission warning"""
        mock_response = [{
            "text": "Check out https://example.com for more info!",
            "tone": "helpful",
            "confidence": 0.7,
            "reasoning": "Providing resource link"
        }]

        with patch.object(service, '_generate_with_ai', new_callable=AsyncMock, return_value=mock_response):
            suggestions = await service.generate_suggestions(
                message="Where can I learn more?",
                message_type=MessageType.DM,
                platform="instagram"
            )

            assert len(suggestions) == 1
            assert suggestions[0].includes_link is True
            assert suggestions[0].requires_permission is True

    @pytest.mark.asyncio
    async def test_generate_suggestions_comment_with_link_no_permission(self, service):
        """Test comment with link doesn't require permission"""
        mock_response = [{
            "text": "Check the link in bio!",
            "tone": "friendly",
            "confidence": 0.8,
            "reasoning": "Directing to profile link"
        }]

        with patch.object(service, '_generate_with_ai', new_callable=AsyncMock, return_value=mock_response):
            suggestions = await service.generate_suggestions(
                message="Where's the download link?",
                message_type=MessageType.COMMENT,
                platform="instagram"
            )

            assert suggestions[0].includes_link is True
            assert suggestions[0].requires_permission is False  # Comments don't need permission

    @pytest.mark.asyncio
    async def test_generate_suggestions_handles_ai_error(self, service):
        """Test graceful handling of AI errors"""
        # Mock _generate_with_ai to return fallback response
        mock_fallback = [{
            "text": "Thank you for your message!",
            "tone": "neutral",
            "confidence": 0.3,
            "reasoning": "Fallback response due to AI error"
        }]

        with patch.object(service, '_generate_with_ai', new_callable=AsyncMock, return_value=mock_fallback):
            suggestions = await service.generate_suggestions(
                message="Test message",
                message_type=MessageType.COMMENT,
                platform="instagram"
            )

            # Should get fallback suggestions
            assert len(suggestions) >= 1
            assert suggestions[0].text == "Thank you for your message!"


class TestBrandVoice:
    """Test brand voice customization"""

    @pytest.fixture
    def service(self):
        ReplySuggestionsService._instance = None
        return ReplySuggestionsService.get_instance()

    def test_update_brand_voice_tone(self, service):
        """Test updating brand voice tone"""
        original_tone = service.brand_voice["tone"]

        service.update_brand_voice(
            brand_id="test-brand",
            tone="casual, fun, energetic"
        )

        assert service.brand_voice["tone"] == "casual, fun, energetic"
        assert service.brand_voice["tone"] != original_tone

    def test_update_brand_voice_multiple_fields(self, service):
        """Test updating multiple brand voice fields"""
        service.update_brand_voice(
            brand_id="test-brand",
            tone="professional, helpful",
            style="formal and precise",
            values="excellence, reliability"
        )

        assert service.brand_voice["tone"] == "professional, helpful"
        assert service.brand_voice["style"] == "formal and precise"
        assert service.brand_voice["values"] == "excellence, reliability"

    def test_update_brand_voice_partial(self, service):
        """Test partial brand voice update"""
        original_style = service.brand_voice["style"]

        service.update_brand_voice(
            brand_id="test-brand",
            tone="new tone"
        )

        # Only tone should change
        assert service.brand_voice["tone"] == "new tone"
        assert service.brand_voice["style"] == original_style


class TestServiceStatus:
    """Test service status reporting"""

    @pytest.fixture
    def service(self):
        ReplySuggestionsService._instance = None
        return ReplySuggestionsService.get_instance()

    def test_get_status(self, service):
        """Test status endpoint returns correct info"""
        status = service.get_status()

        assert status["service"] == "reply_suggestions"
        assert status["status"] == "operational"
        assert "ai_model" in status
        assert "ai_provider" in status
        assert "brand_voice" in status
        assert "timestamp" in status


class TestReplySuggestionModel:
    """Test ReplySuggestion data model"""

    def test_reply_suggestion_creation(self):
        """Test creating a reply suggestion"""
        suggestion = ReplySuggestion(
            text="Thanks for your comment!",
            tone="friendly",
            confidence=0.9,
            reasoning="Polite acknowledgment",
            includes_link=False,
            requires_permission=False
        )

        assert suggestion.text == "Thanks for your comment!"
        assert suggestion.tone == "friendly"
        assert suggestion.confidence == 0.9

    def test_reply_suggestion_to_dict(self):
        """Test converting suggestion to dictionary"""
        suggestion = ReplySuggestion(
            text="Test reply",
            tone="professional",
            confidence=0.8,
            reasoning="Test reasoning",
            includes_link=True,
            requires_permission=True
        )

        data = suggestion.to_dict()

        assert data["text"] == "Test reply"
        assert data["tone"] == "professional"
        assert data["confidence"] == 0.8
        assert data["includes_link"] is True
        assert data["requires_permission"] is True


class TestPromptBuilding:
    """Test AI prompt building"""

    @pytest.fixture
    def service(self):
        ReplySuggestionsService._instance = None
        return ReplySuggestionsService.get_instance()

    def test_system_prompt_includes_brand_voice(self, service):
        """Test system prompt includes brand voice"""
        system_prompt = service._get_system_prompt()

        assert service.brand_voice["tone"] in system_prompt
        assert service.brand_voice["style"] in system_prompt
        assert "JSON" in system_prompt  # Should specify output format

    def test_user_prompt_includes_context(self, service):
        """Test user prompt includes all context"""
        prompt = service._build_ai_prompt(
            message="Test message",
            message_type=MessageType.COMMENT,
            platform="instagram",
            sentiment=SentimentType.POSITIVE,
            context_str="Post: Test Post",
            num_suggestions=3
        )

        assert "Test message" in prompt
        assert "comment" in prompt
        assert "instagram" in prompt
        assert "positive" in prompt
        assert "Post: Test Post" in prompt
        assert "3" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

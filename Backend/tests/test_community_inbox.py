"""
Tests for Community Inbox System
Tests message aggregation, AI replies, saved replies, and content ideas.
"""

import pytest
from datetime import datetime, timezone


class TestInboxServiceImports:
    """Test that all inbox components can be imported."""
    
    def test_inbox_service_imports(self):
        """Test InboxService can be imported."""
        from services.inbox import InboxService, get_inbox_service
        assert InboxService is not None
        assert get_inbox_service is not None
    
    def test_message_model_imports(self):
        """Test InboxMessage dataclass can be imported."""
        from services.inbox import InboxMessage, SavedReply, ContentIdea
        assert InboxMessage is not None
        assert SavedReply is not None
        assert ContentIdea is not None
    
    def test_enums_import(self):
        """Test enums can be imported."""
        from services.inbox import (
            MessagePlatform, 
            MessageType, 
            MessageStatus, 
            MessagePriority, 
            Sentiment
        )
        assert MessagePlatform is not None
        assert MessageType is not None
        assert MessageStatus is not None
        assert MessagePriority is not None
        assert Sentiment is not None


class TestInboxMessage:
    """Tests for InboxMessage dataclass."""
    
    def test_message_creation(self):
        """Test InboxMessage creation with defaults."""
        from services.inbox import InboxMessage
        
        msg = InboxMessage(
            platform="instagram",
            sender_username="testuser",
            content="Great video!"
        )
        
        assert msg.id is not None
        assert msg.platform == "instagram"
        assert msg.sender_username == "testuser"
        assert msg.content == "Great video!"
        assert msg.status == "unread"
        assert msg.priority == "medium"
    
    def test_message_to_dict(self):
        """Test message serialization."""
        from services.inbox import InboxMessage
        
        msg = InboxMessage(
            platform="tiktok",
            sender_username="creator",
            content="Love this!",
            message_type="comment"
        )
        
        data = msg.to_dict()
        
        assert "id" in data
        assert data["platform"] == "tiktok"
        assert data["sender_username"] == "creator"
        assert data["content"] == "Love this!"
        assert data["status"] == "unread"
    
    def test_message_with_full_context(self):
        """Test message with all context fields."""
        from services.inbox import InboxMessage
        
        msg = InboxMessage(
            platform="instagram",
            sender_username="influencer",
            sender_name="Big Influencer",
            sender_follower_count=500000,
            content="This is amazing!",
            message_type="comment",
            post_id="abc123",
            post_url="https://instagram.com/p/abc123",
            post_caption="My latest video",
            priority="high",
            sentiment="positive",
            is_verified=True,
            is_influencer=True
        )
        
        assert msg.sender_follower_count == 500000
        assert msg.is_verified == True
        assert msg.is_influencer == True
        assert msg.priority == "high"


class TestSavedReply:
    """Tests for SavedReply dataclass."""
    
    def test_saved_reply_creation(self):
        """Test SavedReply creation."""
        from services.inbox import SavedReply
        
        reply = SavedReply(
            name="Thank You",
            content="Thanks for your support, {name}!",
            category="gratitude",
            variables=["name"]
        )
        
        assert reply.id is not None
        assert reply.name == "Thank You"
        assert "name" in reply.variables
    
    def test_saved_reply_to_dict(self):
        """Test SavedReply serialization."""
        from services.inbox import SavedReply
        
        reply = SavedReply(
            name="Test",
            content="Hello!",
            category="general"
        )
        
        data = reply.to_dict()
        
        assert "id" in data
        assert data["name"] == "Test"
        assert data["category"] == "general"


class TestContentIdea:
    """Tests for ContentIdea dataclass."""
    
    def test_content_idea_creation(self):
        """Test ContentIdea creation."""
        from services.inbox import ContentIdea
        
        idea = ContentIdea(
            source_message_id="msg123",
            title="Video about productivity",
            description="Based on user question",
            content_type="video",
            platforms=["tiktok", "instagram"]
        )
        
        assert idea.id is not None
        assert idea.title == "Video about productivity"
        assert "tiktok" in idea.platforms
    
    def test_content_idea_to_dict(self):
        """Test ContentIdea serialization."""
        from services.inbox import ContentIdea
        
        idea = ContentIdea(
            source_message_id="msg456",
            title="Test Idea",
            status="idea"
        )
        
        data = idea.to_dict()
        
        assert "id" in data
        assert data["title"] == "Test Idea"
        assert data["status"] == "idea"


class TestInboxServiceOperations:
    """Tests for InboxService operations."""
    
    def test_inbox_singleton(self):
        """Test get_inbox_service returns same instance."""
        from services.inbox import get_inbox_service
        
        inbox1 = get_inbox_service()
        inbox2 = get_inbox_service()
        
        assert inbox1 is inbox2
    
    def test_inbox_initialization(self):
        """Test InboxService initializes correctly."""
        from services.inbox import InboxService
        
        inbox = InboxService()
        assert inbox is not None
        assert inbox.engine is not None
    
    def test_get_stats(self):
        """Test getting inbox statistics."""
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        stats = inbox.get_stats()
        
        assert "by_status" in stats
        assert "by_platform" in stats
        assert "today" in stats
        assert "unread" in stats
    
    def test_get_unread_count(self):
        """Test getting unread message count."""
        from services.inbox import get_inbox_service
        
        inbox = get_inbox_service()
        count = inbox.get_unread_count()
        
        assert isinstance(count, int)
        assert count >= 0


class TestMessageEnums:
    """Tests for message enums."""
    
    def test_message_platforms(self):
        """Test all platforms are defined."""
        from services.inbox import MessagePlatform
        
        platforms = list(MessagePlatform)
        assert len(platforms) >= 5
        
        expected = ["instagram", "tiktok", "twitter", "youtube", "threads"]
        actual_values = [p.value for p in platforms]
        
        for expected_platform in expected:
            assert expected_platform in actual_values
    
    def test_message_types(self):
        """Test all message types are defined."""
        from services.inbox import MessageType
        
        types = list(MessageType)
        assert len(types) >= 4
        
        expected = ["comment", "dm", "mention", "reply"]
        actual_values = [t.value for t in types]
        
        for expected_type in expected:
            assert expected_type in actual_values
    
    def test_message_statuses(self):
        """Test all statuses are defined."""
        from services.inbox import MessageStatus
        
        statuses = list(MessageStatus)
        expected = ["unread", "read", "replied", "archived", "spam"]
        actual_values = [s.value for s in statuses]
        
        for expected_status in expected:
            assert expected_status in actual_values
    
    def test_sentiment_values(self):
        """Test all sentiments are defined."""
        from services.inbox import Sentiment
        
        sentiments = list(Sentiment)
        expected = ["positive", "neutral", "negative", "question"]
        actual_values = [s.value for s in sentiments]
        
        for expected_sentiment in expected:
            assert expected_sentiment in actual_values


class TestInboxAPIEndpoints:
    """Tests for Inbox API endpoints."""
    
    def test_api_router_exists(self):
        """Test API router can be imported."""
        from api.endpoints.inbox import router
        assert router is not None
    
    def test_message_endpoints_exist(self):
        """Test message management endpoints exist."""
        from api.endpoints.inbox import (
            get_messages,
            get_message,
            get_unread_count,
            update_message_status,
            assign_message,
            add_message_tags
        )
        assert get_messages is not None
        assert get_message is not None
        assert get_unread_count is not None
        assert update_message_status is not None
        assert assign_message is not None
        assert add_message_tags is not None
    
    def test_ai_suggestion_endpoints_exist(self):
        """Test AI suggestion endpoints exist."""
        from api.endpoints.inbox import (
            get_ai_suggestions,
            generate_ai_reply,
            analyze_message_sentiment
        )
        assert get_ai_suggestions is not None
        assert generate_ai_reply is not None
        assert analyze_message_sentiment is not None
    
    def test_saved_reply_endpoints_exist(self):
        """Test saved reply endpoints exist."""
        from api.endpoints.inbox import (
            get_saved_replies,
            create_saved_reply,
            use_saved_reply
        )
        assert get_saved_replies is not None
        assert create_saved_reply is not None
        assert use_saved_reply is not None
    
    def test_content_idea_endpoints_exist(self):
        """Test content idea endpoints exist."""
        from api.endpoints.inbox import (
            create_idea_from_message,
            get_content_ideas
        )
        assert create_idea_from_message is not None
        assert get_content_ideas is not None
    
    def test_stats_endpoint_exists(self):
        """Test stats endpoint exists."""
        from api.endpoints.inbox import get_inbox_stats
        assert get_inbox_stats is not None


class TestAIReplyService:
    """Tests for AI Reply Service."""
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_ai_reply_service_imports(self):
        """Test AIReplyService can be imported."""
        from services.inbox.ai_reply_service import AIReplyService, get_ai_reply_service
        assert AIReplyService is not None
        assert get_ai_reply_service is not None
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_reply_suggestion_dataclass(self):
        """Test ReplySuggestion dataclass."""
        from services.inbox.ai_reply_service import ReplySuggestion
        
        suggestion = ReplySuggestion(
            content="Thanks for your comment!",
            tone="friendly",
            intent="thank",
            confidence=0.9,
            variables_used=[]
        )
        
        assert suggestion.content == "Thanks for your comment!"
        assert suggestion.tone == "friendly"
        assert suggestion.confidence == 0.9


class TestInboxIntegration:
    """Integration tests for inbox system."""
    
    def test_message_workflow(self):
        """Test full message workflow."""
        from services.inbox import get_inbox_service, InboxMessage
        
        inbox = get_inbox_service()
        
        # Create a message
        msg = InboxMessage(
            platform="instagram",
            sender_username="workflow_test",
            content="Test workflow message",
            message_type="comment",
            platform_message_id=f"test_{datetime.now().timestamp()}"
        )
        
        # Add to inbox
        added = inbox.add_message(msg)
        assert added.id == msg.id
        
        # Get the message
        retrieved = inbox.get_message(msg.id)
        assert retrieved is not None
        assert retrieved.content == "Test workflow message"
        
        # Update status
        success = inbox.update_status(msg.id, "read")
        assert success == True
    
    def test_saved_reply_workflow(self):
        """Test saved reply workflow."""
        from services.inbox import get_inbox_service, SavedReply
        
        inbox = get_inbox_service()
        
        # Create saved reply with variable
        reply = SavedReply(
            name="Test Reply",
            content="Hello {name}, thanks for reaching out!",
            category="greeting",
            variables=["name"]
        )
        
        created = inbox.create_saved_reply(reply)
        assert created.id == reply.id
        
        # Use the saved reply
        content = inbox.use_saved_reply(reply.id, {"name": "John"})
        assert content == "Hello John, thanks for reaching out!"
        
        # Get all saved replies
        replies = inbox.get_saved_replies()
        assert len(replies) >= 1

"""
Unit tests for Topics registry.

Tests:
- Topic constants
- Pattern matching
- Topic naming conventions
"""

import pytest
from services.event_bus.topics import Topics


class TestTopicConstants:
    """Tests for topic constant definitions."""
    
    def test_media_ingested_topic(self):
        """Should have MEDIA_INGESTED topic."""
        assert hasattr(Topics, 'MEDIA_INGESTED')
        assert Topics.MEDIA_INGESTED == "media.ingested"
    
    def test_media_updated_topic(self):
        """Should have MEDIA_UPDATED topic."""
        assert hasattr(Topics, 'MEDIA_UPDATED')
        assert Topics.MEDIA_UPDATED == "media.updated"
    
    def test_analysis_requested_topic(self):
        """Should have ANALYSIS_REQUESTED topic."""
        assert hasattr(Topics, 'ANALYSIS_REQUESTED')
        assert "analysis" in Topics.ANALYSIS_REQUESTED.lower()
    
    def test_analysis_completed_topic(self):
        """Should have ANALYSIS_COMPLETED topic."""
        assert hasattr(Topics, 'ANALYSIS_COMPLETED')
        assert "completed" in Topics.ANALYSIS_COMPLETED.lower()
    
    def test_publish_requested_topic(self):
        """Should have PUBLISH_REQUESTED topic."""
        assert hasattr(Topics, 'PUBLISH_REQUESTED')
        assert "publish" in Topics.PUBLISH_REQUESTED.lower()
    
    def test_publish_completed_topic(self):
        """Should have PUBLISH_COMPLETED topic."""
        assert hasattr(Topics, 'PUBLISH_COMPLETED')
        assert "completed" in Topics.PUBLISH_COMPLETED.lower()
    
    def test_schedule_due_topic(self):
        """Should have SCHEDULE_DUE topic."""
        assert hasattr(Topics, 'SCHEDULE_DUE')
        assert "schedule" in Topics.SCHEDULE_DUE.lower()


class TestTopicNamingConvention:
    """Tests for topic naming conventions."""
    
    def test_topics_use_dot_separator(self):
        """Topics should use dot separator."""
        topics = [
            Topics.MEDIA_INGESTED,
            Topics.ANALYSIS_REQUESTED,
            Topics.PUBLISH_COMPLETED,
        ]
        
        for topic in topics:
            assert "." in topic
    
    def test_topics_are_lowercase(self):
        """Topic values should be lowercase."""
        topics = [
            Topics.MEDIA_INGESTED,
            Topics.ANALYSIS_REQUESTED,
            Topics.PUBLISH_COMPLETED,
        ]
        
        for topic in topics:
            assert topic == topic.lower()
    
    def test_media_topics_start_with_media(self):
        """Media lifecycle topics should start with 'media'."""
        media_topics = [
            Topics.MEDIA_INGESTED,
            Topics.MEDIA_UPDATED,
            Topics.MEDIA_DELETED,
        ]
        
        for topic in media_topics:
            assert topic.startswith("media.")
    
    def test_publish_topics_start_with_publish(self):
        """Publishing topics should start with 'publish'."""
        publish_topics = [
            Topics.PUBLISH_REQUESTED,
            Topics.PUBLISH_STARTED,
            Topics.PUBLISH_COMPLETED,
            Topics.PUBLISH_FAILED,
        ]
        
        for topic in publish_topics:
            assert topic.startswith("publish.")


class TestPatternMatching:
    """Tests for pattern matching utility."""
    
    def test_exact_match(self):
        """Exact topic should match."""
        result = Topics.matches_pattern("media.ingested", "media.ingested")
        
        assert result is True
    
    def test_exact_no_match(self):
        """Different topic should not match."""
        result = Topics.matches_pattern("media.ingested", "media.updated")
        
        assert result is False
    
    def test_wildcard_suffix_match(self):
        """Pattern 'prefix.*' should match subtopics."""
        result = Topics.matches_pattern("media.*", "media.ingested")
        
        assert result is True
    
    def test_wildcard_suffix_no_match(self):
        """Pattern 'prefix.*' should not match other prefixes."""
        result = Topics.matches_pattern("media.*", "publish.completed")
        
        assert result is False
    
    def test_wildcard_prefix_match(self):
        """Pattern '*.suffix' should match."""
        result = Topics.matches_pattern("*.completed", "publish.completed")
        
        assert result is True
    
    def test_wildcard_all_match(self):
        """Pattern '*' should match any topic."""
        assert Topics.matches_pattern("*", "media.ingested") is True
        assert Topics.matches_pattern("*", "publish.completed") is True
        assert Topics.matches_pattern("*", "any.topic.here") is True


class TestTopicCategories:
    """Tests for topic category groupings."""
    
    def test_analysis_pipeline_topics_exist(self):
        """Analysis pipeline topics should exist."""
        analysis_topics = [
            "ANALYSIS_REQUESTED",
            "ANALYSIS_STARTED",
            "ANALYSIS_COMPLETED",
            "ANALYSIS_FAILED",
        ]
        
        for attr in analysis_topics:
            assert hasattr(Topics, attr), f"Missing topic: {attr}"
    
    def test_scheduling_topics_exist(self):
        """Scheduling topics should exist."""
        schedule_topics = [
            "SCHEDULE_CREATED",
            "SCHEDULE_DUE",
        ]
        
        for attr in schedule_topics:
            assert hasattr(Topics, attr), f"Missing topic: {attr}"
    
    def test_metrics_topics_exist(self):
        """Metrics topics should exist."""
        metrics_topics = [
            "METRICS_FETCH_REQUESTED",
            "METRICS_UPDATED",
        ]
        
        for attr in metrics_topics:
            assert hasattr(Topics, attr), f"Missing topic: {attr}"

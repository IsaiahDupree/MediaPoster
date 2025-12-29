"""
Unit tests for Event model.

Tests:
- Event creation
- Serialization (to_dict, to_json)
- Deserialization (from_dict, from_json)
- Metadata handling
"""

import pytest
import json
from datetime import datetime, timezone
from services.event_bus.event import Event


class TestEventCreation:
    """Tests for Event creation."""
    
    def test_event_with_required_fields(self):
        """Should create event with topic and payload."""
        event = Event(topic="test.topic", payload={"key": "value"})
        
        assert event.topic == "test.topic"
        assert event.payload == {"key": "value"}
    
    def test_event_has_auto_generated_id(self):
        """Event should have auto-generated ID."""
        event = Event(topic="test", payload={})
        
        assert event.id is not None
        assert len(event.id) > 0
    
    def test_event_has_auto_generated_timestamp(self):
        """Event should have auto-generated timestamp."""
        event = Event(topic="test", payload={})
        
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
    
    def test_event_has_auto_generated_correlation_id(self):
        """Event should have auto-generated correlation ID."""
        event = Event(topic="test", payload={})
        
        assert event.correlation_id is not None
        assert len(event.correlation_id) > 0
    
    def test_event_with_custom_id(self):
        """Should accept custom ID."""
        event = Event(id="custom-id", topic="test", payload={})
        
        assert event.id == "custom-id"
    
    def test_event_with_custom_correlation_id(self):
        """Should accept custom correlation ID."""
        event = Event(topic="test", payload={}, correlation_id="my-corr-id")
        
        assert event.correlation_id == "my-corr-id"
    
    def test_event_with_source(self):
        """Should accept source."""
        event = Event(topic="test", payload={}, source="my-service")
        
        assert event.source == "my-service"
    
    def test_event_with_metadata(self):
        """Should accept metadata."""
        event = Event(topic="test", payload={}, metadata={"key": "value"})
        
        assert event.metadata == {"key": "value"}
    
    def test_event_default_source(self):
        """Default source should be 'unknown'."""
        event = Event(topic="test", payload={})
        
        assert event.source == "unknown"
    
    def test_event_default_metadata(self):
        """Default metadata should be empty dict."""
        event = Event(topic="test", payload={})
        
        assert event.metadata == {}


class TestEventSerialization:
    """Tests for Event serialization."""
    
    def test_to_dict_returns_dict(self):
        """to_dict should return dictionary."""
        event = Event(topic="test", payload={"data": 123})
        
        result = event.to_dict()
        
        assert isinstance(result, dict)
    
    def test_to_dict_has_all_fields(self):
        """to_dict should include all fields."""
        event = Event(
            id="my-id",
            topic="test.topic",
            payload={"key": "value"},
            source="my-service",
            correlation_id="my-corr",
            metadata={"meta": "data"}
        )
        
        result = event.to_dict()
        
        assert result["id"] == "my-id"
        assert result["topic"] == "test.topic"
        assert result["payload"] == {"key": "value"}
        assert result["source"] == "my-service"
        assert result["correlation_id"] == "my-corr"
        assert result["metadata"] == {"meta": "data"}
        assert "timestamp" in result
    
    def test_to_dict_timestamp_is_iso_format(self):
        """Timestamp should be ISO format string."""
        event = Event(topic="test", payload={})
        
        result = event.to_dict()
        
        assert isinstance(result["timestamp"], str)
        # Should be parseable as ISO
        datetime.fromisoformat(result["timestamp"])
    
    def test_to_json_returns_string(self):
        """to_json should return JSON string."""
        event = Event(topic="test", payload={"num": 42})
        
        result = event.to_json()
        
        assert isinstance(result, str)
    
    def test_to_json_is_valid_json(self):
        """to_json output should be valid JSON."""
        event = Event(topic="test", payload={"key": "value"})
        
        result = event.to_json()
        parsed = json.loads(result)
        
        assert parsed["topic"] == "test"
        assert parsed["payload"]["key"] == "value"


class TestEventDeserialization:
    """Tests for Event deserialization."""
    
    def test_from_dict_creates_event(self):
        """from_dict should create Event instance."""
        data = {
            "id": "test-id",
            "topic": "test.topic",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "test-source",
            "correlation_id": "test-corr",
            "payload": {"key": "value"},
            "metadata": {}
        }
        
        event = Event.from_dict(data)
        
        assert isinstance(event, Event)
        assert event.id == "test-id"
        assert event.topic == "test.topic"
    
    def test_from_dict_with_minimal_data(self):
        """from_dict should work with minimal required fields."""
        data = {
            "topic": "test.topic",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {}
        }
        
        event = Event.from_dict(data)
        
        assert event.topic == "test.topic"
        assert event.id is not None  # Auto-generated
    
    def test_from_json_creates_event(self):
        """from_json should create Event from JSON string."""
        data = {
            "topic": "test.topic",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"key": "value"}
        }
        json_str = json.dumps(data)
        
        event = Event.from_json(json_str)
        
        assert event.topic == "test.topic"
        assert event.payload["key"] == "value"
    
    def test_roundtrip_serialization(self):
        """Event should survive to_dict/from_dict roundtrip."""
        original = Event(
            topic="test.topic",
            payload={"data": 123, "nested": {"a": 1}},
            source="my-service",
            metadata={"meta_key": "meta_value"}
        )
        
        data = original.to_dict()
        restored = Event.from_dict(data)
        
        assert restored.topic == original.topic
        assert restored.payload == original.payload
        assert restored.source == original.source
        assert restored.metadata == original.metadata
    
    def test_roundtrip_json_serialization(self):
        """Event should survive to_json/from_json roundtrip."""
        original = Event(
            topic="test.topic",
            payload={"list": [1, 2, 3]},
        )
        
        json_str = original.to_json()
        restored = Event.from_json(json_str)
        
        assert restored.topic == original.topic
        assert restored.payload == original.payload


class TestEventMetadata:
    """Tests for Event metadata handling."""
    
    def test_with_metadata_returns_new_event(self):
        """with_metadata should return new Event."""
        original = Event(topic="test", payload={})
        
        new_event = original.with_metadata(key="value")
        
        assert new_event is not original
    
    def test_with_metadata_adds_metadata(self):
        """with_metadata should add metadata to new event."""
        original = Event(topic="test", payload={}, metadata={"existing": "data"})
        
        new_event = original.with_metadata(new_key="new_value")
        
        assert new_event.metadata["existing"] == "data"
        assert new_event.metadata["new_key"] == "new_value"
    
    def test_with_metadata_preserves_other_fields(self):
        """with_metadata should preserve other event fields."""
        original = Event(
            id="my-id",
            topic="test",
            payload={"key": "value"},
            source="my-source",
            correlation_id="my-corr"
        )
        
        new_event = original.with_metadata(added="meta")
        
        assert new_event.id == original.id
        assert new_event.topic == original.topic
        assert new_event.payload == original.payload
        assert new_event.source == original.source
        assert new_event.correlation_id == original.correlation_id


class TestEventRepr:
    """Tests for Event string representation."""
    
    def test_repr_contains_topic(self):
        """repr should contain topic."""
        event = Event(topic="test.topic", payload={})
        
        result = repr(event)
        
        assert "test.topic" in result
    
    def test_repr_contains_id_prefix(self):
        """repr should contain ID prefix."""
        event = Event(id="12345678-abcd-efgh", topic="test", payload={})
        
        result = repr(event)
        
        assert "12345678" in result

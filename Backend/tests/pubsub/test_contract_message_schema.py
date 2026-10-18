"""
Contract Tests: Message Schema Validation
==========================================
Prevent breaking changes in message shape between producers and consumers.

These tests verify:
- Message envelope schema validation
- Required fields presence
- Type checks and enum values
- Versioning rules
- Unknown fields handled gracefully
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4
from enum import Enum
from dataclasses import dataclass, field
import json


# ============================================================================
# MESSAGE SCHEMA DEFINITIONS
# ============================================================================

class EventType(str, Enum):
    """Valid event types."""
    RUN_QUEUED = "run.queued"
    RUN_STARTED = "run.started"
    RUN_SUCCEEDED = "run.succeeded"
    RUN_FAILED = "run.failed"
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    THOUGHT_SUMMARY = "thought.summary"
    ARTIFACT_CREATED = "artifact.created"
    DECISION_MADE = "decision.made"


class Severity(str, Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MessageEnvelope:
    """Standard message envelope for all pub/sub messages."""
    id: str
    topic: str
    run_id: str
    step_key: Optional[str]
    event_type: str
    timestamp: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Schema version
    SCHEMA_VERSION = 2
    
    # Required fields
    REQUIRED_FIELDS = {"id", "topic", "run_id", "event_type", "timestamp", "payload"}
    
    # Required payload fields per event type
    PAYLOAD_REQUIREMENTS = {
        EventType.RUN_QUEUED: {"workflow_type"},
        EventType.RUN_STARTED: {"workflow_type"},
        EventType.RUN_SUCCEEDED: {"duration_ms"},
        EventType.RUN_FAILED: {"error", "duration_ms"},
        EventType.STEP_STARTED: {"step_key"},
        EventType.STEP_COMPLETED: {"step_key", "duration_ms"},
        EventType.STEP_FAILED: {"step_key", "error"},
        EventType.THOUGHT_SUMMARY: {"summary"},
        EventType.ARTIFACT_CREATED: {"artifact_type", "artifact_id"},
        EventType.DECISION_MADE: {"decision", "reasoning"},
    }


class SchemaValidationError(Exception):
    """Raised when message fails schema validation."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Schema validation failed: {errors}")


class MessageSchemaValidator:
    """Validates message schemas for contract compliance."""
    
    @staticmethod
    def validate_envelope(message: Dict[str, Any]) -> List[str]:
        """Validate message envelope structure. Returns list of errors."""
        errors = []
        
        # Check required fields
        for field in MessageEnvelope.REQUIRED_FIELDS:
            if field not in message:
                errors.append(f"Missing required field: {field}")
            elif message[field] is None:
                errors.append(f"Required field is null: {field}")
        
        # Type validations
        if "id" in message and not isinstance(message["id"], str):
            errors.append(f"Field 'id' must be string, got {type(message['id']).__name__}")
        
        if "topic" in message and not isinstance(message["topic"], str):
            errors.append(f"Field 'topic' must be string, got {type(message['topic']).__name__}")
        
        if "run_id" in message and not isinstance(message["run_id"], str):
            errors.append(f"Field 'run_id' must be string, got {type(message['run_id']).__name__}")
        
        if "payload" in message and not isinstance(message["payload"], dict):
            errors.append(f"Field 'payload' must be object, got {type(message['payload']).__name__}")
        
        # Validate timestamp format
        if "timestamp" in message:
            try:
                datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                errors.append(f"Field 'timestamp' must be ISO 8601 format")
        
        # Validate event_type is known
        if "event_type" in message:
            try:
                EventType(message["event_type"])
            except ValueError:
                # Unknown event type - log warning but don't fail (forward compatibility)
                pass
        
        return errors
    
    @staticmethod
    def validate_payload(event_type: str, payload: Dict[str, Any]) -> List[str]:
        """Validate payload for specific event type."""
        errors = []
        
        try:
            et = EventType(event_type)
            required = MessageEnvelope.PAYLOAD_REQUIREMENTS.get(et, set())
            
            for field in required:
                if field not in payload:
                    errors.append(f"Payload missing required field for {event_type}: {field}")
        except ValueError:
            # Unknown event type - can't validate payload requirements
            pass
        
        # Version check
        if "v" in payload:
            version = payload["v"]
            if not isinstance(version, int):
                errors.append("Payload 'v' (version) must be integer")
            elif version > MessageEnvelope.SCHEMA_VERSION:
                errors.append(f"Payload version {version} is newer than supported {MessageEnvelope.SCHEMA_VERSION}")
        
        return errors
    
    @classmethod
    def validate(cls, message: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Full validation. Returns (passed, errors)."""
        errors = cls.validate_envelope(message)
        
        if "event_type" in message and "payload" in message:
            errors.extend(cls.validate_payload(message["event_type"], message["payload"]))
        
        return len(errors) == 0, errors


class ConsumerContract:
    """Defines what a consumer expects from messages."""
    
    def __init__(self, name: str):
        self.name = name
        self.required_fields: Dict[str, set] = {}  # event_type -> required payload fields
    
    def expect(self, event_type: str, required_payload_fields: set) -> "ConsumerContract":
        """Declare expected payload fields for an event type."""
        self.required_fields[event_type] = required_payload_fields
        return self
    
    def validate(self, message: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate message against consumer contract."""
        errors = []
        
        event_type = message.get("event_type")
        if event_type not in self.required_fields:
            return True, []  # Not an event we care about
        
        required = self.required_fields[event_type]
        payload = message.get("payload", {})
        
        for field in required:
            if field not in payload:
                errors.append(f"Consumer '{self.name}' requires '{field}' in {event_type} payload")
        
        return len(errors) == 0, errors


# ============================================================================
# TESTS
# ============================================================================

class TestMessageEnvelopeValidation:
    """Test message envelope schema validation."""
    
    @pytest.fixture
    def valid_message(self):
        """Valid message for testing."""
        return {
            "id": str(uuid4()),
            "topic": "narrative.run.started",
            "run_id": str(uuid4()),
            "step_key": "planning",
            "event_type": "run.started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"v": 1, "workflow_type": "narrative_weekly"},
            "metadata": {"source": "scheduler"},
        }
    
    def test_valid_message_passes(self, valid_message):
        """Valid message should pass validation."""
        passed, errors = MessageSchemaValidator.validate(valid_message)
        assert passed is True
        assert len(errors) == 0
    
    def test_missing_required_field_fails(self, valid_message):
        """Missing required field should fail."""
        del valid_message["run_id"]
        passed, errors = MessageSchemaValidator.validate(valid_message)
        assert passed is False
        assert any("run_id" in e for e in errors)
    
    def test_null_required_field_fails(self, valid_message):
        """Null required field should fail."""
        valid_message["topic"] = None
        passed, errors = MessageSchemaValidator.validate(valid_message)
        assert passed is False
        assert any("null" in e.lower() for e in errors)
    
    def test_wrong_type_fails(self, valid_message):
        """Wrong field type should fail."""
        valid_message["id"] = 12345  # Should be string
        passed, errors = MessageSchemaValidator.validate(valid_message)
        assert passed is False
        assert any("string" in e for e in errors)
    
    def test_invalid_timestamp_fails(self, valid_message):
        """Invalid timestamp format should fail."""
        valid_message["timestamp"] = "not-a-timestamp"
        passed, errors = MessageSchemaValidator.validate(valid_message)
        assert passed is False
        assert any("ISO 8601" in e for e in errors)
    
    def test_payload_not_object_fails(self, valid_message):
        """Payload must be an object."""
        valid_message["payload"] = "not an object"
        passed, errors = MessageSchemaValidator.validate(valid_message)
        assert passed is False
        assert any("object" in e for e in errors)
    
    def test_unknown_event_type_allowed(self, valid_message):
        """Unknown event types should be allowed (forward compatibility)."""
        valid_message["event_type"] = "future.new_event"
        passed, errors = MessageSchemaValidator.validate(valid_message)
        # Should pass envelope validation even with unknown type
        envelope_errors = MessageSchemaValidator.validate_envelope(valid_message)
        assert "event_type" not in str(envelope_errors)
    
    def test_extra_fields_ignored(self, valid_message):
        """Extra fields should be ignored (forward compatibility)."""
        valid_message["future_field"] = "some value"
        valid_message["another_new_field"] = {"nested": True}
        passed, errors = MessageSchemaValidator.validate(valid_message)
        assert passed is True


class TestPayloadValidation:
    """Test payload validation for specific event types."""
    
    def test_run_started_requires_workflow_type(self):
        """run.started must have workflow_type in payload."""
        errors = MessageSchemaValidator.validate_payload(
            "run.started",
            {"v": 1}  # Missing workflow_type
        )
        assert any("workflow_type" in e for e in errors)
    
    def test_run_failed_requires_error_and_duration(self):
        """run.failed must have error and duration_ms."""
        errors = MessageSchemaValidator.validate_payload(
            "run.failed",
            {"v": 1, "error": "Something broke"}  # Missing duration_ms
        )
        assert any("duration_ms" in e for e in errors)
    
    def test_step_completed_requires_step_key(self):
        """step.completed must have step_key."""
        errors = MessageSchemaValidator.validate_payload(
            "step.completed",
            {"v": 1, "duration_ms": 1234}  # Missing step_key
        )
        assert any("step_key" in e for e in errors)
    
    def test_artifact_created_requires_type_and_id(self):
        """artifact.created must have artifact_type and artifact_id."""
        errors = MessageSchemaValidator.validate_payload(
            "artifact.created",
            {"v": 1}  # Missing both
        )
        assert any("artifact_type" in e for e in errors)
        assert any("artifact_id" in e for e in errors)
    
    def test_valid_payload_passes(self):
        """Valid payload should pass."""
        errors = MessageSchemaValidator.validate_payload(
            "run.started",
            {"v": 1, "workflow_type": "narrative_weekly"}
        )
        assert len(errors) == 0
    
    def test_version_must_be_integer(self):
        """Payload version must be integer."""
        errors = MessageSchemaValidator.validate_payload(
            "run.started",
            {"v": "1", "workflow_type": "narrative_weekly"}  # String instead of int
        )
        assert any("integer" in e for e in errors)
    
    def test_future_version_warning(self):
        """Future version should produce error."""
        errors = MessageSchemaValidator.validate_payload(
            "run.started",
            {"v": 999, "workflow_type": "narrative_weekly"}
        )
        assert any("newer" in e for e in errors)


class TestConsumerContract:
    """Test consumer-driven contract validation."""
    
    def test_consumer_gets_required_fields(self):
        """Consumer should receive all required fields."""
        # Timeline UI consumer expects these fields
        timeline_consumer = (
            ConsumerContract("timeline-ui")
            .expect("run.started", {"workflow_type", "run_id"})
            .expect("step.completed", {"step_key", "duration_ms"})
        )
        
        valid_msg = {
            "event_type": "run.started",
            "payload": {"workflow_type": "narrative", "run_id": "abc"}
        }
        
        passed, errors = timeline_consumer.validate(valid_msg)
        assert passed is True
    
    def test_consumer_fails_on_missing_required(self):
        """Consumer should fail if required field missing."""
        timeline_consumer = (
            ConsumerContract("timeline-ui")
            .expect("step.completed", {"step_key", "duration_ms", "progress"})
        )
        
        msg = {
            "event_type": "step.completed",
            "payload": {"step_key": "analysis", "duration_ms": 1000}
            # Missing 'progress'
        }
        
        passed, errors = timeline_consumer.validate(msg)
        assert passed is False
        assert any("progress" in e for e in errors)
    
    def test_consumer_ignores_unsubscribed_events(self):
        """Consumer should pass on events it doesn't care about."""
        # This consumer only cares about run events
        run_consumer = (
            ConsumerContract("run-tracker")
            .expect("run.started", {"workflow_type"})
            .expect("run.succeeded", {"duration_ms"})
        )
        
        # Send a step event - should be ignored
        msg = {
            "event_type": "step.started",
            "payload": {}  # Empty, but we don't care
        }
        
        passed, errors = run_consumer.validate(msg)
        assert passed is True


class TestBackwardCompatibility:
    """Test backward compatibility rules."""
    
    def test_old_consumer_handles_new_fields(self):
        """Old consumer should ignore new fields in payload."""
        # Simulate old consumer that only knows v1 fields
        message = {
            "id": str(uuid4()),
            "topic": "test.topic",
            "run_id": str(uuid4()),
            "event_type": "run.started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "v": 2,
                "workflow_type": "narrative",
                # New v2 fields
                "estimated_duration_ms": 5000,
                "priority": "high",
                "new_nested_object": {"foo": "bar"},
            }
        }
        
        # Old consumer only checks for workflow_type
        old_consumer = ConsumerContract("old-service").expect("run.started", {"workflow_type"})
        
        passed, errors = old_consumer.validate(message)
        assert passed is True
    
    def test_required_fields_never_removed(self):
        """Required fields from v1 must still be present."""
        # This is a policy test - in practice, enforce in code review
        v1_required = {"id", "topic", "run_id", "event_type", "timestamp", "payload"}
        current_required = MessageEnvelope.REQUIRED_FIELDS
        
        # All v1 fields must still be required
        assert v1_required.issubset(current_required)


class TestSerializationRoundtrip:
    """Test that messages survive JSON serialization."""
    
    def test_json_roundtrip_preserves_message(self):
        """Message should be identical after JSON roundtrip."""
        original = {
            "id": str(uuid4()),
            "topic": "test.topic",
            "run_id": str(uuid4()),
            "step_key": "analysis",
            "event_type": "step.completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "v": 1,
                "step_key": "analysis",
                "duration_ms": 1234,
                "nested": {"key": "value"},
            },
            "metadata": {"attempt": 1},
        }
        
        # Serialize and deserialize
        json_str = json.dumps(original)
        restored = json.loads(json_str)
        
        # Should be identical
        assert original == restored
        
        # Should still pass validation
        passed, errors = MessageSchemaValidator.validate(restored)
        assert passed is True

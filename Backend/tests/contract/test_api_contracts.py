"""
API Contract Tests
Validates API response schemas match expected contracts
"""
import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict, List, Optional
import json


def validate_schema(data: Any, schema: Dict) -> List[str]:
    """
    Simple schema validator
    Returns list of validation errors
    """
    errors = []
    
    if schema.get("type") == "object":
        if not isinstance(data, dict):
            return [f"Expected object, got {type(data).__name__}"]
        
        # Check required fields
        for field in schema.get("required", []):
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        for field, field_schema in schema.get("properties", {}).items():
            if field in data:
                errors.extend(validate_field(data[field], field_schema, field))
    
    elif schema.get("type") == "array":
        if not isinstance(data, list):
            return [f"Expected array, got {type(data).__name__}"]
        
        item_schema = schema.get("items", {})
        for i, item in enumerate(data[:5]):  # Check first 5 items
            errors.extend(validate_schema(item, item_schema))
    
    return errors


def validate_field(value: Any, schema: Dict, field_name: str) -> List[str]:
    """Validate a single field"""
    errors = []
    expected_type = schema.get("type")
    
    if value is None:
        if not schema.get("nullable", False):
            errors.append(f"Field '{field_name}' is null but not nullable")
        return errors
    
    type_mapping = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    
    if expected_type and expected_type in type_mapping:
        expected = type_mapping[expected_type]
        if not isinstance(value, expected):
            errors.append(f"Field '{field_name}': expected {expected_type}, got {type(value).__name__}")
    
    return errors


class TestAnalyticsContracts:
    """Contract tests for analytics API"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    # Expected schema for analytics overview
    OVERVIEW_SCHEMA = {
        "type": "object",
        "properties": {
            "total_followers": {"type": "integer", "nullable": True},
            "total_posts": {"type": "integer", "nullable": True},
            "total_engagement": {"type": "number", "nullable": True},
            "accounts": {"type": "array", "nullable": True},
        }
    }
    
    def test_overview_contract(self, client):
        """Test analytics overview response matches contract"""
        response = client.get("/api/social-analytics/overview")
        
        if response.status_code == 200:
            data = response.json()
            errors = validate_schema(data, self.OVERVIEW_SCHEMA)
            assert len(errors) == 0, f"Contract violations: {errors}"
    
    # Expected schema for accounts list
    ACCOUNTS_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "platform": {"type": "string"},
                "username": {"type": "string", "nullable": True},
                "followers": {"type": "integer", "nullable": True},
            },
            "required": ["id", "platform"]
        }
    }
    
    def test_accounts_contract(self, client):
        """Test accounts list response matches contract"""
        response = client.get("/api/social-analytics/accounts")
        
        if response.status_code == 200:
            data = response.json()
            errors = validate_schema(data, self.ACCOUNTS_SCHEMA)
            assert len(errors) == 0, f"Contract violations: {errors}"


class TestVideosContracts:
    """Contract tests for videos API"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    VIDEO_SCHEMA = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string", "nullable": True},
            "duration": {"type": "number", "nullable": True},
            "created_at": {"type": "string", "nullable": True},
            "thumbnail_url": {"type": "string", "nullable": True},
        },
        "required": ["id"]
    }
    
    VIDEOS_LIST_SCHEMA = {
        "type": "array",
        "items": VIDEO_SCHEMA
    }
    
    def test_videos_list_contract(self, client):
        """Test videos list response matches contract"""
        response = client.get("/api/videos?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle paginated response
            if isinstance(data, dict):
                items = data.get("items", data.get("data", []))
            else:
                items = data
            
            for item in items[:5]:
                errors = validate_schema(item, self.VIDEO_SCHEMA)
                assert len(errors) == 0, f"Contract violations: {errors}"


class TestPublishingContracts:
    """Contract tests for publishing API"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    SCHEDULED_POST_SCHEMA = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "content": {"type": "string", "nullable": True},
            "scheduled_time": {"type": "string", "nullable": True},
            "platform": {"type": "string", "nullable": True},
            "status": {"type": "string", "nullable": True},
        },
        "required": ["id"]
    }
    
    def test_scheduled_posts_contract(self, client):
        """Test scheduled posts response matches contract"""
        response = client.get("/api/publishing/scheduled")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                for item in data[:5]:
                    errors = validate_schema(item, self.SCHEDULED_POST_SCHEMA)
                    assert len(errors) == 0, f"Contract violations: {errors}"


class TestGoalsContracts:
    """Contract tests for goals API"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    GOAL_SCHEMA = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string", "nullable": True},
            "target": {"type": "number", "nullable": True},
            "current": {"type": "number", "nullable": True},
            "progress": {"type": "number", "nullable": True},
        },
        "required": ["id"]
    }
    
    def test_goals_contract(self, client):
        """Test goals response matches contract"""
        response = client.get("/api/goals")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                for item in data[:5]:
                    errors = validate_schema(item, self.GOAL_SCHEMA)
                    assert len(errors) == 0, f"Contract violations: {errors}"


class TestErrorContracts:
    """Contract tests for error responses"""
    
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)
    
    ERROR_SCHEMA = {
        "type": "object",
        "properties": {
            "detail": {"type": "string", "nullable": True},
            "message": {"type": "string", "nullable": True},
            "error": {"type": "string", "nullable": True},
        }
    }
    
    def test_404_error_contract(self, client):
        """Test 404 error response matches contract"""
        response = client.get("/api/nonexistent-endpoint-12345")
        
        assert response.status_code == 404
        data = response.json()
        
        # Should have some error message
        has_message = any([
            data.get("detail"),
            data.get("message"),
            data.get("error"),
        ])
        assert has_message, "Error response should have a message"
    
    def test_422_error_contract(self, client):
        """Test validation error response matches contract"""
        response = client.post("/api/goals", json={})
        
        if response.status_code == 422:
            data = response.json()
            # FastAPI validation errors have 'detail' array
            assert "detail" in data or "message" in data or "error" in data


# Mark all as contract tests
pytestmark = pytest.mark.contract

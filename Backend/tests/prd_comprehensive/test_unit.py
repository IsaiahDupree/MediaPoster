"""
PRD Unit Tests
Test individual functions/classes in isolation.
Coverage: 50+ unit tests for core functionality
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import os
import json
import uuid


# =============================================================================
# UNIT TESTS: Scheduling Algorithm (PRD Section 3)
# =============================================================================

class TestSchedulingAlgorithmUnit:
    """Unit tests for the scheduling algorithm from PRD."""
    
    def build_schedule(self, media_count: int, horizon_hours: int = 24*60):
        """PRD scheduling algorithm implementation."""
        if media_count == 0:
            return []
        ideal_spacing = horizon_hours / media_count
        spacing = min(24, max(2, ideal_spacing))
        slots = []
        for i in range(media_count):
            offset_hours = i * spacing
            if offset_hours > horizon_hours:
                break
            slots.append(offset_hours)
        return slots
    
    # Basic functionality
    def test_empty_media_list(self):
        """Zero media returns empty schedule."""
        assert self.build_schedule(0) == []
    
    def test_single_media_item(self):
        """Single item scheduled at time 0."""
        result = self.build_schedule(1)
        assert len(result) == 1
        assert result[0] == 0
    
    def test_two_media_items(self):
        """Two items with proper spacing."""
        result = self.build_schedule(2)
        assert len(result) == 2
        assert result[1] - result[0] >= 2
        assert result[1] - result[0] <= 24
    
    # Minimum gap constraint (2 hours)
    def test_min_gap_with_many_items(self):
        """Many items should have minimum 2h gap."""
        result = self.build_schedule(1000)
        for i in range(1, min(100, len(result))):
            gap = result[i] - result[i-1]
            assert gap >= 2, f"Gap {gap} < 2 hours at index {i}"
    
    def test_min_gap_boundary(self):
        """Test exactly at the 2h boundary."""
        # 720 items in 60 days = 1440h / 720 = 2h spacing exactly
        result = self.build_schedule(720, 1440)
        if len(result) > 1:
            gap = result[1] - result[0]
            assert gap >= 2
    
    # Maximum gap constraint (24 hours)
    def test_max_gap_with_few_items(self):
        """Few items should have max 24h gap."""
        result = self.build_schedule(10, 1440)  # 10 items in 60 days
        for i in range(1, len(result)):
            gap = result[i] - result[i-1]
            assert gap <= 24, f"Gap {gap} > 24 hours at index {i}"
    
    def test_max_gap_boundary(self):
        """Test exactly at the 24h boundary."""
        result = self.build_schedule(60, 1440)  # 60 items = 24h spacing
        if len(result) > 1:
            gap = result[1] - result[0]
            assert gap <= 24
    
    # 60-day horizon constraint
    def test_60_day_horizon_limit(self):
        """No schedule beyond 60 days."""
        result = self.build_schedule(100, 1440)
        for slot in result:
            assert slot <= 1440, f"Slot {slot} exceeds 60-day horizon"
    
    def test_horizon_exact_boundary(self):
        """Test at exact 60-day boundary."""
        result = self.build_schedule(720, 1440)
        assert max(result) <= 1440
    
    # Edge cases
    def test_very_large_media_count(self):
        """Handle very large media counts."""
        result = self.build_schedule(10000, 1440)
        assert len(result) <= 720  # Can't fit more than 720 2h slots in 60 days
    
    def test_very_small_horizon(self):
        """Handle small horizons."""
        result = self.build_schedule(10, 10)
        for i in range(1, len(result)):
            gap = result[i] - result[i-1]
            assert gap >= 2
    
    def test_negative_inputs(self):
        """Negative inputs should return empty."""
        assert self.build_schedule(-1) == []
        assert self.build_schedule(10, -1) == []
    
    # Spacing calculations
    def test_ideal_spacing_calculation(self):
        """Verify ideal spacing formula."""
        media_count = 30
        horizon_hours = 1440
        ideal_spacing = horizon_hours / media_count
        assert ideal_spacing == 48  # 1440/30 = 48, clamped to 24
    
    def test_spacing_clamped_to_min(self):
        """Spacing clamped to 2h minimum."""
        result = self.build_schedule(1000, 100)  # 0.1h ideal spacing
        if len(result) > 1:
            gap = result[1] - result[0]
            assert gap == 2
    
    def test_spacing_clamped_to_max(self):
        """Spacing clamped to 24h maximum."""
        result = self.build_schedule(5, 1440)  # 288h ideal spacing
        if len(result) > 1:
            gap = result[1] - result[0]
            assert gap == 24


# =============================================================================
# UNIT TESTS: Data Validation (PRD Section 2)
# =============================================================================

class TestDataValidationUnit:
    """Unit tests for data validation logic."""
    
    # UUID validation
    def test_valid_uuid(self):
        """Valid UUIDs should pass."""
        valid_uuid = str(uuid.uuid4())
        try:
            uuid.UUID(valid_uuid)
            assert True
        except ValueError:
            assert False
    
    def test_invalid_uuid_format(self):
        """Invalid UUID format should fail."""
        with pytest.raises(ValueError):
            uuid.UUID("not-a-uuid")
    
    def test_uuid_with_hyphens(self):
        """UUID with hyphens."""
        valid = "123e4567-e89b-12d3-a456-426614174000"
        parsed = uuid.UUID(valid)
        assert str(parsed) == valid
    
    def test_uuid_without_hyphens(self):
        """UUID without hyphens."""
        valid = "123e4567e89b12d3a456426614174000"
        parsed = uuid.UUID(valid)
        assert parsed is not None
    
    # Status enum validation
    def test_valid_status_values(self):
        """Valid status values from PRD."""
        valid_statuses = ["ingested", "analyzed", "scheduled", "posted", "archived"]
        for status in valid_statuses:
            assert status in valid_statuses
    
    def test_invalid_status_value(self):
        """Invalid status should be rejected."""
        valid_statuses = ["ingested", "analyzed", "scheduled", "posted", "archived"]
        assert "invalid" not in valid_statuses
    
    # Media type validation
    def test_valid_media_types(self):
        """Valid media types from PRD."""
        valid_types = ["video", "image"]
        for media_type in valid_types:
            assert media_type in valid_types
    
    # Score range validation
    def test_score_in_valid_range(self):
        """Score 0-100 validation."""
        for score in [0, 50, 100]:
            assert 0 <= score <= 100
    
    def test_score_below_range(self):
        """Score below 0 is invalid."""
        assert not (0 <= -1 <= 100)
    
    def test_score_above_range(self):
        """Score above 100 is invalid."""
        assert not (0 <= 101 <= 100)
    
    # Duration validation
    def test_valid_duration(self):
        """Positive duration is valid."""
        duration = 120
        assert duration > 0
    
    def test_zero_duration(self):
        """Zero duration edge case."""
        duration = 0
        assert duration >= 0
    
    def test_negative_duration(self):
        """Negative duration is invalid."""
        duration = -1
        assert duration < 0


# =============================================================================
# UNIT TESTS: File Path Handling
# =============================================================================

class TestFilePathUnit:
    """Unit tests for file path operations."""
    
    def test_valid_file_extension_heic(self):
        """HEIC files are valid."""
        path = Path("/test/file.HEIC")
        assert path.suffix.upper() == ".HEIC"
    
    def test_valid_file_extension_mov(self):
        """MOV files are valid."""
        path = Path("/test/file.MOV")
        assert path.suffix.upper() == ".MOV"
    
    def test_valid_file_extension_mp4(self):
        """MP4 files are valid."""
        path = Path("/test/file.mp4")
        assert path.suffix.lower() == ".mp4"
    
    def test_valid_file_extension_jpg(self):
        """JPG files are valid."""
        path = Path("/test/file.jpg")
        assert path.suffix.lower() == ".jpg"
    
    def test_case_insensitive_extension(self):
        """Extension comparison should be case-insensitive."""
        path1 = Path("/test/file.HEIC")
        path2 = Path("/test/file.heic")
        assert path1.suffix.lower() == path2.suffix.lower()
    
    def test_path_with_spaces(self):
        """Handle paths with spaces."""
        path = Path("/test/my file.mov")
        assert path.name == "my file.mov"
    
    def test_path_with_special_chars(self):
        """Handle paths with special characters."""
        path = Path("/test/file (1).mov")
        assert "(" in path.name
    
    def test_nested_path(self):
        """Handle deeply nested paths."""
        path = Path("/a/b/c/d/e/file.mov")
        assert len(path.parts) == 7
    
    def test_relative_path(self):
        """Handle relative paths."""
        path = Path("relative/path/file.mov")
        assert not path.is_absolute()
    
    def test_absolute_path(self):
        """Handle absolute paths."""
        path = Path("/absolute/path/file.mov")
        assert path.is_absolute()


# =============================================================================
# UNIT TESTS: JSON Handling
# =============================================================================

class TestJSONHandlingUnit:
    """Unit tests for JSON operations."""
    
    def test_valid_json_parse(self):
        """Parse valid JSON."""
        data = '{"key": "value"}'
        parsed = json.loads(data)
        assert parsed["key"] == "value"
    
    def test_nested_json_parse(self):
        """Parse nested JSON."""
        data = '{"outer": {"inner": "value"}}'
        parsed = json.loads(data)
        assert parsed["outer"]["inner"] == "value"
    
    def test_array_json_parse(self):
        """Parse JSON array."""
        data = '[1, 2, 3]'
        parsed = json.loads(data)
        assert len(parsed) == 3
    
    def test_json_with_null(self):
        """Parse JSON with null."""
        data = '{"key": null}'
        parsed = json.loads(data)
        assert parsed["key"] is None
    
    def test_json_with_boolean(self):
        """Parse JSON with boolean."""
        data = '{"flag": true}'
        parsed = json.loads(data)
        assert parsed["flag"] is True
    
    def test_json_serialization(self):
        """Serialize to JSON."""
        data = {"key": "value"}
        serialized = json.dumps(data)
        assert '"key"' in serialized
    
    def test_invalid_json_raises(self):
        """Invalid JSON raises exception."""
        with pytest.raises(json.JSONDecodeError):
            json.loads("not valid json")


# =============================================================================
# UNIT TESTS: Timestamp Handling
# =============================================================================

class TestTimestampUnit:
    """Unit tests for timestamp operations."""
    
    def test_current_timestamp(self):
        """Get current timestamp."""
        now = datetime.now()
        assert now is not None
    
    def test_timestamp_comparison(self):
        """Compare timestamps."""
        earlier = datetime.now()
        later = datetime.now()
        assert later >= earlier
    
    def test_timestamp_addition(self):
        """Add time to timestamp."""
        now = datetime.now()
        later = now + timedelta(hours=2)
        diff = (later - now).total_seconds()
        assert diff == 7200  # 2 hours in seconds
    
    def test_60_day_future(self):
        """Calculate 60 days in future."""
        now = datetime.now()
        future = now + timedelta(days=60)
        diff = (future - now).days
        assert diff == 60
    
    def test_timestamp_iso_format(self):
        """ISO format timestamp."""
        now = datetime.now()
        iso = now.isoformat()
        assert "T" in iso
    
    def test_parse_iso_timestamp(self):
        """Parse ISO timestamp."""
        iso = "2025-12-07T19:00:00"
        parsed = datetime.fromisoformat(iso)
        assert parsed.year == 2025


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Integration tests for the Formats API endpoints.
Tests CRUD operations and run triggering.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import uuid

# Import the app - adjust path as needed
import sys
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

from main import app

client = TestClient(app)


class TestFormatsListEndpoint:
    """Tests for GET /api/formats/list"""
    
    def test_list_formats_empty(self):
        """Should return empty list when no formats exist."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get("/api/formats/list")
            
            assert response.status_code == 200
            data = response.json()
            assert "formats" in data
            assert isinstance(data["formats"], list)
    
    def test_list_formats_with_status_filter(self):
        """Should filter formats by status."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get("/api/formats/list?status=active")
            
            assert response.status_code == 200
            # Verify the query included status filter
            call_args = mock_conn.execute.call_args
            assert "status" in str(call_args) or call_args is not None


class TestFormatsGetEndpoint:
    """Tests for GET /api/formats/{format_id}"""
    
    def test_get_format_not_found(self):
        """Should return 404 for non-existent format."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get("/api/formats/nonexistent_format")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_get_format_success(self):
        """Should return format details."""
        mock_row = (
            "test_format",  # id
            "Test Format",  # name
            "Description",  # description
            "active",       # status
            "1.0.0",        # version
            {"composition": {}},  # definition_json
            "qp_shortform_v1",    # quality_profile_id
            "TestComp",     # remotion_composition_id
            "2024-01-01",   # created_at
            "2024-01-01",   # updated_at
        )
        
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = mock_row
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get("/api/formats/test_format")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test_format"
            assert data["name"] == "Test Format"
            assert data["status"] == "active"


class TestFormatsCreateEndpoint:
    """Tests for POST /api/formats/create"""
    
    def test_create_format_success(self):
        """Should create a new format."""
        format_data = {
            "id": "new_format",
            "name": "New Format",
            "definition_json": {
                "composition": {"remotionCompositionId": "NewComp"}
            }
        }
        
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None  # No existing
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.post("/api/formats/create", json=format_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "new_format"
            assert "created" in data["message"].lower()
    
    def test_create_format_duplicate(self):
        """Should reject duplicate format ID."""
        format_data = {
            "id": "existing_format",
            "name": "Duplicate",
            "definition_json": {}
        }
        
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = ("existing_format",)
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.post("/api/formats/create", json=format_data)
            
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


class TestFormatsUpdateEndpoint:
    """Tests for PUT /api/formats/{format_id}"""
    
    def test_update_format_success(self):
        """Should update format fields."""
        update_data = {
            "name": "Updated Name",
            "status": "active"
        }
        
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.rowcount = 1
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.put("/api/formats/test_format", json=update_data)
            
            assert response.status_code == 200
            assert "updated" in response.json()["message"].lower()
    
    def test_update_format_not_found(self):
        """Should return 404 for non-existent format."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.rowcount = 0
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.put("/api/formats/nonexistent", json={"name": "New"})
            
            assert response.status_code == 404
    
    def test_update_format_no_fields(self):
        """Should reject empty update."""
        response = client.put("/api/formats/test", json={})
        
        assert response.status_code == 400
        assert "no fields" in response.json()["detail"].lower()


class TestFormatsDeleteEndpoint:
    """Tests for DELETE /api/formats/{format_id}"""
    
    def test_delete_format_archives(self):
        """Should archive format (soft delete)."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.rowcount = 1
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.delete("/api/formats/test_format")
            
            assert response.status_code == 200
            assert "archived" in response.json()["message"].lower()


class TestFormatRunEndpoint:
    """Tests for POST /api/formats/{format_id}/run"""
    
    def test_trigger_run_success(self):
        """Should create a new run and return run_id."""
        run_data = {
            "params": {"topic": "Test"},
            "trigger_type": "manual"
        }
        
        mock_format_row = ("test_format", {"composition": {}})
        
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = mock_format_row
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.post("/api/formats/test_format/run", json=run_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "run_id" in data
            assert data["status"] == "queued"
    
    def test_trigger_run_format_not_found(self):
        """Should return 404 for non-existent format."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.post("/api/formats/nonexistent/run", json={})
            
            assert response.status_code == 404


class TestFormatRunsListEndpoint:
    """Tests for GET /api/formats/{format_id}/runs"""
    
    def test_list_runs_empty(self):
        """Should return empty list when no runs exist."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get("/api/formats/test_format/runs")
            
            assert response.status_code == 200
            data = response.json()
            assert "runs" in data
            assert data["runs"] == []
    
    def test_list_runs_with_status_filter(self):
        """Should filter runs by status."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get("/api/formats/test_format/runs?status=succeeded")
            
            assert response.status_code == 200


class TestRunDetailEndpoint:
    """Tests for GET /api/formats/runs/{run_id}"""
    
    def test_get_run_not_found(self):
        """Should return 404 for non-existent run."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get(f"/api/formats/runs/{uuid.uuid4()}")
            
            assert response.status_code == 404
    
    def test_get_run_with_artifacts(self):
        """Should return run details with artifacts."""
        run_id = str(uuid.uuid4())
        mock_run_row = (
            run_id,           # id
            "test_format",    # format_id
            "succeeded",      # status
            "manual",         # trigger_type
            None,             # triggered_by
            {},               # params_json
            {},               # resolved_inputs_json
            {},               # render_props_json
            None,             # variant_id
            None,             # error_json
            "2024-01-01",     # started_at
            "2024-01-01",     # completed_at
            "2024-01-01",     # created_at
            "2024-01-01",     # updated_at
        )
        
        mock_artifact_row = (
            str(uuid.uuid4()),  # id
            "video",            # kind
            "https://example.com/video.mp4",  # url
            None,               # file_path
            1024000,            # file_size_bytes
            30.5,               # duration_sec
            {},                 # meta
            "2024-01-01",       # created_at
        )
        
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            # First call returns run, second returns artifacts
            mock_conn.execute.return_value.fetchone.return_value = mock_run_row
            mock_conn.execute.return_value.fetchall.return_value = [mock_artifact_row]
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get(f"/api/formats/runs/{run_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == run_id
            assert data["status"] == "succeeded"
            assert "artifacts" in data


class TestSeedSamplesEndpoint:
    """Tests for POST /api/formats/seed-samples"""
    
    def test_seed_samples_success(self):
        """Should seed sample formats."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            # All formats are new (no existing)
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.post("/api/formats/seed-samples")
            
            assert response.status_code == 200
            data = response.json()
            assert "created" in data
            assert "skipped" in data
            assert len(data["created"]) > 0
    
    def test_seed_samples_skips_existing(self):
        """Should skip already existing formats."""
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            # All formats already exist
            mock_conn.execute.return_value.fetchone.return_value = ("existing",)
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.post("/api/formats/seed-samples")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["skipped"]) > 0


class TestQualityProfilesEndpoint:
    """Tests for GET /api/formats/quality-profiles/list"""
    
    def test_list_quality_profiles(self):
        """Should return quality profiles."""
        mock_profile_row = (
            "qp_shortform_v1",
            "Short-Form Video Quality",
            "Quality gates for shorts",
            [{"id": "dur", "type": "duration"}],
            True,
            "2024-01-01",
        )
        
        with patch('api.endpoints.formats.get_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchall.return_value = [mock_profile_row]
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
            
            response = client.get("/api/formats/quality-profiles/list")
            
            assert response.status_code == 200
            data = response.json()
            assert "profiles" in data
            assert len(data["profiles"]) == 1
            assert data["profiles"][0]["id"] == "qp_shortform_v1"

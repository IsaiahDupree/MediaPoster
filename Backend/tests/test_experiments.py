"""
Tests for Experiments API Endpoints
Tests experiment creation, management, variants, backlog, and learnings
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json


class TestExperimentsStats:
    """Tests for GET /api/experiments/stats endpoint"""
    
    def test_get_stats_returns_all_fields(self, client):
        """Test that stats endpoint returns all required fields"""
        response = client.get("/api/experiments/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert 'active' in data
        assert 'completed_last_7' in data
        assert 'completed_last_30' in data
        assert 'win_rate' in data
        assert 'avg_uplift' in data
        assert 'biggest_winners' in data
    
    def test_stats_values_are_non_negative(self, client):
        """Test that all stats are non-negative"""
        response = client.get("/api/experiments/stats")
        data = response.json()
        
        assert data['active'] >= 0
        assert data['completed_last_7'] >= 0
        assert data['completed_last_30'] >= 0
        assert data['win_rate'] >= 0
        assert data['avg_uplift'] >= 0


class TestExperimentsList:
    """Tests for GET /api/experiments/list endpoint"""
    
    def test_list_experiments_returns_array(self, client):
        """Test that list endpoint returns experiments array"""
        response = client.get("/api/experiments/list")
        assert response.status_code == 200
        
        data = response.json()
        assert 'experiments' in data
        assert 'total' in data
        assert isinstance(data['experiments'], list)
    
    def test_list_with_status_filter(self, client):
        """Test filtering experiments by status"""
        response = client.get("/api/experiments/list?status=running")
        assert response.status_code == 200
        
        data = response.json()
        for exp in data['experiments']:
            assert exp['status'] == 'running'
    
    def test_list_with_limit(self, client):
        """Test limiting number of experiments returned"""
        response = client.get("/api/experiments/list?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['experiments']) <= 5


class TestCreateExperiment:
    """Tests for POST /api/experiments/create endpoint"""
    
    def test_create_experiment_success(self, client):
        """Test creating a new experiment"""
        payload = {
            "name": "Test Hook Experiment",
            "hypothesis": "A question hook will increase retention by 20%",
            "type": "hook",
            "primary_metric": "hook_rate_3s",
            "variants": [
                {"name": "Control", "description": "Original hook", "is_control": True},
                {"name": "Question Hook", "description": "Starts with a question", "is_control": False}
            ],
            "traffic_split": "even",
            "platform_type": "organic"
        }
        
        response = client.post("/api/experiments/create", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert 'id' in data
        assert data['status'] == 'draft'
    
    def test_create_experiment_with_minimum_fields(self, client):
        """Test creating experiment with minimum required fields"""
        payload = {
            "name": "Minimal Test",
            "hypothesis": "Test hypothesis",
            "type": "caption",
            "primary_metric": "save_rate",
            "variants": [
                {"name": "A", "description": "Control"},
                {"name": "B", "description": "Variant"}
            ]
        }
        
        response = client.post("/api/experiments/create", json=payload)
        assert response.status_code == 200


class TestExperimentLifecycle:
    """Tests for experiment start, stop, complete lifecycle"""
    
    def test_start_experiment(self, client):
        """Test starting a draft experiment"""
        # First create an experiment
        create_payload = {
            "name": "Lifecycle Test",
            "hypothesis": "Test hypothesis",
            "type": "hook",
            "primary_metric": "hook_rate_3s",
            "variants": [
                {"name": "A", "description": "Control", "is_control": True},
                {"name": "B", "description": "Variant"}
            ]
        }
        
        create_res = client.post("/api/experiments/create", json=create_payload)
        exp_id = create_res.json()['id']
        
        # Start it
        start_res = client.post(f"/api/experiments/{exp_id}/start")
        assert start_res.status_code == 200
        
        data = start_res.json()
        assert data['status'] == 'running'
    
    def test_stop_experiment(self, client):
        """Test stopping a running experiment"""
        # Create and start
        create_payload = {
            "name": "Stop Test",
            "hypothesis": "Test",
            "type": "caption",
            "primary_metric": "save_rate",
            "variants": [{"name": "A", "description": "Control"}, {"name": "B", "description": "Var"}]
        }
        
        create_res = client.post("/api/experiments/create", json=create_payload)
        exp_id = create_res.json()['id']
        client.post(f"/api/experiments/{exp_id}/start")
        
        # Stop it
        stop_res = client.post(f"/api/experiments/{exp_id}/stop")
        assert stop_res.status_code == 200
        assert stop_res.json()['status'] == 'stopped'
    
    def test_complete_experiment_with_winner(self, client):
        """Test completing an experiment and declaring a winner"""
        # Create and start
        create_payload = {
            "name": "Complete Test",
            "hypothesis": "Test",
            "type": "cta",
            "primary_metric": "comment_rate",
            "variants": [{"name": "A", "description": "Control"}, {"name": "B", "description": "Winner"}]
        }
        
        create_res = client.post("/api/experiments/create", json=create_payload)
        exp_id = create_res.json()['id']
        client.post(f"/api/experiments/{exp_id}/start")
        
        # Get variant IDs
        exp_res = client.get(f"/api/experiments/{exp_id}")
        variants = exp_res.json()['variants']
        winner_id = variants[1]['id'] if len(variants) > 1 else variants[0]['id']
        
        # Complete with winner
        complete_res = client.post(f"/api/experiments/{exp_id}/complete?winner_variant_id={winner_id}")
        assert complete_res.status_code == 200
        assert complete_res.json()['status'] == 'completed'


class TestExperimentVariants:
    """Tests for experiment variant management"""
    
    def test_get_experiment_with_variants(self, client):
        """Test getting experiment details includes variants"""
        # Create experiment
        create_payload = {
            "name": "Variant Test",
            "hypothesis": "Test",
            "type": "length",
            "primary_metric": "completion_rate",
            "variants": [
                {"name": "Short (15s)", "description": "15 second version"},
                {"name": "Medium (30s)", "description": "30 second version"},
                {"name": "Long (60s)", "description": "60 second version"}
            ]
        }
        
        create_res = client.post("/api/experiments/create", json=create_payload)
        exp_id = create_res.json()['id']
        
        # Get experiment
        response = client.get(f"/api/experiments/{exp_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data['variants']) == 3
        
        # Check variant structure
        for variant in data['variants']:
            assert 'id' in variant
            assert 'name' in variant
            assert 'description' in variant
            assert 'impressions' in variant
            assert 'views' in variant
            assert 'is_control' in variant
    
    def test_update_variant_metrics(self, client):
        """Test updating metrics for a variant"""
        # Create experiment
        create_payload = {
            "name": "Metrics Test",
            "hypothesis": "Test",
            "type": "hook",
            "primary_metric": "hook_rate_3s",
            "variants": [{"name": "A", "description": "Control"}, {"name": "B", "description": "Test"}]
        }
        
        create_res = client.post("/api/experiments/create", json=create_payload)
        exp_id = create_res.json()['id']
        
        # Get variant ID
        exp_res = client.get(f"/api/experiments/{exp_id}")
        variant_id = exp_res.json()['variants'][0]['id']
        
        # Update metrics
        update_res = client.put(
            f"/api/experiments/{exp_id}/variant/{variant_id}/metrics",
            params={"impressions": 10000, "views": 8000, "primary_metric_value": 75.5}
        )
        assert update_res.status_code == 200


class TestExperimentBacklog:
    """Tests for experiment backlog management"""
    
    def test_list_backlog(self, client):
        """Test listing backlog ideas"""
        response = client.get("/api/experiments/backlog/list")
        assert response.status_code == 200
        
        data = response.json()
        assert 'ideas' in data
        assert isinstance(data['ideas'], list)
    
    def test_add_to_backlog(self, client):
        """Test adding an idea to the backlog"""
        payload = {
            "hypothesis": "Adding emojis to captions will increase engagement",
            "target_metric": "comment_rate",
            "expected_impact": "M",
            "effort": "S",
            "confidence": "M"
        }
        
        response = client.post("/api/experiments/backlog/add", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert 'id' in data
        assert 'priority_score' in data
        assert data['priority_score'] > 0
    
    def test_backlog_priority_scoring(self, client):
        """Test that priority score is calculated correctly"""
        # High impact, low effort, high confidence = high priority
        high_priority = {
            "hypothesis": "High priority test",
            "target_metric": "hook_rate_3s",
            "expected_impact": "L",
            "effort": "S",
            "confidence": "L"
        }
        
        # Low impact, high effort, low confidence = low priority
        low_priority = {
            "hypothesis": "Low priority test",
            "target_metric": "save_rate",
            "expected_impact": "S",
            "effort": "L",
            "confidence": "S"
        }
        
        high_res = client.post("/api/experiments/backlog/add", json=high_priority)
        low_res = client.post("/api/experiments/backlog/add", json=low_priority)
        
        assert high_res.json()['priority_score'] > low_res.json()['priority_score']
    
    def test_generate_ideas_from_analytics(self, client):
        """Test AI-generated ideas from analytics"""
        response = client.post("/api/experiments/backlog/generate-ideas")
        assert response.status_code == 200
        
        data = response.json()
        assert 'generated' in data
        assert 'ideas' in data


class TestExperimentLearnings:
    """Tests for experiment learnings/insights"""
    
    def test_get_learnings(self, client):
        """Test getting compiled learnings"""
        response = client.get("/api/experiments/learnings")
        assert response.status_code == 200
        
        data = response.json()
        assert 'learnings' in data
        assert 'best_hooks' in data


class TestExperimentNotFound:
    """Tests for handling non-existent experiments"""
    
    def test_get_nonexistent_experiment(self, client):
        """Test getting an experiment that doesn't exist"""
        response = client.get("/api/experiments/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


# Fixtures
@pytest.fixture
def client():
    """Create test client"""
    from main import app
    return TestClient(app)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for Agent Framework Services
===================================
Unit tests for dispatcher, run_manager, and service handlers.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# DISPATCHER TESTS
# =============================================================================

class TestDispatcher:
    """Tests for the topic dispatcher."""
    
    def test_topics_dictionary_exists(self):
        """Test that TOPICS dictionary is defined."""
        from services.agent_framework.dispatcher import TOPICS
        assert isinstance(TOPICS, dict)
        assert len(TOPICS) > 0
    
    def test_required_topics_exist(self):
        """Test that required topics are defined."""
        from services.agent_framework.dispatcher import TOPICS
        
        required_topics = [
            "RUN_REQUESTED",
            "RUN_QUEUED",
            "RUN_STARTED",
            "RUN_COMPLETED",
            "RUN_FAILED",
        ]
        
        for topic in required_topics:
            assert topic in TOPICS, f"Missing required topic: {topic}"
    
    def test_narrative_topics_exist(self):
        """Test that narrative topics are defined."""
        from services.agent_framework.dispatcher import TOPICS
        
        narrative_topics = [
            "NARRATIVE_WEEKLY_GENERATE_PLAN",
            "NARRATIVE_DAILY_EXECUTE_SCHEDULE",
            "NARRATIVE_WEEKLY_REFLECT",
        ]
        
        for topic in narrative_topics:
            assert topic in TOPICS, f"Missing narrative topic: {topic}"
    
    def test_experiments_topics_exist(self):
        """Test that experiments topics are defined."""
        from services.agent_framework.dispatcher import TOPICS
        
        experiments_topics = [
            "EXPERIMENTS_WEEKLY_PLAN",
            "EXPERIMENTS_DAILY_ANALYZE_RESULTS",
            "EXPERIMENTS_PROMOTE_TO_NARRATIVE",
        ]
        
        for topic in experiments_topics:
            assert topic in TOPICS, f"Missing experiments topic: {topic}"
    
    def test_get_dispatcher_returns_instance(self):
        """Test that get_dispatcher returns a TopicDispatcher instance."""
        from services.agent_framework.dispatcher import get_dispatcher, TopicDispatcher
        dispatcher = get_dispatcher()
        assert isinstance(dispatcher, TopicDispatcher)


# =============================================================================
# RUN MANAGER TESTS
# =============================================================================

class TestRunManager:
    """Tests for the RunManager."""
    
    def test_get_run_manager_returns_singleton(self):
        """Test that get_run_manager returns a singleton."""
        from services.agent_framework import get_run_manager
        
        rm1 = get_run_manager()
        rm2 = get_run_manager()
        assert rm1 is rm2
    
    def test_run_manager_has_required_methods(self):
        """Test that RunManager has all required methods."""
        from services.agent_framework import get_run_manager
        
        rm = get_run_manager()
        
        required_methods = [
            "create_run",
            "start_run",
            "complete_run",
            "fail_run",
            "pause_run",
            "cancel_run",
            "update_progress",
            "start_step",
            "complete_step",
            "emit_event",
            "emit_thought",
            "emit_decision",
            "emit_action",
            "create_artifact",
            "get_run",
            "get_run_steps",
            "get_run_timeline",
            "get_run_artifacts",
            "get_recent_runs",
        ]
        
        for method in required_methods:
            assert hasattr(rm, method), f"RunManager missing method: {method}"
            assert callable(getattr(rm, method)), f"RunManager.{method} is not callable"


# =============================================================================
# SERVICE HANDLER TESTS
# =============================================================================

class TestNarrativeService:
    """Tests for narrative service handlers."""
    
    def test_narrative_handlers_exist(self):
        """Test that narrative service handlers are importable."""
        from services.agent_framework.services.narrative_service import (
            run_narrative_generate_plan,
            run_narrative_reflect,
            run_narrative_execute,
        )
        
        assert callable(run_narrative_generate_plan)
        assert callable(run_narrative_reflect)
        assert callable(run_narrative_execute)


class TestExperimentsService:
    """Tests for experiments service handlers."""
    
    def test_experiments_handlers_exist(self):
        """Test that experiments service handlers are importable."""
        from services.agent_framework.services.experiments_service import (
            run_experiments_plan,
            run_experiments_analyze,
            run_experiments_promote,
        )
        
        assert callable(run_experiments_plan)
        assert callable(run_experiments_analyze)
        assert callable(run_experiments_promote)
    
    def test_experiments_helpers_exist(self):
        """Test that experiments helper functions are importable."""
        from services.agent_framework.services.experiments_service import (
            get_active_experiments,
            get_running_hypotheses,
            create_content_pattern,
        )
        
        assert callable(get_active_experiments)
        assert callable(get_running_hypotheses)
        assert callable(create_content_pattern)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

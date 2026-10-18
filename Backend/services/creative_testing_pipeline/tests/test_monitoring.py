"""
Tests for ACTP Monitoring Module
"""

import pytest

from services.creative_testing_pipeline.monitoring import (
    CostTracker,
    ErrorTracker,
    LatencyTracker,
    CorrelationLogger,
)


class TestLatencyTracker:
    """Test latency tracking per pipeline step."""

    @pytest.mark.asyncio
    async def test_track_records_timing(self):
        tracker = LatencyTracker()
        tracker.reset()
        async with tracker.track("test_step"):
            pass  # instant
        stats = tracker.get_stats()
        assert "test_step" in stats
        assert stats["test_step"]["count"] == 1
        assert stats["test_step"]["avg_ms"] >= 0

    @pytest.mark.asyncio
    async def test_multiple_timings(self):
        tracker = LatencyTracker()
        tracker.reset()
        for _ in range(5):
            async with tracker.track("multi"):
                pass
        stats = tracker.get_stats()
        assert stats["multi"]["count"] == 5

    def test_empty_stats(self):
        tracker = LatencyTracker()
        tracker.reset()
        assert tracker.get_stats() == {}

    def test_reset_clears(self):
        tracker = LatencyTracker()
        tracker._timings["x"] = [1.0, 2.0]
        tracker.reset()
        assert tracker.get_stats() == {}


class TestErrorTracker:
    """Test error rate tracking per module."""

    def test_record_error(self):
        tracker = ErrorTracker()
        tracker.reset()
        tracker.record_error("creative", ValueError("test"), "generation")
        rates = tracker.get_error_rates()
        assert rates["total_errors"] == 1
        assert rates["by_module"]["creative"] == 1

    def test_multiple_modules(self):
        tracker = ErrorTracker()
        tracker.reset()
        tracker.record_error("creative", ValueError("a"))
        tracker.record_error("publisher", RuntimeError("b"))
        tracker.record_error("creative", TypeError("c"))
        rates = tracker.get_error_rates()
        assert rates["total_errors"] == 3
        assert rates["by_module"]["creative"] == 2
        assert rates["by_module"]["publisher"] == 1

    def test_recent_errors_capped(self):
        tracker = ErrorTracker()
        tracker.reset()
        for i in range(150):
            tracker.record_error("test", ValueError(f"err_{i}"))
        assert len(tracker._errors["test"]) <= 100

    def test_reset_clears_all(self):
        tracker = ErrorTracker()
        tracker.record_error("x", ValueError("y"))
        tracker.reset()
        rates = tracker.get_error_rates()
        assert rates["total_errors"] == 0


class TestCostTracker:
    """Test cost estimation and tracking."""

    def test_estimate_sora_cost(self):
        tracker = CostTracker()
        est = tracker.estimate_generation_cost("sora", 5)
        assert est["provider"] == "sora"
        assert est["count"] == 5
        assert est["total_estimated_cents"] > 0
        assert est["total_estimated_usd"] == est["total_estimated_cents"] / 100

    def test_estimate_includes_brief_cost(self):
        tracker = CostTracker()
        with_brief = tracker.estimate_generation_cost("sora", 1, include_brief=True)
        without_brief = tracker.estimate_generation_cost("sora", 1, include_brief=False)
        assert with_brief["total_estimated_cents"] > without_brief["total_estimated_cents"]

    def test_estimate_unknown_provider(self):
        tracker = CostTracker()
        est = tracker.estimate_generation_cost("unknown", 3)
        assert est["generation_cost_cents"] == 0

    def test_record_cost_accumulates(self):
        tracker = CostTracker()
        tracker.record_cost("camp-1", "sora_gen", 100)
        tracker.record_cost("camp-1", "brief_gen", 25)
        assert tracker._session_costs["camp-1"] == 125


class TestCorrelationLogger:
    """Test structured logging."""

    def test_get_correlation_id_format(self):
        cid = CorrelationLogger.get_correlation_id()
        assert isinstance(cid, str)
        assert len(cid) == 8

    def test_unique_ids(self):
        ids = {CorrelationLogger.get_correlation_id() for _ in range(100)}
        assert len(ids) == 100  # All unique

"""
Unit tests for Bandit Allocator Service (AUTO-002)
===================================================
Tests Thompson Sampling allocation algorithm.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch

from services.bandit_allocator import (
    BanditAllocator,
    TemplateStats,
    AllocationBucket
)


@pytest.fixture
def reset_singleton():
    """Reset BanditAllocator singleton between tests"""
    BanditAllocator._instance = None
    yield
    BanditAllocator._instance = None


@pytest.fixture
def allocator(reset_singleton):
    """Create BanditAllocator instance"""
    allocator = BanditAllocator.get_instance()
    return allocator


@pytest.fixture
def mock_event_bus():
    """Mock event bus"""
    with patch('services.bandit_allocator.EventBus') as mock:
        bus_instance = Mock()
        bus_instance.publish = AsyncMock()
        bus_instance.subscribe = Mock()
        bus_instance.set_source = Mock()
        mock.get_instance.return_value = bus_instance
        yield bus_instance


class TestBanditAllocatorInit:
    """Test bandit allocator initialization"""

    def test_singleton(self, reset_singleton):
        """Should enforce singleton pattern"""
        allocator1 = BanditAllocator.get_instance()
        allocator2 = BanditAllocator.get_instance()

        assert allocator1 is allocator2

    def test_init_raises_on_direct_instantiation(self, reset_singleton):
        """Should raise error on direct instantiation after singleton created"""
        _ = BanditAllocator.get_instance()

        with pytest.raises(RuntimeError, match="Use BanditAllocator.get_instance"):
            BanditAllocator()

    def test_default_config(self, allocator):
        """Should initialize with correct default config"""
        assert allocator.winner_weight == 0.70
        assert allocator.promising_weight == 0.20
        assert allocator.experiment_weight == 0.10
        assert allocator.reward_threshold == 0.5
        assert allocator.min_allocation == 0.01
        assert allocator.max_allocation == 0.30


class TestThompsonSampling:
    """Test Thompson Sampling algorithm"""

    def test_sample_beta_returns_valid_probability(self, allocator):
        """Should return value in [0, 1]"""
        for _ in range(100):
            sample = allocator._sample_beta(alpha=5, beta=3)
            assert 0.0 <= sample <= 1.0

    def test_sample_beta_with_high_wins(self, allocator):
        """Should sample higher values with more wins"""
        samples_high_wins = [allocator._sample_beta(alpha=50, beta=10) for _ in range(100)]
        samples_low_wins = [allocator._sample_beta(alpha=10, beta=50) for _ in range(100)]

        avg_high = sum(samples_high_wins) / len(samples_high_wins)
        avg_low = sum(samples_low_wins) / len(samples_low_wins)

        assert avg_high > avg_low

    def test_apply_thompson_sampling(self, allocator):
        """Should assign theta_sample and confidence to all templates"""
        stats = [
            TemplateStats(
                template_id=uuid4(),
                template_name=f"Template {i}",
                awareness_level="problem_aware",
                wins=10 + i * 2,
                losses=5,
                total_uses=15 + i * 2
            )
            for i in range(5)
        ]

        result = allocator._apply_thompson_sampling(stats)

        for s in result:
            assert 0.0 <= s.theta_sample <= 1.0
            assert 0.0 <= s.confidence <= 1.0

    def test_confidence_increases_with_samples(self, allocator):
        """Should have higher confidence with more samples"""
        stats_low_samples = TemplateStats(
            template_id=uuid4(),
            template_name="Low Samples",
            awareness_level="problem_aware",
            wins=5,
            losses=5,
            total_uses=10
        )

        stats_high_samples = TemplateStats(
            template_id=uuid4(),
            template_name="High Samples",
            awareness_level="problem_aware",
            wins=50,
            losses=50,
            total_uses=100
        )

        result = allocator._apply_thompson_sampling([stats_low_samples, stats_high_samples])

        assert result[1].confidence > result[0].confidence


class TestBucketAssignment:
    """Test allocation bucket assignment"""

    def test_assign_buckets_top_20_percent_are_winners(self, allocator):
        """Should assign top 20% to winner bucket"""
        stats = [
            TemplateStats(
                template_id=uuid4(),
                template_name=f"Template {i}",
                awareness_level="problem_aware",
                total_uses=20,
                theta_sample=0.9 - i * 0.05  # Decreasing scores
            )
            for i in range(10)
        ]

        result = allocator._assign_buckets(stats)

        winners = [s for s in result if s.bucket == AllocationBucket.WINNER.value]
        assert len(winners) == 2  # 20% of 10 = 2

    def test_assign_buckets_untested_templates(self, allocator):
        """Should assign untested bucket to templates with < 5 uses"""
        # Create enough templates to test bucketing properly (need at least 5 for percentile ranking)
        stats = [
            TemplateStats(
                template_id=uuid4(),
                template_name=f"Template {i}",
                awareness_level="problem_aware",
                total_uses=20 if i < 5 else 3,  # First 5 are tested, rest are untested
                theta_sample=0.9 - i * 0.05  # Decreasing scores
            )
            for i in range(10)
        ]

        result = allocator._assign_buckets(stats)

        # Check that untested templates (< 5 uses) get untested bucket
        untested_templates = [s for s in result if s.total_uses < 5]
        for template in untested_templates:
            assert template.bucket == AllocationBucket.UNTESTED.value


class TestAllocationComputation:
    """Test allocation probability computation"""

    def test_compute_allocations_from_buckets_sums_to_one(self, allocator):
        """Should compute allocations that sum to ~1.0"""
        stats = [
            TemplateStats(
                template_id=uuid4(),
                template_name=f"Template {i}",
                awareness_level="problem_aware",
                bucket=AllocationBucket.WINNER.value if i < 2 else
                       AllocationBucket.PROMISING.value if i < 5 else
                       AllocationBucket.EXPERIMENT.value,
                theta_sample=0.9 - i * 0.05,
                total_uses=20
            )
            for i in range(10)
        ]

        result = allocator._compute_allocations_from_buckets(stats)

        total = sum(s.allocation for s in result)
        assert abs(total - 1.0) < 0.01  # Allow small floating point error

    def test_winners_get_70_percent_total(self, allocator):
        """Should allocate ~70% to winner bucket"""
        stats = [
            TemplateStats(
                template_id=uuid4(),
                template_name=f"Template {i}",
                awareness_level="problem_aware",
                bucket=AllocationBucket.WINNER.value if i < 2 else AllocationBucket.EXPERIMENT.value,
                theta_sample=0.5,
                total_uses=20
            )
            for i in range(10)
        ]

        result = allocator._compute_allocations_from_buckets(stats)

        winner_allocation = sum(s.allocation for s in result if s.bucket == AllocationBucket.WINNER.value)
        assert abs(winner_allocation - 0.70) < 0.05

    def test_apply_allocation_constraints(self, allocator):
        """Should normalize allocations and enforce constraints"""
        stats = [
            TemplateStats(
                template_id=uuid4(),
                template_name=f"Template {i}",
                awareness_level="problem_aware",
                allocation=0.15 if i < 3 else 0.05  # Some templates get more allocation
            )
            for i in range(10)
        ]

        result = allocator._apply_allocation_constraints(stats)

        # Check that all allocations are positive
        for s in result:
            assert s.allocation > 0, f"Allocation {s.allocation} <= 0"

        # Check normalization (should sum to ~1.0)
        total = sum(s.allocation for s in result)
        assert abs(total - 1.0) < 0.01, f"Total allocation {total} != 1.0"


class TestCaching:
    """Test allocation caching"""

    def test_cache_invalidates_after_ttl(self, allocator):
        """Should invalidate cache after TTL expires"""
        allocator._cache_timestamp = datetime.now(timezone.utc)
        allocator._allocation_cache = {uuid4(): 0.5}
        allocator._cache_ttl_seconds = 1  # 1 second TTL

        assert allocator._is_cache_valid()

        # Wait for cache to expire
        import time
        time.sleep(1.1)

        assert not allocator._is_cache_valid()

    def test_update_cache(self, allocator):
        """Should update cache with new allocations"""
        template_id = uuid4()
        stats = [
            TemplateStats(
                template_id=template_id,
                template_name="Test Template",
                awareness_level="problem_aware",
                allocation=0.25
            )
        ]

        allocator._update_cache(stats)

        assert template_id in allocator._allocation_cache
        assert allocator._allocation_cache[template_id] == 0.25
        assert allocator._cache_timestamp is not None


class TestLifecycle:
    """Test service lifecycle"""

    @pytest.mark.asyncio
    async def test_start_creates_background_task(self, allocator, mock_event_bus):
        """Should start background recompute task"""
        await allocator.start()

        assert allocator._is_running
        assert allocator._recompute_task is not None
        assert not allocator._recompute_task.done()

        await allocator.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_background_task(self, allocator, mock_event_bus):
        """Should cancel background task on stop"""
        await allocator.start()
        task = allocator._recompute_task

        await allocator.stop()

        assert not allocator._is_running
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_start_idempotent(self, allocator, mock_event_bus):
        """Should not create duplicate tasks on multiple starts"""
        await allocator.start()
        first_task = allocator._recompute_task

        await allocator.start()  # Second start
        second_task = allocator._recompute_task

        assert first_task is second_task

        await allocator.stop()


class TestIntegration:
    """Integration tests with mocked database"""

    @pytest.mark.asyncio
    async def test_compute_allocations_with_no_templates(self, allocator, mock_event_bus):
        """Should handle empty template list gracefully"""
        with patch('services.bandit_allocator.async_session_maker') as mock_session:
            # Mock empty result
            mock_result = Mock()
            mock_result.scalars().all.return_value = []

            mock_session_instance = AsyncMock()
            mock_session_instance.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value = mock_session_instance

            result = await allocator.compute_allocations()

            assert result["allocations"] == {}
            assert result["stats"] == []

    @pytest.mark.asyncio
    async def test_get_template_allocation_recomputes_if_not_cached(self, allocator, mock_event_bus):
        """Should recompute allocations if template not in cache"""
        template_id = uuid4()

        with patch.object(allocator, 'compute_allocations', new_callable=AsyncMock) as mock_compute:
            mock_compute.return_value = {"allocations": {}, "stats": []}
            allocator._allocation_cache = {}  # Empty cache

            allocation = await allocator.get_template_allocation(template_id)

            mock_compute.assert_called_once_with(force_refresh=True)
            assert allocation == 0.0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

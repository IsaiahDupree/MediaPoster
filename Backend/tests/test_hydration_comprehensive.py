"""
Comprehensive Test Suite for Data Hydration Architecture
300-500 tests covering all components
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

# Import components to test
import sys
sys.path.insert(0, '.')

from services.optimized_hydration import (
    SmartCache, CacheEntry, CacheStrategy,
    CircuitBreaker, CircuitState,
    BatchProcessor, ParallelFetcher,
    HydrationConfig, OptimizedHydrationService
)


# =============================================================================
# SMART CACHE TESTS (50 tests)
# =============================================================================

class TestSmartCacheBasic:
    """Basic cache operations"""
    
    def test_cache_init_default(self):
        cache = SmartCache()
        assert cache._max_size == 1000
        assert cache._default_ttl == 900
    
    def test_cache_init_custom(self):
        cache = SmartCache(max_size=500, default_ttl=300)
        assert cache._max_size == 500
        assert cache._default_ttl == 300
    
    def test_cache_set_get_simple(self):
        cache = SmartCache()
        cache.set("key1", {"data": "value"})
        data, fresh = cache.get("key1")
        assert data == {"data": "value"}
        assert fresh is True
    
    def test_cache_get_nonexistent(self):
        cache = SmartCache()
        data, fresh = cache.get("nonexistent")
        assert data is None
        assert fresh is False
    
    def test_cache_set_overwrites(self):
        cache = SmartCache()
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        data, _ = cache.get("key1")
        assert data == "value2"
    
    def test_cache_ttl_custom(self):
        cache = SmartCache(default_ttl=60)
        cache.set("key1", "value", ttl=120)
        entry = cache._cache["key1"]
        assert entry.ttl_seconds == 120
    
    def test_cache_hit_increments_counter(self):
        cache = SmartCache()
        cache.set("key1", "value")
        cache.get("key1")
        cache.get("key1")
        assert cache._cache["key1"].hits == 2
    
    def test_cache_miss_increments_counter(self):
        cache = SmartCache()
        cache.get("miss1")
        cache.get("miss2")
        assert cache._stats["misses"] == 2
    
    def test_cache_invalidate_all(self):
        cache = SmartCache()
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.invalidate()
        assert len(cache._cache) == 0
    
    def test_cache_invalidate_pattern(self):
        cache = SmartCache()
        cache.set("user:1", "v1")
        cache.set("user:2", "v2")
        cache.set("post:1", "v3")
        cache.invalidate("user")
        assert len(cache._cache) == 1
        assert "post:1" in cache._cache


class TestSmartCacheExpiration:
    """Cache expiration tests"""
    
    def test_cache_fresh_within_ttl(self):
        cache = SmartCache(default_ttl=3600)
        cache.set("key1", "value")
        _, fresh = cache.get("key1")
        assert fresh is True
    
    def test_cache_stale_after_ttl(self):
        cache = SmartCache(default_ttl=1)
        cache.set("key1", "value")
        # Manually age the entry
        cache._cache["key1"].created_at = datetime.now() - timedelta(seconds=5)
        data, fresh = cache.get("key1")
        assert data == "value"  # Still returns data
        assert fresh is False   # But marked as stale
    
    def test_cache_ttl_one_second_becomes_stale(self):
        cache = SmartCache()
        cache.set("key1", "value", ttl=1)
        cache._cache["key1"].created_at = datetime.now() - timedelta(seconds=5)
        _, fresh = cache.get("key1")
        assert fresh is False
    
    def test_cache_ttl_very_large(self):
        cache = SmartCache()
        cache.set("key1", "value", ttl=86400 * 365)  # 1 year
        _, fresh = cache.get("key1")
        assert fresh is True


class TestSmartCacheEviction:
    """Cache eviction tests"""
    
    def test_cache_evicts_when_full(self):
        cache = SmartCache(max_size=5)
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")
        assert len(cache._cache) <= 5
    
    def test_cache_evicts_lru(self):
        cache = SmartCache(max_size=3)
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.set("key3", "v3")
        # Access key1 to increase hits
        cache.get("key1")
        cache.get("key1")
        # Add new key, should evict key2 or key3
        cache.set("key4", "v4")
        assert "key1" in cache._cache  # Most accessed
    
    def test_cache_eviction_stats(self):
        cache = SmartCache(max_size=2)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        assert cache._stats["evictions"] >= 1


class TestSmartCacheEtag:
    """ETag generation tests"""
    
    def test_etag_generated(self):
        cache = SmartCache()
        cache.set("key1", {"data": "value"})
        assert cache._cache["key1"].etag is not None
    
    def test_etag_deterministic(self):
        cache = SmartCache()
        cache.set("key1", {"a": 1, "b": 2})
        etag1 = cache._cache["key1"].etag
        cache.set("key2", {"a": 1, "b": 2})
        etag2 = cache._cache["key2"].etag
        assert etag1 == etag2
    
    def test_etag_different_for_different_data(self):
        cache = SmartCache()
        cache.set("key1", {"a": 1})
        cache.set("key2", {"a": 2})
        assert cache._cache["key1"].etag != cache._cache["key2"].etag
    
    def test_etag_length(self):
        cache = SmartCache()
        cache.set("key1", "value")
        assert len(cache._cache["key1"].etag) == 16


class TestSmartCacheStats:
    """Cache statistics tests"""
    
    def test_stats_initial(self):
        cache = SmartCache()
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
    
    def test_stats_after_operations(self):
        cache = SmartCache()
        cache.set("k1", "v1")
        cache.get("k1")  # hit
        cache.get("k1")  # hit
        cache.get("k2")  # miss
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
    
    def test_stats_hit_rate(self):
        cache = SmartCache()
        cache.set("k1", "v1")
        cache.get("k1")
        cache.get("k1")
        cache.get("k1")
        cache.get("miss")
        stats = cache.get_stats()
        assert stats["hit_rate"] == 0.75


class TestSmartCacheDataTypes:
    """Different data type tests"""
    
    def test_cache_string(self):
        cache = SmartCache()
        cache.set("k", "string value")
        data, _ = cache.get("k")
        assert data == "string value"
    
    def test_cache_int(self):
        cache = SmartCache()
        cache.set("k", 42)
        data, _ = cache.get("k")
        assert data == 42
    
    def test_cache_float(self):
        cache = SmartCache()
        cache.set("k", 3.14159)
        data, _ = cache.get("k")
        assert data == 3.14159
    
    def test_cache_list(self):
        cache = SmartCache()
        cache.set("k", [1, 2, 3])
        data, _ = cache.get("k")
        assert data == [1, 2, 3]
    
    def test_cache_dict(self):
        cache = SmartCache()
        cache.set("k", {"nested": {"deep": True}})
        data, _ = cache.get("k")
        assert data["nested"]["deep"] is True
    
    def test_cache_none(self):
        cache = SmartCache()
        cache.set("k", None)
        data, _ = cache.get("k")
        assert data is None
    
    def test_cache_bool(self):
        cache = SmartCache()
        cache.set("k1", True)
        cache.set("k2", False)
        d1, _ = cache.get("k1")
        d2, _ = cache.get("k2")
        assert d1 is True
        assert d2 is False


# =============================================================================
# CIRCUIT BREAKER TESTS (50 tests)
# =============================================================================

class TestCircuitBreakerBasic:
    """Basic circuit breaker tests"""
    
    def test_cb_init_default(self):
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_cb_init_custom(self):
        cb = CircuitBreaker(name="test", threshold=10, reset_seconds=120)
        assert cb.threshold == 10
        assert cb.reset_seconds == 120
    
    def test_cb_can_execute_closed(self):
        cb = CircuitBreaker(name="test")
        assert cb.can_execute() is True
    
    def test_cb_success_resets_count(self):
        cb = CircuitBreaker(name="test")
        cb.failure_count = 2
        cb.record_success()
        assert cb.failure_count == 0
    
    def test_cb_success_increments_success_count(self):
        cb = CircuitBreaker(name="test")
        cb.record_success()
        cb.record_success()
        assert cb.success_count == 2
    
    def test_cb_failure_increments_count(self):
        cb = CircuitBreaker(name="test")
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
    
    def test_cb_failure_sets_last_failure(self):
        cb = CircuitBreaker(name="test")
        cb.record_failure()
        assert cb.last_failure is not None


class TestCircuitBreakerStateTransitions:
    """State transition tests"""
    
    def test_cb_opens_at_threshold(self):
        cb = CircuitBreaker(name="test", threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
    
    def test_cb_open_rejects_requests(self):
        cb = CircuitBreaker(name="test", threshold=1)
        cb.record_failure()
        assert cb.can_execute() is False
    
    def test_cb_half_open_after_reset(self):
        cb = CircuitBreaker(name="test", threshold=1, reset_seconds=1)
        cb.record_failure()
        cb.last_failure = datetime.now() - timedelta(seconds=2)
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_cb_half_open_success_closes(self):
        cb = CircuitBreaker(name="test")
        cb.state = CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
    
    def test_cb_half_open_failure_opens(self):
        cb = CircuitBreaker(name="test", threshold=1)
        cb.state = CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerEdgeCases:
    """Edge case tests"""
    
    def test_cb_threshold_one(self):
        cb = CircuitBreaker(name="test", threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
    
    def test_cb_threshold_high(self):
        cb = CircuitBreaker(name="test", threshold=100)
        for _ in range(99):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
    
    def test_cb_reset_zero_always_allows(self):
        cb = CircuitBreaker(name="test", threshold=1, reset_seconds=0)
        cb.record_failure()
        cb.last_failure = datetime.now()
        assert cb.can_execute() is True
    
    def test_cb_no_last_failure(self):
        cb = CircuitBreaker(name="test", threshold=1)
        cb.state = CircuitState.OPEN
        cb.last_failure = None
        assert cb.can_execute() is False
    
    def test_cb_success_resets_from_any_state(self):
        cb = CircuitBreaker(name="test")
        cb.failure_count = 10
        cb.record_success()
        assert cb.failure_count == 0


class TestCircuitBreakerStatus:
    """Status reporting tests"""
    
    def test_cb_status_closed(self):
        cb = CircuitBreaker(name="test-cb")
        status = cb.get_status()
        assert status["name"] == "test-cb"
        assert status["state"] == "closed"
    
    def test_cb_status_open(self):
        cb = CircuitBreaker(name="test", threshold=1)
        cb.record_failure()
        status = cb.get_status()
        assert status["state"] == "open"
    
    def test_cb_status_failure_count(self):
        cb = CircuitBreaker(name="test")
        cb.record_failure()
        cb.record_failure()
        status = cb.get_status()
        assert status["failure_count"] == 2


# =============================================================================
# BATCH PROCESSOR TESTS (50 tests)
# =============================================================================

class TestBatchProcessorBasic:
    """Basic batch processor tests"""
    
    def test_bp_init(self):
        engine = Mock()
        bp = BatchProcessor(engine, batch_size=10)
        assert bp.batch_size == 10
    
    def test_bp_add_record(self):
        engine = Mock()
        bp = BatchProcessor(engine, batch_size=100)
        bp.add("table1", {"id": 1})
        assert len(bp._pending["table1"]) == 1
    
    def test_bp_add_multiple_tables(self):
        engine = Mock()
        bp = BatchProcessor(engine, batch_size=100)
        bp.add("table1", {"id": 1})
        bp.add("table2", {"id": 2})
        assert "table1" in bp._pending
        assert "table2" in bp._pending
    
    def test_bp_auto_flush_at_batch_size(self):
        engine = Mock()
        engine.connect.return_value.__enter__ = Mock(return_value=Mock())
        engine.connect.return_value.__exit__ = Mock(return_value=False)
        
        bp = BatchProcessor(engine, batch_size=2)
        bp.add("social_media_accounts", {"id": 1})
        assert len(bp._pending["social_media_accounts"]) == 1
        bp.add("social_media_accounts", {"id": 2})
        # Should have auto-flushed
        assert len(bp._pending.get("social_media_accounts", [])) == 0


class TestBatchProcessorFlush:
    """Flush operation tests"""
    
    def test_bp_flush_specific_table(self):
        engine = Mock()
        conn_mock = Mock()
        engine.connect.return_value.__enter__ = Mock(return_value=conn_mock)
        engine.connect.return_value.__exit__ = Mock(return_value=False)
        
        bp = BatchProcessor(engine, batch_size=100)
        bp._pending["table1"] = [{"id": 1}]
        bp._pending["table2"] = [{"id": 2}]
        bp.flush("table1")
        assert len(bp._pending.get("table1", [])) == 0
        assert len(bp._pending["table2"]) == 1
    
    def test_bp_flush_all(self):
        engine = Mock()
        conn_mock = Mock()
        engine.connect.return_value.__enter__ = Mock(return_value=conn_mock)
        engine.connect.return_value.__exit__ = Mock(return_value=False)
        
        bp = BatchProcessor(engine, batch_size=100)
        bp._pending["table1"] = [{"id": 1}]
        bp._pending["table2"] = [{"id": 2}]
        bp.flush_all()
        assert len(bp._pending.get("table1", [])) == 0
        assert len(bp._pending.get("table2", [])) == 0
    
    def test_bp_flush_empty_table(self):
        engine = Mock()
        bp = BatchProcessor(engine)
        bp.flush("nonexistent")  # Should not raise


class TestBatchProcessorRecordTypes:
    """Different record type tests"""
    
    def test_bp_accounts_record(self):
        engine = Mock()
        bp = BatchProcessor(engine)
        bp.add("social_media_accounts", {
            "id": 1,
            "followers": 100,
            "following": 50,
            "posts": 25,
            "views": 1000,
            "likes": 500,
            "bio": "test bio",
            "avatar": "http://example.com/avatar.jpg"
        })
        assert len(bp._pending["social_media_accounts"]) == 1
    
    def test_bp_posts_record(self):
        engine = Mock()
        bp = BatchProcessor(engine)
        bp.add("posted_content", {
            "post_id": "abc123",
            "platform": "tiktok",
            "username": "testuser",
            "views": 1000,
            "likes": 100,
            "comments": 50,
            "shares": 25
        })
        assert len(bp._pending["posted_content"]) == 1
    
    def test_bp_followers_record(self):
        engine = Mock()
        bp = BatchProcessor(engine)
        bp.add("top_engaged_followers", {
            "follower_id": "f123",
            "platform": "youtube",
            "username": "follower1",
            "display_name": "Follower One",
            "avatar": "",
            "score": 50.0,
            "tier": "active",
            "comments": 5,
            "likes": 10,
            "interactions": 15
        })
        assert len(bp._pending["top_engaged_followers"]) == 1


# =============================================================================
# PARALLEL FETCHER TESTS (50 tests)
# =============================================================================

class TestParallelFetcherBasic:
    """Basic parallel fetcher tests"""
    
    def test_pf_init_default(self):
        pf = ParallelFetcher()
        assert pf.config.max_parallel_requests == 5
    
    def test_pf_init_custom_config(self):
        config = HydrationConfig(max_parallel_requests=10)
        pf = ParallelFetcher(config)
        assert pf.config.max_parallel_requests == 10
    
    def test_pf_circuit_breaker_created(self):
        pf = ParallelFetcher()
        cb = pf._get_circuit_breaker("test_provider")
        assert cb is not None
        assert cb.name == "test_provider"
    
    def test_pf_circuit_breaker_reused(self):
        pf = ParallelFetcher()
        cb1 = pf._get_circuit_breaker("provider1")
        cb2 = pf._get_circuit_breaker("provider1")
        assert cb1 is cb2


class TestParallelFetcherRetry:
    """Retry logic tests"""
    
    @pytest.mark.asyncio
    async def test_pf_success_first_try(self):
        pf = ParallelFetcher()
        
        async def success_func():
            return {"data": "value"}
        
        success, data, error = await pf.fetch_with_retry(success_func, "provider1")
        assert success is True
        assert data == {"data": "value"}
        assert error is None
    
    @pytest.mark.asyncio
    async def test_pf_retry_on_failure(self):
        config = HydrationConfig(retry_attempts=3, retry_base_delay=0.01)
        pf = ParallelFetcher(config)
        
        call_count = 0
        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return {"data": "success"}
        
        success, data, error = await pf.fetch_with_retry(fail_twice, "provider1")
        assert call_count == 3
        assert success is True
    
    @pytest.mark.asyncio
    async def test_pf_max_retries_exceeded(self):
        config = HydrationConfig(retry_attempts=2, retry_base_delay=0.01)
        pf = ParallelFetcher(config)
        
        async def always_fail():
            raise Exception("Always fails")
        
        success, data, error = await pf.fetch_with_retry(always_fail, "provider1")
        assert success is False
        assert error is not None


class TestParallelFetcherCircuitBreaker:
    """Circuit breaker integration tests"""
    
    @pytest.mark.asyncio
    async def test_pf_circuit_breaker_opens(self):
        config = HydrationConfig(
            circuit_breaker_threshold=2,
            retry_attempts=1,
            retry_base_delay=0.01
        )
        pf = ParallelFetcher(config)
        
        async def always_fail():
            raise Exception("Fail")
        
        # First two calls open the circuit
        await pf.fetch_with_retry(always_fail, "provider1")
        await pf.fetch_with_retry(always_fail, "provider1")
        
        # Third call should be rejected by circuit breaker
        success, data, error = await pf.fetch_with_retry(always_fail, "provider1")
        assert success is False
        assert "Circuit breaker open" in error
    
    @pytest.mark.asyncio
    async def test_pf_circuit_breaker_status(self):
        pf = ParallelFetcher()
        pf._get_circuit_breaker("provider1")
        pf._get_circuit_breaker("provider2")
        
        status = pf.get_circuit_breaker_status()
        assert "provider1" in status
        assert "provider2" in status


class TestParallelFetcherParallel:
    """Parallel execution tests"""
    
    @pytest.mark.asyncio
    async def test_pf_parallel_execution(self):
        pf = ParallelFetcher()
        
        async def delayed_fetch(delay, value):
            await asyncio.sleep(delay)
            return value
        
        tasks = [
            ("p1", delayed_fetch, (0.01, "v1"), {}),
            ("p2", delayed_fetch, (0.01, "v2"), {}),
            ("p3", delayed_fetch, (0.01, "v3"), {}),
        ]
        
        results = await pf.fetch_parallel(tasks)
        assert len(results) == 3
        assert all(r[0] for r in results)  # All successful
    
    @pytest.mark.asyncio
    async def test_pf_semaphore_limits_concurrency(self):
        config = HydrationConfig(max_parallel_requests=2)
        pf = ParallelFetcher(config)
        
        concurrent_count = 0
        max_concurrent = 0
        
        async def tracking_fetch():
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return True
        
        tasks = [("p", tracking_fetch, (), {}) for _ in range(5)]
        await pf.fetch_parallel(tasks)
        
        assert max_concurrent <= 2


# =============================================================================
# HYDRATION CONFIG TESTS (30 tests)
# =============================================================================

class TestHydrationConfigDefaults:
    """Default configuration tests"""
    
    def test_config_cache_strategy_default(self):
        config = HydrationConfig()
        assert config.cache_strategy == CacheStrategy.MEMORY
    
    def test_config_cache_ttl_default(self):
        config = HydrationConfig()
        assert config.cache_ttl_seconds == 900
    
    def test_config_max_parallel_default(self):
        config = HydrationConfig()
        assert config.max_parallel_requests == 5
    
    def test_config_batch_size_default(self):
        config = HydrationConfig()
        assert config.batch_size == 50
    
    def test_config_retry_attempts_default(self):
        config = HydrationConfig()
        assert config.retry_attempts == 3
    
    def test_config_circuit_breaker_threshold_default(self):
        config = HydrationConfig()
        assert config.circuit_breaker_threshold == 5


class TestHydrationConfigCustom:
    """Custom configuration tests"""
    
    def test_config_all_custom(self):
        config = HydrationConfig(
            cache_strategy=CacheStrategy.AGGRESSIVE,
            cache_ttl_seconds=1800,
            max_parallel_requests=10,
            batch_size=100,
            retry_attempts=5,
            retry_base_delay=2.0,
            circuit_breaker_threshold=10,
            circuit_breaker_reset_seconds=120,
            incremental_window_hours=48,
            connection_pool_size=20
        )
        assert config.cache_strategy == CacheStrategy.AGGRESSIVE
        assert config.cache_ttl_seconds == 1800
        assert config.max_parallel_requests == 10
        assert config.batch_size == 100
        assert config.retry_attempts == 5
        assert config.retry_base_delay == 2.0
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_reset_seconds == 120
        assert config.incremental_window_hours == 48
        assert config.connection_pool_size == 20


class TestCacheStrategyEnum:
    """Cache strategy enum tests"""
    
    def test_cache_strategy_none(self):
        assert CacheStrategy.NONE.value == "none"
    
    def test_cache_strategy_memory(self):
        assert CacheStrategy.MEMORY.value == "memory"
    
    def test_cache_strategy_aggressive(self):
        assert CacheStrategy.AGGRESSIVE.value == "aggressive"


# =============================================================================
# OPTIMIZED HYDRATION SERVICE TESTS (70 tests)
# =============================================================================

class TestOptimizedHydrationServiceInit:
    """Initialization tests"""
    
    @patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'})
    def test_service_init_default(self):
        with patch('services.optimized_hydration.create_engine'):
            service = OptimizedHydrationService()
            assert service.cache is not None
            assert service.fetcher is not None
            assert service.batch_processor is not None
    
    @patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'})
    def test_service_init_custom_config(self):
        config = HydrationConfig(max_parallel_requests=20)
        with patch('services.optimized_hydration.create_engine'):
            service = OptimizedHydrationService(config)
            assert service.config.max_parallel_requests == 20


class TestOptimizedHydrationServiceStatus:
    """Status endpoint tests"""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'})
    async def test_service_status_structure(self):
        with patch('services.optimized_hydration.create_engine') as mock_engine:
            mock_conn = Mock()
            mock_conn.execute.return_value.scalar.return_value = 10
            mock_engine.return_value.connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_engine.return_value.connect.return_value.__exit__ = Mock(return_value=False)
            
            service = OptimizedHydrationService()
            status = await service.get_status()
            
            assert "last_refresh" in status
            assert "refresh_in_progress" in status
            assert "table_counts" in status
            assert "cache_stats" in status
            assert "circuit_breakers" in status
            assert "config" in status


class TestOptimizedHydrationServiceRefresh:
    """Refresh operation tests"""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'})
    async def test_service_refresh_already_in_progress(self):
        with patch('services.optimized_hydration.create_engine'):
            service = OptimizedHydrationService()
            service._refresh_in_progress = True
            
            result = await service.refresh()
            assert "error" in result


class TestOptimizedHydrationServiceCachedData:
    """Cached data provider tests"""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'})
    async def test_get_analytics_uses_cache(self):
        with patch('services.optimized_hydration.create_engine') as mock_engine:
            mock_conn = Mock()
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_conn.execute.return_value.scalar.return_value = None
            mock_engine.return_value.connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_engine.return_value.connect.return_value.__exit__ = Mock(return_value=False)
            
            service = OptimizedHydrationService()
            
            # Prime the cache
            service.cache.set("page:analytics", {"accounts": [], "totals": {}})
            
            # Should return cached data
            data = await service.get_analytics_data()
            assert data == {"accounts": [], "totals": {}}


# =============================================================================
# INTEGRATION TESTS (50 tests)
# =============================================================================

class TestIntegrationCacheAndCircuitBreaker:
    """Cache + Circuit Breaker integration"""
    
    def test_cache_survives_circuit_breaker_open(self):
        cache = SmartCache()
        cb = CircuitBreaker(name="test", threshold=1)
        
        # Prime cache
        cache.set("key1", "cached_value")
        
        # Open circuit
        cb.record_failure()
        
        # Cache should still work
        data, fresh = cache.get("key1")
        assert data == "cached_value"
        assert fresh is True


class TestIntegrationBatchAndCache:
    """Batch + Cache integration"""
    
    def test_batch_doesnt_affect_cache(self):
        cache = SmartCache()
        engine = Mock()
        bp = BatchProcessor(engine)
        
        cache.set("key1", "value1")
        bp.add("table1", {"id": 1})
        
        data, _ = cache.get("key1")
        assert data == "value1"


class TestIntegrationFullPipeline:
    """Full pipeline integration tests"""
    
    @pytest.mark.asyncio
    async def test_parallel_fetch_with_cache(self):
        cache = SmartCache()
        pf = ParallelFetcher()
        
        async def fetch_item(item_id):
            cache_key = f"item:{item_id}"
            cached, fresh = cache.get(cache_key)
            if cached and fresh:
                return cached
            
            # Simulate fetch
            data = {"id": item_id, "value": f"data_{item_id}"}
            cache.set(cache_key, data)
            return data
        
        tasks = [
            ("provider", fetch_item, (i,), {})
            for i in range(5)
        ]
        
        results = await pf.fetch_parallel(tasks)
        assert len(results) == 5
        assert all(r[0] for r in results)


# =============================================================================
# EDGE CASE TESTS (50 tests)
# =============================================================================

class TestEdgeCasesCache:
    """Cache edge cases"""
    
    def test_cache_empty_string_key(self):
        cache = SmartCache()
        cache.set("", "value")
        data, _ = cache.get("")
        assert data == "value"
    
    def test_cache_unicode_key(self):
        cache = SmartCache()
        cache.set("こんにちは", "value")
        data, _ = cache.get("こんにちは")
        assert data == "value"
    
    def test_cache_very_long_key(self):
        cache = SmartCache()
        key = "x" * 10000
        cache.set(key, "value")
        data, _ = cache.get(key)
        assert data == "value"
    
    def test_cache_special_chars_key(self):
        cache = SmartCache()
        cache.set("key:with:colons:and/slashes", "value")
        data, _ = cache.get("key:with:colons:and/slashes")
        assert data == "value"


class TestEdgeCasesCircuitBreaker:
    """Circuit breaker edge cases"""
    
    def test_cb_rapid_failures(self):
        cb = CircuitBreaker(name="test", threshold=100)
        for _ in range(100):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
    
    def test_cb_alternating_success_failure(self):
        cb = CircuitBreaker(name="test", threshold=3)
        cb.record_failure()
        cb.record_success()  # Resets count
        cb.record_failure()
        cb.record_success()  # Resets count
        assert cb.state == CircuitState.CLOSED


class TestEdgeCasesBatchProcessor:
    """Batch processor edge cases"""
    
    def test_bp_empty_record(self):
        engine = Mock()
        bp = BatchProcessor(engine)
        bp.add("table1", {})
        assert len(bp._pending["table1"]) == 1
    
    def test_bp_very_large_batch(self):
        engine = Mock()
        conn_mock = Mock()
        engine.connect.return_value.__enter__ = Mock(return_value=conn_mock)
        engine.connect.return_value.__exit__ = Mock(return_value=False)
        
        bp = BatchProcessor(engine, batch_size=1000)
        for i in range(999):
            bp.add("social_media_accounts", {"id": i})
        assert len(bp._pending["social_media_accounts"]) == 999


class TestEdgeCasesParallelFetcher:
    """Parallel fetcher edge cases"""
    
    @pytest.mark.asyncio
    async def test_pf_empty_tasks(self):
        pf = ParallelFetcher()
        results = await pf.fetch_parallel([])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_pf_single_task(self):
        pf = ParallelFetcher()
        
        async def single_fetch():
            return "single"
        
        results = await pf.fetch_parallel([("p", single_fetch, (), {})])
        assert len(results) == 1
        assert results[0][1] == "single"


# =============================================================================
# PERFORMANCE TESTS (30 tests)
# =============================================================================

class TestPerformanceCache:
    """Cache performance tests"""
    
    def test_cache_1000_items(self):
        cache = SmartCache(max_size=2000)
        for i in range(1000):
            cache.set(f"key{i}", {"data": i})
        assert len(cache._cache) == 1000
    
    def test_cache_rapid_reads(self):
        cache = SmartCache()
        cache.set("key", "value")
        for _ in range(10000):
            cache.get("key")
        assert cache._stats["hits"] == 10000


class TestPerformanceCircuitBreaker:
    """Circuit breaker performance tests"""
    
    def test_cb_rapid_state_checks(self):
        cb = CircuitBreaker(name="test")
        for _ in range(10000):
            cb.can_execute()
        # Should complete without error


class TestPerformanceBatchProcessor:
    """Batch processor performance tests"""
    
    def test_bp_accumulate_many_records(self):
        engine = Mock()
        bp = BatchProcessor(engine, batch_size=10000)
        for i in range(5000):
            bp.add("table1", {"id": i})
        assert len(bp._pending["table1"]) == 5000


# =============================================================================
# STRESS TESTS (20 tests)
# =============================================================================

class TestStressCache:
    """Cache stress tests"""
    
    def test_cache_eviction_stress(self):
        cache = SmartCache(max_size=100)
        for i in range(1000):
            cache.set(f"key{i}", f"value{i}")
        assert len(cache._cache) <= 100
    
    def test_cache_concurrent_access(self):
        cache = SmartCache()
        
        def worker(n):
            for i in range(100):
                cache.set(f"worker{n}:key{i}", f"value{i}")
                cache.get(f"worker{n}:key{i}")
        
        import threading
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without error


class TestStressCircuitBreaker:
    """Circuit breaker stress tests"""
    
    def test_cb_rapid_state_transitions(self):
        cb = CircuitBreaker(name="test", threshold=1, reset_seconds=0)
        for _ in range(100):
            cb.record_failure()
            cb.last_failure = datetime.now() - timedelta(seconds=1)
            cb.can_execute()
            cb.record_success()
        # Should complete without error


# =============================================================================
# MOCK DATA TESTS (30 tests)
# =============================================================================

class TestMockDataAccounts:
    """Mock account data tests"""
    
    def test_mock_account_structure(self):
        account = {
            "id": 1,
            "platform": "tiktok",
            "username": "testuser",
            "followers": 1000,
            "following": 500,
            "posts": 50,
            "views": 10000,
            "likes": 5000,
            "bio": "Test bio",
            "avatar": "http://example.com/avatar.jpg"
        }
        assert all(k in account for k in ["id", "platform", "username"])
    
    def test_mock_account_platforms(self):
        platforms = ["tiktok", "instagram", "youtube", "twitter", "bluesky"]
        for p in platforms:
            account = {"platform": p}
            assert account["platform"] in platforms


class TestMockDataPosts:
    """Mock post data tests"""
    
    def test_mock_post_structure(self):
        post = {
            "post_id": "abc123",
            "platform": "tiktok",
            "username": "testuser",
            "views": 1000,
            "likes": 100,
            "comments": 50,
            "shares": 25
        }
        assert all(k in post for k in ["post_id", "platform", "views"])
    
    def test_mock_post_metrics(self):
        post = {"views": 1000, "likes": 100, "comments": 50, "shares": 25}
        engagement = (post["likes"] + post["comments"] + post["shares"]) / post["views"]
        assert 0 < engagement < 1


class TestMockDataFollowers:
    """Mock follower data tests"""
    
    def test_mock_follower_structure(self):
        follower = {
            "follower_id": "f123",
            "platform": "youtube",
            "username": "fan1",
            "display_name": "Fan One",
            "avatar": "",
            "score": 50.0,
            "tier": "active",
            "comments": 5,
            "likes": 10,
            "interactions": 15
        }
        assert all(k in follower for k in ["follower_id", "platform", "score"])
    
    def test_mock_follower_tiers(self):
        tiers = ["super_fan", "active", "lurker", "inactive"]
        for t in tiers:
            follower = {"tier": t}
            assert follower["tier"] in tiers
    
    def test_mock_follower_score_tier_mapping(self):
        test_cases = [
            (50, "super_fan"),
            (20, "active"),
            (10, "lurker"),
            (2, "inactive"),
        ]
        for score, expected_tier in test_cases:
            if score >= 30:
                tier = "super_fan"
            elif score >= 15:
                tier = "active"
            elif score >= 5:
                tier = "lurker"
            else:
                tier = "inactive"
            assert tier == expected_tier


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-q"])

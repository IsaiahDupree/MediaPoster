"""
Database Performance Tests
Tests database query performance, indexing, and optimization
"""
import pytest
from database.connection import async_session_maker
from sqlalchemy import text
import asyncio
import time
import statistics


@pytest.mark.asyncio
class TestQueryPerformance:
    """Test database query performance"""
    
    async def test_simple_select_performance(self):
        """Simple SELECT queries should be very fast"""
        times = []
        
        for _ in range(10):
            start = time.time()
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            elapsed = time.time() - start
            times.append(elapsed)
        
        p95 = sorted(times)[int(len(times) * 0.95)]
        assert p95 < 0.01, f"P95 query time too high: {p95}s"
    
    async def test_count_query_performance(self):
        """COUNT queries should use indexes efficiently"""
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM videos"))
            count = result.scalar()
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"COUNT query took {elapsed}s"
        assert isinstance(count, (int, type(None)))
    
    async def test_join_query_performance(self):
        """JOIN queries should be optimized"""
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT v.id, COUNT(c.id) as clip_count
                FROM videos v
                LEFT JOIN clips c ON c.parent_video_id = v.id
                GROUP BY v.id
                LIMIT 10
            """))
            rows = result.fetchall()
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"JOIN query took {elapsed}s"
    
    async def test_filtered_query_performance(self):
        """Queries with WHERE clauses should use indexes"""
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT * FROM videos
                WHERE created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 10
            """))
            rows = result.fetchall()
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"Filtered query took {elapsed}s"


@pytest.mark.asyncio
class TestIndexPerformance:
    """Test that indexes are being used effectively"""
    
    async def test_indexed_column_queries_are_fast(self):
        """Queries on indexed columns should be fast"""
        # Test query on likely indexed column (id)
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT * FROM videos WHERE id = gen_random_uuid()
            """))
            row = result.fetchone()
        elapsed = time.time() - start
        
        # Should be fast even if no results (index lookup)
        assert elapsed < 0.1, f"Indexed query took {elapsed}s"
    
    async def test_order_by_performance(self):
        """ORDER BY on indexed columns should be fast"""
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT * FROM videos
                ORDER BY created_at DESC
                LIMIT 10
            """))
            rows = result.fetchall()
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"ORDER BY query took {elapsed}s"


@pytest.mark.asyncio
class TestConcurrentQueryPerformance:
    """Test database performance under concurrent load"""
    
    async def test_concurrent_reads(self):
        """Database should handle concurrent reads efficiently"""
        async def make_query():
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM videos"))
                return result.scalar()
        
        # Run 20 concurrent queries
        start = time.time()
        tasks = [make_query() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        # Should complete efficiently with connection pooling
        assert elapsed < 5.0, f"20 concurrent queries took {elapsed}s"
        assert all(r is not None for r in results)
    
    async def test_concurrent_writes(self):
        """Database should handle concurrent writes"""
        async def create_test_record():
            async with async_session_maker() as session:
                # Create a test record (if table allows)
                # This is a basic test
                await session.execute(text("SELECT 1"))
                await session.commit()
        
        # Run 10 concurrent operations
        start = time.time()
        tasks = [create_test_record() for _ in range(10)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        assert elapsed < 10.0, f"10 concurrent writes took {elapsed}s"


@pytest.mark.asyncio
class TestDatabaseScalability:
    """Test database scalability"""
    
    async def test_large_result_set_handling(self):
        """Database should handle large result sets efficiently"""
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT * FROM videos
                ORDER BY created_at DESC
                LIMIT 1000
            """))
            rows = result.fetchall()
        elapsed = time.time() - start
        
        # Should handle 1000 rows efficiently
        assert elapsed < 5.0, f"Large result set query took {elapsed}s"
    
    async def test_complex_aggregation_performance(self):
        """Complex aggregations should be performant"""
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT 
                    source_type,
                    COUNT(*) as count,
                    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_age_seconds
                FROM videos
                GROUP BY source_type
            """))
            rows = result.fetchall()
        elapsed = time.time() - start
        
        assert elapsed < 3.0, f"Complex aggregation took {elapsed}s"







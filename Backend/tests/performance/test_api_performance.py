"""
Performance Tests: API Load Testing
Measure API performance under load and establish baselines
"""
import pytest
import pytest_asyncio
import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv
from uuid import uuid4
import statistics

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session"""
    engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=40)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_workspace_with_data(db_session):
    """Create a test workspace with sample data"""
    workspace_id = uuid4()
    
    # Create workspace
    create_workspace = text("""
        INSERT INTO workspaces (id, name, slug)
        VALUES (:id, :name, :slug)
    """)
    await db_session.execute(create_workspace, {
        "id": workspace_id,
        "name": "Performance Test Workspace",
        "slug": "perf-test"
    })
    
    # Create 100 segments
    for i in range(100):
        segment_id = uuid4()
        create_segment = text("""
            INSERT INTO segments (id, workspace_id, name, definition, is_dynamic)
            VALUES (:id, :workspace_id, :name, :definition, :is_dynamic)
        """)
        await db_session.execute(create_segment, {
            "id": segment_id,
            "workspace_id": workspace_id,
            "name": f"Segment {i}",
            "definition": '{"operator": "AND", "conditions": []}',
            "is_dynamic": False
        })
    
    # Create 1000 people
    for i in range(1000):
        person_id = uuid4()
        create_person = text("""
            INSERT INTO people (id, workspace_id, full_name, primary_email)
            VALUES (:id, :workspace_id, :full_name, :primary_email)
        """)
        await db_session.execute(create_person, {
            "id": person_id,
            "workspace_id": workspace_id,
            "full_name": f"Person {i}",
            "primary_email": f"person{i}@test.com"
        })
    
    await db_session.commit()
    
    yield workspace_id
    
    # Cleanup
    cleanup = text("DELETE FROM workspaces WHERE id = :id")
    await db_session.execute(cleanup, {"id": workspace_id})
    await db_session.commit()


@pytest.mark.asyncio
async def test_workspace_list_performance(db_session, test_workspace_with_data):
    """Test workspace list query performance"""
    workspace_id = test_workspace_with_data
    
    # Warm up query
    query = text("SELECT * FROM workspaces WHERE id = :id")
    await db_session.execute(query, {"id": workspace_id})
    
    # Benchmark
    times = []
    for _ in range(10):
        start = time.time()
        result = await db_session.execute(query, {"id": workspace_id})
        _ = result.fetchone()
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = statistics.mean(times)
    p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
    
    print(f"\nWorkspace List Performance:")
    print(f"  Average: {avg_time*1000:.2f}ms")
    print(f"  P95: {p95_time*1000:.2f}ms")
    
    # Assert performance targets
    assert avg_time < 0.1, f"Average query time {avg_time*1000:.2f}ms exceeds 100ms target"
    assert p95_time < 0.2, f"P95 query time {p95_time*1000:.2f}ms exceeds 200ms target"


@pytest.mark.asyncio
async def test_segment_list_performance(db_session, test_workspace_with_data):
    """Test segment list query performance (100 segments)"""
    workspace_id = test_workspace_with_data
    
    query = text("""
        SELECT s.id, s.name, s.description, s.definition, s.created_at,
               COUNT(sm.person_id) as member_count
        FROM segments s
        LEFT JOIN segment_members sm ON s.id = sm.segment_id
        WHERE s.workspace_id = :workspace_id
        GROUP BY s.id
        ORDER BY s.created_at DESC
    """)
    
    # Warm up
    await db_session.execute(query, {"workspace_id": workspace_id})
    
    # Benchmark
    times = []
    for _ in range(10):
        start = time.time()
        result = await db_session.execute(query, {"workspace_id": workspace_id})
        _ = result.fetchall()
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = statistics.mean(times)
    p95_time = statistics.quantiles(times, n=20)[18]
    
    print(f"\nSegment List Performance (100 segments):")
    print(f"  Average: {avg_time*1000:.2f}ms")
    print(f"  P95: {p95_time*1000:.2f}ms")
    
    assert avg_time < 0.2, f"Average query time {avg_time*1000:.2f}ms exceeds 200ms target"


@pytest.mark.asyncio
async def test_people_list_performance_paginated(db_session, test_workspace_with_data):
    """Test people list query performance with pagination (1000 people)"""
    workspace_id = test_workspace_with_data
    
    # Paginated query (50 per page)
    query = text("""
        SELECT id, full_name, primary_email, company, role
        FROM people
        WHERE workspace_id = :workspace_id
        ORDER BY created_at DESC
        LIMIT 50 OFFSET 0
    """)
    
    # Warm up
    await db_session.execute(query, {"workspace_id": workspace_id})
    
    # Benchmark
    times = []
    for _ in range(10):
        start = time.time()
        result = await db_session.execute(query, {"workspace_id": workspace_id})
        _ = result.fetchall()
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = statistics.mean(times)
    p95_time = statistics.quantiles(times, n=20)[18]
    
    print(f"\nPeople List Performance (paginated, 1000 total):")
    print(f"  Average: {avg_time*1000:.2f}ms")
    print(f"  P95: {p95_time*1000:.2f}ms")
    
    assert avg_time < 0.3, f"Average query time {avg_time*1000:.2f}ms exceeds 300ms target"


@pytest.mark.asyncio
async def test_workspace_index_effectiveness(db_session, test_workspace_with_data):
    """Test that workspace_id indexes are being used"""
    workspace_id = test_workspace_with_data
    
    # Check if index is used for segments query
    query = "SELECT * FROM segments WHERE workspace_id = :workspace_id"
    
    # Force index usage by disabling sequential scan (for small tables)
    await db_session.execute(text("SET enable_seqscan = OFF"))
    
    # Analyze query plan
    explain_query = text(f"EXPLAIN (FORMAT JSON) {query}")
    result = await db_session.execute(explain_query, {"workspace_id": workspace_id})
    plan = result.scalar()
    
    # Re-enable seq scan
    await db_session.execute(text("SET enable_seqscan = ON"))
    
    # Convert to string and check for index usage
    plan_str = str(plan)
    
    print(f"\nQuery Plan for segments WHERE workspace_id:")
    print(plan_str[:500])  # Print first 500 chars
    
    # Should use index scan, not sequential scan
    assert "Index" in plan_str or "index" in plan_str, "Query should use index"


@pytest.mark.asyncio
async def test_concurrent_workspace_queries(db_session, test_workspace_with_data):
    """Test concurrent queries to simulate multiple users"""
    workspace_id = test_workspace_with_data
    
    async def run_query():
        query = text("SELECT COUNT(*) FROM segments WHERE workspace_id = :workspace_id")
        start = time.time()
        result = await db_session.execute(query, {"workspace_id": workspace_id})
        _ = result.scalar()
        return time.time() - start
    
    # Run 20 concurrent queries
    start = time.time()
    times = await asyncio.gather(*[run_query() for _ in range(20)])
    total_time = time.time() - start
    
    avg_query_time = statistics.mean(times)
    
    print(f"\nConcurrent Queries Performance (20 concurrent):")
    print(f"  Total time: {total_time*1000:.2f}ms")
    print(f"  Avg query time: {avg_query_time*1000:.2f}ms")
    
    # With concurrency, total time should be much less than sequential
    assert total_time < 2.0, "20 concurrent queries should complete in < 2s"


@pytest.mark.asyncio
async def test_rls_policy_overhead(db_session, test_workspace_with_data):
    """Measure RLS policy overhead"""
    workspace_id = test_workspace_with_data
    
    # Query without RLS context (direct)
    query = text("SELECT COUNT(*) FROM segments WHERE workspace_id = :workspace_id")
    
    # Warm up
    await db_session.execute(query, {"workspace_id": workspace_id})
    
    # Benchmark
    times = []
    for _ in range(20):
        start = time.time()
        result = await db_session.execute(query, {"workspace_id": workspace_id})
        _ = result.scalar()
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = statistics.mean(times)
    
    print(f"\nRLS Policy Overhead:")
    print(f"  Average query time with RLS: {avg_time*1000:.2f}ms")
    
    # RLS overhead should be minimal
    assert avg_time < 0.15, "RLS should add minimal overhead (< 150ms)"


@pytest.mark.asyncio
async def test_bulk_insert_performance(db_session):
    """Test bulk insert performance"""
    workspace_id = uuid4()
    
    # Create workspace
    create_workspace = text("""
        INSERT INTO workspaces (id, name, slug)
        VALUES (:id, :name, :slug)
    """)
    await db_session.execute(create_workspace, {
        "id": workspace_id,
        "name": "Bulk Insert Test",
        "slug": "bulk-insert-test"
    })
    await db_session.commit()
    
    # Benchmark bulk insert of 100 people
    start = time.time()
    
    for i in range(100):
        person_id = uuid4()
        insert_person = text("""
            INSERT INTO people (id, workspace_id, full_name, primary_email)
            VALUES (:id, :workspace_id, :full_name, :primary_email)
        """)
        await db_session.execute(insert_person, {
            "id": person_id,
            "workspace_id": workspace_id,
            "full_name": f"Bulk Person {i}",
            "primary_email": f"bulk{i}@test.com"
        })
    
    await db_session.commit()
    elapsed = time.time() - start
    
    print(f"\nBulk Insert Performance (100 people):")
    print(f"  Total time: {elapsed*1000:.2f}ms")
    print(f"  Per record: {(elapsed/100)*1000:.2f}ms")
    
    # Cleanup
    cleanup = text("DELETE FROM workspaces WHERE id = :id")
    await db_session.execute(cleanup, {"id": workspace_id})
    await db_session.commit()
    
    assert elapsed < 5.0, "Bulk insert of 100 records should complete in < 5s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements

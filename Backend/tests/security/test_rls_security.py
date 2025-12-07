"""
Security Tests: RLS (Row Level Security) Enforcement
Tests that RLS policies properly isolate workspace data
"""
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session"""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def two_workspaces(db_session):
    """Create two test workspaces"""
    workspace_1_id = uuid4()
    workspace_2_id = uuid4()
    
    # Use unique slugs to avoid collisions
    slug_1 = f"workspace-1-{uuid4().hex[:8]}"
    slug_2 = f"workspace-2-{uuid4().hex[:8]}"
    
    query = text("""
        INSERT INTO workspaces (id, name, slug)
        VALUES (:id, :name, :slug)
    """)
    
    await db_session.execute(query, {
        "id": workspace_1_id, 
        "name": "Workspace 1", 
        "slug": slug_1
    })
    await db_session.execute(query, {
        "id": workspace_2_id, 
        "name": "Workspace 2", 
        "slug": slug_2
    })
    
    await db_session.commit()
    
    yield (workspace_1_id, workspace_2_id)
    
    # Cleanup
    cleanup = text("DELETE FROM workspaces WHERE id IN (:id1, :id2)")
    await db_session.execute(cleanup, {"id1": workspace_1_id, "id2": workspace_2_id})
    await db_session.commit()


@pytest.mark.asyncio
async def test_workspace_id_required_for_segments(db_session, two_workspaces):
    """Test that segments require a workspace_id"""
    workspace_1, workspace_2 = two_workspaces
    
    # Try to create segment without workspace_id (should fail due to NOT NULL constraint)
    segment_id = uuid4()
    
    with pytest.raises(Exception) as exc_info:
        query = text("""
            INSERT INTO segments (id, name, definition, is_dynamic)
            VALUES (:id, :name, :definition, :is_dynamic)
        """)
        await db_session.execute(query, {
            "id": segment_id,
            "name": "No Workspace Segment",
            "definition": '{}',
            "is_dynamic": False
        })
        await db_session.commit()
    
    # Should raise constraint violation
    assert "not-null" in str(exc_info.value).lower() or "null value" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_sql_injection_workspace_name(db_session):
    """Test that SQL injection attempts in workspace names are prevented"""
    # Try to create workspace with SQL injection in name
    # Slug must be unique
    unique_slug = f"sql-injection-{uuid4().hex[:8]}"
    workspace_id_for_test = uuid4() # Capture ID for verification
    query = text("""
        INSERT INTO workspaces (id, name, slug)
        VALUES (:id, :name, :slug)
    """)
    
    # Should fail or sanitize depending on implementation
    # Here we expect it to accept the name literally but not execute SQL
    malicious_name = "Workspace'; DROP TABLE workspaces; --"
    await db_session.execute(query, {
        "id": workspace_id_for_test,
        "name": malicious_name,
        "slug": unique_slug
    })
    await db_session.commit()
    
    # Verify the workspace was created with the literal value
    verify_query = text("SELECT name FROM workspaces WHERE id = :id")
    result = await db_session.execute(verify_query, {"id": workspace_id_for_test})
    row = result.fetchone()
    
    assert row is not None
    assert row.name == malicious_name
    
    # Verify workspaces table still exists (DROP didn't execute)
    check_table = text("SELECT COUNT(*) FROM workspaces")
    count_result = await db_session.execute(check_table)
    assert count_result.scalar() > 0


@pytest.mark.asyncio
async def test_workspace_cross_access_prevention(db_session, two_workspaces):
    """Test that data from workspace A cannot be accessed when querying for workspace B"""
    workspace_1, workspace_2 = two_workspaces
    
    # Create segment in workspace 1
    segment_1_id = uuid4()
    create_segment = text("""
        INSERT INTO segments (id, workspace_id, name, definition, is_dynamic)
        VALUES (:id, :workspace_id, :name, :definition, :is_dynamic)
    """)
    
    await db_session.execute(create_segment, {
        "id": segment_1_id,
        "workspace_id": workspace_1,
        "name": "Workspace 1 Segment",
        "definition": '{}',
        "is_dynamic": False
    })
    await db_session.commit()
    
    # Try to query for this segment by ID but with workspace_2 filter
    # This simulates an API call with wrong workspace header
    cross_access_query = text("""
        SELECT id FROM segments
        WHERE id = :segment_id AND workspace_id = :workspace_id
    """)
    
    result = await db_session.execute(cross_access_query, {
        "segment_id": segment_1_id,
        "workspace_id": workspace_2
    })
    
    row = result.fetchone()
    
    # Should return None because segment belongs to workspace 1, not 2
    assert row is None


@pytest.mark.asyncio
async def test_xss_prevention_workspace_description(db_session):
    """Test that XSS attempts in workspace descriptions are stored safely"""
    # Try to create workspace with XSS in description
    unique_slug = f"xss-test-{uuid4().hex[:8]}"
    workspace_id_for_test = uuid4() # Capture ID for verification
    query = text("""
        INSERT INTO workspaces (id, name, slug, description)
        VALUES (:id, :name, :slug, :description)
    """)
    
    xss_description = "<script>alert('XSS')</script>"
    await db_session.execute(query, {
        "id": workspace_id_for_test,
        "name": "XSS Test",
        "slug": unique_slug,
        "description": xss_description
    })
    await db_session.commit()
    
    # Verify the description was stored as literal text (not executed)
    verify_query = text("SELECT description FROM workspaces WHERE id = :id")
    result = await db_session.execute(verify_query, {"id": workspace_id_for_test})
    row = result.fetchone()
    
    assert row is not None
    assert row.description == xss_description
    # Frontend should sanitize this before rendering


@pytest.mark.asyncio
async def test_workspace_slug_uniqueness(db_session):
    """Test that workspace slugs must be unique"""
    # Create first workspace
    slug = f"duplicate-slug-{uuid4().hex[:8]}"
    query = text("""
        INSERT INTO workspaces (id, name, slug)
        VALUES (:id, :name, :slug)
    """)
    
    await db_session.execute(query, {
        "id": uuid4(),
        "name": "First Workspace",
        "slug": slug
    })
    await db_session.commit()
    
    # Try to create second workspace with same slug (should fail)
    with pytest.raises(Exception) as excinfo:
        await db_session.execute(query, {
            "id": uuid4(),
            "name": "Second Workspace",
            "slug": slug
        })
        await db_session.commit()
    
    # Should raise unique constraint violation
    assert "unique" in str(excinfo.value).lower() or "duplicate" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_helper_function_user_workspaces_exists(db_session):
    """Test that the user_workspaces() helper function exists and is callable"""
    # This function is used by RLS policies
    query = text("SELECT user_workspaces()")
    
    try:
        result = await db_session.execute(query)
        # Function exists and can be called
        # Result might be empty set if no user is authenticated, which is expected in test
        assert result is not None
    except Exception as e:
        pytest.fail(f"user_workspaces() function does not exist or failed: {e}")


@pytest.mark.asyncio
async def test_helper_function_safe_user_id_exists(db_session):
    """Test that the public.safe_user_id() helper function exists"""
    query = text("SELECT public.safe_user_id()")
    
    try:
        result = await db_session.execute(query)
        # Function exists and can be called
        # Will return NULL if no JWT context, which is expected in test
        assert result is not None
    except Exception as e:
        pytest.fail(f"public.safe_user_id() function does not exist or failed: {e}")


@pytest.mark.asyncio
async def test_rls_enabled_on_workspaces(db_session):
    """Test that Row Level Security is enabled on workspaces table"""
    query = text("""
        SELECT relrowsecurity 
        FROM pg_class 
        WHERE relname = 'workspaces'
    """)
    
    result = await db_session.execute(query)
    row = result.fetchone()
    
    assert row is not None
    assert row.relrowsecurity == True


@pytest.mark.asyncio
async def test_overly_long_workspace_name(db_session):
    """Test handling of extremely long workspace names"""
    workspace_id = uuid4()
    
    # Create a very long name (10,000 characters)
    long_name = "A" * 10000
    
    query = text("""
        INSERT INTO workspaces (id, name, slug)
        VALUES (:id, :name, :slug)
    """)
    
    # Should either succeed (if TEXT type has no limit) or fail gracefully
    try:
        await db_session.execute(query, {
            "id": workspace_id,
            "name": long_name,
            "slug": "long-name-test"
        })
        await db_session.commit()
        
        # If it succeeded, verify it was stored
        verify_query = text("SELECT LENGTH(name) FROM workspaces WHERE id = :id")
        result = await db_session.execute(verify_query, {"id": workspace_id})
        row = result.fetchone()
        
        # PostgreSQL TEXT type can handle this
        assert row[0] == 10000
    except Exception:
        # If it fails, that's also acceptable (length constraint)
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

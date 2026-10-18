"""
Integration Tests: Workspace + Endpoints
Tests interactions between workspace system and various API endpoints
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
    DATABASE_URL = DATABASE_URL.replace("localhost", "127.0.0.1")

@pytest_asyncio.fixture
async def db_session():
    """Create a test database session"""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_workspace(db_session):
    """Create a test workspace"""
    workspace_id = uuid4()
    
    query = text("""
        INSERT INTO workspaces (id, name, slug, description)
        VALUES (:id, :name, :slug, :description)
        RETURNING id
    """)
    
    result = await db_session.execute(query, {
        "id": workspace_id,
        "name": "Test Workspace",
        "slug": "test-workspace",
        "description": "Integration test workspace"
    })
    
    await db_session.commit()
    
    yield workspace_id
    
    # Cleanup
    cleanup = text("DELETE FROM workspaces WHERE id = :id")
    await db_session.execute(cleanup, {"id": workspace_id})
    await db_session.commit()


@pytest_asyncio.fixture
async def second_workspace(db_session):
    """Create a second test workspace for isolation testing"""
    workspace_id = uuid4()
    
    query = text("""
        INSERT INTO workspaces (id, name, slug, description)
        VALUES (:id, :name, :slug, :description)
        RETURNING id
    """)
    
    result = await db_session.execute(query, {
        "id": workspace_id,
        "name": "Second Workspace",
        "slug": "second-workspace",
        "description": "Second test workspace"
    })
    
    await db_session.commit()
    
    yield workspace_id
    
    # Cleanup
    cleanup = text("DELETE FROM workspaces WHERE id = :id")
    await db_session.execute(cleanup, {"id": workspace_id})
    await db_session.commit()


@pytest.mark.asyncio
async def test_create_segment_in_workspace(db_session, test_workspace):
    """Test creating a segment in a specific workspace"""
    segment_id = uuid4()
    
    query = text("""
        INSERT INTO segments (id, workspace_id, name, description, definition, is_dynamic)
        VALUES (:id, :workspace_id, :name, :description, :definition, :is_dynamic)
        RETURNING id
    """)
    
    result = await db_session.execute(query, {
        "id": segment_id,
        "workspace_id": test_workspace,
        "name": "Test Segment",
        "description": "Integration test segment",
        "definition": '{"operator": "AND", "conditions": []}',
        "is_dynamic": False
    })
    
    await db_session.commit()
    
    # Verify segment was created
    verify_query = text("""
        SELECT id, workspace_id FROM segments WHERE id = :id
    """)
    verify_result = await db_session.execute(verify_query, {"id": segment_id})
    row = verify_result.fetchone()
    
    assert row is not None
    assert row.workspace_id == test_workspace


@pytest.mark.asyncio
async def test_workspace_isolation_segments(db_session, test_workspace, second_workspace):
    """Test that segments from one workspace are not visible in another"""
    segment_id = uuid4()
    
    # Create segment in first workspace
    create_query = text("""
        INSERT INTO segments (id, workspace_id, name, description, definition, is_dynamic)
        VALUES (:id, :workspace_id, :name, :description, :definition, :is_dynamic)
    """)
    
    await db_session.execute(create_query, {
        "id": segment_id,
        "workspace_id": test_workspace,
        "name": "Workspace 1 Segment",
        "description": "Should not be visible in workspace 2",
        "definition": '{"operator": "AND", "conditions": []}',
        "is_dynamic": False
    })
    await db_session.commit()
    
    # Query for segments in second workspace
    query_workspace_2 = text("""
        SELECT COUNT(*) as count FROM segments WHERE workspace_id = :workspace_id
    """)
    result = await db_session.execute(query_workspace_2, {"workspace_id": second_workspace})
    count = result.scalar()
    
    # Should be 0 because segment belongs to first workspace
    assert count == 0


@pytest.mark.asyncio
async def test_create_person_in_workspace(db_session, test_workspace):
    """Test creating a person in a specific workspace"""
    person_id = uuid4()
    
    query = text("""
        INSERT INTO people (id, workspace_id, full_name, primary_email, company, role)
        VALUES (:id, :workspace_id, :full_name, :primary_email, :company, :role)
        RETURNING id
    """)
    
    result = await db_session.execute(query, {
        "id": person_id,
        "workspace_id": test_workspace,
        "full_name": "John Doe",
        "primary_email": "john@test.com",
        "company": "Test Corp",
        "role": "CEO"
    })
    
    await db_session.commit()
    
    # Verify person was created
    verify_query = text("SELECT id, workspace_id FROM people WHERE id = :id")
    verify_result = await db_session.execute(verify_query, {"id": person_id})
    row = verify_result.fetchone()
    
    assert row is not None
    assert row.workspace_id == test_workspace


@pytest.mark.asyncio
async def test_workspace_isolation_people(db_session, test_workspace, second_workspace):
    """Test that people from one workspace are not visible in another"""
    person_id = uuid4()
    
    # Create person in first workspace
    create_query = text("""
        INSERT INTO people (id, workspace_id, full_name, primary_email)
        VALUES (:id, :workspace_id, :full_name, :primary_email)
    """)
    
    await db_session.execute(create_query, {
        "id": person_id,
        "workspace_id": test_workspace,
        "full_name": "Workspace 1 Person",
        "primary_email": "person1@test.com"
    })
    await db_session.commit()
    
    # Query for people in second workspace
    query_workspace_2 = text("""
        SELECT COUNT(*) as count FROM people WHERE workspace_id = :workspace_id
    """)
    result = await db_session.execute(query_workspace_2, {"workspace_id": second_workspace})
    count = result.scalar()
    
    # Should be 0 because person belongs to first workspace
    assert count == 0


@pytest.mark.asyncio
async def test_cascade_delete_workspace(db_session):
    """Test that deleting a workspace cascades to segments and people"""
    workspace_id = uuid4()
    
    # Create workspace
    create_workspace = text("""
        INSERT INTO workspaces (id, name, slug)
        VALUES (:id, :name, :slug)
    """)
    await db_session.execute(create_workspace, {
        "id": workspace_id,
        "name": "Delete Test",
        "slug": "delete-test"
    })
    
    # Create segment in workspace
    segment_id = uuid4()
    create_segment = text("""
        INSERT INTO segments (id, workspace_id, name, definition, is_dynamic)
        VALUES (:id, :workspace_id, :name, :definition, :is_dynamic)
    """)
    await db_session.execute(create_segment, {
        "id": segment_id,
        "workspace_id": workspace_id,
        "name": "Test Segment",
        "definition": '{}',
        "is_dynamic": False
    })
    
    # Create person in workspace
    person_id = uuid4()
    create_person = text("""
        INSERT INTO people (id, workspace_id, full_name)
        VALUES (:id, :workspace_id, :full_name)
    """)
    await db_session.execute(create_person, {
        "id": person_id,
        "workspace_id": workspace_id,
        "full_name": "Test Person"
    })
    
    await db_session.commit()
    
    # Delete workspace (cascade should delete segment and person)
    delete_workspace = text("DELETE FROM workspaces WHERE id = :id")
    await db_session.execute(delete_workspace, {"id": workspace_id})
    await db_session.commit()
    
    # Verify segment was deleted
    check_segment = text("SELECT COUNT(*) FROM segments WHERE id = :id")
    segment_count = await db_session.execute(check_segment, {"id": segment_id})
    assert segment_count.scalar() == 0
    
    # Verify person was deleted
    check_person = text("SELECT COUNT(*) FROM people WHERE id = :id")
    person_count = await db_session.execute(check_person, {"id": person_id})
    assert person_count.scalar() == 0


@pytest.mark.asyncio
async def test_workspace_member_count(db_session, test_workspace):
    """Test querying workspace member statistics"""
    # Create multiple people in workspace
    for i in range(5):
        person_id = uuid4()
        query = text("""
            INSERT INTO people (id, workspace_id, full_name, primary_email)
            VALUES (:id, :workspace_id, :full_name, :primary_email)
        """)
        await db_session.execute(query, {
            "id": person_id,
            "workspace_id": test_workspace,
            "full_name": f"Person {i}",
            "primary_email": f"person{i}@test.com"
        })
    
    await db_session.commit()
    
    # Query for count
    count_query = text("""
        SELECT COUNT(*) as count FROM people WHERE workspace_id = :workspace_id
    """)
    result = await db_session.execute(count_query, {"workspace_id": test_workspace})
    count = result.scalar()
    
    assert count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

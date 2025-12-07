"""
Real Database Fixtures for Integration Tests
Uses actual database connections instead of mocks
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from database.connection import init_db, close_db, async_session_maker
from database.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Initialize real database for tests"""
    try:
        await init_db()
        yield
    finally:
        await close_db()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get real database session"""
    if not async_session_maker:
        pytest.skip("Database not initialized. Ensure database is running.")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def clean_db(db_session: AsyncSession):
    """Clean database before each test"""
    # Truncate tables (in reverse dependency order)
    from sqlalchemy import text
    
    tables_to_clean = [
        'media_creation_assets',
        'media_creation_projects',
        'media_creation_templates',
        'scheduled_posts',
        'video_clips',
        'video_analysis',
        'videos',
        'connector_configs',
        'social_media_accounts',
        'social_media_posts',
        'social_media_post_analytics',
        'social_media_analytics_snapshots',
    ]
    
    for table in tables_to_clean:
        try:
            await db_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        except Exception:
            # Table might not exist, skip
            pass
    
    await db_session.commit()
    yield
    # Cleanup happens in finally block above







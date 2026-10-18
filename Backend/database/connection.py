"""
Database Connection Manager
Handles connections to Supabase/PostgreSQL
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from supabase import create_client, Client
from typing import AsyncGenerator, Optional
from loguru import logger
import asyncio

from config import settings

# SQLAlchemy setup
Base = declarative_base()

# Database engine
engine: Optional[create_async_engine] = None
async_session_maker: Optional[async_sessionmaker] = None

# Supabase client
supabase_client: Optional[Client] = None


def create_thread_local_session_maker():
    """
    Create a fresh async session maker for use in background threads.
    Each thread running asyncio needs its own engine to avoid event loop conflicts.
    """
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    thread_engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=2,  # Smaller pool for background tasks
        max_overflow=5
    )
    
    return async_sessionmaker(
        thread_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


async def init_db():
    """Initialize database connections"""
    global engine, async_session_maker, supabase_client
    
    # Initialize SQLAlchemy engine
    try:
        # Convert postgres:// to postgresql:// for asyncpg
        db_url = settings.database_url
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        engine = create_async_engine(
            db_url,
            echo=False,  # Set to True only for debugging SQL queries
            pool_pre_ping=True,
            pool_size=20,  # Increased for batch analysis
            max_overflow=40,  # Increased for batch analysis
            pool_timeout=60  # Increased timeout
        )
        
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.success("✓ SQLAlchemy engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize SQLAlchemy: {e}")
        raise
    
    # Initialize Supabase client
    try:
        supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        logger.success("✓ Supabase client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        # Don't raise - Supabase is optional


async def close_db():
    """Close database connections"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session
    Use in FastAPI endpoints with Depends(get_db)
    """
    if not async_session_maker:
        # Try to reinitialize if not initialized
        logger.warning("Database not initialized, attempting to reinitialize...")
        try:
            await init_db()
        except Exception as e:
            logger.error(f"Failed to reinitialize database: {e}")
            raise RuntimeError("Database not initialized and reinitialization failed.")

    async with async_session_maker() as session:
        try:
            # Test connection with a simple query
            await session.execute(text("SELECT 1"))
            yield session
            await session.commit()
        except Exception as e:
            # Rollback on any error
            await session.rollback()
            # Re-raise the exception to be handled by FastAPI
            raise


def get_db_context():
    """
    Context manager for getting database session in background tasks
    Use with 'async with get_db_context() as db:'
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _context():
        if not async_session_maker:
            logger.warning("Database not initialized, attempting to reinitialize...")
            await init_db()

        async with async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _context()


def get_supabase() -> Client:
    """
    Get Supabase client
    Use in FastAPI endpoints with Depends(get_supabase)
    """
    if not supabase_client:
        raise RuntimeError("Supabase not initialized")
    return supabase_client


def get_db_session_factory() -> async_sessionmaker:
    """
    Get the database session factory
    Used in tests and background workers to create new sessions
    """
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return async_session_maker


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for use in services/pipelines.
    Initializes DB connection if not already initialized.
    
    Usage:
        async for session in get_async_session():
            await session.execute(...)
    
    Or with anext:
        session = await anext(get_async_session())
    """
    global async_session_maker
    
    if not async_session_maker:
        await init_db()
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# CRUD base class
class CRUDBase:
    """Base class for CRUD operations"""
    
    def __init__(self, model):
        self.model = model
    
    async def get(self, db: AsyncSession, id: any):
        """Get a single record by ID"""
        from sqlalchemy import select
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        """Get multiple records"""
        from sqlalchemy import select
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: dict):
        """Create a new record"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(self, db: AsyncSession, db_obj, obj_in: dict):
        """Update a record"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: any):
        """Delete a record"""
        from sqlalchemy import delete
        await db.execute(delete(self.model).where(self.model.id == id))
        await db.flush()


# Utility functions
async def test_connection():
    """Test database connection"""
    try:
        await init_db()
        
        if engine:
            async with async_session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
                logger.success("✓ Database connection test passed")
                return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
    finally:
        await close_db()
    
    return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection())

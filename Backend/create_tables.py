"""
Create all database tables from SQLAlchemy models
"""
import asyncio
from database import connection
from database.models import Base
from loguru import logger

async def create_tables():
    """Create all tables defined in models"""
    try:
        # Initialize database connection
        await connection.init_db()
        logger.info("Initializing database...")
        
        # Create all tables
        async with connection.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.success("✓ All tables created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise
    finally:
        await connection.close_db()

if __name__ == '__main__':
    asyncio.run(create_tables())

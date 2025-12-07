"""
Add retry tracking fields to scheduled_posts table
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
import database.connection as db_conn
from loguru import logger


async def add_retry_fields():
    """Add retry_count, next_retry_at, and last_error columns"""
    # Initialize database first
    await db_conn.init_db()
    
    async with db_conn.engine.begin() as conn:
        try:
            # Add retry_count column
            await conn.execute(text("""
                ALTER TABLE scheduled_posts 
                ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0
            """))
            logger.info("✓ Added retry_count column")
            
            # Add next_retry_at column
            await conn.execute(text("""
                ALTER TABLE scheduled_posts 
                ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE
            """))
            logger.info("✓ Added next_retry_at column")
            
            # Add last_error column
            await conn.execute(text("""
                ALTER TABLE scheduled_posts 
                ADD COLUMN IF NOT EXISTS last_error TEXT
            """))
            logger.info("✓ Added last_error column")
            
            logger.success("✓ Migration completed successfully")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    await db_conn.close_db()


if __name__ == "__main__":
    asyncio.run(add_retry_fields())

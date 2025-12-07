"""
Add missing columns to existing tables
"""
import asyncio
from sqlalchemy import text
from database import connection
from loguru import logger

async def add_missing_columns():
    """Add missing columns to existing tables"""
    try:
        await connection.init_db()
        logger.info("Adding missing columns...")
        
        async with connection.engine.begin() as conn:
            # Add video_metadata column if it doesn't exist
            await conn.execute(text("""
                ALTER TABLE original_videos 
                ADD COLUMN IF NOT EXISTS video_metadata JSONB;
            """))
            
        logger.success("✓ Missing columns added successfully!")
        
    except Exception as e:
        logger.error(f"Failed to add columns: {e}")
        raise
    finally:
        await connection.close_db()

if __name__ == '__main__':
    asyncio.run(add_missing_columns())

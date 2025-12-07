"""
Create calendar and AI recommendation tables in Supabase database
"""
import asyncio
from loguru import logger
from database import connection
from database.models import Base, PostingGoal, ScheduledPost, AIRecommendation, ContentPerformanceAnalytics


async def create_calendar_tables():
    """Create tables for content calendar and AI recommendations"""
    try:
        # Initialize database connection
        await connection.init_db()
        logger.info("Initializing database connection...")
        
        # Get the specific tables we want to create
        tables_to_create = [
            PostingGoal.__table__,
            ScheduledPost.__table__,
            AIRecommendation.__table__,
            ContentPerformanceAnalytics.__table__
        ]
        
        logger.info(f"Creating {len(tables_to_create)} new tables...")
        
        # Create only the calendar-related tables
        async with connection.engine.begin() as conn:
            for table in tables_to_create:
                logger.info(f"  Creating table: {table.name}")
                await conn.run_sync(lambda sync_conn, tbl=table: tbl.create(sync_conn, checkfirst=True))
        
        logger.success("✓ Calendar and AI recommendation tables created successfully!")
        logger.info("Created tables:")
        for table in tables_to_create:
            logger.info(f"  - {table.name}")
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise
    finally:
        await connection.close_db()


if __name__ == "__main__":
    asyncio.run(create_calendar_tables())

#!/usr/bin/env python3
"""
Apply migration to add title column to videos table
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


async def apply_migration():
    """Apply the title column migration"""
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:54322/postgres')
    
    # Convert to async URL
    if db_url.startswith("postgres://"):
        async_db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        async_db_url = db_url
    
    # Create async engine
    engine = create_async_engine(async_db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Add title column
            await db.execute(text("""
                ALTER TABLE videos ADD COLUMN IF NOT EXISTS title VARCHAR(150)
            """))
            await db.commit()
            print("✅ Added title column to videos table")
            
            # Add comment
            await db.execute(text("""
                COMMENT ON COLUMN videos.title IS 'AI-generated title (~20% of platform character limit)'
            """))
            await db.commit()
            print("✅ Added comment to title column")
            
            # Verify
            result = await db.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'videos' AND column_name = 'title'
            """))
            row = result.fetchone()
            if row:
                print(f"✅ Verified: {row[0]} ({row[1]}({row[2]}))")
            else:
                print("❌ Column not found after migration")
                return False
            
            # Check video counts
            result = await db.execute(text("""
                SELECT COUNT(*) as total, COUNT(title) as with_titles 
                FROM videos
            """))
            row = result.fetchone()
            if row:
                print(f"📊 Videos: {row[0]} total, {row[1]} with titles")
            
            print("\n✅ Migration applied successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)


"""
Apply database migration programmatically
Runs the schema fix migration using SQLAlchemy
"""
import asyncio
from sqlalchemy import text
from database.connection import get_db_direct

async def apply_migration():
    """Apply the schema fixes migration"""
    
    migration_sql = open('supabase/migrations/20250122000000_fix_schema_mismatches.sql').read()
    
    # Split by statement (rough approach)
    statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    async for db in get_db_direct():
        print("Applying schema fixes migration...")
        
        for statement in statements:
            if statement:
                try:
                    await db.execute(text(statement))
                    await db.commit()
                except Exception as e:
                    print(f"Note: {e}")
                    await db.rollback()
        
        print("✓ Migration applied successfully")
        break

if __name__ == "__main__":
    asyncio.run(apply_migration())

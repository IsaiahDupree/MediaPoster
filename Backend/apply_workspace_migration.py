#!/usr/bin/env python3
"""
Apply the workspace_id migration to people and segments tables
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def apply_migration():
    """Apply the workspace migration."""
    print("🚀 Applying workspace_id migration...")
    
    # Read migration file
    migration_path = Path(__file__).parent / "database" / "migrations" / "010_add_workspace_to_people.sql"
    
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    migration_sql = migration_path.read_text()
    
    # Create engine
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url, echo=True)
    
    # Apply migration - split by DO blocks and COMMENT statements
    async with engine.begin() as conn:
        try:
            # Split migration into individual statements
            # Each DO $$ ... END $$; is one statement
            # Each COMMENT is one statement
            import re
            
            # Extract DO blocks
            do_blocks = re.findall(r'DO \$\$.*?END \$\$;', migration_sql, re.DOTALL)
            
            # Extract COMMENT statements
            comment_statements = re.findall(r'COMMENT ON.*?;', migration_sql)
            
            print(f"Found {len(do_blocks)} DO blocks and {len(comment_statements)} COMMENT statements")
            
            # Execute DO blocks
            for i, block in enumerate(do_blocks, 1):
                print(f"Executing DO block {i}/{len(do_blocks)}...")
                await conn.execute(text(block))
            
            # Execute COMMENT statements
            for i, comment in enumerate(comment_statements, 1):
                print(f"Executing COMMENT {i}/{len(comment_statements)}...")
                await conn.execute(text(comment))
            
            print("✅ Migration applied successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)

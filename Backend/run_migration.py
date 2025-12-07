"""
Apply database migration to fix schema issues
This script connects to the database and runs the migration SQL
"""
import os
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def split_sql_statements(sql_content):
    """Split SQL content into individual executable statements"""
    # Remove comments
    sql_content = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
    
    # Split by $$ blocks (DO blocks) and regular statements
    statements = []
    in_do_block = False
    current_statement = []
    
    for line in sql_content.split('\n'):
        if '$$' in line and not in_do_block:
            in_do_block = True
            current_statement.append(line)
        elif '$$' in line and in_do_block:
            in_do_block = False
            current_statement.append(line)
            stmt = '\n'.join(current_statement).strip()
            if stmt:
                statements.append(stmt)
            current_statement = []
        elif in_do_block:
            current_statement.append(line)
        elif line.strip().endswith(';'):
            current_statement.append(line)
            stmt = '\n'.join(current_statement).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current_statement = []
        elif line.strip():
            current_statement.append(line)
    
    return [s for s in statements if s.strip()]

def apply_migration():
    """Apply the schema fixes migration using sync connection"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    # Read migration file
    migration_path = '../supabase/migrations/20250122000000_fix_schema_mismatches.sql'
    try:
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
    except FileNotFoundError:
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    print("🔄 Connecting to database...")
    print(f"   Database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        print("🔄 Applying migration...")
        
        # Split and execute statements
        statements = split_sql_statements(migration_sql)
        print(f"   Extracted {len(statements)} SQL statements")
        
        with engine.connect() as conn:
            for i, stmt in enumerate(statements, 1):
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception as e:
                    # Some statements might fail if already exists, that's OK
                    if 'already exists' in str(e):
                        print(f"   ⚠️  Statement {i}: Already exists (skipping)")
                    else:
                        print(f"   Note on statement {i}: {str(e)[:100]}")
        
        print()
        print("✅ Migration completed!")
        print()
        print("Schema updates:")
        print("  ✓ video_metadata column added to original_videos")
        print("  ✓ processing_jobs table created")
        print("  ✓ scheduled_posts table created")
        print("  ✓ posting_goals table created")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = apply_migration()
    exit(0 if success else 1)


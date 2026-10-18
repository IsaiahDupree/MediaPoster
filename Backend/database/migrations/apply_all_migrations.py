#!/usr/bin/env python3
"""
Apply all database migrations to local Supabase instance.
Usage: python apply_all_migrations.py [DATABASE_URL]
"""

import os
import sys
import subprocess
from pathlib import Path

# Migration order (respecting dependencies)
MIGRATIONS = [
    "000_content_base_tables.sql",
    "001_people_graph.sql",
    "002_content_graph_extensions.sql",
    "003_connectors.sql",
    "003_base_video_tables.sql",
    "004_content_intelligence_video_analysis.sql",
    "005_content_intelligence_platform_tracking.sql",
    "006_content_intelligence_insights_metrics.sql",
    "008_video_library.sql",
    "009_fix_video_library_fk.sql",
    "009_video_thumbnails.sql",
    "005_video_clips.sql",
    "006_segment_editing.sql",
    "007_publishing_queue.sql",
]

def apply_migrations(database_url: str):
    """Apply all migrations in order."""
    script_dir = Path(__file__).parent
    success_count = 0
    failed_count = 0
    failed_migrations = []
    
    print("🚀 Applying all migrations to local Supabase...")
    print(f"Database: {database_url}")
    print("")
    
    for migration in MIGRATIONS:
        migration_path = script_dir / migration
        
        if not migration_path.exists():
            print(f"⚠️  Skipping {migration} (file not found)")
            continue
        
        print(f"📄 Applying {migration}...")
        
        try:
            # Use psql to apply migration
            result = subprocess.run(
                ["psql", database_url, "-f", str(migration_path)],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ {migration} applied successfully")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to apply {migration}")
            print(f"   Error: {e.stderr}")
            failed_count += 1
            failed_migrations.append(migration)
        except FileNotFoundError:
            print(f"❌ psql not found. Please install PostgreSQL client tools.")
            print(f"   macOS: brew install postgresql")
            print(f"   Or use Supabase CLI: supabase db reset")
            sys.exit(1)
        print("")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 Migration Summary:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {failed_count}")
    
    if failed_count > 0:
        print("")
        print("Failed migrations:")
        for failed in failed_migrations:
            print(f"   - {failed}")
        return False
    else:
        print("")
        print("🎉 All migrations applied successfully!")
        return True

if __name__ == "__main__":
    # Get database URL from argument or environment variable
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    elif "DATABASE_URL" in os.environ:
        database_url = os.environ["DATABASE_URL"]
    else:
        print("Error: DATABASE_URL not provided")
        print("Usage: python apply_all_migrations.py [DATABASE_URL]")
        print("Or set DATABASE_URL environment variable")
        sys.exit(1)
    
    success = apply_migrations(database_url)
    sys.exit(0 if success else 1)



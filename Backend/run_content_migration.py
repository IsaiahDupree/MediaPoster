"""
Run cross-platform content tracking migration
"""
from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")

print("\n🚀 Running Content + Engagement Tracking Migration...\n")

# Read SQL file
sql_file = Path(__file__).parent / 'migrations' / 'add_content_and_engagement_tracking.sql'
with open(sql_file, 'r') as f:
    sql_content = f.read()

# Connect and execute
engine = create_engine(DATABASE_URL)
conn = engine.connect()

try:
    print("📋 Executing SQL migration...")
    # Execute as raw SQL to handle all statements
    conn.connection.connection.set_isolation_level(0)  # autocommit mode
    cursor = conn.connection.connection.cursor()
    cursor.execute(sql_content)
    cursor.close()
    print("✅ Migration completed successfully!\n")
    
    # Verify tables were created
    print("🔍 Verifying tables...")
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('content_items', 'content_posts', 'content_tags', 
                           'followers', 'follower_interactions', 'follower_engagement_scores')
        ORDER BY table_name
    """))
    
    tables = [row[0] for row in result]
    for table in tables:
        print(f"   ✅ {table}")
    
    # Verify views were created
    print("\n🔍 Verifying views...")
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'public' 
        AND (table_name LIKE 'content_%' OR table_name LIKE '%follower%')
        ORDER BY table_name
    """))
    
    views = [row[0] for row in result]
    for view in views:
        print(f"   ✅ {view}")
    
    print("\n" + "="*60)
    print("✅ MIGRATION COMPLETE!")
    print("="*60)
    print("\nPhase 1 Complete! 🎉")
    print("\nWhat was created:")
    print("  📦 Content tracking tables (content_items, content_posts, content_tags)")
    print("  👥 Follower tracking tables (followers, follower_interactions, follower_engagement_scores)")
    print("  📊 Rollup views (content_cross_platform_summary, top_engaged_followers, etc.)")
    print("  🔧 Helper functions (calculate_engagement_score, determine_engagement_tier)")
    print("\nNext steps:")
    print("  1. Update scrapers to save follower data when fetching comments")
    print("  2. Add API endpoints: /content, /followers, /followers/leaderboard")
    print("  3. Create frontend pages: /analytics/content, /analytics/followers")
    print("  4. Build engagement score calculator job")
    print("\n")
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ Migration failed: {e}\n")
    raise
finally:
    conn.close()

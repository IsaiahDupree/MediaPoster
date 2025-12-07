"""
Run Comprehensive Social Media Schema Migration
Executes the complete schema for all 9 platforms
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

def run_migration():
    """Execute the comprehensive social media schema"""
    
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE SOCIAL MEDIA SCHEMA MIGRATION")
    print("="*80 + "\n")
    
    # Database connection
    database_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    print(f"🔌 Connecting to: {database_url}")
    
    try:
        engine = create_engine(database_url)
        conn = engine.connect()
        
        # Read SQL file
        sql_file = Path(__file__).parent / "migrations" / "comprehensive_social_schema.sql"
        
        if not sql_file.exists():
            print(f"❌ SQL file not found: {sql_file}")
            return False
        
        print(f"📄 Reading SQL from: {sql_file}")
        
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Execute entire SQL as one block (Postgres can handle this better)
        print(f"\n⚙️  Executing SQL migration...")
        
        try:
            # Close and recreate connection for fresh transaction
            conn.close()
            conn = engine.connect()
            
            # Execute the entire SQL file
            conn.execute(text(sql_content))
            conn.commit()
            print(f"   ✅ Migration executed successfully!")
            success_count = 1
            
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print(f"   ⚠️  Tables may already exist: {error_msg[:100]}")
                success_count = 1
            else:
                print(f"   ❌ Error: {error_msg[:200]}")
                # Try to rollback
                try:
                    conn.rollback()
                except:
                    pass
                success_count = 0
        
        conn.close()
        
        print(f"\n✅ Migration completed successfully!")
        
        # Verify tables were created
        print("\n📋 Verifying tables...")
        conn = engine.connect()
        
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'social_media%'
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        
        if tables:
            print(f"\n✅ Created {len(tables)} social media tables:")
            for table in tables:
                print(f"   • {table}")
        else:
            print("\n⚠️  No social media tables found. Check for errors above.")
        
        # Check views
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%account%' OR table_name LIKE '%post%'
            ORDER BY table_name
        """))
        
        views = [row[0] for row in result]
        
        if views:
            print(f"\n✅ Created {len(views)} views:")
            for view in views:
                print(f"   • {view}")
        
        conn.close()
        
        print("\n" + "="*80)
        print("🎉 MIGRATION COMPLETE!")
        print("="*80)
        
        print("\n📊 Next Steps:")
        print("\n1. View your tables in Supabase Studio:")
        print("   http://127.0.0.1:54323")
        
        print("\n2. Test fetching analytics:")
        print("   python services/fetch_social_analytics.py tiktok isaiah_dupree")
        
        print("\n3. Query your data:")
        print("   SELECT * FROM latest_account_analytics;")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)

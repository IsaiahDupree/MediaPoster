#!/usr/bin/env python3
"""
Simple Migration Test - Direct Database Connection
Tests all critical tables, columns, and the new title column
"""
import os
import sys
from pathlib import Path

# Use psycopg2 for direct connection (no async needed)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 not installed. Installing...")
    os.system("pip3 install psycopg2-binary")
    import psycopg2
    from psycopg2.extras import RealDictCursor


def test_migrations():
    """Test all critical migrations"""
    # Get database URL
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')
    
    # Parse connection string
    if db_url.startswith('postgresql://'):
        parts = db_url.replace('postgresql://', '').split('@')
        if len(parts) == 2:
            user_pass, host_db = parts
            user, password = user_pass.split(':')
            host_port, database = host_db.split('/')
            if ':' in host_port:
                host, port = host_port.split(':')
            else:
                host, port = host_port, '5432'
        else:
            print("❌ Could not parse DATABASE_URL")
            return False
    
    results = {
        'tables': {'found': [], 'missing': []},
        'columns': {'found': [], 'missing': []},
        'title_column': False
    }
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("="*60)
        print("MIGRATION TEST - MediaPoster Database")
        print("="*60)
        print()
        
        # Test 1: Critical Tables
        print("📋 Testing Critical Tables...")
        critical_tables = [
            'videos',
            'video_analysis',
            'scheduled_posts',
            'posted_content',
            'event_history',
            'social_accounts',
            'social_media_accounts',
            'agent_events',
            'agent_runs',
            'agent_schedules',
            'agent_queue',
            'experiments',
            'narrative_goals',
        ]
        
        for table in critical_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                )
            """, (table,))
            exists = cur.fetchone()['exists']
            if exists:
                results['tables']['found'].append(table)
                print(f"  ✅ {table}")
            else:
                results['tables']['missing'].append(table)
                print(f"  ❌ {table} - MISSING")
        
        print()
        print("📋 Testing Critical Columns...")
        
        # Test 2: Critical Columns (including new title column)
        critical_columns = [
            ('videos', 'title'),  # NEW: The column we just added
            ('videos', 'file_size'),
            ('videos', 'source_uri'),
            ('scheduled_posts', 'source'),
            ('scheduled_posts', 'media_project_id'),
            ('video_analysis', 'deep_analysis'),
            ('social_accounts', 'account_role'),
        ]
        
        for table, column in critical_columns:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s AND column_name = %s
                )
            """, (table, column))
            exists = cur.fetchone()['exists']
            if exists:
                results['columns']['found'].append(f"{table}.{column}")
                if table == 'videos' and column == 'title':
                    results['title_column'] = True
                print(f"  ✅ {table}.{column}")
            else:
                results['columns']['missing'].append(f"{table}.{column}")
                print(f"  ❌ {table}.{column} - MISSING")
        
        # Test 3: Verify title column details
        print()
        print("📋 Verifying Title Column Details...")
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'videos' AND column_name = 'title'
        """)
        title_info = cur.fetchone()
        if title_info:
            print(f"  ✅ Column: {title_info['column_name']}")
            print(f"  ✅ Type: {title_info['data_type']}")
            print(f"  ✅ Max Length: {title_info['character_maximum_length']}")
            print(f"  ✅ Nullable: {title_info['is_nullable']}")
        else:
            print("  ❌ Title column not found!")
        
        # Summary
        print()
        print("="*60)
        print("MIGRATION TEST SUMMARY")
        print("="*60)
        print(f"\nTables: {len(results['tables']['found'])}/{len(critical_tables)} found")
        if results['tables']['missing']:
            print(f"  ⚠️  Missing: {', '.join(results['tables']['missing'])}")
        
        print(f"\nColumns: {len(results['columns']['found'])}/{len(critical_columns)} found")
        if results['columns']['missing']:
            print(f"  ⚠️  Missing: {', '.join(results['columns']['missing'])}")
        
        if results['title_column']:
            print(f"\n  ✅ Title column migration: SUCCESS")
        else:
            print(f"\n  ❌ Title column migration: FAILED")
        
        total_tests = len(critical_tables) + len(critical_columns)
        total_passed = len(results['tables']['found']) + len(results['columns']['found'])
        
        print(f"\n{'='*60}")
        if total_passed == total_tests:
            print(f"✅ ALL TESTS PASSED ({total_passed}/{total_tests})")
            success = True
        else:
            print(f"⚠️  {total_passed}/{total_tests} tests passed ({total_tests - total_passed} failures)")
            success = False
        print("="*60)
        
        cur.close()
        conn.close()
        return success
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_migrations()
    sys.exit(0 if success else 1)


#!/usr/bin/env python3
"""
Comprehensive Migration Test Script
Tests all critical tables, columns, and relationships from migrations
"""
import asyncio
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import init_db, get_db


async def test_migrations():
    """Test all critical migrations"""
    await init_db()
    
    results = {
        'tables': {'found': [], 'missing': []},
        'columns': {'found': [], 'missing': []},
        'relationships': {'found': [], 'missing': []}
    }
    
    async for db in get_db():
        # Test 1: Critical Tables
        critical_tables = [
            'event_history',
            'posted_content',
            'social_media_conversations',
            'automation_actions',
            'trend_hashtags',
            'ai_video_generations',
            'agent_events',
            'experiments',
            'narrative_goals',
            'agent_runs',
            'agent_schedules',
            'agent_queue',
            'social_accounts',
            'social_media_accounts'
        ]
        
        for table in critical_tables:
            result = await db.execute(
                text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')")
            )
            exists = result.scalar()
            if exists:
                results['tables']['found'].append(table)
                print(f"✅ {table}")
            else:
                results['tables']['missing'].append(table)
                print(f"❌ {table} - MISSING")
        
        # Test 2: Critical Columns
        critical_columns = [
            ('scheduled_posts', 'source'),
            ('scheduled_posts', 'media_project_id'),
            ('video_analysis', 'deep_analysis'),
            ('social_accounts', 'account_role')
        ]
        
        for table, column in critical_columns:
            result = await db.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = '{column}'
                )
            """))
            exists = result.scalar()
            if exists:
                results['columns']['found'].append(f"{table}.{column}")
                print(f"✅ {table}.{column}")
            else:
                results['columns']['missing'].append(f"{table}.{column}")
                print(f"❌ {table}.{column} - MISSING")
        
        # Test 3: Foreign Key Relationships
        fk_tests = [
            ('social_media_conversations', 'account_id', 'social_accounts', 'id'),
            ('automation_actions', 'account_id', 'social_accounts', 'id'),
            ('agent_steps', 'run_id', 'agent_runs', 'id'),
        ]
        
        for child_table, fk_column, parent_table, pk_column in fk_tests:
            result = await db.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = '{child_table}'
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND kcu.referenced_table_name = '{parent_table}'
                )
            """))
            exists = result.scalar()
            if exists:
                results['relationships']['found'].append(f"{child_table}.{fk_column} -> {parent_table}.{pk_column}")
                print(f"✅ FK: {child_table}.{fk_column} -> {parent_table}.{pk_column}")
            else:
                results['relationships']['missing'].append(f"{child_table}.{fk_column} -> {parent_table}.{pk_column}")
                print(f"❌ FK: {child_table}.{fk_column} -> {parent_table}.{pk_column} - MISSING")
        
        # Summary
        print("\n" + "="*60)
        print("MIGRATION TEST SUMMARY")
        print("="*60)
        print(f"\nTables: {len(results['tables']['found'])}/{len(critical_tables)} found")
        if results['tables']['missing']:
            print(f"  Missing: {', '.join(results['tables']['missing'])}")
        
        print(f"\nColumns: {len(results['columns']['found'])}/{len(critical_columns)} found")
        if results['columns']['missing']:
            print(f"  Missing: {', '.join(results['columns']['missing'])}")
        
        print(f"\nForeign Keys: {len(results['relationships']['found'])}/{len(fk_tests)} found")
        if results['relationships']['missing']:
            print(f"  Missing: {', '.join(results['relationships']['missing'])}")
        
        total_tests = len(critical_tables) + len(critical_columns) + len(fk_tests)
        total_passed = len(results['tables']['found']) + len(results['columns']['found']) + len(results['relationships']['found'])
        
        print(f"\n{'='*60}")
        if total_passed == total_tests:
            print(f"✅ ALL TESTS PASSED ({total_passed}/{total_tests})")
        else:
            print(f"⚠️  {total_passed}/{total_tests} tests passed ({total_tests - total_passed} failures)")
        print("="*60)
        
        break


if __name__ == "__main__":
    asyncio.run(test_migrations())


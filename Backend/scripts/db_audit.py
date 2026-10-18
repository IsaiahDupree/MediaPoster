#!/usr/bin/env python3
"""
Database Audit Script
=====================
Compares database schema against code expectations.

Run: python scripts/db_audit.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Set, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from config import settings


# Tables expected by various services
EXPECTED_TABLES = {
    # video_ready_pipeline.py
    "original_videos": {
        "service": "video_ready_pipeline.py",
        "columns": ["id", "filename", "file_path", "file_size", "status", "source", "metadata", "ai_title", "ai_description", "transcript", "created_at", "updated_at"]
    },
    "analyzed_videos": {
        "service": "video_ready_pipeline.py",
        "columns": ["id", "original_video_id", "transcript", "ai_title", "ai_description", "ai_hashtags", "virality_score", "duration_seconds", "topics", "platform_captions", "created_at", "updated_at"]
    },
    # post_scheduler.py
    "scheduled_posts": {
        "service": "post_scheduler.py",
        "columns": ["id", "clip_id", "content_variant_id", "platform", "platform_account_id", "scheduled_time", "status", "caption", "title", "hashtags", "account_username", "metadata", "created_at", "updated_at"]
    },
    # slot_executor.py
    "weekly_plan_slots": {
        "service": "slot_executor.py",
        "columns": ["id", "plan_id", "slot_date", "slot_time", "platform", "channel", "awareness_level", "fate_target", "cta_strength", "target_offer_id", "target_icp_id", "status", "metadata", "created_at", "updated_at"]
    },
    # blotato_service.py
    "platform_accounts": {
        "service": "blotato_service.py",
        "columns": ["id", "platform", "username", "display_name", "account_id", "is_active", "metadata", "created_at", "updated_at"]
    },
    # posted content
    "posted_tweets": {
        "service": "twitter_poster.py",
        "columns": []  # Will discover
    },
    "posted_visual_content": {
        "service": "visual_content_poster.py",
        "columns": []
    },
    # safari
    "safari_videos": {
        "service": "safari_automation",
        "columns": []
    },
    # sora
    "sora_video_pipeline": {
        "service": "sora_pipeline.py",
        "columns": []
    },
}


def get_db_tables(cursor) -> Dict[str, List[str]]:
    """Get all tables and their columns from DB"""
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    result = {}
    for table in tables:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        columns = [row[0] for row in cursor.fetchall()]
        result[table] = columns
    
    return result


def audit_tables(db_tables: Dict[str, List[str]]) -> Dict[str, Any]:
    """Audit expected tables vs actual tables"""
    results = {
        "found": [],
        "missing": [],
        "column_mismatches": [],
        "extra_tables": []
    }
    
    expected_names = set(EXPECTED_TABLES.keys())
    actual_names = set(db_tables.keys())
    
    # Check expected tables
    for table_name, expected in EXPECTED_TABLES.items():
        if table_name in db_tables:
            results["found"].append(table_name)
            
            # Check columns if specified
            if expected["columns"]:
                actual_cols = set(db_tables[table_name])
                expected_cols = set(expected["columns"])
                
                missing_cols = expected_cols - actual_cols
                extra_cols = actual_cols - expected_cols
                
                if missing_cols or extra_cols:
                    results["column_mismatches"].append({
                        "table": table_name,
                        "service": expected["service"],
                        "missing_columns": list(missing_cols),
                        "extra_columns": list(extra_cols)
                    })
        else:
            results["missing"].append({
                "table": table_name,
                "service": expected["service"]
            })
    
    return results


def run_tests(cursor) -> List[Dict[str, Any]]:
    """Run basic tests against the database"""
    tests = []
    
    # Test 1: original_videos insert/select
    try:
        cursor.execute("SELECT COUNT(*) FROM original_videos")
        count = cursor.fetchone()[0]
        tests.append({"test": "original_videos SELECT", "status": "✅", "result": f"{count} rows"})
    except Exception as e:
        tests.append({"test": "original_videos SELECT", "status": "❌", "error": str(e)})
    
    # Test 2: analyzed_videos join
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM analyzed_videos av
            LEFT JOIN original_videos ov ON av.original_video_id = ov.id
        """)
        count = cursor.fetchone()[0]
        tests.append({"test": "analyzed_videos JOIN", "status": "✅", "result": f"{count} rows"})
    except Exception as e:
        tests.append({"test": "analyzed_videos JOIN", "status": "❌", "error": str(e)})
    
    # Test 3: scheduled_posts query (from post_scheduler.py)
    try:
        cursor.execute("""
            SELECT id, platform, scheduled_time, status
            FROM scheduled_posts
            WHERE status = 'scheduled'
            LIMIT 5
        """)
        rows = cursor.fetchall()
        tests.append({"test": "scheduled_posts query", "status": "✅", "result": f"{len(rows)} scheduled"})
    except Exception as e:
        tests.append({"test": "scheduled_posts query", "status": "❌", "error": str(e)})
    
    # Test 4: weekly_plan_slots query (from slot_executor.py)
    try:
        cursor.execute("""
            SELECT id, slot_date, slot_time, platform, status
            FROM weekly_plan_slots
            WHERE status = 'scheduled'
            LIMIT 5
        """)
        rows = cursor.fetchall()
        tests.append({"test": "weekly_plan_slots query", "status": "✅", "result": f"{len(rows)} slots"})
    except Exception as e:
        tests.append({"test": "weekly_plan_slots query", "status": "❌", "error": str(e)})
    
    # Test 5: platform_accounts exists
    try:
        cursor.execute("SELECT COUNT(*) FROM platform_accounts WHERE is_active = true")
        count = cursor.fetchone()[0]
        tests.append({"test": "platform_accounts active", "status": "✅", "result": f"{count} active"})
    except Exception as e:
        tests.append({"test": "platform_accounts query", "status": "❌", "error": str(e)})
    
    # Test 6: Check foreign key integrity
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM analyzed_videos av
            WHERE av.original_video_id IS NOT NULL 
            AND NOT EXISTS (SELECT 1 FROM original_videos ov WHERE ov.id = av.original_video_id)
        """)
        orphans = cursor.fetchone()[0]
        if orphans == 0:
            tests.append({"test": "FK integrity check", "status": "✅", "result": "No orphans"})
        else:
            tests.append({"test": "FK integrity check", "status": "⚠️", "result": f"{orphans} orphans"})
    except Exception as e:
        tests.append({"test": "FK integrity check", "status": "❌", "error": str(e)})
    
    return tests


def main():
    print("\n" + "="*70)
    print("🔍 DATABASE AUDIT - Schema vs Code")
    print("="*70 + "\n")
    
    try:
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1
    
    # Get actual DB schema
    print("📊 Fetching database schema...")
    db_tables = get_db_tables(cursor)
    print(f"   Found {len(db_tables)} tables\n")
    
    # Audit tables
    print("🔎 AUDITING TABLES vs CODE EXPECTATIONS")
    print("-" * 50)
    
    audit = audit_tables(db_tables)
    
    print(f"\n✅ FOUND ({len(audit['found'])} tables):")
    for t in sorted(audit['found']):
        print(f"   • {t}")
    
    if audit['missing']:
        print(f"\n❌ MISSING ({len(audit['missing'])} tables):")
        for m in audit['missing']:
            print(f"   • {m['table']} (needed by {m['service']})")
    
    if audit['column_mismatches']:
        print(f"\n⚠️ COLUMN MISMATCHES ({len(audit['column_mismatches'])}):")
        for cm in audit['column_mismatches']:
            print(f"\n   📋 {cm['table']} ({cm['service']}):")
            if cm['missing_columns']:
                print(f"      Missing: {', '.join(cm['missing_columns'])}")
            if cm['extra_columns']:
                print(f"      Extra: {', '.join(cm['extra_columns'][:5])}{'...' if len(cm['extra_columns']) > 5 else ''}")
    
    # Run tests
    print("\n" + "="*70)
    print("🧪 RUNNING DATABASE TESTS")
    print("-" * 50)
    
    tests = run_tests(cursor)
    
    for test in tests:
        status = test['status']
        name = test['test']
        result = test.get('result', test.get('error', ''))
        print(f"   {status} {name}: {result}")
    
    # Summary
    print("\n" + "="*70)
    print("📋 AUDIT SUMMARY")
    print("="*70)
    
    passed = sum(1 for t in tests if t['status'] == '✅')
    failed = sum(1 for t in tests if t['status'] == '❌')
    warnings = sum(1 for t in tests if t['status'] == '⚠️')
    
    print(f"\n   Tables: {len(audit['found'])} found, {len(audit['missing'])} missing")
    print(f"   Column issues: {len(audit['column_mismatches'])}")
    print(f"   Tests: {passed} passed, {failed} failed, {warnings} warnings")
    
    if audit['missing'] or failed > 0:
        print("\n   ❌ AUDIT FAILED - Issues need attention")
        return 1
    else:
        print("\n   ✅ AUDIT PASSED")
        return 0
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    sys.exit(main())

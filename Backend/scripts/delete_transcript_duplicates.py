#!/usr/bin/env python3
"""
Delete Transcript Duplicates
=============================
Deletes duplicate videos identified by similar transcripts.
- Removes database records (videos, video_analysis)
- Optionally deletes files from filesystem
- Uses the duplicate report from find_duplicate_transcripts.py
"""

import asyncio
import asyncpg
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher

DB_URL = "postgresql://postgres:postgres@localhost:54322/postgres"

def similarity(a: str, b: str) -> float:
    """Calculate text similarity (0.0 to 1.0)"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def find_duplicates(conn) -> list:
    """Find all duplicate video pairs based on transcripts"""
    print("📊 Fetching videos with transcripts...")
    rows = await conn.fetch("""
        SELECT 
            v.id,
            v.file_name,
            v.source_uri,
            va.transcript,
            v.created_at
        FROM videos v
        JOIN video_analysis va ON va.video_id = v.id
        WHERE va.transcript IS NOT NULL 
          AND va.transcript != ''
          AND LENGTH(va.transcript) > 50
        ORDER BY v.created_at
    """)
    
    print(f"   Found {len(rows)} videos with transcripts")
    
    # Group by transcript similarity
    # Key: first video ID, Value: list of duplicate IDs to delete
    keep_delete_map = defaultdict(list)
    seen_ids = set()
    
    print("🔍 Finding duplicates...")
    total_pairs = len(rows) * (len(rows) - 1) // 2
    checked = 0
    
    for i, row1 in enumerate(rows):
        if str(row1['id']) in seen_ids:
            continue
            
        for j, row2 in enumerate(rows[i+1:], i+1):
            if str(row2['id']) in seen_ids:
                continue
                
            checked += 1
            if checked % 10000 == 0:
                print(f"   ... checked {checked}/{total_pairs} pairs")
            
            # Quick length check
            len1, len2 = len(row1['transcript']), len(row2['transcript'])
            if abs(len1 - len2) / max(len1, len2) > 0.3:
                continue
            
            sim = similarity(row1['transcript'], row2['transcript'])
            
            if sim >= 0.85:
                # Mark row2 as duplicate of row1 (row1 came first, keep it)
                keep_delete_map[str(row1['id'])].append({
                    'id': str(row2['id']),
                    'file_name': row2['file_name'],
                    'source_uri': row2['source_uri'],
                    'similarity': sim
                })
                seen_ids.add(str(row2['id']))
    
    return keep_delete_map

async def delete_duplicates(conn, keep_delete_map: dict, delete_files: bool = False, dry_run: bool = True):
    """Delete duplicate videos from database and optionally filesystem"""
    
    total_to_delete = sum(len(dups) for dups in keep_delete_map.values())
    print(f"\n{'🔍 DRY RUN' if dry_run else '🗑️  DELETING'}: {total_to_delete} duplicate videos")
    print("=" * 60)
    
    deleted_count = 0
    deleted_files = 0
    total_size_freed = 0
    errors = []
    
    for keep_id, duplicates in keep_delete_map.items():
        # Get info about the video we're keeping
        keep_row = await conn.fetchrow(
            "SELECT file_name FROM videos WHERE id = $1",
            keep_id
        )
        keep_name = keep_row['file_name'] if keep_row else 'Unknown'
        
        if len(duplicates) > 0:
            print(f"\n📁 Keeping: {keep_name} (ID: {keep_id[:8]}...)")
            print(f"   Deleting {len(duplicates)} duplicates:")
        
        for dup in duplicates:
            dup_id = dup['id']
            dup_name = dup['file_name']
            dup_path = dup['source_uri']
            sim = dup['similarity']
            
            # Get file size if exists
            file_size = 0
            if dup_path and os.path.exists(dup_path):
                try:
                    file_size = os.path.getsize(dup_path)
                except:
                    pass
            
            size_str = f" ({file_size / 1024 / 1024:.1f} MB)" if file_size else ""
            
            if dry_run:
                print(f"      Would delete: {dup_name}{size_str} ({sim:.0%} similar)")
            else:
                try:
                    # Delete from video_analysis first (foreign key)
                    await conn.execute(
                        "DELETE FROM video_analysis WHERE video_id = $1",
                        dup_id
                    )
                    
                    # Delete from scheduled_posts if referenced
                    await conn.execute(
                        "DELETE FROM scheduled_posts WHERE clip_id = $1 OR content_variant_id = $1",
                        dup_id
                    )
                    
                    # Delete from videos
                    await conn.execute(
                        "DELETE FROM videos WHERE id = $1",
                        dup_id
                    )
                    
                    deleted_count += 1
                    print(f"      ✅ Deleted DB: {dup_name}")
                    
                    # Optionally delete file
                    if delete_files and dup_path and os.path.exists(dup_path):
                        try:
                            os.remove(dup_path)
                            deleted_files += 1
                            total_size_freed += file_size
                            print(f"         ✅ Deleted file{size_str}")
                        except Exception as e:
                            print(f"         ⚠️  Could not delete file: {e}")
                            errors.append(f"File delete error: {dup_path} - {e}")
                            
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    errors.append(f"DB delete error: {dup_id} - {e}")
    
    return {
        'deleted_db': deleted_count,
        'deleted_files': deleted_files,
        'size_freed_bytes': total_size_freed,
        'errors': errors
    }

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete transcript-based duplicates")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default is dry-run)")
    parser.add_argument("--delete-files", action="store_true", help="Also delete files from filesystem")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🗑️  DELETE TRANSCRIPT DUPLICATES")
    print("=" * 60)
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print(f"Delete files: {'Yes' if args.delete_files else 'No (DB only)'}")
    print("=" * 60)
    
    conn = await asyncpg.connect(DB_URL)
    
    try:
        # Find duplicates
        keep_delete_map = await find_duplicates(conn)
        
        total_duplicates = sum(len(dups) for dups in keep_delete_map.values())
        print(f"\n📊 Found {total_duplicates} duplicates across {len(keep_delete_map)} groups")
        
        if total_duplicates == 0:
            print("✅ No duplicates to delete!")
            return
        
        # Confirmation for execute mode
        if args.execute and not args.confirm:
            print("\n⚠️  WARNING: This will permanently delete records!")
            if args.delete_files:
                print("⚠️  WARNING: Files will also be deleted from disk!")
            response = input(f"\nDelete {total_duplicates} duplicate records? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("❌ Cancelled")
                return
        
        # Delete duplicates
        result = await delete_duplicates(
            conn, 
            keep_delete_map, 
            delete_files=args.delete_files,
            dry_run=not args.execute
        )
        
        # Summary
        print("\n" + "=" * 60)
        if args.execute:
            print("✅ DELETION COMPLETE")
            print(f"   DB records deleted: {result['deleted_db']}")
            if args.delete_files:
                print(f"   Files deleted: {result['deleted_files']}")
                print(f"   Space freed: {result['size_freed_bytes'] / 1024 / 1024:.1f} MB")
            if result['errors']:
                print(f"   Errors: {len(result['errors'])}")
        else:
            print("🔍 DRY RUN COMPLETE")
            print(f"   Would delete: {total_duplicates} DB records")
            print("\n💡 To actually delete, run with --execute flag")
            if not args.delete_files:
                print("   Add --delete-files to also delete files from disk")
        print("=" * 60)
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())

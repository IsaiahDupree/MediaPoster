#!/usr/bin/env python3
"""
Find Duplicate Transcripts
==========================
Finds videos with similar/duplicate transcripts.
- If one has captions and one doesn't: keep both
- If duplicates with same caption status: report for deletion
"""

import asyncio
import asyncpg
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime

DB_URL = "postgresql://postgres:postgres@localhost:54322/postgres"

def similarity(a: str, b: str) -> float:
    """Calculate text similarity (0.0 to 1.0)"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def main():
    print("=" * 60)
    print("🔍 FINDING DUPLICATE TRANSCRIPTS")
    print("=" * 60)
    
    conn = await asyncpg.connect(DB_URL)
    
    # Get all videos with transcripts
    print("\n📊 Fetching videos with transcripts...")
    rows = await conn.fetch("""
        SELECT 
            v.id,
            v.file_name,
            v.source_uri,
            va.transcript
        FROM videos v
        JOIN video_analysis va ON va.video_id = v.id
        WHERE va.transcript IS NOT NULL 
          AND va.transcript != ''
          AND LENGTH(va.transcript) > 50
        ORDER BY v.created_at
    """)
    
    print(f"   Found {len(rows)} videos with transcripts")
    
    if len(rows) < 2:
        print("Not enough videos to compare")
        await conn.close()
        return
    
    # Find duplicates
    print("\n🔍 Comparing transcripts (this may take a moment)...")
    
    duplicates = []
    caption_variants = []  # One has captions, one doesn't
    checked = 0
    total_pairs = len(rows) * (len(rows) - 1) // 2
    
    for i, row1 in enumerate(rows):
        for j, row2 in enumerate(rows[i+1:], i+1):
            checked += 1
            if checked % 10000 == 0:
                print(f"   ... checked {checked}/{total_pairs} pairs")
            
            # Quick length check first (optimization)
            len1, len2 = len(row1['transcript']), len(row2['transcript'])
            if abs(len1 - len2) / max(len1, len2) > 0.3:
                continue  # Skip if length differs by >30%
            
            sim = similarity(row1['transcript'], row2['transcript'])
            
            if sim >= 0.85:  # 85% similar
                dup_info = {
                    "similarity": sim,
                    "video1": {
                        "id": str(row1['id']),
                        "file_name": row1['file_name'],
                        "source_uri": row1['source_uri'],
                        "transcript_preview": row1['transcript'][:100] + "..."
                    },
                    "video2": {
                        "id": str(row2['id']),
                        "file_name": row2['file_name'],
                        "source_uri": row2['source_uri'],
                        "transcript_preview": row2['transcript'][:100] + "..."
                    }
                }
                
                # Check if filenames suggest caption variant (e.g., "video.mov" vs "video_captioned.mov")
                fn1 = row1['file_name'].lower()
                fn2 = row2['file_name'].lower()
                is_caption_variant = (
                    ('caption' in fn1 and 'caption' not in fn2) or
                    ('caption' in fn2 and 'caption' not in fn1) or
                    ('text' in fn1 and 'text' not in fn2) or
                    ('text' in fn2 and 'text' not in fn1)
                )
                
                if is_caption_variant:
                    caption_variants.append(dup_info)
                else:
                    duplicates.append(dup_info)
    
    await conn.close()
    
    # Report results
    print("\n" + "=" * 60)
    print("📋 RESULTS")
    print("=" * 60)
    
    print(f"\n✅ CAPTION VARIANTS (KEEP BOTH): {len(caption_variants)}")
    print("   These appear to be caption/non-caption pairs - keeping both")
    for i, dup in enumerate(caption_variants[:10], 1):
        print(f"\n   {i}. Similarity: {dup['similarity']:.1%}")
        print(f"      Video 1: {dup['video1']['file_name']}")
        print(f"      Video 2: {dup['video2']['file_name']}")
    if len(caption_variants) > 10:
        print(f"   ... and {len(caption_variants) - 10} more")
    
    print(f"\n⚠️  DUPLICATES TO DELETE: {len(duplicates)}")
    print("   These are true duplicates (same caption status)")
    
    # Save full report
    report_path = "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/logs/duplicate_transcripts_report.txt"
    with open(report_path, 'w') as f:
        f.write(f"DUPLICATE TRANSCRIPTS REPORT - {datetime.now()}\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"CAPTION VARIANTS (KEEP BOTH): {len(caption_variants)}\n")
        f.write("-" * 40 + "\n")
        for dup in caption_variants:
            f.write(f"\nSimilarity: {dup['similarity']:.1%}\n")
            f.write(f"  {dup['video1']['file_name']}\n")
            f.write(f"  {dup['video2']['file_name']}\n")
        
        f.write(f"\n\nDUPLICATES TO DELETE: {len(duplicates)}\n")
        f.write("-" * 40 + "\n")
        for dup in duplicates:
            f.write(f"\nSimilarity: {dup['similarity']:.1%}\n")
            f.write(f"  KEEP:   {dup['video1']['file_name']} (ID: {dup['video1']['id']})\n")
            f.write(f"  DELETE: {dup['video2']['file_name']} (ID: {dup['video2']['id']})\n")
            f.write(f"  Path:   {dup['video2']['source_uri']}\n")
    
    print(f"\n📄 Full report saved: {report_path}")
    
    if duplicates:
        print("\n🗑️  TO DELETE (recommended):")
        for i, dup in enumerate(duplicates[:20], 1):
            print(f"   {i}. {dup['video2']['file_name']} ({dup['similarity']:.0%} similar)")
        if len(duplicates) > 20:
            print(f"   ... and {len(duplicates) - 20} more")

if __name__ == "__main__":
    asyncio.run(main())

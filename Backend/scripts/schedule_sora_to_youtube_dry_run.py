#!/usr/bin/env python3
"""
Dry Run: Schedule Sora Videos to YouTube
=========================================
This script shows what would be scheduled without making any changes.

Usage:
    python scripts/schedule_sora_to_youtube_dry_run.py [--execute]

Options:
    --execute   Actually create the scheduled posts (default: dry run only)
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

def get_sora_videos():
    """Get all analyzed Sora videos with AI-generated titles."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            v.id,
            v.title,
            v.source_uri,
            va.pre_social_score,
            va.topics,
            va.hooks
        FROM videos v
        JOIN video_analysis va ON v.id = va.video_id
        WHERE v.source_type = 'sora' 
          AND va.pre_social_score IS NOT NULL
        ORDER BY va.pre_social_score DESC, v.created_at
    """)
    
    videos = cur.fetchall()
    cur.close()
    conn.close()
    return videos

def get_youtube_account():
    """Get YouTube account info."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT id, platform, username, display_name
        FROM social_media_accounts
        WHERE platform = 'youtube' AND is_active = true
        LIMIT 1
    """)
    
    account = cur.fetchone()
    cur.close()
    conn.close()
    return account

def schedule_videos(videos, account, interval_minutes=3, execute=False):
    """Schedule videos to YouTube."""
    if not account:
        print("❌ No YouTube account found!")
        return
    
    print(f"\n{'='*60}")
    print(f"{'DRY RUN' if not execute else 'EXECUTING'}: Schedule Sora Videos to YouTube")
    print(f"{'='*60}")
    print(f"YouTube Account: {account['display_name']} (@{account['username']})")
    print(f"Total Videos: {len(videos)}")
    print(f"Interval: {interval_minutes} minutes between posts")
    print(f"Total Duration: {len(videos) * interval_minutes} minutes ({len(videos) * interval_minutes / 60:.1f} hours)")
    print(f"{'='*60}\n")
    
    now = datetime.now(timezone.utc)
    scheduled_posts = []
    
    for i, video in enumerate(videos):
        scheduled_time = now + timedelta(minutes=i * interval_minutes)
        
        # Generate description from topics
        topics = video.get('topics') or []
        if isinstance(topics, str):
            description = topics[:200]
        elif isinstance(topics, list):
            description = ", ".join(topics[:5]) if topics else "AI Generated Video"
        else:
            description = "AI Generated Video"
        
        post = {
            'video_id': str(video['id']),
            'title': video['title'] or f"Sora Video #{i+1}",
            'description': description,
            'scheduled_time': scheduled_time,
            'score': video['pre_social_score'],
            'source': Path(video['source_uri']).name if video['source_uri'] else 'unknown'
        }
        scheduled_posts.append(post)
        
        # Print first 10 and last 3
        if i < 10 or i >= len(videos) - 3:
            local_time = scheduled_time.astimezone()
            print(f"{i+1:3}. [{post['score']:2}] {local_time.strftime('%I:%M %p')} - {post['title'][:40]}")
        elif i == 10:
            print(f"    ... ({len(videos) - 13} more videos) ...")
    
    if execute:
        print(f"\n🚀 Creating {len(scheduled_posts)} scheduled posts...")
        created = create_scheduled_posts(scheduled_posts, account)
        print(f"✅ Created {created} scheduled posts!")
    else:
        print(f"\n📋 DRY RUN COMPLETE")
        print(f"   Would create {len(scheduled_posts)} scheduled posts")
        print(f"   First post at: {scheduled_posts[0]['scheduled_time'].astimezone().strftime('%I:%M %p')}")
        print(f"   Last post at: {scheduled_posts[-1]['scheduled_time'].astimezone().strftime('%I:%M %p')}")
        print(f"\n   Run with --execute to create the posts")
    
    return scheduled_posts

def create_scheduled_posts(posts, account):
    """Actually create the scheduled posts in the database."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    created = 0
    for post in posts:
        try:
            cur.execute("""
                INSERT INTO scheduled_posts (
                    id, clip_id, platform, platform_account_id, account_username,
                    scheduled_time, status, title, caption, hashtags, 
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), %s, 'youtube', %s, %s,
                    %s, 'scheduled', %s, %s, %s,
                    NOW(), NOW()
                )
            """, (
                post['video_id'],
                str(account['id']),
                account['username'],
                post['scheduled_time'],
                post['title'],
                post['description'],
                '["sora", "ai", "aigenerated", "shorts"]'
            ))
            created += 1
        except Exception as e:
            print(f"   ⚠️ Failed to schedule {post['title']}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    return created

def main():
    execute = '--execute' in sys.argv
    
    print("\n🎬 Sora Video YouTube Scheduler")
    print("-" * 40)
    
    # Get data
    print("📂 Fetching Sora videos...")
    videos = get_sora_videos()
    print(f"   Found {len(videos)} analyzed videos")
    
    print("📺 Fetching YouTube account...")
    account = get_youtube_account()
    if account:
        print(f"   Account: {account['display_name']}")
    else:
        print("   ❌ No YouTube account found!")
        return
    
    # Schedule
    schedule_videos(videos, account, interval_minutes=3, execute=execute)

if __name__ == "__main__":
    main()

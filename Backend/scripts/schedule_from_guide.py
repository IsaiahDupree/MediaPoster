#!/usr/bin/env python3
"""
Schedule From Guide — Parse a publishing guide markdown and schedule all videos.
=================================================================================
Reads a structured markdown file containing video titles, descriptions, file paths,
and hashtags, then schedules everything into the PostScheduler DB.

This is the reusable version of the Sora video enrichment workflow.

Guide Format (markdown):
    ### Video Name
    **File:** `~/path/to/video.mp4`
    **YouTube Title** (optional char count): `Full Title Here`
    **Description:**
    ```
    Full description text here...
    
    #Hashtag1 #Hashtag2 #Hashtag3
    ```

Usage:
    # Parse guide and schedule to YouTube
    python schedule_from_guide.py /path/to/publishing-guide.md --platform youtube

    # Cross-post to all platforms
    python schedule_from_guide.py /path/to/guide.md --platform youtube,tiktok,instagram

    # Dry run to preview
    python schedule_from_guide.py /path/to/guide.md --dry-run

    # Schedule with custom start time
    python schedule_from_guide.py /path/to/guide.md --start "2026-03-01 10:00"

    # Export parsed metadata to JSON for use with schedule_videos.py
    python schedule_from_guide.py /path/to/guide.md --export-metadata metadata.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

DEFAULT_ACCOUNTS = {
    "youtube": {"id": "228", "username": "Isaiah Dupree"},
    "tiktok": {"id": "710", "username": "isaiah_dupree"},
    "instagram": {"id": "807", "username": "the_isaiah_dupree"},
}

OPTIMAL_HOURS_UTC = {
    "youtube": [15, 19, 23],
    "tiktok": [14, 17, 21],
    "instagram": [15, 18, 23],
}


def parse_guide(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse a publishing guide markdown into structured video entries.
    
    Supports multiple markdown formats:
    - ### Title with **File:** and **Description:** blocks
    - Numbered lists with file paths and descriptions
    - YAML frontmatter style
    """
    with open(filepath) as f:
        content = f.read()
    
    entries = []
    
    # Split by --- separators or ### headers
    sections = re.split(r'\n---\n|\n(?=###\s)', content)
    
    for section in sections:
        entry = {}
        
        # Extract title (multiple patterns)
        title_match = (
            re.search(r'\*\*(?:YouTube )?Title\*\*[^:]*:\s*`([^`]+)`', section)
            or re.search(r'###\s+(?:Trilogy \d+\s*[—-]\s*)?(.+?)(?:\n|$)', section)
        )
        if not title_match:
            continue
        entry["title"] = title_match.group(1).strip()
        
        # Extract file path
        file_match = re.search(r'\*\*File:?\*\*\s*`([^`]+)`', section)
        if file_match:
            raw_path = file_match.group(1)
            # Expand ~ to home directory
            entry["file"] = str(Path(raw_path).expanduser())
        
        # Extract description (content between ``` markers)
        desc_match = re.search(r'\*\*Description:?\*\*\s*```\n?(.*?)```', section, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()
            
            # Split description into text and hashtags
            lines = description.split('\n')
            hashtag_line = lines[-1] if lines[-1].strip().startswith('#') else ''
            
            if hashtag_line:
                desc_text = '\n'.join(lines[:-1]).strip()
                hashtags = [h.strip() for h in hashtag_line.split() if h.startswith('#')]
            else:
                desc_text = description
                hashtags = []
            
            entry["description"] = desc_text
            entry["hashtags"] = hashtags
            entry["full_caption"] = description
        
        # Extract parts/chapters if present
        parts_match = re.search(r'\*\*Parts?:?\*\*\s*(.+?)(?:\n|$)', section)
        if parts_match:
            entry["parts"] = parts_match.group(1).strip()
        
        # Extract type if present
        type_match = re.search(r'\*\*Type:?\*\*\s*(.+?)(?:\n|$)', section)
        if type_match:
            entry["type"] = type_match.group(1).strip()
        
        if entry.get("title"):
            entries.append(entry)
    
    return entries


def resolve_file_path(path_str: str) -> Optional[str]:
    """Resolve a file path, handling ~, glob patterns, and partial paths."""
    p = Path(path_str).expanduser()
    
    if p.exists():
        return str(p)
    
    # Try glob if there's a wildcard
    if '*' in str(p):
        parent = p.parent
        if parent.exists():
            matches = sorted(parent.glob(p.name))
            if matches:
                return str(matches[0])
    
    # If path is relative or just a filename, try common base dirs
    if not p.is_absolute():
        home = Path.home()
        search_dirs = [
            home / "sora-videos",
            home / "sora-videos" / "valentines-22-tips" / "cleaned",
            home / "sora-videos" / "valentines-love",
            home / "Videos",
            Path.cwd(),
        ]
        for base in search_dirs:
            candidate = base / p.name if p.name != str(p) else base / p
            if candidate.exists():
                return str(candidate)
            # Try glob in directory
            if '*' in p.name and base.exists():
                matches = sorted(base.glob(p.name))
                if matches:
                    return str(matches[0])
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Schedule From Guide — Parse publishing guide and schedule videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("guide", help="Path to publishing guide markdown file")
    parser.add_argument("--platform", "-p", default="youtube",
                        help="Platform(s), comma-separated (default: youtube)")
    parser.add_argument("--account", "-a", default=None,
                        help="Account ref(s) (default: platform defaults)")
    parser.add_argument("--start", "-s", default=None,
                        help="Start time (default: tomorrow 10am EST)")
    parser.add_argument("--posts-per-day", type=int, default=2,
                        help="Posts per day per platform (default: 2)")
    parser.add_argument("--cross-post-delay", type=float, default=2,
                        help="Hours delay for cross-posts (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to DB")
    parser.add_argument("--export-metadata", default=None,
                        help="Export parsed metadata to JSON file")
    parser.add_argument("--thumbnails", action="store_true",
                        help="Generate thumbnails from videos")
    parser.add_argument("--caption-limit", type=int, default=4990,
                        help="Max caption length (default: 4990)")
    
    args = parser.parse_args()
    
    # Parse the guide
    guide_path = Path(args.guide).expanduser()
    if not guide_path.exists():
        print(f"❌ Guide file not found: {args.guide}")
        sys.exit(1)
    
    entries = parse_guide(str(guide_path))
    if not entries:
        print(f"❌ No video entries found in guide.")
        sys.exit(1)
    
    print(f"📄 Parsed {len(entries)} entries from: {guide_path.name}")
    
    # Resolve file paths
    resolved = 0
    missing = 0
    for entry in entries:
        if "file" in entry:
            path = resolve_file_path(entry["file"])
            if path:
                entry["resolved_path"] = path
                resolved += 1
            else:
                missing += 1
                print(f"  ⚠️  File not found: {entry['file']}")
    
    print(f"  Files: {resolved} found, {missing} missing")
    
    # Export metadata if requested
    if args.export_metadata:
        export = {"videos": {}}
        for entry in entries:
            key = Path(entry.get("file", "")).name or entry["title"]
            export["videos"][key] = {
                "title": entry.get("title", ""),
                "caption": entry.get("full_caption", entry.get("description", "")),
                "hashtags": entry.get("hashtags", []),
                "file": entry.get("resolved_path", entry.get("file", "")),
            }
        with open(args.export_metadata, "w") as f:
            json.dump(export, f, indent=2)
        print(f"📋 Exported metadata to: {args.export_metadata}")
        if not args.platform:
            return
    
    # Resolve platforms and accounts
    platforms = [p.strip().lower() for p in args.platform.split(",")]
    
    platform_accounts = []
    if args.account:
        account_refs = [a.strip() for a in args.account.split(",")]
        if len(account_refs) == 1:
            account_refs = account_refs * len(platforms)
        for platform, ref in zip(platforms, account_refs):
            default = DEFAULT_ACCOUNTS.get(platform, {"id": ref, "username": ref})
            platform_accounts.append((platform, ref, default.get("username", ref)))
    else:
        for platform in platforms:
            default = DEFAULT_ACCOUNTS.get(platform, {})
            if default:
                platform_accounts.append((platform, default["id"], default["username"]))
            else:
                print(f"  ❌ No default account for {platform}. Use --account.")
                sys.exit(1)
    
    for platform, bid, username in platform_accounts:
        print(f"  ✅ {platform}: @{username} (ID: {bid})")
    
    # Parse start time
    if args.start:
        try:
            start_time = datetime.fromisoformat(args.start)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone(timedelta(hours=-5)))
        except ValueError:
            print(f"❌ Invalid start time: {args.start}")
            sys.exit(1)
    else:
        tomorrow = datetime.now(timezone.utc).replace(
            hour=15, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        start_time = tomorrow
    
    # Generate thumbnails
    thumb_dir = BACKEND_DIR / "static" / "thumbnails"
    if args.thumbnails:
        thumb_dir.mkdir(parents=True, exist_ok=True)
    
    # Build schedule
    publishable = [e for e in entries if e.get("resolved_path")]
    
    db_posts = []
    for video_idx, entry in enumerate(publishable):
        day = video_idx // args.posts_per_day
        slot = video_idx % args.posts_per_day
        
        for plat_idx, (platform, blotato_id, username) in enumerate(platform_accounts):
            # Calculate time using optimal hours
            base_date = start_time + timedelta(days=day)
            
            if platform in OPTIMAL_HOURS_UTC:
                hours = OPTIMAL_HOURS_UTC[platform]
                hour = hours[slot % len(hours)]
                post_time = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            else:
                post_time = base_date + timedelta(hours=8 * slot)
            
            # Cross-post delay
            if plat_idx > 0:
                post_time += timedelta(hours=args.cross_post_delay * plat_idx)
            
            # Adapt caption for platform
            caption = entry.get("full_caption", entry.get("description", ""))
            if platform == "tiktok":
                caption = caption[:2200]
            elif platform == "instagram":
                caption = caption[:2200]
            else:
                caption = caption[:args.caption_limit]
            
            # Adapt title
            title = entry.get("title", "")
            if platform != "youtube" and "#shorts" in title.lower():
                title = re.sub(r'\s*#shorts\s*', '', title, flags=re.IGNORECASE).strip()
            
            # Thumbnail
            thumbnail_url = None
            if args.thumbnails:
                video_path = Path(entry["resolved_path"])
                thumb_name = f"{video_path.stem}.jpg"
                thumb_path = thumb_dir / thumb_name
                if not thumb_path.exists():
                    try:
                        subprocess.run([
                            'ffmpeg', '-i', str(video_path), '-ss', '00:00:01',
                            '-vframes', '1', '-vf', 'scale=360:-1', '-q:v', '3',
                            str(thumb_path), '-y'
                        ], capture_output=True, timeout=10)
                    except Exception:
                        pass
                if thumb_path.exists():
                    thumbnail_url = f"/static/thumbnails/{thumb_name}"
            
            post_type = "short" if platform == "youtube" else "reel"
            
            db_posts.append({
                "id": str(uuid4()),
                "platform": platform,
                "title": title,
                "caption": caption,
                "hashtags": entry.get("hashtags") or None,
                "media_path": entry["resolved_path"],
                "scheduled_time": post_time,
                "blotato_id": blotato_id,
                "username": username,
                "thumbnail_url": thumbnail_url,
                "post_type": post_type,
            })
    
    # Display schedule
    print(f"\n{'=' * 70}")
    print(f"📅 SCHEDULE: {len(db_posts)} posts from {len(publishable)} videos × {len(platforms)} platform(s)")
    print(f"{'=' * 70}")
    
    current_date = None
    for post in db_posts:
        date_str = str(post["scheduled_time"])[:10]
        if date_str != current_date:
            current_date = date_str
            day_count = sum(1 for p in db_posts if str(p["scheduled_time"])[:10] == date_str)
            print(f"\n  📆 {date_str} ({day_count} posts):")
        
        time_str = str(post["scheduled_time"])[11:16]
        cap_len = len(post["caption"]) if post["caption"] else 0
        tag_count = len(post["hashtags"]) if post["hashtags"] else 0
        print(f"    {time_str} UTC | {post['platform']:10s} | {post['title'][:42]:42s} | {cap_len}c {tag_count}t")
    
    # Summary
    dates = sorted(set(str(p["scheduled_time"])[:10] for p in db_posts))
    print(f"\n  Range: {dates[0]} → {dates[-1]} ({len(dates)} days)")
    
    if args.dry_run:
        print(f"\n🔍 DRY RUN — No changes made.")
        return
    
    # Insert into DB
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_URL)
    
    inserted = 0
    with engine.begin() as conn:
        for post in db_posts:
            try:
                conn.execute(text("""
                    INSERT INTO scheduled_posts 
                    (id, platform, title, caption, hashtags, media_path,
                     scheduled_time, status, blotato_account_id, account_username,
                     thumbnail_url, post_type, source, created_at, updated_at)
                    VALUES 
                    (:id, :platform, :title, :caption, :hashtags, :media_path,
                     :scheduled_time, 'scheduled', :blotato_id, :username,
                     :thumbnail_url, :post_type, 'guide', NOW(), NOW())
                """), post)
                inserted += 1
            except Exception as e:
                print(f"  ❌ {post['title'][:30]}: {e}")
    
    print(f"\n✅ Inserted {inserted}/{len(db_posts)} posts into scheduled_posts")
    print(f"   PostScheduler will auto-publish when posts become due.")


if __name__ == "__main__":
    main()

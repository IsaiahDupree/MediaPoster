#!/usr/bin/env python3
"""
Schedule Videos — Standalone CLI for scheduling new videos into the PostScheduler DB.
=====================================================================================
Scans a folder (or single file) for videos, generates metadata, and inserts them
into the scheduled_posts table. The PostScheduler background worker then handles
the actual publishing to Blotato → YouTube/TikTok/Instagram/etc.

This script works INDEPENDENTLY of the backend server. It connects directly to
the Supabase PostgreSQL database and doesn't require the API to be running.

Usage:
    # Schedule a folder of videos to YouTube, 2 posts/day starting tomorrow 10am
    python schedule_videos.py /path/to/videos --platform youtube --account 228 \\
        --start "2026-02-15 10:00" --posts-per-day 2

    # Cross-post to YouTube + TikTok + Instagram
    python schedule_videos.py /path/to/videos --platform youtube,tiktok,instagram \\
        --account 228,710,807 --start "2026-02-15 10:00" --cross-post-delay 2

    # Schedule with a metadata file (titles, descriptions, hashtags per video)
    python schedule_videos.py /path/to/videos --metadata /path/to/metadata.json \\
        --platform youtube --account 228

    # Use filenames as titles + auto-generate hashtags
    python schedule_videos.py /path/to/videos --platform youtube --account 228 \\
        --titles-from-filenames --auto-hashtags

    # Dry run to preview
    python schedule_videos.py /path/to/videos --platform youtube --account 228 --dry-run

    # Schedule a single video
    python schedule_videos.py /path/to/video.mp4 --platform youtube --account 228 \\
        --title "My Video Title" --caption "Description here" --start "2026-02-15 15:00"

    # Generate thumbnails during scheduling
    python schedule_videos.py /path/to/videos --platform youtube --account 228 --thumbnails
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from uuid import uuid4

# Add Backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Database connection (works without backend running)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

# Default account mappings
DEFAULT_ACCOUNTS = {
    "youtube": {"id": "228", "username": "Isaiah Dupree"},
    "tiktok": {"id": "710", "username": "isaiah_dupree"},
    "instagram": {"id": "807", "username": "the_isaiah_dupree"},
    "threads": {"id": "173", "username": "the_isaiah_dupree_"},
    "twitter": {"id": "4151", "username": "IsaiahDupree7"},
    "pinterest": {"id": "173", "username": "isaiahdupree33"},
    "linkedin": {"id": "571", "username": "IsaiahDupree7"},
    "facebook": {"id": "786", "username": "Isaiah Dupree"},
    "bluesky": {"id": "201", "username": "isaiahdupree.bsky.social"},
}

# Optimal posting hours (UTC) by platform
OPTIMAL_HOURS_UTC = {
    "youtube": [15, 19, 23],       # 10am, 2pm, 6pm EST
    "tiktok": [14, 17, 21, 0],     # 9am, 12pm, 4pm, 7pm EST
    "instagram": [15, 18, 23],     # 10am, 1pm, 6pm EST
    "threads": [16, 20],
    "twitter": [14, 17, 21],
    "pinterest": [18, 22],
    "linkedin": [13, 17],
    "facebook": [15, 19],
    "bluesky": [15, 19],
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


# =============================================================================
# VIDEO DISCOVERY
# =============================================================================

def discover_videos(source: str) -> List[Path]:
    """Find video files in a path (file or directory)."""
    p = Path(source).expanduser().resolve()
    
    if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
        return [p]
    
    if p.is_dir():
        videos = []
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(f)
        return videos
    
    # Try glob pattern
    parent = p.parent
    if parent.exists():
        videos = sorted(parent.glob(p.name))
        return [f for f in videos if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]
    
    return []


# =============================================================================
# METADATA GENERATION
# =============================================================================

def title_from_filename(filename: str) -> str:
    """Generate a clean title from a filename."""
    name = Path(filename).stem
    # Remove common prefixes/suffixes
    name = re.sub(r'^(cleaned_|final_|v\d+_)', '', name, flags=re.IGNORECASE)
    # Replace separators with spaces
    name = re.sub(r'[-_]+', ' ', name)
    # Title case
    name = name.strip().title()
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name)
    return name[:100]


def generate_hashtags_from_title(title: str, platform: str = "youtube") -> List[str]:
    """Generate relevant hashtags from a video title."""
    # Extract meaningful words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', title)
    tags = []
    for w in words[:8]:
        tag = f"#{w.replace(' ', '')}"
        if tag.lower() not in [t.lower() for t in tags]:
            tags.append(tag)
    
    # Platform-specific defaults
    if platform == "youtube":
        tags.extend(["#Shorts", "#YouTubeShorts"])
    elif platform == "tiktok":
        tags.extend(["#fyp", "#viral"])
    elif platform == "instagram":
        tags.extend(["#Reels", "#InstagramReels"])
    
    return tags[:15]


def load_metadata_file(path: str) -> Dict[str, Any]:
    """
    Load a metadata JSON or YAML file.
    
    Expected format:
    {
        "defaults": {
            "caption": "Default caption for all videos",
            "hashtags": ["tag1", "tag2"],
        },
        "videos": {
            "filename.mp4": {
                "title": "Video Title",
                "caption": "Full description...",
                "hashtags": ["specific", "tags"]
            }
        }
    }
    
    Or a simple list format:
    [
        {
            "file": "filename.mp4",
            "title": "Video Title",
            "caption": "Description",
            "hashtags": ["tag1", "tag2"]
        }
    ]
    """
    p = Path(path)
    if not p.exists():
        print(f"❌ Metadata file not found: {path}")
        return {}
    
    with open(p) as f:
        if p.suffix in ('.yaml', '.yml'):
            try:
                import yaml
                data = yaml.safe_load(f)
            except ImportError:
                print("❌ PyYAML not installed. Use JSON format or: pip install pyyaml")
                return {}
        else:
            data = json.load(f)
    
    # Normalize list format to dict format
    if isinstance(data, list):
        videos = {}
        for item in data:
            filename = item.get("file") or item.get("filename", "")
            videos[filename] = item
        return {"videos": videos}
    
    return data


def get_video_metadata(
    video: Path,
    metadata: Dict[str, Any],
    title_from_file: bool = False,
    auto_hashtags: bool = False,
    default_caption: str = "",
    default_title: str = "",
    default_hashtags: List[str] = None,
    platform: str = "youtube",
) -> Dict[str, str]:
    """Get title, caption, and hashtags for a video."""
    defaults = metadata.get("defaults", {})
    videos = metadata.get("videos", {})
    
    # Look up by filename (exact match or stem match)
    video_meta = videos.get(video.name, {})
    if not video_meta:
        video_meta = videos.get(video.stem, {})
    
    # Title
    title = (
        video_meta.get("title")
        or default_title
        or defaults.get("title", "")
    )
    if not title and title_from_file:
        title = title_from_filename(video.name)
    
    # Caption / description
    caption = (
        video_meta.get("caption")
        or video_meta.get("description")
        or default_caption
        or defaults.get("caption", "")
        or defaults.get("description", "")
    )
    
    # Hashtags
    hashtags = (
        video_meta.get("hashtags")
        or default_hashtags
        or defaults.get("hashtags", [])
    )
    if not hashtags and auto_hashtags and title:
        hashtags = generate_hashtags_from_title(title, platform)
    
    return {
        "title": title,
        "caption": caption,
        "hashtags": hashtags or [],
    }


# =============================================================================
# THUMBNAIL GENERATION
# =============================================================================

def generate_thumbnail(video_path: Path, output_dir: Path) -> Optional[str]:
    """Generate a thumbnail from a video using ffmpeg."""
    thumb_name = f"{video_path.stem}.jpg"
    thumb_path = output_dir / thumb_name
    
    if thumb_path.exists():
        return f"/static/thumbnails/{thumb_name}"
    
    try:
        subprocess.run([
            'ffmpeg', '-i', str(video_path), '-ss', '00:00:01', '-vframes', '1',
            '-vf', 'scale=360:-1', '-q:v', '3', str(thumb_path), '-y'
        ], capture_output=True, timeout=10)
        
        if thumb_path.exists():
            return f"/static/thumbnails/{thumb_name}"
    except Exception as e:
        print(f"  ⚠️  Thumbnail failed for {video_path.name}: {e}")
    
    return None


# =============================================================================
# SCHEDULE PLANNING
# =============================================================================

def plan_schedule(
    video_count: int,
    platforms: List[str],
    start_time: datetime,
    posts_per_day: int = 2,
    spacing_hours: float = 8,
    cross_post_delay_hours: float = 2,
    optimal_hours: bool = True,
) -> List[Dict[str, Any]]:
    """
    Plan a schedule for videos across platforms.
    
    Returns list of {platform, video_index, scheduled_time} dicts.
    """
    schedule = []
    
    for video_idx in range(video_count):
        # Calculate day and slot
        day = video_idx // posts_per_day
        slot = video_idx % posts_per_day
        
        # Base time for this video
        base_date = start_time + timedelta(days=day)
        
        for plat_idx, platform in enumerate(platforms):
            if optimal_hours and platform in OPTIMAL_HOURS_UTC:
                hours = OPTIMAL_HOURS_UTC[platform]
                hour = hours[slot % len(hours)]
                post_time = base_date.replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
                # Add cross-post delay for non-primary platforms
                if plat_idx > 0:
                    post_time += timedelta(hours=cross_post_delay_hours * plat_idx)
            else:
                # Simple spacing
                post_time = base_date + timedelta(
                    hours=spacing_hours * slot + cross_post_delay_hours * plat_idx
                )
            
            schedule.append({
                "platform": platform,
                "video_index": video_idx,
                "scheduled_time": post_time,
            })
    
    return sorted(schedule, key=lambda x: x["scheduled_time"])


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def get_engine():
    """Get SQLAlchemy engine (works without backend running)."""
    from sqlalchemy import create_engine
    return create_engine(DATABASE_URL)


def get_existing_schedule(engine, platform: str = None) -> List[Dict]:
    """Get current scheduled posts from DB."""
    from sqlalchemy import text
    
    where = "WHERE status = 'scheduled'"
    params = {}
    if platform:
        where += " AND platform = :platform"
        params["platform"] = platform
    
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT id, title, platform, scheduled_time, media_path, 
                   blotato_account_id, account_username, status
            FROM scheduled_posts
            {where}
            ORDER BY scheduled_time ASC
        """), params)
        
        return [
            {
                "id": str(r[0]), "title": r[1], "platform": r[2],
                "scheduled_time": r[3], "media_path": r[4],
                "blotato_account_id": r[5], "account_username": r[6],
                "status": r[7],
            }
            for r in result.fetchall()
        ]


def insert_scheduled_posts(engine, posts: List[Dict], dry_run: bool = False) -> int:
    """Insert posts into scheduled_posts table. Returns count inserted."""
    from sqlalchemy import text
    
    if dry_run:
        return len(posts)
    
    inserted = 0
    with engine.begin() as conn:
        for post in posts:
            try:
                conn.execute(text("""
                    INSERT INTO scheduled_posts 
                    (id, platform, title, caption, hashtags, media_path,
                     scheduled_time, status, blotato_account_id, account_username,
                     thumbnail_url, post_type, source, created_at, updated_at)
                    VALUES 
                    (:id, :platform, :title, :caption, :hashtags, :media_path,
                     :scheduled_time, 'scheduled', :blotato_id, :username,
                     :thumbnail_url, :post_type, 'cli', NOW(), NOW())
                """), post)
                inserted += 1
            except Exception as e:
                print(f"  ❌ Failed to insert {post.get('title', '?')}: {e}")
    
    return inserted


# =============================================================================
# MAIN CLI
# =============================================================================

def resolve_account(platform: str, account_ref: str) -> Tuple[str, str]:
    """Resolve account ref to (blotato_id, username)."""
    # Try numeric ID
    try:
        int(account_ref)
        # Look up in known accounts
        try:
            from config.blotato_accounts import BLOTATO_ACCOUNTS
            for acc in BLOTATO_ACCOUNTS:
                if str(acc.blotato_id) == account_ref:
                    return account_ref, acc.username
        except ImportError:
            pass
        # Return as-is with platform default username
        default = DEFAULT_ACCOUNTS.get(platform, {})
        return account_ref, default.get("username", "unknown")
    except ValueError:
        pass
    
    # Try username lookup
    account_ref = account_ref.lstrip("@")
    try:
        from config.blotato_accounts import get_blotato_id, get_blotato_account
        blotato_id = get_blotato_id(platform, account_ref)
        if blotato_id:
            acc = get_blotato_account(platform, account_ref)
            return str(blotato_id), acc.username if acc else account_ref
    except ImportError:
        pass
    
    # Use default for platform
    if platform in DEFAULT_ACCOUNTS:
        default = DEFAULT_ACCOUNTS[platform]
        return default["id"], default["username"]
    
    raise ValueError(f"Cannot resolve account '{account_ref}' for {platform}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Schedule Videos — Insert new videos into PostScheduler DB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Schedule folder to YouTube
  %(prog)s ~/sora-videos/new-batch --platform youtube --account 228

  # Cross-post to 3 platforms
  %(prog)s ~/videos --platform youtube,tiktok,instagram --account 228,710,807

  # With metadata file
  %(prog)s ~/videos --metadata ~/videos/metadata.json --platform youtube

  # Use filenames as titles
  %(prog)s ~/videos --platform youtube --titles-from-filenames --auto-hashtags

  # Preview only
  %(prog)s ~/videos --platform youtube --dry-run

  # Single video with custom metadata
  %(prog)s ~/video.mp4 --platform youtube --title "My Title" --caption "Description"

  # Show current schedule
  %(prog)s --show-schedule

  # Show available accounts
  %(prog)s --show-accounts
        """,
    )
    
    # Source (positional, optional if using --show-*)
    parser.add_argument("source", nargs="?", default=None,
                        help="Video file or directory path")
    
    # Platform & Account
    parser.add_argument("--platform", "-p", default="youtube",
                        help="Platform(s), comma-separated (default: youtube)")
    parser.add_argument("--account", "-a", default=None,
                        help="Account ref(s), comma-separated (ID, username, or @username)")
    
    # Scheduling
    parser.add_argument("--start", "-s", default=None,
                        help="Start time: 'YYYY-MM-DD HH:MM' or ISO 8601 (default: tomorrow 10am EST)")
    parser.add_argument("--posts-per-day", type=int, default=2,
                        help="Max posts per day per platform (default: 2)")
    parser.add_argument("--spacing", type=float, default=8,
                        help="Hours between posts on same platform (default: 8)")
    parser.add_argument("--cross-post-delay", type=float, default=2,
                        help="Hours delay for cross-platform posts (default: 2)")
    parser.add_argument("--no-optimal-hours", action="store_true",
                        help="Don't use platform-optimal posting hours")
    
    # Content
    parser.add_argument("--metadata", "-m", default=None,
                        help="JSON/YAML metadata file with titles, descriptions, hashtags")
    parser.add_argument("--title", default="",
                        help="Title for all videos (or single video)")
    parser.add_argument("--caption", default="",
                        help="Caption/description for all videos")
    parser.add_argument("--hashtags", default="",
                        help="Comma-separated hashtags for all videos")
    parser.add_argument("--titles-from-filenames", action="store_true",
                        help="Generate titles from filenames")
    parser.add_argument("--auto-hashtags", action="store_true",
                        help="Auto-generate hashtags from titles")
    
    # Features
    parser.add_argument("--thumbnails", action="store_true",
                        help="Generate thumbnails from videos")
    parser.add_argument("--ai-generated", action="store_true",
                        help="Mark content as AI-generated")
    
    # Output
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview schedule without inserting into DB")
    parser.add_argument("--output", "-o", default=None,
                        help="Save schedule plan to JSON file")
    parser.add_argument("--show-schedule", action="store_true",
                        help="Show current scheduled posts and exit")
    parser.add_argument("--show-accounts", action="store_true",
                        help="Show available Blotato accounts and exit")
    
    return parser.parse_args()


def show_current_schedule():
    """Display the current schedule from the database."""
    engine = get_engine()
    posts = get_existing_schedule(engine)
    
    if not posts:
        print("📭 No scheduled posts found.")
        return
    
    print(f"\n📅 Current Schedule ({len(posts)} posts):")
    print("=" * 80)
    
    # Group by date
    by_date = {}
    for p in posts:
        date = str(p["scheduled_time"])[:10]
        by_date.setdefault(date, []).append(p)
    
    for date in sorted(by_date.keys()):
        items = by_date[date]
        print(f"\n  {date} ({len(items)} posts):")
        for p in items:
            time = str(p["scheduled_time"])[11:16]
            print(f"    {time} UTC | {p['platform']:10s} | {(p['title'] or 'Untitled')[:45]}")
    
    # Platform summary
    print(f"\n{'=' * 80}")
    by_plat = {}
    for p in posts:
        by_plat[p["platform"]] = by_plat.get(p["platform"], 0) + 1
    for plat, count in sorted(by_plat.items()):
        print(f"  {plat:12s} {count} posts")
    
    dates = sorted(by_date.keys())
    print(f"  Date range:  {dates[0]} → {dates[-1]}")


def show_accounts():
    """Display available Blotato accounts."""
    print("\n📋 Available Accounts:")
    print("=" * 60)
    
    # Try to load from config
    try:
        from config.blotato_accounts import BLOTATO_ACCOUNTS
        platforms = {}
        for acc in BLOTATO_ACCOUNTS:
            platforms.setdefault(acc.platform, []).append(acc)
        
        for platform in sorted(platforms.keys()):
            accs = platforms[platform]
            print(f"\n  {platform.upper()}:")
            for acc in accs:
                print(f"    ID {acc.blotato_id:>5} | @{acc.username:<25} | {acc.display_name or ''}")
    except ImportError:
        print("\n  Default accounts (from config):")
        for plat, info in sorted(DEFAULT_ACCOUNTS.items()):
            print(f"    {plat:12s} ID {info['id']:>5} | @{info['username']}")


def main():
    args = parse_args()
    
    if args.show_schedule:
        show_current_schedule()
        return
    
    if args.show_accounts:
        show_accounts()
        return
    
    if not args.source:
        print("❌ No video source specified. Use --help for usage.")
        sys.exit(1)
    
    # Discover videos
    videos = discover_videos(args.source)
    if not videos:
        print(f"❌ No video files found in: {args.source}")
        sys.exit(1)
    
    print(f"📦 Found {len(videos)} video(s)")
    for v in videos[:5]:
        size_mb = v.stat().st_size / (1024 * 1024)
        print(f"  {v.name} ({size_mb:.1f} MB)")
    if len(videos) > 5:
        print(f"  ... and {len(videos) - 5} more")
    
    # Resolve platforms and accounts
    platforms = [p.strip().lower() for p in args.platform.split(",")]
    
    if args.account:
        account_refs = [a.strip() for a in args.account.split(",")]
    else:
        account_refs = [DEFAULT_ACCOUNTS.get(p, {}).get("id", "") for p in platforms]
    
    # Match platforms to accounts
    if len(account_refs) == 1 and len(platforms) > 1:
        account_refs = account_refs * len(platforms)
    
    if len(account_refs) != len(platforms):
        print(f"❌ {len(platforms)} platforms but {len(account_refs)} accounts. Must match or provide 1.")
        sys.exit(1)
    
    platform_accounts = []
    for platform, ref in zip(platforms, account_refs):
        try:
            blotato_id, username = resolve_account(platform, ref)
            platform_accounts.append((platform, blotato_id, username))
            print(f"  ✅ {platform}: @{username} (Blotato ID: {blotato_id})")
        except ValueError as e:
            print(f"  ❌ {e}")
            sys.exit(1)
    
    # Load metadata
    metadata = {}
    if args.metadata:
        metadata = load_metadata_file(args.metadata)
        video_count = len(metadata.get("videos", {}))
        print(f"📄 Loaded metadata for {video_count} videos")
    
    default_hashtags = [h.strip() for h in args.hashtags.split(",") if h.strip()] if args.hashtags else None
    
    # Parse start time
    if args.start:
        try:
            start_time = datetime.fromisoformat(args.start)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone(timedelta(hours=-5)))  # EST
        except ValueError:
            print(f"❌ Invalid start time: {args.start}")
            sys.exit(1)
    else:
        # Default: tomorrow at 10am EST (15:00 UTC)
        tomorrow = datetime.now(timezone.utc).replace(
            hour=15, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        start_time = tomorrow
    
    print(f"⏰ Start: {start_time.strftime('%Y-%m-%d %H:%M %Z')}")
    
    # Plan the schedule
    schedule_plan = plan_schedule(
        video_count=len(videos),
        platforms=platforms,
        start_time=start_time,
        posts_per_day=args.posts_per_day,
        spacing_hours=args.spacing,
        cross_post_delay_hours=args.cross_post_delay,
        optimal_hours=not args.no_optimal_hours,
    )
    
    # Generate thumbnails
    thumb_dir = BACKEND_DIR / "static" / "thumbnails"
    if args.thumbnails:
        thumb_dir.mkdir(parents=True, exist_ok=True)
        print(f"🖼  Generating thumbnails...")
    
    # Build DB records
    db_posts = []
    for entry in schedule_plan:
        video = videos[entry["video_index"]]
        platform = entry["platform"]
        
        # Find account for this platform
        blotato_id, username = None, None
        for p, bid, uname in platform_accounts:
            if p == platform:
                blotato_id, username = bid, uname
                break
        
        if not blotato_id:
            continue
        
        # Get metadata for this video
        meta = get_video_metadata(
            video, metadata,
            title_from_file=args.titles_from_filenames,
            auto_hashtags=args.auto_hashtags,
            default_caption=args.caption,
            default_title=args.title,
            default_hashtags=default_hashtags,
            platform=platform,
        )
        
        # Thumbnail
        thumbnail_url = None
        if args.thumbnails:
            thumbnail_url = generate_thumbnail(video, thumb_dir)
        
        # Post type
        post_type = "short" if platform == "youtube" else "reel"
        
        # Adapt title for platform (remove #shorts for non-YouTube)
        title = meta["title"]
        if platform != "youtube" and "#shorts" in title.lower():
            title = re.sub(r'\s*#shorts\s*', '', title, flags=re.IGNORECASE).strip()
        
        db_posts.append({
            "id": str(uuid4()),
            "platform": platform,
            "title": title,
            "caption": meta["caption"][:4990] if meta["caption"] else "",
            "hashtags": meta["hashtags"] or None,
            "media_path": str(video),
            "scheduled_time": entry["scheduled_time"],
            "blotato_id": blotato_id,
            "username": username,
            "thumbnail_url": thumbnail_url,
            "post_type": post_type,
        })
    
    # Display schedule
    print(f"\n{'=' * 70}")
    print(f"📅 SCHEDULE PLAN — {len(db_posts)} posts across {len(platforms)} platform(s)")
    print(f"{'=' * 70}")
    
    current_date = None
    for post in db_posts:
        date_str = str(post["scheduled_time"])[:10]
        if date_str != current_date:
            current_date = date_str
            day_posts = [p for p in db_posts if str(p["scheduled_time"])[:10] == date_str]
            print(f"\n  📆 {date_str} ({len(day_posts)} posts):")
        
        time_str = str(post["scheduled_time"])[11:16]
        title = post["title"][:42] if post["title"] else Path(post["media_path"]).stem[:42]
        caption_len = len(post["caption"]) if post["caption"] else 0
        tags = len(post["hashtags"]) if post["hashtags"] else 0
        
        print(f"    {time_str} UTC | {post['platform']:10s} | {title:42s} | {caption_len}c {tags}t")
    
    # Summary
    print(f"\n{'=' * 70}")
    by_plat = {}
    for p in db_posts:
        by_plat[p["platform"]] = by_plat.get(p["platform"], 0) + 1
    for plat, count in sorted(by_plat.items()):
        print(f"  {plat:12s} {count} posts")
    
    dates = sorted(set(str(p["scheduled_time"])[:10] for p in db_posts))
    print(f"  Date range:  {dates[0]} → {dates[-1]}")
    print(f"  Videos:      {len(videos)}")
    print(f"  Total posts: {len(db_posts)}")
    
    if args.dry_run:
        print(f"\n🔍 DRY RUN — No changes made to database.")
    else:
        # Insert into DB
        print(f"\n💾 Writing to database...")
        engine = get_engine()
        inserted = insert_scheduled_posts(engine, db_posts)
        print(f"✅ Inserted {inserted}/{len(db_posts)} posts into scheduled_posts")
        print(f"   PostScheduler will auto-publish when posts become due.")
    
    # Save plan to file
    if args.output:
        output_data = []
        for post in db_posts:
            output_data.append({
                "platform": post["platform"],
                "title": post["title"],
                "caption_length": len(post["caption"]) if post["caption"] else 0,
                "hashtag_count": len(post["hashtags"]) if post["hashtags"] else 0,
                "media_path": post["media_path"],
                "scheduled_time": post["scheduled_time"].isoformat(),
                "account": post["username"],
            })
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"📋 Plan saved to: {args.output}")


if __name__ == "__main__":
    main()

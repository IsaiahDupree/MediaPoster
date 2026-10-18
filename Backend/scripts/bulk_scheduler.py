#!/usr/bin/env python3
"""
Bulk Scheduler — Platform-Agnostic Content Scheduling Tool
===========================================================
Leverages existing MediaPoster infrastructure (BlotatoAPI, target dataclasses,
account registry) to schedule content from any media source to any platform.

Usage Examples:
    # Schedule local videos to TikTok, 30 min apart
    python bulk_scheduler.py --source /path/to/videos --platform tiktok --account isaiah_dupree --spacing 30

    # Schedule Google Drive folder to Instagram as reels, 2 hours apart
    python bulk_scheduler.py --source gdrive:FOLDER_ID --platform instagram --account the_isaiah_dupree --spacing 120 --media-type reel

    # Schedule to YouTube with titles from filenames
    python bulk_scheduler.py --source /path/to/videos --platform youtube --account 228 --spacing 180 --use-filename-as-title

    # Schedule to multiple platforms at once
    python bulk_scheduler.py --source /path/to/videos --platform tiktok,instagram --account isaiah_dupree,the_isaiah_dupree --spacing 30

    # Immediate publish (no scheduling)
    python bulk_scheduler.py --source /path/to/video.mp4 --platform tiktok --account 710 --now

    # Dry run to preview what would be scheduled
    python bulk_scheduler.py --source /path/to/videos --platform tiktok --account 710 --spacing 30 --dry-run

Rate Limits (TikTok OpenAPI):
    ~15 posts per 24-hour rolling window per creator account.
    Recommended safe max: 8 posts/day, 3+ hours apart.
"""

import argparse
import asyncio
import json
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

# Add Backend to path for imports
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.blotato_api import (
    BlotatoAPI,
    PostContent,
    Platform,
    TikTokTarget,
    TikTokPrivacy,
    InstagramTarget,
    YouTubeTarget,
    YouTubePrivacy,
    TwitterTarget,
    LinkedInTarget,
    FacebookTarget,
    PinterestTarget,
    ThreadsTarget,
    BlueskyTarget,
)
from config.blotato_accounts import (
    get_blotato_id,
    get_blotato_account,
    get_all_accounts_for_platform,
    normalize_username,
    BLOTATO_ACCOUNTS,
)


# =============================================================================
# RATE LIMITS PER PLATFORM (posts per 24h rolling window)
# =============================================================================
PLATFORM_DAILY_LIMITS = {
    "tiktok": 15,       # TikTok OpenAPI hard limit
    "instagram": 25,    # Instagram API limit
    "youtube": 50,      # YouTube API generous limit
    "twitter": 50,      # X/Twitter
    "threads": 25,
    "pinterest": 50,
    "linkedin": 25,
    "facebook": 25,
    "bluesky": 50,
}

PLATFORM_SAFE_LIMITS = {
    "tiktok": 8,        # Conservative to avoid 24h blocks
    "instagram": 15,
    "youtube": 30,
    "twitter": 30,
    "threads": 15,
    "pinterest": 30,
    "linkedin": 15,
    "facebook": 15,
    "bluesky": 30,
}

# Blotato API rate limits
BLOTATO_POST_RATE = 30    # 30 requests/minute
BLOTATO_MEDIA_RATE = 10   # 10 requests/minute


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MediaItem:
    """A single media item to be scheduled."""
    path: str                     # Local file path or URL
    filename: str                 # Display name
    size_bytes: int = 0
    gdrive_id: Optional[str] = None
    gdrive_url: Optional[str] = None
    blotato_media_url: Optional[str] = None


@dataclass
class ScheduleEntry:
    """A scheduled post entry."""
    media: MediaItem
    platform: str
    account_id: str
    account_username: str
    scheduled_time: datetime
    caption: str = ""
    title: str = ""
    target_config: Dict[str, Any] = field(default_factory=dict)
    # Result
    submission_id: Optional[str] = None
    status: str = "pending"       # pending, scheduled, failed
    error: Optional[str] = None


@dataclass 
class ScheduleResult:
    """Summary of a scheduling run."""
    total: int = 0
    scheduled: int = 0
    failed: int = 0
    entries: List[Dict[str, Any]] = field(default_factory=list)
    first_post: Optional[str] = None
    last_post: Optional[str] = None


# =============================================================================
# MEDIA SOURCE RESOLVERS
# =============================================================================

def resolve_local_source(path: str, extensions: tuple = (".mp4", ".mov", ".avi", ".mkv", ".webm")) -> List[MediaItem]:
    """Resolve local files or directory to MediaItems."""
    p = Path(path)
    items = []
    
    if p.is_file():
        items.append(MediaItem(
            path=str(p),
            filename=p.name,
            size_bytes=p.stat().st_size,
        ))
    elif p.is_dir():
        for f in sorted(p.iterdir()):
            if f.suffix.lower() in extensions and f.is_file():
                items.append(MediaItem(
                    path=str(f),
                    filename=f.name,
                    size_bytes=f.stat().st_size,
                ))
    else:
        print(f"❌ Path not found: {path}")
    
    return items


def resolve_gdrive_source(folder_id: str) -> List[MediaItem]:
    """Resolve Google Drive folder to MediaItems using gdrive CLI."""
    try:
        result = subprocess.run(
            ["gdrive", "files", "list",
             "--query", f"'{folder_id}' in parents and mimeType contains 'video/'",
             "--full-name"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ gdrive error: {result.stderr}")
            return []
        
        items = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                file_id = parts[0]
                # Name is everything between ID and "regular"
                name_end = line.find("regular")
                if name_end == -1:
                    name_end = line.find("   ", len(file_id) + 3)
                name = line[len(file_id):name_end].strip() if name_end > 0 else parts[1]
                
                gdrive_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                items.append(MediaItem(
                    path=gdrive_url,
                    filename=name,
                    gdrive_id=file_id,
                    gdrive_url=gdrive_url,
                ))
        
        return items
    except Exception as e:
        print(f"❌ Failed to list Google Drive folder: {e}")
        return []


def resolve_source(source: str) -> List[MediaItem]:
    """Auto-detect and resolve media source."""
    if source.startswith("gdrive:"):
        folder_id = source[7:]
        print(f"📁 Resolving Google Drive folder: {folder_id}")
        return resolve_gdrive_source(folder_id)
    else:
        print(f"📁 Resolving local path: {source}")
        return resolve_local_source(source)


# =============================================================================
# PLATFORM TARGET BUILDERS
# =============================================================================

def build_target(platform: str, **kwargs) -> Any:
    """Build platform-specific target with smart defaults."""
    platform = platform.lower()
    
    if platform == "tiktok":
        return TikTokTarget(
            privacy_level=TikTokPrivacy(kwargs.get("privacy", "PUBLIC_TO_EVERYONE")),
            disabled_comments=kwargs.get("disabled_comments", False),
            disabled_duet=kwargs.get("disabled_duet", False),
            disabled_stitch=kwargs.get("disabled_stitch", False),
            is_branded_content=kwargs.get("is_branded_content", False),
            is_your_brand=kwargs.get("is_your_brand", False),
            is_ai_generated=kwargs.get("is_ai_generated", False),
            title=kwargs.get("title"),
            auto_add_music=kwargs.get("auto_add_music", False),
        )
    
    elif platform == "instagram":
        return InstagramTarget(
            media_type=kwargs.get("media_type", "reel"),
            alt_text=kwargs.get("alt_text"),
            collaborators=kwargs.get("collaborators"),
        )
    
    elif platform == "youtube":
        return YouTubeTarget(
            title=kwargs.get("title", ""),
            privacy_status=YouTubePrivacy(kwargs.get("privacy", "public")),
            should_notify_subscribers=kwargs.get("notify_subscribers", True),
            is_made_for_kids=kwargs.get("made_for_kids", False),
            contains_synthetic_media=kwargs.get("synthetic_media", False),
        )
    
    elif platform == "twitter":
        return TwitterTarget()
    
    elif platform == "linkedin":
        return LinkedInTarget(page_id=kwargs.get("page_id"))
    
    elif platform == "facebook":
        return FacebookTarget(
            page_id=kwargs.get("page_id", ""),
            media_type=kwargs.get("media_type"),
        )
    
    elif platform == "pinterest":
        return PinterestTarget(
            board_id=kwargs.get("board_id", ""),
            title=kwargs.get("title"),
            alt_text=kwargs.get("alt_text"),
            link=kwargs.get("link"),
        )
    
    elif platform == "threads":
        return ThreadsTarget(
            reply_control=kwargs.get("reply_control"),
        )
    
    elif platform == "bluesky":
        return BlueskyTarget()
    
    else:
        raise ValueError(f"Unsupported platform: {platform}")


# =============================================================================
# ACCOUNT RESOLUTION
# =============================================================================

def resolve_account(platform: str, account_ref: str) -> Tuple[str, str]:
    """
    Resolve account reference to (blotato_id, username).
    Accepts: numeric ID, username, or @username.
    """
    # Try as numeric ID first
    try:
        account_id = int(account_ref)
        for acc in BLOTATO_ACCOUNTS:
            if acc.blotato_id == account_id and acc.platform.lower() == platform.lower():
                return str(acc.blotato_id), acc.username
        # If ID found but not for this platform, still use it
        for acc in BLOTATO_ACCOUNTS:
            if acc.blotato_id == account_id:
                return str(acc.blotato_id), acc.username
    except ValueError:
        pass
    
    # Try as username
    blotato_id = get_blotato_id(platform, account_ref)
    if blotato_id:
        account = get_blotato_account(platform, account_ref)
        return str(blotato_id), account.username if account else account_ref
    
    # Fuzzy match
    normalized = normalize_username(account_ref)
    for acc in BLOTATO_ACCOUNTS:
        if acc.platform.lower() == platform.lower():
            if normalized in normalize_username(acc.username) or normalize_username(acc.username) in normalized:
                return str(acc.blotato_id), acc.username
    
    raise ValueError(f"No Blotato account found for {platform}/@{account_ref}")


# =============================================================================
# CAPTION GENERATION
# =============================================================================

def generate_caption(
    platform: str,
    filename: str,
    caption: str = "",
    hashtags: List[str] = None,
    use_filename: bool = False,
) -> str:
    """Generate platform-appropriate caption."""
    if caption:
        text = caption
    elif use_filename:
        # Clean filename for caption
        name = Path(filename).stem
        # Remove common patterns like video IDs
        import re
        name = re.sub(r'#?\d{15,}', '', name)  # Remove TikTok-style IDs
        name = re.sub(r'_+', ' ', name).strip()
        name = re.sub(r'\s+', ' ', name).strip(' -_')
        text = name if name else ""
    else:
        text = ""
    
    # Add hashtags if provided
    if hashtags:
        hashtag_str = " ".join(f"#{h.lstrip('#')}" for h in hashtags)
        if text:
            text = f"{text}\n\n{hashtag_str}"
        else:
            text = hashtag_str
    
    # Platform-specific defaults
    if platform == "tiktok" and "#fyp" not in text.lower():
        if hashtags or use_filename:
            text = f"{text} #fyp" if text else "#fyp"
    
    return text


def generate_title(platform: str, filename: str, title: str = "", use_filename: bool = False) -> str:
    """Generate platform-appropriate title."""
    if title:
        return title
    if use_filename:
        name = Path(filename).stem
        import re
        name = re.sub(r'#?\d{15,}', '', name)
        name = re.sub(r'_+', ' ', name).strip()
        name = re.sub(r'\s+', ' ', name).strip(' -_')
        return name[:100] if name else ""
    return ""


# =============================================================================
# SCHEDULING ENGINE
# =============================================================================

async def make_gdrive_public(file_id: str) -> bool:
    """Make a Google Drive file publicly accessible."""
    try:
        result = subprocess.run(
            ["gdrive", "permissions", "share", file_id, "--role", "reader", "--type", "anyone"],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


async def schedule_entries(
    entries: List[ScheduleEntry],
    api: BlotatoAPI,
    dry_run: bool = False,
) -> ScheduleResult:
    """Execute the scheduling of all entries via Blotato API."""
    result = ScheduleResult(total=len(entries))
    
    if dry_run:
        print(f"\n{'='*60}")
        print(f"🔍 DRY RUN — {len(entries)} posts would be scheduled:")
        print(f"{'='*60}")
        for i, entry in enumerate(entries):
            local_time = entry.scheduled_time.astimezone()
            print(f"  [{i+1}] {entry.media.filename[:50]}")
            print(f"      → {entry.platform} @{entry.account_username}")
            print(f"      📅 {local_time.strftime('%b %d %I:%M %p')}")
            if entry.caption:
                print(f"      💬 {entry.caption[:60]}...")
            if entry.title:
                print(f"      📝 {entry.title[:60]}")
            result.entries.append({
                "filename": entry.media.filename,
                "platform": entry.platform,
                "account": entry.account_username,
                "scheduled": entry.scheduled_time.isoformat(),
                "status": "dry_run",
            })
        result.scheduled = len(entries)
        return result
    
    import httpx
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {api.api_key}",
            "Content-Type": "application/json",
        }
        
        for i, entry in enumerate(entries):
            local_time = entry.scheduled_time.astimezone()
            print(f"\n[{i+1}/{len(entries)}] {entry.media.filename[:50]}")
            print(f"  🎯 {entry.platform} @{entry.account_username}")
            print(f"  📅 {local_time.strftime('%b %d %I:%M %p')}")
            
            # Step 1: Resolve media URL
            media_url = entry.media.blotato_media_url
            
            if not media_url:
                # Need to upload to Blotato
                source_url = entry.media.gdrive_url or entry.media.path
                
                if entry.media.gdrive_id:
                    # Ensure GDrive file is public
                    await make_gdrive_public(entry.media.gdrive_id)
                
                if source_url.startswith("http"):
                    try:
                        print(f"  ⬆️  Uploading to Blotato...")
                        resp = await client.post(
                            f"{api.BASE_URL}/media",
                            headers=headers,
                            json={"url": source_url},
                            timeout=120,
                        )
                        if resp.status_code == 429:
                            print(f"  ⚠️  Media rate limited, waiting 60s...")
                            await asyncio.sleep(60)
                            resp = await client.post(
                                f"{api.BASE_URL}/media",
                                headers=headers,
                                json={"url": source_url},
                                timeout=120,
                            )
                        resp.raise_for_status()
                        data = resp.json()
                        media_url = data.get("url") or data.get("mediaUrl") or source_url
                        entry.media.blotato_media_url = media_url
                        print(f"  ✅ Media uploaded")
                    except Exception as e:
                        print(f"  ❌ Media upload failed: {e}")
                        media_url = source_url  # Fallback to direct URL
                else:
                    print(f"  ❌ Local files need a cloud URL. Upload to GDrive first.")
                    entry.status = "failed"
                    entry.error = "Local file needs cloud URL"
                    result.failed += 1
                    result.entries.append({
                        "filename": entry.media.filename,
                        "platform": entry.platform,
                        "status": "failed",
                        "error": entry.error,
                    })
                    continue
            
            # Step 2: Build target
            target = build_target(entry.platform, **entry.target_config)
            
            # Step 3: Build post payload
            content = PostContent(
                text=entry.caption,
                platform=Platform(entry.platform),
                media_urls=[media_url],
            )
            
            payload = {
                "post": {
                    "accountId": entry.account_id,
                    "content": content.to_dict(),
                    "target": target.to_dict(),
                }
            }
            
            # Add scheduling (omit for immediate publish)
            if entry.scheduled_time:
                payload["scheduledTime"] = entry.scheduled_time.isoformat()
            
            # Step 4: Submit to Blotato
            try:
                resp = await client.post(
                    f"{api.BASE_URL}/posts",
                    headers=headers,
                    json=payload,
                    timeout=60,
                )
                
                if resp.status_code == 429:
                    print(f"  ⚠️  Post rate limited, waiting 60s...")
                    await asyncio.sleep(60)
                    resp = await client.post(
                        f"{api.BASE_URL}/posts",
                        headers=headers,
                        json=payload,
                        timeout=60,
                    )
                
                resp.raise_for_status()
                resp_data = resp.json()
                entry.submission_id = resp_data.get("postSubmissionId")
                entry.status = "scheduled"
                result.scheduled += 1
                print(f"  ✅ Scheduled! ID: {entry.submission_id}")
                
            except Exception as e:
                entry.status = "failed"
                entry.error = str(e)
                result.failed += 1
                print(f"  ❌ Failed: {e}")
            
            result.entries.append({
                "filename": entry.media.filename,
                "platform": entry.platform,
                "account": entry.account_username,
                "scheduled": entry.scheduled_time.isoformat(),
                "submission_id": entry.submission_id,
                "status": entry.status,
                "error": entry.error,
            })
            
            # Rate limit pause between requests (Blotato: 30 posts/min, 10 media/min)
            await asyncio.sleep(3)
    
    # Summary
    if result.entries:
        scheduled_entries = [e for e in result.entries if e["status"] == "scheduled"]
        if scheduled_entries:
            result.first_post = scheduled_entries[0]["scheduled"]
            result.last_post = scheduled_entries[-1]["scheduled"]
    
    return result


# =============================================================================
# MAIN CLI
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Bulk Scheduler — Platform-agnostic content scheduling via Blotato",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # TikTok, 30 min apart
  %(prog)s --source ./videos --platform tiktok --account isaiah_dupree --spacing 30

  # Google Drive → Instagram reels, 2h apart  
  %(prog)s --source gdrive:FOLDER_ID --platform instagram --account 807 --spacing 120 --media-type reel

  # YouTube with titles from filenames
  %(prog)s --source ./videos --platform youtube --account 228 --spacing 180 --use-filename-as-title

  # Multi-platform
  %(prog)s --source ./videos --platform tiktok,instagram --account 710,807 --spacing 30

  # Immediate publish
  %(prog)s --source ./video.mp4 --platform tiktok --account 710 --now

  # Preview without posting
  %(prog)s --source ./videos --platform tiktok --account 710 --dry-run
        """,
    )
    
    # Required
    parser.add_argument("--source", required=True,
                        help="Media source: local path, directory, or gdrive:FOLDER_ID")
    parser.add_argument("--platform", required=True,
                        help="Target platform(s), comma-separated: tiktok,instagram,youtube,twitter,threads,pinterest,linkedin,facebook,bluesky")
    parser.add_argument("--account", required=True,
                        help="Account reference(s), comma-separated: username, @username, or numeric Blotato ID")
    
    # Scheduling
    parser.add_argument("--spacing", type=int, default=30,
                        help="Minutes between posts (default: 30)")
    parser.add_argument("--start", type=str, default=None,
                        help="Start time: ISO 8601 or 'YYYY-MM-DD HH:MM' (default: 5 min from now)")
    parser.add_argument("--now", action="store_true",
                        help="Publish immediately (no scheduling)")
    parser.add_argument("--max-per-day", type=int, default=None,
                        help="Override max posts per day (default: platform-safe limit)")
    
    # Content
    parser.add_argument("--caption", type=str, default="",
                        help="Caption text for all posts")
    parser.add_argument("--hashtags", type=str, default="",
                        help="Comma-separated hashtags (without #)")
    parser.add_argument("--title", type=str, default="",
                        help="Title for platforms that support it (YouTube, TikTok, Pinterest)")
    parser.add_argument("--use-filename-as-title", action="store_true",
                        help="Use cleaned filename as title")
    parser.add_argument("--use-filename-as-caption", action="store_true",
                        help="Use cleaned filename as caption")
    
    # Platform-specific
    parser.add_argument("--privacy", type=str, default=None,
                        help="Privacy level: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY")
    parser.add_argument("--media-type", type=str, default=None,
                        help="Media type: reel, story (Instagram), video, reel (Facebook)")
    parser.add_argument("--ai-generated", action="store_true",
                        help="Mark content as AI-generated (TikTok requirement)")
    parser.add_argument("--no-comments", action="store_true",
                        help="Disable comments (TikTok)")
    parser.add_argument("--no-duet", action="store_true",
                        help="Disable duet (TikTok)")
    parser.add_argument("--no-stitch", action="store_true",
                        help="Disable stitch (TikTok)")
    parser.add_argument("--board-id", type=str, default="",
                        help="Pinterest board ID")
    parser.add_argument("--made-for-kids", action="store_true",
                        help="YouTube: made for kids")
    parser.add_argument("--draft", action="store_true",
                        help="Save as draft (TikTok)")
    
    # Output
    parser.add_argument("--output", type=str, default=None,
                        help="Save results to JSON file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview schedule without posting")
    parser.add_argument("--list-accounts", action="store_true",
                        help="List all available accounts and exit")
    
    return parser.parse_args()


def list_all_accounts():
    """Print all available Blotato accounts."""
    print("\n📋 Available Blotato Accounts:")
    print("=" * 60)
    
    platforms = {}
    for acc in BLOTATO_ACCOUNTS:
        platforms.setdefault(acc.platform, []).append(acc)
    
    for platform, accounts in sorted(platforms.items()):
        print(f"\n  {platform.upper()} ({len(accounts)} accounts):")
        for acc in accounts:
            safe_limit = PLATFORM_SAFE_LIMITS.get(platform, 10)
            print(f"    ID {acc.blotato_id:>5} | @{acc.username:<25} | {acc.display_name or ''}")
        print(f"    └─ Safe limit: {safe_limit} posts/day")


async def main():
    args = parse_args()
    
    if args.list_accounts:
        list_all_accounts()
        return
    
    # Initialize Blotato API
    api = BlotatoAPI()
    if not api.api_key:
        print("❌ BLOTATO_API_KEY not set. Export it or add to Backend/.env")
        sys.exit(1)
    
    # Resolve media source
    media_items = resolve_source(args.source)
    if not media_items:
        print("❌ No media files found")
        sys.exit(1)
    
    print(f"📦 Found {len(media_items)} media file(s)")
    
    # Resolve platforms and accounts
    platforms = [p.strip().lower() for p in args.platform.split(",")]
    accounts_raw = [a.strip() for a in args.account.split(",")]
    
    # Match platforms to accounts (1:1 or broadcast)
    if len(accounts_raw) == 1 and len(platforms) > 1:
        accounts_raw = accounts_raw * len(platforms)
    elif len(accounts_raw) != len(platforms):
        print(f"❌ Mismatch: {len(platforms)} platforms but {len(accounts_raw)} accounts")
        sys.exit(1)
    
    platform_accounts = []
    for platform, account_ref in zip(platforms, accounts_raw):
        try:
            account_id, username = resolve_account(platform, account_ref)
            platform_accounts.append((platform, account_id, username))
            print(f"  ✅ {platform}: @{username} (ID: {account_id})")
        except ValueError as e:
            print(f"  ❌ {e}")
            sys.exit(1)
    
    # Parse hashtags
    hashtags = [h.strip() for h in args.hashtags.split(",") if h.strip()] if args.hashtags else []
    
    # Parse start time
    if args.now:
        start_time = None  # Immediate
    elif args.start:
        try:
            start_time = datetime.fromisoformat(args.start)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone(timedelta(hours=-5)))  # Default EST
        except ValueError:
            print(f"❌ Invalid start time: {args.start}")
            sys.exit(1)
    else:
        start_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # Build schedule entries
    entries = []
    for platform, account_id, username in platform_accounts:
        safe_max = args.max_per_day or PLATFORM_SAFE_LIMITS.get(platform, 10)
        
        for i, media in enumerate(media_items):
            # Calculate scheduled time with day rollover at safe limit
            if start_time:
                day = i // safe_max
                slot = i % safe_max
                scheduled = start_time + timedelta(days=day, minutes=args.spacing * slot)
            else:
                scheduled = None  # Immediate
            
            # Build target config
            target_cfg = {}
            if args.privacy:
                target_cfg["privacy"] = args.privacy
            if args.media_type:
                target_cfg["media_type"] = args.media_type
            if args.ai_generated:
                target_cfg["is_ai_generated"] = True
            if args.no_comments:
                target_cfg["disabled_comments"] = True
            if args.no_duet:
                target_cfg["disabled_duet"] = True
            if args.no_stitch:
                target_cfg["disabled_stitch"] = True
            if args.board_id:
                target_cfg["board_id"] = args.board_id
            if args.made_for_kids:
                target_cfg["made_for_kids"] = True
            if args.draft:
                target_cfg["is_draft"] = True
            
            # Title (for YouTube, TikTok, Pinterest)
            title = generate_title(
                platform, media.filename,
                title=args.title,
                use_filename=args.use_filename_as_title,
            )
            if title and platform in ("youtube", "tiktok", "pinterest"):
                target_cfg["title"] = title
            
            # Caption
            caption = generate_caption(
                platform, media.filename,
                caption=args.caption,
                hashtags=hashtags,
                use_filename=args.use_filename_as_caption,
            )
            
            entries.append(ScheduleEntry(
                media=media,
                platform=platform,
                account_id=account_id,
                account_username=username,
                scheduled_time=scheduled,
                caption=caption,
                title=title,
                target_config=target_cfg,
            ))
    
    # Rate limit warnings
    for platform, _, username in platform_accounts:
        platform_entries = [e for e in entries if e.platform == platform]
        safe_max = PLATFORM_SAFE_LIMITS.get(platform, 10)
        if len(platform_entries) > safe_max:
            days_needed = (len(platform_entries) + safe_max - 1) // safe_max
            print(f"\n⚠️  {platform}: {len(platform_entries)} posts will span {days_needed} days "
                  f"(safe limit: {safe_max}/day)")
    
    # Execute
    print(f"\n🚀 Scheduling {len(entries)} posts...")
    sched_result = await schedule_entries(entries, api, dry_run=args.dry_run)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Scheduled: {sched_result.scheduled}")
    print(f"❌ Failed: {sched_result.failed}")
    
    if sched_result.first_post:
        first = datetime.fromisoformat(sched_result.first_post).astimezone()
        last = datetime.fromisoformat(sched_result.last_post).astimezone()
        print(f"⏰ First: {first.strftime('%b %d %I:%M %p')}")
        print(f"⏰ Last:  {last.strftime('%b %d %I:%M %p')}")
    
    # Save results
    output_path = args.output or f"schedule_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(sched_result.entries, f, indent=2)
    print(f"📋 Results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())

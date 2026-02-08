#!/usr/bin/env python3
"""
Watch Folder — Auto-ingest daemon for new videos.
====================================================
Monitors one or more folders for new video files and auto-schedules them
to the PostScheduler DB. Runs as a background daemon.

When a new video is detected:
  1. Waits for file to finish writing (stable size check)
  2. Generates thumbnail
  3. Creates schedule entries for configured platforms
  4. Inserts into scheduled_posts DB
  5. PostScheduler handles the actual publishing

Usage:
    # Watch ~/sora-videos/incoming for new videos → schedule to YouTube
    python watch_folder.py ~/sora-videos/incoming --platform youtube

    # Watch multiple folders
    python watch_folder.py ~/incoming ~/sora-videos/new --platform youtube,tiktok,instagram

    # Custom scheduling (3 posts/day, 6h apart)
    python watch_folder.py ~/incoming --platform youtube --posts-per-day 3 --spacing 6

    # Watch with metadata template auto-generation
    python watch_folder.py ~/incoming --platform youtube --auto-metadata

    # Run as daemon (background)
    python watch_folder.py ~/incoming --platform youtube --daemon

    # Process existing files on startup then watch
    python watch_folder.py ~/incoming --platform youtube --process-existing
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

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

LOG_PREFIX = "📂 [WatchFolder]"


# =============================================================================
# FILE STABILITY CHECK
# =============================================================================

def wait_for_stable(path: Path, check_interval: float = 2.0, max_wait: float = 300.0) -> bool:
    """Wait for a file to finish writing (stable size)."""
    if not path.exists():
        return False
    
    prev_size = -1
    elapsed = 0.0
    
    while elapsed < max_wait:
        try:
            current_size = path.stat().st_size
            if current_size == prev_size and current_size > 0:
                return True
            prev_size = current_size
            time.sleep(check_interval)
            elapsed += check_interval
        except OSError:
            return False
    
    return False


# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def title_from_filename(filename: str) -> str:
    """Generate a clean title from a filename."""
    name = Path(filename).stem
    name = re.sub(r'^(cleaned_|final_|v\d+_|draft_)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]+', ' ', name)
    name = name.strip().title()
    name = re.sub(r'\s+', ' ', name)
    return name[:100]


def load_sidecar_metadata(video_path: Path) -> Dict:
    """Load metadata from a sidecar JSON file (same name as video)."""
    json_path = video_path.with_suffix('.json')
    if json_path.exists():
        try:
            with open(json_path) as f:
                return json.load(f)
        except Exception:
            pass
    
    # Try .meta.json
    meta_path = video_path.parent / f"{video_path.stem}.meta.json"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                return json.load(f)
        except Exception:
            pass
    
    return {}


def generate_thumbnail(video_path: Path, thumb_dir: Path) -> Optional[str]:
    """Generate a thumbnail from a video."""
    thumb_name = f"{video_path.stem}.jpg"
    thumb_path = thumb_dir / thumb_name
    
    if thumb_path.exists():
        return f"/static/thumbnails/{thumb_name}"
    
    try:
        subprocess.run([
            'ffmpeg', '-i', str(video_path), '-ss', '00:00:01', '-vframes', '1',
            '-vf', 'scale=360:-1', '-q:v', '3', str(thumb_path), '-y'
        ], capture_output=True, timeout=10)
        
        if thumb_path.exists():
            return f"/static/thumbnails/{thumb_name}"
    except Exception:
        pass
    
    return None


# =============================================================================
# SCHEDULING
# =============================================================================

def find_next_slot(engine, platform: str, posts_per_day: int = 2, spacing_hours: float = 8) -> datetime:
    """Find the next available scheduling slot for a platform."""
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Get the latest scheduled time for this platform
        result = conn.execute(text("""
            SELECT MAX(scheduled_time) 
            FROM scheduled_posts 
            WHERE platform = :platform AND status = 'scheduled'
        """), {"platform": platform})
        
        latest = result.scalar()
    
    now = datetime.now(timezone.utc)
    
    if latest and latest > now:
        # Schedule after the last post with spacing
        next_slot = latest + timedelta(hours=spacing_hours)
    else:
        # Start from the next optimal hour
        optimal = OPTIMAL_HOURS_UTC.get(platform, [15])
        tomorrow = now + timedelta(days=1)
        next_slot = tomorrow.replace(hour=optimal[0], minute=0, second=0, microsecond=0)
    
    # Don't schedule more than posts_per_day on the same day
    from sqlalchemy import text as sa_text
    with engine.connect() as conn:
        date_str = next_slot.strftime('%Y-%m-%d')
        result = conn.execute(sa_text("""
            SELECT COUNT(*) FROM scheduled_posts 
            WHERE platform = :platform 
              AND status = 'scheduled'
              AND DATE(scheduled_time) = :date
        """), {"platform": platform, "date": date_str})
        
        day_count = result.scalar()
        
        if day_count >= posts_per_day:
            # Move to next day at first optimal hour
            optimal = OPTIMAL_HOURS_UTC.get(platform, [15])
            next_day = next_slot + timedelta(days=1)
            next_slot = next_day.replace(hour=optimal[0], minute=0, second=0, microsecond=0)
    
    return next_slot


def schedule_video(
    engine,
    video_path: Path,
    platforms: List[Tuple[str, str, str]],  # [(platform, blotato_id, username)]
    posts_per_day: int = 2,
    spacing_hours: float = 8,
    cross_post_delay: float = 2,
    auto_metadata: bool = True,
    thumb_dir: Optional[Path] = None,
) -> List[Dict]:
    """Schedule a single video across platforms. Returns list of created posts."""
    from sqlalchemy import text
    
    # Load sidecar metadata
    meta = load_sidecar_metadata(video_path)
    
    # Generate title
    title = meta.get("title", "")
    if not title:
        title = title_from_filename(video_path.name)
    
    # Caption
    caption = meta.get("caption", meta.get("description", ""))
    
    # Hashtags
    hashtags = meta.get("hashtags", [])
    
    # Thumbnail
    thumbnail_url = None
    if thumb_dir:
        thumbnail_url = generate_thumbnail(video_path, thumb_dir)
    
    posts = []
    base_slot = None
    
    for plat_idx, (platform, blotato_id, username) in enumerate(platforms):
        if base_slot is None:
            slot = find_next_slot(engine, platform, posts_per_day, spacing_hours)
            base_slot = slot
        else:
            # Cross-post delay from primary platform
            slot = base_slot + timedelta(hours=cross_post_delay * plat_idx)
        
        # Adapt title for platform
        plat_title = title
        if platform == "youtube" and "#shorts" not in plat_title.lower():
            plat_title = f"{plat_title} #shorts" if len(plat_title) < 90 else plat_title
        elif platform != "youtube":
            plat_title = re.sub(r'\s*#shorts\s*', '', plat_title, flags=re.IGNORECASE).strip()
        
        post_type = "short" if platform == "youtube" else "reel"
        
        post = {
            "id": str(uuid4()),
            "platform": platform,
            "title": plat_title,
            "caption": caption[:4990] if caption else "",
            "hashtags": hashtags if hashtags else None,
            "media_path": str(video_path),
            "scheduled_time": slot,
            "blotato_id": blotato_id,
            "username": username,
            "thumbnail_url": thumbnail_url,
            "post_type": post_type,
        }
        
        # Insert into DB
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO scheduled_posts 
                    (id, platform, title, caption, hashtags, media_path,
                     scheduled_time, status, blotato_account_id, account_username,
                     thumbnail_url, post_type, source, created_at, updated_at)
                    VALUES 
                    (:id, :platform, :title, :caption, :hashtags, :media_path,
                     :scheduled_time, 'scheduled', :blotato_id, :username,
                     :thumbnail_url, :post_type, 'watcher', NOW(), NOW())
                """), post)
            
            posts.append(post)
            local_time = slot.astimezone()
            print(f"{LOG_PREFIX} ✅ Scheduled: {video_path.name} → {platform} @{username} "
                  f"at {local_time.strftime('%b %d %I:%M %p')}")
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ Failed to schedule {video_path.name} → {platform}: {e}")
    
    return posts


# =============================================================================
# FOLDER WATCHER
# =============================================================================

class FolderWatcher:
    """Watches folders for new video files and auto-schedules them."""
    
    def __init__(
        self,
        watch_dirs: List[Path],
        platforms: List[Tuple[str, str, str]],
        posts_per_day: int = 2,
        spacing_hours: float = 8,
        cross_post_delay: float = 2,
        poll_interval: float = 10.0,
        process_existing: bool = False,
        auto_metadata: bool = True,
        generate_thumbnails: bool = True,
    ):
        self.watch_dirs = watch_dirs
        self.platforms = platforms
        self.posts_per_day = posts_per_day
        self.spacing_hours = spacing_hours
        self.cross_post_delay = cross_post_delay
        self.poll_interval = poll_interval
        self.process_existing = process_existing
        self.auto_metadata = auto_metadata
        self.generate_thumbnails = generate_thumbnails
        
        self.known_files: Set[str] = set()
        self.running = False
        self.engine = None
        self.thumb_dir = BACKEND_DIR / "static" / "thumbnails"
        
        # Stats
        self.total_scheduled = 0
        self.total_errors = 0
        self.start_time = None
    
    def _get_engine(self):
        if self.engine is None:
            from sqlalchemy import create_engine
            self.engine = create_engine(DATABASE_URL)
        return self.engine
    
    def _scan_existing(self) -> Set[str]:
        """Get all existing video files in watched directories."""
        files = set()
        for d in self.watch_dirs:
            if d.exists():
                for f in d.iterdir():
                    if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
                        files.add(str(f))
        return files
    
    def _detect_new_files(self) -> List[Path]:
        """Detect new video files that weren't seen before."""
        new_files = []
        for d in self.watch_dirs:
            if not d.exists():
                continue
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
                    key = str(f)
                    if key not in self.known_files:
                        new_files.append(f)
                        self.known_files.add(key)
        return sorted(new_files)
    
    def _process_file(self, video_path: Path):
        """Process a single new video file."""
        print(f"\n{LOG_PREFIX} 🆕 New video detected: {video_path.name}")
        
        # Wait for file to finish writing
        print(f"{LOG_PREFIX} ⏳ Waiting for file to stabilize...")
        if not wait_for_stable(video_path):
            print(f"{LOG_PREFIX} ⚠️  File didn't stabilize: {video_path.name}")
            return
        
        size_mb = video_path.stat().st_size / (1024 * 1024)
        print(f"{LOG_PREFIX} 📦 File ready: {size_mb:.1f} MB")
        
        # Schedule across platforms
        engine = self._get_engine()
        thumb_dir = self.thumb_dir if self.generate_thumbnails else None
        if thumb_dir:
            thumb_dir.mkdir(parents=True, exist_ok=True)
        
        posts = schedule_video(
            engine=engine,
            video_path=video_path,
            platforms=self.platforms,
            posts_per_day=self.posts_per_day,
            spacing_hours=self.spacing_hours,
            cross_post_delay=self.cross_post_delay,
            auto_metadata=self.auto_metadata,
            thumb_dir=thumb_dir,
        )
        
        self.total_scheduled += len(posts)
        if not posts:
            self.total_errors += 1
    
    def start(self):
        """Start watching folders."""
        self.running = True
        self.start_time = datetime.now()
        
        # Create watch directories if they don't exist
        for d in self.watch_dirs:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initial scan
        existing = self._scan_existing()
        
        if self.process_existing:
            print(f"{LOG_PREFIX} Processing {len(existing)} existing files...")
            for f in sorted(existing):
                self.known_files.add(f)
                self._process_file(Path(f))
        else:
            self.known_files = existing
            print(f"{LOG_PREFIX} Skipping {len(existing)} existing files (use --process-existing to include)")
        
        # Watch loop
        dirs_str = ", ".join(str(d) for d in self.watch_dirs)
        plats_str = ", ".join(p[0] for p in self.platforms)
        
        print(f"\n{LOG_PREFIX} 👁️  Watching for new videos...")
        print(f"{LOG_PREFIX} 📁 Directories: {dirs_str}")
        print(f"{LOG_PREFIX} 📱 Platforms: {plats_str}")
        print(f"{LOG_PREFIX} ⏱️  Check interval: {self.poll_interval}s")
        print(f"{LOG_PREFIX} Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                new_files = self._detect_new_files()
                
                for f in new_files:
                    self._process_file(f)
                
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            pass
        
        self.stop()
    
    def stop(self):
        """Stop watching."""
        self.running = False
        elapsed = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        print(f"\n{LOG_PREFIX} 🛑 Stopped")
        print(f"{LOG_PREFIX} ⏱️  Ran for: {elapsed}")
        print(f"{LOG_PREFIX} ✅ Scheduled: {self.total_scheduled} posts")
        print(f"{LOG_PREFIX} ❌ Errors: {self.total_errors}")


# =============================================================================
# CLI
# =============================================================================

def _load_env():
    """Load .env file for config access."""
    env_path = BACKEND_DIR / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            # Manual fallback
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())


def resolve_account(platform: str, ref: str) -> Tuple[str, str]:
    """Resolve account reference to (blotato_id, username)."""
    # Empty ref → use defaults
    if not ref or not ref.strip():
        if platform in DEFAULT_ACCOUNTS:
            default = DEFAULT_ACCOUNTS[platform]
            return default["id"], default["username"]
        raise ValueError(f"No default account for {platform}")
    
    # Numeric ref → Blotato ID
    try:
        int(ref)
        try:
            _load_env()
            from config.blotato_accounts import BLOTATO_ACCOUNTS
            for acc in BLOTATO_ACCOUNTS:
                if str(acc.blotato_id) == ref:
                    return ref, acc.username
        except Exception:
            pass
        default = DEFAULT_ACCOUNTS.get(platform, {})
        return ref, default.get("username", "unknown")
    except ValueError:
        pass
    
    # Username ref
    ref = ref.lstrip("@")
    try:
        _load_env()
        from config.blotato_accounts import get_blotato_id, get_blotato_account
        blotato_id = get_blotato_id(platform, ref)
        if blotato_id:
            acc = get_blotato_account(platform, ref)
            return str(blotato_id), acc.username if acc else ref
    except Exception:
        pass
    
    if platform in DEFAULT_ACCOUNTS:
        default = DEFAULT_ACCOUNTS[platform]
        return default["id"], default["username"]
    
    raise ValueError(f"Cannot resolve account '{ref}' for {platform}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Watch Folder — Auto-ingest daemon for new videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch folder for new videos → YouTube
  %(prog)s ~/incoming --platform youtube

  # Watch folder → 3 platforms
  %(prog)s ~/incoming --platform youtube,tiktok,instagram

  # Process existing files too
  %(prog)s ~/incoming --platform youtube --process-existing

  # Custom scheduling
  %(prog)s ~/incoming --platform youtube --posts-per-day 3 --spacing 6

  # Watch multiple folders
  %(prog)s ~/folder1 ~/folder2 --platform youtube
        """,
    )
    
    parser.add_argument("folders", nargs="+", help="Folder(s) to watch for new videos")
    parser.add_argument("--platform", "-p", default="youtube",
                        help="Platform(s), comma-separated (default: youtube)")
    parser.add_argument("--account", "-a", default=None,
                        help="Account ref(s), comma-separated")
    parser.add_argument("--posts-per-day", type=int, default=2,
                        help="Max posts per day per platform (default: 2)")
    parser.add_argument("--spacing", type=float, default=8,
                        help="Hours between posts (default: 8)")
    parser.add_argument("--cross-post-delay", type=float, default=2,
                        help="Hours delay for cross-posts (default: 2)")
    parser.add_argument("--interval", type=float, default=10,
                        help="Seconds between folder checks (default: 10)")
    parser.add_argument("--process-existing", action="store_true",
                        help="Process existing files on startup")
    parser.add_argument("--no-thumbnails", action="store_true",
                        help="Don't generate thumbnails")
    parser.add_argument("--auto-metadata", action="store_true", default=True,
                        help="Auto-generate metadata from filename (default: true)")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in background (detach from terminal)")
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Resolve folders
    watch_dirs = [Path(f).expanduser().resolve() for f in args.folders]
    for d in watch_dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"{LOG_PREFIX} Created watch directory: {d}")
    
    # Resolve platforms and accounts
    platforms = [p.strip().lower() for p in args.platform.split(",")]
    
    if args.account:
        account_refs = [a.strip() for a in args.account.split(",")]
    else:
        account_refs = [DEFAULT_ACCOUNTS.get(p, {}).get("id", "") for p in platforms]
    
    if len(account_refs) == 1 and len(platforms) > 1:
        account_refs = account_refs * len(platforms)
    
    platform_accounts = []
    for platform, ref in zip(platforms, account_refs):
        try:
            blotato_id, username = resolve_account(platform, ref)
            platform_accounts.append((platform, blotato_id, username))
            print(f"{LOG_PREFIX} ✅ {platform}: @{username} (ID: {blotato_id})")
        except ValueError as e:
            print(f"{LOG_PREFIX} ❌ {e}")
            sys.exit(1)
    
    # Daemon mode
    if args.daemon:
        pid = os.fork()
        if pid > 0:
            print(f"{LOG_PREFIX} Daemon started (PID: {pid})")
            sys.exit(0)
        
        os.setsid()
        # Redirect output to log file
        log_file = BACKEND_DIR / "logs" / "watch_folder.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(log_file, "a")
        sys.stderr = sys.stdout
    
    # Create and start watcher
    watcher = FolderWatcher(
        watch_dirs=watch_dirs,
        platforms=platform_accounts,
        posts_per_day=args.posts_per_day,
        spacing_hours=args.spacing,
        cross_post_delay=args.cross_post_delay,
        poll_interval=args.interval,
        process_existing=args.process_existing,
        auto_metadata=args.auto_metadata,
        generate_thumbnails=not args.no_thumbnails,
    )
    
    # Handle signals
    def handle_signal(signum, frame):
        watcher.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    watcher.start()


if __name__ == "__main__":
    main()

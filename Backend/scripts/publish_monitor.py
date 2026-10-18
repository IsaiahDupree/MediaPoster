#!/usr/bin/env python3
"""
Publish Monitor — Real-time monitoring of post publishing status.
==================================================================
Connects to the PostScheduler DB and monitors publishing activity.
Shows countdown timers, publish results, and alerts on failures.

Can also send notifications via:
  - Terminal notifications (macOS native)
  - Log file
  - Webhook (Slack, Discord, etc.)

Usage:
    # Live monitor with countdown to next post
    python publish_monitor.py

    # Monitor with macOS notifications
    python publish_monitor.py --notify

    # Monitor with webhook alerts (Slack/Discord)
    python publish_monitor.py --webhook https://hooks.slack.com/...

    # One-shot status check (no live monitoring)
    python publish_monitor.py --status

    # Show publish history (last 24h)
    python publish_monitor.py --history

    # Watch for failures only
    python publish_monitor.py --failures-only
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

LOG_PREFIX = "📡 [Monitor]"


# =============================================================================
# NOTIFICATIONS
# =============================================================================

def notify_macos(title: str, message: str, sound: str = "Glass"):
    """Send macOS native notification."""
    try:
        script = f'display notification "{message}" with title "{title}" sound name "{sound}"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass


def notify_webhook(url: str, title: str, message: str, color: str = "good"):
    """Send webhook notification (Slack/Discord compatible)."""
    try:
        import httpx
        payload = {
            "text": f"*{title}*\n{message}",
            "attachments": [{
                "color": color,
                "title": title,
                "text": message,
                "ts": int(time.time()),
            }]
        }
        httpx.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"{LOG_PREFIX} ⚠️  Webhook failed: {e}")


def notify_log(log_path: Path, title: str, message: str):
    """Append to log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] {title}: {message}\n")


# =============================================================================
# DATABASE QUERIES
# =============================================================================

def get_engine():
    from sqlalchemy import create_engine
    return create_engine(DATABASE_URL)


def get_status_summary(engine) -> Dict:
    """Get current schedule status summary."""
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT status, COUNT(*) 
            FROM scheduled_posts 
            GROUP BY status 
            ORDER BY status
        """))
        counts = {r[0]: r[1] for r in result.fetchall()}
    
    return counts


def get_upcoming_posts(engine, limit: int = 10) -> List[Dict]:
    """Get upcoming scheduled posts."""
    from sqlalchemy import text
    
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, title, platform, account_username, scheduled_time, status
            FROM scheduled_posts
            WHERE status = 'scheduled' AND scheduled_time > :now
            ORDER BY scheduled_time ASC
            LIMIT :limit
        """), {"now": now, "limit": limit})
        
        posts = []
        for r in result.fetchall():
            posts.append({
                "id": str(r[0]),
                "title": r[1] or "Untitled",
                "platform": r[2],
                "username": r[3] or "",
                "scheduled_time": r[4],
                "status": r[5],
            })
    return posts


def get_due_posts(engine) -> List[Dict]:
    """Get posts that are due now but haven't published yet."""
    from sqlalchemy import text
    
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, title, platform, account_username, scheduled_time, status
            FROM scheduled_posts
            WHERE status IN ('scheduled', 'publishing')
              AND scheduled_time <= :now
            ORDER BY scheduled_time ASC
        """), {"now": now})
        
        posts = []
        for r in result.fetchall():
            posts.append({
                "id": str(r[0]),
                "title": r[1] or "Untitled",
                "platform": r[2],
                "username": r[3] or "",
                "scheduled_time": r[4],
                "status": r[5],
            })
    return posts


def get_recently_published(engine, hours: int = 24) -> List[Dict]:
    """Get recently published or failed posts."""
    from sqlalchemy import text
    
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, title, platform, account_username, scheduled_time, 
                   status, updated_at, last_error
            FROM scheduled_posts
            WHERE status IN ('published', 'posted', 'failed')
              AND updated_at > :since
            ORDER BY updated_at DESC
        """), {"since": since})
        
        posts = []
        for r in result.fetchall():
            posts.append({
                "id": str(r[0]),
                "title": r[1] or "Untitled",
                "platform": r[2],
                "username": r[3] or "",
                "scheduled_time": r[4],
                "status": r[5],
                "updated_at": r[6],
                "error": r[7],
            })
    return posts


def get_failed_posts(engine) -> List[Dict]:
    """Get failed posts."""
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, title, platform, account_username, scheduled_time,
                   last_error, retry_count, updated_at
            FROM scheduled_posts
            WHERE status = 'failed'
            ORDER BY updated_at DESC
            LIMIT 20
        """))
        
        posts = []
        for r in result.fetchall():
            posts.append({
                "id": str(r[0]),
                "title": r[1] or "Untitled",
                "platform": r[2],
                "username": r[3] or "",
                "scheduled_time": r[4],
                "error": r[5] or "Unknown error",
                "retry_count": r[6] or 0,
                "updated_at": r[7],
            })
    return posts


# =============================================================================
# DISPLAY
# =============================================================================

def format_countdown(dt: datetime) -> str:
    """Format a countdown string from now to dt."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = dt - now
    
    if diff.total_seconds() < 0:
        mins = abs(int(diff.total_seconds() / 60))
        return f"OVERDUE by {mins}m"
    
    total_secs = int(diff.total_seconds())
    days = total_secs // 86400
    hours = (total_secs % 86400) // 3600
    mins = (total_secs % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"


def print_status(engine):
    """Print a comprehensive status overview."""
    counts = get_status_summary(engine)
    upcoming = get_upcoming_posts(engine, limit=5)
    due = get_due_posts(engine)
    
    now = datetime.now()
    print(f"\n{'='*65}")
    print(f"{LOG_PREFIX} PUBLISH STATUS — {now.strftime('%b %d %Y %I:%M %p %Z')}")
    print(f"{'='*65}")
    
    # Counts
    total = sum(counts.values())
    scheduled = counts.get("scheduled", 0)
    published = counts.get("published", 0) + counts.get("posted", 0)
    failed = counts.get("failed", 0)
    draft = counts.get("draft", 0)
    publishing = counts.get("publishing", 0)
    
    print(f"\n📊 Schedule: {total} total")
    print(f"   📅 Scheduled:  {scheduled}")
    print(f"   ✅ Published:  {published}")
    print(f"   ❌ Failed:     {failed}")
    if draft:
        print(f"   📝 Draft:      {draft}")
    if publishing:
        print(f"   🔄 Publishing: {publishing}")
    
    # Due now
    if due:
        print(f"\n⚠️  DUE NOW ({len(due)} posts):")
        for p in due:
            overdue = format_countdown(p["scheduled_time"])
            print(f"   🔴 {p['title'][:35]:35s} | {p['platform']:10s} | {overdue}")
    
    # Upcoming
    if upcoming:
        print(f"\n⏳ NEXT UP:")
        for i, p in enumerate(upcoming):
            countdown = format_countdown(p["scheduled_time"])
            local_time = p["scheduled_time"].astimezone()
            time_str = local_time.strftime("%b %d %I:%M %p")
            marker = "🟢" if i == 0 else "⚪"
            print(f"   {marker} {p['title'][:30]:30s} | {p['platform']:10s} | {time_str} | T-{countdown}")
    
    print(f"{'='*65}\n")


def print_history(engine, hours: int = 24):
    """Print recent publish history."""
    recent = get_recently_published(engine, hours)
    
    print(f"\n{'='*65}")
    print(f"{LOG_PREFIX} PUBLISH HISTORY (last {hours}h)")
    print(f"{'='*65}")
    
    if not recent:
        print(f"\n   No posts published or failed in the last {hours}h")
    else:
        for p in recent:
            if p["status"] in ("published", "posted"):
                icon = "✅"
            else:
                icon = "❌"
            
            updated = p["updated_at"].astimezone() if p["updated_at"] else None
            time_str = updated.strftime("%b %d %I:%M %p") if updated else "?"
            
            print(f"   {icon} {p['title'][:30]:30s} | {p['platform']:10s} | {time_str}")
            if p.get("error"):
                print(f"      Error: {p['error'][:60]}")
    
    print(f"{'='*65}\n")


# =============================================================================
# LIVE MONITOR
# =============================================================================

def live_monitor(
    engine,
    notify: bool = False,
    webhook_url: Optional[str] = None,
    failures_only: bool = False,
    interval: float = 30,
):
    """Run live monitoring loop."""
    log_path = BACKEND_DIR / "logs" / "publish_monitor.log"
    known_published = set()
    known_failed = set()
    
    # Initial scan of already-published posts
    recent = get_recently_published(engine, hours=24)
    for p in recent:
        if p["status"] in ("published", "posted"):
            known_published.add(p["id"])
        elif p["status"] == "failed":
            known_failed.add(p["id"])
    
    print(f"{LOG_PREFIX} Live monitoring started (interval: {interval}s)")
    print(f"{LOG_PREFIX} Notifications: {'macOS' if notify else 'off'}")
    if webhook_url:
        print(f"{LOG_PREFIX} Webhook: configured")
    print(f"{LOG_PREFIX} Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Check for newly published posts
            recent = get_recently_published(engine, hours=1)
            
            for p in recent:
                post_id = p["id"]
                
                if p["status"] in ("published", "posted") and post_id not in known_published:
                    known_published.add(post_id)
                    
                    if not failures_only:
                        title = f"✅ Published: {p['platform']}"
                        message = f"{p['title'][:50]} → @{p['username']}"
                        
                        print(f"\n{LOG_PREFIX} {title}")
                        print(f"   {message}")
                        
                        notify_log(log_path, title, message)
                        
                        if notify:
                            notify_macos(title, message)
                        if webhook_url:
                            notify_webhook(webhook_url, title, message, color="good")
                
                elif p["status"] == "failed" and post_id not in known_failed:
                    known_failed.add(post_id)
                    
                    title = f"❌ FAILED: {p['platform']}"
                    message = f"{p['title'][:50]} — {p.get('error', 'Unknown')[:60]}"
                    
                    print(f"\n{LOG_PREFIX} {title}")
                    print(f"   {message}")
                    
                    notify_log(log_path, title, message)
                    
                    if notify:
                        notify_macos(title, message, sound="Basso")
                    if webhook_url:
                        notify_webhook(webhook_url, title, message, color="danger")
            
            # Print countdown to next post
            upcoming = get_upcoming_posts(engine, limit=1)
            due = get_due_posts(engine)
            
            if due:
                sys.stdout.write(f"\r{LOG_PREFIX} ⚠️  {len(due)} posts due now | ")
            elif upcoming:
                p = upcoming[0]
                countdown = format_countdown(p["scheduled_time"])
                sys.stdout.write(f"\r{LOG_PREFIX} Next: {p['platform']:8s} T-{countdown:12s} | ")
            else:
                sys.stdout.write(f"\r{LOG_PREFIX} No upcoming posts | ")
            
            now = datetime.now().strftime("%H:%M:%S")
            sys.stdout.write(f"Checked: {now}    ")
            sys.stdout.flush()
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\n\n{LOG_PREFIX} Monitoring stopped")
        print(f"{LOG_PREFIX} Published: {len(known_published)}, Failed: {len(known_failed)}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Publish Monitor — Real-time publishing status and notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("--status", action="store_true",
                        help="One-shot status check (no live monitoring)")
    parser.add_argument("--history", action="store_true",
                        help="Show publish history")
    parser.add_argument("--hours", type=int, default=24,
                        help="Hours of history to show (default: 24)")
    parser.add_argument("--notify", action="store_true",
                        help="Enable macOS native notifications")
    parser.add_argument("--webhook", type=str, default=None,
                        help="Webhook URL for Slack/Discord notifications")
    parser.add_argument("--failures-only", action="store_true",
                        help="Only alert on failures")
    parser.add_argument("--interval", type=float, default=30,
                        help="Check interval in seconds (default: 30)")
    parser.add_argument("--failures", action="store_true",
                        help="Show failed posts")
    
    args = parser.parse_args()
    
    engine = get_engine()
    
    if args.status:
        print_status(engine)
        return
    
    if args.history:
        print_history(engine, args.hours)
        return
    
    if args.failures:
        failed = get_failed_posts(engine)
        if not failed:
            print(f"{LOG_PREFIX} No failed posts")
        else:
            print(f"\n{LOG_PREFIX} FAILED POSTS ({len(failed)}):")
            for p in failed:
                print(f"   ❌ {p['title'][:35]:35s} | {p['platform']:10s} | retries: {p['retry_count']}")
                print(f"      Error: {p['error'][:70]}")
        return
    
    # Default: print status then start live monitoring
    print_status(engine)
    live_monitor(
        engine=engine,
        notify=args.notify,
        webhook_url=args.webhook,
        failures_only=args.failures_only,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Content Planner — Strategic scheduling analysis and planning tool.
===================================================================
Analyzes the current schedule, identifies gaps and optimal slots, and helps
plan new content drops. Works independently of the backend server.

Usage:
    # Show full schedule overview with gap analysis
    python plan_content.py overview

    # Find optimal time slots for N new videos
    python plan_content.py find-slots --count 10 --platform youtube

    # Analyze posting density and suggest improvements
    python plan_content.py analyze

    # Clear all scheduled posts for a platform (with confirmation)
    python plan_content.py clear --platform tiktok --status draft

    # Export current schedule to JSON
    python plan_content.py export --output schedule.json

    # Import schedule from JSON (created by schedule_videos.py --output)
    python plan_content.py import --input schedule.json

    # Show what's publishing today/tomorrow
    python plan_content.py upcoming --days 2

    # Reschedule all posts for a platform (shift times)
    python plan_content.py shift --platform youtube --hours 3

    # Show account health and posting stats
    python plan_content.py accounts
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add Backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

# Optimal posting windows (UTC hours)
OPTIMAL_WINDOWS = {
    "youtube": {
        "prime": [(15, 16), (19, 20), (23, 0)],   # 10-11am, 2-3pm, 6-7pm EST
        "good":  [(13, 15), (17, 19), (21, 23)],
        "avoid": [(3, 10)],                         # 10pm-5am EST
    },
    "tiktok": {
        "prime": [(14, 15), (17, 18), (21, 22)],   # 9-10am, 12-1pm, 4-5pm EST
        "good":  [(12, 14), (16, 17), (19, 21)],
        "avoid": [(3, 10)],
    },
    "instagram": {
        "prime": [(15, 16), (18, 19), (23, 0)],    # 10-11am, 1-2pm, 6-7pm EST
        "good":  [(12, 15), (17, 18), (20, 23)],
        "avoid": [(3, 10)],
    },
}

PLATFORM_DAILY_SAFE = {
    "youtube": 4, "tiktok": 6, "instagram": 5,
    "threads": 4, "twitter": 8, "pinterest": 8,
    "linkedin": 3, "facebook": 4, "bluesky": 6,
}


def get_engine():
    from sqlalchemy import create_engine
    return create_engine(DATABASE_URL)


def query_posts(engine, where: str = "1=1", params: dict = None) -> List[Dict]:
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT id, title, platform, scheduled_time, status, media_path,
                   blotato_account_id, account_username, caption, hashtags,
                   published_at, created_at, thumbnail_url
            FROM scheduled_posts
            WHERE {where}
            ORDER BY scheduled_time ASC
        """), params or {})
        return [
            {
                "id": str(r[0]), "title": r[1], "platform": r[2],
                "scheduled_time": r[3], "status": r[4], "media_path": r[5],
                "blotato_account_id": r[6], "account_username": r[7],
                "caption": r[8], "hashtags": r[9], "published_at": r[10],
                "created_at": r[11], "thumbnail_url": r[12],
            }
            for r in result.fetchall()
        ]


# =============================================================================
# COMMANDS
# =============================================================================

def cmd_overview(args):
    """Full schedule overview with gap analysis."""
    engine = get_engine()
    posts = query_posts(engine, "status IN ('scheduled', 'publishing', 'published')")
    
    if not posts:
        print("📭 No posts found.")
        return
    
    scheduled = [p for p in posts if p["status"] == "scheduled"]
    published = [p for p in posts if p["status"] == "published"]
    
    print(f"\n{'=' * 70}")
    print(f"  📊 SCHEDULE OVERVIEW")
    print(f"{'=' * 70}")
    print(f"  Total posts:     {len(posts)}")
    print(f"  Scheduled:       {len(scheduled)}")
    print(f"  Published:       {len(published)}")
    
    # Platform breakdown
    print(f"\n  📱 By Platform:")
    by_plat = defaultdict(lambda: {"scheduled": 0, "published": 0})
    for p in posts:
        by_plat[p["platform"]][p["status"]] += 1
    for plat in sorted(by_plat.keys()):
        counts = by_plat[plat]
        total = counts["scheduled"] + counts["published"]
        print(f"    {plat:12s} {total:3d} total ({counts['scheduled']} pending, {counts['published']} done)")
    
    # Date range
    times = [p["scheduled_time"] for p in scheduled if p["scheduled_time"]]
    if times:
        first = min(times)
        last = max(times)
        days = (last - first).days + 1
        print(f"\n  📅 Date Range: {str(first)[:10]} → {str(last)[:10]} ({days} days)")
    
    # Daily density
    print(f"\n  📈 Daily Density:")
    by_date = defaultdict(lambda: defaultdict(int))
    for p in scheduled:
        if p["scheduled_time"]:
            date = str(p["scheduled_time"])[:10]
            by_date[date][p["platform"]] += 1
    
    for date in sorted(by_date.keys()):
        platforms = by_date[date]
        total = sum(platforms.values())
        plat_str = " | ".join(f"{p}:{c}" for p, c in sorted(platforms.items()))
        bar = "█" * min(total, 30)
        print(f"    {date} {bar} {total:2d} ({plat_str})")
    
    # Gap analysis
    if times:
        print(f"\n  🔍 Gap Analysis:")
        dates = sorted(set(str(t)[:10] for t in times))
        all_dates = []
        current = datetime.fromisoformat(dates[0])
        end = datetime.fromisoformat(dates[-1])
        while current <= end:
            all_dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        gaps = [d for d in all_dates if d not in dates]
        if gaps:
            print(f"    ⚠️  {len(gaps)} day(s) with NO posts:")
            for g in gaps[:10]:
                print(f"      {g}")
            if len(gaps) > 10:
                print(f"      ... and {len(gaps) - 10} more")
        else:
            print(f"    ✅ No gaps — every day has at least 1 post")
    
    # Content quality
    print(f"\n  📝 Content Quality:")
    no_caption = [p for p in scheduled if not p["caption"] or len(p["caption"]) < 50]
    no_hashtags = [p for p in scheduled if not p["hashtags"]]
    no_thumbnail = [p for p in scheduled if not p["thumbnail_url"]]
    no_media = [p for p in scheduled if not p["media_path"]]
    
    print(f"    Missing/short captions: {len(no_caption)}")
    print(f"    Missing hashtags:       {len(no_hashtags)}")
    print(f"    Missing thumbnails:     {len(no_thumbnail)}")
    print(f"    Missing media files:    {len(no_media)}")
    
    if no_media:
        print(f"\n    ⚠️  Posts without media files (CANNOT PUBLISH):")
        for p in no_media[:5]:
            print(f"      {p['platform']:10s} | {(p['title'] or '?')[:40]}")


def cmd_analyze(args):
    """Analyze posting strategy and suggest improvements."""
    engine = get_engine()
    posts = query_posts(engine, "status = 'scheduled'")
    
    if not posts:
        print("📭 No scheduled posts to analyze.")
        return
    
    print(f"\n{'=' * 70}")
    print(f"  🧠 STRATEGIC ANALYSIS")
    print(f"{'=' * 70}")
    
    # Time distribution
    print(f"\n  ⏰ Posting Time Distribution (UTC):")
    by_hour = defaultdict(lambda: defaultdict(int))
    for p in posts:
        if p["scheduled_time"]:
            hour = p["scheduled_time"].hour
            by_hour[hour][p["platform"]] += 1
    
    for hour in sorted(by_hour.keys()):
        platforms = by_hour[hour]
        total = sum(platforms.values())
        bar = "█" * min(total, 20)
        est_hour = (hour - 5) % 24
        am_pm = "AM" if est_hour < 12 else "PM"
        est_display = est_hour if est_hour <= 12 else est_hour - 12
        if est_display == 0:
            est_display = 12
        print(f"    {hour:02d}:00 UTC ({est_display:2d}{am_pm} EST) {bar:20s} {total}")
    
    # Platform-specific timing analysis
    for platform in sorted(set(p["platform"] for p in posts)):
        plat_posts = [p for p in posts if p["platform"] == platform]
        if platform in OPTIMAL_WINDOWS:
            windows = OPTIMAL_WINDOWS[platform]
            prime_count = 0
            avoid_count = 0
            for p in plat_posts:
                if p["scheduled_time"]:
                    h = p["scheduled_time"].hour
                    for start, end in windows.get("prime", []):
                        if start <= h < (end if end > start else 24):
                            prime_count += 1
                    for start, end in windows.get("avoid", []):
                        if start <= h < end:
                            avoid_count += 1
            
            print(f"\n  📱 {platform.upper()} Timing:")
            print(f"    Prime time posts:  {prime_count}/{len(plat_posts)} ({prime_count*100//len(plat_posts)}%)")
            if avoid_count:
                print(f"    ⚠️  Off-hours posts: {avoid_count} (consider rescheduling)")
    
    # Caption length analysis
    print(f"\n  📝 Caption Analysis:")
    for platform in sorted(set(p["platform"] for p in posts)):
        plat_posts = [p for p in posts if p["platform"] == platform]
        cap_lens = [len(p["caption"]) for p in plat_posts if p["caption"]]
        if cap_lens:
            avg = sum(cap_lens) // len(cap_lens)
            print(f"    {platform:12s} avg {avg:,} chars (min {min(cap_lens):,}, max {max(cap_lens):,})")
    
    # Cross-posting analysis
    print(f"\n  🔄 Cross-Posting Analysis:")
    by_media = defaultdict(list)
    for p in posts:
        if p["media_path"]:
            by_media[p["media_path"]].append(p["platform"])
    
    single_platform = sum(1 for platforms in by_media.values() if len(platforms) == 1)
    multi_platform = sum(1 for platforms in by_media.values() if len(platforms) > 1)
    print(f"    Unique videos:      {len(by_media)}")
    print(f"    Single platform:    {single_platform}")
    print(f"    Cross-posted:       {multi_platform}")
    
    if single_platform > 0:
        print(f"\n    💡 {single_platform} videos only on 1 platform. Consider cross-posting to maximize reach.")
    
    # Suggestions
    print(f"\n  💡 Suggestions:")
    suggestions = []
    
    daily_counts = defaultdict(int)
    for p in posts:
        if p["scheduled_time"]:
            date = str(p["scheduled_time"])[:10]
            daily_counts[date] += 1
    
    heavy_days = [(d, c) for d, c in daily_counts.items() if c > 12]
    if heavy_days:
        suggestions.append(f"  • {len(heavy_days)} day(s) with >12 posts. Consider spreading out.")
    
    light_days = [(d, c) for d, c in daily_counts.items() if c < 3]
    if light_days:
        suggestions.append(f"  • {len(light_days)} day(s) with <3 posts. Add more content for consistency.")
    
    if single_platform > multi_platform:
        suggestions.append(f"  • Most videos only on 1 platform. Run schedule_videos.py with --platform youtube,tiktok,instagram")
    
    no_tags = sum(1 for p in posts if not p["hashtags"])
    if no_tags > 0:
        suggestions.append(f"  • {no_tags} posts missing hashtags. Use --auto-hashtags or provide a metadata file.")
    
    if suggestions:
        for s in suggestions:
            print(f"  {s}")
    else:
        print(f"    ✅ Schedule looks well-optimized!")


def cmd_find_slots(args):
    """Find optimal time slots for new videos."""
    engine = get_engine()
    posts = query_posts(engine, "status = 'scheduled'")
    
    platform = args.platform or "youtube"
    count = args.count or 5
    
    print(f"\n{'=' * 70}")
    print(f"  🔍 FINDING {count} OPTIMAL SLOTS FOR {platform.upper()}")
    print(f"{'=' * 70}")
    
    # Build occupancy map
    occupied = defaultdict(set)  # date -> set of hours
    for p in posts:
        if p["scheduled_time"] and p["platform"] == platform:
            date = str(p["scheduled_time"])[:10]
            hour = p["scheduled_time"].hour
            occupied[date].add(hour)
    
    # Find available slots starting from tomorrow
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    prime_hours = [h for start_h, end_h in OPTIMAL_WINDOWS.get(platform, {}).get("prime", [])
                   for h in range(start_h, end_h if end_h > start_h else 24)]
    good_hours = [h for start_h, end_h in OPTIMAL_WINDOWS.get(platform, {}).get("good", [])
                  for h in range(start_h, end_h if end_h > start_h else 24)]
    
    available = []
    safe_daily = PLATFORM_DAILY_SAFE.get(platform, 3)
    
    for day_offset in range(60):  # Look 60 days ahead
        date = start + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")
        used_hours = occupied.get(date_str, set())
        daily_count = len(used_hours)
        
        if daily_count >= safe_daily:
            continue
        
        # Try prime hours first, then good hours
        for hour in prime_hours + good_hours:
            if hour not in used_hours:
                slot_time = date.replace(hour=hour, minute=0)
                available.append({
                    "time": slot_time,
                    "date": date_str,
                    "hour": hour,
                    "quality": "🟢 prime" if hour in prime_hours else "🟡 good",
                    "daily_load": daily_count + 1,
                })
                used_hours.add(hour)
                daily_count += 1
                
                if len(available) >= count:
                    break
        
        if len(available) >= count:
            break
    
    if not available:
        print(f"  ❌ No available slots found in the next 60 days!")
        return
    
    print(f"\n  Available slots:")
    for i, slot in enumerate(available[:count]):
        est_hour = (slot["hour"] - 5) % 24
        am_pm = "AM" if est_hour < 12 else "PM"
        est_display = est_hour if est_hour <= 12 else est_hour - 12
        if est_display == 0:
            est_display = 12
        
        print(f"    [{i+1}] {slot['date']} {slot['hour']:02d}:00 UTC "
              f"({est_display}{am_pm} EST) {slot['quality']} "
              f"(day load: {slot['daily_load']}/{safe_daily})")
    
    print(f"\n  💡 Use these slots with schedule_videos.py:")
    first_slot = available[0]
    print(f"     python schedule_videos.py /path/to/videos \\")
    print(f"       --platform {platform} --start \"{first_slot['date']} {first_slot['hour']:02d}:00\"")


def cmd_upcoming(args):
    """Show what's publishing soon."""
    engine = get_engine()
    days = args.days or 2
    
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    
    posts = query_posts(
        engine,
        "scheduled_time >= :now AND scheduled_time <= :end AND status = 'scheduled'",
        {"now": now, "end": end}
    )
    
    if not posts:
        print(f"📭 No posts in the next {days} day(s).")
        return
    
    print(f"\n{'=' * 70}")
    print(f"  ⏰ UPCOMING POSTS (next {days} day(s) — {len(posts)} total)")
    print(f"{'=' * 70}")
    
    current_date = None
    for p in posts:
        date_str = str(p["scheduled_time"])[:10]
        if date_str != current_date:
            current_date = date_str
            print(f"\n  📆 {date_str}:")
        
        time_str = str(p["scheduled_time"])[11:16]
        has_media = "✅" if p["media_path"] and Path(p["media_path"]).exists() else "❌"
        has_caption = "📝" if p["caption"] and len(p["caption"]) > 50 else "⚠️"
        
        print(f"    {time_str} UTC | {p['platform']:10s} | {has_media} {has_caption} | "
              f"{(p['title'] or 'Untitled')[:40]}")
    
    # Readiness check
    not_ready = [p for p in posts if not p["media_path"] or not Path(p["media_path"]).exists()]
    if not_ready:
        print(f"\n  ⚠️  {len(not_ready)} post(s) missing media files — WILL FAIL:")
        for p in not_ready:
            print(f"    {p['platform']:10s} | {(p['title'] or '?')[:40]}")


def cmd_clear(args):
    """Clear scheduled posts with confirmation."""
    from sqlalchemy import text
    engine = get_engine()
    
    where_parts = ["1=1"]
    params = {}
    
    if args.platform:
        where_parts.append("platform = :platform")
        params["platform"] = args.platform
    
    status = args.status or "draft"
    where_parts.append("status = :status")
    params["status"] = status
    
    where = " AND ".join(where_parts)
    posts = query_posts(engine, where, params)
    
    if not posts:
        print(f"📭 No matching posts found.")
        return
    
    print(f"\n⚠️  About to DELETE {len(posts)} posts:")
    for p in posts[:10]:
        print(f"  {p['platform']:10s} | {p['status']:10s} | {(p['title'] or '?')[:40]}")
    if len(posts) > 10:
        print(f"  ... and {len(posts) - 10} more")
    
    confirm = input(f"\nType 'yes' to confirm deletion: ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return
    
    with engine.begin() as conn:
        result = conn.execute(text(f"""
            DELETE FROM scheduled_posts WHERE {where}
        """), params)
        print(f"✅ Deleted {result.rowcount} posts.")


def cmd_shift(args):
    """Shift all scheduled times for a platform."""
    from sqlalchemy import text
    engine = get_engine()
    
    platform = args.platform
    hours = args.hours
    
    if not platform:
        print("❌ --platform required")
        return
    
    posts = query_posts(engine, "platform = :platform AND status = 'scheduled'", {"platform": platform})
    
    if not posts:
        print(f"📭 No scheduled {platform} posts found.")
        return
    
    direction = "forward" if hours > 0 else "backward"
    print(f"\n⏰ Shifting {len(posts)} {platform} posts {abs(hours)}h {direction}")
    print(f"   Before: {str(posts[0]['scheduled_time'])[:16]} → {str(posts[-1]['scheduled_time'])[:16]}")
    
    new_first = posts[0]["scheduled_time"] + timedelta(hours=hours)
    new_last = posts[-1]["scheduled_time"] + timedelta(hours=hours)
    print(f"   After:  {str(new_first)[:16]} → {str(new_last)[:16]}")
    
    confirm = input(f"\nType 'yes' to confirm: ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return
    
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE scheduled_posts 
            SET scheduled_time = scheduled_time + :interval,
                updated_at = NOW()
            WHERE platform = :platform AND status = 'scheduled'
        """), {"interval": timedelta(hours=hours), "platform": platform})
    
    print(f"✅ Shifted {len(posts)} posts by {hours}h")


def cmd_export(args):
    """Export schedule to JSON."""
    engine = get_engine()
    posts = query_posts(engine, "status IN ('scheduled', 'published')")
    
    output = args.output or f"schedule_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    export_data = []
    for p in posts:
        export_data.append({
            "id": p["id"],
            "title": p["title"],
            "platform": p["platform"],
            "status": p["status"],
            "scheduled_time": p["scheduled_time"].isoformat() if p["scheduled_time"] else None,
            "media_path": p["media_path"],
            "blotato_account_id": p["blotato_account_id"],
            "account_username": p["account_username"],
            "caption_length": len(p["caption"]) if p["caption"] else 0,
            "hashtag_count": len(p["hashtags"]) if p["hashtags"] else 0,
            "has_thumbnail": bool(p["thumbnail_url"]),
        })
    
    with open(output, "w") as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Exported {len(export_data)} posts to {output}")


def cmd_accounts(args):
    """Show account posting stats."""
    engine = get_engine()
    posts = query_posts(engine, "1=1")
    
    print(f"\n{'=' * 70}")
    print(f"  👤 ACCOUNT POSTING STATS")
    print(f"{'=' * 70}")
    
    by_account = defaultdict(lambda: {"scheduled": 0, "published": 0, "failed": 0, "platform": "", "username": ""})
    for p in posts:
        key = f"{p['blotato_account_id']}:{p['platform']}"
        by_account[key]["platform"] = p["platform"]
        by_account[key]["username"] = p["account_username"] or "?"
        by_account[key]["blotato_id"] = p["blotato_account_id"] or "?"
        status = p["status"]
        if status in by_account[key]:
            by_account[key][status] += 1
    
    for key in sorted(by_account.keys()):
        info = by_account[key]
        total = info["scheduled"] + info["published"] + info["failed"]
        print(f"\n  {info['platform']:10s} @{info['username']} (ID: {info.get('blotato_id', '?')})")
        print(f"    Scheduled: {info['scheduled']} | Published: {info['published']} | Failed: {info['failed']} | Total: {total}")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Content Planner — Strategic scheduling analysis and planning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  overview      Full schedule overview with gap analysis
  analyze       Strategic analysis with suggestions
  find-slots    Find optimal time slots for new content
  upcoming      Show upcoming posts (next N days)
  clear         Clear posts by status/platform
  shift         Shift scheduled times by N hours
  export        Export schedule to JSON
  accounts      Account posting stats
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # overview
    sub = subparsers.add_parser("overview", help="Full schedule overview")
    
    # analyze
    sub = subparsers.add_parser("analyze", help="Strategic analysis")
    
    # find-slots
    sub = subparsers.add_parser("find-slots", help="Find optimal time slots")
    sub.add_argument("--count", "-n", type=int, default=5, help="Number of slots to find")
    sub.add_argument("--platform", "-p", default="youtube", help="Platform (default: youtube)")
    
    # upcoming
    sub = subparsers.add_parser("upcoming", help="Show upcoming posts")
    sub.add_argument("--days", "-d", type=int, default=2, help="Days ahead (default: 2)")
    
    # clear
    sub = subparsers.add_parser("clear", help="Clear posts")
    sub.add_argument("--platform", "-p", default=None, help="Filter by platform")
    sub.add_argument("--status", "-s", default="draft", help="Filter by status (default: draft)")
    
    # shift
    sub = subparsers.add_parser("shift", help="Shift scheduled times")
    sub.add_argument("--platform", "-p", required=True, help="Platform to shift")
    sub.add_argument("--hours", type=float, required=True, help="Hours to shift (+/-)")
    
    # export
    sub = subparsers.add_parser("export", help="Export schedule to JSON")
    sub.add_argument("--output", "-o", default=None, help="Output file path")
    
    # accounts
    sub = subparsers.add_parser("accounts", help="Account posting stats")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        "overview": cmd_overview,
        "analyze": cmd_analyze,
        "find-slots": cmd_find_slots,
        "upcoming": cmd_upcoming,
        "clear": cmd_clear,
        "shift": cmd_shift,
        "export": cmd_export,
        "accounts": cmd_accounts,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

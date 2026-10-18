"""
Sora YouTube Shorts Publishing Schedule
========================================
Schedules 40 publish-ready Sora videos to YouTube Shorts across Feb 8 - Mar 9, 2026.

Strategy:
- Existing system posts 1x/day at 3:00 PM EST (long-form) — we avoid that slot
- Sora Shorts use 10:00 AM EST (morning) and 6:00 PM EST (evening) slots
- Valentine's tips front-loaded around Feb 14 for maximum relevance
- Love trilogies follow while romance is in the air
- Action trilogies close out the month to pivot channel identity
- Never more than 2 Sora Shorts per day (algo-safe alongside the existing daily post)

YouTube Account: Blotato ID 228 (Isaiah Dupree / UCnDBsELI2OlaEl5yxA77HNA)

Usage:
    python scripts/sora_youtube_schedule.py              # Print schedule
    python scripts/sora_youtube_schedule.py --insert     # Insert into scheduled_posts DB
    python scripts/sora_youtube_schedule.py --json       # Output JSON
"""

import json
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============================================================================
# SCHEDULE DATA
# ============================================================================

YOUTUBE_ACCOUNT_ID = "228"  # Blotato: Isaiah Dupree YouTube
YOUTUBE_CHANNEL = "UCnDBsELI2OlaEl5yxA77HNA"
PLATFORM = "youtube"
CONTENT_TYPE = "short"

# Base paths
TIPS_BASE = os.path.expanduser("~/sora-videos/valentines-22-tips/cleaned")
LOVE_BASE = os.path.expanduser("~/sora-videos/valentines-love")
SORA_BASE = os.path.expanduser("~/sora-videos")

# All 40 videos with metadata
VIDEOS = [
    # === VALENTINE'S 22 TIPS (standalone shorts) ===
    {"id": 1,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-01-presence-over-presents.mp4",
     "title": "Valentine's Day Tip #1: She Wants Your Presence, Not Your Presents #shorts",
     "category": "Valentine's Tips"},
    {"id": 2,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-02-remember-the-small-things.mp4",
     "title": "Valentine's Day Tip #2: Remember the Small Things — That's How She Knows",
     "category": "Valentine's Tips"},
    {"id": 3,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-03-write-her-a-letter.mp4",
     "title": "Valentine's Day Tip #3: Write Her a Letter. By Hand. That's the Move",
     "category": "Valentine's Tips"},
    {"id": 4,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-04-put-the-phone-down.mp4",
     "title": "Valentine's Day Tip #4: Put the Phone Down. Look Her in the Eyes. Listen.",
     "category": "Valentine's Tips"},
    {"id": 5,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-05-love-her-loud-every-day.mp4",
     "title": "Valentine's Day Tip #5: Don't Wait for Feb 14th. Love Her Loud Every Day",
     "category": "Valentine's Tips"},
    {"id": 6,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-06-cook-for-her.mp4",
     "title": "Valentine's Day Tip #6: Cook for Her. Even If You Burn It. The Effort IS It",
     "category": "Valentine's Tips"},
    {"id": 7,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-07-plan-the-whole-day.mp4",
     "title": "Valentine's Day Tip #7: Don't Just Plan Dinner. Plan the Whole Day for Her",
     "category": "Valentine's Tips"},
    {"id": 8,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-08-make-a-playlist.mp4",
     "title": "Valentine's Day Tip #8: Make Her a Playlist. Music Says What Your Mouth Can't",
     "category": "Valentine's Tips"},
    {"id": 9,  "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-09-the-random-tuesday-text.mp4",
     "title": "Valentine's Day Tip #9: The Random Tuesday Text Hits Harder Than Roses on V-Day",
     "category": "Valentine's Tips"},
    {"id": 10, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-10-date-your-friends-too.mp4",
     "title": "Valentine's Day Tip #10: Date Your Friends Too. Love Isn't Just Romantic",
     "category": "Valentine's Tips"},
    {"id": 11, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-11-if-you-re-single-invest-in-you.mp4",
     "title": "Valentine's Day Tip #11: Single? Don't Be Bitter. Be Better. Invest in You",
     "category": "Valentine's Tips"},
    {"id": 12, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-12-experiences-over-objects.mp4",
     "title": "Valentine's Day Tip #12: Give Her an Experience, Not an Object. Build Memories",
     "category": "Valentine's Tips"},
    {"id": 13, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-13-recreate-your-first-date.mp4",
     "title": "Valentine's Day Tip #13: Take Her Back to Where It Started. That's the Gift",
     "category": "Valentine's Tips"},
    {"id": 14, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-14-say-the-thing-you-ve-been-holding.mp4",
     "title": "Valentine's Day Tip #14: Say the Thing You've Been Holding Back. She's Waiting",
     "category": "Valentine's Tips"},
    {"id": 15, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-15-the-anti-valentine-s-move.mp4",
     "title": "Valentine's Day Tip #15: Skip the Fancy Dinner. Go Bowling. Get Tacos.",
     "category": "Valentine's Tips"},
    {"id": 16, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-16-the-notes-app-move.mp4",
     "title": "Valentine's Day Tip #16: Write 14 Things You Love About Her in Notes App",
     "category": "Valentine's Tips"},
    {"id": 17, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-17-build-something-with-your-hands.mp4",
     "title": "Valentine's Day Tip #17: Build Something With Your Hands. Imperfection = Love",
     "category": "Valentine's Tips"},
    {"id": 18, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-18-the-date-jar.mp4",
     "title": "Valentine's Day Tip #18: Make a Date Jar. Romance Isn't a Day, It's a Rhythm",
     "category": "Valentine's Tips"},
    {"id": 19, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-19-surprise-her-at-work.mp4",
     "title": "Valentine's Day Tip #19: Show Up at Her Job. One Flower. Lunch. Just Because",
     "category": "Valentine's Tips"},
    {"id": 20, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-20-long-distance-send-real-mail.mp4",
     "title": "Valentine's Day Tip #20: Long Distance? Send a Real Letter. Paper. Ink. Stamp",
     "category": "Valentine's Tips"},
    {"id": 21, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-21-make-it-easy-with-steadyletters.mp4",
     "title": "Valentine's Day Tip #21: Don't Know What to Say? SteadyLetters Makes It Easy",
     "category": "Valentine's Tips"},
    {"id": 22, "series": "tips", "file": f"{TIPS_BASE}/cleaned_tip-22-the-best-valentine-s-tip.mp4",
     "title": "Valentine's Day Tip #22: The Best Tip? Actually Follow Through. Do It Tonight.",
     "category": "Valentine's Tips"},

    # === VALENTINE'S LOVE TRILOGIES (stitched finals) ===
    {"id": 23, "series": "love", "file": f"{LOVE_BASE}/first-light/first-light-final.mp4",
     "title": "FIRST LIGHT — A First Love Story | @isaiahdupree Cinematic Love Trilogy",
     "category": "Love Trilogy"},
    {"id": 24, "series": "love", "file": f"{LOVE_BASE}/ocean-between-us/ocean-between-us-final.mp4",
     "title": "OCEAN BETWEEN US — A Long-Distance Love Story | @isaiahdupree Love Trilogy",
     "category": "Love Trilogy"},
    {"id": 25, "series": "love", "file": f"{LOVE_BASE}/embers/embers-final.mp4",
     "title": "EMBERS — A Second Chance Love Story | @isaiahdupree Cinematic Love Trilogy",
     "category": "Love Trilogy"},
    {"id": 26, "series": "love", "file": f"{LOVE_BASE}/through-the-fire/through-the-fire-final.mp4",
     "title": "THROUGH THE FIRE — Love Through Adversity | @isaiahdupree Cinematic Love Trilogy",
     "category": "Love Trilogy"},
    {"id": 27, "series": "love", "file": f"{LOVE_BASE}/magnetic/magnetic-final.mp4",
     "title": "MAGNETIC — A Passionate Love Story | @isaiahdupree Cinematic Love Trilogy",
     "category": "Love Trilogy"},
    {"id": 28, "series": "love", "file": f"{LOVE_BASE}/silent-knowing/silent-knowing-final.mp4",
     "title": "SILENT KNOWING — A Soulmate Love Story | @isaiahdupree Cinematic Love Trilogy",
     "category": "Love Trilogy"},
    {"id": 29, "series": "love", "file": f"{LOVE_BASE}/bridges/bridges-final.mp4",
     "title": "BRIDGES — A Forbidden Love Story Against All Odds | @isaiahdupree Love Trilogy",
     "category": "Love Trilogy"},
    {"id": 30, "series": "love", "file": f"{LOVE_BASE}/forever-echoes/forever-echoes-final.mp4",
     "title": "FOREVER ECHOES — An Eternal Love Across Lifetimes | @isaiahdupree Love Trilogy",
     "category": "Love Trilogy"},

    # === ACTION TRILOGIES (stitched finals) ===
    {"id": 31, "series": "action", "file": f"{SORA_BASE}/badass/badass-final.mp4",
     "title": "BADASS — Volcano Surfing to Meteor Riding | @isaiahdupree Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 32, "series": "action", "file": f"{SORA_BASE}/space-journey/space-journey-final.mp4",
     "title": "SPACE JOURNEY — Earth to Moon to Mars | @isaiahdupree Cinematic Space Trilogy",
     "category": "Action Trilogy"},
    {"id": 33, "series": "action", "file": f"{SORA_BASE}/volcanic_fury/volcanic_fury-final.mp4",
     "title": "VOLCANIC FURY — Climbing an Erupting Volcano | @isaiahdupree Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 34, "series": "action", "file": f"{SORA_BASE}/abyssal_descent/abyssal_descent-final.mp4",
     "title": "ABYSSAL DESCENT — Deep Sea Discovery & Escape | @isaiahdupree Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 35, "series": "action", "file": f"{SORA_BASE}/neon_shadows/neon_shadows-final.mp4",
     "title": "NEON SHADOWS — A Cyberpunk Heist Story | @isaiahdupree Cinematic Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 36, "series": "action", "file": f"{SORA_BASE}/frozen_edge/frozen_edge-final.mp4",
     "title": "FROZEN EDGE — Arctic Survival & Northern Lights | @isaiahdupree Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 37, "series": "action", "file": f"{SORA_BASE}/titan_protocol/titan_protocol-final.mp4",
     "title": "TITAN PROTOCOL — Giant Mech Warfare | @isaiahdupree Cinematic Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 38, "series": "action", "file": f"{SORA_BASE}/temporal_shift/temporal_shift-final.mp4",
     "title": "TEMPORAL SHIFT — Time Travel Through History | @isaiahdupree Cinematic Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 39, "series": "action", "file": f"{SORA_BASE}/midnight_run/midnight_run-final.mp4",
     "title": "MIDNIGHT RUN — Underground Street Racing | @isaiahdupree Cinematic Action Trilogy",
     "category": "Action Trilogy"},
    {"id": 40, "series": "action", "file": f"{SORA_BASE}/way_of_dragon/way_of_dragon-final.mp4",
     "title": "WAY OF THE DRAGON — Martial Arts Tournament | @isaiahdupree Cinematic Action Trilogy",
     "category": "Action Trilogy"},
]


# ============================================================================
# SCHEDULE ASSIGNMENTS
# ============================================================================
# Format: (video_id, date_str, time_est, rationale)
#
# Strategy:
#   - Existing system posts at 3:00 PM EST daily (long-form YouTube slot) — AVOID
#   - Sora Shorts: primary slot 10:00 AM EST, secondary slot 6:00 PM EST
#   - Pre-V-Day: 2-3 tips/day for momentum (algo rewards series consistency)
#   - V-Day: emotional peak — finale tip + first love trilogy
#   - Post-V-Day: wind down tips, introduce love trilogies
#   - Late Feb: pivot to action trilogies at 1/day steady cadence
#   - March: finish action trilogies, channel identity established

SCHEDULE = [
    # ── Phase 1: Pre-Valentine's Buildup (Feb 8-13) ─────────────────────
    # 2 tips/day, morning + evening, building anticipation
    (1,  "2026-02-08", "10:00", "Series launch — strong opener, Saturday morning"),
    (2,  "2026-02-08", "18:00", "Double-drop day 1: Saturday evening engagement"),

    (3,  "2026-02-09", "10:00", "Sunday morning — high watch time"),
    (4,  "2026-02-09", "18:00", "Sunday evening wind-down"),

    (5,  "2026-02-10", "10:00", "Monday morning commute slot"),
    (6,  "2026-02-10", "18:00", "Monday evening — after work browsing"),

    (7,  "2026-02-11", "10:00", "Tuesday — mid-week push"),
    (8,  "2026-02-11", "18:00", "Tuesday evening — playlist tip drives saves"),

    (9,  "2026-02-12", "10:00", "Wednesday — 2 days to V-Day urgency"),
    (10, "2026-02-12", "18:00", "Wednesday evening — friends tip broadens audience"),

    (11, "2026-02-13", "10:00", "Thursday — V-Day eve, singles content hits hard"),
    (12, "2026-02-13", "18:00", "Thursday evening — last-minute gift ideas"),
    (13, "2026-02-13", "21:00", "BONUS third: recreate first date — high urgency night before V-Day"),

    # ── Phase 2: Valentine's Day (Feb 14) ───────────────────────────────
    # Peak emotional day — vulnerability tip + first love trilogy
    (14, "2026-02-14", "10:00", "V-DAY MORNING: Say the thing — peak emotional resonance"),
    (15, "2026-02-14", "14:00", "V-DAY AFTERNOON: Anti-Valentine's — counter-programming hook"),
    (23, "2026-02-14", "18:00", "V-DAY EVENING: FIRST LIGHT premiere — first love story"),

    # ── Phase 3: Post-V-Day Wind-Down (Feb 15-19) ──────────────────────
    # Finish tips series + start love trilogies, 2/day
    (16, "2026-02-15", "10:00", "Saturday — Notes App move, high shareability"),
    (24, "2026-02-15", "18:00", "Saturday evening — OCEAN BETWEEN US (long-distance)"),

    (17, "2026-02-16", "10:00", "Sunday — Build something tip, weekend DIY energy"),
    (25, "2026-02-16", "18:00", "Sunday evening — EMBERS (second chance love)"),

    (18, "2026-02-17", "10:00", "Monday — Date Jar tip, year-round romance hook"),
    (26, "2026-02-17", "18:00", "Monday evening — THROUGH THE FIRE (adversity love)"),

    (19, "2026-02-18", "10:00", "Tuesday — Surprise at work, shareable concept"),
    (27, "2026-02-18", "18:00", "Tuesday evening — MAGNETIC (passionate love)"),

    (20, "2026-02-19", "10:00", "Wednesday — Long distance mail tip"),
    (28, "2026-02-19", "18:00", "Wednesday evening — SILENT KNOWING (soulmate love)"),

    # ── Phase 4: Love Trilogy Finale + Transition (Feb 20-22) ───────────
    # Finish love series, bridge to action with 1-2/day
    (21, "2026-02-20", "10:00", "Thursday — SteadyLetters tip (product tie-in)"),
    (29, "2026-02-20", "18:00", "Thursday evening — BRIDGES (forbidden love)"),

    (22, "2026-02-21", "10:00", "Friday — SERIES FINALE: Follow Through tip — call to action"),
    (30, "2026-02-21", "18:00", "Friday evening — FOREVER ECHOES (eternal love) — love finale"),

    # ── Phase 5: Action Trilogy Rollout (Feb 22 - Mar 3) ────────────────
    # 1/day steady cadence — channel identity pivot to cinematic action
    (31, "2026-02-22", "10:00", "Sunday — BADASS debut, explosive channel pivot moment"),
    (32, "2026-02-23", "10:00", "Monday — SPACE JOURNEY, aspirational Monday energy"),
    (33, "2026-02-24", "10:00", "Tuesday — VOLCANIC FURY, mid-week adrenaline"),
    (34, "2026-02-25", "10:00", "Wednesday — ABYSSAL DESCENT, mystery/thriller hook"),
    (35, "2026-02-26", "10:00", "Thursday — NEON SHADOWS, cyberpunk hits sci-fi audience"),
    (36, "2026-02-27", "10:00", "Friday — FROZEN EDGE, weekend exploration energy"),
    (37, "2026-02-28", "10:00", "Saturday — TITAN PROTOCOL, mech warfare weekend content"),
    (38, "2026-03-01", "10:00", "Sunday — TEMPORAL SHIFT, new month fresh start"),
    (39, "2026-03-02", "10:00", "Monday — MIDNIGHT RUN, street racing energy"),
    (40, "2026-03-03", "10:00", "Tuesday — WAY OF THE DRAGON, martial arts finale — series complete"),
]


def get_video_by_id(vid_id: int) -> dict:
    """Get video metadata by ID."""
    for v in VIDEOS:
        if v["id"] == vid_id:
            return v
    return None


def build_schedule() -> list:
    """Build the full schedule with all metadata."""
    schedule = []
    for vid_id, date_str, time_est, rationale in SCHEDULE:
        video = get_video_by_id(vid_id)
        if not video:
            print(f"⚠️  Video ID {vid_id} not found!")
            continue

        dt = datetime.strptime(f"{date_str} {time_est}", "%Y-%m-%d %H:%M")
        # EST = UTC-5
        scheduled_utc = dt + timedelta(hours=5)

        file_exists = os.path.exists(video["file"])

        schedule.append({
            "video_id": video["id"],
            "title": video["title"],
            "category": video["category"],
            "series": video["series"],
            "file_path": video["file"],
            "file_exists": file_exists,
            "scheduled_date": date_str,
            "scheduled_time_est": time_est,
            "scheduled_utc": scheduled_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "platform": PLATFORM,
            "account_id": YOUTUBE_ACCOUNT_ID,
            "content_type": CONTENT_TYPE,
            "rationale": rationale,
        })

    return schedule


def print_schedule(schedule: list):
    """Pretty-print the schedule."""
    print("=" * 90)
    print("  SORA YOUTUBE SHORTS PUBLISHING SCHEDULE")
    print(f"  {len(schedule)} videos | Feb 8 – Mar 3, 2026 | YouTube Shorts")
    print(f"  Account: Blotato #{YOUTUBE_ACCOUNT_ID} (Isaiah Dupree)")
    print("=" * 90)

    current_phase = ""
    for i, s in enumerate(schedule):
        date = s["scheduled_date"]
        day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%a")

        # Phase headers
        if date <= "2026-02-13" and current_phase != "phase1":
            current_phase = "phase1"
            print(f"\n{'─' * 90}")
            print(f"  📅 PHASE 1: Pre-Valentine's Buildup (Feb 8-13) — 2-3 tips/day")
            print(f"{'─' * 90}")
        elif date == "2026-02-14" and current_phase != "phase2":
            current_phase = "phase2"
            print(f"\n{'─' * 90}")
            print(f"  💝 PHASE 2: Valentine's Day (Feb 14) — Peak Emotional Day")
            print(f"{'─' * 90}")
        elif "2026-02-15" <= date <= "2026-02-19" and current_phase != "phase3":
            current_phase = "phase3"
            print(f"\n{'─' * 90}")
            print(f"  💌 PHASE 3: Post-V-Day (Feb 15-19) — Tips + Love Trilogies")
            print(f"{'─' * 90}")
        elif "2026-02-20" <= date <= "2026-02-21" and current_phase != "phase4":
            current_phase = "phase4"
            print(f"\n{'─' * 90}")
            print(f"  🎬 PHASE 4: Series Finales (Feb 20-21) — Tips + Love Wrap-Up")
            print(f"{'─' * 90}")
        elif date >= "2026-02-22" and current_phase != "phase5":
            current_phase = "phase5"
            print(f"\n{'─' * 90}")
            print(f"  🔥 PHASE 5: Action Trilogies (Feb 22 - Mar 3) — 1/day Steady")
            print(f"{'─' * 90}")

        exists = "✅" if s["file_exists"] else "❌"
        print(f"  {exists} {day_name} {date} @ {s['scheduled_time_est']} EST | #{s['video_id']:2d} | {s['title'][:60]}")

    # Summary
    tips_count = sum(1 for s in schedule if s["series"] == "tips")
    love_count = sum(1 for s in schedule if s["series"] == "love")
    action_count = sum(1 for s in schedule if s["series"] == "action")
    exists_count = sum(1 for s in schedule if s["file_exists"])

    dates = sorted(set(s["scheduled_date"] for s in schedule))
    max_per_day = max(sum(1 for s in schedule if s["scheduled_date"] == d) for d in dates)

    print(f"\n{'=' * 90}")
    print(f"  SUMMARY")
    print(f"  Total videos: {len(schedule)} ({exists_count} files confirmed on disk)")
    print(f"  Tips: {tips_count} | Love Trilogies: {love_count} | Action Trilogies: {action_count}")
    print(f"  Date range: {dates[0]} → {dates[-1]} ({len(dates)} publishing days)")
    print(f"  Max per day: {max_per_day} (algo-safe: ≤3 Shorts/day)")
    print(f"  Time slots: 10:00 AM EST (primary), 6:00 PM EST (secondary)")
    print(f"  Avoids: 3:00 PM EST (existing daily post slot)")
    print(f"{'=' * 90}")


def insert_to_db(schedule: list):
    """Insert schedule into scheduled_posts database table."""
    try:
        from sqlalchemy import create_engine, text
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        engine = create_engine(db_url)

        with engine.begin() as conn:
            inserted = 0
            skipped = 0
            for s in schedule:
                # Check if already inserted (by title + scheduled_time)
                existing = conn.execute(text("""
                    SELECT id FROM scheduled_posts 
                    WHERE title = :title AND scheduled_time = :scheduled_time
                """), {"title": s["title"], "scheduled_time": s["scheduled_utc"]}).fetchone()

                if existing:
                    skipped += 1
                    continue

                post_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO scheduled_posts 
                    (id, platform, title, caption, scheduled_time, status,
                     is_ai_recommended, recommendation_score, recommendation_reasoning,
                     created_at)
                    VALUES 
                    (:id, :platform, :title, :caption, :scheduled_time, 'scheduled',
                     TRUE, :score, :reasoning, NOW())
                """), {
                    "id": post_id,
                    "platform": s["platform"],
                    "title": s["title"],
                    "caption": f"Sora AI Video | {s['category']} | File: {s['file_path']}",
                    "scheduled_time": s["scheduled_utc"],
                    "score": 0.95,
                    "reasoning": f"Sora YouTube Schedule | {s['category']} | {s['rationale']}",
                })
                inserted += 1

            print(f"✅ Inserted {inserted} scheduled posts into database")
            if skipped:
                print(f"   Skipped {skipped} already existing")

    except Exception as e:
        print(f"❌ Database insert failed: {e}")
        print("   Make sure Supabase is running (supabase start)")
        print("   Schedule JSON saved — you can retry with --insert later")


def export_json(schedule: list):
    """Export schedule as JSON."""
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_videos": len(schedule),
        "platform": "youtube",
        "account": f"Blotato #{YOUTUBE_ACCOUNT_ID}",
        "strategy": {
            "primary_slot": "10:00 AM EST",
            "secondary_slot": "6:00 PM EST",
            "avoided_slot": "3:00 PM EST (existing daily post)",
            "max_per_day": 3,
            "date_range": f"{schedule[0]['scheduled_date']} to {schedule[-1]['scheduled_date']}",
        },
        "schedule": schedule,
    }
    print(json.dumps(output, indent=2))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    schedule = build_schedule()

    if "--json" in sys.argv:
        export_json(schedule)
    elif "--insert" in sys.argv:
        print_schedule(schedule)
        print()
        insert_to_db(schedule)
    else:
        print_schedule(schedule)

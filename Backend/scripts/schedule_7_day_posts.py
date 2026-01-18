#!/usr/bin/env python3
"""
Schedule 7-Day Posts Using Narrative Builder

This script:
1. Finds approved, analyzed, unposted/unscheduled videos
2. Uses the narrative builder to select videos matching content pillars
3. Schedules across all platforms using different Blotato accounts
4. Prevents duplicate scheduling of the same video
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from loguru import logger

# Load environment variables first
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Define BlotatoAccount locally to avoid config import issues
@dataclass
class BlotatoAccount:
    blotato_id: int
    platform: str
    username: str
    display_name: Optional[str] = None
    is_active: bool = True


# Blotato accounts (copied from config to avoid import issues)
BLOTATO_ACCOUNTS: List[BlotatoAccount] = [
    # TikTok accounts
    BlotatoAccount(710, "tiktok", "isaiah_dupree", "Isaiah Dupree"),
    BlotatoAccount(243, "tiktok", "the_isaiah_dupree", "The Isaiah Dupree"),
    BlotatoAccount(4508, "tiktok", "dupree_isaiah", "Dupree Isaiah"),
    
    # Instagram accounts
    BlotatoAccount(807, "instagram", "the_isaiah_dupree", "The Isaiah Dupree"),
    BlotatoAccount(670, "instagram", "the_isaiah_dupree_", "The Isaiah Dupree"),
    BlotatoAccount(1369, "instagram", "dupree_isaiah_", "Dupree Isaiah"),
    BlotatoAccount(4508, "instagram", "dupree_isaiah", "Dupree Isaiah"),
    
    # YouTube accounts
    BlotatoAccount(228, "youtube", "UCnDBsELI2OlaEl5yxA77HNA", "Isaiah Dupree"),
    BlotatoAccount(3370, "youtube", "lofi_creator", "lofi creator"),
    
    # Twitter/X accounts
    BlotatoAccount(4151, "twitter", "soursides_is_sour", "Soursides"),
    
    # Threads accounts
    BlotatoAccount(1369, "threads", "dupree_isaiah_", "Dupree Isaiah"),
    BlotatoAccount(4150, "threads", "isaiahdupree75", "Isaiah Dupree"),
    
    # Pinterest accounts
    BlotatoAccount(173, "pinterest", "isaiahdupree33", "Isaiah Dupree"),
    BlotatoAccount(243, "pinterest", "isaiahdupree75", "Isaiah Dupree"),
    
    # LinkedIn accounts
    BlotatoAccount(571, "linkedin", "IsaiahDupree7", "Isaiah Dupree"),
    
    # Facebook accounts
    BlotatoAccount(786, "facebook", "Isaiah Dupree", "Isaiah Dupree"),
    
    # Bluesky accounts
    BlotatoAccount(201, "bluesky", "the_isaiah_dupree_", "The Isaiah Dupree"),
]

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")

# Try to import narrative scheduler, but don't fail if unavailable
try:
    from services.narrative_scheduler.scheduler import NarrativeScheduler
    NARRATIVE_SCHEDULER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Narrative scheduler not available: {e}")
    NARRATIVE_SCHEDULER_AVAILABLE = False
    NarrativeScheduler = None

# Platforms to schedule for (using primary account per platform)
PLATFORM_CONFIG = {
    "tiktok": {
        "posts_per_day": 2,
        "posting_times": ["12:00", "18:00", "21:00"],
        "primary_account_id": 710,  # @isaiah_dupree
    },
    "instagram": {
        "posts_per_day": 2,
        "posting_times": ["09:00", "17:00", "20:00"],
        "primary_account_id": 807,  # @the_isaiah_dupree
    },
    "youtube": {
        "posts_per_day": 1,
        "posting_times": ["14:00"],
        "primary_account_id": 228,  # Isaiah Dupree
    },
    "threads": {
        "posts_per_day": 1,
        "posting_times": ["10:00", "19:00"],
        "primary_account_id": 1369,  # @dupree_isaiah_
    },
    "twitter": {
        "posts_per_day": 1,
        "posting_times": ["11:00", "16:00"],
        "primary_account_id": 4151,  # @soursides_is_sour
    },
}


def get_engine():
    return create_engine(DATABASE_URL)


def get_approved_unscheduled_videos(engine, min_score: int = 50, limit: int = 200) -> List[Dict]:
    """
    Get videos that are:
    - Analyzed with curation_status = 'approved'
    - Not already scheduled
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                v.id,
                v.file_name,
                v.source_uri,
                v.thumbnail_path,
                v.duration_sec,
                va.pre_social_score,
                va.transcript,
                va.topics,
                va.hooks,
                va.tone,
                va.curation_status
            FROM videos v
            JOIN video_analysis va ON va.video_id = v.id
            WHERE va.curation_status = 'approved'
              AND va.pre_social_score >= :min_score
              -- Not already scheduled
              AND NOT EXISTS (
                  SELECT 1 FROM scheduled_posts sp 
                  WHERE (sp.content_id = v.id::text OR sp.clip_id = v.id)
                    AND sp.status IN ('scheduled', 'publishing', 'posted', 'published')
              )
            ORDER BY va.pre_social_score DESC
            LIMIT :limit
        """), {"min_score": min_score, "limit": limit})
        
        videos = []
        for row in result:
            videos.append({
                "id": str(row[0]),
                "file_name": row[1],
                "source_uri": row[2],
                "thumbnail_path": row[3],
                "duration_sec": float(row[4]) if row[4] else None,
                "pre_social_score": int(row[5]) if row[5] else 0,
                "transcript": row[6],
                "topics": list(row[7]) if row[7] else [],
                "hooks": list(row[8]) if row[8] else [],
                "tone": row[9],
                "curation_status": row[10],
            })
        
        return videos


def get_existing_scheduled_video_ids(engine) -> set:
    """Get all video IDs that are already scheduled"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT content_id 
            FROM scheduled_posts 
            WHERE status IN ('pending', 'scheduled', 'publishing', 'posted', 'published')
              AND content_id IS NOT NULL
        """))
        return {row[0] for row in result}


def get_scheduled_transcripts_by_account(engine) -> Dict[str, set]:
    """
    Get transcripts already scheduled per account to prevent duplicate content.
    Returns: {account_id: set of transcript hashes}
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                sp.account_id,
                md5(va.transcript) as transcript_hash
            FROM scheduled_posts sp
            JOIN videos v ON v.id::text = sp.content_id
            JOIN video_analysis va ON va.video_id = v.id
            WHERE sp.status IN ('pending', 'scheduled', 'publishing', 'posted', 'published')
              AND va.transcript IS NOT NULL
              AND LENGTH(va.transcript) > 50
        """))
        
        transcripts_by_account = {}
        for row in result:
            account_id = str(row[0])
            transcript_hash = row[1]
            if account_id not in transcripts_by_account:
                transcripts_by_account[account_id] = set()
            transcripts_by_account[account_id].add(transcript_hash)
        
        return transcripts_by_account


def get_existing_schedules_by_platform(engine, start_date: date, end_date: date) -> Dict[str, Dict[str, int]]:
    """
    Get count of existing scheduled posts per platform per day.
    Returns: {platform: {date_str: count}}
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                platform,
                DATE(COALESCE(scheduled_time, scheduled_at)) as sched_date,
                COUNT(*) as count
            FROM scheduled_posts 
            WHERE status IN ('scheduled', 'publishing')
              AND COALESCE(scheduled_time, scheduled_at) >= :start_date
              AND COALESCE(scheduled_time, scheduled_at) < :end_date
            GROUP BY platform, DATE(COALESCE(scheduled_time, scheduled_at))
        """), {"start_date": start_date, "end_date": end_date + timedelta(days=1)})
        
        schedules = {}
        for row in result:
            platform = row[0].lower()
            date_str = str(row[1])
            count = row[2]
            
            if platform not in schedules:
                schedules[platform] = {}
            schedules[platform][date_str] = count
        
        return schedules


def get_blotato_account_info(account_id: int) -> Optional[BlotatoAccount]:
    """Get Blotato account by ID"""
    for account in BLOTATO_ACCOUNTS:
        if account.blotato_id == account_id:
            return account
    return None


def schedule_post(
    engine,
    video: Dict,
    platform: str,
    account: BlotatoAccount,
    scheduled_datetime: datetime,
    pillar: Optional[str] = None,
    selection_reason: Optional[str] = None,
    scheduled_transcripts: Optional[Dict[str, set]] = None
) -> bool:
    """Create a scheduled post entry with deduplication checks"""
    try:
        with engine.connect() as conn:
            account_id = str(account.blotato_id)
            
            # Check 1: Same video already scheduled for this account
            existing = conn.execute(text("""
                SELECT 1 FROM scheduled_posts 
                WHERE content_id = :content_id 
                  AND account_id = :account_id
                  AND status IN ('pending', 'scheduled', 'publishing', 'posted', 'published')
                LIMIT 1
            """), {"content_id": video["id"], "account_id": account_id}).fetchone()
            
            if existing:
                logger.warning(f"Video {video['id']} already scheduled for account {account_id}, skipping")
                return False
            
            # Check 2: Same transcript already scheduled for this account (prevent duplicate content)
            if video.get("transcript") and len(video.get("transcript", "")) > 50:
                import hashlib
                transcript_hash = hashlib.md5(video["transcript"].encode()).hexdigest()
                
                # Check against in-memory cache first
                if scheduled_transcripts and account_id in scheduled_transcripts:
                    if transcript_hash in scheduled_transcripts[account_id]:
                        logger.warning(f"Video {video['id']} has duplicate transcript for account {account_id}, skipping")
                        return False
                
                # Also check database for existing scheduled posts with same transcript
                dupe_transcript = conn.execute(text("""
                    SELECT 1 FROM scheduled_posts sp
                    JOIN videos v ON v.id::text = sp.content_id
                    JOIN video_analysis va ON va.video_id = v.id
                    WHERE sp.account_id = :account_id
                      AND sp.status IN ('pending', 'scheduled', 'publishing', 'posted', 'published')
                      AND md5(va.transcript) = :transcript_hash
                    LIMIT 1
                """), {"account_id": account_id, "transcript_hash": transcript_hash}).fetchone()
                
                if dupe_transcript:
                    logger.warning(f"Video {video['id']} has duplicate transcript in DB for account {account_id}, skipping")
                    return False
                
                # Add to in-memory cache for current run
                if scheduled_transcripts is not None:
                    if account_id not in scheduled_transcripts:
                        scheduled_transcripts[account_id] = set()
                    scheduled_transcripts[account_id].add(transcript_hash)
            
            # Generate caption from video data
            title = video.get("file_name", "Untitled")
            if video.get("hooks"):
                title = video["hooks"][0] if video["hooks"] else title
            
            # Build caption from topics/hooks
            caption_parts = []
            if video.get("hooks"):
                caption_parts.append(video["hooks"][0])
            if video.get("topics"):
                hashtags = " ".join([f"#{t.replace(' ', '')}" for t in video["topics"][:5]])
                caption_parts.append(hashtags)
            
            caption = "\n\n".join(caption_parts) if caption_parts else title
            
            # Recommendation reasoning
            reasoning = {
                "pillar": pillar,
                "selection_reason": selection_reason,
                "pre_social_score": video.get("pre_social_score"),
                "scheduled_by": "narrative_builder_7day_script",
                "scheduled_at": datetime.now().isoformat()
            }
            
            conn.execute(text("""
                INSERT INTO scheduled_posts (
                    content_id, 
                    title, 
                    caption,
                    hashtags,
                    thumbnail_url,
                    platform, 
                    account_id,
                    account_username,
                    blotato_account_id,
                    scheduled_at,
                    scheduled_time,
                    status, 
                    post_type,
                    recommendation_reasoning,
                    is_ai_recommended,
                    created_at
                ) VALUES (
                    :content_id,
                    :title,
                    :caption,
                    :hashtags,
                    :thumbnail_url,
                    :platform,
                    :account_id,
                    :account_username,
                    :blotato_account_id,
                    :scheduled_at,
                    :scheduled_time,
                    'pending',
                    'reel',
                    :reasoning,
                    TRUE,
                    NOW()
                )
            """), {
                "content_id": video["id"],
                "title": title[:200],
                "caption": caption[:2000],
                "hashtags": json.dumps(video.get("topics", [])[:10]),
                "thumbnail_url": video.get("thumbnail_path"),
                "platform": platform,
                "account_id": str(account.blotato_id),
                "account_username": account.username,
                "blotato_account_id": str(account.blotato_id),
                "scheduled_at": scheduled_datetime,
                "scheduled_time": scheduled_datetime,
                "reasoning": json.dumps(reasoning),
            })
            conn.commit()
            
            logger.info(f"✓ Scheduled {video['id'][:8]}... for {platform}/@{account.username} at {scheduled_datetime}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to schedule video {video['id']}: {e}")
        return False


async def run_narrative_scheduling():
    """Main function to run the 7-day scheduling"""
    
    logger.info("=" * 60)
    logger.info("🗓️  NARRATIVE BUILDER - 7 DAY SCHEDULING")
    logger.info("=" * 60)
    
    engine = get_engine()
    
    # Calculate date range: tomorrow through 7 days from tomorrow
    today = date.today()
    start_date = today + timedelta(days=1)  # Start tomorrow
    end_date = start_date + timedelta(days=6)  # 7 days total
    
    logger.info(f"📅 Scheduling window: {start_date} to {end_date}")
    
    # Get approved, unscheduled videos
    logger.info("🔍 Finding approved, unscheduled videos...")
    videos = get_approved_unscheduled_videos(engine, min_score=50, limit=200)
    logger.info(f"   Found {len(videos)} eligible videos")
    
    if not videos:
        logger.error("❌ No approved, unscheduled videos found!")
        return
    
    # Get already scheduled video IDs
    scheduled_ids = get_existing_scheduled_video_ids(engine)
    logger.info(f"   {len(scheduled_ids)} videos already scheduled (will skip)")
    
    # Filter out already scheduled
    available_videos = [v for v in videos if v["id"] not in scheduled_ids]
    logger.info(f"   {len(available_videos)} videos available for scheduling")
    
    if not available_videos:
        logger.error("❌ All videos are already scheduled!")
        return
    
    # Get existing schedule counts
    existing_schedules = get_existing_schedules_by_platform(engine, start_date, end_date)
    logger.info(f"📊 Existing schedules: {existing_schedules}")
    
    # Try to use narrative scheduler for AI-powered selection
    plan = None
    if NARRATIVE_SCHEDULER_AVAILABLE and NarrativeScheduler:
        try:
            scheduler = NarrativeScheduler()
            logger.info("🤖 Using Narrative Scheduler for AI-powered video selection...")
            
            # Generate plan using narrative scheduler
            plan = await scheduler.generate_7_day_plan(use_defaults=True)
            logger.info(f"   Generated plan with {plan.total_posts} slots")
            logger.info(f"   Reasoning: {plan.justification_summary[:200] if plan.justification_summary else 'N/A'}...")
            
        except Exception as e:
            logger.warning(f"⚠️ Narrative scheduler error: {e}")
            logger.info("   Falling back to score-based selection")
            plan = None
    else:
        logger.info("📊 Using score-based selection (narrative scheduler not available)")
    
    # Load existing scheduled transcripts per account for deduplication
    scheduled_transcripts = get_scheduled_transcripts_by_account(engine)
    logger.info(f"📋 Loaded transcript hashes for {len(scheduled_transcripts)} accounts")
    
    # Schedule posts for each day and platform
    total_scheduled = 0
    video_index = 0
    used_video_ids = set()  # Track videos used in this run
    
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        date_str = str(current_date)
        
        logger.info(f"\n📅 Day {day_offset + 1}: {current_date} ({current_date.strftime('%A')})")
        
        for platform, config in PLATFORM_CONFIG.items():
            # Get existing count for this platform/date
            existing_count = existing_schedules.get(platform, {}).get(date_str, 0)
            posts_needed = config["posts_per_day"] - existing_count
            
            if posts_needed <= 0:
                logger.info(f"   {platform}: Already has {existing_count} posts scheduled")
                continue
            
            # Get account for this platform
            account = get_blotato_account_info(config["primary_account_id"])
            if not account:
                logger.warning(f"   {platform}: No account found for ID {config['primary_account_id']}")
                continue
            
            # Schedule posts for this platform/day
            posting_times = config["posting_times"][:posts_needed]
            
            for time_idx, time_str in enumerate(posting_times):
                if video_index >= len(available_videos):
                    logger.warning(f"   Ran out of videos at day {day_offset + 1}")
                    break
                
                # Find next unused video
                while video_index < len(available_videos):
                    video = available_videos[video_index]
                    video_index += 1
                    
                    if video["id"] not in used_video_ids:
                        break
                else:
                    logger.warning(f"   No more unique videos available")
                    break
                
                # Parse time
                hour, minute = map(int, time_str.split(":"))
                scheduled_dt = datetime.combine(
                    current_date,
                    datetime.strptime(time_str, "%H:%M").time()
                )
                
                # Determine pillar (from plan if available, otherwise from topics)
                pillar = None
                selection_reason = f"Score: {video.get('pre_social_score', 0)}"
                
                if video.get("topics"):
                    pillar = video["topics"][0] if video["topics"] else None
                
                # Schedule the post (with transcript deduplication)
                success = schedule_post(
                    engine=engine,
                    video=video,
                    platform=platform,
                    account=account,
                    scheduled_datetime=scheduled_dt,
                    pillar=pillar,
                    selection_reason=selection_reason,
                    scheduled_transcripts=scheduled_transcripts
                )
                
                if success:
                    total_scheduled += 1
                    used_video_ids.add(video["id"])
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 SCHEDULING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Total posts scheduled: {total_scheduled}")
    logger.info(f"📅 Date range: {start_date} to {end_date}")
    logger.info(f"🎬 Unique videos used: {len(used_video_ids)}")
    
    # Show breakdown by platform
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT platform, COUNT(*) 
            FROM scheduled_posts 
            WHERE status = 'scheduled'
              AND scheduled_time >= :start_date
              AND scheduled_time < :end_date
            GROUP BY platform
        """), {"start_date": start_date, "end_date": end_date + timedelta(days=1)})
        
        logger.info("\n📱 Posts by Platform:")
        for row in result:
            logger.info(f"   {row[0]}: {row[1]} posts")
    
    logger.info("\n✅ Done! Check the Schedule page in the dashboard to review.")


if __name__ == "__main__":
    asyncio.run(run_narrative_scheduling())

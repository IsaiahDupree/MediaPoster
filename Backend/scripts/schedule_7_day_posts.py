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
    logger.error("airtime_required: legacy database scheduling is disabled; use Airtime")
    return False


async def run_narrative_scheduling():
    logger.error("airtime_required: legacy seven-day scheduler is disabled; use Airtime")
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run_narrative_scheduling()) or 0)

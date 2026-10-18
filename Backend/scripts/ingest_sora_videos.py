#!/usr/bin/env python3
"""
Ingest Sora Videos into MediaPoster
- Imports all watermark-removed videos
- Analyzes each (transcription, content analysis)
- Generates titles and captions
- Schedules posts to YouTube and TikTok
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid
import hashlib

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from loguru import logger

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
SORA_DIR = Path("/Users/isaiahdupree/Documents/SoraVideos")

# Blotato accounts for YouTube and TikTok
YOUTUBE_ACCOUNTS = [
    {"id": 228, "username": "Isaiah Dupree"},
    {"id": 3370, "username": "lofi_creator"},
]

TIKTOK_ACCOUNTS = [
    {"id": 710, "username": "@isaiah_dupree"},
    {"id": 243, "username": "@the_isaiah_dupree"},
    {"id": 4508, "username": "@dupree_isaiah"},
]


def get_clean_videos():
    """Get all clean (non-watermarked) videos."""
    videos = []
    for f in SORA_DIR.glob("s_*.mp4"):
        if "_watermarked" not in f.name:
            videos.append(f)
    return sorted(videos)


def compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash of file."""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def ingest_videos(engine):
    """Ingest all Sora videos into the database."""
    videos = get_clean_videos()
    logger.info(f"Found {len(videos)} clean Sora videos to ingest")
    
    ingested = 0
    skipped = 0
    
    with engine.connect() as conn:
        for video_path in videos:
            # Check if already ingested by source_uri
            result = conn.execute(text("""
                SELECT id FROM videos 
                WHERE source_uri = :uri
            """), {"uri": str(video_path)})
            
            if result.fetchone():
                logger.debug(f"Already ingested: {video_path.name}")
                skipped += 1
                continue
            
            # Get file info
            stat = video_path.stat()
            file_hash = compute_file_hash(video_path)
            
            # Check for duplicate by hash
            result = conn.execute(text("""
                SELECT id FROM videos 
                WHERE file_hash = :hash
            """), {"hash": file_hash})
            
            if result.fetchone():
                logger.debug(f"Duplicate hash: {video_path.name}")
                skipped += 1
                continue
            
            # Get video duration using ffprobe
            import subprocess
            try:
                probe = subprocess.run([
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path)
                ], capture_output=True, text=True)
                duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
            except:
                duration = 0
            
            # Insert video record
            video_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO videos (
                    id, file_name, file_path, source_uri, file_hash,
                    file_size, duration, status, media_type,
                    created_at, updated_at
                ) VALUES (
                    :id, :file_name, :file_path, :source_uri, :file_hash,
                    :file_size, :duration, 'pending', 'video',
                    NOW(), NOW()
                )
            """), {
                "id": video_id,
                "file_name": video_path.name,
                "file_path": str(video_path),
                "source_uri": str(video_path),
                "file_hash": file_hash,
                "file_size": stat.st_size,
                "duration": duration
            })
            
            ingested += 1
            logger.success(f"✓ Ingested: {video_path.name} ({duration:.1f}s)")
        
        conn.commit()
    
    logger.info(f"Ingestion complete: {ingested} new, {skipped} skipped")
    return ingested


def analyze_videos(engine):
    """Analyze all unanalyzed Sora videos."""
    from services.whisper_transcriber import WhisperTranscriber
    from services.ai_client import AIClient
    from config.model_registry import TaskType, ModelRegistry
    
    # Get videos needing analysis
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT v.id, v.file_path, v.file_name
            FROM videos v
            LEFT JOIN video_analysis va ON va.video_id = v.id
            WHERE v.source_uri LIKE '%SoraVideos%'
              AND va.id IS NULL
            ORDER BY v.created_at DESC
        """))
        videos = result.fetchall()
    
    if not videos:
        logger.info("All Sora videos already analyzed")
        return 0
    
    logger.info(f"Analyzing {len(videos)} Sora videos...")
    
    transcriber = WhisperTranscriber()
    config = ModelRegistry.get_model_config(TaskType.CONTENT_ANALYSIS)
    ai_client = AIClient(config)
    
    analyzed = 0
    
    for video_id, file_path, file_name in videos:
        try:
            logger.info(f"Analyzing: {file_name}")
            
            # Transcribe
            transcript_result = transcriber.transcribe_video(file_path)
            transcript = transcript_result.get("text", "")
            
            # Since these are AI-generated Sora videos, they may not have audio
            # Generate description based on visual analysis would be ideal
            # For now, we'll mark them and generate content differently
            
            # Insert analysis record
            with engine.connect() as conn:
                analysis_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO video_analysis (
                        id, video_id, transcript, language,
                        status, created_at, updated_at
                    ) VALUES (
                        :id, :video_id, :transcript, :language,
                        'completed', NOW(), NOW()
                    )
                """), {
                    "id": analysis_id,
                    "video_id": video_id,
                    "transcript": transcript if transcript else "[No audio - AI generated video]",
                    "language": transcript_result.get("language", "en") if transcript else None
                })
                
                # Update video status
                conn.execute(text("""
                    UPDATE videos SET status = 'analyzed', updated_at = NOW()
                    WHERE id = :id
                """), {"id": video_id})
                
                conn.commit()
            
            analyzed += 1
            logger.success(f"✓ Analyzed: {file_name}")
            
        except Exception as e:
            logger.error(f"Analysis failed for {file_name}: {e}")
    
    logger.info(f"Analysis complete: {analyzed} videos")
    return analyzed


def generate_content_for_sora_videos(engine):
    """Generate titles and captions for Sora videos using AI."""
    from services.ai_client import AIClient
    from config.model_registry import TaskType, ModelRegistry
    
    config = ModelRegistry.get_model_config(TaskType.CONTENT_ANALYSIS)
    ai_client = AIClient(config)
    
    # Get Sora videos without generated content
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT v.id, v.file_name, va.transcript
            FROM videos v
            JOIN video_analysis va ON va.video_id = v.id
            WHERE v.source_uri LIKE '%SoraVideos%'
              AND v.status = 'analyzed'
              AND (v.title IS NULL OR v.title = '')
            ORDER BY v.created_at DESC
        """))
        videos = result.fetchall()
    
    if not videos:
        logger.info("All Sora videos already have generated content")
        return 0
    
    logger.info(f"Generating content for {len(videos)} Sora videos...")
    
    generated = 0
    
    for video_id, file_name, transcript in videos:
        try:
            # Extract video ID from filename for context
            sora_id = file_name.replace(".mp4", "").replace("s_", "")
            
            prompt = f"""Generate a creative title and caption for a Sora AI-generated video.

Video ID: {sora_id}
Transcript/Audio: {transcript if transcript and "[No audio" not in transcript else "No audio (visual-only AI video)"}

This is an AI-generated video from OpenAI's Sora. Create engaging content that:
1. Highlights the AI-generated nature creatively
2. Is suitable for YouTube Shorts and TikTok
3. Uses relevant hashtags

Return JSON format:
{{
    "title": "Short catchy title (max 100 chars)",
    "caption": "Engaging caption with hashtags (max 300 chars)",
    "hashtags": ["sora", "ai", "openai", ...]
}}"""

            response = ai_client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            import json
            try:
                content = json.loads(response)
            except:
                # Try to extract JSON from response
                import re
                match = re.search(r'\{[^{}]+\}', response, re.DOTALL)
                if match:
                    content = json.loads(match.group())
                else:
                    content = {
                        "title": f"AI Magic ✨ Sora Creation #{sora_id[:8]}",
                        "caption": "Created with OpenAI Sora 🎬 #sora #ai #openai #aigeneratedvideo",
                        "hashtags": ["sora", "ai", "openai"]
                    }
            
            # Update video with generated content
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE videos 
                    SET title = :title,
                        description = :caption,
                        status = 'ready',
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": video_id,
                    "title": content.get("title", "")[:100],
                    "caption": content.get("caption", "")[:300]
                })
                conn.commit()
            
            generated += 1
            logger.success(f"✓ Generated content: {content.get('title', '')[:50]}...")
            
        except Exception as e:
            logger.error(f"Content generation failed for {file_name}: {e}")
    
    logger.info(f"Content generation complete: {generated} videos")
    return generated


def schedule_to_platforms(engine, max_per_platform: int = 10):
    """Schedule Sora videos to YouTube and TikTok."""
    
    # Get ready videos not yet scheduled
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT v.id, v.file_path, v.title, v.description, v.file_name
            FROM videos v
            WHERE v.source_uri LIKE '%SoraVideos%'
              AND v.status = 'ready'
              AND v.id NOT IN (
                  SELECT DISTINCT content_id::uuid FROM scheduled_posts 
                  WHERE content_id IS NOT NULL
              )
            ORDER BY v.created_at DESC
            LIMIT :limit
        """), {"limit": max_per_platform * 2})
        videos = result.fetchall()
    
    if not videos:
        logger.info("No Sora videos ready to schedule")
        return 0
    
    logger.info(f"Scheduling {len(videos)} Sora videos to YouTube and TikTok...")
    
    scheduled = 0
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    
    with engine.connect() as conn:
        for i, (video_id, file_path, title, caption, file_name) in enumerate(videos):
            # Alternate between platforms and accounts
            platforms = [
                ("youtube", YOUTUBE_ACCOUNTS[i % len(YOUTUBE_ACCOUNTS)]),
                ("tiktok", TIKTOK_ACCOUNTS[i % len(TIKTOK_ACCOUNTS)]),
            ]
            
            for platform, account in platforms:
                if scheduled >= max_per_platform * 2:
                    break
                
                # Schedule time (spread out over next few days)
                schedule_time = start_time + timedelta(hours=scheduled * 4)
                
                post_id = str(uuid.uuid4())
                
                conn.execute(text("""
                    INSERT INTO scheduled_posts (
                        id, content_id, clip_id, platform, platform_account_id,
                        account_username, scheduled_time, status,
                        title, caption, post_type,
                        created_at, updated_at
                    ) VALUES (
                        :id, :content_id, :clip_id, :platform, :account_id,
                        :username, :scheduled_time, 'scheduled',
                        :title, :caption, 'reel',
                        NOW(), NOW()
                    )
                """), {
                    "id": post_id,
                    "content_id": str(video_id),
                    "clip_id": video_id,
                    "platform": platform,
                    "account_id": str(account["id"]),
                    "username": account["username"],
                    "scheduled_time": schedule_time,
                    "title": title[:100] if title else f"Sora AI Video #{file_name[:8]}",
                    "caption": caption[:300] if caption else "Created with OpenAI Sora #sora #ai"
                })
                
                scheduled += 1
                logger.success(f"✓ Scheduled to {platform} ({account['username']}): {title[:40]}...")
        
        conn.commit()
    
    logger.info(f"Scheduling complete: {scheduled} posts created")
    return scheduled


async def main():
    """Main pipeline."""
    logger.info("="*60)
    logger.info("SORA VIDEO INGESTION PIPELINE")
    logger.info("="*60)
    
    engine = create_engine(DATABASE_URL)
    
    # Step 1: Ingest videos
    logger.info("\n📥 Step 1: Ingesting videos...")
    ingested = ingest_videos(engine)
    
    # Step 2: Analyze videos
    logger.info("\n🔍 Step 2: Analyzing videos...")
    analyzed = analyze_videos(engine)
    
    # Step 3: Generate content
    logger.info("\n✍️ Step 3: Generating titles and captions...")
    generated = generate_content_for_sora_videos(engine)
    
    # Step 4: Schedule to platforms
    logger.info("\n📅 Step 4: Scheduling to YouTube and TikTok...")
    scheduled = schedule_to_platforms(engine, max_per_platform=10)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*60)
    logger.success(f"✓ Ingested: {ingested} videos")
    logger.success(f"✓ Analyzed: {analyzed} videos")
    logger.success(f"✓ Generated content: {generated} videos")
    logger.success(f"✓ Scheduled: {scheduled} posts")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
AI Title/Description Generator for Scheduled Posts

This script:
1. Fetches all pending scheduled posts
2. Uses video analysis data (transcript, topics, hooks, tone)
3. Generates optimized titles and descriptions via OpenAI
4. Respects platform character limits (~20% under max)
5. Updates the scheduled posts with AI-generated content
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from loguru import logger
import openai

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Platform character limits (~20% buffer for safety)
# Actual limits -> Target limits (80% of max)
PLATFORM_LIMITS = {
    "tiktok": {
        "title": 80,          # Max ~100, target 80
        "description": 1800,  # Max 2200, target 1760 -> rounded to 1800
    },
    "instagram": {
        "title": 80,          # No strict title, but keep short
        "description": 1760,  # Max 2200, target 1760
    },
    "youtube": {
        "title": 80,          # Max 100, target 80
        "description": 4000,  # Max 5000, target 4000
    },
    "threads": {
        "title": 40,          # Keep very short
        "description": 400,   # Max 500, target 400
    },
    "twitter": {
        "title": 40,          # N/A but keep short
        "description": 224,   # Max 280, target 224
    },
    "bluesky": {
        "title": 40,          # Keep short
        "description": 240,   # Max 300, target 240
    },
    "linkedin": {
        "title": 80,          # Keep reasonable
        "description": 2400,  # Max 3000, target 2400
    },
    "facebook": {
        "title": 80,          # Keep reasonable
        "description": 5000,  # Generous limit
    },
    "pinterest": {
        "title": 80,          # Max 100
        "description": 400,   # Max 500
    },
}

# Default limits for unknown platforms
DEFAULT_LIMITS = {"title": 60, "description": 500}


def get_engine():
    """Create SQLAlchemy engine with connection pooling."""
    return create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


def get_pending_posts_with_video_data(engine) -> List[Dict]:
    """Get all pending scheduled posts with their video analysis data."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                sp.id,
                sp.content_id,
                sp.platform,
                sp.title,
                sp.caption,
                sp.account_username,
                va.transcript,
                va.topics,
                va.hooks,
                va.tone,
                va.pre_social_score,
                v.file_name,
                v.duration_sec
            FROM scheduled_posts sp
            LEFT JOIN videos v ON v.id::text = sp.content_id
            LEFT JOIN video_analysis va ON va.video_id = v.id
            WHERE sp.status = 'pending'
              AND sp.scheduled_time > NOW()
            ORDER BY sp.scheduled_time
        """))
        
        posts = []
        for row in result:
            posts.append({
                "id": str(row[0]),
                "content_id": row[1],
                "platform": row[2],
                "current_title": row[3],
                "current_caption": row[4],
                "account_username": row[5],
                "transcript": row[6],
                "topics": list(row[7]) if row[7] else [],
                "hooks": list(row[8]) if row[8] else [],
                "tone": row[9],
                "score": int(row[10]) if row[10] else 0,
                "file_name": row[11],
                "duration_sec": float(row[12]) if row[12] else None,
            })
        
        return posts


async def generate_ai_content(
    client: openai.AsyncOpenAI,
    post: Dict,
    title_limit: int,
    description_limit: int
) -> Dict[str, str]:
    """Generate AI title and description for a post."""
    
    # Build context from available data
    context_parts = []
    
    if post.get("transcript"):
        # Use first 500 chars of transcript for context
        transcript_preview = post["transcript"][:500]
        context_parts.append(f"Video transcript: {transcript_preview}...")
    
    if post.get("hooks"):
        context_parts.append(f"Key hooks: {', '.join(post['hooks'][:3])}")
    
    if post.get("topics"):
        context_parts.append(f"Topics: {', '.join(post['topics'][:5])}")
    
    if post.get("tone"):
        context_parts.append(f"Tone: {post['tone']}")
    
    if post.get("duration_sec"):
        duration = int(post["duration_sec"])
        context_parts.append(f"Video duration: {duration} seconds")
    
    context = "\n".join(context_parts) if context_parts else "Short-form video content"
    
    platform = post["platform"]
    
    prompt = f"""Generate an engaging title and description for a {platform} video post.

VIDEO CONTEXT:
{context}

REQUIREMENTS:
- Title: Maximum {title_limit} characters, catchy and engaging
- Description: Maximum {description_limit} characters
- Include relevant hashtags in description (but count toward limit)
- Match the platform's style ({platform})
- Be authentic and conversational
- Include a call-to-action if appropriate

PLATFORM STYLE GUIDE:
- TikTok: Casual, trendy, hook-focused, use emojis sparingly
- Instagram: Polished but relatable, storytelling, hashtags important
- YouTube: Descriptive, SEO-friendly, include keywords
- Threads: Very concise, conversational, minimal hashtags
- Twitter: Punchy, witty, very short, 1-2 hashtags max
- LinkedIn: Professional, value-focused, thought leadership

Respond in JSON format:
{{"title": "your title here", "description": "your description here"}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Enforce limits
        title = result.get("title", "")[:title_limit]
        description = result.get("description", "")[:description_limit]
        
        return {"title": title, "description": description}
        
    except Exception as e:
        logger.error(f"OpenAI error for post {post['id']}: {e}")
        # Return current content as fallback
        return {
            "title": (post.get("current_title") or post.get("hooks", [""])[0] or "Check this out")[:title_limit],
            "description": (post.get("current_caption") or "")[:description_limit]
        }


def update_post_content(engine, post_id: str, title: str, description: str):
    """Update a scheduled post with new title and caption."""
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE scheduled_posts
            SET title = :title,
                caption = :description,
                updated_at = NOW()
            WHERE id = :id
        """), {"id": post_id, "title": title, "description": description})
        conn.commit()


async def process_all_posts(dry_run: bool = False):
    """Process all pending posts and generate AI content."""
    
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set!")
        return
    
    engine = get_engine()
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    # Get all pending posts
    posts = get_pending_posts_with_video_data(engine)
    logger.info(f"Found {len(posts)} pending posts to process")
    
    if not posts:
        logger.info("No pending posts found")
        return
    
    updated_count = 0
    
    for i, post in enumerate(posts):
        platform = post["platform"].lower()
        limits = PLATFORM_LIMITS.get(platform, DEFAULT_LIMITS)
        
        logger.info(f"[{i+1}/{len(posts)}] Processing {platform} post {post['id'][:8]}...")
        
        # Generate AI content
        result = await generate_ai_content(
            client,
            post,
            limits["title"],
            limits["description"]
        )
        
        title = result["title"]
        description = result["description"]
        
        logger.info(f"  Title ({len(title)}/{limits['title']} chars): {title[:50]}...")
        logger.info(f"  Description ({len(description)}/{limits['description']} chars): {description[:80]}...")
        
        if not dry_run:
            update_post_content(engine, post["id"], title, description)
            updated_count += 1
        else:
            logger.info("  [DRY RUN - not saving]")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ Updated {updated_count}/{len(posts)} posts with AI-generated content")
    logger.info(f"{'='*60}")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate AI titles/descriptions for scheduled posts")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving changes")
    parser.add_argument("--post-id", type=str, help="Process a specific post ID only")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("🤖 AI Post Content Generator")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be saved")
    
    await process_all_posts(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())

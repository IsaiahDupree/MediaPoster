"""
AI Analysis API Endpoints - Phase 1
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from pathlib import Path
import uuid
import json
import os
from loguru import logger

from database.connection import get_db
from database.models import OriginalVideo, ProcessingJob
from modules.ai_analysis import ContentAnalyzer
from config.platform_limits import get_platform_limits, PLATFORM_LIMITS, DEFAULT_PROMPT_SETTINGS
from services.event_bus import EventBus, Topics

router = APIRouter()


class AnalysisRequest(BaseModel):
    transcribe: bool = True
    analyze_vision: bool = True
    analyze_audio: bool = True
    max_frames: int = 15


class AnalysisResponse(BaseModel):
    job_id: uuid.UUID
    video_id: uuid.UUID
    status: str
    message: str


class GenerateCaptionsRequest(BaseModel):
    platform: str = "tiktok"
    tone: str = "engaging"
    style: Optional[str] = None
    include_hashtags: bool = True
    include_hook: bool = True
    custom_prompt: Optional[str] = None


@router.post("/full-analysis/{video_id}", response_model=AnalysisResponse)
async def start_full_analysis(
    video_id: uuid.UUID,
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start comprehensive AI analysis for a video
    
    Includes:
    - Whisper transcription
    - Frame extraction and GPT-4 Vision analysis
    - Audio characteristic analysis
    """
    from sqlalchemy import select
    
    # Get video from database
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Create processing job
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="ai_analysis",
        status="queued",
        config_json={
            'transcribe': request.transcribe,
            'analyze_vision': request.analyze_vision,
            'analyze_audio': request.analyze_audio,
            'max_frames': request.max_frames
        }
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Emit ANALYSIS_REQUESTED event
    try:
        event_bus = EventBus.get_instance()
        await event_bus.publish(Topics.ANALYSIS_REQUESTED, {
            "job_id": str(job.job_id),
            "video_id": str(video_id),
            "transcribe": request.transcribe,
            "analyze_vision": request.analyze_vision,
        })
        logger.info(f"[PubSub] Emitted ANALYSIS_REQUESTED for {job.job_id}")
    except Exception as e:
        logger.warning(f"[PubSub] Failed to emit analysis event: {e}")
    
    # Start analysis in background
    background_tasks.add_task(
        run_analysis,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path),
        config=request.dict()
    )
    
    return AnalysisResponse(
        job_id=job.job_id,
        video_id=video_id,
        status="queued",
        message="Analysis started. Check job status for progress."
    )


@router.post("/transcribe/{video_id}")
async def transcribe_video(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Transcribe video audio with Whisper"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job = ProcessingJob(
        parent_video_id=video_id,
        job_type="transcription",
        status="queued"
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    background_tasks.add_task(
        run_transcription_only,
        video_id=video_id,
        job_id=job.job_id,
        video_path=Path(video.file_path)
    )
    
    return {"job_id": str(job.job_id), "status": "queued"}


@router.get("/results")
async def list_analysis_results(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all videos with analysis results"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo)
        .filter(OriginalVideo.analysis_data.isnot(None))
        .limit(limit)
        .offset(offset)
        .order_by(OriginalVideo.created_at.desc())
    )
    videos = list(result.scalars().all())
    
    return {
        "total": len(videos),
        "videos": [
            {
                "video_id": str(v.video_id),
                "video_name": v.file_name,
                "has_analysis": v.analysis_data is not None,
                "analysis_keys": list(v.analysis_data.keys()) if v.analysis_data else []
            }
            for v in videos
        ]
    }


@router.get("/results/{video_id}")
async def get_analysis_results(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get analysis results for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analysis_data:
        raise HTTPException(status_code=404, detail="No analysis data available")
    
    return {
        "video_id": str(video_id),
        "video_name": video.file_name,
        "analysis": video.analysis_data
    }


@router.get("/transcript/{video_id}")
async def get_transcript(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get transcript for a video"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analysis_data or 'transcript' not in video.analysis_data:
        raise HTTPException(status_code=404, detail="Transcript not available")
    
    return {
        "video_id": str(video_id),
        "transcript": video.analysis_data['transcript']
    }


@router.post("/generate-captions/{media_id}")
async def generate_captions(
    media_id: str,
    request: GenerateCaptionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered captions for a media item using transcript and analysis data.
    
    Args:
        media_id: UUID of the media item
        request: Generation parameters including platform, tone, style
        
    Returns:
        Generated captions for each platform with hashtags and hooks
    """
    from sqlalchemy import select, text
    
    logger.info(f"[GenerateCaptions] 🚀 Starting caption generation for media_id={media_id}")
    logger.info(f"[GenerateCaptions] 📋 Request: platform={request.platform}, tone={request.tone}, style={request.style}")
    logger.info(f"[GenerateCaptions] 📋 Custom prompt: {request.custom_prompt}")
    
    # Try to find media in the videos table (media-db)
    transcript = ""
    topics = []
    hooks = []
    title = ""
    
    try:
        # First, get the video metadata
        video_result = await db.execute(
            text("SELECT id, file_name FROM videos WHERE id = :media_id"),
            {"media_id": media_id}
        )
        video_row = video_result.fetchone()
        
        if video_row:
            # Video found in videos table - get analysis from video_analysis table
            title = video_row[1] or ''
            logger.info(f"[GenerateCaptions] 📄 Found video: {title}")
            
            # Get analysis data from video_analysis table
            analysis_result = await db.execute(
                text("SELECT transcript, topics, hooks FROM video_analysis WHERE video_id = :media_id"),
                {"media_id": media_id}
            )
            analysis_row = analysis_result.fetchone()
            
            if analysis_row:
                transcript = analysis_row[0] or ''
                # Handle PostgreSQL arrays - they come as lists or None
                topics_raw = analysis_row[1]
                hooks_raw = analysis_row[2]
                topics = list(topics_raw) if topics_raw else []
                hooks = list(hooks_raw) if hooks_raw else []
                logger.info(f"[GenerateCaptions] 📝 Transcript length: {len(transcript)} chars")
                logger.info(f"[GenerateCaptions] 🏷️ Topics ({len(topics)}): {topics}")
                logger.info(f"[GenerateCaptions] 🎣 Hooks ({len(hooks)}): {hooks}")
            else:
                logger.warning(f"[GenerateCaptions] ⚠️ No analysis data found for video_id={media_id}")
        else:
            # Try original_videos table as fallback
            logger.warning(f"[GenerateCaptions] ⚠️ Media not found in videos table, trying original_videos")
            result = await db.execute(
                select(OriginalVideo).filter(OriginalVideo.video_id == uuid.UUID(media_id))
            )
            media = result.scalar_one_or_none()
            
            if media:
                title = media.file_name or ''
                transcript = media.transcript or ''
                topics = media.topics or []
                hooks = media.hooks if hasattr(media, 'hooks') else []
                
                # Also check analysis_data for hooks
                if media.analysis_data:
                    hooks_from_data = media.analysis_data.get('hooks', [])
                    if hooks_from_data:
                        hooks = hooks_from_data
                
                logger.info(f"[GenerateCaptions] 📄 Found original video: {title}")
                logger.info(f"[GenerateCaptions] 📝 Transcript length: {len(transcript)} chars")
                logger.info(f"[GenerateCaptions] 🏷️ Topics: {topics}")
                logger.info(f"[GenerateCaptions] 🎣 Hooks: {hooks}")
            else:
                logger.error(f"[GenerateCaptions] ❌ Media not found: {media_id}")
                raise HTTPException(status_code=404, detail="Media not found")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GenerateCaptions] ❌ Database query error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if not title:
        logger.error(f"[GenerateCaptions] ❌ Media not found: {media_id}")
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Use AI to generate creative title and description from analysis context
    original_filename = title
    import re
    is_filename = re.match(r'^(IMG_|VID_|MOV_|\d+\.)', title, re.IGNORECASE) or title.endswith('.MOV') or title.endswith('.mp4')
    
    # Get platform limits for title generation (20% of max)
    from config.platform_limits import get_platform_limits
    platform_limits = get_platform_limits(request.platform)
    title_target = platform_limits.title_target  # 20% buffer already applied (80% of max)
    
    # Always use AI to generate title if we have enough context
    if transcript or topics or hooks:
        try:
            from openai import OpenAI
            import os
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Build rich context for AI
            context_parts = []
            if topics:
                context_parts.append(f"Main Topics: {', '.join(topics[:5])}")
            if hooks:
                context_parts.append(f"Key Hooks: {'; '.join(hooks[:3])}")
            if transcript:
                context_parts.append(f"Content Summary: {transcript[:500]}")
            
            context = "\n".join(context_parts)
            
            # Generate creative title using AI with platform-specific limit (20% of max)
            title_prompt = f"""Based on this video analysis, create a SHORT, catchy, viral-worthy title for {request.platform}.
REQUIREMENTS:
- Maximum {title_target} characters (strict limit - this is 20% of {request.platform}'s max title length)
- Punchy and attention-grabbing
- NO quotes, NO hashtags, NO emojis
- Make people want to click and watch
- Optimized for {request.platform} audience

Analysis Context:
{context}

Generate ONLY the title, no quotes, no explanation."""

            logger.info(f"[GenerateCaptions] 🤖 Calling OpenAI to generate platform-specific title (target: {title_target} chars for {request.platform})...")
            
            title_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are a viral content title expert for {request.platform}. Create short, punchy titles under {title_target} characters."},
                    {"role": "user", "content": title_prompt}
                ],
                max_tokens=60,
                temperature=0.8
            )
            
            ai_title = title_response.choices[0].message.content.strip().strip('"').strip("'")
            # Enforce platform-specific limit
            if ai_title and len(ai_title) > 5:
                if len(ai_title) > title_target:
                    ai_title = ai_title[:title_target - 3] + "..."
                title = ai_title
                logger.info(f"[GenerateCaptions] ✨ AI Generated title ({len(title)}/{title_target} chars): {title}")
            
        except Exception as e:
            logger.error(f"[GenerateCaptions] ❌ AI title generation failed: {e}")
            # Fallback to topics-based title (still within limit)
            if topics and len(topics) > 0:
                fallback_title = f"The Truth About {topics[0]}"
                if len(fallback_title) > title_target:
                    fallback_title = fallback_title[:title_target - 3] + "..."
                title = fallback_title
                logger.info(f"[GenerateCaptions] 🏷️ Fallback title from topics: {title}")
    
    # Generate captions using AI or templates (will generate platform-specific titles/descriptions)
    generated = await _generate_platform_captions(
        title=title,
        transcript=transcript,
        topics=topics,
        hooks=hooks,
        platform=request.platform,
        tone=request.tone,
        style=request.style,
        custom_prompt=request.custom_prompt,
        include_hashtags=request.include_hashtags,
        include_hook=request.include_hook
    )
    
    logger.info(f"[GenerateCaptions] ✅ Generated captions successfully")
    logger.info(f"[GenerateCaptions] 📤 TikTok caption: {generated['tiktok'][:100]}...")
    
    # Extract platform-specific titles and descriptions from generated captions
    # Note: Currently generates one title, but captions are platform-specific
    platform_titles = {}
    platform_descriptions = {}
    
    # For now, use the generated title for all platforms
    # TODO: Generate platform-specific titles in _generate_platform_captions
    for platform_key in generated.keys():
        platform_titles[platform_key] = title
        # Extract description from caption (remove hashtags for description)
        caption = generated[platform_key]
        # Description is the caption without hashtags (rough extraction)
        desc = caption.split('#')[0].strip() if '#' in caption else caption
        platform_descriptions[platform_key] = desc
    
    return {
        "success": True,
        "media_id": media_id,
        "title": title,  # Generic title (for backward compatibility)
        "platform_titles": platform_titles,  # Platform-specific titles
        "platform_descriptions": platform_descriptions,  # Platform-specific descriptions
        "transcript_available": len(transcript) > 0,
        "captions": generated
    }


def truncate_to_limit(text: str, max_chars: int, add_ellipsis: bool = True) -> str:
    """Truncate text to fit within character limit"""
    if len(text) <= max_chars:
        return text
    if add_ellipsis and max_chars > 3:
        return text[:max_chars - 3].rsplit(' ', 1)[0] + "..."
    return text[:max_chars]


async def _generate_platform_captions(
    title: str,
    transcript: str,
    topics: List[str],
    hooks: List[str],
    platform: str,
    tone: str,
    style: Optional[str],
    custom_prompt: Optional[str],
    include_hashtags: bool,
    include_hook: bool
) -> Dict[str, str]:
    """Generate captions for all platforms using AI based on content analysis.
    
    Enforces platform-specific character limits with 20% buffer for safety.
    """
    
    logger.info(f"[_generate_platform_captions] 🎯 Generating for tone={tone}, style={style}")
    
    # Get platform limits for all platforms we'll generate for
    platforms_to_generate = ["tiktok", "instagram", "youtube", "twitter", "threads", "pinterest", "linkedin", "bluesky", "facebook"]
    platform_limits = {p: get_platform_limits(p) for p in platforms_to_generate}
    
    # Build context from available data
    topics_str = ', '.join(topics[:5]) if topics else ""
    hooks_str = '; '.join(hooks[:3]) if hooks else ""
    transcript_snippet = transcript[:500] if transcript else ""
    
    # Use AI to generate creative descriptions
    description_text = ""
    try:
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Build rich context
        context = f"""
Video Title: {title}
Topics: {topics_str}
Key Hooks: {hooks_str}
Content: {transcript_snippet}
Tone: {tone}
Platform: {platform}
"""
        
        # Get platform-specific description target (20% of max = 80% of max limit)
        platform_limit = platform_limits.get(platform, platform_limits.get('tiktok'))
        desc_target = platform_limit.description_target  # Already 80% of max (20% buffer)
        
        desc_prompt = f"""Based on this video analysis, write a compelling description for {platform}.
REQUIREMENTS:
- Maximum {desc_target} characters (strict limit - this is 20% of {platform}'s max description length)
- 2-3 sentences that summarize the VALUE and INSIGHT the viewer will get
- DO NOT copy the transcript word-for-word
- Make it engaging and encourage interaction
- Match the {tone} tone
- Optimized for {platform} audience

{context}

Write ONLY the description (2-3 sentences), no hashtags, no title. Be creative and compelling."""

        logger.info(f"[_generate_platform_captions] 🤖 Calling OpenAI to generate platform-specific description (target: {desc_target} chars for {platform})...")
        
        # Adjust max_tokens based on target length (roughly 1 token = 4 chars)
        max_tokens_for_desc = min(200, int(desc_target / 3))
        
        desc_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": desc_prompt}],
            max_tokens=max_tokens_for_desc,
            temperature=0.7
        )
        
        description_text = desc_response.choices[0].message.content.strip()
        
        # Enforce platform-specific limit
        if len(description_text) > desc_target:
            description_text = truncate_to_limit(description_text, desc_target)
        
        logger.info(f"[_generate_platform_captions] ✨ AI Generated description ({len(description_text)}/{desc_target} chars): {description_text[:80]}...")
        
    except Exception as e:
        logger.error(f"[_generate_platform_captions] ❌ AI description generation failed: {e}")
        # Fallback to basic description
        if topics:
            description_text = f"Discover insights about {topics[0].lower()} and how it can transform your approach."
        else:
            description_text = "Watch to discover valuable insights that could change your perspective."
    
    logger.info(f"[_generate_platform_captions] 📄 Title: {title[:50]}...")
    logger.info(f"[_generate_platform_captions] 📝 Description: {description_text[:80]}...")
    
    # Determine tone modifiers
    is_humorous = tone == 'funny' or (style and 'funny' in style.lower()) or (custom_prompt and 'funny' in custom_prompt.lower())
    is_professional = tone == 'professional' or (style and 'professional' in style.lower())
    is_casual = tone == 'casual' or (style and 'casual' in style.lower())
    is_engaging = tone == 'engaging' or not (is_humorous or is_professional or is_casual)
    
    logger.info(f"[_generate_platform_captions] 🎭 Tone detection: humorous={is_humorous}, professional={is_professional}, casual={is_casual}, engaging={is_engaging}")
    
    # Generate hashtags based on topics
    base_hashtags = []
    if topics:
        base_hashtags = [f"#{t.replace(' ', '').lower()}" for t in topics[:5]]
    
    # Platform-specific generation
    # NOTE: Descriptions should NOT include the title - title is separate
    captions = {}
    
    # TikTok caption - description only, no title
    if is_humorous:
        tiktok_caption = ""
        if description_text:
            tiktok_caption = f"😂 You won't believe this... {description_text}\n\n"
        tiktok_caption += f"#fyp #viral #comedy {' '.join(base_hashtags[:3])}"
    elif is_professional:
        tiktok_caption = ""
        if description_text:
            tiktok_caption = f"📊 {description_text}\n\n"
        tiktok_caption += f"#business #professional {' '.join(base_hashtags[:3])}"
    elif is_casual:
        tiktok_caption = ""
        if description_text:
            tiktok_caption = f"👋 {description_text}\n\n"
        tiktok_caption += f"#fyp #foryou {' '.join(base_hashtags[:3])}"
    else:
        # Engaging/default
        tiktok_caption = ""
        if description_text:
            tiktok_caption = f"🔥 {description_text}\n\n"
        tiktok_caption += f"#fyp #viral {' '.join(base_hashtags[:3])}"
    
    captions['tiktok'] = tiktok_caption.strip()
    
    # Instagram caption - description only, no title
    if is_humorous:
        instagram_caption = ""
        if description_text:
            instagram_caption = f"😂 {description_text}\n\n"
        instagram_caption += f"Tag someone who needs to see this! 👇\n\n#reels #funny {' '.join(base_hashtags[:5])}"
    elif is_professional:
        instagram_caption = ""
        if description_text:
            instagram_caption = f"{description_text}\n\n"
        instagram_caption += f"What are your thoughts? Share below.\n\n#professional {' '.join(base_hashtags[:5])}"
    elif is_casual:
        instagram_caption = ""
        if description_text:
            instagram_caption = f"✨ {description_text}\n\n"
        instagram_caption += f"#reels #mood {' '.join(base_hashtags[:5])}"
    else:
        instagram_caption = ""
        if description_text:
            instagram_caption = f"✨ {description_text}\n\n"
        instagram_caption += f"#reels #explore {' '.join(base_hashtags[:5])}"
    
    captions['instagram'] = instagram_caption.strip()
    
    # YouTube caption - description only, no title
    if is_humorous:
        youtube_caption = ""
        if description_text:
            youtube_caption = f"{description_text} 😂\n\n"
        youtube_caption += f"Don't forget to like and subscribe for more!\n\nTopics: {topics_str}"
    elif is_professional:
        youtube_caption = ""
        if description_text:
            youtube_caption = f"{description_text}\n\n"
        youtube_caption += f"For more professional content, subscribe to our channel.\n\nTopics: {topics_str}"
    elif is_casual:
        youtube_caption = ""
        if description_text:
            youtube_caption = f"{description_text}\n\n"
        youtube_caption += f"Thanks for watching! 💜\n\nTopics: {topics_str}"
    else:
        youtube_caption = ""
        if description_text:
            youtube_caption = f"{description_text}\n\n"
        youtube_caption += f"Topics: {topics_str}"
    
    captions['youtube'] = youtube_caption.strip()
    
    # Generate for additional platforms with proper limits
    # NOTE: All descriptions should NOT include the title - title is separate
    
    # Twitter/X - description only (short platform)
    twitter_limit = platform_limits['twitter']
    twitter_caption = ""
    if description_text:
        twitter_caption = truncate_to_limit(description_text, twitter_limit.description_target - 40)
    if include_hashtags and base_hashtags:
        twitter_caption += f" {' '.join(base_hashtags[:2])}"
    captions['twitter'] = truncate_to_limit(twitter_caption.strip(), twitter_limit.description_target)
    
    # Threads - description only
    threads_limit = platform_limits['threads']
    threads_caption = ""
    if description_text:
        threads_caption = f"✨ {truncate_to_limit(description_text, threads_limit.description_target - 50)}\n\n"
    if include_hashtags and base_hashtags:
        threads_caption += ' '.join(base_hashtags[:3])
    captions['threads'] = truncate_to_limit(threads_caption.strip(), threads_limit.description_target)
    
    # Pinterest - description only
    pinterest_limit = platform_limits['pinterest']
    pinterest_title = truncate_to_limit(title, pinterest_limit.title_target)
    pinterest_desc = description_text if description_text else f"Discover insights about {topics[0] if topics else 'this topic'}"
    captions['pinterest'] = truncate_to_limit(pinterest_desc, pinterest_limit.description_target)
    captions['pinterest_title'] = pinterest_title
    
    # LinkedIn - description only
    linkedin_limit = platform_limits['linkedin']
    linkedin_caption = ""
    if description_text:
        linkedin_caption = f"{description_text}\n\n"
    linkedin_caption += "What are your thoughts? Share in the comments below."
    if include_hashtags and base_hashtags:
        linkedin_caption += f"\n\n{' '.join(base_hashtags[:5])}"
    captions['linkedin'] = truncate_to_limit(linkedin_caption.strip(), linkedin_limit.description_target)
    
    # Bluesky - description only
    bluesky_limit = platform_limits['bluesky']
    bluesky_caption = ""
    if description_text:
        bluesky_caption = truncate_to_limit(description_text, bluesky_limit.description_target - 30)
    captions['bluesky'] = truncate_to_limit(bluesky_caption.strip(), bluesky_limit.description_target)
    
    # Facebook - description only
    facebook_limit = platform_limits['facebook']
    facebook_caption = ""
    if description_text:
        facebook_caption = f"{description_text}\n\n"
    if include_hashtags and base_hashtags:
        facebook_caption += ' '.join(base_hashtags[:3])
    captions['facebook'] = truncate_to_limit(facebook_caption.strip(), facebook_limit.description_target)
    
    # Enforce limits on previously generated captions
    captions['tiktok'] = truncate_to_limit(captions['tiktok'], platform_limits['tiktok'].description_target)
    captions['instagram'] = truncate_to_limit(captions['instagram'], platform_limits['instagram'].description_target)
    captions['youtube'] = truncate_to_limit(captions['youtube'], platform_limits['youtube'].description_target)
    
    # Log character counts for debugging
    for p, caption in captions.items():
        if p in platform_limits:
            limit = platform_limits[p].description_target
            logger.info(f"[_generate_platform_captions] 📏 {p}: {len(caption)}/{limit} chars")
    
    return captions


# Background task functions
async def run_analysis(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path,
    config: dict
):
    """Run complete analysis in background"""
    from database.connection import async_session_maker
    from sqlalchemy import select, update
    from datetime import datetime
    
    async with async_session_maker() as session:
        try:
            # Update job status
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await session.commit()
            
            # Run analysis
            analyzer = ContentAnalyzer()
            analysis = analyzer.analyze_video_complete(
                video_path,
                extract_frames=True,
                analyze_vision=config['analyze_vision'],
                transcribe_audio=config['transcribe'],
                analyze_audio=config['analyze_audio'],
                max_frames=config['max_frames']
            )
            
            # Save analysis to video record
            await session.execute(
                update(OriginalVideo)
                .where(OriginalVideo.video_id == video_id)
                .values(analysis_data=analysis)
            )
            
            # Update job status
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    progress_percent=100
                )
            )
            await session.commit()
            
        except Exception as e:
            # Update job with error
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(
                    status="failed",
                    error_message=str(e)
                )
            )
            await session.commit()
            raise


async def run_transcription_only(
    video_id: uuid.UUID,
    job_id: uuid.UUID,
    video_path: Path
):
    """Run transcription only"""
    from database.connection import async_session_maker
    from sqlalchemy import update
    from datetime import datetime
    from modules.ai_analysis import WhisperService
    
    async with async_session_maker() as session:
        try:
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="running", started_at=datetime.utcnow())
            )
            await session.commit()
            
            whisper = WhisperService()
            transcript = whisper.transcribe_video(video_path)
            
            # Save to video
            result = await session.execute(
                select(OriginalVideo).filter(OriginalVideo.video_id == video_id)
            )
            video = result.scalar_one()
            
            if video.analysis_data:
                video.analysis_data['transcript'] = transcript
            else:
                video.analysis_data = {'transcript': transcript}
            
            await session.commit()
            
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="completed", completed_at=datetime.utcnow(), progress_percent=100)
            )
            await session.commit()
            
        except Exception as e:
            await session.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(status="failed", error_message=str(e))
            )
            await session.commit()

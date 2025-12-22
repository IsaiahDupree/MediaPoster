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
            
            # Generate creative title using AI
            title_prompt = f"""Based on this video analysis, create a SHORT, catchy, viral-worthy title (max 50 chars).
DO NOT copy the transcript directly. Create something creative and attention-grabbing.
The title should make people want to click and watch.

Analysis Context:
{context}

Generate ONLY the title, no quotes, no explanation. Make it punchy and engaging for {request.platform}."""

            logger.info(f"[GenerateCaptions] 🤖 Calling OpenAI to generate creative title...")
            
            title_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": title_prompt}],
                max_tokens=60,
                temperature=0.8
            )
            
            ai_title = title_response.choices[0].message.content.strip().strip('"').strip("'")
            if ai_title and len(ai_title) > 5:
                title = ai_title
                logger.info(f"[GenerateCaptions] ✨ AI Generated title: {title}")
            
        except Exception as e:
            logger.error(f"[GenerateCaptions] ❌ AI title generation failed: {e}")
            # Fallback to topics-based title
            if topics and len(topics) > 0:
                title = f"The Truth About {topics[0]}"
                logger.info(f"[GenerateCaptions] 🏷️ Fallback title from topics: {title}")
    
    # Generate captions using AI or templates
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
    
    return {
        "success": True,
        "media_id": media_id,
        "title": title,
        "transcript_available": len(transcript) > 0,
        "captions": generated
    }


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
    """Generate captions for all platforms using AI based on content analysis"""
    
    logger.info(f"[_generate_platform_captions] 🎯 Generating for tone={tone}, style={style}")
    
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
        
        desc_prompt = f"""Based on this video analysis, write a compelling 2-3 sentence description for {platform}.
DO NOT copy the transcript word-for-word. Summarize the VALUE and INSIGHT the viewer will get.
Make it engaging and encourage interaction. Match the {tone} tone.

{context}

Write ONLY the description (2-3 sentences), no hashtags, no title. Be creative and compelling."""

        logger.info(f"[_generate_platform_captions] 🤖 Calling OpenAI to generate creative description...")
        
        desc_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": desc_prompt}],
            max_tokens=150,
            temperature=0.7
        )
        
        description_text = desc_response.choices[0].message.content.strip()
        logger.info(f"[_generate_platform_captions] ✨ AI Generated description: {description_text[:80]}...")
        
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
    captions = {}
    
    # TikTok caption - use description_text to avoid duplication
    if is_humorous:
        tiktok_caption = f"😂 {title}\n\n"
        if description_text:
            tiktok_caption += f"You won't believe this... {description_text}...\n\n"
        tiktok_caption += f"#fyp #viral #comedy {' '.join(base_hashtags[:3])}"
    elif is_professional:
        tiktok_caption = f"📊 {title}\n\n"
        if description_text:
            tiktok_caption += f"{description_text}...\n\n"
        tiktok_caption += f"#business #professional {' '.join(base_hashtags[:3])}"
    elif is_casual:
        tiktok_caption = f"Hey! 👋 {title}\n\n"
        if description_text:
            tiktok_caption += f"{description_text}...\n\n"
        tiktok_caption += f"#fyp #foryou {' '.join(base_hashtags[:3])}"
    else:
        # Engaging/default
        tiktok_caption = f"🔥 {title}\n\n"
        if description_text:
            tiktok_caption += f"{description_text}...\n\n"
        tiktok_caption += f"#fyp #viral {' '.join(base_hashtags[:3])}"
    
    captions['tiktok'] = tiktok_caption
    
    # Instagram caption - use description_text to avoid duplication
    if is_humorous:
        instagram_caption = f"LOL 😂 {title}\n\n"
        if description_text:
            instagram_caption += f"{description_text}...\n\n"
        instagram_caption += f"Tag someone who needs to see this! 👇\n\n#reels #funny {' '.join(base_hashtags[:5])}"
    elif is_professional:
        instagram_caption = f"{title}\n\n"
        if description_text:
            instagram_caption += f"{description_text}...\n\n"
        instagram_caption += f"What are your thoughts? Share below.\n\n#professional {' '.join(base_hashtags[:5])}"
    elif is_casual:
        instagram_caption = f"Just vibing ✨ {title}\n\n"
        if description_text:
            instagram_caption += f"{description_text}...\n\n"
        instagram_caption += f"#reels #mood {' '.join(base_hashtags[:5])}"
    else:
        instagram_caption = f"✨ {title}\n\n"
        if description_text:
            instagram_caption += f"{description_text}...\n\n"
        instagram_caption += f"#reels #explore {' '.join(base_hashtags[:5])}"
    
    captions['instagram'] = instagram_caption
    
    # YouTube caption - use description_text to avoid duplication
    if is_humorous:
        youtube_caption = f"{title} 😂\n\n"
        if description_text:
            youtube_caption += f"{description_text}\n\n"
        youtube_caption += f"Don't forget to like and subscribe for more!\n\nTopics: {topics_str}"
    elif is_professional:
        youtube_caption = f"{title}\n\n"
        if description_text:
            youtube_caption += f"{description_text}\n\n"
        youtube_caption += f"For more professional content, subscribe to our channel.\n\nTopics: {topics_str}"
    elif is_casual:
        youtube_caption = f"{title}\n\n"
        if description_text:
            youtube_caption += f"{description_text}\n\n"
        youtube_caption += f"Thanks for watching! 💜\n\nTopics: {topics_str}"
    else:
        youtube_caption = f"{title}\n\n"
        if description_text:
            youtube_caption += f"{description_text}\n\n"
        youtube_caption += f"Topics: {topics_str}"
    
    captions['youtube'] = youtube_caption
    
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

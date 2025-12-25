"""
Video Analyzer - Main orchestrator for video analysis pipeline
Combines transcription, content analysis, and database storage
"""
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

from services.whisper_transcriber import WhisperTranscriber
from services.content_analyzer import ContentAnalyzer


class VideoAnalyzer:
    """Main orchestrator for video analysis"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize video analyzer
        
        Args:
            api_key: OpenAI API key for both Whisper and GPT-4
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize services
        self.transcriber = WhisperTranscriber(api_key=self.api_key)
        self.content_analyzer = ContentAnalyzer(api_key=self.api_key)
        
        # Lazy import to avoid circular deps if any
        from services.frame_analyzer import FrameAnalyzer
        from services.thumbnail_generator import ThumbnailGenerator
        
        self.frame_analyzer = FrameAnalyzer(api_key=self.api_key)
        self.thumbnail_generator = ThumbnailGenerator(openai_api_key=self.api_key)
    
    async def analyze_video(
        self,
        video_id: uuid.UUID,
        video_path: str,
        db_session,
        metadata: dict = None,
        on_step_callback: callable = None
    ) -> dict:
        """
        Run complete video analysis pipeline
        
        Args:
            video_id: UUID of video in database
            video_path: Path to video file
            db_session: Async database session
            metadata: Optional video metadata (duration, title, etc.)
            on_step_callback: Optional callback for step progress updates
            
        Returns:
            Complete analysis results
        """
        from database.models import VideoAnalysis, Video
        from sqlalchemy import select, update
        
        def notify_step(step_name):
            if on_step_callback:
                on_step_callback(step_name)
        
        logger.info(f"Starting analysis for video {video_id}: {Path(video_path).name}")
        
        try:
            # Step 1: Transcribe video
            logger.info("Step 1/4: Transcribing with Whisper")
            notify_step("1/4 Transcribing")
            
            transcript = ""
            transcript_error = None
            has_audio = True
            
            try:
                transcript_data = self.transcriber.transcribe_video(video_path)
                transcript = transcript_data.get("text", "")
                has_audio = not transcript_data.get("no_audio", False)
                
                if not transcript and not has_audio:
                    logger.warning(f"[Analysis] No audio stream in video {video_id}")
                    transcript_error = "No audio stream detected in video"
                elif not transcript:
                    logger.warning(f"[Analysis] Empty transcript for {video_id}")
                    transcript_error = "Transcription returned empty"
                else:
                    logger.info(f"[Analysis] Transcript: {len(transcript)} chars, {len(transcript.split())} words")
                    
            except Exception as e:
                logger.error(f"[Analysis] Transcription failed for {video_id}: {e}")
                transcript_error = f"Transcription error: {str(e)}"
            
            # Step 2: Visual Analysis & Thumbnail Selection
            logger.info("Step 2/4: Analyzing visuals (Frames + Thumbnail)")
            notify_step("2/4 Analyzing visuals")
            visual_context = {}
            best_frame_score = 0.0
            visual_error = None
            
            try:
                # Extract frames
                frames = self.thumbnail_generator.extract_frames(video_path, num_frames=5)
                logger.info(f"[Analysis] Extracted {len(frames) if frames else 0} frames")
                
                if frames:
                    # Analyze frames with Vision
                    visual_analysis = self.frame_analyzer.analyze_frames(frames)
                    visual_context = visual_analysis
                    logger.info(f"[Analysis] Visual analysis complete: {len(visual_context.get('visual_summary', ''))} chars")
                    
                    # Select best frame for thumbnail
                    best_frame_path, best_frame_stats = self.thumbnail_generator.select_best_from_frames(frames)
                    best_frame_score = best_frame_stats.get('overall_score', 0.0)
                    logger.info(f"[Analysis] Best frame score: {best_frame_score:.2f}")
                    # Note: best_frame_score will be saved in Step 4 with other analysis data
                else:
                    logger.warning(f"[Analysis] No frames extracted from video {video_id}")
                    visual_error = "No frames could be extracted"
                    
            except Exception as e:
                logger.error(f"Visual analysis failed: {e}")
                visual_context = {"error": str(e)}
                visual_error = str(e)

            # Step 3: Analyze content with GPT-4 (Transcript + Visuals)
            logger.info("Step 3/4: Analyzing content with GPT-4")
            notify_step("3/4 GPT-4 Analysis")
            
            # Add visual context to metadata for GPT-4
            analysis_metadata = metadata or {}
            if visual_context.get("visual_summary"):
                analysis_metadata["visual_context"] = visual_context["visual_summary"]
            
            # Run content analysis - prioritize transcript, fallback to visuals
            analysis = {}
            analysis_source = "none"
            
            if transcript and len(transcript.strip()) > 10:
                # Full transcript analysis
                logger.info(f"[Analysis] Running GPT-4 content analysis on transcript ({len(transcript)} chars)")
                try:
                    analysis = self.content_analyzer.analyze_transcript(
                        transcript=transcript,
                        video_metadata=analysis_metadata
                    )
                    analysis_source = "transcript"
                    logger.info(f"[Analysis] Transcript analysis complete: {len(analysis.get('topics', []))} topics, score={analysis.get('pre_social_score')}")
                except Exception as e:
                    logger.error(f"[Analysis] Transcript analysis failed: {e}")
                    analysis_source = "transcript_failed"
            
            # If no transcript or transcript analysis failed, try visual analysis
            if not analysis or analysis_source == "transcript_failed":
                visual_summary = visual_context.get("visual_summary", "")
                
                if visual_summary and len(visual_summary) > 20:
                    logger.info(f"[Analysis] Generating analysis from visual context ({len(visual_summary)} chars)")
                    try:
                        analysis = self.content_analyzer.analyze_from_visuals(
                            visual_summary=visual_summary,
                            video_metadata=analysis_metadata
                        )
                        analysis_source = "visuals"
                        logger.info(f"[Analysis] Visual analysis complete: {len(analysis.get('topics', []))} topics, score={analysis.get('pre_social_score')}")
                    except Exception as e:
                        logger.error(f"[Analysis] Visual content analysis failed: {e}")
                        analysis_source = "visuals_failed"
                else:
                    logger.warning(f"[Analysis] No visual summary available for fallback analysis")
            
            # Ultimate fallback - ensure we always have SOME analysis
            if not analysis or not analysis.get("topics"):
                logger.warning(f"[Analysis] Using minimal fallback analysis for {video_id}")
                analysis = {
                    "topics": ["video content", "media"],
                    "hooks": ["Check out this content"],
                    "tone": "neutral",
                    "pacing": "medium",
                    "pre_social_score": 50,
                    "analysis_note": f"Limited analysis - source: {analysis_source}, transcript_error: {transcript_error}, visual_error: {visual_error}"
                }
                analysis_source = "fallback"
            
            # Add metadata about analysis source
            analysis["_analysis_source"] = analysis_source
            if transcript_error:
                analysis["_transcript_error"] = transcript_error
            if visual_error:
                analysis["_visual_error"] = visual_error
            
            # Step 4: Save to database
            logger.info("Step 4/4: Saving to database")
            notify_step("4/4 Saving")
            
            # Check if analysis record exists
            result = await db_session.execute(
                select(VideoAnalysis).where(VideoAnalysis.video_id == video_id)
            )
            existing = result.scalar_one_or_none()
            
            # Ensure pre_social_score is on 0-100 scale
            raw_score = analysis.get("pre_social_score", analysis.get("viral_score", 50))
            if raw_score <= 10:
                raw_score = raw_score * 10  # Convert 0-10 scale to 0-100
            
            # Add analysis metadata to visual_context for debugging
            visual_context["analysis_source"] = analysis_source
            if analysis.get("analysis_note"):
                visual_context["analysis_note"] = analysis.get("analysis_note")
            if transcript_error:
                visual_context["transcript_error"] = transcript_error
            if visual_error:
                visual_context["visual_error"] = visual_error
            
            # Ensure we have topics and hooks (never empty)
            topics = analysis.get("topics", [])
            hooks = analysis.get("hooks", [])
            if not topics:
                topics = ["video content"]
            if not hooks and visual_context.get("visual_summary"):
                # Extract a hook from visual summary
                vs = visual_context.get("visual_summary", "")
                hooks = [vs[:100] + "..." if len(vs) > 100 else vs] if vs else []
            
            # Extract best hook from hooks list
            best_hook = hooks[0] if hooks else None
            
            # Determine pillar tags from topics
            pillar_tags = topics[:3] if topics else None
            
            # Determine format tags based on video metadata
            format_tags = []
            if metadata:
                duration = metadata.get("duration", 0)
                if duration < 60:
                    format_tags.append("short-form")
                elif duration < 180:
                    format_tags.append("medium-form")
                else:
                    format_tags.append("long-form")
            format_tags.append("video")
            
            # Add frame count to visual context
            visual_context["frame_count"] = len(frames) if frames else 5
            
            analysis_values = {
                "transcript": transcript if transcript else "",
                "topics": topics,
                "hooks": hooks,
                "tone": analysis.get("tone", "neutral"),
                "pacing": analysis.get("pacing", "medium"),
                "key_moments": analysis.get("key_moments", {}),
                "visual_analysis": visual_context,
                "detected_hook": best_hook,
                "pillar_tags": pillar_tags,
                "format_tags": format_tags,
                "music_suggestion": analysis.get("music_suggestion"),
                "pre_social_score": float(raw_score),
                "analysis_version": "3.0",  # Version with all deep analysis fields
                "analyzed_at": datetime.utcnow()
            }
            
            logger.info(f"[Analysis] Saving: source={analysis_source}, transcript={len(transcript)} chars, topics={len(topics)}, hooks={len(hooks)}, score={raw_score}")
            
            # VALIDATE: Ensure analysis is complete before saving
            # This prevents false positives where videos are marked as "analyzed" with incomplete data
            is_complete = (
                transcript and len(transcript) > 10 and  # Must have meaningful transcript
                topics and len(topics) > 0 and  # Must have at least one topic
                raw_score is not None  # Must have a score
            )
            
            if not is_complete:
                error_msg = (
                    f"[Analysis] INCOMPLETE analysis for {video_id} - NOT saving to prevent false positives. "
                    f"transcript={len(transcript) if transcript else 0} chars, "
                    f"topics={len(topics) if topics else 0}, "
                    f"score={raw_score}"
                )
                logger.error(error_msg)
                print(f"\n{'='*80}")
                print(f"❌ [ANALYSIS VALIDATION FAILED] Video: {video_id}")
                print(f"   Transcript: {len(transcript) if transcript else 0} chars (required: >10)")
                print(f"   Topics: {len(topics) if topics else 0} (required: >0)")
                print(f"   Score: {raw_score} (required: not None)")
                print(f"   Analysis NOT saved - will not be marked as 'analyzed'")
                print(f"{'='*80}\n")
                raise ValueError(f"Incomplete analysis: transcript={bool(transcript)}, topics={len(topics) if topics else 0}, score={raw_score is not None}")
            
            # Generate AI title (~20% of platform character limit = ~30 chars)
            ai_title = await self._generate_ai_title(transcript, topics, hooks, video_path)
            if ai_title:
                # Update video record with generated title
                from database.models import Video
                await db_session.execute(
                    update(Video)
                    .where(Video.id == video_id)
                    .values(title=ai_title)
                )
                logger.info(f"[Analysis] Generated title: {ai_title}")
            
            if existing:
                # Update existing
                await db_session.execute(
                    update(VideoAnalysis)
                    .where(VideoAnalysis.video_id == video_id)
                    .values(**analysis_values)
                )
            else:
                # Create new
                new_analysis = VideoAnalysis(
                    video_id=video_id,
                    **analysis_values
                )
                db_session.add(new_analysis)
            
            # Save best_frame_score to Video table
            if best_frame_score > 0:
                await db_session.execute(
                    update(Video)
                    .where(Video.id == video_id)
                    .values(best_frame_score=best_frame_score)
                )
                logger.info(f"[Analysis] Saved best_frame_score: {best_frame_score:.2f}")
            
            await db_session.commit()
            
            logger.success(f"Video analysis complete for {video_id} - VALIDATED: transcript={len(transcript)} chars, topics={len(topics)}, score={raw_score}")
            print(f"✅ [ANALYSIS SAVED] Video: {video_id} | Transcript: {len(transcript)} chars | Topics: {len(topics)} | Score: {raw_score}")
            
            return {
                "video_id": str(video_id),
                "status": "complete",
                "analysis_complete": True,
                "transcript": transcript,
                **analysis,
                "visual_analysis": visual_context
            }
            
        except Exception as e:
            logger.error(f"Video analysis failed for {video_id}: {e}")
            await db_session.rollback()
            raise
    
    async def _generate_ai_title(
        self,
        transcript: str,
        topics: list,
        hooks: list,
        video_path: str
    ) -> Optional[str]:
        """
        Generate an AI-powered title for the video.
        Target: ~30 characters (20% of TikTok's 150 char limit)
        
        Platform limits:
        - TikTok: 150 chars → target ~30 chars
        - Instagram: 2200 chars → target ~30 chars (keep consistent)
        - YouTube: 100 chars → target ~20 chars
        """
        if not self.api_key:
            return None
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            # Build context for title generation
            context_parts = []
            if transcript and len(transcript) > 20:
                context_parts.append(f"Transcript excerpt: {transcript[:300]}")
            if topics:
                context_parts.append(f"Topics: {', '.join(topics[:5])}")
            if hooks:
                context_parts.append(f"Hooks: {', '.join(hooks[:3])}")
            
            if not context_parts:
                # No context, extract from filename
                filename = Path(video_path).stem if video_path else ""
                if filename and not filename.startswith(('IMG_', 'VID_', 'MOV_')):
                    return filename[:30]
                return None
            
            context = "\n".join(context_parts)
            
            prompt = f"""Generate a SHORT, catchy, viral-worthy video title.

REQUIREMENTS:
- Maximum 30 characters (strict limit)
- Punchy and attention-grabbing
- NO quotes, NO hashtags, NO emojis
- Make people want to click and watch

VIDEO CONTEXT:
{context}

Return ONLY the title text, nothing else."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral content title expert. Create short, punchy titles under 30 characters."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=50
            )
            
            title = response.choices[0].message.content.strip()
            # Clean up title
            title = title.strip('"\'')
            # Enforce 30 char limit
            if len(title) > 30:
                title = title[:27] + "..."
            
            return title if len(title) > 3 else None
            
        except Exception as e:
            logger.warning(f"[Analysis] AI title generation failed: {e}")
            return None

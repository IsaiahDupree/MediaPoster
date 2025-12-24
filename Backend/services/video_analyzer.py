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
                    
                    # Update Video record with thumbnail info
                    await db_session.execute(
                        update(Video)
                        .where(Video.id == video_id)
                        .values(best_frame_score=best_frame_score)
                    )
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
            
            await db_session.commit()
            
            logger.success(f"Video analysis complete for {video_id}")
            
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

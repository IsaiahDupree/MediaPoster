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
        metadata: dict = None
    ) -> dict:
        """
        Run complete video analysis pipeline
        
        Args:
            video_id: UUID of video in database
            video_path: Path to video file
            db_session: Async database session
            metadata: Optional video metadata (duration, title, etc.)
            
        Returns:
            Complete analysis results
        """
        from database.models import VideoAnalysis, Video
        from sqlalchemy import select, update
        
        logger.info(f"Starting analysis for video {video_id}: {Path(video_path).name}")
        
        try:
            # Step 1: Transcribe video
            logger.info("Step 1/4: Transcribing with Whisper")
            transcript_data = self.transcriber.transcribe_video(video_path)
            transcript = transcript_data["text"]
            
            # Step 2: Visual Analysis & Thumbnail Selection
            logger.info("Step 2/4: Analyzing visuals (Frames + Thumbnail)")
            visual_context = {}
            best_frame_score = 0.0
            
            try:
                # Extract frames
                frames = self.thumbnail_generator.extract_frames(video_path, num_frames=5)
                
                if frames:
                    # Analyze frames with Vision
                    visual_analysis = self.frame_analyzer.analyze_frames(frames)
                    visual_context = visual_analysis
                    
                    # Select best frame for thumbnail
                    best_frame_path, best_frame_stats = self.thumbnail_generator.select_best_from_frames(frames)
                    best_frame_score = best_frame_stats.get('overall_score', 0.0)
                    
                    # Update Video record with thumbnail info
                    # Note: We are just calculating score here, actual thumbnail generation/saving 
                    # might happen in a separate task or we could do it here.
                    # For now, we'll update the score.
                    await db_session.execute(
                        update(Video)
                        .where(Video.id == video_id)
                        .values(best_frame_score=best_frame_score)
                    )
                    
            except Exception as e:
                logger.error(f"Visual analysis failed: {e}")
                visual_context = {"error": str(e)}

            # Step 3: Analyze content with GPT-4 (Transcript + Visuals)
            logger.info("Step 3/4: Analyzing content with GPT-4")
            
            # Add visual context to metadata for GPT-4
            analysis_metadata = metadata or {}
            if visual_context.get("visual_summary"):
                analysis_metadata["visual_context"] = visual_context["visual_summary"]
            
            analysis = self.content_analyzer.analyze_transcript(
                transcript=transcript,
                video_metadata=analysis_metadata
            )
            
            # Step 4: Save to database
            logger.info("Step 4/4: Saving to database")
            
            # Check if analysis record exists
            result = await db_session.execute(
                select(VideoAnalysis).where(VideoAnalysis.video_id == video_id)
            )
            existing = result.scalar_one_or_none()
            
            analysis_values = {
                "transcript": transcript,
                "topics": analysis.get("topics", []),
                "hooks": analysis.get("hooks", []),
                "tone": analysis.get("tone", ""),
                "pacing": analysis.get("pacing", ""),
                "key_moments": analysis.get("key_moments", {}),
                "visual_analysis": visual_context,
                "music_suggestion": analysis.get("music_suggestion", {}),
                "pre_social_score": analysis.get("viral_score", 0.0),
                "analysis_version": "2.0",
                "analyzed_at": datetime.utcnow()
            }
            
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

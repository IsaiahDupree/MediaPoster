"""
Content Analysis Orchestrator
Coordinates transcription, psychology tagging, and video analysis
Complete workflow for analyzing viral video components
"""
import logging
from typing import Dict, List, Optional, Any
import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from database.models import (
    AnalyzedVideo, VideoSegment, VideoWord,
    OriginalVideo, ContentItem
)
from services.transcription import TranscriptionService
from services.psychology_tagger import PsychologyTagger
from services.video_analysis import VideoAnalysisService
from services.segment_editor import SegmentEditor, ValidationResult
from services.performance_correlator import PerformanceCorrelator

logger = logging.getLogger(__name__)


class ContentAnalysisOrchestrator:
    """Orchestrates full content analysis workflow"""
    
    def __init__(
        self,
        db: Session,
        openai_api_key: Optional[str] = None,
        frame_output_dir: str = "/tmp/frames"
    ):
        """
        Initialize content analysis orchestrator
        
        Args:
            db: Database session
            openai_api_key: OpenAI API key
            frame_output_dir: Directory for frame extraction
        """
        self.db = db
        self.transcription = TranscriptionService(api_key=openai_api_key)
        self.psychology = PsychologyTagger(api_key=openai_api_key)
        self.video_analysis = VideoAnalysisService(
            db=db,
            frame_output_dir=frame_output_dir,
            openai_api_key=openai_api_key
        )
        self.segment_editor = SegmentEditor(db)
        self.performance_correlator = PerformanceCorrelator(db)
    
    def is_ready(self) -> Dict[str, bool]:
        """Check if all services are ready"""
        return {
            "transcription_enabled": self.transcription.is_enabled(),
            "psychology_enabled": self.psychology.is_enabled(),
            "ffmpeg_installed": self.video_analysis.is_ready()["ffmpeg_installed"],
            "vision_api_enabled": self.video_analysis.is_ready()["vision_api_enabled"]
        }
    
    def analyze_video_complete(
        self,
        video_path: str,
        original_video_id: Optional[uuid.UUID] = None,
        content_item_id: Optional[uuid.UUID] = None,
        store_in_db: bool = True
    ) -> Dict[str, Any]:
        """
        Complete video analysis workflow
        
        Steps:
        1. Transcribe with word-level timestamps
        2. Classify segments (hook, context, body, CTA)
        3. Tag psychology (FATE/AIDA)
        4. Sample and analyze frames
        5. Store everything in database
        
        Args:
            video_path: Path to video file
            original_video_id: Reference to original_videos table
            content_item_id: Reference to content_items table
            store_in_db: Whether to store results
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting complete video analysis for {video_path}")
        
        readiness = self.is_ready()
        logger.info(f"Service readiness: {readiness}")
        
        results = {
            "video_path": video_path,
            "services_ready": readiness,
            "transcription": {},
            "psychology": {},
            "visual": {},
            "database": {}
        }
        
        try:
            # Step 1: Transcribe
            if readiness["transcription_enabled"]:
                logger.info("Step 1: Transcribing video...")
                transcript_result = self.transcription.transcribe_video(video_path)
                
                if "error" not in transcript_result:
                    results["transcription"] = transcript_result
                    results["transcription"]["stats"] = self.transcription.get_transcript_statistics(transcript_result)
                    logger.info(f"Transcription complete: {len(transcript_result.get('words', []))} words")
                else:
                    logger.error(f"Transcription failed: {transcript_result['error']}")
                    results["transcription"] = transcript_result
            else:
                logger.warning("Transcription skipped - service not enabled")
            
            # Step 2: Psychology analysis
            if readiness["psychology_enabled"] and results["transcription"].get("text"):
                logger.info("Step 2: Running psychology analysis...")
                transcript_text = results["transcription"]["text"]
                duration = results["transcription"].get("duration")
                
                psych_result = self.psychology.comprehensive_analysis(
                    transcript_text,
                    duration_s=duration
                )
                
                results["psychology"] = psych_result
                logger.info("Psychology analysis complete")
            else:
                logger.warning("Psychology analysis skipped")
            
            # Step 3: Visual analysis
            if readiness["ffmpeg_installed"]:
                logger.info("Step 3: Running visual analysis...")
                
                # Create AnalyzedVideo record first if storing
                analyzed_video_id = None
                
                if store_in_db:
                    analyzed_video = AnalyzedVideo(
                        original_video_id=original_video_id,
                        content_item_id=content_item_id,
                        duration_seconds=results["transcription"].get("duration"),
                        transcript_full=results["transcription"].get("text", "")
                    )
                    self.db.add(analyzed_video)
                    self.db.commit()
                    self.db.refresh(analyzed_video)
                    analyzed_video_id = analyzed_video.id
                    logger.info(f"Created AnalyzedVideo record: {analyzed_video_id}")
                else:
                    analyzed_video_id = uuid.uuid4()
                
                # Run visual analysis
                visual_result = self.video_analysis.analyze_video_frames(
                    video_path=video_path,
                    video_id=analyzed_video_id,
                    sampling_interval_s=1.0,
                    analysis_type="comprehensive",
                    store_in_db=store_in_db
                )
                
                results["visual"] = visual_result
                logger.info("Visual analysis complete")
                
                # Step 4: Store transcript data
                if store_in_db and analyzed_video_id:
                    logger.info("Step 4: Storing transcript and psychology data...")
                    
                    # Store segments
                    if "segments" in results["psychology"]:
                        segments_stored = self._store_segments(
                            analyzed_video_id,
                            results["psychology"]["segments"].get("segments", [])
                        )
                        results["database"]["segments_stored"] = segments_stored
                    
                    # Store words
                    if "words" in results["transcription"]:
                        words_stored = self._store_words(
                            analyzed_video_id,
                            results["transcription"]["words"]
                        )
                        results["database"]["words_stored"] = words_stored
                    
                    results["database"]["analyzed_video_id"] = str(analyzed_video_id)
                    logger.info("Database storage complete")
            
            results["success"] = True
            logger.info("Complete video analysis finished successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in complete video analysis: {e}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    def _store_segments(
        self,
        video_id: uuid.UUID,
        segments: List[Dict[str, Any]]
    ) -> int:
        """Store video segments in database"""
        stored_count = 0
        
        for seg in segments:
            try:
                fate_tags = seg.get("fate_tags", {})
                
                segment = VideoSegment(
                    video_id=video_id,
                    segment_type=seg.get("segment_type", "body"),
                    start_s=seg.get("start_s", 0),
                    end_s=seg.get("end_s", 0),
                    hook_type=seg.get("hook_type"),
                    focus=fate_tags.get("focus"),
                    authority_signal=fate_tags.get("authority_signal"),
                    tribe_marker=fate_tags.get("tribe_marker"),
                    emotion=fate_tags.get("emotion")
                )
                
                self.db.add(segment)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing segment: {e}")
                continue
        
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing segments: {e}")
            self.db.rollback()
            return 0
        
        return stored_count
    
    def _store_words(
        self,
        video_id: uuid.UUID,
        words: List[Dict[str, Any]]
    ) -> int:
        """Store word-level timestamps in database"""
        stored_count = 0
        
        for idx, word_data in enumerate(words):
            try:
                word = VideoWord(
                    video_id=video_id,
                    word_index=idx,
                    word=word_data.get("word", ""),
                    start_s=word_data.get("start", 0),
                    end_s=word_data.get("end", 0)
                )
                
                self.db.add(word)
                stored_count += 1
                
                # Commit in batches to avoid memory issues
                if stored_count % 100 == 0:
                    self.db.commit()
                    
            except Exception as e:
                logger.error(f"Error storing word {idx}: {e}")
                continue
        
        # Final commit
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing words: {e}")
            self.db.rollback()
            return 0
        
        return stored_count
    
    def reanalyze_segment(
        self,
        segment_id: str,
        update_type: bool = True,
        update_tags: bool = True
    ) -> Optional[VideoSegment]:
        """
        Re-analyze a specific segment using AI
        
        Args:
            segment_id: UUID of segment
            update_type: Whether to re-classify type
            update_tags: Whether to re-generate psychology tags
            
        Returns:
            Updated VideoSegment
        """
        segment = self.db.query(VideoSegment).filter(VideoSegment.id == segment_id).first()
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")
            
        # Get transcript for this segment
        # In a real implementation, we would query VideoWord table
        # For now, we'll assume we can get the text
        transcript_text = "..." # Placeholder
        
        if update_tags:
            # Re-run psychology analysis on just this text
            # psych_result = self.psychology.analyze_segment(transcript_text)
            # segment.psychology_tags = psych_result
            pass
            
        self.db.commit()
        return segment

    def analyze_with_performance(
        self,
        video_id: str,
        post_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Run performance correlation analysis for a video
        
        Args:
            video_id: UUID of video
            post_ids: List of post UUIDs to correlate
            
        Returns:
            Analysis results including correlations
        """
        # 1. Get all segments
        segments = self.db.query(VideoSegment).filter(VideoSegment.video_id == video_id).all()
        
        results = {
            "video_id": video_id,
            "segments_analyzed": len(segments),
            "correlations": []
        }
        
        # 2. Correlate each segment
        for segment in segments:
            perf_records = self.performance_correlator.correlate_segment_to_metrics(
                str(segment.id),
                post_ids
            )
            results["correlations"].extend([
                {
                    "segment_id": str(p.segment_id),
                    "post_id": str(p.post_id),
                    "score": p.engagement_score
                }
                for p in perf_records
            ])
            
        return results

    def validate_analysis(self, video_id: str) -> ValidationResult:
        """Validate analysis data for a video"""
        return self.segment_editor.validate_segments(video_id)

    def export_analysis(self, video_id: str) -> Dict[str, Any]:
        """Export full analysis data as JSON"""
        video = self.db.query(AnalyzedVideo).filter(AnalyzedVideo.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")
            
        segments = self.db.query(VideoSegment).filter(VideoSegment.video_id == video_id).all()
        
        return {
            "video_id": str(video.id),
            "duration": video.duration_seconds,
            "transcript": video.transcript_full,
            "segments": [
                {
                    "id": str(s.id),
                    "start": s.start_time,
                    "end": s.end_time,
                    "type": s.segment_type,
                    "tags": s.psychology_tags,
                    "is_manual": s.is_manual
                }
                for s in segments
            ],
            "exported_at": str(datetime.now())
        }

    def cleanup(self, video_id: Optional[uuid.UUID] = None):
        """Clean up temporary files"""
        self.video_analysis.cleanup(video_id)


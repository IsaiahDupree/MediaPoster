"""
Integration Tests: Endpoints with Real Video Data
Tests endpoints using actual video files and full data structures from video resources
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from datetime import datetime, timedelta
import uuid
import json
import os
from pathlib import Path
from typing import List, Dict, Any

from main import app
from database.models import OriginalVideo, Video, VideoWord, VideoFrame, AnalyzedVideo
from database.connection import async_session_maker


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest_asyncio.fixture
async def db_session():
    """Get real database session"""
    from database.connection import init_db
    
    if async_session_maker is None:
        await init_db()
        from database.connection import async_session_maker
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def real_video_from_db(db_session: AsyncSession):
    """Get a real video from the database if available"""
    # Try to get an existing video from the database
    result = await db_session.execute(
        text("SELECT id, file_name, source_uri FROM videos LIMIT 1")
    )
    video_row = result.first()
    
    if video_row:
        return {
            "id": str(video_row.id),
            "file_name": video_row.file_name,
            "source_uri": video_row.source_uri
        }
    return None


@pytest_asyncio.fixture
async def real_original_video_from_db(db_session: AsyncSession):
    """Get a real OriginalVideo from the database if available"""
    result = await db_session.execute(
        select(OriginalVideo).limit(1)
    )
    video = result.scalar_one_or_none()
    return video


@pytest_asyncio.fixture
async def video_with_full_analysis(db_session: AsyncSession, real_original_video_from_db):
    """Create or update a video with complete analysis data"""
    if real_original_video_from_db:
        video = real_original_video_from_db
    else:
        # Create a new video if none exists
        video = OriginalVideo(
            video_id=uuid.uuid4(),
            file_name="test_full_analysis.mp4",
            file_path="/tmp/test_full_analysis.mp4",
            duration_seconds=120.0,
            file_size_bytes=2048000
        )
        db_session.add(video)
        await db_session.flush()
    
    # Add comprehensive analysis data
    video.analysis_data = {
        "transcript": {
            "text": "This is a comprehensive test video transcript. It contains multiple sentences and demonstrates full analysis capabilities.",
            "duration": 120.0,
            "segments": [
                {"start": 0.0, "end": 10.0, "text": "Introduction segment"},
                {"start": 10.0, "end": 60.0, "text": "Main content with detailed information"},
                {"start": 60.0, "end": 120.0, "text": "Conclusion and call to action"}
            ]
        },
        "topics": ["technology", "testing", "video analysis", "integration"],
        "hooks": [
            "You won't believe what happens next!",
            "This changes everything you know about testing"
        ],
        "tone": "educational",
        "pacing": "medium",
        "key_moments": [
            {
                "start": 0.0,
                "end": 5.0,
                "summary": "Strong opening hook",
                "suggested_caption": "Starting with a bang!"
            },
            {
                "start": 30.0,
                "end": 45.0,
                "summary": "Key insight revealed",
                "suggested_caption": "The moment of truth"
            },
            {
                "start": 100.0,
                "end": 120.0,
                "summary": "Call to action",
                "suggested_caption": "Don't forget to subscribe!"
            }
        ],
        "pre_social_score": 8.5,
        "visual_analysis": {
            "frames_analyzed": 3600,
            "face_detection": {
                "frames_with_faces": 2800,
                "eye_contact_percentage": 75.5
            },
            "shot_types": {
                "close_up": 1200,
                "medium": 1800,
                "wide": 600
            }
        },
        "audio_analysis": {
            "speech_rate": 150,  # words per minute
            "pauses": [
                {"start": 10.5, "duration": 2.0},
                {"start": 45.2, "duration": 1.5}
            ],
            "volume_peaks": [
                {"timestamp": 5.0, "intensity": 0.85},
                {"timestamp": 30.0, "intensity": 0.92}
            ]
        },
        "highlights": {
            "selected": [
                {
                    "start_time": 0.0,
                    "end_time": 15.0,
                    "score": 0.92,
                    "reasoning": "Strong hook with visual engagement",
                    "gpt_reasoning": "This opening segment has high engagement potential due to immediate visual interest and clear hook structure."
                },
                {
                    "start_time": 28.0,
                    "end_time": 48.0,
                    "score": 0.88,
                    "reasoning": "Key moment with peak engagement",
                    "gpt_reasoning": "This segment contains the main value proposition with high visual and audio engagement."
                }
            ],
            "all_ranked": [],
            "report": "Found 2 high-quality highlights suitable for short-form content"
        }
    }
    
    await db_session.commit()
    await db_session.refresh(video)
    
    return video


@pytest_asyncio.fixture
async def video_with_viral_analysis_data(db_session: AsyncSession):
    """Create a video with full word-level and frame-level analysis"""
    video_id = uuid.uuid4()
    
    # Create video in videos table
    video = Video(
        id=video_id,
        file_name="viral_test_video.mp4",
        source_uri="/tmp/viral_test_video.mp4",
        source_type="local",
        duration_sec=90,
        user_id=uuid.uuid4(),
        created_at=datetime.utcnow()
    )
    
    db_session.add(video)
    await db_session.flush()
    
    # Add comprehensive word-level data
    transcript_text = "This is an amazing video that demonstrates viral potential. Watch this incredible content that will blow your mind!"
    words = transcript_text.split()
    
    word_data_list = []
    current_time = 0.0
    for idx, word in enumerate(words):
        word_duration = 0.3 + (len(word) * 0.05)  # Variable duration based on word length
        word_data_list.append({
            "video_id": str(video_id),
            "word_index": idx,
            "word": word,
            "start_s": current_time,
            "end_s": current_time + word_duration,
            "is_emphasis": word.lower() in ["amazing", "incredible", "blow"],
            "is_cta_keyword": word.lower() in ["watch", "check"],
            "is_question": word.endswith("?"),
            "speech_function": "statement",
            "sentiment_score": 0.7 if word.lower() in ["amazing", "incredible"] else 0.5,
            "emotion": "excited" if word.lower() in ["amazing", "incredible"] else "neutral"
        })
        current_time += word_duration + 0.1  # Small pause between words
    
    # Batch insert words
    for word_data in word_data_list:
        await db_session.execute(
            text("""
                INSERT INTO video_words 
                (video_id, word_index, word, start_s, end_s, is_emphasis, is_cta_keyword, 
                 is_question, speech_function, sentiment_score, emotion)
                VALUES (:video_id, :word_index, :word, :start_s, :end_s, :is_emphasis, 
                        :is_cta_keyword, :is_question, :speech_function, :sentiment_score, :emotion)
            """),
            word_data
        )
    
    # Add comprehensive frame-level data
    fps = 30
    total_frames = int(90 * fps)  # 90 seconds at 30 fps
    
    # Insert frames in batches
    frame_batch = []
    for frame_num in range(0, min(total_frames, 100)):  # Limit to 100 frames for test
        timestamp = frame_num / fps
        frame_batch.append({
            "video_id": str(video_id),
            "frame_number": frame_num,
            "timestamp_s": timestamp,
            "shot_type": "close_up" if frame_num % 60 < 30 else "medium",
            "has_face": frame_num % 10 < 7,  # 70% of frames have faces
            "face_count": 1 if frame_num % 10 < 7 else 0,
            "eye_contact": frame_num % 10 < 5,  # 50% eye contact
            "has_text": frame_num % 20 < 2,  # 10% have text
            "visual_clutter_score": 0.3 + (frame_num % 10) * 0.05,
            "contrast_score": 0.6 + (frame_num % 10) * 0.03,
            "motion_score": 0.4 + (frame_num % 10) * 0.04,
            "scene_change": frame_num % 90 == 0 and frame_num > 0
        })
    
    # Insert frames
    for frame_data in frame_batch:
        await db_session.execute(
            text("""
                INSERT INTO video_frames
                (video_id, frame_number, timestamp_s, shot_type, has_face, face_count,
                 eye_contact, has_text, visual_clutter_score, contrast_score, motion_score, scene_change)
                VALUES (:video_id, :frame_number, :timestamp_s, :shot_type, :has_face, :face_count,
                        :eye_contact, :has_text, :visual_clutter_score, :contrast_score, :motion_score, :scene_change)
            """),
            frame_data
        )
    
    await db_session.commit()
    await db_session.refresh(video)
    
    return video


class TestAnalysisResultsWithRealData:
    """Test /api/analysis/results with real video data"""
    
    @pytest.mark.asyncio
    async def test_list_analysis_results_with_real_video(
        self, client, db_session, video_with_full_analysis
    ):
        """Test listing analysis results with a real video that has full analysis"""
        await db_session.commit()
        
        response = client.get("/api/analysis/results")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        assert data["total"] > 0
        
        # Find our test video
        test_video = next(
            (v for v in data["videos"] if v["video_id"] == str(video_with_full_analysis.video_id)),
            None
        )
        
        if test_video:
            assert test_video["has_analysis"] is True
            assert len(test_video["analysis_keys"]) > 0
            assert "transcript" in test_video["analysis_keys"]
            assert "topics" in test_video["analysis_keys"]
            assert "highlights" in test_video["analysis_keys"]
    
    @pytest.mark.asyncio
    async def test_get_analysis_results_detail(
        self, client, db_session, video_with_full_analysis
    ):
        """Test getting detailed analysis results for a specific video"""
        await db_session.commit()
        
        video_id = video_with_full_analysis.video_id
        
        response = client.get(f"/api/analysis/results/{video_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "video_id" in data
        assert "video_name" in data
        assert "analysis" in data
        
        analysis = data["analysis"]
        assert "transcript" in analysis
        assert "topics" in analysis
        assert "hooks" in analysis
        assert "key_moments" in analysis
        assert "pre_social_score" in analysis
        assert "visual_analysis" in analysis
        assert "audio_analysis" in analysis
        assert "highlights" in analysis
        
        # Verify transcript structure
        assert "text" in analysis["transcript"]
        assert "segments" in analysis["transcript"]
        assert len(analysis["transcript"]["segments"]) > 0
        
        # Verify highlights structure
        assert "selected" in analysis["highlights"]
        assert len(analysis["highlights"]["selected"]) > 0
        highlight = analysis["highlights"]["selected"][0]
        assert "start_time" in highlight
        assert "end_time" in highlight
        assert "score" in highlight
        assert "reasoning" in highlight


class TestHighlightsResultsWithRealData:
    """Test /api/highlights/results with real video data"""
    
    @pytest.mark.asyncio
    async def test_list_highlights_with_real_video(
        self, client, db_session, video_with_full_analysis
    ):
        """Test listing highlights with a real video"""
        await db_session.commit()
        
        response = client.get("/api/highlights/results")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        
        # Find our test video
        test_video = next(
            (v for v in data["videos"] if v["video_id"] == str(video_with_full_analysis.video_id)),
            None
        )
        
        if test_video:
            assert test_video["has_highlights"] is True
            assert test_video["highlight_count"] > 0
    
    @pytest.mark.asyncio
    async def test_get_highlights_detail(
        self, client, db_session, video_with_full_analysis
    ):
        """Test getting detailed highlights for a specific video"""
        await db_session.commit()
        
        video_id = video_with_full_analysis.video_id
        
        response = client.get(f"/api/highlights/results/{video_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "video_id" in data
        assert "highlights" in data
        
        highlights = data["highlights"]
        assert "selected" in highlights
        assert len(highlights["selected"]) > 0
        
        # Verify highlight structure
        highlight = highlights["selected"][0]
        assert "start_time" in highlight
        assert "end_time" in highlight
        assert "score" in highlight
        assert "reasoning" in highlight
        assert "gpt_reasoning" in highlight


class TestViralAnalysisWithRealData:
    """Test /api/viral-analysis/videos with real word and frame data"""
    
    @pytest.mark.asyncio
    async def test_list_viral_analysis_with_real_data(
        self, client, db_session, video_with_viral_analysis_data
    ):
        """Test listing viral analysis videos with real word and frame data"""
        await db_session.commit()
        
        response = client.get("/api/viral-analysis/videos")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        
        # Find our test video
        test_video = next(
            (v for v in data["videos"] if v["video_id"] == str(video_with_viral_analysis_data.id)),
            None
        )
        
        if test_video:
            assert test_video["word_count"] > 0
            assert test_video["frame_count"] > 0
            assert test_video["analyzed"] is True
    
    @pytest.mark.asyncio
    async def test_get_video_words(
        self, client, db_session, video_with_viral_analysis_data
    ):
        """Test getting word-level data for a video"""
        await db_session.commit()
        
        video_id = video_with_viral_analysis_data.id
        
        response = client.get(f"/api/viral-analysis/videos/{video_id}/words")
        assert response.status_code == 200
        data = response.json()
        
        assert "video_id" in data
        assert "word_count" in data
        assert "words" in data
        assert data["word_count"] > 0
        assert len(data["words"]) > 0
        
        # Verify word structure
        word = data["words"][0]
        assert "word_index" in word
        assert "word" in word
        assert "start_s" in word
        assert "end_s" in word
        assert "is_emphasis" in word
        assert "is_cta_keyword" in word
    
    @pytest.mark.asyncio
    async def test_get_video_frames(
        self, client, db_session, video_with_viral_analysis_data
    ):
        """Test getting frame-level data for a video"""
        await db_session.commit()
        
        video_id = video_with_viral_analysis_data.id
        
        response = client.get(f"/api/viral-analysis/videos/{video_id}/frames")
        assert response.status_code == 200
        data = response.json()
        
        assert "video_id" in data
        assert "frame_count" in data
        assert "frames" in data
        assert data["frame_count"] > 0
        assert len(data["frames"]) > 0
        
        # Verify frame structure
        frame = data["frames"][0]
        assert "frame_number" in frame
        assert "timestamp_s" in frame
        assert "shot_type" in frame
        assert "has_face" in frame
        assert "face_count" in frame
        assert "eye_contact" in frame
    
    @pytest.mark.asyncio
    async def test_get_video_metrics(
        self, client, db_session, video_with_viral_analysis_data
    ):
        """Test getting aggregate metrics for a video"""
        await db_session.commit()
        
        video_id = video_with_viral_analysis_data.id
        
        response = client.get(f"/api/viral-analysis/videos/{video_id}/metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert "video_id" in data
        assert "pacing" in data
        assert "composition" in data
        assert "shot_distribution" in data
        
        # Verify pacing metrics
        assert "total_words" in data["pacing"]
        assert "words_per_minute" in data["pacing"]
        assert "emphasis_word_count" in data["pacing"]
        
        # Verify composition metrics
        assert "total_frames" in data["composition"]
        assert "face_presence_pct" in data["composition"]
        assert "eye_contact_pct" in data["composition"]


class TestEndpointsWithExistingVideos:
    """Test endpoints using existing videos from the database"""
    
    @pytest.mark.asyncio
    async def test_analysis_results_with_existing_videos(
        self, client, db_session, real_original_video_from_db
    ):
        """Test analysis results endpoint with existing videos from database"""
        if not real_original_video_from_db:
            pytest.skip("No existing videos in database")
        
        # Add analysis data to existing video
        if not real_original_video_from_db.analysis_data:
            real_original_video_from_db.analysis_data = {
                "transcript": "Test transcript for existing video",
                "topics": ["test"],
                "pre_social_score": 6.0
            }
            await db_session.commit()
        
        response = client.get("/api/analysis/results")
        assert response.status_code == 200
        data = response.json()
        
        # Should include our existing video
        video_ids = [v["video_id"] for v in data["videos"]]
        assert str(real_original_video_from_db.video_id) in video_ids
    
    @pytest.mark.asyncio
    async def test_manipulate_video_analysis_data(
        self, client, db_session, real_original_video_from_db
    ):
        """Test manipulating live video analysis data"""
        if not real_original_video_from_db:
            pytest.skip("No existing videos in database")
        
        video = real_original_video_from_db
        video_id = video.video_id
        
        # Add comprehensive analysis data
        video.analysis_data = {
            "transcript": "Manipulated transcript for testing",
            "topics": ["manipulation", "testing"],
            "hooks": ["Test hook"],
            "pre_social_score": 7.0,
            "highlights": {
                "selected": [
                    {
                        "start_time": 0.0,
                        "end_time": 10.0,
                        "score": 0.8,
                        "reasoning": "Test highlight"
                    }
                ]
            }
        }
        
        await db_session.commit()
        await db_session.refresh(video)
        
        # Verify the data was saved
        response = client.get(f"/api/analysis/results/{video_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["analysis"]["transcript"] == "Manipulated transcript for testing"
        assert len(data["analysis"]["highlights"]["selected"]) == 1


class TestFullDataStructures:
    """Test endpoints with complete, realistic data structures"""
    
    @pytest.mark.asyncio
    async def test_complete_analysis_data_structure(
        self, client, db_session
    ):
        """Test with a complete, realistic analysis data structure"""
        video_id = uuid.uuid4()
        
        video = OriginalVideo(
            video_id=video_id,
            file_name="complete_analysis_test.mp4",
            file_path="/tmp/complete_analysis_test.mp4",
            duration_seconds=180.0,
            file_size_bytes=5120000,
            analysis_data={
                # Complete transcript structure
                "transcript": {
                    "text": "Full transcript text here...",
                    "duration": 180.0,
                    "language": "en",
                    "segments": [
                        {
                            "id": 0,
                            "start": 0.0,
                            "end": 10.0,
                            "text": "Segment 1",
                            "words": [
                                {"word": "Full", "start": 0.0, "end": 0.3},
                                {"word": "transcript", "start": 0.3, "end": 0.8}
                            ]
                        }
                    ]
                },
                # Complete topics structure
                "topics": [
                    {"topic": "Technology", "confidence": 0.9},
                    {"topic": "Testing", "confidence": 0.85}
                ],
                # Complete hooks structure
                "hooks": [
                    {
                        "text": "You won't believe this!",
                        "timestamp": 0.0,
                        "score": 0.95,
                        "type": "curiosity"
                    }
                ],
                # Complete key moments
                "key_moments": [
                    {
                        "start": 0.0,
                        "end": 15.0,
                        "summary": "Opening hook",
                        "suggested_caption": "Starting strong!",
                        "engagement_score": 0.9
                    }
                ],
                # Complete visual analysis
                "visual_analysis": {
                    "frames_analyzed": 5400,
                    "face_detection": {
                        "total_faces_detected": 4200,
                        "unique_faces": 1,
                        "eye_contact_percentage": 78.5,
                        "face_size_distribution": {"small": 500, "medium": 2000, "large": 1700}
                    },
                    "shot_types": {
                        "close_up": 1800,
                        "medium": 2700,
                        "wide": 900
                    },
                    "scene_changes": 12,
                    "color_analysis": {
                        "dominant_colors": ["#FF5733", "#33FF57", "#3357FF"],
                        "color_temperature": "warm"
                    }
                },
                # Complete audio analysis
                "audio_analysis": {
                    "speech_rate": 160,
                    "pauses": [
                        {"start": 10.5, "duration": 2.0, "type": "natural"},
                        {"start": 45.2, "duration": 1.5, "type": "dramatic"}
                    ],
                    "volume_peaks": [
                        {"timestamp": 5.0, "intensity": 0.85, "type": "emphasis"},
                        {"timestamp": 30.0, "intensity": 0.92, "type": "climax"}
                    ],
                    "background_music": {
                        "detected": True,
                        "volume_level": 0.3,
                        "genre": "upbeat"
                    }
                },
                # Complete highlights
                "highlights": {
                    "selected": [
                        {
                            "start_time": 0.0,
                            "end_time": 15.0,
                            "score": 0.92,
                            "reasoning": "Strong hook",
                            "gpt_reasoning": "Excellent opening with immediate engagement",
                            "metrics": {
                                "engagement_potential": 0.9,
                                "shareability": 0.85,
                                "viral_score": 0.88
                            }
                        }
                    ],
                    "all_ranked": [],
                    "report": "Comprehensive highlight analysis complete"
                },
                "pre_social_score": 8.5,
                "post_social_score": None,  # Will be updated after posting
                "analyzed_at": datetime.utcnow().isoformat()
            }
        )
        
        db_session.add(video)
        await db_session.commit()
        await db_session.refresh(video)
        
        # Test that all endpoints can handle this complete structure
        response = client.get(f"/api/analysis/results/{video_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify all nested structures are present
        assert "transcript" in data["analysis"]
        assert "segments" in data["analysis"]["transcript"]
        assert "visual_analysis" in data["analysis"]
        assert "face_detection" in data["analysis"]["visual_analysis"]
        assert "audio_analysis" in data["analysis"]
        assert "highlights" in data["analysis"]
        assert "selected" in data["analysis"]["highlights"]
        
        # Verify highlights endpoint
        response = client.get(f"/api/highlights/results/{video_id}")
        assert response.status_code == 200
        highlights_data = response.json()
        assert len(highlights_data["highlights"]["selected"]) > 0


class TestDataManipulation:
    """Test manipulating live video data"""
    
    @pytest.mark.asyncio
    async def test_add_analysis_to_existing_video(
        self, client, db_session, real_original_video_from_db
    ):
        """Test adding analysis data to an existing video"""
        if not real_original_video_from_db:
            pytest.skip("No existing videos in database")
        
        video = real_original_video_from_db
        
        # Add analysis if it doesn't exist
        if not video.analysis_data:
            video.analysis_data = {}
        
        video.analysis_data.update({
            "transcript": "Added transcript",
            "topics": ["added", "test"],
            "pre_social_score": 7.5
        })
        
        await db_session.commit()
        await db_session.refresh(video)
        
        # Verify it was added
        response = client.get(f"/api/analysis/results/{video.video_id}")
        assert response.status_code == 200
        assert "transcript" in response.json()["analysis"]
    
    @pytest.mark.asyncio
    async def test_update_highlights_for_existing_video(
        self, client, db_session, real_original_video_from_db
    ):
        """Test updating highlights for an existing video"""
        if not real_original_video_from_db:
            pytest.skip("No existing videos in database")
        
        video = real_original_video_from_db
        
        # Ensure analysis_data exists
        if not video.analysis_data:
            video.analysis_data = {}
        
        # Add/update highlights
        video.analysis_data["highlights"] = {
            "selected": [
                {
                    "start_time": 5.0,
                    "end_time": 20.0,
                    "score": 0.9,
                    "reasoning": "Updated highlight",
                    "gpt_reasoning": "This is an updated highlight with new reasoning"
                }
            ],
            "all_ranked": [],
            "report": "Updated highlight analysis"
        }
        
        await db_session.commit()
        await db_session.refresh(video)
        
        # Verify highlights were updated
        response = client.get(f"/api/highlights/results/{video.video_id}")
        assert response.status_code == 200
        highlights = response.json()["highlights"]["selected"]
        assert len(highlights) == 1
        assert highlights[0]["start_time"] == 5.0







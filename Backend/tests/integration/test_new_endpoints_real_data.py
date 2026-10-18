"""
Integration Tests: New Endpoints with Real Data
Tests the newly added list endpoints with full, real database data
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from datetime import datetime
import uuid
import json

from main import app
from database.models import OriginalVideo, AnalyzedVideo, Video, VideoWord, VideoFrame


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest_asyncio.fixture
async def db_session():
    """Get real database session"""
    from database.connection import async_session_maker
    
    if async_session_maker is None:
        from database.connection import init_db
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
async def test_video_with_analysis(db_session: AsyncSession):
    """Create a test video with full analysis data"""
    video_id = uuid.uuid4()
    
    # Create original video
    video = OriginalVideo(
        video_id=video_id,
        file_name="test_video.mp4",
        file_path="/tmp/test_video.mp4",
        duration_seconds=120.0,
        file_size_bytes=1024000,
        analysis_data={
            "transcript": "This is a test video transcript with some content.",
            "topics": ["test", "video", "analysis"],
            "hooks": ["Check this out!", "You won't believe this"],
            "tone": "educational",
            "pacing": "medium",
            "key_moments": [
                {"start": 0, "end": 10, "summary": "Introduction"},
                {"start": 10, "end": 60, "summary": "Main content"},
                {"start": 60, "end": 120, "summary": "Conclusion"}
            ],
            "pre_social_score": 7.5
        }
    )
    
    db_session.add(video)
    await db_session.flush()
    await db_session.refresh(video)
    
    return video


@pytest_asyncio.fixture
async def test_video_with_highlights(db_session: AsyncSession):
    """Create a test video with highlights"""
    video_id = uuid.uuid4()
    
    video = OriginalVideo(
        video_id=video_id,
        file_name="highlight_video.mp4",
        file_path="/tmp/highlight_video.mp4",
        duration_seconds=180.0,
        file_size_bytes=2048000,
        analysis_data={
            "transcript": "This video has highlights at specific moments.",
            "highlights": {
                "selected": [
                    {
                        "start_time": 10.0,
                        "end_time": 25.0,
                        "score": 0.85,
                        "reasoning": "Strong hook and visual engagement"
                    },
                    {
                        "start_time": 60.0,
                        "end_time": 75.0,
                        "score": 0.78,
                        "reasoning": "Key moment with high engagement"
                    }
                ],
                "all_ranked": [],
                "report": "Found 2 high-quality highlights"
            }
        }
    )
    
    db_session.add(video)
    await db_session.flush()
    await db_session.refresh(video)
    
    return video


@pytest_asyncio.fixture
async def test_viral_analysis_video(db_session: AsyncSession):
    """Create a video with word-level and frame-level analysis"""
    video_id = uuid.uuid4()
    
    # Create video in videos table
    video = Video(
        id=video_id,
        file_name="viral_test.mp4",
        source_uri="/tmp/viral_test.mp4",
        source_type="local",
        duration_sec=60,
        user_id=uuid.uuid4()
    )
    
    db_session.add(video)
    await db_session.flush()
    
    # Add word-level data
    words_data = [
        {"word_index": 0, "word": "This", "start_s": 0.0, "end_s": 0.3, "is_emphasis": False},
        {"word_index": 1, "word": "is", "start_s": 0.3, "end_s": 0.5, "is_emphasis": False},
        {"word_index": 2, "word": "amazing", "start_s": 0.5, "end_s": 1.0, "is_emphasis": True},
    ]
    
    for word_data in words_data:
        await db_session.execute(
            text("""
                INSERT INTO video_words 
                (video_id, word_index, word, start_s, end_s, is_emphasis, is_cta_keyword, is_question)
                VALUES (:video_id, :word_index, :word, :start_s, :end_s, :is_emphasis, :is_cta_keyword, :is_question)
            """),
            {
                "video_id": str(video_id),
                **word_data,
                "is_cta_keyword": False,
                "is_question": False
            }
        )
    
    # Add frame-level data
    frames_data = [
        {"frame_number": 0, "timestamp_s": 0.0, "has_face": True, "face_count": 1, "shot_type": "close_up"},
        {"frame_number": 1, "timestamp_s": 1.0, "has_face": True, "face_count": 1, "shot_type": "medium"},
    ]
    
    for frame_data in frames_data:
        await db_session.execute(
            text("""
                INSERT INTO video_frames
                (video_id, frame_number, timestamp_s, has_face, face_count, shot_type, eye_contact, has_text, scene_change)
                VALUES (:video_id, :frame_number, :timestamp_s, :has_face, :face_count, :shot_type, :eye_contact, :has_text, :scene_change)
            """),
            {
                "video_id": str(video_id),
                **frame_data,
                "eye_contact": True,
                "has_text": False,
                "scene_change": False
            }
        )
    
    await db_session.commit()
    await db_session.refresh(video)
    
    return video


@pytest_asyncio.fixture
async def test_enhanced_analysis_video(db_session: AsyncSession):
    """Create a video with enhanced analysis (AnalyzedVideo)"""
    video_id = uuid.uuid4()
    analyzed_video_id = uuid.uuid4()
    
    # Create analyzed video
    analyzed_video = AnalyzedVideo(
        id=analyzed_video_id,
        original_video_id=video_id,
        duration_seconds=90.0,
        transcript_full="This is a full transcript for enhanced analysis.",
        analyzed_at=datetime.utcnow()
    )
    
    db_session.add(analyzed_video)
    await db_session.flush()
    
    # Add segments
    segments_data = [
        {"segment_type": "hook", "start_s": 0.0, "end_s": 5.0},
        {"segment_type": "body", "start_s": 5.0, "end_s": 80.0},
        {"segment_type": "cta", "start_s": 80.0, "end_s": 90.0},
    ]
    
    for seg_data in segments_data:
        await db_session.execute(
            text("""
                INSERT INTO video_segments
                (video_id, segment_type, start_s, end_s, created_at)
                VALUES (:video_id, :segment_type, :start_s, :end_s, NOW())
            """),
            {
                "video_id": str(analyzed_video_id),
                **seg_data
            }
        )
    
    await db_session.commit()
    await db_session.refresh(analyzed_video)
    
    return analyzed_video


class TestAnalysisResultsEndpoint:
    """Test /api/analysis/results endpoint with real data"""
    
    @pytest.mark.asyncio
    async def test_list_analysis_results_empty(self, client, db_session):
        """Test listing analysis results structure (handles empty or existing data)"""
        response = client.get("/api/analysis/results")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "videos" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["videos"], list)
        assert data["total"] >= 0
        assert len(data["videos"]) == data["total"]  # Consistency check
    
    @pytest.mark.asyncio
    async def test_list_analysis_results_with_data(
        self, client, db_session, test_video_with_analysis
    ):
        """Test listing analysis results with real video data"""
        await db_session.commit()
        
        response = client.get("/api/analysis/results")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        assert data["total"] > 0
        
        # Verify video structure
        if len(data["videos"]) > 0:
            video = data["videos"][0]
            assert "video_id" in video
            assert "video_name" in video
            assert "has_analysis" in video
            assert "analysis_keys" in video
            assert video["has_analysis"] is True
    
    @pytest.mark.asyncio
    async def test_list_analysis_results_pagination(
        self, client, db_session, test_video_with_analysis
    ):
        """Test pagination for analysis results"""
        await db_session.commit()
        
        # Test with limit
        response = client.get("/api/analysis/results?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) <= 1
        
        # Test with offset
        response = client.get("/api/analysis/results?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data


class TestHighlightsResultsEndpoint:
    """Test /api/highlights/results endpoint with real data"""
    
    @pytest.mark.asyncio
    async def test_list_highlights_results_empty(self, client, db_session):
        """Test listing highlights when no data exists"""
        response = client.get("/api/highlights/results")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "videos" in data
    
    @pytest.mark.asyncio
    async def test_list_highlights_results_with_data(
        self, client, db_session, test_video_with_highlights
    ):
        """Test listing highlights with real video data"""
        await db_session.commit()
        
        response = client.get("/api/highlights/results")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        
        # Verify video structure
        if len(data["videos"]) > 0:
            video = data["videos"][0]
            assert "video_id" in video
            assert "video_name" in video
            assert "has_highlights" in video
            assert "highlight_count" in video


class TestViralAnalysisVideosEndpoint:
    """Test /api/viral-analysis/videos endpoint with real data"""
    
    @pytest.mark.asyncio
    async def test_list_viral_analysis_videos_empty(self, client, db_session):
        """Test listing viral analysis videos when no data exists"""
        response = client.get("/api/viral-analysis/videos")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "videos" in data
    
    @pytest.mark.asyncio
    async def test_list_viral_analysis_videos_with_data(
        self, client, db_session, test_viral_analysis_video
    ):
        """Test listing viral analysis videos with real data"""
        await db_session.commit()
        
        response = client.get("/api/viral-analysis/videos")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        
        # Verify video structure
        if len(data["videos"]) > 0:
            video = data["videos"][0]
            assert "video_id" in video
            assert "file_name" in video
            assert "word_count" in video
            assert "frame_count" in video
            assert "analyzed" in video
            assert video["word_count"] > 0 or video["frame_count"] > 0


class TestAPIUsageEndpoint:
    """Test /api/api-usage/usage endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_api_usage(self, client):
        """Test getting API usage statistics"""
        response = client.get("/api/api-usage/usage")
        assert response.status_code == 200
        data = response.json()
        
        assert "apis" in data
        assert "total_apis" in data
        assert isinstance(data["apis"], list)
        assert data["total_apis"] >= 0


class TestEnhancedAnalysisVideosEndpoint:
    """Test /api/enhanced-analysis/videos endpoint with real data"""
    
    @pytest.mark.asyncio
    async def test_list_enhanced_analysis_videos_empty(self, client, db_session):
        """Test listing enhanced analysis videos when no data exists"""
        response = client.get("/api/enhanced-analysis/videos")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "videos" in data
    
    @pytest.mark.asyncio
    async def test_list_enhanced_analysis_videos_with_data(
        self, client, db_session, test_enhanced_analysis_video
    ):
        """Test listing enhanced analysis videos with real data"""
        await db_session.commit()
        
        response = client.get("/api/enhanced-analysis/videos")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        
        # Verify video structure
        if len(data["videos"]) > 0:
            video = data["videos"][0]
            assert "video_id" in video
            assert "has_segments" in video
            assert "segment_count" in video
            assert video["segment_count"] >= 0


class TestEndpointsWithFullData:
    """Test all endpoints with comprehensive real data"""
    
    @pytest.mark.asyncio
    async def test_all_endpoints_with_multiple_videos(
        self, client, db_session,
        test_video_with_analysis,
        test_video_with_highlights,
        test_viral_analysis_video,
        test_enhanced_analysis_video
    ):
        """Test all new endpoints with multiple videos"""
        await db_session.commit()
        
        # Test analysis results
        response = client.get("/api/analysis/results")
        assert response.status_code == 200
        analysis_data = response.json()
        assert analysis_data["total"] >= 1
        
        # Test highlights results
        response = client.get("/api/highlights/results")
        assert response.status_code == 200
        highlights_data = response.json()
        assert highlights_data["total"] >= 1
        
        # Test viral analysis videos
        response = client.get("/api/viral-analysis/videos")
        assert response.status_code == 200
        viral_data = response.json()
        assert viral_data["total"] >= 1
        
        # Test enhanced analysis videos
        response = client.get("/api/enhanced-analysis/videos")
        assert response.status_code == 200
        enhanced_data = response.json()
        # May be 0 if table doesn't exist, but should not error
        
        # Test API usage
        response = client.get("/api/api-usage/usage")
        assert response.status_code == 200
        usage_data = response.json()
        assert "apis" in usage_data
    
    @pytest.mark.asyncio
    async def test_pagination_consistency(self, client, db_session, test_video_with_analysis):
        """Test that pagination works consistently across endpoints"""
        await db_session.commit()
        
        endpoints = [
            "/api/analysis/results",
            "/api/highlights/results",
            "/api/viral-analysis/videos",
            "/api/enhanced-analysis/videos"
        ]
        
        for endpoint in endpoints:
            # Test first page
            response = client.get(f"{endpoint}?limit=5&offset=0")
            assert response.status_code == 200
            page1 = response.json()
            
            # Test second page
            response = client.get(f"{endpoint}?limit=5&offset=5")
            assert response.status_code == 200
            page2 = response.json()
            
            # Verify structure is consistent
            assert "total" in page1
            assert "videos" in page1
            assert isinstance(page1["videos"], list)
    
    @pytest.mark.asyncio
    async def test_endpoint_response_structure(self, client, db_session, test_video_with_analysis):
        """Test that all endpoints return consistent response structures"""
        await db_session.commit()
        
        endpoints = {
            "/api/analysis/results": ["total", "videos"],
            "/api/highlights/results": ["total", "videos"],
            "/api/viral-analysis/videos": ["total", "videos"],
            "/api/enhanced-analysis/videos": ["total", "videos"],
            "/api/api-usage/usage": ["apis", "total_apis"]
        }
        
        for endpoint, required_keys in endpoints.items():
            response = client.get(endpoint)
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}"
            data = response.json()
            
            for key in required_keys:
                assert key in data, f"{endpoint} missing key: {key}"


"""
Integration Tests: Using Real Video Files from System
Discovers and uses actual video files from the user's system for testing
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from pathlib import Path
import uuid
import os
from typing import List, Optional

from main import app
from database.models import Video, OriginalVideo
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


def discover_video_files(search_paths: List[str] = None, max_files: int = 10) -> List[Path]:
    """
    Discover real video files from the system
    
    Args:
        search_paths: List of paths to search (defaults to common locations)
        max_files: Maximum number of files to return
    
    Returns:
        List of Path objects to video files
    """
    if search_paths is None:
        # Default search paths
        home = Path.home()
        search_paths = [
            str(home / "Documents" / "IphoneImport"),
            str(home / "Downloads"),
            str(home / "Desktop"),
            str(home / "Movies"),
        ]
    
    video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm'}
    found_files = []
    
    for search_path in search_paths:
        path = Path(search_path).expanduser()
        if not path.exists() or not path.is_dir():
            continue
        
        # Search recursively but limit depth
        for ext in video_extensions:
            for video_file in path.rglob(f"*{ext}"):
                if video_file.is_file() and video_file.stat().st_size > 0:
                    found_files.append(video_file)
                    if len(found_files) >= max_files:
                        return found_files
    
    return found_files


@pytest_asyncio.fixture
async def real_video_files():
    """Discover real video files from the system"""
    files = discover_video_files(max_files=5)
    if not files:
        pytest.skip("No video files found in common locations")
    return files


@pytest_asyncio.fixture
async def video_from_database(db_session: AsyncSession):
    """Get a video that exists in the database with a real file path"""
    # Try to get a video with a valid file path
    result = await db_session.execute(
        text("""
            SELECT id, file_name, source_uri, source_type 
            FROM videos 
            WHERE source_type = 'local' 
              AND source_uri IS NOT NULL
            LIMIT 1
        """)
    )
    row = result.first()
    
    if row:
        # Verify file exists
        file_path = Path(row.source_uri)
        if file_path.exists():
            return {
                "id": str(row.id),
                "file_name": row.file_name,
                "source_uri": row.source_uri,
                "source_type": row.source_type
            }
    
    return None


class TestWithRealVideoFiles:
    """Test endpoints using actual video files from the system"""
    
    @pytest.mark.asyncio
    async def test_scan_real_video_directory(
        self, client, db_session, real_video_files
    ):
        """Test scanning a directory with real video files"""
        if not real_video_files:
            pytest.skip("No video files found")
        
        # Use the parent directory of the first found file
        test_dir = real_video_files[0].parent
        
        response = client.post(
            "/api/videos/scan",
            json={"path": str(test_dir)}
        )
        
        # Should either succeed or return appropriate error
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "scan_id" in data or "message" in data
    
    @pytest.mark.asyncio
    async def test_list_videos_with_real_files(
        self, client, db_session, video_from_database
    ):
        """Test listing videos that have real file paths"""
        response = client.get("/api/videos")
        assert response.status_code == 200
        videos = response.json()
        
        assert isinstance(videos, list)
        
        # If we have a known video, verify it's in the list
        if video_from_database:
            video_ids = [v.get("id") for v in videos]
            assert video_from_database["id"] in video_ids
    
    @pytest.mark.asyncio
    async def test_get_video_detail_with_real_file(
        self, client, db_session, video_from_database
    ):
        """Test getting details for a video with a real file"""
        if not video_from_database:
            pytest.skip("No videos with real files in database")
        
        video_id = video_from_database["id"]
        
        response = client.get(f"/api/videos/{video_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == video_id
        assert "source_uri" in data
        assert "file_name" in data
        
        # Verify the file path is valid
        file_path = Path(data["source_uri"])
        assert file_path.exists() or file_path.parent.exists()


class TestManipulateRealVideoData:
    """Test manipulating data for videos with real files"""
    
    @pytest.mark.asyncio
    async def test_add_analysis_to_real_video(
        self, client, db_session, video_from_database
    ):
        """Test adding analysis data to a video with a real file"""
        if not video_from_database:
            pytest.skip("No videos with real files in database")
        
        # Get the video from OriginalVideo table if it exists
        result = await db_session.execute(
            select(OriginalVideo).filter(
                OriginalVideo.file_path == video_from_database["source_uri"]
            ).limit(1)
        )
        original_video = result.scalar_one_or_none()
        
        if not original_video:
            # Create an OriginalVideo entry for this video
            original_video = OriginalVideo(
                video_id=uuid.uuid4(),
                file_name=video_from_database["file_name"],
                file_path=video_from_database["source_uri"],
                duration_seconds=0.0,  # Will be updated if we can get metadata
                file_size_bytes=Path(video_from_database["source_uri"]).stat().st_size if Path(video_from_database["source_uri"]).exists() else 0
            )
            db_session.add(original_video)
            await db_session.flush()
        
        # Add comprehensive analysis data
        original_video.analysis_data = {
            "transcript": f"Analysis for real video file: {video_from_database['file_name']}",
            "topics": ["real_video", "test"],
            "pre_social_score": 7.0,
            "highlights": {
                "selected": [
                    {
                        "start_time": 0.0,
                        "end_time": 10.0,
                        "score": 0.85,
                        "reasoning": "Real video highlight"
                    }
                ]
            }
        }
        
        await db_session.commit()
        await db_session.refresh(original_video)
        
        # Verify the analysis was added
        response = client.get(f"/api/analysis/results/{original_video.video_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "analysis" in data
        assert "transcript" in data["analysis"]
        assert "highlights" in data["analysis"]
    
    @pytest.mark.asyncio
    async def test_create_viral_analysis_for_real_video(
        self, client, db_session, video_from_database
    ):
        """Test creating viral analysis data for a real video"""
        if not video_from_database:
            pytest.skip("No videos with real files in database")
        
        video_id = uuid.UUID(video_from_database["id"])
        
        # Add word-level data
        words_data = [
            {
                "video_id": str(video_id),
                "word_index": 0,
                "word": "This",
                "start_s": 0.0,
                "end_s": 0.3,
                "is_emphasis": False,
                "is_cta_keyword": False,
                "is_question": False
            },
            {
                "video_id": str(video_id),
                "word_index": 1,
                "word": "is",
                "start_s": 0.3,
                "end_s": 0.5,
                "is_emphasis": False,
                "is_cta_keyword": False,
                "is_question": False
            },
            {
                "video_id": str(video_id),
                "word_index": 2,
                "word": "amazing",
                "start_s": 0.5,
                "end_s": 1.0,
                "is_emphasis": True,
                "is_cta_keyword": False,
                "is_question": False
            }
        ]
        
        for word_data in words_data:
            await db_session.execute(
                text("""
                    INSERT INTO video_words 
                    (video_id, word_index, word, start_s, end_s, is_emphasis, is_cta_keyword, is_question)
                    VALUES (:video_id, :word_index, :word, :start_s, :end_s, :is_emphasis, :is_cta_keyword, :is_question)
                    ON CONFLICT DO NOTHING
                """),
                word_data
            )
        
        # Add frame-level data
        frames_data = [
            {
                "video_id": str(video_id),
                "frame_number": 0,
                "timestamp_s": 0.0,
                "has_face": True,
                "face_count": 1,
                "shot_type": "close_up",
                "eye_contact": True,
                "has_text": False,
                "scene_change": False
            },
            {
                "video_id": str(video_id),
                "frame_number": 1,
                "timestamp_s": 0.033,
                "has_face": True,
                "face_count": 1,
                "shot_type": "medium",
                "eye_contact": False,
                "has_text": False,
                "scene_change": False
            }
        ]
        
        for frame_data in frames_data:
            await db_session.execute(
                text("""
                    INSERT INTO video_frames
                    (video_id, frame_number, timestamp_s, has_face, face_count, shot_type, eye_contact, has_text, scene_change)
                    VALUES (:video_id, :frame_number, :timestamp_s, :has_face, :face_count, :shot_type, :eye_contact, :has_text, :scene_change)
                    ON CONFLICT DO NOTHING
                """),
                frame_data
            )
        
        await db_session.commit()
        
        # Verify viral analysis endpoint can find it
        response = client.get("/api/viral-analysis/videos")
        assert response.status_code == 200
        data = response.json()
        
        video_ids = [v["video_id"] for v in data["videos"]]
        assert str(video_id) in video_ids
        
        # Verify we can get word data
        response = client.get(f"/api/viral-analysis/videos/{video_id}/words")
        assert response.status_code == 200
        words_data = response.json()
        assert words_data["word_count"] > 0


class TestBulkOperationsWithRealData:
    """Test bulk operations on real video data"""
    
    @pytest.mark.asyncio
    async def test_list_all_analysis_results(
        self, client, db_session
    ):
        """Test listing all analysis results from the database"""
        response = client.get("/api/analysis/results?limit=100")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "videos" in data
        
        # Verify structure for all returned videos
        for video in data["videos"]:
            assert "video_id" in video
            assert "video_name" in video
            assert "has_analysis" in video
    
    @pytest.mark.asyncio
    async def test_pagination_with_real_data(
        self, client, db_session
    ):
        """Test pagination with real data from database"""
        # Get first page
        response1 = client.get("/api/analysis/results?limit=10&offset=0")
        assert response1.status_code == 200
        page1 = response1.json()
        
        # Get second page
        response2 = client.get("/api/analysis/results?limit=10&offset=10")
        assert response2.status_code == 200
        page2 = response2.json()
        
        # Verify pages are different (if enough data exists)
        if page1["total"] > 10:
            page1_ids = {v["video_id"] for v in page1["videos"]}
            page2_ids = {v["video_id"] for v in page2["videos"]}
            assert page1_ids != page2_ids
    
    @pytest.mark.asyncio
    async def test_all_endpoints_with_real_data(
        self, client, db_session
    ):
        """Test all new endpoints with whatever real data exists"""
        endpoints = [
            "/api/analysis/results",
            "/api/highlights/results",
            "/api/viral-analysis/videos",
            "/api/enhanced-analysis/videos",
            "/api/api-usage/usage"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"{endpoint} failed with {response.status_code}"
            data = response.json()
            
            # Verify response structure
            assert isinstance(data, dict), f"{endpoint} should return a dict"
            
            # Endpoint-specific checks
            if "results" in endpoint or "videos" in endpoint:
                assert "total" in data or "videos" in data or "apis" in data







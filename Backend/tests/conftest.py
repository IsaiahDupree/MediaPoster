"""
Pytest configuration and fixtures
"""
import pytest
import pytest_asyncio
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Generator
import sys
import os
import asyncio
from dotenv import load_dotenv

# Configure pytest-asyncio
pytest_asyncio.fixture = pytest_asyncio.fixture

# Load environment variables from .env file
load_dotenv()

# Use REAL database for tests (not mocks)
# Ensure DATABASE_URL points to test database
if not os.getenv("DATABASE_URL"):
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")

# Set other environment variables
os.environ.setdefault("SUPABASE_URL", os.getenv("SUPABASE_URL", "https://localhost:54321"))
os.environ.setdefault("SUPABASE_KEY", os.getenv("SUPABASE_KEY", "test_key"))
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "test_key"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Fix for SQLAlchemy table redefinition issue
# Clear any previously loaded models before importing
if 'database.models' in sys.modules:
    del sys.modules['database.models']

# Import must happen AFTER the cleanup above
try:
    from database.models import Base
except ImportError:
    Base = None  # Tests will use mocks instead


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Initialize database before all tests
# Database initialization happens in db_session fixture


@pytest.fixture(scope="session", autouse=True)
def clear_sqlalchemy_registry():
    """Clear SQLAlchemy registry once before all tests"""
    if Base is not None:
        # Clear the metadata to avoid redefinition errors
        # Base.metadata.clear()
        pass
    yield


@pytest.fixture(scope="session")
def db_engine():
    """Create in-memory SQLite engine for tests"""
    if Base is None:
        pytest.skip("Database models not available")
        
    # Use in-memory SQLite with StaticPool to share connection across threads
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    return engine


@pytest_asyncio.fixture
async def db_session():
    """Get REAL database session for each test"""
    import database.connection as db_conn
    
    # Initialize database if not already initialized
    if db_conn.async_session_maker is None:
        await db_conn.init_db()
    
    # Re-import to get updated reference
    from database.connection import async_session_maker
    
    # Double-check after init
    if async_session_maker is None:
        raise RuntimeError("Failed to initialize database session maker")
    
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
async def clean_db(db_session):
    """Clean database before each test"""
    from sqlalchemy import text
    import uuid
    
    # Create a default workspace if it doesn't exist (for foreign key constraint)
    test_workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    try:
        await db_session.execute(text("""
            INSERT INTO workspaces (id, name, slug, created_at, updated_at)
            VALUES (:id, 'Test Workspace', 'test-workspace', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"id": test_workspace_id})
        await db_session.commit()
    except Exception as e:
        # Table might not exist or workspace already exists, continue
        await db_session.rollback()
        # Log but don't fail - workspace might already exist
        pass
    
    # Truncate tables (in reverse dependency order to respect foreign keys)
    tables_to_clean = [
        'media_creation_assets',
        'media_creation_projects',
        'media_creation_templates',
        'scheduled_posts',
        'video_clips',
        'video_analysis',
        'videos',
        'posting_goals',  # Goals table
        'connector_configs',
        'social_media_accounts',
        'social_media_posts',
        'social_media_post_analytics',
        'social_media_analytics_snapshots',
    ]
    
    for table in tables_to_clean:
        try:
            await db_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        except Exception:
            # Table might not exist, skip
            pass
    
    await db_session.commit()
    yield


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_video(temp_dir: Path) -> Path:
    """
    Create a sample video file for testing
    Uses FFmpeg to generate a test video
    """
    video_path = temp_dir / "test_video.mp4"
    
    # Generate a 10-second test video with FFmpeg
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=10:size=1920x1080:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=1000:duration=10',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '10',
        '-y',
        str(video_path)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        return video_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        pytest.skip(f"FFmpeg not available or failed: {e}")


@pytest.fixture
def short_video(temp_dir: Path) -> Path:
    """Create a very short video (too short to be valid)"""
    video_path = temp_dir / "short_video.mp4"
    
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=2:size=1280x720:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=1000:duration=2',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '2',
        '-y',
        str(video_path)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        return video_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("FFmpeg not available")


@pytest.fixture
def large_video(temp_dir: Path) -> Path:
    """Create a larger video file for testing"""
    video_path = temp_dir / "large_video.mp4"
    
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=30:size=1920x1080:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=1000:duration=30',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '30',
        '-y',
        str(video_path)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=60)
        return video_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("FFmpeg not available")


@pytest.fixture
def invalid_file(temp_dir: Path) -> Path:
    """Create an invalid (non-video) file"""
    file_path = temp_dir / "not_a_video.txt"
    file_path.write_text("This is not a video file")
    return file_path


@pytest.fixture
def watch_directory(temp_dir: Path) -> Path:
    """Create a directory for file watching tests"""
    watch_dir = temp_dir / "watch"
    watch_dir.mkdir()
    return watch_dir


@pytest.fixture
def mock_icloud_library(temp_dir: Path) -> Path:
    """Create a mock Photos library structure"""
    library_path = temp_dir / "Photos Library.photoslibrary"
    library_path.mkdir()
    
    # Create database directory
    db_dir = library_path / "database"
    db_dir.mkdir()
    
    # Create a dummy database file
    (db_dir / "Photos.sqlite").touch()
    
    return library_path

#!/usr/bin/env python3
"""
iPhone Media Ingestion Script with Smart Resume
Systematically ingests and analyzes all media from IphoneImport folder
with progress tracking and resume capabilities.
"""
import os
import sys
import json
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ingestion.log')
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================
IPHONE_IMPORT_PATH = Path(os.path.expanduser("~/Documents/IphoneImport"))
STATE_FILE = Path(__file__).parent / "ingestion_state.json"
SUPPORTED_VIDEO_EXTENSIONS = {'.mov', '.mp4', '.m4v', '.avi', '.mkv'}
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.webp', '.gif'}
BATCH_SIZE = 5  # Process this many files before saving state
MAX_RETRIES = 3


class MediaStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    INGESTED = "ingested"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MediaFile:
    path: str
    filename: str
    file_type: str  # 'video' or 'image'
    size_bytes: int
    modified_at: str
    file_hash: str
    status: str = MediaStatus.PENDING
    error_message: Optional[str] = None
    retry_count: int = 0
    ingested_at: Optional[str] = None
    analyzed_at: Optional[str] = None
    media_id: Optional[str] = None
    analysis_result: Optional[Dict] = None


@dataclass
class IngestionState:
    started_at: str
    last_updated: str
    total_files: int
    processed_count: int
    success_count: int
    failed_count: int
    skipped_count: int
    current_batch: int
    files: Dict[str, Dict]  # file_hash -> MediaFile as dict
    
    @classmethod
    def create_new(cls) -> 'IngestionState':
        now = datetime.now().isoformat()
        return cls(
            started_at=now,
            last_updated=now,
            total_files=0,
            processed_count=0,
            success_count=0,
            failed_count=0,
            skipped_count=0,
            current_batch=0,
            files={}
        )
    
    def save(self, path: Path = STATE_FILE):
        """Save state to JSON file."""
        self.last_updated = datetime.now().isoformat()
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2, default=str)
        logger.debug(f"State saved: {self.processed_count}/{self.total_files} processed")
    
    @classmethod
    def load(cls, path: Path = STATE_FILE) -> Optional['IngestionState']:
        """Load state from JSON file."""
        if not path.exists():
            return None
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None


def compute_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Compute MD5 hash of file for deduplication."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        # Only hash first 1MB for speed on large files
        data = f.read(1024 * 1024)
        hasher.update(data)
    return hasher.hexdigest()


def scan_directory(directory: Path) -> List[MediaFile]:
    """Scan directory for media files."""
    media_files = []
    
    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        return media_files
    
    logger.info(f"Scanning {directory}...")
    
    for file_path in directory.iterdir():
        if file_path.is_file():
            ext = file_path.suffix.lower()
            
            if ext in SUPPORTED_VIDEO_EXTENSIONS:
                file_type = 'video'
            elif ext in SUPPORTED_IMAGE_EXTENSIONS:
                file_type = 'image'
            else:
                continue
            
            try:
                stat = file_path.stat()
                file_hash = compute_file_hash(file_path)
                
                media_file = MediaFile(
                    path=str(file_path),
                    filename=file_path.name,
                    file_type=file_type,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    file_hash=file_hash
                )
                media_files.append(media_file)
                
            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")
    
    logger.info(f"Found {len(media_files)} media files")
    return media_files


class MediaIngester:
    """Handles media ingestion and analysis with resume capability."""
    
    def __init__(self, state: IngestionState):
        self.state = state
        self.db_session = None
    
    async def initialize_db(self):
        """Initialize database connection."""
        try:
            from database.connection import init_db, async_session_maker
            await init_db()
            self.async_session_maker = async_session_maker
            logger.info("Database connection initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def ingest_file(self, media_file: MediaFile) -> bool:
        """Ingest a single media file into the database."""
        # Skip non-video files for now (just mark as analyzed)
        if media_file.file_type != 'video':
            media_file.status = MediaStatus.INGESTED
            media_file.ingested_at = datetime.now().isoformat()
            return True
        
        try:
            from database.models import Video
            from sqlalchemy import select
            import uuid
            
            # Default user_id for system imports
            DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
            
            async with self.async_session_maker() as session:
                # Check if already exists by source_uri (file path)
                result = await session.execute(
                    select(Video).where(Video.source_uri == media_file.path)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Skipping duplicate: {media_file.filename}")
                    media_file.status = MediaStatus.SKIPPED
                    media_file.media_id = str(existing.id)
                    return True
                
                # Get video metadata
                duration, resolution, aspect_ratio = await self.get_video_metadata(media_file.path)
                
                # Create new video record
                video = Video(
                    id=uuid.uuid4(),
                    user_id=DEFAULT_USER_ID,
                    source_type='local',
                    source_uri=media_file.path,
                    file_name=media_file.filename,
                    file_size=media_file.size_bytes,
                    duration_sec=duration,
                    resolution=resolution,
                    aspect_ratio=aspect_ratio,
                )
                
                session.add(video)
                await session.commit()
                
                media_file.media_id = str(video.id)
                media_file.status = MediaStatus.INGESTED
                media_file.ingested_at = datetime.now().isoformat()
                
                logger.info(f"Ingested: {media_file.filename} -> {media_file.media_id}")
                return True
                
        except ImportError as e:
            # Database models not available, use mock ingestion
            logger.warning(f"Database not available, using mock ingestion: {e}")
            return await self.mock_ingest_file(media_file)
        except Exception as e:
            logger.error(f"Error ingesting {media_file.filename}: {e}")
            media_file.error_message = str(e)
            media_file.retry_count += 1
            if media_file.retry_count >= MAX_RETRIES:
                media_file.status = MediaStatus.FAILED
            return False
    
    async def get_video_metadata(self, file_path: str) -> tuple:
        """Extract video metadata using ffprobe."""
        import subprocess
        import json as json_module
        
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return None, None, None
            
            data = json_module.loads(result.stdout)
            
            # Get duration
            duration = None
            if 'format' in data and 'duration' in data['format']:
                duration = int(float(data['format']['duration']))
            
            # Get video stream info
            resolution = None
            aspect_ratio = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    if width and height:
                        resolution = f"{width}x{height}"
                        # Calculate aspect ratio
                        from math import gcd
                        g = gcd(width, height)
                        aspect_ratio = f"{width//g}:{height//g}"
                    break
            
            return duration, resolution, aspect_ratio
            
        except Exception as e:
            logger.warning(f"Failed to get metadata for {file_path}: {e}")
            return None, None, None
    
    async def mock_ingest_file(self, media_file: MediaFile) -> bool:
        """Mock ingestion for testing without database."""
        import uuid
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        media_file.media_id = str(uuid.uuid4())
        media_file.status = MediaStatus.INGESTED
        media_file.ingested_at = datetime.now().isoformat()
        
        logger.info(f"[MOCK] Ingested: {media_file.filename}")
        return True
    
    async def analyze_file(self, media_file: MediaFile) -> bool:
        """Run AI analysis on a media file."""
        if media_file.file_type != 'video':
            # Skip analysis for images (or do simpler analysis)
            media_file.status = MediaStatus.ANALYZED
            media_file.analyzed_at = datetime.now().isoformat()
            media_file.analysis_result = {"type": "image", "analyzed": True}
            return True
        
        try:
            # Try to use real AI analysis
            from services.ai_analysis import analyze_video
            
            result = await analyze_video(media_file.path)
            media_file.analysis_result = result
            media_file.status = MediaStatus.ANALYZED
            media_file.analyzed_at = datetime.now().isoformat()
            
            logger.info(f"Analyzed: {media_file.filename} - Score: {result.get('pre_social_score', 'N/A')}")
            return True
            
        except ImportError:
            # AI service not available, use mock
            return await self.mock_analyze_file(media_file)
        except Exception as e:
            logger.error(f"Error analyzing {media_file.filename}: {e}")
            media_file.error_message = str(e)
            media_file.retry_count += 1
            if media_file.retry_count >= MAX_RETRIES:
                media_file.status = MediaStatus.FAILED
            return False
    
    async def mock_analyze_file(self, media_file: MediaFile) -> bool:
        """Mock analysis for testing."""
        import random
        
        # Simulate processing time
        await asyncio.sleep(0.2)
        
        media_file.status = MediaStatus.ANALYZED
        media_file.analyzed_at = datetime.now().isoformat()
        media_file.analysis_result = {
            "type": media_file.file_type,
            "pre_social_score": random.randint(60, 95),
            "hook_strength": random.randint(6, 10),
            "pacing_score": random.randint(6, 10),
            "analyzed": True,
            "mock": True
        }
        
        logger.info(f"[MOCK] Analyzed: {media_file.filename} - Score: {media_file.analysis_result['pre_social_score']}")
        return True
    
    async def process_batch(self, files: List[MediaFile]) -> int:
        """Process a batch of files."""
        success_count = 0
        
        for media_file in files:
            file_state = self.state.files.get(media_file.file_hash, asdict(media_file))
            current_status = file_state.get('status', MediaStatus.PENDING)
            
            # Restore state
            media_file.status = current_status
            media_file.retry_count = file_state.get('retry_count', 0)
            media_file.media_id = file_state.get('media_id')
            
            # Skip if already completed or failed
            if current_status in [MediaStatus.ANALYZED, MediaStatus.FAILED, MediaStatus.SKIPPED]:
                logger.debug(f"Skipping {media_file.filename} (status: {current_status})")
                continue
            
            # Ingest if needed
            if current_status in [MediaStatus.PENDING, MediaStatus.INGESTING]:
                media_file.status = MediaStatus.INGESTING
                self.state.files[media_file.file_hash] = asdict(media_file)
                
                if await self.ingest_file(media_file):
                    if media_file.status == MediaStatus.SKIPPED:
                        self.state.skipped_count += 1
                else:
                    self.state.files[media_file.file_hash] = asdict(media_file)
                    continue
            
            # Analyze if ingested
            if media_file.status in [MediaStatus.INGESTED, MediaStatus.ANALYZING]:
                media_file.status = MediaStatus.ANALYZING
                self.state.files[media_file.file_hash] = asdict(media_file)
                
                if await self.analyze_file(media_file):
                    success_count += 1
                    self.state.success_count += 1
            
            # Update state
            self.state.files[media_file.file_hash] = asdict(media_file)
            self.state.processed_count += 1
            
            if media_file.status == MediaStatus.FAILED:
                self.state.failed_count += 1
        
        return success_count
    
    async def run(self, media_files: List[MediaFile], batch_size: int = 5, resume: bool = True):
        """Run the full ingestion pipeline."""
        logger.info(f"Starting ingestion of {len(media_files)} files (resume={resume}, batch_size={batch_size})")
        
        # Initialize database
        db_available = await self.initialize_db()
        if not db_available:
            logger.warning("Database not available, running in mock mode")
        
        # Add new files to state
        for mf in media_files:
            if mf.file_hash not in self.state.files:
                self.state.files[mf.file_hash] = asdict(mf)
        
        self.state.total_files = len(media_files)
        
        # Process in batches
        total_batches = (len(media_files) + batch_size - 1) // batch_size
        
        for batch_num in range(self.state.current_batch, total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(media_files))
            batch = media_files[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} files)")
            
            self.state.current_batch = batch_num
            success = await self.process_batch(batch)
            
            # Save state after each batch
            self.state.save()
            
            # Progress report
            progress = (self.state.processed_count / self.state.total_files) * 100
            logger.info(
                f"Progress: {progress:.1f}% | "
                f"Success: {self.state.success_count} | "
                f"Failed: {self.state.failed_count} | "
                f"Skipped: {self.state.skipped_count}"
            )
        
        # Final report
        self.print_summary()
    
    def print_summary(self):
        """Print ingestion summary."""
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(f"Total Files:     {self.state.total_files}")
        print(f"Processed:       {self.state.processed_count}")
        print(f"Successful:      {self.state.success_count}")
        print(f"Failed:          {self.state.failed_count}")
        print(f"Skipped (dupes): {self.state.skipped_count}")
        print(f"Started:         {self.state.started_at}")
        print(f"Completed:       {self.state.last_updated}")
        print("=" * 60)
        
        # List failed files
        if self.state.failed_count > 0:
            print("\nFailed files:")
            for file_hash, file_data in self.state.files.items():
                if file_data.get('status') == MediaStatus.FAILED:
                    print(f"  - {file_data['filename']}: {file_data.get('error_message', 'Unknown error')}")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest iPhone media with resume capability")
    parser.add_argument("--path", type=str, default=str(IPHONE_IMPORT_PATH),
                       help="Path to media directory")
    parser.add_argument("--reset", action="store_true",
                       help="Reset state and start fresh")
    parser.add_argument("--status", action="store_true",
                       help="Show current ingestion status")
    parser.add_argument("--batch-size", type=int, default=5,
                       help="Number of files to process per batch")
    
    args = parser.parse_args()
    
    batch_size = args.batch_size
    
    # Status only
    if args.status:
        state = IngestionState.load()
        if state:
            print(f"\nIngestion Status:")
            print(f"  Started: {state.started_at}")
            print(f"  Last Updated: {state.last_updated}")
            print(f"  Progress: {state.processed_count}/{state.total_files}")
            print(f"  Success: {state.success_count}")
            print(f"  Failed: {state.failed_count}")
            print(f"  Skipped: {state.skipped_count}")
            print(f"  Current Batch: {state.current_batch}")
        else:
            print("No ingestion in progress")
        return
    
    # Load or create state
    if args.reset or not STATE_FILE.exists():
        logger.info("Starting fresh ingestion")
        state = IngestionState.create_new()
    else:
        state = IngestionState.load()
        if state:
            logger.info(f"Resuming from batch {state.current_batch}, {state.processed_count}/{state.total_files} processed")
        else:
            state = IngestionState.create_new()
    
    # Scan directory
    media_path = Path(args.path)
    media_files = scan_directory(media_path)
    
    if not media_files:
        logger.error("No media files found")
        return
    
    # Run ingestion
    ingester = MediaIngester(state)
    await ingester.run(media_files, batch_size=batch_size)


if __name__ == "__main__":
    asyncio.run(main())

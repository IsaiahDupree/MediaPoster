"""
Generate thumbnails for videos that don't have them
Uses AI-powered best frame selection or ffmpeg fallback
"""
import os
import subprocess
import hashlib
import sys
from sqlalchemy import create_engine, text
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
THUMB_DIR = "/tmp/mediaposter/thumbnails"
MEDIA_DIR = "/Users/isaiahdupree/Documents/Software/MediaPoster/media"

# Try to import AI thumbnail selector
try:
    from services.ai_thumbnail_selector import AIThumbnailSelector
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️ AI thumbnail selector not available, using basic ffmpeg")


def get_video_hash(file_path: str) -> str:
    """Generate a short hash for the video file"""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read(1024 * 100)).hexdigest()[:16]


def generate_thumbnail_basic(video_path: str, output_path: str) -> bool:
    """Generate a thumbnail from a video using ffmpeg (fallback)"""
    try:
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-ss', '00:00:01',
            '-vframes', '1',
            '-vf', 'scale=320:-1',
            '-q:v', '2',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        print(f"  Error: {e}")
        return False


def generate_thumbnail_ai(video_path: str, video_id: str, use_ai: bool = True) -> tuple:
    """Generate thumbnail using AI-powered best frame selection"""
    if not AI_AVAILABLE:
        return None, None
    
    try:
        selector = AIThumbnailSelector()
        thumb_path, analysis = selector.generate_thumbnail(video_path, video_id, use_ai=use_ai)
        return thumb_path, analysis
    except Exception as e:
        print(f"  AI thumbnail failed: {e}")
        return None, None


def find_video_file(file_name: str, search_dirs: list) -> str | None:
    """Find a video file in the search directories"""
    for dir_path in search_dirs:
        if not os.path.exists(dir_path):
            continue
        for root, dirs, files in os.walk(dir_path):
            if file_name in files:
                return os.path.join(root, file_name)
    return None


def main(limit: int = 50, use_ai: bool = False):
    """
    Generate thumbnails for videos missing them.
    
    Args:
        limit: Number of videos to process
        use_ai: Use AI-powered best frame selection (slower but better)
    """
    os.makedirs(THUMB_DIR, exist_ok=True)
    
    engine = create_engine(DATABASE_URL)
    
    # Search directories for video files
    search_dirs = [
        MEDIA_DIR,
        "/Users/isaiahdupree/Movies",
        "/Users/isaiahdupree/Downloads",
    ]
    
    mode = "AI-powered" if (use_ai and AI_AVAILABLE) else "basic ffmpeg"
    print(f"🎬 Thumbnail generation mode: {mode}")
    
    with engine.connect() as conn:
        # Get videos without thumbnails that are video files
        result = conn.execute(text("""
            SELECT id, file_name, source_uri 
            FROM videos 
            WHERE thumbnail_path IS NULL
              AND LOWER(file_name) ~ '\\.(mov|mp4|avi|mkv|webm|m4v)$'
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        print(f"Found {len(result)} videos without thumbnails")
        
        generated = 0
        failed = 0
        
        for row in result:
            video_id = str(row[0])
            file_name = row[1]
            source_uri = row[2]
            
            # Try to find the video file
            video_path = None
            if source_uri and os.path.exists(source_uri):
                video_path = source_uri
            else:
                video_path = find_video_file(file_name, search_dirs)
            
            if not video_path:
                print(f"  ⚠️ Cannot find: {file_name}")
                failed += 1
                continue
            
            print(f"  Generating: {file_name}...", end=" ", flush=True)
            
            thumb_path = None
            analysis = None
            best_frame_score = None
            
            # Try AI-powered generation first
            if use_ai and AI_AVAILABLE:
                thumb_path, analysis = generate_thumbnail_ai(video_path, video_id, use_ai=True)
                if analysis:
                    best_frame_score = float(analysis.get("combined_score", 0))  # Convert numpy to float
            
            # Fallback to basic generation
            if not thumb_path:
                base_name = Path(file_name).stem
                video_hash = get_video_hash(video_path)
                thumb_filename = f"{base_name}_{video_hash}_medium.jpg"
                thumb_path = os.path.join(THUMB_DIR, thumb_filename)
                
                if not generate_thumbnail_basic(video_path, thumb_path):
                    thumb_path = None
            
            if thumb_path and os.path.exists(thumb_path):
                # Update database with thumbnail and score
                update_sql = "UPDATE videos SET thumbnail_path = :thumb_path"
                params = {"thumb_path": thumb_path, "id": video_id}
                
                if best_frame_score is not None:
                    update_sql += ", best_frame_score = :score"
                    params["score"] = best_frame_score
                
                update_sql += " WHERE id = :id"
                conn.execute(text(update_sql), params)
                conn.commit()
                
                score_str = f" (score: {best_frame_score:.2f})" if best_frame_score else ""
                print(f"✅{score_str}")
                generated += 1
            else:
                print("❌")
                failed += 1
        
        print(f"\n✅ Generated: {generated}")
        print(f"❌ Failed: {failed}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate thumbnails for videos")
    parser.add_argument("limit", type=int, nargs="?", default=50, help="Number of videos to process")
    parser.add_argument("--ai", action="store_true", help="Use AI-powered best frame selection")
    parser.add_argument("--no-ai", action="store_true", help="Force basic ffmpeg mode")
    
    args = parser.parse_args()
    
    use_ai = args.ai and not args.no_ai
    main(args.limit, use_ai=use_ai)

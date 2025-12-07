#!/usr/bin/env python3
"""
Quick Start Server - Minimal dependencies
Test video viewing without full database setup
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
from datetime import datetime
import uvicorn

app = FastAPI(title="MediaPoster Quick Start")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Video directories
ICLOUD_PHOTOS = Path.home() / "Pictures" / "Photos Library.photoslibrary"
IPHONE_IMPORT = Path.home() / "Downloads" / "iPhone_Videos"
CUSTOM_IMPORT = Path.home() / "Documents" / "IphoneImport"
WATCH_DIRS = [
    Path.home() / "Pictures",
    Path.home() / "Movies",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    IPHONE_IMPORT,
    CUSTOM_IMPORT
]

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "running",
        "app": "MediaPoster Quick Start",
        "version": "1.0.0",
        "endpoints": [
            "/api/videos",
            "/api/videos/scan",
            "/api/videos/{video_id}"
        ]
    }

@app.get("/api/videos/scan")
async def scan_videos():
    """Scan for videos in watch directories"""
    found_videos = []
    
    # Scan watch directories
    for watch_dir in WATCH_DIRS:
        if watch_dir.exists():
            print(f"Scanning: {watch_dir}")
            for pattern in ['*.mp4', '*.mov', '*.m4v']:
                for video_file in watch_dir.glob(pattern):
                    try:
                        stat = video_file.stat()
                        found_videos.append({
                            "id": str(hash(str(video_file)))[-8:],
                            "filename": video_file.name,
                            "path": str(video_file),
                            "size_mb": round(stat.st_size / (1024*1024), 2),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "directory": str(video_file.parent)
                        })
                    except Exception as e:
                        print(f"Error reading {video_file}: {e}")
    
    # Sort by modification time (newest first)
    found_videos.sort(key=lambda x: x['modified'], reverse=True)
    
    return {
        "total": len(found_videos),
        "videos": found_videos[:50],  # Return first 50
        "scanned_directories": [str(d) for d in WATCH_DIRS if d.exists()]
    }

@app.get("/api/videos")
async def list_videos():
    """List all videos (calls scan)"""
    return await scan_videos()

@app.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    """Get video details and serve file"""
    # This is a simple implementation - in production you'd use database
    scan_result = await scan_videos()
    
    for video in scan_result['videos']:
        if video['id'] == video_id:
            video_path = Path(video['path'])
            if video_path.exists():
                return FileResponse(
                    path=video_path,
                    media_type="video/mp4",
                    filename=video['filename']
                )
    
    raise HTTPException(status_code=404, detail="Video not found")

@app.get("/api/videos/{video_id}/info")
async def get_video_info(video_id: str):
    """Get video metadata"""
    scan_result = await scan_videos()
    
    for video in scan_result['videos']:
        if video['id'] == video_id:
            return video
    
    raise HTTPException(status_code=404, detail="Video not found")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  MediaPoster - Quick Start Server")
    print("="*60)
    print("\nStarting server...")
    print("Watching directories:")
    for d in WATCH_DIRS:
        exists = "✓" if d.exists() else "✗"
        print(f"  {exists} {d}")
    print("\nServer will run at: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

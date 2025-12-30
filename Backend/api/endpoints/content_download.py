"""
Content Download API Endpoints
==============================
Download content from social platforms to local folder.
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from services.content_download.platform_downloader import PlatformDownloader, DownloadResult

router = APIRouter(prefix="/api/v1/download", tags=["Content Download"])


# =========================================================================
# Request/Response Models
# =========================================================================

class SingleDownloadRequest(BaseModel):
    url: str = Field(..., description="URL to download")
    subfolder: str = Field("downloads", description="Subfolder to save to")


class BatchDownloadRequest(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to download")
    subfolder: str = Field("batch", description="Subfolder to save to")


class AccountDownloadRequest(BaseModel):
    username: str = Field(..., description="Account username (without @)")
    platform: str = Field("instagram", description="Platform: instagram or tiktok")
    max_posts: int = Field(20, ge=1, le=100, description="Max posts to download")
    subfolder: Optional[str] = Field(None, description="Custom subfolder")


class DownloadResponse(BaseModel):
    success: bool
    url: str
    platform: str
    content_id: str
    local_path: Optional[str]
    filename: Optional[str]
    file_size_mb: float
    error: Optional[str]


# =========================================================================
# Endpoints
# =========================================================================

@router.post("/single", response_model=DownloadResponse)
async def download_single(request: SingleDownloadRequest):
    """
    Download a single video from Instagram or TikTok.
    
    Supports:
    - Instagram Reels: https://www.instagram.com/reel/ABC123/
    - Instagram Posts: https://www.instagram.com/p/ABC123/
    - TikTok Videos: https://www.tiktok.com/@user/video/1234567890
    """
    downloader = PlatformDownloader()
    
    # Detect platform
    url_lower = request.url.lower()
    
    try:
        if "instagram.com" in url_lower:
            result = await downloader.download_instagram_reel(request.url, request.subfolder)
        elif "tiktok.com" in url_lower:
            result = await downloader.download_tiktok_video(request.url, request.subfolder)
        else:
            raise HTTPException(status_code=400, detail="Unsupported platform. Use Instagram or TikTok URLs.")
        
        return DownloadResponse(
            success=result.success,
            url=result.url,
            platform=result.platform,
            content_id=result.content_id,
            local_path=result.local_path,
            filename=result.filename,
            file_size_mb=result.file_size_mb,
            error=result.error
        )
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def download_batch(request: BatchDownloadRequest):
    """
    Download multiple videos in batch.
    
    Automatically detects platform from each URL.
    Skips already-downloaded files.
    """
    if len(request.urls) > 50:
        raise HTTPException(status_code=400, detail="Max 50 URLs per batch")
    
    downloader = PlatformDownloader()
    
    try:
        result = await downloader.download_batch(request.urls, request.subfolder)
        
        return {
            "total_requested": result.total_requested,
            "successful": result.successful,
            "failed": result.failed,
            "skipped": result.skipped,
            "total_size_mb": round(result.total_size_mb, 2),
            "output_folder": result.output_folder,
            "downloads": [
                {
                    "success": d.success,
                    "url": d.url,
                    "platform": d.platform,
                    "content_id": d.content_id,
                    "filename": d.filename,
                    "file_size_mb": round(d.file_size_mb, 2),
                    "error": d.error
                }
                for d in result.downloads
            ]
        }
        
    except Exception as e:
        logger.error(f"Batch download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/account")
async def download_account(request: AccountDownloadRequest):
    """
    Download content from a specific account.
    
    Downloads the most recent posts up to max_posts.
    Saves to accounts/{username}/posts/ by default.
    """
    downloader = PlatformDownloader()
    
    try:
        result = await downloader.download_account_content(
            username=request.username,
            platform=request.platform,
            max_posts=request.max_posts,
            subfolder=request.subfolder
        )
        
        return {
            "username": request.username,
            "platform": request.platform,
            "total_requested": result.total_requested,
            "successful": result.successful,
            "failed": result.failed,
            "skipped": result.skipped,
            "total_size_mb": round(result.total_size_mb, 2),
            "output_folder": result.output_folder
        }
        
    except Exception as e:
        logger.error(f"Account download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def download_info():
    """Get Content Download feature information"""
    return {
        "name": "Content Download",
        "description": "Download content from social platforms to local folder",
        "version": "1.0.0",
        "supported_platforms": [
            {"name": "Instagram", "types": ["Reels", "Posts", "IGTV"]},
            {"name": "TikTok", "types": ["Videos"]}
        ],
        "endpoints": [
            {
                "name": "Single Download",
                "method": "POST",
                "path": "/single",
                "description": "Download a single video by URL"
            },
            {
                "name": "Batch Download",
                "method": "POST",
                "path": "/batch",
                "description": "Download multiple videos (max 50)"
            },
            {
                "name": "Account Download",
                "method": "POST",
                "path": "/account",
                "description": "Download recent posts from an account"
            }
        ],
        "output_folder": "/Users/isaiahdupree/Documents/CompetitorResearch",
        "notes": [
            "Files are saved with platform prefix (ig_, tt_)",
            "Already downloaded files are skipped",
            "RapidAPI key required for downloads"
        ]
    }

"""
Thumbnail Generation API Endpoints
Intelligent thumbnail creation for multi-platform publishing
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid
import os
from pathlib import Path

from database.connection import get_db
from services.thumbnail_generator import ThumbnailGenerator, PLATFORM_DIMENSIONS

router = APIRouter()


# ==================== Response Models ====================

class BestFrameResponse(BaseModel):
    """Best frame selection result"""
    frame_path: str
    sharpness: float
    brightness: float
    contrast: float
    faces_detected: int
    vibrancy: float
    overall_score: float


class ThumbnailResponse(BaseModel):
    """Thumbnail generation result"""
    platform: str
    thumbnail_path: str
    width: int
    height: int
    aspect_ratio: str
    orientation: str


class PlatformDimensionsResponse(BaseModel):
    """Platform dimension info"""
    platform: str
    width: int
    height: int
    aspect_ratio: str
    orientation: str


# ==================== Endpoints ====================

@router.get("/dimensions", response_model=List[PlatformDimensionsResponse])
def get_platform_dimensions():
    """
    Get thumbnail dimensions for all platforms
    
    Returns specifications for:
    - YouTube (landscape & shorts)
    - TikTok
    - Instagram (feed, story, reel)
    - Facebook, Twitter, LinkedIn
    - Pinterest, Snapchat, Threads
    
    Example:
        ```
        GET /api/thumbnails/dimensions
        ```
    """
    return [
        PlatformDimensionsResponse(
            platform=key,
            width=dims.width,
            height=dims.height,
            aspect_ratio=dims.aspect_ratio,
            orientation=dims.orientation
        )
        for key, dims in PLATFORM_DIMENSIONS.items()
    ]


@router.post("/select-best-frame", response_model=BestFrameResponse)
async def select_best_frame(
    video_path: str = Form(..., description="Path to video file"),
    num_candidates: int = Form(10, description="Number of frames to analyze"),
    db: Session = Depends(get_db)
):
    """
    Select the best frame from a video for thumbnail generation
    
    Analyzes frames for:
    - Sharpness and clarity
    - Proper brightness and contrast
    - Face detection
    - Color vibrancy
    - Overall composition
    
    Example:
        ```
        POST /api/thumbnails/select-best-frame
        {
            "video_path": "/path/to/video.mp4",
            "num_candidates": 10
        }
        ```
    """
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    generator = ThumbnailGenerator()
    
    try:
        best_frame, analysis = generator.select_best_frame(
            video_path=video_path,
            num_candidates=num_candidates
        )
        
        return BestFrameResponse(**analysis)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=List[ThumbnailResponse])
async def generate_thumbnails(
    source_image: str = Form(..., description="Path to source image"),
    platforms: Optional[str] = Form(None, description="Comma-separated platform list (or 'all')"),
    output_dir: str = Form("/tmp/thumbnails", description="Output directory"),
    base_name: str = Form("thumbnail", description="Base filename"),
    db: Session = Depends(get_db)
):
    """
    Generate platform-specific thumbnails from source image
    
    Supports all major social media platforms with correct dimensions
    
    Example:
        ```
        POST /api/thumbnails/generate
        {
            "source_image": "/path/to/frame.jpg",
            "platforms": "youtube,tiktok,instagram_feed",
            "output_dir": "/path/to/output"
        }
        ```
    """
    if not os.path.exists(source_image):
        raise HTTPException(status_code=404, detail="Source image not found")
    
    generator = ThumbnailGenerator()
    
    try:
        if platforms is None or platforms.lower() == "all":
            # Generate for all platforms
            thumbnails = generator.generate_all_platforms(
                source_image=source_image,
                output_dir=output_dir,
                base_name=base_name
            )
        else:
            # Generate for specific platforms
            platform_list = [p.strip() for p in platforms.split(",")]
            thumbnails = {}
            
            for platform in platform_list:
                if platform not in PLATFORM_DIMENSIONS:
                    continue
                
                output_path = f"{output_dir}/{base_name}_{platform}.jpg"
                generator.generate_thumbnail(
                    source_image=source_image,
                    platform=platform,
                    output_path=output_path
                )
                thumbnails[platform] = output_path
        
        # Build response
        results = []
        for platform, path in thumbnails.items():
            dims = PLATFORM_DIMENSIONS[platform]
            results.append(ThumbnailResponse(
                platform=platform,
                thumbnail_path=path,
                width=dims.width,
                height=dims.height,
                aspect_ratio=dims.aspect_ratio,
                orientation=dims.orientation
            ))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-from-video")
async def generate_from_video(
    video_path: str = Form(..., description="Path to video file"),
    platforms: Optional[str] = Form("all", description="Comma-separated platform list"),
    output_dir: str = Form("/tmp/thumbnails", description="Output directory"),
    num_candidates: int = Form(10, description="Number of frames to analyze"),
    db: Session = Depends(get_db)
):
    """
    Complete workflow: Select best frame and generate all thumbnails
    
    This endpoint:
    1. Analyzes video to find the best frame
    2. Generates thumbnails for all specified platforms
    3. Returns paths to all generated thumbnails
    
    Example:
        ```
        POST /api/thumbnails/generate-from-video
        {
            "video_path": "/path/to/video.mp4",
            "platforms": "all",
            "output_dir": "/path/to/output"
        }
        ```
    """
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    generator = ThumbnailGenerator()
    
    try:
        # Step 1: Select best frame
        best_frame, analysis = generator.select_best_frame(
            video_path=video_path,
            num_candidates=num_candidates
        )
        
        # Step 2: Generate thumbnails
        if platforms.lower() == "all":
            thumbnails = generator.generate_all_platforms(
                source_image=best_frame,
                output_dir=output_dir,
                base_name="thumbnail"
            )
        else:
            platform_list = [p.strip() for p in platforms.split(",")]
            thumbnails = {}
            
            for platform in platform_list:
                if platform not in PLATFORM_DIMENSIONS:
                    continue
                
                output_path = f"{output_dir}/thumbnail_{platform}.jpg"
                generator.generate_thumbnail(
                    source_image=best_frame,
                    platform=platform,
                    output_path=output_path
                )
                thumbnails[platform] = output_path
        
        # Build response
        results = {
            "best_frame": {
                "path": best_frame,
                "analysis": analysis
            },
            "thumbnails": [
                {
                    "platform": platform,
                    "path": path,
                    "dimensions": {
                        "width": PLATFORM_DIMENSIONS[platform].width,
                        "height": PLATFORM_DIMENSIONS[platform].height,
                        "aspect_ratio": PLATFORM_DIMENSIONS[platform].aspect_ratio
                    }
                }
                for platform, path in thumbnails.items()
            ]
        }
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance-with-ai")
async def enhance_with_ai(
    image_path: str = Form(..., description="Path to thumbnail image"),
    title: str = Form(..., description="Video title for text generation"),
    output_path: str = Form(..., description="Where to save enhanced thumbnail"),
    style: str = Form("bold", description="Text style: bold, minimal, colorful"),
    db: Session = Depends(get_db)
):
    """
    Add AI-generated catchy text overlay to thumbnail
    
    Uses GPT to:
    - Generate short, attention-grabbing text
    - Add professional text overlay
    - Optimize for clickability
    
    Example:
        ```
        POST /api/thumbnails/enhance-with-ai
        {
            "image_path": "/path/to/thumbnail.jpg",
            "title": "10 Amazing Life Hacks You Need to Know",
            "output_path": "/path/to/enhanced.jpg",
            "style": "bold"
        }
        ```
    """
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    generator = ThumbnailGenerator()
    
    try:
        enhanced_path = await generator.add_ai_text_overlay(
            image_path=image_path,
            title=title,
            output_path=output_path,
            style=style
        )
        
        return {
            "enhanced_thumbnail": enhanced_path,
            "original": image_path,
            "ai_enhancement": "Text overlay added successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete-workflow")
async def complete_thumbnail_workflow(
    video_path: str = Form(..., description="Path to video file"),
    title: str = Form(..., description="Video title"),
    platforms: str = Form("all", description="Platforms to generate for"),
    output_dir: str = Form("/tmp/thumbnails", description="Output directory"),
    add_text_overlay: bool = Form(True, description="Add AI text overlay"),
    db: Session = Depends(get_db)
):
    """
    Complete AI-powered thumbnail generation workflow
    
    This is the ultimate endpoint that:
    1. Selects the best frame from video
    2. Generates thumbnails for all platforms
    3. Adds AI-generated catchy text overlays
    4. Returns all enhanced thumbnails
    
    Example:
        ```
        POST /api/thumbnails/complete-workflow
        {
            "video_path": "/path/to/video.mp4",
            "title": "How I Made $10,000 in 30 Days",
            "platforms": "youtube,tiktok,instagram_feed",
            "add_text_overlay": true
        }
        ```
    """
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    generator = ThumbnailGenerator()
    
    try:
        # Step 1: Select best frame
        best_frame, analysis = generator.select_best_frame(video_path, num_candidates=10)
        
        # Step 2: Generate platform thumbnails
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        if platforms.lower() == "all":
            platform_list = list(PLATFORM_DIMENSIONS.keys())
        else:
            platform_list = [p.strip() for p in platforms.split(",")]
        
        results = {
            "best_frame_analysis": analysis,
            "thumbnails": []
        }
        
        for platform in platform_list:
            if platform not in PLATFORM_DIMENSIONS:
                continue
            
            # Generate base thumbnail
            base_output = f"{output_dir}/thumbnail_{platform}_base.jpg"
            generator.generate_thumbnail(best_frame, platform, base_output)
            
            thumbnail_data = {
                "platform": platform,
                "base_thumbnail": base_output,
                "dimensions": {
                    "width": PLATFORM_DIMENSIONS[platform].width,
                    "height": PLATFORM_DIMENSIONS[platform].height,
                    "aspect_ratio": PLATFORM_DIMENSIONS[platform].aspect_ratio
                }
            }
            
            # Add AI text overlay if requested
            if add_text_overlay:
                enhanced_output = f"{output_dir}/thumbnail_{platform}_enhanced.jpg"
                await generator.add_ai_text_overlay(
                    image_path=base_output,
                    title=title,
                    output_path=enhanced_output
                )
                thumbnail_data["enhanced_thumbnail"] = enhanced_output
            
            results["thumbnails"].append(thumbnail_data)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

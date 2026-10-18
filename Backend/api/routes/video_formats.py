"""
Video Formats API - Manage saved prompt templates and Sora generation jobs
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import asyncio
from pathlib import Path

router = APIRouter(prefix="/api/video-formats", tags=["video-formats"])

# Storage paths
FORMATS_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch/formats")
FORMATS_DIR.mkdir(parents=True, exist_ok=True)
FORMATS_FILE = FORMATS_DIR / "formats.json"


class VideoFormat(BaseModel):
    id: str
    name: str
    source_creator: str
    description: str
    master_sora_prompt: str
    master_veo3_prompt: str
    themes: List[str]
    example_locations: List[str]
    avg_duration: int
    scene_count: int
    created_at: Optional[str] = None
    videos_generated: int = 0


class GenerateRequest(BaseModel):
    location: str
    theme: Optional[str] = None
    scheduled_at: Optional[str] = None


def load_formats() -> List[dict]:
    """Load formats from file"""
    if FORMATS_FILE.exists():
        with open(FORMATS_FILE) as f:
            return json.load(f)
    return []


def save_formats(formats: List[dict]):
    """Save formats to file"""
    with open(FORMATS_FILE, "w") as f:
        json.dump(formats, f, indent=2)


def get_default_format() -> dict:
    """Return the default pensacola_bigfoot format"""
    return {
        "id": "pensacola_bigfoot",
        "name": "Florida Location Roast",
        "source_creator": "@pensacola_bigfoot",
        "description": "Sarcastic local guide roasting Florida locations with humor",
        "master_sora_prompt": """Create a dynamic TikTok-style video featuring a humorous character exploring varied locations.

**Visual Style:**
- Use medium and wide-angle shots to capture both character and setting.
- Set in vibrant and recognizable public places, using natural daylight and warm evening tones.
- Emphasize vibrant colors with slight contrast for visual appeal.

**Camera Work:**
- Predominantly selfie-style and eye-level angles for personal engagement.

**Pacing:**
- Implement quick cuts with straightforward transitions to maintain a dynamic flow.

**Subject Presentation:**
- Character is distinguished by humorous attire, like costumes or distinctive accessories.
- Engage actively with settings in a playful, comedic manner.

**Mood:**
- Light-hearted, engaging, and humor-centered, with a quick-witted narration style.

**Text Overlays:**
- Bold white text with selected highlights in pink or other vibrant colors at the bottom of the screen.""",
        "master_veo3_prompt": """Generate a vibrant and engaging video featuring a comedic character in public settings.

**Visuals:**
- Use a mix of wide, medium, and selfie-style shots to ensure visibility of character and environment.
- Employ bright, natural lighting with vivid, high-contrast colors.

**Camera & Lighting:**
- Eye-level and wide-angle perspectives for visual variety.
- Natural daylight and warm-toned evening lighting.

**Narrative & Pacing:**
- Maintain humor and sarcasm with engaging dialogue.
- Utilize quick transitions for a lively pace, ensuring viewer attention.

**Character Design:**
- Dress the character in whimsical attire or costume with eye-catching accessories.

**Text Overlay:**
- Bold, white text with key phrases highlighted in colorful outlines at the bottom of the frame.

**Opening Hook:**
- Hook viewers immediately with a unique or humorous character introduction.""",
        "themes": ["tourist traps", "beach town quirks", "college stereotypes", "suburban oddities", "florida man energy"],
        "example_locations": ["Pensacola, FL", "Tampa, FL", "Orlando, FL", "Miami, FL", "Jacksonville, FL"],
        "avg_duration": 30,
        "scene_count": 5,
        "created_at": datetime.now().isoformat(),
        "videos_generated": 0
    }


@router.get("")
async def list_formats():
    """List all saved video formats"""
    formats = load_formats()
    
    # Add default if empty
    if not formats:
        formats = [get_default_format()]
        save_formats(formats)
    
    return {"formats": formats}


@router.get("/{format_id}")
async def get_format(format_id: str):
    """Get a specific format by ID"""
    formats = load_formats()
    
    for fmt in formats:
        if fmt["id"] == format_id:
            return fmt
    
    # Return default if requested
    if format_id == "pensacola_bigfoot":
        return get_default_format()
    
    raise HTTPException(status_code=404, detail="Format not found")


@router.post("")
async def create_format(format_data: VideoFormat):
    """Create a new video format"""
    formats = load_formats()
    
    # Check for duplicate
    for fmt in formats:
        if fmt["id"] == format_data.id:
            raise HTTPException(status_code=400, detail="Format ID already exists")
    
    new_format = format_data.dict()
    new_format["created_at"] = datetime.now().isoformat()
    formats.append(new_format)
    save_formats(formats)
    
    return {"success": True, "format": new_format}


@router.post("/{format_id}/generate")
async def generate_video(format_id: str, request: GenerateRequest, background_tasks: BackgroundTasks):
    """Queue a video generation job for this format"""
    formats = load_formats()
    
    # Find format
    format_data = None
    for fmt in formats:
        if fmt["id"] == format_id:
            format_data = fmt
            break
    
    if not format_data and format_id == "pensacola_bigfoot":
        format_data = get_default_format()
    
    if not format_data:
        raise HTTPException(status_code=404, detail="Format not found")
    
    # Create job
    job_id = f"gen_{format_id}_{int(datetime.now().timestamp())}"
    
    job = {
        "id": job_id,
        "format_id": format_id,
        "location": request.location,
        "theme": request.theme,
        "status": "pending",
        "scheduled_at": request.scheduled_at or datetime.now().isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    # Save job
    jobs_file = FORMATS_DIR / "jobs.json"
    jobs = []
    if jobs_file.exists():
        with open(jobs_file) as f:
            jobs = json.load(f)
    
    jobs.append(job)
    with open(jobs_file, "w") as f:
        json.dump(jobs, f, indent=2)
    
    # Update format count
    for fmt in formats:
        if fmt["id"] == format_id:
            fmt["videos_generated"] = fmt.get("videos_generated", 0) + 1
    save_formats(formats)
    
    return {"success": True, "job": job}


@router.delete("/{format_id}")
async def delete_format(format_id: str):
    """Delete a video format"""
    formats = load_formats()
    formats = [f for f in formats if f["id"] != format_id]
    save_formats(formats)
    
    return {"success": True}

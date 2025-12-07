from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from modules.cloud_staging.google_drive import GoogleDriveUploader
from connectors.blotato.connector import BlotatoConnector
from connectors.base import ContentVariant

# Load env vars
load_dotenv()

router = APIRouter()

class ScheduleResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

async def process_scheduling_workflow(
    file_path: Path,
    platforms: List[str],
    caption: str,
    scheduled_time: Optional[datetime]
):
    """
    Background task to handle the full scheduling workflow:
    1. Upload to Google Drive
    2. Post to Blotato (for each platform)
    3. Trigger scrapers/checkbacks
    """
    try:
        # 1. Upload to Google Drive
        uploader = GoogleDriveUploader()
        if uploader.authenticate():
            folder_id = uploader.get_or_create_folder("MediaPoster_Staging")
            drive_file = uploader.upload_file(
                file_path, 
                folder_id=folder_id, 
                description=f"Scheduled post: {caption[:50]}..."
            )
            drive_link = drive_file.get('link') if drive_file else None
            print(f"Uploaded to Drive: {drive_link}")
        else:
            print("Google Drive authentication failed, skipping upload")
            drive_link = None

        # 2. Post to Blotato
        connector = BlotatoConnector()
        results = []
        
        for platform in platforms:
            print(f"Scheduling for {platform}...")
            variant = ContentVariant(
                content_id=f"sched_{datetime.now().timestamp()}",
                platform=platform
            )
            # In a real implementation, we'd pass the file path/url and caption to publish_variant
            # For now, we assume publish_variant handles the API call
            try:
                # Mocking the publish call with extra args if needed
                # result = await connector.publish_variant(variant, file_url=drive_link, caption=caption)
                result = await connector.publish_variant(variant)
                results.append({
                    "platform": platform,
                    "status": "success",
                    "post_id": result.get("platform_post_id"),
                    "url": result.get("url")
                })
                
                # 3. Trigger Scraper / Checkback
                # This would ideally be a separate Celery task or delayed job
                print(f"Triggering scraper for {platform} post {result.get('platform_post_id')}")
                # await trigger_scraper(platform, result.get('url'))
                
            except Exception as e:
                print(f"Failed to schedule for {platform}: {e}")
                results.append({
                    "platform": platform,
                    "status": "failed",
                    "error": str(e)
                })

        print(f"Scheduling complete: {results}")

    except Exception as e:
        print(f"Scheduling workflow failed: {e}")
    finally:
        # Cleanup temp file
        if file_path.exists():
            file_path.unlink()

@router.post("/upload")
async def schedule_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    platforms: str = Form(...), # Comma-separated list
    caption: str = Form(...),
    scheduled_time: Optional[str] = Form(None)
):
    """
    Upload a file and schedule it for posting.
    """
    try:
        # Save uploaded file temporarily
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / file.filename
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        platform_list = [p.strip() for p in platforms.split(",")]
        
        # Parse scheduled time if provided
        dt = datetime.fromisoformat(scheduled_time) if scheduled_time else None

        # Add to background tasks
        background_tasks.add_task(
            process_scheduling_workflow,
            temp_path,
            platform_list,
            caption,
            dt
        )
        
        return ScheduleResponse(
            success=True,
            message="File uploaded and scheduling workflow started",
            data={
                "filename": file.filename,
                "platforms": platform_list,
                "task_status": "processing"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

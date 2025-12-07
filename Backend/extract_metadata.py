#!/usr/bin/env python3
"""
Extract and populate video metadata using FFprobe
"""
import asyncio
import os
import subprocess
import json
from pathlib import Path

import sys
sys.path.insert(0, '/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')

from database.connection import init_db, async_session_maker
from database.models import Video
from sqlalchemy import select, update
from loguru import logger


def get_video_metadata(file_path: str) -> dict:
    """Extract metadata from video file using ffprobe"""
    if not os.path.exists(file_path):
        return {}
    
    # Check if it's an image (not a video)
    ext = Path(file_path).suffix.lower()
    if ext in {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.heif'}:
        # For images, just get file size
        return {
            'file_size': os.path.getsize(file_path),
            'is_image': True
        }
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration:format=duration,size",
        "-of", "json",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        metadata = {}
        
        # Get video dimensions
        if 'streams' in data and len(data['streams']) > 0:
            stream = data['streams'][0]
            metadata['width'] = stream.get('width')
            metadata['height'] = stream.get('height')
            
            # Try to get duration from stream
            if 'duration' in stream:
                metadata['duration'] = float(stream['duration'])
        
        # Get format info
        if 'format' in data:
            format_data = data['format']
            
            # Duration from format (fallback)
            if 'duration' not in metadata and 'duration' in format_data:
                metadata['duration'] = float(format_data['duration'])
            
            # File size
            if 'size' in format_data:
                metadata['file_size'] = int(format_data['size'])
        
        # If we still don't have file size, get it from filesystem
        if 'file_size' not in metadata:
            metadata['file_size'] = os.path.getsize(file_path)
        
        return metadata
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error extracting metadata from {file_path}: {e}")
        # Fallback: at least get file size
        return {
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else None
        }


async def update_video_metadata():
    """Update metadata for all videos"""
    await init_db()
    
    # Import after init_db to ensure it's initialized
    from database.connection import async_session_maker as session_maker
    
    if session_maker is None:
        logger.error("Failed to initialize database session maker")
        return
    
    async with session_maker() as session:
        # Get all videos
        result = await session.execute(select(Video))
        videos = result.scalars().all()
        
        logger.info(f"Found {len(videos)} videos to process")
        
        updated_count = 0
        for video in videos:
            video_path = os.path.expanduser(video.source_uri)
            
            logger.info(f"Processing: {video.file_name}")
            
            # Extract metadata
            metadata = get_video_metadata(video_path)
            
            if not metadata:
                logger.warning(f"No metadata extracted for {video.file_name}")
                continue
            
            # Update video record
            update_values = {}
            
            if 'duration' in metadata:
                update_values['duration_sec'] = metadata['duration']
            
            if 'width' in metadata and 'height' in metadata:
                update_values['resolution'] = f"{metadata['width']}x{metadata['height']}"
                update_values['aspect_ratio'] = f"{metadata['width']}:{metadata['height']}"
            
            if update_values:
                await session.execute(
                    update(Video)
                    .where(Video.id == video.id)
                    .values(**update_values)
                )
                updated_count += 1
                logger.info(f"✅ Updated {video.file_name}: {update_values}")
        
        await session.commit()
        logger.success(f"Updated metadata for {updated_count}/{len(videos)} videos")


if __name__ == "__main__":
    asyncio.run(update_video_metadata())

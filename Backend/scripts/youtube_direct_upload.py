#!/usr/bin/env python3
"""
YouTube Direct Upload Script
============================
Uploads videos directly to YouTube using the YouTube Data API v3.
Bypasses Blotato for direct uploads when rate limits are hit.

Usage:
    python scripts/youtube_direct_upload.py [--dry-run] [--limit N]

Requirements:
    - Google OAuth2 credentials (client_secrets.json)
    - YouTube Data API v3 enabled
    - pip install google-api-python-client google-auth-oauthlib
"""

import sys
import os
import json
import time
import pickle
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("⚠️ Google API libraries not installed. Run:")
    print("   pip install google-api-python-client google-auth-oauthlib")

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
CLIENT_SECRETS_FILE = Path(__file__).parent.parent / "config" / "youtube_client_secrets.json"
TOKEN_FILE = Path(__file__).parent.parent / "config" / "youtube_token.pickle"

class YouTubeDirectUploader:
    def __init__(self):
        self.youtube = None
        self.authenticated = False
        
    def authenticate(self):
        """Authenticate with YouTube API using OAuth2."""
        if not GOOGLE_API_AVAILABLE:
            print("❌ Google API libraries not available")
            return False
            
        creds = None
        
        # Load existing token
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CLIENT_SECRETS_FILE.exists():
                    print(f"❌ Client secrets file not found: {CLIENT_SECRETS_FILE}")
                    print("\nTo set up YouTube API:")
                    print("1. Go to https://console.cloud.google.com/apis/credentials")
                    print("2. Create OAuth 2.0 Client ID (Desktop app)")
                    print("3. Download JSON and save as:")
                    print(f"   {CLIENT_SECRETS_FILE}")
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRETS_FILE), SCOPES)
                creds = flow.run_local_server(port=8090)
            
            # Save credentials
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        self.authenticated = True
        print("✅ YouTube API authenticated")
        return True
    
    def upload_video(self, video_path: str, title: str, description: str, 
                     tags: list = None, category_id: str = "22",
                     privacy_status: str = "public") -> dict:
        """
        Upload a video to YouTube.
        
        Args:
            video_path: Path to the video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags
            category_id: YouTube category (22 = People & Blogs)
            privacy_status: public, private, or unlisted
            
        Returns:
            dict with video_id and url on success
        """
        if not self.authenticated:
            if not self.authenticate():
                return {"error": "Not authenticated"}
        
        if not Path(video_path).exists():
            return {"error": f"Video file not found: {video_path}"}
        
        # Prepare metadata
        body = {
            'snippet': {
                'title': title[:100],  # YouTube max is 100 chars
                'description': description[:5000] if description else "",
                'tags': tags or ['sora', 'ai', 'shorts'],
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False,
                'madeForKids': False
            }
        }
        
        # Create media upload
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024*1024  # 1MB chunks
        )
        
        try:
            # Execute upload
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"   Upload progress: {int(status.progress() * 100)}%")
            
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            return {
                "success": True,
                "video_id": video_id,
                "url": video_url,
                "title": title
            }
            
        except Exception as e:
            return {"error": str(e)}


def get_pending_videos():
    """Get videos that need to be uploaded."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            sp.id as schedule_id,
            sp.title,
            sp.caption as description,
            sp.clip_id,
            v.source_uri as video_path,
            sp.status
        FROM scheduled_posts sp
        JOIN videos v ON sp.clip_id = v.id
        WHERE sp.platform = 'youtube'
          AND sp.created_at > NOW() - INTERVAL '6 hours'
          AND sp.status IN ('scheduled', 'publishing')
        ORDER BY sp.scheduled_time
    """)
    
    videos = cur.fetchall()
    cur.close()
    conn.close()
    return videos


def mark_as_posted(schedule_id: str, video_id: str, video_url: str):
    """Mark a scheduled post as posted."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE scheduled_posts
        SET status = 'posted',
            platform_post_id = %s,
            platform_url = %s,
            published_at = NOW(),
            updated_at = NOW()
        WHERE id = %s
    """, (video_id, video_url, schedule_id))
    
    conn.commit()
    cur.close()
    conn.close()


def mark_as_failed(schedule_id: str, error: str):
    """Mark a scheduled post as failed."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE scheduled_posts
        SET status = 'failed',
            error_message = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (error[:500], schedule_id))
    
    conn.commit()
    cur.close()
    conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Upload videos directly to YouTube')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be uploaded')
    parser.add_argument('--limit', type=int, default=30, help='Max videos to upload')
    parser.add_argument('--delay', type=int, default=30, help='Seconds between uploads')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("YouTube Direct Upload Script")
    print("="*60)
    
    # Get pending videos
    videos = get_pending_videos()
    print(f"\n📹 Found {len(videos)} videos pending upload")
    
    if not videos:
        print("No videos to upload!")
        return
    
    # Limit videos
    videos = videos[:args.limit]
    print(f"📤 Will upload {len(videos)} videos")
    
    if args.dry_run:
        print("\n🔍 DRY RUN - No uploads will be made\n")
        for i, v in enumerate(videos, 1):
            print(f"{i:3}. [{v['status']}] {v['title'][:40]}")
            print(f"     Path: {v['video_path']}")
        print(f"\nRun without --dry-run to upload these {len(videos)} videos")
        return
    
    # Initialize uploader
    uploader = YouTubeDirectUploader()
    if not uploader.authenticate():
        print("❌ Failed to authenticate with YouTube API")
        return
    
    # Upload videos
    success = 0
    failed = 0
    
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] Uploading: {video['title'][:40]}...")
        
        result = uploader.upload_video(
            video_path=video['video_path'],
            title=video['title'] or "Sora AI Video",
            description=video['description'] or "AI Generated Video #shorts",
            tags=['sora', 'ai', 'aigenerated', 'shorts']
        )
        
        if result.get('success'):
            print(f"   ✅ Success: {result['url']}")
            mark_as_posted(video['schedule_id'], result['video_id'], result['url'])
            success += 1
        else:
            print(f"   ❌ Failed: {result.get('error')}")
            mark_as_failed(video['schedule_id'], result.get('error', 'Unknown error'))
            failed += 1
        
        # Rate limit delay (avoid YouTube quota issues)
        if i < len(videos):
            print(f"   ⏳ Waiting {args.delay}s before next upload...")
            time.sleep(args.delay)
    
    print("\n" + "="*60)
    print(f"COMPLETE: {success} uploaded, {failed} failed")
    print("="*60)


if __name__ == "__main__":
    main()

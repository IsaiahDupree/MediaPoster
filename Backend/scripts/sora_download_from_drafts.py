#!/usr/bin/env python3
"""
Sora Download from Drafts - Reproducible Script
================================================
Downloads videos from Sora /drafts page to local machine.

Usage:
    python scripts/sora_download_from_drafts.py           # Download 1 video
    python scripts/sora_download_from_drafts.py 3         # Download 3 videos

Success Criteria:
    ✅ Navigate to /drafts
    ✅ Get video URLs
    ✅ Download to local machine
    ✅ Verify file exists

Output Directory: /Users/isaiahdupree/Documents/CompetitorResearch/sora_downloads/
"""

import sys
import time
import os
import subprocess
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.sora_full_automation import SoraFullAutomation


def download_from_drafts(count: int = 1) -> list:
    """
    Download videos from Sora /drafts page.
    
    Args:
        count: Number of videos to download (default 1)
        
    Returns:
        List of downloaded file paths
    """
    print('='*60)
    print('SORA DOWNLOAD FROM DRAFTS')
    print('='*60)
    
    sora = SoraFullAutomation()
    
    # Step 1: Navigate to drafts
    print('\n📍 Step 1: Navigating to /drafts...')
    script = 'tell application "Safari" to set URL of front document to "https://sora.chatgpt.com/drafts"'
    subprocess.run(['osascript', '-e', script], capture_output=True)
    time.sleep(4)
    print('   ✅ Navigated to drafts')
    
    # Step 2: Get videos from drafts
    print('\n📋 Step 2: Getting videos from drafts...')
    videos = sora.get_completed_videos(scroll_count=2)
    print(f'   Found {len(videos)} videos')
    
    if not videos:
        print('   ❌ No videos found in drafts')
        return []
    
    # Show available videos
    for i, v in enumerate(videos[:5]):
        src = v.get('video_src', '')[:50]
        print(f'   {i+1}. {src}...')
    
    # Step 3: Download videos
    print(f'\n📥 Step 3: Downloading {count} video(s)...')
    downloaded = sora.download_from_drafts(count)
    
    # Step 4: Verify downloads
    print('\n✅ Step 4: Verifying downloads...')
    verified = []
    for path in downloaded:
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024 / 1024
            print(f'   ✅ {Path(path).name} ({size:.1f} MB)')
            verified.append(path)
        else:
            print(f'   ❌ File not found: {path}')
    
    # Summary
    print('\n' + '='*60)
    if verified:
        print(f'SUCCESS! Downloaded {len(verified)} video(s)')
        print(f'Location: {sora.DOWNLOAD_DIR}')
        for path in verified:
            print(f'  - {Path(path).name}')
    else:
        print('FAILED - No videos downloaded')
    print('='*60)
    
    return verified


def main():
    """Main entry point."""
    # Get count from command line
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    # Download
    downloaded = download_from_drafts(count)
    
    # Return exit code
    sys.exit(0 if downloaded else 1)


if __name__ == "__main__":
    main()

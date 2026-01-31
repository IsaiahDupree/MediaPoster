#!/usr/bin/env python3
"""
Publish Sora Videos Script
==========================
Publishes analyzed Sora videos to YouTube and TikTok using:
1. Upload to Supabase/GDrive → get public URL
2. Upload to Blotato → get Blotato-hosted URL
3. Publish to platform via Blotato API
4. Poll for platform URL

Run: python scripts/publish_sora_videos.py
     python scripts/publish_sora_videos.py --list
     python scripts/publish_sora_videos.py --video cleaned_badass-01.mp4
     python scripts/publish_sora_videos.py --all --platform youtube
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from loguru import logger
from config import settings


# Platform account IDs (from Blotato)
ACCOUNTS = {
    'youtube': {'id': '228', 'username': 'UCnDBsELI2OlaEl5yxA77HNA'},
    'tiktok': {'id': '710', 'username': 'isaiah_dupree'},
    'instagram': {'id': '807', 'username': 'the_isaiah_dupree'},
}


def get_analyzed_videos() -> List[Dict[str, Any]]:
    """Get all analyzed Sora videos from database"""
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ov.id, ov.filename, ov.file_path, av.ai_title, av.platform_captions, av.virality_score
        FROM original_videos ov
        JOIN analyzed_videos av ON av.original_video_id = ov.id
        WHERE ov.source = 'sora_cleaned'
        ORDER BY ov.created_at DESC
    """)
    
    videos = []
    for row in cursor.fetchall():
        videos.append({
            'id': str(row[0]),
            'filename': row[1],
            'file_path': row[2],
            'title': row[3],
            'captions': row[4],
            'virality_score': row[5]
        })
    
    cursor.close()
    conn.close()
    return videos


async def publish_video(video: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Publish a single video to a platform"""
    from services.publish_service import PublishService
    import json
    
    service = PublishService()
    account = ACCOUNTS.get(platform)
    
    if not account:
        return {'success': False, 'error': f'Unknown platform: {platform}'}
    
    # Parse captions
    captions = video['captions']
    if isinstance(captions, str):
        captions = json.loads(captions)
    
    # Get platform-specific caption
    if platform == 'youtube':
        text = captions.get('youtube_description', video['title'])
        title = video['title']
    elif platform == 'tiktok':
        text = captions.get('tiktok_caption', video['title'])[:150]
        title = None
    elif platform == 'instagram':
        text = captions.get('instagram_caption', video['title'])
        title = None
    else:
        text = video['title']
        title = None
    
    # Add hashtags
    text += "\n\n#AI #Sora #Viral #Shorts"
    
    file_path = Path(video['file_path'])
    if not file_path.exists():
        return {'success': False, 'error': f'File not found: {file_path}'}
    
    logger.info(f"Publishing {video['filename']} to {platform}...")
    logger.info(f"  Title: {video['title'][:50]}...")
    logger.info(f"  Account: {account['username']}")
    
    # Build target config
    target_config = {}
    if platform == 'youtube' and title:
        target_config['title'] = title
    
    # Execute full publish flow
    result = await service.full_publish_flow(
        file_path=file_path,
        account_id=account['id'],
        platform=platform,
        text=text,
        target_config=target_config,
        cleanup_storage=True,
        use_supabase=False  # Use GDrive (Supabase bucket not configured)
    )
    
    if result['success']:
        logger.success(f"✅ Published to {platform}: {result.get('post_submission_id')}")
        
        # Poll for platform URL
        if result.get('post_submission_id'):
            logger.info("Polling for platform URL...")
            for i in range(10):
                await asyncio.sleep(3)
                status = await service.get_post_status(result['post_submission_id'])
                if status.get('publicUrl'):
                    logger.success(f"🔗 Platform URL: {status['publicUrl']}")
                    result['platform_url'] = status['publicUrl']
                    break
                elif status.get('errorMessage'):
                    logger.error(f"❌ Post failed: {status['errorMessage']}")
                    break
    else:
        logger.error(f"❌ Publish failed: {result.get('error')}")
    
    return result


async def main():
    parser = argparse.ArgumentParser(description='Publish Sora videos to social media')
    parser.add_argument('--list', action='store_true', help='List available videos')
    parser.add_argument('--video', type=str, help='Specific video filename to publish')
    parser.add_argument('--all', action='store_true', help='Publish all videos')
    parser.add_argument('--platform', type=str, default='youtube', 
                       choices=['youtube', 'tiktok', 'instagram', 'all'],
                       help='Platform to publish to')
    parser.add_argument('--limit', type=int, default=3, help='Max videos to publish')
    
    args = parser.parse_args()
    
    # Get videos from database
    videos = get_analyzed_videos()
    
    if not videos:
        print("❌ No analyzed Sora videos found in database")
        return 1
    
    if args.list:
        print(f"\n📹 ANALYZED SORA VIDEOS ({len(videos)} total)")
        print("-" * 60)
        for i, v in enumerate(videos, 1):
            print(f"  {i}. {v['filename']:<35} score: {v['virality_score']}")
        print()
        return 0
    
    # Filter videos
    if args.video:
        videos = [v for v in videos if args.video in v['filename']]
        if not videos:
            print(f"❌ Video not found: {args.video}")
            return 1
    elif not args.all:
        videos = videos[:1]  # Default: first video only
    else:
        videos = videos[:args.limit]
    
    # Determine platforms
    platforms = ['youtube', 'tiktok'] if args.platform == 'all' else [args.platform]
    
    print(f"\n🚀 PUBLISHING {len(videos)} VIDEO(S) TO {platforms}")
    print("=" * 60)
    
    results = []
    for video in videos:
        for platform in platforms:
            print(f"\n📤 [{video['filename']}] → {platform}")
            result = await publish_video(video, platform)
            results.append({
                'video': video['filename'],
                'platform': platform,
                'success': result['success'],
                'url': result.get('platform_url'),
                'error': result.get('error')
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PUBLISH SUMMARY")
    print("-" * 60)
    
    success = sum(1 for r in results if r['success'])
    print(f"  Total: {len(results)} | Success: {success} | Failed: {len(results) - success}")
    
    for r in results:
        status = "✅" if r['success'] else "❌"
        url_or_error = r.get('url') or r.get('error', '')
        print(f"  {status} {r['video']:<30} → {r['platform']:<10} {url_or_error[:40]}")
    
    return 0 if success == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

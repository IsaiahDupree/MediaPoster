"""
Fetch YouTube transcripts from Ben Facciani's channel
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from datetime import datetime

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
except ImportError:
    print("Installing youtube-transcript-api...")
    os.system("pip install youtube-transcript-api")
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

try:
    import yt_dlp
except ImportError:
    print("Installing yt-dlp...")
    os.system("pip install yt-dlp")
    import yt_dlp

def get_channel_videos(channel_url: str, max_videos: int = 10) -> list:
    """Get list of videos from a YouTube channel."""
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlist_items': f'1:{max_videos}',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(channel_url, download=False)
        
    videos = []
    if 'entries' in result:
        for entry in result['entries']:
            if entry:
                videos.append({
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                })
    
    return videos


def get_transcript(video_id: str) -> dict:
    """Get transcript for a single video."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.fetch(video_id)
        full_text = " ".join([t.text for t in transcript_list])
        return {
            'success': True,
            'transcript': full_text,
            'segments': [{'text': t.text, 'start': t.start, 'duration': t.duration} for t in transcript_list]
        }
    except TranscriptsDisabled:
        return {'success': False, 'error': 'Transcripts disabled for this video'}
    except NoTranscriptFound:
        return {'success': False, 'error': 'No transcript found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    channel_url = "https://www.youtube.com/@BenFacciani/videos"
    
    print("=" * 60)
    print("Fetching YouTube Transcripts from Ben Facciani's Channel")
    print("=" * 60)
    
    # Get videos from channel
    print("\n📹 Fetching video list...")
    videos = get_channel_videos(channel_url, max_videos=10)
    print(f"Found {len(videos)} videos")
    
    results = []
    
    for video in videos:
        print(f"\n🎬 Processing: {video['title']}")
        print(f"   ID: {video['id']}")
        
        transcript_result = get_transcript(video['id'])
        
        result = {
            'video_id': video['id'],
            'title': video['title'],
            'url': video['url'],
            **transcript_result
        }
        results.append(result)
        
        if transcript_result['success']:
            print(f"   ✓ Transcript: {len(transcript_result['transcript'])} chars")
        else:
            print(f"   ✗ Error: {transcript_result['error']}")
    
    # Save results
    output_file = Path("/tmp/ben_facciani_transcripts.json")
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'channel': channel_url,
            'videos': results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Print successful transcripts
    print("\n" + "=" * 60)
    print("TRANSCRIPTS FOUND")
    print("=" * 60)
    
    for result in results:
        if result.get('success'):
            print(f"\n### {result['title']} ###")
            print(f"URL: {result['url']}")
            print("-" * 40)
            # Print first 1000 chars
            transcript = result['transcript']
            if len(transcript) > 2000:
                print(transcript[:2000] + "...[truncated]")
            else:
                print(transcript)
            print()
    
    return results


if __name__ == "__main__":
    main()

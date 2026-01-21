# PRD: YouTube Playlist → Content Pipeline Automation

**Version:** 1.1  
**Date:** January 20, 2026  
**Status:** Active (Make.com)  
**Priority:** High  
**Platform:** Make.com (Integromat)

---

## Executive Summary

This automation monitors a YouTube playlist for new videos, extracts transcripts via RapidAPI, generates AI-powered insights using GPT-4o, creates Medium blog posts, and distributes content across social platforms (Bluesky, Threads, Buffer). The workflow is triggered when videos are saved to a specific playlist and logged to a Google Sheet.

---

## Workflow Overview

### Name
**Rapid API Youtube Insight To Medium Notes V10 (Content Created)**

### Trigger
Videos saved to YouTube playlist → Logged to Google Sheet with status "ID_Captured"

### Data Source
- **Google Sheet:** `Youtube Wisdom copy`
- **Sheet ID:** `1HhB3A4BgJZRlQsRfwZZp8Krke7YT--Hsy0ybcnfZ7HQ`
- **Filter Column:** S (Status) = "ID_Captured"

---

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  TRIGGER: Google Sheets Filter                                  │
│  • Sheet: Youtube Wisdom copy                                   │
│  • Filter: Status (S) = "ID_Captured"                          │
│  • Returns: 1 row at a time (newest first)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Get Video Duration (YouTube Data API)                  │
│  Check if video length > 20 minutes                             │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ROUTER: Branch based on video duration                         │
├─────────────────────────────────────────────────────────────────┤
│  Route A (≤20 min): Use RapidAPI transcript                     │
│  Route B (>20 min): Download video + local transcription        │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2a: Fetch YouTube Transcript (Short Videos)               │
│  API: youtube-transcriptor.p.rapidapi.com                       │
│  Endpoint: /transcript?video_id={id}&lang=en                    │
├─────────────────────────────────────────────────────────────────┤
│  STEP 2b: Local Transcript (Long Videos >20 min)                │
│  1. Download video via yt-dlp                                   │
│  2. Extract audio (ffmpeg)                                      │
│  3. Transcribe via Whisper API                                  │
│  4. Clean up temp files                                         │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Parse JSON Response                                    │
│  Extract transcript data from API response                      │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ROUTER: Branch based on transcript success                     │
├─────────────────────────────────────────────────────────────────┤
│  Route A (Status 200): Process transcript                       │
│  Route B (Error): Handle failure                                │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: GPT-4o Processing                                      │
│  • Decode JSON to readable transcript                           │
│  • Generate insights and overview                               │
│  • Create SEO title                                             │
│  • Format for Medium blog post (HTML)                          │
│  • Generate social media snippets                               │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Content Distribution                                   │
├─────────────────────────────────────────────────────────────────┤
│  • Upload thumbnail to Google Drive                             │
│  • Create Medium blog post                                      │
│  • Post to Bluesky (via Blotato API)                           │
│  • Post to Threads (via Blotato API)                           │
│  • Post to Buffer (multiple profiles)                          │
│  • Update Google Sheet with URLs and status                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Schema

### Google Sheet Columns

| Column | Field | Description |
|--------|-------|-------------|
| A | Playlist ID | YouTube playlist identifier |
| B | Video ID | YouTube video identifier |
| C | Title | Original video title |
| D | Description | Video description |
| E | Transcription | Raw transcript |
| F | Overview | AI-generated overview |
| G | Insights | AI-generated insights |
| H | Owner | Channel name |
| I | Owner ID | Channel ID |
| J | Publish Time | Video publish date |
| K | Image File ID | Google Drive thumbnail ID |
| L | SEO Title | AI-optimized title |
| M | Medium Image URL | Public image URL |
| N | ID1 | Internal reference |
| O | Medium Blog Post (HTML) | Full blog content |
| P | ID2 | Medium post ID |
| Q | Medium Blog URL | Published blog URL |
| R | (Reserved) | - |
| S | Status | Workflow status |
| T-Z | Content 1-7 | Social media variations |

### Status Values

| Status | Meaning |
|--------|---------|
| `ID_Captured` | Ready for processing |
| `Downloading` | Video being downloaded (>20 min) |
| `Transcribing_Local` | Local Whisper transcription in progress |
| `Transcript_Fetched` | Transcript obtained |
| `AI_Processed` | GPT analysis complete |
| `Published` | All content distributed |
| `Error` | Processing failed |

---

## Long Video Fallback System (>20 Minutes)

### Overview

RapidAPI transcript services can fail or return incomplete results for longer videos. When a video exceeds **20 minutes**, the system automatically falls back to a local transcription pipeline using MediaPoster's infrastructure.

### Duration Check

```python
# Get video duration from YouTube Data API or video metadata
duration_seconds = get_video_duration(video_id)
LONG_VIDEO_THRESHOLD = 20 * 60  # 20 minutes in seconds

if duration_seconds > LONG_VIDEO_THRESHOLD:
    transcript = await local_transcription_pipeline(video_id)
else:
    transcript = await rapidapi_transcript(video_id)
```

### Local Transcription Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  LONG VIDEO DETECTED (>20 min)                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Download Video                                         │
│  Tool: yt-dlp                                                   │
│  Output: /tmp/youtube_downloads/{video_id}.mp4                  │
│  Options: --format best[ext=mp4] --no-playlist                  │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Extract Audio                                          │
│  Tool: ffmpeg                                                   │
│  Output: /tmp/youtube_downloads/{video_id}.mp3                  │
│  Command: ffmpeg -i input.mp4 -vn -acodec mp3 -ab 128k output   │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Transcribe with Whisper                                │
│  Option A: OpenAI Whisper API (cloud)                           │
│  Option B: Local Whisper model (faster-whisper)                 │
│  Output: JSON with timestamps + plain text                      │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Cleanup                                                │
│  • Delete temp video file                                       │
│  • Delete temp audio file                                       │
│  • Cache transcript in database                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Continue to GPT-4o Processing...                               │
└─────────────────────────────────────────────────────────────────┘
```

### MediaPoster Implementation

```python
# Backend/services/youtube/local_transcription.py

import subprocess
import os
from openai import OpenAI

class LocalTranscriptionService:
    """
    Fallback transcription for long YouTube videos (>20 min).
    Downloads video, extracts audio, transcribes with Whisper.
    """
    
    DOWNLOAD_DIR = "/tmp/youtube_downloads"
    LONG_VIDEO_THRESHOLD = 20 * 60  # 20 minutes
    
    def __init__(self):
        self.openai = OpenAI()
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
    
    async def should_use_local(self, video_id: str) -> bool:
        """Check if video exceeds 20 minute threshold."""
        duration = await self.get_video_duration(video_id)
        return duration > self.LONG_VIDEO_THRESHOLD
    
    async def get_video_duration(self, video_id: str) -> int:
        """Get video duration in seconds via yt-dlp."""
        result = subprocess.run([
            "yt-dlp", "--get-duration", "--no-playlist",
            f"https://youtube.com/watch?v={video_id}"
        ], capture_output=True, text=True)
        
        # Parse duration string (e.g., "1:23:45" or "23:45")
        return self._parse_duration(result.stdout.strip())
    
    async def transcribe(self, video_id: str) -> dict:
        """Full local transcription pipeline."""
        video_path = None
        audio_path = None
        
        try:
            # Step 1: Download video
            video_path = await self._download_video(video_id)
            
            # Step 2: Extract audio
            audio_path = await self._extract_audio(video_path)
            
            # Step 3: Transcribe with Whisper
            transcript = await self._transcribe_audio(audio_path)
            
            return {
                "success": True,
                "transcript": transcript,
                "method": "local_whisper",
                "video_id": video_id
            }
            
        finally:
            # Step 4: Cleanup temp files
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
    
    async def _download_video(self, video_id: str) -> str:
        """Download YouTube video using yt-dlp."""
        output_path = f"{self.DOWNLOAD_DIR}/{video_id}.mp4"
        
        subprocess.run([
            "yt-dlp",
            "--format", "best[ext=mp4]/best",
            "--no-playlist",
            "--output", output_path,
            f"https://youtube.com/watch?v={video_id}"
        ], check=True)
        
        return output_path
    
    async def _extract_audio(self, video_path: str) -> str:
        """Extract audio from video using ffmpeg."""
        audio_path = video_path.replace(".mp4", ".mp3")
        
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "libmp3lame", "-ab", "128k",
            "-y", audio_path
        ], check=True)
        
        return audio_path
    
    async def _transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio using OpenAI Whisper API."""
        with open(audio_path, "rb") as audio_file:
            response = self.openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        return response
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse yt-dlp duration string to seconds."""
        parts = duration_str.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0])
```

### API Endpoint

```python
# Backend/api/endpoints/youtube_automation.py

@router.post("/transcript/{video_id}")
async def get_transcript(video_id: str, force_local: bool = False):
    """
    Get YouTube video transcript.
    Auto-selects RapidAPI or local based on duration (>20 min = local).
    """
    local_service = LocalTranscriptionService()
    
    # Check duration or force local
    use_local = force_local or await local_service.should_use_local(video_id)
    
    if use_local:
        result = await local_service.transcribe(video_id)
        return {
            "transcript": result["transcript"],
            "method": "local_whisper",
            "duration_category": "long"
        }
    else:
        # Use RapidAPI for shorter videos
        transcript = await rapidapi_service.get_transcript(video_id)
        return {
            "transcript": transcript,
            "method": "rapidapi",
            "duration_category": "short"
        }
```

### Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `LONG_VIDEO_THRESHOLD` | 1200 (20 min) | Seconds threshold for local fallback |
| `WHISPER_MODEL` | `whisper-1` | OpenAI Whisper model |
| `DOWNLOAD_DIR` | `/tmp/youtube_downloads` | Temp storage for downloads |
| `CLEANUP_AFTER` | `true` | Delete temp files after transcription |

### Cost Comparison

| Method | Cost | Speed | Reliability |
|--------|------|-------|-------------|
| **RapidAPI** | ~$0.001/video | Fast (2-5s) | May fail on long videos |
| **Local Whisper** | ~$0.006/min audio | Slower (1-3 min) | Very reliable |

*Example: 30-min video = ~$0.18 via Whisper API*

### Dependencies

```bash
# Required system tools
brew install yt-dlp ffmpeg

# Python packages (already in requirements.txt)
pip install openai yt-dlp
```

---

## API Integrations

### 1. RapidAPI - YouTube Transcriptor

```
Endpoint: https://youtube-transcriptor.p.rapidapi.com/transcript
Method: GET
Parameters:
  - video_id: YouTube video ID
  - lang: en (English)
Headers:
  - x-rapidapi-host: youtube-transcriptor.p.rapidapi.com
  - x-rapidapi-key: [API_KEY]
```

### 2. OpenAI GPT-4o

```
Model: gpt-4o
Max Tokens: 3500
Temperature: 1
Tasks:
  - Transcript decoding
  - Insight generation
  - SEO title creation
  - Blog post formatting
  - Social snippet generation
```

### 3. Blotato API

```
Endpoint: https://backend.blotato.com/v2/posts
Method: POST
Headers:
  - blotato-api-key: [API_KEY]
Platforms:
  - Bluesky (accountId: 2)
  - Threads (accountId: varies)
```

### 4. Buffer API

```
Connection: Isaiah Dupree account
Profiles:
  - Bluesky (isaiahdupree.bsky.social)
Features:
  - Link shortening
  - Immediate posting
```

### 5. Medium API

```
Integration: Via Make.com module
Features:
  - HTML content support
  - Image embedding
  - Tag assignment
```

---

## AI Prompts Used

### Transcript Decoding
```
Decode this JSON Data from a Youtube Video into a transcript. 
the json file {transcript_json}
```

### Insight Generation
```
Based on this transcript, generate:
1. A comprehensive overview (2-3 paragraphs)
2. Key insights and takeaways (5-7 bullet points)
3. SEO-optimized title
4. Social media snippets (280 chars each)
```

### Medium Blog Formatting
```
Format the following content as an HTML blog post:
- Include proper headings (h2, h3)
- Add blockquotes for key insights
- Include call-to-action
- Embed original video link
```

---

## MediaPoster Integration

### Replication in MediaPoster

This Make.com workflow can be replicated within MediaPoster using:

| Make.com Module | MediaPoster Equivalent |
|-----------------|------------------------|
| Google Sheets Filter | `/api/youtube/playlist/watch` |
| RapidAPI HTTP | `/api/youtube/transcript/{video_id}` |
| GPT-4o | `/api/ai/analyze` |
| Medium Post | `/api/publishing/medium` |
| Blotato Post | `/api/blotato/publish` |
| Buffer Post | `/api/buffer/publish` |

### Proposed MediaPoster Automation

```python
# Backend/automation/youtube_playlist_pipeline.py

class YouTubePlaylistPipeline:
    """
    Automation that mirrors the Make.com workflow:
    YouTube Playlist → Transcript → AI Analysis → Multi-platform publish
    """
    
    async def process_playlist_video(self, video_id: str):
        # 1. Fetch transcript
        transcript = await self.rapidapi_service.get_transcript(video_id)
        
        # 2. AI analysis
        analysis = await self.ai_service.analyze_transcript(
            transcript,
            generate_overview=True,
            generate_insights=True,
            generate_seo_title=True,
            generate_social_snippets=True
        )
        
        # 3. Create Medium blog
        medium_url = await self.medium_service.create_post(
            title=analysis.seo_title,
            content_html=analysis.blog_html,
            tags=analysis.suggested_tags
        )
        
        # 4. Distribute to social
        await self.blotato_service.post(
            platform='bluesky',
            text=analysis.social_snippet,
            account_id=2
        )
        
        await self.buffer_service.post(
            profiles=['isaiahdupree.bsky.social'],
            text=analysis.social_snippet
        )
        
        # 5. Update tracking
        await self.update_status(video_id, 'Published', medium_url)
```

### API Endpoint for Trigger

```python
# Backend/api/endpoints/youtube_automation.py

@router.post("/playlist/process")
async def process_playlist_video(video_id: str, playlist_id: str):
    """
    Trigger the YouTube → Content pipeline for a specific video.
    Can be called by:
    - Webhook from Google Sheets
    - Manual trigger from dashboard
    - Scheduled polling
    """
    pipeline = YouTubePlaylistPipeline()
    result = await pipeline.process_playlist_video(video_id)
    return {"status": "success", "medium_url": result.medium_url}
```

---

## Dashboard Integration

### Automation Card

```
┌─────────────────────────────────────────────────────────────────┐
│  📺 YouTube Playlist → Content Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│  Status: ✅ Active (Make.com)                                   │
│  Last Run: Jan 20, 2026 8:15 PM                                │
│  Videos Processed: 47                                          │
│  Success Rate: 94%                                             │
│                                                                   │
│  Outputs:                                                        │
│  • 47 Medium blog posts                                         │
│  • 141 social posts (Bluesky, Threads, Buffer)                 │
│                                                                   │
│  [View Sheet] [Run Now] [View Logs] [Settings]                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Files

### Make.com Scenario JSON

Location: `Backend/automation/make_scenarios/youtube_insight_v10.json`

This file contains the complete Make.com scenario configuration for backup and version control.

---

## Future Enhancements

1. **Native MediaPoster Implementation** - Replace Make.com with internal automation
2. **Multi-language Support** - Process non-English transcripts
3. **Video Clip Extraction** - Extract highlights for short-form content
4. **Analytics Tracking** - Track performance of generated content
5. **A/B Testing** - Test different AI prompts for engagement

---

## Monitoring & Alerts

| Event | Alert |
|-------|-------|
| Transcript fetch failed | Slack notification |
| GPT quota exceeded | Email alert |
| Medium post failed | Dashboard warning |
| 3+ consecutive failures | Pause automation |

---

**Document Owner:** Automation Team  
**Make.com Scenario ID:** (from Make.com dashboard)  
**Last Updated:** January 20, 2026

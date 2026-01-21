# PRD: YouTube Playlist → Content Pipeline Automation

**Version:** 1.0  
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
│  STEP 1: Fetch YouTube Transcript                               │
│  API: youtube-transcriptor.p.rapidapi.com                       │
│  Endpoint: /transcript?video_id={id}&lang=en                    │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Parse JSON Response                                    │
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
| `Transcript_Fetched` | Transcript obtained |
| `AI_Processed` | GPT analysis complete |
| `Published` | All content distributed |
| `Error` | Processing failed |

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

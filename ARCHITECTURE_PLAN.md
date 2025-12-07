# Designing a Modular macOS Social Video Automation System

## Architecture Overview

This system is composed of several modular components that together automate the workflow from capturing iPhone videos to posting optimized short clips across platforms. Each module can operate independently or as part of an integrated pipeline.

**High-level flow:** video ingestion → AI analysis → clip generation → cloud staging → multi-platform upload → post-publish monitoring → data storage

The design emphasizes decoupling, so the Mac app can orchestrate the modules or they can run as standalone services.

## System Modules

| Module | Role & Responsibilities | Key Tools/Technologies |
|--------|------------------------|------------------------|
| Video Ingestion (Sync) | Automatically syncs raw videos from iPhone to Mac storage | iCloud Photos, Apple Photos library API, Image Capture, or AirDrop |
| AI Analysis | Analyzes video content using AI: extracts key frames, generates transcripts, and identifies highlights | FFmpeg (frame extraction), OpenAI Whisper (transcription), OpenAI GPT-4 Vision or image captioning models (frame analysis), OpenCV/CLIP for scene & object detection, Azure/Google Vision |
| Highlight Detection | Detects the most engaging moments using visual, audio, and textual cues | Scene change detection (FFmpeg/OpenCV), audio energy analysis, keyword detection in transcript, LLM-based summarization (GPT-4) to rank highlights |
| Clip Generation | Creates short, "viral-style" clips from highlights with captions, hooks, and visual overlays | FFmpeg (video cutting, overlays), MoviePy or AVFoundation, OpenAI GPT (for generating catchy hook text), OpenAI Whisper or ffmpeg drawtext (for burned-in subtitles) |
| Cloud Staging | Uploads final clips to cloud storage (as temporary holding) and retrieves shareable URLs | Google Drive API (file upload & permission), convert to direct download URL for Blotato |
| Blotato Uploader | Interfaces with Blotato API to distribute videos to all supported social platforms | Blotato API /v2/media and /v2/posts endpoints, HTTP requests (POST) to upload media by URL and trigger multi-platform posting |
| Content Monitor | Checks posting status, collects post URLs and initial performance metrics, handles cleanup | Blotato post status or direct platform APIs (YouTube Data API for views, etc.), scheduled queries after posting, platform deletion APIs for removals |
| Data Storage & Tagging | Stores video content metadata, analysis results, and performance data; organizes content by tags for optimization | Local database (SQLite/CoreData) and/or Supabase (Postgres with storage) for cloud sync. Schema includes tags for topics, hook type, keywords, etc. |
| Orchestration & UI | Provides a Mac-based interface to manage the workflow and allows manual control of each module | Swift app or Electron app on Mac, scheduling via cron or n8n workflows for automation, inter-module communication via files or HTTP |

## Detailed Module Specifications

### 1. Video Ingestion: Syncing iPhone Videos to Mac

**Purpose:** Automatically get new videos from iPhone into Mac environment

**Approaches:**
- **iCloud Photos** (Recommended): Continuous wireless sync when enabled on iPhone. Monitor Photos library via Photos API or filesystem for new videos
- **Direct USB Import (Image Capture)**: Auto-launch and import to folder when iPhone connects via USB
- **Wireless Transfer**: AirDrop or third-party apps (e.g. PhotoSync) for manual/scripted wireless transfer

**Recommended Tools:**
- iCloud Photos (most seamless, no code needed)
- Apple's PhotoKit or AppleScript for detecting new items
- Image Capture API/CLI for automated imports
- Event/notification system for triggering next stage

### 2. AI Analysis: Frame Extraction, Transcription, and Content Analysis

**Purpose:** Extract rich data from video for intelligent processing

**Components:**

#### Frame Extraction
- Sample frames at fixed rate (1 fps) or at scene changes
- **FFmpeg command**: `ffmpeg -i input.mp4 -vf fps=1 frames/%04d.jpg`
- **Scene-change detection**: `ffmpeg -i input.mp4 -vf "select='gt(scene,0.4)',showinfo"`
- Yields representative frame images for analysis

#### Image-to-Text Analysis
- Analyze extracted frames using:
  - OpenAI GPT-4 Vision for frame descriptions
  - OpenAI CLIP model for object/scene identification
  - Azure Computer Vision or Azure Video Indexer for labels, OCR, emotion detection
- Produces text descriptions of visual content

#### Audio Transcription
- OpenAI Whisper model for timestamped transcripts
- Outputs SRT/VTT subtitle file or raw text
- High accuracy without separate audio extraction
- Critical for understanding dialog, narration, voiceover

#### Multimodal Content Analysis
- Detect language and sentiment
- Identify named entities/topics in transcript
- Cross-reference visual cues with transcript
- Example: "Now this is amazing!" + exciting visual = highlight candidate

**Output:** Structured data object containing:
- Full transcript
- List of key frames with descriptions
- Scene boundaries
- Audio volume spikes

**Recommended Tools:**
- FFmpeg (video processing)
- OpenAI Whisper or Whisper API (transcription)
- OpenAI GPT-4 with vision or Azure Video Indexer (frame analysis)
- AssemblyAI or Google Cloud Video Intelligence (alternatives)

### 3. Highlight Detection: Finding the Best Moments

**Purpose:** Identify most engaging segments for short clips

**Detection Signals:**

#### Scene and Activity Changes
- Significant scene changes/camera cuts indicate new segments
- Rapid cuts or scenery changes (e.g., talking head → dramatic visual)
- Timestamps from FFmpeg/OpenCV or Azure scene segmentation

#### Speaker Emphasis & Audio Peaks
- Volume peaks and tone changes flag excitement
- Detect loudness spikes, laughter, applause
- Energetic speech patterns in transcript + audio amplitude

#### Key Phrases in Transcript
- Scan for punchlines, key takeaways, surprising facts
- Use NLP or GPT-4 to identify high-impact sentences
- Detect trending topic keywords

#### Visual Salience
- Unusual or eye-catching visuals (explosions, demonstrations, large text)
- Audience engagement signals (clapping, slide changes)
- Object/scene prominence

**Scoring System:**
- Combine signals to score "highlight potential"
- Example: scene change + excited tone + notable phrase = high score
- Output: Timestamp ranges (e.g., 00:45 to 01:10) with reasoning

**LLM Integration:**
Prompt GPT-4: "Identify 2-3 of the most interesting or important moments in this video, with timestamps and reasoning."

**Recommended Tools:**
- OpenAI GPT-4 (text analysis)
- PysceneDetect (scene detection)
- Academic models like Lighthouse for video moment retrieval
- Audiorista-style algorithms for excitement detection

### 4. Clip Generation: Producing Viral-Style Short Videos

**Purpose:** Create polished 15-60 second clips optimized for social media

**Key Tasks:**

#### Video Trimming & Resizing
- Cut video to highlight timestamp range using FFmpeg
- Resize/crop for target aspect ratio (9:16 portrait for TikTok/Reels)
- Apply blurred background effect for horizontal → vertical conversion

#### Caption Generation and Burn-in
- Generate subtitles from Whisper transcript with timestamps
- Overlay text using FFmpeg drawtext filter or SRT file
- Style: Large sans-serif text with colored background
- Word-by-word highlighting (viral TikTok style)
- Reference: m1guelpf/auto-subtitle project

#### Catchy Text Hooks
- Generate punchy headline or question for first 5 seconds
- Use GPT-4 based on clip content or striking quotes
- Overlay as centered big text or top/bottom banner
- Templates: listicles, shocking facts, questions, negative hooks ("stop doing X")

#### Visual Enhancements
- **Progress bars**: Animated rectangle showing video progress (encourages completion)
- **Emojis/overlays**: Add 🔥 emoji for exciting moments, arrows for emphasis
- **FFmpeg overlay filter**: Image overlays with specified timing
- **Picture-in-picture**: Pop up screenshots of tweets, quotes, etc.

#### Segment Branding and Formatting
- Optional outro with CTA text ("Follow for more!", "Link in bio")
- Consistent style: fonts, colors, watermark logo
- Append static image or text screen at end

**Output:**
- Ready-to-post MP4 file
- Metadata: auto-generated caption, suggested title, hashtags
- File naming with title/keywords

**Recommended Tools:**
- FFmpeg (video editing, overlays, subtitles)
- MoviePy or ffmpeg-python (Python libraries for filter graphs)
- Apple AVFoundation (alternative for macOS)
- OpenAI GPT-4 (hook lines, titles)
- Viral content hook templates library

### 5. Cloud Staging: Google Drive Integration

**Purpose:** Upload clips to cloud storage and obtain shareable URLs for Blotato

**Process:**

#### Uploading to Drive
- Use Google Drive API (v3) to upload files
- Target specific folder (e.g., "Staging")
- Set sharing permission: "anyone with link can view"
- Retrieve webViewLink or webContentLink from API

#### Shareable Link Conversion
- Convert Drive share link to direct download URL
- Format: `https://drive.google.com/uc?export=download&id=<FILEID>`
- Required for Blotato media URL download
- Avoids virus scan interstitial for large files

**Output:**
- Direct download URL for each video
- File ID stored for cleanup
- Content accessible by posting backend

**Recommended Tools:**
- Google Drive API client libraries (Python API client recommended)
- OAuth or service account authentication
- Chunked upload for large files
- gdrive CLI (alternative, but API is more flexible)

### 6. Blotato Integration: Multi-Platform Posting

**Purpose:** Distribute videos across social platforms using unified API

**API Workflow:**

#### Step 1: Upload Media to Blotato
- Call `/v2/media` endpoint
- Provide Google Drive download URL in JSON payload
- Blotato fetches and stores media on their CDN
- Response: `{ "url": "https://database.blotato.com/....mp4" }`

#### Step 2: Publish Post
- Call `/v2/posts` endpoint
- Specify: caption text, mediaUrls array, target platforms/accounts
- Platform-specific fields (TikTok privacy, Instagram reel vs story)
- Loop through platforms or use combined call

#### Step 3: Scheduling/Instant Post
- Post immediately (no scheduledTime) or schedule
- Blotato handles platform login and upload

#### Step 4: Response Handling
- Capture post ID or job ID from response
- Store Blotato post ID and platform content IDs
- Handle synchronous or asynchronous responses

**Benefits:**
- Unified API instead of maintaining separate platform integrations
- Credentials stored in Blotato
- Simplified multi-platform distribution

**Recommended Tools:**
- Blotato REST API with API key authentication
- HTTP client (Python requests or Swift URLSession)
- JSON payload construction
- Error handling for rate limits, format issues

### 7. Post-Publish Checkback: Monitoring and Cleanup

**Purpose:** Verify posts, gather metrics, and remove low-performers

**Monitoring Tasks:**

#### Delayed Status Check (5-10 minutes)
- Verify post is live on each platform
- Fetch post URL or ID from Blotato or platform APIs
- **YouTube**: YouTube Data API for video URL and statistics
- **TikTok**: Construct URL from ID/handle or rely on Blotato
- **Instagram**: Graph API for business accounts (media URL, insights)

#### Collect Performance Metrics
- Record: view count, likes, comments
- Early metrics visible within minutes on fast platforms (TikTok)
- Log in database for tracking

#### Identify Failures
- Mark failed posts (platform rejection, upload issues)
- Alert or retry logic
- Attempt remedies (re-cut shorter version, skip platform)

#### Remove Low-Performers
- Delete posts with near-zero views after first check
- Threshold: e.g., <100 views in 10 minutes on TikTok
- **YouTube**: Delete via YouTube Data API
- **TikTok**: Delete via Blotato endpoint `/v2/videos/:id/delete` if available
- Keep profiles "clean" to maintain engagement rate

#### Finalize Post Records
- Update database with confirmed post URLs
- Store for later analysis
- Schedule further checkbacks (1 hour, 24 hours) for growth tracking

**Recommended Tools:**
- Platform APIs (YouTube, Facebook/Instagram Graph API)
- Web scraping for TikTok stats (if no API)
- Blotato analytics endpoints (if available)
- Platform deletion APIs with user auth tokens

### 8. Content Tagging and Metadata Schema

**Purpose:** Organize content for performance optimization and learning

#### Original Video Record
```
- video_id (unique identifier)
- source (e.g., iPhone Camera Roll, album name)
- date_recorded
- date_processed
- transcript (full text)
- topics/keywords (e.g., "fitness, nutrition")
- duration
- analysis_data (JSON: frame descriptions, scene timestamps)
```

#### Clip Records
```
- clip_id (unique, linked to parent video)
- parent_video_id
- segment_start
- segment_end
- clip_duration
- hook_text (catchy title/hook used)
- caption_text (description for posting)
- tags (array: ["tutorial", "AI tool", "hook:listicle", "CTA:yes"])
- platform_posts (JSON: platform, post URL/ID, post time)
- initial_views
- initial_likes
- status ("posted", "deleted after 10min", "failed upload")
```

#### Performance Tags
- **Content Category**: educational, entertainment, personal story
- **Hook Type**: question, listicle, bold statement, story, negative hook, tutorial
- **Presence of CTA**: boolean for call-to-action
- **Visual Elements**: has_progress_bar, emoji_used, text_overlay
- **Keywords**: main keyword targeted (important for TikTok SEO)
- **Audience Reaction**: humor, inspirational, shocking (predicted)

#### Metrics Tracking
```
Table: metrics
- clip_id
- platform
- timestamp
- views
- likes
- comments
```

**Analysis Capabilities:**
- Query by hook type and performance
- Compare topic performance across platforms
- Identify viral vs. DOA content patterns
- Growth curve analysis

**External Integration:**
- Supabase Postgres for relations and SQL queries
- Supabase Storage for video files/thumbnails
- Supabase Edge Functions or N8N for automated triggers
- Analytics reports when video exceeds thresholds

### 9. Orchestration & UI

**Purpose:** Coordinate modules and provide user control

**Options:**

#### Local (Mac) Deployment
- Mac handles all processing: detection, AI models, FFmpeg, API calls
- Requires sufficient compute (Apple Silicon recommended for Whisper)
- Advantages: privacy, lower cloud costs
- Needs stable internet for OpenAI and Blotato APIs
- Menu bar app or daemon for orchestration

#### Cloud-Assisted Deployment
- Delegate AI analysis to cloud services (OpenAI Whisper API, Azure Video Indexer)
- Offload CPU/GPU intensive tasks
- Mac assembles results
- Video rendering can be cloud-based but transfer may be slower

#### Hybrid Storage
- Local metadata (SQLite/CoreData) with Supabase backup
- Cloud storage for transcripts and analysis results
- Multi-machine/user access via Supabase
- Long-term archival in Supabase Storage or S3

#### Scalability Options
- Containerize modules for cloud deployment
- Serverless functions watching cloud storage buckets
- Multiple Mac instances for different channels
- Mix-and-match: AI Analyzer on cloud VM, Mac for sync/UI

#### Fault Tolerance
- Store intermediate results (DB or disk)
- Resume processing after crashes
- Queue system for pending tasks

**Recommended Tools:**
- Swift app or Electron app for Mac UI
- Cron or n8n for workflow scheduling
- Inter-module communication via files or HTTP
- Keychain or environment variables for API keys
- Service account authentication for cloud services

## Deployment Architecture

### Local Deployment
- **Best for**: Individual creators, privacy-focused, Mac with Apple Silicon
- **Components**: All modules on Mac
- **Storage**: Local SQLite + optional Supabase sync
- **Compute**: Local Whisper, FFmpeg, orchestration

### Cloud-Assisted Deployment
- **Best for**: Heavy processing, team collaboration
- **Components**: AI analysis in cloud, Mac for orchestration
- **Storage**: Supabase primary, local cache
- **Compute**: Cloud APIs (OpenAI, Azure), local FFmpeg

### Hybrid Deployment
- **Best for**: Scalability with local control
- **Components**: Critical path on Mac, analysis offloadable
- **Storage**: Supabase primary with local working copies
- **Compute**: Smart distribution based on task

## Security Considerations

- Secure storage of API keys (Keychain, env vars, Supabase server-side)
- OAuth/service account for Google APIs
- Restricted Drive folder permissions
- No credential exposure in cloud deployments

## Implementation Phases

### Phase 1: Core Pipeline
1. Video Ingestion (iCloud Photos monitoring)
2. Basic FFmpeg frame extraction
3. Whisper transcription
4. Simple clip generation
5. Google Drive upload
6. Blotato single-platform posting

### Phase 2: AI Enhancement
1. GPT-4 Vision frame analysis
2. Intelligent highlight detection
3. Automated hook generation
4. Caption styling and overlays
5. Visual enhancements (progress bars, emojis)

### Phase 3: Multi-Platform & Analytics
1. Multi-platform Blotato integration
2. Post-publish monitoring
3. Performance metrics collection
4. Low-performer deletion
5. Database schema implementation

### Phase 4: Optimization & Learning
1. Content tagging system
2. Performance analysis queries
3. A/B testing framework
4. Automated strategy adjustments
5. Dashboard UI with insights

### Phase 5: Advanced Features
1. AI video service integrations
2. Watermark removal
3. N8N workflow automation
4. Team collaboration features
5. Mobile monitoring app

## Success Metrics

- **Automation Rate**: % of videos processed without manual intervention
- **Posting Success Rate**: % of clips successfully posted to all target platforms
- **Engagement Rate**: Average views/likes per clip across platforms
- **Processing Time**: Minutes from iPhone capture to live post
- **Cost Efficiency**: API costs per video processed
- **Content Performance**: Improvement in engagement over time

## Conclusion

This modular macOS-based system automates the journey from raw footage to multi-platform social media content. By breaking the workflow into distinct components, it offers flexibility and robustness. Each module uses specialized tools most suited to its task.

The recommended architecture ensures content is not only mass-produced but also optimized using AI to find the best moments and present them with proven engagement boosters. The data layer turns automation into a learning loop, enabling continuous improvement of content strategy.

By supporting standalone operation of components, the design allows users to plug-in or use parts as needed, resulting in a highly automated yet modular and extensible system for social video production—from pocket to platform, with AI at its core.

# MediaPoster - Phased Development Plan

## Overview

Building a complete video automation system from iPhone to multi-platform distribution in 6 phases. Each phase is independently testable and builds on the previous one.

**Timeline**: 6-8 weeks for full MVP
**Testing**: Real integrations, no mocks
**Deployment**: Local testing → Production deployment

---

## ✅ Phase 0: Foundation (COMPLETED)

**Status**: ✅ Done  
**Duration**: Completed  
**What's Built**:

- ✅ Next.js 15 frontend dashboard
- ✅ FastAPI backend with WebSocket
- ✅ PostgreSQL/Supabase database (11 tables)
- ✅ Video ingestion system (iCloud, USB, AirDrop, file watching)
- ✅ Video validation and metadata extraction
- ✅ API endpoints (videos, ingestion, jobs, analytics)
- ✅ Testing infrastructure (no mocks)
- ✅ Blotato API key configured

**Can Test Now**:
- Video upload and validation
- Real-time file detection
- Database CRUD operations
- API server with Swagger docs

---

## 🎯 Phase 1: AI Analysis Module

**Goal**: Extract intelligence from videos using AI
**Duration**: 1-2 weeks
**Priority**: High

### Features to Build

#### 1.1 Audio Transcription (Whisper)
- Integrate OpenAI Whisper API
- Extract audio from video
- Generate timestamped transcripts
- Support SRT/VTT subtitle formats
- Store transcripts in database

#### 1.2 Frame Extraction
- FFmpeg-based frame sampling (1 fps or scene-based)
- Scene change detection
- Key frame identification
- Store frame metadata

#### 1.3 Visual Analysis (GPT-4 Vision)
- Analyze extracted frames with GPT-4 Vision
- Generate frame descriptions
- Detect objects, text, people
- Identify visual themes

#### 1.4 Audio Analysis
- Volume level detection
- Silence detection
- Audio peak identification
- Speech vs. music classification

#### 1.5 Multimodal Content Understanding
- Combine transcript + visual data
- Generate video summary
- Extract key topics/keywords
- Sentiment analysis

### Deliverables

```
backend/modules/ai_analysis/
├── __init__.py
├── whisper_service.py          # Whisper transcription
├── frame_extractor.py          # FFmpeg frame extraction
├── vision_analyzer.py          # GPT-4 Vision analysis
├── audio_analyzer.py           # Audio processing
└── content_analyzer.py         # Multimodal synthesis

backend/api/endpoints/
└── analysis.py                 # AI analysis API endpoints

backend/tests/
└── test_ai_analysis.py         # Real API tests
```

### API Endpoints

```
POST /api/analysis/transcribe/{video_id}
POST /api/analysis/extract-frames/{video_id}
POST /api/analysis/analyze-frames/{video_id}
POST /api/analysis/analyze-audio/{video_id}
POST /api/analysis/full-analysis/{video_id}
GET  /api/analysis/status/{job_id}
```

### Testing Checklist

- [ ] Whisper transcribes real video (test with 30s clip)
- [ ] Frames extracted at correct intervals
- [ ] GPT-4 Vision describes frames accurately
- [ ] Audio peaks detected correctly
- [ ] Full analysis completes end-to-end
- [ ] Results stored in database
- [ ] API returns proper status codes

### Success Criteria

✅ Given a video, system produces:
- Complete transcript with timestamps
- 10-30 key frames with descriptions
- Audio analysis (peaks, silence)
- Video summary and topics

**Time to Test**: Real 1-minute video should process in ~30-60 seconds

---

## 🎬 Phase 2: Highlight Detection Module

**Goal**: Identify the best moments for short clips
**Duration**: 1 week
**Priority**: High

### Features to Build

#### 2.1 Scene Detection
- FFmpeg scene change detection
- Timestamp extraction
- Shot boundary detection
- Scene scoring

#### 2.2 Audio Signal Processing
- Volume spike detection
- Speech emphasis detection
- Laughter/applause detection
- Energy level analysis

#### 2.3 Transcript Analysis
- Key phrase extraction
- Question detection
- Punchline identification
- Hook potential scoring

#### 2.4 Visual Salience
- Unusual visual detection
- On-screen text detection
- Audience engagement signals
- Visual interest scoring

#### 2.5 AI-Powered Ranking
- Multi-signal scoring algorithm
- GPT-4 highlight recommendations
- Timestamp ranking
- Reasoning generation

### Deliverables

```
backend/modules/highlight_detection/
├── __init__.py
├── scene_detector.py           # Scene change detection
├── audio_signals.py            # Audio analysis
├── transcript_scanner.py       # Key phrase detection
├── visual_detector.py          # Visual salience
├── highlight_ranker.py         # Scoring algorithm
└── gpt_recommender.py          # LLM-based ranking

backend/api/endpoints/
└── highlights.py               # Highlight API endpoints
```

### API Endpoints

```
POST /api/highlights/detect/{video_id}
GET  /api/highlights/{video_id}
POST /api/highlights/{highlight_id}/approve
POST /api/highlights/{highlight_id}/reject
GET  /api/highlights/{highlight_id}/reasoning
```

### Testing Checklist

- [ ] Scene changes detected accurately
- [ ] Audio peaks identified correctly
- [ ] Key phrases extracted from transcript
- [ ] Visual salience scores make sense
- [ ] Multi-signal scoring produces good results
- [ ] GPT-4 recommendations align with manual review
- [ ] Top 3 highlights are actually interesting

### Success Criteria

✅ Given a 5-minute video, system identifies:
- 3-5 high-quality highlight moments
- Each 15-60 seconds long
- With reasoning for each selection
- 80%+ accuracy vs. manual review

**Time to Test**: Process 5-min video in ~2 minutes, return ranked highlights

---

## ✨ Phase 3: Clip Generation Module

**Goal**: Create viral-style short videos from highlights
**Duration**: 1-2 weeks
**Priority**: High

### Features to Build

#### 3.1 Video Editing
- FFmpeg clip extraction
- Aspect ratio conversion (9:16)
- Quality optimization
- Fade in/out effects

#### 3.2 Caption Generation
- Whisper subtitle extraction for segment
- Word-level timing
- Caption styling (fonts, colors)
- Burn-in with FFmpeg drawtext

#### 3.3 Hook Text Generation
- GPT-4 hook generation
- Multiple hook templates
- A/B testing variants
- Text overlay with timing

#### 3.4 Visual Enhancements
- Progress bar generation
- Emoji overlays
- Arrow/highlight effects
- Picture-in-picture support

#### 3.5 Branding & CTAs
- Watermark overlay
- Outro screen
- Call-to-action text
- Consistent styling

### Deliverables

```
backend/modules/clip_generation/
├── __init__.py
├── video_editor.py             # FFmpeg editing
├── caption_generator.py        # Subtitle creation
├── hook_generator.py           # GPT-4 hooks
├── visual_enhancer.py          # Overlays, effects
├── template_library.py         # Viral templates
└── clip_compiler.py            # Complete clip assembly

backend/api/endpoints/
└── clips.py                    # Clip generation API
```

### API Endpoints

```
POST /api/clips/generate/{highlight_id}
POST /api/clips/generate-batch/{video_id}
GET  /api/clips/{clip_id}
GET  /api/clips/{clip_id}/preview
POST /api/clips/{clip_id}/regenerate
PUT  /api/clips/{clip_id}/edit
```

### Testing Checklist

- [ ] Clip extracted with correct timestamps
- [ ] Aspect ratio converted properly
- [ ] Captions synced with audio
- [ ] Hook text readable and engaging
- [ ] Progress bar animates smoothly
- [ ] Emojis positioned correctly
- [ ] Final clip plays without issues
- [ ] File size optimized for platforms

### Success Criteria

✅ Given a highlight, system produces:
- 15-60 second vertical video (9:16)
- Synced captions in viral style
- Catchy hook in first 3 seconds
- Progress bar at bottom
- <50MB file size
- Ready to post directly

**Time to Test**: Generate clip from highlight in ~30 seconds

---

## ☁️ Phase 4: Cloud Staging & Blotato Integration

**Goal**: Upload clips to cloud and distribute to social platforms
**Duration**: 1 week
**Priority**: High

### Features to Build

#### 4.1 Google Drive Integration
- OAuth authentication
- File upload with progress
- Share link generation
- Direct download URL conversion
- Folder organization

#### 4.2 Blotato Media Upload
- Upload to Blotato from Drive URL
- Get Blotato CDN URL
- Handle upload errors
- Retry logic

#### 4.3 Multi-Platform Publishing
- Platform-specific configurations
- Caption customization per platform
- Hashtag generation
- Posting queue management

#### 4.4 Post Scheduling
- Immediate posting
- Scheduled posting
- Best time recommendations
- Queue management

### Deliverables

```
backend/modules/cloud_staging/
├── __init__.py
├── google_drive.py             # Drive API integration
├── url_converter.py            # Share link conversion
└── storage_manager.py          # File organization

backend/modules/blotato_uploader/
├── __init__.py
├── media_uploader.py           # Upload to Blotato
├── post_publisher.py           # Multi-platform posting
├── platform_config.py          # Platform-specific settings
└── queue_manager.py            # Post scheduling

backend/services/
├── google_drive_service.py
└── blotato_service.py

backend/api/endpoints/
├── storage.py                  # Cloud storage API
└── publishing.py               # Publishing API
```

### API Endpoints

```
POST /api/storage/upload/{clip_id}
GET  /api/storage/{clip_id}/url
DELETE /api/storage/{clip_id}

POST /api/publishing/upload-media/{clip_id}
POST /api/publishing/post/{clip_id}
POST /api/publishing/post-multi/{clip_id}
GET  /api/publishing/status/{post_id}
DELETE /api/publishing/{post_id}
```

### Testing Checklist

- [ ] File uploads to Google Drive
- [ ] Share link converts to direct URL
- [ ] Blotato receives file from URL
- [ ] Media uploads to Blotato CDN
- [ ] Post publishes to single platform
- [ ] Multi-platform posting works
- [ ] Caption variations applied correctly
- [ ] Post IDs returned properly
- [ ] Error handling works (retry, fallback)

### Success Criteria

✅ Given a generated clip:
- Uploads to Google Drive (<30s)
- Converts to direct URL
- Uploads to Blotato successfully
- Posts to TikTok, Instagram, YouTube simultaneously
- Returns post IDs for tracking

**Time to Test**: Upload + post to 3 platforms in ~60 seconds

---

## 📊 Phase 5: Content Monitor & Analytics

**Goal**: Track performance and optimize content strategy
**Duration**: 1 week
**Priority**: Medium

### Features to Build

#### 5.1 Post-Publish Monitoring
- Delayed status checks (10 min, 1 hour, 24 hour)
- Platform API integrations
- Metrics collection (views, likes, comments)
- Post URL verification

#### 5.2 Performance Tracking
- Time-series metrics storage
- Engagement rate calculation
- Growth curve analysis
- Platform comparison

#### 5.3 Low-Performer Deletion
- Threshold-based detection
- Automatic deletion API calls
- Manual review option
- Deletion logs

#### 5.4 Analytics Dashboard
- Performance by hook type
- Best performing platforms
- Keyword effectiveness
- A/B test results

#### 5.5 Optimization Insights
- Content recommendations
- Best posting times
- Hook template performance
- Viral pattern detection

### Deliverables

```
backend/modules/content_monitor/
├── __init__.py
├── post_checker.py             # Status verification
├── metrics_collector.py        # Platform API calls
├── performance_tracker.py      # Analytics
├── low_performer_detector.py   # Deletion logic
└── scheduler.py                # Delayed checks

backend/services/
├── youtube_api.py              # YouTube Data API
├── instagram_api.py            # Instagram Graph API
└── tiktok_scraper.py           # TikTok stats (no public API)

backend/api/endpoints/
├── monitoring.py               # Monitoring API
└── insights.py                 # Analytics insights
```

### API Endpoints

```
POST /api/monitoring/check/{post_id}
GET  /api/monitoring/metrics/{post_id}
POST /api/monitoring/delete-low-performers
GET  /api/monitoring/schedule

GET  /api/insights/summary
GET  /api/insights/performance?platform=X&hook_type=Y
GET  /api/insights/recommendations
GET  /api/insights/best-times
```

### Testing Checklist

- [ ] Initial check after 10 minutes works
- [ ] Platform APIs return metrics
- [ ] Views/likes/comments collected
- [ ] Low performers identified correctly
- [ ] Deletion API calls succeed
- [ ] Analytics queries return insights
- [ ] Recommendations make sense
- [ ] Dashboard shows accurate data

### Success Criteria

✅ After posting:
- First check at 10 minutes (views, post URL)
- Subsequent checks at 1h, 24h, 7d
- Metrics stored in time-series
- Posts with <100 views at 10min deleted
- Analytics dashboard shows performance
- Recommendations generated

**Time to Test**: Schedule checks, verify data collection over 24 hours

---

## 🎨 Phase 6: Watermark Removal & Polish

**Goal**: Handle AI-generated videos and finalize system
**Duration**: 1 week
**Priority**: Medium

### Features to Build

#### 6.1 Watermark Detection
- AI-powered watermark detection
- Common watermark patterns
- Position identification
- Confidence scoring

#### 6.2 Watermark Removal
- Inpainting-based removal
- FFmpeg-based cropping
- Quality preservation
- Metadata cleaning

#### 6.3 AI Video Service Integration
- RunwayML integration (if needed)
- Stable Diffusion integration (if needed)
- Other AI video services
- Output processing pipeline

#### 6.4 System Polish
- Error recovery improvements
- Logging enhancements
- Performance optimization
- Edge case handling

#### 6.5 Production Readiness
- Docker containerization
- Environment configuration
- Deployment scripts
- Monitoring setup

### Deliverables

```
backend/modules/watermark_remover/
├── __init__.py
├── detector.py                 # Watermark detection
├── remover.py                  # Removal algorithms
├── inpainter.py                # AI-based inpainting
└── metadata_cleaner.py         # EXIF cleaning

backend/modules/ai_video_services/
├── __init__.py
├── runway_ml.py                # RunwayML integration
├── stable_diffusion.py         # SD video
└── service_manager.py          # Service orchestration

backend/docker/
├── Dockerfile
├── docker-compose.yml
└── .dockerignore

backend/scripts/
├── deploy.sh
├── backup.sh
└── monitor.sh
```

### API Endpoints

```
POST /api/watermark/detect/{video_id}
POST /api/watermark/remove/{video_id}
GET  /api/watermark/status/{job_id}

POST /api/ai-services/generate
GET  /api/ai-services/status/{job_id}
```

### Testing Checklist

- [ ] Watermark detected accurately
- [ ] Removal preserves video quality
- [ ] Metadata cleaned properly
- [ ] AI service integrations work
- [ ] Docker build succeeds
- [ ] Deployment scripts run
- [ ] Production config validated
- [ ] Monitoring alerts working

### Success Criteria

✅ System handles:
- Videos with watermarks removed cleanly
- AI-generated videos processed
- Production deployment ready
- Monitoring and alerts configured
- Error recovery automatic

**Time to Test**: Process watermarked video, deploy to staging environment

---

## 🎯 Phase Integration & Testing

### After Each Phase

1. **Unit Tests**: Test individual functions
2. **Integration Tests**: Test module interactions
3. **End-to-End Tests**: Test complete workflows
4. **Performance Tests**: Ensure speed targets met
5. **User Acceptance**: Manual review of outputs

### Complete Pipeline Test (After Phase 6)

**Scenario**: iPhone Video → Social Media Posts

1. Record video on iPhone
2. Video syncs via iCloud (Phase 0)
3. System detects and validates (Phase 0)
4. AI analyzes content (Phase 1)
5. System identifies 3 highlights (Phase 2)
6. Generates 3 viral clips (Phase 3)
7. Uploads and posts to platforms (Phase 4)
8. Monitors performance for 24h (Phase 5)
9. Deletes low performers (Phase 5)

**Success**: 3 polished clips live on 3+ platforms within 10 minutes of iPhone recording

---

## 📅 Timeline & Milestones

| Phase | Duration | Cumulative | Key Milestone |
|-------|----------|------------|---------------|
| Phase 0 | ✅ Done | ✅ | Backend + Ingestion working |
| Phase 1 | 1-2 weeks | 2 weeks | AI analysis producing insights |
| Phase 2 | 1 week | 3 weeks | Highlights identified automatically |
| Phase 3 | 1-2 weeks | 5 weeks | Viral clips generated |
| Phase 4 | 1 week | 6 weeks | Multi-platform posting live |
| Phase 5 | 1 week | 7 weeks | Analytics tracking performance |
| Phase 6 | 1 week | 8 weeks | Production ready |

**MVP Target**: 6-8 weeks from now
**First Revenue**: End of Phase 4 (can start posting)
**Full Feature Set**: End of Phase 6

---

## 🚀 Getting Started with Phase 1

Ready to start Phase 1? Here's what to do:

```bash
cd backend

# Create Phase 1 branch
git checkout -b phase-1-ai-analysis

# Create module structure
mkdir -p modules/ai_analysis
touch modules/ai_analysis/__init__.py
touch modules/ai_analysis/whisper_service.py
touch modules/ai_analysis/frame_extractor.py
touch modules/ai_analysis/vision_analyzer.py

# Start building!
```

---

## 📊 Success Metrics by Phase

**Phase 1**: 95%+ transcript accuracy, <60s processing time
**Phase 2**: 80%+ highlight quality (manual review), top-3 all good
**Phase 3**: 90%+ clips ready to post as-is, <50MB files
**Phase 4**: 99%+ upload success rate, <2min total time
**Phase 5**: Real-time metrics, <5min delay for first check
**Phase 6**: 95%+ watermark removal quality, production stable

---

## 💡 Development Philosophy

- **Build incrementally**: Each phase is independently valuable
- **Test continuously**: No mocks, real integrations only
- **Deploy early**: Get feedback from real usage
- **Optimize later**: Make it work, then make it fast
- **Document everything**: Future you will thank you

---

## 🎬 Let's Build!

Phase 0 is complete. Ready to start Phase 1?

**Next Command**:
```bash
cd backend
# We'll start building Whisper integration!
```

Ask me to start any phase when you're ready! 🚀

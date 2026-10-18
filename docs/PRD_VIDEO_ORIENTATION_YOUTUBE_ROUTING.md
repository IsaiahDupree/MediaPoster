# PRD: Video Orientation Detection & YouTube Routing

**Version:** 1.0  
**Date:** December 25, 2024  
**Status:** Implementation Ready  
**Owner:** MediaPoster Team

---

## Executive Summary

Implement intelligent video routing based on orientation and duration. Vertical videos (< 1 minute) go to short-form platforms (TikTok, Instagram Reels, YouTube Shorts), while horizontal videos (> 1 minute) are automatically routed to YouTube as full-length content.

**Key Benefits:**
- Automatic platform selection based on video characteristics
- Optimized content delivery for each platform
- Reduced manual decision-making for creators
- Better engagement through proper format matching

---

## Problem Statement

Creators currently must manually decide which platform to post each video to, leading to:
1. **Suboptimal platform selection** - Horizontal videos posted to TikTok perform poorly
2. **Manual routing decisions** - Time-consuming and error-prone
3. **Missed YouTube opportunities** - Long-form horizontal content not leveraged
4. **Format mismatches** - Wrong aspect ratios for platforms

**Current Pain Points:**
- No automatic detection of video orientation
- No duration-based routing logic
- Manual YouTube channel selection required
- Scheduler doesn't consider video format

---

## Product Vision

### Core Features

**A. Video Orientation Detection**
- Automatic aspect ratio detection (width/height)
- Classification: Vertical (9:16), Horizontal (16:9), Square (1:1)
- Metadata extraction from video files
- Support for all common formats (MP4, MOV, AVI, MKV)

**B. Duration-Based Routing**
- Extract video duration from metadata
- Apply routing rules based on duration thresholds
- Configurable duration limits per platform

**C. YouTube Channel Integration**
- Direct upload to specified YouTube channel
- OAuth 2.0 authentication
- Channel selection UI
- Upload metadata (title, description, tags)
- Privacy settings (public, unlisted, private)

**D. Smart Scheduler Integration**
- Automatic platform selection in scheduler
- Override capability for manual selection
- Visual indicators for routing decisions
- Batch routing for multiple videos

---

## Technical Architecture

### 1. Video Analysis Service

```python
class VideoAnalyzer:
    """
    Analyzes video files to extract orientation and duration.
    """
    
    def analyze_video(self, file_path: str) -> VideoMetadata:
        """
        Extract video metadata using FFmpeg.
        
        Returns:
            VideoMetadata with orientation, duration, resolution
        """
        pass
    
    def detect_orientation(self, width: int, height: int) -> Orientation:
        """
        Determine video orientation from dimensions.
        
        Returns:
            VERTICAL (9:16), HORIZONTAL (16:9), or SQUARE (1:1)
        """
        pass
    
    def get_duration(self, file_path: str) -> float:
        """
        Extract video duration in seconds.
        """
        pass
```

### 2. Routing Engine

```python
class VideoRouter:
    """
    Routes videos to appropriate platforms based on characteristics.
    """
    
    def determine_platforms(
        self,
        orientation: Orientation,
        duration: float,
        user_preferences: Dict
    ) -> List[Platform]:
        """
        Apply routing rules to determine target platforms.
        
        Rules:
        - Vertical + < 60s → TikTok, Instagram Reels, YouTube Shorts
        - Horizontal + > 60s → YouTube (main channel)
        - Horizontal + < 60s → YouTube Shorts
        - Square → Instagram Feed, Facebook
        """
        pass
    
    def should_route_to_youtube(
        self,
        orientation: Orientation,
        duration: float
    ) -> bool:
        """
        Determine if video should go to YouTube main channel.
        """
        return orientation == Orientation.HORIZONTAL and duration > 60
```

### 3. YouTube Upload Service

```python
class YouTubeUploader:
    """
    Handles uploads to YouTube channels.
    """
    
    def __init__(self, credentials: OAuth2Credentials):
        self.youtube = build('youtube', 'v3', credentials=credentials)
    
    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        channel_id: str,
        privacy: str = "public",
        tags: List[str] = None
    ) -> str:
        """
        Upload video to YouTube channel.
        
        Returns:
            Video ID of uploaded video
        """
        pass
    
    def list_channels(self) -> List[Channel]:
        """
        Get list of user's YouTube channels.
        """
        pass
```

### 4. Database Schema

```sql
-- Add orientation and routing fields to videos table
ALTER TABLE videos ADD COLUMN orientation TEXT; -- 'vertical', 'horizontal', 'square'
ALTER TABLE videos ADD COLUMN aspect_ratio FLOAT; -- e.g., 0.5625 for 9:16
ALTER TABLE videos ADD COLUMN duration_seconds FLOAT;
ALTER TABLE videos ADD COLUMN auto_routed BOOLEAN DEFAULT FALSE;
ALTER TABLE videos ADD COLUMN routing_reason TEXT;

-- YouTube channel configuration
CREATE TABLE youtube_channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  channel_id TEXT UNIQUE NOT NULL,
  channel_name TEXT NOT NULL,
  channel_url TEXT,
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMPTZ,
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Video routing history
CREATE TABLE video_routing_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id),
  orientation TEXT NOT NULL,
  duration_seconds FLOAT NOT NULL,
  selected_platforms TEXT[], -- Array of platform names
  routing_rule TEXT, -- Description of rule applied
  manual_override BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_videos_orientation ON videos(orientation);
CREATE INDEX idx_videos_duration ON videos(duration_seconds);
CREATE INDEX idx_youtube_channels_user ON youtube_channels(user_id);
CREATE INDEX idx_routing_log_video ON video_routing_log(video_id);
```

---

## Implementation Phases

### Phase 1: Video Analysis (Week 1)

**Deliverables:**
- [ ] Video analyzer service using FFmpeg
- [ ] Orientation detection algorithm
- [ ] Duration extraction
- [ ] Aspect ratio calculation
- [ ] Database schema updates
- [ ] API endpoint: `POST /api/videos/analyze`

**Success Metrics:**
- Correctly detect orientation for 100% of test videos
- Extract duration within 0.1s accuracy
- Process video metadata in < 2 seconds

### Phase 2: Routing Engine (Week 1)

**Deliverables:**
- [ ] Routing rules engine
- [ ] Platform selection algorithm
- [ ] Configurable routing rules (admin UI)
- [ ] Routing decision logging
- [ ] API endpoint: `POST /api/videos/route`

**Success Metrics:**
- Apply routing rules correctly 100% of time
- Support manual overrides
- Log all routing decisions

### Phase 3: YouTube Integration (Week 2)

**Deliverables:**
- [ ] YouTube OAuth 2.0 flow
- [ ] Channel selection UI
- [ ] Video upload service
- [ ] Upload progress tracking
- [ ] Metadata management (title, description, tags)
- [ ] API endpoints:
  - `GET /api/youtube/channels` - List channels
  - `POST /api/youtube/upload` - Upload video
  - `GET /api/youtube/upload/{id}/status` - Check status

**Success Metrics:**
- Successfully authenticate with YouTube
- Upload videos to correct channel
- Track upload progress accurately
- Handle upload failures gracefully

### Phase 4: Scheduler Integration (Week 2)

**Deliverables:**
- [ ] Update scheduler to use routing engine
- [ ] Visual indicators for auto-routing
- [ ] Manual override UI
- [ ] Batch routing for multiple videos
- [ ] Preview routing decisions before scheduling

**Success Metrics:**
- Scheduler automatically routes 90%+ of videos correctly
- Users can override routing in < 3 clicks
- Batch routing processes 100+ videos in < 10 seconds

---

## Routing Rules

### Default Rules

| Orientation | Duration | Platforms |
|-------------|----------|-----------|
| Vertical (9:16) | < 60s | TikTok, Instagram Reels, YouTube Shorts |
| Vertical (9:16) | > 60s | Instagram Reels, YouTube (if < 90s) |
| Horizontal (16:9) | < 60s | YouTube Shorts, Facebook |
| Horizontal (16:9) | > 60s | **YouTube (Main Channel)** |
| Square (1:1) | Any | Instagram Feed, Facebook |

### Orientation Detection

```python
def detect_orientation(width: int, height: int) -> Orientation:
    """
    Detect video orientation from dimensions.
    
    Thresholds:
    - Vertical: aspect_ratio < 0.75 (e.g., 9:16 = 0.5625)
    - Horizontal: aspect_ratio > 1.33 (e.g., 16:9 = 1.7778)
    - Square: 0.75 <= aspect_ratio <= 1.33
    """
    aspect_ratio = width / height
    
    if aspect_ratio < 0.75:
        return Orientation.VERTICAL
    elif aspect_ratio > 1.33:
        return Orientation.HORIZONTAL
    else:
        return Orientation.SQUARE
```

### Duration Thresholds

```python
DURATION_THRESHOLDS = {
    "short_form": 60,      # < 60s = short-form content
    "medium_form": 300,    # 60-300s = medium-form
    "long_form": 300       # > 300s = long-form
}
```

---

## API Specifications

### 1. Analyze Video

**Endpoint:** `POST /api/videos/analyze`

**Request:**
```json
{
  "video_id": "uuid",
  "file_path": "/path/to/video.mp4"
}
```

**Response:**
```json
{
  "video_id": "uuid",
  "orientation": "horizontal",
  "aspect_ratio": 1.7778,
  "width": 1920,
  "height": 1080,
  "duration_seconds": 125.5,
  "file_size_bytes": 45678901,
  "codec": "h264",
  "bitrate": 2500000,
  "fps": 30
}
```

### 2. Route Video

**Endpoint:** `POST /api/videos/route`

**Request:**
```json
{
  "video_id": "uuid",
  "orientation": "horizontal",
  "duration_seconds": 125.5,
  "user_preferences": {
    "prefer_youtube": true,
    "default_youtube_channel": "channel_id"
  }
}
```

**Response:**
```json
{
  "video_id": "uuid",
  "recommended_platforms": ["youtube"],
  "routing_rule": "horizontal_long_form",
  "reasoning": "Horizontal video over 60 seconds - optimal for YouTube main channel",
  "youtube_channel": {
    "id": "channel_id",
    "name": "My Channel",
    "url": "https://youtube.com/channel/..."
  },
  "alternative_platforms": ["facebook"],
  "can_override": true
}
```

### 3. List YouTube Channels

**Endpoint:** `GET /api/youtube/channels`

**Response:**
```json
{
  "channels": [
    {
      "id": "channel_id_1",
      "name": "Main Channel",
      "url": "https://youtube.com/channel/...",
      "subscriber_count": 10000,
      "is_default": true
    },
    {
      "id": "channel_id_2",
      "name": "Gaming Channel",
      "url": "https://youtube.com/channel/...",
      "subscriber_count": 5000,
      "is_default": false
    }
  ]
}
```

### 4. Upload to YouTube

**Endpoint:** `POST /api/youtube/upload`

**Request:**
```json
{
  "video_id": "uuid",
  "channel_id": "channel_id",
  "title": "My Video Title",
  "description": "Video description with #hashtags",
  "tags": ["tag1", "tag2", "tag3"],
  "privacy": "public",
  "category_id": "22",
  "notify_subscribers": true
}
```

**Response:**
```json
{
  "upload_id": "uuid",
  "youtube_video_id": "dQw4w9WgXcQ",
  "status": "processing",
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "estimated_processing_time": 300
}
```

### 5. Check Upload Status

**Endpoint:** `GET /api/youtube/upload/{upload_id}/status`

**Response:**
```json
{
  "upload_id": "uuid",
  "status": "completed",
  "youtube_video_id": "dQw4w9WgXcQ",
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "processing_progress": 100,
  "views": 0,
  "uploaded_at": "2024-12-25T14:30:00Z"
}
```

---

## Frontend UI Components

### 1. Video Orientation Badge

```tsx
<Badge variant={orientation === 'horizontal' ? 'blue' : 'purple'}>
  {orientation === 'horizontal' ? '16:9 Horizontal' : '9:16 Vertical'}
</Badge>
```

### 2. Routing Decision Card

```tsx
<Card>
  <CardHeader>
    <CardTitle>Automatic Routing</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Video className="w-4 h-4" />
        <span>Horizontal • 2:15 duration</span>
      </div>
      <div className="flex items-center gap-2">
        <Youtube className="w-4 h-4 text-red-500" />
        <span className="font-medium">Recommended: YouTube</span>
      </div>
      <p className="text-sm text-muted-foreground">
        This video is optimal for YouTube main channel due to horizontal 
        orientation and 2+ minute duration.
      </p>
      <Button variant="outline" size="sm">
        Change Platform
      </Button>
    </div>
  </CardContent>
</Card>
```

### 3. YouTube Channel Selector

```tsx
<Select value={selectedChannel} onValueChange={setSelectedChannel}>
  <SelectTrigger>
    <SelectValue placeholder="Select YouTube channel" />
  </SelectTrigger>
  <SelectContent>
    {channels.map(channel => (
      <SelectItem key={channel.id} value={channel.id}>
        <div className="flex items-center gap-2">
          <Youtube className="w-4 h-4" />
          <span>{channel.name}</span>
          {channel.is_default && (
            <Badge variant="secondary">Default</Badge>
          )}
        </div>
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

### 4. Upload Progress

```tsx
<div className="space-y-2">
  <div className="flex justify-between text-sm">
    <span>Uploading to YouTube...</span>
    <span>{progress}%</span>
  </div>
  <Progress value={progress} />
  <p className="text-xs text-muted-foreground">
    Estimated time remaining: {estimatedTime}
  </p>
</div>
```

---

## Testing Strategy

### Unit Tests

**Video Analyzer Tests:**
```python
def test_detect_vertical_orientation():
    """Test vertical video detection (9:16)"""
    orientation = detect_orientation(1080, 1920)
    assert orientation == Orientation.VERTICAL

def test_detect_horizontal_orientation():
    """Test horizontal video detection (16:9)"""
    orientation = detect_orientation(1920, 1080)
    assert orientation == Orientation.HORIZONTAL

def test_detect_square_orientation():
    """Test square video detection (1:1)"""
    orientation = detect_orientation(1080, 1080)
    assert orientation == Orientation.SQUARE

def test_extract_duration():
    """Test video duration extraction"""
    duration = get_duration("test_video.mp4")
    assert 120.0 <= duration <= 121.0  # 2 minutes
```

**Routing Engine Tests:**
```python
def test_route_vertical_short_to_tiktok():
    """Vertical < 60s should route to TikTok/Reels"""
    platforms = determine_platforms(
        Orientation.VERTICAL,
        duration=45.0
    )
    assert "tiktok" in platforms
    assert "instagram_reels" in platforms

def test_route_horizontal_long_to_youtube():
    """Horizontal > 60s should route to YouTube"""
    platforms = determine_platforms(
        Orientation.HORIZONTAL,
        duration=125.0
    )
    assert "youtube" in platforms
    assert len(platforms) == 1  # Only YouTube

def test_manual_override():
    """Test manual platform override"""
    platforms = determine_platforms(
        Orientation.HORIZONTAL,
        duration=125.0,
        manual_override=["tiktok"]
    )
    assert "tiktok" in platforms
```

### Integration Tests

```python
def test_analyze_and_route_workflow():
    """Test complete analyze → route workflow"""
    # Analyze video
    metadata = video_analyzer.analyze("test_horizontal.mp4")
    assert metadata.orientation == "horizontal"
    
    # Route based on analysis
    routing = video_router.route(metadata)
    assert "youtube" in routing.platforms
    
    # Verify database update
    video = db.query(Video).filter_by(id=video_id).first()
    assert video.orientation == "horizontal"
    assert video.auto_routed == True

def test_youtube_upload_integration():
    """Test YouTube upload with real credentials"""
    upload_id = youtube_uploader.upload(
        file_path="test_video.mp4",
        title="Test Video",
        channel_id="test_channel"
    )
    
    # Wait for processing
    status = youtube_uploader.get_status(upload_id)
    assert status.youtube_video_id is not None
```

### E2E Tests

```typescript
test('should auto-route horizontal video to YouTube', async () => {
  // Upload horizontal video
  await uploadVideo('horizontal_2min.mp4');
  
  // Wait for analysis
  await waitForAnalysis();
  
  // Verify routing recommendation
  const routing = await getRoutingDecision();
  expect(routing.platforms).toContain('youtube');
  expect(routing.reasoning).toContain('horizontal');
  
  // Schedule to YouTube
  await scheduleToYouTube();
  
  // Verify scheduled
  const scheduled = await getScheduledPosts();
  expect(scheduled[0].platform).toBe('youtube');
});
```

---

## Success Metrics

### Phase 1-2 (Analysis & Routing)
- [ ] 100% accurate orientation detection
- [ ] Duration extraction within 0.1s accuracy
- [ ] Routing rules applied correctly 100% of time
- [ ] < 2 second analysis time per video

### Phase 3 (YouTube Integration)
- [ ] Successful OAuth authentication 100% of time
- [ ] Upload success rate > 99%
- [ ] Upload progress tracking accuracy > 95%
- [ ] Support for videos up to 12 hours long

### Phase 4 (Scheduler Integration)
- [ ] 90%+ of videos auto-routed correctly
- [ ] Manual override in < 3 clicks
- [ ] Batch routing processes 100+ videos in < 10s
- [ ] User satisfaction > 90%

---

## Risk Mitigation

### Technical Risks

**Risk 1: FFmpeg Dependency**
- **Mitigation:** Bundle FFmpeg with application or use system FFmpeg
- **Fallback:** Use Python libraries (moviepy, opencv) as backup

**Risk 2: YouTube API Rate Limits**
- **Mitigation:** Implement request queuing and retry logic
- **Monitoring:** Track API quota usage
- **Upgrade Path:** Request quota increase from Google

**Risk 3: Large File Uploads**
- **Mitigation:** Implement resumable uploads
- **Chunking:** Upload in 5MB chunks
- **Progress Tracking:** Real-time upload progress

**Risk 4: OAuth Token Expiration**
- **Mitigation:** Automatic token refresh
- **Monitoring:** Alert when refresh fails
- **Fallback:** Prompt user to re-authenticate

---

## Future Enhancements

**Post-MVP Features:**
- Multi-channel routing (upload to multiple YouTube channels)
- Automatic thumbnail generation for YouTube
- YouTube playlist management
- YouTube Shorts optimization
- Cross-platform analytics comparison
- A/B testing for video formats
- Automatic video transcoding for optimal formats
- AI-powered title and description generation for YouTube

---

## Technical Stack

**Backend:**
- FFmpeg - Video analysis
- google-api-python-client - YouTube API
- google-auth - OAuth 2.0
- FastAPI - API endpoints
- PostgreSQL - Data storage

**Frontend:**
- React - UI components
- shadcn/ui - Component library
- Lucide React - Icons
- React Query - Data fetching

**Infrastructure:**
- YouTube Data API v3
- OAuth 2.0 for authentication
- Resumable uploads for large files

---

## Appendix: FFmpeg Commands

### Extract Video Metadata
```bash
ffprobe -v quiet -print_format json -show_format -show_streams video.mp4
```

### Get Video Duration
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 video.mp4
```

### Get Video Dimensions
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 video.mp4
```

### Get Aspect Ratio
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=display_aspect_ratio -of default=noprint_wrappers=1:nokey=1 video.mp4
```

---

**End of PRD**

**Next Steps:**
1. Review and approve PRD
2. Set up YouTube API credentials
3. Begin Phase 1 implementation
4. Weekly progress reviews
5. Beta testing with real videos

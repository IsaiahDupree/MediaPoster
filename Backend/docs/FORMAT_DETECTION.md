# Content Format Detection System

Comprehensive content format classification for videos in MediaPoster.

## Overview

The Format Detection System automatically classifies videos into content formats based on:
- **Transcript analysis** - Speech content, word count, pace
- **Visual analysis** - Scene descriptions, people, actions
- **Audio characteristics** - Speech, music, silence ratios
- **Existing B-roll analysis** - Leverages prior B-roll detection

## Content Formats

### Primary Formats

| Format | Description | Suggested Use |
|--------|-------------|---------------|
| `talking_head` | Person speaking directly to camera (vlog, tutorial, commentary) | Primary content |
| `interview` | Two or more people in conversation | Primary content |
| `broll_scenic` | Environmental/landscape footage, no people | Overlay B-roll |
| `broll_action` | Movement/action footage, may have people | Cutaway B-roll |
| `broll_people` | People visible but not speaking to camera | Cutaway B-roll |
| `animated` | Animation, motion graphics, illustrated content | Standalone |
| `screen_recording` | Software demo, gameplay, screen capture | Primary content |
| `slideshow` | Static images with transitions | Standalone |
| `music_video` | Music-focused content with visuals | Standalone |
| `montage` | Quick cuts of multiple clips, often with music | Standalone |
| `documentary` | Narrated footage, voiceover style | Primary content |
| `reaction` | Person reacting to other content | Primary content |
| `tutorial_hands` | Hands-on tutorial (cooking, crafts, unboxing) | Primary content |
| `live_event` | Concert, sports, live performance | Standalone |
| `meme_content` | Meme-style edits, text overlays, viral format | Standalone |

### Suggested Use Categories

| Use | Description | Formats |
|-----|-------------|---------|
| `primary` | Main content for posts | talking_head, interview, screen_recording, documentary, tutorial_hands |
| `overlay` | B-roll for video overlays | broll_scenic |
| `cutaway` | Transition footage | broll_action, broll_people |
| `standalone` | Self-contained clips | animated, music_video, montage, live_event, meme_content |

## API Endpoints

### GET `/api/content-format/stats`

Returns format detection statistics.

**Response:**
```json
{
  "total_videos": 739,
  "processed": 739,
  "unprocessed": 0,
  "by_format": {
    "talking_head": {"count": 214, "avg_confidence": 0.66},
    "broll_scenic": {"count": 235, "avg_confidence": 0.63},
    "screen_recording": {"count": 138, "avg_confidence": 0.50}
  },
  "by_suggested_use": {
    "primary": 412,
    "overlay": 235,
    "cutaway": 42,
    "standalone": 50
  }
}
```

### GET `/api/content-format/formats`

Lists all available format types with descriptions.

**Response:**
```json
{
  "formats": [
    {"value": "talking_head", "label": "Talking Head", "description": "Person speaking directly to camera"},
    {"value": "broll_scenic", "label": "B-Roll (Scenic)", "description": "Environmental/landscape footage"}
  ]
}
```

### GET `/api/content-format/list`

List videos filtered by format.

**Parameters:**
- `format_type` (optional): Filter by specific format
- `limit` (default: 50, max: 200): Number of results

**Response:**
```json
{
  "total": 50,
  "format_type": "talking_head",
  "videos": [
    {
      "id": "uuid",
      "file_name": "video.mp4",
      "format": "talking_head",
      "confidence": 0.75,
      "has_speech": true,
      "has_people": true,
      "best_platforms": ["youtube", "tiktok"],
      "suggested_use": "primary"
    }
  ]
}
```

### GET `/api/content-format/detect/{video_id}`

Detect and return format for a single video.

**Response:**
```json
{
  "video_id": "uuid",
  "file_name": "video.mp4",
  "primary_format": "talking_head",
  "confidence": 0.75,
  "secondary_formats": ["documentary"],
  "attributes": {
    "has_speech": true,
    "has_music": false,
    "has_voiceover": false,
    "has_captions": false,
    "has_text_overlay": false,
    "has_people": true,
    "people_speaking": true,
    "people_count": 1
  },
  "duration_category": "medium",
  "production_quality": "medium",
  "best_platforms": ["youtube", "tiktok", "instagram"],
  "suggested_use": "primary",
  "reasons": [
    "Significant speech detected (85 words)",
    "Visual shows person speaking to camera"
  ]
}
```

### POST `/api/content-format/detect-all`

Batch detect formats for all videos.

**Parameters:**
- `limit` (default: 200, max: 1000): Max videos to process
- `only_unprocessed` (default: true): Only process videos without format

**Response:**
```json
{
  "processed": 200,
  "format_distribution": {
    "talking_head": 65,
    "broll_scenic": 80,
    "screen_recording": 30,
    "interview": 15,
    "animated": 10
  }
}
```

## Detection Logic

### Transcript Analysis

| Condition | Effect |
|-----------|--------|
| Word count >= 30 | +0.3 talking_head, +0.2 documentary |
| Word count 10-30 | +0.1 talking_head, +0.1 montage |
| Word count < 10 | +0.2 broll_scenic, +0.2 broll_action, +0.2 music_video |
| WPM > 120 | +0.2 talking_head (energetic content) |
| WPM < 60 | +0.1 documentary, +0.1 tutorial_hands |
| Silence ratio > 0.5 | +0.2 broll_scenic, +0.1 music_video |

### Visual Keyword Matching

The system searches for keywords in `visual_analysis.visual_summary`:

**Talking Head Keywords:**
- "person speaking", "talking", "face", "presenter", "looking at camera"

**Scenic Keywords:**
- "landscape", "nature", "sky", "ocean", "mountain", "aerial", "drone"

**Action Keywords:**
- "movement", "action", "running", "driving", "sports", "dancing"

**Animated Keywords:**
- "animation", "animated", "cartoon", "motion graphics", "3d", "cgi"

**Screen Recording Keywords:**
- "screen", "computer", "software", "cursor", "desktop", "code", "terminal"

### Confidence Calculation

1. Positive factors are averaged: `avg(positive_scores)`
2. Negative factors subtract from score
3. Final score clamped to 0.0 - 1.0

**Confidence Levels:**
- `>= 0.7`: High confidence
- `0.5 - 0.7`: Medium confidence  
- `0.3 - 0.5`: Low confidence
- `< 0.3`: Very low / Unknown

## Service Architecture

### FormatDetector Class

```python
from services.format_detector import FormatDetector, ContentFormat

detector = FormatDetector()

# Detect format from raw data
result = detector.detect_format(
    transcript="Hello everyone, welcome to my channel...",
    visual_analysis={"visual_summary": "Person speaking to camera"},
    duration_sec=120
)

print(result.primary_format)  # ContentFormat.TALKING_HEAD
print(result.confidence)      # 0.75
print(result.suggested_use)   # "primary"

# Detect from database record
result = detector.detect_from_db_record(video_analysis_dict)
```

### FormatAnalysis Dataclass

```python
@dataclass
class FormatAnalysis:
    primary_format: ContentFormat    # Main format classification
    confidence: float                # 0.0 to 1.0
    secondary_formats: List[ContentFormat]  # Other possible formats
    
    # Attributes
    has_speech: bool
    has_music: bool
    has_voiceover: bool
    has_captions: bool
    has_text_overlay: bool
    has_people: bool
    people_speaking: bool
    people_count_estimate: int
    
    # Technical
    is_vertical: bool
    duration_category: str  # "short", "medium", "long"
    production_quality: ProductionQuality
    
    # Output
    reasons: List[str]          # Why this format was detected
    best_platforms: List[str]   # Recommended platforms
    suggested_use: str          # "primary", "overlay", "cutaway", "standalone"
```

## Database Schema

Format detection adds these columns to `video_analysis`:

```sql
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS
    content_format TEXT,           -- Primary format (e.g., "talking_head")
    format_confidence FLOAT,       -- Confidence score 0.0-1.0
    format_secondary JSONB,        -- Secondary formats array
    format_attributes JSONB,       -- Attributes (has_speech, etc.)
    format_best_platforms JSONB,   -- Platform recommendations
    format_suggested_use TEXT;     -- Usage suggestion
```

## Platform Recommendations

Each format maps to recommended platforms:

| Format | Best Platforms |
|--------|----------------|
| talking_head | YouTube, TikTok, Instagram |
| interview | YouTube, Spotify |
| broll_scenic | Instagram, TikTok |
| broll_action | TikTok, Instagram, YouTube |
| animated | YouTube, TikTok, Instagram |
| screen_recording | YouTube, TikTok |
| music_video | TikTok, Instagram, YouTube |
| documentary | YouTube |
| meme_content | TikTok, Twitter, Instagram |
| live_event | Instagram, TikTok, YouTube |

Duration adjustments:
- **Short (<60s)**: Prioritize TikTok
- **Long (>180s)**: Prioritize YouTube

## Integration with Other Systems

### B-Roll Detection

Format detection leverages existing B-roll analysis:

```python
if existing_broll_analysis.get("is_broll"):
    visual_type = existing_broll_analysis.get("broll_visual_type")
    if visual_type == "scenic":
        format_scores[ContentFormat.BROLL_SCENIC] += 0.3
```

### Narrative Builder

Format detection informs content scheduling:
- Primary content for main posts
- B-roll for supplemental content
- Platform recommendations for cross-posting

### Content Library

Filter and organize content by format:
- Find all talking head videos for vlogs
- Find B-roll for video editing
- Find animated content for specific campaigns

## Testing

### Unit Tests

```bash
pytest tests/unit/test_format_detector.py -v
```

Tests cover:
- All format detection scenarios
- Edge cases (empty inputs, minimal data)
- Attribute extraction
- Platform recommendations
- Confidence calculation

### Integration Tests

```bash
pytest tests/integration/test_content_format_api.py -v
```

Tests cover:
- All API endpoints
- Response structure validation
- Format value validation
- Suggested use validation
- Confidence range validation

## Usage Examples

### Find B-Roll for Video Editing

```bash
# Get all scenic B-roll
curl "http://localhost:5555/api/content-format/list?format_type=broll_scenic&limit=20"
```

### Get Content Statistics

```bash
curl "http://localhost:5555/api/content-format/stats"
```

### Process New Videos

```bash
# Process only unprocessed videos
curl -X POST "http://localhost:5555/api/content-format/detect-all?only_unprocessed=true"
```

### Classify Single Video

```bash
curl "http://localhost:5555/api/content-format/detect/{video_id}"
```

## Performance

- Processing speed: ~50-100 videos/second
- Memory efficient: Processes in batches
- Database: Uses connection pooling
- Caching: Results stored in video_analysis table

## Future Enhancements

1. **AI-Enhanced Detection**: Use GPT-4o for more accurate visual analysis
2. **Audio Analysis**: Detect music vs speech audio tracks
3. **Aspect Ratio Detection**: Determine vertical vs horizontal
4. **Quality Scoring**: Auto-detect production quality level
5. **Scene Segmentation**: Detect format changes within videos

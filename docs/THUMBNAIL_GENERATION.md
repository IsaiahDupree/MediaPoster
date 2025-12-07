# AI Thumbnail Generation System

## Overview
Intelligent thumbnail generation system that automatically selects the best frame from videos and generates platform-specific thumbnails with AI-powered enhancements.

## Features

###1. **Best Frame Selection**
Analyzes video frames based on:
- **Sharpness**: Laplacian variance for clarity
- **Brightness**: Optimal midrange lighting
- **Contrast**: Dynamic range analysis
- **Face Detection**: Bonus for human presence
- **Color Vibrancy**: Saturation analysis
- **Overall Composition**: Weighted scoring

### 2. **Multi-Platform Support**

#### Landscape (Horizontal)
- **YouTube**: 1280×720 (16:9)
- **Facebook**: 1200×630 (1.91:1)
- **Twitter/X**: 1200×675 (16:9)
- **LinkedIn**: 1200×627 (1.91:1)

#### Portrait (Vertical)
- **YouTube Shorts**: 1080×1920 (9:16)
- **TikTok**: 1080×1920 (9:16)
- **Instagram Story/Reel**: 1080×1920 (9:16)
- **Pinterest**: 1000×1500 (2:3)
- **Snapchat**: 1080×1920 (9:16)
- **Threads**: 1080×1350 (4:5)

#### Square
- **Instagram Feed**: 1080×1080 (1:1)

### 3. **AI Text Enhancement**
- GPT-4 generates catchy, short text overlays
- Professional text positioning
- Outline for visibility
- Optimized for clickability

### 4. **Smart Cropping**
- Maintains focal points
- Intelligent composition
- Platform-optimized aspect ratios

## API Endpoints

### Get Platform Dimensions
```bash
GET /api/thumbnails/dimensions
```
Returns specifications for all supported platforms.

### Select Best Frame
```bash
POST /api/thumbnails/select-best-frame
{
  "video_path": "/path/to/video.mp4",
  "num_candidates": 10
}
```
Analyzes video and returns the optimal frame for thumbnails.

### Generate Thumbnails
```bash
POST /api/thumbnails/generate
{
  "source_image": "/path/to/frame.jpg",
  "platforms": "youtube,tiktok,instagram_feed",
  "output_dir": "/path/to/output"
}
```
Generates platform-specific thumbnails from source image.

### Generate from Video (Complete)
```bash
POST /api/thumbnails/generate-from-video
{
  "video_path": "/path/to/video.mp4",
  "platforms": "all",
  "output_dir": "/path/to/output"
}
```
Selects best frame and generates all thumbnails in one step.

### AI Enhancement
```bash
POST /api/thumbnails/enhance-with-ai
{
  "image_path": "/path/to/thumbnail.jpg",
  "title": "10 Amazing Life Hacks",
  "output_path": "/path/to/enhanced.jpg"
}
```
Adds AI-generated catchy text overlay to thumbnail.

### Complete Workflow (Recommended)
```bash
POST /api/thumbnails/complete-workflow
{
  "video_path": "/path/to/video.mp4",
  "title": "How I Made $10,000 in 30 Days",
  "platforms": "all",
  "add_text_overlay": true
}
```
End-to-end: selects frame, generates thumbnails, adds AI text.

## Usage Examples

### Example 1: Quick Thumbnail Generation
```python
import requests

response = requests.post("http://localhost:5555/api/thumbnails/complete-workflow", data={
    "video_path": "/videos/my_video.mp4",
    "title": "Amazing Tutorial",
    "platforms": "youtube,tiktok",
    "add_text_overlay": True
})

thumbnails = response.json()["thumbnails"]
for thumb in thumbnails:
    print(f"{thumb['platform']}: {thumb['enhanced_thumbnail']}")
```

### Example 2: Custom Frame Selection
```python
# Step 1: Select best frame
frame_response = requests.post("http://localhost:5555/api/thumbnails/select-best-frame", data={
    "video_path": "/videos/my_video.mp4",
    "num_candidates": 15
})

best_frame = frame_response.json()["frame_path"]
print(f"Best frame score: {frame_response.json()['overall_score']}")

# Step 2: Generate specific platforms
thumb_response = requests.post("http://localhost:5555/api/thumbnails/generate", data={
    "source_image": best_frame,
    "platforms": "youtube,instagram_feed,tiktok",
    "output_dir": "/output/thumbnails"
})
```

### Example 3: AI Text Overlay Only
```python
response = requests.post("http://localhost:5555/api/thumbnails/enhance-with-ai", data={
    "image_path": "/images/my_thumbnail.jpg",
    "title": "The Ultimate Guide to Success",
    "output_path": "/output/enhanced.jpg",
    "style": "bold"
})
```

## Configuration

### Environment Variables
```bash
# Required for AI text enhancement
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Already configured
RAPIDAPI_KEY=a87cab3052mshf494034b314ie1ep1aacb0jen580589e4be0b
```

### Dependencies
```bash
pip install opencv-python-headless pillow openai
```

## Quality Scoring

Each frame is scored from 0.0 to 1.0 based on:
- **Sharpness** (30%): Clear, not blurry
- **Brightness** (20%): Well-lit, not too dark/bright
- **Contrast** (20%): Good dynamic range
- **Faces** (20%): Human presence bonus
- **Vibrancy** (10%): Colorful content

## Smart Cropping

The system uses intelligent cropping:
- **Wider sources**: Crops sides, keeps center
- **Taller sources**: Crops more from bottom (keeps faces)
- **Focal point detection**: Maintains important visual elements

## Image Enhancements

All thumbnails receive automatic enhancements:
- **+20% Sharpness**: Crisper details
- **+10% Saturation**: More vibrant colors
- **+10% Contrast**: Better visual pop

## AI Text Overlay

When enabled, the system:
1. Uses GPT-4 to generate 1-5 word catchy text
2. Positions text in bottom third (most visible)
3. Adds black outline for readability
4. Uses large, bold font
5. Centers text horizontally

## Best Practices

### For YouTube
- Use landscape (16:9) format
- Enable AI text overlay
- Select high-action frames
- Ensure faces are visible

### For Short-Form (TikTok, Reels, Shorts)
- Use portrait (9:16) format
- Keep text minimal
- High-energy frames work best
- Close-up shots perform well

### For Instagram Feed
- Use square (1:1) format
- Aesthetic over action
- Clean, simple compositions
- Good lighting crucial

## Integration with Video Analysis

The thumbnail generator integrates with existing video analysis:
- Uses frame data from `VideoFrame` table
- Can leverage pattern interrupt detection
- Syncs with best moments in content
- Considers existing metadata

## Output Organization

Thumbnails are organized:
```
/output/thumbnails/
├── thumbnail_youtube.jpg
├── thumbnail_youtube_enhanced.jpg
├── thumbnail_tiktok.jpg
├── thumbnail_tiktok_enhanced.jpg
├── thumbnail_instagram_feed.jpg
├── thumbnail_instagram_feed_enhanced.jpg
└── ...
```

Base thumbnails: Clean, platform-sized  
Enhanced thumbnails: With AI text overlay

## Future Enhancements

- [ ] A/B testing suggestions
- [ ] Emotion detection for frame selection
- [ ] Custom branding overlay
- [ ] Batch processing
- [ ] Template system
- [ ] Color palette extraction
- [ ] Click-through rate prediction

## Troubleshooting

### No OpenCV/Pillow
```bash
pip install opencv-python-headless pillow
```

### FFmpeg not found
```bash
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Linux
```

### No faces detected
- Face detection uses Haar cascades
- Works best with frontal faces
- Score still considers other factors

### Text not visible
- System adds automatic outline
- Positioned in bottom third
- Black outline + white text = maximum contrast

## Performance

- Frame extraction: ~1-2s for 10 frames
- Quality analysis: ~0.5s per frame
- Thumbnail generation: ~0.2s per platform
- AI text overlay: ~2-3s (GPT-4 API call)

**Total workflow**: ~10-15 seconds for complete multi-platform thumbnail suite

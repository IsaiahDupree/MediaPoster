# Phase 3 Testing Guide - Clip Generation

## Quick Start (2 minutes)

```bash
cd backend
python3 test_phase3.py
# Choose option 4 (Complete Clip Generation)
```

You'll be prompted for:
1. Video file path
2. Highlights JSON (from Phase 2) OR manual start/duration
3. Transcript JSON (optional, for captions)

**Result**: A finished, viral-ready clip!

## What Gets Generated

Your clip will have:
- ✅ 9:16 vertical format (TikTok/Instagram ready)
- ✅ Styled captions (if transcript provided)
- ✅ Viral hook overlay (first 3 seconds)
- ✅ Progress bar (top)
- ✅ Color enhancement (vibrant filter)
- ✅ Platform optimization

## Testing Scenarios

### Scenario 1: Complete Pipeline (Best Results)

**Prerequisites**: All phases complete
```bash
# You have:
# - Video file
# - Highlights from Phase 2
# - Transcript from Phase 1

python3 test_phase3.py
# Option 4
# Provide all files
```

**Expected Output**:
```
✓ Clip generated: clip_10s_20s_0.87_tiktok.mp4
✓ Size: 15.2 MB
✓ Duration: 20.0s
✓ Hook: "Watch what happens next 🔥"
✓ Hashtags: #fyp #viral #trending #amazing #wow
```

### Scenario 2: Manual Timing (No Phase 2)

**Prerequisites**: Video file only
```bash
python3 test_phase3.py
# Option 4
# Skip highlights JSON
# Enter: Start time: 10
# Enter: Duration: 20
```

**Result**: Clip generated at your specified time

### Scenario 3: No Captions (Fast)

**Prerequisites**: Video file
```bash
python3 test_phase3.py
# Option 4
# Skip transcript
```

**Result**: Clip without captions (faster, simpler)

### Scenario 4: Individual Components

Test each module separately:

```bash
# Video editing only
python3 test_phase3.py
# Option 1

# Caption generation
python3 test_phase3.py
# Option 2

# Hook generation (requires OpenAI API key)
python3 test_phase3.py
# Option 3
```

## API Testing

### Prerequisites
- Server running: `uvicorn main:app --reload`
- Video uploaded and analyzed (Phases 1 & 2)

### Generate Clips

```bash
# Single platform
curl -X POST http://localhost:8000/api/clips/generate/{VIDEO_ID} \
  -H "Content-Type: application/json" \
  -d '{
    "template": "viral_basic",
    "platforms": ["tiktok"],
    "use_highlights": true
  }'

# Multiple platforms
curl -X POST http://localhost:8000/api/clips/generate/{VIDEO_ID} \
  -H "Content-Type: application/json" \
  -d '{
    "template": "viral_basic",
    "platforms": ["tiktok", "instagram", "youtube_shorts"],
    "use_highlights": true
  }'
```

### Check Job Status

```bash
curl http://localhost:8000/api/jobs/{JOB_ID}
```

### List Generated Clips

```bash
curl http://localhost:8000/api/clips/list/{VIDEO_ID}
```

## Templates

Test different templates:

**Viral Basic** (Recommended):
```json
{"template": "viral_basic"}
```
- Captions + Hook + Progress Bar + Effects

**Clean**:
```json
{"template": "clean"}
```
- Captions only, no effects

**Maximum**:
```json
{"template": "maximum"}
```
- Everything + Zoom + Vignette

**Minimal**:
```json
{"template": "minimal"}
```
- Just vertical conversion

## Expected Processing Times

| Clip Length | Template | Processing Time |
|-------------|----------|-----------------|
| 15s | minimal | ~20s |
| 15s | clean | ~30s |
| 15s | viral_basic | ~45s |
| 15s | maximum | ~60s |
| 30s | viral_basic | ~75s |
| 60s | viral_basic | ~120s |

Times include all steps: extract + vertical + captions + hook + effects + optimize

## Output Files

Generated clips are saved to:
```
backend/generated_clips/
├── clip_10s_20s_0.87_tiktok.mp4
├── clip_10s_20s_0.87_instagram.mp4
├── clip_45s_25s_0.82_tiktok.mp4
└── batch_metadata.json
```

**Metadata file** contains:
```json
[
  {
    "clip_path": "...",
    "duration": 20.0,
    "platform": "tiktok",
    "has_captions": true,
    "hook_text": "...",
    "hashtags": [...],
    "cta": "...",
    "file_size_mb": 15.2
  }
]
```

## Troubleshooting

### Issue: FFmpeg not found

```bash
# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg

# Test
ffmpeg -version
```

### Issue: Captions fail

**Cause**: No transcript provided or invalid format

**Solution**:
- Provide transcript JSON from Phase 1
- Or skip captions (still generates clip)

### Issue: Hooks fail

**Cause**: No OpenAI API key or rate limit

**Solution**:
```bash
# Check .env
cat .env | grep OPENAI_API_KEY

# Or disable hooks
# Use template: "clean" or "minimal"
```

### Issue: File size too large

**Cause**: Platform limits exceeded

**Solutions**:
- Shorter duration
- Lower bitrate
- Different platform (YouTube Shorts has highest limit)

Platform limits:
- TikTok: 287 MB max
- Instagram: 100 MB max
- YouTube Shorts: 256 MB max

### Issue: Poor vertical crop

**Cause**: Source video aspect ratio

**Solution**: Try different crop modes
```python
# In video_editor.py or custom API call
crop_mode = "center"  # or "smart" or "blur"
```

### Issue: Captions off-sync

**Cause**: Transcript timing inaccurate

**Solution**:
- Re-run Phase 1 transcription
- Check source video framerate
- Verify transcript JSON format

## Performance Optimization

### Speed Up Processing

1. **Use `minimal` template** - Just vertical conversion
2. **Skip captions** - Don't provide transcript
3. **Disable hooks** - No GPT API calls
4. **Fast extraction** - Uses copy codec (but less precise)

### Improve Quality

1. **Use `maximum` template** - All effects
2. **Provide transcript** - For accurate captions
3. **Enable GPT hooks** - Better engagement
4. **Use exact cutting** - More precise (but slower)

### Batch Processing

Generate multiple clips efficiently:
```python
# In test script or custom code
assembler.create_clips_batch(
    video_path,
    highlights,  # List of highlights
    transcript,
    video_context,
    template='viral_basic',
    platforms=['tiktok', 'instagram']
)
```

This is faster than individual calls!

## Success Criteria ✅

A successful Phase 3 test should:

- [x] Extract clip at correct timestamp
- [x] Convert to 9:16 vertical
- [x] Burn captions (if transcript provided)
- [x] Add hook overlay (if GPT enabled)
- [x] Apply visual effects
- [x] Optimize for platform
- [x] Output valid video file
- [x] Meet platform size limits
- [x] Complete in reasonable time

## Quality Checklist

Before considering a clip "production-ready":

- [ ] Video plays smoothly
- [ ] Captions are readable and synced
- [ ] Hook text doesn't overlap important content
- [ ] Progress bar is visible
- [ ] Colors look good (not over-saturated)
- [ ] File size under platform limit
- [ ] Audio quality preserved
- [ ] Aspect ratio correct (9:16)
- [ ] No black bars or cropping issues

## Next Steps

### After Testing

1. **Review clips** - Are they viral-worthy?
2. **Tune templates** - Adjust effects, styles
3. **Test platforms** - Upload to TikTok/Instagram (manually for now)
4. **Measure performance** - Which clips perform best?

### Move to Phase 4

Once satisfied with clip quality:
```bash
# Phase 4 will automate:
# - Google Drive upload
# - Multi-platform posting via Blotato
# - Scheduling and optimization
```

## Tips for Best Results

1. **Start with Phase 1 & 2** - Better highlights = better clips
2. **Use GPT hooks** - Significantly boosts engagement
3. **Test different templates** - Find what works for your content
4. **Batch process** - More efficient for multiple clips
5. **Check platform specs** - Each has different requirements
6. **Iterate quickly** - Generate, test, adjust, repeat

---

## Quick Command Reference

```bash
# Complete test
python3 test_phase3.py

# Individual modules
python3 -m modules.clip_generation.video_editor video.mp4

# API
uvicorn main:app --reload
# Then use curl commands above

# Check output
ls -lh generated_clips/
```

---

**Phase 3 is ready to test!** 🚀

Try it now:
```bash
cd backend
python3 test_phase3.py
```

Generate your first viral clip in under 2 minutes!

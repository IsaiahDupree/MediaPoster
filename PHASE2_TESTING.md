# Phase 2 Testing Guide - Highlight Detection

## Quick Start (Recommended)

### Prerequisites
- Python 3.8+
- FFmpeg installed
- Backend dependencies installed
- Phase 1 analysis complete for test video (optional but recommended)

### Run Complete Test

```bash
cd backend
python3 test_phase2.py
```

Choose option **4** (Complete Highlight Detection)

This will:
1. Detect scenes in your video
2. Analyze audio signals
3. Scan transcript (if available)
4. Analyze visuals (if available)
5. Rank and select top highlights
6. Optionally get GPT-4 recommendations

## Individual Component Tests

### 1. Scene Detection Only

```bash
python3 test_phase2.py
# Choose option 1
```

**What it tests**:
- FFmpeg scene change detection
- Scene duration scoring
- Basic highlight potential

**Expected output**:
```
✓ Detected 12 scenes
📊 Top scored scenes:
  #1 - Score: 0.82
    Time: 45.2s - 65.8s
    Factors: duration:0.95, change:0.85, ...
```

### 2. Audio Signal Processing

```bash
python3 test_phase2.py
# Choose option 2
```

**What it tests**:
- Volume spike detection
- Energy curve calculation
- Peak identification

**Expected output**:
```
✓ Found 18 volume spikes
✓ Generated 300 energy points
✓ Found 12 energy peaks
```

### 3. Transcript Scanning

```bash
python3 test_phase2.py
# Choose option 3
```

**Prerequisites**: Transcript JSON from Phase 1

**What it tests**:
- Hook phrase detection
- Question identification
- Punchline detection
- Emphasis word scanning

**Expected output**:
```
HOOKS: 5 found
  1. [12.3s] watch this amazing trick...
QUESTIONS: 7 found
  1. [45.6s] what do you think happens next?
```

### 4. Complete Pipeline (Recommended)

```bash
python3 test_phase2.py
# Choose option 4
```

**What it tests**:
- Full multi-signal analysis
- Composite scoring
- Top highlight selection
- Optional GPT recommendations

## Testing with Real Videos

### Scenario 1: Without Phase 1 Analysis

```bash
python3 test_phase2.py
# Option 4
# Enter video path: ~/Videos/test.mp4
# Skip analysis JSON (press Enter)
```

**Result**: Still works! Uses scene + audio signals only  
**Quality**: Good, but not optimal

### Scenario 2: With Phase 1 Analysis (Recommended)

```bash
# First, run Phase 1
python3 test_phase1.py
# Option 6 (Complete workflow)
# This generates analysis JSON

# Then run Phase 2
python3 test_phase2.py
# Option 4
# Enter video path: ~/Videos/test.mp4
# Enter analysis JSON path: ~/Videos/test_analysis.json
```

**Result**: Full multi-signal analysis  
**Quality**: Excellent

### Scenario 3: API Testing

```bash
# Start server
uvicorn main:app --reload

# In another terminal:
# Upload video
VIDEO_ID=$(curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@test.mp4" | jq -r '.video_id')

# Run Phase 1
curl -X POST http://localhost:8000/api/analysis/full-analysis/$VIDEO_ID \
  -H "Content-Type: application/json" \
  -d '{"transcribe": true, "analyze_vision": true}'

# Wait for completion...

# Run Phase 2
JOB_ID=$(curl -X POST http://localhost:8000/api/highlights/detect/$VIDEO_ID \
  -H "Content-Type: application/json" \
  -d '{"max_highlights": 5, "use_gpt": true}' | jq -r '.job_id')

# Check status
curl http://localhost:8000/api/jobs/$JOB_ID

# Get results
curl http://localhost:8000/api/highlights/results/$VIDEO_ID
```

## Expected Results

### Good Video (Podcast, Vlog, Talk)

**Input**: 10-minute conversation video

**Expected Output**:
- 3-5 highlights detected
- Average score: 0.7-0.85
- Duration: 15-45 seconds each
- Strong signals: transcript, audio

**Example**:
```
🎬 HIGHLIGHT #1 (Score: 0.87)
   Time: 2:15 - 2:42 (27s)
   Strengths: Strong hook, High energy
```

### Action Video (Sports, Gaming)

**Expected Output**:
- 5-7 highlights detected
- Average score: 0.6-0.8
- Duration: 10-30 seconds each
- Strong signals: visual, audio

### Music Video / Montage

**Expected Output**:
- 3-5 highlights detected
- Average score: 0.5-0.7
- Duration: 15-45 seconds each
- Strong signals: visual, audio energy

## Troubleshooting

### Issue: No highlights detected

**Causes**:
- Video too short (< 30s)
- Min score threshold too high
- Low variance (static camera/audio)

**Solutions**:
```python
# Lower min_score
curl ... -d '{"min_score": 0.3, ...}'

# Lower min_duration
curl ... -d '{"min_duration": 5.0, ...}'
```

### Issue: All highlights overlap

**Solution**: Increase min_gap
```python
# In test script or API
min_gap = 15.0  # seconds between highlights
```

### Issue: GPT recommendations fail

**Causes**:
- Missing OPENAI_API_KEY
- API rate limit
- No credits

**Solution**:
```bash
# Check .env
cat .env | grep OPENAI_API_KEY

# Test without GPT
curl ... -d '{"use_gpt": false, ...}'
```

### Issue: FFmpeg errors

**Causes**:
- FFmpeg not installed
- Corrupted video file
- Unsupported codec

**Solutions**:
```bash
# Install FFmpeg
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Linux

# Test video
ffprobe video.mp4

# Re-encode if needed
ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4
```

## Performance Expectations

| Video Length | Processing Time | Memory Usage | Highlights |
|--------------|-----------------|--------------|------------|
| 2 minutes    | ~25-30s        | ~200MB       | 2-3        |
| 5 minutes    | ~50-60s        | ~400MB       | 3-5        |
| 10 minutes   | ~90-120s       | ~600MB       | 4-7        |
| 30 minutes   | ~5-7min        | ~1.5GB       | 5-10       |

**With GPT**: Add ~5-10 seconds

## Success Criteria ✅

A successful Phase 2 test should:

- [x] Detect scenes (at least 1 per minute)
- [x] Find audio peaks (at least 5 for 5-min video)
- [x] Score all scenes (0.0-1.0 range)
- [x] Select top highlights (3-5 for most videos)
- [x] Non-overlapping (10s+ gap)
- [x] Reasonable scores (0.4-0.9 range)
- [x] Output valid JSON
- [x] Complete in reasonable time

## Next Steps

### After Testing

1. **Review highlights** - Are they actually good moments?
2. **Adjust parameters** - Tune weights, thresholds, durations
3. **Try different videos** - Test various content types
4. **Measure accuracy** - Track how many highlights are "viral-worthy"

### Move to Phase 3

Once satisfied with highlight quality:

```bash
# Phase 3 will generate actual clips from these highlights!
# Coming next...
```

## Debug Mode

Enable verbose logging:

```python
# In test script
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment
export LOG_LEVEL=DEBUG
python3 test_phase2.py
```

## Tips for Best Results

1. **Use Phase 1 first** - Transcript + visuals = better highlights
2. **Test different content** - Podcasts, vlogs, gaming, sports
3. **Adjust parameters** - Tune for your specific content type
4. **Enable GPT** - Get intelligent recommendations (requires API key)
5. **Save output** - Review JSON to understand scoring

---

## Quick Command Reference

```bash
# Complete test (recommended)
python3 test_phase2.py

# Individual modules
python3 -m modules.highlight_detection.scene_detector video.mp4
python3 -m modules.highlight_detection.audio_signals video.mp4
python3 -m modules.highlight_detection.transcript_scanner transcript.json

# API test
uvicorn main:app --reload
# Then use curl commands above

# Check results
cat video_highlights.json | jq '.highlights[] | {time: .start, score: .composite_score}'
```

---

**Phase 2 is ready to test!** 🚀

Try it now:
```bash
cd backend
python3 test_phase2.py
```

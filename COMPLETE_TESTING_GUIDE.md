# 🧪 Complete Testing Guide

## Everything is Ready! Here's how to test and use it all.

---

## ✅ What We Built

1. ✅ **Video Analysis Pipeline** - `Backend/services/video_pipeline.py`
2. ✅ **Batch Analyzer** - `Backend/services/batch_analyzer.py`  
3. ✅ **API Endpoints** - `Backend/api/endpoints/viral_analysis.py`
4. ✅ **API Integration** - Added to `Backend/main.py`

---

## 🚀 Quick Start: Test on 1 Video

### Method 1: Using the Pipeline Service Directly

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

# Run the standalone test
python3 -m services.video_pipeline
```

**What it does:**
- Gets first video from database
- Runs complete analysis (transcribe → word analysis → frame analysis)
- Shows results with metrics

**Expected output:**
```
Analyzing: video_filename.mp4
============================================================
✅ Analysis Complete!
  Duration: 45.3s
  Words: 156
  Frames: 120
  WPM: 234.5
  Face presence: 78.3%
  Emphasis segments: 3
  CTA segments: 2
```

---

### Method 2: Using the API

**Start your backend server:**
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Test the API (in another terminal):**

```bash
# Get a video ID from database
VIDEO_ID=$(docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -t -c \
  "SELECT id FROM videos LIMIT 1" | tr -d ' ')

# Run sync analysis (waits for completion)
curl -X POST "http://localhost:8000/api/viral-analysis/videos/$VIDEO_ID/analyze-sync?skip_existing=false" \
  -H "Content-Type: application/json"
```

**Or use async (returns immediately, runs in background):**
```bash
curl -X POST "http://localhost:8000/api/viral-analysis/videos/$VIDEO_ID/analyze?skip_existing=false"
```

---

## 📊 Test the Query Endpoints

### Get Word Timeline
```bash
curl "http://localhost:8000/api/viral-analysis/videos/$VIDEO_ID/words"
```

**Returns:**
```json
{
  "video_id": "...",
  "word_count": 156,
  "words": [
    {
      "word": "Hey",
      "start_s": 0.0,
      "end_s": 0.3,
      "is_emphasis": false,
      "speech_function": "greeting"
    },
    {
      "word": "struggling",
      "start_s": 0.3,
      "end_s": 0.8,
      "is_emphasis": true,
      "speech_function": "pain_point"
    }
  ]
}
```

### Get Frame Analysis
```bash
curl "http://localhost:8000/api/viral-analysis/videos/$VIDEO_ID/frames"
```

### Get Timeline at Specific Time
```bash
# Get what's happening at 5.5 seconds
curl "http://localhost:8000/api/viral-analysis/videos/$VIDEO_ID/timeline?timestamp_s=5.5&window_s=2.0"
```

### Get Aggregate Metrics
```bash
curl "http://localhost:8000/api/viral-analysis/videos/$VIDEO_ID/metrics"
```

**Returns:**
```json
{
  "pacing": {
    "words_per_minute": 234.5,
    "emphasis_word_count": 12,
    "cta_word_count": 3
  },
  "composition": {
    "face_presence_pct": 78.3,
    "eye_contact_pct": 65.2,
    "text_presence_pct": 45.1,
    "scene_change_count": 8
  },
  "shot_distribution": {
    "close_up": 45,
    "medium": 38,
    "screen_record": 37
  }
}
```

---

## 🎯 Test on 10 Videos

### Method 1: Using Batch Analyzer

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

# Analyze 10 videos with 5 parallel workers
python3 -m services.batch_analyzer --limit 10 --workers 5
```

**Expected output:**
```
============================================================
BATCH VIDEO ANALYSIS STARTED
Max workers: 5
Skip existing: True
============================================================

📊 Found 10 videos to analyze

🎬 Starting: video1.mp4
🎬 Starting: video2.mp4
🎬 Starting: video3.mp4
...

============================================================
📊 Progress: 10/10 (100.0%)
   ✅ Succeeded: 8
   ⏭️  Skipped: 1
   ❌ Failed: 1
   ⚡ Rate: 0.18 videos/sec
   ⏱️  ETA: 0:00:00
============================================================

✅ Complete: 156 words, 120 frames (45.3s)
...

============================================================
BATCH ANALYSIS COMPLETE
============================================================
Total videos: 10
Processed: 10
Succeeded: 8
Skipped: 1
Failed: 1
Duration: 0:08:32
Rate: 0.19 videos/sec
Avg time per video: 51.2s
============================================================

📝 Summary saved to batch_analysis_summary.json
```

---

## ⚡ Process All 8,410 Videos

### Recommended Settings

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

# Process all videos with 50 parallel workers
python3 -m services.batch_analyzer --workers 50

# Or process in batches (safer)
python3 -m services.batch_analyzer --limit 1000 --workers 50
# Run multiple times until all done
```

### Performance Estimates

**With 50 workers:**
- Processing rate: ~0.8-1.2 videos/second
- 8,410 videos ÷ 1 video/sec = ~140 minutes = **2.3 hours**
- Actual time with overhead: **2.5-3.5 hours**

**With 20 workers (more stable):**
- Processing rate: ~0.5-0.7 videos/second
- 8,410 videos ÷ 0.6 video/sec = ~234 minutes = **3.9 hours**
- Actual time: **4-5 hours**

### Monitor Progress

The batch analyzer logs progress every 10 videos:

```
============================================================
📊 Progress: 230/8410 (2.7%)
   ✅ Succeeded: 215
   ⏭️  Skipped: 12
   ❌ Failed: 3
   ⚡ Rate: 0.95 videos/sec
   ⏱️  ETA: 2:23:15
============================================================
```

### Resume After Interruption

The analyzer skips already-processed videos by default, so you can safely restart:

```bash
# Restart - will skip already analyzed videos
python3 -m services.batch_analyzer --workers 50
```

### Force Reanalyze
```bash
# Reanalyze everything (even if already processed)
python3 -m services.batch_analyzer --workers 50 --no-skip
```

---

## 🔍 Verify Results

### Check How Many Videos Are Analyzed

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT 
  COUNT(DISTINCT video_id) as analyzed_videos,
  SUM(CASE WHEN video_id IN (SELECT id FROM videos) THEN 1 ELSE 0 END) as total_videos,
  COUNT(*) as total_words
FROM video_words;
"
```

### See Analysis Coverage

```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT 
  COUNT(*) as total_videos,
  SUM(CASE WHEN id IN (SELECT DISTINCT video_id FROM video_words) THEN 1 ELSE 0 END) as analyzed,
  ROUND(SUM(CASE WHEN id IN (SELECT DISTINCT video_id FROM video_words) THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as pct_analyzed
FROM videos;
"
```

### Sample Analysis Data

```bash
# Get 5 analyzed videos with metrics
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c "
SELECT 
  v.file_name,
  COUNT(DISTINCT vw.id) as words,
  COUNT(DISTINCT vf.id) as frames,
  ROUND(AVG(vw.sentiment_score)::numeric, 2) as avg_sentiment
FROM videos v
JOIN video_words vw ON v.id = vw.video_id
LEFT JOIN video_frames vf ON v.id = vf.video_id
GROUP BY v.id, v.file_name
LIMIT 5;
"
```

---

## 📈 Performance Optimization Tips

### 1. Adjust Worker Count

**More workers = faster, but more resource usage**

```bash
# Conservative (low resource usage)
python3 -m services.batch_analyzer --workers 10

# Balanced (recommended)
python3 -m services.batch_analyzer --workers 30

# Aggressive (fast, high resource usage)
python3 -m services.batch_analyzer --workers 70
```

### 2. Process by Workspace

```bash
# Get workspace ID
WORKSPACE_ID=$(docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -t -c \
  "SELECT id FROM workspaces LIMIT 1" | tr -d ' ')

# Process only videos in that workspace
python3 -m services.batch_analyzer --workspace-id $WORKSPACE_ID --workers 50
```

### 3. Monitor System Resources

```bash
# In another terminal, monitor resource usage
watch -n 2 'ps aux | grep python | head -20'

# Or use htop
htop
```

### 4. Batch Processing Strategy

```bash
# Process in chunks of 500 videos
for i in {1..17}; do
  echo "Processing batch $i"
  python3 -m services.batch_analyzer --limit 500 --workers 50
  sleep 60  # Rest between batches
done
```

---

## 🐛 Troubleshooting

### Error: "OPENAI_API_KEY not found"

Make sure your `.env` file has the key:
```bash
echo "OPENAI_API_KEY=sk-..." >> Backend/.env
```

### Error: "Video file not found"

Check video paths in database:
```bash
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c \
  "SELECT source_uri FROM videos WHERE id NOT IN (SELECT DISTINCT video_id FROM video_words) LIMIT 5;"
```

### Error: "Database connection failed"

Make sure Supabase is running:
```bash
supabase status
```

### Slow Performance

- Reduce worker count
- Check disk I/O (video files should be on SSD)
- Monitor OpenAI API rate limits
- Check network connectivity

### Memory Issues

```bash
# Reduce workers
python3 -m services.batch_analyzer --workers 10

# Process in smaller batches
python3 -m services.batch_analyzer --limit 100 --workers 10
```

---

## 📊 Expected Results

### After Analyzing All Videos

You should have:
- ✅ ~1.2 million words in `video_words` table
- ✅ ~5 million frames in `video_frames` table
- ✅ Complete timeline data for all videos
- ✅ Speech function tagging on all words
- ✅ Shot type classification on all frames
- ✅ Face detection and eye contact metrics
- ✅ Text detection on frames
- ✅ Visual composition scores

### Database Size

- Words: ~1.2M rows × 200 bytes = ~240 MB
- Frames: ~5M rows × 300 bytes = ~1.5 GB
- **Total additional storage: ~1.7 GB**

---

## 🎬 What's Next?

### After Analysis Complete

1. **Build Pattern Library**
   - Analyze successful videos
   - Extract common patterns
   - Populate `viral_patterns` table

2. **Create UI Components**
   - Timeline viewer
   - Word/frame sync
   - Pattern matcher

3. **Add Publishing Features**
   - Clip editor
   - Caption styling
   - Post scheduler

4. **Generate Insights**
   - Auto-identify best hooks
   - Suggest optimal CTAs
   - Recommend posting times

---

## 🚀 Commands Reference

```bash
# Test single video (pipeline)
python3 -m services.video_pipeline

# Test 10 videos (batch)
python3 -m services.batch_analyzer --limit 10 --workers 5

# Process all videos (production)
python3 -m services.batch_analyzer --workers 50

# Start API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Check analysis coverage
docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres -c \
  "SELECT COUNT(DISTINCT video_id) FROM video_words;"

# View batch results
cat batch_analysis_summary.json
```

---

**Ready to analyze! 🎉**

Start with 10 videos to test, then scale up to all 8,410!

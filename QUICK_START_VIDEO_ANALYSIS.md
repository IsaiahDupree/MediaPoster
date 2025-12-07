# 🚀 Quick Start: Video Analysis

Get your viral video insights running in **15 minutes**!

---

## Step 1: Run Database Migration (2 minutes)

### Option A: Via Docker (Recommended)
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster

# Run the migration
cat Backend/migrations/add_video_analysis_tables.sql | docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres
```

### Option B: Via Supabase Dashboard
1. Go to https://app.supabase.com (or your local Supabase Studio at http://127.0.0.1:54323)
2. Navigate to **SQL Editor**
3. Copy contents of `Backend/migrations/add_video_analysis_tables.sql`
4. Paste and click **Run**

### Verify Installation
```bash
# Check tables were created
echo "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE '%video%';" | docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres
```

You should see:
- `videos` (existing)
- `video_analysis` ✨ NEW
- `video_segments` ✨ NEW

---

## Step 2: Test the Analysis Service (5 minutes)

### Create a test script:

```bash
cd Backend
cat > test_analysis.py << 'EOF'
import asyncio
from services.video_viral_analyzer import VideoViralAnalyzer
from config import settings

async def test_analysis():
    # Initialize analyzer
    analyzer = VideoViralAnalyzer(api_key=settings.openai_api_key)
    
    # Test with a sample video
    result = await analyzer.analyze_video(
        video_id="test-123",
        filename="how-to-automate-emails.mp4",
        duration_sec=45,
        transcript="""
        Stop wasting hours on emails. I'm going to show you how to automate 
        your entire email workflow in under 5 minutes. Here's the exact system 
        I use that saves me 10 hours per week. First, set up these three 
        automation rules. Then connect your email to Make.com. Finally, watch 
        it run on autopilot. Comment 'AUTOMATION' to get my free template.
        """
    )
    
    print("\n" + "="*60)
    print("VIDEO ANALYSIS RESULTS")
    print("="*60)
    print(f"Hook Type: {result['hook_type']}")
    print(f"Hook Strength: {result['hook_strength_score']:.0%}")
    print(f"FATE Score: {result['fate_combined_score']:.0%}")
    print(f"Virality Prediction: {result['virality_prediction']}")
    print(f"Main Topic: {result['main_topic']}")
    print(f"Content Style: {result['content_style']}")
    print(f"Emotion: {result['emotion_type']} ({result['emotion_intensity']:.0%})")
    print(f"\nTop Quote: {result['transcript_summary']}")
    print(f"\nRecommendations:")
    import json
    for i, rec in enumerate(json.loads(result['recommendations']), 1):
        print(f"  {i}. {rec}")
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(test_analysis())
EOF

# Run the test
./venv/bin/python test_analysis.py
```

Expected output:
```
============================================================
VIDEO ANALYSIS RESULTS
============================================================
Hook Type: pain
Hook Strength: 85%
FATE Score: 78%
Virality Prediction: high
Main Topic: Email automation
Content Style: tutorial
Emotion: relief (70%)

Top Quote: Stop wasting hours on emails
...
```

---

## Step 3: Add Analysis Endpoint to API (5 minutes)

Add this to `Backend/api/endpoints/videos.py`:

```python
@router.post("/{video_id}/analyze")
async def analyze_video_viral(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a video for viral potential using AI
    """
    from sqlalchemy import select, insert
    from database.models import Video
    from services.video_viral_analyzer import VideoViralAnalyzer
    from config import settings
    
    # Get video
    result = await db.execute(
        select(Video).filter(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Initialize analyzer
    analyzer = VideoViralAnalyzer(api_key=settings.openai_api_key)
    
    # Analyze
    analysis_result = await analyzer.analyze_video(
        video_id=str(video_id),
        filename=video.file_name,
        duration_sec=video.duration_sec or 60,  # default if no duration
        transcript=None  # TODO: Add transcript if available
    )
    
    # Store in database
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    
    stmt = pg_insert(VideoAnalysis).values(
        **{k: v for k, v in analysis_result.items() if v != "now()"}
    ).on_conflict_do_update(
        index_elements=['video_id'],
        set_=analysis_result
    )
    
    await db.execute(stmt)
    await db.commit()
    
    return analysis_result


@router.post("/analyze-batch")
async def analyze_videos_batch(
    max_videos: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze multiple unanalyzed videos
    """
    from sqlalchemy import select
    from database.models import Video
    from services.video_viral_analyzer import VideoViralAnalyzer
    from config import settings
    
    # Get unanalyzed videos
    result = await db.execute(
        select(Video)
        .outerjoin(VideoAnalysis, Video.id == VideoAnalysis.video_id)
        .where(VideoAnalysis.id.is_(None))
        .where(Video.duration_sec.isnot(None))
        .limit(max_videos)
    )
    videos = result.scalars().all()
    
    if not videos:
        return {"message": "No videos to analyze", "count": 0}
    
    # Analyze in batch
    analyzer = VideoViralAnalyzer(api_key=settings.openai_api_key)
    
    video_data = [
        {
            "id": str(v.id),
            "filename": v.file_name,
            "duration_sec": v.duration_sec or 60,
            "transcript": None
        }
        for v in videos
    ]
    
    results = await analyzer.batch_analyze(video_data, max_concurrent=3)
    
    # Store results
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    
    for result in results:
        if result.get('analysis_status') == 'complete':
            stmt = pg_insert(VideoAnalysis).values(
                **{k: v for k, v in result.items() if v != "now()"}
            ).on_conflict_do_update(
                index_elements=['video_id'],
                set_=result
            )
            await db.execute(stmt)
    
    await db.commit()
    
    successful = sum(1 for r in results if r.get('analysis_status') == 'complete')
    
    return {
        "message": f"Analyzed {successful}/{len(videos)} videos",
        "total": len(videos),
        "successful": successful,
        "failed": len(videos) - successful
    }
```

Don't forget to import at the top:
```python
from database.models import VideoAnalysis  # Add this import
```

---

## Step 4: Update VideoAnalysis Model (3 minutes)

Add to `Backend/database/models.py`:

```python
class VideoAnalysis(Base):
    """AI-generated viral insights for videos"""
    __tablename__ = "video_analysis"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), unique=True)
    
    # Analysis Status
    analysis_status = Column(String(20))
    analyzed_at = Column(TIMESTAMP(timezone=True))
    error_message = Column(Text)
    
    # Topics
    main_topic = Column(Text)
    topics = Column(JSONB)
    
    # Hook
    hook_type = Column(String(50))
    hook_strength_score = Column(Numeric(3,2))
    
    # Emotion
    emotion_type = Column(String(50))
    emotion_intensity = Column(Numeric(3,2))
    
    # FATE Model
    focus_score = Column(Numeric(3,2))
    authority_score = Column(Numeric(3,2))
    tribe_score = Column(Numeric(3,2))
    emotion_score = Column(Numeric(3,2))
    fate_combined_score = Column(Numeric(3,2))
    
    # Content
    content_style = Column(String(50))
    pacing = Column(String(20))
    complexity_level = Column(String(20))
    
    # CTA
    has_cta = Column(Boolean, default=False)
    cta_type = Column(String(50))
    cta_clarity_score = Column(Numeric(3,2))
    cta_text = Column(Text)
    
    # Visual
    primary_shot_type = Column(String(50))
    has_text_overlays = Column(Boolean, default=False)
    has_meme_elements = Column(Boolean, default=False)
    
    # Insights
    transcript_summary = Column(Text)
    key_quotes = Column(JSONB)
    recommendations = Column(JSONB)
    virality_prediction = Column(String(20))
    
    # Metadata
    processing_time_ms = Column(Integer)
    model_version = Column(String(50))
    tokens_used = Column(Integer)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="analysis")
```

And update the `Video` model to add the relationship:
```python
# In the Video class, add:
analysis = relationship("VideoAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")
```

---

## Step 5: Test the API (5 minutes)

### Start your backend:
```bash
cd Backend
./venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 5555
```

### Test single video analysis:
```bash
# Get a video ID from your library
VIDEO_ID="<paste-a-real-video-id-here>"

# Analyze it
curl -X POST "http://localhost:5555/api/videos/$VIDEO_ID/analyze"
```

### Test batch analysis:
```bash
# Analyze up to 10 videos
curl -X POST "http://localhost:5555/api/videos/analyze-batch?max_videos=10"
```

---

## Step 6: Add Filters to Frontend (Later)

Update `useVideos` hook to support viral filters:

```typescript
// Add these parameters
interface UseVideosParams {
  // ... existing params
  hookType?: string
  fateScore?: string  // 'high' | 'medium' | 'low'
  emotionType?: string
  viralityPrediction?: string
}
```

---

## 🎯 What You Get

After completing these steps, you can:

### 1. Analyze Any Video
```bash
POST /api/videos/{video_id}/analyze
```

### 2. Batch Analyze Your Library
```bash
POST /api/videos/analyze-batch?max_videos=50
```

### 3. Filter by Viral Insights
```bash
GET /api/videos/?hook_type=pain&fate_score=high
GET /api/videos/?emotion_type=curiosity&virality_prediction=high
```

### 4. See Analysis Results
```sql
SELECT 
  v.file_name,
  va.fate_combined_score,
  va.hook_type,
  va.virality_prediction,
  va.main_topic
FROM videos v
JOIN video_analysis va ON v.id = va.video_id
WHERE va.fate_combined_score > 0.7
ORDER BY va.fate_combined_score DESC
LIMIT 10;
```

---

## 📊 Example Results

After analyzing 100 videos, you'll see patterns like:

```
Top Viral Patterns:
├─ Pain Hook + Tutorial = 0.85 avg FATE
├─ Curiosity Hook + Story = 0.78 avg FATE  
└─ Aspirational Hook + Demo = 0.72 avg FATE

Best Performing:
├─ Hook: Pain (40% of high scorers)
├─ Emotion: Relief (35%)
├─ Style: Tutorial (45%)
└─ Pacing: Fast (60%)
```

---

## 🐛 Troubleshooting

### "OPENAI_API_KEY not found"
Make sure your `.env` has:
```
OPENAI_API_KEY=sk-...
```

### "Table video_analysis does not exist"
Run the migration again:
```bash
cat Backend/migrations/add_video_analysis_tables.sql | docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres
```

### "Analysis keeps failing"
Check your API key has credits:
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## 🚀 Next Steps

1. ✅ Run migration
2. ✅ Test analysis service
3. ✅ Analyze 10 sample videos
4. ✅ Review FATE scores
5. → Add frontend viral filters (coming next!)
6. → Build insights dashboard
7. → Create recommendation engine

**You're ready to start analyzing! 🎬**

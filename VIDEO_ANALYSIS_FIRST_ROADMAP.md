# 🎬 Video Analysis First - Focused Roadmap

## Goal
Analyze all videos using AI and filter on key insights that lead to virality.

---

## 🎯 Phase 1: Video Analysis Schema & Infrastructure

### Database Extensions

#### 1. **Video Analysis Table** (Basic Insights)
```sql
CREATE TABLE video_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  
  -- Analysis Status
  analysis_status TEXT CHECK (analysis_status IN ('pending', 'processing', 'complete', 'failed')),
  analyzed_at TIMESTAMPTZ,
  
  -- AI-Generated Insights
  main_topic TEXT,
  topics JSONB,  -- ["automation", "AI", "productivity"]
  
  -- Virality Indicators
  hook_strength_score NUMERIC(3,2),  -- 0.00 - 1.00
  hook_type TEXT,  -- pain, curiosity, aspirational, contrarian, gap
  
  emotion_type TEXT,  -- relief, excitement, curiosity, fomo
  emotion_intensity NUMERIC(3,2),  -- 0.00 - 1.00
  
  -- FATE Model Scores
  focus_score NUMERIC(3,2),      -- How specific/targeted
  authority_score NUMERIC(3,2),  -- Credibility signals
  tribe_score NUMERIC(3,2),      -- Community/identity appeal
  emotion_score NUMERIC(3,2),    -- Emotional impact
  fate_combined_score NUMERIC(3,2),  -- Overall FATE score
  
  -- Content Type
  content_style TEXT,  -- tutorial, story, rant, vlog, review
  pacing TEXT,  -- fast, medium, slow
  complexity_level TEXT,  -- simple, medium, technical
  
  -- CTA Analysis
  has_cta BOOLEAN DEFAULT false,
  cta_type TEXT,  -- engagement, conversion, open_loop, conversation
  cta_clarity_score NUMERIC(3,2),
  
  -- Visual Analysis (basic)
  primary_shot_type TEXT,  -- talking_head, screen_record, b_roll, mixed
  has_text_overlays BOOLEAN DEFAULT false,
  has_meme_elements BOOLEAN DEFAULT false,
  
  -- Transcript Summary
  transcript_summary TEXT,
  key_quotes JSONB,  -- ["quote1", "quote2"]
  
  -- Metadata
  processing_time_ms INTEGER,
  model_version TEXT DEFAULT 'gpt-4o-mini',
  
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for filtering
CREATE INDEX idx_video_analysis_video_id ON video_analysis(video_id);
CREATE INDEX idx_video_analysis_status ON video_analysis(analysis_status);
CREATE INDEX idx_video_analysis_hook_type ON video_analysis(hook_type);
CREATE INDEX idx_video_analysis_emotion_type ON video_analysis(emotion_type);
CREATE INDEX idx_video_analysis_content_style ON video_analysis(content_style);
CREATE INDEX idx_video_analysis_fate_score ON video_analysis(fate_combined_score);
CREATE INDEX idx_video_analysis_hook_strength ON video_analysis(hook_strength_score);
```

#### 2. **Video Segments Table** (Timeline Structure)
```sql
CREATE TABLE video_segments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  
  -- Segment Info
  segment_type TEXT CHECK (segment_type IN ('hook', 'context', 'payload', 'payoff', 'cta')),
  start_time_sec NUMERIC(8,2),
  end_time_sec NUMERIC(8,2),
  
  -- Content
  transcript_text TEXT,
  summary TEXT,
  
  -- Insights per Segment
  key_points JSONB,
  sentiment_score NUMERIC(3,2),  -- -1.00 to 1.00
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_video_segments_video_id ON video_segments(video_id);
CREATE INDEX idx_video_segments_type ON video_segments(segment_type);
```

#### 3. **Performance Predictions Table** (Future)
```sql
CREATE TABLE video_predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  
  -- Predictions (based on similar analyzed videos)
  predicted_retention_3sec NUMERIC(3,2),  -- % who watch first 3 seconds
  predicted_avg_watch_pct NUMERIC(3,2),   -- Average % watched
  predicted_engagement_rate NUMERIC(3,2), -- Likes + comments + shares / views
  
  confidence_score NUMERIC(3,2),
  similar_videos_count INTEGER,
  
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 🤖 Phase 2: AI Analysis Pipeline

### Analysis Job Flow

```
1. Video Uploaded/Scanned
   ↓
2. Extract Basic Info (duration, resolution, file size)
   ↓
3. Generate Transcript (if video)
   ↓
4. AI Analysis (send to GPT-4)
   ↓
5. Store Insights in video_analysis table
   ↓
6. Update video status
```

### AI Analysis Prompt Template

```python
VIRAL_ANALYSIS_PROMPT = """
Analyze this video for virality potential. Provide structured insights.

VIDEO INFO:
- Filename: {filename}
- Duration: {duration} seconds
- Transcript: {transcript}

ANALYZE FOR:

1. HOOK (First 3-5 seconds):
   - Hook Type: [pain | curiosity | aspirational | contrarian | gap | absurd]
   - Hook Strength: [0.0 - 1.0]
   - Why it works or doesn't

2. CONTENT:
   - Main Topic: [one primary topic]
   - Related Topics: [list of 3-5 topics]
   - Content Style: [tutorial | story | rant | vlog | review | explainer]
   - Pacing: [fast | medium | slow]
   - Complexity: [simple | medium | technical]

3. EMOTION:
   - Primary Emotion: [relief | excitement | curiosity | fomo | frustration | hope]
   - Intensity: [0.0 - 1.0]

4. FATE MODEL:
   - Focus Score [0.0-1.0]: How specific and targeted
   - Authority Score [0.0-1.0]: Credibility and proof
   - Tribe Score [0.0-1.0]: Community/identity appeal  
   - Emotion Score [0.0-1.0]: Emotional impact
   - Overall FATE: [0.0-1.0]

5. CTA:
   - Has CTA: [true/false]
   - CTA Type: [engagement | conversion | open_loop | conversation]
   - CTA Clarity: [0.0-1.0]

6. VISUAL STYLE (if detectable):
   - Primary Shot: [talking_head | screen_record | b_roll | mixed]
   - Text Overlays: [true/false]
   - Meme Elements: [true/false]

7. KEY INSIGHTS:
   - Top Quote: [best one-liner]
   - Virality Prediction: [low | medium | high]
   - Recommendations: [3 specific improvements]

Return as JSON:
{
  "hook": {
    "type": "pain",
    "strength": 0.85,
    "analysis": "Opens with relatable pain point"
  },
  "content": {
    "main_topic": "Email automation",
    "topics": ["automation", "productivity", "AI"],
    "style": "tutorial",
    "pacing": "fast",
    "complexity": "medium"
  },
  "emotion": {
    "type": "relief",
    "intensity": 0.7
  },
  "fate": {
    "focus": 0.9,
    "authority": 0.7,
    "tribe": 0.6,
    "emotion": 0.8,
    "combined": 0.75
  },
  "cta": {
    "has_cta": true,
    "type": "engagement",
    "clarity": 0.8
  },
  "visual": {
    "primary_shot": "screen_record",
    "text_overlays": true,
    "meme_elements": false
  },
  "insights": {
    "top_quote": "Stop doing email manually",
    "virality_prediction": "high",
    "recommendations": [
      "Add stronger hook in first 2 seconds",
      "Include face cam for credibility",
      "Make CTA more specific"
    ]
  }
}
"""
```

### Backend Analysis Service

```python
# services/video_viral_analyzer.py

from openai import AsyncOpenAI
from typing import Dict, Optional
import json

class VideoViralAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def analyze_video(
        self,
        video_id: str,
        filename: str,
        duration_sec: int,
        transcript: Optional[str] = None
    ) -> Dict:
        """
        Analyze a video for viral potential
        """
        
        # Build prompt
        prompt = VIRAL_ANALYSIS_PROMPT.format(
            filename=filename,
            duration=duration_sec,
            transcript=transcript or "No transcript available"
        )
        
        # Call OpenAI
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a viral video analysis expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        # Parse response
        analysis = json.loads(response.choices[0].message.content)
        
        return {
            "video_id": video_id,
            "hook_type": analysis["hook"]["type"],
            "hook_strength_score": analysis["hook"]["strength"],
            "main_topic": analysis["content"]["main_topic"],
            "topics": analysis["content"]["topics"],
            "content_style": analysis["content"]["style"],
            "pacing": analysis["content"]["pacing"],
            "complexity_level": analysis["content"]["complexity"],
            "emotion_type": analysis["emotion"]["type"],
            "emotion_intensity": analysis["emotion"]["intensity"],
            "focus_score": analysis["fate"]["focus"],
            "authority_score": analysis["fate"]["authority"],
            "tribe_score": analysis["fate"]["tribe"],
            "emotion_score": analysis["fate"]["emotion"],
            "fate_combined_score": analysis["fate"]["combined"],
            "has_cta": analysis["cta"]["has_cta"],
            "cta_type": analysis["cta"].get("type"),
            "cta_clarity_score": analysis["cta"]["clarity"],
            "primary_shot_type": analysis["visual"]["primary_shot"],
            "has_text_overlays": analysis["visual"]["text_overlays"],
            "has_meme_elements": analysis["visual"]["meme_elements"],
            "transcript_summary": analysis["insights"]["top_quote"],
            "key_quotes": [analysis["insights"]["top_quote"]],
            "analysis_status": "complete",
            "model_version": "gpt-4o-mini"
        }
```

---

## 🎨 Phase 3: UI - Viral Filters & Analysis View

### New Filters in Video Library

```typescript
// Add to existing filters
const [hookType, setHookType] = useState<string>("")
const [emotionType, setEmotionType] = useState<string>("")
const [contentStyle, setContentStyle] = useState<string>("")
const [fateScore, setFateScore] = useState<string>("")  // high, medium, low
const [hasAnalysis, setHasAnalysis] = useState<boolean | undefined>()

// Filter controls
<Select value={hookType} onValueChange={setHookType}>
  <SelectItem value="all">All Hook Types</SelectItem>
  <SelectItem value="pain">Pain Point</SelectItem>
  <SelectItem value="curiosity">Curiosity Gap</SelectItem>
  <SelectItem value="aspirational">Aspirational</SelectItem>
  <SelectItem value="contrarian">Contrarian</SelectItem>
  <SelectItem value="gap">Information Gap</SelectItem>
</Select>

<Select value={emotionType} onValueChange={setEmotionType}>
  <SelectItem value="all">All Emotions</SelectItem>
  <SelectItem value="relief">Relief</SelectItem>
  <SelectItem value="excitement">Excitement</SelectItem>
  <SelectItem value="curiosity">Curiosity</SelectItem>
  <SelectItem value="fomo">FOMO</SelectItem>
</Select>

<Select value={fateScore} onValueChange={setFateScore}>
  <SelectItem value="all">All FATE Scores</SelectItem>
  <SelectItem value="high">High Viral Potential (0.7+)</SelectItem>
  <SelectItem value="medium">Medium Potential (0.4-0.7)</SelectItem>
  <SelectItem value="low">Low Potential (<0.4)</SelectItem>
</Select>
```

### Video Card Enhancement

```tsx
// Show viral insights on video card
<VideoCard video={video}>
  {video.analysis && (
    <div className="mt-2 space-y-1">
      {/* FATE Score Badge */}
      <Badge variant={
        video.analysis.fate_combined_score > 0.7 ? "success" :
        video.analysis.fate_combined_score > 0.4 ? "warning" :
        "destructive"
      }>
        FATE: {(video.analysis.fate_combined_score * 100).toFixed(0)}%
      </Badge>
      
      {/* Hook Type */}
      <Badge variant="outline">
        {video.analysis.hook_type}
      </Badge>
      
      {/* Emotion */}
      <Badge variant="secondary">
        {video.analysis.emotion_type}
      </Badge>
      
      {/* Content Style */}
      <div className="text-xs text-muted-foreground">
        {video.analysis.content_style} • {video.analysis.pacing}
      </div>
    </div>
  )}
</VideoCard>
```

### Analysis Details Page

```tsx
// New route: /video-library/[videoId]/analysis

<AnalysisView video={video} analysis={analysis}>
  {/* Viral Score Overview */}
  <Card>
    <CardHeader>
      <CardTitle>Viral Potential Score</CardTitle>
    </CardHeader>
    <CardContent>
      <Progress value={analysis.fate_combined_score * 100} />
      <p className="text-2xl font-bold">
        {(analysis.fate_combined_score * 100).toFixed(0)}%
      </p>
    </CardContent>
  </Card>
  
  {/* FATE Breakdown */}
  <Card>
    <CardHeader>
      <CardTitle>FATE Model Breakdown</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-2">
        <div>
          <div className="flex justify-between">
            <span>Focus (Specificity)</span>
            <span>{(analysis.focus_score * 100).toFixed(0)}%</span>
          </div>
          <Progress value={analysis.focus_score * 100} />
        </div>
        
        <div>
          <div className="flex justify-between">
            <span>Authority (Credibility)</span>
            <span>{(analysis.authority_score * 100).toFixed(0)}%</span>
          </div>
          <Progress value={analysis.authority_score * 100} />
        </div>
        
        <div>
          <div className="flex justify-between">
            <span>Tribe (Community Appeal)</span>
            <span>{(analysis.tribe_score * 100).toFixed(0)}%</span>
          </div>
          <Progress value={analysis.tribe_score * 100} />
        </div>
        
        <div>
          <div className="flex justify-between">
            <span>Emotion (Impact)</span>
            <span>{(analysis.emotion_score * 100).toFixed(0)}%</span>
          </div>
          <Progress value={analysis.emotion_score * 100} />
        </div>
      </div>
    </CardContent>
  </Card>
  
  {/* Hook Analysis */}
  <Card>
    <CardHeader>
      <CardTitle>Hook Analysis</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Badge>{analysis.hook_type}</Badge>
          <Progress value={analysis.hook_strength_score * 100} className="flex-1" />
          <span className="text-sm">{(analysis.hook_strength_score * 100).toFixed(0)}%</span>
        </div>
        <p className="text-sm text-muted-foreground">
          This video uses a <strong>{analysis.hook_type}</strong> hook with 
          <strong> {analysis.hook_strength_score > 0.7 ? 'strong' : analysis.hook_strength_score > 0.4 ? 'medium' : 'weak'}</strong> effectiveness.
        </p>
      </div>
    </CardContent>
  </Card>
  
  {/* Content Insights */}
  <Card>
    <CardHeader>
      <CardTitle>Content Insights</CardTitle>
    </CardHeader>
    <CardContent>
      <dl className="space-y-2">
        <div>
          <dt className="text-sm font-medium">Main Topic</dt>
          <dd className="text-sm text-muted-foreground">{analysis.main_topic}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium">Related Topics</dt>
          <dd className="flex gap-1 flex-wrap">
            {analysis.topics.map(topic => (
              <Badge key={topic} variant="outline">{topic}</Badge>
            ))}
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium">Style</dt>
          <dd className="text-sm text-muted-foreground">
            {analysis.content_style} • {analysis.pacing} pacing • {analysis.complexity_level}
          </dd>
        </div>
      </dl>
    </CardContent>
  </Card>
</AnalysisView>
```

---

## 🔄 Phase 4: Batch Analysis & Queue System

### Analyze All Videos Button

```tsx
// In Video Library
<Button onClick={handleAnalyzeAll}>
  <Sparkles className="mr-2 h-4 w-4" />
  Analyze All Videos ({unanalyzedCount})
</Button>
```

### Backend Queue

```python
# api/endpoints/videos.py

@router.post("/analyze-batch")
async def analyze_videos_batch(
    max_videos: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze up to N videos that don't have analysis yet
    """
    from sqlalchemy import select
    from database.models import Video, VideoAnalysis
    
    # Get videos without analysis
    result = await db.execute(
        select(Video)
        .outerjoin(VideoAnalysis, Video.id == VideoAnalysis.video_id)
        .where(VideoAnalysis.id.is_(None))
        .where(Video.duration_sec.isnot(None))  # Only videos with duration
        .limit(max_videos)
    )
    videos = result.scalars().all()
    
    # Queue for background processing
    for video in videos:
        # Create pending analysis record
        analysis = VideoAnalysis(
            video_id=video.id,
            analysis_status='pending'
        )
        db.add(analysis)
    
    await db.commit()
    
    # Trigger background jobs
    # (Use Celery, n8n, or background tasks)
    
    return {
        "message": f"Queued {len(videos)} videos for analysis",
        "video_count": len(videos)
    }
```

---

## 📊 Phase 5: Viral Insights Dashboard

### New Dashboard View

```
┌─────────────────────────────────────────────────────┐
│ Viral Insights Dashboard                           │
├─────────────────────────────────────────────────────┤
│ 📊 Your Content Breakdown                          │
│                                                     │
│ Hook Types:                                         │
│ ████████░░ Pain (40%)                              │
│ ██████░░░░ Curiosity (30%)                         │
│ ████░░░░░░ Aspirational (20%)                      │
│                                                     │
│ FATE Scores:                                        │
│ High Potential (0.7+):     23 videos              │
│ Medium Potential (0.4-0.7): 45 videos              │
│ Low Potential (<0.4):      12 videos               │
│                                                     │
│ Top Performing Patterns:                           │
│ 🏆 Pain + Tutorial + Fast = 0.85 avg FATE         │
│ 🥈 Curiosity + Story + Medium = 0.78 avg FATE     │
│ 🥉 Aspirational + Vlog + Fast = 0.72 avg FATE     │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Implementation Order

### Week 1: Database & Basic Analysis
- ✅ Create `video_analysis` table
- ✅ Create `video_segments` table
- ✅ Build `VideoViralAnalyzer` service
- ✅ Add analysis endpoint
- ✅ Test with 10 sample videos

### Week 2: Filtering & UI
- ✅ Add viral filters to backend API
- ✅ Update frontend with new filter controls
- ✅ Create analysis detail page
- ✅ Add viral badges to video cards

### Week 3: Batch Processing
- ✅ Build batch analysis queue
- ✅ Add "Analyze All" button
- ✅ Progress tracking UI
- ✅ Error handling & retries

### Week 4: Insights Dashboard
- ✅ Aggregate viral insights
- ✅ Build insights dashboard
- ✅ Pattern detection
- ✅ Recommendations engine

---

## 🎯 Success Metrics

After implementation, you should be able to:
- ✅ Analyze 1,000+ videos automatically
- ✅ Filter videos by hook type, emotion, FATE score
- ✅ See which patterns lead to high viral scores
- ✅ Identify your best-performing content styles
- ✅ Get AI recommendations for improvement

---

**This is your focused roadmap for video analysis first! 🎬**

Ready to start with the database schema and AI analysis service?

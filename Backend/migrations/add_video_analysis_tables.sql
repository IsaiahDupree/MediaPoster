-- Add video analysis tables for viral insights
-- Run this against your Supabase database

-- 1. Video Analysis Table (AI-generated viral insights)
CREATE TABLE IF NOT EXISTS video_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE UNIQUE,
  
  -- Analysis Status
  analysis_status TEXT CHECK (analysis_status IN ('pending', 'processing', 'complete', 'failed')) DEFAULT 'pending',
  analyzed_at TIMESTAMPTZ,
  error_message TEXT,
  
  -- Main Topic
  main_topic TEXT,
  topics JSONB,  -- ["automation", "AI", "productivity"]
  
  -- Hook Analysis (First 3-5 seconds)
  hook_type TEXT CHECK (hook_type IN ('pain', 'curiosity', 'aspirational', 'contrarian', 'gap', 'absurd')),
  hook_strength_score NUMERIC(3,2) CHECK (hook_strength_score >= 0 AND hook_strength_score <= 1),
  
  -- Emotion Analysis
  emotion_type TEXT CHECK (emotion_type IN ('relief', 'excitement', 'curiosity', 'fomo', 'frustration', 'hope', 'surprise')),
  emotion_intensity NUMERIC(3,2) CHECK (emotion_intensity >= 0 AND emotion_intensity <= 1),
  
  -- FATE Model Scores (viral potential framework)
  focus_score NUMERIC(3,2) CHECK (focus_score >= 0 AND focus_score <= 1),       -- How specific/targeted (0-1)
  authority_score NUMERIC(3,2) CHECK (authority_score >= 0 AND authority_score <= 1),  -- Credibility signals (0-1)
  tribe_score NUMERIC(3,2) CHECK (tribe_score >= 0 AND tribe_score <= 1),       -- Community/identity appeal (0-1)
  emotion_score NUMERIC(3,2) CHECK (emotion_score >= 0 AND emotion_score <= 1), -- Emotional impact (0-1)
  fate_combined_score NUMERIC(3,2) CHECK (fate_combined_score >= 0 AND fate_combined_score <= 1),  -- Overall viral potential (0-1)
  
  -- Content Classification
  content_style TEXT CHECK (content_style IN ('tutorial', 'story', 'rant', 'vlog', 'review', 'explainer', 'demo', 'interview')),
  pacing TEXT CHECK (pacing IN ('fast', 'medium', 'slow')),
  complexity_level TEXT CHECK (complexity_level IN ('simple', 'medium', 'technical')),
  
  -- CTA Analysis
  has_cta BOOLEAN DEFAULT false,
  cta_type TEXT CHECK (cta_type IN ('engagement', 'conversion', 'open_loop', 'conversation')),
  cta_clarity_score NUMERIC(3,2) CHECK (cta_clarity_score >= 0 AND cta_clarity_score <= 1),
  cta_text TEXT,
  
  -- Visual Style (basic detection from filename/metadata)
  primary_shot_type TEXT CHECK (primary_shot_type IN ('talking_head', 'screen_record', 'b_roll', 'mixed', 'animation')),
  has_text_overlays BOOLEAN DEFAULT false,
  has_meme_elements BOOLEAN DEFAULT false,
  
  -- AI Insights
  transcript_summary TEXT,
  key_quotes JSONB,  -- ["quote1", "quote2", "quote3"]
  recommendations JSONB,  -- ["recommendation1", "recommendation2", "recommendation3"]
  virality_prediction TEXT CHECK (virality_prediction IN ('low', 'medium', 'high')),
  
  -- Processing Metadata
  processing_time_ms INTEGER,
  model_version TEXT DEFAULT 'gpt-4o-mini',
  tokens_used INTEGER,
  
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast filtering
CREATE INDEX idx_video_analysis_video_id ON video_analysis(video_id);
CREATE INDEX idx_video_analysis_status ON video_analysis(analysis_status);
CREATE INDEX idx_video_analysis_hook_type ON video_analysis(hook_type);
CREATE INDEX idx_video_analysis_emotion_type ON video_analysis(emotion_type);
CREATE INDEX idx_video_analysis_content_style ON video_analysis(content_style);
CREATE INDEX idx_video_analysis_fate_score ON video_analysis(fate_combined_score DESC);
CREATE INDEX idx_video_analysis_hook_strength ON video_analysis(hook_strength_score DESC);
CREATE INDEX idx_video_analysis_virality ON video_analysis(virality_prediction);

-- Full text search on topics
CREATE INDEX idx_video_analysis_topics_gin ON video_analysis USING gin(topics);

-- 2. Video Segments Table (Timeline breakdown)
CREATE TABLE IF NOT EXISTS video_segments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  
  -- Segment Info
  segment_type TEXT CHECK (segment_type IN ('hook', 'context', 'payload', 'payoff', 'cta')) NOT NULL,
  segment_order INTEGER,  -- 1, 2, 3... for ordering
  start_time_sec NUMERIC(8,2),
  end_time_sec NUMERIC(8,2),
  
  -- Content
  transcript_text TEXT,
  summary TEXT,
  
  -- Segment-specific insights
  key_points JSONB,
  sentiment_score NUMERIC(3,2) CHECK (sentiment_score >= -1 AND sentiment_score <= 1),  -- -1 (negative) to 1 (positive)
  importance_score NUMERIC(3,2) CHECK (importance_score >= 0 AND importance_score <= 1),
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_video_segments_video_id ON video_segments(video_id);
CREATE INDEX idx_video_segments_type ON video_segments(segment_type);
CREATE INDEX idx_video_segments_order ON video_segments(video_id, segment_order);

-- 3. Comments for documentation
COMMENT ON TABLE video_analysis IS 'AI-generated viral insights and FATE model scores for each video';
COMMENT ON COLUMN video_analysis.fate_combined_score IS 'Combined FATE score: higher = more viral potential (0-1)';
COMMENT ON COLUMN video_analysis.hook_strength_score IS 'How effective the first 3-5 seconds are at grabbing attention (0-1)';
COMMENT ON COLUMN video_analysis.focus_score IS 'FATE: How specific and targeted the content is (0-1)';
COMMENT ON COLUMN video_analysis.authority_score IS 'FATE: Credibility and proof signals (0-1)';
COMMENT ON COLUMN video_analysis.tribe_score IS 'FATE: Community and identity appeal (0-1)';
COMMENT ON COLUMN video_analysis.emotion_score IS 'FATE: Emotional impact and resonance (0-1)';

-- 4. Update function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_video_analysis_updated_at BEFORE UPDATE ON video_analysis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. View for easy querying of videos with analysis
CREATE OR REPLACE VIEW videos_with_analysis AS
SELECT 
    v.*,
    va.analysis_status,
    va.hook_type,
    va.hook_strength_score,
    va.emotion_type,
    va.fate_combined_score,
    va.content_style,
    va.virality_prediction,
    va.main_topic,
    va.has_cta
FROM videos v
LEFT JOIN video_analysis va ON v.id = va.video_id;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Video analysis tables created successfully!';
    RAISE NOTICE 'Tables created: video_analysis, video_segments';
    RAISE NOTICE 'View created: videos_with_analysis';
    RAISE NOTICE 'Next step: Run the analysis service to populate insights';
END $$;

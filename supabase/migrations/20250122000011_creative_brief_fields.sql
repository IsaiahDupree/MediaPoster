-- Migration: Add Creative Brief Generation Fields to video_analysis
-- Version: 3.2
-- Purpose: Enable comprehensive creative brief regeneration from analysis data

-- Add new columns for pain points and emotional analysis
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS pain_points TEXT[] DEFAULT '{}';

ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS emotional_drivers TEXT[] DEFAULT '{}';

ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS emotional_journey JSONB DEFAULT '{}';

-- Add structured CTA extraction
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS call_to_action JSONB DEFAULT '{}';

-- Add scene structure for video generation
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS scene_structure JSONB DEFAULT '[]';

-- Add content classification
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS content_type TEXT;

-- Add target audience analysis
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS target_audience JSONB DEFAULT '{}';

-- Add comments for documentation
COMMENT ON COLUMN video_analysis.pain_points IS 'Problems/frustrations the content addresses';
COMMENT ON COLUMN video_analysis.emotional_drivers IS 'Motivations: FOMO, transformation, belonging, etc.';
COMMENT ON COLUMN video_analysis.emotional_journey IS 'Emotional arc: {opening_emotion, peak_emotion, closing_emotion}';
COMMENT ON COLUMN video_analysis.call_to_action IS 'Structured CTA: {type, text, strength, timestamp_hint}';
COMMENT ON COLUMN video_analysis.scene_structure IS 'Scene breakdown: [{start_sec, end_sec, role, summary, emotion}]';
COMMENT ON COLUMN video_analysis.content_type IS 'Content classification: tutorial, storytime, review, transformation, etc.';
COMMENT ON COLUMN video_analysis.target_audience IS 'Audience analysis: {demographic, interests[], awareness_level}';

-- Create index for content_type filtering
CREATE INDEX IF NOT EXISTS idx_video_analysis_content_type ON video_analysis(content_type);

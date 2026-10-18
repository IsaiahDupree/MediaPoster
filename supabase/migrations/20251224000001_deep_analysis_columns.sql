-- Add deep analysis columns to video_analysis table
-- This enables full visual/frame analysis alongside transcription

-- Add visual analysis column (stores frame-by-frame analysis)
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS visual_analysis JSONB DEFAULT NULL;

-- Add deep analysis column (stores comprehensive AI analysis)
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS deep_analysis JSONB DEFAULT NULL;

-- Add frame analyses column (stores individual frame data)
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS frame_analyses JSONB DEFAULT NULL;

-- Add platform-specific content suggestions
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS platform_content JSONB DEFAULT NULL;

-- Add detected hook (best hook moment)
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS detected_hook TEXT DEFAULT NULL;

-- Add music suggestion
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS music_suggestion JSONB DEFAULT NULL;

-- Add pillar tags for content categorization
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS pillar_tags TEXT[] DEFAULT NULL;

-- Add format tags
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS format_tags TEXT[] DEFAULT NULL;

-- Create index for faster queries on analyzed content
CREATE INDEX IF NOT EXISTS idx_video_analysis_score ON video_analysis(pre_social_score DESC);
CREATE INDEX IF NOT EXISTS idx_video_analysis_topics ON video_analysis USING GIN(topics);

COMMENT ON COLUMN video_analysis.visual_analysis IS 'Frame-by-frame visual analysis from GPT-4 Vision';
COMMENT ON COLUMN video_analysis.deep_analysis IS 'Comprehensive deep analysis including visual, audio, and content insights';
COMMENT ON COLUMN video_analysis.frame_analyses IS 'Individual frame analysis data with timestamps';
COMMENT ON COLUMN video_analysis.platform_content IS 'Platform-specific content recommendations (TikTok, Instagram, YouTube)';
COMMENT ON COLUMN video_analysis.detected_hook IS 'Best detected hook phrase from the content';
COMMENT ON COLUMN video_analysis.music_suggestion IS 'AI-suggested music/audio recommendations';

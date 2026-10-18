-- Add curation columns to video_analysis table
-- Migration for curation state persistence

-- Add curation_status and curated_at columns to video_analysis
ALTER TABLE video_analysis 
ADD COLUMN IF NOT EXISTS curation_status TEXT,
ADD COLUMN IF NOT EXISTS curated_at TIMESTAMPTZ;

-- Create index for curation_status filtering
CREATE INDEX IF NOT EXISTS idx_video_analysis_curation_status ON video_analysis(curation_status);

-- Add comments for documentation
COMMENT ON COLUMN video_analysis.curation_status IS 'Curation status: pending, approved, rejected';
COMMENT ON COLUMN video_analysis.curated_at IS 'Timestamp when video was curated';

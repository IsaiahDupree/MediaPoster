-- Add video orientation and routing fields to videos table
-- Migration for video orientation detection and YouTube routing feature

-- Add orientation and routing fields
ALTER TABLE videos 
ADD COLUMN IF NOT EXISTS orientation TEXT CHECK (orientation IN ('vertical', 'horizontal', 'square')),
ADD COLUMN IF NOT EXISTS aspect_ratio FLOAT,
ADD COLUMN IF NOT EXISTS duration_seconds FLOAT,
ADD COLUMN IF NOT EXISTS auto_routed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS routing_reason TEXT,
ADD COLUMN IF NOT EXISTS recommended_platforms TEXT[];

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_videos_orientation ON videos(orientation);
CREATE INDEX IF NOT EXISTS idx_videos_duration ON videos(duration_seconds);
CREATE INDEX IF NOT EXISTS idx_videos_auto_routed ON videos(auto_routed);

-- Create YouTube channel configuration table
CREATE TABLE IF NOT EXISTS youtube_channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  channel_id TEXT UNIQUE NOT NULL,
  channel_name TEXT NOT NULL,
  channel_url TEXT,
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMPTZ,
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create video routing history table
CREATE TABLE IF NOT EXISTS video_routing_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  orientation TEXT NOT NULL,
  duration_seconds FLOAT NOT NULL,
  selected_platforms TEXT[] NOT NULL,
  routing_rule TEXT NOT NULL,
  manual_override BOOLEAN DEFAULT FALSE,
  youtube_channel_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for routing log
CREATE INDEX IF NOT EXISTS idx_routing_log_video ON video_routing_log(video_id);
CREATE INDEX IF NOT EXISTS idx_routing_log_created ON video_routing_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routing_log_orientation ON video_routing_log(orientation);

-- Create indexes for YouTube channels
CREATE INDEX IF NOT EXISTS idx_youtube_channels_user ON youtube_channels(user_id);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_default ON youtube_channels(is_default) WHERE is_default = TRUE;

-- Add comments for documentation
COMMENT ON COLUMN videos.orientation IS 'Video orientation: vertical (9:16), horizontal (16:9), or square (1:1)';
COMMENT ON COLUMN videos.aspect_ratio IS 'Video aspect ratio (width/height)';
COMMENT ON COLUMN videos.duration_seconds IS 'Video duration in seconds';
COMMENT ON COLUMN videos.auto_routed IS 'Whether video was automatically routed based on orientation/duration';
COMMENT ON COLUMN videos.routing_reason IS 'Explanation of routing decision';
COMMENT ON COLUMN videos.recommended_platforms IS 'Array of recommended platforms based on video characteristics';

COMMENT ON TABLE youtube_channels IS 'YouTube channel configurations for video uploads';
COMMENT ON TABLE video_routing_log IS 'History of video routing decisions for analytics';

-- Update trigger for youtube_channels updated_at
CREATE OR REPLACE FUNCTION update_youtube_channels_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER youtube_channels_updated_at
  BEFORE UPDATE ON youtube_channels
  FOR EACH ROW
  EXECUTE FUNCTION update_youtube_channels_updated_at();

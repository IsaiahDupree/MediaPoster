-- Base video tables for Content Intelligence System
-- Migration: 003_base_video_tables
-- Created: 2025-01-21
-- Creates original_videos and clips tables with id columns to match migration expectations

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Original Videos Table (with id column for compatibility)
CREATE TABLE IF NOT EXISTS original_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID UNIQUE DEFAULT gen_random_uuid(), -- Keep for backward compatibility
    source VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    duration_seconds FLOAT NOT NULL,
    
    date_recorded TIMESTAMP WITH TIME ZONE,
    date_uploaded TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date_processed TIMESTAMP WITH TIME ZONE,
    
    transcript TEXT,
    topics TEXT[],
    keywords TEXT[],
    
    analysis_data JSONB,
    metadata JSONB,
    
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_original_videos_status ON original_videos(processing_status);
CREATE INDEX IF NOT EXISTS idx_original_videos_date_recorded ON original_videos(date_recorded DESC);
CREATE INDEX IF NOT EXISTS idx_original_videos_video_id ON original_videos(video_id);

-- Clips Table (with id column for compatibility)
CREATE TABLE IF NOT EXISTS clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id UUID UNIQUE DEFAULT gen_random_uuid(), -- Keep for backward compatibility
    parent_video_id UUID REFERENCES original_videos(id) ON DELETE CASCADE,
    
    segment_start_seconds FLOAT NOT NULL,
    segment_end_seconds FLOAT NOT NULL,
    clip_duration_seconds FLOAT NOT NULL,
    
    file_path TEXT,
    file_size_bytes BIGINT,
    
    hook_text TEXT,
    caption_text TEXT,
    generated_hashtags TEXT[],
    
    tags TEXT[],
    content_category VARCHAR(100),
    hook_type VARCHAR(100),
    has_cta BOOLEAN DEFAULT false,
    visual_elements JSONB,
    target_keyword VARCHAR(255),
    predicted_audience_reaction VARCHAR(100),
    
    clip_status VARCHAR(50) DEFAULT 'generated',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clips_parent_video ON clips(parent_video_id);
CREATE INDEX IF NOT EXISTS idx_clips_status ON clips(clip_status);
CREATE INDEX IF NOT EXISTS idx_clips_hook_type ON clips(hook_type);
CREATE INDEX IF NOT EXISTS idx_clips_target_keyword ON clips(target_keyword);
CREATE INDEX IF NOT EXISTS idx_clips_clip_id ON clips(clip_id);

-- Enable RLS
ALTER TABLE original_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE clips ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE original_videos IS 'Original videos uploaded from iPhone or other sources';
COMMENT ON TABLE clips IS 'Generated short clips from video highlights';



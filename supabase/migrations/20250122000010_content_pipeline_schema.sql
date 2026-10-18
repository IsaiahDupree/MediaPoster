-- Migration: Content Pipeline Schema for Analysis-to-Generation Flow
-- Version: 1.0
-- Purpose: Complete schema for content assets, deep audits, posts, snapshots, 
--          retention series, comments, platform constraints, copy plans, and Remotion specs

-- Enable UUIDs (Supabase usually has this)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================
-- 1) CONTENT ASSETS - Canonical video/media assets
-- =====================================================
CREATE TABLE IF NOT EXISTS content_asset (
  asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT NOT NULL CHECK (source_type IN ('uploaded_video','url_import','platform_download','live_capture','local_file')),
  source_url TEXT,
  source_path TEXT,  -- Local file path if applicable
  duration_sec NUMERIC NOT NULL,
  fps NUMERIC,
  width INT,
  height INT,
  aspect_ratio TEXT,  -- '9:16', '1:1', '16:9', etc.
  codec TEXT,
  bitrate_kbps INT,
  loudness_lufs NUMERIC,
  audio_language TEXT,

  -- Dedupe / linking same video across posts
  phash TEXT,           -- perceptual hash (video)
  audio_hash TEXT,      -- audio fingerprint hash
  file_hash TEXT,       -- MD5/SHA hash of file

  -- Link to existing videos table if applicable
  video_id UUID REFERENCES videos(id) ON DELETE SET NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_asset_video ON content_asset(video_id);
CREATE INDEX IF NOT EXISTS idx_content_asset_phash ON content_asset(phash);
CREATE INDEX IF NOT EXISTS idx_content_asset_source ON content_asset(source_type);

-- =====================================================
-- 2) DEEP AUDIT - Comprehensive AI analysis (pre-post)
-- =====================================================
CREATE TABLE IF NOT EXISTS deep_audit (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID NOT NULL REFERENCES content_asset(asset_id) ON DELETE CASCADE,

  audit_version TEXT NOT NULL,     -- e.g., 'deep_audit_v1', 'deep_audit_v2'
  model TEXT,                      -- e.g., 'gpt-4-turbo', 'gpt-4o', 'whisper-1'
  prompt_hash TEXT,                -- Hash of prompt used for reproducibility
  temperature NUMERIC,

  -- Big JSON blob containing all analysis data
  data JSONB NOT NULL,             -- transcript/beat_sheet/edl/style_fingerprint/scene_structure/etc.
  
  -- Quick access fields extracted from data
  transcript_text TEXT,
  hook TEXT,
  topics TEXT[],
  tone TEXT,
  viral_score NUMERIC,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deep_audit_asset ON deep_audit(asset_id);
CREATE INDEX IF NOT EXISTS idx_deep_audit_version ON deep_audit(audit_version);

-- =====================================================
-- 3) PLATFORM POSTS - Published content across platforms
-- =====================================================
CREATE TABLE IF NOT EXISTS platform_post (
  post_uid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID NOT NULL REFERENCES content_asset(asset_id) ON DELETE CASCADE,

  platform TEXT NOT NULL,          -- 'youtube','instagram','tiktok','x','threads','linkedin','pinterest','facebook'
  platform_post_id TEXT NOT NULL,  -- Platform's native ID
  handle TEXT,                     -- Account handle used
  account_id TEXT,                 -- Internal account ID (e.g., Blotato account ID)
  published_at TIMESTAMPTZ,
  permalink TEXT,

  -- Creative content used
  creative JSONB,                  -- title/description/caption/hashtags/audio_id/thumbnail_id etc.
  raw_publish JSONB,               -- Raw publish payload envelope

  -- Status tracking
  status TEXT DEFAULT 'published', -- 'draft', 'scheduled', 'published', 'deleted', 'failed'

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  UNIQUE(platform, platform_post_id)
);

CREATE INDEX IF NOT EXISTS idx_platform_post_asset ON platform_post(asset_id);
CREATE INDEX IF NOT EXISTS idx_platform_post_platform ON platform_post(platform);
CREATE INDEX IF NOT EXISTS idx_platform_post_handle ON platform_post(handle);
CREATE INDEX IF NOT EXISTS idx_platform_post_published ON platform_post(published_at);

-- =====================================================
-- 4) POST SNAPSHOTS - Performance checkbacks over time
-- =====================================================
CREATE TABLE IF NOT EXISTS post_snapshot (
  snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_uid UUID NOT NULL REFERENCES platform_post(post_uid) ON DELETE CASCADE,

  sampled_at TIMESTAMPTZ NOT NULL,
  window_label TEXT NOT NULL,      -- 'T+1h','T+24h','T+7d','T+30d', etc.

  -- Metrics buckets
  totals JSONB,                    -- views/likes/comments/shares/saves/impressions/reach/clicks
  watch JSONB,                     -- avg_view_duration, completion_rate, quartiles
  conversion JSONB,                -- follows, profile_visits, website_clicks, dm_initiations
  monetization JSONB,              -- rpm/cpm/revenue if available
  derived JSONB,                   -- engagement_rate, velocity, decay calculations
  availability JSONB,              -- per-field availability state (which metrics available)
  raw_snapshot JSONB,              -- Raw API response envelope

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshot_post ON post_snapshot(post_uid, sampled_at);
CREATE INDEX IF NOT EXISTS idx_snapshot_window ON post_snapshot(window_label);

-- =====================================================
-- 5) RETENTION SERIES - Drop-off curve data
-- =====================================================
CREATE TABLE IF NOT EXISTS retention_series (
  retention_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_uid UUID NOT NULL REFERENCES platform_post(post_uid) ON DELETE CASCADE,
  sampled_at TIMESTAMPTZ NOT NULL,

  points JSONB,                    -- Array of buckets [{t_ratio, t_sec, retention_pct, viewers}]
  annotations JSONB,               -- biggest_drops, hold_points mapped to beat_id/edl events
  availability JSONB,
  raw_retention JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_retention_post ON retention_series(post_uid, sampled_at);

-- =====================================================
-- 6) COMMENTS - Raw comments + AI-generated insights
-- =====================================================
CREATE TABLE IF NOT EXISTS comment_event (
  platform TEXT NOT NULL,
  post_uid UUID NOT NULL REFERENCES platform_post(post_uid) ON DELETE CASCADE,

  comment_id TEXT NOT NULL,
  parent_comment_id TEXT,          -- For replies
  commented_at TIMESTAMPTZ NOT NULL,

  author_id_hash TEXT,             -- Hashed to avoid PII
  author_handle TEXT,
  text TEXT NOT NULL,
  like_count INT DEFAULT 0,
  reply_count INT DEFAULT 0,
  is_creator BOOLEAN DEFAULT FALSE,
  is_creator_reply BOOLEAN DEFAULT FALSE,

  -- Sentiment/classification
  sentiment TEXT,                  -- 'positive', 'negative', 'neutral'
  intent TEXT,                     -- 'question', 'praise', 'criticism', 'suggestion'

  raw_comment JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  PRIMARY KEY (platform, post_uid, comment_id)
);

CREATE INDEX IF NOT EXISTS idx_comment_post ON comment_event(post_uid, commented_at);

CREATE TABLE IF NOT EXISTS comment_insights_snapshot (
  insights_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_uid UUID NOT NULL REFERENCES platform_post(post_uid) ON DELETE CASCADE,
  sampled_at TIMESTAMPTZ NOT NULL,

  insights JSONB NOT NULL,         -- themes, objections, faq, next_video_ideas, reply_templates
  raw_insights JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comment_insights_post ON comment_insights_snapshot(post_uid);

-- =====================================================
-- 7) PLATFORM TEXT CONSTRAINTS - Character limits & rules
-- =====================================================
CREATE TABLE IF NOT EXISTS platform_text_constraints (
  constraint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  platform TEXT NOT NULL,          -- 'youtube','instagram','tiktok','x','threads','pinterest','linkedin','facebook'
  surface TEXT NOT NULL,           -- 'organic_post','reel','short','video','feed','post','pin','standard_post','long_post'
  field TEXT NOT NULL,             -- 'title','description','caption','hashtags','mentions'

  max_chars INT,                   -- Hard max if known
  soft_cap_chars INT,              -- Recommended cap (for sanity)
  target_margin_pct NUMERIC NOT NULL DEFAULT 0.20, -- 20% under max

  max_hashtags INT,
  max_mentions INT,

  count_rule TEXT NOT NULL DEFAULT 'graphemes', -- 'utf16'|'utf8_bytes'|'graphemes'
  notes TEXT,

  source_url TEXT,
  source_quality TEXT NOT NULL DEFAULT 'official', -- 'official'|'public'|'unknown'
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE(platform, surface, field)
);

CREATE INDEX IF NOT EXISTS idx_constraints_lookup ON platform_text_constraints(platform, surface, field);

-- =====================================================
-- 8) COPY PLAN - AI-generated platform-specific copy
-- =====================================================
CREATE TABLE IF NOT EXISTS copy_plan (
  copy_plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID REFERENCES content_asset(asset_id) ON DELETE CASCADE,
  post_uid UUID REFERENCES platform_post(post_uid) ON DELETE CASCADE,
  audit_id UUID REFERENCES deep_audit(audit_id) ON DELETE SET NULL,

  platform TEXT NOT NULL,
  surface TEXT NOT NULL,

  -- Full copy plan data
  data JSONB NOT NULL,             -- Generated titles/captions/descriptions + char counts + fits flags
  
  -- Quick access fields
  title TEXT,
  caption TEXT,
  description TEXT,
  hashtags TEXT[],
  mentions TEXT[],
  
  -- Generation metadata
  model TEXT,
  prompt_version TEXT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_copy_plan_asset ON copy_plan(asset_id, platform, surface);
CREATE INDEX IF NOT EXISTS idx_copy_plan_post ON copy_plan(post_uid);

-- =====================================================
-- 9) REMOTION RENDER SPEC - Video composition specs
-- =====================================================
CREATE TABLE IF NOT EXISTS remotion_render_spec (
  render_spec_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID NOT NULL REFERENCES content_asset(asset_id) ON DELETE CASCADE,
  audit_id UUID REFERENCES deep_audit(audit_id) ON DELETE SET NULL,

  composition_id TEXT NOT NULL,    -- e.g. 'ShortFormV1', 'LongFormTutorial'
  fps INT NOT NULL,
  width INT NOT NULL,
  height INT NOT NULL,
  duration_in_frames INT NOT NULL,

  -- Full spec blob for Remotion
  spec JSONB NOT NULL,
  
  -- Status tracking
  status TEXT DEFAULT 'draft',     -- 'draft', 'ready', 'rendering', 'completed', 'failed'
  render_job_id TEXT,              -- External render job ID
  output_url TEXT,                 -- Final rendered video URL

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_render_asset ON remotion_render_spec(asset_id);
CREATE INDEX IF NOT EXISTS idx_render_composition ON remotion_render_spec(composition_id);

-- =====================================================
-- 10) BEAT SHEET - Scene/segment structure
-- =====================================================
CREATE TABLE IF NOT EXISTS beat_sheet (
  beat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID NOT NULL REFERENCES content_asset(asset_id) ON DELETE CASCADE,
  audit_id UUID REFERENCES deep_audit(audit_id) ON DELETE SET NULL,

  beat_order INT NOT NULL,
  start_sec NUMERIC NOT NULL,
  end_sec NUMERIC NOT NULL,
  
  role TEXT NOT NULL,              -- 'hook', 'problem', 'solution', 'proof', 'cta', 'transition', 'other'
  summary TEXT,
  emotion TEXT,
  
  -- Visual/audio markers
  visual_markers JSONB,            -- Key frame info, transitions
  audio_markers JSONB,             -- Music cues, emphasis points
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_beat_asset ON beat_sheet(asset_id, beat_order);

-- =====================================================
-- Add comments for documentation
-- =====================================================
COMMENT ON TABLE content_asset IS 'Canonical video/media assets with technical metadata and deduplication hashes';
COMMENT ON TABLE deep_audit IS 'Comprehensive AI analysis results from GPT-4, Whisper, Vision, etc.';
COMMENT ON TABLE platform_post IS 'Published content across social platforms with creative metadata';
COMMENT ON TABLE post_snapshot IS 'Performance metrics snapshots at different time windows (T+1h, T+24h, etc.)';
COMMENT ON TABLE retention_series IS 'Watch-time retention curves and drop-off analysis';
COMMENT ON TABLE comment_event IS 'Individual comments with sentiment and intent classification';
COMMENT ON TABLE comment_insights_snapshot IS 'AI-summarized comment themes, objections, and content ideas';
COMMENT ON TABLE platform_text_constraints IS 'Platform-specific character limits and counting rules';
COMMENT ON TABLE copy_plan IS 'AI-generated platform-optimized copy (titles, captions, descriptions)';
COMMENT ON TABLE remotion_render_spec IS 'Video composition specs for Remotion rendering';
COMMENT ON TABLE beat_sheet IS 'Scene/segment structure with roles and timing';

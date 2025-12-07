-- ============================================================================
-- PHASE 1: ESSENTIAL FOUNDATION
-- Core tables needed for MediaPoster to function
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. WORKSPACES & USERS (Multi-tenant foundation)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_id UUID,  -- Will reference users after users table created
  plan TEXT CHECK (plan IN ('free', 'pro', 'enterprise')),
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add foreign key for workspace owner
ALTER TABLE workspaces 
  ADD CONSTRAINT fk_workspace_owner 
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS workspace_members (
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);

-- ----------------------------------------------------------------------------
-- 2. SOCIAL ACCOUNTS (Connected platforms)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS social_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN (
    'instagram', 'facebook', 'threads', 'tiktok', 'youtube', 
    'twitter', 'linkedin', 'pinterest', 'blotato', 'other'
  )),
  handle TEXT,
  external_account_id TEXT,  -- Platform user/page/channel ID
  display_name TEXT,
  status TEXT NOT NULL CHECK (status IN ('connected', 'needs_reauth', 'disconnected', 'error')),
  
  -- OAuth/Token data (encrypt in production)
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMPTZ,
  scopes TEXT[],
  
  metadata JSONB DEFAULT '{}',
  last_sync_at TIMESTAMPTZ,
  last_error TEXT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_social_accounts_workspace ON social_accounts(workspace_id);
CREATE INDEX idx_social_accounts_platform ON social_accounts(platform);
CREATE UNIQUE INDEX idx_social_accounts_platform_external 
  ON social_accounts(platform, external_account_id) 
  WHERE external_account_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 3. CONTENT ITEMS (Canonical content across platforms)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS content_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  slug TEXT UNIQUE,
  type TEXT NOT NULL CHECK (type IN ('video', 'image', 'carousel', 'article', 'audio', 'other')),
  
  title TEXT,
  description TEXT,
  
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_content_items_workspace ON content_items(workspace_id);
CREATE INDEX idx_content_items_type ON content_items(type);
CREATE INDEX idx_content_items_created ON content_items(created_at DESC);

-- ----------------------------------------------------------------------------
-- 4. VIDEOS (Extends existing videos table or creates if missing)
-- ----------------------------------------------------------------------------

-- Check if videos table exists and add missing columns
DO $$
BEGIN
  -- Add workspace_id if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'videos' AND column_name = 'workspace_id'
  ) THEN
    ALTER TABLE videos ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;
  END IF;
  
  -- Add content_item_id if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'videos' AND column_name = 'content_item_id'
  ) THEN
    ALTER TABLE videos ADD COLUMN content_item_id UUID REFERENCES content_items(id) ON DELETE SET NULL;
  END IF;
  
  -- Add uploaded_by if it doesn't exist
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'videos' AND column_name = 'uploaded_by'
  ) THEN
    ALTER TABLE videos ADD COLUMN uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL;
  END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_videos_workspace ON videos(workspace_id);
CREATE INDEX IF NOT EXISTS idx_videos_content_item ON videos(content_item_id);

-- ----------------------------------------------------------------------------
-- 5. CLIPS (Time ranges from videos)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS clips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  content_item_id UUID REFERENCES content_items(id) ON DELETE SET NULL,
  
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  
  label TEXT,
  start_s NUMERIC NOT NULL CHECK (start_s >= 0),
  end_s NUMERIC NOT NULL CHECK (end_s > start_s),
  duration_s NUMERIC GENERATED ALWAYS AS (end_s - start_s) STORED,
  
  status TEXT NOT NULL CHECK (status IN ('draft', 'rendering', 'ready', 'error')) DEFAULT 'draft',
  error_message TEXT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_clips_workspace ON clips(workspace_id);
CREATE INDEX idx_clips_video ON clips(video_id);
CREATE INDEX idx_clips_status ON clips(status);

-- ----------------------------------------------------------------------------
-- 6. CLIP STYLES (Captions + headline overlays per platform)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS clip_styles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_id UUID NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
  
  platform TEXT CHECK (platform IN (
    'instagram', 'tiktok', 'youtube', 'facebook', 
    'twitter', 'linkedin', 'pinterest', 'other'
  )),
  aspect_ratio TEXT CHECK (aspect_ratio IN ('9:16', '16:9', '1:1', '4:5', '4:3')),
  
  -- Template
  template_id UUID,
  
  -- Captions
  captions_enabled BOOLEAN NOT NULL DEFAULT true,
  caption_style_preset TEXT,  -- 'Bold Pop', 'Clean Subtitle', 'Meme Block', etc.
  caption_font_family TEXT,
  caption_font_weight TEXT,
  caption_font_size TEXT,
  caption_color TEXT,
  caption_bg_mode TEXT CHECK (caption_bg_mode IN ('box', 'outline', 'highlight', 'none')),
  caption_position TEXT CHECK (caption_position IN ('top', 'middle', 'bottom')),
  caption_animation TEXT,  -- 'fade_in', 'pop', 'typewriter', 'karaoke'
  
  -- Keyword emphasis
  keyword_emphasis_enabled BOOLEAN DEFAULT false,
  keyword_emphasis_color TEXT,
  
  -- Persistent headline overlay
  headline_enabled BOOLEAN DEFAULT false,
  headline_text TEXT,
  headline_subtext TEXT,
  headline_position TEXT CHECK (headline_position IN (
    'top', 'bottom', 'top_left', 'top_right', 
    'bottom_left', 'bottom_right', 'middle_left', 'middle_right'
  )),
  headline_style JSONB DEFAULT '{}',  -- {font, color, bg, border_radius, padding}
  
  -- Safe zones
  safe_zone_overlay BOOLEAN DEFAULT true,
  
  -- Extra config
  extra JSONB DEFAULT '{}',
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_clip_styles_clip ON clip_styles(clip_id);
CREATE INDEX idx_clip_styles_platform ON clip_styles(platform);

-- ----------------------------------------------------------------------------
-- 7. POSTS (Scheduled/published content)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  
  -- Links to content
  clip_id UUID REFERENCES clips(id) ON DELETE SET NULL,
  content_item_id UUID REFERENCES content_items(id) ON DELETE SET NULL,
  social_account_id UUID REFERENCES social_accounts(id) ON DELETE SET NULL,
  
  platform TEXT NOT NULL,
  
  -- Scheduling
  scheduled_time TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  
  -- Status
  status TEXT NOT NULL CHECK (status IN (
    'draft', 'scheduled', 'publishing', 'published', 'failed', 'canceled'
  )) DEFAULT 'draft',
  
  -- Content
  title TEXT,
  caption TEXT,
  hashtags TEXT[],
  thumbnail_url TEXT,
  
  -- AI generations (references to ai_generations table when added)
  ai_title_generation_id UUID,
  ai_caption_generation_id UUID,
  
  -- Metadata
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_posts_workspace ON posts(workspace_id);
CREATE INDEX idx_posts_clip ON posts(clip_id);
CREATE INDEX idx_posts_account ON posts(social_account_id);
CREATE INDEX idx_posts_scheduled ON posts(scheduled_time);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_platform ON posts(platform);

-- ----------------------------------------------------------------------------
-- 8. POST PLATFORM PUBLISH (Actual platform IDs/URLs)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS post_platform_publish (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  
  external_post_id TEXT,  -- Platform's post ID
  permalink_url TEXT,     -- Direct URL to post
  
  published_at TIMESTAMPTZ,
  last_sync_at TIMESTAMPTZ,
  last_error TEXT,
  
  metadata JSONB DEFAULT '{}',
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_post_platform_publish_post ON post_platform_publish(post_id);
CREATE INDEX idx_post_platform_publish_external ON post_platform_publish(external_post_id);

-- ----------------------------------------------------------------------------
-- 9. UPDATED_AT TRIGGER
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_social_accounts_updated_at BEFORE UPDATE ON social_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_items_updated_at BEFORE UPDATE ON content_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clips_updated_at BEFORE UPDATE ON clips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clip_styles_updated_at BEFORE UPDATE ON clip_styles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 10. HELPFUL VIEWS
-- ----------------------------------------------------------------------------

-- View: Posts with full context
CREATE OR REPLACE VIEW posts_full AS
SELECT 
  p.*,
  c.label as clip_label,
  c.duration_s as clip_duration,
  v.file_name as video_filename,
  v.duration_sec as video_duration,
  sa.platform as account_platform,
  sa.handle as account_handle,
  ppp.external_post_id,
  ppp.permalink_url,
  w.name as workspace_name
FROM posts p
LEFT JOIN clips c ON p.clip_id = c.id
LEFT JOIN videos v ON c.video_id = v.id
LEFT JOIN social_accounts sa ON p.social_account_id = sa.id
LEFT JOIN post_platform_publish ppp ON p.id = ppp.post_id
LEFT JOIN workspaces w ON p.workspace_id = w.id;

-- View: Clips with video context
CREATE OR REPLACE VIEW clips_full AS
SELECT 
  c.*,
  v.file_name as video_filename,
  v.duration_sec as video_duration,
  v.source_uri as video_source_uri,
  w.name as workspace_name,
  COUNT(p.id) as post_count
FROM clips c
LEFT JOIN videos v ON c.video_id = v.id
LEFT JOIN workspaces w ON c.workspace_id = w.id
LEFT JOIN posts p ON c.id = p.clip_id
GROUP BY c.id, v.id, w.id;

-- ----------------------------------------------------------------------------
-- SUCCESS MESSAGE
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    RAISE NOTICE '╔════════════════════════════════════════════════╗';
    RAISE NOTICE '║  PHASE 1 ESSENTIALS INSTALLED! ✅              ║';
    RAISE NOTICE '╚════════════════════════════════════════════════╝';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables Created:';
    RAISE NOTICE '  ✓ workspaces';
    RAISE NOTICE '  ✓ users';
    RAISE NOTICE '  ✓ workspace_members';
    RAISE NOTICE '  ✓ social_accounts';
    RAISE NOTICE '  ✓ content_items';
    RAISE NOTICE '  ✓ videos (enhanced)';
    RAISE NOTICE '  ✓ clips';
    RAISE NOTICE '  ✓ clip_styles';
    RAISE NOTICE '  ✓ posts';
    RAISE NOTICE '  ✓ post_platform_publish';
    RAISE NOTICE '';
    RAISE NOTICE 'Views Created:';
    RAISE NOTICE '  ✓ posts_full';
    RAISE NOTICE '  ✓ clips_full';
    RAISE NOTICE '';
    RAISE NOTICE 'Next: Run add_comprehensive_viral_schema.sql';
    RAISE NOTICE 'for viral analysis capabilities!';
END $$;

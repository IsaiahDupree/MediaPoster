-- Video Orchestrator Schema
-- Supports Sora-first video generation with Director/SceneCrafter/Assessor workflow

-- 0) Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Enums
DO $$ BEGIN
  CREATE TYPE video_provider_name AS ENUM ('sora', 'runway', 'kling', 'pika', 'luma', 'mock');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE clip_run_status AS ENUM ('queued', 'running', 'succeeded', 'failed', 'canceled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE assessment_verdict AS ENUM ('pass', 'fail', 'needs_review');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE orchestrator_role AS ENUM ('content_brief', 'director', 'scene_crafter', 'assessor');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE clip_state AS ENUM ('pending', 'generating', 'passed', 'failed', 'skipped');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE plan_status AS ENUM ('draft', 'ready', 'running', 'completed', 'failed', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE render_status AS ENUM ('queued', 'running', 'succeeded', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE bible_kind AS ENUM ('style', 'character', 'continuity');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 2) Video Projects (top-level container)
CREATE TABLE IF NOT EXISTS video_projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID, -- references auth.users if using Supabase auth
  title TEXT NOT NULL,
  description TEXT,
  tags TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3) Bibles (style, character, continuity rules)
CREATE TABLE IF NOT EXISTS video_bibles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
  kind bible_kind NOT NULL,
  name TEXT NOT NULL,
  body JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4) Content Briefs
CREATE TABLE IF NOT EXISTS video_content_briefs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
  objective TEXT NOT NULL,
  audience TEXT NOT NULL,
  tone TEXT,
  cta TEXT,
  key_points TEXT[] NOT NULL DEFAULT '{}',
  safety JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5) Scripts
CREATE TABLE IF NOT EXISTS video_scripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
  brief_id UUID REFERENCES video_content_briefs(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6) Clip Plans (orchestration plan)
CREATE TABLE IF NOT EXISTS video_clip_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
  brief_id UUID REFERENCES video_content_briefs(id) ON DELETE SET NULL,
  script_id UUID REFERENCES video_scripts(id) ON DELETE SET NULL,
  
  style_bible_id UUID REFERENCES video_bibles(id) ON DELETE SET NULL,
  character_bible_id UUID REFERENCES video_bibles(id) ON DELETE SET NULL,
  continuity_bible_id UUID REFERENCES video_bibles(id) ON DELETE SET NULL,
  
  version TEXT NOT NULL DEFAULT '1.0.0',
  constraints JSONB NOT NULL DEFAULT '{}'::jsonb,
  plan_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status plan_status NOT NULL DEFAULT 'draft',
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7) Scenes (containers within clip plans)
CREATE TABLE IF NOT EXISTS video_scenes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_plan_id UUID NOT NULL REFERENCES video_clip_plans(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  goal TEXT,
  beats TEXT[] NOT NULL DEFAULT '{}',
  scene_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8) Clip Plan Clips (individual clip definitions)
CREATE TABLE IF NOT EXISTS video_clip_plan_clips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scene_id UUID NOT NULL REFERENCES video_scenes(id) ON DELETE CASCADE,
  clip_order INT NOT NULL,
  
  target_seconds INT NOT NULL CHECK (target_seconds > 0 AND target_seconds <= 60),
  
  narration JSONB NOT NULL DEFAULT '{}'::jsonb,
  visual_intent JSONB NOT NULL DEFAULT '{}'::jsonb,
  provider_hints JSONB NOT NULL DEFAULT '{}'::jsonb,
  acceptance JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  state clip_state NOT NULL DEFAULT 'pending',
  provider_override video_provider_name,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9) Clip Runs (provider generation attempts)
CREATE TABLE IF NOT EXISTS video_clip_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_plan_clip_id UUID NOT NULL REFERENCES video_clip_plan_clips(id) ON DELETE CASCADE,
  
  provider video_provider_name NOT NULL,
  provider_generation_id TEXT NOT NULL,
  
  attempt INT NOT NULL DEFAULT 1,
  status clip_run_status NOT NULL DEFAULT 'queued',
  
  request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  error TEXT,
  duration_actual FLOAT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  UNIQUE (clip_plan_clip_id, attempt)
);

-- 10) Video Assets (stored files)
CREATE TABLE IF NOT EXISTS video_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('video_mp4', 'image_png', 'image_jpg', 'json', 'text', 'audio_wav', 'audio_mp3')),
  url TEXT NOT NULL,
  content_type TEXT,
  bytes BIGINT,
  sha256 TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11) Clip Run Assets (link runs to assets)
CREATE TABLE IF NOT EXISTS video_clip_run_assets (
  clip_run_id UUID NOT NULL REFERENCES video_clip_runs(id) ON DELETE CASCADE,
  asset_id UUID NOT NULL REFERENCES video_assets(id) ON DELETE CASCADE,
  PRIMARY KEY (clip_run_id, asset_id)
);

-- 12) Assessments
CREATE TABLE IF NOT EXISTS video_assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_run_id UUID NOT NULL REFERENCES video_clip_runs(id) ON DELETE CASCADE,
  assessor_role orchestrator_role NOT NULL DEFAULT 'assessor',
  
  verdict assessment_verdict NOT NULL,
  score NUMERIC NOT NULL CHECK (score >= 0 AND score <= 1),
  reasons TEXT[] NOT NULL DEFAULT '{}',
  breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
  repair_instruction JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13) Repair Attempts
CREATE TABLE IF NOT EXISTS video_repair_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_plan_clip_id UUID NOT NULL REFERENCES video_clip_plan_clips(id) ON DELETE CASCADE,
  from_clip_run_id UUID REFERENCES video_clip_runs(id) ON DELETE SET NULL,
  strategy TEXT NOT NULL CHECK (strategy IN ('prompt_patch', 'remix', 'fallback_provider')),
  prompt_delta TEXT,
  fallback_provider video_provider_name,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14) Final Renders (assembled timeline outputs)
CREATE TABLE IF NOT EXISTS video_renders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_plan_id UUID NOT NULL REFERENCES video_clip_plans(id) ON DELETE CASCADE,
  status render_status NOT NULL DEFAULT 'queued',
  output_asset_id UUID REFERENCES video_assets(id) ON DELETE SET NULL,
  timeline_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  error TEXT,
  duration_seconds FLOAT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15) Indexes for performance
CREATE INDEX IF NOT EXISTS idx_video_clip_plan_clips_scene_order ON video_clip_plan_clips(scene_id, clip_order);
CREATE INDEX IF NOT EXISTS idx_video_clip_runs_clip_attempt ON video_clip_runs(clip_plan_clip_id, attempt);
CREATE INDEX IF NOT EXISTS idx_video_assessments_clip_run ON video_assessments(clip_run_id);
CREATE INDEX IF NOT EXISTS idx_video_assets_project_kind ON video_assets(project_id, kind);
CREATE INDEX IF NOT EXISTS idx_video_scenes_plan_order ON video_scenes(clip_plan_id, scene_order);
CREATE INDEX IF NOT EXISTS idx_video_clip_plans_project ON video_clip_plans(project_id);
CREATE INDEX IF NOT EXISTS idx_video_bibles_project_kind ON video_bibles(project_id, kind);

-- 16) Updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

DO $$ BEGIN
  CREATE TRIGGER update_video_projects_updated_at BEFORE UPDATE ON video_projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER update_video_bibles_updated_at BEFORE UPDATE ON video_bibles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER update_video_content_briefs_updated_at BEFORE UPDATE ON video_content_briefs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER update_video_scripts_updated_at BEFORE UPDATE ON video_scripts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER update_video_clip_plans_updated_at BEFORE UPDATE ON video_clip_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER update_video_clip_plan_clips_updated_at BEFORE UPDATE ON video_clip_plan_clips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER update_video_clip_runs_updated_at BEFORE UPDATE ON video_clip_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER update_video_renders_updated_at BEFORE UPDATE ON video_renders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

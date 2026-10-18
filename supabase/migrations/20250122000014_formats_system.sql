-- Migration: Formats System for Clips Studio
-- Parameterized, renderable video formats that can be re-generated on demand with fresh data

-- ============================================================================
-- QUALITY PROFILES TABLE - Baseline quality rules (MUST BE CREATED FIRST)
-- ============================================================================
CREATE TABLE IF NOT EXISTS quality_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    
    -- Gate rules JSON array
    gates_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Settings
    is_default BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FORMATS TABLE - The blueprint/template definition
-- ============================================================================
CREATE TABLE IF NOT EXISTS formats (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    version TEXT NOT NULL DEFAULT '1.0.0',
    
    -- The full format definition JSON (composition, bindings, data sources, etc.)
    definition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Quick access fields (denormalized from definition_json)
    remotion_composition_id TEXT,
    quality_profile_id TEXT REFERENCES quality_profiles(id),
    
    -- Metadata
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FORMAT RUNS TABLE - Each execution of a format
-- ============================================================================
CREATE TABLE IF NOT EXISTS format_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    format_id TEXT NOT NULL REFERENCES formats(id) ON DELETE CASCADE,
    
    -- Run status tracking
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'failed', 'succeeded', 'published')),
    
    -- Trigger information
    trigger_type TEXT NOT NULL DEFAULT 'manual' CHECK (trigger_type IN ('manual', 'schedule', 'webhook', 'event')),
    triggered_by TEXT,
    
    -- Parameters and resolved data (for reproducibility)
    params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_inputs_json JSONB,
    render_props_json JSONB,
    
    -- Variant selection
    variant_id TEXT,
    
    -- Error tracking
    error_json JSONB,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- RUN ARTIFACTS TABLE - Generated files from each run
-- ============================================================================
CREATE TABLE IF NOT EXISTS run_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES format_runs(id) ON DELETE CASCADE,
    
    -- Artifact type: voice, music, timeline, captions, video, thumbnail, logs
    kind TEXT NOT NULL,
    
    -- Location and metadata
    url TEXT NOT NULL,
    file_path TEXT,
    file_size_bytes BIGINT,
    duration_sec NUMERIC(10, 3),
    
    -- Additional metadata
    meta JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FORMAT TRIGGERS TABLE - Scheduled/event-based triggers
-- ============================================================================
CREATE TABLE IF NOT EXISTS format_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    format_id TEXT NOT NULL REFERENCES formats(id) ON DELETE CASCADE,
    
    -- Trigger type
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('schedule', 'event', 'webhook')),
    
    -- Configuration
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- For scheduled triggers
    cron_expression TEXT,
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    
    -- Status
    enabled BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_formats_status ON formats(status);
CREATE INDEX IF NOT EXISTS idx_format_runs_format_id ON format_runs(format_id);
CREATE INDEX IF NOT EXISTS idx_format_runs_status ON format_runs(status);
CREATE INDEX IF NOT EXISTS idx_format_runs_created_at ON format_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_run_artifacts_run_id ON run_artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_run_artifacts_kind ON run_artifacts(kind);
CREATE INDEX IF NOT EXISTS idx_format_triggers_format_id ON format_triggers(format_id);
CREATE INDEX IF NOT EXISTS idx_format_triggers_next_run ON format_triggers(next_run_at) WHERE enabled = TRUE;

-- ============================================================================
-- DEFAULT QUALITY PROFILE
-- ============================================================================
INSERT INTO quality_profiles (id, name, description, gates_json, is_default)
VALUES (
    'qp_shortform_v1',
    'Short-Form Video Quality',
    'Quality gates for TikTok, Reels, and Shorts (under 60s)',
    '[
        {"id": "req_fields", "type": "required_fields", "level": "fail", "config": {"paths": ["topic", "script.segments"]}},
        {"id": "dur_60", "type": "duration", "level": "fail", "config": {"maxSec": 60}},
        {"id": "cap_len", "type": "captions", "level": "warn", "config": {"maxCharsPerLine": 44}},
        {"id": "voice_required", "type": "audio", "level": "fail", "config": {"requireVoice": true}},
        {"id": "visual_density", "type": "visual", "level": "warn", "config": {"maxOnScreenWords": 12}},
        {"id": "hook_timing", "type": "duration", "level": "warn", "config": {"hookMustAppearBySec": 1.5}}
    ]'::jsonb,
    TRUE
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE formats IS 'Video format blueprints that can be regenerated with fresh data';
COMMENT ON TABLE format_runs IS 'Execution history for each format run';
COMMENT ON TABLE run_artifacts IS 'Generated artifacts (voice, video, captions, etc.) from format runs';
COMMENT ON TABLE quality_profiles IS 'Quality gate profiles for video validation';
COMMENT ON TABLE format_triggers IS 'Scheduled and event-based triggers for format runs';

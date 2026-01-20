-- Migration: Character Assets and Variants (CHAR-001)
-- Description: Add tables for AI-generated character management
-- Date: 2026-01-20

-- Character Assets table
CREATE TABLE IF NOT EXISTS character_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Character identity
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    style VARCHAR(50) NOT NULL,
    base_expression VARCHAR(50) DEFAULT 'neutral',

    -- File information
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    checksum VARCHAR(64),
    image_url TEXT,

    -- Generation metadata
    original_prompt TEXT,
    revised_prompt TEXT,
    generation_params JSONB DEFAULT '{}',

    -- Character properties (CHAR-002, CHAR-003, CHAR-004)
    has_transparent_background BOOLEAN DEFAULT FALSE,
    has_body_layer BOOLEAN DEFAULT FALSE,
    has_mouth_layer BOOLEAN DEFAULT FALSE,
    body_layer_path TEXT,
    mouth_layer_path TEXT,

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Character Variants table
CREATE TABLE IF NOT EXISTS character_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES character_assets(id) ON DELETE CASCADE,

    -- Variant details
    expression VARCHAR(50) NOT NULL,

    -- File information
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    image_url TEXT,

    -- Generation metadata
    prompt TEXT,
    revised_prompt TEXT,
    generation_params JSONB DEFAULT '{}',

    -- Variant properties (CHAR-004)
    has_transparent_background BOOLEAN DEFAULT FALSE,
    has_body_layer BOOLEAN DEFAULT FALSE,
    has_mouth_layer BOOLEAN DEFAULT FALSE,
    body_layer_path TEXT,
    mouth_layer_path TEXT,

    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_character_assets_workspace_id ON character_assets(workspace_id);
CREATE INDEX IF NOT EXISTS idx_character_assets_style ON character_assets(style);
CREATE INDEX IF NOT EXISTS idx_character_assets_checksum ON character_assets(checksum);

CREATE INDEX IF NOT EXISTS idx_character_variants_character_id ON character_variants(character_id);
CREATE INDEX IF NOT EXISTS idx_character_variants_expression ON character_variants(expression);

-- Updated_at trigger for character_assets
CREATE OR REPLACE FUNCTION update_character_assets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_character_assets_updated_at
    BEFORE UPDATE ON character_assets
    FOR EACH ROW
    EXECUTE FUNCTION update_character_assets_updated_at();

-- Updated_at trigger for character_variants
CREATE OR REPLACE FUNCTION update_character_variants_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_character_variants_updated_at
    BEFORE UPDATE ON character_variants
    FOR EACH ROW
    EXECUTE FUNCTION update_character_variants_updated_at();

-- Comments
COMMENT ON TABLE character_assets IS 'AI-generated character assets (CHAR-001)';
COMMENT ON TABLE character_variants IS 'Character expression variants for consistent characters';
COMMENT ON COLUMN character_assets.has_transparent_background IS 'CHAR-002: Background removal applied';
COMMENT ON COLUMN character_assets.has_body_layer IS 'CHAR-004: Separate body layer available';
COMMENT ON COLUMN character_assets.has_mouth_layer IS 'CHAR-004: Separate mouth layer for lip-sync';

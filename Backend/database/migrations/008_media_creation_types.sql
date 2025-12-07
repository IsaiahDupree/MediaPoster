-- Media Creation Types Schema
-- Supports various content creation formats: blog, video, carousel, AI-generated, etc.

-- Content Types Enum
CREATE TYPE content_type_enum AS ENUM (
    'blog_post',
    'video',
    'carousel',
    'ai_generated_carousel',
    'ai_generated_video',
    'words_on_video',
    'broll_with_text',
    'image',
    'reel',
    'story',
    'live_stream'
);

-- Media Creation Templates
CREATE TABLE IF NOT EXISTS media_creation_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Template Info
    template_name VARCHAR(200) NOT NULL,
    content_type content_type_enum NOT NULL,
    description TEXT,
    
    -- Template Configuration
    template_config JSONB NOT NULL DEFAULT '{}',  -- Type-specific settings
    ai_provider VARCHAR(50),  -- 'openai', 'anthropic', 'stability', 'runway', etc.
    ai_model VARCHAR(100),    -- Specific model name
    
    -- Visual Settings
    theme VARCHAR(100),        -- 'minimal', 'bold', 'elegant', etc.
    color_scheme JSONB,        -- Primary/secondary colors
    font_family VARCHAR(100),
    
    -- Content Settings
    default_duration INTEGER,  -- For video types (seconds)
    aspect_ratio VARCHAR(20),  -- '9:16', '16:9', '1:1', '4:5'
    resolution VARCHAR(20),     -- '1080x1920', '1920x1080', etc.
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT FALSE,  -- Shareable templates
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_templates_content_type ON media_creation_templates(content_type);
CREATE INDEX idx_templates_user ON media_creation_templates(user_id);

-- Media Creation Projects
CREATE TABLE IF NOT EXISTS media_creation_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Project Info
    project_name VARCHAR(200) NOT NULL,
    content_type content_type_enum NOT NULL,
    template_id UUID REFERENCES media_creation_templates(id),
    
    -- Content Data
    content_data JSONB NOT NULL DEFAULT '{}',  -- Type-specific content
    -- For blog: {title, body, images, etc.}
    -- For carousel: {slides: [{image, text, order}], etc.}
    -- For words_on_video: {video_url, text_overlays: [{text, position, timing}], etc.}
    -- For AI-generated: {prompt, style, parameters, etc.}
    
    -- Media Assets
    source_video_id UUID REFERENCES videos(id),
    source_images JSONB,  -- Array of image URLs/IDs
    generated_media_url TEXT,  -- For AI-generated content
    thumbnail_url TEXT,
    
    -- Editing State
    editing_state JSONB,  -- Current editing progress
    is_draft BOOLEAN DEFAULT TRUE,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',  -- draft, editing, ready, published
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_projects_content_type ON media_creation_projects(content_type);
CREATE INDEX idx_projects_user ON media_creation_projects(user_id);
CREATE INDEX idx_projects_status ON media_creation_projects(status);

-- Media Creation Assets
CREATE TABLE IF NOT EXISTS media_creation_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES media_creation_projects(id) ON DELETE CASCADE,
    
    -- Asset Info
    asset_type VARCHAR(50) NOT NULL,  -- 'image', 'video', 'audio', 'text', 'ai_generated'
    asset_url TEXT NOT NULL,
    asset_path TEXT,  -- Local file path if applicable
    
    -- Metadata (renamed to asset_metadata to avoid SQLAlchemy reserved word conflict)
    asset_metadata JSONB DEFAULT '{}',  -- Dimensions, duration, file size, etc.
    order_index INTEGER,  -- For ordered assets (carousel slides)
    
    -- AI Generation Info (if applicable)
    ai_provider VARCHAR(50),
    ai_model VARCHAR(100),
    generation_prompt TEXT,
    generation_params JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assets_project ON media_creation_assets(project_id);
CREATE INDEX idx_assets_type ON media_creation_assets(asset_type);

-- Link projects to scheduled posts
ALTER TABLE scheduled_posts 
ADD COLUMN IF NOT EXISTS media_project_id UUID REFERENCES media_creation_projects(id);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_media_project ON scheduled_posts(media_project_id);


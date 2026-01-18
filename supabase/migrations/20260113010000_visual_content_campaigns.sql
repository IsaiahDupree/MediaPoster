-- Visual Content Campaign System
-- Instagram Carousels & TikTok Picture Music Videos
-- Uses same 5 awareness stages and content types as Twitter

-- =============================================================================
-- CONTENT FORMATS
-- =============================================================================
CREATE TYPE content_format AS ENUM (
    'instagram_carousel',    -- 2-10 slide carousels
    'tiktok_picture_video',  -- Picture + music videos
    'instagram_reel',        -- Short video reels
    'tiktok_video'           -- Standard TikTok videos
);

-- =============================================================================
-- VISUAL TEMPLATES - Frameworks inspired by @personalbrandlaunch
-- =============================================================================
CREATE TABLE IF NOT EXISTS visual_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    format content_format NOT NULL,
    template_type TEXT NOT NULL, -- 'listicle', 'before_after', 'step_by_step', 'quote', 'problem_solution', 'story_arc'
    
    -- Structure
    slide_count INTEGER DEFAULT 5,
    structure_json JSONB NOT NULL, -- Slide-by-slide structure
    
    -- Styling
    color_scheme JSONB DEFAULT '{"primary": "#000000", "secondary": "#ffffff", "accent": "#6366f1"}',
    font_config JSONB DEFAULT '{"heading": "Inter Bold", "body": "Inter Regular"}',
    animation_preset TEXT DEFAULT 'fade', -- 'fade', 'slide', 'zoom', 'bounce'
    
    -- Music (for TikTok)
    music_mood TEXT, -- 'upbeat', 'chill', 'dramatic', 'inspiring'
    music_bpm_range JSONB DEFAULT '{"min": 100, "max": 130}',
    
    -- Performance
    avg_engagement_rate FLOAT DEFAULT 0,
    times_used INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SCHEDULED VISUAL CONTENT
-- =============================================================================
CREATE TABLE IF NOT EXISTS scheduled_visual_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    template_id UUID REFERENCES visual_templates(id) ON DELETE SET NULL,
    
    -- Content details
    format content_format NOT NULL,
    awareness_stage awareness_stage NOT NULL,
    content_type TEXT NOT NULL, -- hook, authority, story, emotional, cta
    
    -- Generated content
    title TEXT NOT NULL,
    hook_text TEXT, -- Opening hook
    slides_json JSONB NOT NULL, -- Array of slide content
    caption TEXT NOT NULL,
    hashtags TEXT[],
    
    -- Media files
    rendered_media_urls TEXT[], -- Carousel images or video URL
    music_track_url TEXT, -- For TikTok
    thumbnail_url TEXT,
    
    -- Remotion render
    remotion_job_id TEXT,
    render_status TEXT DEFAULT 'pending', -- pending, rendering, completed, failed
    
    -- Scheduling
    scheduled_time TIMESTAMPTZ NOT NULL,
    platform TEXT NOT NULL, -- 'instagram', 'tiktok'
    blotato_account_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, rendering, scheduled, publishing, posted, failed
    
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- POSTED VISUAL CONTENT
-- =============================================================================
CREATE TABLE IF NOT EXISTS posted_visual_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheduled_content_id UUID REFERENCES scheduled_visual_content(id) ON DELETE SET NULL,
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    template_id UUID REFERENCES visual_templates(id) ON DELETE SET NULL,
    
    -- Content details
    format content_format NOT NULL,
    awareness_stage awareness_stage NOT NULL,
    content_type TEXT NOT NULL,
    title TEXT NOT NULL,
    caption TEXT NOT NULL,
    slides_json JSONB,
    
    -- Platform tracking
    platform TEXT NOT NULL,
    platform_post_id TEXT,
    platform_url TEXT,
    blotato_account_id TEXT,
    blotato_submission_id TEXT,
    
    -- Media
    rendered_media_urls TEXT[],
    thumbnail_url TEXT,
    
    -- Timestamps
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Analytics
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    video_views INTEGER DEFAULT 0,
    video_completion_rate FLOAT DEFAULT 0,
    
    -- Calculated
    engagement_rate FLOAT DEFAULT 0,
    performance_score FLOAT DEFAULT 0,
    
    -- Check-back tracking
    last_analytics_check TIMESTAMPTZ,
    analytics_check_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- VISUAL CAMPAIGN CYCLES
-- =============================================================================
CREATE TABLE IF NOT EXISTS visual_campaign_cycles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    platform TEXT NOT NULL, -- 'instagram', 'tiktok'
    
    current_awareness_stage awareness_stage DEFAULT 'unaware',
    current_content_type TEXT DEFAULT 'hook',
    current_template_idx INTEGER DEFAULT 0,
    
    stage_content_count INTEGER DEFAULT 0,
    type_content_count INTEGER DEFAULT 0,
    total_content_today INTEGER DEFAULT 0,
    
    last_post_at TIMESTAMPTZ,
    last_stage_rotation TIMESTAMPTZ,
    last_type_rotation TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id, platform)
);

-- =============================================================================
-- MUSIC LIBRARY (for TikTok videos)
-- =============================================================================
CREATE TABLE IF NOT EXISTS content_music_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    artist TEXT,
    mood TEXT NOT NULL, -- upbeat, chill, dramatic, inspiring, energetic
    bpm INTEGER,
    duration_seconds FLOAT,
    
    -- File
    file_url TEXT NOT NULL,
    preview_url TEXT,
    
    -- Usage
    is_royalty_free BOOLEAN DEFAULT TRUE,
    source TEXT, -- 'epidemic_sound', 'artlist', 'custom', 'trending'
    trending_on TEXT[], -- ['tiktok', 'instagram']
    
    -- Performance
    times_used INTEGER DEFAULT 0,
    avg_video_completion_rate FLOAT DEFAULT 0,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_scheduled_visual_time ON scheduled_visual_content(scheduled_time) WHERE status IN ('pending', 'scheduled');
CREATE INDEX IF NOT EXISTS idx_scheduled_visual_platform ON scheduled_visual_content(platform, status);
CREATE INDEX IF NOT EXISTS idx_posted_visual_platform ON posted_visual_content(platform);
CREATE INDEX IF NOT EXISTS idx_posted_visual_posted_at ON posted_visual_content(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_visual_templates_format ON visual_templates(format);

-- =============================================================================
-- SEED VISUAL TEMPLATES - PersonalBrandLaunch-inspired frameworks
-- =============================================================================
INSERT INTO visual_templates (name, format, template_type, slide_count, structure_json, animation_preset, music_mood)
VALUES
-- Instagram Carousel Templates
(
    'Listicle Carousel',
    'instagram_carousel',
    'listicle',
    7,
    '{
        "slides": [
            {"type": "hook", "layout": "centered_text", "content": "{{count}} {{topic}} that will {{benefit}}"},
            {"type": "item", "layout": "number_title_description", "number": 1},
            {"type": "item", "layout": "number_title_description", "number": 2},
            {"type": "item", "layout": "number_title_description", "number": 3},
            {"type": "item", "layout": "number_title_description", "number": 4},
            {"type": "item", "layout": "number_title_description", "number": 5},
            {"type": "cta", "layout": "centered_cta", "content": "Save this for later! Follow @{{username}} for more"}
        ]
    }',
    'slide',
    NULL
),
(
    'Problem → Solution Carousel',
    'instagram_carousel',
    'problem_solution',
    5,
    '{
        "slides": [
            {"type": "hook", "layout": "question", "content": "Still struggling with {{problem}}?"},
            {"type": "problem", "layout": "pain_points", "content": "The real issue is..."},
            {"type": "bridge", "layout": "transition", "content": "But what if you could..."},
            {"type": "solution", "layout": "benefits", "content": "Introducing {{product}}"},
            {"type": "cta", "layout": "action", "content": "Try it free → Link in bio"}
        ]
    }',
    'fade',
    NULL
),
(
    'Before/After Carousel',
    'instagram_carousel',
    'before_after',
    4,
    '{
        "slides": [
            {"type": "hook", "layout": "contrast_title", "content": "{{topic}}: Before vs After"},
            {"type": "before", "layout": "pain_state", "content": "Before: {{pain_points}}"},
            {"type": "after", "layout": "benefit_state", "content": "After: {{benefits}}"},
            {"type": "cta", "layout": "transformation_cta", "content": "Ready for your transformation?"}
        ]
    }',
    'slide',
    NULL
),
(
    'Step-by-Step Guide',
    'instagram_carousel',
    'step_by_step',
    6,
    '{
        "slides": [
            {"type": "hook", "layout": "how_to", "content": "How to {{achieve_goal}} in {{timeframe}}"},
            {"type": "step", "layout": "step_card", "number": 1, "content": "{{step_1}}"},
            {"type": "step", "layout": "step_card", "number": 2, "content": "{{step_2}}"},
            {"type": "step", "layout": "step_card", "number": 3, "content": "{{step_3}}"},
            {"type": "step", "layout": "step_card", "number": 4, "content": "{{step_4}}"},
            {"type": "cta", "layout": "result_cta", "content": "Follow for more tips!"}
        ]
    }',
    'slide',
    NULL
),
(
    'Quote/Insight Carousel',
    'instagram_carousel',
    'quote',
    3,
    '{
        "slides": [
            {"type": "hook", "layout": "bold_statement", "content": "{{contrarian_take}}"},
            {"type": "explanation", "layout": "supporting_points", "content": "Here''s why..."},
            {"type": "cta", "layout": "engage_cta", "content": "Agree? Drop a 🔥 below"}
        ]
    }',
    'zoom',
    NULL
),

-- TikTok Picture Video Templates
(
    'Listicle Picture Video',
    'tiktok_picture_video',
    'listicle',
    7,
    '{
        "slides": [
            {"type": "hook", "duration": 2, "layout": "bold_text", "content": "{{count}} things you NEED to know"},
            {"type": "item", "duration": 3, "layout": "number_reveal", "number": 1},
            {"type": "item", "duration": 3, "layout": "number_reveal", "number": 2},
            {"type": "item", "duration": 3, "layout": "number_reveal", "number": 3},
            {"type": "item", "duration": 3, "layout": "number_reveal", "number": 4},
            {"type": "item", "duration": 3, "layout": "number_reveal", "number": 5},
            {"type": "cta", "duration": 2, "layout": "follow_cta", "content": "Follow for Part 2!"}
        ],
        "total_duration": 19
    }',
    'bounce',
    'upbeat'
),
(
    'Story Arc Video',
    'tiktok_picture_video',
    'story_arc',
    5,
    '{
        "slides": [
            {"type": "hook", "duration": 3, "layout": "attention_grab", "content": "I was {{struggle}}..."},
            {"type": "struggle", "duration": 4, "layout": "pain_visual", "content": "Until I discovered..."},
            {"type": "discovery", "duration": 4, "layout": "reveal", "content": "{{product}} changed everything"},
            {"type": "result", "duration": 4, "layout": "transformation", "content": "Now I {{benefit}}"},
            {"type": "cta", "duration": 2, "layout": "action_cta", "content": "Link in bio to try it"}
        ],
        "total_duration": 17
    }',
    'fade',
    'inspiring'
),
(
    'Quick Tips Video',
    'tiktok_picture_video',
    'step_by_step',
    5,
    '{
        "slides": [
            {"type": "hook", "duration": 2, "layout": "quick_hook", "content": "{{topic}} hack that actually works:"},
            {"type": "tip", "duration": 4, "layout": "tip_card", "number": 1},
            {"type": "tip", "duration": 4, "layout": "tip_card", "number": 2},
            {"type": "tip", "duration": 4, "layout": "tip_card", "number": 3},
            {"type": "cta", "duration": 2, "layout": "save_cta", "content": "Save this! More on my page"}
        ],
        "total_duration": 16
    }',
    'slide',
    'energetic'
)
ON CONFLICT DO NOTHING;

-- Initialize visual campaign cycles for existing products
INSERT INTO visual_campaign_cycles (product_id, platform)
SELECT id, 'instagram' FROM campaign_products
ON CONFLICT (product_id, platform) DO NOTHING;

INSERT INTO visual_campaign_cycles (product_id, platform)
SELECT id, 'tiktok' FROM campaign_products
ON CONFLICT (product_id, platform) DO NOTHING;

-- =============================================================================
-- UPDATE TRIGGERS
-- =============================================================================
CREATE TRIGGER update_visual_templates_timestamp
    BEFORE UPDATE ON visual_templates
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

CREATE TRIGGER update_scheduled_visual_content_timestamp
    BEFORE UPDATE ON scheduled_visual_content
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

CREATE TRIGGER update_posted_visual_content_timestamp
    BEFORE UPDATE ON posted_visual_content
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

CREATE TRIGGER update_visual_campaign_cycles_timestamp
    BEFORE UPDATE ON visual_campaign_cycles
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

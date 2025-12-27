-- Competitor Audit System Schema
-- Comprehensive competitor/influencer analysis with multi-tier data collection
-- Supports: public data, authorized metrics, AI-inferred insights

-- =============================================================================
-- CORE: Competitor Account
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_account (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Platform identity
    platform TEXT NOT NULL,  -- instagram, tiktok, youtube, x, linkedin, threads
    handle TEXT NOT NULL,
    profile_url TEXT,
    platform_user_id TEXT,  -- Platform's internal ID if available
    
    -- Profile data
    display_name TEXT,
    bio_text TEXT,
    category TEXT,
    linkout_urls TEXT[],  -- Links in bio
    
    -- Profile assets
    avatar_url TEXT,
    banner_url TEXT,
    pinned_post_ids TEXT[],
    highlight_names TEXT[],  -- Instagram highlights, YouTube playlists, etc.
    
    -- Visible metrics (Tier A)
    follower_count INTEGER,
    following_count INTEGER,
    post_count INTEGER,
    
    -- Fetch tracking
    audit_run_id UUID,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    last_full_audit_at TIMESTAMPTZ,
    
    -- Raw platform response
    platform_raw_profile JSONB,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, handle)
);

CREATE INDEX idx_competitor_account_platform ON competitor_account(platform);
CREATE INDEX idx_competitor_account_handle ON competitor_account(handle);
CREATE INDEX idx_competitor_account_fetched ON competitor_account(fetched_at DESC);

-- =============================================================================
-- CORE: Competitor Posts
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_post (
    post_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES competitor_account(account_id) ON DELETE CASCADE,
    
    -- Post identity
    platform TEXT NOT NULL,
    platform_post_id TEXT NOT NULL,
    permalink TEXT,
    posted_at TIMESTAMPTZ,
    
    -- Content
    caption_text TEXT,
    hashtags TEXT[],
    mentions TEXT[],
    
    -- Media
    media_type TEXT,  -- video, image, carousel, text
    media_urls TEXT[],
    thumbnail_url TEXT,
    duration_sec FLOAT,
    
    -- Visible metrics (Tier A) - snapshot at fetch time
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    saves INTEGER,
    
    -- Audio info (for music tracking)
    audio_id TEXT,
    audio_title TEXT,
    audio_artist TEXT,
    is_original_audio BOOLEAN,
    
    -- OCR / detected text
    ocr_text TEXT,
    on_screen_text_detected TEXT[],
    
    -- Fetch tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Raw platform response
    platform_raw_post JSONB,
    
    -- Metadata
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, platform_post_id)
);

CREATE INDEX idx_competitor_post_account ON competitor_post(account_id);
CREATE INDEX idx_competitor_post_posted ON competitor_post(posted_at DESC);
CREATE INDEX idx_competitor_post_views ON competitor_post(views DESC);

-- =============================================================================
-- METRICS: Post Snapshots (for velocity/decay tracking)
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_post_snapshot (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES competitor_post(post_id) ON DELETE CASCADE,
    
    -- Timing
    sampled_at TIMESTAMPTZ DEFAULT NOW(),
    window_label TEXT,  -- 'T+1h', 'T+24h', 'T+7d', etc.
    hours_since_post FLOAT,
    
    -- Visible metrics at this point
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    saves INTEGER,
    
    -- Derived metrics
    velocity_views_per_hour FLOAT,
    engagement_rate FLOAT,  -- (likes+comments+shares)/views
    
    -- Change from previous snapshot
    delta_views INTEGER,
    delta_likes INTEGER,
    delta_comments INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_snapshot_post ON competitor_post_snapshot(post_id);
CREATE INDEX idx_competitor_snapshot_sampled ON competitor_post_snapshot(sampled_at DESC);

-- =============================================================================
-- AI ANALYSIS: Deep Audit (Tier C - AI Inference)
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_deep_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Can audit account OR specific post
    account_id UUID REFERENCES competitor_account(account_id) ON DELETE CASCADE,
    post_id UUID REFERENCES competitor_post(post_id) ON DELETE CASCADE,
    
    -- Audit metadata
    audit_type TEXT NOT NULL,  -- 'account', 'post', 'batch'
    audit_version TEXT DEFAULT '1.0',
    model_used TEXT,
    
    -- Transcript (if available)
    transcript TEXT,
    transcript_source TEXT,  -- 'platform_api', 'whisper', 'manual', 'youtube_cc'
    
    -- Visual analysis
    visual_fingerprint JSONB,  -- fonts, colors, caption_style, cut_density
    style_signature TEXT,  -- e.g., "FastCaptions_BrightColors_HighEnergy"
    
    -- Content classification
    hook_archetype TEXT,  -- "Stop doing X", "3 mistakes", "Nobody tells you"
    hook_text TEXT,
    angle_type TEXT,  -- tutorial, teardown, myth-bust, case-study, listicle
    content_pillar TEXT,
    topic_tags TEXT[],
    
    -- CTA analysis
    cta_type TEXT,  -- comment_keyword, link_bio, follow_part2, dm_me
    cta_text TEXT,
    cta_placement TEXT,  -- opening, middle, closing
    
    -- Beat sheet / structure
    beat_sheet JSONB,  -- [{role, start_sec, end_sec, summary}]
    edl_guess JSONB,  -- Edit decision list inference
    
    -- Emotional/positioning
    emotional_promise TEXT,
    positioning_statement TEXT,  -- "They help X achieve Y using Z"
    differentiators TEXT[],
    
    -- Embeddings for clustering (requires pgvector extension)
    -- topic_embedding VECTOR(1536),  -- OpenAI ada-002 embedding
    -- style_embedding VECTOR(1536),
    
    -- Scores
    hook_score FLOAT,  -- 0-100
    retention_tactics_score FLOAT,
    production_quality_score FLOAT,
    
    -- Full AI response
    ai_analysis_raw JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_deep_audit_account ON competitor_deep_audit(account_id);
CREATE INDEX idx_competitor_deep_audit_post ON competitor_deep_audit(post_id);
CREATE INDEX idx_competitor_deep_audit_hook ON competitor_deep_audit(hook_archetype);

-- =============================================================================
-- FUNNEL: Funnel Map (inferred from bio, CTAs, posts)
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_funnel_map (
    funnel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES competitor_account(account_id) ON DELETE CASCADE,
    
    -- Entry points
    entry_points JSONB,  -- [{type, url, description}]
    
    -- Lead magnets
    lead_magnets JSONB,  -- [{type: 'freebie'|'webinar'|'newsletter'|'community', name, url}]
    
    -- Conversion paths
    conversion_paths JSONB,  -- [{trigger, action, destination}]
    
    -- Offer stack (inferred)
    offer_stack JSONB,  -- [{tier: 'free'|'low'|'mid'|'high', name, price_hint, evidence}]
    
    -- CTA patterns
    top_cta_types TEXT[],
    cta_frequency JSONB,  -- {type: count}
    
    -- Proof assets
    proof_types TEXT[],  -- testimonials, case_studies, results_screenshots
    proof_posts TEXT[],  -- post_ids with proof
    
    -- Evidence links
    evidence_posts TEXT[],  -- post_ids used to infer funnel
    evidence_urls TEXT[],
    
    -- Funnel clarity score
    funnel_clarity_score FLOAT,  -- 0-100, how clear is their funnel
    
    -- AI reasoning
    funnel_analysis_raw JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_funnel_account ON competitor_funnel_map(account_id);

-- =============================================================================
-- OUTPUT: Post Rankings
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_post_ranking (
    ranking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES competitor_account(account_id) ON DELETE CASCADE,
    
    -- Ranking context
    ranking_type TEXT NOT NULL,  -- 'velocity', 'engagement', 'viral_potential', 'template_worthy'
    time_window TEXT,  -- '7d', '30d', '90d', 'all'
    
    -- Ranked posts
    ranked_posts JSONB,  -- [{post_id, rank, score, reasoning}]
    
    -- Scoring weights used
    scoring_config JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_ranking_account ON competitor_post_ranking(account_id);

-- =============================================================================
-- OUTPUT: Template Packs (Remotion-ready)
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_template_pack (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source
    account_id UUID REFERENCES competitor_account(account_id) ON DELETE CASCADE,
    source_post_id UUID REFERENCES competitor_post(post_id) ON DELETE SET NULL,
    
    -- Template identity
    template_name TEXT NOT NULL,
    template_slug TEXT UNIQUE,
    
    -- Style fingerprint
    style_fingerprint JSONB,  -- caption_style, cut_density, motion_presets, color_scheme
    
    -- Beat sheet template
    beat_sheet_template JSONB,  -- [{role, default_duration, notes}]
    
    -- Remotion spec with placeholders
    remotion_render_spec JSONB,  -- RemotionRenderSpecV1 with {{PLACEHOLDERS}}
    
    -- Placeholder definitions
    placeholders JSONB,  -- [{key: '{{HOOK_TEXT}}', type: 'text', description, example}]
    
    -- Swap rules
    swap_rules JSONB,  -- How to replace assets without breaking pacing
    
    -- Usage guidance
    best_for TEXT[],  -- ['tutorial', 'testimonial', 'product_launch']
    difficulty_level TEXT,  -- 'beginner', 'intermediate', 'advanced'
    estimated_production_time TEXT,
    
    -- Preview
    preview_thumbnail_url TEXT,
    example_output_url TEXT,
    
    -- Metrics
    times_used INTEGER DEFAULT 0,
    avg_performance_score FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_template_account ON competitor_template_pack(account_id);
CREATE INDEX idx_competitor_template_slug ON competitor_template_pack(template_slug);

-- =============================================================================
-- REPORTS: Full Audit Reports
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_audit_report (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES competitor_account(account_id) ON DELETE CASCADE,
    
    -- Report metadata
    report_version TEXT DEFAULT '1.0',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    posts_analyzed INTEGER,
    time_window TEXT,
    
    -- Section: Unique Factors
    unique_factors JSONB,  -- {positioning, differentiators, emotional_promise, credibility_signals}
    
    -- Section: Strategy Decomposition
    strategy JSONB,  -- {content_pillars, angle_library, hook_system, retention_tactics}
    
    -- Section: Funnel Setup
    funnel_summary JSONB,  -- {top_ctas, lead_capture, offer_ladder, proof_assets}
    
    -- Section: Top Posts
    top_posts_analysis JSONB,  -- [{post_id, rank, scores, why_it_works}]
    
    -- Section: Playbook
    playbook JSONB,  -- {templates_to_replicate, experiment_ideas, implementation_roadmap}
    
    -- Scores
    overall_strategy_score FLOAT,
    funnel_clarity_score FLOAT,
    content_consistency_score FLOAT,
    
    -- Full report data
    full_report_json JSONB,
    
    -- Export formats
    report_markdown TEXT,
    report_pdf_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_report_account ON competitor_audit_report(account_id);
CREATE INDEX idx_competitor_report_generated ON competitor_audit_report(generated_at DESC);

-- =============================================================================
-- AUDIT RUNS: Track audit job execution
-- =============================================================================

CREATE TABLE IF NOT EXISTS competitor_audit_run (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Input
    platform TEXT NOT NULL,
    handle TEXT NOT NULL,
    requested_post_count INTEGER DEFAULT 20,
    time_window TEXT DEFAULT '30d',
    
    -- Options
    include_deep_audit BOOLEAN DEFAULT TRUE,
    include_funnel_map BOOLEAN DEFAULT TRUE,
    include_templates BOOLEAN DEFAULT TRUE,
    snapshot_schedule TEXT[],  -- ['T+1h', 'T+24h', 'T+7d']
    
    -- Status
    status TEXT DEFAULT 'pending',  -- pending, collecting, analyzing, complete, failed
    progress_pct INTEGER DEFAULT 0,
    current_step TEXT,
    
    -- Results
    account_id UUID REFERENCES competitor_account(account_id),
    report_id UUID REFERENCES competitor_audit_report(report_id),
    posts_collected INTEGER,
    posts_analyzed INTEGER,
    
    -- Errors
    error_message TEXT,
    error_details JSONB,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_run_status ON competitor_audit_run(status);
CREATE INDEX idx_competitor_run_platform ON competitor_audit_run(platform, handle);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE competitor_account IS 'Competitor/influencer accounts being tracked for analysis';
COMMENT ON TABLE competitor_post IS 'Individual posts from competitor accounts with visible metrics';
COMMENT ON TABLE competitor_post_snapshot IS 'Time-series snapshots of post metrics for velocity/decay analysis';
COMMENT ON TABLE competitor_deep_audit IS 'AI-generated deep analysis of accounts and posts';
COMMENT ON TABLE competitor_funnel_map IS 'Inferred sales/marketing funnel structure from competitor content';
COMMENT ON TABLE competitor_post_ranking IS 'Ranked lists of top posts by various scoring methods';
COMMENT ON TABLE competitor_template_pack IS 'Remotion-ready templates extracted from competitor formats';
COMMENT ON TABLE competitor_audit_report IS 'Full strategic reports combining all analysis';
COMMENT ON TABLE competitor_audit_run IS 'Job tracking for competitor audit workflows';

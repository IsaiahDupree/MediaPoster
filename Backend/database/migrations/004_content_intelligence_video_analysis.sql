-- Content Intelligence System - Part 1: Video Analysis Tables
-- This migration creates tables for comprehensive video/image analysis
-- including word-level timestamps, frame analysis, segments, captions, and headlines

-- Core video analysis metadata
CREATE TABLE IF NOT EXISTS analyzed_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_video_id UUID REFERENCES original_videos(id) ON DELETE CASCADE,
    content_item_id UUID REFERENCES content_items(id) ON DELETE CASCADE,
    duration_seconds DECIMAL,
    transcript_full TEXT,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Timeline segments (hook, context, body, CTA, payoff)
CREATE TABLE IF NOT EXISTS video_segments (
    id BIGSERIAL PRIMARY KEY,
    video_id UUID REFERENCES analyzed_videos(id) ON DELETE CASCADE,
    segment_type TEXT NOT NULL, -- 'hook' | 'context' | 'body' | 'cta' | 'payoff'
    start_s DECIMAL NOT NULL,
    end_s DECIMAL NOT NULL,
    
    -- Psychology tags (FATE + AIDA framework)
    hook_type TEXT, -- 'pain' | 'curiosity' | 'aspirational' | 'contrarian' | 'gap' | 'absurd'
    focus TEXT, -- Target audience/problem description
    authority_signal TEXT, -- Credentials, proof, experience mentioned
    tribe_marker TEXT, -- Identity calls, shared language
    emotion TEXT, -- 'relief' | 'excitement' | 'curiosity' | 'FOMO' | 'frustration'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_time_range CHECK (end_s >= start_s)
);

-- Word-level timestamps with NLP analysis
CREATE TABLE IF NOT EXISTS video_words (
    id BIGSERIAL PRIMARY KEY,
    video_id UUID REFERENCES analyzed_videos(id) ON DELETE CASCADE,
    segment_id BIGINT REFERENCES video_segments(id) ON DELETE CASCADE,
    word_index INTEGER NOT NULL,
    word TEXT NOT NULL,
    start_s DECIMAL NOT NULL,
    end_s DECIMAL NOT NULL,
    
    -- Analysis tags
    is_emphasis BOOLEAN DEFAULT FALSE, -- Caps, pitch change, hook words
    is_question BOOLEAN DEFAULT FALSE,
    is_cta_keyword BOOLEAN DEFAULT FALSE,
    speech_function TEXT, -- 'hook' | 'proof' | 'step' | 'metaphor' | 'cta' | 'future_promise'
    sentiment_score DECIMAL, -- -1 to +1
    emotion TEXT, -- 'curiosity' | 'frustration' | 'hope' | 'flex' | 'warning'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_word_time CHECK (end_s >= start_s)
);

-- Frame-by-frame visual analysis
CREATE TABLE IF NOT EXISTS video_frames (
    id BIGSERIAL PRIMARY KEY,
    video_id UUID REFERENCES analyzed_videos(id) ON DELETE CASCADE,
    segment_id BIGINT REFERENCES video_segments(id) ON DELETE SET NULL,
    frame_time_s DECIMAL NOT NULL,
    frame_url TEXT, -- S3/storage URL for the frame image
    
    -- Visual classification
    shot_type TEXT, -- 'close_up' | 'medium' | 'wide' | 'screen_record' | 'broll'
    camera_motion TEXT, -- 'static' | 'slight' | 'aggressive'
    presence TEXT[], -- ['face', 'full_body', 'hands', 'laptop', 'whiteboard', 'phone']
    objects TEXT[], -- Detected objects
    text_on_screen TEXT, -- OCR extracted text
    logo_detected TEXT[], -- Brand logos found
    
    -- Visual properties
    brightness_level TEXT, -- 'dark' | 'normal' | 'bright'
    color_temperature TEXT, -- 'warm' | 'neutral' | 'cool'
    visual_clutter_score DECIMAL, -- 0-1 (how busy/messy the frame is)
    
    -- Pattern analysis
    is_pattern_interrupt BOOLEAN DEFAULT FALSE, -- Big change vs previous frame
    is_hook_frame BOOLEAN DEFAULT FALSE, -- Eyes to camera, bold text, etc.
    has_meme_element BOOLEAN DEFAULT FALSE, -- Reaction face, overlay, cutaway
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Caption styling and positioning
CREATE TABLE IF NOT EXISTS video_captions (
    id BIGSERIAL PRIMARY KEY,
    video_id UUID REFERENCES analyzed_videos(id) ON DELETE CASCADE,
    clip_id UUID REFERENCES clips(id) ON DELETE CASCADE,
    start_s DECIMAL NOT NULL,
    end_s DECIMAL NOT NULL,
    text TEXT NOT NULL,
    
    -- Styling
    font_family TEXT,
    font_weight TEXT, -- 'regular' | 'semibold' | 'bold'
    font_size INTEGER,
    text_color TEXT,
    background_style TEXT, -- 'box' | 'outline' | 'highlight_bar' | 'none'
    position TEXT, -- 'top' | 'mid' | 'bottom'
    animation TEXT, -- 'fade' | 'pop' | 'typewriter' | 'karaoke'
    
    -- Keyword emphasis
    emphasized_words TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_caption_time CHECK (end_s >= start_s)
);

-- Persistent headline overlay ("catchy text throughout")
CREATE TABLE IF NOT EXISTS video_headlines (
    id BIGSERIAL PRIMARY KEY,
    video_id UUID REFERENCES analyzed_videos(id) ON DELETE CASCADE,
    clip_id UUID REFERENCES clips(id) ON DELETE CASCADE,
    main_text TEXT NOT NULL,
    sub_text TEXT,
    start_s DECIMAL DEFAULT 0,
    end_s DECIMAL, -- NULL = entire video duration
    position TEXT, -- 'top_bar' | 'bottom_bar' | 'mid_left' | 'mid_right'
    
    -- Styling
    font_family TEXT,
    font_size INTEGER,
    text_color TEXT,
    background_style TEXT, -- 'pill' | 'banner' | 'transparent' | 'blur_bar'
    corner_radius INTEGER,
    padding INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_analyzed_videos_original ON analyzed_videos(original_video_id);
CREATE INDEX IF NOT EXISTS idx_analyzed_videos_content ON analyzed_videos(content_item_id);

CREATE INDEX IF NOT EXISTS idx_video_segments_video ON video_segments(video_id);
CREATE INDEX IF NOT EXISTS idx_video_segments_type ON video_segments(segment_type);
CREATE INDEX IF NOT EXISTS idx_video_segments_time ON video_segments(start_s, end_s);

CREATE INDEX IF NOT EXISTS idx_video_words_video ON video_words(video_id);
CREATE INDEX IF NOT EXISTS idx_video_words_segment ON video_words(segment_id);
CREATE INDEX IF NOT EXISTS idx_video_words_time ON video_words(start_s);
CREATE INDEX IF NOT EXISTS idx_video_words_cta ON video_words(is_cta_keyword) WHERE is_cta_keyword = TRUE;

CREATE INDEX IF NOT EXISTS idx_video_frames_video ON video_frames(video_id);
CREATE INDEX IF NOT EXISTS idx_video_frames_segment ON video_frames(segment_id);
CREATE INDEX IF NOT EXISTS idx_video_frames_time ON video_frames(frame_time_s);
CREATE INDEX IF NOT EXISTS idx_video_frames_hooks ON video_frames(is_hook_frame) WHERE is_hook_frame = TRUE;
CREATE INDEX IF NOT EXISTS idx_video_frames_interrupts ON video_frames(is_pattern_interrupt) WHERE is_pattern_interrupt = TRUE;

CREATE INDEX IF NOT EXISTS idx_video_captions_video ON video_captions(video_id);
CREATE INDEX IF NOT EXISTS idx_video_captions_clip ON video_captions(clip_id);

CREATE INDEX IF NOT EXISTS idx_video_headlines_video ON video_headlines(video_id);
CREATE INDEX IF NOT EXISTS idx_video_headlines_clip ON video_headlines(clip_id);

-- Enable RLS
ALTER TABLE analyzed_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_words ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_frames ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_captions ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_headlines ENABLE ROW LEVEL SECURITY;

-- Comments for documentation
COMMENT ON TABLE analyzed_videos IS 'Core video analysis metadata with transcript';
COMMENT ON TABLE video_segments IS 'Timeline segments: hook, context, body, CTA with psychology tags';
COMMENT ON TABLE video_words IS 'Word-level timestamps with NLP analysis and sentiment';
COMMENT ON TABLE video_frames IS 'Frame-by-frame visual analysis with OCR and object detection';
COMMENT ON TABLE video_captions IS 'Caption styling and positioning for generated clips';
COMMENT ON TABLE video_headlines IS 'Persistent headline overlays explaining the video';

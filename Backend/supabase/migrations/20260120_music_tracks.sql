-- Migration: Music Library (MUSIC-001)
-- Description: Music tracks table with rich metadata for background music selection
-- Date: 2026-01-20

CREATE TABLE IF NOT EXISTS music_tracks (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Track identification
    title VARCHAR(500) NOT NULL,
    artist VARCHAR(500),
    source VARCHAR(50) NOT NULL, -- 'suno', 'soundcloud', 'social_platform', 'local'
    source_id TEXT,
    source_url TEXT,

    -- File information
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    file_format VARCHAR(20), -- 'mp3', 'wav', 'ogg', etc.
    checksum VARCHAR(64), -- SHA-256 for deduplication

    -- Audio properties
    duration_seconds FLOAT NOT NULL,
    sample_rate INTEGER, -- Hz
    bitrate INTEGER, -- kbps
    channels INTEGER DEFAULT 2, -- 1=mono, 2=stereo

    -- Musical metadata
    tempo_bpm FLOAT,
    key VARCHAR(10), -- 'C', 'Am', 'F#m', etc.
    time_signature VARCHAR(10), -- '4/4', '3/4', etc.
    genre VARCHAR(100),
    subgenre VARCHAR(100),

    -- Mood & Energy (for auto-matching)
    mood VARCHAR(100), -- 'energetic', 'calm', 'upbeat', 'melancholic', etc.
    energy_level FLOAT, -- 0.0-1.0 scale
    valence FLOAT, -- 0.0-1.0 (negative to positive emotional tone)
    danceability FLOAT, -- 0.0-1.0
    instrumentalness FLOAT, -- 0.0-1.0 (0=vocals, 1=instrumental)

    -- Tagging & categorization
    tags TEXT[], -- ['viral', 'trending', 'uplifting', 'cinematic']
    moods TEXT[], -- Multiple moods
    use_cases TEXT[], -- ['intro', 'background', 'outro', 'transition']

    -- Content matching attributes
    suitable_for_content_types TEXT[], -- ['educational', 'comedy', 'motivational']
    recommended_video_pacing VARCHAR(50), -- 'slow', 'medium', 'fast', 'dynamic'

    -- Licensing & usage
    license_type VARCHAR(100), -- 'public_domain', 'royalty_free', 'licensed', 'copyright'
    attribution_required BOOLEAN DEFAULT FALSE,
    commercial_use_allowed BOOLEAN DEFAULT TRUE,
    license_url TEXT,

    -- Platform-specific metadata
    platform VARCHAR(50), -- 'tiktok', 'instagram', 'youtube', etc.
    platform_popularity INTEGER,
    is_trending BOOLEAN DEFAULT FALSE,
    trending_rank INTEGER,
    trending_date DATE,

    -- Audio analysis (advanced)
    audio_features JSONB, -- Detailed audio analysis from librosa/essentia
    waveform_peaks JSONB, -- Peak timestamps for sync
    beat_timestamps JSONB, -- Beat detection for video sync

    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    avg_match_score FLOAT, -- Average compatibility score when matched

    -- Quality & status
    quality_rating FLOAT, -- 1.0-5.0 user/system rating
    is_active BOOLEAN DEFAULT TRUE,
    is_curated BOOLEAN DEFAULT FALSE, -- Hand-picked by team
    curation_notes TEXT,

    -- Import metadata
    imported_from VARCHAR(100), -- 'suno_crawler', 'manual_upload', 'api_import'
    import_batch_id UUID,
    imported_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast querying
CREATE INDEX idx_music_tracks_source ON music_tracks(source);
CREATE INDEX idx_music_tracks_genre ON music_tracks(genre);
CREATE INDEX idx_music_tracks_mood ON music_tracks(mood);
CREATE INDEX idx_music_tracks_tempo ON music_tracks(tempo_bpm);
CREATE INDEX idx_music_tracks_energy ON music_tracks(energy_level);
CREATE INDEX idx_music_tracks_is_trending ON music_tracks(is_trending);
CREATE INDEX idx_music_tracks_workspace_id ON music_tracks(workspace_id);
CREATE INDEX idx_music_tracks_checksum ON music_tracks(checksum);

-- Updated_at trigger
CREATE TRIGGER update_music_tracks_updated_at
    BEFORE UPDATE ON music_tracks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE music_tracks IS 'Music library with rich metadata for background music selection (MUSIC-001)';
COMMENT ON COLUMN music_tracks.energy_level IS 'Energy level 0.0-1.0 for auto-matching';
COMMENT ON COLUMN music_tracks.checksum IS 'SHA-256 checksum for deduplication';
COMMENT ON COLUMN music_tracks.audio_features IS 'Detailed audio analysis from librosa/essentia';

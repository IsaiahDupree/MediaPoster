-- Enable pgvector extension for semantic search and embeddings
-- =============================================================================

-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Add vector columns to competitor_deep_audit (if not exists)
-- =============================================================================

DO $$ 
BEGIN
    -- Add topic_embedding column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='competitor_deep_audit' AND column_name='topic_embedding') THEN
        ALTER TABLE competitor_deep_audit ADD COLUMN topic_embedding VECTOR(1536);
        COMMENT ON COLUMN competitor_deep_audit.topic_embedding IS 'OpenAI ada-002 embedding for topic similarity search';
    END IF;
    
    -- Add style_embedding column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='competitor_deep_audit' AND column_name='style_embedding') THEN
        ALTER TABLE competitor_deep_audit ADD COLUMN style_embedding VECTOR(1536);
        COMMENT ON COLUMN competitor_deep_audit.style_embedding IS 'Style/format embedding for similar content discovery';
    END IF;
END $$;


-- =============================================================================
-- Add vector columns to video_analysis for content similarity
-- =============================================================================

DO $$ 
BEGIN
    -- Content embedding for video analysis
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='content_embedding') THEN
        ALTER TABLE video_analysis ADD COLUMN content_embedding VECTOR(1536);
        COMMENT ON COLUMN video_analysis.content_embedding IS 'Embedding of transcript/content for semantic search';
    END IF;
    
    -- Hook embedding for hook similarity
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='hook_embedding') THEN
        ALTER TABLE video_analysis ADD COLUMN hook_embedding VECTOR(1536);
        COMMENT ON COLUMN video_analysis.hook_embedding IS 'Embedding of hooks for finding similar hooks';
    END IF;
END $$;


-- =============================================================================
-- Add vector columns to video_template_library
-- =============================================================================

DO $$ 
BEGIN
    -- Template embedding for finding similar templates
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_template_library' AND column_name='template_embedding') THEN
        ALTER TABLE video_template_library ADD COLUMN template_embedding VECTOR(1536);
        COMMENT ON COLUMN video_template_library.template_embedding IS 'Embedding of template characteristics for similarity matching';
    END IF;
END $$;


-- =============================================================================
-- Create indexes for vector similarity search (using HNSW for fast ANN)
-- =============================================================================

-- Index on competitor_deep_audit topic embeddings
CREATE INDEX IF NOT EXISTS idx_deep_audit_topic_embedding 
ON competitor_deep_audit USING hnsw (topic_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index on competitor_deep_audit style embeddings
CREATE INDEX IF NOT EXISTS idx_deep_audit_style_embedding 
ON competitor_deep_audit USING hnsw (style_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index on video_analysis content embeddings
CREATE INDEX IF NOT EXISTS idx_video_analysis_content_embedding 
ON video_analysis USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index on video_analysis hook embeddings
CREATE INDEX IF NOT EXISTS idx_video_analysis_hook_embedding 
ON video_analysis USING hnsw (hook_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index on template library embeddings
CREATE INDEX IF NOT EXISTS idx_template_library_embedding 
ON video_template_library USING hnsw (template_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);


-- =============================================================================
-- Helper function for cosine similarity search
-- =============================================================================

CREATE OR REPLACE FUNCTION match_similar_content(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    video_id UUID,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id,
        1 - (v.content_embedding <=> query_embedding) as similarity
    FROM video_analysis v
    WHERE v.content_embedding IS NOT NULL
    AND 1 - (v.content_embedding <=> query_embedding) > match_threshold
    ORDER BY v.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_similar_content IS 'Find videos with similar content using cosine similarity';


-- =============================================================================
-- Helper function for finding similar hooks
-- =============================================================================

CREATE OR REPLACE FUNCTION match_similar_hooks(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.75,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    video_id UUID,
    hooks TEXT[],
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id,
        v.hooks,
        1 - (v.hook_embedding <=> query_embedding) as similarity
    FROM video_analysis v
    WHERE v.hook_embedding IS NOT NULL
    AND 1 - (v.hook_embedding <=> query_embedding) > match_threshold
    ORDER BY v.hook_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_similar_hooks IS 'Find videos with similar hooks for inspiration';


-- =============================================================================
-- Helper function for finding similar competitor content
-- =============================================================================

CREATE OR REPLACE FUNCTION match_similar_competitor_content(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    audit_id UUID,
    account_id UUID,
    hook_archetype TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.audit_id,
        d.account_id,
        d.hook_archetype,
        1 - (d.topic_embedding <=> query_embedding) as similarity
    FROM competitor_deep_audit d
    WHERE d.topic_embedding IS NOT NULL
    AND 1 - (d.topic_embedding <=> query_embedding) > match_threshold
    ORDER BY d.topic_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_similar_competitor_content IS 'Find similar competitor content by topic';


COMMENT ON EXTENSION vector IS 'pgvector - vector similarity search for embeddings';

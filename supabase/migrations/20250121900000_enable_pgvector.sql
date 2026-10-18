-- Enable pgvector extension for semantic search and embeddings
-- =============================================================================

-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Note: Vector columns and indexes are added in their respective table migrations
COMMENT ON EXTENSION vector IS 'pgvector - vector similarity search for embeddings';

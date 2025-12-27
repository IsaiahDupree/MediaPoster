"""
Integration Tests for Embedding Service
=======================================
Tests embedding generation and pgvector similarity search with real database.
"""
import pytest
import os
from uuid import uuid4

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def db_engine():
    """Create database engine"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture
def cleanup_test_data(db_engine):
    """Cleanup test data after tests"""
    test_ids = []
    yield test_ids
    
    if test_ids:
        with db_engine.connect() as conn:
            for table, id_col, id_val in test_ids:
                try:
                    conn.execute(text(f"DELETE FROM {table} WHERE {id_col} = :id"), {"id": id_val})
                    conn.commit()
                except:
                    pass


# ============================================================================
# pgvector Extension Tests
# ============================================================================

class TestPgvectorExtension:
    """Tests for pgvector extension"""
    
    def test_pgvector_enabled(self, db_engine):
        """Verify pgvector extension is enabled"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT extversion FROM pg_extension WHERE extname = 'vector'
            """))
            row = result.fetchone()
        
        assert row is not None, "pgvector extension not enabled"
        assert row[0] == "0.8.0", f"Unexpected version: {row[0]}"
    
    def test_vector_type_works(self, db_engine):
        """Test that VECTOR type operations work"""
        with db_engine.connect() as conn:
            # Create a simple vector and test operations
            result = conn.execute(text("""
                SELECT '[1,2,3]'::vector <=> '[4,5,6]'::vector as distance
            """))
            row = result.fetchone()
        
        assert row is not None
        assert row[0] > 0  # Distance should be positive
    
    def test_cosine_similarity_calculation(self, db_engine):
        """Test cosine similarity calculation"""
        with db_engine.connect() as conn:
            # Identical vectors should have distance 0
            result = conn.execute(text("""
                SELECT 1 - ('[1,0,0]'::vector <=> '[1,0,0]'::vector) as similarity
            """))
            row = result.fetchone()
        
        assert row[0] == pytest.approx(1.0, abs=0.001)
    
    def test_orthogonal_vectors(self, db_engine):
        """Test orthogonal vectors have 0 cosine similarity"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 1 - ('[1,0,0]'::vector <=> '[0,1,0]'::vector) as similarity
            """))
            row = result.fetchone()
        
        # Orthogonal vectors have cosine similarity of 0 (distance of 1)
        assert row[0] == pytest.approx(0.0, abs=0.1)


# ============================================================================
# Vector Column Tests
# ============================================================================

class TestVectorColumns:
    """Tests for vector columns in tables"""
    
    def test_competitor_deep_audit_has_vector_columns(self, db_engine):
        """Verify competitor_deep_audit has vector columns"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_deep_audit'
                AND column_name IN ('topic_embedding', 'style_embedding')
            """))
            columns = {row[0]: row[1] for row in result}
        
        assert "topic_embedding" in columns
        assert "style_embedding" in columns
    
    def test_video_analysis_has_vector_columns(self, db_engine):
        """Verify video_analysis has vector columns"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'video_analysis'
                AND column_name IN ('content_embedding', 'hook_embedding')
            """))
            columns = [row[0] for row in result]
        
        assert "content_embedding" in columns
        assert "hook_embedding" in columns
    
    def test_template_library_has_vector_column(self, db_engine):
        """Verify video_template_library has vector column"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'video_template_library'
                AND column_name = 'template_embedding'
            """))
            columns = [row[0] for row in result]
        
        assert "template_embedding" in columns


# ============================================================================
# Vector Insert/Query Tests
# ============================================================================

class TestVectorOperations:
    """Tests for vector insert and query operations"""
    
    def test_insert_and_query_vector(self, db_engine, cleanup_test_data):
        """Test inserting and querying a vector"""
        # Create test embedding (1536 dimensions)
        test_embedding = [0.1] * 1536
        embedding_str = "[" + ",".join(str(x) for x in test_embedding) + "]"
        
        # Insert into template library
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO video_template_library (
                    name, slug, category, target_duration_sec, difficulty,
                    template_embedding
                ) VALUES (
                    :name, :slug, 'test', 30, 'beginner',
                    CAST(:embedding AS vector)
                )
                RETURNING template_id
            """), {
                "name": f"Test Template {uuid4().hex[:6]}",
                "slug": f"test-{uuid4().hex[:8]}",
                "embedding": embedding_str
            })
            conn.commit()
            template_id = str(result.fetchone()[0])
        
        cleanup_test_data.append(("video_template_library", "template_id", template_id))
        
        # Query the embedding back
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT template_embedding::text, vector_dims(template_embedding) as dims
                FROM video_template_library 
                WHERE template_id = :id
            """), {"id": template_id})
            row = result.fetchone()
        
        assert row is not None
        assert row[0] is not None
        assert row[1] == 1536  # Check dimension count
    
    def test_similarity_search(self, db_engine, cleanup_test_data):
        """Test vector similarity search"""
        # Create two templates with very different embeddings
        # First: mostly positive values
        embedding1 = [0.1 + (i % 10) * 0.01 for i in range(1536)]
        # Second: alternating positive/negative values (different direction)
        embedding2 = [0.5 if i % 2 == 0 else -0.5 for i in range(1536)]
        
        embedding_str1 = "[" + ",".join(str(x) for x in embedding1) + "]"
        embedding_str2 = "[" + ",".join(str(x) for x in embedding2) + "]"
        
        with db_engine.connect() as conn:
            # Insert first template
            result = conn.execute(text("""
                INSERT INTO video_template_library (
                    name, slug, category, target_duration_sec, difficulty,
                    template_embedding
                ) VALUES (
                    :name, :slug, 'test', 30, 'beginner',
                    CAST(:embedding AS vector)
                )
                RETURNING template_id
            """), {
                "name": f"Similar Template {uuid4().hex[:6]}",
                "slug": f"similar-{uuid4().hex[:8]}",
                "embedding": embedding_str1
            })
            conn.commit()
            template_id1 = str(result.fetchone()[0])
            
            # Insert second template
            result = conn.execute(text("""
                INSERT INTO video_template_library (
                    name, slug, category, target_duration_sec, difficulty,
                    template_embedding
                ) VALUES (
                    :name, :slug, 'test', 30, 'beginner',
                    CAST(:embedding AS vector)
                )
                RETURNING template_id
            """), {
                "name": f"Different Template {uuid4().hex[:6]}",
                "slug": f"different-{uuid4().hex[:8]}",
                "embedding": embedding_str2
            })
            conn.commit()
            template_id2 = str(result.fetchone()[0])
        
        cleanup_test_data.append(("video_template_library", "template_id", template_id1))
        cleanup_test_data.append(("video_template_library", "template_id", template_id2))
        
        # Search for similar to embedding1
        query_embedding = "[" + ",".join(str(x) for x in embedding1) + "]"
        
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT template_id, name,
                       1 - (template_embedding <=> CAST(:query AS vector)) as similarity
                FROM video_template_library
                WHERE template_embedding IS NOT NULL
                ORDER BY template_embedding <=> CAST(:query AS vector)
                LIMIT 5
            """), {"query": query_embedding})
            rows = result.fetchall()
        
        assert len(rows) >= 2
        # First result should be template1 (most similar)
        assert str(rows[0][0]) == template_id1
        assert rows[0][2] > rows[1][2]  # First should have higher similarity


# ============================================================================
# HNSW Index Tests
# ============================================================================

class TestHNSWIndexes:
    """Tests for HNSW indexes"""
    
    def test_hnsw_indexes_exist(self, db_engine):
        """Verify HNSW indexes were created"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE indexname LIKE 'idx_%embedding%'
            """))
            indexes = [row[0] for row in result]
        
        expected_indexes = [
            "idx_deep_audit_topic_embedding",
            "idx_deep_audit_style_embedding",
            "idx_video_analysis_content_embedding",
            "idx_video_analysis_hook_embedding",
            "idx_template_library_embedding"
        ]
        
        for idx in expected_indexes:
            assert idx in indexes, f"Missing index: {idx}"


# ============================================================================
# SQL Helper Functions Tests
# ============================================================================

class TestSQLHelperFunctions:
    """Tests for SQL helper functions"""
    
    def test_match_similar_content_exists(self, db_engine):
        """Verify match_similar_content function exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_name = 'match_similar_content'
            """))
            row = result.fetchone()
        
        assert row is not None
    
    def test_match_similar_hooks_exists(self, db_engine):
        """Verify match_similar_hooks function exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_name = 'match_similar_hooks'
            """))
            row = result.fetchone()
        
        assert row is not None
    
    def test_match_similar_competitor_content_exists(self, db_engine):
        """Verify match_similar_competitor_content function exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_name = 'match_similar_competitor_content'
            """))
            row = result.fetchone()
        
        assert row is not None


# ============================================================================
# EmbeddingService Integration Tests
# ============================================================================

class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService with real DB"""
    
    @pytest.fixture
    def embedding_service(self):
        """Create embedding service"""
        from services.embedding_service import EmbeddingService
        return EmbeddingService(db_url=DATABASE_URL)
    
    @pytest.mark.asyncio
    async def test_check_pgvector_enabled(self, embedding_service):
        """Test pgvector check method"""
        result = await embedding_service.check_pgvector_enabled()
        assert result == True
    
    def test_format_vector_1536_dimensions(self, embedding_service):
        """Test vector formatting for 1536 dimensions"""
        embedding = [0.1] * 1536
        formatted = embedding_service._format_vector(embedding)
        
        assert formatted.startswith("[")
        assert formatted.endswith("]")
        # Count commas (should be 1535 for 1536 elements)
        assert formatted.count(",") == 1535


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

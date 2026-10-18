"""
Unit Tests for Embedding Service
================================
Tests for vector embedding generation and similarity search.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_embedding():
    """Mock 1536-dimensional embedding"""
    return [0.1] * 1536


@pytest.fixture
def mock_openai_embedding_response(mock_embedding):
    """Mock OpenAI embedding response"""
    mock_data = Mock()
    mock_data.embedding = mock_embedding
    mock_data.index = 0
    
    mock_response = Mock()
    mock_response.data = [mock_data]
    return mock_response


# ============================================================================
# EmbeddingService Tests
# ============================================================================

class TestEmbeddingService:
    """Tests for EmbeddingService"""
    
    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies"""
        with patch('services.embedding_service.create_engine'):
            with patch('services.embedding_service.OpenAI'):
                from services.embedding_service import EmbeddingService
                svc = EmbeddingService(
                    db_url="postgresql://test:test@localhost/test",
                    openai_api_key="test_key"
                )
                return svc
    
    def test_embedding_model_config(self, service):
        """Test embedding model configuration"""
        assert service.EMBEDDING_MODEL == "text-embedding-ada-002"
        assert service.EMBEDDING_DIMENSIONS == 1536
    
    def test_format_vector(self, service, mock_embedding):
        """Test vector formatting for PostgreSQL"""
        formatted = service._format_vector(mock_embedding)
        
        assert formatted.startswith("[")
        assert formatted.endswith("]")
        assert "0.1" in formatted
        # Should have 1536 values
        assert formatted.count(",") == 1535
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, service, mock_openai_embedding_response):
        """Test successful embedding generation"""
        service.client.embeddings.create = Mock(return_value=mock_openai_embedding_response)
        
        embedding = await service.generate_embedding("Test text for embedding")
        
        assert embedding is not None
        assert len(embedding) == 1536
        service.client.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embedding_no_client(self):
        """Test embedding generation without OpenAI client"""
        with patch('services.embedding_service.create_engine'):
            from services.embedding_service import EmbeddingService
            service = EmbeddingService(db_url="test", openai_api_key=None)
            service.client = None
            
            embedding = await service.generate_embedding("Test")
            assert embedding is None
    
    @pytest.mark.asyncio
    async def test_generate_embedding_truncation(self, service, mock_openai_embedding_response):
        """Test that long text is truncated"""
        service.client.embeddings.create = Mock(return_value=mock_openai_embedding_response)
        
        long_text = "x" * 50000  # Very long text
        embedding = await service.generate_embedding(long_text)
        
        # Check that the call was made with truncated text
        call_args = service.client.embeddings.create.call_args
        input_text = call_args.kwargs.get('input') or call_args[1].get('input')
        assert len(input_text) <= 32000
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, service):
        """Test batch embedding generation"""
        # Create mock response for batch
        mock_data1 = Mock()
        mock_data1.embedding = [0.1] * 1536
        mock_data1.index = 0
        
        mock_data2 = Mock()
        mock_data2.embedding = [0.2] * 1536
        mock_data2.index = 1
        
        mock_response = Mock()
        mock_response.data = [mock_data1, mock_data2]
        
        service.client.embeddings.create = Mock(return_value=mock_response)
        
        embeddings = await service.generate_embeddings_batch(["Text 1", "Text 2"])
        
        assert len(embeddings) == 2
        assert embeddings[0][0] == 0.1
        assert embeddings[1][0] == 0.2
    
    @pytest.mark.asyncio
    async def test_check_pgvector_enabled(self, service):
        """Test pgvector check"""
        mock_result = Mock()
        mock_result.fetchone.return_value = ("0.8.0",)
        
        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        
        service.engine.connect = Mock(return_value=mock_conn)
        
        result = await service.check_pgvector_enabled()
        assert result == True


class TestSimilarContentDataclass:
    """Tests for SimilarContent dataclass"""
    
    def test_similar_content_creation(self):
        """Test SimilarContent dataclass"""
        from services.embedding_service import SimilarContent
        
        content = SimilarContent(
            id="test-id",
            similarity=0.85,
            metadata={"title": "Test Video", "hooks": ["Hook 1"]}
        )
        
        assert content.id == "test-id"
        assert content.similarity == 0.85
        assert content.metadata["title"] == "Test Video"


class TestVectorSearch:
    """Tests for vector similarity search"""
    
    @pytest.fixture
    def service(self):
        """Create service"""
        with patch('services.embedding_service.create_engine'):
            with patch('services.embedding_service.OpenAI'):
                from services.embedding_service import EmbeddingService
                return EmbeddingService(db_url="test", openai_api_key="test")
    
    @pytest.mark.asyncio
    async def test_find_similar_videos_no_embedding(self, service):
        """Test similar videos search with failed embedding"""
        service.generate_embedding = AsyncMock(return_value=None)
        
        results = await service.find_similar_videos("test query")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_find_similar_hooks_no_embedding(self, service):
        """Test similar hooks search with failed embedding"""
        service.generate_embedding = AsyncMock(return_value=None)
        
        results = await service.find_similar_hooks("test hook")
        assert results == []
    
    @pytest.mark.asyncio
    async def test_find_similar_competitor_no_embedding(self, service):
        """Test similar competitor search with failed embedding"""
        service.generate_embedding = AsyncMock(return_value=None)
        
        results = await service.find_similar_competitor_content("test query")
        assert results == []


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

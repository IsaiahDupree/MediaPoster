"""
Semantic Search API
===================
API endpoints for semantic content search using vector embeddings.

Features:
- Search similar videos by content
- Search similar hooks
- Search similar competitor content
- Generate embeddings for new content
- Check database embedding coverage

Implements EMBED-001 (Embedding Service) and EMBED-002 (Semantic Content Search)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

from services.embedding_service import EmbeddingService, SimilarContent


router = APIRouter(prefix="/api/semantic-search", tags=["Semantic Search"])


# Request/Response Models
class SearchRequest(BaseModel):
    """Request for semantic search"""
    query: str = Field(..., description="Search query text")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold (0-1)")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")


class EmbedRequest(BaseModel):
    """Request to generate embedding"""
    text: str = Field(..., description="Text to embed")


class BatchEmbedRequest(BaseModel):
    """Request to generate multiple embeddings"""
    texts: List[str] = Field(..., description="List of texts to embed")


class VideoEmbedRequest(BaseModel):
    """Request to store video embedding"""
    video_id: str = Field(..., description="Video analysis ID")
    content_text: str = Field(..., description="Main content/transcript text")
    hooks: Optional[List[str]] = Field(default=None, description="List of hooks to embed")


class CompetitorEmbedRequest(BaseModel):
    """Request to store competitor embedding"""
    audit_id: str = Field(..., description="Competitor audit ID")
    topic_text: str = Field(..., description="Topic/content description")
    style_text: Optional[str] = Field(default=None, description="Style/format description")


class SimilarContentResponse(BaseModel):
    """Response for similar content"""
    id: str
    similarity: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Response for search queries"""
    success: bool
    query: str
    results: List[SimilarContentResponse]
    count: int
    threshold: float


class EmbeddingResponse(BaseModel):
    """Response for embedding generation"""
    success: bool
    embedding: Optional[List[float]] = None
    dimensions: Optional[int] = None
    error: Optional[str] = None


# Initialize service
embedding_service = EmbeddingService()


# Health check
@router.get("/health")
async def health_check():
    """
    Check if semantic search service is operational.

    Returns:
        - pgvector extension status
        - OpenAI API availability
        - Service readiness
    """
    try:
        pgvector_enabled = await embedding_service.check_pgvector_enabled()
        openai_available = embedding_service.client is not None

        return {
            "success": True,
            "data": {
                "pgvector_enabled": pgvector_enabled,
                "openai_configured": openai_available,
                "ready": pgvector_enabled and openai_available,
                "embedding_model": embedding_service.EMBEDDING_MODEL,
                "dimensions": embedding_service.EMBEDDING_DIMENSIONS
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Search endpoints
@router.post("/search/videos", response_model=SearchResponse)
async def search_similar_videos(request: SearchRequest):
    """
    Search for videos similar to a query text.

    Uses semantic similarity based on content embeddings.
    Returns videos ranked by cosine similarity.

    Args:
        query: Search query text
        threshold: Minimum similarity (0-1, default: 0.7)
        limit: Max results (1-50, default: 10)

    Returns:
        List of similar videos with similarity scores and metadata
    """
    try:
        logger.info(f"Searching similar videos: '{request.query[:50]}...'")

        results = await embedding_service.find_similar_videos(
            query_text=request.query,
            threshold=request.threshold,
            limit=request.limit
        )

        response_results = [
            SimilarContentResponse(
                id=r.id,
                similarity=r.similarity,
                metadata=r.metadata
            )
            for r in results
        ]

        return SearchResponse(
            success=True,
            query=request.query,
            results=response_results,
            count=len(response_results),
            threshold=request.threshold
        )

    except Exception as e:
        logger.error(f"Video search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/hooks", response_model=SearchResponse)
async def search_similar_hooks(request: SearchRequest):
    """
    Search for videos with similar hooks.

    Uses semantic similarity on hook embeddings.
    Useful for finding content with similar opening strategies.

    Args:
        query: Hook text to search for
        threshold: Minimum similarity (0-1, default: 0.75)
        limit: Max results (1-50, default: 5)

    Returns:
        List of videos with similar hooks
    """
    try:
        logger.info(f"Searching similar hooks: '{request.query[:50]}...'")

        results = await embedding_service.find_similar_hooks(
            hook_text=request.query,
            threshold=request.threshold,
            limit=request.limit
        )

        response_results = [
            SimilarContentResponse(
                id=r.id,
                similarity=r.similarity,
                metadata=r.metadata
            )
            for r in results
        ]

        return SearchResponse(
            success=True,
            query=request.query,
            results=response_results,
            count=len(response_results),
            threshold=request.threshold
        )

    except Exception as e:
        logger.error(f"Hook search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/competitors", response_model=SearchResponse)
async def search_similar_competitors(request: SearchRequest):
    """
    Search for similar competitor content.

    Uses semantic similarity on competitor audit embeddings.
    Useful for finding similar content strategies and approaches.

    Args:
        query: Topic/concept to search for
        threshold: Minimum similarity (0-1, default: 0.7)
        limit: Max results (1-50, default: 10)

    Returns:
        List of similar competitor audits
    """
    try:
        logger.info(f"Searching similar competitor content: '{request.query[:50]}...'")

        results = await embedding_service.find_similar_competitor_content(
            query_text=request.query,
            threshold=request.threshold,
            limit=request.limit
        )

        response_results = [
            SimilarContentResponse(
                id=r.id,
                similarity=r.similarity,
                metadata=r.metadata
            )
            for r in results
        ]

        return SearchResponse(
            success=True,
            query=request.query,
            results=response_results,
            count=len(response_results),
            threshold=request.threshold
        )

    except Exception as e:
        logger.error(f"Competitor search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Embedding generation endpoints
@router.post("/embed/text", response_model=EmbeddingResponse)
async def embed_text(request: EmbedRequest):
    """
    Generate embedding for a text string.

    Returns a 1536-dimensional vector from OpenAI's ada-002 model.

    Args:
        text: Text to embed (max ~8000 tokens)

    Returns:
        Embedding vector and metadata
    """
    try:
        logger.info(f"Generating embedding for {len(request.text)} chars")

        embedding = await embedding_service.generate_embedding(request.text)

        if embedding:
            return EmbeddingResponse(
                success=True,
                embedding=embedding,
                dimensions=len(embedding)
            )
        else:
            return EmbeddingResponse(
                success=False,
                error="Failed to generate embedding"
            )

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return EmbeddingResponse(
            success=False,
            error=str(e)
        )


@router.post("/embed/batch")
async def embed_batch(request: BatchEmbedRequest):
    """
    Generate embeddings for multiple texts in batch.

    More efficient than individual requests for multiple texts.

    Args:
        texts: List of texts to embed

    Returns:
        List of embeddings (null for failed items)
    """
    try:
        logger.info(f"Generating {len(request.texts)} embeddings in batch")

        embeddings = await embedding_service.generate_embeddings_batch(request.texts)

        return {
            "success": True,
            "embeddings": embeddings,
            "count": len(embeddings),
            "dimensions": embedding_service.EMBEDDING_DIMENSIONS
        }

    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/embed/video")
async def embed_video(request: VideoEmbedRequest):
    """
    Generate and store embeddings for a video.

    Creates embeddings for both main content and hooks,
    then stores them in the database for semantic search.

    Args:
        video_id: Video analysis ID
        content_text: Main content/transcript text
        hooks: Optional list of hooks

    Returns:
        Success status
    """
    try:
        logger.info(f"Storing video embeddings for {request.video_id}")

        success = await embedding_service.store_video_embedding(
            video_id=request.video_id,
            content_text=request.content_text,
            hooks=request.hooks
        )

        if success:
            return {
                "success": True,
                "message": f"Embeddings stored for video {request.video_id}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to store embeddings"
            }

    except Exception as e:
        logger.error(f"Video embedding storage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed/competitor")
async def embed_competitor(request: CompetitorEmbedRequest):
    """
    Generate and store embeddings for competitor content.

    Creates embeddings for topic and style,
    then stores them in the database for semantic search.

    Args:
        audit_id: Competitor audit ID
        topic_text: Topic/content description
        style_text: Optional style/format description

    Returns:
        Success status
    """
    try:
        logger.info(f"Storing competitor embeddings for {request.audit_id}")

        success = await embedding_service.store_competitor_embedding(
            audit_id=request.audit_id,
            topic_text=request.topic_text,
            style_text=request.style_text
        )

        if success:
            return {
                "success": True,
                "message": f"Embeddings stored for audit {request.audit_id}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to store embeddings"
            }

    except Exception as e:
        logger.error(f"Competitor embedding storage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Statistics endpoint
@router.get("/stats")
async def get_embedding_stats():
    """
    Get statistics about embeddings in the database.

    Returns:
        - Total videos with embeddings
        - Total competitor audits with embeddings
        - Coverage percentages
    """
    try:
        from sqlalchemy import text

        with embedding_service.engine.connect() as conn:
            # Video embeddings
            video_result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(content_embedding) as with_content,
                    COUNT(hook_embedding) as with_hooks
                FROM video_analysis
            """))
            video_row = video_result.fetchone()

            # Competitor embeddings
            comp_result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(topic_embedding) as with_topic,
                    COUNT(style_embedding) as with_style
                FROM competitor_deep_audit
            """))
            comp_row = comp_result.fetchone()

        return {
            "success": True,
            "data": {
                "videos": {
                    "total": video_row[0],
                    "with_content_embedding": video_row[1],
                    "with_hook_embedding": video_row[2],
                    "content_coverage": (video_row[1] / video_row[0] * 100) if video_row[0] > 0 else 0,
                    "hook_coverage": (video_row[2] / video_row[0] * 100) if video_row[0] > 0 else 0
                },
                "competitors": {
                    "total": comp_row[0],
                    "with_topic_embedding": comp_row[1],
                    "with_style_embedding": comp_row[2],
                    "topic_coverage": (comp_row[1] / comp_row[0] * 100) if comp_row[0] > 0 else 0,
                    "style_coverage": (comp_row[2] / comp_row[0] * 100) if comp_row[0] > 0 else 0
                }
            }
        }

    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Embedding Service
=================
Generates and manages vector embeddings for semantic search.
Uses OpenAI's text-embedding-ada-002 model (1536 dimensions).
"""
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from openai import OpenAI
from sqlalchemy import create_engine, text


@dataclass
class SimilarContent:
    """Result of similarity search"""
    id: str
    similarity: float
    metadata: Dict[str, Any]


class EmbeddingService:
    """
    Service for generating and querying vector embeddings.
    Uses OpenAI ada-002 for embeddings and pgvector for storage/search.
    """
    
    EMBEDDING_MODEL = "text-embedding-ada-002"
    EMBEDDING_DIMENSIONS = 1536
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        self.engine = create_engine(self.db_url)
        
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a text string.
        
        Args:
            text: Text to embed (will be truncated if too long)
            
        Returns:
            1536-dimensional embedding vector
        """
        if not self.client:
            logger.warning("OpenAI client not configured - cannot generate embeddings")
            return None
        
        # Truncate to ~8000 tokens (ada-002 max is 8191)
        text = text[:32000]  # Rough character limit
        
        try:
            response = self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for {len(text)} chars")
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (None for failed items)
        """
        if not self.client:
            return [None] * len(texts)
        
        # Truncate each text
        texts = [t[:32000] for t in texts]
        
        try:
            response = self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=texts
            )
            
            embeddings = [None] * len(texts)
            for item in response.data:
                embeddings[item.index] = item.embedding
            
            logger.info(f"Generated {len(texts)} embeddings in batch")
            return embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return [None] * len(texts)
    
    async def store_video_embedding(
        self,
        video_id: str,
        content_text: str,
        hooks: Optional[List[str]] = None
    ) -> bool:
        """
        Generate and store embeddings for a video.
        
        Args:
            video_id: Video analysis ID
            content_text: Main content/transcript text
            hooks: List of hooks to embed
            
        Returns:
            Success status
        """
        # Generate content embedding
        content_embedding = await self.generate_embedding(content_text)
        
        # Generate hook embedding if hooks provided
        hook_embedding = None
        if hooks:
            hook_text = " | ".join(hooks)
            hook_embedding = await self.generate_embedding(hook_text)
        
        if not content_embedding:
            return False
        
        try:
            with self.engine.connect() as conn:
                # Format embedding as PostgreSQL array
                content_vec = self._format_vector(content_embedding)
                hook_vec = self._format_vector(hook_embedding) if hook_embedding else None
                
                if hook_vec:
                    conn.execute(text("""
                        UPDATE video_analysis 
                        SET content_embedding = :content_vec::vector,
                            hook_embedding = :hook_vec::vector
                        WHERE id = :video_id
                    """), {
                        "video_id": video_id,
                        "content_vec": content_vec,
                        "hook_vec": hook_vec
                    })
                else:
                    conn.execute(text("""
                        UPDATE video_analysis 
                        SET content_embedding = :content_vec::vector
                        WHERE id = :video_id
                    """), {
                        "video_id": video_id,
                        "content_vec": content_vec
                    })
                conn.commit()
                
            logger.info(f"Stored embeddings for video {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store video embedding: {e}")
            return False
    
    async def store_competitor_embedding(
        self,
        audit_id: str,
        topic_text: str,
        style_text: Optional[str] = None
    ) -> bool:
        """
        Store embeddings for competitor deep audit.
        
        Args:
            audit_id: Deep audit ID
            topic_text: Topic/content description
            style_text: Style/format description
            
        Returns:
            Success status
        """
        topic_embedding = await self.generate_embedding(topic_text)
        style_embedding = await self.generate_embedding(style_text) if style_text else None
        
        if not topic_embedding:
            return False
        
        try:
            with self.engine.connect() as conn:
                topic_vec = self._format_vector(topic_embedding)
                style_vec = self._format_vector(style_embedding) if style_embedding else None
                
                if style_vec:
                    conn.execute(text("""
                        UPDATE competitor_deep_audit 
                        SET topic_embedding = :topic_vec::vector,
                            style_embedding = :style_vec::vector
                        WHERE audit_id = :audit_id
                    """), {
                        "audit_id": audit_id,
                        "topic_vec": topic_vec,
                        "style_vec": style_vec
                    })
                else:
                    conn.execute(text("""
                        UPDATE competitor_deep_audit 
                        SET topic_embedding = :topic_vec::vector
                        WHERE audit_id = :audit_id
                    """), {
                        "audit_id": audit_id,
                        "topic_vec": topic_vec
                    })
                conn.commit()
                
            logger.info(f"Stored embeddings for audit {audit_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store competitor embedding: {e}")
            return False
    
    async def find_similar_videos(
        self,
        query_text: str,
        threshold: float = 0.7,
        limit: int = 10
    ) -> List[SimilarContent]:
        """
        Find videos similar to a query text.
        
        Args:
            query_text: Text to search for
            threshold: Minimum similarity (0-1)
            limit: Max results
            
        Returns:
            List of similar videos
        """
        query_embedding = await self.generate_embedding(query_text)
        if not query_embedding:
            return []
        
        try:
            query_vec = self._format_vector(query_embedding)
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        id,
                        title,
                        topics,
                        hooks,
                        1 - (content_embedding <=> :query_vec::vector) as similarity
                    FROM video_analysis
                    WHERE content_embedding IS NOT NULL
                    AND 1 - (content_embedding <=> :query_vec::vector) > :threshold
                    ORDER BY content_embedding <=> :query_vec::vector
                    LIMIT :limit
                """), {
                    "query_vec": query_vec,
                    "threshold": threshold,
                    "limit": limit
                })
                
                results = []
                for row in result:
                    results.append(SimilarContent(
                        id=str(row[0]),
                        similarity=row[4],
                        metadata={
                            "title": row[1],
                            "topics": row[2],
                            "hooks": row[3]
                        }
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"Similar video search failed: {e}")
            return []
    
    async def find_similar_hooks(
        self,
        hook_text: str,
        threshold: float = 0.75,
        limit: int = 5
    ) -> List[SimilarContent]:
        """
        Find videos with similar hooks.
        
        Args:
            hook_text: Hook to search for
            threshold: Minimum similarity
            limit: Max results
            
        Returns:
            List of videos with similar hooks
        """
        query_embedding = await self.generate_embedding(hook_text)
        if not query_embedding:
            return []
        
        try:
            query_vec = self._format_vector(query_embedding)
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        id,
                        hooks,
                        1 - (hook_embedding <=> :query_vec::vector) as similarity
                    FROM video_analysis
                    WHERE hook_embedding IS NOT NULL
                    AND 1 - (hook_embedding <=> :query_vec::vector) > :threshold
                    ORDER BY hook_embedding <=> :query_vec::vector
                    LIMIT :limit
                """), {
                    "query_vec": query_vec,
                    "threshold": threshold,
                    "limit": limit
                })
                
                results = []
                for row in result:
                    results.append(SimilarContent(
                        id=str(row[0]),
                        similarity=row[2],
                        metadata={"hooks": row[1]}
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"Similar hooks search failed: {e}")
            return []
    
    async def find_similar_competitor_content(
        self,
        query_text: str,
        threshold: float = 0.7,
        limit: int = 10
    ) -> List[SimilarContent]:
        """
        Find similar competitor content.
        
        Args:
            query_text: Text to search for
            threshold: Minimum similarity
            limit: Max results
            
        Returns:
            List of similar competitor audits
        """
        query_embedding = await self.generate_embedding(query_text)
        if not query_embedding:
            return []
        
        try:
            query_vec = self._format_vector(query_embedding)
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        d.audit_id,
                        d.hook_archetype,
                        d.angle_type,
                        a.handle,
                        a.platform,
                        1 - (d.topic_embedding <=> :query_vec::vector) as similarity
                    FROM competitor_deep_audit d
                    JOIN competitor_account a ON d.account_id = a.account_id
                    WHERE d.topic_embedding IS NOT NULL
                    AND 1 - (d.topic_embedding <=> :query_vec::vector) > :threshold
                    ORDER BY d.topic_embedding <=> :query_vec::vector
                    LIMIT :limit
                """), {
                    "query_vec": query_vec,
                    "threshold": threshold,
                    "limit": limit
                })
                
                results = []
                for row in result:
                    results.append(SimilarContent(
                        id=str(row[0]),
                        similarity=row[5],
                        metadata={
                            "hook_archetype": row[1],
                            "angle_type": row[2],
                            "handle": row[3],
                            "platform": row[4]
                        }
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"Similar competitor search failed: {e}")
            return []
    
    def _format_vector(self, embedding: List[float]) -> str:
        """Format embedding as PostgreSQL vector string"""
        return "[" + ",".join(str(x) for x in embedding) + "]"
    
    async def check_pgvector_enabled(self) -> bool:
        """Check if pgvector extension is enabled"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT extversion FROM pg_extension WHERE extname = 'vector'
                """))
                row = result.fetchone()
                if row:
                    logger.info(f"pgvector enabled: v{row[0]}")
                    return True
                return False
        except Exception as e:
            logger.error(f"pgvector check failed: {e}")
            return False

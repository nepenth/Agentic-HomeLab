"""
Vector Search Service for high-performance semantic search.

This service provides vector similarity search using pgvector and PostgreSQL,
integrating with the content and embedding database models for scalable search.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy import text, desc, and_, or_, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentEmbedding, ContentAnalytics
from app.services.semantic_processing import embedding_service, vector_operations
from app.services.model_selection_service import ModelSelector
from app.utils.logging import get_logger

logger = get_logger("vector_search_service")


@dataclass
class SearchQuery:
    """Represents a search query with various parameters."""
    query_text: str
    top_k: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)
    search_type: str = "semantic"  # semantic, keyword, hybrid
    model_name: Optional[str] = None
    include_metadata: bool = True
    min_score: float = 0.0


@dataclass
class SearchResult:
    """Individual search result."""
    content_item_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding_model: str = ""
    content_type: str = ""
    title: Optional[str] = None
    source_type: str = ""


@dataclass
class SearchResponse:
    """Complete search response."""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    search_type: str
    filters_applied: Dict[str, Any]


@dataclass
class IndexStats:
    """Indexing statistics."""
    total_documents: int
    total_embeddings: int
    indexed_content_types: List[str]
    last_indexed_at: Optional[datetime]
    average_embedding_dimensions: int


class VectorSearchService:
    """High-performance vector search service using pgvector."""

    def __init__(self, model_selector: Optional[ModelSelector] = None):
        self.model_selector = model_selector
        self.index_stats: Optional[IndexStats] = None

    async def search(self, query: SearchQuery) -> SearchResponse:
        """
        Perform vector similarity search.

        Args:
            query: SearchQuery object with search parameters

        Returns:
            SearchResponse with results and metadata
        """
        start_time = time.time()

        try:
            # Generate query embedding
            embedding_result = await embedding_service.generate_embedding(
                text=query.query_text,
                model_name=query.model_name
            )

            query_embedding = embedding_result.embedding

            # Perform search based on type
            if query.search_type == "semantic":
                results = await self._semantic_search(query_embedding, query)
            elif query.search_type == "hybrid":
                results = await self._hybrid_search(query_embedding, query)
            else:
                results = await self._semantic_search(query_embedding, query)

            search_time = (time.time() - start_time) * 1000

            response = SearchResponse(
                query=query.query_text,
                results=results,
                total_results=len(results),
                search_time_ms=search_time,
                search_type=query.search_type,
                filters_applied=query.filters
            )

            logger.info(f"Search completed: {len(results)} results in {search_time:.2f}ms")
            return response

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def _semantic_search(self, query_embedding: List[float], query: SearchQuery) -> List[SearchResult]:
        """Perform pure semantic vector search."""
        db = next(get_db())

        try:
            # Build the vector similarity query
            similarity_query = text("""
                SELECT
                    ce.content_item_id,
                    ce.embedding_vector <=> :query_embedding as similarity_score,
                    ce.embedding_model,
                    ci.title,
                    ci.content_type,
                    ci.source_type,
                    ci.metadata as content_metadata,
                    LEFT(ci.description, 500) as description
                FROM content_embeddings ce
                JOIN content_items ci ON ce.content_item_id = ci.id
                WHERE ce.embedding_vector <=> :query_embedding < :max_distance
                AND (:content_type_filter IS NULL OR ci.content_type = :content_type_filter)
                AND (:source_type_filter IS NULL OR ci.source_type = :source_type_filter)
                ORDER BY ce.embedding_vector <=> :query_embedding
                LIMIT :limit
            """)

            # Calculate max distance (1.0 - min_score for cosine similarity)
            max_distance = 1.0 - query.min_score

            # Apply filters
            content_type_filter = query.filters.get('content_type')
            source_type_filter = query.filters.get('source_type')

            params = {
                'query_embedding': query_embedding,
                'max_distance': max_distance,
                'limit': query.top_k,
                'content_type_filter': content_type_filter,
                'source_type_filter': source_type_filter
            }

            result = db.execute(similarity_query, params)
            rows = result.fetchall()

            # Convert to SearchResult objects
            results = []
            for row in rows:
                # Get content preview (first 500 chars or description)
                content_preview = row.description or ""
                if not content_preview and hasattr(row, 'content_metadata'):
                    # Try to extract content from metadata
                    pass

                result_obj = SearchResult(
                    content_item_id=str(row.content_item_id),
                    content=content_preview,
                    similarity_score=1.0 - row.similarity_score,  # Convert distance to similarity
                    metadata=row.content_metadata or {},
                    embedding_model=row.embedding_model,
                    content_type=row.content_type,
                    title=row.title,
                    source_type=row.source_type
                )
                results.append(result_obj)

            return results

        finally:
            db.close()

    async def _hybrid_search(self, query_embedding: List[float], query: SearchQuery) -> List[SearchResult]:
        """Perform hybrid search combining semantic and keyword search."""
        # For now, implement as semantic search
        # TODO: Implement full-text search + semantic search combination
        return await self._semantic_search(query_embedding, query)

    async def index_content(
        self,
        content_item_id: str,
        content_text: str,
        model_name: Optional[str] = None,
        chunk_strategy: str = "semantic"
    ) -> Dict[str, Any]:
        """
        Index content for search by generating and storing embeddings.

        Args:
            content_item_id: ID of the content item
            content_text: Text content to index
            model_name: Model to use for embedding
            chunk_strategy: Text chunking strategy

        Returns:
            Indexing result metadata
        """
        start_time = time.time()

        try:
            # Generate embedding
            embedding_result = await embedding_service.generate_embedding(
                text=content_text,
                model_name=model_name
            )

            # Store in database
            db = next(get_db())

            try:
                # Create embedding record
                embedding_record = ContentEmbedding(
                    content_item_id=content_item_id,
                    embedding_model=embedding_result.model_used,
                    embedding_dimensions=len(embedding_result.embedding),
                    embedding_vector=embedding_result.embedding,
                    content_chunk=content_text[:1000] if len(content_text) > 1000 else content_text,
                    generation_duration_ms=int(embedding_result.processing_time_ms),
                    embedding_quality_score=0.9  # TODO: Implement quality scoring
                )

                db.add(embedding_record)
                db.commit()

                indexing_time = (time.time() - start_time) * 1000

                result = {
                    "content_item_id": content_item_id,
                    "embedding_model": embedding_result.model_used,
                    "dimensions": len(embedding_result.embedding),
                    "tokens_used": embedding_result.token_count,
                    "processing_time_ms": indexing_time,
                    "status": "indexed"
                }

                logger.info(f"Content indexed: {content_item_id} with model {embedding_result.model_used}")
                return result

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to index content {content_item_id}: {e}")
            raise

    async def batch_index_content(
        self,
        content_items: List[Dict[str, Any]],
        model_name: Optional[str] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Batch index multiple content items.

        Args:
            content_items: List of content items with id and text
            model_name: Model to use for embeddings
            batch_size: Number of items to process in each batch

        Returns:
            Batch indexing results
        """
        total_items = len(content_items)
        successful = 0
        failed = 0
        results = []

        for i in range(0, total_items, batch_size):
            batch = content_items[i:i + batch_size]

            # Process batch concurrently
            tasks = []
            for item in batch:
                task = self.index_content(
                    content_item_id=item['id'],
                    content_text=item['text'],
                    model_name=model_name
                )
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    failed += 1
                    logger.error(f"Failed to index item {batch[j]['id']}: {result}")
                else:
                    successful += 1
                    results.append(result)

        return {
            "total_items": total_items,
            "successful": successful,
            "failed": failed,
            "results": results
        }

    async def remove_from_index(self, content_item_id: str) -> bool:
        """Remove content from search index."""
        db = next(get_db())

        try:
            # Delete embeddings for this content item
            deleted_count = db.query(ContentEmbedding).filter(
                ContentEmbedding.content_item_id == content_item_id
            ).delete()

            db.commit()

            logger.info(f"Removed {deleted_count} embeddings for content {content_item_id}")
            return deleted_count > 0

        except Exception as e:
            logger.error(f"Failed to remove from index: {e}")
            db.rollback()
            return False

        finally:
            db.close()

    async def get_index_stats(self) -> IndexStats:
        """Get current indexing statistics."""
        db = next(get_db())

        try:
            # Count total documents
            total_docs = db.query(ContentItem).count()

            # Count total embeddings
            total_embeddings = db.query(ContentEmbedding).count()

            # Get content types
            content_types_result = db.query(ContentItem.content_type).distinct().all()
            content_types = [ct[0] for ct in content_types_result]

            # Get last indexed timestamp
            last_indexed = db.query(ContentEmbedding.generated_at).order_by(
                desc(ContentEmbedding.generated_at)
            ).first()

            # Get average embedding dimensions
            avg_dims_result = db.query(func.avg(ContentEmbedding.embedding_dimensions)).first()
            avg_dims = int(avg_dims_result[0]) if avg_dims_result[0] else 0

            stats = IndexStats(
                total_documents=total_docs,
                total_embeddings=total_embeddings,
                indexed_content_types=content_types,
                last_indexed_at=last_indexed[0] if last_indexed else None,
                average_embedding_dimensions=avg_dims
            )

            self.index_stats = stats
            return stats

        finally:
            db.close()

    async def reindex_content(
        self,
        content_item_ids: Optional[List[str]] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reindex content items.

        Args:
            content_item_ids: Specific content IDs to reindex (None for all)
            model_name: Model to use for reindexing

        Returns:
            Reindexing results
        """
        db = next(get_db())

        try:
            # Get content items to reindex
            query = db.query(ContentItem)
            if content_item_ids:
                query = query.filter(ContentItem.id.in_(content_item_ids))

            content_items = query.all()

            # Prepare for batch indexing
            items_to_index = []
            for item in content_items:
                # Get content text (from description or other fields)
                content_text = item.description or ""
                if not content_text and item.metadata:
                    # Try to extract from metadata
                    content_text = item.metadata.get('content', '')

                if content_text:
                    items_to_index.append({
                        'id': str(item.id),
                        'text': content_text
                    })

            # Remove existing embeddings first
            if content_item_ids:
                db.query(ContentEmbedding).filter(
                    ContentEmbedding.content_item_id.in_(content_item_ids)
                ).delete()
            else:
                db.query(ContentEmbedding).delete()

            db.commit()

            # Batch index
            if items_to_index:
                result = await self.batch_index_content(
                    content_items=items_to_index,
                    model_name=model_name
                )
                return result
            else:
                return {"message": "No content to reindex"}

        finally:
            db.close()


# Global instance
vector_search_service = VectorSearchService()
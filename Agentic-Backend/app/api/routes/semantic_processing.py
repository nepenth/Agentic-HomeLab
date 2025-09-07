"""
API routes for Semantic Processing Infrastructure.

This module provides REST endpoints for embeddings, vector operations,
content chunking, semantic search, and quality assessment.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.semantic_processing import (
    embedding_service,
    vector_operations,
    semantic_search,
    quality_scorer,
    model_usage_tracker,
    TextChunker,
    ChunkingStrategy,
    VectorOperation
)
from app.utils.logging import get_logger

logger = get_logger("semantic_processing_routes")

router = APIRouter(prefix="/semantic", tags=["Semantic Processing"])


# Pydantic models for request/response
class EmbeddingRequest(BaseModel):
    """Embedding generation request."""
    text: str = Field(..., description="Text to generate embeddings for")
    model_name: Optional[str] = Field(default=None, description="Specific model to use")
    chunk_strategy: Optional[str] = Field(default="semantic", description="Text chunking strategy")


class EmbeddingResponse(BaseModel):
    """Embedding generation response."""
    text: str
    embedding: List[float]
    model_used: str
    token_count: int
    processing_time_ms: float
    chunk_count: int
    timestamp: datetime


class BatchEmbeddingRequest(BaseModel):
    """Batch embedding generation request."""
    texts: List[str] = Field(..., description="List of texts to embed")
    model_name: Optional[str] = Field(default=None, description="Specific model to use")
    batch_size: int = Field(default=10, description="Batch size for processing")


class BatchEmbeddingResponse(BaseModel):
    """Batch embedding response."""
    total_texts: int
    processed_texts: int
    failed_texts: int
    results: List[EmbeddingResponse]
    processing_time_ms: float
    timestamp: datetime


class SearchRequest(BaseModel):
    """Semantic search request."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, description="Number of results to return")
    model_name: Optional[str] = Field(default=None, description="Embedding model to use")


class SearchResult(BaseModel):
    """Individual search result."""
    item_id: str
    content: str
    similarity_score: float


class SearchResponse(BaseModel):
    """Semantic search response."""
    query_text: str
    results: List[SearchResult]
    search_time_ms: float
    total_candidates: int
    timestamp: datetime


class ClusteringRequest(BaseModel):
    """Content clustering request."""
    content_items: List[Dict[str, Any]] = Field(..., description="List of content items with IDs and texts")
    n_clusters: int = Field(default=5, description="Number of clusters to create")
    model_name: Optional[str] = Field(default=None, description="Embedding model to use")


class ClusteringResponse(BaseModel):
    """Clustering response."""
    clusters: List[Dict[str, Any]]
    centroids: List[List[float]]
    labels: List[int]
    silhouette_score: Optional[float]
    processing_time_ms: float
    timestamp: datetime


class ChunkingRequest(BaseModel):
    """Text chunking request."""
    text: str = Field(..., description="Text to chunk")
    strategy: str = Field(default="semantic", description="Chunking strategy")
    max_chunk_size: int = Field(default=512, description="Maximum chunk size")
    overlap: int = Field(default=50, description="Overlap between chunks")


class TextChunk(BaseModel):
    """Text chunk response."""
    content: str
    start_pos: int
    end_pos: int
    chunk_index: int
    token_count: int
    sentence_count: int
    metadata: Dict[str, Any]


class ChunkingResponse(BaseModel):
    """Text chunking response."""
    original_text_length: int
    chunk_count: int
    chunks: List[TextChunk]
    strategy_used: str
    processing_time_ms: float
    timestamp: datetime


class QualityScoreRequest(BaseModel):
    """Quality scoring request."""
    text: str = Field(..., description="Text to score")
    content_type: str = Field(default="text", description="Content type for scoring")


class QualityScoreResponse(BaseModel):
    """Quality scoring response."""
    overall_score: float
    readability_score: float
    coherence_score: float
    informativeness_score: float
    metrics: Dict[str, Any]
    content_type: str
    processing_time_ms: float
    timestamp: datetime


class ModelUsageStats(BaseModel):
    """Model usage statistics."""
    model_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_processing_time_ms: float
    average_tokens_per_request: float
    success_rate: float
    task_distribution: Dict[str, int]
    content_type_distribution: Dict[str, int]


@router.post("/embed", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """
    Generate embeddings for text.

    This endpoint generates vector embeddings for the provided text using
    the specified or automatically selected embedding model.
    """
    start_time = datetime.now()

    try:
        # Convert chunking strategy
        try:
            chunk_strategy = ChunkingStrategy(request.chunk_strategy)
        except ValueError:
            chunk_strategy = ChunkingStrategy.SEMANTIC

        # Generate embedding
        result = await embedding_service.generate_embedding(
            text=request.text,
            model_name=request.model_name,
            chunk_strategy=chunk_strategy
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        response = EmbeddingResponse(
            text=result.text,
            embedding=result.embedding,
            model_used=result.model_used,
            token_count=result.token_count,
            processing_time_ms=result.processing_time_ms,
            chunk_count=1,  # Single embedding for now
            timestamp=datetime.now()
        )

        logger.info(f"Generated embedding using model {result.model_used} for {result.token_count} tokens")
        return response

    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")


@router.post("/embed/batch", response_model=BatchEmbeddingResponse)
async def generate_batch_embeddings(request: BatchEmbeddingRequest) -> BatchEmbeddingResponse:
    """
    Generate embeddings for multiple texts.

    This endpoint processes multiple texts in batches for efficient embedding generation.
    """
    start_time = datetime.now()

    try:
        # Generate batch embeddings
        results = await embedding_service.generate_multiple_embeddings(
            texts=request.texts,
            model_name=request.model_name,
            batch_size=request.batch_size
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Convert results to response format
        response_results = []
        for result in results:
            if hasattr(result, 'text'):  # Check if it's a valid result
                response_results.append(EmbeddingResponse(
                    text=result.text,
                    embedding=result.embedding,
                    model_used=result.model_used,
                    token_count=result.token_count,
                    processing_time_ms=result.processing_time_ms,
                    chunk_count=1,
                    timestamp=datetime.now()
                ))

        response = BatchEmbeddingResponse(
            total_texts=len(request.texts),
            processed_texts=len(response_results),
            failed_texts=len(request.texts) - len(response_results),
            results=response_results,
            processing_time_ms=processing_time,
            timestamp=datetime.now()
        )

        logger.info(f"Batch processed {len(request.texts)} texts: {len(response_results)} successful")
        return response

    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate batch embeddings: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def perform_semantic_search(request: SearchRequest) -> SearchResponse:
    """
    Perform semantic search.

    This endpoint performs semantic similarity search using vector embeddings
    to find the most relevant content for the given query.
    """
    try:
        # Perform search
        result = await semantic_search.search(
            query=request.query,
            top_k=request.top_k,
            model_name=request.model_name
        )

        # Convert results to response format
        search_results = []
        for item in result.similar_items:
            search_results.append(SearchResult(
                item_id=item['item_id'],
                content=item['content'],
                similarity_score=item['similarity_score']
            ))

        response = SearchResponse(
            query_text=result.query_text,
            results=search_results,
            search_time_ms=result.search_time_ms,
            total_candidates=result.total_candidates,
            timestamp=datetime.now()
        )

        logger.info(f"Semantic search completed: {len(search_results)} results in {result.search_time_ms:.2f}ms")
        return response

    except Exception as e:
        logger.error(f"Failed to perform semantic search: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to perform semantic search: {str(e)}")


@router.post("/cluster", response_model=ClusteringResponse)
async def perform_clustering(request: ClusteringRequest) -> ClusteringResponse:
    """
    Perform content clustering.

    This endpoint clusters content items based on their semantic similarity
    using vector embeddings and K-means clustering.
    """
    try:
        # Prepare embeddings for clustering
        embeddings_data = []
        for item in request.content_items:
            item_id = item.get('id', str(hash(item.get('text', ''))))
            text = item.get('text', '')

            # Generate embedding for this item
            embedding_result = await embedding_service.generate_embedding(
                text=text,
                model_name=request.model_name
            )

            embeddings_data.append((item_id, embedding_result.embedding))

        # Perform clustering
        result = vector_operations.cluster_embeddings(
            embeddings=embeddings_data,
            n_clusters=request.n_clusters
        )

        response = ClusteringResponse(
            clusters=result.clusters,
            centroids=result.centroids,
            labels=result.labels,
            silhouette_score=result.silhouette_score,
            processing_time_ms=result.processing_time_ms,
            timestamp=datetime.now()
        )

        logger.info(f"Clustering completed: {len(result.clusters)} clusters created")
        return response

    except Exception as e:
        logger.error(f"Failed to perform clustering: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to perform clustering: {str(e)}")


@router.post("/chunk", response_model=ChunkingResponse)
async def chunk_text(request: ChunkingRequest) -> ChunkingResponse:
    """
    Chunk text using intelligent strategies.

    This endpoint splits text into semantically meaningful chunks
    using various chunking strategies for optimal processing.
    """
    start_time = datetime.now()

    try:
        # Convert chunking strategy
        try:
            strategy = ChunkingStrategy(request.strategy)
        except ValueError:
            strategy = ChunkingStrategy.SEMANTIC

        # Create chunker with custom settings
        chunker = TextChunker(
            max_chunk_size=request.max_chunk_size,
            overlap=request.overlap
        )

        # Perform chunking
        chunks = chunker.chunk_text(request.text, strategy)

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Convert chunks to response format
        response_chunks = []
        for chunk in chunks:
            response_chunks.append(TextChunk(
                content=chunk.content,
                start_pos=chunk.start_pos,
                end_pos=chunk.end_pos,
                chunk_index=chunk.chunk_index,
                token_count=chunk.token_count,
                sentence_count=chunk.sentence_count,
                metadata=chunk.metadata
            ))

        response = ChunkingResponse(
            original_text_length=len(request.text),
            chunk_count=len(chunks),
            chunks=response_chunks,
            strategy_used=strategy.value,
            processing_time_ms=processing_time,
            timestamp=datetime.now()
        )

        logger.info(f"Text chunking completed: {len(chunks)} chunks created using {strategy.value} strategy")
        return response

    except Exception as e:
        logger.error(f"Failed to chunk text: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to chunk text: {str(e)}")


@router.post("/quality", response_model=QualityScoreResponse)
async def score_content_quality(request: QualityScoreRequest) -> QualityScoreResponse:
    """
    Score content quality.

    This endpoint assesses the quality of content using various metrics
    including readability, coherence, and informativeness.
    """
    start_time = datetime.now()

    try:
        # Convert content type
        from app.services.content_framework import ContentType
        try:
            content_type = ContentType(request.content_type)
        except ValueError:
            content_type = ContentType.TEXT

        # Score quality
        score = quality_scorer.score_content(request.text, content_type)

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        response = QualityScoreResponse(
            overall_score=score.overall_score,
            readability_score=score.readability_score,
            coherence_score=score.coherence_score,
            informativeness_score=score.informativeness_score,
            metrics=score.metrics,
            content_type=request.content_type,
            processing_time_ms=processing_time,
            timestamp=datetime.now()
        )

        logger.info(f"Quality scoring completed: {score.overall_score:.2f} overall score")
        return response

    except Exception as e:
        logger.error(f"Failed to score content quality: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to score content quality: {str(e)}")


@router.get("/usage/stats")
async def get_model_usage_stats(model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get model usage statistics.

    Returns comprehensive usage statistics for models in the semantic processing system.
    """
    try:
        if model_name:
            stats = model_usage_tracker.get_usage_stats(model_name)
            if not stats:
                raise HTTPException(status_code=404, detail=f"No usage stats found for model: {model_name}")
            return stats
        else:
            return model_usage_tracker.get_usage_stats()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage stats: {str(e)}")


@router.post("/index")
async def index_content_for_search(
    item_id: str,
    text: str,
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Index content for semantic search.

    This endpoint adds content to the semantic search index for future similarity searches.
    """
    try:
        await semantic_search.index_content(item_id, text, model_name)

        response = {
            "message": f"Content indexed successfully for item {item_id}",
            "item_id": item_id,
            "model_used": model_name,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Content indexed for search: {item_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to index content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to index content: {str(e)}")


@router.delete("/index/{item_id}")
async def remove_from_search_index(item_id: str) -> Dict[str, Any]:
    """
    Remove content from search index.

    This endpoint removes content from the semantic search index.
    """
    try:
        semantic_search.remove_from_index(item_id)

        response = {
            "message": f"Content removed from search index: {item_id}",
            "item_id": item_id,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Content removed from search index: {item_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to remove from index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove from index: {str(e)}")


@router.get("/similarity")
async def calculate_similarity(
    text1: str,
    text2: str,
    operation: str = "cosine_similarity",
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate similarity between two texts.

    This endpoint calculates semantic similarity between two text inputs
    using various vector operations.
    """
    try:
        # Generate embeddings
        emb1_result = await embedding_service.generate_embedding(text1, model_name)
        emb2_result = await embedding_service.generate_embedding(text2, model_name)

        # Calculate similarity
        try:
            vector_op = VectorOperation(operation)
        except ValueError:
            vector_op = VectorOperation.COSINE_SIMILARITY

        if vector_op == VectorOperation.COSINE_SIMILARITY:
            score = vector_operations.cosine_similarity(emb1_result.embedding, emb2_result.embedding)
        elif vector_op == VectorOperation.EUCLIDEAN_DISTANCE:
            score = vector_operations.euclidean_distance(emb1_result.embedding, emb2_result.embedding)
        elif vector_op == VectorOperation.DOT_PRODUCT:
            score = vector_operations.dot_product(emb1_result.embedding, emb2_result.embedding)
        elif vector_op == VectorOperation.MANHATTAN_DISTANCE:
            score = vector_operations.manhattan_distance(emb1_result.embedding, emb2_result.embedding)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")

        response = {
            "text1_preview": text1[:100] + "..." if len(text1) > 100 else text1,
            "text2_preview": text2[:100] + "..." if len(text2) > 100 else text2,
            "similarity_score": score,
            "operation": operation,
            "model_used": emb1_result.model_used,
            "timestamp": datetime.now().isoformat()
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate similarity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate similarity: {str(e)}")


@router.get("/capabilities")
async def get_semantic_capabilities() -> Dict[str, Any]:
    """
    Get semantic processing capabilities.

    Returns information about available models, operations, and features
    in the semantic processing system.
    """
    try:
        capabilities = {
            "embedding_models": ["nomic-embed-text", "all-MiniLM"],
            "text_models": ["llama2", "codellama", "mistral"],
            "chunking_strategies": ["fixed_size", "sentence_based", "semantic", "overlapping"],
            "vector_operations": ["cosine_similarity", "euclidean_distance", "dot_product", "manhattan_distance"],
            "clustering_algorithms": ["kmeans"],
            "quality_metrics": ["readability", "coherence", "informativeness"],
            "supported_content_types": ["text", "image", "audio", "video", "document"],
            "features": [
                "automatic_model_selection",
                "intelligent_chunking",
                "semantic_search",
                "content_clustering",
                "quality_assessment",
                "usage_tracking"
            ]
        }

        response = {
            "capabilities": capabilities,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")
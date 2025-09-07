"""
Semantic Processing API Routes.

This module provides REST API endpoints for semantic processing including:
- Text embeddings and vector search
- Knowledge graph construction and querying
- Semantic duplicate detection
- Entity extraction and relationship mapping
- Content classification and importance scoring
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.semantic_processing_service import (
    semantic_processing_service,
    SemanticSearchResult,
    DuplicateDetectionResult,
    KnowledgeEntity,
    KnowledgeRelation
)
from app.api.dependencies import get_db_session, verify_api_key
from app.utils.logging import get_logger

logger = get_logger("semantic_api")
router = APIRouter(
    tags=["Semantic Processing"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Embedding and Vector Operations
# ============================================================================

@router.post("/embed", response_model=Dict[str, Any])
async def generate_embeddings(
    text: str = Body(..., description="Text to generate embeddings for"),
    model_name: Optional[str] = Body(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Generate embeddings for the provided text."""
    try:
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        if len(text) > 10000:  # Limit text length
            raise HTTPException(
                status_code=400,
                detail="Text too long (maximum 10,000 characters)"
            )

        # Generate embeddings
        embedding = await semantic_processing_service.generate_embedding(text, model_name)

        return {
            "status": "success",
            "data": {
                "embedding": embedding,
                "dimensions": len(embedding),
                "model_used": model_name or semantic_processing_service.embedding_model,
                "text_length": len(text),
                "generated_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings: {str(e)}"
        )


@router.post("/search", response_model=Dict[str, Any])
async def semantic_search(
    query: str = Body(..., description="Search query"),
    top_k: int = Body(10, ge=1, le=50, description="Number of results to return"),
    threshold: float = Body(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    source_filter: Optional[str] = Body(None, description="Filter by source ID"),
    current_user: Dict = Depends(verify_api_key)
):
    """Perform semantic search using vector similarity."""
    try:
        if not query or not query.strip():
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )

        # Perform semantic search
        results = await semantic_processing_service.semantic_search(
            query=query,
            top_k=top_k,
            threshold=threshold,
            source_filter=source_filter
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "content_id": result.content_id,
                "content": result.content,
                "similarity_score": result.similarity_score,
                "metadata": result.metadata,
                "source_id": result.source_id
            })

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "search_parameters": {
                    "top_k": top_k,
                    "threshold": threshold,
                    "source_filter": source_filter
                },
                "searched_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform semantic search: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform semantic search: {str(e)}"
        )


@router.post("/chunk", response_model=Dict[str, Any])
async def chunk_text(
    text: str = Body(..., description="Text to chunk"),
    source_id: str = Body(..., description="Source identifier"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="Additional metadata"),
    current_user: Dict = Depends(verify_api_key)
):
    """Split text into semantically meaningful chunks."""
    try:
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        if not source_id:
            raise HTTPException(
                status_code=400,
                detail="Source ID is required"
            )

        # Chunk the text
        chunks = await semantic_processing_service.chunk_text(
            text=text,
            source_id=source_id,
            metadata=metadata
        )

        # Format results
        formatted_chunks = []
        for chunk in chunks:
            formatted_chunks.append({
                "id": chunk.id,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata,
                "source_id": chunk.source_id,
                "created_at": chunk.created_at.isoformat()
            })

        return {
            "status": "success",
            "data": {
                "source_id": source_id,
                "total_chunks": len(formatted_chunks),
                "chunks": formatted_chunks,
                "chunking_parameters": {
                    "chunk_size": semantic_processing_service.chunk_size,
                    "chunk_overlap": semantic_processing_service.chunk_overlap
                },
                "processed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to chunk text: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to chunk text: {str(e)}"
        )


# ============================================================================
# Duplicate Detection
# ============================================================================

@router.post("/detect-duplicates", response_model=Dict[str, Any])
async def detect_duplicates(
    content_id: str = Body(..., description="ID of content to check"),
    content: str = Body(..., description="Content text to analyze"),
    threshold: Optional[float] = Body(None, ge=0.0, le=1.0, description="Similarity threshold"),
    current_user: Dict = Depends(verify_api_key)
):
    """Detect duplicate or similar content."""
    try:
        if not content_id:
            raise HTTPException(
                status_code=400,
                detail="Content ID is required"
            )

        if not content or not content.strip():
            raise HTTPException(
                status_code=400,
                detail="Content cannot be empty"
            )

        # Detect duplicates
        duplicates = await semantic_processing_service.detect_duplicates(
            content_id=content_id,
            content=content,
            threshold=threshold
        )

        # Format results
        formatted_duplicates = []
        for duplicate in duplicates:
            formatted_duplicates.append({
                "original_content_id": duplicate.original_content_id,
                "duplicate_content_id": duplicate.duplicate_content_id,
                "similarity_score": duplicate.similarity_score,
                "duplicate_type": duplicate.duplicate_type,
                "confidence": duplicate.confidence
            })

        return {
            "status": "success",
            "data": {
                "content_id": content_id,
                "total_duplicates": len(formatted_duplicates),
                "duplicates": formatted_duplicates,
                "detection_parameters": {
                    "threshold": threshold or semantic_processing_service.similarity_threshold
                },
                "analyzed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect duplicates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect duplicates: {str(e)}"
        )


# ============================================================================
# Knowledge Graph Operations
# ============================================================================

@router.post("/extract-relations", response_model=Dict[str, Any])
async def extract_entities_and_relations(
    text: str = Body(..., description="Text to analyze for entities and relations"),
    source_id: str = Body(..., description="Source identifier"),
    current_user: Dict = Depends(verify_api_key)
):
    """Extract entities and build relationships for knowledge graph."""
    try:
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        if not source_id:
            raise HTTPException(
                status_code=400,
                detail="Source ID is required"
            )

        # Extract entities
        entities = await semantic_processing_service.extract_entities(text, source_id)

        # Build knowledge graph relationships
        relations = await semantic_processing_service.build_knowledge_graph(entities, text)

        # Format results
        formatted_entities = []
        for entity in entities:
            formatted_entities.append({
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "properties": entity.properties,
                "confidence": entity.confidence,
                "created_at": entity.created_at.isoformat()
            })

        formatted_relations = []
        for relation in relations:
            formatted_relations.append({
                "id": relation.id,
                "source_entity_id": relation.source_entity_id,
                "target_entity_id": relation.target_entity_id,
                "relation_type": relation.relation_type,
                "description": relation.description,
                "properties": relation.properties,
                "confidence": relation.confidence,
                "created_at": relation.created_at.isoformat()
            })

        return {
            "status": "success",
            "data": {
                "source_id": source_id,
                "entities": {
                    "total": len(formatted_entities),
                    "items": formatted_entities
                },
                "relations": {
                    "total": len(formatted_relations),
                    "items": formatted_relations
                },
                "processed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract entities and relations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract entities and relations: {str(e)}"
        )


@router.get("/entities", response_model=Dict[str, Any])
async def get_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of entities to return"),
    current_user: Dict = Depends(verify_api_key)
):
    """Get entities from the knowledge graph."""
    try:
        entities = list(semantic_processing_service.entities.values())

        # Filter by entity type if specified
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]

        # Sort by creation time (most recent first)
        entities.sort(key=lambda x: x.created_at, reverse=True)

        # Limit results
        entities = entities[:limit]

        # Format results
        formatted_entities = []
        for entity in entities:
            formatted_entities.append({
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "properties": entity.properties,
                "confidence": entity.confidence,
                "created_at": entity.created_at.isoformat()
            })

        return {
            "status": "success",
            "data": {
                "entities": formatted_entities,
                "total": len(formatted_entities),
                "filter": {"entity_type": entity_type} if entity_type else None,
                "limit": limit,
                "retrieved_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get entities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve entities: {str(e)}"
        )


@router.get("/relations", response_model=Dict[str, Any])
async def get_relations(
    relation_type: Optional[str] = Query(None, description="Filter by relation type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of relations to return"),
    current_user: Dict = Depends(verify_api_key)
):
    """Get relations from the knowledge graph."""
    try:
        relations = list(semantic_processing_service.relations.values())

        # Filter by relation type if specified
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]

        # Sort by creation time (most recent first)
        relations.sort(key=lambda x: x.created_at, reverse=True)

        # Limit results
        relations = relations[:limit]

        # Format results
        formatted_relations = []
        for relation in relations:
            formatted_relations.append({
                "id": relation.id,
                "source_entity_id": relation.source_entity_id,
                "target_entity_id": relation.target_entity_id,
                "relation_type": relation.relation_type,
                "description": relation.description,
                "properties": relation.properties,
                "confidence": relation.confidence,
                "created_at": relation.created_at.isoformat()
            })

        return {
            "status": "success",
            "data": {
                "relations": formatted_relations,
                "total": len(formatted_relations),
                "filter": {"relation_type": relation_type} if relation_type else None,
                "limit": limit,
                "retrieved_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get relations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve relations: {str(e)}"
        )


# ============================================================================
# Content Classification and Analysis
# ============================================================================

@router.post("/classify", response_model=Dict[str, Any])
async def classify_content(
    content: str = Body(..., description="Content to classify"),
    categories: List[str] = Body(..., description="List of possible categories"),
    current_user: Dict = Depends(verify_api_key)
):
    """Classify content into predefined categories."""
    try:
        if not content or not content.strip():
            raise HTTPException(
                status_code=400,
                detail="Content cannot be empty"
            )

        if not categories:
            raise HTTPException(
                status_code=400,
                detail="Categories list cannot be empty"
            )

        # Classify content
        classification = await semantic_processing_service.classify_content(content, categories)

        return {
            "status": "success",
            "data": {
                "content": content[:200] + "..." if len(content) > 200 else content,
                "categories": categories,
                "classification": classification,
                "top_category": max(classification.items(), key=lambda x: x[1]) if classification else None,
                "classified_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to classify content: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to classify content: {str(e)}"
        )


@router.post("/score-importance", response_model=Dict[str, Any])
async def score_importance(
    content: str = Body(..., description="Content to score"),
    context: Optional[str] = Body(None, description="Context for scoring"),
    current_user: Dict = Depends(verify_api_key)
):
    """Score the importance of content."""
    try:
        if not content or not content.strip():
            raise HTTPException(
                status_code=400,
                detail="Content cannot be empty"
            )

        # Score importance
        importance_score = await semantic_processing_service.score_importance(content, context)

        return {
            "status": "success",
            "data": {
                "content": content[:200] + "..." if len(content) > 200 else content,
                "context": context,
                "importance_score": importance_score,
                "importance_level": (
                    "high" if importance_score > 0.7 else
                    "medium" if importance_score > 0.4 else
                    "low"
                ),
                "scored_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to score importance: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to score importance: {str(e)}"
        )


# ============================================================================
# Service Health and Statistics
# ============================================================================

@router.get("/health", response_model=Dict[str, Any])
async def get_semantic_service_health():
    """Get semantic processing service health status."""
    try:
        stats = semantic_processing_service.get_stats()

        return {
            "status": "success",
            "data": {
                "service": "semantic_processing",
                "status": "healthy",
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get semantic service health: {e}")
        return {
            "status": "error",
            "data": {
                "service": "semantic_processing",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }


@router.get("/stats", response_model=Dict[str, Any])
async def get_semantic_service_stats(
    current_user: Dict = Depends(verify_api_key)
):
    """Get comprehensive semantic service statistics."""
    try:
        stats = semantic_processing_service.get_stats()

        return {
            "status": "success",
            "data": {
                "service_stats": stats,
                "configuration": {
                    "chunk_size": semantic_processing_service.chunk_size,
                    "chunk_overlap": semantic_processing_service.chunk_overlap,
                    "similarity_threshold": semantic_processing_service.similarity_threshold,
                    "entity_confidence_threshold": semantic_processing_service.entity_confidence_threshold
                },
                "generated_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get semantic service stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve semantic service stats: {str(e)}"
        )
"""
Search and Discovery API Routes.

This module provides REST endpoints for vector search, content recommendations,
query understanding, and advanced analytics.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.vector_search_service import (
    vector_search_service, SearchQuery, SearchResponse, IndexStats
)
from app.services.content_recommendation_service import (
    content_recommendation_engine, RecommendationRequest, UserContext
)
from app.services.query_understanding_service import (
    query_understanding_service, QueryAnalysis, QueryExpansion
)
from app.services.advanced_analytics_service import (
    advanced_analytics_service, AnalyticsReport, UsagePattern, ContentInsight, TrendAnalysis
)
from app.utils.logging import get_logger

logger = get_logger("search_routes")

router = APIRouter(prefix="/search", tags=["Search & Discovery"])


# Pydantic models for request/response
class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=10, description="Number of results to return")
    search_type: str = Field(default="semantic", description="Search type: semantic, keyword, hybrid")
    content_type_filter: Optional[str] = Field(default=None, description="Filter by content type")
    source_filter: Optional[str] = Field(default=None, description="Filter by source type")
    min_score: float = Field(default=0.0, description="Minimum similarity score")
    include_metadata: bool = Field(default=True, description="Include metadata in results")


class SearchResult(BaseModel):
    """Individual search result."""
    content_item_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    embedding_model: str
    content_type: str
    title: Optional[str]
    source_type: str


class SearchAPIResponse(BaseModel):
    """Search API response."""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    search_type: str
    filters_applied: Dict[str, Any]


class IndexContentRequest(BaseModel):
    """Content indexing request."""
    content_item_id: str = Field(..., description="Content item ID")
    content_text: str = Field(..., description="Content text to index")
    model_name: Optional[str] = Field(default=None, description="Embedding model to use")
    chunk_strategy: str = Field(default="semantic", description="Text chunking strategy")


class BatchIndexRequest(BaseModel):
    """Batch indexing request."""
    content_items: List[Dict[str, Any]] = Field(..., description="List of content items to index")
    model_name: Optional[str] = Field(default=None, description="Embedding model to use")
    batch_size: int = Field(default=10, description="Batch size for processing")


class RecommendationAPIRequest(BaseModel):
    """Recommendation request."""
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="User context for personalization")
    content_type_filter: Optional[str] = Field(default=None, description="Filter by content type")
    source_filter: Optional[str] = Field(default=None, description="Filter by source type")
    max_recommendations: int = Field(default=10, description="Maximum recommendations to return")
    diversity_factor: float = Field(default=0.7, description="Diversity factor (0.0-1.0)")
    freshness_weight: float = Field(default=0.3, description="Freshness weight")
    popularity_weight: float = Field(default=0.2, description="Popularity weight")
    similarity_weight: float = Field(default=0.5, description="Similarity weight")


class ContentRecommendation(BaseModel):
    """Content recommendation."""
    content_item_id: str
    title: Optional[str]
    content_type: str
    source_type: str
    recommendation_score: float
    recommendation_reason: str
    metadata: Dict[str, Any]


class RecommendationAPIResponse(BaseModel):
    """Recommendation API response."""
    recommendations: List[ContentRecommendation]
    total_recommendations: int
    processing_time_ms: float
    recommendation_strategy: str


class QueryAnalysisRequest(BaseModel):
    """Query analysis request."""
    query: str = Field(..., description="Query to analyze")


class QueryAnalysisResponse(BaseModel):
    """Query analysis response."""
    original_query: str
    cleaned_query: str
    query_type: str
    intent: str
    entities: List[str]
    keywords: List[str]
    topics: List[str]
    sentiment: str
    complexity: str
    confidence_score: float
    suggested_expansions: List[str]
    related_queries: List[str]
    processing_time_ms: float


class QueryExpansionRequest(BaseModel):
    """Query expansion request."""
    query: str = Field(..., description="Query to expand")
    expansion_type: str = Field(default="auto", description="Expansion type: auto, synonym, related, contextual")


class QueryExpansionResponse(BaseModel):
    """Query expansion response."""
    original_query: str
    expanded_query: str
    expansion_type: str
    confidence_score: float
    reasoning: str


class AnalyticsReportRequest(BaseModel):
    """Analytics report request."""
    time_period_days: int = Field(default=30, description="Time period in days")
    include_trends: bool = Field(default=True, description="Include trend analysis")
    include_insights: bool = Field(default=True, description="Include content insights")


class AnalyticsReportResponse(BaseModel):
    """Analytics report response."""
    report_type: str
    time_period: str
    total_content: int
    total_users: int
    key_metrics: Dict[str, float]
    usage_patterns: List[Dict[str, Any]]
    content_insights: List[Dict[str, Any]]
    trends: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime


# Search endpoints
@router.post("/", response_model=SearchAPIResponse)
async def perform_search(request: SearchRequest) -> SearchAPIResponse:
    """
    Perform semantic search across indexed content.

    This endpoint performs vector similarity search to find the most relevant
    content for the given query using advanced semantic understanding.
    """
    try:
        # Convert request to SearchQuery
        search_query = SearchQuery(
            query_text=request.query,
            top_k=request.top_k,
            search_type=request.search_type,
            filters={
                'content_type': request.content_type_filter,
                'source_type': request.source_filter
            },
            min_score=request.min_score,
            include_metadata=request.include_metadata
        )

        # Perform search
        response = await vector_search_service.search(search_query)

        # Convert to API response format
        api_results = []
        for result in response.results:
            api_result = SearchResult(
                content_item_id=result.content_item_id,
                content=result.content,
                similarity_score=result.similarity_score,
                metadata=result.metadata,
                embedding_model=result.embedding_model,
                content_type=result.content_type,
                title=result.title,
                source_type=result.source_type
            )
            api_results.append(api_result)

        api_response = SearchAPIResponse(
            query=response.query,
            results=api_results,
            total_results=response.total_results,
            search_time_ms=response.search_time_ms,
            search_type=response.search_type,
            filters_applied=response.filters_applied
        )

        logger.info(f"Search completed: {len(api_results)} results for query '{request.query}'")
        return api_response

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/index", response_model=Dict[str, Any])
async def index_content(request: IndexContentRequest) -> Dict[str, Any]:
    """
    Index content for search.

    This endpoint adds content to the search index by generating embeddings
    and storing them for future similarity searches.
    """
    try:
        result = await vector_search_service.index_content(
            content_item_id=request.content_item_id,
            content_text=request.content_text,
            model_name=request.model_name,
            chunk_strategy=request.chunk_strategy
        )

        logger.info(f"Content indexed: {request.content_item_id}")
        return result

    except Exception as e:
        logger.error(f"Content indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content indexing failed: {str(e)}")


@router.post("/index/batch", response_model=Dict[str, Any])
async def batch_index_content(request: BatchIndexRequest) -> Dict[str, Any]:
    """
    Batch index multiple content items.

    This endpoint efficiently indexes multiple content items in batches
    for optimal performance.
    """
    try:
        result = await vector_search_service.batch_index_content(
            content_items=request.content_items,
            model_name=request.model_name,
            batch_size=request.batch_size
        )

        logger.info(f"Batch indexing completed: {result['successful']} successful, {result['failed']} failed")
        return result

    except Exception as e:
        logger.error(f"Batch indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch indexing failed: {str(e)}")


@router.delete("/index/{content_item_id}", response_model=Dict[str, Any])
async def remove_from_index(content_item_id: str) -> Dict[str, Any]:
    """
    Remove content from search index.

    This endpoint removes content from the search index.
    """
    try:
        success = await vector_search_service.remove_from_index(content_item_id)

        if success:
            result = {
                "message": f"Content removed from search index: {content_item_id}",
                "content_item_id": content_item_id,
                "status": "removed"
            }
        else:
            result = {
                "message": f"Content not found in search index: {content_item_id}",
                "content_item_id": content_item_id,
                "status": "not_found"
            }

        logger.info(f"Index removal result: {result['status']} for {content_item_id}")
        return result

    except Exception as e:
        logger.error(f"Index removal failed: {e}")
        raise HTTPException(status_code=500, detail=f"Index removal failed: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_index_stats() -> Dict[str, Any]:
    """
    Get search index statistics.

    Returns comprehensive statistics about the search index including
    total documents, embeddings, and performance metrics.
    """
    try:
        stats = await vector_search_service.get_index_stats()

        return {
            "total_documents": stats.total_documents,
            "total_embeddings": stats.total_embeddings,
            "indexed_content_types": stats.indexed_content_types,
            "last_indexed_at": stats.last_indexed_at.isoformat() if stats.last_indexed_at else None,
            "average_embedding_dimensions": stats.average_embedding_dimensions
        }

    except Exception as e:
        logger.error(f"Failed to get index stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get index stats: {str(e)}")


@router.post("/reindex", response_model=Dict[str, Any])
async def reindex_content(
    content_item_ids: Optional[List[str]] = None,
    model_name: Optional[str] = None,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Reindex content items.

    This endpoint reindexes specified content items or all content if none specified.
    Can run in background for large reindexing operations.
    """
    try:
        # For large reindexing, run in background
        if not content_item_ids or len(content_item_ids) > 100:
            background_tasks.add_task(
                vector_search_service.reindex_content,
                content_item_ids,
                model_name
            )

            return {
                "message": "Reindexing started in background",
                "content_items": len(content_item_ids) if content_item_ids else "all",
                "status": "background"
            }

        # For smaller reindexing, run synchronously
        result = await vector_search_service.reindex_content(
            content_item_ids=content_item_ids,
            model_name=model_name
        )

        logger.info(f"Reindexing completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Reindexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


# Recommendation endpoints
@router.post("/recommend", response_model=RecommendationAPIResponse)
async def get_recommendations(request: RecommendationAPIRequest) -> RecommendationAPIResponse:
    """
    Get personalized content recommendations.

    This endpoint provides AI-powered content recommendations based on user behavior,
    content similarity, popularity, and contextual relevance.
    """
    try:
        # Convert user context
        user_context = None
        if request.user_context:
            user_context = UserContext(
                user_id=request.user_context.get('user_id'),
                recent_interactions=request.user_context.get('recent_interactions', []),
                preferred_content_types=request.user_context.get('preferred_content_types', []),
                preferred_sources=request.user_context.get('preferred_sources', []),
                interaction_history=request.user_context.get('interaction_history', {})
            )

        # Create recommendation request
        rec_request = RecommendationRequest(
            user_context=user_context,
            content_type_filter=request.content_type_filter,
            source_filter=request.source_filter,
            max_recommendations=request.max_recommendations,
            diversity_factor=request.diversity_factor,
            freshness_weight=request.freshness_weight,
            popularity_weight=request.popularity_weight,
            similarity_weight=request.similarity_weight
        )

        # Get recommendations
        response = await content_recommendation_engine.get_recommendations(rec_request)

        # Convert to API response format
        api_recommendations = []
        for rec in response.recommendations:
            api_rec = ContentRecommendation(
                content_item_id=rec.content_item_id,
                title=rec.title,
                content_type=rec.content_type,
                source_type=rec.source_type,
                recommendation_score=rec.recommendation_score,
                recommendation_reason=rec.recommendation_reason,
                metadata=rec.metadata
            )
            api_recommendations.append(api_rec)

        api_response = RecommendationAPIResponse(
            recommendations=api_recommendations,
            total_recommendations=response.total_recommendations,
            processing_time_ms=response.processing_time_ms,
            recommendation_strategy=response.recommendation_strategy
        )

        logger.info(f"Recommendations generated: {len(api_recommendations)} items")
        return api_response

    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {str(e)}")


@router.get("/recommend/trending", response_model=List[ContentRecommendation])
async def get_trending_content(
    time_window_hours: int = Query(default=24, description="Time window in hours"),
    limit: int = Query(default=10, description="Maximum results")
) -> List[ContentRecommendation]:
    """
    Get trending content based on recent engagement.

    Returns content that has shown significant activity in the specified time window.
    """
    try:
        trending = await content_recommendation_engine.get_trending_content(
            time_window_hours=time_window_hours,
            limit=limit
        )

        # Convert to API format
        api_trending = []
        for item in trending:
            api_item = ContentRecommendation(
                content_item_id=item.content_item_id,
                title=item.title,
                content_type=item.content_type,
                source_type=item.source_type,
                recommendation_score=item.recommendation_score,
                recommendation_reason=item.recommendation_reason,
                metadata=item.metadata
            )
            api_trending.append(api_item)

        logger.info(f"Trending content retrieved: {len(api_trending)} items")
        return api_trending

    except Exception as e:
        logger.error(f"Trending content retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trending content retrieval failed: {str(e)}")


@router.get("/recommend/similar/{content_item_id}", response_model=List[ContentRecommendation])
async def get_similar_content(
    content_item_id: str,
    limit: int = Query(default=5, description="Maximum similar items")
) -> List[ContentRecommendation]:
    """
    Get content similar to the specified item.

    Uses vector similarity to find content with similar semantic meaning.
    """
    try:
        similar = await content_recommendation_engine.get_similar_content(
            content_item_id=content_item_id,
            limit=limit
        )

        # Convert to API format
        api_similar = []
        for item in similar:
            api_item = ContentRecommendation(
                content_item_id=item.content_item_id,
                title=item.title,
                content_type=item.content_type,
                source_type=item.source_type,
                recommendation_score=item.recommendation_score,
                recommendation_reason=item.recommendation_reason,
                metadata=item.metadata
            )
            api_similar.append(api_item)

        logger.info(f"Similar content retrieved: {len(api_similar)} items for {content_item_id}")
        return api_similar

    except Exception as e:
        logger.error(f"Similar content retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Similar content retrieval failed: {str(e)}")


# Query understanding endpoints
@router.post("/analyze", response_model=QueryAnalysisResponse)
async def analyze_query(request: QueryAnalysisRequest) -> QueryAnalysisResponse:
    """
    Analyze user query for intent and context.

    This endpoint performs comprehensive query analysis including intent detection,
    entity extraction, topic identification, and expansion suggestions.
    """
    try:
        analysis = await query_understanding_service.analyze_query(request.query)

        response = QueryAnalysisResponse(
            original_query=analysis.original_query,
            cleaned_query=analysis.cleaned_query,
            query_type=analysis.query_type.value,
            intent=analysis.intent.value,
            entities=analysis.entities,
            keywords=analysis.keywords,
            topics=analysis.topics,
            sentiment=analysis.sentiment,
            complexity=analysis.complexity,
            confidence_score=analysis.confidence_score,
            suggested_expansions=analysis.suggested_expansions,
            related_queries=analysis.related_queries,
            processing_time_ms=analysis.metadata.get('processing_time_ms', 0)
        )

        logger.info(f"Query analysis completed: {analysis.query_type.value} intent with {analysis.confidence_score:.2f} confidence")
        return response

    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query analysis failed: {str(e)}")


@router.post("/expand", response_model=QueryExpansionResponse)
async def expand_query(request: QueryExpansionRequest) -> QueryExpansionResponse:
    """
    Expand query with additional context or related terms.

    This endpoint enhances search queries with synonyms, related terms,
    or contextual information to improve search relevance.
    """
    try:
        expansion = await query_understanding_service.expand_query(
            query=request.query,
            expansion_type=request.expansion_type
        )

        response = QueryExpansionResponse(
            original_query=expansion.original_query,
            expanded_query=expansion.expanded_query,
            expansion_type=expansion.expansion_type,
            confidence_score=expansion.confidence_score,
            reasoning=expansion.reasoning
        )

        logger.info(f"Query expansion completed: {expansion.expansion_type} expansion")
        return response

    except Exception as e:
        logger.error(f"Query expansion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query expansion failed: {str(e)}")


# Analytics endpoints
@router.post("/analytics/report", response_model=AnalyticsReportResponse)
async def generate_analytics_report(request: AnalyticsReportRequest) -> AnalyticsReportResponse:
    """
    Generate comprehensive analytics report.

    This endpoint creates detailed analytics reports including usage patterns,
    content insights, trends, and actionable recommendations.
    """
    try:
        report = await advanced_analytics_service.generate_comprehensive_report(
            time_period_days=request.time_period_days,
            include_trends=request.include_trends,
            include_insights=request.include_insights
        )

        # Convert dataclasses to dicts for JSON serialization
        usage_patterns = [pattern.__dict__ for pattern in report.usage_patterns]
        content_insights = [insight.__dict__ for insight in report.content_insights]
        trends = [trend.__dict__ for trend in report.trends]

        response = AnalyticsReportResponse(
            report_type=report.report_type,
            time_period=report.time_period,
            total_content=report.total_content,
            total_users=report.total_users,
            key_metrics=report.key_metrics,
            usage_patterns=usage_patterns,
            content_insights=content_insights,
            trends=trends,
            recommendations=report.recommendations,
            generated_at=report.generated_at
        )

        logger.info(f"Analytics report generated: {report.total_content} content items analyzed")
        return response

    except Exception as e:
        logger.error(f"Analytics report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics report generation failed: {str(e)}")


@router.get("/analytics/usage-patterns", response_model=List[Dict[str, Any]])
async def get_usage_patterns(
    time_period_days: int = Query(default=30, description="Time period in days"),
    granularity: str = Query(default="daily", description="Time granularity")
) -> List[Dict[str, Any]]:
    """
    Get usage patterns analysis.

    Returns detailed analysis of usage patterns including trends,
    peak times, and insights.
    """
    try:
        patterns = await advanced_analytics_service.generate_usage_patterns(
            time_period_days=time_period_days,
            granularity=granularity
        )

        # Convert to dicts
        api_patterns = []
        for pattern in patterns:
            api_pattern = {
                "pattern_type": pattern.pattern_type,
                "time_period": pattern.time_period,
                "metric": pattern.metric,
                "trend_direction": pattern.trend_direction,
                "trend_strength": pattern.trend_strength,
                "peak_times": pattern.peak_times,
                "insights": pattern.insights
            }
            api_patterns.append(api_pattern)

        logger.info(f"Usage patterns retrieved: {len(api_patterns)} patterns")
        return api_patterns

    except Exception as e:
        logger.error(f"Usage patterns retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Usage patterns retrieval failed: {str(e)}")


@router.get("/analytics/content-insights", response_model=List[Dict[str, Any]])
async def get_content_insights(
    content_ids: Optional[List[str]] = Query(default=None, description="Specific content IDs to analyze"),
    insight_types: Optional[List[str]] = Query(default=None, description="Types of insights to generate")
) -> List[Dict[str, Any]]:
    """
    Get content performance insights.

    Returns detailed insights about content performance including
    popularity, engagement, quality metrics, and recommendations.
    """
    try:
        insights = await advanced_analytics_service.generate_content_insights(
            content_ids=content_ids,
            insight_types=insight_types
        )

        # Convert to dicts
        api_insights = []
        for insight in insights:
            api_insight = {
                "content_id": insight.content_id,
                "insight_type": insight.insight_type,
                "metric": insight.metric,
                "value": insight.value,
                "benchmark": insight.benchmark,
                "percentile": insight.percentile,
                "recommendation": insight.recommendation,
                "confidence": insight.confidence
            }
            api_insights.append(api_insight)

        logger.info(f"Content insights generated: {len(api_insights)} insights")
        return api_insights

    except Exception as e:
        logger.error(f"Content insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content insights generation failed: {str(e)}")


@router.get("/analytics/trends", response_model=List[Dict[str, Any]])
async def detect_trends(
    time_period_days: int = Query(default=30, description="Time period in days"),
    min_growth_rate: float = Query(default=0.1, description="Minimum growth rate")
) -> List[Dict[str, Any]]:
    """
    Detect content and usage trends.

    Returns emerging trends, declining patterns, and growth analysis
    for content and user engagement.
    """
    try:
        trends = await advanced_analytics_service.detect_trends(
            time_period_days=time_period_days,
            min_growth_rate=min_growth_rate
        )

        # Convert to dicts
        api_trends = []
        for trend in trends:
            api_trend = {
                "trend_name": trend.trend_name,
                "trend_type": trend.trend_type,
                "growth_rate": trend.growth_rate,
                "time_period": trend.time_period,
                "related_content": trend.related_content,
                "predictions": trend.predictions
            }
            api_trends.append(api_trend)

        logger.info(f"Trends detected: {len(api_trends)} trends")
        return api_trends

    except Exception as e:
        logger.error(f"Trend detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend detection failed: {str(e)}")


@router.get("/capabilities", response_model=Dict[str, Any])
async def get_search_capabilities() -> Dict[str, Any]:
    """
    Get search and discovery capabilities.

    Returns information about available search features, models,
    and supported operations.
    """
    try:
        capabilities = {
            "search_types": ["semantic", "keyword", "hybrid"],
            "embedding_models": ["nomic-embed-text", "all-MiniLM", "llama2"],
            "recommendation_strategies": ["personalized", "popular", "trending", "similar"],
            "query_analysis": ["intent_detection", "entity_extraction", "topic_detection", "sentiment_analysis"],
            "analytics_features": ["usage_patterns", "content_insights", "trend_detection", "performance_metrics"],
            "supported_content_types": ["text", "image", "audio", "video", "structured"],
            "vector_operations": ["cosine_similarity", "euclidean_distance", "dot_product"],
            "chunking_strategies": ["fixed_size", "sentence_based", "semantic", "overlapping"],
            "features": [
                "real_time_indexing",
                "batch_processing",
                "personalized_recommendations",
                "query_expansion",
                "content_similarity",
                "trend_analysis",
                "usage_analytics",
                "performance_monitoring"
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
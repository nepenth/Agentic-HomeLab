"""
API routes for Performance Cache service.

Provides endpoints for cache management, performance monitoring,
and optimization controls.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.performance_cache import (
    performance_cache,
    email_analysis_cache_key,
    thread_detection_cache_key,
    search_results_cache_key,
    semantic_embedding_cache_key,
    query_optimizer
)
from app.utils.logging import get_logger

logger = get_logger("performance_cache_api")
router = APIRouter(prefix="/api/v1/cache", tags=["Performance Cache"])


# Pydantic models for API
class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    cache_enabled: bool
    cache_hits: int
    cache_misses: int
    hit_rate: float
    total_requests: int
    local_cache_size: int
    max_local_cache_size: int
    default_ttl: int
    redis_connected: bool
    redis_used_memory: Optional[str] = None
    redis_connected_clients: Optional[int] = None
    redis_uptime_days: Optional[int] = None


class CacheEntryResponse(BaseModel):
    """Response model for cache entries."""
    key: str
    value: Any
    exists: bool
    ttl_remaining: Optional[int] = None


class QueryOptimizationRequest(BaseModel):
    """Request model for query optimization."""
    query: str
    params: Dict[str, Any]


class QueryOptimizationResponse(BaseModel):
    """Response model for query optimization results."""
    original_query: str
    optimized_query: str
    original_params: Dict[str, Any]
    optimized_params: Dict[str, Any]
    recommendations: List[str]


class PerformanceAnalysisRequest(BaseModel):
    """Request model for performance analysis."""
    operation_name: str
    execution_time_ms: float
    metadata: Optional[Dict[str, Any]] = None


class PerformanceAnalysisResponse(BaseModel):
    """Response model for performance analysis."""
    operation_name: str
    execution_time_ms: float
    performance_rating: str
    recommendations: List[str]
    optimization_suggestions: List[str]


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Get comprehensive cache performance statistics."""
    try:
        stats = await performance_cache.get_stats()

        return CacheStatsResponse(
            cache_enabled=stats["cache_enabled"],
            cache_hits=stats["cache_hits"],
            cache_misses=stats["cache_misses"],
            hit_rate=stats["hit_rate"],
            total_requests=stats["total_requests"],
            local_cache_size=stats["local_cache_size"],
            max_local_cache_size=stats["max_local_cache_size"],
            default_ttl=stats["default_ttl"],
            redis_connected=stats["redis_connected"],
            redis_used_memory=stats.get("redis_used_memory"),
            redis_connected_clients=stats.get("redis_connected_clients"),
            redis_uptime_days=stats.get("redis_uptime_days")
        )

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.get("/entry/{key}", response_model=CacheEntryResponse)
async def get_cache_entry(key: str):
    """Get a specific cache entry."""
    try:
        value = await performance_cache.get(key)
        exists = value is not None

        # Get TTL information if Redis is available
        ttl_remaining = None
        if performance_cache.redis_client and exists:
            try:
                ttl_remaining = await performance_cache.redis_client.ttl(key)
                if ttl_remaining == -1:  # No expiration
                    ttl_remaining = None
            except Exception:
                pass

        return CacheEntryResponse(
            key=key,
            value=value,
            exists=exists,
            ttl_remaining=ttl_remaining
        )

    except Exception as e:
        logger.error(f"Failed to get cache entry {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache entry: {str(e)}")


@router.post("/entry")
async def set_cache_entry(
    key: str,
    value: Any,
    ttl: Optional[int] = None
):
    """Set a cache entry."""
    try:
        success = await performance_cache.set(key, value, ttl)

        if success:
            return {"message": "Cache entry set successfully", "key": key}
        else:
            raise HTTPException(status_code=500, detail="Failed to set cache entry")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set cache entry {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set cache entry: {str(e)}")


@router.delete("/entry/{key}")
async def delete_cache_entry(key: str):
    """Delete a cache entry."""
    try:
        deleted = await performance_cache.delete(key)

        if deleted:
            return {"message": "Cache entry deleted successfully", "key": key}
        else:
            raise HTTPException(status_code=404, detail="Cache entry not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete cache entry {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete cache entry: {str(e)}")


@router.delete("/clear")
async def clear_cache(pattern: Optional[str] = None):
    """Clear cache entries matching a pattern."""
    try:
        cleared_count = await performance_cache.clear(pattern)

        return {
            "message": f"Cache cleared successfully",
            "pattern": pattern or "*",
            "entries_cleared": cleared_count
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/keys")
async def list_cache_keys(
    pattern: Optional[str] = None,
    limit: int = 100
):
    """List cache keys matching a pattern."""
    try:
        keys = []

        # Get keys from Redis if available
        if performance_cache.redis_client:
            try:
                if pattern:
                    async for key in performance_cache.redis_client.scan_iter(pattern):
                        keys.append(key)
                        if len(keys) >= limit:
                            break
                else:
                    async for key in performance_cache.redis_client.scan_iter():
                        keys.append(key)
                        if len(keys) >= limit:
                            break
            except Exception as e:
                logger.warning(f"Failed to scan Redis keys: {e}")

        # Add local cache keys
        local_keys = list(performance_cache.local_cache.keys())
        if pattern:
            local_keys = [k for k in local_keys if pattern in k]

        # Combine and deduplicate
        all_keys = list(set(keys + local_keys))[:limit]

        return {
            "keys": all_keys,
            "count": len(all_keys),
            "pattern": pattern,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Failed to list cache keys: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list cache keys: {str(e)}")


@router.post("/optimize-query", response_model=QueryOptimizationResponse)
async def optimize_query(request: QueryOptimizationRequest):
    """Optimize a database query."""
    try:
        optimized_query, optimized_params = await query_optimizer.optimize_query(
            request.query,
            request.params
        )

        # Generate recommendations
        recommendations = []
        if "SELECT *" in request.query.upper():
            recommendations.append("Avoid SELECT * - specify required columns")
        if "WHERE" in request.query.upper() and "INDEX" not in request.query.upper():
            recommendations.append("Consider adding database indexes for WHERE conditions")
        if "JOIN" in request.query.upper():
            recommendations.append("Review JOIN operations for potential optimization")

        return QueryOptimizationResponse(
            original_query=request.query,
            optimized_query=optimized_query,
            original_params=request.params,
            optimized_params=optimized_params,
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Failed to optimize query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to optimize query: {str(e)}")


@router.post("/analyze-performance", response_model=PerformanceAnalysisResponse)
async def analyze_performance(request: PerformanceAnalysisRequest):
    """Analyze performance metrics and provide recommendations."""
    try:
        # Determine performance rating
        if request.execution_time_ms < 100:
            rating = "excellent"
        elif request.execution_time_ms < 500:
            rating = "good"
        elif request.execution_time_ms < 2000:
            rating = "moderate"
        else:
            rating = "poor"

        # Generate recommendations
        recommendations = []
        optimization_suggestions = []

        if request.execution_time_ms > 2000:
            recommendations.append("Consider implementing caching for this operation")
            recommendations.append("Review database queries for optimization")
            optimization_suggestions.append("Add database indexes if not present")
            optimization_suggestions.append("Consider query result pagination")

        if request.execution_time_ms > 5000:
            recommendations.append("Consider implementing async processing")
            recommendations.append("Review algorithm complexity")
            optimization_suggestions.append("Implement background job processing")
            optimization_suggestions.append("Consider result caching with TTL")

        # Operation-specific recommendations
        if "search" in request.operation_name.lower():
            optimization_suggestions.append("Implement search result caching")
            optimization_suggestions.append("Consider search query optimization")

        if "analysis" in request.operation_name.lower():
            optimization_suggestions.append("Cache analysis results")
            optimization_suggestions.append("Implement incremental analysis")

        return PerformanceAnalysisResponse(
            operation_name=request.operation_name,
            execution_time_ms=request.execution_time_ms,
            performance_rating=rating,
            recommendations=recommendations,
            optimization_suggestions=optimization_suggestions
        )

    except Exception as e:
        logger.error(f"Failed to analyze performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze performance: {str(e)}")


@router.get("/cache-keys/email-analysis/{email_id}")
async def get_email_analysis_cache_key(email_id: str, analysis_type: str = "general"):
    """Generate cache key for email analysis."""
    try:
        cache_key = email_analysis_cache_key(email_id, analysis_type)
        return {"cache_key": cache_key, "email_id": email_id, "analysis_type": analysis_type}

    except Exception as e:
        logger.error(f"Failed to generate email analysis cache key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate cache key: {str(e)}")


@router.get("/cache-keys/thread-detection")
async def get_thread_detection_cache_key(email_ids: List[str] = Query(...)):
    """Generate cache key for thread detection."""
    try:
        cache_key = thread_detection_cache_key(email_ids)
        return {"cache_key": cache_key, "email_ids": email_ids}

    except Exception as e:
        logger.error(f"Failed to generate thread detection cache key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate cache key: {str(e)}")


@router.get("/cache-keys/search-results")
async def get_search_results_cache_key(
    query: str = Query(...),
    filters: Optional[str] = None
):
    """Generate cache key for search results."""
    try:
        filters_dict = {}
        if filters:
            try:
                filters_dict = eval(filters)  # Simple eval for demo - use proper JSON parsing in production
            except:
                filters_dict = {}

        cache_key = search_results_cache_key(query, filters_dict)
        return {"cache_key": cache_key, "query": query, "filters": filters_dict}

    except Exception as e:
        logger.error(f"Failed to generate search results cache key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate cache key: {str(e)}")


@router.get("/cache-keys/semantic-embedding")
async def get_semantic_embedding_cache_key(content: str = Query(..., max_length=1000)):
    """Generate cache key for semantic embeddings."""
    try:
        cache_key = semantic_embedding_cache_key(content)
        return {"cache_key": cache_key, "content_length": len(content)}

    except Exception as e:
        logger.error(f"Failed to generate semantic embedding cache key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate cache key: {str(e)}")


@router.post("/warmup/email-analysis")
async def warmup_email_analysis_cache(email_ids: List[str]):
    """Warm up cache with email analysis results."""
    try:
        warmed_up = 0

        for email_id in email_ids:
            # Generate cache key
            cache_key = email_analysis_cache_key(email_id)

            # Check if already cached
            exists = await performance_cache.exists(cache_key)
            if not exists:
                # In a real implementation, you would fetch and cache the analysis
                # For now, we'll just mark it as cached with a placeholder
                await performance_cache.set(cache_key, {"status": "warmup_placeholder"}, 3600)
                warmed_up += 1

        return {
            "message": f"Cache warmup completed",
            "emails_processed": len(email_ids),
            "entries_warmed_up": warmed_up
        }

    except Exception as e:
        logger.error(f"Failed to warmup email analysis cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to warmup cache: {str(e)}")


@router.get("/health")
async def cache_health_check():
    """Health check for cache service."""
    try:
        stats = await performance_cache.get_stats()

        # Determine health status
        is_healthy = True
        issues = []

        if not stats["redis_connected"]:
            issues.append("Redis connection not available")
            is_healthy = False

        if stats["local_cache_size"] > stats["max_local_cache_size"] * 0.9:
            issues.append("Local cache near capacity")

        if stats["hit_rate"] < 0.5 and stats["total_requests"] > 100:
            issues.append("Low cache hit rate detected")

        return {
            "healthy": is_healthy,
            "issues": issues,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "healthy": False,
            "issues": [f"Health check failed: {str(e)}"],
            "stats": {}
        }
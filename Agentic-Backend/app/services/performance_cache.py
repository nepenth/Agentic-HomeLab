"""
Performance Optimization Service with advanced caching capabilities.

This service provides Redis-based caching, query optimization, and performance
monitoring for the email workflow system.
"""

import asyncio
import json
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import redis.asyncio as redis
from contextlib import asynccontextmanager

from app.utils.logging import get_logger
from app.config import settings


class CacheEntry:
    """Represents a cached entry with metadata."""

    def __init__(self, key: str, value: Any, ttl: Optional[int] = None):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "ttl": self.ttl,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        entry = cls(data["key"], data["value"], data["ttl"])
        entry.created_at = datetime.fromisoformat(data["created_at"])
        entry.access_count = data["access_count"]
        entry.last_accessed = datetime.fromisoformat(data["last_accessed"])
        return entry

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if not self.ttl:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl

    def access(self):
        """Record access to this cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class PerformanceCache:
    """Advanced caching service with Redis backend and performance monitoring."""

    def __init__(self, redis_url: Optional[str] = None):
        self.logger = get_logger("performance_cache")
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: Dict[str, CacheEntry] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_enabled = True

        # Cache configuration
        self.default_ttl = 3600  # 1 hour
        self.max_local_cache_size = 10000
        self.cleanup_interval = 300  # 5 minutes

        # Start cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the cache service."""
        try:
            if self.redis_url:
                self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                self.logger.info("Redis cache initialized successfully")
            else:
                self.logger.warning("No Redis URL provided, using local cache only")

            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

        except Exception as e:
            self.logger.error(f"Failed to initialize cache: {e}")
            self.redis_client = None

    async def close(self):
        """Close the cache service."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        if self.redis_client:
            await self.redis_client.close()

    @asynccontextmanager
    async def cache_operation(self, operation: str):
        """Context manager for cache operations with performance monitoring."""
        start_time = datetime.now()
        try:
            yield
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.debug(f"Cache operation '{operation}' completed in {duration:.2f}ms")
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Cache operation '{operation}' failed after {duration:.2f}ms: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        async with self.cache_operation(f"get:{key}"):
            # Try Redis first
            if self.redis_client:
                try:
                    value = await self.redis_client.get(key)
                    if value:
                        self.cache_hits += 1
                        # Update access metadata
                        await self._update_access_metadata(key)
                        return json.loads(value)
                except Exception as e:
                    self.logger.warning(f"Redis get failed for key {key}: {e}")

            # Try local cache
            if key in self.local_cache:
                entry = self.local_cache[key]
                if not entry.is_expired():
                    entry.access()
                    self.cache_hits += 1
                    return entry.value
                else:
                    # Remove expired entry
                    del self.local_cache[key]

            self.cache_misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        async with self.cache_operation(f"set:{key}"):
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value)

            # Store in Redis
            if self.redis_client:
                try:
                    await self.redis_client.setex(key, ttl, serialized_value)
                except Exception as e:
                    self.logger.warning(f"Redis set failed for key {key}: {e}")

            # Store in local cache
            entry = CacheEntry(key, value, ttl)
            self.local_cache[key] = entry

            # Cleanup if local cache is too large
            if len(self.local_cache) > self.max_local_cache_size:
                await self._cleanup_local_cache()

            return True

    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        async with self.cache_operation(f"delete:{key}"):
            deleted = False

            # Delete from Redis
            if self.redis_client:
                try:
                    result = await self.redis_client.delete(key)
                    deleted = result > 0
                except Exception as e:
                    self.logger.warning(f"Redis delete failed for key {key}: {e}")

            # Delete from local cache
            if key in self.local_cache:
                del self.local_cache[key]
                deleted = True

            return deleted

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        async with self.cache_operation(f"exists:{key}"):
            # Check Redis
            if self.redis_client:
                try:
                    exists = await self.redis_client.exists(key)
                    if exists:
                        return True
                except Exception as e:
                    self.logger.warning(f"Redis exists check failed for key {key}: {e}")

            # Check local cache
            if key in self.local_cache:
                entry = self.local_cache[key]
                if not entry.is_expired():
                    return True
                else:
                    del self.local_cache[key]

            return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching a pattern."""
        async with self.cache_operation(f"clear:{pattern or '*'}"):
            cleared = 0

            # Clear Redis
            if self.redis_client:
                try:
                    if pattern:
                        # Use SCAN for pattern matching
                        keys = []
                        async for key in self.redis_client.scan_iter(pattern):
                            keys.append(key)

                        if keys:
                            await self.redis_client.delete(*keys)
                            cleared += len(keys)
                    else:
                        await self.redis_client.flushdb()
                        cleared = -1  # Indicate full clear
                except Exception as e:
                    self.logger.warning(f"Redis clear failed for pattern {pattern}: {e}")

            # Clear local cache
            if pattern:
                keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.local_cache[key]
                cleared += len(keys_to_delete)
            else:
                cleared += len(self.local_cache)
                self.local_cache.clear()

            return cleared

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests) if total_requests > 0 else 0

        stats = {
            "cache_enabled": self.cache_enabled,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "local_cache_size": len(self.local_cache),
            "max_local_cache_size": self.max_local_cache_size,
            "default_ttl": self.default_ttl,
            "redis_connected": self.redis_client is not None
        }

        # Add Redis-specific stats if available
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                stats.update({
                    "redis_used_memory": redis_info.get("used_memory_human", "unknown"),
                    "redis_connected_clients": redis_info.get("connected_clients", 0),
                    "redis_uptime_days": redis_info.get("uptime_in_days", 0)
                })
            except Exception as e:
                self.logger.warning(f"Failed to get Redis stats: {e}")

        return stats

    async def _update_access_metadata(self, key: str):
        """Update access metadata for a cache entry."""
        if self.redis_client:
            try:
                # Store access metadata in a separate key
                metadata_key = f"{key}:metadata"
                metadata = {
                    "last_accessed": datetime.now().isoformat(),
                    "access_count": 1  # Simplified - would need to increment in real implementation
                }
                await self.redis_client.setex(metadata_key, self.default_ttl, json.dumps(metadata))
            except Exception as e:
                self.logger.warning(f"Failed to update access metadata for {key}: {e}")

    async def _cleanup_local_cache(self):
        """Clean up expired entries from local cache."""
        expired_keys = []
        for key, entry in self.local_cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self.local_cache[key]

        # If still too large, remove least recently used items
        if len(self.local_cache) > self.max_local_cache_size:
            # Sort by last accessed time
            sorted_entries = sorted(
                self.local_cache.items(),
                key=lambda x: x[1].last_accessed
            )

            # Remove oldest 20%
            to_remove = len(sorted_entries) // 5
            for key, _ in sorted_entries[:to_remove]:
                del self.local_cache[key]

    async def _periodic_cleanup(self):
        """Periodic cleanup of expired cache entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_local_cache()

                # Log cache statistics
                stats = await self.get_stats()
                self.logger.debug(f"Cache stats: hits={stats['cache_hits']}, "
                                f"misses={stats['cache_misses']}, "
                                f"hit_rate={stats['hit_rate']:.2%}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")

    def cached(self, ttl: Optional[int] = None, key_prefix: str = ""):
        """Decorator for caching function results."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.cache_enabled:
                    return await func(*args, **kwargs)

                # Generate cache key
                key_parts = [key_prefix or func.__name__]
                key_parts.extend([str(arg) for arg in args if arg is not None])
                key_parts.extend([f"{k}:{v}" for k, v in kwargs.items() if v is not None])

                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

                # Try to get from cache first
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute function and cache result
                result = await func(*args, **kwargs)
                if result is not None:
                    await self.set(cache_key, result, ttl)

                return result

            return wrapper
        return decorator


# Global cache instance
performance_cache = PerformanceCache()


# Cache key generators for common patterns
def email_analysis_cache_key(email_id: str, analysis_type: str = "general") -> str:
    """Generate cache key for email analysis results."""
    return f"email_analysis:{email_id}:{analysis_type}"


def thread_detection_cache_key(email_ids: List[str]) -> str:
    """Generate cache key for thread detection results."""
    # Sort for consistent key generation
    sorted_ids = sorted(email_ids)
    ids_hash = hashlib.md5(",".join(sorted_ids).encode()).hexdigest()
    return f"thread_detection:{ids_hash}"


def search_results_cache_key(query: str, filters: Dict[str, Any]) -> str:
    """Generate cache key for search results."""
    # Create a stable representation of filters
    filter_str = json.dumps(filters, sort_keys=True)
    query_hash = hashlib.md5(f"{query}:{filter_str}".encode()).hexdigest()
    return f"search_results:{query_hash}"


def semantic_embedding_cache_key(content: str) -> str:
    """Generate cache key for semantic embeddings."""
    content_hash = hashlib.md5(content.encode()).hexdigest()
    return f"semantic_embedding:{content_hash}"


# Performance monitoring utilities
async def measure_execution_time(func: Callable, *args, **kwargs) -> tuple:
    """Measure execution time of a function."""
    start_time = datetime.now()
    result = await func(*args, **kwargs)
    execution_time = (datetime.now() - start_time).total_seconds() * 1000
    return result, execution_time


def log_performance(func_name: str, execution_time: float, threshold: float = 1000):
    """Log performance metrics if execution time exceeds threshold."""
    logger = get_logger("performance_monitoring")

    if execution_time > threshold:
        logger.warning(f"Performance alert: {func_name} took {execution_time:.2f}ms "
                      f"(threshold: {threshold}ms)")
    else:
        logger.debug(f"Performance: {func_name} completed in {execution_time:.2f}ms")


# Database query optimization utilities
class QueryOptimizer:
    """Utility class for database query optimization."""

    def __init__(self):
        self.logger = get_logger("query_optimizer")

    async def optimize_query(self, query: str, params: Dict[str, Any]) -> tuple:
        """Optimize a database query with given parameters."""
        # This is a simplified implementation
        # In production, this would analyze query patterns and suggest optimizations

        optimized_query = query
        optimized_params = params.copy()

        # Add LIMIT if not present for large result sets
        if "LIMIT" not in query.upper() and "SELECT" in query.upper():
            optimized_query += " LIMIT 1000"

        # Add appropriate indexes hints (simplified)
        if "WHERE" in query.upper():
            self.logger.debug("Query contains WHERE clause - consider adding database indexes")

        return optimized_query, optimized_params

    def analyze_query_performance(self, query: str, execution_time: float) -> Dict[str, Any]:
        """Analyze query performance and provide recommendations."""
        analysis = {
            "query_type": "SELECT" if "SELECT" in query.upper() else "OTHER",
            "execution_time_ms": execution_time,
            "performance_rating": "good" if execution_time < 100 else "slow" if execution_time > 1000 else "moderate",
            "recommendations": []
        }

        # Performance recommendations
        if execution_time > 1000:
            analysis["recommendations"].append("Consider adding database indexes")
            analysis["recommendations"].append("Review query complexity")

        if "SELECT *" in query.upper():
            analysis["recommendations"].append("Avoid SELECT * - specify required columns")

        if "JOIN" in query.upper():
            analysis["recommendations"].append("Review JOIN operations for optimization")

        return analysis


# Global query optimizer instance
query_optimizer = QueryOptimizer()
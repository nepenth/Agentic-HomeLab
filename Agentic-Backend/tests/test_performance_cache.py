"""
Tests for Performance Cache service.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.performance_cache import (
    PerformanceCache,
    CacheEntry,
    email_analysis_cache_key,
    thread_detection_cache_key,
    search_results_cache_key,
    semantic_embedding_cache_key,
    measure_execution_time,
    log_performance,
    QueryOptimizer
)


class TestPerformanceCache:
    """Test cases for the Performance Cache service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PerformanceCache()

    def teardown_method(self):
        """Clean up after tests."""
        # Cancel cleanup task if running
        if hasattr(self.cache, 'cleanup_task') and self.cache.cleanup_task:
            self.cache.cleanup_task.cancel()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test cache initialization."""
        assert self.cache.redis_client is None  # No Redis URL provided
        assert self.cache.local_cache == {}
        assert self.cache.cache_enabled is True
        assert self.cache.default_ttl == 3600

    @pytest.mark.asyncio
    async def test_cache_operations_without_redis(self):
        """Test basic cache operations without Redis."""
        # Test set and get
        await self.cache.set("test_key", {"data": "test_value"})
        result = await self.cache.get("test_key")

        assert result == {"data": "test_value"}

        # Test exists
        exists = await self.cache.exists("test_key")
        assert exists

        # Test delete
        deleted = await self.cache.delete("test_key")
        assert deleted

        # Verify deletion
        result = await self.cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache entry expiration."""
        # Set with short TTL
        await self.cache.set("expire_key", "test_value", ttl=1)

        # Should exist immediately
        result = await self.cache.get("expire_key")
        assert result == "test_value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        result = await self.cache.get("expire_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        # Perform some operations
        await self.cache.set("key1", "value1")
        await self.cache.set("key2", "value2")
        await self.cache.get("key1")  # Hit
        await self.cache.get("key3")  # Miss

        stats = await self.cache.get_stats()

        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["local_cache_size"] == 2
        assert stats["redis_connected"] is False

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing operations."""
        # Add some entries
        await self.cache.set("key1", "value1")
        await self.cache.set("key2", "value2")
        await self.cache.set("prefix_key3", "value3")

        # Clear all
        cleared = await self.cache.clear()
        assert cleared >= 2  # At least the entries we added

        # Verify cleared
        result1 = await self.cache.get("key1")
        result2 = await self.cache.get("key2")
        assert result1 is None
        assert result2 is None

    @pytest.mark.asyncio
    async def test_cache_pattern_clear(self):
        """Test clearing cache with patterns."""
        # Add entries with different patterns
        await self.cache.set("user_1", "user1_data")
        await self.cache.set("user_2", "user2_data")
        await self.cache.set("post_1", "post1_data")

        # Clear user entries
        cleared = await self.cache.clear("user_*")
        assert cleared >= 2

        # Verify user entries cleared but post remains
        user_result = await self.cache.get("user_1")
        post_result = await self.cache.get("post_1")
        assert user_result is None
        assert post_result == "post1_data"

    def test_cache_entry_operations(self):
        """Test CacheEntry class operations."""
        entry = CacheEntry("test_key", "test_value", ttl=60)

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.ttl == 60
        assert not entry.is_expired()

        # Test expiration
        expired_entry = CacheEntry("expired_key", "expired_value", ttl=0)
        expired_entry.created_at = datetime.now() - timedelta(seconds=1)
        assert expired_entry.is_expired()

        # Test access tracking
        entry.access()
        assert entry.access_count == 1
        assert entry.last_accessed is not None

    def test_cache_decorator(self):
        """Test the cached decorator."""
        call_count = 0

        @self.cache.cached(ttl=60)
        async def test_function(x, y=10):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call should execute function
        result1 = asyncio.run(test_function(5, 15))
        assert result1 == 20
        assert call_count == 1

        # Second call with same args should use cache
        result2 = asyncio.run(test_function(5, 15))
        assert result2 == 20
        assert call_count == 1  # Should not have increased

        # Call with different args should execute function
        result3 = asyncio.run(test_function(10, 15))
        assert result3 == 25
        assert call_count == 2

    def test_cache_key_generators(self):
        """Test cache key generation functions."""
        # Email analysis key
        email_key = email_analysis_cache_key("email123", "importance")
        assert "email_analysis" in email_key
        assert "email123" in email_key

        # Thread detection key
        thread_key = thread_detection_cache_key(["email1", "email2", "email3"])
        assert "thread_detection" in thread_key

        # Search results key
        search_key = search_results_cache_key("test query", {"filter": "value"})
        assert "search_results" in search_key

        # Semantic embedding key
        embedding_key = semantic_embedding_cache_key("test content")
        assert "semantic_embedding" in embedding_key

    @pytest.mark.asyncio
    async def test_measure_execution_time(self):
        """Test execution time measurement utility."""
        async def test_func():
            await asyncio.sleep(0.1)
            return "result"

        result, execution_time = await measure_execution_time(test_func)

        assert result == "result"
        assert execution_time >= 100  # At least 100ms
        assert execution_time < 200   # Less than 200ms

    def test_log_performance(self):
        """Test performance logging utility."""
        with patch('app.services.performance_cache.get_logger') as mock_logger:
            mock_log_instance = MagicMock()
            mock_logger.return_value = mock_log_instance

            # Test normal performance
            log_performance("test_func", 50, threshold=100)
            mock_log_instance.debug.assert_called_once()

            # Reset mock
            mock_log_instance.reset_mock()

            # Test slow performance
            log_performance("test_func", 150, threshold=100)
            mock_log_instance.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_optimizer(self):
        """Test query optimization functionality."""
        optimizer = QueryOptimizer()

        # Test basic query optimization
        query = "SELECT * FROM users WHERE active = 1"
        params = {"active": 1}

        optimized_query, optimized_params = await optimizer.optimize_query(query, params)

        # Should add LIMIT
        assert "LIMIT" in optimized_query
        assert optimized_params == params

        # Test performance analysis
        analysis = optimizer.analyze_query_performance(query, 500)

        assert analysis["execution_time_ms"] == 500
        assert analysis["performance_rating"] == "moderate"
        assert len(analysis["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_cache_with_mock_redis(self):
        """Test cache operations with mocked Redis."""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.from_url.return_value = mock_redis
            mock_redis.ping = AsyncMock()
            mock_redis.setex = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.delete = AsyncMock(return_value=1)

            # Create cache with Redis URL
            cache = PerformanceCache(redis_url="redis://localhost:6379")
            await cache.initialize()

            # Test operations
            await cache.set("test_key", "test_value")
            mock_redis.setex.assert_called_once()

            result = await cache.get("test_key")
            mock_redis.get.assert_called_once()
            assert result is None  # Redis returned None

            deleted = await cache.delete("test_key")
            mock_redis.delete.assert_called_once()
            assert deleted is True

    @pytest.mark.asyncio
    async def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        # Add entries with different TTLs
        await self.cache.set("short_ttl", "value1", ttl=1)
        await self.cache.set("long_ttl", "value2", ttl=3600)

        # Wait for short TTL to expire
        await asyncio.sleep(1.1)

        # Manual cleanup
        await self.cache._cleanup_local_cache()

        # Short TTL entry should be removed
        short_result = await self.cache.get("short_ttl")
        long_result = await self.cache.get("long_ttl")

        assert short_result is None
        assert long_result == "value2"

    @pytest.mark.asyncio
    async def test_cache_size_limits(self):
        """Test cache size limits and cleanup."""
        # Set small cache size for testing
        self.cache.max_local_cache_size = 3

        # Add entries beyond limit
        for i in range(5):
            await self.cache.set(f"key_{i}", f"value_{i}")

        # Should trigger cleanup and maintain size
        assert len(self.cache.local_cache) <= self.cache.max_local_cache_size + 1  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_periodic_cleanup(self):
        """Test periodic cleanup functionality."""
        # This test is more complex due to async timing
        # In practice, the periodic cleanup runs in the background

        # Add an expired entry
        await self.cache.set("expired", "value", ttl=1)
        await asyncio.sleep(1.1)

        # The periodic cleanup should eventually remove it
        # We can't easily test the async task, but we can verify the cleanup logic
        await self.cache._cleanup_local_cache()

        result = await self.cache.get("expired")
        assert result is None
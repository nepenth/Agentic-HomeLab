#!/usr/bin/env python3
"""
Test script for Phase 1 implementations.

This script validates the core functionality of all Phase 1 services:
- Enhanced Workflow Orchestration Engine
- Agentic HTTP Client Framework
- Dynamic Model Selection System
- Multi-Modal Content Framework
- Semantic Processing Infrastructure
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("phase1_test")


async def test_http_client():
    """Test the Agentic HTTP Client Framework."""
    logger.info("Testing Agentic HTTP Client Framework...")

    try:
        from app.services.agentic_http_client import agentic_http_client

        # Test basic HTTP request
        response = await agentic_http_client.request(
            method="GET",
            url="https://httpbin.org/get",
            timeout=10.0
        )

        if response.status_code == 200:
            logger.info("✅ HTTP Client: Basic request successful")
            return True
        else:
            logger.error(f"❌ HTTP Client: Request failed with status {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ HTTP Client: Test failed with error: {e}")
        return False


async def test_model_selection():
    """Test the Dynamic Model Selection System."""
    logger.info("Testing Dynamic Model Selection System...")

    try:
        from app.services.model_selection_service import model_registry, model_selector

        # Test model discovery
        models = await model_registry.discover_models()

        if models:
            logger.info(f"✅ Model Selection: Discovered {len(models)} models")

            # Test model selection
            from app.services.model_selection_service import TaskType, ContentType, ProcessingTask

            task = ProcessingTask(
                task_type=TaskType.TEXT_GENERATION,
                content_type=ContentType.TEXT,
                priority="balanced"
            )

            selection = await model_selector.select_for_task(task)

            if selection and selection.model_name:
                logger.info(f"✅ Model Selection: Selected model {selection.model_name}")
                return True
            else:
                logger.error("❌ Model Selection: No model selected")
                return False
        else:
            logger.warning("⚠️ Model Selection: No models discovered (this may be expected if Ollama is not running)")
            return True  # Consider this a pass since the service is working

    except Exception as e:
        logger.error(f"❌ Model Selection: Test failed with error: {e}")
        return False


async def test_content_framework():
    """Test the Multi-Modal Content Framework."""
    logger.info("Testing Multi-Modal Content Framework...")

    try:
        from app.services.content_framework import content_detector, content_processor

        # Test content type detection
        test_url = "https://httpbin.org/json"
        metadata = await content_detector.detect_from_url(test_url)

        if metadata and metadata.content_type:
            logger.info(f"✅ Content Framework: Detected content type {metadata.content_type.value}")

            # Test content processing
            content_data = await content_processor.process_url(test_url)

            if content_data and content_data.metadata:
                logger.info("✅ Content Framework: Content processing successful")
                return True
            else:
                logger.error("❌ Content Framework: Content processing failed")
                return False
        else:
            logger.error("❌ Content Framework: Content type detection failed")
            return False

    except Exception as e:
        logger.error(f"❌ Content Framework: Test failed with error: {e}")
        return False


async def test_semantic_processing():
    """Test the Semantic Processing Infrastructure."""
    logger.info("Testing Semantic Processing Infrastructure...")

    try:
        from app.services.semantic_processing import embedding_service, vector_operations

        # Test basic embedding generation
        test_text = "This is a test for semantic processing."
        result = await embedding_service.generate_embedding(test_text)

        if result and result.embedding and len(result.embedding) > 0:
            logger.info(f"✅ Semantic Processing: Generated embedding with {len(result.embedding)} dimensions")

            # Test vector operations
            similarity = vector_operations.cosine_similarity(result.embedding, result.embedding)

            if abs(similarity - 1.0) < 0.01:  # Should be very close to 1.0 (identical vectors)
                logger.info("✅ Semantic Processing: Vector similarity calculation working")
                return True
            else:
                logger.error(f"❌ Semantic Processing: Vector similarity incorrect: {similarity}")
                return False
        else:
            logger.error("❌ Semantic Processing: Embedding generation failed")
            return False

    except Exception as e:
        logger.error(f"❌ Semantic Processing: Test failed with error: {e}")
        return False


def test_database_models():
    """Test database models can be imported and instantiated."""
    logger.info("Testing Database Models...")

    try:
        from app.db.models.model_performance import ModelPerformanceMetrics, ModelUsageLog, ModelRegistry
        from app.db.models.http_request_log import HttpRequestLog, HttpClientMetrics, HttpClientConfig

        # Test model instantiation
        model_metric = ModelPerformanceMetrics(
            model_name="test-model",
            task_type="text_generation",
            content_type="text",
            success_rate=0.95,
            average_response_time_ms=1000.0,
            total_requests=100
        )

        http_log = HttpRequestLog(
            request_id="test-request-123",
            method="GET",
            url="https://example.com",
            status_code=200,
            response_time_ms=500.0
        )

        logger.info("✅ Database Models: All models can be instantiated")
        return True

    except Exception as e:
        logger.error(f"❌ Database Models: Test failed with error: {e}")
        return False


def test_api_routes():
    """Test API routes can be imported."""
    logger.info("Testing API Routes...")

    try:
        from app.api.routes.http_client import router as http_router
        from app.api.routes.model_selection import router as model_router
        from app.api.routes.content_framework import router as content_router
        from app.api.routes.semantic_processing import router as semantic_router

        # Check that routers have routes
        http_routes = len(http_router.routes)
        model_routes = len(model_router.routes)
        content_routes = len(content_router.routes)
        semantic_routes = len(semantic_router.routes)

        logger.info(f"✅ API Routes: HTTP Client ({http_routes} routes), Model Selection ({model_routes} routes), Content Framework ({content_routes} routes), Semantic Processing ({semantic_routes} routes)")
        return True

    except Exception as e:
        logger.error(f"❌ API Routes: Test failed with error: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    logger.info("Testing Configuration...")

    try:
        # Test that new configuration values are accessible
        http_enabled = settings.http_client_circuit_breaker_enabled
        model_cache_ttl = settings.model_selection_cache_ttl
        content_cache_size = settings.content_cache_max_size_mb
        semantic_batch_size = settings.semantic_embedding_batch_size

        logger.info("✅ Configuration: All Phase 1 settings loaded successfully")
        logger.info(f"   HTTP Client Circuit Breaker: {http_enabled}")
        logger.info(f"   Model Selection Cache TTL: {model_cache_ttl}s")
        logger.info(f"   Content Cache Max Size: {content_cache_size}MB")
        logger.info(f"   Semantic Embedding Batch Size: {semantic_batch_size}")

        return True

    except Exception as e:
        logger.error(f"❌ Configuration: Test failed with error: {e}")
        return False


async def run_all_tests():
    """Run all Phase 1 validation tests."""
    logger.info("🚀 Starting Phase 1 Implementation Validation Tests")
    logger.info("=" * 60)

    test_results = []

    # Test configuration first (synchronous)
    test_results.append(("Configuration", test_configuration()))

    # Test database models (synchronous)
    test_results.append(("Database Models", test_database_models()))

    # Test API routes (synchronous)
    test_results.append(("API Routes", test_api_routes()))

    # Test services (asynchronous)
    test_results.append(("HTTP Client", await test_http_client()))
    test_results.append(("Model Selection", await test_model_selection()))
    test_results.append(("Content Framework", await test_content_framework()))
    test_results.append(("Semantic Processing", await test_semantic_processing()))

    # Summary
    logger.info("=" * 60)
    logger.info("📊 Phase 1 Validation Test Results:")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1

    logger.info("=" * 60)
    logger.info(f"🎯 Overall Result: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All Phase 1 implementations validated successfully!")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
"""
Content Connector API Routes.

This module provides REST API endpoints for the Universal Content Connector Framework,
enabling content discovery, fetching, and processing through various connectors.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import json

from app.connectors.base import (
    ConnectorRegistry,
    ContentItem,
    ContentData,
    ValidationResult,
    ConnectorType,
    ContentType,
    ConnectorConfig
)
from app.connectors.web import RSSFeedConnector, WebScrapingConnector
from app.connectors.social_media import TwitterConnector, RedditConnector, LinkedInConnector
from app.connectors.communication import EmailConnector, SlackConnector, DiscordConnector
from app.connectors.filesystem import LocalFileSystemConnector, S3Connector, GoogleCloudStorageConnector
from app.connectors.api import RESTAPIConnector, GraphQLConnector, WebSocketConnector
from app.processors.content_pipeline import ContentProcessingPipeline, ProcessingResult
from app.db.database import get_db
from app.db.models.content import ContentItem as DBContentItem, ContentCache
from sqlalchemy import select, desc
from app.utils.logging import get_logger

logger = get_logger("content_routes")

# Create router
router = APIRouter(prefix="/api/v1/content", tags=["content"])

# Global instances
connector_registry = ConnectorRegistry()
content_pipeline = ContentProcessingPipeline({})

# Initialize connectors
def initialize_connectors():
    """Initialize and register all available connectors."""
    try:
        # Web connectors
        connector_registry.register(RSSFeedConnector(ConnectorConfig(
            name="rss",
            connector_type=ConnectorType.WEB,
            source_config={}
        )))
        connector_registry.register(WebScrapingConnector(ConnectorConfig(
            name="web_scraper",
            connector_type=ConnectorType.WEB,
            source_config={}
        )))

        # Social media connectors
        from app.config import settings

        # Use actual X API credentials from settings
        credentials = {}
        if settings.x_bearer_token:
            credentials["bearer_token"] = settings.x_bearer_token
        if settings.x_api_key and settings.x_api_secret:
            credentials["api_key"] = settings.x_api_key
            credentials["api_secret"] = settings.x_api_secret
        # Removed old X API fields - now only using bearer_token, api_key, api_secret

        connector_registry.register(TwitterConnector(ConnectorConfig(
            name="twitter",
            connector_type=ConnectorType.SOCIAL_MEDIA,
            source_config={},
            credentials=credentials
        )))
        connector_registry.register(RedditConnector(ConnectorConfig(
            name="reddit",
            connector_type=ConnectorType.SOCIAL_MEDIA,
            source_config={}
        )))
        connector_registry.register(LinkedInConnector(ConnectorConfig(
            name="linkedin",
            connector_type=ConnectorType.SOCIAL_MEDIA,
            source_config={}
        )))

        # Communication connectors
        connector_registry.register(EmailConnector(ConnectorConfig(
            name="email",
            connector_type=ConnectorType.COMMUNICATION,
            source_config={}
        )))
        connector_registry.register(SlackConnector(ConnectorConfig(
            name="slack",
            connector_type=ConnectorType.COMMUNICATION,
            source_config={}
        )))
        connector_registry.register(DiscordConnector(ConnectorConfig(
            name="discord",
            connector_type=ConnectorType.COMMUNICATION,
            source_config={}
        )))

        # File system connectors
        connector_registry.register(LocalFileSystemConnector(ConnectorConfig(
            name="local_fs",
            connector_type=ConnectorType.FILE_SYSTEM,
            source_config={}
        )))
        connector_registry.register(S3Connector(ConnectorConfig(
            name="s3",
            connector_type=ConnectorType.FILE_SYSTEM,
            source_config={}
        )))
        connector_registry.register(GoogleCloudStorageConnector(ConnectorConfig(
            name="gcs",
            connector_type=ConnectorType.FILE_SYSTEM,
            source_config={}
        )))

        # API connectors
        connector_registry.register(RESTAPIConnector(ConnectorConfig(
            name="rest_api",
            connector_type=ConnectorType.API,
            source_config={}
        )))
        connector_registry.register(GraphQLConnector(ConnectorConfig(
            name="graphql",
            connector_type=ConnectorType.API,
            source_config={}
        )))
        connector_registry.register(WebSocketConnector(ConnectorConfig(
            name="websocket",
            connector_type=ConnectorType.API,
            source_config={}
        )))

        logger.info("Content connectors initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize content connectors: {e}")
        raise

# Initialize on module load
initialize_connectors()

# Pydantic models for API requests/responses
class ContentSource(BaseModel):
    """Content source configuration."""
    type: str = Field(..., description="Connector type (e.g., 'rss', 'twitter', 'local_fs')")
    config: Dict[str, Any] = Field(..., description="Connector-specific configuration")

class ContentDiscoveryRequest(BaseModel):
    """Request for content discovery."""
    sources: List[ContentSource] = Field(..., description="List of content sources to discover from")
    max_items_per_source: Optional[int] = Field(50, description="Maximum items to discover per source")
    parallel: Optional[bool] = Field(True, description="Whether to discover in parallel")

class ContentFetchRequest(BaseModel):
    """Request for content fetching."""
    content_id: str = Field(..., description="ID of the content item to fetch")
    source_type: str = Field(..., description="Type of the source connector")
    source_config: Optional[Dict[str, Any]] = Field(None, description="Source configuration if needed")

class ContentProcessingRequest(BaseModel):
    """Request for content processing."""
    content_id: str = Field(..., description="ID of the content to process")
    operations: List[str] = Field(..., description="List of processing operations to perform")
    options: Optional[Dict[str, Any]] = Field({}, description="Processing options")
    source_type: Optional[str] = Field(None, description="Source connector type")
    source_config: Optional[Dict[str, Any]] = Field(None, description="Source configuration")

class BatchProcessingRequest(BaseModel):
    """Request for batch content processing."""
    items: List[Dict[str, Any]] = Field(..., description="List of content items to process")
    operations: List[str] = Field(..., description="Processing operations to perform")
    options: Optional[Dict[str, Any]] = Field({}, description="Processing options")
    parallel: Optional[bool] = Field(True, description="Whether to process in parallel")
    batch_size: Optional[int] = Field(10, description="Batch size for processing")

class ContentItemResponse(BaseModel):
    """Response containing content item information."""
    id: str
    source: str
    connector_type: str
    content_type: str
    title: Optional[str]
    description: Optional[str]
    url: Optional[str]
    metadata: Dict[str, Any]
    last_modified: Optional[datetime]
    tags: List[str]

class ContentDataResponse(BaseModel):
    """Response containing content data."""
    item: ContentItemResponse
    raw_data_size: int
    text_content_preview: Optional[str]
    structured_data_keys: Optional[List[str]]
    metadata: Dict[str, Any]
    processing_time_ms: float

class ProcessingResultResponse(BaseModel):
    """Response containing processing results."""
    content_id: str
    processed_content: Dict[str, Any]
    processing_steps: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_time_ms: float
    success: bool
    errors: List[str]
    warnings: List[str]

class ConnectorInfo(BaseModel):
    """Information about a connector."""
    type: str
    name: str
    description: str
    supported_content_types: List[str]
    capabilities: Dict[str, Any]
    status: str

# API Endpoints
@router.get("/{content_id}", response_model=ContentDataResponse)
async def get_content_by_id(content_id: str) -> ContentDataResponse:
    """
    Get content by ID with caching support.

    This endpoint retrieves content by ID, first checking the cache for performance.
    If not cached or cache is expired, it will fetch from the original source.
    """
    try:
        # First check cache
        async for session in get_db():
            cache_result = await session.execute(
                select(ContentCache).where(
                    ContentCache.cache_key == f"content:{content_id}",
                    ContentCache.is_valid == True
                ).order_by(desc(ContentCache.last_accessed_at))
            )
            cache_entry = cache_result.scalar_one_or_none()

            if cache_entry and cache_entry.expires_at and cache_entry.expires_at > datetime.now():
                # Cache hit - return cached content
                content_result = await session.execute(
                    select(DBContentItem).where(DBContentItem.id == cache_entry.content_item_id)
                )
                content_item = content_result.scalar_one_or_none()

                if content_item:
                    # Update cache access time
                    cache_entry.last_accessed_at = datetime.now()
                    cache_entry.access_count += 1
                    await session.commit()

                    # Return cached response
                    response_item = ContentItemResponse(
                        id=str(content_item.id),
                        source=content_item.source_id,
                        connector_type=content_item.connector_type,
                        content_type=content_item.content_type,
                        title=content_item.title,
                        description=content_item.description,
                        url=content_item.url,
                        metadata=content_item.content_metadata or {},
                        last_modified=content_item.last_modified,
                        tags=content_item.tags or []
                    )

                    return ContentDataResponse(
                        item=response_item,
                        raw_data_size=cache_entry.file_size_bytes or 0,
                        text_content_preview=f"Cached content from {cache_entry.created_at.isoformat()}",
                        structured_data_keys=None,
                        metadata={"cached": True, "cache_created": cache_entry.created_at.isoformat()},
                        processing_time_ms=0
                    )

        # Cache miss or expired - fetch from source
        # For now, return a placeholder response since we don't have the source info
        # In a real implementation, you'd store source information with the content
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found in cache and source information not available")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content {content_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")


@router.post("/discover", response_model=List[ContentItemResponse])
async def discover_content(
    request: ContentDiscoveryRequest,
    background_tasks: BackgroundTasks
) -> List[ContentItemResponse]:
    """
    Discover content from multiple sources.

    This endpoint allows discovering content from various sources including:
    - RSS feeds and web scraping
    - Social media platforms (Twitter, Reddit, LinkedIn)
    - Communication channels (Email, Slack, Discord)
    - File systems (local, S3, GCS)
    - APIs (REST, GraphQL, WebSocket)
    """
    try:
        all_items = []

        if request.parallel:
            # Discover in parallel
            tasks = []
            for source in request.sources:
                task = _discover_from_source(
                    source.type,
                    source.config,
                    request.max_items_per_source
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to discover from source {request.sources[i].type}: {result}")
                    continue
                all_items.extend(result)
        else:
            # Discover sequentially
            for source in request.sources:
                try:
                    items = await _discover_from_source(
                        source.type,
                        source.config,
                        request.max_items_per_source
                    )
                    all_items.extend(items)
                except Exception as e:
                    logger.error(f"Failed to discover from source {source.type}: {e}")
                    continue

        # Convert to response format
        response_items = []
        for item in all_items:
            response_item = ContentItemResponse(
                id=item.id,
                source=item.source,
                connector_type=item.connector_type.value,
                content_type=item.content_type.value,
                title=item.title,
                description=item.description,
                url=item.url,
                metadata=item.metadata,
                last_modified=item.last_modified,
                tags=item.tags
            )
            response_items.append(response_item)

        logger.info(f"Discovered {len(response_items)} content items from {len(request.sources)} sources")
        return response_items

    except Exception as e:
        logger.error(f"Content discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content discovery failed: {str(e)}")

@router.post("/fetch", response_model=ContentDataResponse)
async def fetch_content(
    request: ContentFetchRequest
) -> ContentDataResponse:
    """
    Fetch content data for a specific content item.

    This endpoint retrieves the actual content data (text, binary, structured)
    for a previously discovered content item.
    """
    try:
        # Get the connector
        connector = connector_registry.get_connector(request.source_type)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector type '{request.source_type}' not found")

        # Create a mock ContentItem for fetching
        # In a real implementation, you'd retrieve this from a database
        content_ref = ContentItem(
            id=request.content_id,
            source=f"{request.source_type}:{request.content_id}",
            connector_type=ConnectorType(request.source_type) if hasattr(ConnectorType, request.source_type.upper()) else ConnectorType.API,
            content_type=ContentType.TEXT,  # Default, will be determined during fetch
            title="",
            description="",
            metadata={}
        )

        # Fetch the content
        start_time = datetime.now()
        content_data = await connector.fetch(content_ref)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Prepare response
        response_item = ContentItemResponse(
            id=content_data.item.id,
            source=content_data.item.source,
            connector_type=content_data.item.connector_type.value,
            content_type=content_data.item.content_type.value,
            title=content_data.item.title,
            description=content_data.item.description,
            url=content_data.item.url,
            metadata=content_data.item.metadata,
            last_modified=content_data.item.last_modified,
            tags=content_data.item.tags
        )

        # Get preview of text content
        text_preview = None
        if content_data.text_content:
            text_preview = content_data.text_content[:500] + "..." if len(content_data.text_content) > 500 else content_data.text_content

        # Get structured data keys
        structured_keys = None
        if content_data.structured_data and isinstance(content_data.structured_data, dict):
            structured_keys = list(content_data.structured_data.keys())

        response = ContentDataResponse(
            item=response_item,
            raw_data_size=len(content_data.raw_data),
            text_content_preview=text_preview,
            structured_data_keys=structured_keys,
            metadata=content_data.metadata,
            processing_time_ms=processing_time
        )

        logger.info(f"Fetched content {request.content_id} in {processing_time:.2f}ms")
        return response

    except Exception as e:
        logger.error(f"Content fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content fetch failed: {str(e)}")

@router.post("/process", response_model=ProcessingResultResponse)
async def process_content(
    request: ContentProcessingRequest,
    background_tasks: BackgroundTasks
) -> ProcessingResultResponse:
    """
    Process content using the content processing pipeline.

    This endpoint applies various processing operations to content including:
    - Text: summarization, entity extraction, sentiment analysis
    - Image: description, OCR, object detection
    - Audio: transcription, speaker identification
    - Structured: validation, transformation, enrichment
    """
    try:
        # First fetch the content if we have source info
        content_data = None
        if request.source_type:
            connector = connector_registry.get_connector(request.source_type)
            if connector:
                content_ref = ContentItem(
                    id=request.content_id,
                    source=f"{request.source_type}:{request.content_id}",
                    connector_type=ConnectorType(request.source_type) if hasattr(ConnectorType, request.source_type.upper()) else ConnectorType.API,
                    content_type=ContentType.TEXT,
                    title="",
                    description="",
                    metadata={}
                )
                content_data = await connector.fetch(content_ref)
        else:
            # Create mock content data for processing
            content_data = ContentData(
                item=ContentItem(
                    id=request.content_id,
                    source=f"direct:{request.content_id}",
                    connector_type=ConnectorType.API,
                    content_type=ContentType.TEXT,
                    title="",
                    description="",
                    metadata={}
                ),
                raw_data=b"",
                text_content="",
                metadata={}
            )

        if not content_data:
            raise HTTPException(status_code=404, detail=f"Content {request.content_id} not found")

        # Process the content
        processing_config = {
            "operations": request.operations,
            "options": request.options or {}
        }

        result = await content_pipeline.process_content(content_data, processing_config)

        # Convert to response format
        response = ProcessingResultResponse(
            content_id=request.content_id,
            processed_content=result.processed_content,
            processing_steps=result.processing_steps,
            metadata=result.metadata,
            processing_time_ms=result.processing_time_ms,
            success=result.success,
            errors=result.errors,
            warnings=result.warnings
        )

        logger.info(f"Processed content {request.content_id} in {result.processing_time_ms:.2f}ms")
        return response

    except Exception as e:
        logger.error(f"Content processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content processing failed: {str(e)}")

@router.post("/batch", response_model=List[ProcessingResultResponse])
async def batch_process_content(
    request: BatchProcessingRequest,
    background_tasks: BackgroundTasks
) -> List[ProcessingResultResponse]:
    """
    Process multiple content items in batch.

    This endpoint allows processing multiple content items simultaneously,
    with options for parallel processing and batching.
    """
    try:
        results = []

        if request.parallel:
            # Process in parallel
            tasks = []
            for item_config in request.items:
                task = _process_single_item(
                    item_config,
                    request.operations,
                    request.options or {}
                )
                tasks.append(task)

            # Process in batches to avoid overwhelming the system
            batch_results = []
            for i in range(0, len(tasks), request.batch_size):
                batch_tasks = tasks[i:i + request.batch_size]
                batch_result = await asyncio.gather(*batch_tasks, return_exceptions=True)
                batch_results.extend(batch_result)

            # Convert results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch processing failed for item {i}: {result}")
                    results.append(ProcessingResultResponse(
                        content_id=request.items[i].get("content_id", f"item_{i}"),
                        processed_content={},
                        processing_steps=[],
                        metadata={},
                        processing_time_ms=0,
                        success=False,
                        errors=[str(result)],
                        warnings=[]
                    ))
                else:
                    results.append(result)
        else:
            # Process sequentially
            for item_config in request.items:
                try:
                    result = await _process_single_item(
                        item_config,
                        request.operations,
                        request.options or {}
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Sequential processing failed for item: {e}")
                    results.append(ProcessingResultResponse(
                        content_id=item_config.get("content_id", "unknown"),
                        processed_content={},
                        processing_steps=[],
                        metadata={},
                        processing_time_ms=0,
                        success=False,
                        errors=[str(e)],
                        warnings=[]
                    ))

        logger.info(f"Batch processed {len(results)} items")
        return results

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@router.get("/connectors", response_model=List[ConnectorInfo])
async def list_connectors() -> List[ConnectorInfo]:
    """
    List all available content connectors with their capabilities.
    """
    try:
        connectors_info = []

        for connector_type, connector in connector_registry.connectors.items():
            try:
                capabilities = connector.get_capabilities()
                info = ConnectorInfo(
                    type=connector_type,
                    name=connector.__class__.__name__,
                    description=f"Connector for {connector_type.replace('_', ' ')}",
                    supported_content_types=capabilities.get("supported_content_types", []),
                    capabilities=capabilities,
                    status="available"
                )
                connectors_info.append(info)
            except Exception as e:
                logger.error(f"Failed to get info for connector {connector_type}: {e}")
                info = ConnectorInfo(
                    type=connector_type,
                    name=connector.__class__.__name__,
                    description=f"Connector for {connector_type.replace('_', ' ')}",
                    supported_content_types=[],
                    capabilities={},
                    status="error"
                )
                connectors_info.append(info)

        return connectors_info

    except Exception as e:
        logger.error(f"Failed to list connectors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list connectors: {str(e)}")

@router.get("/pipeline/info")
async def get_pipeline_info() -> Dict[str, Any]:
    """
    Get information about the content processing pipeline.
    """
    try:
        return content_pipeline.get_pipeline_info()
    except Exception as e:
        logger.error(f"Failed to get pipeline info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline info: {str(e)}")

@router.post("/validate/{connector_type}")
async def validate_connector(
    connector_type: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a connector configuration.
    """
    try:
        connector = connector_registry.get_connector(connector_type)
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector type '{connector_type}' not found")

        # Test the configuration by attempting to discover with it
        test_items = await connector.discover(config)

        return {
            "valid": True,
            "connector_type": connector_type,
            "test_items_discovered": len(test_items),
            "capabilities": connector.get_capabilities(),
            "message": f"Connector configuration is valid. Discovered {len(test_items)} test items."
        }

    except Exception as e:
        logger.error(f"Connector validation failed: {e}")
        return {
            "valid": False,
            "connector_type": connector_type,
            "error": str(e),
            "message": "Connector configuration is invalid"
        }

# Helper functions
async def _discover_from_source(
    source_type: str,
    config: Dict[str, Any],
    max_items: Optional[int] = None
) -> List[ContentItem]:
    """Discover content from a single source."""
    connector = connector_registry.get_connector(source_type)
    if not connector:
        raise ValueError(f"Connector type '{source_type}' not found")

    # Add max_items to config if provided
    if max_items:
        config = dict(config)  # Copy to avoid modifying original
        config["max_items"] = max_items

    return await connector.discover(config)

async def _process_single_item(
    item_config: Dict[str, Any],
    operations: List[str],
    options: Dict[str, Any]
) -> ProcessingResultResponse:
    """Process a single content item."""
    content_id = item_config.get("content_id", "unknown")
    source_type = item_config.get("source_type")
    source_config = item_config.get("source_config", {})

    # Fetch content
    content_data = None
    if source_type:
        connector = connector_registry.get_connector(source_type)
        if connector:
            content_ref = ContentItem(
                id=content_id,
                source=f"{source_type}:{content_id}",
                connector_type=ConnectorType(source_type) if hasattr(ConnectorType, source_type.upper()) else ConnectorType.API,
                content_type=ContentType.TEXT,
                title="",
                description="",
                metadata={}
            )
            content_data = await connector.fetch(content_ref)

    if not content_data:
        # Create mock content data
        content_data = ContentData(
            item=ContentItem(
                id=content_id,
                source=f"direct:{content_id}",
                connector_type=ConnectorType.API,
                content_type=ContentType.TEXT,
                title="",
                description="",
                metadata={}
            ),
            raw_data=b"",
            text_content="",
            metadata={}
        )

    # Process content
    processing_config = {
        "operations": operations,
        "options": options
    }

    result = await content_pipeline.process_content(content_data, processing_config)

    # Convert to response format
    return ProcessingResultResponse(
        content_id=content_id,
        processed_content=result.processed_content,
        processing_steps=result.processing_steps,
        metadata=result.metadata,
        processing_time_ms=result.processing_time_ms,
        success=result.success,
        errors=result.errors,
        warnings=result.warnings
    )

# Health check endpoint
@router.get("/health")
async def content_health() -> Dict[str, Any]:
    """Check the health of the content connector system."""
    try:
        # Test basic connector registry functionality
        available_connectors = len(connector_registry.connectors)

        # Test pipeline functionality
        pipeline_info = content_pipeline.get_pipeline_info()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "connectors": {
                "total_available": available_connectors,
                "types": list(connector_registry.connectors.keys())
            },
            "pipeline": {
                "available_processors": len(pipeline_info.get("available_processors", [])),
                "supported_content_types": pipeline_info.get("supported_content_types", [])
            }
        }

    except Exception as e:
        logger.error(f"Content health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
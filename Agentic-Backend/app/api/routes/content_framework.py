"""
API routes for Multi-Modal Content Framework.

This module provides REST endpoints for content processing, type detection,
metadata extraction, and caching operations.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime
import os
import tempfile

from app.services.content_framework import (
    content_processor,
    content_detector,
    content_cache,
    ContentData,
    ContentType,
    ContentMetadata
)
from app.utils.logging import get_logger

logger = get_logger("content_framework_routes")

router = APIRouter(prefix="/content", tags=["Content Framework"])


# Pydantic models for request/response
class ContentProcessRequest(BaseModel):
    """Content processing request."""
    source_url: Optional[str] = Field(default=None, description="URL to fetch content from")
    content_type_hint: Optional[str] = Field(default=None, description="Hint about content type")
    extract_metadata: bool = Field(default=True, description="Whether to extract metadata")
    cache_result: bool = Field(default=True, description="Whether to cache the result")


class ContentProcessResponse(BaseModel):
    """Content processing response."""
    content_id: str
    content_type: str
    format: str
    mime_type: str
    size_bytes: int
    processing_time_ms: float
    quality_score: Optional[float]
    metadata: Dict[str, Any]
    cached: bool
    timestamp: datetime


class BatchProcessRequest(BaseModel):
    """Batch content processing request."""
    items: List[ContentProcessRequest] = Field(..., description="List of content items to process")
    parallel_processing: bool = Field(default=True, description="Whether to process in parallel")


class BatchProcessResponse(BaseModel):
    """Batch processing response."""
    total_items: int
    processed_items: int
    failed_items: int
    results: List[ContentProcessResponse]
    processing_time_ms: float
    timestamp: datetime


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    total_entries: int
    total_size_bytes: int
    total_size_mb: float
    max_size_mb: int
    utilization_percent: float
    timestamp: datetime


@router.post("/process", response_model=ContentProcessResponse)
async def process_content(request: ContentProcessRequest) -> ContentProcessResponse:
    """
    Process content from URL or uploaded data.

    This endpoint processes content from a URL or uploaded file,
    automatically detects the content type, extracts metadata,
    and returns comprehensive content information.
    """
    start_time = datetime.now()

    try:
        content_data = None

        if request.source_url:
            # Process from URL
            content_data = await content_processor.process_url(request.source_url)
        else:
            raise HTTPException(status_code=400, detail="Either source_url or file upload required")

        # Enrich metadata if requested
        if request.extract_metadata:
            content_data = await content_processor.enrich_metadata(content_data)

        # Cache result if requested
        cached = False
        if request.cache_result:
            # Cache the metadata (content itself might be too large)
            cache_key = f"metadata_{content_data.id}"
            await content_cache.put(cache_key, "metadata", content_data.metadata.__dict__, ttl_seconds=3600)
            cached = True

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        response = ContentProcessResponse(
            content_id=content_data.id,
            content_type=content_data.metadata.content_type.value,
            format=content_data.metadata.format.value,
            mime_type=content_data.metadata.mime_type,
            size_bytes=content_data.metadata.size_bytes,
            processing_time_ms=processing_time,
            quality_score=content_data.metadata.quality_score,
            metadata={
                "char_count": content_data.metadata.char_count,
                "word_count": content_data.metadata.word_count,
                "line_count": content_data.metadata.line_count,
                "encoding": content_data.metadata.encoding,
                "language": content_data.metadata.language,
                "width": content_data.metadata.width,
                "height": content_data.metadata.height,
                "duration_seconds": content_data.metadata.duration_seconds,
                "page_count": content_data.metadata.page_count,
                "custom_fields": content_data.metadata.custom_fields
            },
            cached=cached,
            timestamp=datetime.now()
        )

        logger.info(f"Processed content {content_data.id}: {content_data.metadata.content_type.value}")
        return response

    except Exception as e:
        logger.error(f"Failed to process content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process content: {str(e)}")


@router.post("/upload", response_model=ContentProcessResponse)
async def upload_and_process_content(
    file: UploadFile = File(...),
    extract_metadata: bool = True,
    cache_result: bool = True
) -> ContentProcessResponse:
    """
    Upload and process a file.

    This endpoint accepts file uploads, processes them automatically,
    detects content type, extracts metadata, and returns comprehensive information.
    """
    start_time = datetime.now()

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Process the file
            content_data = await content_processor.process_file(temp_file_path)

            # Enrich metadata if requested
            if extract_metadata:
                content_data = await content_processor.enrich_metadata(content_data)

            # Cache result if requested
            cached = False
            if cache_result:
                cache_key = f"metadata_{content_data.id}"
                await content_cache.put(cache_key, "metadata", content_data.metadata.__dict__, ttl_seconds=3600)
                cached = True

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            response = ContentProcessResponse(
                content_id=content_data.id,
                content_type=content_data.metadata.content_type.value,
                format=content_data.metadata.format.value,
                mime_type=content_data.metadata.mime_type,
                size_bytes=content_data.metadata.size_bytes,
                processing_time_ms=processing_time,
                quality_score=content_data.metadata.quality_score,
                metadata={
                    "filename": file.filename,
                    "char_count": content_data.metadata.char_count,
                    "word_count": content_data.metadata.word_count,
                    "line_count": content_data.metadata.line_count,
                    "encoding": content_data.metadata.encoding,
                    "width": content_data.metadata.width,
                    "height": content_data.metadata.height,
                    "duration_seconds": content_data.metadata.duration_seconds,
                    "page_count": content_data.metadata.page_count,
                    "custom_fields": content_data.metadata.custom_fields
                },
                cached=cached,
                timestamp=datetime.now()
            )

            logger.info(f"Processed uploaded file {file.filename}: {content_data.metadata.content_type.value}")
            return response

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Failed to process uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded file: {str(e)}")


@router.post("/batch", response_model=BatchProcessResponse)
async def batch_process_content(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks
) -> BatchProcessResponse:
    """
    Process multiple content items in batch.

    This endpoint processes multiple content items efficiently,
    with support for parallel processing and comprehensive error handling.
    """
    start_time = datetime.now()

    try:
        results = []
        failed_count = 0

        if request.parallel_processing:
            # Process in parallel
            import asyncio

            async def process_item(item_request):
                try:
                    return await process_content(item_request)
                except Exception as e:
                    logger.error(f"Failed to process batch item: {e}")
                    return None

            tasks = [process_item(item) for item in request.items]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception) or result is None:
                    failed_count += 1
                else:
                    results.append(result)
        else:
            # Process sequentially
            for item in request.items:
                try:
                    result = await process_content(item)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process batch item: {e}")
                    failed_count += 1

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        response = BatchProcessResponse(
            total_items=len(request.items),
            processed_items=len(results),
            failed_items=failed_count,
            results=results,
            processing_time_ms=processing_time,
            timestamp=datetime.now()
        )

        logger.info(f"Batch processed {len(request.items)} items: {len(results)} successful, {failed_count} failed")
        return response

    except Exception as e:
        logger.error(f"Failed to process batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process batch: {str(e)}")


@router.get("/{content_id}")
async def get_content_data(content_id: str) -> Dict[str, Any]:
    """
    Get processed content data by ID.

    Retrieves cached content data and metadata for a specific content item.
    """
    try:
        # Try to get from cache
        cache_key = f"metadata_{content_id}"
        cached_metadata = await content_cache.get(cache_key, "metadata")

        if cached_metadata:
            return {
                "content_id": content_id,
                "cached": True,
                "metadata": cached_metadata,
                "timestamp": datetime.now().isoformat()
            }

        raise HTTPException(status_code=404, detail=f"Content {content_id} not found in cache")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content data: {str(e)}")


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """
    Get content cache statistics.

    Returns comprehensive statistics about the content cache
    including size, utilization, and performance metrics.
    """
    try:
        stats = content_cache.get_stats()

        response = CacheStatsResponse(
            total_entries=stats['total_entries'],
            total_size_bytes=stats['total_size_bytes'],
            total_size_mb=stats['total_size_mb'],
            max_size_mb=stats['max_size_mb'],
            utilization_percent=stats['utilization_percent'],
            timestamp=datetime.now()
        )

        return response

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.delete("/cache/{content_id}")
async def invalidate_cache(content_id: str) -> Dict[str, Any]:
    """
    Invalidate cached content data.

    Removes content data from the cache for the specified content ID.
    """
    try:
        cache_key = f"metadata_{content_id}"
        await content_cache.invalidate(content_id, "metadata")

        response = {
            "message": f"Cache invalidated for content {content_id}",
            "cache_key": cache_key,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Invalidated cache for content {content_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {str(e)}")


@router.post("/detect")
async def detect_content_type(
    url: Optional[str] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect content type from URL or filename.

    This endpoint performs content type detection without full processing,
    useful for quick type identification.
    """
    try:
        if url:
            metadata = await content_detector.detect_from_url(url)
        elif filename:
            # For filename-only detection, create a mock file path
            import mimetypes
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type:
                from app.services.content_framework import ContentFormat, ContentType as CTEnum
                content_type, content_format = content_detector._classify_mime_type(mime_type)
                metadata = ContentMetadata(
                    content_type=content_type,
                    format=content_format,
                    mime_type=mime_type,
                    size_bytes=0
                )
            else:
                metadata = ContentMetadata(
                    content_type=ContentType.UNKNOWN,
                    format=ContentFormat.PLAIN_TEXT,
                    mime_type="application/octet-stream",
                    size_bytes=0
                )
        else:
            raise HTTPException(status_code=400, detail="Either url or filename parameter required")

        response = {
            "content_type": metadata.content_type.value,
            "format": metadata.format.value,
            "mime_type": metadata.mime_type,
            "detected_at": datetime.now().isoformat()
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect content type: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to detect content type: {str(e)}")


@router.get("/types")
async def get_supported_content_types() -> Dict[str, Any]:
    """
    Get supported content types and formats.

    Returns information about all supported content types,
    formats, and their capabilities.
    """
    try:
        supported_types = {
            "text": {
                "formats": ["plain", "markdown", "html", "json", "xml", "csv"],
                "capabilities": ["metadata_extraction", "language_detection", "quality_scoring"]
            },
            "image": {
                "formats": ["jpeg", "png", "gif", "webp", "bmp", "tiff"],
                "capabilities": ["dimension_extraction", "format_detection", "quality_scoring"]
            },
            "audio": {
                "formats": ["mp3", "wav", "flac", "ogg", "m4a"],
                "capabilities": ["duration_extraction", "bitrate_detection", "quality_scoring"]
            },
            "video": {
                "formats": ["mp4", "avi", "mov", "webm"],
                "capabilities": ["duration_extraction", "format_detection"]
            },
            "document": {
                "formats": ["pdf", "docx", "xlsx", "pptx"],
                "capabilities": ["page_count", "metadata_extraction"]
            },
            "structured": {
                "formats": ["json", "xml", "csv"],
                "capabilities": ["schema_validation", "structure_analysis"]
            }
        }

        response = {
            "supported_types": supported_types,
            "total_types": len(supported_types),
            "features": [
                "automatic_type_detection",
                "metadata_extraction",
                "quality_scoring",
                "intelligent_caching",
                "batch_processing"
            ],
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get supported content types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported content types: {str(e)}")
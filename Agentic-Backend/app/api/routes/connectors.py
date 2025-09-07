"""
Content Connectors API Routes.

This module provides REST API endpoints for managing content connectors,
including discovery, fetching, validation, and processing of content from various sources.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.connectors.base import (
    connector_registry,
    ContentConnector,
    ContentType,
    ConnectorType,
    ContentItem,
    ContentData,
    ValidationResult
)
from app.services.content_validation_service import content_validation_service
from app.services.content_processing_pipeline import content_processing_pipeline, ProcessingStage
from app.api.dependencies import get_db_session, verify_api_key
from app.utils.logging import get_logger

logger = get_logger("connectors_api")
router = APIRouter(
    tags=["Content Connectors"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Connector Management Endpoints
# ============================================================================

@router.get("/connectors", response_model=Dict[str, Any])
async def list_connectors(
    connector_type: Optional[ConnectorType] = Query(None, description="Filter by connector type"),
    enabled_only: bool = Query(True, description="Show only enabled connectors"),
    current_user: Dict = Depends(verify_api_key)
):
    """List all registered content connectors."""
    try:
        connectors = connector_registry.list_connectors()

        # Apply filters
        if connector_type:
            connectors = [c for c in connectors if c['type'] == connector_type.value]

        if enabled_only:
            connectors = [c for c in connectors if c['enabled']]

        return {
            "status": "success",
            "data": {
                "connectors": connectors,
                "total": len(connectors),
                "filtered_by": {
                    "type": connector_type.value if connector_type else None,
                    "enabled_only": enabled_only
                }
            }
        }

    except Exception as e:
        logger.error(f"Failed to list connectors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve connectors: {str(e)}"
        )


@router.get("/connectors/{connector_name}", response_model=Dict[str, Any])
async def get_connector_info(
    connector_name: str,
    current_user: Dict = Depends(verify_api_key)
):
    """Get detailed information about a specific connector."""
    try:
        connector = connector_registry.get_connector(connector_name)

        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector '{connector_name}' not found"
            )

        return {
            "status": "success",
            "data": {
                "name": connector.name,
                "type": connector.connector_type.value,
                "enabled": connector.config.enabled,
                "capabilities": connector.get_capabilities(),
                "config": {
                    "rate_limits": bool(connector.config.rate_limits),
                    "retry_config": bool(connector.config.retry_config),
                    "credentials": bool(connector.config.credentials)
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connector info for {connector_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve connector info: {str(e)}"
        )


@router.post("/connectors/{connector_name}/health", response_model=Dict[str, Any])
async def check_connector_health(
    connector_name: str,
    current_user: Dict = Depends(verify_api_key)
):
    """Check the health status of a specific connector."""
    try:
        connector = connector_registry.get_connector(connector_name)

        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector '{connector_name}' not found"
            )

        health_status = await connector.health_check()

        return {
            "status": "success",
            "data": health_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check health for connector {connector_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check connector health: {str(e)}"
        )


@router.get("/connectors/health", response_model=Dict[str, Any])
async def check_all_connectors_health(
    current_user: Dict = Depends(verify_api_key)
):
    """Check the health status of all connectors."""
    try:
        health_status = await connector_registry.health_check_all()

        return {
            "status": "success",
            "data": health_status
        }

    except Exception as e:
        logger.error(f"Failed to check all connectors health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check connectors health: {str(e)}"
        )


# ============================================================================
# Content Discovery Endpoints
# ============================================================================

@router.post("/connectors/{connector_name}/discover", response_model=Dict[str, Any])
async def discover_content(
    connector_name: str,
    source_config: Dict[str, Any],
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of items to discover"),
    current_user: Dict = Depends(verify_api_key)
):
    """Discover content using a specific connector."""
    try:
        connector = connector_registry.get_connector(connector_name)

        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector '{connector_name}' not found"
            )

        if not connector.config.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Connector '{connector_name}' is disabled"
            )

        # Discover content
        content_items = await connector.discover(source_config)

        # Apply limit
        content_items = content_items[:limit]

        # Convert to response format
        items_data = []
        for item in content_items:
            items_data.append({
                "id": item.id,
                "source": item.source,
                "connector_type": item.connector_type.value,
                "content_type": item.content_type.value,
                "title": item.title,
                "description": item.description,
                "url": item.url,
                "size_bytes": item.size_bytes,
                "tags": item.tags,
                "discovered_at": item.discovered_at.isoformat() if item.discovered_at else None,
                "last_modified": item.last_modified.isoformat() if item.last_modified else None
            })

        return {
            "status": "success",
            "data": {
                "connector": connector_name,
                "items": items_data,
                "total_discovered": len(content_items),
                "limit": limit
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to discover content with {connector_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover content: {str(e)}"
        )


# ============================================================================
# Content Fetching Endpoints
# ============================================================================

@router.post("/connectors/{connector_name}/fetch", response_model=Dict[str, Any])
async def fetch_content(
    connector_name: str,
    content_ref: str = Query(..., description="Content reference (ID, URL, or identifier)"),
    current_user: Dict = Depends(verify_api_key)
):
    """Fetch content using a specific connector."""
    try:
        connector = connector_registry.get_connector(connector_name)

        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector '{connector_name}' not found"
            )

        if not connector.config.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Connector '{connector_name}' is disabled"
            )

        # Fetch content
        content_data = await connector.fetch(content_ref)

        return {
            "status": "success",
            "data": {
                "connector": connector_name,
                "content_ref": content_ref,
                "content_type": content_data.item.content_type.value,
                "size_bytes": len(content_data.raw_data),
                "text_content_length": len(content_data.text_content) if content_data.text_content else 0,
                "has_structured_data": content_data.structured_data is not None,
                "fetched_at": content_data.fetched_at.isoformat() if content_data.fetched_at else None,
                "processing_time_ms": content_data.processing_time_ms
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch content with {connector_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch content: {str(e)}"
        )


# ============================================================================
# Content Validation Endpoints
# ============================================================================

@router.post("/validate", response_model=Dict[str, Any])
async def validate_content(
    file: UploadFile = File(...),
    content_type: str = Query(..., description="Type of content (text, image, audio, video, document)"),
    current_user: Dict = Depends(verify_api_key)
):
    """Validate uploaded content."""
    try:
        # Read file content
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Empty file provided"
            )

        # Validate content
        validation_result = await content_validation_service.validate_content(
            content,
            content_type,
            file.filename
        )

        return {
            "status": "success" if validation_result["is_valid"] else "failed",
            "data": {
                "filename": file.filename,
                "content_type": content_type,
                "is_valid": validation_result["is_valid"],
                "errors": validation_result.get("errors", []),
                "warnings": validation_result.get("warnings", []),
                "sanitized": validation_result.get("sanitized", False),
                "metadata": validation_result.get("metadata", {}),
                "validated_at": validation_result.get("validated_at")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate content: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate content: {str(e)}"
        )


@router.post("/connectors/{connector_name}/validate", response_model=Dict[str, Any])
async def validate_with_connector(
    connector_name: str,
    content_ref: str = Query(..., description="Content reference to validate"),
    current_user: Dict = Depends(verify_api_key)
):
    """Validate content using a specific connector's validation method."""
    try:
        connector = connector_registry.get_connector(connector_name)

        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"Connector '{connector_name}' not found"
            )

        if not connector.config.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Connector '{connector_name}' is disabled"
            )

        # Fetch content first
        content_data = await connector.fetch(content_ref)

        # Validate content
        validation_result = await connector.validate(content_data)

        return {
            "status": "success" if validation_result.is_valid else "failed",
            "data": {
                "connector": connector_name,
                "content_ref": content_ref,
                "is_valid": validation_result.is_valid,
                "status": validation_result.status.value,
                "message": validation_result.message,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "metadata": validation_result.metadata,
                "validated_at": validation_result.validated_at.isoformat() if validation_result.validated_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate content with {connector_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate content: {str(e)}"
        )


# ============================================================================
# Content Processing Pipeline Endpoints
# ============================================================================

@router.post("/process", response_model=Dict[str, Any])
async def process_content(
    file: UploadFile = File(...),
    content_type: str = Query(..., description="Type of content (text, image, audio, video, document)"),
    stages: Optional[List[str]] = Query(None, description="Processing stages to run (comma-separated)"),
    current_user: Dict = Depends(verify_api_key)
):
    """Process content through the processing pipeline."""
    try:
        # Read file content
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Empty file provided"
            )

        # Parse stages
        pipeline_stages = None
        if stages:
            try:
                pipeline_stages = [ProcessingStage(stage.strip()) for stage in stages]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid processing stage: {str(e)}"
                )

        # Prepare context
        context = {
            "content_type": content_type,
            "filename": file.filename,
            "source": "upload",
            "uploaded_at": datetime.now().isoformat()
        }

        # Process through pipeline
        result = await content_processing_pipeline.process_content(
            content, context, pipeline_stages
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "content_type": content_type,
                "success": result.success,
                "stages_processed": list(result.stage_results.keys()),
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata,
                "processing_time": result.processing_time,
                "total_processing_time": result.metadata.get("total_processing_time")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process content: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process content: {str(e)}"
        )


@router.get("/pipeline/stages", response_model=Dict[str, Any])
async def get_pipeline_stages(
    current_user: Dict = Depends(verify_api_key)
):
    """Get available processing pipeline stages."""
    try:
        stages = content_processing_pipeline.get_available_stages()

        stage_details = {}
        for stage_name in stages:
            try:
                stage_enum = ProcessingStage(stage_name)
                processors = content_processing_pipeline.get_stage_processors(stage_enum)
                stage_details[stage_name] = {
                    "processors": processors,
                    "description": f"Processing stage: {stage_name}"
                }
            except ValueError:
                continue

        return {
            "status": "success",
            "data": {
                "stages": stages,
                "stage_details": stage_details,
                "total_stages": len(stages)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get pipeline stages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pipeline stages: {str(e)}"
        )


# ============================================================================
# Content Types and Capabilities
# ============================================================================

@router.get("/types", response_model=Dict[str, Any])
async def get_content_types(
    current_user: Dict = Depends(verify_api_key)
):
    """Get supported content types and their capabilities."""
    try:
        content_types = [ct.value for ct in ContentType]
        connector_types = [ct.value for ct in ConnectorType]

        # Get validation service stats
        validation_stats = content_validation_service.get_validation_stats()

        return {
            "status": "success",
            "data": {
                "content_types": content_types,
                "connector_types": connector_types,
                "validation_stats": validation_stats
            }
        }

    except Exception as e:
        logger.error(f"Failed to get content types: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve content types: {str(e)}"
        )
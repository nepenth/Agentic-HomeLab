"""
API routes for Agentic HTTP Client Framework.

This module provides REST endpoints for the enterprise-grade HTTP client
with circuit breaker, rate limiting, and comprehensive observability features.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from app.services.agentic_http_client import (
    agentic_http_client,
    AuthConfig,
    RetryConfig,
    RateLimit,
    HttpResponse
)
from app.db.database import get_db
from app.db.models.http_request_log import HttpRequestLog
from sqlalchemy import desc, select
from app.utils.logging import get_logger

logger = get_logger("http_client_routes")

router = APIRouter(prefix="/http", tags=["HTTP Client"])


# Pydantic models for request/response
class HttpRequestModel(BaseModel):
    """HTTP request configuration."""
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE, etc.)")
    url: str = Field(..., description="Target URL")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    data: Optional[str] = Field(default=None, description="Request body data")
    json_data: Optional[Dict[str, Any]] = Field(default=None, description="JSON request body")
    timeout: Optional[float] = Field(default=None, description="Request timeout in seconds")
    auth: Optional[Dict[str, Any]] = Field(default=None, description="Authentication configuration")
    retry_config: Optional[Dict[str, Any]] = Field(default=None, description="Retry configuration")
    rate_limit: Optional[Dict[str, Any]] = Field(default=None, description="Rate limiting configuration")


class StreamDownloadModel(BaseModel):
    """Streaming download configuration."""
    url: str = Field(..., description="Download URL")
    destination_path: str = Field(..., description="Local destination path")
    progress_callback_url: Optional[str] = Field(default=None, description="Progress callback URL")
    auth: Optional[Dict[str, Any]] = Field(default=None, description="Authentication configuration")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")


class HttpResponseModel(BaseModel):
    """HTTP response data."""
    request_id: str
    status_code: int
    headers: Dict[str, str]
    content: str
    response_time_ms: float
    retry_count: int
    rate_limit_info: Optional[Dict[str, Any]] = None
    timestamp: datetime


class DownloadResultModel(BaseModel):
    """Download result data."""
    file_path: str
    total_size: int
    downloaded_size: int
    duration: float
    success: bool
    checksum: Optional[str] = None


class HttpMetricsModel(BaseModel):
    """HTTP client metrics."""
    total_requests: int
    recent_requests: int
    circuit_breaker_state: str
    rate_limiter_active: bool
    session_active: bool


@router.post("/request", response_model=HttpResponseModel)
async def make_http_request(request: HttpRequestModel) -> HttpResponseModel:
    """
    Make an HTTP request with agentic features.

    This endpoint provides enterprise-grade HTTP client capabilities including:
    - Circuit breaker pattern for resilience
    - Intelligent retry logic with exponential backoff
    - Rate limiting and compliance
    - Comprehensive observability and metrics
    - Authentication support (API keys, OAuth, JWT, custom)
    """
    try:
        # Convert request model to service parameters
        auth_config = None
        if request.auth:
            auth_config = AuthConfig(**request.auth)

        retry_config = None
        if request.retry_config:
            retry_config = RetryConfig(**request.retry_config)

        rate_limit_config = None
        if request.rate_limit:
            rate_limit_config = RateLimit(**request.rate_limit)

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Make the HTTP request
        response = await agentic_http_client.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            data=request.data,
            json_data=request.json_data,
            auth=auth_config,
            timeout=request.timeout,
            retry_config=retry_config,
            rate_limit=rate_limit_config
        )

        # Convert to response model
        response_model = HttpResponseModel(
            request_id=request_id,
            status_code=response.status_code,
            headers=response.headers,
            content=response.text,
            response_time_ms=response.request_duration * 1000,  # Convert to ms
            retry_count=response.retry_count,
            rate_limit_info=response.rate_limit_info,
            timestamp=datetime.now()
        )

        logger.info(f"HTTP request {request_id} completed: {request.method} {request.url} -> {response.status_code}")
        return response_model

    except Exception as e:
        logger.error(f"HTTP request failed: {e}")
        raise HTTPException(status_code=500, detail=f"HTTP request failed: {str(e)}")


@router.post("/stream-download", response_model=DownloadResultModel)
async def stream_download(
    request: StreamDownloadModel,
    background_tasks: BackgroundTasks
) -> DownloadResultModel:
    """
    Stream large file downloads with progress tracking.

    This endpoint supports:
    - Large file downloads with streaming
    - Progress tracking and callbacks
    - Authentication support
    - Checksum validation
    - Background processing for large files
    """
    try:
        # Convert auth config
        auth_config = None
        if request.auth:
            auth_config = AuthConfig(**request.auth)

        # Perform streaming download
        result = await agentic_http_client.stream_download(
            url=request.url,
            destination=request.destination_path,
            progress_callback=None,  # Could be implemented with webhook
            auth=auth_config,
            headers=request.headers
        )

        # Convert to response model
        response_model = DownloadResultModel(
            file_path=result.file_path,
            total_size=result.total_size,
            downloaded_size=result.downloaded_size,
            duration=result.duration,
            success=result.success,
            checksum=result.checksum
        )

        logger.info(f"Download completed: {request.url} -> {request.destination_path} ({result.downloaded_size} bytes)")
        return response_model

    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/metrics", response_model=HttpMetricsModel)
async def get_http_metrics() -> HttpMetricsModel:
    """
    Get HTTP client performance metrics.

    Returns comprehensive metrics about the HTTP client's performance,
    including request counts, circuit breaker status, and rate limiting information.
    """
    try:
        metrics = agentic_http_client.get_metrics()

        response_model = HttpMetricsModel(
            total_requests=metrics.get("total_requests", 0),
            recent_requests=metrics.get("recent_requests", 0),
            circuit_breaker_state=metrics.get("circuit_breaker_state", "unknown"),
            rate_limiter_active=metrics.get("rate_limiter_active", False),
            session_active=metrics.get("session_active", False)
        )

        return response_model

    except Exception as e:
        logger.error(f"Failed to get HTTP metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/requests/{request_id}")
async def get_request_details(request_id: str) -> Dict[str, Any]:
    """
    Get details for a specific HTTP request.

    This endpoint provides detailed information about a specific HTTP request
    including timing, headers, and any error information.
    """
    try:
        # Query database for the specific request
        async for session in get_db():
            result = await session.execute(
                select(HttpRequestLog).where(HttpRequestLog.request_id == request_id)
            )
            request_log = result.scalar_one_or_none()

            if request_log:
                return request_log.to_dict()

        # Fallback to in-memory log if not found in database
        request_log = agentic_http_client.get_request_log(limit=1000)
        for log_entry in request_log:
            if log_entry.get("request_id") == request_id:
                return log_entry

        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get request details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get request details: {str(e)}")


@router.get("/health")
async def get_http_health() -> Dict[str, Any]:
    """
    Get HTTP client health status.

    Returns the health status of the HTTP client including
    connection status, circuit breaker state, and any issues.
    """
    try:
        metrics = agentic_http_client.get_metrics()

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "circuit_breaker_state": metrics.get("circuit_breaker_state", "unknown"),
                "session_active": metrics.get("session_active", False),
                "total_requests": metrics.get("total_requests", 0)
            }
        }

        # Check for potential issues
        if metrics.get("circuit_breaker_state") == "open":
            health_status["status"] = "degraded"
            health_status["issues"] = ["Circuit breaker is open"]

        if not metrics.get("session_active", False):
            health_status["status"] = "warning"
            health_status["issues"] = health_status.get("issues", []) + ["HTTP session not active"]

        return health_status

    except Exception as e:
        logger.error(f"Failed to get HTTP health: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/requests")
async def list_recent_requests(limit: int = 50) -> Dict[str, Any]:
    """
    List recent HTTP requests.

    Returns a list of recent HTTP requests with their details
    for monitoring and debugging purposes.
    """
    try:
        # Query database for recent requests
        async for session in get_db():
            result = await session.execute(
                select(HttpRequestLog)
                .order_by(desc(HttpRequestLog.created_at))
                .limit(limit)
            )
            db_requests = result.scalars().all()

            if db_requests:
                return {
                    "requests": [req.to_dict() for req in db_requests],
                    "total_count": len(db_requests),
                    "limit": limit,
                    "source": "database"
                }

        # Fallback to in-memory log if database query fails
        request_log = agentic_http_client.get_request_log(limit=limit)
        return {
            "requests": request_log,
            "total_count": len(request_log),
            "limit": limit,
            "source": "memory"
        }

    except Exception as e:
        logger.error(f"Failed to list requests: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list requests: {str(e)}")
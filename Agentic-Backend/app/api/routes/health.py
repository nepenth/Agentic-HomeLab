from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.config import settings
from app.utils.metrics import registry
from app.api.dependencies import verify_api_key
import asyncio

router = APIRouter()


@router.get("/health", summary="Health Check")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "timestamp": "2024-01-01T00:00:00Z"  # Will be dynamically set
    }


@router.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(verify_api_key)])
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(registry)


@router.get("/ready", summary="Readiness Check")
async def readiness_check():
    """Readiness check for Kubernetes."""
    # Add checks for database, redis, etc.
    try:
        # Simple async check
        await asyncio.sleep(0.001)
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}, 503
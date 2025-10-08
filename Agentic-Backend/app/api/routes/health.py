from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.config import settings
from app.utils.metrics import registry
from app.api.dependencies import verify_api_key
from app.db.database import get_session_context
from sqlalchemy import text
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


@router.get("/db-connections", summary="Database Connection Monitor")
async def database_connections():
    """Monitor database connections to detect leaks and issues."""
    try:
        async with get_session_context() as db:
            # Query current connection stats
            query = text("""
                SELECT
                    application_name,
                    state,
                    count(*) as connection_count,
                    min(backend_start) as earliest_connection,
                    max(backend_start) as latest_connection
                FROM pg_stat_activity
                WHERE application_name LIKE 'Agentic Backend%'
                GROUP BY application_name, state
                ORDER BY connection_count DESC
            """)
            result = await db.execute(query)
            connections = result.fetchall()

            # Get total connection limit
            max_conn_query = text("SHOW max_connections")
            max_conn_result = await db.execute(max_conn_query)
            max_connections = int(max_conn_result.scalar())

            # Calculate totals
            total_connections = sum(row[2] for row in connections)
            idle_in_transaction = sum(row[2] for row in connections if row[1] == 'idle in transaction')

            return {
                "status": "healthy" if idle_in_transaction == 0 else "warning",
                "max_connections": max_connections,
                "total_app_connections": total_connections,
                "idle_in_transaction_count": idle_in_transaction,
                "connection_breakdown": [
                    {
                        "application_name": row[0],
                        "state": row[1],
                        "count": row[2],
                        "earliest": row[3].isoformat() if row[3] else None,
                        "latest": row[4].isoformat() if row[4] else None
                    }
                    for row in connections
                ],
                "warnings": ["Found idle in transaction connections - potential leak"] if idle_in_transaction > 0 else []
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500
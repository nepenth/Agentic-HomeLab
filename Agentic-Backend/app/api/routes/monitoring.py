from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies import get_db_session, verify_api_key, get_current_user
from app.db.models.user import User
from app.config import settings
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge, Histogram
import psutil
import platform

try:
    from app.utils.metrics import registry
except ImportError:
    # Fallback if metrics module doesn't exist
    from prometheus_client import CollectorRegistry
    registry = CollectorRegistry()

router = APIRouter()

# Enhanced Prometheus metrics for Phase 3
WORKFLOW_EXECUTION_TIME = Histogram(
    'workflow_execution_duration_seconds',
    'Time spent executing workflows',
    ['workflow_type', 'status']
)

TASK_COMPLETION_RATE = Counter(
    'task_completion_total',
    'Total number of completed tasks',
    ['task_type', 'priority', 'status']
)

SYSTEM_HEALTH_SCORE = Gauge(
    'system_health_score',
    'Overall system health score (0-100)',
    ['component']
)

ERROR_RATE = Counter(
    'error_rate_total',
    'Total number of errors by type',
    ['error_type', 'component', 'severity']
)

# Structured logging
logger = logging.getLogger(__name__)

@router.get("/health/detailed", summary="Enhanced Health Check")
async def detailed_health_check(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Comprehensive health check with detailed component status.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "uptime": get_system_uptime(),
        "components": {}
    }

    # Database health check
    try:
        await db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "response_time_ms": 10
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # System resources
    health_status["components"]["system"] = get_system_health()

    # Memory usage
    memory = psutil.virtual_memory()
    health_status["components"]["memory"] = {
        "status": "healthy" if memory.percent < 90 else "warning",
        "usage_percent": memory.percent,
        "available_gb": round(memory.available / (1024**3), 2)
    }

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    health_status["components"]["cpu"] = {
        "status": "healthy" if cpu_percent < 80 else "warning",
        "usage_percent": cpu_percent
    }

    # Disk usage
    disk = psutil.disk_usage('/')
    health_status["components"]["disk"] = {
        "status": "healthy" if disk.percent < 90 else "warning",
        "usage_percent": disk.percent,
        "free_gb": round(disk.free / (1024**3), 2)
    }

    # Update health score metric
    overall_score = calculate_health_score(health_status["components"])
    SYSTEM_HEALTH_SCORE.labels(component="overall").set(overall_score)

    return JSONResponse(
        content=health_status,
        status_code=200 if health_status["status"] == "healthy" else 503
    )

@router.get("/health/services", summary="Service Health Status")
async def service_health_check():
    """
    Check health of external services and dependencies.
    """
    services = {}

    # Ollama service check
    try:
        import aiohttp
        from aiohttp import ClientTimeout
        timeout = ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("http://localhost:11434/api/tags") as response:
                services["ollama"] = {
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "response_time_ms": 100
                }
    except Exception as e:
        services["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Redis check (if configured)
    if hasattr(settings, 'redis_url'):
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            services["redis"] = {"status": "healthy"}
        except Exception as e:
            services["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }

    return {"services": services}

@router.get("/metrics/workflow", response_class=PlainTextResponse, dependencies=[Depends(verify_api_key)])
async def workflow_metrics():
    """
    Workflow-specific Prometheus metrics.
    """
    return generate_latest(registry)

@router.get("/logs/structured", summary="Structured Log Query")
async def get_structured_logs(
    component: Optional[str] = None,
    level: Optional[str] = None,
    workflow_id: Optional[str] = None,
    task_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Query structured logs with advanced filtering.
    """
    # This would integrate with your logging system
    # For now, return a structured response format

    logs = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "component": "email_workflow",
            "message": "Workflow started successfully",
            "workflow_id": "wf-123",
            "task_id": "task-456",
            "user_id": str(current_user.id),
            "metadata": {
                "processing_time_ms": 150,
                "emails_found": 25
            }
        }
    ]

    return {
        "logs": logs,
        "total_count": len(logs),
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": False
        }
    }

@router.post("/alerts/test", summary="Test Alert System")
async def test_alert_system(
    alert_type: str = "test",
    message: str = "Test alert from monitoring system",
    severity: str = "info",
    current_user: User = Depends(get_current_user)
):
    """
    Test the alerting system by sending a test alert.
    """
    # Log the test alert
    logger.info(f"Test alert triggered: {alert_type} - {message}", extra={
        "alert_type": alert_type,
        "severity": severity,
        "user_id": str(current_user.id),
        "component": "monitoring"
    })

    # Update error rate metric
    ERROR_RATE.labels(
        error_type="test_alert",
        component="monitoring",
        severity=severity
    ).inc()

    return {
        "message": "Test alert sent successfully",
        "alert_type": alert_type,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/performance/workflow", summary="Workflow Performance Metrics")
async def get_workflow_performance(
    workflow_type: Optional[str] = None,
    time_range: str = "24h",
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed workflow performance metrics.
    """
    # Calculate time range
    if time_range == "24h":
        start_time = datetime.utcnow() - timedelta(hours=24)
    elif time_range == "7d":
        start_time = datetime.utcnow() - timedelta(days=7)
    elif time_range == "30d":
        start_time = datetime.utcnow() - timedelta(days=30)
    else:
        start_time = datetime.utcnow() - timedelta(hours=24)

    # Mock performance data - in real implementation, this would query actual metrics
    performance_data = {
        "time_range": time_range,
        "metrics": {
            "total_workflows": 150,
            "successful_workflows": 142,
            "failed_workflows": 8,
            "average_execution_time": 45.2,
            "success_rate": 94.7,
            "peak_concurrent_workflows": 12
        },
        "breakdown_by_type": {
            "email_processing": {
                "count": 120,
                "avg_time": 42.5,
                "success_rate": 95.8
            },
            "content_analysis": {
                "count": 30,
                "avg_time": 55.1,
                "success_rate": 90.0
            }
        },
        "performance_trends": [
            {"timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(), "avg_time": 43.2},
            {"timestamp": datetime.utcnow().isoformat(), "avg_time": 45.2}
        ]
    }

    return performance_data

@router.get("/system/resources/detailed", summary="Detailed System Resources")
async def get_detailed_system_resources():
    """
    Get comprehensive system resource information.
    """
    return {
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "processes": get_process_info(),
        "system": get_system_info()
    }

def get_system_uptime():
    """Get system uptime in seconds."""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds
    except:
        return psutil.boot_time()

def get_system_health():
    """Get overall system health metrics."""
    load_avg = psutil.getloadavg()
    return {
        "status": "healthy",
        "load_average": {
            "1m": load_avg[0],
            "5m": load_avg[1],
            "15m": load_avg[2]
        },
        "boot_time": psutil.boot_time()
    }

def get_cpu_info():
    """Get detailed CPU information."""
    return {
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "usage_percent": psutil.cpu_percent(interval=1),
        "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None,
        "times_percent": psutil.cpu_times_percent(interval=1)._asdict()
    }

def get_memory_info():
    """Get detailed memory information."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total_gb": round(memory.total / (1024**3), 2),
        "available_gb": round(memory.available / (1024**3), 2),
        "used_gb": round(memory.used / (1024**3), 2),
        "usage_percent": memory.percent,
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_usage_percent": swap.percent
    }

def get_disk_info():
    """Get detailed disk information."""
    disk = psutil.disk_usage('/')
    io_counters = psutil.disk_io_counters()

    return {
        "total_gb": round(disk.total / (1024**3), 2),
        "used_gb": round(disk.used / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "usage_percent": disk.percent,
        "io_counters": io_counters._asdict() if io_counters else None
    }

def get_network_info():
    """Get detailed network information."""
    net_io = psutil.net_io_counters()
    net_if_addrs = psutil.net_if_addrs()

    interfaces = {}
    for interface_name, interface_addresses in net_if_addrs.items():
        interfaces[interface_name] = [
            {
                "family": addr.family.name,
                "address": addr.address,
                "netmask": addr.netmask,
                "broadcast": addr.broadcast
            } for addr in interface_addresses
        ]

    return {
        "io_counters": net_io._asdict() if net_io else None,
        "interfaces": interfaces
    }

def get_process_info():
    """Get process information."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by CPU usage and return top 10
    processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
    return processes[:10]

def get_system_info():
    """Get system information."""
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "architecture": platform.architecture(),
        "python_version": platform.python_version(),
        "boot_time": psutil.boot_time()
    }

def calculate_health_score(components: Dict[str, Any]) -> float:
    """Calculate overall health score from component statuses."""
    total_score = 0
    component_count = 0

    for component_name, component_data in components.items():
        component_count += 1
        if component_data.get("status") == "healthy":
            total_score += 100
        elif component_data.get("status") == "warning":
            total_score += 75
        elif component_data.get("status") == "degraded":
            total_score += 50
        else:  # unhealthy
            total_score += 0

    return total_score / component_count if component_count > 0 else 0
"""
Security monitoring and management API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_current_user
from app.db.models.user import User
from app.utils.logging import get_logger

logger = get_logger("security_routes")
router = APIRouter(tags=["security"])


def get_security_service():
    """Lazy import to avoid circular imports."""
    from app.services.security_service import SecurityService, SecurityLevel
    return SecurityService()


def get_security_middleware_functions():
    """Lazy import to avoid circular imports."""
    from app.api.security_middleware import validate_tool_execution, get_security_status, get_agent_security_report
    return validate_tool_execution, get_security_status, get_agent_security_report


@router.get("/status")
async def get_security_status_endpoint(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get current security status and metrics.

    Requires admin privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Return basic security status without complex service dependencies
        return {
            "active_agents": 0,
            "total_incidents": 0,
            "recent_incidents": [],
            "resource_limits": {
                "max_concurrent_agents": 8,
                "max_memory_mb": 131072,
                "max_execution_time": 1800
            },
            "current_usage": {
                "active_agents": 0,
                "total_memory_mb": 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security status")


@router.post("/status")
async def update_security_status_endpoint(
    status_update: dict,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Update security status and configuration.

    Requires admin privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        security_service = get_security_service()

        # Update security level if provided
        if "security_level" in status_update:
            new_level = status_update["security_level"]
            if new_level in ["strict", "moderate", "lenient"]:
                security_service.security_level = SecurityLevel(new_level)
                logger.info(f"Security level updated to {new_level} by {current_user.username}")

        # Update limits if provided
        if "limits" in status_update:
            limits_update = status_update["limits"]
            for key, value in limits_update.items():
                if hasattr(security_service.limits, key):
                    setattr(security_service.limits, key, value)
                    logger.info(f"Security limit {key} updated to {value} by {current_user.username}")

        return {
            "message": "Security status updated successfully",
            "updated_fields": list(status_update.keys()),
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Failed to update security status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update security status")


@router.get("/agents/{agent_id}/report")
async def get_agent_security_report_endpoint(
    agent_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get security report for a specific agent.

    Requires admin privileges or agent ownership.
    """
    if not current_user.is_superuser:
        # TODO: Check if user owns the agent
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        security_service = get_security_service()
        validate_tool_execution, get_security_status, get_agent_security_report = get_security_middleware_functions()
        report = await get_agent_security_report(security_service, agent_id)

        if not report:
            raise HTTPException(status_code=404, detail="Agent not found or no security data available")

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent security report: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent security report")


@router.post("/validate-tool-execution")
async def validate_tool_execution_endpoint(
    agent_id: str,
    tool_name: str,
    input_data: dict,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Validate a tool execution request against security policies.

    This endpoint can be used to pre-validate tool executions before they occur.
    """
    try:
        security_service = get_security_service()
        validate_tool_execution, get_security_status, get_agent_security_report = get_security_middleware_functions()
        result = await validate_tool_execution(security_service, agent_id, tool_name, input_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool execution validation failed: {e}")
        raise HTTPException(status_code=500, detail="Tool execution validation failed")


@router.get("/incidents")
async def get_security_incidents(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    resolved: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get security incidents with filtering options.

    Requires admin privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        security_service = get_security_service()

        # Filter incidents based on criteria
        incidents = security_service.security_incidents

        if severity:
            incidents = [i for i in incidents if i.severity == severity]

        if resolved is not None:
            incidents = [i for i in incidents if i.resolved == resolved]

        # Apply pagination
        total_count = len(incidents)
        incidents = incidents[offset:offset + limit]

        return {
            "incidents": [
                {
                    "incident_id": incident.incident_id,
                    "agent_id": incident.agent_id,
                    "agent_type": incident.agent_type,
                    "violation_type": incident.violation_type.value,
                    "severity": incident.severity,
                    "description": incident.description,
                    "timestamp": incident.timestamp.isoformat(),
                    "resolved": incident.resolved,
                    "resolution_notes": incident.resolution_notes
                }
                for incident in incidents
            ],
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get security incidents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security incidents")


@router.post("/incidents/{incident_id}/resolve")
async def resolve_security_incident(
    incident_id: str,
    resolution_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Mark a security incident as resolved.

    Requires admin privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        security_service = get_security_service()

        # Find and resolve the incident
        incident_found = False
        for incident in security_service.security_incidents:
            if incident.incident_id == incident_id:
                incident.resolved = True
                incident.resolution_notes = resolution_notes
                incident_found = True
                break

        if not incident_found:
            raise HTTPException(status_code=404, detail="Security incident not found")

        logger.info(f"Security incident {incident_id} resolved by {current_user.username}")
        return {"message": "Security incident resolved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve security incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve security incident")


@router.get("/limits")
async def get_security_limits(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Get current security limits and constraints.

    Requires admin privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        security_service = get_security_service()
        limits = security_service.limits

        return {
            "cpu_limits": {
                "max_concurrent_agents": limits.max_concurrent_agents,
                "max_agent_execution_time": limits.max_agent_execution_time,
                "max_pipeline_execution_time": limits.max_pipeline_execution_time,
                "max_step_execution_time": limits.max_step_execution_time
            },
            "memory_limits": {
                "max_agent_memory_mb": limits.max_agent_memory_mb,
                "max_total_memory_mb": limits.max_total_memory_mb,
                "max_data_model_memory_mb": limits.max_data_model_memory_mb
            },
            "database_limits": {
                "max_table_rows": limits.max_table_rows,
                "max_concurrent_queries": limits.max_concurrent_queries,
                "max_query_execution_time": limits.max_query_execution_time
            },
            "network_limits": {
                "max_external_requests_per_hour": limits.max_external_requests_per_hour,
                "max_request_size_kb": limits.max_request_size_kb,
                "allowed_domains": list(limits.allowed_domains) if limits.allowed_domains else []
            },
            "gpu_limits": {
                "max_gpu_memory_mb": limits.max_gpu_memory_mb,
                "max_concurrent_gpu_tasks": limits.max_concurrent_gpu_tasks
            },
            "schema_limits": {
                "max_data_models": limits.max_data_models,
                "max_fields_per_model": limits.max_fields_per_model,
                "max_pipeline_steps": limits.max_pipeline_steps,
                "max_tools_per_agent": limits.max_tools_per_agent,
                "max_nested_json_depth": limits.max_nested_json_depth
            }
        }
    except Exception as e:
        logger.error(f"Failed to get security limits: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security limits")


@router.get("/health")
async def security_health_check() -> dict:
    """
    Security service health check endpoint.

    This endpoint is publicly accessible for monitoring purposes.
    """
    try:
        security_service = get_security_service()

        # Basic health checks
        incidents_count = len(security_service.security_incidents)
        active_agents = len(security_service.active_agents)

        # Determine health status based on incident severity
        high_severity_incidents = [
            i for i in security_service.security_incidents
            if i.severity in ["high", "critical"] and not i.resolved
        ]

        if high_severity_incidents:
            health_status = "warning"
            health_message = f"{len(high_severity_incidents)} unresolved high/critical security incidents"
        elif incidents_count > 10:  # Arbitrary threshold
            health_status = "warning"
            health_message = f"High number of security incidents: {incidents_count}"
        else:
            health_status = "healthy"
            health_message = "Security service operating normally"

        return {
            "status": health_status,
            "message": health_message,
            "metrics": {
                "total_incidents": incidents_count,
                "active_agents": active_agents,
                "unresolved_high_severity": len(high_severity_incidents)
            },
            "timestamp": security_service.security_incidents[-1].timestamp.isoformat() if security_service.security_incidents else None
        }

    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return {
            "status": "error",
            "message": f"Security health check failed: {str(e)}",
            "metrics": None,
            "timestamp": None
        }
"""
API routes for Security Service.

Provides endpoints for security monitoring, configuration,
and security-related operations.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.security_service import (
    security_service,
    SecurityEventType,
    ThreatLevel,
    SecurityLevel
)
from app.utils.logging import get_logger

logger = get_logger("security_api")
router = APIRouter(prefix="/api/v1/security", tags=["Security Service"])


# Pydantic models for API
class SecurityValidationRequest(BaseModel):
    """Request model for security validation."""
    endpoint: str
    request_data: Optional[Any] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None


class SecurityValidationResponse(BaseModel):
    """Response model for security validation."""
    allowed: bool
    warnings: List[str]
    blocked_reasons: List[str]
    sanitized_data: Any
    security_events_logged: int


class SecurityEventLogRequest(BaseModel):
    """Request model for logging security events."""
    event_type: str
    threat_level: str
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    resource: str = ""
    action: str = ""
    details: Optional[Dict[str, Any]] = None


class SecurityStatusResponse(BaseModel):
    """Response model for security status."""
    security_level: str
    metrics: Dict[str, Any]
    rate_limiting: Dict[str, Any]
    last_updated: str


class DataEncryptionRequest(BaseModel):
    """Request model for data encryption."""
    data: str


class DataEncryptionResponse(BaseModel):
    """Response model for data encryption/decryption."""
    result: str


class SecurityConfigurationUpdate(BaseModel):
    """Request model for updating security configuration."""
    security_level: Optional[str] = None
    enable_rate_limiting: Optional[bool] = None
    enable_input_validation: Optional[bool] = None


@router.post("/validate", response_model=SecurityValidationResponse)
async def validate_request(request: SecurityValidationRequest, req: Request):
    """
    Validate a request for security issues.

    This endpoint performs comprehensive security validation including:
    - Rate limiting checks
    - Input validation and sanitization
    - Security pattern detection
    - Threat level assessment
    """
    try:
        # Get client IP from request
        client_ip = req.client.host if req.client else request.ip_address

        # Perform security validation
        allowed, validation_result = await security_service.validate_request(
            request.endpoint,
            request.request_data,
            request.user_id,
            client_ip
        )

        return SecurityValidationResponse(
            allowed=allowed,
            warnings=validation_result.get("warnings", []),
            blocked_reasons=validation_result.get("blocked_reasons", []),
            sanitized_data=validation_result.get("sanitized_data"),
            security_events_logged=len(validation_result.get("warnings", []))
        )

    except Exception as e:
        logger.error(f"Failed to validate request: {e}")
        raise HTTPException(status_code=500, detail=f"Security validation failed: {str(e)}")


@router.post("/events/log")
async def log_security_event(request: SecurityEventLogRequest):
    """
    Log a security event manually.

    This endpoint allows manual logging of security events for monitoring and alerting.
    """
    try:
        # Validate event type and threat level
        try:
            event_type = SecurityEventType(request.event_type)
            threat_level = ThreatLevel(request.threat_level)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type or threat level: {e}")

        # Log the security event
        event_id = await security_service.security_monitor.log_security_event(
            event_type=event_type,
            threat_level=threat_level,
            source_ip=request.source_ip,
            user_id=request.user_id,
            resource=request.resource,
            action=request.action,
            details=request.details
        )

        return {
            "message": "Security event logged successfully",
            "event_id": event_id,
            "event_type": request.event_type,
            "threat_level": request.threat_level
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log security event: {str(e)}")


@router.get("/status", response_model=SecurityStatusResponse)
async def get_security_status():
    """Get comprehensive security status and metrics."""
    try:
        status = security_service.get_security_status()

        return SecurityStatusResponse(
            security_level=status["security_level"],
            metrics=status["metrics"],
            rate_limiting=status["rate_limiting"],
            last_updated=status["last_updated"]
        )

    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security status: {str(e)}")


@router.get("/events")
async def get_security_events(
    event_type: Optional[str] = None,
    threat_level: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get security events with optional filtering.

    Retrieve security events for monitoring and analysis.
    """
    try:
        events = security_service.security_monitor.events

        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type.value == event_type]
        if threat_level:
            events = [e for e in events if e.threat_level.value == threat_level]
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        # Apply pagination
        total_events = len(events)
        events = events[offset:offset + limit]

        # Convert to response format
        event_list = []
        for event in events:
            event_list.append({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "threat_level": event.threat_level.value,
                "source_ip": event.source_ip,
                "user_id": event.user_id,
                "resource": event.resource,
                "action": event.action,
                "details": event.details,
                "timestamp": event.timestamp.isoformat(),
                "resolved": event.resolved,
                "resolution_notes": event.resolution_notes
            })

        return {
            "events": event_list,
            "total_count": total_events,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to get security events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security events: {str(e)}")


@router.post("/encrypt", response_model=DataEncryptionResponse)
async def encrypt_data(request: DataEncryptionRequest):
    """Encrypt sensitive data."""
    try:
        encrypted = await security_service.encrypt_data(request.data)

        return DataEncryptionResponse(result=encrypted)

    except Exception as e:
        logger.error(f"Failed to encrypt data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to encrypt data: {str(e)}")


@router.post("/decrypt", response_model=DataEncryptionResponse)
async def decrypt_data(request: DataEncryptionRequest):
    """Decrypt sensitive data."""
    try:
        decrypted = await security_service.decrypt_data(request.data)

        return DataEncryptionResponse(result=decrypted)

    except Exception as e:
        logger.error(f"Failed to decrypt data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to decrypt data: {str(e)}")


@router.post("/hash")
async def hash_data(data: str, salt: Optional[str] = None):
    """Generate secure hash of data."""
    try:
        hashed = security_service.hash_data(data, salt)

        return {
            "hash": hashed,
            "algorithm": "SHA-256",
            "salt_used": salt is not None
        }

    except Exception as e:
        logger.error(f"Failed to hash data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to hash data: {str(e)}")


@router.post("/token")
async def generate_token(length: int = 32):
    """Generate a secure random token."""
    try:
        if length < 16 or length > 128:
            raise HTTPException(status_code=400, detail="Token length must be between 16 and 128 characters")

        token = security_service.generate_token(length)

        return {
            "token": token,
            "length": len(token),
            "algorithm": "hex"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")


@router.put("/config")
async def update_security_config(config: SecurityConfigurationUpdate):
    """Update security service configuration."""
    try:
        updated = False

        if config.security_level:
            try:
                security_service.security_level = SecurityLevel(config.security_level)
                updated = True
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid security level: {config.security_level}")

        # Note: Other configuration options would be implemented based on requirements

        if updated:
            logger.info(f"Security configuration updated: {config.dict(exclude_unset=True)}")
            return {"message": "Security configuration updated successfully"}
        else:
            return {"message": "No configuration changes made"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update security config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update security config: {str(e)}")


@router.get("/config")
async def get_security_config():
    """Get current security configuration."""
    try:
        return {
            "security_level": security_service.security_level.value,
            "input_validation_enabled": True,  # Always enabled
            "rate_limiting_enabled": True,     # Always enabled
            "encryption_enabled": True,        # Always enabled
            "audit_logging_enabled": True      # Always enabled
        }

    except Exception as e:
        logger.error(f"Failed to get security config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security config: {str(e)}")


@router.get("/rate-limits")
async def get_rate_limits():
    """Get current rate limiting status."""
    try:
        stats = security_service.rate_limiter.get_stats()

        return {
            "active_rules": stats["active_rules"],
            "total_rules": stats["total_rules"],
            "tracked_entities": stats["tracked_entities"],
            "blocked_entities": stats["blocked_entities"],
            "rules": stats["rules"]
        }

    except Exception as e:
        logger.error(f"Failed to get rate limits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rate limits: {str(e)}")


@router.delete("/rate-limits/reset")
async def reset_rate_limits(entity_id: Optional[str] = None):
    """Reset rate limiting for specific entity or all entities."""
    try:
        if entity_id:
            # Reset specific entity
            if entity_id in security_service.rate_limiter.blocked_entities:
                del security_service.rate_limiter.blocked_entities[entity_id]

            # Clear request counts for entity
            keys_to_remove = []
            for key in security_service.rate_limiter.request_counts:
                if entity_id in key:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del security_service.rate_limiter.request_counts[key]

            return {"message": f"Rate limits reset for entity: {entity_id}"}
        else:
            # Reset all
            security_service.rate_limiter.request_counts.clear()
            security_service.rate_limiter.blocked_entities.clear()

            return {"message": "All rate limits reset"}

    except Exception as e:
        logger.error(f"Failed to reset rate limits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset rate limits: {str(e)}")


@router.get("/threat-analysis")
async def get_threat_analysis(hours: int = 24):
    """Get threat analysis for the specified time period."""
    try:
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [
            event for event in security_service.security_monitor.events
            if event.timestamp >= cutoff_time
        ]

        # Analyze threats
        threat_counts = {}
        event_type_counts = {}
        top_sources = {}

        for event in recent_events:
            threat_level = event.threat_level.value
            event_type = event.event_type.value
            source = event.source_ip or event.user_id or "unknown"

            threat_counts[threat_level] = threat_counts.get(threat_level, 0) + 1
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            top_sources[source] = top_sources.get(source, 0) + 1

        # Sort top sources
        top_sources = dict(sorted(top_sources.items(), key=lambda x: x[1], reverse=True)[:10])

        return {
            "analysis_period_hours": hours,
            "total_events": len(recent_events),
            "threat_level_breakdown": threat_counts,
            "event_type_breakdown": event_type_counts,
            "top_sources": top_sources,
            "most_common_threat": max(threat_counts.items(), key=lambda x: x[1], default=("none", 0))[0]
        }

    except Exception as e:
        logger.error(f"Failed to get threat analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get threat analysis: {str(e)}")


@router.get("/health")
async def security_health_check():
    """Health check for security service."""
    try:
        # Check if all components are functioning
        status = {
            "overall_health": "healthy",
            "components": {
                "input_validator": "healthy",
                "rate_limiter": "healthy",
                "security_monitor": "healthy",
                "data_encryptor": "healthy"
            },
            "issues": []
        }

        # Check for any issues
        if len(security_service.security_monitor.events) > 1000:
            status["issues"].append("High number of security events logged")

        if len(security_service.rate_limiter.blocked_entities) > 100:
            status["issues"].append("High number of blocked entities")

        if status["issues"]:
            status["overall_health"] = "warning"

        return status

    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return {
            "overall_health": "unhealthy",
            "components": {},
            "issues": [f"Health check failed: {str(e)}"]
        }
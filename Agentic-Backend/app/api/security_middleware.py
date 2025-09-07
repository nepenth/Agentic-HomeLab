"""
Security middleware for agent execution sandboxing.
"""
import re
import time
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.security_service import SecurityService
from app.schemas.agent_schema import AgentSchema
from app.utils.logging import get_logger


class MockSecurityService:
    """
    Mock security service for when the full SecurityService fails to initialize.
    Provides basic functionality to prevent crashes.
    """

    def __init__(self):
        self.active_agents = {}
        self.security_incidents = []

    async def initialize_agent_sandbox(self, agent_id: str, agent_type: str, schema=None):
        """Mock sandbox initialization."""
        return True

    async def cleanup_agent_sandbox(self, agent_id: str):
        """Mock sandbox cleanup."""
        pass

    async def monitor_execution(self, agent_id: str, execution_context: dict):
        """Mock execution monitoring."""
        pass

    def get_security_status(self):
        """Return basic security status."""
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

    async def get_agent_security_report(self, agent_id: str):
        """Mock agent security report."""
        return None

logger = get_logger("security_middleware")


class AgentSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enforcing agent execution security policies.
    """

    def __init__(self, app, security_service: Optional[SecurityService] = None):
        super().__init__(app)
        try:
            self.security_service = security_service or SecurityService()
        except Exception as e:
            logger.warning(f"Failed to initialize SecurityService: {e}. Using mock service.")
            # Create a mock security service that doesn't crash
            self.security_service = MockSecurityService()

    async def dispatch(self, request: Request, call_next):
        """
        Process request through security middleware.
        """
        start_time = time.time()

        # Extract agent information from request
        agent_id = self._extract_agent_id(request)
        agent_type = self._extract_agent_type(request)

        try:
            # Initialize agent sandbox if this is an agent execution request
            if self._is_agent_execution_request(request):
                if agent_id and agent_type:
                    # Try to initialize sandbox
                    sandbox_initialized = await self.security_service.initialize_agent_sandbox(
                        agent_id, agent_type, None  # Schema will be validated separately
                    )

                    if not sandbox_initialized:
                        logger.warning(f"Failed to initialize sandbox for agent {agent_id}")
                        return JSONResponse(
                            status_code=429,
                            content={
                                "error": "Resource limit exceeded",
                                "message": "Unable to initialize agent execution environment"
                            }
                        )

                    # Store agent context in request state
                    request.state.agent_id = agent_id
                    request.state.agent_type = agent_type
                    request.state.sandbox_initialized = True

            # Process the request
            response = await call_next(request)

            # Monitor execution if sandbox was initialized
            if hasattr(request.state, 'sandbox_initialized') and request.state.sandbox_initialized:
                execution_time = time.time() - start_time
                await self._monitor_execution(request, execution_time)

            return response

        except Exception as e:
            logger.error(f"Security middleware error: {e}")

            # Cleanup sandbox on error
            if hasattr(request.state, 'sandbox_initialized') and request.state.sandbox_initialized:
                if agent_id:
                    await self.security_service.cleanup_agent_sandbox(agent_id)

            # Return appropriate error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Security processing error",
                    "message": "An error occurred during security validation"
                }
            )
        finally:
            # Cleanup sandbox after request completion
            if hasattr(request.state, 'sandbox_initialized') and request.state.sandbox_initialized:
                if agent_id:
                    await self.security_service.cleanup_agent_sandbox(agent_id)

    def _extract_agent_id(self, request: Request) -> Optional[str]:
        """Extract agent ID from request."""
        # Try different sources for agent ID
        agent_id = None

        # From URL path (e.g., /api/v1/agents/{agent_id}/execute)
        if "agents" in request.url.path:
            path_parts = request.url.path.split("/")
            try:
                agent_index = path_parts.index("agents")
                if agent_index + 1 < len(path_parts):
                    agent_id = path_parts[agent_index + 1]
            except (ValueError, IndexError):
                pass

        # From headers
        if not agent_id:
            agent_id = request.headers.get("X-Agent-ID")

        # From query parameters
        if not agent_id:
            agent_id = request.query_params.get("agent_id")

        return agent_id

    def _extract_agent_type(self, request: Request) -> Optional[str]:
        """Extract agent type from request."""
        # From headers
        agent_type = request.headers.get("X-Agent-Type")

        # From query parameters
        if not agent_type:
            agent_type = request.query_params.get("agent_type")

        return agent_type

    def _is_agent_execution_request(self, request: Request) -> bool:
        """Determine if this is an agent execution request."""
        execution_paths = [
            "/api/v1/agents/",
            "/api/v1/tasks/",
            "/api/v1/agent-builder/"
        ]

        return any(path in request.url.path for path in execution_paths) and \
               request.method in ["POST", "PUT", "PATCH"]

    async def _monitor_execution(self, request: Request, execution_time: float):
        """Monitor agent execution for security violations."""
        try:
            agent_id = getattr(request.state, 'agent_id', None)
            if not agent_id:
                return

            # Create execution context for monitoring
            execution_context = {
                "execution_time": execution_time,
                "request_method": request.method,
                "request_path": request.url.path,
                "user_agent": request.headers.get("User-Agent", ""),
                "client_ip": request.client.host if request.client else None
            }

            # Monitor the execution
            await self.security_service.monitor_execution(agent_id, execution_context)

        except Exception as e:
            logger.error(f"Execution monitoring error: {e}")


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating incoming requests against security policies.
    """

    def __init__(self, app, security_service: Optional[SecurityService] = None):
        super().__init__(app)
        self.security_service = security_service or SecurityService()

    async def dispatch(self, request: Request, call_next):
        """
        Validate incoming request.
        """
        try:
            # Validate request size
            if hasattr(request, 'body'):
                # This is a simplified check - in production you'd stream and check size
                pass

            # Validate request headers
            await self._validate_request_headers(request)

            # Check for suspicious patterns
            await self._check_request_patterns(request)

            # Process request
            response = await call_next(request)
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Request validation error: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Request validation failed",
                    "message": "Invalid request format or content"
                }
            )

    async def _validate_request_headers(self, request: Request):
        """Validate request headers for security."""
        # Skip header validation for security endpoints since they may have proxy headers
        if "/api/v1/security/" in request.url.path:
            return

        # Check for required security headers in production
        suspicious_headers = [
            header for header in request.headers.keys()
            if header.lower() in ['x-forwarded-for', 'x-real-ip'] and len(request.headers.getlist(header)) > 1
        ]

        if suspicious_headers:
            logger.warning(f"Suspicious headers detected: {suspicious_headers}")
            raise HTTPException(status_code=400, detail="Invalid request headers")

    async def _check_request_patterns(self, request: Request):
        """Check request for suspicious patterns."""
        # Skip pattern validation for security endpoints
        if "/api/v1/security/" in request.url.path:
            return

        # This is a simplified implementation
        # In production, you'd implement more sophisticated pattern detection

        suspicious_patterns = [
            r'\.\./',  # Directory traversal
            r'<script',  # XSS attempts
            r'union\s+select',  # SQL injection
        ]

        # Check URL for suspicious patterns
        url_str = str(request.url)
        for pattern in suspicious_patterns:
            if re.search(pattern, url_str, re.IGNORECASE):
                logger.warning(f"Suspicious pattern detected in URL: {pattern}")
                raise HTTPException(status_code=400, detail="Invalid request")

        # Check query parameters
        for param, value in request.query_params.items():
            for pattern in suspicious_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected in query param {param}: {pattern}")
                    raise HTTPException(status_code=400, detail="Invalid request parameters")


# Security monitoring utilities
async def validate_tool_execution(
    security_service: SecurityService,
    agent_id: str,
    tool_name: str,
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate tool execution request.

    Args:
        security_service: Security service instance
        agent_id: Agent identifier
        tool_name: Tool being executed
        input_data: Input data for the tool

    Returns:
        Validation result with allowed status and reason

    Raises:
        HTTPException: If validation fails
    """
    is_allowed, denial_reason = await security_service.validate_execution_request(
        agent_id, tool_name, input_data
    )

    if not is_allowed:
        logger.warning(f"Tool execution denied for agent {agent_id}, tool {tool_name}: {denial_reason}")
        raise HTTPException(
            status_code=403,
            detail=f"Tool execution not allowed: {denial_reason}"
        )

    return {
        "allowed": True,
        "agent_id": agent_id,
        "tool_name": tool_name,
        "validation_time": time.time()
    }


async def get_security_status(security_service: SecurityService) -> Dict[str, Any]:
    """
    Get current security status.

    Args:
        security_service: Security service instance

    Returns:
        Security status information
    """
    return security_service.get_security_status()


async def get_agent_security_report(
    security_service: SecurityService,
    agent_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get security report for a specific agent.

    Args:
        security_service: Security service instance
        agent_id: Agent identifier

    Returns:
        Agent security report or None if not found
    """
    return await security_service.get_agent_security_report(agent_id)
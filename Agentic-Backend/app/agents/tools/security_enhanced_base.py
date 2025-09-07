"""
Security-enhanced tool base class with integrated security validation.
"""
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.agents.tools.base import Tool, ExecutionContext, ToolExecutionError, ToolValidationError
from app.services.security_service import SecurityService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityEnhancedTool(Tool):
    """
    Enhanced tool base class with integrated security validation and monitoring.
    """

    def __init__(self, config: Dict[str, Any], security_service: Optional[SecurityService] = None):
        super().__init__(config)
        self.security_service = security_service or SecurityService()
        self.execution_metrics = {
            "total_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "last_execution_time": None
        }

    async def execute(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute tool with security validation and monitoring.

        Args:
            input_data: Input data for the tool
            context: Execution context

        Returns:
            Tool execution results

        Raises:
            ToolExecutionError: If execution fails
            SecurityViolationError: If security validation fails
        """
        execution_start = time.time()
        agent_id = context.get_agent_id()
        tool_name = self.tool_type

        try:
            # Pre-execution security validation
            if agent_id:
                is_allowed, denial_reason = await self.security_service.validate_execution_request(
                    agent_id, tool_name, input_data
                )

                if not is_allowed:
                    raise SecurityViolationError(f"Tool execution denied: {denial_reason}")

            # Input validation
            validated_input = await self.validate_input(input_data)

            # Execute the tool
            logger.info(f"Executing secure tool '{tool_name}' for agent '{agent_id}'")
            result = await self._execute_secure(validated_input, context)

            # Update execution metrics
            execution_time = time.time() - execution_start
            self._update_execution_metrics(execution_time, success=True)

            # Post-execution security monitoring
            if agent_id:
                await self._monitor_execution(agent_id, tool_name, execution_time, success=True)

            logger.info(f"Tool '{tool_name}' executed successfully in {execution_time:.3f}s")
            return result

        except SecurityViolationError:
            raise
        except Exception as e:
            execution_time = time.time() - execution_start
            self._update_execution_metrics(execution_time, success=False)

            # Log security incident for failures
            if agent_id:
                await self._monitor_execution(agent_id, tool_name, execution_time, success=False, error=str(e))

            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            raise ToolExecutionError(f"Tool execution failed: {str(e)}", tool_name)

    async def _execute_secure(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute the actual tool logic with security context.

        Args:
            input_data: Validated input data
            context: Execution context

        Returns:
            Tool execution results
        """
        # This method should be overridden by subclasses
        raise NotImplementedError("Subclasses must implement _execute_secure method")

    async def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input data with security checks.

        Args:
            input_data: Input data to validate

        Returns:
            Validated input data

        Raises:
            ToolValidationError: If validation fails
        """
        # Basic security validation
        await self._validate_input_security(input_data)

        # Call parent validation
        return await super().validate_input(input_data)

    async def _validate_input_security(self, input_data: Dict[str, Any]) -> None:
        """
        Perform security validation on input data.

        Args:
            input_data: Input data to validate

        Raises:
            ToolValidationError: If security validation fails
        """
        # Check for malicious content
        malicious_content = self.security_service._scan_for_malicious_content(input_data)
        if malicious_content:
            raise ToolValidationError(
                f"Malicious content detected in input: {malicious_content}",
                self.tool_type,
                malicious_content
            )

        # Check input size limits
        input_size = len(str(input_data).encode('utf-8'))
        max_size = self.security_service.limits.max_request_size_kb * 1024

        if input_size > max_size:
            raise ToolValidationError(
                f"Input size {input_size} bytes exceeds limit of {max_size} bytes",
                self.tool_type
            )

    def _update_execution_metrics(self, execution_time: float, success: bool) -> None:
        """Update execution metrics."""
        self.execution_metrics["total_executions"] += 1
        self.execution_metrics["last_execution_time"] = datetime.utcnow()

        if not success:
            self.execution_metrics["failed_executions"] += 1

        # Update rolling average execution time
        current_avg = self.execution_metrics["average_execution_time"]
        total_executions = self.execution_metrics["total_executions"]

        self.execution_metrics["average_execution_time"] = (
            (current_avg * (total_executions - 1)) + execution_time
        ) / total_executions

    async def _monitor_execution(
        self,
        agent_id: str,
        tool_name: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Monitor tool execution for security purposes."""
        try:
            execution_context = {
                "tool_name": tool_name,
                "execution_time": execution_time,
                "success": success,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }

            await self.security_service.monitor_execution(agent_id, execution_context)

        except Exception as e:
            logger.error(f"Execution monitoring failed: {e}")

    def get_security_info(self) -> Dict[str, Any]:
        """Get security-related information about the tool."""
        return {
            "tool_type": self.tool_type,
            "execution_metrics": self.execution_metrics.copy(),
            "security_limits": {
                "max_input_size_kb": self.security_service.limits.max_request_size_kb,
                "max_execution_time": self.security_service.limits.max_step_execution_time
            },
            "last_execution": self.execution_metrics["last_execution_time"].isoformat() if self.execution_metrics["last_execution_time"] else None
        }


class SecurityViolationError(ToolExecutionError):
    """Raised when a security violation is detected."""

    def __init__(self, message: str, tool_type: str = "unknown", violation_details: Optional[Dict[str, Any]] = None):
        super().__init__(message, tool_type, violation_details)
        self.violation_details = violation_details or {}


class RateLimitedTool(SecurityEnhancedTool):
    """
    Tool with built-in rate limiting capabilities.
    """

    def __init__(self, config: Dict[str, Any], security_service: Optional[SecurityService] = None):
        super().__init__(config, security_service)
        self.rate_limit_config = config.get("rate_limit", {})
        self._request_times: List[float] = []

    async def _execute_secure(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute with rate limiting.
        """
        # Check rate limit before execution
        await self._check_rate_limit(context.get_agent_id())

        # Execute the actual tool logic
        return await super()._execute_secure(input_data, context)

    async def _check_rate_limit(self, agent_id: str) -> None:
        """
        Check if execution should be rate limited.

        Args:
            agent_id: Agent identifier

        Raises:
            SecurityViolationError: If rate limit exceeded
        """
        if not self.rate_limit_config:
            return

        current_time = time.time()
        window_seconds = self._parse_rate_limit_window(self.rate_limit_config.get("window", "1 minute"))
        max_requests = self.rate_limit_config.get("max_requests", 10)

        # Clean old requests
        cutoff_time = current_time - window_seconds
        self._request_times = [t for t in self._request_times if t > cutoff_time]

        # Check if limit exceeded
        if len(self._request_times) >= max_requests:
            raise SecurityViolationError(
                f"Rate limit exceeded: {max_requests} requests per {self.rate_limit_config.get('window', '1 minute')}",
                self.tool_type,
                {"current_requests": len(self._request_times), "limit": max_requests}
            )

        # Add current request
        self._request_times.append(current_time)

    def _parse_rate_limit_window(self, window: str) -> int:
        """Parse rate limit window string to seconds."""
        window = window.lower()
        if "second" in window:
            return int(window.split()[0])
        elif "minute" in window:
            return int(window.split()[0]) * 60
        elif "hour" in window:
            return int(window.split()[0]) * 3600
        else:
            return 60  # Default to 1 minute
"""
Unified Logging Service for Modern Agentic Workflows

This service provides a comprehensive logging solution that supports:
- User-scoped workflows with hierarchical context
- Real-time streaming + persistent storage
- Consistent logging patterns across all workflows
- Admin vs user visibility levels
- Trace correlation across distributed operations
"""

import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, Integer

from app.db.models.task import TaskLog, LogLevel
from app.db.models.user import User
from app.db.database import get_session_context
from app.services.pubsub_service import pubsub_service
from app.utils.logging import get_logger
from app.utils.metrics import MetricsCollector

logger = get_logger("unified_log_service")


class WorkflowType(str, Enum):
    """Types of workflows in the agentic system."""
    EMAIL_SYNC = "email_sync"
    AGENT_TASK = "agent_task"
    CONTENT_PROCESSING = "content_processing"
    WORKFLOW_AUTOMATION = "workflow_automation"
    CHAT_SESSION = "chat_session"
    SYSTEM_OPERATION = "system_operation"


class LogScope(str, Enum):
    """Scope levels for log visibility."""
    USER = "user"          # User-initiated workflows
    SYSTEM = "system"      # System operations
    ADMIN = "admin"        # Admin-only operations


@dataclass
class LogContext:
    """Structured context for hierarchical logging."""
    user_id: Optional[int] = None
    workflow_id: Optional[str] = None
    workflow_type: Optional[WorkflowType] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    step_id: Optional[str] = None
    trace_id: Optional[str] = None
    scope: LogScope = LogScope.USER
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value if self.workflow_type else None,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "step_id": self.step_id,
            "trace_id": self.trace_id,
            "scope": self.scope.value,
            "metadata": self.metadata
        }


class UnifiedLogService:
    """Unified logging service for all agentic workflows."""

    def __init__(self):
        self.pubsub = pubsub_service
        self.logger = get_logger("unified_log_service")
        self._active_contexts: Dict[str, LogContext] = {}

    async def create_workflow_context(
        self,
        user_id: int,
        workflow_type: WorkflowType,
        workflow_name: str,
        scope: LogScope = LogScope.USER,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogContext:
        """Create a new workflow logging context."""
        workflow_id = f"{workflow_type.value}_{uuid.uuid4().hex[:8]}"
        trace_id = uuid.uuid4().hex

        context = LogContext(
            user_id=user_id,
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            trace_id=trace_id,
            scope=scope,
            metadata=metadata or {}
        )

        self._active_contexts[workflow_id] = context

        # Log workflow start
        await self.log(
            context=context,
            level=LogLevel.INFO,
            message=f"Started {workflow_type.value} workflow: {workflow_name}",
            component="workflow_manager"
        )

        return context

    async def create_task_context(
        self,
        parent_context: LogContext,
        task_name: str,
        agent_id: Optional[str] = None
    ) -> LogContext:
        """Create a task context within a workflow."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        task_context = LogContext(
            user_id=parent_context.user_id,
            workflow_id=parent_context.workflow_id,
            workflow_type=parent_context.workflow_type,
            task_id=task_id,
            agent_id=agent_id,
            trace_id=parent_context.trace_id,
            scope=parent_context.scope,
            metadata=parent_context.metadata.copy()
        )

        await self.log(
            context=task_context,
            level=LogLevel.INFO,
            message=f"Started task: {task_name}",
            component="task_manager"
        )

        return task_context

    async def create_step_context(
        self,
        parent_context: LogContext,
        step_name: str
    ) -> LogContext:
        """Create a step context within a task."""
        step_id = f"step_{uuid.uuid4().hex[:8]}"

        step_context = LogContext(
            user_id=parent_context.user_id,
            workflow_id=parent_context.workflow_id,
            workflow_type=parent_context.workflow_type,
            task_id=parent_context.task_id,
            agent_id=parent_context.agent_id,
            step_id=step_id,
            trace_id=parent_context.trace_id,
            scope=parent_context.scope,
            metadata=parent_context.metadata.copy()
        )

        await self.log(
            context=step_context,
            level=LogLevel.DEBUG,
            message=f"Started step: {step_name}",
            component="step_executor"
        )

        return step_context

    async def log(
        self,
        context: LogContext,
        level: LogLevel,
        message: str,
        component: str,
        error: Optional[Exception] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a message with full hierarchical context."""
        try:
            # Prepare log data
            log_id = uuid.uuid4()
            log_data = {
                "id": log_id.hex,
                "level": level.value,
                "message": message,
                "component": component,
                "timestamp": datetime.utcnow().isoformat(),
                **context.to_dict()
            }

            # Add extra metadata
            if extra_metadata:
                log_data["metadata"].update(extra_metadata)

            # Add error details if present
            if error:
                log_data["error"] = {
                    "type": error.__class__.__name__,
                    "message": str(error),
                    "traceback": str(error.__traceback__) if error.__traceback__ else None
                }

            # Store in database
            log_record = await self._store_log(log_data)

            # Publish to Redis Stream for real-time streaming
            try:
                if not self.pubsub._running:
                    await self.pubsub.connect()
                stream_id = await self.pubsub.publish_log(log_data)
            except Exception as e:
                self.logger.warning(f"Failed to publish to Redis stream: {e}")
                stream_id = None

            # Update database record with stream_id
            if log_record and stream_id:
                async with get_session_context() as session:
                    log_record.stream_id = stream_id
                    await session.commit()

            # Send to WebSocket subscribers
            await self._broadcast_log(log_data)

            return log_id.hex

        except Exception as e:
            self.logger.error(f"Failed to log message: {e}")
            # Fallback to Python logging
            self.logger.log(getattr(logging, level.value.upper()), f"{component}: {message}")
            return ""

    async def get_workflow_logs(
        self,
        user_id: int,
        workflow_id: Optional[str] = None,
        workflow_type: Optional[WorkflowType] = None,
        level: Optional[LogLevel] = None,
        limit: int = 100,
        offset: int = 0,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """Get logs for workflows with user scoping."""
        try:
            async with get_session_context() as session:
                query = select(TaskLog)
                filters = []

                # User scoping
                if not is_admin:
                    # Regular users only see their own logs
                    filters.append(TaskLog.context["user_id"].astext.cast(Integer) == user_id)
                else:
                    # Admins can filter by user or see all
                    if user_id:
                        filters.append(TaskLog.context["user_id"].astext.cast(Integer) == user_id)

                # Workflow filtering
                if workflow_id:
                    filters.append(TaskLog.context["workflow_id"].astext == workflow_id)

                if workflow_type:
                    filters.append(TaskLog.context["workflow_type"].astext == workflow_type.value)

                # Level filtering
                if level:
                    filters.append(TaskLog.level == level)

                if filters:
                    query = query.where(and_(*filters))

                query = query.offset(offset).limit(limit).order_by(TaskLog.timestamp.desc())

                result = await session.execute(query)
                logs = result.scalars().all()

                return [log.to_dict() for log in logs]

        except Exception as e:
            self.logger.error(f"Failed to get workflow logs: {e}")
            return []

    async def complete_workflow(self, context: LogContext, success: bool = True, summary: Optional[str] = None):
        """Mark a workflow as completed."""
        status = "completed" if success else "failed"
        message = summary or f"Workflow {status}"

        await self.log(
            context=context,
            level=LogLevel.INFO if success else LogLevel.ERROR,
            message=message,
            component="workflow_manager",
            extra_metadata={"workflow_status": status}
        )

        # Clean up active context
        if context.workflow_id in self._active_contexts:
            del self._active_contexts[context.workflow_id]

    async def _store_log(self, log_data: Dict[str, Any]) -> Optional[TaskLog]:
        """Store log in database."""
        try:
            async with get_session_context() as session:
                # Handle UUID conversion safely
                log_id = log_data["id"]
                if isinstance(log_id, str) and len(log_id) == 32:
                    # Convert hex string to UUID
                    log_uuid = uuid.UUID(hex=log_id)
                elif isinstance(log_id, str) and len(log_id) > 0:
                    # Try parsing as full UUID string
                    log_uuid = uuid.UUID(log_id)
                else:
                    # Generate new UUID if invalid
                    log_uuid = uuid.uuid4()

                # Handle task_id and agent_id safely - allow None for workflow logs
                task_id_str = log_data.get("task_id")
                agent_id_str = log_data.get("agent_id")

                # Convert to UUIDs safely, allowing None
                task_uuid = None
                if task_id_str and task_id_str not in ["", "null"]:
                    try:
                        task_uuid = uuid.UUID(task_id_str)
                    except (ValueError, TypeError):
                        task_uuid = None

                agent_uuid = None
                if agent_id_str and agent_id_str not in ["", "null"]:
                    try:
                        agent_uuid = uuid.UUID(agent_id_str)
                    except (ValueError, TypeError):
                        agent_uuid = None

                log_record = TaskLog(
                    id=log_uuid,
                    task_id=task_uuid,
                    agent_id=agent_uuid,
                    level=LogLevel(log_data["level"]),
                    message=log_data["message"],
                    context=log_data,
                    timestamp=datetime.fromisoformat(log_data["timestamp"].replace('Z', '+00:00'))
                )

                session.add(log_record)
                await session.commit()
                return log_record

        except Exception as e:
            self.logger.error(f"Failed to store log in database: {e}")
            return None

    async def _broadcast_log(self, log_data: Dict[str, Any]):
        """Broadcast log to WebSocket subscribers."""
        try:
            # Import websocket manager locally to avoid circular imports
            from app.api.routes.websocket import manager as websocket_manager

            # Filter subscribers based on user permissions
            user_id = log_data.get("user_id")
            scope = log_data.get("scope", "user")

            # Broadcast to appropriate subscribers
            await websocket_manager.broadcast_log(log_data, user_id, scope)

        except Exception as e:
            self.logger.error(f"Failed to broadcast log: {e}")

    @asynccontextmanager
    async def workflow_context(
        self,
        user_id: int,
        workflow_type: WorkflowType,
        workflow_name: str,
        scope: LogScope = LogScope.USER
    ):
        """Context manager for workflow logging."""
        context = await self.create_workflow_context(user_id, workflow_type, workflow_name, scope)
        try:
            yield context
            await self.complete_workflow(context, success=True)
        except Exception as e:
            await self.complete_workflow(context, success=False, summary=f"Workflow failed: {str(e)}")
            raise

    @asynccontextmanager
    async def task_context(self, parent_context: LogContext, task_name: str, agent_id: Optional[str] = None):
        """Context manager for task logging."""
        context = await self.create_task_context(parent_context, task_name, agent_id)
        try:
            yield context
            await self.log(context, LogLevel.INFO, f"Completed task: {task_name}", "task_manager")
        except Exception as e:
            await self.log(context, LogLevel.ERROR, f"Task failed: {task_name}", "task_manager", error=e)
            raise

    @asynccontextmanager
    async def step_context(self, parent_context: LogContext, step_name: str):
        """Context manager for step logging."""
        context = await self.create_step_context(parent_context, step_name)
        try:
            yield context
            await self.log(context, LogLevel.INFO, f"Completed step: {step_name}", "step_manager")
        except Exception as e:
            await self.log(context, LogLevel.ERROR, f"Step failed: {step_name}", "step_manager", error=e)
            raise

    async def cleanup_old_logs(self, retention_days: int = 30):
        """Clean up old logs based on retention policy."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            async with get_session_context() as session:
                # Delete old logs
                result = await session.execute(
                    select(TaskLog).where(TaskLog.timestamp < cutoff_date)
                )
                old_logs = result.scalars().all()

                for log in old_logs:
                    await session.delete(log)

                await session.commit()

                self.logger.info(f"Cleaned up {len(old_logs)} old log records")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")


# Global instance
unified_log_service = UnifiedLogService()
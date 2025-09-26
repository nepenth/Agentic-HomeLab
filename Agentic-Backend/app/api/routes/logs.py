from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from app.db.models.task import TaskLog, LogLevel
from app.db.models.user import User
from app.api.dependencies import get_db_session, get_current_user
from app.utils.logging import get_logger
from app.services.unified_log_service import unified_log_service, WorkflowType, LogScope

logger = get_logger("logs_api")
router = APIRouter()


class LogResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    level: str
    message: str
    context: dict
    stream_id: Optional[str]
    timestamp: str


@router.get("/system", response_model=List[LogResponse])
async def get_system_logs(
    workflow_type: Optional[WorkflowType] = None,
    level: Optional[LogLevel] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get system logs - admin only endpoint."""
    try:
        # Check if user is admin/superuser
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required to view system logs"
            )

        # Use unified log service to get logs with admin permissions
        logs = await unified_log_service.get_workflow_logs(
            user_id=current_user.id,
            workflow_type=workflow_type,
            level=level,
            limit=limit,
            offset=offset,
            is_admin=True
        )

        return [LogResponse(**log) for log in logs]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system logs"
        )


@router.get("/user/{user_id}", response_model=List[LogResponse])
async def get_user_logs(
    user_id: int,
    workflow_type: Optional[WorkflowType] = None,
    level: Optional[LogLevel] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get logs for a specific user - users can see their own logs, admins can see any user's logs."""
    try:
        # Check permissions: users can see their own logs, admins can see any user's logs
        if not current_user.is_superuser and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: can only view your own logs"
            )

        # Use unified log service to get user-scoped logs
        logs = await unified_log_service.get_workflow_logs(
            user_id=user_id,
            workflow_type=workflow_type,
            level=level,
            limit=limit,
            offset=offset,
            is_admin=current_user.is_superuser
        )

        return [LogResponse(**log) for log in logs]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user logs for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user logs"
        )


@router.post("/test/generate")
async def generate_test_logs(
    count: int = Query(default=5, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate test logs for testing the log system - development only."""
    try:
        from datetime import datetime
        import uuid

        test_logs = []

        for i in range(count):
            # Create test context
            context = await unified_log_service.create_workflow_context(
                user_id=current_user.id,
                workflow_type=WorkflowType.EMAIL_SYNC if i % 2 == 0 else WorkflowType.AGENT_TASK,
                workflow_name=f"Test Workflow {i+1}",
                scope=LogScope.USER if i % 3 != 0 else LogScope.ADMIN
            )

            # Generate test logs
            levels = [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.DEBUG]
            messages = [
                f"Test log message {i+1}: Starting workflow execution",
                f"Test log message {i+1}: Processing data batch",
                f"Test log message {i+1}: Workflow completed successfully",
                f"Test log message {i+1}: Error occurred during processing",
                f"Test log message {i+1}: Debug information available"
            ]

            level = levels[i % len(levels)]
            message = messages[i % len(messages)]

            log_id = await unified_log_service.log(
                context=context,
                level=level,
                message=message,
                component="test_generator",
                extra_metadata={"test": True, "batch": i+1}
            )

            test_logs.append({
                "id": log_id,
                "level": level.value,
                "message": message,
                "user_id": current_user.id,
                "workflow_type": context.workflow_type.value if context.workflow_type else None,
                "scope": context.scope.value
            })

        return {
            "message": f"Generated {count} test logs",
            "logs": test_logs,
            "user": current_user.username
        }

    except Exception as e:
        logger.error(f"Failed to generate test logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test logs: {str(e)}"
        )


@router.get("/history", response_model=List[LogResponse])
async def get_historical_logs(
    agent_id: Optional[UUID] = None,
    task_id: Optional[UUID] = None,
    level: Optional[LogLevel] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    search: Optional[str] = Query(None, description="Search in log messages"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Query historical logs with advanced filtering."""
    try:
        query = select(TaskLog)
        filters = []

        if agent_id:
            filters.append(TaskLog.agent_id == agent_id)

        if task_id:
            filters.append(TaskLog.task_id == task_id)

        if level:
            filters.append(TaskLog.level == level)

        if start_time:
            filters.append(TaskLog.timestamp >= start_time)

        if end_time:
            filters.append(TaskLog.timestamp <= end_time)

        if search:
            filters.append(TaskLog.message.ilike(f"%{search}%"))

        if filters:
            query = query.where(and_(*filters))

        query = query.offset(offset).limit(limit).order_by(TaskLog.timestamp.desc())

        result = await db.execute(query)
        logs = result.scalars().all()

        return [LogResponse(**log.to_dict()) for log in logs]

    except Exception as e:
        logger.error(f"Failed to get historical logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve historical logs"
        )


@router.get("/{task_id}", response_model=List[LogResponse])
async def get_task_logs(
    task_id: UUID,
    level: Optional[LogLevel] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get task execution logs with pagination and filtering."""
    try:
        query = select(TaskLog).where(TaskLog.task_id == task_id)

        if level:
            query = query.where(TaskLog.level == level)

        query = query.offset(offset).limit(limit).order_by(TaskLog.timestamp.desc())

        result = await db.execute(query)
        logs = result.scalars().all()

        return [LogResponse(**log.to_dict()) for log in logs]

    except Exception as e:
        logger.error(f"Failed to get logs for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve logs"
        )


@router.get("/stream/{task_id}")
async def stream_task_logs(
    task_id: UUID,
    level: Optional[LogLevel] = None,
):
    """Server-sent events for real-time task logs."""
    
    async def event_generator():
        """Generate SSE events for log streaming."""
        try:
            # This is a placeholder - will be implemented with Redis Streams
            # For now, send a test event
            yield {
                "event": "log",
                "data": f"Streaming logs for task {task_id}"
            }
            
            # TODO: Implement real-time streaming with Redis Streams
            # while True:
            #     # Read from Redis Stream
            #     # Yield new log entries
            #     await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in log stream: {e}")
            yield {
                "event": "error",
                "data": str(e)
            }
    
    return EventSourceResponse(event_generator())


@router.get("/system", response_model=List[LogResponse])
async def get_system_logs(
    workflow_type: Optional[WorkflowType] = None,
    level: Optional[LogLevel] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get system logs - admin only endpoint."""
    try:
        # Check if user is admin/superuser
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required to view system logs"
            )

        # Use unified log service to get logs with admin permissions
        logs = await unified_log_service.get_workflow_logs(
            user_id=current_user.id,
            workflow_type=workflow_type,
            level=level,
            limit=limit,
            offset=offset,
            is_admin=True
        )

        return [LogResponse(**log) for log in logs]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system logs"
        )


@router.get("/user/{user_id}", response_model=List[LogResponse])
async def get_user_logs(
    user_id: int,
    workflow_type: Optional[WorkflowType] = None,
    level: Optional[LogLevel] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get logs for a specific user - users can see their own logs, admins can see any user's logs."""
    try:
        # Check permissions: users can see their own logs, admins can see any user's logs
        if not current_user.is_superuser and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: can only view your own logs"
            )

        # Use unified log service to get user-scoped logs
        logs = await unified_log_service.get_workflow_logs(
            user_id=user_id,
            workflow_type=workflow_type,
            level=level,
            limit=limit,
            offset=offset,
            is_admin=current_user.is_superuser
        )

        return [LogResponse(**log) for log in logs]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user logs for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user logs"
        )


@router.post("/test/generate")
async def generate_test_logs(
    count: int = Query(default=5, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate test logs for testing the log system - development only."""
    try:
        from datetime import datetime
        import uuid

        test_logs = []

        for i in range(count):
            # Create test context
            context = await unified_log_service.create_workflow_context(
                user_id=current_user.id,
                workflow_type=WorkflowType.EMAIL_SYNC if i % 2 == 0 else WorkflowType.AGENT_TASK,
                workflow_name=f"Test Workflow {i+1}",
                scope=LogScope.USER if i % 3 != 0 else LogScope.ADMIN
            )

            # Generate test logs
            levels = [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.DEBUG]
            messages = [
                f"Test log message {i+1}: Starting workflow execution",
                f"Test log message {i+1}: Processing data batch",
                f"Test log message {i+1}: Workflow completed successfully",
                f"Test log message {i+1}: Error occurred during processing",
                f"Test log message {i+1}: Debug information available"
            ]

            level = levels[i % len(levels)]
            message = messages[i % len(messages)]

            log_id = await unified_log_service.log(
                context=context,
                level=level,
                message=message,
                component="test_generator",
                extra_metadata={"test": True, "batch": i+1}
            )

            test_logs.append({
                "id": log_id,
                "level": level.value,
                "message": message,
                "user_id": current_user.id,
                "workflow_type": context.workflow_type.value if context.workflow_type else None,
                "scope": context.scope.value
            })

        return {
            "message": f"Generated {count} test logs",
            "logs": test_logs,
            "user": current_user.username
        }

    except Exception as e:
        logger.error(f"Failed to generate test logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test logs: {str(e)}"
        )
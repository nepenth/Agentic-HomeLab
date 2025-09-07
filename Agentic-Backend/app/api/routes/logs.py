from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from app.db.models.task import TaskLog, LogLevel
from app.api.dependencies import get_db_session
from app.utils.logging import get_logger

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
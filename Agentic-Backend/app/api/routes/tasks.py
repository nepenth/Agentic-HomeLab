from fastapi import APIRouter, Depends, HTTPException, status, Query
from starlette import status as status_codes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from app.db.models.task import Task, TaskStatus
from app.db.models.agent import Agent
from app.db.models.agent_type import AgentType
from app.api.dependencies import get_db_session, verify_api_key
from app.services.schema_manager import SchemaManager
from app.utils.logging import get_logger

logger = get_logger("tasks_api")
router = APIRouter()


class TaskCreate(BaseModel):
    agent_id: UUID
    input: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    id: str
    agent_id: str
    status: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    error_message: Optional[str]
    retry_count: int
    celery_task_id: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


@router.post("/run", response_model=TaskResponse, dependencies=[Depends(verify_api_key)])
async def run_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Enqueue a new task for execution."""
    try:
        # Create task record
        task = Task(
            agent_id=task_data.agent_id,
            input=task_data.input,
            status=TaskStatus.PENDING
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Enqueue Celery task
        from app.tasks.agent_tasks import process_agent_task
        celery_task = process_agent_task.delay(
            str(task.id),
            str(task_data.agent_id), 
            task_data.input
        )
        
        task.celery_task_id = celery_task.id
        await db.commit()
        
        logger.info(f"Created task: {task.id} for agent: {task_data.agent_id}")
        return TaskResponse(**task.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.get("/{task_id}/status", response_model=TaskResponse)
async def get_task_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get task status and result."""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return TaskResponse(**task.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task"
        )


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    agent_id: Optional[UUID] = None,
    agent_type: Optional[str] = Query(None, description="Filter by agent type (for dynamic agents)"),
    status: Optional[TaskStatus] = None,
    include_dynamic: bool = Query(True, description="Include tasks from dynamic agents"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List tasks with optional filtering."""
    try:
        # Join with Agent table to get agent type information
        query = select(Task).join(Agent, Task.agent_id == Agent.id)

        if agent_id:
            query = query.where(Task.agent_id == agent_id)

        if status:
            query = query.where(Task.status == status)

        # Filter by agent type if specified
        if agent_type:
            query = query.join(AgentType, Agent.agent_type_id == AgentType.id)
            query = query.where(AgentType.type_name == agent_type)

        # Filter dynamic vs static agents
        if not include_dynamic:
            # Only tasks from static agents
            query = query.where(Agent.agent_type_id.is_(None))

        query = query.offset(offset).limit(limit).order_by(Task.created_at.desc())

        result = await db.execute(query)
        tasks = result.scalars().all()

        return [TaskResponse(**task.to_dict()) for task in tasks]

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )


@router.delete("/{task_id}", dependencies=[Depends(verify_api_key)])
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Cancel a running task."""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task cannot be cancelled"
            )
        
        # Cancel Celery task if it exists
        if task.celery_task_id is not None:
            from app.celery_app import celery_app
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        
        # Update task status
        stmt = update(Task).where(Task.id == task_id).values(status=TaskStatus.CANCELLED)
        await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Cancelled task: {task_id}")
        return {"message": "Task cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task"
        )
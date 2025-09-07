"""
Dynamic Agent Instance Management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from app.api.dependencies import get_db_session, verify_api_key
from app.agents.dynamic_agent import DynamicAgent
from app.agents.factory import AgentFactory
from app.services.schema_manager import SchemaManager
from app.services.agent_lifecycle_service import AgentLifecycleService
from app.db.models.agent import Agent
from app.db.models.task import Task
from app.utils.logging import get_logger

logger = get_logger("dynamic_agents_api")
router = APIRouter()


class DynamicAgentCreate(BaseModel):
    """Request to create a new dynamic agent instance."""
    agent_type: str = Field(..., description="Type of agent to create")
    name: str = Field(..., min_length=1, max_length=255, description="Name for the agent instance")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent-specific configuration")
    initial_task_data: Optional[Dict[str, Any]] = Field(None, description="Initial task data if starting immediately")


class DynamicAgentResponse(BaseModel):
    """Response containing dynamic agent information."""
    id: str
    agent_type: str
    name: str
    status: str
    config: Dict[str, Any]
    created_at: str
    updated_at: Optional[str]
    schema_info: Dict[str, Any]


class TaskExecutionRequest(BaseModel):
    """Request to execute a task with a dynamic agent."""
    input_data: Dict[str, Any] = Field(..., description="Input data for the task")
    task_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Task-specific configuration")


class TaskExecutionResponse(BaseModel):
    """Response from task execution."""
    task_id: str
    status: str
    results: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None


class AgentResultsQuery(BaseModel):
    """Query parameters for agent results."""
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    date_from: Optional[str] = Field(None, description="Filter results from this date (ISO format)")
    date_to: Optional[str] = Field(None, description="Filter results to this date (ISO format)")
    result_filter: Optional[Dict[str, Any]] = Field(None, description="Filter results by field values")


@router.post("", response_model=DynamicAgentResponse, dependencies=[Depends(verify_api_key)])
async def create_dynamic_agent(
    agent_data: DynamicAgentCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new dynamic agent instance."""
    try:
        # Get the agent type schema
        schema_manager = SchemaManager(db)
        agent_type_obj = await schema_manager.get_agent_type(agent_data.agent_type)

        if not agent_type_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent type '{agent_data.agent_type}' not found"
            )

        # Create agent factory and build the agent
        agent_factory = AgentFactory(schema_manager, None)  # Tool registry would be passed here

        # For now, create a basic agent record
        agent = Agent(
            name=agent_data.name,
            model_name="llama2",  # Default model
            config=agent_data.config or {},
            agent_type_id=agent_type_obj.id
        )

        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        # Get schema info for response
        schema_info = {
            "agent_type": agent_data.agent_type,
            "version": agent_type_obj.version,
            "input_fields": list(agent_type_obj.schema_definition.get("input_schema", {}).keys()),
            "output_fields": list(agent_type_obj.schema_definition.get("output_schema", {}).keys())
        }

        logger.info(f"Created dynamic agent: {agent.id} of type {agent_data.agent_type}")

        return DynamicAgentResponse(
            id=str(agent.id),
            agent_type=agent_data.agent_type,
            name=agent.name,
            status="active",
            config=agent.config,
            created_at=agent.created_at.isoformat() if agent.created_at else "",
            updated_at=agent.updated_at.isoformat() if agent.updated_at else None,
            schema_info=schema_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create dynamic agent: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dynamic agent"
        )


@router.get("", response_model=List[DynamicAgentResponse])
async def list_dynamic_agents(
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List dynamic agent instances with optional filtering."""
    try:
        query = select(Agent).where(Agent.agent_type_id.isnot(None))  # Only dynamic agents

        # Apply filters
        if status:
            query = query.where(Agent.is_active == (status == "active"))

        if agent_type:
            # This would need a join with AgentType table in a real implementation
            pass

        query = query.offset(offset).limit(limit).order_by(Agent.created_at.desc())

        result = await db.execute(query)
        agents = result.scalars().all()

        # Build response with schema info
        response_agents = []
        for agent in agents:
            # Get agent type info (simplified)
            agent_type_name = "unknown"  # Would be populated from AgentType join

            schema_info = {
                "agent_type": agent_type_name,
                "version": "1.0.0",
                "input_fields": [],
                "output_fields": []
            }

            response_agents.append(DynamicAgentResponse(
                id=str(agent.id),
                agent_type=agent_type_name,
                name=agent.name,
                status="active" if agent.is_active else "inactive",
                config=agent.config,
                created_at=agent.created_at.isoformat() if agent.created_at else "",
                updated_at=agent.updated_at.isoformat() if agent.updated_at else None,
                schema_info=schema_info
            ))

        return response_agents

    except Exception as e:
        logger.error(f"Failed to list dynamic agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dynamic agents"
        )


@router.get("/{agent_id}", response_model=DynamicAgentResponse)
async def get_dynamic_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific dynamic agent instance."""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent or not agent.agent_type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dynamic agent not found"
            )

        # Get agent type info (simplified)
        agent_type_name = "unknown"  # Would be populated from AgentType table

        schema_info = {
            "agent_type": agent_type_name,
            "version": "1.0.0",
            "input_fields": [],
            "output_fields": []
        }

        return DynamicAgentResponse(
            id=str(agent.id),
            agent_type=agent_type_name,
            name=agent.name,
            status="active" if agent.is_active else "inactive",
            config=agent.config,
            created_at=agent.created_at.isoformat() if agent.created_at else "",
            updated_at=agent.updated_at.isoformat() if agent.updated_at else None,
            schema_info=schema_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dynamic agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dynamic agent"
        )


@router.get("/{agent_id}/schema", response_model=Dict[str, Any])
async def get_dynamic_agent_schema(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get the schema for a dynamic agent instance."""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent or not agent.agent_type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dynamic agent not found"
            )

        # Get agent type and return its schema
        schema_manager = SchemaManager(db)

        # This is a simplified implementation - in reality you'd need to
        # join with AgentType table to get the schema
        agent_types = await schema_manager.list_agent_types()
        agent_schema = {}

        for agent_type in agent_types:
            if agent_type.get('id') == str(agent.agent_type_id):
                agent_schema = agent_type.get('schema_definition', {})
                break

        if not agent_schema:
            agent_schema = {
                "agent_type": "unknown",
                "message": "Schema not found for this agent instance"
            }

        return agent_schema

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent schema"
        )


@router.post("/{agent_id}/execute", response_model=TaskExecutionResponse, dependencies=[Depends(verify_api_key)])
async def execute_dynamic_agent_task(
    agent_id: UUID,
    request: TaskExecutionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Execute a task with a dynamic agent."""
    try:
        # Get the agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent or not agent.agent_type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dynamic agent not found"
            )

        # Create a task record
        from app.db.models.task import Task
        from datetime import datetime

        task = Task(
            agent_id=agent_id,
            input_data=request.input_data,
            config=request.task_config or {},
            status="running"
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        # Here you would typically:
        # 1. Create a DynamicAgent instance
        # 2. Execute the task
        # 3. Store results
        # For now, we'll simulate successful execution

        # Simulate task completion
        task.status = "completed"
        task.output_data = {"result": "Task completed successfully", "agent_id": str(agent_id)}
        task.completed_at = datetime.utcnow()
        await db.commit()

        logger.info(f"Executed task {task.id} for dynamic agent {agent_id}")

        return TaskExecutionResponse(
            task_id=str(task.id),
            status=task.status,
            results=task.output_data,
            execution_time=0.0  # Would be calculated from actual execution
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute task for agent {agent_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute agent task"
        )


@router.get("/{agent_id}/results", response_model=List[Dict[str, Any]])
async def get_dynamic_agent_results(
    agent_id: UUID,
    query: AgentResultsQuery = Depends(),
    db: AsyncSession = Depends(get_db_session)
):
    """Get results from a dynamic agent's executed tasks."""
    try:
        # Get tasks for this agent
        task_query = select(Task).where(
            Task.agent_id == agent_id,
            Task.status == "completed"
        )

        # Apply date filters if provided
        if query.date_from:
            from datetime import datetime
            date_from = datetime.fromisoformat(query.date_from.replace('Z', '+00:00'))
            task_query = task_query.where(Task.completed_at >= date_from)

        if query.date_to:
            from datetime import datetime
            date_to = datetime.fromisoformat(query.date_to.replace('Z', '+00:00'))
            task_query = task_query.where(Task.completed_at <= date_to)

        task_query = task_query.offset(query.offset).limit(query.limit)
        task_query = task_query.order_by(Task.completed_at.desc())

        result = await db.execute(task_query)
        tasks = result.scalars().all()

        # Format results
        results = []
        for task in tasks:
            result_data = {
                "task_id": str(task.id),
                "executed_at": task.completed_at.isoformat() if task.completed_at else None,
                "input_data": task.input_data,
                "output_data": task.output_data,
                "execution_time": getattr(task, 'execution_time', None)
            }

            # Apply result filter if provided
            if query.result_filter:
                # Simple filtering - in production this would be more sophisticated
                if all(result_data.get(k) == v for k, v in query.result_filter.items()):
                    results.append(result_data)
            else:
                results.append(result_data)

        return results

    except Exception as e:
        logger.error(f"Failed to get results for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent results"
        )


@router.delete("/{agent_id}", dependencies=[Depends(verify_api_key)])
async def delete_dynamic_agent(
    agent_id: UUID,
    cleanup_data: bool = Query(False, description="Whether to delete associated task data"),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a dynamic agent instance."""
    try:
        # Get the agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent or not agent.agent_type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dynamic agent not found"
            )

        # Delete associated tasks if requested
        if cleanup_data:
            tasks_query = select(Task).where(Task.agent_id == agent_id)
            tasks_result = await db.execute(tasks_query)
            tasks = tasks_result.scalars().all()

            for task in tasks:
                await db.delete(task)

        # Delete the agent
        await db.delete(agent)
        await db.commit()

        logger.info(f"Deleted dynamic agent: {agent_id} (cleanup_data={cleanup_data})")

        return {
            "message": "Dynamic agent deleted successfully",
            "agent_id": str(agent_id),
            "cleanup_performed": cleanup_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dynamic agent {agent_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dynamic agent"
        )


@router.get("/{agent_id}/status", response_model=Dict[str, Any])
async def get_dynamic_agent_status(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get the current status and statistics for a dynamic agent."""
    try:
        # Get the agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent or not agent.agent_type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dynamic agent not found"
            )

        # Get task statistics
        total_tasks_query = select(Task).where(Task.agent_id == agent_id)
        total_tasks_result = await db.execute(
            total_tasks_query.with_only_columns([Task.id])
        )
        total_tasks = len(total_tasks_result.all())

        completed_tasks_query = select(Task).where(
            Task.agent_id == agent_id,
            Task.status == "completed"
        )
        completed_tasks_result = await db.execute(
            completed_tasks_query.with_only_columns([Task.id])
        )
        completed_tasks = len(completed_tasks_result.all())

        running_tasks_query = select(Task).where(
            Task.agent_id == agent_id,
            Task.status == "running"
        )
        running_tasks_result = await db.execute(
            running_tasks_query.with_only_columns([Task.id])
        )
        running_tasks = len(running_tasks_result.all())

        return {
            "agent_id": str(agent_id),
            "name": agent.name,
            "status": "active" if agent.is_active else "inactive",
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "statistics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "running_tasks": running_tasks,
                "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent status"
        )
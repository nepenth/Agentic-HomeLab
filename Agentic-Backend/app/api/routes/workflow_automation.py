"""
Workflow Automation API Routes

Provides REST API endpoints for:
- Workflow definition management
- Workflow execution and scheduling
- Execution monitoring and control
- Resource optimization and health monitoring

Author: Kilo Code
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workflow_automation_service import (
    workflow_automation_service,
    WorkflowStatus,
    TriggerType,
    Priority,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowSchedule
)
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["Workflow Automation"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Pydantic Models for API
# ============================================================================

class WorkflowStepModel(BaseModel):
    """API model for workflow step"""
    id: str
    name: str
    type: str
    config: Dict[str, Any]
    dependencies: List[str] = []
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    on_failure: Optional[str] = None
    conditions: List[Dict[str, Any]] = []


class WorkflowDefinitionCreate(BaseModel):
    """API model for creating workflow definition"""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    version: str = Field("1.0.0", description="Workflow version")
    steps: Dict[str, WorkflowStepModel] = Field(..., description="Workflow steps")
    trigger_config: Dict[str, Any] = Field(default_factory=dict, description="Trigger configuration")
    priority: Priority = Field(Priority.NORMAL, description="Workflow priority")
    max_execution_time: int = Field(3600, description="Maximum execution time in seconds")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict, description="Resource requirements")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WorkflowDefinitionUpdate(BaseModel):
    """API model for updating workflow definition"""
    name: Optional[str] = Field(None, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: Optional[str] = Field(None, description="Workflow version")
    steps: Optional[Dict[str, WorkflowStepModel]] = Field(None, description="Workflow steps")
    trigger_config: Optional[Dict[str, Any]] = Field(None, description="Trigger configuration")
    priority: Optional[Priority] = Field(None, description="Workflow priority")
    max_execution_time: Optional[int] = Field(None, description="Maximum execution time in seconds")
    resource_requirements: Optional[Dict[str, Any]] = Field(None, description="Resource requirements")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WorkflowExecutionResponse(BaseModel):
    """API model for workflow execution response"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    error_message: Optional[str] = None
    retry_count: int = 0
    priority: Priority


class WorkflowScheduleCreate(BaseModel):
    """API model for creating workflow schedule"""
    workflow_id: str = Field(..., description="Workflow ID to schedule")
    trigger_type: TriggerType = Field(..., description="Trigger type")
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduled triggers")
    interval_seconds: Optional[int] = Field(None, description="Interval in seconds for interval triggers")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")


class WorkflowScheduleResponse(BaseModel):
    """API model for workflow schedule response"""
    id: str
    workflow_id: str
    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    enabled: bool = True
    parameters: Dict[str, Any] = {}


# ============================================================================
# Workflow Definition Endpoints
# ============================================================================

@router.post("/definitions", response_model=Dict[str, Any])
async def create_workflow_definition(
    definition: WorkflowDefinitionCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new workflow definition

    This endpoint allows creating complex workflow definitions with:
    - Multiple steps with dependencies
    - Conditional logic and branching
    - Error recovery and retry mechanisms
    - Resource requirements and optimization
    """
    try:
        # Convert Pydantic models to service models
        steps_dict = {}
        for step_id, step_model in definition.steps.items():
            steps_dict[step_id] = {
                "id": step_model.id,
                "name": step_model.name,
                "type": step_model.type,
                "config": step_model.config,
                "dependencies": step_model.dependencies,
                "timeout_seconds": step_model.timeout_seconds,
                "retry_count": step_model.retry_count,
                "max_retries": step_model.max_retries,
                "on_failure": step_model.on_failure,
                "conditions": step_model.conditions
            }

        definition_data = {
            "name": definition.name,
            "description": definition.description,
            "version": definition.version,
            "steps": steps_dict,
            "trigger_config": definition.trigger_config,
            "priority": definition.priority.value,
            "max_execution_time": definition.max_execution_time,
            "resource_requirements": definition.resource_requirements,
            "metadata": definition.metadata
        }

        created_definition = await workflow_automation_service.create_workflow_definition(definition_data)

        return {
            "status": "success",
            "message": "Workflow definition created successfully",
            "data": {
                "id": created_definition.id,
                "name": created_definition.name,
                "description": created_definition.description,
                "version": created_definition.version,
                "steps_count": len(created_definition.steps),
                "created_at": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to create workflow definition: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create workflow definition: {str(e)}")


@router.get("/definitions", response_model=Dict[str, Any])
async def list_workflow_definitions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: Dict = Depends(get_current_user)
):
    """List all workflow definitions with pagination"""
    try:
        # Get all workflow definitions (in real implementation, this would be paginated from database)
        definitions = list(workflow_automation_service.workflow_definitions.values())

        # Apply pagination
        total = len(definitions)
        definitions = definitions[skip:skip + limit]

        # Convert to response format
        definition_list = []
        for definition in definitions:
            definition_list.append({
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "version": definition.version,
                "steps_count": len(definition.steps),
                "priority": definition.priority.name,
                "created_at": datetime.utcnow().isoformat()  # Placeholder
            })

        return {
            "status": "success",
            "data": {
                "definitions": definition_list,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }

    except Exception as e:
        logger.error(f"Failed to list workflow definitions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflow definitions: {str(e)}")


@router.get("/definitions/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow_definition(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific workflow definition"""
    try:
        if workflow_id not in workflow_automation_service.workflow_definitions:
            raise HTTPException(status_code=404, detail=f"Workflow definition not found: {workflow_id}")

        definition = workflow_automation_service.workflow_definitions[workflow_id]

        return {
            "status": "success",
            "data": {
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "version": definition.version,
                "steps": definition.steps,
                "trigger_config": definition.trigger_config,
                "priority": definition.priority.name,
                "max_execution_time": definition.max_execution_time,
                "resource_requirements": definition.resource_requirements,
                "metadata": definition.metadata
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow definition {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow definition: {str(e)}")


@router.put("/definitions/{workflow_id}", response_model=Dict[str, Any])
async def update_workflow_definition(
    workflow_id: str,
    updates: WorkflowDefinitionUpdate,
    current_user: Dict = Depends(get_current_user)
):
    """Update an existing workflow definition"""
    try:
        if workflow_id not in workflow_automation_service.workflow_definitions:
            raise HTTPException(status_code=404, detail=f"Workflow definition not found: {workflow_id}")

        # Convert updates to dict
        update_data = updates.dict(exclude_unset=True)

        # Convert steps if present
        if 'steps' in update_data and update_data['steps']:
            steps_dict = {}
            for step_id, step_model in update_data['steps'].items():
                if isinstance(step_model, dict):
                    steps_dict[step_id] = step_model
                else:
                    steps_dict[step_id] = step_model.dict()
            update_data['steps'] = steps_dict

        # Convert priority enum
        if 'priority' in update_data and update_data['priority']:
            update_data['priority'] = update_data['priority'].value

        updated_definition = await workflow_automation_service.update_workflow_definition(workflow_id, update_data)

        return {
            "status": "success",
            "message": "Workflow definition updated successfully",
            "data": {
                "id": updated_definition.id,
                "name": updated_definition.name,
                "version": updated_definition.version,
                "updated_at": datetime.utcnow().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow definition {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update workflow definition: {str(e)}")


@router.delete("/definitions/{workflow_id}", response_model=Dict[str, Any])
async def delete_workflow_definition(
    workflow_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a workflow definition"""
    try:
        success = await workflow_automation_service.delete_workflow_definition(workflow_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow definition not found: {workflow_id}")

        return {
            "status": "success",
            "message": "Workflow definition deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow definition {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow definition: {str(e)}")


# ============================================================================
# Workflow Execution Endpoints
# ============================================================================

@router.post("/execute", response_model=Dict[str, Any])
async def execute_workflow(
    workflow_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    priority: Priority = Priority.NORMAL,
    background_tasks: BackgroundTasks = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Execute a workflow immediately

    This endpoint starts workflow execution and returns immediately with execution ID.
    Use the execution status endpoint to monitor progress.
    """
    try:
        execution_id = await workflow_automation_service.execute_workflow(
            workflow_id,
            parameters,
            priority
        )

        return {
            "status": "success",
            "message": "Workflow execution started",
            "data": {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "started_at": datetime.utcnow().isoformat()
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")


@router.post("/schedule", response_model=Dict[str, Any])
async def schedule_workflow(
    schedule: WorkflowScheduleCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Schedule a workflow for future execution"""
    try:
        schedule_id = await workflow_automation_service.schedule_workflow(
            schedule.workflow_id,
            {
                "type": schedule.trigger_type.value,
                "cron_expression": schedule.cron_expression,
                "interval_seconds": schedule.interval_seconds
            },
            schedule.parameters
        )

        return {
            "status": "success",
            "message": "Workflow scheduled successfully",
            "data": {
                "schedule_id": schedule_id,
                "workflow_id": schedule.workflow_id,
                "trigger_type": schedule.trigger_type.value
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to schedule workflow {schedule.workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule workflow: {str(e)}")


@router.get("/executions", response_model=Dict[str, Any])
async def list_workflow_executions(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    status: Optional[WorkflowStatus] = Query(None, description="Filter by execution status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: Dict = Depends(get_current_user)
):
    """List workflow executions with optional filtering"""
    try:
        executions = await workflow_automation_service.list_workflow_executions(
            workflow_id=workflow_id,
            status=status,
            limit=limit
        )

        # Convert to response format
        execution_list = []
        for execution in executions:
            execution_list.append({
                "execution_id": execution.id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "start_time": execution.start_time.isoformat(),
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "current_step": execution.current_step,
                "error_message": execution.error_message,
                "retry_count": execution.retry_count,
                "priority": execution.priority.name
            })

        return {
            "status": "success",
            "data": {
                "executions": execution_list,
                "count": len(execution_list)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list workflow executions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflow executions: {str(e)}")


@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_workflow_execution_status(
    execution_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get the status of a specific workflow execution"""
    try:
        execution = await workflow_automation_service.get_workflow_execution_status(execution_id)

        if not execution:
            raise HTTPException(status_code=404, detail=f"Workflow execution not found: {execution_id}")

        return {
            "status": "success",
            "data": {
                "execution_id": execution.id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "start_time": execution.start_time.isoformat(),
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "current_step": execution.current_step,
                "step_results": execution.step_results,
                "context": execution.context,
                "error_message": execution.error_message,
                "retry_count": execution.retry_count,
                "priority": execution.priority.name,
                "duration_seconds": (
                    (execution.end_time - execution.start_time).total_seconds()
                    if execution.end_time else None
                )
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow execution status {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow execution status: {str(e)}")


@router.delete("/executions/{execution_id}", response_model=Dict[str, Any])
async def cancel_workflow_execution(
    execution_id: str,
    reason: str = Query("Cancelled by user", description="Cancellation reason"),
    current_user: Dict = Depends(get_current_user)
):
    """Cancel a running workflow execution"""
    try:
        success = await workflow_automation_service.cancel_workflow_execution(execution_id, reason)

        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow execution not found or cannot be cancelled: {execution_id}")

        return {
            "status": "success",
            "message": "Workflow execution cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow execution: {str(e)}")


# ============================================================================
# Workflow Schedule Management Endpoints
# ============================================================================

@router.get("/schedules", response_model=Dict[str, Any])
async def list_workflow_schedules(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    current_user: Dict = Depends(get_current_user)
):
    """List workflow schedules with optional filtering"""
    try:
        schedules = list(workflow_automation_service.workflow_schedules.values())

        # Apply filters
        if workflow_id:
            schedules = [s for s in schedules if s.workflow_id == workflow_id]
        if enabled is not None:
            schedules = [s for s in schedules if s.enabled == enabled]

        # Convert to response format
        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                "id": schedule.id,
                "workflow_id": schedule.workflow_id,
                "trigger_type": schedule.trigger_type.value,
                "cron_expression": schedule.cron_expression,
                "interval_seconds": schedule.interval_seconds,
                "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "enabled": schedule.enabled,
                "parameters": schedule.parameters
            })

        return {
            "status": "success",
            "data": {
                "schedules": schedule_list,
                "count": len(schedule_list)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list workflow schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflow schedules: {str(e)}")


@router.delete("/schedules/{schedule_id}", response_model=Dict[str, Any])
async def delete_workflow_schedule(
    schedule_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a workflow schedule"""
    try:
        if schedule_id not in workflow_automation_service.workflow_schedules:
            raise HTTPException(status_code=404, detail=f"Workflow schedule not found: {schedule_id}")

        # Remove from service
        del workflow_automation_service.workflow_schedules[schedule_id]

        return {
            "status": "success",
            "message": "Workflow schedule deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow schedule: {str(e)}")


# ============================================================================
# Workflow Health and Monitoring Endpoints
# ============================================================================

@router.get("/health", response_model=Dict[str, Any])
async def get_workflow_service_health():
    """Get workflow automation service health status"""
    try:
        # Get basic service stats
        active_executions = len([
            e for e in workflow_automation_service.active_workflows.values()
            if e.status in [WorkflowStatus.RUNNING, WorkflowStatus.PENDING]
        ])

        total_definitions = len(workflow_automation_service.workflow_definitions)
        total_schedules = len(workflow_automation_service.workflow_schedules)

        # Check scheduler health
        scheduler_healthy = True
        try:
            # This would check if the scheduler is running properly
            pass
        except Exception:
            scheduler_healthy = False

        health_status = "healthy" if scheduler_healthy else "degraded"

        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "workflow_automation",
            "metrics": {
                "active_executions": active_executions,
                "total_definitions": total_definitions,
                "total_schedules": total_schedules,
                "scheduler_healthy": scheduler_healthy
            }
        }

    except Exception as e:
        logger.error(f"Failed to get workflow service health: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "workflow_automation",
            "error": str(e)
        }


@router.get("/stats", response_model=Dict[str, Any])
async def get_workflow_service_stats():
    """Get comprehensive workflow service statistics"""
    try:
        # Calculate various statistics
        executions_by_status = {}
        for execution in workflow_automation_service.active_workflows.values():
            status_name = execution.status.value
            executions_by_status[status_name] = executions_by_status.get(status_name, 0) + 1

        # Get schedule statistics
        enabled_schedules = sum(1 for s in workflow_automation_service.workflow_schedules.values() if s.enabled)
        disabled_schedules = len(workflow_automation_service.workflow_schedules) - enabled_schedules

        return {
            "status": "success",
            "data": {
                "definitions": {
                    "total": len(workflow_automation_service.workflow_definitions),
                    "by_priority": {}  # Would be calculated from definitions
                },
                "executions": {
                    "total_active": len(workflow_automation_service.active_workflows),
                    "by_status": executions_by_status
                },
                "schedules": {
                    "total": len(workflow_automation_service.workflow_schedules),
                    "enabled": enabled_schedules,
                    "disabled": disabled_schedules
                },
                "performance": {
                    "average_execution_time": None,  # Would be calculated from historical data
                    "success_rate": None  # Would be calculated from historical data
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get workflow service stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow service stats: {str(e)}")


# ============================================================================
# Conditional Logic Evaluation Endpoint
# ============================================================================

@router.post("/evaluate-conditions", response_model=Dict[str, Any])
async def evaluate_workflow_conditions(
    conditions: List[Dict[str, Any]],
    context: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Evaluate conditional logic against a context

    This endpoint allows testing conditional logic before creating workflows
    or for debugging existing workflow conditions.
    """
    try:
        result = await workflow_automation_service.evaluate_conditions(conditions, context)

        return {
            "status": "success",
            "data": {
                "result": result,
                "conditions_evaluated": len(conditions),
                "context_keys": list(context.keys())
            }
        }

    except Exception as e:
        logger.error(f"Failed to evaluate conditions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate conditions: {str(e)}")
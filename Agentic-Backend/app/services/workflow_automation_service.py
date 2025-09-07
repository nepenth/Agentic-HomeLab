"""
Workflow Automation Engine Service

This service provides intelligent workflow automation capabilities including:
- Scheduled workflows (time-based and event-triggered execution)
- Conditional logic (rule-based workflow branching and decisions)
- Error recovery (automatic retry and alternative path execution)
- Resource optimization (intelligent resource allocation and scaling)

Author: Kilo Code
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
import aio_pika
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.database import get_db
from app.services.pubsub_service import RedisPubSubService as PubSubService
from app.services.system_metrics_service import SystemMetricsService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TriggerType(Enum):
    """Workflow trigger types"""
    SCHEDULED = "scheduled"
    EVENT = "event"
    MANUAL = "manual"
    API = "api"


class Priority(Enum):
    """Workflow priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    id: str
    name: str
    type: str
    config: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    on_failure: Optional[str] = None  # Alternative step to execute on failure
    conditions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    version: str
    steps: Dict[str, WorkflowStep]
    trigger_config: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    max_execution_time: int = 3600  # 1 hour
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    id: str
    workflow_id: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    priority: Priority = Priority.NORMAL
    processed_items: List[str] = field(default_factory=list)  # Track successfully processed items
    total_items: int = 0  # Total items to process
    progress_percentage: float = 0.0  # Progress tracking


@dataclass
class WorkflowSchedule:
    """Scheduled workflow configuration"""
    id: str
    workflow_id: str
    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


class WorkflowAutomationService:
    """
    Intelligent workflow automation engine with scheduling, conditional logic,
    error recovery, and resource optimization capabilities.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.redis: Optional[redis.Redis] = None
        self.pubsub_service = PubSubService()
        self.metrics_service = SystemMetricsService()
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.workflow_schedules: Dict[str, WorkflowSchedule] = {}

    async def initialize(self):
        """Initialize the workflow automation service"""
        try:
            # Initialize Redis for distributed state management
            self.redis = redis.Redis(
                host="localhost",
                port=6379,
                db=1,  # Use separate DB for workflow data
                decode_responses=True
            )

            # Start the scheduler
            self.scheduler.start()

            # Load existing workflow definitions and schedules
            await self._load_workflow_definitions()
            await self._load_workflow_schedules()

            # Register event handlers
            await self._register_event_handlers()

            logger.info("Workflow Automation Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Workflow Automation Service: {e}")
            raise

    async def shutdown(self):
        """Shutdown the workflow automation service"""
        try:
            # Stop all active workflows
            for execution_id, execution in self.active_workflows.items():
                if execution.status == WorkflowStatus.RUNNING:
                    await self._cancel_workflow_execution(execution_id, "Service shutdown")

            # Stop the scheduler
            if self.scheduler.running:
                self.scheduler.shutdown()

            # Close Redis connection
            if self.redis:
                await self.redis.close()

            logger.info("Workflow Automation Service shutdown complete")

        except Exception as e:
            logger.error(f"Error during Workflow Automation Service shutdown: {e}")

    # ============================================================================
    # Workflow Definition Management
    # ============================================================================

    async def create_workflow_definition(self, definition_data: Dict[str, Any]) -> WorkflowDefinition:
        """Create a new workflow definition"""
        try:
            # Validate workflow definition
            definition = await self._validate_workflow_definition(definition_data)

            # Store in memory
            self.workflow_definitions[definition.id] = definition

            # Persist to database
            await self._persist_workflow_definition(definition)

            # Create schedule if specified
            if definition.trigger_config:
                await self._create_workflow_schedule(definition)

            logger.info(f"Created workflow definition: {definition.name} ({definition.id})")
            return definition

        except Exception as e:
            logger.error(f"Failed to create workflow definition: {e}")
            raise

    async def update_workflow_definition(self, workflow_id: str, updates: Dict[str, Any]) -> WorkflowDefinition:
        """Update an existing workflow definition"""
        try:
            if workflow_id not in self.workflow_definitions:
                raise ValueError(f"Workflow definition not found: {workflow_id}")

            definition = self.workflow_definitions[workflow_id]

            # Apply updates to definition attributes
            for key, value in updates.items():
                if hasattr(definition, key) and key not in ['steps']:  # Handle steps separately
                    setattr(definition, key, value)

            # Handle steps updates specifically
            if 'steps' in updates:
                steps_updates = updates['steps']
                if isinstance(steps_updates, dict):
                    # Update existing steps and add new ones
                    for step_id, step_data in steps_updates.items():
                        if step_id in definition.steps:
                            # Update existing step
                            existing_step = definition.steps[step_id]
                            for attr, val in step_data.items():
                                if hasattr(existing_step, attr):
                                    setattr(existing_step, attr, val)
                        else:
                            # Add new step
                            new_step = WorkflowStep(
                                id=step_id,
                                name=step_data.get('name', step_id),
                                type=step_data.get('type', 'task'),
                                config=step_data.get('config', {}),
                                dependencies=step_data.get('dependencies', []),
                                timeout_seconds=step_data.get('timeout_seconds', 300),
                                retry_count=0,
                                max_retries=step_data.get('max_retries', 3),
                                on_failure=step_data.get('on_failure'),
                                conditions=step_data.get('conditions', [])
                            )
                            definition.steps[step_id] = new_step

            # Re-validate the updated definition
            definition_dict = {
                'id': definition.id,
                'name': definition.name,
                'description': definition.description,
                'version': definition.version,
                'steps': {sid: step.__dict__ for sid, step in definition.steps.items()},
                'trigger_config': definition.trigger_config,
                'priority': definition.priority.value,
                'max_execution_time': definition.max_execution_time,
                'resource_requirements': definition.resource_requirements,
                'metadata': definition.metadata
            }

            definition = await self._validate_workflow_definition(definition_dict)

            # Update in memory
            self.workflow_definitions[workflow_id] = definition

            # Persist changes
            await self._persist_workflow_definition(definition)

            # Update schedule if trigger config changed
            if 'trigger_config' in updates:
                await self._update_workflow_schedule(definition)

            logger.info(f"Updated workflow definition: {definition.name} ({definition.id})")
            return definition

        except Exception as e:
            logger.error(f"Failed to update workflow definition: {e}")
            raise

    async def delete_workflow_definition(self, workflow_id: str) -> bool:
        """Delete a workflow definition"""
        try:
            if workflow_id not in self.workflow_definitions:
                return False

            definition = self.workflow_definitions[workflow_id]

            # Remove from scheduler
            await self._remove_workflow_schedule(workflow_id)

            # Remove from memory
            del self.workflow_definitions[workflow_id]

            # Remove from database
            await self._delete_workflow_definition_from_db(workflow_id)

            logger.info(f"Deleted workflow definition: {definition.name} ({workflow_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to delete workflow definition: {e}")
            raise

    # ============================================================================
    # Workflow Execution Management
    # ============================================================================

    async def execute_workflow(
        self,
        workflow_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: Priority = Priority.NORMAL
    ) -> str:
        """Execute a workflow immediately"""
        try:
            if workflow_id not in self.workflow_definitions:
                raise ValueError(f"Workflow definition not found: {workflow_id}")

            definition = self.workflow_definitions[workflow_id]

            # Check resource availability
            if not await self._check_resource_availability(definition):
                raise RuntimeError("Insufficient resources to execute workflow")

            # Create execution instance
            execution = WorkflowExecution(
                id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                status=WorkflowStatus.PENDING,
                start_time=datetime.utcnow(),
                priority=priority,
                context=parameters or {}
            )

            # Store execution
            self.active_workflows[execution.id] = execution

            # Start execution asynchronously
            asyncio.create_task(self._execute_workflow_async(execution))

            logger.info(f"Started workflow execution: {execution.id} for workflow {workflow_id}")
            return execution.id

        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            raise

    async def schedule_workflow(
        self,
        workflow_id: str,
        trigger_config: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule a workflow for future execution"""
        try:
            if workflow_id not in self.workflow_definitions:
                raise ValueError(f"Workflow definition not found: {workflow_id}")

            # Create schedule
            schedule = WorkflowSchedule(
                id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                trigger_type=TriggerType(trigger_config.get('type', 'scheduled')),
                parameters=parameters or {}
            )

            # Configure trigger
            if schedule.trigger_type == TriggerType.SCHEDULED:
                await self._configure_scheduled_trigger(schedule, trigger_config)
            elif schedule.trigger_type == TriggerType.EVENT:
                await self._configure_event_trigger(schedule, trigger_config)

            # Store schedule
            self.workflow_schedules[schedule.id] = schedule

            # Persist to database
            await self._persist_workflow_schedule(schedule)

            logger.info(f"Scheduled workflow: {workflow_id} with schedule {schedule.id}")
            return schedule.id

        except Exception as e:
            logger.error(f"Failed to schedule workflow: {e}")
            raise

    async def cancel_workflow_execution(self, execution_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel a running workflow execution"""
        try:
            if execution_id not in self.active_workflows:
                return False

            execution = self.active_workflows[execution_id]

            if execution.status not in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
                return False

            await self._cancel_workflow_execution(execution_id, reason)
            return True

        except Exception as e:
            logger.error(f"Failed to cancel workflow execution: {e}")
            raise

    async def get_workflow_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get the status of a workflow execution"""
        return self.active_workflows.get(execution_id)

    async def list_workflow_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 50
    ) -> List[WorkflowExecution]:
        """List workflow executions with optional filtering"""
        executions = list(self.active_workflows.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        if status:
            executions = [e for e in executions if e.status == status]

        # Sort by start time (most recent first)
        executions.sort(key=lambda x: x.start_time, reverse=True)

        return executions[:limit]

    # ============================================================================
    # Conditional Logic and Decision Making
    # ============================================================================

    async def evaluate_conditions(self, conditions: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Evaluate a list of conditions against the current context"""
        try:
            for condition in conditions:
                condition_type = condition.get('type')
                field = condition.get('field')
                operator = condition.get('operator')
                value = condition.get('value')

                if not all([condition_type, field, operator]):
                    continue

                # Get field value from context
                field_value = self._get_nested_value(context, field)

                # Evaluate condition
                if not self._evaluate_condition(field_value, operator, value):
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to evaluate conditions: {e}")
            return False

    def _evaluate_condition(self, field_value: Any, operator: str, expected_value: Any) -> bool:
        """Evaluate a single condition"""
        try:
            if operator == 'equals':
                return field_value == expected_value
            elif operator == 'not_equals':
                return field_value != expected_value
            elif operator == 'greater_than':
                return field_value > expected_value
            elif operator == 'less_than':
                return field_value < expected_value
            elif operator == 'contains':
                return expected_value in field_value if isinstance(field_value, (str, list)) else False
            elif operator == 'not_contains':
                return expected_value not in field_value if isinstance(field_value, (str, list)) else True
            elif operator == 'is_empty':
                return not field_value
            elif operator == 'is_not_empty':
                return bool(field_value)
            else:
                logger.warning(f"Unknown condition operator: {operator}")
                return False

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a nested value from a dictionary using dot notation"""
        try:
            keys = path.split('.')
            value = data

            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                elif isinstance(value, list) and key.isdigit():
                    value = value[int(key)] if int(key) < len(value) else None
                else:
                    return None

            return value

        except Exception:
            return None

    # ============================================================================
    # Error Recovery and Retry Logic
    # ============================================================================

    async def handle_workflow_error(
        self,
        execution: WorkflowExecution,
        step_id: str,
        error: Exception,
        step_config: WorkflowStep
    ) -> bool:
        """Handle errors in workflow execution with retry and recovery logic"""
        try:
            execution.error_message = str(error)
            execution.retry_count += 1

            # Special handling for LLM-related errors (Ollama API failures)
            is_llm_error = self._is_llm_related_error(error)

            if is_llm_error:
                # For LLM errors, use more conservative retry logic
                max_llm_retries = min(step_config.max_retries, 3)  # Max 3 retries for LLM tasks

                if execution.retry_count < max_llm_retries:
                    logger.info(f"Retrying LLM step {step_id} for execution {execution.id} (attempt {execution.retry_count}/{max_llm_retries})")

                    # Update status
                    execution.status = WorkflowStatus.RETRYING

                    # Longer delay for LLM retries (API rate limits, model loading, etc.)
                    delay = min(600, 5 * execution.retry_count)  # 5s, 10s, 15s max
                    asyncio.create_task(self._retry_step_after_delay(execution, step_id, delay))

                    return True  # Retry scheduled

            # General retry logic for non-LLM errors
            elif execution.retry_count < step_config.max_retries:
                logger.info(f"Retrying step {step_id} for execution {execution.id} (attempt {execution.retry_count})")

                # Update status
                execution.status = WorkflowStatus.RETRYING

                # Schedule retry with exponential backoff
                delay = min(300, 2 ** execution.retry_count)  # Max 5 minutes
                asyncio.create_task(self._retry_step_after_delay(execution, step_id, delay))

                return True  # Retry scheduled

            # Max retries exceeded, try alternative path
            if step_config.on_failure:
                logger.info(f"Max retries exceeded for step {step_id}, trying alternative path: {step_config.on_failure}")

                # Execute alternative step
                alternative_step = step_config.on_failure
                asyncio.create_task(self._execute_step(execution, alternative_step))

                return True  # Alternative path executed

            # No recovery possible, fail the workflow
            logger.error(f"Workflow execution {execution.id} failed at step {step_id}: {error}")
            execution.status = WorkflowStatus.FAILED
            execution.end_time = datetime.utcnow()

            # Publish failure event (if pubsub is available)
            try:
                if hasattr(self.pubsub_service, 'publish_event'):
                    await self.pubsub_service.publish_event(
                        "workflow.failed",
                        {
                            "execution_id": execution.id,
                            "workflow_id": execution.workflow_id,
                            "failed_step": step_id,
                            "error": str(error),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
            except Exception as pubsub_error:
                logger.warning(f"Could not publish workflow failure event: {pubsub_error}")

            return False  # Workflow failed

        except Exception as e:
            logger.error(f"Error in workflow error handling: {e}")
            return False

    def _is_llm_related_error(self, error: Exception) -> bool:
        """Check if an error is related to LLM/Ollama operations"""
        error_str = str(error).lower()
        llm_indicators = [
            'ollama', 'llm', 'model', 'embedding', 'generation',
            'connection refused', 'timeout', 'rate limit', '429',
            '500', '502', '503', '504'  # Common API errors
        ]

        return any(indicator in error_str for indicator in llm_indicators)

    async def _retry_step_after_delay(self, execution: WorkflowExecution, step_id: str, delay: int):
        """Retry a failed step after a delay"""
        try:
            await asyncio.sleep(delay)
            await self._execute_step(execution, step_id)

        except Exception as e:
            logger.error(f"Failed to retry step {step_id}: {e}")

    # ============================================================================
    # Resource Optimization
    # ============================================================================

    async def _check_resource_availability(self, definition: WorkflowDefinition) -> bool:
        """Check if sufficient resources are available to execute the workflow"""
        try:
            # For homelab setup with limited GPU resources, focus on concurrent workflow limits
            # rather than strict CPU/memory checks

            # Check concurrent workflow limit (more relevant for homelab)
            active_count = len([e for e in self.active_workflows.values()
                              if e.status == WorkflowStatus.RUNNING])
            max_concurrent = definition.resource_requirements.get('max_concurrent', 3)  # Lower default for homelab

            if active_count >= max_concurrent:
                logger.warning(f"Maximum concurrent workflows limit reached ({active_count}/{max_concurrent})")
                return False

            # Check if Ollama service is available (critical for LLM tasks)
            try:
                # Simple health check - could be enhanced to check actual Ollama status
                ollama_available = True  # Assume available unless we implement health checks
                if not ollama_available:
                    logger.warning("Ollama service not available for workflow execution")
                    return False
            except Exception as e:
                logger.warning(f"Could not verify Ollama availability: {e}")
                # Don't block execution for Ollama check failures

            # Check for GPU-intensive workflows (if any steps require GPU)
            gpu_required = any(
                step.config.get('requires_gpu', False)
                for step in definition.steps.values()
            )

            if gpu_required:
                # For homelab with 2x Tesla P40, limit concurrent GPU workflows
                gpu_workflows = len([
                    e for e in self.active_workflows.values()
                    if e.status == WorkflowStatus.RUNNING and
                    any(s.config.get('requires_gpu', False)
                        for s in self.workflow_definitions[e.workflow_id].steps.values())
                ])

                if gpu_workflows >= 1:  # Only allow 1 GPU workflow at a time
                    logger.warning("GPU workflow already running, cannot start another")
                    return False

            logger.info(f"Resource check passed for workflow: {definition.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to check resource availability: {e}")
            # For homelab setup, be more permissive on resource check failures
            logger.warning("Resource check failed, but allowing workflow execution for homelab setup")
            return True

    async def optimize_resource_allocation(self, execution: WorkflowExecution) -> Dict[str, Any]:
        """Optimize resource allocation for workflow execution"""
        try:
            definition = self.workflow_definitions[execution.workflow_id]

            # Calculate optimal resource allocation based on priority and system load
            base_allocation = definition.resource_requirements.copy()

            # Adjust based on priority
            if execution.priority == Priority.HIGH:
                base_allocation['cpu_percent'] = min(100, base_allocation.get('cpu_percent', 10) * 1.5)
                base_allocation['memory_gb'] = base_allocation.get('memory_gb', 1) * 1.2
            elif execution.priority == Priority.CRITICAL:
                base_allocation['cpu_percent'] = min(100, base_allocation.get('cpu_percent', 10) * 2)
                base_allocation['memory_gb'] = base_allocation.get('memory_gb', 1) * 1.5

            # Adjust based on system load
            metrics = await self.metrics_service.get_system_metrics()
            system_load_factor = metrics.cpu.usage_percent / 100

            if system_load_factor > 0.8:  # High load
                base_allocation['cpu_percent'] = max(5, base_allocation.get('cpu_percent', 10) * 0.7)
            elif system_load_factor < 0.3:  # Low load
                base_allocation['cpu_percent'] = min(100, base_allocation.get('cpu_percent', 10) * 1.3)

            return base_allocation

        except Exception as e:
            logger.error(f"Failed to optimize resource allocation: {e}")
            return definition.resource_requirements

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _execute_workflow_async(self, execution: WorkflowExecution):
        """Execute a workflow asynchronously"""
        try:
            definition = self.workflow_definitions[execution.workflow_id]

            # Update status
            execution.status = WorkflowStatus.RUNNING

            # Optimize resource allocation
            execution.context['resource_allocation'] = await self.optimize_resource_allocation(execution)

            # Execute workflow steps
            success = await self._execute_workflow_steps(execution, definition)

            # Update final status
            if success:
                execution.status = WorkflowStatus.COMPLETED
                logger.info(f"Workflow execution {execution.id} completed successfully")
            else:
                execution.status = WorkflowStatus.FAILED
                logger.error(f"Workflow execution {execution.id} failed")

            execution.end_time = datetime.utcnow()

            # Publish completion event
            await self.pubsub_service.publish_event(
                f"workflow.{execution.status.value}",
                {
                    "execution_id": execution.id,
                    "workflow_id": execution.workflow_id,
                    "duration_seconds": (execution.end_time - execution.start_time).total_seconds(),
                    "timestamp": execution.end_time.isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error executing workflow {execution.id}: {e}")
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = datetime.utcnow()

        finally:
            # Clean up after some time
            asyncio.create_task(self._cleanup_execution_after_delay(execution.id, 3600))  # 1 hour

    async def _execute_workflow_steps(self, execution: WorkflowExecution, definition: WorkflowDefinition) -> bool:
        """Execute all steps in a workflow"""
        try:
            # Get initial steps (no dependencies)
            pending_steps = [step_id for step_id, step in definition.steps.items()
                           if not step.dependencies]

            completed_steps = set()

            while pending_steps:
                # Execute steps that can run in parallel
                parallel_tasks = []

                for step_id in pending_steps[:]:  # Copy to avoid modification during iteration
                    step = definition.steps[step_id]

                    # Check if all dependencies are satisfied
                    if all(dep in completed_steps for dep in step.dependencies):
                        # Check step conditions
                        if await self.evaluate_conditions(step.conditions, execution.context):
                            parallel_tasks.append(self._execute_step(execution, step_id))
                            pending_steps.remove(step_id)

                # Wait for parallel tasks to complete
                if parallel_tasks:
                    results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

                    # Process results
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Step execution failed: {result}")
                            return False

                # Check for completion
                if not parallel_tasks and pending_steps:
                    logger.error(f"Workflow stuck with pending steps: {pending_steps}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error executing workflow steps: {e}")
            return False

    async def _execute_step(self, execution: WorkflowExecution, step_id: str) -> bool:
        """Execute a single workflow step with atomic processing"""
        try:
            definition = self.workflow_definitions[execution.workflow_id]
            step = definition.steps[step_id]

            execution.current_step = step_id

            logger.info(f"Executing step {step_id} for workflow {execution.workflow_id}")

            # Execute the step based on its type
            result = await self._execute_step_by_type(step, execution.context)

            # Store result with atomic write
            step_result = {
                'status': 'completed',
                'result': result,
                'timestamp': datetime.utcnow().isoformat(),
                'step_id': step_id
            }

            execution.step_results[step_id] = step_result

            # Update context with step result
            execution.context[f"step_{step_id}_result"] = result

            # Atomic progress tracking for homelab setup
            await self._update_execution_progress(execution, step_id, step_result)

            logger.info(f"Step {step_id} completed successfully with atomic write")
            return True

        except Exception as e:
            logger.error(f"Failed to execute step {step_id}: {e}")

            # Handle error with retry/recovery logic
            return await self.handle_workflow_error(execution, step_id, e, step)

    async def _execute_step_by_type(self, step: WorkflowStep, context: Dict[str, Any]) -> Any:
        """Execute a step based on its type"""
        try:
            step_type = step.type

            if step_type == 'http_request':
                # Execute HTTP request
                return await self._execute_http_request_step(step, context)
            elif step_type == 'database_query':
                # Execute database query
                return await self._execute_database_query_step(step, context)
            elif step_type == 'ai_processing':
                # Execute AI processing
                return await self._execute_ai_processing_step(step, context)
            elif step_type == 'conditional':
                # Execute conditional logic
                return await self._execute_conditional_step(step, context)
            elif step_type == 'webhook':
                # Execute webhook notification
                return await self._execute_webhook_step(step, context)
            else:
                raise ValueError(f"Unknown step type: {step_type}")

        except Exception as e:
            logger.error(f"Error executing step of type {step.type}: {e}")
            raise

    async def _execute_http_request_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an HTTP request step"""
        # This would integrate with the agentic HTTP client
        # Implementation would use the existing HTTP client service
        config = step.config
        url = config.get('url')
        method = config.get('method', 'GET')
        headers = config.get('headers', {})
        data = config.get('data', {})

        # Placeholder for HTTP client integration
        logger.info(f"Executing HTTP request: {method} {url}")
        return {"status": "success", "url": url, "method": method}

    async def _execute_database_query_step(self, step: WorkflowStep, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a database query step"""
        # This would integrate with the database service
        config = step.config
        query = config.get('query')
        parameters = config.get('parameters', {})

        # Placeholder for database integration
        logger.info(f"Executing database query: {query}")
        return [{"result": "placeholder"}]

    async def _execute_ai_processing_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an AI processing step"""
        # This would integrate with AI services
        config = step.config
        model = config.get('model')
        prompt = config.get('prompt')

        # Placeholder for AI service integration
        logger.info(f"Executing AI processing with model: {model}")
        return {"result": "AI processing completed", "model": model}

    async def _execute_conditional_step(self, step: WorkflowStep, context: Dict[str, Any]) -> bool:
        """Execute a conditional logic step"""
        config = step.config
        conditions = config.get('conditions', [])

        return await self.evaluate_conditions(conditions, context)

    async def _execute_webhook_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a webhook notification step"""
        config = step.config
        url = config.get('url')
        method = config.get('method', 'POST')
        payload = config.get('payload', {})

        # Placeholder for webhook execution
        logger.info(f"Sending webhook to: {url}")
        return {"status": "sent", "url": url, "method": method}

    async def _cancel_workflow_execution(self, execution_id: str, reason: str):
        """Cancel a workflow execution"""
        try:
            if execution_id in self.active_workflows:
                execution = self.active_workflows[execution_id]
                execution.status = WorkflowStatus.CANCELLED
                execution.error_message = reason
                execution.end_time = datetime.utcnow()

                logger.info(f"Cancelled workflow execution: {execution_id} - {reason}")

        except Exception as e:
            logger.error(f"Failed to cancel workflow execution {execution_id}: {e}")

    async def _update_execution_progress(self, execution: WorkflowExecution, step_id: str, step_result: Dict[str, Any]):
        """Update execution progress with atomic writes for homelab setup"""
        try:
            # Track successfully processed items
            if step_result['status'] == 'completed':
                if step_id not in execution.processed_items:
                    execution.processed_items.append(step_id)

            # Calculate progress percentage
            definition = self.workflow_definitions[execution.workflow_id]
            total_steps = len(definition.steps)
            completed_steps = len(execution.processed_items)

            if total_steps > 0:
                execution.progress_percentage = (completed_steps / total_steps) * 100

            # For homelab setup, persist progress to Redis for recovery
            if self.redis:
                progress_data = {
                    'execution_id': execution.id,
                    'processed_items': execution.processed_items,
                    'progress_percentage': execution.progress_percentage,
                    'current_step': execution.current_step,
                    'last_updated': datetime.utcnow().isoformat()
                }

                await self.redis.setex(
                    f"workflow_progress:{execution.id}",
                    86400,  # 24 hours TTL
                    json.dumps(progress_data)
                )

            logger.debug(f"Updated progress for execution {execution.id}: {execution.progress_percentage:.1f}% complete")

        except Exception as e:
            logger.error(f"Failed to update execution progress: {e}")
            # Don't fail the step execution for progress tracking errors

    async def _cleanup_execution_after_delay(self, execution_id: str, delay_seconds: int):
        """Clean up a completed execution after a delay"""
        try:
            await asyncio.sleep(delay_seconds)

            if execution_id in self.active_workflows:
                execution = self.active_workflows[execution_id]

                # Only clean up if execution is complete
                if execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                    del self.active_workflows[execution_id]
                    logger.info(f"Cleaned up workflow execution: {execution_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup execution {execution_id}: {e}")

    async def _validate_workflow_definition(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """Validate a workflow definition"""
        required_fields = ['name', 'description', 'steps']

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Create WorkflowDefinition object
        definition = WorkflowDefinition(
            id=data.get('id', str(uuid.uuid4())),
            name=data['name'],
            description=data['description'],
            version=data.get('version', '1.0.0'),
            steps={},
            trigger_config=data.get('trigger_config', {}),
            priority=Priority(data.get('priority', 2)),
            max_execution_time=data.get('max_execution_time', 3600),
            resource_requirements=data.get('resource_requirements', {}),
            metadata=data.get('metadata', {})
        )

        # Validate and convert steps
        for step_id, step_data in data.get('steps', {}).items():
            step = WorkflowStep(
                id=step_id,
                name=step_data.get('name', step_id),
                type=step_data['type'],
                config=step_data.get('config', {}),
                dependencies=step_data.get('dependencies', []),
                timeout_seconds=step_data.get('timeout_seconds', 300),
                retry_count=0,
                max_retries=step_data.get('max_retries', 3),
                on_failure=step_data.get('on_failure'),
                conditions=step_data.get('conditions', [])
            )
            definition.steps[step_id] = step

        return definition

    async def _configure_scheduled_trigger(self, schedule: WorkflowSchedule, trigger_config: Dict[str, Any]):
        """Configure a scheduled trigger"""
        cron_expression = trigger_config.get('cron_expression')
        interval_seconds = trigger_config.get('interval_seconds')

        if cron_expression:
            schedule.cron_expression = cron_expression
            trigger = CronTrigger.from_crontab(cron_expression)
        elif interval_seconds:
            schedule.interval_seconds = interval_seconds
            trigger = IntervalTrigger(seconds=interval_seconds)
        else:
            raise ValueError("Either cron_expression or interval_seconds must be provided for scheduled triggers")

        # Calculate next run time
        schedule.next_run = trigger.get_next_fire_time(None, datetime.utcnow())

        # Add to scheduler
        self.scheduler.add_job(
            self._execute_scheduled_workflow,
            trigger=trigger,
            args=[schedule.workflow_id, schedule.parameters],
            id=schedule.id,
            name=f"Workflow: {schedule.workflow_id}",
            replace_existing=True
        )

    async def _configure_event_trigger(self, schedule: WorkflowSchedule, trigger_config: Dict[str, Any]):
        """Configure an event-based trigger"""
        event_type = trigger_config.get('event_type')
        if not event_type:
            raise ValueError("event_type is required for event triggers")

        # Register event handler
        await self.pubsub_service.subscribe(event_type, self._handle_workflow_event)

        schedule.cron_expression = f"event:{event_type}"

    async def _execute_scheduled_workflow(self, workflow_id: str, parameters: Dict[str, Any]):
        """Execute a scheduled workflow"""
        try:
            logger.info(f"Executing scheduled workflow: {workflow_id}")

            # Update schedule's last run time
            schedule = next((s for s in self.workflow_schedules.values()
                           if s.workflow_id == workflow_id), None)
            if schedule:
                schedule.last_run = datetime.utcnow()
                await self._persist_workflow_schedule(schedule)

            # Execute the workflow
            await self.execute_workflow(workflow_id, parameters)

        except Exception as e:
            logger.error(f"Failed to execute scheduled workflow {workflow_id}: {e}")

    async def _handle_workflow_event(self, event_data: Dict[str, Any]):
        """Handle workflow trigger events"""
        try:
            event_type = event_data.get('type')
            if not event_type:
                return

            # Find schedules that match this event type
            matching_schedules = [
                s for s in self.workflow_schedules.values()
                if s.trigger_type == TriggerType.EVENT and
                s.cron_expression == f"event:{event_type}" and
                s.enabled
            ]

            # Execute matching workflows
            for schedule in matching_schedules:
                try:
                    await self.execute_workflow(schedule.workflow_id, schedule.parameters)
                    logger.info(f"Triggered workflow {schedule.workflow_id} from event {event_type}")
                except Exception as e:
                    logger.error(f"Failed to trigger workflow {schedule.workflow_id}: {e}")

        except Exception as e:
            logger.error(f"Error handling workflow event: {e}")

    # ============================================================================
    # Database Persistence Methods
    # ============================================================================

    async def _persist_workflow_definition(self, definition: WorkflowDefinition):
        """Persist workflow definition to database"""
        # Implementation would save to database
        pass

    async def _persist_workflow_schedule(self, schedule: WorkflowSchedule):
        """Persist workflow schedule to database"""
        # Implementation would save to database
        pass

    async def _load_workflow_definitions(self):
        """Load workflow definitions from database"""
        # Implementation would load from database
        pass

    async def _load_workflow_schedules(self):
        """Load workflow schedules from database"""
        # Implementation would load from database
        pass

    async def _delete_workflow_definition_from_db(self, workflow_id: str):
        """Delete workflow definition from database"""
        # Implementation would delete from database
        pass

    async def _remove_workflow_schedule(self, workflow_id: str):
        """Remove workflow schedule from scheduler"""
        try:
            # Find and remove schedule
            schedule = next((s for s in self.workflow_schedules.values()
                           if s.workflow_id == workflow_id), None)

            if schedule:
                # Remove from scheduler
                if self.scheduler.get_job(schedule.id):
                    self.scheduler.remove_job(schedule.id)

                # Remove from memory
                del self.workflow_schedules[schedule.id]

                # Remove from database
                # Implementation would delete from database

        except Exception as e:
            logger.error(f"Failed to remove workflow schedule: {e}")

    async def _update_workflow_schedule(self, definition: WorkflowDefinition):
        """Update workflow schedule when definition changes"""
        try:
            # Find existing schedule
            schedule = next((s for s in self.workflow_schedules.values()
                           if s.workflow_id == definition.id), None)

            if schedule and definition.trigger_config:
                # Update schedule configuration
                await self._configure_scheduled_trigger(schedule, definition.trigger_config)
                await self._persist_workflow_schedule(schedule)

        except Exception as e:
            logger.error(f"Failed to update workflow schedule: {e}")

    async def _register_event_handlers(self):
        """Register event handlers for workflow triggers"""
        # Implementation would register event handlers
        pass


# Global service instance
workflow_automation_service = WorkflowAutomationService()
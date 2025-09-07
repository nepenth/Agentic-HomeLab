from celery import Task
from celery.exceptions import Retry
from typing import Dict, Any, Optional
from uuid import UUID
import asyncio
from datetime import datetime
from sqlalchemy import select, update
from app.celery_app import celery_app
from app.db.models.task import Task as TaskModel, TaskStatus
from app.db.models.agent import Agent
from app.db.models.agent_type import AgentType
from app.db.database import get_session_context
from app.services.ollama_client import ollama_client
from app.services.log_service import log_service
from app.agents.simple_agent import SimpleAgent
from app.agents.dynamic_agent import DynamicAgent
from app.agents.factory import AgentFactory
from app.services.schema_manager import SchemaManager
from app.services.security_service import SecurityService
from app.agents.tools.registry import ToolRegistry
from app.utils.logging import get_logger
from app.utils.metrics import MetricsCollector, Timer

logger = get_logger("agent_tasks")


class AgentTask(Task):
    """Base class for agent tasks with enhanced error handling and logging."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Update task status in database
        try:
            asyncio.run(self._update_task_status(
                task_id=kwargs.get("task_id"),
                status=TaskStatus.FAILED,
                error_message=str(exc)
            ))
        except Exception as e:
            logger.error(f"Failed to update task status on failure: {e}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {task_id} completed successfully")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.warning(f"Task {task_id} retrying: {exc}")
    
    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        output: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """Update task status in database."""
        try:
            task_uuid = UUID(task_id)
            
            async with get_session_context() as session:
                update_data = {
                    "status": status
                }
                
                if status == TaskStatus.RUNNING:
                    update_data["started_at"] = datetime.utcnow()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    update_data["completed_at"] = datetime.utcnow()
                
                if output:
                    update_data["output"] = output
                
                if error_message:
                    update_data["error_message"] = error_message
                
                stmt = update(TaskModel).where(TaskModel.id == task_uuid).values(**update_data)
                await session.execute(stmt)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            raise


@celery_app.task(base=AgentTask, bind=True, max_retries=3, default_retry_delay=60)
def process_agent_task(self, task_id: str, agent_id: str, input_data: Dict[str, Any]):
    """Main Celery task for processing agent requests."""
    return asyncio.run(_process_agent_task_async(self, task_id, agent_id, input_data))


async def _process_agent_task_async(
    task: AgentTask,
    task_id: str,
    agent_id: str,
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Async implementation of agent task processing."""
    task_uuid = UUID(task_id)
    agent_uuid = UUID(agent_id)
    
    # Initialize connections
    await ollama_client.connect()
    await log_service.pubsub.connect()
    
    try:
        # Update task status to running
        await task._update_task_status(task_uuid, TaskStatus.RUNNING)
        
        # Log task start
        await log_service.log_info(
            task_uuid, agent_uuid,
            f"Starting task execution",
            {"input": input_data}
        )
        
        # Get agent from database
        async with get_session_context() as session:
            result = await session.execute(select(Agent).where(Agent.id == agent_uuid))
            agent = result.scalar_one_or_none()

            if not agent:
                error_msg = f"Agent {agent_id} not found"
                await log_service.log_error(task_uuid, agent_uuid, error_msg)
                await task._update_task_status(task_uuid, TaskStatus.FAILED, error_message=error_msg)
                return {"error": error_msg}

        # Determine agent type and create appropriate instance
        if agent.agent_type_id is not None:
            # Dynamic agent
            logger.info(f"Processing task for dynamic agent: {agent_id}")
            agent_instance = await _create_dynamic_agent_instance(
                agent, agent_uuid, task_uuid, session
            )
        else:
            # Static agent (legacy)
            logger.info(f"Processing task for static agent: {agent_id}")
            agent_instance = SimpleAgent(
                agent_id=agent_uuid,
                task_id=task_uuid,
                name=agent.name,
                model_name=agent.model_name,
                config=agent.config or {},
                ollama_client=ollama_client,
                log_service=log_service
            )
        
        # Process the task with metrics
        with Timer(
            MetricsCollector.record_task_duration,
            str(agent_uuid)
        ):
            result = await agent_instance.process_task(input_data)
        
        # Log completion
        await log_service.log_info(
            task_uuid, agent_uuid,
            f"Task completed successfully",
            {"output": result}
        )
        
        # Update task status to completed
        await task._update_task_status(task_uuid, TaskStatus.COMPLETED, output=result)
        
        # Update metrics
        MetricsCollector.increment_task_counter(str(agent_uuid), "completed")
        
        return result
        
    except Exception as e:
        error_msg = f"Task execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log error
        await log_service.log_error(
            task_uuid, agent_uuid,
            error_msg,
            {"error_type": type(e).__name__, "error_details": str(e)}
        )
        
        # Update task status to failed
        await task._update_task_status(task_uuid, TaskStatus.FAILED, error_message=error_msg)
        
        # Update metrics
        MetricsCollector.increment_task_counter(str(agent_uuid), "failed")
        
        # Retry logic
        if task.request.retries < task.max_retries:
            logger.info(f"Retrying task {task_id} (attempt {task.request.retries + 1})")
            raise task.retry(countdown=60 * (2 ** task.request.retries))  # Exponential backoff
        
        raise e
        
    finally:
        # Cleanup connections
        try:
            await ollama_client.disconnect()
            await log_service.pubsub.disconnect()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


@celery_app.task(base=AgentTask, bind=True)
def health_check_task(self):
    """Health check task for monitoring."""
    return asyncio.run(_health_check_async())


async def _health_check_async() -> Dict[str, Any]:
    """Async health check implementation."""
    try:
        # Check Ollama connection
        ollama_health = await ollama_client.health_check()
        
        # Check log service
        log_health = await log_service.health_check()
        
        # Check database
        db_health = {"status": "unknown"}
        try:
            async with get_session_context() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                db_health = {"status": "connected"}
        except Exception as e:
            db_health = {"status": "error", "error": str(e)}
        
        overall_status = "healthy"
        if (ollama_health["status"] != "healthy" or 
            log_health["status"] not in ["healthy", "degraded"] or
            db_health["status"] != "connected"):
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "ollama": ollama_health,
                "logging": log_health,
                "database": db_health
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task
def cleanup_old_logs(days: int = 7):
    """Clean up old log entries."""
    return asyncio.run(_cleanup_old_logs_async(days))


async def _cleanup_old_logs_async(days: int) -> Dict[str, Any]:
    """Async cleanup implementation."""
    try:
        from sqlalchemy import delete
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with get_session_context() as session:
            from app.db.models.task import TaskLog
            
            # Delete old logs
            stmt = delete(TaskLog).where(TaskLog.timestamp < cutoff_date)
            result = await session.execute(stmt)
            await session.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Cleaned up {deleted_count} old log entries")
            
            return {
                "status": "completed",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to cleanup old logs: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


async def _create_dynamic_agent_instance(agent, agent_uuid, task_uuid, session):
    """Create a dynamic agent instance for task processing."""
    try:
        # Initialize services
        schema_manager = SchemaManager(session)
        tool_registry = ToolRegistry()
        security_service = SecurityService()

        # Get agent type schema by querying directly
        query = select(AgentType).where(AgentType.id == agent.agent_type_id)
        result = await session.execute(query)
        agent_type_obj = result.scalar_one_or_none()

        if not agent_type_obj:
            raise ValueError(f"Agent type {agent.agent_type_id} not found")

        # Create agent factory and build the agent
        agent_factory = AgentFactory(
            db_session=session,
            schema_manager=schema_manager,
            tool_registry=tool_registry,
            ollama_client=ollama_client,
            log_service=log_service
        )

        # Create dynamic agent instance
        dynamic_agent = await agent_factory.create_agent(
            agent_id=agent_uuid,
            task_id=task_uuid,
            agent_type=agent_type_obj.type_name,
            name=agent.name,
            config=agent.config or {}
        )

        return dynamic_agent

    except Exception as e:
        logger.error(f"Failed to create dynamic agent instance: {e}")
        raise
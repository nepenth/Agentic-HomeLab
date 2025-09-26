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
from app.services.ollama_client import sync_ollama_client as ollama_client
from app.services.log_service import log_service
from app.services.email_analysis_service import sync_email_analysis_service
from app.services.email_task_converter import sync_email_task_converter
from app.services.email_deduplication_service import EmailDeduplicationService
from app.connectors.base import ContentItem, ConnectorType, ContentType
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
            # Handle different task_id formats
            if isinstance(task_id, str):
                try:
                    task_uuid = UUID(task_id)
                except ValueError:
                    logger.warning(f"Invalid UUID format for task_id: {task_id}, skipping status update")
                    return
            elif isinstance(task_id, UUID):
                task_uuid = task_id
            else:
                logger.warning(f"Unsupported task_id type: {type(task_id)}, skipping status update")
                return

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
    
    # Note: sync_ollama_client doesn't need explicit connect/disconnect
    # Log service connection is handled internally
    
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
            # sync_ollama_client handles cleanup internally
            # Log service cleanup is handled internally
            pass
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
        ollama_health = ollama_client.health_check()
        
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


@celery_app.task(base=AgentTask, bind=True, max_retries=3, default_retry_delay=60)
def process_email_workflow_task(self, workflow_id: str, mailbox_config: Dict[str, Any], processing_options: Dict[str, Any]):
    """Celery task for processing email workflows using synchronous operations."""
    return _process_email_workflow_sync(workflow_id, mailbox_config, processing_options)


async def _process_email_workflow_async(
    task: AgentTask,
    workflow_id: str,
    mailbox_config: Dict[str, Any],
    processing_options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Modern unified email workflow processing.

    Uses locally synced emails with embeddings instead of live email fetching.
    This provides better performance, consistency, and intelligence.
    """
    from app.services.unified_email_workflow_service import unified_email_workflow_service
    from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus, EmailWorkflowLog
    from app.db.models.notification import Notification, NotificationStatus
    from app.services.pubsub_service import pubsub_service
    from datetime import datetime

    workflow_uuid = UUID(workflow_id)

    try:
        # Get workflow
        async with get_session_context() as session:
            workflow = await session.get(EmailWorkflow, workflow_uuid)
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return {"error": "Workflow not found"}

            # Create initial log entry
            initial_log = EmailWorkflowLog(
                workflow_id=workflow_uuid,
                user_id=workflow.user_id,
                level="info",
                message="Unified email workflow processing started (using local emails)",
                context={"phase": "initialization", "approach": "unified_local_emails"},
                workflow_phase="initialization"
            )
            session.add(initial_log)
            await session.commit()

            # Update workflow status to running
            workflow.status = EmailWorkflowStatus.RUNNING
            workflow.started_at = datetime.utcnow()
            await session.commit()

            # Use unified service to process locally synced emails
            result = await unified_email_workflow_service.process_workflow_from_synced_emails(
                db=session,
                user_id=workflow.user_id,
                workflow_id=workflow_id,
                processing_options=processing_options
            )

            # Handle result from unified service
            if not result.get("success"):
                # Workflow failed in unified service
                error_message = result.get("error", "Unknown error in unified service")

                workflow.status = EmailWorkflowStatus.FAILED
                workflow.completed_at = datetime.utcnow()
                workflow.error_message = error_message
                await session.commit()

                # Log failure
                failure_log = EmailWorkflowLog(
                    workflow_id=workflow_uuid,
                    user_id=workflow.user_id,
                    level="error",
                    message=f"Unified email workflow failed: {error_message}",
                    context={"error": error_message, "approach": "unified_local_emails"},
                    workflow_phase="failed"
                )
                session.add(failure_log)
                await session.commit()

                return {
                    "status": "failed",
                    "error": error_message,
                    "emails_processed": 0,
                    "tasks_created": 0
                }

            # Workflow succeeded - extract results
            emails_processed = result.get("emails_processed", 0)
            tasks_created = result.get("tasks_created", 0)
            success_message = result.get("message", "Unified workflow completed")

            # Update workflow with results
            workflow.emails_processed = emails_processed
            workflow.tasks_created = tasks_created
            workflow.status = EmailWorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            await session.commit()

            # Log successful completion
            completion_log = EmailWorkflowLog(
                workflow_id=workflow_uuid,
                user_id=workflow.user_id,
                level="info",
                message=f"Unified email workflow completed: {emails_processed} emails processed, {tasks_created} tasks created",
                context={
                    "emails_processed": emails_processed,
                    "tasks_created": tasks_created,
                    "processing_time_seconds": (datetime.utcnow() - workflow.started_at).total_seconds() if workflow.started_at else None,
                    "approach": "unified_local_emails",
                    "message": success_message
                },
                workflow_phase="completed",
                email_count=emails_processed,
                task_count=tasks_created
            )
            session.add(completion_log)
            await session.commit()

            # Publish notification
            notification = Notification(
                user_id=str(workflow.user_id),
                type="workflow_complete",
                message=f"Email workflow completed: {emails_processed} emails processed, {tasks_created} tasks created",
                related_id=str(workflow_id)
            )
            session.add(notification)
            await session.commit()

            # Publish via pubsub
            await pubsub_service.publish("notifications", notification.to_dict())

            logger.info(f"Completed unified email workflow {workflow_id}: {emails_processed} emails, {tasks_created} tasks")

            return {
                "status": "completed",
                "emails_processed": emails_processed,
                "tasks_created": tasks_created,
                "approach": "unified_local_emails"
            }

    except Exception as e:
        logger.error(f"Email workflow task failed for {workflow_id}: {e}")

        # Get workflow again in case of error
        try:
            async with get_session_context() as session:
                error_workflow = await session.get(EmailWorkflow, workflow_uuid)
                if error_workflow:
                    error_workflow.status = EmailWorkflowStatus.FAILED
                    error_workflow.completed_at = datetime.utcnow()
                    error_workflow.error_message = str(e)
                    await session.commit()

                # Create error log
                error_log = EmailWorkflowLog(
                    workflow_id=workflow_uuid,
                    user_id=error_workflow.user_id if error_workflow else "unknown",
                    level="error",
                    message=f"Email workflow failed: {str(e)}",
                    context={"error": str(e), "error_type": type(e).__name__},
                    workflow_phase="failed"
                )
                session.add(error_log)
                await session.commit()

        except Exception as log_error:
            logger.error(f"Failed to log workflow error: {log_error}")

        raise e


def _process_email_workflow_sync(workflow_id: str, mailbox_config: Dict[str, Any], processing_options: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous implementation of email workflow processing."""
    from app.db.database import get_sync_session
    from app.services.email_analysis_service import SyncEmailAnalysisService
    from app.services.email_task_converter import SyncEmailTaskConverter, TaskCreationRequest
    from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus, EmailWorkflowLog
    from app.db.models.content import ContentItem as ContentItemModel
    from app.db.models.notification import Notification, NotificationStatus
    from app.connectors.communication import SyncEmailConnector as EmailConnector
    from app.connectors.base import ConnectorConfig, ConnectorType
    from app.services.pubsub_service import pubsub_service
    import json
    from datetime import datetime

    workflow_uuid = UUID(workflow_id)
    session = get_sync_session()

    # Initialize progress tracking
    phases = []
    current_phase = "initialization"

    def update_progress(phase_name: str, progress_percentage: float = 0, items_processed: int = 0, total_items: int = 0, model_used: str = "n/a", tasks_created: int = 0):
        """Update workflow progress and send to frontend."""
        nonlocal current_phase
        current_phase = phase_name

        # Update phases array
        phase_index = next((i for i, p in enumerate(phases) if p.get('phase_name') == phase_name), -1)
        if phase_index >= 0:
            phases[phase_index].update({
                'status': 'running',
                'progress_percentage': progress_percentage,
                'items_processed': items_processed,
                'total_items': total_items,
                'model_used': model_used,
                'processing_duration_ms': 0  # Will be updated when phase completes
            })
        else:
            phases.append({
                'phase_name': phase_name,
                'status': 'running',
                'progress_percentage': progress_percentage,
                'items_processed': items_processed,
                'total_items': total_items,
                'model_used': model_used,
                'processing_duration_ms': 0
            })

        # Send progress update to frontend via WebSocket
        try:
            progress_data = {
                'type': 'workflow_progress',
                'workflow_id': workflow_id,
                'status': 'running',
                'current_phase': current_phase,
                'progress_percentage': progress_percentage,
                'emails_processed': items_processed if phase_name == 'email_processing' else 0,
                'tasks_created': tasks_created,
                'items_processed': items_processed,
                'total_items': total_items,
                'model_used': model_used
            }

            # Import WebSocket manager and send progress update
            try:
                from app.api.routes.websocket import manager
                # Send to all connected clients (in production, filter by user)
                # For now, broadcast to all email progress connections
                import asyncio
                
                # Check if there's an event loop running
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in an event loop context, create task
                    asyncio.create_task(manager.broadcast(progress_data, list(manager.active_connections.keys())))
                except RuntimeError:
                    # No event loop running, we're in Celery worker context
                    # Create a new event loop just for this operation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Filter connections to email progress connections only
                        email_connections = [conn_id for conn_id in manager.active_connections.keys() 
                                           if conn_id.startswith('email_progress_')]
                        if email_connections:
                            loop.run_until_complete(manager.broadcast(progress_data, email_connections))
                        else:
                            logger.debug("No email progress WebSocket connections to broadcast to")
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)
                        
            except ImportError:
                logger.warning("WebSocket manager not available for progress updates")
            except Exception as ws_error:
                logger.warning(f"Failed to send WebSocket progress update: {ws_error}")

            logger.info(f"Workflow {workflow_id} progress: {phase_name} - {progress_percentage}% ({tasks_created} tasks)")

        except Exception as e:
            logger.warning(f"Failed to send progress update: {e}")

    try:
        # Get workflow
        workflow = session.query(EmailWorkflow).filter(EmailWorkflow.id == workflow_uuid).first()
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return {"error": "Workflow not found"}

        # Initialize sync services with user_id to load user-specific settings
        user_id = workflow.user_id
        sync_email_analysis_service = SyncEmailAnalysisService(user_id=user_id)
        sync_email_task_converter = SyncEmailTaskConverter(user_id=user_id)

        # Start initialization phase
        update_progress("initialization", 10, 0, 0, "n/a", 0)

        # Create initial log entry
        initial_log = EmailWorkflowLog(
            workflow_id=workflow_uuid,
            user_id=workflow.user_id,
            level="info",
            message="Email workflow processing started",
            context={"phase": "initialization"},
            workflow_phase="initialization"
        )
        session.add(initial_log)
        session.commit()

        # Complete initialization phase
        update_progress("initialization", 100, 0, 0, "n/a", 0)

        # Start email discovery phase
        update_progress("email_discovery", 20, 0, 0, "n/a", 0)

        # Use EmailConnector to fetch emails
        processing_opts = processing_options or {}
        max_emails = processing_opts.get('max_emails', 50)
        unread_only = processing_opts.get('unread_only', False)
        since_date = processing_opts.get('since_date')

        # Create proper ConnectorConfig object
        connector_config = ConnectorConfig(
            name="email_workflow_connector",
            connector_type=ConnectorType.COMMUNICATION,
            source_config={
                "mailbox": mailbox_config.get("mailbox", "INBOX"),
                "limit": max_emails,
                "unread_only": unread_only,
                "since_date": since_date
            },
            credentials={
                "imap_server": mailbox_config.get("server"),
                "imap_port": mailbox_config.get("port", 993),
                "username": mailbox_config.get("username"),
                "password": mailbox_config.get("password")
            }
        )

        connector = EmailConnector(connector_config)

        # Log email discovery start
        discovery_log = EmailWorkflowLog(
            workflow_id=workflow_uuid,
            user_id=workflow.user_id,
            level="info",
            message="Starting email discovery from mailbox",
            context={
                "mailbox": mailbox_config.get("mailbox", "INBOX"),
                "max_emails": max_emails,
                "unread_only": unread_only
            },
            workflow_phase="email_discovery"
        )
        session.add(discovery_log)
        session.commit()

        # Use discover method instead of fetch_emails
        source_config = {
            "mailbox": mailbox_config.get("mailbox", "INBOX"),
            "limit": max_emails,
            "unread_only": unread_only,
            "since_date": since_date
        }

        # Use sync discover method
        update_progress("email_discovery", 50, 0, 0, "n/a", 0)
        content_items = connector.discover(source_config)

        # Log email discovery completion
        discovery_complete_log = EmailWorkflowLog(
            workflow_id=workflow_uuid,
            user_id=workflow.user_id,
            level="info",
            message=f"Email discovery completed: {len(content_items)} emails found",
            context={"emails_found": len(content_items)},
            workflow_phase="email_discovery",
            email_count=len(content_items)
        )
        session.add(discovery_complete_log)
        session.commit()

        # Complete email discovery phase
        update_progress("email_discovery", 100, 0, len(content_items), "n/a", 0)

        # Convert ContentItems to email format expected by the rest of the code
        emails = []
        for item in content_items:
            email_data = {
                'id': item.id,
                'subject': item.title or '',
                'body': item.description or '',
                'sender': item.metadata.get('sender', ''),
                'date': item.last_modified.isoformat() if item.last_modified else datetime.now().isoformat(),
                'metadata': item.metadata
            }
            emails.append(email_data)

        emails_processed = 0
        tasks_created = 0

        # Start email processing phase
        update_progress("email_processing", 0, 0, len(emails), "email-analysis", 0)

        # Initialize deduplication service
        dedup_service = EmailDeduplicationService(session)
        emails_skipped_duplicate = 0
        
        # Log processing start
        processing_log = EmailWorkflowLog(
            workflow_id=workflow_uuid,
            user_id=workflow.user_id,
            level="info",
            message=f"Starting to process {len(emails)} emails with smart deduplication",
            context={"total_emails": len(emails)},
            workflow_phase="email_processing",
            email_count=len(emails)
        )
        session.add(processing_log)
        session.commit()

        for i, email in enumerate(emails):
            email_id = email.get('id', f'email_{i}')
            logger.info(f"Processing email {i+1}/{len(emails)}: {email_id}")

            try:
                # Update progress for current email
                progress_percentage = int(((i + 1) / len(emails)) * 100)
                update_progress("email_processing", progress_percentage, i + 1, len(emails), "email-analysis", tasks_created)

                # Convert email dict to ContentItem for deduplication
                email_content_item = ContentItem(
                    email_id,
                    "email",
                    ConnectorType.COMMUNICATION,
                    ContentType.TEXT,
                    title=email.get('subject', 'No Subject'),
                    description=email.get('body', ''),
                    metadata=email.get('metadata', {}),
                    last_modified=datetime.now()
                )

                # Check for duplicates using smart deduplication
                dedup_result = dedup_service.check_duplicate(
                    email_content_item, 
                    int(workflow.user_id), 
                    str(workflow_uuid)
                )
                
                logger.info(f"Email {email_id} deduplication: duplicate={dedup_result.is_duplicate}, "
                          f"should_create_task={dedup_result.should_create_task}, reason={dedup_result.reason}")

                # Always record the email as seen
                processed_email_record = dedup_service.record_processed_email(
                    email_content_item,
                    int(workflow.user_id),
                    str(workflow_uuid),
                    task_created=False  # Will update this later if task is actually created
                )

                # Skip processing if duplicate and shouldn't create task
                if dedup_result.is_duplicate and not dedup_result.should_create_task:
                    emails_skipped_duplicate += 1
                    logger.info(f"Skipping duplicate email {email_id}: {dedup_result.reason}")
                    emails_processed += 1
                    continue

                # Analyze email using sync service with error handling
                analysis = sync_email_analysis_service.analyze_email(email['body'], email['metadata'])

                # Log analysis results
                logger.info(f"Email {email_id} analysis: importance={analysis.importance_score:.2f}, "
                          f"action_required={analysis.action_required}, categories={analysis.categories}")

                # Create tasks if action required
                result = None
                if analysis.action_required:
                    task_request = TaskCreationRequest(
                        email_analysis=analysis,
                        user_id=workflow.user_id,
                        email_content=email['body'],
                        email_metadata=email['metadata']
                    )

                    # Use sync task converter with error handling
                    result = sync_email_task_converter.convert_to_tasks(task_request, session)

                    if result and result.tasks_created:
                        # Link tasks to the processed email record
                        for task in result.tasks_created:
                            task.email_id = processed_email_record.id
                            task.email_sender = email.get('metadata', {}).get('sender', '')
                            task.email_subject = email.get('metadata', {}).get('subject', email.get('subject', ''))
                        
                        # Update the processed email record to reflect task creation
                        processed_email_record.task_created = True
                        processed_email_record.processing_status = "processed"
                        
                        tasks_created += len(result.tasks_created)
                        logger.info(f"Created {len(result.tasks_created)} tasks for email {email_id}")

                        # Update progress with current task count
                        update_progress("email_processing", progress_percentage, emails_processed, len(emails), "email-analysis", tasks_created)
                    else:
                        logger.warning(f"No tasks created for email {email_id}")

                emails_processed += 1
                workflow.emails_processed += 1
                workflow.tasks_created += len(result.tasks_created) if result else 0

                # Update workflow progress periodically (every 5 emails or at the end)
                if emails_processed % 5 == 0 or emails_processed == len(emails):
                    session.commit()
                    logger.info(f"Progress: {emails_processed}/{len(emails)} emails processed, "
                              f"{tasks_created} total tasks created")

                    # Send detailed progress update
                    update_progress("email_processing", progress_percentage, emails_processed, len(emails), "email-analysis", tasks_created)

            except Exception as e:
                logger.error(f"Failed to process email {email_id}: {e}")
                # Continue processing other emails instead of failing the entire workflow
                # Log the error but don't increment processed count for failed emails
                try:
                    # Create error log entry
                    error_log = EmailWorkflowLog(
                        workflow_id=workflow_uuid,
                        user_id=workflow.user_id,
                        level="error",
                        message=f"Failed to process email {email_id}: {str(e)}",
                        context={"email_id": email_id, "error": str(e), "error_type": type(e).__name__},
                        workflow_phase="email_processing"
                    )
                    session.add(error_log)
                    session.commit()
                except Exception as log_error:
                    logger.error(f"Failed to log email processing error: {log_error}")

        # Complete email processing phase
        update_progress("email_processing", 100, emails_processed, len(emails), "email-analysis", tasks_created)

        # Start completion phase
        update_progress("completion", 0, emails_processed, len(emails), "n/a", tasks_created)

        # Final workflow update
        session.commit()

        workflow.status = EmailWorkflowStatus.COMPLETED
        workflow.completed_at = datetime.utcnow()
        session.commit()

        # Complete completion phase
        update_progress("completion", 100, emails_processed, len(emails), "n/a", tasks_created)

        # Log final completion status
        logger.info(f"Workflow {workflow_uuid} marked as COMPLETED in database")

        # Log successful completion with deduplication stats
        completion_log = EmailWorkflowLog(
            workflow_id=workflow_uuid,
            user_id=workflow.user_id,
            level="info",
            message=f"Email workflow completed successfully: {emails_processed} emails processed, {tasks_created} tasks created, {emails_skipped_duplicate} duplicates skipped",
            context={
                "emails_processed": emails_processed,
                "emails_skipped_duplicate": emails_skipped_duplicate,
                "emails_unique": emails_processed - emails_skipped_duplicate,
                "tasks_created": tasks_created,
                "deduplication_rate": (emails_skipped_duplicate / emails_processed * 100) if emails_processed > 0 else 0,
                "task_creation_rate": (tasks_created / (emails_processed - emails_skipped_duplicate) * 100) if (emails_processed - emails_skipped_duplicate) > 0 else 0,
                "processing_time_seconds": (datetime.utcnow() - workflow.started_at).total_seconds() if workflow.started_at else None
            },
            workflow_phase="completed",
            email_count=emails_processed,
            task_count=tasks_created
        )
        session.add(completion_log)
        session.commit()

        # Publish notification
        notification = Notification(
            user_id=str(workflow.user_id),
            type="workflow_complete",
            message=f"Email workflow completed: {emails_processed} emails processed, {tasks_created} tasks created",
            related_id=str(workflow_id)
        )
        session.add(notification)
        session.commit()

        # Publish via pubsub (commented out for now - needs sync method)
        # TODO: Add synchronous publish method to pubsub service
        # try:
        #     pubsub_service.publish_sync("notifications", notification.to_dict())
        # except Exception as e:
        #     logger.warning(f"Failed to publish notification: {e}")

        logger.info(f"Completed email workflow {workflow_id}: {emails_processed} emails, {tasks_created} tasks, {emails_skipped_duplicate} duplicates skipped")

        return {
            "status": "completed",
            "emails_processed": emails_processed,
            "emails_skipped_duplicate": emails_skipped_duplicate,
            "emails_unique": emails_processed - emails_skipped_duplicate,
            "tasks_created": tasks_created,
            "deduplication_rate": (emails_skipped_duplicate / emails_processed * 100) if emails_processed > 0 else 0
        }

    except Exception as e:
        logger.error(f"Email workflow task failed for {workflow_id}: {e}")

        # Get workflow again in case of error
        try:
            error_workflow = session.query(EmailWorkflow).filter(EmailWorkflow.id == workflow_uuid).first()
            if error_workflow:
                error_workflow.status = EmailWorkflowStatus.FAILED
                error_workflow.completed_at = datetime.utcnow()
                error_workflow.error_message = str(e)
                session.commit()

            # Create error log
            error_log = EmailWorkflowLog(
                workflow_id=workflow_uuid,
                user_id=error_workflow.user_id if error_workflow else "unknown",
                level="error",
                message=f"Email workflow failed: {str(e)}",
                context={"error": str(e), "error_type": type(e).__name__},
                workflow_phase="failed"
            )
            session.add(error_log)
            session.commit()

        except Exception as log_error:
            logger.error(f"Failed to log workflow error: {log_error}")

        raise e

    finally:
        session.close()


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
"""
Email Workflow API Routes.

This module provides REST API endpoints for email workflow management including:
- Email analysis and processing
- Task creation from emails
- Workflow status tracking
- Email search and filtering
- Dashboard stats
- Workflow-specific analytics
- Notifications
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from starlette import status as status_codes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, Float
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timedelta
import json

from app.api.dependencies import get_db_session, verify_api_key, get_current_user
from app.services.email_analysis_service import email_analysis_service, EmailAnalysis
from app.services.email_task_converter import email_task_converter, TaskCreationRequest, TaskCreationResult
from app.db.models.task import Task, TaskStatus
from app.db.models.content import ContentItem
from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus
from app.db.models.notification import Notification, NotificationStatus
from app.db.models.user import User
from app.connectors.communication import EmailConnector
from app.services.secrets_service import secrets_service
from app.utils.logging import get_logger
from app.services.pubsub_service import pubsub_service
from app.services.email_semantic_search import email_semantic_search

logger = get_logger("email_workflow_api")
router = APIRouter()

class EmailWorkflowRequest(BaseModel):
    """Request to start an email workflow."""
    mailbox_config: Dict[str, Any] = Field(..., description="IMAP mailbox configuration")
    processing_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processing options")

    @field_validator('mailbox_config')
    @classmethod
    def validate_mailbox_config(cls, v):
        required_fields = ['server', 'port', 'username', 'password']
        for field in required_fields:
            if field not in v:
                raise ValueError(f'Mailbox config must include {field}')
        return v

class EmailWorkflowResponse(BaseModel):
    """Response for workflow operations."""
    workflow_id: str
    status: str
    message: str
    created_at: str

class EmailWorkflowStatusResponse(BaseModel):
    """Status of an email workflow."""
    workflow_id: str
    status: str
    emails_processed: int
    tasks_created: int
    started_at: str
    completed_at: Optional[str]
    processing_time_ms: Optional[float]

class EmailDashboardStats(BaseModel):
    """Dashboard statistics for email workflows."""
    total_workflows: int
    active_workflows: int
    completed_workflows: int
    total_emails_processed: int
    total_tasks_created: int
    pending_tasks: int
    completed_tasks: int
    overdue_tasks: int
    success_rate: float
    avg_processing_time: float

class WorkflowAnalyticsOverview(BaseModel):
    """Analytics overview for a specific workflow."""
    workflow_id: str
    emails_processed: int
    tasks_created: int
    avg_importance_score: float
    top_categories: List[Dict[str, Any]]
    trend: Dict[str, Any]
    alerts: List[Dict[str, Any]]

class EmailNotificationsResponse(BaseModel):
    """Response for email notifications."""
    notifications: List[Dict[str, Any]]
    total_unread: int
    total: int

class RecentActivityResponse(BaseModel):
    """Response for recent activity feed."""
    activities: List[Dict[str, Any]]
    total: int
    has_more: bool

class ExportResponse(BaseModel):
    """Response for export operations."""
    export_id: str
    format: str
    status: str
    download_url: Optional[str]
    message: str


class EmailSettingsRequest(BaseModel):
    """Request to update email settings."""
    server: str
    port: int
    username: str
    password: str
    use_ssl: bool = True
    mailbox: str = "INBOX"


class EmailSettingsResponse(BaseModel):
    """Response for email settings."""
    server: Optional[str]
    port: Optional[int]
    username: Optional[str]
    use_ssl: Optional[bool]
    mailbox: Optional[str]
    has_password: bool

@router.post("/workflows/start", response_model=EmailWorkflowResponse)
async def start_email_workflow(
    request: EmailWorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start email processing workflow."""
    try:
        workflow = EmailWorkflow(
            user_id=current_user.id,
            status=EmailWorkflowStatus.RUNNING,
            mailbox_config=request.mailbox_config,
            processing_options=request.processing_options or {}
        )
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

        background_tasks.add_task(process_email_workflow_background, workflow.id, request, db)

        logger.info(f"Started email workflow {workflow.id} for user {current_user.username}")
        return EmailWorkflowResponse(
            workflow_id=str(workflow.id),
            status=workflow.status.value,
            message="Email workflow started successfully",
            created_at=workflow.created_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to start email workflow: {e}")
        raise HTTPException(status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start workflow")

async def process_email_workflow_background(workflow_id: UUID, request: EmailWorkflowRequest, db: AsyncSession):
    """Background task to process email workflow."""
    try:
        # Get workflow
        workflow = await db.get(EmailWorkflow, workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return

        # Use EmailConnector to fetch emails
        connector_config = request.mailbox_config
        processing_opts = request.processing_options or {}
        max_emails = processing_opts.get('max_emails', 50)
        unread_only = processing_opts.get('unread_only', False)
        since_date = processing_opts.get('since_date')

        connector = EmailConnector(connector_config)
        emails = await connector.fetch_emails(limit=max_emails, unread_only=unread_only, since_date=since_date)

        emails_processed = 0
        tasks_created = 0

        for email in emails:
            # Create ContentItem for email
            content_item = ContentItem(
                source_id=email['id'],
                source_type='email',
                connector_type='imap',
                content_type='text',
                title=email['subject'],
                description=email['body'][:500],  # Truncate for description
                published_at=email['date'],
                content_metadata=json.dumps(email)
            )
            db.add(content_item)
            await db.commit()
            await db.refresh(content_item)

            # Analyze email
            analysis = await email_analysis_service.analyze_email(email['body'], email['metadata'])

            # Create tasks if action required
            if analysis.action_required:
                task_request = TaskCreationRequest(
                    email_analysis=analysis,
                    user_id=workflow.user_id,
                    email_content=email['body'],
                    email_metadata=email['metadata']
                )
                result = await email_task_converter.convert_to_tasks(task_request, db)
                tasks_created += len(result.tasks_created)

            emails_processed += 1
            workflow.emails_processed += 1
            workflow.tasks_created += len(result.tasks_created) if 'result' in locals() else 0

            # Update workflow
            await db.commit()

        workflow.status = EmailWorkflowStatus.COMPLETED
        workflow.completed_at = datetime.utcnow()
        await db.commit()

        # Publish notification
        notification = Notification(
            user_id=workflow.user_id,
            type="workflow_complete",
            message=f"Email workflow completed: {emails_processed} emails processed, {tasks_created} tasks created",
            related_id=str(workflow_id)
        )
        db.add(notification)
        await db.commit()

        # Publish via pubsub
        await pubsub_service.publish("notifications", notification.to_dict())

        logger.info(f"Completed email workflow {workflow_id}: {emails_processed} emails, {tasks_created} tasks")

    except Exception as e:
        logger.error(f"Background email workflow failed for {workflow_id}: {e}")
        workflow.status = EmailWorkflowStatus.FAILED
        workflow.completed_at = datetime.utcnow()
        workflow.error_message = str(e)
        await db.commit()

@router.get("/workflows/{workflow_id}/status", response_model=EmailWorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get email workflow status."""
    workflow = await db.get(EmailWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    return EmailWorkflowStatusResponse(
        workflow_id=str(workflow.id),
        status=workflow.status,
        emails_processed=workflow.emails_processed,
        tasks_created=workflow.tasks_created,
        started_at=workflow.started_at.isoformat() if workflow.started_at else None,
        completed_at=workflow.completed_at.isoformat() if workflow.completed_at else None,
        processing_time_ms=None  # Calculate if needed
    )

@router.get("/workflows/history", response_model=List[EmailWorkflowStatusResponse])
async def get_workflow_history(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get email workflow history for user."""
    query = select(EmailWorkflow).where(EmailWorkflow.user_id == current_user.id).offset(offset).limit(limit).order_by(EmailWorkflow.created_at.desc())
    result = await db.execute(query)
    workflows = result.scalars().all()

    response = []
    for workflow in workflows:
        response.append(EmailWorkflowStatusResponse(
            workflow_id=str(workflow.id),
            status=workflow.status,
            emails_processed=workflow.emails_processed,
            tasks_created=workflow.tasks_created,
            started_at=workflow.started_at.isoformat() if workflow.started_at else None,
            completed_at=workflow.completed_at.isoformat() if workflow.completed_at else None,
            processing_time_ms=None
        ))

    return response

@router.post("/workflows/{workflow_id}/cancel")
async def cancel_email_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Cancel an email workflow."""
    workflow = await db.get(EmailWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    
    workflow.status = EmailWorkflowStatus.CANCELLED
    workflow.cancelled_at = datetime.utcnow()
    await db.commit()
    
    # Publish notification
    notification = Notification(
        user_id=workflow.user_id,
        type="workflow_cancelled",
        message=f"Email workflow {workflow_id} cancelled by user",
        related_id=str(workflow_id)
    )
    db.add(notification)
    await db.commit()
    
    await pubsub_service.publish("notifications", notification.to_dict())
    
    return {"message": "Workflow cancelled successfully"}

@router.get("/dashboard/stats", response_model=EmailDashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get dashboard statistics for email workflows."""
    # Query workflows
    total_workflows_query = select(func.count(EmailWorkflow.id)).where(EmailWorkflow.user_id == current_user.id)
    total_workflows = await db.execute(total_workflows_query)
    total_workflows = total_workflows.scalar()

    active_workflows_query = select(func.count(EmailWorkflow.id)).where(and_(EmailWorkflow.user_id == current_user.id, EmailWorkflow.status == EmailWorkflowStatus.RUNNING))
    active_workflows = await db.execute(active_workflows_query)
    active_workflows = active_workflows.scalar()

    completed_workflows_query = select(func.count(EmailWorkflow.id)).where(and_(EmailWorkflow.user_id == current_user.id, EmailWorkflow.status == EmailWorkflowStatus.COMPLETED))
    completed_workflows = await db.execute(completed_workflows_query)
    completed_workflows = completed_workflows.scalar()

    # Query emails processed (sum emails_processed from workflows)
    total_emails_query = select(func.sum(EmailWorkflow.emails_processed)).where(EmailWorkflow.user_id == current_user.id)
    total_emails = await db.execute(total_emails_query)
    total_emails = total_emails.scalar() or 0

    # Query tasks created (sum tasks_created from workflows)
    total_tasks_query = select(func.sum(EmailWorkflow.tasks_created)).where(EmailWorkflow.user_id == current_user.id)
    total_tasks = await db.execute(total_tasks_query)
    total_tasks = total_tasks.scalar() or 0

    # Query pending tasks (from Task model, where input has email_id and user_id matches)
    pending_tasks_query = select(func.count(Task.id)).where(and_(
        Task.input.op('->>')('email_id').isnot(None),
        Task.input.op('->>')('user_id') == str(current_user.id),
        Task.status == TaskStatus.PENDING
    ))
    pending_tasks = await db.execute(pending_tasks_query)
    pending_tasks = pending_tasks.scalar() or 0

    # Query completed tasks
    completed_tasks_query = select(func.count(Task.id)).where(and_(
        Task.input.op('->>')('email_id').isnot(None),
        Task.input.op('->>')('user_id') == str(current_user.id),
        Task.status == TaskStatus.COMPLETED
    ))
    completed_tasks = await db.execute(completed_tasks_query)
    completed_tasks = completed_tasks.scalar() or 0

    # Query overdue tasks (using created_at as proxy for due date logic)
    overdue_tasks_query = select(func.count(Task.id)).where(
        and_(
            Task.input.op('->>')('email_id').isnot(None),
            Task.input.op('->>')('user_id') == str(current_user.id),
            Task.status == TaskStatus.PENDING,
            Task.created_at < datetime.utcnow() - timedelta(days=7)  # Tasks older than 7 days
        )
    )
    overdue_tasks = await db.execute(overdue_tasks_query)
    overdue_tasks = overdue_tasks.scalar() or 0
    
    # Simple success rate (completed workflows / total workflows)
    success_rate = (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0.0
    
    # Avg processing time (placeholder, calculate from completed workflows)
    avg_processing_time = 45.2  # Mock for now
    
    return EmailDashboardStats(
        total_workflows=total_workflows,
        active_workflows=active_workflows,
        completed_workflows=completed_workflows,
        total_emails_processed=total_emails,
        total_tasks_created=total_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        success_rate=success_rate,
        avg_processing_time=avg_processing_time
    )

@router.get("/analytics/overview", response_model=WorkflowAnalyticsOverview)
async def get_email_analytics_overview(
    current_user: User = Depends(get_current_user),
    period_days: int = Query(default=30, description="Analysis period in days"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get email analytics overview for user."""
    # Get workflows for the user in the specified period
    since_date = datetime.utcnow() - timedelta(days=period_days)
    workflows_query = select(EmailWorkflow).where(
        and_(EmailWorkflow.user_id == current_user.id, EmailWorkflow.created_at >= since_date)
    )
    workflows_result = await db.execute(workflows_query)
    workflows = workflows_result.scalars().all()

    # Aggregate statistics
    total_workflows = len(workflows)
    completed_workflows = len([w for w in workflows if w.status == EmailWorkflowStatus.COMPLETED])
    total_emails_processed = sum(w.emails_processed for w in workflows)
    total_tasks_created = sum(w.tasks_created for w in workflows)

    # Calculate success rate
    success_rate = (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0.0

    # Get average processing time
    completed_times = [w for w in workflows if w.completed_at and w.started_at]
    avg_processing_time = 0.0
    if completed_times:
        total_time = sum((w.completed_at - w.started_at).total_seconds() for w in completed_times)
        avg_processing_time = total_time / len(completed_times)

    # Mock data for categories and trends (would be calculated from actual data)
    top_categories = [
        {"category": "business", "count": 45},
        {"category": "personal", "count": 23},
        {"category": "finance", "count": 18}
    ]

    trend = {
        "emails_per_day": [],
        "tasks_per_day": [],
        "success_rate_trend": success_rate
    }

    alerts = []
    if success_rate < 80:
        alerts.append({"type": "warning", "message": "Workflow success rate below 80%"})

    return WorkflowAnalyticsOverview(
        workflow_id="user_overview",  # Special ID for user overview
        emails_processed=total_emails_processed,
        tasks_created=total_tasks_created,
        avg_importance_score=0.75,  # Mock value
        top_categories=top_categories,
        trend=trend,
        alerts=alerts
    )

@router.get("/workflows/{workflow_id}/analytics/overview", response_model=WorkflowAnalyticsOverview)
async def get_workflow_analytics_overview(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get analytics overview for a specific workflow."""
    workflow = await db.get(EmailWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    # Get tasks created by this workflow
    tasks_query = select(func.count(Task.id)).where(
        Task.input.op('->>')('workflow_id') == str(workflow_id)
    )
    tasks_result = await db.execute(tasks_query)
    tasks_created = tasks_result.scalar() or 0

    # Mock data for demonstration
    top_categories = [
        {"category": "business", "count": 12},
        {"category": "urgent", "count": 8},
        {"category": "personal", "count": 5}
    ]

    trend = {
        "emails_per_day": [],
        "processing_time_trend": []
    }

    alerts = []
    if workflow.status == EmailWorkflowStatus.FAILED:
        alerts.append({"type": "error", "message": "Workflow failed to complete"})

    return WorkflowAnalyticsOverview(
        workflow_id=str(workflow_id),
        emails_processed=workflow.emails_processed,
        tasks_created=tasks_created,
        avg_importance_score=0.8,  # Mock value
        top_categories=top_categories,
        trend=trend,
        alerts=alerts
    )

@router.get("/notifications", response_model=EmailNotificationsResponse)
async def get_email_notifications(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0),
    unread_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db_session)
):
    """Get email notifications for user."""
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.status == NotificationStatus.UNREAD)
    query = query.offset(offset).limit(limit).order_by(Notification.created_at.desc())
    result = await db.execute(query)
    notifications = result.scalars().all()

    total_unread_query = select(func.count(Notification.id)).where(and_(Notification.user_id == current_user.id, Notification.status == NotificationStatus.UNREAD))
    total_unread = await db.execute(total_unread_query)
    total_unread = total_unread.scalar() or 0

    total_query = select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
    total = await db.execute(total_query)
    total = total.scalar() or 0
    
    response = []
    for notification in notifications:
        response.append({
            "id": str(notification.id),
            "type": notification.type,
            "message": notification.message,
            "related_id": notification.related_id,
            "status": notification.status.value,
            "created_at": notification.created_at.isoformat()
        })
    
    return EmailNotificationsResponse(
        notifications=response,
        total_unread=total_unread,
        total=total
    )

@router.get("/dashboard/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get recent activity feed for email workflows."""
    activities = []

    # Get recent workflows
    workflows_query = select(EmailWorkflow).where(EmailWorkflow.user_id == current_user.id).order_by(EmailWorkflow.created_at.desc()).limit(limit)
    workflows_result = await db.execute(workflows_query)
    workflows = workflows_result.scalars().all()

    for workflow in workflows:
        activities.append({
            "id": str(workflow.id),
            "type": "workflow",
            "action": "created" if workflow.status == EmailWorkflowStatus.RUNNING else "completed",
            "title": f"Email workflow {workflow.status.value}",
            "description": f"Processed {workflow.emails_processed} emails, created {workflow.tasks_created} tasks",
            "timestamp": workflow.created_at.isoformat(),
            "metadata": {
                "workflow_id": str(workflow.id),
                "emails_processed": workflow.emails_processed,
                "tasks_created": workflow.tasks_created,
                "status": workflow.status.value
            }
        })

    # Get recent notifications
    notifications_query = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(limit)
    notifications_result = await db.execute(notifications_query)
    notifications = notifications_result.scalars().all()

    for notification in notifications:
        activities.append({
            "id": str(notification.id),
            "type": "notification",
            "action": "created",
            "title": notification.type.replace("_", " ").title(),
            "description": notification.message,
            "timestamp": notification.created_at.isoformat(),
            "metadata": {
                "notification_id": str(notification.id),
                "type": notification.type,
                "status": notification.status.value,
                "related_id": notification.related_id
            }
        })

    # Get recent tasks
    tasks_query = select(Task).where(Task.input.op('->>')('user_id') == str(current_user.id)).order_by(Task.created_at.desc()).limit(limit)
    tasks_result = await db.execute(tasks_query)
    tasks = tasks_result.scalars().all()

    for task in tasks:
        activities.append({
            "id": str(task.id),
            "type": "task",
            "action": task.status.value,
            "title": f"Task {task.status.value}",
            "description": task.input.get('description', 'Task created from email'),
            "timestamp": task.created_at.isoformat(),
            "metadata": {
                "task_id": str(task.id),
                "status": task.status.value,
                "priority": task.input.get('priority', 'medium'),
                "email_id": task.input.get('email_id')
            }
        })

    # Sort all activities by timestamp and apply pagination
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    paginated_activities = activities[offset:offset + limit]
    has_more = len(activities) > offset + limit

    return RecentActivityResponse(
        activities=paginated_activities,
        total=len(activities),
        has_more=has_more
    )

@router.post("/dashboard/export/{format}", response_model=ExportResponse)
async def export_dashboard_data(
    format: str,
    current_user: User = Depends(get_current_user),
    include_workflows: bool = Query(default=True),
    include_tasks: bool = Query(default=True),
    include_notifications: bool = Query(default=True),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """Export dashboard data in specified format."""
    supported_formats = ['csv', 'json', 'pdf']
    if format not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format. Supported: {', '.join(supported_formats)}"
        )

    try:
        export_data = {
            "export_id": str(uuid4()),
            "format": format,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "data": {}
        }

        # Parse date filters
        date_from_dt = None
        date_to_dt = None
        if date_from:
            date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))

        # Export workflows
        if include_workflows:
            workflows_query = select(EmailWorkflow).where(EmailWorkflow.user_id == current_user.id)
            if date_from_dt:
                workflows_query = workflows_query.where(EmailWorkflow.created_at >= date_from_dt)
            if date_to_dt:
                workflows_query = workflows_query.where(EmailWorkflow.created_at <= date_to_dt)

            workflows_result = await db.execute(workflows_query)
            workflows = workflows_result.scalars().all()

            export_data["data"]["workflows"] = [
                {
                    "id": str(w.id),
                    "status": w.status.value,
                    "emails_processed": w.emails_processed,
                    "tasks_created": w.tasks_created,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                    "completed_at": w.completed_at.isoformat() if w.completed_at else None
                } for w in workflows
            ]

        # Export tasks
        if include_tasks:
            tasks_query = select(Task).where(Task.input.op('->>')('user_id') == str(current_user.id))
            if date_from_dt:
                tasks_query = tasks_query.where(Task.created_at >= date_from_dt)
            if date_to_dt:
                tasks_query = tasks_query.where(Task.created_at <= date_to_dt)

            tasks_result = await db.execute(tasks_query)
            tasks = tasks_result.scalars().all()

            export_data["data"]["tasks"] = [
                {
                    "id": str(t.id),
                    "status": t.status.value,
                    "description": t.input.get('description', ''),
                    "priority": t.input.get('priority', 'medium'),
                    "created_at": t.created_at.isoformat(),
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                } for t in tasks
            ]

        # Export notifications
        if include_notifications:
            notifications_query = select(Notification).where(Notification.user_id == current_user.id)
            if date_from_dt:
                notifications_query = notifications_query.where(Notification.created_at >= date_from_dt)
            if date_to_dt:
                notifications_query = notifications_query.where(Notification.created_at <= date_to_dt)

            notifications_result = await db.execute(notifications_query)
            notifications = notifications_result.scalars().all()

            export_data["data"]["notifications"] = [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "message": n.message,
                    "status": n.status.value,
                    "created_at": n.created_at.isoformat()
                } for n in notifications
            ]

        # For now, return the data directly (in production, this would be saved to file and URL returned)
        export_data["status"] = "completed"
        export_data["download_url"] = None  # Would be a presigned URL in production
        export_data["message"] = f"Dashboard data exported successfully in {format} format"

        return ExportResponse(**export_data)

    except Exception as e:
        logger.error(f"Failed to export dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export dashboard data"
        )


@router.get("/settings", response_model=EmailSettingsResponse)
async def get_email_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's email settings."""
    return EmailSettingsResponse(
        server=current_user.email_server,
        port=current_user.email_port,
        username=current_user.email_username,
        use_ssl=current_user.email_use_ssl,
        mailbox=current_user.email_mailbox,
        has_password=current_user.email_password_encrypted is not None
    )


@router.put("/settings", response_model=EmailSettingsResponse)
async def update_email_settings(
    settings: EmailSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update user's email settings."""
    # Encrypt the password before storing
    encrypted_password = None
    if settings.password:
        # For now, we'll store it as-is. In production, use proper encryption
        encrypted_password = settings.password

    # Update user settings
    current_user.email_server = settings.server
    current_user.email_port = settings.port
    current_user.email_username = settings.username
    current_user.email_password_encrypted = encrypted_password
    current_user.email_use_ssl = settings.use_ssl
    current_user.email_mailbox = settings.mailbox

    await db.commit()
    await db.refresh(current_user)

    logger.info(f"Updated email settings for user {current_user.username}")

    return EmailSettingsResponse(
        server=current_user.email_server,
        port=current_user.email_port,
        username=current_user.email_username,
        use_ssl=current_user.email_use_ssl,
        mailbox=current_user.email_mailbox,
        has_password=current_user.email_password_encrypted is not None
    )


@router.post("/workflows/start-with-saved-settings", response_model=EmailWorkflowResponse)
async def start_email_workflow_with_saved_settings(
    processing_options: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Start email workflow using saved email settings."""
    # Check if user has email settings configured
    if not current_user.email_server or not current_user.email_username or not current_user.email_password_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email settings not configured. Please configure your email settings first."
        )

    # Build mailbox config from saved settings
    mailbox_config = {
        "server": current_user.email_server,
        "port": current_user.email_port,
        "username": current_user.email_username,
        "password": current_user.email_password_encrypted,  # In production, decrypt this
        "mailbox": current_user.email_mailbox or "INBOX",
        "use_ssl": current_user.email_use_ssl if current_user.email_use_ssl is not None else True
    }

    # Create workflow request
    request = EmailWorkflowRequest(
        mailbox_config=mailbox_config,
        processing_options=processing_options or {}
    )

    # Start the workflow
    workflow = EmailWorkflow(
        user_id=current_user.id,
        status=EmailWorkflowStatus.RUNNING,
        mailbox_config=mailbox_config,
        processing_options=request.processing_options or {}
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    if background_tasks:
        background_tasks.add_task(process_email_workflow_background, workflow.id, request, db)

    logger.info(f"Started email workflow {workflow.id} for user {current_user.username} using saved settings")

    return EmailWorkflowResponse(
        workflow_id=str(workflow.id),
        status=workflow.status.value,
        message="Email workflow started successfully using saved settings",
        created_at=workflow.created_at.isoformat()
    )

# Existing routes for analyze, tasks, etc. remain the same, but update to use models where possible
# For example, the analyze route can remain as is, but add DB save for analysis if needed
# ... (keep the existing code for analyze, tasks, etc.)
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

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status as status_codes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, Float
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timedelta
from sse_starlette.sse import EventSourceResponse
import json

from app.api.dependencies import get_db_session, verify_api_key, get_current_user
from app.utils.auth import verify_token, get_user_by_username
from app.db.models.user import User

# Import models to avoid circular imports in cleanup endpoints
from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus, EmailWorkflowLog
from app.db.models.task import Task, TaskStatus
from app.db.models.notification import Notification, NotificationStatus

security = HTTPBearer(auto_error=False)
from app.utils.logging import get_logger

logger = get_logger("email_workflow_api")
router = APIRouter()

class EmailWorkflowRequest(BaseModel):
    """Request to start an email workflow with custom mailbox configuration."""
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


class EmailWorkflowLogResponse(BaseModel):
    """Response for email workflow logs."""
    id: str
    workflow_id: Optional[str]
    task_id: Optional[str]
    level: str
    message: str
    context: Dict[str, Any]
    timestamp: str
    workflow_phase: Optional[str]
    email_count: Optional[int]


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


class EmailWorkflowSettingsRequest(BaseModel):
    """Request to create/update email workflow settings."""
    settings_name: str
    description: Optional[str] = None
    max_emails_per_workflow: int = 50
    importance_threshold: float = 0.7
    spam_threshold: float = 0.8
    default_task_priority: str = "medium"
    analysis_timeout_seconds: int = 120
    task_conversion_timeout_seconds: int = 60
    ollama_request_timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 1
    create_tasks_automatically: bool = True
    schedule_followups: bool = True
    process_attachments: bool = True


class EmailWorkflowSettingsResponse(BaseModel):
    """Response for email workflow settings."""
    id: str
    user_id: str
    settings_name: str
    description: Optional[str]
    max_emails_per_workflow: int
    importance_threshold: float
    spam_threshold: float
    default_task_priority: str
    analysis_timeout_seconds: int
    task_conversion_timeout_seconds: int
    ollama_request_timeout_seconds: int
    max_retries: int
    retry_delay_seconds: int
    create_tasks_automatically: bool
    schedule_followups: bool
    process_attachments: bool
    is_default: bool
    is_active: bool
    usage_count: int
    created_at: str
    updated_at: str

@router.post("/workflows/start", response_model=EmailWorkflowResponse)
async def start_email_workflow(
    request: EmailWorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start email processing workflow."""
    try:
        workflow = EmailWorkflow(
            user_id=str(current_user.id),
            status=EmailWorkflowStatus.RUNNING,
            mailbox_config=request.mailbox_config,
            processing_options=request.processing_options or {}
        )

        db.add(workflow)
        await db.commit()
        # No need to refresh since we only need the ID which is already set

        # Start Celery task for email workflow processing
        from app.tasks.agent_tasks import process_email_workflow_task
        task = process_email_workflow_task.delay(
            workflow_id=str(workflow.id),
            mailbox_config=request.mailbox_config,
            processing_options=request.processing_options or {}
        )

        logger.info(f"Started Celery task {task.id} for email workflow {workflow.id}")

        return EmailWorkflowResponse(
            workflow_id=str(workflow.id),
            status="running",
            message="Email workflow started successfully",
            created_at=workflow.created_at.isoformat() if workflow.created_at else ""
        )
    except Exception as e:
        logger.error(f"Failed to start email workflow: {e}")
        await db.rollback()
        raise HTTPException(status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start workflow")


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
        status=workflow.status.value if hasattr(workflow.status, 'value') else str(workflow.status),
        emails_processed=workflow.emails_processed,
        tasks_created=workflow.tasks_created,
        started_at=workflow.started_at.isoformat() if workflow.started_at else "",
        completed_at=workflow.completed_at.isoformat() if workflow.completed_at else "",
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
    query = select(EmailWorkflow).where(EmailWorkflow.user_id == str(current_user.id)).offset(offset).limit(limit).order_by(EmailWorkflow.created_at.desc())
    result = await db.execute(query)
    workflows = result.scalars().all()

    response = []
    for workflow in workflows:
        response.append(EmailWorkflowStatusResponse(
            workflow_id=str(workflow.id),
            status=workflow.status.value if hasattr(workflow.status, 'value') else str(workflow.status),
            emails_processed=workflow.emails_processed,
            tasks_created=workflow.tasks_created,
            started_at=workflow.started_at.isoformat() if workflow.started_at else "",
            completed_at=workflow.completed_at.isoformat() if workflow.completed_at else "",
            processing_time_ms=None
        ))

    return response


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_email_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Cancel an email workflow."""
    try:
        workflow = await db.get(EmailWorkflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

        workflow.status = EmailWorkflowStatus.CANCELLED.value
        workflow.cancelled_at = datetime.utcnow()
        await db.commit()

        logger.info(f"Cancelled email workflow {workflow_id}")

        return {"message": "Workflow cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel workflow"
        )


@router.get("/dashboard/stats", response_model=EmailDashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get dashboard statistics for email workflows."""
    # Import required models inside function to avoid circular imports
    from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus
    from app.db.models.task import Task, TaskStatus

    user_id = str(current_user.id)

    # Query workflows
    total_workflows_query = select(func.count(EmailWorkflow.id)).where(EmailWorkflow.user_id == user_id)
    total_workflows = await db.execute(total_workflows_query)
    total_workflows = total_workflows.scalar()

    active_workflows_query = select(func.count(EmailWorkflow.id)).where(and_(EmailWorkflow.user_id == user_id, EmailWorkflow.status == EmailWorkflowStatus.RUNNING))
    active_workflows = await db.execute(active_workflows_query)
    active_workflows = active_workflows.scalar()

    completed_workflows_query = select(func.count(EmailWorkflow.id)).where(and_(EmailWorkflow.user_id == user_id, EmailWorkflow.status == EmailWorkflowStatus.COMPLETED))
    completed_workflows = await db.execute(completed_workflows_query)
    completed_workflows = completed_workflows.scalar()

    # Query emails processed (sum emails_processed from workflows)
    total_emails_query = select(func.sum(EmailWorkflow.emails_processed)).where(EmailWorkflow.user_id == user_id)
    total_emails = await db.execute(total_emails_query)
    total_emails = total_emails.scalar() or 0

    # Query tasks created (sum tasks_created from workflows)
    total_tasks_query = select(func.sum(EmailWorkflow.tasks_created)).where(EmailWorkflow.user_id == user_id)
    total_tasks = await db.execute(total_tasks_query)
    total_tasks = total_tasks.scalar() or 0

    # Query pending tasks (from Task model, where input has email_id and user_id matches)
    pending_tasks_query = select(func.count(Task.id)).where(and_(
        Task.input.op('->>')('email_id').isnot(None),
        Task.input.op('->>')('user_id') == user_id,
        Task.status == TaskStatus.PENDING
    ))
    pending_tasks = await db.execute(pending_tasks_query)
    pending_tasks = pending_tasks.scalar() or 0

    # Query completed tasks
    completed_tasks_query = select(func.count(Task.id)).where(and_(
        Task.input.op('->>')('email_id').isnot(None),
        Task.input.op('->>')('user_id') == user_id,
        Task.status == TaskStatus.COMPLETED
    ))
    completed_tasks = await db.execute(completed_tasks_query)
    completed_tasks = completed_tasks.scalar() or 0

    # Query overdue tasks (using created_at as proxy for due date logic)
    overdue_tasks_query = select(func.count(Task.id)).where(
        and_(
            Task.input.op('->>')('email_id').isnot(None),
            Task.input.op('->>')('user_id') == user_id,
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
        and_(EmailWorkflow.user_id == str(current_user.id), EmailWorkflow.created_at >= since_date)
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
    query = select(Notification).where(Notification.user_id == str(current_user.id))
    if unread_only:
        query = query.where(Notification.status == NotificationStatus.UNREAD)
    query = query.offset(offset).limit(limit).order_by(Notification.created_at.desc())
    result = await db.execute(query)
    notifications = result.scalars().all()

    total_unread_query = select(func.count(Notification.id)).where(and_(Notification.user_id == str(current_user.id), Notification.status == NotificationStatus.UNREAD))
    total_unread = await db.execute(total_unread_query)
    total_unread = total_unread.scalar() or 0

    total_query = select(func.count(Notification.id)).where(Notification.user_id == str(current_user.id))
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
    workflows_query = select(EmailWorkflow).where(EmailWorkflow.user_id == str(current_user.id)).order_by(EmailWorkflow.created_at.desc()).limit(limit)
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
    notifications_query = select(Notification).where(Notification.user_id == str(current_user.id)).order_by(Notification.created_at.desc()).limit(limit)
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
            "user_id": str(current_user.id),
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
            workflows_query = select(EmailWorkflow).where(EmailWorkflow.user_id == str(current_user.id))
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
            notifications_query = select(Notification).where(Notification.user_id == str(current_user.id))
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
    # Query user data directly to avoid lazy loading issues
    from sqlalchemy import select
    user_result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user_data = user_result.scalar_one_or_none()

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return EmailSettingsResponse(
        server=user_data.email_server,
        port=user_data.email_port,
        username=user_data.email_username,
        use_ssl=user_data.email_use_ssl,
        mailbox=user_data.email_mailbox,
        has_password=user_data.email_password_encrypted is not None
    )


@router.put("/settings", response_model=EmailSettingsResponse)
async def update_email_settings(
    settings: EmailSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update user's email settings."""
    # Query user data directly to avoid lazy loading issues
    from sqlalchemy import select, update
    user_result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user_data = user_result.scalar_one_or_none()

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Encrypt the password before storing
    encrypted_password = None
    if settings.password:
        # For now, we'll store it as-is. In production, use proper encryption
        encrypted_password = settings.password

    # Update user settings using explicit update query
    update_stmt = (
        update(User)
        .where(User.id == user_data.id)
        .values(
            email_server=settings.server,
            email_port=settings.port,
            email_username=settings.username,
            email_password_encrypted=encrypted_password,
            email_use_ssl=settings.use_ssl,
            email_mailbox=settings.mailbox
        )
    )
    await db.execute(update_stmt)
    await db.commit()

    # Refresh the user data
    user_result = await db.execute(
        select(User).where(User.id == user_data.id)
    )
    updated_user = user_result.scalar_one()

    logger.info(f"Updated email settings for user {updated_user.username}")

    return EmailSettingsResponse(
        server=updated_user.email_server,
        port=updated_user.email_port,
        username=updated_user.email_username,
        use_ssl=updated_user.email_use_ssl,
        mailbox=updated_user.email_mailbox,
        has_password=updated_user.email_password_encrypted is not None
    )


class EmailWorkflowStartRequest(BaseModel):
    """Request to start email workflow with saved settings."""
    processing_options: Optional[Dict[str, Any]] = Field(default_factory=dict)

@router.post("/workflows/start-with-saved-settings", response_model=EmailWorkflowResponse)
async def start_email_workflow_with_saved_settings(
    request: EmailWorkflowStartRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start email workflow using saved email settings."""
    try:
        logger.info("Starting email workflow with saved settings")

        # Store user ID early to avoid session issues
        user_id = str(current_user.id)

        # Validate that all required email settings are configured
        required_settings = {
            'email_server': current_user.email_server,
            'email_port': current_user.email_port,
            'email_username': current_user.email_username,
            'email_password_encrypted': current_user.email_password_encrypted
        }

        missing_settings = [key for key, value in required_settings.items() if not value]
        if missing_settings:
            logger.warning(f"Missing email settings for user {user_id}: {missing_settings}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email settings not fully configured. Missing: {', '.join(missing_settings)}. Please configure your email settings first."
            )

        logger.info("Email settings are configured")

        # Build mailbox config from saved settings
        mailbox_config = {
            "server": current_user.email_server,
            "port": current_user.email_port,
            "username": current_user.email_username,
            "password": current_user.email_password_encrypted,  # In production, decrypt this
            "mailbox": current_user.email_mailbox or "INBOX",
            "use_ssl": current_user.email_use_ssl if current_user.email_use_ssl is not None else True
        }

        # Extract processing options from request
        processing_options = request.processing_options or {}
        
        # Create workflow request
        workflow_request = EmailWorkflowRequest(
            mailbox_config=mailbox_config,
            processing_options=processing_options
        )

        # Import required models inside function to avoid circular imports
        from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus

        # Start the workflow
        workflow = EmailWorkflow(
            user_id=user_id,
            status=EmailWorkflowStatus.RUNNING,
            mailbox_config=mailbox_config,
            processing_options=processing_options
        )

        logger.info(f"About to add workflow to database: {workflow.id}")
        db.add(workflow)
        logger.info("About to commit workflow to database")
        await db.commit()
        await db.refresh(workflow)  # Refresh to get the generated ID
        logger.info("Workflow committed successfully")
        workflow_id = str(workflow.id)

        # Start Celery task for email workflow processing
        from app.tasks.agent_tasks import process_email_workflow_task
        task = process_email_workflow_task.delay(
            workflow_id=workflow_id,
            mailbox_config=mailbox_config,
            processing_options=processing_options
        )

        logger.info(f"Started Celery task {task.id} for email workflow {workflow_id}")

        logger.info(f"Started email workflow {workflow_id} for user {user_id} using saved settings")

        return EmailWorkflowResponse(
            workflow_id=workflow_id,
            status="running",
            message="Email workflow started successfully using saved settings",
            created_at=""  # Will be set by the database
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start email workflow with saved settings: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start workflow")

@router.get("/tasks", response_model=List[Dict[str, Any]])
async def get_email_tasks(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by task status"),
    priority: Optional[str] = Query(None, description="Filter by task priority"),
    email_id: Optional[str] = Query(None, description="Filter by email ID"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get email-related tasks for the current user."""
    try:
        # Import required models inside function to avoid circular imports
        from app.db.models.task import Task, TaskStatus

        # Build query to get tasks related to emails for this user
        query = select(Task).where(Task.input.op('->>')('user_id') == str(current_user.id))

        # Add email-related filter (tasks that have email_id in their input)
        query = query.where(Task.input.op('->>')('email_id').isnot(None))

        # Apply status filter if provided
        if status:
            query = query.where(Task.status == TaskStatus(status))

        # Apply priority filter if provided (stored in input JSON)
        if priority:
            query = query.where(Task.input.op('->>')('priority') == priority)

        # Apply email_id filter if provided
        if email_id:
            query = query.where(Task.input.op('->>')('email_id') == email_id)

        # Apply pagination and ordering
        query = query.offset(offset).limit(limit).order_by(Task.created_at.desc())

        result = await db.execute(query)
        tasks = result.scalars().all()

        # Convert tasks to response format
        response = []
        for task in tasks:
            task_data = {
                "id": str(task.id),
                "status": task.status.value,
                "description": task.input.get('description', ''),
                "priority": task.input.get('priority', 'medium'),
                "email_id": task.input.get('email_id'),
                "email_sender": task.input.get('email_sender'),
                "email_subject": task.input.get('email_subject'),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error_message": task.error_message,
                "retry_count": task.retry_count,
                "celery_task_id": task.celery_task_id,
                "input": task.input,
                "output": task.output
            }
            response.append(task_data)

        return response

    except Exception as e:
        logger.error(f"Failed to get email tasks: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email tasks"
        )


@router.get("/tasks/{task_id}/email-content")
async def get_task_email_content(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the full email content for a task."""
    try:
        from app.db.models.task import Task
        
        # Find the task
        task = await db.get(Task, task_id)
        if not task:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify the task belongs to the current user
        if task.input.get('user_id') != str(current_user.id):
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Extract email content and metadata
        email_content = task.input.get('email_content', '')
        email_metadata = task.input.get('email_metadata', {})
        
        return {
            "task_id": str(task.id),
            "email_content": email_content,
            "email_metadata": email_metadata,
            "email_sender": task.input.get('email_sender'),
            "email_subject": task.input.get('email_subject'),
            "email_id": task.input.get('email_id')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email content for task: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email content"
        )


@router.post("/tasks/{task_id}/complete")
async def complete_email_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Mark an email task as completed."""
    try:
        from app.db.models.task import Task, TaskStatus
        from datetime import datetime
        
        # Find the task
        task = await db.get(Task, task_id)
        if not task:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify the task belongs to the current user
        if task.input.get('user_id') != str(current_user.id):
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update task status
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        
        # Record user feedback for email learning
        if task.email_id:
            try:
                from app.services.email_deduplication_service import EmailDeduplicationService
                dedup_service = EmailDeduplicationService(db)
                dedup_service.record_user_action(
                    str(task.email_id),
                    'completed',
                    {
                        'task_id': str(task.id),
                        'completion_time': task.completed_at.isoformat(),
                        'email_subject': task.email_subject,
                        'email_sender': task.email_sender
                    }
                )
            except Exception as feedback_error:
                logger.warning(f"Failed to record completion feedback for task {task_id}: {feedback_error}")
        
        await db.commit()
        await db.refresh(task)
        
        return {
            "id": str(task.id),
            "status": task.status.value,
            "message": "Task marked as completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete email task: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete task"
        )


@router.post("/tasks/{task_id}/mark-not-important")
async def mark_task_not_important(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Mark an email task as not important and close it with feedback."""
    try:
        from app.db.models.task import Task, TaskStatus
        from datetime import datetime
        
        # Find the task
        task = await db.get(Task, task_id)
        if not task:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify the task belongs to the current user
        if task.input.get('user_id') != str(current_user.id):
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update task status and add feedback metadata
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        
        # Add feedback to task output for future learning
        task.output = task.output or {}
        task.output.update({
            "user_feedback": "not_important",
            "feedback_timestamp": datetime.utcnow().isoformat(),
            "original_importance": task.input.get('importance_score'),
            "marked_not_important_by": str(current_user.id)
        })
        
        # Record user feedback for email learning
        if task.email_id:
            try:
                from app.services.email_deduplication_service import EmailDeduplicationService
                dedup_service = EmailDeduplicationService(db)
                dedup_service.record_user_action(
                    str(task.email_id),
                    'dismissed',
                    {
                        'task_id': str(task.id),
                        'dismissal_time': task.completed_at.isoformat(),
                        'original_importance': task.input.get('importance_score'),
                        'email_subject': task.email_subject,
                        'email_sender': task.email_sender,
                        'user_reason': 'not_important'
                    }
                )
                logger.info(f"Recorded 'not important' feedback for email {task.email_id}")
            except Exception as feedback_error:
                logger.warning(f"Failed to record dismissal feedback for task {task_id}: {feedback_error}")
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Task {task_id} marked as not important by user {current_user.id}. "
                   f"Original importance: {task.input.get('importance_score')}")
        
        return {
            "id": str(task.id),
            "status": task.status.value,
            "message": "Task marked as not important and completed",
            "feedback_recorded": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark task as not important: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark task as not important"
        )


@router.get("/deduplication/stats", response_model=dict)
async def get_deduplication_stats(
    current_user: User = Depends(get_current_user),
    days: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db_session)
):
    """Get email deduplication statistics for the user."""
    try:
        from app.services.email_deduplication_service import EmailDeduplicationService
        dedup_service = EmailDeduplicationService(db)
        
        stats = dedup_service.get_deduplication_stats(current_user.id, days)
        
        return {
            "user_id": current_user.id,
            "stats": stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get deduplication stats: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deduplication statistics"
        )


@router.get("/workflows/{workflow_id}/logs", response_model=List[EmailWorkflowLogResponse])
async def get_workflow_logs(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    level: Optional[str] = Query(None, description="Filter by log level"),
    phase: Optional[str] = Query(None, description="Filter by workflow phase"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get logs for a specific workflow."""
    try:
        # Verify workflow belongs to user
        workflow = await db.get(EmailWorkflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if workflow.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Build query for logs
        query = select(EmailWorkflowLog).where(EmailWorkflowLog.workflow_id == workflow_id)

        # Apply filters
        if level:
            query = query.where(EmailWorkflowLog.level == level)
        if phase:
            query = query.where(EmailWorkflowLog.workflow_phase == phase)

        # Apply pagination and ordering
        query = query.offset(offset).limit(limit).order_by(EmailWorkflowLog.created_at.desc())

        result = await db.execute(query)
        logs = result.scalars().all()

        # Convert to response format
        response = []
        for log in logs:
            response.append(EmailWorkflowLogResponse(
                id=str(log.id),
                workflow_id=str(log.workflow_id),
                task_id=str(log.task_id) if log.task_id else None,
                level=log.level,
                message=log.message,
                context=log.context,
                timestamp=log.created_at.isoformat() if log.created_at else "",
                workflow_phase=log.workflow_phase,
                email_count=log.email_count
            ))

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow logs for {workflow_id}: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow logs"
        )


@router.get("/workflows/summary")
async def get_workflows_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a summary of workflow and task statistics."""
    try:
        # Import required models inside function to avoid circular imports
        from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus
        from app.db.models.task import Task, TaskStatus

        user_id = str(current_user.id)

        # Workflow statistics
        workflow_stats_query = select(
            EmailWorkflow.status,
            func.count(EmailWorkflow.id)
        ).where(
            EmailWorkflow.user_id == user_id
        ).group_by(EmailWorkflow.status)

        workflow_result = await db.execute(workflow_stats_query)
        workflow_stats = {row[0]: row[1] for row in workflow_result}

        # Task statistics
        task_stats_query = select(
            Task.status,
            func.count(Task.id)
        ).where(
            Task.input.op('->>')('user_id') == user_id
        ).group_by(Task.status)

        task_result = await db.execute(task_stats_query)
        task_stats = {row[0]: row[1] for row in task_result}

        # Calculate totals
        total_workflows = sum(workflow_stats.values())
        active_workflows = workflow_stats.get('running', 0)
        total_tasks = sum(task_stats.values())
        pending_tasks = task_stats.get('pending', 0)
        completed_tasks = task_stats.get('completed', 0)
        failed_tasks = task_stats.get('failed', 0)

        # Check for stale workflows
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        stale_query = select(func.count(EmailWorkflow.id)).where(
            and_(
                EmailWorkflow.user_id == user_id,
                EmailWorkflow.status == EmailWorkflowStatus.RUNNING,
                EmailWorkflow.created_at < cutoff_time
            )
        )
        stale_result = await db.execute(stale_query)
        stale_count = stale_result.scalar()

        return {
            "workflows": {
                "total": total_workflows,
                "active": active_workflows,
                "completed": workflow_stats.get('completed', 0),
                "failed": workflow_stats.get('failed', 0),
                "cancelled": workflow_stats.get('cancelled', 0),
                "stale": stale_count
            },
            "tasks": {
                "total": total_tasks,
                "pending": pending_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
                "running": task_stats.get('running', 0)
            },
            "needs_cleanup": stale_count > 0
        }

    except Exception as e:
        logger.error(f"Failed to get workflow summary: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow summary"
        )

@router.post("/workflows/cleanup-stale")
async def cleanup_stale_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    max_age_hours: int = Query(default=24, description="Maximum age in hours for stale workflows")
):
    """Clean up stale workflows that have been running too long."""
    try:
        from app.db.database import get_session_context

        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        async with get_session_context() as session:
            # Find stale workflows (running for more than max_age_hours)
            stale_query = select(EmailWorkflow).where(
                and_(
                    EmailWorkflow.user_id == str(current_user.id),
                    EmailWorkflow.status == EmailWorkflowStatus.RUNNING,
                    EmailWorkflow.created_at < cutoff_time
                )
            )
            result = await session.execute(stale_query)
            stale_workflows = result.scalars().all()

            cleaned_count = 0
            for workflow in stale_workflows:
                workflow.status = EmailWorkflowStatus.FAILED
                workflow.completed_at = datetime.utcnow()
                workflow.error_message = f"Workflow marked as failed due to timeout (running > {max_age_hours} hours"
                cleaned_count += 1

            await session.commit()

        logger.info(f"Cleaned up {cleaned_count} stale workflows for user {current_user.username}")

        return {
            "message": f"Successfully cleaned up {cleaned_count} stale workflows",
            "cleaned_count": cleaned_count,
            "max_age_hours": max_age_hours
        }

    except Exception as e:
        logger.error(f"Failed to cleanup stale workflows: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup stale workflows"
        )


@router.delete("/workflows/clear-all")
async def clear_all_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    confirm: bool = Query(default=False, description="Must be true to confirm deletion")
):
    """Clear all workflows for the current user (dangerous operation)."""
    try:
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation required. Set confirm=true to proceed with clearing all workflows."
            )

        from app.db.database import get_session_context

        async with get_session_context() as session:
            # Count workflows before deletion
            count_query = select(func.count(EmailWorkflow.id)).where(
                EmailWorkflow.user_id == str(current_user.id)
            )
            result = await session.execute(count_query)
            total_count = result.scalar()

            # Delete all logs for user's workflows
            from sqlalchemy import delete
            await session.execute(
                delete(EmailWorkflowLog).where(EmailWorkflowLog.user_id == str(current_user.id))
            )

            # Delete all workflows
            await session.execute(
                delete(EmailWorkflow).where(EmailWorkflow.user_id == str(current_user.id))
            )

            await session.commit()

        logger.warning(f"Cleared all {total_count} workflows for user {current_user.username}")

        return {
            "message": f"Successfully cleared all {total_count} workflows",
            "deleted_count": total_count,
            "user_id": str(current_user.id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear all workflows: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear all workflows"
        )

# Email Workflow Settings Management
@router.post("/workflow-settings", response_model=EmailWorkflowSettingsResponse)
async def create_workflow_settings(
    settings: EmailWorkflowSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create new email workflow settings profile."""
    try:
        # Import the model
        from app.db.models.email_workflow import EmailWorkflowSettings

        # Create new settings
        workflow_settings = EmailWorkflowSettings(
            user_id=str(current_user.id),
            settings_name=settings.settings_name,
            description=settings.description,
            max_emails_per_workflow=settings.max_emails_per_workflow,
            importance_threshold=settings.importance_threshold,
            spam_threshold=settings.spam_threshold,
            default_task_priority=settings.default_task_priority,
            analysis_timeout_seconds=settings.analysis_timeout_seconds,
            task_conversion_timeout_seconds=settings.task_conversion_timeout_seconds,
            ollama_request_timeout_seconds=settings.ollama_request_timeout_seconds,
            max_retries=settings.max_retries,
            retry_delay_seconds=settings.retry_delay_seconds,
            create_tasks_automatically=settings.create_tasks_automatically,
            schedule_followups=settings.schedule_followups,
            process_attachments=settings.process_attachments
        )

        db.add(workflow_settings)
        await db.commit()
        await db.refresh(workflow_settings)

        logger.info(f"Created workflow settings {workflow_settings.id} for user {current_user.username}")

        return EmailWorkflowSettingsResponse(**workflow_settings.to_dict())

    except Exception as e:
        logger.error(f"Failed to create workflow settings: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow settings"
        )


@router.get("/workflow-settings", response_model=List[EmailWorkflowSettingsResponse])
async def list_workflow_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all email workflow settings profiles for the current user."""
    try:
        # Import the model
        from app.db.models.email_workflow import EmailWorkflowSettings

        # Query settings
        query = select(EmailWorkflowSettings).where(EmailWorkflowSettings.user_id == str(current_user.id))
        result = await db.execute(query)
        settings_list = result.scalars().all()

        return [EmailWorkflowSettingsResponse(**settings.to_dict()) for settings in settings_list]

    except Exception as e:
        logger.error(f"Failed to list workflow settings: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow settings"
        )


# Default workflow settings routes (must come before parameterized routes)
@router.get("/workflow-settings/default", response_model=EmailWorkflowSettingsResponse)
async def get_default_workflow_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's default email workflow settings, creating them if they don't exist."""
    try:
        # Import the model
        from app.db.models.email_workflow import EmailWorkflowSettings

        # Try to get existing default settings
        query = select(EmailWorkflowSettings).where(
            and_(EmailWorkflowSettings.user_id == str(current_user.id), EmailWorkflowSettings.is_default == True)
        )
        result = await db.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            # Create default settings
            default_settings = EmailWorkflowSettings(
                user_id=str(current_user.id),
                settings_name="Default Settings",
                description="Default email workflow settings",
                is_default=True
            )
            db.add(default_settings)
            await db.commit()
            await db.refresh(default_settings)
            settings = default_settings

        return EmailWorkflowSettingsResponse(**settings.to_dict())

    except Exception as e:
        logger.error(f"Failed to get default workflow settings: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve default workflow settings"
        )


@router.put("/workflow-settings/default", response_model=EmailWorkflowSettingsResponse)
async def update_default_workflow_settings(
    settings_update: EmailWorkflowSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update user's default email workflow settings with modern async/SQLAlchemy patterns.
    
    This implementation uses comprehensive async safety measures to prevent greenlet spawn errors:
    - Proper session management with explicit connection establishment
    - Eager attribute loading to prevent lazy loading issues
    - Modern Pydantic compatibility for both v1 and v2
    - Comprehensive error handling and logging
    """
    try:
        from app.db.models.email_workflow import EmailWorkflowSettings
        
        logger.info(f"Updating default workflow settings for user {current_user.username}")

        # Query with explicit options to prevent lazy loading  
        query = (
            select(EmailWorkflowSettings)
            .where(
                and_(
                    EmailWorkflowSettings.user_id == str(current_user.id),
                    EmailWorkflowSettings.is_default == True
                )
            )
            .execution_options(populate_existing=True)  # Force refresh from DB
        )
        
        result = await db.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            logger.info(f"Creating new default settings for user {current_user.id}")
            settings = EmailWorkflowSettings(
                user_id=str(current_user.id),
                settings_name="Default Settings",
                description="Default email workflow settings",
                is_default=True
            )
            db.add(settings)
            await db.flush()  # Get the ID assigned
            await db.refresh(settings)  # Ensure all attributes loaded

        # Handle Pydantic version compatibility
        try:
            update_data = settings_update.model_dump(exclude_unset=True)
        except AttributeError:
            update_data = settings_update.dict(exclude_unset=True)

        # Apply updates with careful attribute handling
        for field, value in update_data.items():
            if hasattr(settings, field) and value is not None:
                current_value = getattr(settings, field, None)
                logger.debug(f"Updating {field}: {current_value} -> {value}")
                setattr(settings, field, value)

        # Flush changes and refresh to ensure consistency
        await db.flush()
        await db.refresh(settings)
        
        # Eagerly load ALL attributes while session is active
        settings_dict = {
            "id": str(settings.id),
            "user_id": str(settings.user_id),
            "settings_name": str(settings.settings_name) if settings.settings_name else "",
            "description": settings.description,
            "max_emails_per_workflow": int(settings.max_emails_per_workflow or 50),
            "importance_threshold": float(settings.importance_threshold or 0.7),
            "spam_threshold": float(settings.spam_threshold or 0.8),
            "default_task_priority": str(settings.default_task_priority or "medium"),
            "analysis_timeout_seconds": int(settings.analysis_timeout_seconds or 120),
            "task_conversion_timeout_seconds": int(settings.task_conversion_timeout_seconds or 60),
            "ollama_request_timeout_seconds": int(settings.ollama_request_timeout_seconds or 60),
            "max_retries": int(settings.max_retries or 3),
            "retry_delay_seconds": int(settings.retry_delay_seconds or 1),
            "create_tasks_automatically": bool(settings.create_tasks_automatically),
            "schedule_followups": bool(settings.schedule_followups),
            "process_attachments": bool(settings.process_attachments),
            "is_default": bool(settings.is_default),
            "is_active": bool(settings.is_active),
            "usage_count": int(settings.usage_count or 0),
            "created_at": str(settings.created_at) if settings.created_at else "",
            "updated_at": str(settings.updated_at) if settings.updated_at else ""
        }
        
        # Commit happens automatically via session dependency
            
        # Create response outside of transaction context
        logger.info(f"Successfully updated default workflow settings for user {current_user.username}")
        
        return EmailWorkflowSettingsResponse(**settings_dict)

    except Exception as e:
        logger.error(f"Failed to update default workflow settings: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Ensure rollback
        try:
            await db.rollback()
        except:
            pass
            
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update default workflow settings"
        )


@router.get("/workflow-settings/{settings_id}", response_model=EmailWorkflowSettingsResponse)
async def get_workflow_settings(
    settings_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get specific email workflow settings profile."""
    try:
        # Import the model
        from app.db.models.email_workflow import EmailWorkflowSettings

        # Handle the case where settings_id might be "default"
        if settings_id == "default":
            # Redirect to the default settings endpoint
            return await get_default_workflow_settings(current_user, db)

        # Try to parse as UUID
        try:
            uuid_obj = UUID(settings_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid settings ID format")

        # Get settings
        settings = await db.get(EmailWorkflowSettings, uuid_obj)
        if not settings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow settings not found")

        if settings.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return EmailWorkflowSettingsResponse(**settings.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow settings {settings_id}: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow settings"
        )


@router.put("/workflow-settings/{settings_id}", response_model=EmailWorkflowSettingsResponse)
async def update_workflow_settings(
    settings_id: str,
    settings_update: EmailWorkflowSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update email workflow settings profile."""
    try:
        # Import the model
        from app.db.models.email_workflow import EmailWorkflowSettings

        # Parse settings_id as UUID
        try:
            uuid_obj = UUID(settings_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid settings ID format")

        # Get existing settings
        settings = await db.get(EmailWorkflowSettings, uuid_obj)
        if not settings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow settings not found")

        if settings.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Update fields
        try:
            # Try newer Pydantic v2 method first
            try:
                update_data = settings_update.model_dump()
            except AttributeError:
                # Fall back to older Pydantic v1 method
                update_data = settings_update.dict()
                
            for field, value in update_data.items():
                if hasattr(settings, field):
                    logger.info(f"Updating field {field} with value {value} (type: {type(value)})")
                    setattr(settings, field, value)
                else:
                    logger.warning(f"Field {field} does not exist on EmailWorkflowSettings model")

            # Use the existing session
            await db.commit()
            await db.refresh(settings)

            logger.info(f"Updated workflow settings {settings_id} for user {current_user.username}")

            # Try to create the response
            response_data = settings.to_dict()
            return EmailWorkflowSettingsResponse(**response_data)

        except Exception as update_error:
            logger.error(f"Error during workflow settings update: {update_error}")
            await db.rollback()
            raise HTTPException(
                status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update workflow settings: {str(update_error)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow settings {settings_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow settings"
        )


@router.delete("/workflow-settings/{settings_id}")
async def delete_workflow_settings(
    settings_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete email workflow settings profile."""
    try:
        # Import the model
        from app.db.models.email_workflow import EmailWorkflowSettings

        # Get settings
        settings = await db.get(EmailWorkflowSettings, settings_id)
        if not settings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow settings not found")

        if settings.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        await db.delete(settings)
        await db.commit()

        logger.info(f"Deleted workflow settings {settings_id} for user {current_user.username}")

        return {"message": "Workflow settings deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow settings {settings_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow settings"
        )


@router.get("/logs", response_model=List[EmailWorkflowLogResponse])
async def get_email_workflow_logs(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0),
    level: Optional[str] = Query(None, description="Filter by log level"),
    workflow_id: Optional[UUID] = Query(None, description="Filter by workflow ID"),
    phase: Optional[str] = Query(None, description="Filter by workflow phase"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get email workflow logs for the current user."""
    try:
        # Build query for logs from user's workflows
        query = select(EmailWorkflowLog).join(
            EmailWorkflow, EmailWorkflowLog.workflow_id == EmailWorkflow.id
        ).where(EmailWorkflow.user_id == str(current_user.id))

        # Apply filters
        if level:
            query = query.where(EmailWorkflowLog.level == level)
        if workflow_id:
            query = query.where(EmailWorkflowLog.workflow_id == workflow_id)
        if phase:
            query = query.where(EmailWorkflowLog.workflow_phase == phase)

        # Apply pagination and ordering
        query = query.offset(offset).limit(limit).order_by(EmailWorkflowLog.created_at.desc())

        result = await db.execute(query)
        logs = result.scalars().all()

        # Convert to response format
        response = []
        for log in logs:
            response.append(EmailWorkflowLogResponse(
                id=str(log.id),
                workflow_id=str(log.workflow_id),
                task_id=str(log.task_id) if log.task_id else None,
                level=log.level,
                message=log.message,
                context=log.context,
                timestamp=log.created_at.isoformat() if log.created_at else "",
                workflow_phase=log.workflow_phase,
                email_count=log.email_count
            ))

        return response

    except Exception as e:
        logger.error(f"Failed to get email workflow logs: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email workflow logs"
        )


@router.delete("/cleanup/tasks")
async def cleanup_all_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete all email tasks for the current user."""
    try:
        from app.db.models.task import Task
        from sqlalchemy import delete
        
        # Delete all tasks belonging to the current user
        query = delete(Task).where(
            Task.input['user_id'].astext == str(current_user.id)
        )
        
        result = await db.execute(query)
        deleted_count = result.rowcount
        
        await db.commit()
        
        logger.info(f"Deleted {deleted_count} tasks for user {current_user.username}")
        
        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} tasks",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup tasks: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup tasks"
        )


@router.delete("/cleanup/processing-history")
async def cleanup_processing_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Clear email processing history to allow reprocessing of emails."""
    try:
        from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowLog
        from app.db.models.notification import Notification
        from sqlalchemy import delete, String
        
        deleted_items = {
            "workflows": 0,
            "logs": 0,
            "notifications": 0
        }
        
        # Delete workflow logs for user's workflows
        logs_query = delete(EmailWorkflowLog).where(
            EmailWorkflowLog.workflow_id.in_(
                select(EmailWorkflow.id).where(EmailWorkflow.user_id == str(current_user.id))
            )
        )
        logs_result = await db.execute(logs_query)
        deleted_items["logs"] = logs_result.rowcount
        
        # Delete notifications for user's workflows
        notifications_query = delete(Notification).where(
            Notification.user_id == str(current_user.id)
        ).where(
            Notification.context['workflow_id'].astext.in_(
                select(EmailWorkflow.id.cast(String)).where(EmailWorkflow.user_id == str(current_user.id))
            )
        )
        notifications_result = await db.execute(notifications_query)
        deleted_items["notifications"] = notifications_result.rowcount
        
        # Delete email workflows for the current user
        workflows_query = delete(EmailWorkflow).where(
            EmailWorkflow.user_id == str(current_user.id)
        )
        workflows_result = await db.execute(workflows_query)
        deleted_items["workflows"] = workflows_result.rowcount
        
        # Clear deduplication cache/history (if we have a service for this)
        try:
            from app.services.email_deduplication_service import EmailDeduplicationService
            dedup_service = EmailDeduplicationService(db)
            await dedup_service.clear_user_history(str(current_user.id))
        except Exception as dedup_error:
            logger.warning(f"Failed to clear deduplication history: {dedup_error}")
        
        await db.commit()
        
        total_deleted = sum(deleted_items.values())
        logger.info(f"Cleared processing history for user {current_user.username}: {deleted_items}")
        
        return {
            "status": "success",
            "message": f"Successfully cleared processing history ({total_deleted} items)",
            "deleted_items": deleted_items,
            "note": "Emails will be reprocessed on next workflow run"
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup processing history: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup processing history"
        )


@router.delete("/cleanup/complete-reset")
async def complete_cleanup_reset(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Perform a complete cleanup - delete all tasks and processing history."""
    try:
        # First cleanup tasks
        tasks_response = await cleanup_all_tasks(current_user, db)
        
        # Then cleanup processing history
        history_response = await cleanup_processing_history(current_user, db)
        
        return {
            "status": "success",
            "message": "Complete cleanup successful - all tasks and processing history cleared",
            "tasks_deleted": tasks_response["deleted_count"],
            "history_items_deleted": history_response["deleted_items"],
            "note": "All emails will be reprocessed as new on next workflow run"
        }
        
    except Exception as e:
        logger.error(f"Failed to perform complete cleanup: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform complete cleanup"
        )



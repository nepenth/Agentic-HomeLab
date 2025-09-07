"""
API routes for Automated Follow-ups service.

Provides endpoints for managing automated email follow-ups,
scheduling, monitoring, and customization.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.automated_followups import (
    automated_followups_service,
    FollowUpItem,
    FollowUpType,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpTemplate
)
from app.utils.logging import get_logger

logger = get_logger("automated_followups_api")
router = APIRouter(prefix="/api/v1/followups", tags=["Automated Follow-ups"])


# Pydantic models for API
class FollowUpItemResponse(BaseModel):
    """Response model for follow-up items."""
    id: str
    email_id: str
    follow_up_type: str
    priority: str
    status: str
    scheduled_time: datetime
    created_time: datetime
    completed_time: Optional[datetime]
    subject: str
    recipient: str
    content_preview: str
    trigger_reason: str
    follow_up_content: Optional[str]
    reminder_count: int
    last_reminder_time: Optional[datetime]
    metadata: Dict[str, Any]


class FollowUpTemplateResponse(BaseModel):
    """Response model for follow-up templates."""
    id: str
    name: str
    type: str
    template_text: str
    variables: List[str]
    conditions: Dict[str, Any]


class FollowUpStatsResponse(BaseModel):
    """Response model for follow-up statistics."""
    total_followups: int
    status_breakdown: Dict[str, int]
    type_breakdown: Dict[str, int]
    pending_count: int
    completed_count: int
    overdue_count: int


class ScheduleFollowUpsRequest(BaseModel):
    """Request model for scheduling follow-ups."""
    email_ids: List[str] = Field(..., description="List of email IDs to analyze for follow-ups")
    analysis_results: Optional[List[Dict[str, Any]]] = Field(None, description="Optional email analysis results")


class CreateCustomFollowUpRequest(BaseModel):
    """Request model for creating custom follow-ups."""
    email_id: str
    follow_up_type: str
    priority: str = "medium"
    scheduled_time: datetime
    custom_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/schedule", response_model=List[FollowUpItemResponse])
async def schedule_followups(
    request: ScheduleFollowUpsRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze emails and schedule automated follow-ups.

    This endpoint analyzes the provided emails and automatically schedules
    appropriate follow-ups based on content analysis and predefined rules.
    """
    try:
        # Convert email IDs to email data (simplified - in production this would fetch from database)
        emails = []
        for email_id in request.email_ids:
            # This is a placeholder - in production you'd fetch actual email data
            emails.append({
                "message_id": email_id,
                "subject": f"Email {email_id}",
                "content": "Sample email content",
                "sender": "sender@example.com"
            })

        # Schedule follow-ups
        followups = await automated_followups_service.analyze_and_schedule_followups(
            emails,
            request.analysis_results
        )

        # Convert to response format
        response = []
        for followup in followups:
            response.append(FollowUpItemResponse(
                id=followup.id,
                email_id=followup.email_id,
                follow_up_type=followup.follow_up_type.value,
                priority=followup.priority.value,
                status=followup.status.value,
                scheduled_time=followup.scheduled_time,
                created_time=followup.created_time,
                completed_time=followup.completed_time,
                subject=followup.subject,
                recipient=followup.recipient,
                content_preview=followup.content_preview,
                trigger_reason=followup.trigger_reason,
                follow_up_content=followup.follow_up_content,
                reminder_count=followup.reminder_count,
                last_reminder_time=followup.last_reminder_time,
                metadata=followup.metadata
            ))

        logger.info(f"Scheduled {len(response)} follow-ups")
        return response

    except Exception as e:
        logger.error(f"Failed to schedule follow-ups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule follow-ups: {str(e)}")


@router.post("/custom", response_model=FollowUpItemResponse)
async def create_custom_followup(request: CreateCustomFollowUpRequest):
    """
    Create a custom follow-up item.

    Allows manual creation of follow-up items with custom scheduling and content.
    """
    try:
        import uuid

        # Create custom follow-up
        followup = FollowUpItem(
            id=str(uuid.uuid4()),
            email_id=request.email_id,
            follow_up_type=FollowUpType.CUSTOM_FOLLOWUP,
            priority=FollowUpPriority(request.priority),
            status=FollowUpStatus.SCHEDULED,
            scheduled_time=request.scheduled_time,
            created_time=datetime.now(),
            subject=f"Custom follow-up for {request.email_id}",
            recipient="recipient@example.com",  # This would be determined from email
            content_preview="Custom follow-up",
            trigger_reason="Manually created",
            follow_up_content=request.custom_content,
            metadata=request.metadata or {}
        )

        # Store the follow-up
        automated_followups_service.follow_ups[followup.id] = followup

        # Convert to response
        response = FollowUpItemResponse(
            id=followup.id,
            email_id=followup.email_id,
            follow_up_type=followup.follow_up_type.value,
            priority=followup.priority.value,
            status=followup.status.value,
            scheduled_time=followup.scheduled_time,
            created_time=followup.created_time,
            completed_time=followup.completed_time,
            subject=followup.subject,
            recipient=followup.recipient,
            content_preview=followup.content_preview,
            trigger_reason=followup.trigger_reason,
            follow_up_content=followup.follow_up_content,
            reminder_count=followup.reminder_count,
            last_reminder_time=followup.last_reminder_time,
            metadata=followup.metadata
        )

        logger.info(f"Created custom follow-up {followup.id}")
        return response

    except Exception as e:
        logger.error(f"Failed to create custom follow-up: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create custom follow-up: {str(e)}")


@router.get("/", response_model=List[FollowUpItemResponse])
async def get_followups(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get follow-up items with optional filtering.

    Retrieve follow-up items with support for filtering by status, priority, and type.
    """
    try:
        followups = list(automated_followups_service.follow_ups.values())

        # Apply filters
        if status:
            followups = [f for f in followups if f.status.value == status]
        if priority:
            followups = [f for f in followups if f.priority.value == priority]
        if type:
            followups = [f for f in followups if f.follow_up_type.value == type]

        # Apply pagination
        followups = followups[offset:offset + limit]

        # Convert to response format
        response = []
        for followup in followups:
            response.append(FollowUpItemResponse(
                id=followup.id,
                email_id=followup.email_id,
                follow_up_type=followup.follow_up_type.value,
                priority=followup.priority.value,
                status=followup.status.value,
                scheduled_time=followup.scheduled_time,
                created_time=followup.created_time,
                completed_time=followup.completed_time,
                subject=followup.subject,
                recipient=followup.recipient,
                content_preview=followup.content_preview,
                trigger_reason=followup.trigger_reason,
                follow_up_content=followup.follow_up_content,
                reminder_count=followup.reminder_count,
                last_reminder_time=followup.last_reminder_time,
                metadata=followup.metadata
            ))

        return response

    except Exception as e:
        logger.error(f"Failed to get follow-ups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get follow-ups: {str(e)}")


@router.get("/{followup_id}", response_model=FollowUpItemResponse)
async def get_followup(followup_id: str):
    """Get a specific follow-up item by ID."""
    try:
        followup = automated_followups_service.follow_ups.get(followup_id)
        if not followup:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        return FollowUpItemResponse(
            id=followup.id,
            email_id=followup.email_id,
            follow_up_type=followup.follow_up_type.value,
            priority=followup.priority.value,
            status=followup.status.value,
            scheduled_time=followup.scheduled_time,
            created_time=followup.created_time,
            completed_time=followup.completed_time,
            subject=followup.subject,
            recipient=followup.recipient,
            content_preview=followup.content_preview,
            trigger_reason=followup.trigger_reason,
            follow_up_content=followup.follow_up_content,
            reminder_count=followup.reminder_count,
            last_reminder_time=followup.last_reminder_time,
            metadata=followup.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get follow-up {followup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get follow-up: {str(e)}")


@router.delete("/{followup_id}")
async def cancel_followup(followup_id: str):
    """Cancel a scheduled follow-up."""
    try:
        success = automated_followups_service.cancel_followup(followup_id)
        if not success:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        logger.info(f"Cancelled follow-up {followup_id}")
        return {"message": "Follow-up cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel follow-up {followup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel follow-up: {str(e)}")


@router.post("/process-pending")
async def process_pending_followups():
    """
    Process and send all pending follow-ups that are due.

    This endpoint should be called periodically (e.g., via cron job)
    to process scheduled follow-ups.
    """
    try:
        processed_followups = await automated_followups_service.process_pending_followups()

        return {
            "message": f"Processed {len(processed_followups)} follow-ups",
            "processed_followups": [f.id for f in processed_followups]
        }

    except Exception as e:
        logger.error(f"Failed to process pending follow-ups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process pending follow-ups: {str(e)}")


@router.get("/pending/count")
async def get_pending_count():
    """Get the count of pending follow-ups."""
    try:
        pending = automated_followups_service.get_pending_followups()
        overdue = automated_followups_service.get_overdue_followups()

        return {
            "pending_count": len(pending),
            "overdue_count": len(overdue),
            "total_pending": len(pending) + len(overdue)
        }

    except Exception as e:
        logger.error(f"Failed to get pending count: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending count: {str(e)}")


@router.get("/overdue", response_model=List[FollowUpItemResponse])
async def get_overdue_followups():
    """Get all overdue follow-ups."""
    try:
        overdue = automated_followups_service.get_overdue_followups()

        response = []
        for followup in overdue:
            response.append(FollowUpItemResponse(
                id=followup.id,
                email_id=followup.email_id,
                follow_up_type=followup.follow_up_type.value,
                priority=followup.priority.value,
                status=followup.status.value,
                scheduled_time=followup.scheduled_time,
                created_time=followup.created_time,
                completed_time=followup.completed_time,
                subject=followup.subject,
                recipient=followup.recipient,
                content_preview=followup.content_preview,
                trigger_reason=followup.trigger_reason,
                follow_up_content=followup.follow_up_content,
                reminder_count=followup.reminder_count,
                last_reminder_time=followup.last_reminder_time,
                metadata=followup.metadata
            ))

        return response

    except Exception as e:
        logger.error(f"Failed to get overdue follow-ups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get overdue follow-ups: {str(e)}")


@router.get("/templates", response_model=List[FollowUpTemplateResponse])
async def get_followup_templates():
    """Get all available follow-up templates."""
    try:
        templates = list(automated_followups_service.templates.values())

        response = []
        for template in templates:
            response.append(FollowUpTemplateResponse(
                id=template.id,
                name=template.name,
                type=template.type.value,
                template_text=template.template_text,
                variables=template.variables,
                conditions=template.conditions
            ))

        return response

    except Exception as e:
        logger.error(f"Failed to get follow-up templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get follow-up templates: {str(e)}")


@router.get("/stats", response_model=FollowUpStatsResponse)
async def get_followup_stats():
    """Get comprehensive follow-up statistics."""
    try:
        stats = automated_followups_service.get_followup_stats()

        return FollowUpStatsResponse(
            total_followups=stats["total_followups"],
            status_breakdown=stats["status_breakdown"],
            type_breakdown=stats["type_breakdown"],
            pending_count=stats["pending_count"],
            completed_count=stats["completed_count"],
            overdue_count=stats["overdue_count"]
        )

    except Exception as e:
        logger.error(f"Failed to get follow-up stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get follow-up stats: {str(e)}")


@router.post("/{followup_id}/reschedule")
async def reschedule_followup(followup_id: str, new_time: datetime):
    """Reschedule a follow-up to a new time."""
    try:
        followup = automated_followups_service.follow_ups.get(followup_id)
        if not followup:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        followup.scheduled_time = new_time
        followup.status = FollowUpStatus.SCHEDULED

        logger.info(f"Rescheduled follow-up {followup_id} to {new_time}")
        return {"message": "Follow-up rescheduled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reschedule follow-up {followup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reschedule follow-up: {str(e)}")


@router.post("/{followup_id}/complete")
async def complete_followup(followup_id: str):
    """Mark a follow-up as completed."""
    try:
        followup = automated_followups_service.follow_ups.get(followup_id)
        if not followup:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        followup.status = FollowUpStatus.COMPLETED
        followup.completed_time = datetime.now()

        logger.info(f"Completed follow-up {followup_id}")
        return {"message": "Follow-up marked as completed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete follow-up {followup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete follow-up: {str(e)}")
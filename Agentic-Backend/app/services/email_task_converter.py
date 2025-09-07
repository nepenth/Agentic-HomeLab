"""
Email Task Converter Service for converting email analysis into actionable tasks.

This service takes email analysis results and creates appropriate tasks based on:
- Importance scores and urgency levels
- Required actions and deadlines
- Follow-up scheduling
- Task prioritization
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from app.services.email_analysis_service import EmailAnalysis
from app.db.models.task import Task, TaskStatus
from app.utils.logging import get_logger

logger = get_logger("email_task_converter")


@dataclass
class TaskCreationRequest:
    """Request to create a task from email analysis."""
    email_analysis: EmailAnalysis
    user_id: str
    email_content: str
    email_metadata: Dict[str, Any]
    priority_override: Optional[str] = None  # "low", "medium", "high", "urgent"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "email_analysis": self.email_analysis.to_dict(),
            "user_id": self.user_id,
            "email_content": self.email_content,
            "email_metadata": self.email_metadata,
            "priority_override": self.priority_override
        }


@dataclass
class TaskCreationResult:
    """Result of task creation from email analysis."""
    tasks_created: List[Task]
    follow_up_scheduled: bool
    follow_up_date: Optional[datetime]
    processing_time_ms: float
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tasks_created": [task.to_dict() for task in self.tasks_created],
            "follow_up_scheduled": self.follow_up_scheduled,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class TaskTemplate:
    """Template for creating tasks from email analysis."""
    name: str
    description: str
    priority: str
    estimated_duration_hours: float
    requires_follow_up: bool
    follow_up_days: int
    categories: List[str]
    action_keywords: List[str]


class EmailTaskConverter:
    """Service for converting email analysis into actionable tasks."""

    def __init__(self):
        self.logger = get_logger("email_task_converter")

        # Task templates based on email analysis
        self.task_templates = {
            "urgent_response": TaskTemplate(
                name="Urgent Email Response Required",
                description="Respond to urgent email requiring immediate attention",
                priority="urgent",
                estimated_duration_hours=1.0,
                requires_follow_up=True,
                follow_up_days=1,
                categories=["communication", "urgent"],
                action_keywords=["respond", "reply", "urgent", "asap"]
            ),
            "high_priority_review": TaskTemplate(
                name="High Priority Email Review",
                description="Review and respond to high-priority email",
                priority="high",
                estimated_duration_hours=2.0,
                requires_follow_up=True,
                follow_up_days=2,
                categories=["communication", "review"],
                action_keywords=["review", "important", "priority"]
            ),
            "meeting_scheduling": TaskTemplate(
                name="Schedule Meeting from Email",
                description="Schedule meeting or call based on email request",
                priority="high",
                estimated_duration_hours=0.5,
                requires_follow_up=True,
                follow_up_days=1,
                categories=["meeting", "scheduling"],
                action_keywords=["meeting", "call", "schedule", "appointment"]
            ),
            "task_assignment": TaskTemplate(
                name="Complete Task from Email",
                description="Complete specific task mentioned in email",
                priority="medium",
                estimated_duration_hours=4.0,
                requires_follow_up=True,
                follow_up_days=3,
                categories=["task", "work"],
                action_keywords=["task", "complete", "finish", "deadline"]
            ),
            "information_request": TaskTemplate(
                name="Provide Requested Information",
                description="Gather and provide information requested in email",
                priority="medium",
                estimated_duration_hours=2.0,
                requires_follow_up=True,
                follow_up_days=2,
                categories=["information", "research"],
                action_keywords=["information", "details", "data", "research"]
            ),
            "follow_up_needed": TaskTemplate(
                name="Follow Up on Previous Email",
                description="Follow up on previous email thread or conversation",
                priority="low",
                estimated_duration_hours=0.5,
                requires_follow_up=True,
                follow_up_days=7,
                categories=["follow_up", "communication"],
                action_keywords=["follow_up", "check", "update", "status"]
            ),
            "attachment_review": TaskTemplate(
                name="Review Email Attachments",
                description="Review and process email attachments",
                priority="medium",
                estimated_duration_hours=1.0,
                requires_follow_up=False,
                follow_up_days=0,
                categories=["review", "attachments"],
                action_keywords=["attachment", "file", "document", "review"]
            )
        }

        # Priority mapping
        self.priority_mapping = {
            "urgent": "urgent",
            "high": "high",
            "medium": "medium",
            "low": "low"
        }

    async def convert_to_tasks(
        self,
        request: TaskCreationRequest,
        db_session: Any = None
    ) -> TaskCreationResult:
        """
        Convert email analysis into actionable tasks.

        Args:
            request: Task creation request with email analysis
            db_session: Database session for creating tasks

        Returns:
            TaskCreationResult with created tasks and metadata
        """
        start_time = datetime.now()

        try:
            analysis = request.email_analysis

            # Skip task creation for low importance or spam emails
            if analysis.importance_score < 0.3 or analysis.spam_probability > 0.8:
                self.logger.info(f"Skipping task creation for low importance/spam email: {analysis.email_id}")
                return TaskCreationResult(
                    tasks_created=[],
                    follow_up_scheduled=False,
                    follow_up_date=None,
                    processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            # Determine task templates to use
            applicable_templates = self._select_task_templates(analysis, request.email_content)

            # Create tasks from templates
            tasks_created = []
            for template in applicable_templates:
                task = await self._create_task_from_template(
                    template, request, analysis, db_session
                )
                if task:
                    tasks_created.append(task)

            # Schedule follow-up if needed
            follow_up_scheduled = False
            follow_up_date = None

            if analysis.action_required and any(template.requires_follow_up for template in applicable_templates):
                follow_up_date = self._calculate_follow_up_date(analysis, applicable_templates)
                follow_up_scheduled = True

                # Create follow-up task
                followup_task = await self._create_followup_task(
                    request, analysis, follow_up_date, db_session
                )
                if followup_task:
                    tasks_created.append(followup_task)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            result = TaskCreationResult(
                tasks_created=tasks_created,
                follow_up_scheduled=follow_up_scheduled,
                follow_up_date=follow_up_date,
                processing_time_ms=processing_time
            )

            self.logger.info(f"Created {len(tasks_created)} tasks from email {analysis.email_id}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to convert email to tasks: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return TaskCreationResult(
                tasks_created=[],
                follow_up_scheduled=False,
                follow_up_date=None,
                processing_time_ms=processing_time
            )

    def _select_task_templates(self, analysis: EmailAnalysis, email_content: str) -> List[TaskTemplate]:
        """Select appropriate task templates based on email analysis."""
        applicable_templates = []

        # Check suggested actions first
        for action in analysis.suggested_actions:
            action_lower = action.lower()
            for template_name, template in self.task_templates.items():
                if any(keyword in action_lower for keyword in template.action_keywords):
                    if template not in applicable_templates:
                        applicable_templates.append(template)

        # Check categories
        for category in analysis.categories:
            category_lower = category.lower()
            for template_name, template in self.task_templates.items():
                if any(cat in category_lower for cat in template.categories):
                    if template not in applicable_templates:
                        applicable_templates.append(template)

        # Check urgency level
        if analysis.urgency_level in ["urgent", "high"]:
            urgent_template = self.task_templates.get("urgent_response")
            if urgent_template and urgent_template not in applicable_templates:
                applicable_templates.insert(0, urgent_template)  # Add to front

        # Check for attachments
        if analysis.attachment_analysis and analysis.attachment_analysis.get("has_attachments"):
            attachment_template = self.task_templates.get("attachment_review")
            if attachment_template and attachment_template not in applicable_templates:
                applicable_templates.append(attachment_template)

        # Default to general task if nothing matches
        if not applicable_templates:
            applicable_templates.append(self.task_templates.get("high_priority_review"))

        return applicable_templates[:3]  # Limit to top 3 templates

    async def _create_task_from_template(
        self,
        template: TaskTemplate,
        request: TaskCreationRequest,
        analysis: EmailAnalysis,
        db_session: Any = None
    ) -> Optional[Task]:
        """Create a task from a template."""
        try:
            # Determine final priority
            priority = request.priority_override or template.priority
            if analysis.urgency_level == "urgent":
                priority = "urgent"
            elif analysis.urgency_level == "high" and priority == "low":
                priority = "medium"

            # Calculate due date based on priority and urgency
            due_date = self._calculate_due_date(priority, analysis.urgency_level)

            # Create task description
            task_description = self._generate_task_description(template, request, analysis)

            # Create task input data
            task_input = {
                "email_id": analysis.email_id,
                "email_subject": request.email_metadata.get("subject", ""),
                "email_sender": request.email_metadata.get("sender", ""),
                "importance_score": analysis.importance_score,
                "categories": analysis.categories,
                "urgency_level": analysis.urgency_level,
                "key_topics": analysis.key_topics,
                "email_content_preview": request.email_content[:500] + "..." if len(request.email_content) > 500 else request.email_content
            }

            # Create task object with proper SQLAlchemy initialization
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID(self._get_agent_id_for_task(template, request)),
                status=TaskStatus.PENDING,
                input=task_input,
                created_at=datetime.now()
            )

            # In a real implementation, this would be saved to database
            if db_session:
                db_session.add(task)
                await db_session.commit()

            self.logger.debug(f"Created task from template '{template.name}' for email {analysis.email_id}")
            return task

        except Exception as e:
            self.logger.error(f"Failed to create task from template {template.name}: {e}")
            return None

    def _get_agent_id_for_task(self, template: TaskTemplate, request: TaskCreationRequest) -> str:
        """Determine which agent should handle this task."""
        # This is a simplified implementation
        # In a real system, this would map templates to specific agents
        agent_mapping = {
            "urgent_response": "email-responder-agent",
            "high_priority_review": "email-reviewer-agent",
            "meeting_scheduling": "calendar-agent",
            "task_assignment": "task-manager-agent",
            "information_request": "research-agent",
            "follow_up_needed": "followup-agent",
            "attachment_review": "document-reviewer-agent"
        }

        return agent_mapping.get(template.name.lower().replace(" ", "_"), "general-email-agent")

    def _calculate_due_date(self, priority: str, urgency_level: str) -> datetime:
        """Calculate task due date based on priority and urgency."""
        now = datetime.now()

        if urgency_level == "urgent":
            return now + timedelta(hours=2)
        elif urgency_level == "high":
            return now + timedelta(hours=4)
        elif priority == "high":
            return now + timedelta(hours=8)
        elif priority == "medium":
            return now + timedelta(days=1)
        else:  # low priority
            return now + timedelta(days=3)

    def _generate_task_description(self, template: TaskTemplate, request: TaskCreationRequest, analysis: EmailAnalysis) -> str:
        """Generate detailed task description."""
        subject = request.email_metadata.get("subject", "No Subject")
        sender = request.email_metadata.get("sender", "Unknown Sender")

        description = f"{template.description}\n\n"
        description += f"Email: {subject}\n"
        description += f"From: {sender}\n"
        description += f"Importance: {analysis.importance_score:.2f}\n"
        description += f"Urgency: {analysis.urgency_level}\n"

        if analysis.key_topics:
            description += f"Topics: {', '.join(analysis.key_topics)}\n"

        if analysis.suggested_actions:
            description += f"Suggested Actions: {', '.join(analysis.suggested_actions)}\n"

        return description

    def _calculate_follow_up_date(self, analysis: EmailAnalysis, templates: List[TaskTemplate]) -> datetime:
        """Calculate when follow-up should occur."""
        now = datetime.now()

        # Use the shortest follow-up period from applicable templates
        min_followup_days = min(template.follow_up_days for template in templates if template.requires_follow_up)

        # Adjust based on urgency
        if analysis.urgency_level == "urgent":
            min_followup_days = max(1, min_followup_days // 2)
        elif analysis.urgency_level == "high":
            min_followup_days = max(1, min_followup_days // 1.5)

        return now + timedelta(days=min_followup_days)

    async def _create_followup_task(
        self,
        request: TaskCreationRequest,
        analysis: EmailAnalysis,
        follow_up_date: datetime,
        db_session: Any = None
    ) -> Optional[Task]:
        """Create a follow-up task."""
        try:
            followup_template = self.task_templates.get("follow_up_needed")
            if not followup_template:
                return None

            # Create follow-up task input
            followup_input = {
                "email_id": analysis.email_id,
                "original_importance": analysis.importance_score,
                "follow_up_reason": "Check if original email was addressed",
                "scheduled_date": follow_up_date.isoformat(),
                "email_subject": request.email_metadata.get("subject", ""),
                "email_sender": request.email_metadata.get("sender", "")
            }

            # Create follow-up task
            followup_task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID(self._get_agent_id_for_task(followup_template, request)),
                status=TaskStatus.PENDING,
                input=followup_input,
                created_at=datetime.now()
            )

            # In a real implementation, this would be saved to database
            if db_session:
                db_session.add(followup_task)
                await db_session.commit()

            self.logger.debug(f"Created follow-up task for email {analysis.email_id}")
            return followup_task

        except Exception as e:
            self.logger.error(f"Failed to create follow-up task: {e}")
            return None

    async def batch_convert_emails(
        self,
        requests: List[TaskCreationRequest],
        db_session: Any = None
    ) -> List[TaskCreationResult]:
        """
        Convert multiple emails to tasks in batch.

        Args:
            requests: List of task creation requests
            db_session: Database session

        Returns:
            List of task creation results
        """
        try:
            # Process emails concurrently
            tasks = [self.convert_to_tasks(request, db_session) for request in requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to process email {i}: {result}")
                    # Return empty result for failed processing
                    processed_results.append(TaskCreationResult(
                        tasks_created=[],
                        follow_up_scheduled=False,
                        follow_up_date=None,
                        processing_time_ms=0.0
                    ))
                else:
                    processed_results.append(result)

            return processed_results

        except Exception as e:
            self.logger.error(f"Batch email processing failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "task_templates_count": len(self.task_templates),
            "priority_mapping": self.priority_mapping,
            "supported_urgency_levels": ["low", "medium", "high", "urgent"],
            "supported_priorities": ["low", "medium", "high", "urgent"]
        }


# Global instance
email_task_converter = EmailTaskConverter()
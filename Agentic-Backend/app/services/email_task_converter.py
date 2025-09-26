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
from app.db.models.task import Task, TaskStatus, LogLevel
from app.services.unified_log_service import unified_log_service, WorkflowType, LogScope
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

        # Create unified workflow context for task creation
        async with unified_log_service.workflow_context(
            user_id=int(request.user_id),
            workflow_type=WorkflowType.AGENT_TASK,
            workflow_name=f"Email task creation for {request.email_metadata.get('subject', 'Unknown')}",
            scope=LogScope.USER
        ) as workflow_context:

            try:
                analysis = request.email_analysis

                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.INFO,
                    message="Starting email task conversion",
                    component="email_task_converter",
                    extra_metadata={
                        "email_id": analysis.email_id,
                        "importance_score": analysis.importance_score,
                        "action_required": analysis.action_required,
                        "spam_probability": analysis.spam_probability
                    }
                )

                # Only skip obvious spam emails
                if analysis.spam_probability > 0.8:
                    await unified_log_service.log(
                        context=workflow_context,
                        level=LogLevel.INFO,
                        message="Skipping task creation for spam email",
                        component="email_task_converter",
                        extra_metadata={"spam_probability": analysis.spam_probability}
                    )
                    return TaskCreationResult(
                        tasks_created=[],
                        follow_up_scheduled=False,
                        follow_up_date=None,
                        processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                    )

                # Create appropriate tasks based on importance and analysis
                async with unified_log_service.task_context(
                    parent_context=workflow_context,
                    task_name="Create tasks from email analysis",
                    agent_id="task_creation_agent"
                ) as task_context:

                    tasks_created = await self._create_tasks_for_email_with_logging(
                        analysis, request, db_session, task_context
                    )

                    if not tasks_created:
                        await unified_log_service.log(
                            context=task_context,
                            level=LogLevel.INFO,
                            message="No specific tasks identified, creating general review task",
                            component="email_task_converter"
                        )
                        # If no specific tasks created, create a general review task
                        review_task = await self._create_review_task_with_logging(
                            analysis, request, db_session, task_context
                        )
                        if review_task:
                            tasks_created = [review_task]

                    await unified_log_service.log(
                        context=task_context,
                        level=LogLevel.INFO,
                        message=f"Created {len(tasks_created)} tasks from email",
                        component="email_task_converter",
                        extra_metadata={"tasks_count": len(tasks_created)}
                    )

                # If we created custom tasks, use those instead of templates
                if tasks_created:
                    # Schedule follow-up if needed for high importance emails
                    follow_up_scheduled = False
                    follow_up_date = None

                    if analysis.importance_score >= 0.7 and analysis.action_required:
                        follow_up_date = datetime.now() + timedelta(days=3)  # Follow up in 3 days
                        follow_up_scheduled = True

                        await unified_log_service.log(
                            context=workflow_context,
                            level=LogLevel.INFO,
                            message="Scheduled follow-up for high importance email",
                            component="email_task_converter",
                            extra_metadata={
                                "follow_up_date": follow_up_date.isoformat(),
                                "importance_score": analysis.importance_score
                            }
                        )

                    processing_time = (datetime.now() - start_time).total_seconds() * 1000

                    await unified_log_service.log(
                        context=workflow_context,
                        level=LogLevel.INFO,
                        message="Email task conversion completed successfully",
                        component="email_task_converter",
                        extra_metadata={
                            "processing_time_ms": processing_time,
                            "tasks_created": len(tasks_created),
                            "follow_up_scheduled": follow_up_scheduled
                        }
                    )
                
                    return TaskCreationResult(
                        tasks_created=tasks_created,
                        follow_up_scheduled=follow_up_scheduled,
                        follow_up_date=follow_up_date,
                        processing_time_ms=processing_time
                    )

                # If no tasks were created from analysis, fallback to template approach
                if not tasks_created:
                    await unified_log_service.log(
                        context=workflow_context,
                        level=LogLevel.INFO,
                        message="No tasks created, using fallback template approach",
                        component="email_task_converter"
                    )

                    # Determine task templates to use
                    applicable_templates = self._select_task_templates(analysis, request.email_content)

                    # Create tasks from templates
                    template_tasks = []
                    for template in applicable_templates:
                        task = await self._create_task_from_template(
                            template, request, analysis, db_session
                        )
                        if task:
                            template_tasks.append(task)

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
                            template_tasks.append(followup_task)

                    processing_time = (datetime.now() - start_time).total_seconds() * 1000

                    await unified_log_service.log(
                        context=workflow_context,
                        level=LogLevel.INFO,
                        message=f"Template approach created {len(template_tasks)} tasks",
                        component="email_task_converter",
                        extra_metadata={
                            "template_tasks": len(template_tasks),
                            "follow_up_scheduled": follow_up_scheduled
                        }
                    )

                    return TaskCreationResult(
                        tasks_created=template_tasks,
                        follow_up_scheduled=follow_up_scheduled,
                        follow_up_date=follow_up_date,
                        processing_time_ms=processing_time
                    )

            except Exception as e:
                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.ERROR,
                    message="Failed to convert email to tasks",
                    component="email_task_converter",
                    error=e
                )
                processing_time = (datetime.now() - start_time).total_seconds() * 1000

                return TaskCreationResult(
                    tasks_created=[],
                    follow_up_scheduled=False,
                    follow_up_date=None,
                    processing_time_ms=processing_time
                )

    async def _create_tasks_for_email_with_logging(
        self,
        analysis: EmailAnalysis,
        request: TaskCreationRequest,
        db_session: Any,
        task_context
    ) -> List[Task]:
        """Create tasks for email with unified logging."""
        try:
            await unified_log_service.log(
                context=task_context,
                level=LogLevel.INFO,
                message="Analyzing email for task creation",
                component="email_task_converter",
                extra_metadata={
                    "importance_score": analysis.importance_score,
                    "action_required": analysis.action_required,
                    "urgency_level": analysis.urgency_level,
                    "sentiment": analysis.sentiment
                }
            )

            tasks = self._create_tasks_for_email(analysis, request, db_session)

            await unified_log_service.log(
                context=task_context,
                level=LogLevel.INFO,
                message=f"Task analysis complete - {len(tasks)} tasks identified",
                component="email_task_converter",
                extra_metadata={"tasks_identified": len(tasks)}
            )

            return tasks

        except Exception as e:
            await unified_log_service.log(
                context=task_context,
                level=LogLevel.ERROR,
                message="Failed to create tasks from email",
                component="email_task_converter",
                error=e
            )
            return []

    async def _create_review_task_with_logging(
        self,
        analysis: EmailAnalysis,
        request: TaskCreationRequest,
        db_session: Any,
        task_context
    ) -> Optional[Task]:
        """Create review task with unified logging."""
        try:
            await unified_log_service.log(
                context=task_context,
                level=LogLevel.INFO,
                message="Creating general review task",
                component="email_task_converter"
            )

            task = self._create_review_task(analysis, request, db_session)

            if task:
                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.INFO,
                    message="Review task created successfully",
                    component="email_task_converter",
                    extra_metadata={"task_id": str(task.id)}
                )

            return task

        except Exception as e:
            await unified_log_service.log(
                context=task_context,
                level=LogLevel.ERROR,
                message="Failed to create review task",
                component="email_task_converter",
                error=e
            )
            return None

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
                "user_id": request.user_id,
                "email_id": analysis.email_id,
                "email_subject": request.email_metadata.get("subject", ""),
                "email_sender": request.email_metadata.get("sender", ""),
                "email_content": request.email_content,
                "email_metadata": request.email_metadata,
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


    def _create_tasks_for_email(self, analysis: EmailAnalysis, request: TaskCreationRequest, db_session: Any = None) -> List[Task]:
        """Create appropriate tasks based on email analysis."""
        tasks = []
        
        # Determine task priority based on importance and urgency
        priority = self._determine_task_priority(analysis)
        
        # Create specific task types based on email content and importance
        if analysis.importance_score >= 0.7:
            # High importance - create specific action tasks
            if "meeting" in analysis.content_summary.lower() or "schedule" in analysis.content_summary.lower():
                task = self._create_calendar_task(analysis, request, priority, db_session)
                if task: tasks.append(task)
            elif "invoice" in analysis.content_summary.lower() or "payment" in analysis.content_summary.lower():
                task = self._create_finance_task(analysis, request, priority, db_session)
                if task: tasks.append(task)
            elif any(cat in ["work/business"] for cat in analysis.categories):
                task = self._create_business_task(analysis, request, priority, db_session)
                if task: tasks.append(task)
            else:
                task = self._create_action_task(analysis, request, priority, db_session)
                if task: tasks.append(task)
                
        elif analysis.importance_score >= 0.5:
            # Medium importance - create review/response tasks
            task = self._create_response_task(analysis, request, priority, db_session)
            if task: tasks.append(task)
            
        elif analysis.importance_score >= 0.4:
            # Lower importance - create review tasks
            task = self._create_review_task(analysis, request, priority, db_session)
            if task: tasks.append(task)
            
        return tasks
    
    def _determine_task_priority(self, analysis: EmailAnalysis) -> str:
        """Determine task priority based on email analysis."""
        if analysis.urgency_level == "urgent" or analysis.importance_score >= 0.8:
            return "urgent"
        elif analysis.urgency_level == "high" or analysis.importance_score >= 0.7:
            return "high"
        elif analysis.urgency_level == "medium" or analysis.importance_score >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _create_review_task(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str = "low", db_session: Any = None) -> Optional[Task]:
        """Create a general email review task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Review email from {sender}: {subject}"
            if analysis.content_summary:
                description += f"\n\nSummary: {analysis.content_summary[:200]}..."
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # Default agent ID
                status=TaskStatus.PENDING,
                input={
                    "type": "email_review",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "categories": analysis.categories,
                    "suggested_actions": analysis.suggested_actions,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create review task: {e}")
            return None
    
    def _create_action_task(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a specific action task for high-importance emails."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            # Generate specific action description based on suggested actions
            action_description = "Take action on email"
            if analysis.suggested_actions:
                action_description = analysis.suggested_actions[0]
            
            description = f"ACTION REQUIRED: {action_description} - Email from {sender}: {subject}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "email_action",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "urgency_level": analysis.urgency_level,
                    "suggested_actions": analysis.suggested_actions,
                    "categories": analysis.categories,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create action task: {e}")
            return None
    
    def _create_response_task(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a response task for medium-importance emails."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Respond to email from {sender}: {subject}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "email_response",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "suggested_actions": analysis.suggested_actions,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create response task: {e}")
            return None
    
    def _create_business_task(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a business-specific task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Business Action: {subject} from {sender}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "business_email",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "categories": analysis.categories,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create business task: {e}")
            return None
    
    def _create_calendar_task(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a calendar/meeting task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Schedule/Meeting: {subject} from {sender}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "calendar_email",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create calendar task: {e}")
            return None
    
    def _create_finance_task(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a finance-related task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Finance: {subject} from {sender}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "finance_email",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create finance task: {e}")
            return None

# Global instance
email_task_converter = EmailTaskConverter()


class SyncEmailTaskConverter:
    """Synchronous version of EmailTaskConverter for use in Celery tasks."""

    def __init__(self, user_id: str = None):
        from app.config import settings
        self.async_converter = EmailTaskConverter()
        self.user_id = user_id
        # Load settings from database if user_id provided, otherwise use defaults
        self.task_timeout = self._get_task_timeout()

    def _get_task_timeout(self) -> int:
        """Get task conversion timeout from database settings or use default."""
        if not self.user_id:
            from app.config import settings
            return getattr(settings, 'email_workflow_task_timeout', 60)

        try:
            # Import here to avoid circular imports
            from app.db.models.email_workflow import EmailWorkflowSettings
            from sqlalchemy.ext.asyncio import AsyncSession
            from app.db.database import get_db_session

            # This is a synchronous context, so we need to be careful
            # For now, return default and load dynamically when needed
            return 60
        except Exception:
            from app.config import settings
            return getattr(settings, 'email_workflow_task_timeout', 60)

    def convert_to_tasks(
        self,
        request: TaskCreationRequest,
        db_session: Any = None
    ) -> TaskCreationResult:
        """Synchronous task conversion with improved logic."""
        start_time = datetime.now()
        
        try:
            analysis = request.email_analysis
            
            # Only skip obvious spam emails
            if analysis.spam_probability > 0.8:
                logger.info(f"Skipping task creation for spam email: {analysis.email_id}")
                return TaskCreationResult(
                    tasks_created=[],
                    follow_up_scheduled=False,
                    follow_up_date=None,
                    processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            
            # Create appropriate tasks based on importance and analysis
            tasks_created = self._create_tasks_for_email_sync(analysis, request, db_session)
            
            if not tasks_created:
                # If no specific tasks created, create a general review task
                review_task = self._create_review_task_sync(analysis, request, db_session)
                if review_task:
                    tasks_created = [review_task]
            
            # Schedule follow-up if needed for high importance emails
            follow_up_scheduled = False
            follow_up_date = None
            
            if analysis.importance_score >= 0.7 and analysis.action_required:
                follow_up_date = datetime.now() + timedelta(days=3)  # Follow up in 3 days
                follow_up_scheduled = True
                
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return TaskCreationResult(
                tasks_created=tasks_created,
                follow_up_scheduled=follow_up_scheduled,
                follow_up_date=follow_up_date,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Task conversion failed: {e}")
            return TaskCreationResult(
                    tasks_created=[],
                    follow_up_scheduled=False,
                    follow_up_date=None,
                    processing_time_ms=0.0
                )

    def _run_conversion_in_thread(
        self,
        request: TaskCreationRequest,
        db_session: Any = None
    ) -> TaskCreationResult:
        """Run conversion in a separate thread with its own event loop."""
        import asyncio

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run the async conversion
            return loop.run_until_complete(
                self.async_converter.convert_to_tasks(request, db_session)
            )
        finally:
            try:
                loop.close()
            except Exception:
                pass  # Ignore cleanup errors

    def _create_tasks_for_email_sync(self, analysis: EmailAnalysis, request: TaskCreationRequest, db_session: Any = None) -> List[Task]:
        """Synchronous version of create tasks for email."""
        tasks = []
        
        # Determine task priority based on importance and urgency
        priority = self._determine_task_priority_sync(analysis)
        
        # Create specific task types based on email content and importance
        if analysis.importance_score >= 0.7:
            # High importance - create specific action tasks
            if "meeting" in analysis.content_summary.lower() or "schedule" in analysis.content_summary.lower():
                task = self._create_calendar_task_sync(analysis, request, priority, db_session)
                if task: tasks.append(task)
            elif "invoice" in analysis.content_summary.lower() or "payment" in analysis.content_summary.lower():
                task = self._create_finance_task_sync(analysis, request, priority, db_session)
                if task: tasks.append(task)
            elif any(cat in ["work/business"] for cat in analysis.categories):
                task = self._create_business_task_sync(analysis, request, priority, db_session)
                if task: tasks.append(task)
            else:
                task = self._create_action_task_sync(analysis, request, priority, db_session)
                if task: tasks.append(task)
                
        elif analysis.importance_score >= 0.5:
            # Medium importance - create review/response tasks
            task = self._create_response_task_sync(analysis, request, priority, db_session)
            if task: tasks.append(task)
            
        elif analysis.importance_score >= 0.4:
            # Lower importance - create review tasks
            task = self._create_review_task_sync(analysis, request, priority, db_session)
            if task: tasks.append(task)
            
        return tasks
    
    def _determine_task_priority_sync(self, analysis: EmailAnalysis) -> str:
        """Determine task priority based on email analysis."""
        if analysis.urgency_level == "urgent" or analysis.importance_score >= 0.8:
            return "urgent"
        elif analysis.urgency_level == "high" or analysis.importance_score >= 0.7:
            return "high"
        elif analysis.urgency_level == "medium" or analysis.importance_score >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _create_review_task_sync(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str = "low", db_session: Any = None) -> Optional[Task]:
        """Create a general email review task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Review email from {sender}: {subject}"
            if analysis.content_summary:
                description += f"\n\nSummary: {analysis.content_summary[:200]}..."
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "email_review",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "categories": analysis.categories,
                    "suggested_actions": analysis.suggested_actions,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create review task: {e}")
            return None
    
    def _create_action_task_sync(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a specific action task for high-importance emails."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            # Generate specific action description based on suggested actions
            action_description = "Take action on email"
            if analysis.suggested_actions:
                action_description = analysis.suggested_actions[0]
            
            description = f"ACTION REQUIRED: {action_description} - Email from {sender}: {subject}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "email_action",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "urgency_level": analysis.urgency_level,
                    "suggested_actions": analysis.suggested_actions,
                    "categories": analysis.categories,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create action task: {e}")
            return None
    
    def _create_response_task_sync(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a response task for medium-importance emails."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Respond to email from {sender}: {subject}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "email_response",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "suggested_actions": analysis.suggested_actions,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create response task: {e}")
            return None
    
    def _create_business_task_sync(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a business-specific task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Business Action: {subject} from {sender}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "business_email",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "categories": analysis.categories,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create business task: {e}")
            return None
    
    def _create_calendar_task_sync(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a calendar/meeting task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Schedule/Meeting: {subject} from {sender}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "calendar_email",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create calendar task: {e}")
            return None
    
    def _create_finance_task_sync(self, analysis: EmailAnalysis, request: TaskCreationRequest, priority: str, db_session: Any = None) -> Optional[Task]:
        """Create a finance-related task."""
        try:
            sender = request.email_metadata.get("sender", "Unknown sender")
            subject = request.email_metadata.get("subject", "No subject")
            
            description = f"Finance: {subject} from {sender}"
            
            task = Task(
                id=uuid.uuid4(),
                agent_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                status=TaskStatus.PENDING,
                input={
                    "type": "finance_email",
                    "description": description,
                    "priority": priority,
                    "email_id": analysis.email_id,
                    "email_sender": sender,
                    "email_subject": subject,
                    "email_content": request.email_content,
                    "email_metadata": request.email_metadata,
                    "importance_score": analysis.importance_score,
                    "user_id": request.user_id
                },
                created_at=datetime.now()
            )
            
            if db_session:
                db_session.add(task)
                
            return task
            
        except Exception as e:
            logger.error(f"Failed to create finance task: {e}")
            return None


# Global sync instance for Celery tasks
sync_email_task_converter = SyncEmailTaskConverter()
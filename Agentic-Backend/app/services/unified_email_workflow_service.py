"""
Unified Email Workflow Service

Modern agentic approach that uses locally synced emails with embeddings
for intelligent task creation instead of fetching emails live.

This service:
- Uses the local emails database as the single source of truth
- Applies workflow settings as intelligent filters on local emails
- Leverages existing embeddings for semantic task creation
- Maintains consistency between chat and workflow systems
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.db.models.email import Email, EmailAccount, EmailEmbedding
from app.db.models.user import User
from app.db.models.task import Task, TaskStatus, TaskPriority
from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus
from app.services.email_task_converter import email_task_converter, TaskCreationRequest
from app.services.unified_log_service import unified_log_service, WorkflowType, LogScope
from app.services.email_embedding_service import EmailEmbeddingService
from app.services.semantic_processing_service import semantic_processing_service
from app.utils.logging import get_logger

logger = get_logger("unified_email_workflow_service")


class UnifiedEmailWorkflowService:
    """Service for processing locally synced emails into intelligent tasks."""

    def __init__(self):
        self.logger = get_logger("unified_email_workflow_service")
        self.embedding_service = EmailEmbeddingService()

    async def process_workflow_from_synced_emails(
        self,
        db: AsyncSession,
        user_id: int,
        workflow_id: str,
        processing_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process locally synced emails for task creation using workflow settings.

        This is the modern approach that leverages:
        - Local email storage (single source of truth)
        - Existing embeddings for semantic intelligence
        - User workflow settings for filtering
        - Efficient processing without redundant email fetching
        """

        async with unified_log_service.workflow_context(
            user_id=user_id,
            workflow_type=WorkflowType.EMAIL_SYNC,
            workflow_name=f"Unified email workflow {workflow_id}",
            scope=LogScope.USER
        ) as workflow_context:

            try:
                # Get user's email accounts
                accounts_query = select(EmailAccount).where(
                    EmailAccount.user_id == user_id
                ).options(selectinload(EmailAccount.emails))

                accounts_result = await db.execute(accounts_query)
                accounts = accounts_result.scalars().all()

                if not accounts:
                    return {
                        "success": False,
                        "error": "No email accounts configured for user",
                        "emails_processed": 0,
                        "tasks_created": 0
                    }

                # Apply workflow settings to filter local emails
                emails_to_process = await self._get_filtered_emails(
                    db, user_id, accounts, processing_options
                )

                self.logger.info(f"Found {len(emails_to_process)} emails to process for workflow {workflow_id}")

                if not emails_to_process:
                    return {
                        "success": True,
                        "message": "No emails found matching workflow criteria",
                        "emails_processed": 0,
                        "tasks_created": 0
                    }

                # Group emails by semantic similarity to optimize task creation
                email_groups = await self._group_emails_by_similarity(
                    db, emails_to_process, processing_options
                )

                # Process emails using existing embeddings and intelligence
                tasks_created = await self._create_intelligent_tasks(
                    db, email_groups, processing_options, workflow_context
                )

                # Mark emails as processed
                email_ids = [email.id for email in emails_to_process]
                await self._mark_emails_processed(db, email_ids)

                await unified_log_service.log(
                    workflow_context,
                    "INFO",
                    f"Workflow completed: processed {len(emails_to_process)} emails, created {tasks_created} tasks",
                    "unified_workflow"
                )

                return {
                    "success": True,
                    "emails_processed": len(emails_to_process),
                    "tasks_created": tasks_created,
                    "message": f"Successfully processed {len(emails_to_process)} local emails"
                }

            except Exception as e:
                self.logger.error(f"Unified workflow failed: {e}")
                await unified_log_service.log(
                    workflow_context,
                    "ERROR",
                    f"Workflow failed: {str(e)}",
                    "unified_workflow",
                    error=e
                )
                raise

    async def _get_filtered_emails(
        self,
        db: AsyncSession,
        user_id: int,
        accounts: List[EmailAccount],
        processing_options: Dict[str, Any]
    ) -> List[Email]:
        """
        Filter locally synced emails based on workflow settings.
        This replaces live email fetching with intelligent local filtering.
        """

        # Extract workflow settings (supporting both old and new format)
        max_emails = processing_options.get('max_emails', processing_options.get('max_emails_per_workflow', 50))
        importance_threshold = processing_options.get('importance_threshold', 0.7)
        spam_threshold = processing_options.get('spam_threshold', 0.8)
        unread_only = processing_options.get('unread_only', False)
        since_date = processing_options.get('since_date')
        days_back = processing_options.get('days_back', 7)  # Default to last week

        # Enhanced workflow settings from EmailWorkflowSettings model
        default_task_priority = processing_options.get('default_task_priority',
                                                      processing_options.get('default_priority', 'medium'))
        create_tasks_automatically = processing_options.get('create_tasks_automatically', True)
        schedule_followups = processing_options.get('schedule_followups', False)
        process_attachments = processing_options.get('process_attachments', False)

        # Additional filtering options for advanced workflows
        sender_filter = processing_options.get('sender_filter')  # Filter by sender domain/email
        category_filter = processing_options.get('category_filter')  # Filter by email category
        thread_filter = processing_options.get('thread_filter')  # Include/exclude threaded emails
        attachment_filter = processing_options.get('attachment_filter')  # Filter by attachment presence

        # Build query filters
        filters = [
            Email.user_id == user_id,
            Email.tasks_generated == False,  # Only process emails that haven't had tasks created
            Email.is_spam == False,  # Exclude spam
            Email.is_deleted == False,  # Exclude deleted
        ]

        # Account filtering
        account_ids = [account.id for account in accounts]
        if account_ids:
            filters.append(Email.account_id.in_(account_ids))

        # Importance filtering
        if importance_threshold:
            filters.append(Email.importance_score >= importance_threshold)

        # Unread filtering
        if unread_only:
            filters.append(Email.is_read == False)

        # Date filtering
        if since_date:
            since_dt = datetime.fromisoformat(since_date.replace('Z', '+00:00'))
            filters.append(Email.received_at >= since_dt)
        elif days_back:
            since_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
            filters.append(Email.received_at >= since_dt)

        # Advanced filtering options
        if sender_filter:
            if isinstance(sender_filter, dict):
                # Support complex sender filtering
                if sender_filter.get('domains'):
                    domain_conditions = []
                    for domain in sender_filter['domains']:
                        domain_conditions.append(Email.sender_email.like(f'%@{domain}'))
                    if domain_conditions:
                        filters.append(or_(*domain_conditions))

                if sender_filter.get('emails'):
                    filters.append(Email.sender_email.in_(sender_filter['emails']))

                if sender_filter.get('exclude_domains'):
                    for domain in sender_filter['exclude_domains']:
                        filters.append(~Email.sender_email.like(f'%@{domain}'))
            else:
                # Simple sender filter (string)
                filters.append(Email.sender_email.like(f'%{sender_filter}%'))

        # Category filtering
        if category_filter:
            if isinstance(category_filter, list):
                filters.append(Email.category.in_(category_filter))
            else:
                filters.append(Email.category == category_filter)

        # Attachment filtering
        if attachment_filter is not None:
            if attachment_filter:
                filters.append(Email.has_attachments == True)
            else:
                filters.append(Email.has_attachments == False)

        # Query with embeddings for semantic processing
        query = select(Email).where(and_(*filters)).options(
            selectinload(Email.embeddings),
            selectinload(Email.account)
        ).order_by(desc(Email.received_at)).limit(max_emails)

        result = await db.execute(query)
        return result.scalars().all()

    async def _group_emails_by_similarity(
        self,
        db: AsyncSession,
        emails: List[Email],
        processing_options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Group emails by semantic similarity using existing embeddings.
        This creates intelligent email groups to optimize task creation.
        """

        similarity_threshold = processing_options.get('similarity_threshold', 0.8)
        enable_grouping = processing_options.get('enable_semantic_grouping', True)

        if not enable_grouping:
            # Return each email as its own group
            return [{"primary_email": email, "related_emails": [], "group_type": "single"} for email in emails]

        email_groups = []
        processed_emails = set()

        for email in emails:
            if email.id in processed_emails:
                continue

            # Find similar emails using embeddings
            similar_emails = await self._find_similar_emails(
                db, email, emails, similarity_threshold
            )

            # Create email group
            group = {
                "primary_email": email,
                "related_emails": [e for e in similar_emails if e.id != email.id],
                "group_type": "similar" if similar_emails else "single",
                "similarity_scores": {},  # To be filled by _find_similar_emails
                "semantic_keywords": await self._extract_semantic_keywords(email),
                "group_priority": max([e.importance_score for e in [email] + similar_emails])
            }

            email_groups.append(group)

            # Mark all emails in this group as processed
            for similar_email in [email] + similar_emails:
                processed_emails.add(similar_email.id)

        self.logger.info(
            f"Grouped {len(emails)} emails into {len(email_groups)} semantic groups "
            f"(threshold: {similarity_threshold})"
        )

        return email_groups

    async def _find_similar_emails(
        self,
        db: AsyncSession,
        target_email: Email,
        candidate_emails: List[Email],
        similarity_threshold: float
    ) -> List[Email]:
        """Find emails similar to target email using embedding cosine similarity."""

        if not target_email.embeddings_generated:
            return []

        try:
            # Get target email's combined embedding
            target_embedding_query = select(EmailEmbedding).where(
                and_(
                    EmailEmbedding.email_id == target_email.id,
                    EmailEmbedding.embedding_type == "combined"
                )
            )
            result = await db.execute(target_embedding_query)
            target_embedding = result.scalar_one_or_none()

            if not target_embedding or not target_embedding.embedding_vector:
                return []

            similar_emails = []
            candidate_ids = [email.id for email in candidate_emails if email.embeddings_generated]

            if not candidate_ids:
                return []

            # Query for similar embeddings using pgvector
            similarity_query = select(
                EmailEmbedding,
                EmailEmbedding.embedding_vector.cosine_distance(target_embedding.embedding_vector).label('distance')
            ).where(
                and_(
                    EmailEmbedding.email_id.in_(candidate_ids),
                    EmailEmbedding.embedding_type == "combined",
                    EmailEmbedding.embedding_vector.cosine_distance(target_embedding.embedding_vector) < (1 - similarity_threshold)
                )
            ).order_by('distance')

            result = await db.execute(similarity_query)
            similar_embeddings = result.all()

            # Get corresponding emails
            for embedding_row in similar_embeddings:
                embedding, distance = embedding_row
                similarity_score = 1 - distance  # Convert distance to similarity

                # Find the email object
                for email in candidate_emails:
                    if email.id == embedding.email_id:
                        similar_emails.append(email)
                        break

            return similar_emails

        except Exception as e:
            self.logger.warning(f"Error finding similar emails: {e}")
            return []

    async def _extract_semantic_keywords(self, email: Email) -> List[str]:
        """Extract semantic keywords from email content using embeddings context."""

        # Simple keyword extraction based on email content
        # In a more advanced implementation, this could use LLM analysis
        keywords = []

        # Extract from subject
        if email.subject:
            # Simple keyword extraction - could be enhanced with NLP
            subject_words = email.subject.lower().split()
            keywords.extend([word for word in subject_words if len(word) > 3])

        # Extract from category
        if email.category:
            keywords.append(email.category.lower())

        # Extract from sender domain
        if email.sender_email and '@' in email.sender_email:
            domain = email.sender_email.split('@')[1].split('.')[0]
            keywords.append(f"domain_{domain}")

        return list(set(keywords))[:10]  # Limit to 10 keywords

    async def _create_intelligent_tasks(
        self,
        db: AsyncSession,
        email_groups: List[Dict[str, Any]],
        processing_options: Dict[str, Any],
        workflow_context
    ) -> int:
        """
        Create intelligent tasks from email groups using existing embeddings and semantic analysis.
        This leverages semantic grouping and local intelligence instead of re-processing emails.
        """

        async with unified_log_service.task_context(
            parent_context=workflow_context,
            task_name="Create intelligent tasks from grouped emails",
            agent_id="unified_email_agent"
        ) as task_context:

            tasks_created = 0
            default_priority = processing_options.get('default_task_priority',
                                                     processing_options.get('default_priority', 'medium'))
            create_tasks_automatically = processing_options.get('create_tasks_automatically', True)
            schedule_followups = processing_options.get('schedule_followups', False)
            process_attachments = processing_options.get('process_attachments', False)
            group_similar_tasks = processing_options.get('group_similar_tasks', True)

            if not create_tasks_automatically:
                await unified_log_service.log(
                    task_context,
                    "INFO",
                    "Task creation disabled in workflow settings",
                    "task_creator"
                )
                return 0

            # Process email groups instead of individual emails
            for email_group in email_groups:
                try:
                    primary_email = email_group["primary_email"]
                    related_emails = email_group["related_emails"]
                    group_type = email_group["group_type"]
                    semantic_keywords = email_group["semantic_keywords"]

                    # Determine task priority based on group priority
                    task_priority = self._determine_task_priority(
                        email_group["group_priority"],
                        primary_email.urgency_score,
                        default_priority
                    )

                    if group_similar_tasks and group_type == "similar" and related_emails:
                        # Create a single consolidated task for similar emails
                        task_title = self._generate_group_task_title(primary_email, related_emails)
                        task_description = self._generate_group_task_description(
                            primary_email, related_emails, semantic_keywords, process_attachments
                        )

                        # Enhanced metadata for grouped task
                        task_metadata = {
                            "email_subject": primary_email.subject,
                            "sender": primary_email.sender_email,
                            "importance_score": email_group["group_priority"],
                            "urgency_score": primary_email.urgency_score,
                            "has_embeddings": primary_email.embeddings_generated,
                            "account_id": str(primary_email.account_id),
                            "workflow_approach": "unified_local_emails_grouped",
                            "schedule_followups": schedule_followups,
                            "process_attachments": process_attachments,
                            "group_type": group_type,
                            "related_email_count": len(related_emails),
                            "semantic_keywords": semantic_keywords,
                            "related_email_ids": [str(e.id) for e in related_emails],
                            "total_attachments": sum([getattr(e, 'attachment_count', 0) for e in [primary_email] + related_emails])
                        }

                        task_request = TaskCreationRequest(
                            title=task_title,
                            description=task_description,
                            priority=task_priority,
                            source_email_id=str(primary_email.id),
                            category=primary_email.category or "email",
                            metadata=task_metadata
                        )

                        # Create consolidated task
                        task_result = await email_task_converter.create_task_from_request(
                            db, primary_email.user_id, task_request
                        )

                        if task_result.get('success'):
                            tasks_created += 1
                            self.logger.debug(
                                f"Created grouped task for {len(related_emails) + 1} similar emails "
                                f"(primary: {primary_email.id})"
                            )

                    else:
                        # Create individual task for primary email only
                        task_metadata = {
                            "email_subject": primary_email.subject,
                            "sender": primary_email.sender_email,
                            "importance_score": primary_email.importance_score,
                            "urgency_score": primary_email.urgency_score,
                            "has_embeddings": primary_email.embeddings_generated,
                            "account_id": str(primary_email.account_id),
                            "workflow_approach": "unified_local_emails",
                            "schedule_followups": schedule_followups,
                            "process_attachments": process_attachments,
                            "semantic_keywords": semantic_keywords,
                            "has_attachments": getattr(primary_email, 'has_attachments', False),
                            "attachment_count": getattr(primary_email, 'attachment_count', 0),
                            "thread_id": getattr(primary_email, 'thread_id', None),
                            "is_reply": getattr(primary_email, 'is_reply', False)
                        }

                        task_request = TaskCreationRequest(
                            title=self._generate_task_title(primary_email),
                            description=self._generate_enhanced_task_description(
                                primary_email, semantic_keywords, process_attachments
                            ),
                            priority=task_priority,
                            source_email_id=str(primary_email.id),
                            category=primary_email.category or "email",
                            metadata=task_metadata
                        )

                        # Create task using existing task converter
                        task_result = await email_task_converter.create_task_from_request(
                            db, primary_email.user_id, task_request
                        )

                        if task_result.get('success'):
                            tasks_created += 1
                            self.logger.debug(f"Created task for email {primary_email.id}")

                except Exception as e:
                    primary_email_id = email_group.get("primary_email", {}).get("id", "unknown")
                    self.logger.warning(f"Failed to create task for email group {primary_email_id}: {e}")
                    continue

            await unified_log_service.log(
                task_context,
                "INFO",
                f"Created {tasks_created} tasks from {len(emails)} emails",
                "task_creator"
            )

            return tasks_created

    async def _mark_emails_processed(self, db: AsyncSession, email_ids: List[str]):
        """Mark emails as having tasks generated to avoid reprocessing."""
        from sqlalchemy import update

        await db.execute(
            update(Email)
            .where(Email.id.in_(email_ids))
            .values(
                tasks_generated=True,
                last_processed_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()

    def _determine_task_priority(
        self,
        importance_score: float,
        urgency_score: float,
        default_priority: str
    ) -> TaskPriority:
        """Determine task priority based on email intelligence scores."""

        # Use existing email intelligence instead of re-analyzing
        combined_score = (importance_score + urgency_score) / 2

        if combined_score >= 0.8:
            return TaskPriority.URGENT
        elif combined_score >= 0.7:
            return TaskPriority.HIGH
        elif combined_score >= 0.5:
            return TaskPriority.MEDIUM
        else:
            return TaskPriority.LOW

    def _generate_task_title(self, email: Email) -> str:
        """Generate intelligent task title from email."""
        subject = email.subject or "No Subject"
        sender = email.sender_name or email.sender_email or "Unknown Sender"

        # Smart title generation based on content
        if "action required" in subject.lower():
            return f"Action Required: {subject}"
        elif "follow up" in subject.lower() or "follow-up" in subject.lower():
            return f"Follow Up: {subject}"
        elif "review" in subject.lower():
            return f"Review: {subject}"
        else:
            return f"Email from {sender}: {subject}"

    def _generate_task_description(self, email: Email, process_attachments: bool = False) -> str:
        """Generate intelligent task description from email content."""

        # Use email snippet or first part of body
        content = email.snippet or email.body_text or email.body_html or ""
        if len(content) > 200:
            content = content[:200] + "..."

        # Enhanced description with workflow context
        description_parts = [
            f"Email Task Created from: {email.subject}",
            f"From: {email.sender_name or email.sender_email}",
            f"Received: {email.received_at.strftime('%Y-%m-%d %H:%M') if email.received_at else 'Unknown'}",
            f"Importance: {email.importance_score:.2f}/1.0",
            f"Category: {email.category or 'General'}",
        ]

        # Add attachment information if relevant
        if getattr(email, 'has_attachments', False):
            attachment_count = getattr(email, 'attachment_count', 0)
            description_parts.append(f"Attachments: {attachment_count} file(s)")
            if process_attachments:
                description_parts.append("Note: Attachment processing enabled for this workflow")

        # Add thread information if available
        if getattr(email, 'thread_id', None):
            description_parts.append(f"Thread ID: {email.thread_id}")
            if getattr(email, 'is_reply', False):
                description_parts.append("Note: This is a reply in an email thread")

        description_parts.extend([
            "",
            "Content Preview:",
            content,
            "",
            f"Email ID: {email.id}",
            "Created via: Unified Email Workflow (Local Sync)"
        ])

        return "\n".join(description_parts)

    def _generate_group_task_title(self, primary_email: Email, related_emails: List[Email]) -> str:
        """Generate intelligent task title for grouped similar emails."""

        total_emails = len(related_emails) + 1
        subject = primary_email.subject or "No Subject"
        sender = primary_email.sender_name or primary_email.sender_email or "Unknown Sender"

        # Smart group title generation
        if "action required" in subject.lower():
            return f"Action Required: {subject} (+{len(related_emails)} similar)"
        elif "follow up" in subject.lower() or "follow-up" in subject.lower():
            return f"Follow Up: {subject} (+{len(related_emails)} similar)"
        elif "review" in subject.lower():
            return f"Review: {subject} (+{len(related_emails)} similar)"
        else:
            return f"Email Group from {sender}: {subject} (+{len(related_emails)} similar)"

    def _generate_group_task_description(
        self,
        primary_email: Email,
        related_emails: List[Email],
        semantic_keywords: List[str],
        process_attachments: bool = False
    ) -> str:
        """Generate intelligent task description for grouped emails."""

        # Primary email content
        content = primary_email.snippet or primary_email.body_text or primary_email.body_html or ""
        if len(content) > 150:
            content = content[:150] + "..."

        description_parts = [
            f"Grouped Email Task Created from {len(related_emails) + 1} Similar Emails",
            "",
            "PRIMARY EMAIL:",
            f"Subject: {primary_email.subject}",
            f"From: {primary_email.sender_name or primary_email.sender_email}",
            f"Received: {primary_email.received_at.strftime('%Y-%m-%d %H:%M') if primary_email.received_at else 'Unknown'}",
            f"Importance: {primary_email.importance_score:.2f}/1.0",
            f"Category: {primary_email.category or 'General'}",
            "",
            "Content Preview:",
            content,
            "",
            f"RELATED EMAILS ({len(related_emails)}):"
        ]

        # Add information about related emails
        for i, email in enumerate(related_emails[:3], 1):  # Limit to first 3 for brevity
            description_parts.extend([
                f"{i}. From: {email.sender_name or email.sender_email}",
                f"   Subject: {email.subject}",
                f"   Received: {email.received_at.strftime('%Y-%m-%d %H:%M') if email.received_at else 'Unknown'}"
            ])

        if len(related_emails) > 3:
            description_parts.append(f"   ... and {len(related_emails) - 3} more similar emails")

        # Add semantic context
        if semantic_keywords:
            description_parts.extend([
                "",
                f"Semantic Keywords: {', '.join(semantic_keywords[:8])}"
            ])

        # Add attachment info if relevant
        total_attachments = sum([getattr(e, 'attachment_count', 0) for e in [primary_email] + related_emails])
        if total_attachments > 0:
            description_parts.append(f"Total Attachments: {total_attachments} file(s)")
            if process_attachments:
                description_parts.append("Note: Attachment processing enabled for this workflow")

        description_parts.extend([
            "",
            f"Primary Email ID: {primary_email.id}",
            f"Related Email IDs: {', '.join([str(e.id) for e in related_emails])}",
            "Created via: Unified Email Workflow (Semantic Grouping)"
        ])

        return "\n".join(description_parts)

    def _generate_enhanced_task_description(
        self,
        email: Email,
        semantic_keywords: List[str],
        process_attachments: bool = False
    ) -> str:
        """Generate enhanced task description with semantic context."""

        # Use email snippet or first part of body
        content = email.snippet or email.body_text or email.body_html or ""
        if len(content) > 200:
            content = content[:200] + "..."

        # Enhanced description with semantic context
        description_parts = [
            f"Email Task Created from: {email.subject}",
            f"From: {email.sender_name or email.sender_email}",
            f"Received: {email.received_at.strftime('%Y-%m-%d %H:%M') if email.received_at else 'Unknown'}",
            f"Importance: {email.importance_score:.2f}/1.0",
            f"Category: {email.category or 'General'}",
        ]

        # Add semantic keywords
        if semantic_keywords:
            description_parts.append(f"Semantic Keywords: {', '.join(semantic_keywords[:8])}")

        # Add attachment information if relevant
        if getattr(email, 'has_attachments', False):
            attachment_count = getattr(email, 'attachment_count', 0)
            description_parts.append(f"Attachments: {attachment_count} file(s)")
            if process_attachments:
                description_parts.append("Note: Attachment processing enabled for this workflow")

        # Add thread information if available
        if getattr(email, 'thread_id', None):
            description_parts.append(f"Thread ID: {email.thread_id}")
            if getattr(email, 'is_reply', False):
                description_parts.append("Note: This is a reply in an email thread")

        description_parts.extend([
            "",
            "Content Preview:",
            content,
            "",
            f"Email ID: {email.id}",
            "Created via: Unified Email Workflow (Semantic Enhancement)"
        ])

        return "\n".join(description_parts)


# Global service instance
unified_email_workflow_service = UnifiedEmailWorkflowService()
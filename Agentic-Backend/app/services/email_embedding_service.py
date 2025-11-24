"""
Email Embedding Generation Service

This service generates vector embeddings for synced emails to enable
semantic search and LLM-powered email conversations.

Features:
- Multiple embedding types (subject, body, combined, summary)
- Incremental processing (only new/changed emails)
- Batch processing for efficiency
- Content deduplication via hashing
- Integration with semantic processing service
"""

import hashlib
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models.email import Email, EmailEmbedding, EmailAttachment
from app.db.models.task import LogLevel
from app.db.models.embedding_task import EmbeddingTask, EmbeddingTaskStatus
from app.services.semantic_processing_service import semantic_processing_service
from app.services.unified_log_service import unified_log_service, WorkflowType, LogScope
from app.utils.logging import get_logger

logger = get_logger("email_embedding_service")


class EmailEmbeddingService:
    """Service for generating and managing email embeddings."""

    def __init__(self):
        from app.config import settings
        self.config = settings
        self.logger = get_logger("email_embedding_service")
        self.batch_size = settings.embedding_batch_size  # Process emails in batches
        self.concurrency = settings.embedding_concurrency  # Number of concurrent embedding operations
        # Max chars for embedding - set conservatively for smallest model (embeddinggemma: 2048 tokens)
        # Using ~3.5 chars per token: 2048 tokens ≈ 7000 chars, use 6000 for safety margin
        self.max_content_length = 6000
        self.max_retries = 3
        self.retry_delay_minutes = 5

    async def _enqueue_missing_tasks(self, db: AsyncSession, user_id: Optional[int] = None):
        """Create EmbeddingTask records for emails that need them."""
        # Find emails that need embeddings but don't have a task
        # We use a left join to find missing tasks
        query = select(Email.id).outerjoin(
            EmbeddingTask, Email.id == EmbeddingTask.email_id
        ).where(
            and_(
                or_(
                    Email.embeddings_generated == False,
                    Email.embeddings_generated.is_(None)
                ),
                EmbeddingTask.id.is_(None)
            )
        )

        if user_id:
            query = query.where(Email.user_id == user_id)

        result = await db.execute(query)
        email_ids = result.scalars().all()

        if not email_ids:
            return

        # Bulk insert tasks
        for i in range(0, len(email_ids), 1000):
            batch_ids = email_ids[i:i + 1000]
            tasks = [
                EmbeddingTask(
                    email_id=eid,
                    status=EmbeddingTaskStatus.PENDING
                )
                for eid in batch_ids
            ]
            db.add_all(tasks)
        
        await db.commit()
        self.logger.info(f"Enqueued {len(email_ids)} new embedding tasks")

    async def _get_pending_tasks(
        self, 
        db: AsyncSession, 
        user_id: Optional[int] = None, 
        limit: int = 1000
    ) -> List[EmbeddingTask]:
        """Get pending embedding tasks."""
        now = datetime.now(timezone.utc)
        
        query = select(EmbeddingTask).join(Email).options(
            selectinload(EmbeddingTask.email).selectinload(Email.attachments),
            selectinload(EmbeddingTask.email).selectinload(Email.embeddings)
        ).where(
            or_(
                EmbeddingTask.status == EmbeddingTaskStatus.PENDING,
                and_(
                    EmbeddingTask.status == EmbeddingTaskStatus.FAILED,
                    EmbeddingTask.next_retry <= now
                )
            )
        )

        if user_id:
            query = query.where(Email.user_id == user_id)

        query = query.limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def process_pending_emails(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        force_regenerate: bool = False
    ) -> Dict[str, int]:
        """
        Process all emails that need embeddings generated using the task queue.
        """
        # Create unified workflow context for embedding generation
        async with unified_log_service.workflow_context(
            user_id=user_id or 0,  # Use 0 for system-wide operations
            workflow_type=WorkflowType.CONTENT_PROCESSING,
            workflow_name=f"Email embedding generation",
            scope=LogScope.USER if user_id else LogScope.SYSTEM
        ) as workflow_context:

            stats = {
                "emails_processed": 0,
                "embeddings_generated": 0,
                "attachments_processed": 0,
                "errors": 0
            }

            try:
                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.INFO,
                    message="Starting email embedding generation",
                    component="email_embedding_service",
                    extra_metadata={
                        "user_id": user_id,
                        "force_regenerate": force_regenerate
                    }
                )

                # Step 1: Enqueue missing tasks
                if not force_regenerate:
                    await self._enqueue_missing_tasks(db, user_id)

                # Step 2: Get pending tasks
                # If force_regenerate is True, we might need different logic, 
                # but for now let's assume we rely on the queue for robustness.
                # If force_regenerate, we might want to reset all tasks to PENDING?
                # For now, let's stick to the queue processing.
                
                tasks = await self._get_pending_tasks(db, user_id)

                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.INFO,
                    message=f"Found {len(tasks)} pending embedding tasks",
                    component="email_embedding_service",
                    extra_metadata={"tasks_to_process": len(tasks)}
                )

                # Process tasks in batches
                async with unified_log_service.task_context(
                    parent_context=workflow_context,
                    task_name="Process embedding tasks in batches",
                    agent_id="embedding_generator_agent"
                ) as task_context:

                    for i in range(0, len(tasks), self.batch_size):
                        batch = tasks[i:i + self.batch_size]
                        batch_num = i//self.batch_size + 1
                        total_batches = (len(tasks)-1)//self.batch_size + 1

                        await unified_log_service.log(
                            context=task_context,
                            level=LogLevel.INFO,
                            message=f"Processing batch {batch_num}/{total_batches}",
                            component="email_embedding_service",
                            extra_metadata={
                                "batch_size": len(batch),
                                "batch_number": batch_num,
                                "total_batches": total_batches
                            }
                        )

                        batch_stats = await self._process_task_batch_with_logging(
                            db, batch, force_regenerate, task_context
                        )

                        stats["emails_processed"] += batch_stats["emails_processed"]
                        stats["embeddings_generated"] += batch_stats["embeddings_generated"]
                        stats["attachments_processed"] += batch_stats["attachments_processed"]
                        stats["errors"] += batch_stats["errors"]

                        # Commit batch
                        await db.commit()

                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.INFO,
                    message="Email embedding generation completed",
                    component="email_embedding_service",
                    extra_metadata=stats
                )

            except Exception as e:
                import traceback
                traceback.print_exc()
                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.ERROR,
                    message="Error processing pending emails",
                    component="email_embedding_service",
                    error=e
                )
                stats["errors"] += 1
                await db.rollback()

            return stats

    async def generate_email_embeddings(
        self,
        db: AsyncSession,
        email: Email,
        force_regenerate: bool = False,
        account_embedding_model: Optional[str] = None
    ) -> List[EmailEmbedding]:
        """
        Generate embeddings for a single email.

        Args:
            db: Database session
            email: Email to process
            force_regenerate: Regenerate even if embeddings exist
            account_embedding_model: Specific embedding model for this account (overrides default)

        Returns:
            List of generated EmailEmbedding objects
        """
        generated_embeddings = []

        try:
            # Check if embeddings already exist
            if not force_regenerate and email.embeddings_generated:
                existing_query = select(EmailEmbedding).where(EmailEmbedding.email_id == email.id)
                result = await db.execute(existing_query)
                existing = result.scalars().all()
                if existing:
                    return existing

            # Generate different types of embeddings
            embedding_types = await self._prepare_embedding_content(email)

            for embedding_type, content in embedding_types.items():
                if not content:
                    continue

                # Generate content hash for deduplication
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

                # Check if this exact content already has an embedding
                if not force_regenerate:
                    existing_query = select(EmailEmbedding).where(
                        and_(
                            EmailEmbedding.email_id == email.id,
                            EmailEmbedding.embedding_type == embedding_type
                        )
                    )
                    result = await db.execute(existing_query)
                    existing = result.scalar_one_or_none()
                    if existing:
                        generated_embeddings.append(existing)
                        continue

                # Generate embedding vector using account-specific model if provided
                embedding_vector = await semantic_processing_service.generate_embedding(
                    content,
                    model_name=account_embedding_model
                )

                if embedding_vector:
                    # Determine which model was actually used
                    used_model = account_embedding_model or semantic_processing_service.embedding_model

                    # Create EmailEmbedding record
                    email_embedding = EmailEmbedding(
                        email_id=email.id,
                        embedding_type=embedding_type,
                        content_hash=content_hash,
                        embedding_vector=embedding_vector,
                        model_name=used_model,
                        model_version="1.0"
                    )

                    db.add(email_embedding)
                    generated_embeddings.append(email_embedding)

            # Mark email as processed
            email.embeddings_generated = True
            email.last_processed_at = datetime.now()

            self.logger.debug(f"Generated {len(generated_embeddings)} embeddings for email {email.id}")

        except Exception as e:
            self.logger.error(f"Error generating embeddings for email {email.id}: {e}")
            raise

        return generated_embeddings

    async def search_similar_emails(
        self,
        db: AsyncSession,
        query_text: str,
        user_id: int,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        embedding_types: Optional[List[str]] = None,
        temporal_boost: float = 0.1,
        importance_boost: float = 0.2,
        intent_filter: Optional[str] = None
    ) -> List[Tuple[Email, float]]:
        """
        Search for emails using advanced similarity with temporal ranking and importance weighting.

        Args:
            db: Database session
            query_text: Text to search for
            user_id: User to search emails for
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            embedding_types: Types of embeddings to search (None = all)
            temporal_boost: Boost factor for recent emails (0.0-1.0)
            importance_boost: Boost factor for important emails (0.0-1.0)
            intent_filter: Filter by intent ("urgent", "action", "info", etc.)

        Returns:
            List of (Email, advanced_score) tuples sorted by relevance
        """
        try:
            # Generate embedding for query
            query_embedding = await semantic_processing_service.generate_embedding(query_text)
            if not query_embedding:
                return []

            # Detect intent from query
            detected_intent = await self._detect_query_intent(query_text)

            # Build similarity search query with extended limit for advanced scoring
            embedding_filter = and_(
                EmailEmbedding.email_id == Email.id,
                Email.user_id == user_id
            )

            if embedding_types:
                embedding_filter = and_(
                    embedding_filter,
                    EmailEmbedding.embedding_type.in_(embedding_types)
                )

            # Apply intent filter if specified
            if intent_filter:
                intent_conditions = self._build_intent_filter(intent_filter)
                if intent_conditions is not None:
                    embedding_filter = and_(embedding_filter, intent_conditions)

            # Advanced similarity search with email metadata
            similarity_query = select(
                Email,
                EmailEmbedding.embedding_vector.cosine_distance(query_embedding).label('distance'),
                Email.importance_score,
                Email.urgency_score,
                Email.sent_at,
                Email.is_important,
                Email.is_flagged,
                Email.category
            ).join(EmailEmbedding).where(
                embedding_filter
            ).where(
                EmailEmbedding.embedding_vector.cosine_distance(query_embedding) < (1 - similarity_threshold)
            ).order_by(
                EmailEmbedding.embedding_vector.cosine_distance(query_embedding)
            ).limit(limit * 2)  # Get more results for advanced scoring

            result = await db.execute(similarity_query)
            rows = result.all()

            # Advanced scoring with temporal, importance, and intent weighting
            scored_emails = []
            from datetime import timezone
            now = datetime.now(timezone.utc)

            for email, distance, importance_score, urgency_score, sent_at, is_important, is_flagged, category in rows:
                # Base similarity score
                base_similarity = 1 - distance

                # Temporal boost (recent emails get higher scores)
                if sent_at:
                    # Handle timezone-naive datetimes
                    if sent_at.tzinfo is None:
                        sent_at = sent_at.replace(tzinfo=timezone.utc)
                    days_ago = (now - sent_at).days
                    temporal_factor = max(0, 1 - (days_ago / 30))  # Decay over 30 days
                else:
                    temporal_factor = 0

                # Importance boost
                importance_factor = (importance_score or 0.5) + (urgency_score or 0.5)
                if is_important:
                    importance_factor += 0.3
                if is_flagged:
                    importance_factor += 0.2

                # Intent alignment boost
                intent_factor = self._calculate_intent_alignment(
                    detected_intent, category, is_important, is_flagged
                )

                # Calculate final advanced score
                advanced_score = (
                    base_similarity +
                    (temporal_boost * temporal_factor) +
                    (importance_boost * importance_factor) +
                    (0.15 * intent_factor)  # Intent boost factor
                )

                # Normalize score to [0, 1]
                advanced_score = min(1.0, max(0.0, advanced_score))

                scored_emails.append((email, advanced_score))

            # Sort by advanced score and limit results
            scored_emails.sort(key=lambda x: x[1], reverse=True)
            return scored_emails[:limit]

        except Exception as e:
            self.logger.error(f"Error searching similar emails: {e}")
            return []

    async def get_email_context(
        self,
        db: AsyncSession,
        email: Email,
        include_similar: bool = True,
        include_thread: bool = True
    ) -> Dict[str, Any]:
        """
        Get rich context for an email including similar emails and thread context.

        Args:
            db: Database session
            email: Email to get context for
            include_similar: Include similar emails
            include_thread: Include thread emails

        Returns:
            Dict with email context information
        """
        context = {
            "email": email,
            "similar_emails": [],
            "thread_emails": [],
            "embeddings": []
        }

        try:
            # Get email embeddings
            embeddings_query = select(EmailEmbedding).where(EmailEmbedding.email_id == email.id)
            result = await db.execute(embeddings_query)
            context["embeddings"] = result.scalars().all()

            # Get similar emails if requested
            if include_similar and email.body_text:
                similar_emails = await self.search_similar_emails(
                    db=db,
                    query_text=email.body_text[:500],  # Use first 500 chars
                    user_id=email.user_id,
                    limit=5,
                    similarity_threshold=0.6
                )
                context["similar_emails"] = [
                    {"email": sim_email, "similarity": score}
                    for sim_email, score in similar_emails
                    if sim_email.id != email.id  # Exclude the email itself
                ]

            # Get thread emails if requested
            if include_thread and email.thread_id:
                thread_query = select(Email).where(
                    and_(
                        Email.thread_id == email.thread_id,
                        Email.user_id == email.user_id
                    )
                ).order_by(Email.sent_at)

                result = await db.execute(thread_query)
                thread_emails = result.scalars().all()
                context["thread_emails"] = [
                    te for te in thread_emails if te.id != email.id
                ]

        except Exception as e:
            self.logger.error(f"Error getting email context: {e}")

        return context

    # Private helper methods

    async def _process_task_batch_with_logging(
        self,
        db: AsyncSession,
        tasks: List[EmbeddingTask],
        force_regenerate: bool,
        task_context
    ) -> Dict[str, int]:
        """Process embedding task batch with unified logging."""
        stats = {
            "emails_processed": 0,
            "embeddings_generated": 0,
            "attachments_processed": 0,
            "errors": 0
        }

        for task in tasks:
            try:
                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.DEBUG,
                    message=f"Processing embedding task",
                    component="email_embedding_service",
                    extra_metadata={
                        "task_id": str(task.id),
                        "email_id": str(task.email_id),
                        "attempt": task.attempts + 1
                    }
                )

                # Call processing method
                batch_stats = await self._process_task_batch(db, [task], force_regenerate)

                stats["emails_processed"] += batch_stats["emails_processed"]
                stats["embeddings_generated"] += batch_stats["embeddings_generated"]
                stats["attachments_processed"] += batch_stats["attachments_processed"]
                stats["errors"] += batch_stats["errors"]

            except Exception as e:
                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.ERROR,
                    message=f"Failed to process embedding task",
                    component="email_embedding_service",
                    error=e,
                    extra_metadata={"task_id": str(task.id)}
                )
                stats["errors"] += 1

        return stats

    async def _process_task_batch(
        self,
        db: AsyncSession,
        tasks: List[EmbeddingTask],
        force_regenerate: bool
    ) -> Dict[str, int]:
        """
        Process a batch of embedding tasks with concurrent processing.
        """
        stats = {
            "emails_processed": 0,
            "embeddings_generated": 0,
            "attachments_processed": 0,
            "errors": 0
        }

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.concurrency)

        async def process_single_task(task: EmbeddingTask):
            """Process a single task with semaphore control."""
            async with semaphore:
                try:
                    # Update task status
                    task.status = EmbeddingTaskStatus.PROCESSING
                    task.last_attempt = datetime.now(timezone.utc)
                    task.attempts += 1
                    
                    # Generate email embeddings
                    embeddings = await self.generate_email_embeddings(db, task.email, force_regenerate)
                    
                    email_stats = {
                        "embeddings_generated": len(embeddings),
                        "attachments_processed": 0,
                        "errors": 0
                    }

                    # Process attachments if they have extracted text
                    for attachment in task.email.attachments:
                        if attachment.extracted_text and not attachment.embeddings_generated:
                            await self._generate_attachment_embedding(db, attachment)
                            email_stats["attachments_processed"] += 1

                    # Mark task as completed
                    task.status = EmbeddingTaskStatus.COMPLETED
                    task.error_message = None
                    
                    return email_stats

                except Exception as e:
                    self.logger.error(f"Error processing task {task.id}: {e}")
                    
                    # Handle retry logic
                    task.error_message = str(e)
                    if task.attempts >= self.max_retries:
                        task.status = EmbeddingTaskStatus.FAILED_PERMANENTLY
                    else:
                        task.status = EmbeddingTaskStatus.FAILED
                        task.next_retry = datetime.now(timezone.utc) + timedelta(minutes=self.retry_delay_minutes * task.attempts)
                    
                    return {"embeddings_generated": 0, "attachments_processed": 0, "errors": 1}

        # Process all tasks concurrently
        # Ensure email is loaded
        task_futures = [process_single_task(task) for task in tasks]
        results = await asyncio.gather(*task_futures, return_exceptions=True)

        # Aggregate results
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Unexpected error in concurrent processing: {result}")
                stats["errors"] += 1
            elif isinstance(result, dict):
                stats["emails_processed"] += 1 if result["errors"] == 0 else 0
                stats["embeddings_generated"] += result["embeddings_generated"]
                stats["attachments_processed"] += result["attachments_processed"]
                stats["errors"] += result["errors"]

        return stats

    async def _process_email_batch_with_logging(
        self,
        db: AsyncSession,
        emails: List[Email],
        force_regenerate: bool,
        task_context
    ) -> Dict[str, int]:
        """Process email batch with unified logging."""
        stats = {
            "emails_processed": 0,
            "embeddings_generated": 0,
            "attachments_processed": 0,
            "errors": 0
        }

        for email in emails:
            try:
                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.DEBUG,
                    message=f"Processing email embeddings",
                    component="email_embedding_service",
                    extra_metadata={
                        "email_id": str(email.id),
                        "subject": email.subject[:50] if email.subject else "No subject"
                    }
                )

                # Call original method
                batch_stats = await self._process_email_batch(db, [email], force_regenerate)

                stats["emails_processed"] += batch_stats["emails_processed"]
                stats["embeddings_generated"] += batch_stats["embeddings_generated"]
                stats["attachments_processed"] += batch_stats["attachments_processed"]
                stats["errors"] += batch_stats["errors"]

            except Exception as e:
                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.ERROR,
                    message=f"Failed to process email embedding",
                    component="email_embedding_service",
                    error=e,
                    extra_metadata={"email_id": str(email.id)}
                )
                stats["errors"] += 1

        return stats

    async def _process_email_batch(
        self,
        db: AsyncSession,
        emails: List[Email],
        force_regenerate: bool
    ) -> Dict[str, int]:
        """
        Process a batch of emails for embedding generation with concurrent processing.

        Uses a semaphore to limit concurrent operations to self.concurrency.
        """
        stats = {
            "emails_processed": 0,
            "embeddings_generated": 0,
            "attachments_processed": 0,
            "errors": 0
        }

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.concurrency)

        async def process_single_email(email: Email):
            """Process a single email with semaphore control."""
            async with semaphore:
                try:
                    # Generate email embeddings
                    embeddings = await self.generate_email_embeddings(db, email, force_regenerate)
                    email_stats = {
                        "embeddings_generated": len(embeddings),
                        "attachments_processed": 0,
                        "errors": 0
                    }

                    # Process attachments if they have extracted text
                    for attachment in email.attachments:
                        if attachment.extracted_text and not attachment.embeddings_generated:
                            await self._generate_attachment_embedding(db, attachment)
                            email_stats["attachments_processed"] += 1

                    return email_stats

                except Exception as e:
                    self.logger.error(f"Error processing email {email.id}: {e}")
                    return {"embeddings_generated": 0, "attachments_processed": 0, "errors": 1}

        # Process all emails concurrently with limited concurrency
        tasks = [process_single_email(email) for email in emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Unexpected error in concurrent processing: {result}")
                stats["errors"] += 1
            elif isinstance(result, dict):
                stats["emails_processed"] += 1 if result["errors"] == 0 else 0
                stats["embeddings_generated"] += result["embeddings_generated"]
                stats["attachments_processed"] += result["attachments_processed"]
                stats["errors"] += result["errors"]

        return stats

    async def _prepare_embedding_content(self, email: Email) -> Dict[str, str]:
        """
        Prepare different types of content for embedding generation.

        Args:
            email: Email to process

        Returns:
            Dict mapping embedding type to content string
        """
        content_types = {}

        # Subject embedding
        if email.subject:
            content_types["subject"] = email.subject[:500]  # Limit subject length

        # Body embedding (text or HTML)
        body_content = None
        if email.body_text:
            body_content = email.body_text
        elif email.body_html:
            # Extract text from HTML
            body_content = self._extract_text_from_html(email.body_html)

        if body_content:
            # Clean and truncate body text
            clean_body = self._clean_email_text(body_content)
            content_types["body"] = clean_body[:self.max_content_length]

        # Combined embedding (subject + body)
        if email.subject and body_content:
            combined = f"Subject: {email.subject}\n\nBody: {body_content}"
            clean_combined = self._clean_email_text(combined)
            content_types["combined"] = clean_combined[:self.max_content_length]

        # Summary embedding (for long emails)
        if body_content and len(body_content) > 2000:
            # Create a summary of the email for embedding
            summary = await self._generate_email_summary(email)
            if summary:
                content_types["summary"] = summary

        return content_types

    def _clean_email_text(self, text: str) -> str:
        """Clean email text for embedding generation."""
        if not text:
            return ""

        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)

        # Remove quoted text (basic detection)
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            # Skip lines that look like quoted text
            if not (line.startswith('>') or line.startswith('On ') and 'wrote:' in line):
                clean_lines.append(line)

        return ' '.join(clean_lines).strip()

    async def _generate_email_summary(self, email: Email) -> Optional[str]:
        """Generate a summary of the email for embedding."""
        try:
            # Use LLM to generate a concise summary
            prompt = f"""
            Please provide a concise summary of this email in 2-3 sentences:

            Subject: {email.subject or 'No subject'}
            From: {email.sender_email}
            Body: {email.body_text[:1000]}...

            Summary:
            """

            # This would use your LLM service
            # summary = await ollama_client.generate_completion(prompt)
            # For now, return a simple truncated version
            if email.body_text:
                sentences = email.body_text.split('.')[:3]
                return '. '.join(sentences) + '.'

        except Exception as e:
            self.logger.warning(f"Failed to generate summary for email {email.id}: {e}")

        return None

    async def _generate_attachment_embedding(
        self,
        db: AsyncSession,
        attachment: EmailAttachment
    ) -> Optional[EmailEmbedding]:
        """Generate embedding for attachment extracted text."""
        try:
            if not attachment.extracted_text:
                return None

            # Clean and truncate extracted text
            clean_text = self._clean_email_text(attachment.extracted_text)
            content = clean_text[:self.max_content_length]

            # Generate embedding
            embedding_vector = await semantic_processing_service.generate_embedding(content)
            if not embedding_vector:
                return None

            # Store embedding in attachment record
            attachment.embedding_vector = embedding_vector
            attachment.embeddings_generated = True

            return embedding_vector

        except Exception as e:
            self.logger.error(f"Error generating attachment embedding: {e}")
            return None

    async def _detect_query_intent(self, query_text: str) -> str:
        """Detect the intent of a search query."""
        query_lower = query_text.lower()

        # Intent keywords mapping
        intent_keywords = {
            "urgent": ["urgent", "asap", "emergency", "critical", "immediate"],
            "action": ["action", "task", "todo", "follow up", "complete", "deadline", "due"],
            "meeting": ["meeting", "schedule", "calendar", "appointment", "call", "zoom"],
            "financial": ["payment", "invoice", "budget", "cost", "expense", "billing"],
            "project": ["project", "milestone", "deliverable", "progress", "status"],
            "personal": ["personal", "family", "friend", "vacation", "holiday"],
            "work": ["work", "office", "business", "client", "customer"],
            "info": ["information", "details", "report", "summary", "update"]
        }

        # Score intents based on keyword matches
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                intent_scores[intent] = score

        # Return the highest scoring intent or "general" if no matches
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        return "general"

    def _build_intent_filter(self, intent_filter: str) -> Optional[Any]:
        """Build database filter conditions based on intent."""
        if intent_filter == "urgent":
            return or_(
                Email.is_important == True,
                Email.is_flagged == True,
                Email.urgency_score >= 0.7,
                Email.category.in_(["urgent", "critical"])
            )
        elif intent_filter == "action":
            return or_(
                Email.category.in_(["task", "action", "todo"]),
                Email.subject.ilike("%action%"),
                Email.subject.ilike("%task%"),
                Email.subject.ilike("%deadline%")
            )
        elif intent_filter == "meeting":
            return or_(
                Email.category.in_(["meeting", "calendar"]),
                Email.subject.ilike("%meeting%"),
                Email.subject.ilike("%schedule%"),
                Email.subject.ilike("%call%")
            )
        elif intent_filter == "financial":
            return or_(
                Email.category.in_(["finance", "billing"]),
                Email.subject.ilike("%payment%"),
                Email.subject.ilike("%invoice%"),
                Email.subject.ilike("%billing%")
            )
        elif intent_filter == "important":
            return or_(
                Email.is_important == True,
                Email.importance_score >= 0.7
            )

        return None

    def _calculate_intent_alignment(
        self,
        detected_intent: str,
        category: Optional[str],
        is_important: bool,
        is_flagged: bool
    ) -> float:
        """Calculate how well an email aligns with the detected query intent."""
        if not detected_intent or detected_intent == "general":
            return 0.5  # Neutral score

        alignment_score = 0.0
        category_lower = (category or "").lower()

        # Intent-category alignment
        if detected_intent == "urgent" and (is_important or is_flagged):
            alignment_score += 0.8
        elif detected_intent == "urgent" and "urgent" in category_lower:
            alignment_score += 0.9
        elif detected_intent == "action" and category_lower in ["task", "action", "todo"]:
            alignment_score += 0.9
        elif detected_intent == "meeting" and "meeting" in category_lower:
            alignment_score += 0.9
        elif detected_intent == "financial" and category_lower in ["finance", "billing", "payment"]:
            alignment_score += 0.9
        elif detected_intent == "project" and "project" in category_lower:
            alignment_score += 0.9
        elif detected_intent == "work" and category_lower in ["work", "business", "client"]:
            alignment_score += 0.7
        elif detected_intent == "personal" and category_lower in ["personal", "family"]:
            alignment_score += 0.7
        elif detected_intent == "info" and category_lower in ["info", "report", "summary"]:
            alignment_score += 0.8

        # General importance boost
        if is_important and detected_intent in ["urgent", "action", "important"]:
            alignment_score += 0.2
        if is_flagged and detected_intent in ["urgent", "action"]:
            alignment_score += 0.1

        return min(1.0, alignment_score)

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text from HTML content."""
        if not html_content:
            return ""

        try:
            import re
            from html import unescape

            # Remove script and style elements
            html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)

            # Unescape HTML entities
            text = unescape(text)

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            return text

        except Exception as e:
            self.logger.warning(f"Failed to extract text from HTML: {e}")
            # Fallback: return HTML with tags stripped using simple regex
            import re
            return re.sub(r'<[^>]+>', '', html_content or "").strip()


# Global instance
email_embedding_service = EmailEmbeddingService()
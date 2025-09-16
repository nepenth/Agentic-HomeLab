"""
Email Deduplication Service for preventing duplicate task creation.

This service provides intelligent email deduplication capabilities to prevent
processing the same emails multiple times across workflow runs.
"""

import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import json

from app.db.models.processed_email import ProcessedEmail
from app.db.models.task import Task
from app.db.database import get_db
from app.utils.logging import get_logger
from app.connectors.base import ContentItem

logger = get_logger("email_deduplication_service")


class EmailDeduplicationResult:
    """Result of email deduplication check."""
    
    def __init__(
        self,
        is_duplicate: bool,
        existing_email: Optional[ProcessedEmail] = None,
        should_create_task: bool = True,
        reason: str = "",
        confidence: float = 1.0
    ):
        self.is_duplicate = is_duplicate
        self.existing_email = existing_email
        self.should_create_task = should_create_task
        self.reason = reason
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "is_duplicate": self.is_duplicate,
            "should_create_task": self.should_create_task,
            "reason": self.reason,
            "confidence": self.confidence,
            "existing_email_id": str(self.existing_email.id) if self.existing_email else None
        }


class EmailDeduplicationService:
    """
    Service for intelligent email deduplication and task creation decisions.
    
    This service implements a multi-layered approach to email deduplication:
    1. Exact Message-ID matching (highest confidence)
    2. Subject + sender fingerprint matching (high confidence)  
    3. Content similarity matching (medium confidence)
    4. User action learning (behavioral intelligence)
    """

    def __init__(self, db_session: Session = None):
        self.db_session = db_session or next(get_db())
        self.logger = logger

    def create_email_fingerprint(self, email: ContentItem) -> Tuple[str, str, str]:
        """
        Create email fingerprint for deduplication matching.
        
        Args:
            email: ContentItem representing the email
            
        Returns:
            Tuple of (subject_hash, sender_hash, content_fingerprint)
        """
        subject = email.metadata.get('subject', email.title or '')
        sender = email.metadata.get('sender', '')
        content = email.description or ''
        
        # Normalize subject (remove Re:, Fwd:, etc.)
        normalized_subject = re.sub(r'^(re|fwd|fw):\s*', '', subject.lower().strip())
        normalized_subject = re.sub(r'\s+', ' ', normalized_subject)  # Normalize whitespace
        subject_hash = hashlib.sha256(normalized_subject.encode()).hexdigest()
        
        # Normalize sender (extract email address)
        sender_match = re.search(r'<([^>]+)>', sender)
        normalized_sender = sender_match.group(1) if sender_match else sender.lower().strip()
        sender_hash = hashlib.sha256(normalized_sender.encode()).hexdigest()
        
        # Create content fingerprint
        normalized_content = re.sub(r'\s+', ' ', content.lower().strip())
        # Remove common email signatures and footers
        normalized_content = re.sub(r'sent from my \w+', '', normalized_content)
        normalized_content = re.sub(r'--\s*$', '', normalized_content)
        content_fingerprint = hashlib.sha256(normalized_content.encode()).hexdigest()
        
        return subject_hash, sender_hash, content_fingerprint

    def check_duplicate(self, email: ContentItem, user_id: int, workflow_id: str) -> EmailDeduplicationResult:
        """
        Check if an email is a duplicate and determine if tasks should be created.
        
        Args:
            email: ContentItem representing the email
            user_id: User ID for scoping the check
            workflow_id: Current workflow ID
            
        Returns:
            EmailDeduplicationResult with deduplication decision
        """
        try:
            message_id = email.metadata.get('message_id', '').strip()
            
            # Strategy 1: Exact Message-ID match (highest confidence)
            if message_id:
                existing = self._find_by_message_id(message_id, user_id)
                if existing:
                    should_create_task = self._should_create_task_for_existing(existing, workflow_id)
                    return EmailDeduplicationResult(
                        is_duplicate=True,
                        existing_email=existing,
                        should_create_task=should_create_task,
                        reason=f"Exact Message-ID match: {message_id}",
                        confidence=1.0
                    )
            
            # Strategy 2: Subject + sender fingerprint match (high confidence)
            subject_hash, sender_hash, content_fingerprint = self.create_email_fingerprint(email)
            existing = self._find_by_fingerprint(subject_hash, sender_hash, user_id)
            if existing:
                should_create_task = self._should_create_task_for_existing(existing, workflow_id)
                return EmailDeduplicationResult(
                    is_duplicate=True,
                    existing_email=existing,
                    should_create_task=should_create_task,
                    reason="Subject + sender fingerprint match",
                    confidence=0.9
                )
            
            # Strategy 3: Content similarity (medium confidence)
            if content_fingerprint:
                similar_emails = self._find_similar_content(content_fingerprint, user_id, threshold=0.8)
                if similar_emails:
                    existing = similar_emails[0]  # Take the most recent match
                    should_create_task = self._should_create_task_for_existing(existing, workflow_id)
                    return EmailDeduplicationResult(
                        is_duplicate=True,
                        existing_email=existing,
                        should_create_task=should_create_task,
                        reason="Content similarity match",
                        confidence=0.7
                    )
            
            # Not a duplicate - new email
            return EmailDeduplicationResult(
                is_duplicate=False,
                should_create_task=True,
                reason="New email - no duplicates found",
                confidence=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error in duplicate check: {e}")
            # Fail safe - assume it's new to avoid blocking workflow
            return EmailDeduplicationResult(
                is_duplicate=False,
                should_create_task=True,
                reason=f"Error in deduplication check: {str(e)}",
                confidence=0.5
            )

    def _find_by_message_id(self, message_id: str, user_id: int) -> Optional[ProcessedEmail]:
        """Find existing email by Message-ID."""
        return self.db_session.query(ProcessedEmail).filter(
            and_(
                ProcessedEmail.message_id == message_id,
                ProcessedEmail.user_id == user_id
            )
        ).first()

    def _find_by_fingerprint(self, subject_hash: str, sender_hash: str, user_id: int) -> Optional[ProcessedEmail]:
        """Find existing email by subject + sender fingerprint."""
        return self.db_session.query(ProcessedEmail).filter(
            and_(
                ProcessedEmail.subject_hash == subject_hash,
                ProcessedEmail.sender_hash == sender_hash,
                ProcessedEmail.user_id == user_id
            )
        ).first()

    def _find_similar_content(self, content_fingerprint: str, user_id: int, threshold: float = 0.8) -> List[ProcessedEmail]:
        """Find emails with similar content."""
        # For now, do exact content match - could be enhanced with semantic similarity
        return self.db_session.query(ProcessedEmail).filter(
            and_(
                ProcessedEmail.content_fingerprint == content_fingerprint,
                ProcessedEmail.user_id == user_id
            )
        ).order_by(ProcessedEmail.first_seen_at.desc()).limit(5).all()

    def _should_create_task_for_existing(self, existing_email: ProcessedEmail, workflow_id: str) -> bool:
        """
        Determine if a task should be created for an existing email based on user history.
        
        Args:
            existing_email: The previously processed email record
            workflow_id: Current workflow ID
            
        Returns:
            True if a task should be created
        """
        # Don't create if user previously dismissed similar emails
        if existing_email.task_dismissed and existing_email.similar_email_action == 'skip_future':
            self.logger.info(f"Skipping task creation for email {existing_email.id} - user previously dismissed similar emails")
            return False
        
        # Don't create if already completed (unless user wants to reprocess)
        if existing_email.task_completed:
            self.logger.info(f"Skipping task creation for email {existing_email.id} - task already completed")
            return False
        
        # Don't create if we already created a task for this email recently
        if existing_email.task_created:
            recent_threshold = datetime.utcnow() - timedelta(hours=24)
            if existing_email.last_processed_at and existing_email.last_processed_at > recent_threshold:
                self.logger.info(f"Skipping task creation for email {existing_email.id} - task created recently")
                return False
        
        # Update workflow tracking
        self._update_workflow_tracking(existing_email, workflow_id)
        
        return True

    def _update_workflow_tracking(self, existing_email: ProcessedEmail, workflow_id: str):
        """Update workflow tracking for an existing email."""
        workflow_ids = existing_email.workflow_ids or []
        if workflow_id not in workflow_ids:
            workflow_ids.append(workflow_id)
            existing_email.workflow_ids = workflow_ids
            existing_email.last_processed_at = datetime.utcnow()
            self.db_session.commit()

    def record_processed_email(
        self, 
        email: ContentItem, 
        user_id: int, 
        workflow_id: str,
        task_created: bool = False
    ) -> ProcessedEmail:
        """
        Record an email as processed in the deduplication system.
        
        Args:
            email: ContentItem representing the email
            user_id: User ID
            workflow_id: Workflow ID that processed this email
            task_created: Whether a task was created for this email
            
        Returns:
            ProcessedEmail record
        """
        message_id = email.metadata.get('message_id', '').strip()
        subject_hash, sender_hash, content_fingerprint = self.create_email_fingerprint(email)
        
        # Check if already exists
        existing = None
        if message_id:
            existing = self._find_by_message_id(message_id, user_id)
        if not existing:
            existing = self._find_by_fingerprint(subject_hash, sender_hash, user_id)
        
        if existing:
            # Update existing record
            self._update_workflow_tracking(existing, workflow_id)
            if task_created:
                existing.task_created = True
                existing.processing_status = "processed"
            self.db_session.commit()
            return existing
        else:
            # Create new record
            processed_email = ProcessedEmail(
                message_id=message_id or None,
                source_email_id=email.id,
                subject_hash=subject_hash,
                sender_hash=sender_hash,
                content_fingerprint=content_fingerprint,
                user_id=user_id,
                workflow_ids=[workflow_id],
                processing_status="processed" if task_created else "skipped",
                task_created=task_created,
                email_metadata=email.metadata
            )
            
            self.db_session.add(processed_email)
            self.db_session.commit()
            return processed_email

    def record_user_action(self, email_id: str, action: str, feedback_data: dict = None):
        """
        Record user action on an email task for learning.
        
        Args:
            email_id: ProcessedEmail ID
            action: 'completed', 'dismissed', or 'reopened'
            feedback_data: Additional feedback information
        """
        try:
            processed_email = self.db_session.query(ProcessedEmail).filter(
                ProcessedEmail.id == email_id
            ).first()
            
            if not processed_email:
                self.logger.warning(f"Processed email {email_id} not found for user action recording")
                return
            
            processed_email.record_user_action(action, feedback_data)
            self.db_session.commit()
            
            self.logger.info(f"Recorded user action '{action}' for email {email_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to record user action: {e}")
            self.db_session.rollback()

    def get_deduplication_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get deduplication statistics for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dictionary with deduplication statistics
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Total emails processed
            total_emails = self.db_session.query(ProcessedEmail).filter(
                and_(
                    ProcessedEmail.user_id == user_id,
                    ProcessedEmail.first_seen_at >= since_date
                )
            ).count()
            
            # Tasks created
            tasks_created = self.db_session.query(ProcessedEmail).filter(
                and_(
                    ProcessedEmail.user_id == user_id,
                    ProcessedEmail.task_created == True,
                    ProcessedEmail.first_seen_at >= since_date
                )
            ).count()
            
            # Tasks completed
            tasks_completed = self.db_session.query(ProcessedEmail).filter(
                and_(
                    ProcessedEmail.user_id == user_id,
                    ProcessedEmail.task_completed == True,
                    ProcessedEmail.first_seen_at >= since_date
                )
            ).count()
            
            # Tasks dismissed
            tasks_dismissed = self.db_session.query(ProcessedEmail).filter(
                and_(
                    ProcessedEmail.user_id == user_id,
                    ProcessedEmail.task_dismissed == True,
                    ProcessedEmail.first_seen_at >= since_date
                )
            ).count()
            
            return {
                "period_days": days,
                "total_emails_processed": total_emails,
                "tasks_created": tasks_created,
                "tasks_completed": tasks_completed,
                "tasks_dismissed": tasks_dismissed,
                "task_creation_rate": (tasks_created / total_emails * 100) if total_emails > 0 else 0,
                "task_completion_rate": (tasks_completed / tasks_created * 100) if tasks_created > 0 else 0,
                "emails_skipped": total_emails - tasks_created,
                "duplicate_detection_effectiveness": ((total_emails - tasks_created) / total_emails * 100) if total_emails > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get deduplication stats: {e}")
            return {
                "error": str(e),
                "period_days": days
            }

    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Clean up old processed email records.
        
        Args:
            days: Number of days to keep records
            
        Returns:
            Number of records cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Only delete records that don't have active tasks and are old
            old_records = self.db_session.query(ProcessedEmail).filter(
                and_(
                    ProcessedEmail.first_seen_at < cutoff_date,
                    ProcessedEmail.task_completed == True,
                    ProcessedEmail.task_dismissed == False
                )
            )
            
            count = old_records.count()
            old_records.delete()
            self.db_session.commit()
            
            self.logger.info(f"Cleaned up {count} old processed email records")
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old records: {e}")
            self.db_session.rollback()
            return 0
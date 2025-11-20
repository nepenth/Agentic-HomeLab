"""
Processed Email model for tracking email deduplication and user actions.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Index, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class ProcessedEmail(Base):
    """
    Model for tracking processed emails to prevent duplicates and learn from user actions.
    
    This table serves as the central registry for email processing state, enabling:
    - Deduplication across workflow runs
    - User action learning (completed/dismissed tasks)
    - Processing analytics and optimization
    """
    __tablename__ = "processed_emails"
    
    # Primary identifier
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Email identification fields
    message_id = Column(String(500), nullable=True, index=True)  # RFC 2822 Message-ID header
    source_email_id = Column(String(200), nullable=False, index=True)  # IMAP/source specific ID
    subject_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of normalized subject
    sender_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of normalized sender
    content_fingerprint = Column(String(64), nullable=True, index=True)  # Content similarity hash
    
    # User and workflow tracking
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workflow_ids = Column(JSONB, nullable=True, default=list)  # List of workflow IDs that processed this email
    
    # Processing state
    processing_status = Column(String(50), nullable=False, default="discovered", index=True)  # discovered, processed, failed, skipped
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    last_processed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Task creation and user action tracking
    task_created = Column(Boolean, nullable=False, default=False, index=True)
    task_completed = Column(Boolean, nullable=False, default=False)
    task_dismissed = Column(Boolean, nullable=False, default=False)  # User marked as "not important"
    
    # Learning and analytics data
    importance_score = Column(String, nullable=True)  # JSON: latest AI importance assessment
    user_feedback_score = Column(String, nullable=True)  # JSON: user's implicit feedback score
    similar_email_action = Column(String(50), nullable=True)  # skip_future, create_tasks, ask_user
    
    # Email metadata for matching and analytics
    email_metadata = Column(JSONB, nullable=True)  # Cached email metadata for quick access
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="processed_emails")
    # tasks = relationship("Task", back_populates="processed_email")
    
    # Indexes for efficient querying
    __table_args__ = (
        # Unique constraint on email identity per user
        Index('idx_processed_emails_identity', 'user_id', 'message_id', unique=True, postgresql_where=Column('message_id').isnot(None)),
        Index('idx_processed_emails_fingerprint', 'user_id', 'subject_hash', 'sender_hash', unique=True),
        
        # Performance indexes
        Index('idx_processed_emails_user_status', 'user_id', 'processing_status'),
        Index('idx_processed_emails_user_first_seen', 'user_id', 'first_seen_at'),
        Index('idx_processed_emails_task_state', 'user_id', 'task_created', 'task_completed', 'task_dismissed'),
        Index('idx_processed_emails_content_fingerprint', 'content_fingerprint'),
        
        # Analytics indexes
        Index('idx_processed_emails_workflow_tracking', 'user_id', 'last_processed_at'),
    )
    
    def __repr__(self):
        return f"<ProcessedEmail(id={self.id}, user_id={self.user_id}, message_id={self.message_id}, status={self.processing_status})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "message_id": self.message_id,
            "source_email_id": self.source_email_id,
            "user_id": self.user_id,
            "processing_status": self.processing_status,
            "task_created": self.task_created,
            "task_completed": self.task_completed,
            "task_dismissed": self.task_dismissed,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None,
            "workflow_ids": self.workflow_ids or [],
            "importance_score": self.importance_score,
            "user_feedback_score": self.user_feedback_score,
            "similar_email_action": self.similar_email_action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_email_fingerprint(cls, subject: str, sender: str, content: str = None) -> tuple:
        """
        Create email fingerprint for deduplication.
        
        Args:
            subject: Email subject line
            sender: Email sender address
            content: Email content (optional)
            
        Returns:
            Tuple of (subject_hash, sender_hash, content_fingerprint)
        """
        import hashlib
        import re
        
        # Normalize subject (remove Re:, Fwd:, etc.)
        normalized_subject = re.sub(r'^(re|fwd|fw):\s*', '', subject.lower().strip())
        subject_hash = hashlib.sha256(normalized_subject.encode()).hexdigest()
        
        # Normalize sender (extract email address)
        sender_match = re.search(r'<([^>]+)>', sender)
        normalized_sender = sender_match.group(1) if sender_match else sender.lower().strip()
        sender_hash = hashlib.sha256(normalized_sender.encode()).hexdigest()
        
        # Create content fingerprint if provided
        content_fingerprint = None
        if content:
            # Remove common variations (whitespace, signatures, etc.)
            normalized_content = re.sub(r'\s+', ' ', content.lower().strip())
            content_fingerprint = hashlib.sha256(normalized_content.encode()).hexdigest()
        
        return subject_hash, sender_hash, content_fingerprint
    
    def is_duplicate_of(self, other_email: dict) -> bool:
        """
        Check if this processed email is a duplicate of another email.
        
        Args:
            other_email: Dictionary with email data (subject, sender, message_id, etc.)
            
        Returns:
            True if this is likely a duplicate
        """
        # Exact Message-ID match (most reliable)
        if self.message_id and other_email.get('message_id'):
            return self.message_id == other_email['message_id']
        
        # Subject + sender fingerprint match
        subject = other_email.get('subject', '')
        sender = other_email.get('sender', '')
        
        if subject and sender:
            subject_hash, sender_hash, _ = self.create_email_fingerprint(subject, sender)
            return self.subject_hash == subject_hash and self.sender_hash == sender_hash
        
        return False
    
    def should_create_task(self) -> bool:
        """
        Determine if a task should be created for this email based on user history.
        
        Returns:
            True if a task should be created
        """
        # Don't create if user previously dismissed similar emails
        if self.task_dismissed and self.similar_email_action == 'skip_future':
            return False
        
        # Don't create if already completed
        if self.task_completed:
            return False
        
        # Default: create task
        return True
    
    def record_user_action(self, action: str, feedback_data: dict = None):
        """
        Record user action on this email's task.
        
        Args:
            action: 'completed', 'dismissed', or 'reopened'
            feedback_data: Additional feedback information
        """
        import json
        
        if action == 'completed':
            self.task_completed = True
            self.task_dismissed = False
        elif action == 'dismissed':
            self.task_dismissed = True
            self.task_completed = False
            self.similar_email_action = 'skip_future'  # Learn to skip similar emails
        elif action == 'reopened':
            self.task_completed = False
            self.task_dismissed = False
            self.similar_email_action = None
        
        # Update feedback score
        if feedback_data:
            self.user_feedback_score = json.dumps(feedback_data)
        
        self.updated_at = func.now()
"""
Database models for email workflow system.

This module defines additional database models specific to email workflow
functionality, extending the existing content and task models.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.database import Base


class EmailWorkflowStatus(str, enum.Enum):
    """Status of email workflow processing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EmailWorkflow(Base):
    """Model for tracking email workflow executions."""
    __tablename__ = "email_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=False, index=True)
    workflow_name = Column(String(200), nullable=True)

    # Workflow configuration
    mailbox_config = Column(JSONB, nullable=False)  # IMAP configuration
    processing_options = Column(JSONB, nullable=True)  # Processing settings

    # Status and timing
    status = Column(String(50), nullable=False, default=EmailWorkflowStatus.PENDING.value, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Statistics
    emails_discovered = Column(Integer, default=0, nullable=False)
    emails_processed = Column(Integer, default=0, nullable=False)
    emails_analyzed = Column(Integer, default=0, nullable=False)
    tasks_created = Column(Integer, default=0, nullable=False)
    followups_scheduled = Column(Integer, default=0, nullable=False)

    # Error tracking
    error_message = Column(Text, nullable=True)
    warning_messages = Column(JSONB, nullable=True)

    # Metadata
    workflow_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_workflows_user_status', 'user_id', 'status'),
        Index('idx_email_workflows_started_at', 'started_at'),
        Index('idx_email_workflows_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<EmailWorkflow(id={self.id}, user={self.user_id}, status={self.status})>"


class EmailAnalysisResult(Base):
    """Model for storing detailed email analysis results."""
    __tablename__ = "email_analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_base_items.id'), nullable=False, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('email_workflows.id'), nullable=True, index=True)

    # Analysis results
    importance_score = Column(JSON, nullable=True)  # Store as JSON for flexibility
    categories = Column(JSONB, nullable=True)
    urgency_level = Column(String(20), nullable=True)
    sender_reputation = Column(JSON, nullable=True)
    content_summary = Column(Text, nullable=True)
    key_topics = Column(JSONB, nullable=True)
    action_required = Column(Boolean, nullable=True)
    suggested_actions = Column(JSONB, nullable=True)

    # Additional analysis data
    thread_info = Column(JSONB, nullable=True)
    attachment_analysis = Column(JSONB, nullable=True)
    spam_probability = Column(JSON, nullable=True)

    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    analyzed_at = Column(DateTime, default=func.now(), nullable=False)
    analysis_version = Column(String(50), nullable=True)

    # Relationships
    content_item = relationship("KnowledgeBaseItem")
    workflow = relationship("EmailWorkflow")

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_analysis_content_workflow', 'content_item_id', 'workflow_id'),
        Index('idx_email_analysis_importance', 'importance_score'),
        Index('idx_email_analysis_analyzed_at', 'analyzed_at'),
    )

    def __repr__(self):
        return f"<EmailAnalysisResult(id={self.id}, importance={self.importance_score}, action_required={self.action_required})>"


class EmailTaskLink(Base):
    """Model linking emails to created tasks."""
    __tablename__ = "email_task_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_base_items.id'), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id'), nullable=False, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('email_workflows.id'), nullable=True, index=True)

    # Link metadata
    link_type = Column(String(50), nullable=False)  # 'primary', 'followup', 'related'
    importance_score = Column(JSON, nullable=True)  # Score at time of task creation
    categories = Column(JSONB, nullable=True)  # Categories at time of task creation

    # Timing
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    task_completed_at = Column(DateTime, nullable=True)
    followup_scheduled_at = Column(DateTime, nullable=True)

    # Relationships
    content_item = relationship("KnowledgeBaseItem")
    task = relationship("Task")
    workflow = relationship("EmailWorkflow")

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_task_links_content_task', 'content_item_id', 'task_id'),
        Index('idx_email_task_links_workflow_type', 'workflow_id', 'link_type'),
        Index('idx_email_task_links_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<EmailTaskLink(id={self.id}, content={self.content_item_id}, task={self.task_id}, type={self.link_type})>"


class EmailFollowupSchedule(Base):
    """Model for tracking scheduled email follow-ups."""
    __tablename__ = "email_followup_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_base_items.id'), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id'), nullable=True, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('email_workflows.id'), nullable=True, index=True)

    # Follow-up details
    followup_type = Column(String(50), nullable=False)  # 'response_check', 'status_update', 'deadline_reminder'
    scheduled_date = Column(DateTime, nullable=False, index=True)
    followup_notes = Column(Text, nullable=True)
    priority = Column(String(20), nullable=True)  # 'low', 'medium', 'high', 'urgent'

    # Status
    status = Column(String(50), nullable=False, default="scheduled")  # 'scheduled', 'sent', 'completed', 'cancelled'
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Notification settings
    notification_sent = Column(Boolean, default=False, nullable=False)
    notification_sent_at = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0, nullable=False)

    # Metadata
    followup_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    content_item = relationship("KnowledgeBaseItem")
    task = relationship("Task")
    workflow = relationship("EmailWorkflow")

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_followups_scheduled_date', 'scheduled_date'),
        Index('idx_email_followups_status_date', 'status', 'scheduled_date'),
        Index('idx_email_followups_content_task', 'content_item_id', 'task_id'),
    )

    def __repr__(self):
        return f"<EmailFollowupSchedule(id={self.id}, type={self.followup_type}, date={self.scheduled_date})>"


class EmailTemplate(Base):
    """Model for storing email processing templates."""
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Template configuration
    template_type = Column(String(50), nullable=False)  # 'analysis', 'task_creation', 'followup'
    config = Column(JSONB, nullable=False)  # Template configuration as JSON

    # Template metadata
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    # Audit fields
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_templates_type_active', 'template_type', 'is_active'),
        Index('idx_email_templates_default', 'is_default'),
    )

    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name={self.name}, type={self.template_type})>"


class EmailWorkflowStats(Base):
    """Model for storing email workflow statistics."""
    __tablename__ = "email_workflow_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)

    # Statistics
    total_workflows = Column(Integer, default=0, nullable=False)
    successful_workflows = Column(Integer, default=0, nullable=False)
    failed_workflows = Column(Integer, default=0, nullable=False)

    total_emails_processed = Column(Integer, default=0, nullable=False)
    total_tasks_created = Column(Integer, default=0, nullable=False)
    total_followups_scheduled = Column(Integer, default=0, nullable=False)

    avg_processing_time_ms = Column(Integer, nullable=True)
    avg_importance_score = Column(JSON, nullable=True)

    # Category breakdown
    emails_by_category = Column(JSONB, nullable=True)
    tasks_by_priority = Column(JSONB, nullable=True)

    # Metadata
    stats_metadata = Column(JSONB, nullable=True)
    calculated_at = Column(DateTime, default=func.now(), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_workflow_stats_user_period', 'user_id', 'period_start', 'period_end'),
        Index('idx_email_workflow_stats_calculated', 'calculated_at'),
    )

    def __repr__(self):
        return f"<EmailWorkflowStats(id={self.id}, user={self.user_id}, period={self.period_start} to {self.period_end})>"
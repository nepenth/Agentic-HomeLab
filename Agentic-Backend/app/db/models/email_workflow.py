"""
Database models for email workflow system.

This module defines additional database models specific to email workflow
functionality, extending the existing content and task models.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index, Float
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


class EmailWorkflowLogLevel(str, enum.Enum):
    """Log levels for email workflow logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


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


class EmailWorkflowSettings(Base):
    """Model for storing user-configurable email workflow settings."""
    __tablename__ = "email_workflow_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=False, index=True)

    # Settings name and description
    settings_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Processing settings
    max_emails_per_workflow = Column(Integer, default=50, nullable=False)
    importance_threshold = Column(Float, default=0.7, nullable=False)  # Use Float instead of JSON
    spam_threshold = Column(Float, default=0.8, nullable=False)
    default_task_priority = Column(String(20), default="medium", nullable=False)

    # Timeout settings (in seconds)
    analysis_timeout_seconds = Column(Integer, default=120, nullable=False)
    task_conversion_timeout_seconds = Column(Integer, default=60, nullable=False)
    ollama_request_timeout_seconds = Column(Integer, default=60, nullable=False)

    # Retry settings
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay_seconds = Column(Integer, default=1, nullable=False)

    # Automation settings
    create_tasks_automatically = Column(Boolean, default=True, nullable=False)
    schedule_followups = Column(Boolean, default=True, nullable=False)
    process_attachments = Column(Boolean, default=True, nullable=False)

    # Metadata
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    # Audit fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_workflow_settings_user_name', 'user_id', 'settings_name'),
        Index('idx_email_workflow_settings_default', 'user_id', 'is_default'),
        Index('idx_email_workflow_settings_active', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f"<EmailWorkflowSettings(id={self.id}, user={self.user_id}, name={self.settings_name})>"

    def to_dict(self, load_attrs=True):
        """
        Convert model to dictionary with async-safe attribute access.
        
        Args:
            load_attrs: If True, loads all attributes immediately to prevent lazy loading issues
        """
        if load_attrs:
            # Force loading of all attributes to prevent lazy loading issues in async context
            _ = (
                self.id, self.user_id, self.settings_name, self.description,
                self.max_emails_per_workflow, self.importance_threshold, self.spam_threshold,
                self.default_task_priority, self.analysis_timeout_seconds,
                self.task_conversion_timeout_seconds, self.ollama_request_timeout_seconds,
                self.max_retries, self.retry_delay_seconds, self.create_tasks_automatically,
                self.schedule_followups, self.process_attachments, self.is_default,
                self.is_active, self.usage_count, self.created_at, self.updated_at
            )
        
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "settings_name": str(self.settings_name),
            "description": self.description,
            "max_emails_per_workflow": int(self.max_emails_per_workflow),
            "importance_threshold": float(self.importance_threshold),
            "spam_threshold": float(self.spam_threshold),
            "default_task_priority": str(self.default_task_priority),
            "analysis_timeout_seconds": int(self.analysis_timeout_seconds),
            "task_conversion_timeout_seconds": int(self.task_conversion_timeout_seconds),
            "ollama_request_timeout_seconds": int(self.ollama_request_timeout_seconds),
            "max_retries": int(self.max_retries),
            "retry_delay_seconds": int(self.retry_delay_seconds),
            "create_tasks_automatically": bool(self.create_tasks_automatically),
            "schedule_followups": bool(self.schedule_followups),
            "process_attachments": bool(self.process_attachments),
            "is_default": bool(self.is_default),
            "is_active": bool(self.is_active),
            "usage_count": int(self.usage_count),
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
    
    @classmethod
    def get_column_names(cls):
        """Get all column names for this model."""
        return [column.name for column in cls.__table__.columns]


class EmailWorkflowLog(Base):
    """Model for storing email workflow execution logs."""
    __tablename__ = "email_workflow_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('email_workflows.id'), nullable=False, index=True)
    user_id = Column(String(200), nullable=False, index=True)

    # Log details
    level = Column(String(20), nullable=False, default="info", index=True)
    message = Column(Text, nullable=False)
    context = Column(JSONB, nullable=True, default=dict)

    # Workflow phase information
    workflow_phase = Column(String(100), nullable=True)
    email_count = Column(Integer, nullable=True)
    task_count = Column(Integer, nullable=True)

    # Timing
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    workflow = relationship("EmailWorkflow")

    # Indexes for performance
    __table_args__ = (
        Index('idx_email_workflow_logs_workflow_timestamp', 'workflow_id', 'timestamp'),
        Index('idx_email_workflow_logs_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_email_workflow_logs_level_timestamp', 'level', 'timestamp'),
    )

    def __repr__(self):
        return f"<EmailWorkflowLog(id={self.id}, workflow={self.workflow_id}, level={self.level}, phase={self.workflow_phase})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "user_id": self.user_id,
            "level": self.level,
            "message": self.message,
            "context": self.context,
            "workflow_phase": self.workflow_phase,
            "email_count": self.email_count,
            "task_count": self.task_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
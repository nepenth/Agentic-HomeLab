"""
Email synchronization and intelligence models.

This module defines SQLAlchemy models for the email sync system including:
- Email accounts (user email configurations)
- Emails (local email storage)
- Email embeddings (vector search)
- Email attachments (file management)
- Email tasks (AI-generated tasks)
- Email sync history (audit trail)
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.database import Base
import uuid


class EmailAccount(Base):
    """User email account configuration for synchronization."""

    __tablename__ = "email_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Account configuration
    account_type = Column(String(50), nullable=False)  # gmail, outlook, imap, exchange
    email_address = Column(String(255), nullable=False)
    display_name = Column(String(255))

    # Authentication (encrypted)
    auth_type = Column(String(50), nullable=False)  # oauth2, password, app_password
    auth_credentials = Column(JSONB)  # Encrypted auth data

    # Sync configuration
    sync_settings = Column(JSONB, default={})  # folders, date ranges, filters
    sync_interval_minutes = Column(Integer, default=15)
    auto_sync_enabled = Column(Boolean, default=True)
    embedding_model = Column(String(200))  # Embedding model for this account (None = use system default)

    # Sync status
    last_sync_at = Column(TIMESTAMP(timezone=True))
    next_sync_at = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(50), default="pending")  # pending, syncing, success, error
    last_error = Column(Text)
    total_emails_synced = Column(Integer, default=0)

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="email_accounts")
    emails = relationship("Email", back_populates="account", cascade="all, delete-orphan")
    sync_history = relationship("EmailSyncHistory", back_populates="account", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "email_address", name="uq_user_email"),
    )


class Email(Base):
    """Local storage of synchronized email content."""

    __tablename__ = "emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False)

    # Email identifiers
    message_id = Column(String(255), nullable=False)  # From email headers
    thread_id = Column(String(255))
    in_reply_to = Column(String(255))

    # Content
    subject = Column(Text)
    body_text = Column(Text)
    body_html = Column(Text)
    snippet = Column(Text)  # First 200 chars for preview

    # Participants
    sender_email = Column(String(255))
    sender_name = Column(String(255))
    reply_to_email = Column(String(255))
    to_recipients = Column(JSONB, default=[])  # Array of {email, name}
    cc_recipients = Column(JSONB, default=[])
    bcc_recipients = Column(JSONB, default=[])

    # Timestamps
    sent_at = Column(TIMESTAMP(timezone=True))
    received_at = Column(TIMESTAMP(timezone=True))

    # Classification
    importance_score = Column(Float, default=0.5)  # 0.0 to 1.0
    urgency_score = Column(Float, default=0.5)
    category = Column(String(100))  # work, personal, finance, travel, etc.
    labels = Column(JSONB, default=[])  # Array of label strings

    # Email metadata
    folder_path = Column(String(500))  # INBOX, Sent, etc.
    size_bytes = Column(Integer)
    has_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)

    # Status flags
    is_read = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    is_important = Column(Boolean, default=False)
    is_spam = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    # Processing status
    embeddings_generated = Column(Boolean, default=False)
    tasks_generated = Column(Boolean, default=False)
    last_processed_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="emails")
    account = relationship("EmailAccount", back_populates="emails")
    embeddings = relationship("EmailEmbedding", back_populates="email", cascade="all, delete-orphan")
    attachments = relationship("EmailAttachment", back_populates="email", cascade="all, delete-orphan")
    tasks = relationship("EmailTask", back_populates="email", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("account_id", "message_id", name="uq_account_message"),
    )


class EmailEmbedding(Base):
    """Vector embeddings for semantic email search."""

    __tablename__ = "email_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)

    # Embedding metadata
    embedding_type = Column(String(50), nullable=False)  # subject, body, combined, summary
    content_hash = Column(String(64))  # SHA256 of source content

    # Vector embedding
    embedding_vector = Column(Vector(1024))  # Snowflake Arctic Embed 2.0 dimensions

    # Model info
    model_name = Column(String(100))
    model_version = Column(String(50))

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    email = relationship("Email", back_populates="embeddings")

    # Constraints
    __table_args__ = (
        UniqueConstraint("email_id", "embedding_type", name="uq_email_embedding_type"),
    )


class EmailAttachment(Base):
    """Email attachments with extracted content and embeddings."""

    __tablename__ = "email_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)

    # File info
    filename = Column(String(500), nullable=False)
    content_type = Column(String(200))
    content_id = Column(String(255))  # For inline attachments
    size_bytes = Column(Integer)

    # Storage
    storage_type = Column(String(50), default="local")  # local, s3, gcs
    file_path = Column(Text)  # Local or cloud storage path
    content_hash = Column(String(64))  # SHA256 for deduplication

    # Processing
    is_inline = Column(Boolean, default=False)
    extracted_text = Column(Text)  # OCR/extracted text for search
    embedding_vector = Column(Vector(1536))  # For document similarity search
    embeddings_generated = Column(Boolean, default=False)

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    email = relationship("Email", back_populates="attachments")

    # Constraints
    __table_args__ = (
        UniqueConstraint("email_id", "filename", name="uq_email_attachment"),
    )


class EmailTask(Base):
    """Tasks automatically generated from email analysis."""

    __tablename__ = "email_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Task content
    title = Column(String(500), nullable=False)
    description = Column(Text)
    task_type = Column(String(100))  # reply, followup, calendar, action_item, reminder

    # Scheduling
    due_date = Column(TIMESTAMP(timezone=True))
    priority = Column(Integer, default=3)  # 1=urgent, 5=low
    estimated_duration_minutes = Column(Integer)

    # Status
    status = Column(String(50), default="pending")  # pending, in_progress, completed, cancelled
    completion_percentage = Column(Integer, default=0)

    # Generation metadata
    auto_generated = Column(Boolean, default=True)
    generation_prompt = Column(Text)
    generation_model = Column(String(100))
    confidence_score = Column(Float)  # 0.0 to 1.0

    # Context
    related_emails = Column(JSONB, default=[])  # Array of related email IDs
    action_required = Column(Boolean, default=False)
    external_references = Column(JSONB, default={})  # Calendar events, contacts, etc.

    # Completion tracking
    completed_at = Column(TIMESTAMP(timezone=True))
    completed_by = Column(Integer, ForeignKey("users.id"))

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    email = relationship("Email", back_populates="tasks")
    user = relationship("User", foreign_keys=[user_id])
    completed_by_user = relationship("User", foreign_keys=[completed_by])


class EmailSyncHistory(Base):
    """Audit log of email synchronization operations."""

    __tablename__ = "email_sync_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False)

    # Sync details
    sync_type = Column(String(50), nullable=False)  # full, incremental, manual
    started_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))
    status = Column(String(50), nullable=False)  # running, success, error, cancelled

    # Results
    emails_processed = Column(Integer, default=0)
    emails_added = Column(Integer, default=0)
    emails_updated = Column(Integer, default=0)
    emails_deleted = Column(Integer, default=0)
    attachments_processed = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSONB)

    # Performance metrics
    duration_seconds = Column(Integer)
    memory_usage_mb = Column(Integer)
    api_calls_made = Column(Integer)

    # Relationships
    account = relationship("EmailAccount", back_populates="sync_history")
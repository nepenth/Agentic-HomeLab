"""
Database models for OCR workflow system.

This module defines database models for OCR (Optical Character Recognition) workflow
functionality, supporting batch processing of images and document generation.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.database import Base


class OCRWorkflowStatus(str, enum.Enum):
    """Status of OCR workflow processing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OCRBatchStatus(str, enum.Enum):
    """Status of OCR batch processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRWorkflow(Base):
    """Model for tracking OCR workflow executions."""
    __tablename__ = "ocr_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=False, index=True)
    workflow_name = Column(String(200), nullable=True)
    ocr_model = Column(String(200), nullable=False, default="deepseek-ocr")  # Configurable OCR model

    # Workflow configuration
    processing_options = Column(JSONB, nullable=True)  # Processing settings

    # Status and timing
    status = Column(String(50), nullable=False, default="pending", index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Statistics
    total_images = Column(Integer, default=0, nullable=False)
    processed_images = Column(Integer, default=0, nullable=False)
    total_pages = Column(Integer, default=0, nullable=False)  # For multi-page documents

    # Error tracking
    error_message = Column(Text, nullable=True)
    warning_messages = Column(JSONB, nullable=True)

    # Metadata
    workflow_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    batches = relationship("OCRBatch", back_populates="workflow")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ocr_workflows_user_status', 'user_id', 'status'),
        Index('idx_ocr_workflows_started_at', 'started_at'),
        Index('idx_ocr_workflows_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<OCRWorkflow(id={self.id}, user={self.user_id}, status={self.status})>"


class OCRBatch(Base):
    """Model for OCR batch processing (group of images as one document)."""
    __tablename__ = "ocr_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('ocr_workflows.id'), nullable=False, index=True)
    batch_name = Column(String(200), nullable=True)  # User-defined name for the batch
    document_title = Column(String(500), nullable=True)  # Generated or user-defined title

    # Batch configuration
    status = Column(String(50), nullable=False, default="pending", index=True)
    processing_order = Column(Integer, default=0, nullable=False)  # Order in workflow

    # Image processing
    total_images = Column(Integer, default=0, nullable=False)
    processed_images = Column(Integer, default=0, nullable=False)

    # Results
    combined_markdown = Column(Text, nullable=True)  # Combined markdown from all images
    page_count = Column(Integer, default=0, nullable=False)  # Number of pages in final document

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Metadata
    batch_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    workflow = relationship("OCRWorkflow", back_populates="batches")
    images = relationship("OCRImage", back_populates="batch", order_by="OCRImage.processing_order")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ocr_batches_workflow_status', 'workflow_id', 'status'),
        Index('idx_ocr_batches_processing_order', 'workflow_id', 'processing_order'),
    )

    def __repr__(self):
        return f"<OCRBatch(id={self.id}, workflow={self.workflow_id}, status={self.status})>"


class OCRImage(Base):
    """Model for individual OCR image processing."""
    __tablename__ = "ocr_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('ocr_batches.id'), nullable=False, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('ocr_workflows.id'), nullable=False, index=True)

    # File information
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)  # Path to stored image file
    file_size = Column(Integer, nullable=True)  # File size in bytes
    mime_type = Column(String(100), nullable=True)

    # Processing information
    status = Column(String(50), nullable=False, default="pending", index=True)
    processing_order = Column(Integer, default=0, nullable=False)  # Order within batch
    ocr_model_used = Column(String(200), nullable=True)  # Model used for this image

    # OCR results
    raw_markdown = Column(Text, nullable=True)  # Raw OCR output
    processed_markdown = Column(Text, nullable=True)  # Processed/cleaned markdown
    confidence_score = Column(Float, nullable=True)  # OCR confidence (0-1)

    # Image metadata
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    image_dpi = Column(Integer, nullable=True)

    # Timing
    uploaded_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Metadata
    image_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    batch = relationship("OCRBatch", back_populates="images")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ocr_images_batch_status', 'batch_id', 'status'),
        Index('idx_ocr_images_workflow_status', 'workflow_id', 'status'),
        Index('idx_ocr_images_processing_order', 'batch_id', 'processing_order'),
    )

    def __repr__(self):
        return f"<OCRImage(id={self.id}, batch={self.batch_id}, status={self.status})>"


class OCRDocument(Base):
    """Model for storing final OCR documents (exported versions)."""
    __tablename__ = "ocr_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('ocr_batches.id'), nullable=True, index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('ocr_workflows.id'), nullable=True, index=True)

    # Document information
    title = Column(String(500), nullable=True)
    document_type = Column(String(50), nullable=False, default="markdown")  # markdown, pdf, docx

    # Content
    content = Column(Text, nullable=True)  # For markdown/text content
    file_path = Column(String(1000), nullable=True)  # For binary files (PDF, DOCX)
    file_size = Column(Integer, nullable=True)

    # Export metadata
    export_format = Column(String(50), nullable=True)  # pdf, docx, markdown
    exported_at = Column(DateTime, default=func.now(), nullable=False)

    # Metadata
    document_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    batch = relationship("OCRBatch")
    workflow = relationship("OCRWorkflow")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ocr_documents_user_type', 'user_id', 'document_type'),
        Index('idx_ocr_documents_batch', 'batch_id'),
        Index('idx_ocr_documents_exported_at', 'exported_at'),
    )

    def __repr__(self):
        return f"<OCRDocument(id={self.id}, user={self.user_id}, type={self.document_type})>"


class OCRWorkflowStats(Base):
    """Model for storing OCR workflow statistics."""
    __tablename__ = "ocr_workflow_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(200), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)

    # Statistics
    total_workflows = Column(Integer, default=0, nullable=False)
    successful_workflows = Column(Integer, default=0, nullable=False)
    failed_workflows = Column(Integer, default=0, nullable=False)

    total_images_processed = Column(Integer, default=0, nullable=False)
    total_batches_created = Column(Integer, default=0, nullable=False)
    total_documents_exported = Column(Integer, default=0, nullable=False)

    avg_processing_time_ms = Column(Integer, nullable=True)
    avg_confidence_score = Column(Float, nullable=True)

    # Category breakdown
    images_by_status = Column(JSONB, nullable=True)
    workflows_by_model = Column(JSONB, nullable=True)

    # Metadata
    stats_metadata = Column(JSONB, nullable=True)
    calculated_at = Column(DateTime, default=func.now(), nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_ocr_workflow_stats_user_period', 'user_id', 'period_start', 'period_end'),
        Index('idx_ocr_workflow_stats_calculated', 'calculated_at'),
    )

    def __repr__(self):
        return f"<OCRWorkflowStats(id={self.id}, user={self.user_id}, period={self.period_start} to {self.period_end})>"


class OCRWorkflowLog(Base):
    """Model for storing OCR workflow execution logs."""
    __tablename__ = "ocr_workflow_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('ocr_workflows.id'), nullable=True, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('ocr_batches.id'), nullable=True, index=True)
    image_id = Column(UUID(as_uuid=True), ForeignKey('ocr_images.id'), nullable=True, index=True)
    user_id = Column(String(200), nullable=False, index=True)

    # Log details
    level = Column(String(20), nullable=False, default="info", index=True)
    message = Column(Text, nullable=False)
    context = Column(JSONB, nullable=True, default=dict)

    # Workflow phase information
    workflow_phase = Column(String(100), nullable=True)
    batch_count = Column(Integer, nullable=True)
    image_count = Column(Integer, nullable=True)

    # Timing
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    workflow = relationship("OCRWorkflow")
    batch = relationship("OCRBatch")
    image = relationship("OCRImage")

    # Indexes for performance
    __table_args__ = (
        Index('idx_ocr_workflow_logs_workflow_timestamp', 'workflow_id', 'timestamp'),
        Index('idx_ocr_workflow_logs_batch_timestamp', 'batch_id', 'timestamp'),
        Index('idx_ocr_workflow_logs_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_ocr_workflow_logs_level_timestamp', 'level', 'timestamp'),
    )

    def __repr__(self):
        return f"<OCRWorkflowLog(id={self.id}, workflow={self.workflow_id}, level={self.level}, phase={self.workflow_phase})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "batch_id": str(self.batch_id) if self.batch_id else None,
            "image_id": str(self.image_id) if self.image_id else None,
            "user_id": self.user_id,
            "level": self.level,
            "message": self.message,
            "context": self.context,
            "workflow_phase": self.workflow_phase,
            "batch_count": self.batch_count,
            "image_count": self.image_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
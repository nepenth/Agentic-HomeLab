"""
Database models for model performance tracking.

This module defines database models for tracking AI model performance,
usage statistics, and selection metrics.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class ModelPerformanceMetrics(Base):
    """Tracks performance metrics for AI models."""
    __tablename__ = "model_performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=True, index=True)
    model_name = Column(String(255), nullable=False, index=True)
    model_version = Column(String(100), nullable=True)
    task_type = Column(String(100), nullable=False, index=True)  # text_generation, image_analysis, etc.
    content_type = Column(String(100), nullable=False, index=True)  # text, image, audio, etc.

    # Performance metrics
    success_rate = Column(Float, nullable=False, default=0.0)
    average_response_time_ms = Column(Float, nullable=False, default=0.0)
    average_tokens_per_second = Column(Float, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    total_requests = Column(Integer, nullable=False, default=0)

    # Model capabilities and metadata
    capabilities = Column(ARRAY(String), nullable=True)  # ['vision', 'text', 'audio', 'embedding']
    model_size_mb = Column(Float, nullable=True)
    context_length = Column(Integer, nullable=True)

    # Performance score (composite metric)
    performance_score = Column(Float, nullable=False, default=0.0)

    # Metadata
    model_metadata = Column(JSONB, nullable=True, default=dict)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ModelPerformanceMetrics(model={self.model_name}, task={self.task_type}, score={self.performance_score:.2f})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "task_type": self.task_type,
            "content_type": self.content_type,
            "success_rate": self.success_rate,
            "average_response_time_ms": self.average_response_time_ms,
            "average_tokens_per_second": self.average_tokens_per_second,
            "error_count": self.error_count,
            "total_requests": self.total_requests,
            "capabilities": self.capabilities,
            "model_size_mb": self.model_size_mb,
            "context_length": self.context_length,
            "performance_score": self.performance_score,
            "model_metadata": self.model_metadata,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelUsageLog(Base):
    """Logs individual model usage events."""
    __tablename__ = "model_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=True, index=True)
    model_name = Column(String(255), nullable=False, index=True)
    model_version = Column(String(100), nullable=True)
    task_type = Column(String(100), nullable=False, index=True)
    content_type = Column(String(100), nullable=False, index=True)

    # Usage details
    request_id = Column(String(255), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Performance data
    processing_time_ms = Column(Float, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    tokens_per_second = Column(Float, nullable=True)
    success = Column(Boolean, nullable=False, default=True)

    # Request/Response details
    input_length = Column(Integer, nullable=True)  # characters or tokens
    output_length = Column(Integer, nullable=True)  # characters or tokens
    request_params = Column(JSONB, nullable=True, default=dict)
    response_metadata = Column(JSONB, nullable=True, default=dict)

    # Error information
    error_type = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    # Context
    source = Column(String(100), nullable=True)  # api, agent, workflow, etc.
    endpoint = Column(String(255), nullable=True)  # API endpoint used

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ModelUsageLog(model={self.model_name}, task={self.task_type}, success={self.success})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "task_type": self.task_type,
            "content_type": self.content_type,
            "request_id": self.request_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
            "tokens_per_second": self.tokens_per_second,
            "success": self.success,
            "input_length": self.input_length,
            "output_length": self.output_length,
            "request_params": self.request_params,
            "response_metadata": self.response_metadata,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "source": self.source,
            "endpoint": self.endpoint,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelRegistry(Base):
    """Registry of available AI models."""
    __tablename__ = "model_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    model_name = Column(String(255), nullable=False, unique=True, index=True)
    model_version = Column(String(100), nullable=True)

    # Model metadata
    provider = Column(String(100), nullable=True)  # ollama, openai, anthropic, etc.
    model_family = Column(String(100), nullable=True)  # llama, gpt, claude, etc.
    capabilities = Column(ARRAY(String), nullable=True)

    # Technical specs
    context_length = Column(Integer, nullable=True)
    model_size_mb = Column(Float, nullable=True)
    quantization = Column(String(50), nullable=True)  # Q8_0, Q4_0, etc.

    # Status and availability
    is_available = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_checked = Column(DateTime(timezone=True), nullable=True)
    health_status = Column(String(50), nullable=True, default="unknown")  # healthy, degraded, unhealthy

    # Configuration
    default_config = Column(JSONB, nullable=True, default=dict)
    supported_formats = Column(ARRAY(String), nullable=True)  # jpeg, png, mp3, etc.

    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    registry_metadata = Column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    performance_metrics = relationship("ModelPerformanceMetrics", back_populates="model", cascade="all, delete-orphan")
    usage_logs = relationship("ModelUsageLog", back_populates="model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ModelRegistry(name={self.model_name}, provider={self.provider}, available={self.is_available})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "provider": self.provider,
            "model_family": self.model_family,
            "capabilities": self.capabilities,
            "context_length": self.context_length,
            "model_size_mb": self.model_size_mb,
            "quantization": self.quantization,
            "is_available": self.is_available,
            "is_active": self.is_active,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "health_status": self.health_status,
            "default_config": self.default_config,
            "supported_formats": self.supported_formats,
            "description": self.description,
            "tags": self.tags,
            "registry_metadata": self.registry_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Add relationships to existing models
ModelPerformanceMetrics.model = relationship("ModelRegistry", back_populates="performance_metrics")
ModelUsageLog.model = relationship("ModelRegistry", back_populates="usage_logs")
"""
Integration Layer Database Models
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.database import Base


class QueueItem(Base):
    """Database model for processing queue items"""
    __tablename__ = "queue_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_name = Column(String(100), nullable=False)
    type = Column(String(50), default="generic")  # workflow_execution, webhook_delivery, etc.
    priority = Column(String(20), default="normal")  # low, normal, high, critical
    data = Column(JSON, nullable=False)  # Item data/payload
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    processing_duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    callback_url = Column(String(500), nullable=True)
    processing_deadline = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_queue_items_queue_name', 'queue_name'),
        Index('idx_queue_items_status', 'status'),
        Index('idx_queue_items_priority', 'priority'),
        Index('idx_queue_items_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "queue_name": self.queue_name,
            "type": self.type,
            "priority": self.priority,
            "data": self.data,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "processing_duration_ms": self.processing_duration_ms,
            "error_message": self.error_message,
            "callback_url": self.callback_url,
            "processing_deadline": self.processing_deadline.isoformat() if self.processing_deadline else None
        }


class BackendService(Base):
    """Database model for backend services in load balancer"""
    __tablename__ = "backend_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    service_type = Column(String(50), nullable=False)  # ai_processing, data_analysis, etc.
    supported_request_types = Column(JSON, default=list)  # List of supported request types
    is_active = Column(Boolean, default=True)
    health_check_url = Column(String(500), nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(20), default="unknown")  # healthy, unhealthy, unknown
    max_concurrent_requests = Column(Integer, default=10)
    request_timeout_seconds = Column(Integer, default=30)
    rate_limit_per_minute = Column(Integer, default=60)
    config = Column(JSON, default=dict)  # Service-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    metrics = relationship("BackendServiceMetrics", back_populates="service")

    # Indexes
    __table_args__ = (
        Index('idx_backend_services_type', 'service_type'),
        Index('idx_backend_services_active', 'is_active'),
        Index('idx_backend_services_health', 'health_status'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "url": self.url,
            "service_type": self.service_type,
            "supported_request_types": self.supported_request_types,
            "is_active": self.is_active,
            "health_check_url": self.health_check_url,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "health_status": self.health_status,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout_seconds": self.request_timeout_seconds,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class BackendServiceMetrics(Base):
    """Database model for backend service performance metrics"""
    __tablename__ = "backend_service_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("backend_services.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    average_response_time_ms = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)
    active_connections = Column(Integer, default=0)
    queue_depth = Column(Integer, default=0)
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)

    # Relationships
    service = relationship("BackendService", back_populates="metrics")

    # Indexes
    __table_args__ = (
        Index('idx_backend_metrics_service_id', 'service_id'),
        Index('idx_backend_metrics_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "service_id": str(self.service_id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "average_response_time_ms": self.average_response_time_ms,
            "error_rate": self.error_rate,
            "active_connections": self.active_connections,
            "queue_depth": self.queue_depth,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_mb": self.memory_usage_mb
        }


class LoadBalancerStats(Base):
    """Database model for load balancer statistics"""
    __tablename__ = "load_balancer_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_requests = Column(Integer, default=0)
    active_connections = Column(Integer, default=0)
    average_response_time_ms = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)
    backend_health_summary = Column(JSON, default=dict)  # Health status of all backends
    request_distribution = Column(JSON, default=dict)  # How requests were distributed
    performance_metrics = Column(JSON, default=dict)  # Overall performance data

    # Indexes
    __table_args__ = (
        Index('idx_lb_stats_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "total_requests": self.total_requests,
            "active_connections": self.active_connections,
            "average_response_time_ms": self.average_response_time_ms,
            "error_rate": self.error_rate,
            "backend_health_summary": self.backend_health_summary,
            "request_distribution": self.request_distribution,
            "performance_metrics": self.performance_metrics
        }


class APIGatewayMetrics(Base):
    """Database model for API gateway metrics"""
    __tablename__ = "api_gateway_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    request_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    average_response_time_ms = Column(Float, default=0.0)
    rate_limit_hits = Column(Integer, default=0)
    authentication_failures = Column(Integer, default=0)

    # Indexes
    __table_args__ = (
        Index('idx_api_metrics_endpoint', 'endpoint'),
        Index('idx_api_metrics_method', 'method'),
        Index('idx_api_metrics_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "endpoint": self.endpoint,
            "method": self.method,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "average_response_time_ms": self.average_response_time_ms,
            "rate_limit_hits": self.rate_limit_hits,
            "authentication_failures": self.authentication_failures
        }
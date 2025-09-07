"""
Database models for HTTP request logging.

This module defines database models for tracking HTTP client requests,
responses, performance metrics, and error handling.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class HttpRequestLog(Base):
    """Logs HTTP client requests and responses."""
    __tablename__ = "http_request_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    request_id = Column(String(255), nullable=False, unique=True, index=True)

    # Request details
    method = Column(String(10), nullable=False, index=True)  # GET, POST, PUT, DELETE
    url = Column(Text, nullable=False)
    headers = Column(JSONB, nullable=True, default=dict)
    request_body_size = Column(Integer, nullable=True)  # bytes
    user_agent = Column(Text, nullable=True)

    # Response details
    status_code = Column(Integer, nullable=True, index=True)
    response_headers = Column(JSONB, nullable=True, default=dict)
    response_body_size = Column(Integer, nullable=True)  # bytes
    response_time_ms = Column(Float, nullable=True)

    # Performance and reliability
    retry_count = Column(Integer, nullable=False, default=0)
    circuit_breaker_state = Column(String(50), nullable=True)  # closed, open, half_open
    rate_limit_hit = Column(Boolean, nullable=False, default=False)
    rate_limit_info = Column(JSONB, nullable=True, default=dict)

    # Error handling
    error_type = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    is_success = Column(Boolean, nullable=False, default=True)

    # Context and metadata
    source = Column(String(100), nullable=True)  # api, agent, workflow, etc.
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    agent_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    task_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    endpoint = Column(String(255), nullable=True)  # API endpoint or service

    # Authentication and security
    auth_type = Column(String(50), nullable=True)  # api_key, oauth, jwt, none
    has_sensitive_data = Column(Boolean, nullable=False, default=False)

    # Network and connection details
    remote_ip = Column(String(45), nullable=True)  # IPv4/IPv6
    connection_reused = Column(Boolean, nullable=True)
    ssl_handshake_time_ms = Column(Float, nullable=True)

    # Additional metadata
    request_metadata = Column(JSONB, nullable=True, default=dict)
    response_metadata = Column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<HttpRequestLog(id={self.request_id}, method={self.method}, status={self.status_code})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "request_id": self.request_id,
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "request_body_size": self.request_body_size,
            "user_agent": self.user_agent,
            "status_code": self.status_code,
            "response_headers": self.response_headers,
            "response_body_size": self.response_body_size,
            "response_time_ms": self.response_time_ms,
            "retry_count": self.retry_count,
            "circuit_breaker_state": self.circuit_breaker_state,
            "rate_limit_hit": self.rate_limit_hit,
            "rate_limit_info": self.rate_limit_info,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "is_success": self.is_success,
            "source": self.source,
            "user_id": str(self.user_id) if self.user_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "task_id": str(self.task_id) if self.task_id else None,
            "endpoint": self.endpoint,
            "auth_type": self.auth_type,
            "has_sensitive_data": self.has_sensitive_data,
            "remote_ip": self.remote_ip,
            "connection_reused": self.connection_reused,
            "ssl_handshake_time_ms": self.ssl_handshake_time_ms,
            "request_metadata": self.request_metadata,
            "response_metadata": self.response_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class HttpClientMetrics(Base):
    """Aggregated HTTP client performance metrics."""
    __tablename__ = "http_client_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Time window
    time_window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    time_window_end = Column(DateTime(timezone=True), nullable=False, index=True)
    window_duration_minutes = Column(Integer, nullable=False, default=60)

    # Request statistics
    total_requests = Column(Integer, nullable=False, default=0)
    successful_requests = Column(Integer, nullable=False, default=0)
    failed_requests = Column(Integer, nullable=False, default=0)
    retried_requests = Column(Integer, nullable=False, default=0)

    # Performance metrics
    average_response_time_ms = Column(Float, nullable=True)
    median_response_time_ms = Column(Float, nullable=True)
    p95_response_time_ms = Column(Float, nullable=True)
    p99_response_time_ms = Column(Float, nullable=True)

    # Error breakdown
    error_4xx_count = Column(Integer, nullable=False, default=0)
    error_5xx_count = Column(Integer, nullable=False, default=0)
    timeout_count = Column(Integer, nullable=False, default=0)
    connection_error_count = Column(Integer, nullable=False, default=0)

    # Circuit breaker metrics
    circuit_breaker_trips = Column(Integer, nullable=False, default=0)
    circuit_breaker_state_changes = Column(Integer, nullable=False, default=0)

    # Rate limiting metrics
    rate_limit_hits = Column(Integer, nullable=False, default=0)
    rate_limit_delays_total_ms = Column(Float, nullable=False, default=0.0)

    # Throughput metrics
    requests_per_minute = Column(Float, nullable=True)
    bytes_sent_per_minute = Column(Float, nullable=True)
    bytes_received_per_minute = Column(Float, nullable=True)

    # Endpoint breakdown (top endpoints by request count)
    top_endpoints = Column(JSONB, nullable=True, default=dict)

    # Error patterns
    common_errors = Column(JSONB, nullable=True, default=dict)

    # Metadata
    metrics_metadata = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<HttpClientMetrics(window={self.time_window_start} to {self.time_window_end}, requests={self.total_requests})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "time_window_start": self.time_window_start.isoformat() if self.time_window_start else None,
            "time_window_end": self.time_window_end.isoformat() if self.time_window_end else None,
            "window_duration_minutes": self.window_duration_minutes,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retried_requests": self.retried_requests,
            "average_response_time_ms": self.average_response_time_ms,
            "median_response_time_ms": self.median_response_time_ms,
            "p95_response_time_ms": self.p95_response_time_ms,
            "p99_response_time_ms": self.p99_response_time_ms,
            "error_4xx_count": self.error_4xx_count,
            "error_5xx_count": self.error_5xx_count,
            "timeout_count": self.timeout_count,
            "connection_error_count": self.connection_error_count,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "circuit_breaker_state_changes": self.circuit_breaker_state_changes,
            "rate_limit_hits": self.rate_limit_hits,
            "rate_limit_delays_total_ms": self.rate_limit_delays_total_ms,
            "requests_per_minute": self.requests_per_minute,
            "bytes_sent_per_minute": self.bytes_sent_per_minute,
            "bytes_received_per_minute": self.bytes_received_per_minute,
            "top_endpoints": self.top_endpoints,
            "common_errors": self.common_errors,
            "metrics_metadata": self.metrics_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HttpClientConfig(Base):
    """Configuration for HTTP client behavior."""
    __tablename__ = "http_client_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    config_key = Column(String(255), nullable=False, unique=True, index=True)

    # Circuit breaker settings
    circuit_breaker_enabled = Column(Boolean, nullable=False, default=True)
    circuit_breaker_failure_threshold = Column(Integer, nullable=False, default=5)
    circuit_breaker_recovery_timeout = Column(Float, nullable=False, default=60.0)  # seconds
    circuit_breaker_expected_exception = Column(JSONB, nullable=True, default=list)

    # Retry settings
    retry_enabled = Column(Boolean, nullable=False, default=True)
    retry_max_attempts = Column(Integer, nullable=False, default=3)
    retry_backoff_factor = Column(Float, nullable=False, default=2.0)
    retry_status_codes = Column(JSONB, nullable=True, default=[429, 500, 502, 503, 504])

    # Rate limiting settings
    rate_limiting_enabled = Column(Boolean, nullable=False, default=True)
    rate_limit_requests_per_minute = Column(Integer, nullable=False, default=60)
    rate_limit_burst_size = Column(Integer, nullable=False, default=10)

    # Timeout settings
    connect_timeout = Column(Float, nullable=False, default=10.0)
    read_timeout = Column(Float, nullable=False, default=30.0)
    total_timeout = Column(Float, nullable=False, default=300.0)

    # Connection settings
    max_connections = Column(Integer, nullable=False, default=100)
    max_connections_per_host = Column(Integer, nullable=False, default=30)
    keepalive_timeout = Column(Float, nullable=False, default=30.0)

    # Security settings
    ssl_verify = Column(Boolean, nullable=False, default=True)
    ssl_cert_path = Column(String(500), nullable=True)
    ssl_key_path = Column(String(500), nullable=True)

    # Domain whitelisting
    allowed_domains = Column(JSONB, nullable=True, default=list)
    blocked_domains = Column(JSONB, nullable=True, default=list)

    # Metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    config_metadata = Column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<HttpClientConfig(key={self.config_key}, active={self.is_active})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "config_key": self.config_key,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "circuit_breaker_failure_threshold": self.circuit_breaker_failure_threshold,
            "circuit_breaker_recovery_timeout": self.circuit_breaker_recovery_timeout,
            "circuit_breaker_expected_exception": self.circuit_breaker_expected_exception,
            "retry_enabled": self.retry_enabled,
            "retry_max_attempts": self.retry_max_attempts,
            "retry_backoff_factor": self.retry_backoff_factor,
            "retry_status_codes": self.retry_status_codes,
            "rate_limiting_enabled": self.rate_limiting_enabled,
            "rate_limit_requests_per_minute": self.rate_limit_requests_per_minute,
            "rate_limit_burst_size": self.rate_limit_burst_size,
            "connect_timeout": self.connect_timeout,
            "read_timeout": self.read_timeout,
            "total_timeout": self.total_timeout,
            "max_connections": self.max_connections,
            "max_connections_per_host": self.max_connections_per_host,
            "keepalive_timeout": self.keepalive_timeout,
            "ssl_verify": self.ssl_verify,
            "ssl_cert_path": self.ssl_cert_path,
            "ssl_key_path": self.ssl_key_path,
            "allowed_domains": self.allowed_domains,
            "blocked_domains": self.blocked_domains,
            "description": self.description,
            "is_active": self.is_active,
            "config_metadata": self.config_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
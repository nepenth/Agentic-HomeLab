"""
Workflow Database Models
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.database import Base


class WorkflowDefinition(Base):
    """Database model for workflow definitions"""
    __tablename__ = "workflow_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), default="1.0.0")
    steps = Column(JSON, nullable=False)  # Workflow steps definition
    trigger_config = Column(JSON, default=dict)  # Trigger configuration
    priority = Column(String(20), default="normal")  # low, normal, high, critical
    max_execution_time = Column(Integer, default=3600)  # seconds
    resource_requirements = Column(JSON, default=dict)  # CPU, memory, etc.
    workflow_metadata = Column(JSON, default=dict)  # Additional metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)  # User who created it

    # Relationships
    executions = relationship("WorkflowExecution", back_populates="definition")
    schedules = relationship("WorkflowSchedule", back_populates="definition")

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": self.steps,
            "trigger_config": self.trigger_config,
            "priority": self.priority,
            "max_execution_time": self.max_execution_time,
            "resource_requirements": self.resource_requirements,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None
        }


class WorkflowExecution(Base):
    """Database model for workflow executions"""
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed, cancelled
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    current_step = Column(String(255), nullable=True)
    step_results = Column(JSON, default=dict)  # Results from each step
    context = Column(JSON, default=dict)  # Execution context/parameters
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    priority = Column(String(20), default="normal")
    execution_time_ms = Column(Integer, nullable=True)  # Total execution time
    resource_usage = Column(JSON, default=dict)  # CPU, memory usage

    # Relationships
    definition = relationship("WorkflowDefinition", back_populates="executions")
    logs = relationship("WorkflowExecutionLog", back_populates="execution")

    def to_dict(self):
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "current_step": self.current_step,
            "step_results": self.step_results,
            "context": self.context,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "priority": self.priority,
            "execution_time_ms": self.execution_time_ms,
            "resource_usage": self.resource_usage
        }


class WorkflowSchedule(Base):
    """Database model for workflow schedules"""
    __tablename__ = "workflow_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=False)
    trigger_type = Column(String(20), default="scheduled")  # scheduled, event, manual
    cron_expression = Column(String(255), nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    next_run = Column(DateTime, nullable=True)
    last_run = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    parameters = Column(JSON, default=dict)  # Default parameters for execution
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    definition = relationship("WorkflowDefinition", back_populates="schedules")

    def to_dict(self):
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "trigger_type": self.trigger_type,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "is_active": self.is_active,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": str(self.created_by) if self.created_by else None
        }


class WorkflowExecutionLog(Base):
    """Database model for workflow execution logs"""
    __tablename__ = "workflow_execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    step_id = Column(String(255), nullable=True)
    log_level = Column(String(20), default="info")  # debug, info, warning, error
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    log_metadata = Column(JSON, default=dict)  # Additional log data

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="logs")

    def to_dict(self):
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id),
            "step_id": self.step_id,
            "log_level": self.log_level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }


class WorkflowMetrics(Base):
    """Database model for workflow performance metrics"""
    __tablename__ = "workflow_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=True)
    metric_type = Column(String(50), nullable=False)  # execution_time, success_rate, etc.
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metrics_metadata = Column(JSON, default=dict)  # Additional metric data

    def to_dict(self):
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "metric_type": self.metric_type,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }
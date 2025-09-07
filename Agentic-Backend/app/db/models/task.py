from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(ENUM(TaskStatus), nullable=False, default=TaskStatus.PENDING, index=True)
    input = Column(JSONB, nullable=True, default=dict)
    output = Column(JSONB, nullable=True, default=dict)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    celery_task_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Task(id={self.id}, agent_id={self.agent_id}, status='{self.status}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "status": self.status.value,
            "input": self.input,
            "output": self.output,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "celery_task_id": self.celery_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TaskLog(Base):
    __tablename__ = "task_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(ENUM(LogLevel), nullable=False, default=LogLevel.INFO, index=True)
    message = Column(Text, nullable=False)
    context = Column(JSONB, nullable=True, default=dict)
    stream_id = Column(String(255), nullable=True, index=True)  # Redis Stream correlation
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    task = relationship("Task", back_populates="logs")
    agent = relationship("Agent", back_populates="task_logs")
    
    def __repr__(self):
        return f"<TaskLog(id={self.id}, task_id={self.task_id}, level='{self.level}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "agent_id": str(self.agent_id),
            "level": self.level.value,
            "message": self.message,
            "context": self.context,
            "stream_id": self.stream_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
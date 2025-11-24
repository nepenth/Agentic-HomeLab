
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.database import Base

class EmbeddingTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_PERMANENTLY = "failed_permanently"

class EmbeddingTask(Base):
    """
    Tracks the status of embedding generation for emails.
    Acts as a queue and dead-letter queue for embedding jobs.
    """
    __tablename__ = "embedding_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    status = Column(Enum(EmbeddingTaskStatus), default=EmbeddingTaskStatus.PENDING, nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_attempt = Column(DateTime(timezone=True), nullable=True)
    next_retry = Column(DateTime(timezone=True), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    email = relationship("Email", backref="embedding_task")

    def __repr__(self):
        return f"<EmbeddingTask(id={self.id}, email_id={self.email_id}, status='{self.status}', attempts={self.attempts})>"

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback for development without pgvector installed
    from sqlalchemy import Text as Vector


class Embedding(Base):
    __tablename__ = "embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    vector = Column(Vector(1536), nullable=False)  # OpenAI embedding dimension
    content_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash
    meta_data = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="embeddings")
    
    def __repr__(self):
        return f"<Embedding(id={self.id}, task_id={self.task_id})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "content_hash": self.content_hash,
            "meta_data": self.meta_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
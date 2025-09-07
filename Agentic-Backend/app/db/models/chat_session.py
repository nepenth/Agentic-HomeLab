from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_type = Column(String(50), nullable=False, index=True)  # e.g., "agent_creation", "workflow_setup"
    user_id = Column(String(255), nullable=True, index=True)  # For future user tracking
    model_name = Column(String(255), nullable=False)  # Ollama model used
    title = Column(String(500), nullable=True)  # Auto-generated or user-provided title
    status = Column(String(50), nullable=False, default="active", index=True)  # active, completed, archived, resumable
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_resumable = Column(Boolean, nullable=False, default=True, index=True)  # Always resumable by default
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Configuration
    config = Column(JSONB, nullable=True, default=dict)  # Session-specific config (temperature, etc.)

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, type='{self.session_type}', model='{self.model_name}', status='{self.status}')>"

    def to_dict(self):
        # Safely get message count without triggering lazy loading
        try:
            message_count = len(self.messages) if hasattr(self, 'messages') and self.messages is not None else 0
        except:
            message_count = 0

        return {
            "id": str(self.id),
            "session_type": self.session_type,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "title": self.title,
            "status": self.status,
            "is_active": self.is_active,
            "is_resumable": self.is_resumable,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at is not None else None,
            "config": self.config,
            "message_count": message_count
        }


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=True)  # "text", "json", "code", "error"
    message_metadata = Column(JSONB, nullable=True, default=dict)  # Additional data (tokens used, etc.)
    token_count = Column(Integer, nullable=True)  # Approximate token count
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}', type='{self.message_type}')>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "message_metadata": self.message_metadata,
            "token_count": self.token_count,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None
        }
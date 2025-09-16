"""
Chat Session and Conversation Models for Email Assistant.

These models support:
- Multi-turn conversations with context persistence
- Model selection and switching within sessions
- Rich message types (text, tasks, emails, search results)
- User preferences and assistant settings
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from app.db.database import Base


class MessageType(str, Enum):
    """Types of messages in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ACTION = "action"  # Assistant performed an action
    SEARCH_RESULT = "search_result"
    TASK_UPDATE = "task_update"
    EMAIL_CONTENT = "email_content"


class ChatSession(Base):
    """
    Chat session for Email Assistant conversations.

    Maintains conversation context, user preferences, and session metadata.
    """
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session metadata
    title = Column(String(255), nullable=True)  # Auto-generated or user-set title
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_activity = Column(DateTime, default=func.now(), nullable=False)

    # Session settings
    selected_model = Column(String(100), nullable=False, default="llama2")
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)

    # Session state
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)

    # Context and preferences
    context = Column(JSONB, default=dict)  # Session-specific context
    preferences = Column(JSONB, default=dict)  # User preferences for this session

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    user = relationship("User", backref="chat_sessions")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, model={self.selected_model})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "selected_model": self.selected_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "context": self.context,
            "preferences": self.preferences
        }


class ChatMessage(Base):
    """
    Individual message within a chat session.

    Supports rich message types including text, actions, search results, and task updates.
    """
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)

    # Message metadata
    message_type = Column(String(20), nullable=False, default=MessageType.USER.value)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    sequence_number = Column(Integer, nullable=False)  # Order within session

    # Message content
    content = Column(Text, nullable=False)  # Main message text
    rich_content = Column(JSONB, default=dict)  # Structured data (tasks, emails, search results)

    # Assistant-specific fields
    model_used = Column(String(100), nullable=True)  # Model used to generate this message
    tokens_used = Column(Integer, nullable=True)  # Token count for this message
    generation_time_ms = Column(Float, nullable=True)  # Response generation time

    # Context and metadata
    message_metadata = Column(JSONB, default=dict)  # Additional message metadata
    user_feedback = Column(String(20), nullable=True)  # thumbs_up, thumbs_down, etc.

    # Action tracking
    actions_performed = Column(JSONB, default=list)  # List of actions assistant performed
    related_entities = Column(JSONB, default=dict)  # Related tasks, emails, etc.

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, type={self.message_type}, content={self.content[:50]}...)>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "message_type": self.message_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sequence_number": self.sequence_number,
            "content": self.content,
            "rich_content": self.rich_content,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "generation_time_ms": self.generation_time_ms,
            "message_metadata": self.message_metadata,
            "user_feedback": self.user_feedback,
            "actions_performed": self.actions_performed,
            "related_entities": self.related_entities
        }


class UserChatPreferences(Base):
    """
    User preferences for Email Assistant chat functionality.

    Stores default settings, frequently used models, and personalization data.
    """
    __tablename__ = "user_chat_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Default settings
    default_model = Column(String(100), nullable=False, default="llama2")
    default_temperature = Column(Float, default=0.7)
    default_max_tokens = Column(Integer, default=2048)

    # UI preferences
    show_model_selector = Column(Boolean, default=True)
    show_quick_actions = Column(Boolean, default=True)
    enable_auto_suggestions = Column(Boolean, default=True)
    theme = Column(String(20), default="auto")  # light, dark, auto

    # Behavior preferences
    auto_save_conversations = Column(Boolean, default=True)
    enable_streaming = Column(Boolean, default=True)
    max_conversation_history = Column(Integer, default=100)  # Max messages per session

    # Personalization data
    frequent_models = Column(JSONB, default=list)  # List of frequently used models
    custom_prompts = Column(JSONB, default=dict)  # Custom system prompts
    quick_actions = Column(JSONB, default=list)  # Customized quick action buttons

    # Analytics and usage
    total_messages_sent = Column(Integer, default=0)
    favorite_features = Column(JSONB, default=list)
    feedback_history = Column(JSONB, default=list)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="chat_preferences")

    def __repr__(self):
        return f"<UserChatPreferences(user_id={self.user_id}, default_model={self.default_model})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "default_model": self.default_model,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "show_model_selector": self.show_model_selector,
            "show_quick_actions": self.show_quick_actions,
            "enable_auto_suggestions": self.enable_auto_suggestions,
            "theme": self.theme,
            "auto_save_conversations": self.auto_save_conversations,
            "enable_streaming": self.enable_streaming,
            "max_conversation_history": self.max_conversation_history,
            "frequent_models": self.frequent_models,
            "custom_prompts": self.custom_prompts,
            "quick_actions": self.quick_actions,
            "total_messages_sent": self.total_messages_sent,
            "favorite_features": self.favorite_features,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def create_default_preferences(cls, user_id: int) -> "UserChatPreferences":
        """Create default preferences for a new user."""
        default_quick_actions = [
            {"id": "show_pending_tasks", "label": "Show pending tasks", "icon": "assignment"},
            {"id": "search_emails", "label": "Search emails", "icon": "search"},
            {"id": "show_urgent", "label": "Show urgent emails", "icon": "priority_high"},
            {"id": "workflow_status", "label": "Workflow status", "icon": "timeline"}
        ]

        return cls(
            user_id=user_id,
            quick_actions=default_quick_actions,
            frequent_models=["llama2"],
            favorite_features=[]
        )
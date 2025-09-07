from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum
from datetime import datetime
import uuid

from app.db.database import Base

class NotificationStatus(enum.Enum):
    UNREAD = "unread"
    READ = "read"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # e.g., "task_due", "workflow_complete", "email_alert"
    message = Column(String, nullable=False)
    related_id = Column(String, nullable=True)  # e.g., task_id or workflow_id
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.UNREAD, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
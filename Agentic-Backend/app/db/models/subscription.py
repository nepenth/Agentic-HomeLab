from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class LogSubscription(Base):
    __tablename__ = "log_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    filters = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="log_subscriptions")
    
    def __repr__(self):
        return f"<LogSubscription(id={self.id}, session_id={self.session_id})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "filters": self.filters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen_timestamp": self.last_seen_timestamp.isoformat() if self.last_seen_timestamp else None,
        }
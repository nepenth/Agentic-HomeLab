"""
Webhook Subscription Database Model
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.database import Base


class WebhookSubscription(Base):
    """Database model for webhook subscriptions"""
    __tablename__ = "webhook_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False)  # List of event types
    secret = Column(String(64), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)
    headers = Column(JSON, default=dict)  # Custom headers
    filters = Column(JSON, default=dict)  # Event filters
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Associated user

    def to_dict(self):
        return {
            "id": str(self.id),
            "url": self.url,
            "events": self.events,
            "secret": self.secret,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "failure_count": self.failure_count,
            "headers": self.headers,
            "filters": self.filters,
            "user_id": str(self.user_id) if self.user_id else None
        }


class WebhookDeliveryLog(Base):
    """Database model for webhook delivery logs"""
    __tablename__ = "webhook_delivery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("webhook_subscriptions.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    delivered_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationship
    subscription = relationship("WebhookSubscription", backref="delivery_logs")

    def to_dict(self):
        return {
            "id": str(self.id),
            "subscription_id": str(self.subscription_id),
            "event_type": self.event_type,
            "payload": self.payload,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "success": self.success,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class AgentSecret(Base):
    __tablename__ = "agent_secrets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    secret_key = Column(String(255), nullable=False, index=True)  # e.g., "imap_password", "api_key"
    encrypted_value = Column(Text, nullable=False)  # Encrypted secret value
    description = Column(Text, nullable=True)  # Optional description of what this secret is for
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="secrets")

    def __repr__(self):
        return f"<AgentSecret(id={self.id}, agent_id={self.agent_id}, key='{self.secret_key}')>"

    def to_dict(self, include_encrypted_value=False):
        """Convert to dictionary, optionally including encrypted value."""
        result = {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "secret_key": self.secret_key,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_encrypted_value:
            result["encrypted_value"] = self.encrypted_value
        return result
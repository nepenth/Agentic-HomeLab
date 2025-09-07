from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class AgentTool(Base):
    __tablename__ = "agent_tools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(255), nullable=False, index=True)
    tool_config = Column(JSONB, nullable=True, default=dict)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="tools")
    
    def __repr__(self):
        return f"<AgentTool(id={self.id}, agent_id={self.agent_id}, tool='{self.tool_name}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "tool_name": self.tool_name,
            "tool_config": self.tool_config,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
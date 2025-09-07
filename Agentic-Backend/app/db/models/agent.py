from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    model_name = Column(String(255), nullable=False, default="llama2")
    config = Column(JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Dynamic agent support
    agent_type_id = Column(UUID(as_uuid=True), ForeignKey("agent_types.id"), nullable=True, index=True)
    dynamic_config = Column(JSONB, nullable=True, default=dict)
    documentation_url = Column(String(500), nullable=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="agent", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="agent", cascade="all, delete-orphan")
    tools = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")
    task_logs = relationship("TaskLog", back_populates="agent")
    agent_type = relationship("AgentType", back_populates="agent_instances")
    secrets = relationship("AgentSecret", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', model='{self.model_name}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "model_name": self.model_name,
            "config": self.config,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "agent_type_id": str(self.agent_type_id) if self.agent_type_id else None,
            "dynamic_config": self.dynamic_config,
            "documentation_url": self.documentation_url,
        }
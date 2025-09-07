"""
Database models for dynamic agent schema management.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class AgentType(Base):
    """Model for storing agent type definitions and schemas."""
    __tablename__ = "agent_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    type_name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    schema_definition = Column(JSONB, nullable=False)
    documentation = Column(JSONB, nullable=True, default=dict)
    schema_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of schema
    
    # Status and lifecycle
    status = Column(String(50), nullable=False, default="active", index=True)  # active, deprecated, disabled
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deprecated_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    dynamic_tables = relationship("DynamicTable", back_populates="agent_type", cascade="all, delete-orphan")
    agent_instances = relationship("Agent", back_populates="agent_type")
    
    # Unique constraint on type_name + version
    __table_args__ = (
        {'schema': None}  # Use default schema
    )
    
    def __repr__(self):
        return f"<AgentType(type_name='{self.type_name}', version='{self.version}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "type_name": self.type_name,
            "version": self.version,
            "schema_definition": self.schema_definition,
            "documentation": self.documentation,
            "schema_hash": self.schema_hash,
            "status": self.status,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deprecated_at": self.deprecated_at.isoformat() if self.deprecated_at else None,
            "created_by": self.created_by,
        }


class DynamicTable(Base):
    """Model for tracking dynamically created tables."""
    __tablename__ = "dynamic_tables"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_type_id = Column(UUID(as_uuid=True), ForeignKey("agent_types.id"), nullable=False, index=True)
    table_name = Column(String(63), nullable=False, index=True)  # PostgreSQL table name limit
    model_name = Column(String(100), nullable=False)  # Name in the schema definition
    schema_definition = Column(JSONB, nullable=False)
    
    # Table statistics
    row_count = Column(Integer, nullable=False, default=0)
    last_analyzed = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    agent_type = relationship("AgentType", back_populates="dynamic_tables")
    
    def __repr__(self):
        return f"<DynamicTable(table_name='{self.table_name}', model_name='{self.model_name}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_type_id": str(self.agent_type_id),
            "table_name": self.table_name,
            "model_name": self.model_name,
            "schema_definition": self.schema_definition,
            "row_count": self.row_count,
            "last_analyzed": self.last_analyzed.isoformat() if self.last_analyzed else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentBuilderSession(Base):
    """Model for AI-assisted agent builder sessions."""
    __tablename__ = "agent_builder_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    initial_description = Column(Text, nullable=False)
    conversation_history = Column(JSONB, nullable=False, default=list)
    requirements = Column(JSONB, nullable=False, default=dict)
    generated_schema = Column(JSONB, nullable=True)
    
    # Session status
    status = Column(String(50), nullable=False, default="active", index=True)  # active, completed, abandoned
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<AgentBuilderSession(id='{self.id}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "initial_description": self.initial_description,
            "conversation_history": self.conversation_history,
            "requirements": self.requirements,
            "generated_schema": self.generated_schema,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
        }


class RegisteredTool(Base):
    """Model for tracking registered tools in the system."""
    __tablename__ = "registered_tools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tool_name = Column(String(255), nullable=False, unique=True, index=True)
    tool_class = Column(String(500), nullable=False)  # Python class path
    schema_definition = Column(JSONB, nullable=False)
    documentation = Column(JSONB, nullable=False, default=dict)
    
    # Tool status
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<RegisteredTool(tool_name='{self.tool_name}', is_enabled={self.is_enabled})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tool_name": self.tool_name,
            "tool_class": self.tool_class,
            "schema_definition": self.schema_definition,
            "documentation": self.documentation,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class AgentDeletionLog(Base):
    """Model for auditing agent deletions."""
    __tablename__ = "agent_deletion_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    agent_type = Column(String(100), nullable=False, index=True)
    agent_type_id = Column(UUID(as_uuid=True), nullable=True)  # May be null if type was deleted
    deletion_type = Column(String(50), nullable=False, index=True)  # soft, hard, purge
    
    # Deletion details
    tables_affected = Column(JSONB, nullable=False, default=list)
    rows_deleted = Column(JSONB, nullable=False, default=dict)
    
    # Metadata
    deleted_by = Column(String(255), nullable=True)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<AgentDeletionLog(agent_type='{self.agent_type}', deletion_type='{self.deletion_type}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_type": self.agent_type,
            "agent_type_id": str(self.agent_type_id) if self.agent_type_id else None,
            "deletion_type": self.deletion_type,
            "tables_affected": self.tables_affected,
            "rows_deleted": self.rows_deleted,
            "deleted_by": self.deleted_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "notes": self.notes,
        }
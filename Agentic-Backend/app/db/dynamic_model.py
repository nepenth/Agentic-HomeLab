"""
Dynamic SQLAlchemy model generation from schema definitions.
"""
from typing import Dict, Any, Type, Optional, List, Union
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, Date,
    JSON, Index, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid
import re
from datetime import datetime, date

from app.schemas.agent_schema import (
    DataModelDefinition, FieldDefinition, FieldType, 
    IndexDefinition, RelationshipDefinition
)
from app.db.database import Base


class DynamicModelError(Exception):
    """Exception raised when dynamic model creation fails."""
    pass


class FieldTypeMapper:
    """Maps schema field types to SQLAlchemy column types."""
    
    TYPE_MAPPING = {
        FieldType.STRING: String,
        FieldType.INTEGER: Integer,
        FieldType.FLOAT: Float,
        FieldType.BOOLEAN: Boolean,
        FieldType.TEXT: Text,
        FieldType.JSON: JSON,
        FieldType.UUID: UUID,
        FieldType.DATETIME: DateTime,
        FieldType.DATE: Date,
        FieldType.ARRAY: ARRAY,
        FieldType.ENUM: String,  # Will be handled specially with constraints
    }
    
    @classmethod
    def get_column_type(cls, field_def: FieldDefinition) -> Any:
        """Convert field definition to SQLAlchemy column type."""
        field_type = field_def.type
        
        if field_type not in cls.TYPE_MAPPING:
            raise DynamicModelError(f"Unsupported field type: {field_type}")
        
        base_type = cls.TYPE_MAPPING[field_type]
        
        # Handle type-specific configurations
        if field_type == FieldType.STRING:
            max_length = field_def.max_length or 255
            return base_type(max_length)
        
        elif field_type == FieldType.UUID:
            return base_type(as_uuid=True)
        
        elif field_type == FieldType.DATETIME:
            return base_type(timezone=True)
        
        elif field_type == FieldType.ARRAY:
            if not field_def.items:
                raise DynamicModelError("Array field must specify items type")
            
            # Map items type to SQLAlchemy type
            try:
                items_type = FieldType(field_def.items)
            except ValueError:
                raise DynamicModelError(f"Unsupported array items type: {field_def.items}")
            
            if items_type == FieldType.STRING:
                return ARRAY(String(255))
            elif items_type == FieldType.INTEGER:
                return ARRAY(Integer)
            elif items_type == FieldType.FLOAT:
                return ARRAY(Float)
            else:
                raise DynamicModelError(f"Unsupported array items type: {items_type}")
        
        return base_type()
    
    @classmethod
    def get_column_constraints(cls, field_def: FieldDefinition) -> List[Any]:
        """Generate SQLAlchemy constraints from field definition."""
        constraints = []
        
        # Range constraints for numeric types
        if field_def.range and field_def.type in [FieldType.INTEGER, FieldType.FLOAT]:
            min_val, max_val = field_def.range
            constraint_name = f"check_{field_def.type.value}_range"
            constraints.append(
                CheckConstraint(f"value >= {min_val} AND value <= {max_val}", name=constraint_name)
            )
        
        # Length constraints for string types
        if field_def.min_length and field_def.type in [FieldType.STRING, FieldType.TEXT]:
            constraint_name = f"check_{field_def.type.value}_min_length"
            constraints.append(
                CheckConstraint(f"length(value) >= {field_def.min_length}", name=constraint_name)
            )
        
        # Enum constraints
        if field_def.type == FieldType.ENUM and field_def.values:
            values_str = "', '".join(field_def.values)
            constraint_name = f"check_enum_values"
            constraints.append(
                CheckConstraint(f"value IN ('{values_str}')", name=constraint_name)
            )
        
        return constraints


class DynamicModel:
    """Factory for creating SQLAlchemy models from schema definitions."""
    
    _model_cache: Dict[str, Type] = {}
    
    @classmethod
    def create_model(
        cls, 
        model_name: str, 
        model_def: DataModelDefinition,
        agent_type_id: Optional[str] = None
    ) -> Type:
        """
        Create a SQLAlchemy model class from a data model definition.
        
        Args:
            model_name: Name of the model class
            model_def: Data model definition from schema
            agent_type_id: Optional agent type ID for foreign key relationships
            
        Returns:
            SQLAlchemy model class
        """
        # Check cache first
        cache_key = f"{model_name}_{hash(str(model_def.model_dump()))}"
        if cache_key in cls._model_cache:
            return cls._model_cache[cache_key]
        
        # Validate model name
        if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', model_name):
            raise DynamicModelError(f"Invalid model name: {model_name}")
        
        # Create attributes dictionary for the new class
        attrs = {
            '__tablename__': model_def.table_name,
            '__table_args__': cls._build_table_args(model_def),
        }
        
        # Add standard columns
        attrs['id'] = Column(
            UUID(as_uuid=True), 
            primary_key=True, 
            default=uuid.uuid4, 
            index=True
        )
        
        # Add agent_id foreign key if agent_type_id is provided
        if agent_type_id:
            attrs['agent_id'] = Column(
                UUID(as_uuid=True),
                ForeignKey('agents.id'),
                nullable=False,
                index=True
            )
        
        # Add task_id foreign key for tracking
        attrs['task_id'] = Column(
            UUID(as_uuid=True),
            ForeignKey('tasks.id'),
            nullable=True,
            index=True
        )
        
        # Add timestamp columns
        attrs['created_at'] = Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
        attrs['updated_at'] = Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )
        
        # Add fields from schema definition
        for field_name, field_def in model_def.fields.items():
            attrs[field_name] = cls._create_column(field_name, field_def)
        
        # Add relationships if defined
        if model_def.relationships:
            for rel_name, rel_def in model_def.relationships.items():
                attrs[rel_name] = cls._create_relationship(rel_name, rel_def)
        
        # Add utility methods
        attrs['to_dict'] = cls._create_to_dict_method(model_def.fields)
        attrs['__repr__'] = cls._create_repr_method(model_name)
        
        # Create the model class
        model_class = type(model_name, (Base,), attrs)
        
        # Cache the model
        cls._model_cache[cache_key] = model_class
        
        return model_class
    
    @classmethod
    def _create_column(cls, field_name: str, field_def: FieldDefinition) -> Column:
        """Create a SQLAlchemy column from field definition."""
        # Get column type
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        # Build column arguments
        column_args = {
            'nullable': not field_def.required,
            'index': field_name in ['id', 'agent_id', 'task_id'],  # Index common lookup fields
        }
        
        # Add default value
        if field_def.default is not None:
            column_args['default'] = field_def.default
        
        # Add server default for timestamps
        if field_def.type == FieldType.DATETIME and field_def.default == 'now':
            column_args['server_default'] = func.now()
        
        # Create column
        column = Column(column_type, **column_args)
        
        # Add constraints
        constraints = FieldTypeMapper.get_column_constraints(field_def)
        for constraint in constraints:
            # Note: Constraints will be added at table level in __table_args__
            pass
        
        return column
    
    @classmethod
    def _create_relationship(cls, rel_name: str, rel_def: RelationshipDefinition) -> relationship:
        """Create a SQLAlchemy relationship from relationship definition."""
        rel_args = {}
        
        if rel_def.back_populates:
            rel_args['back_populates'] = rel_def.back_populates
        
        if rel_def.type == "one_to_many":
            rel_args['cascade'] = "all, delete-orphan"
        
        return relationship(rel_def.target_model, **rel_args)
    
    @classmethod
    def _build_table_args(cls, model_def: DataModelDefinition) -> tuple:
        """Build __table_args__ for the model."""
        args = []
        
        # Add indexes
        if model_def.indexes:
            for index_def in model_def.indexes:
                index = Index(
                    index_def.name,
                    *index_def.fields,
                    unique=index_def.unique,
                    postgresql_using=index_def.type
                )
                args.append(index)
        
        # Add field constraints
        for field_name, field_def in model_def.fields.items():
            constraints = FieldTypeMapper.get_column_constraints(field_def)
            for constraint in constraints:
                # Update constraint name to include field name
                if hasattr(constraint, 'name'):
                    constraint.name = f"{constraint.name}_{field_name}"
                args.append(constraint)
        
        return tuple(args) if args else tuple()
    
    @classmethod
    def _create_to_dict_method(cls, fields: Dict[str, FieldDefinition]):
        """Create a to_dict method for the model."""
        def to_dict(self):
            result = {
                'id': str(self.id),
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }
            
            # Add agent_id and task_id if they exist
            if hasattr(self, 'agent_id') and self.agent_id:
                result['agent_id'] = str(self.agent_id)
            if hasattr(self, 'task_id') and self.task_id:
                result['task_id'] = str(self.task_id)
            
            # Add schema-defined fields
            for field_name in fields.keys():
                value = getattr(self, field_name, None)
                if value is not None:
                    # Handle special types
                    if isinstance(value, (datetime, date)):
                        result[field_name] = value.isoformat()
                    elif isinstance(value, uuid.UUID):
                        result[field_name] = str(value)
                    else:
                        result[field_name] = value
                else:
                    result[field_name] = None
            
            return result
        
        return to_dict
    
    @classmethod
    def _create_repr_method(cls, model_name: str):
        """Create a __repr__ method for the model."""
        def __repr__(self):
            return f"<{model_name}(id='{self.id}')>"
        
        return __repr__
    
    @classmethod
    def get_model_from_cache(cls, cache_key: str) -> Optional[Type]:
        """Get a model from cache by key."""
        return cls._model_cache.get(cache_key)
    
    @classmethod
    def clear_cache(cls):
        """Clear the model cache."""
        cls._model_cache.clear()
    
    @classmethod
    def create_models_from_schema(
        cls, 
        agent_schema: Dict[str, Any], 
        agent_type_id: Optional[str] = None
    ) -> Dict[str, Type]:
        """
        Create all models defined in an agent schema.
        
        Args:
            agent_schema: Complete agent schema dictionary
            agent_type_id: Optional agent type ID
            
        Returns:
            Dictionary mapping model names to SQLAlchemy model classes
        """
        models = {}
        data_models = agent_schema.get('data_models', {})
        
        for model_name, model_def_dict in data_models.items():
            # Convert dict to DataModelDefinition
            model_def = DataModelDefinition(**model_def_dict)
            
            # Create model class
            model_class = cls.create_model(
                model_name=model_name,
                model_def=model_def,
                agent_type_id=agent_type_id
            )
            
            models[model_name] = model_class
        
        return models


class DynamicModelRegistry:
    """Registry for managing dynamic models."""
    
    def __init__(self):
        self._models: Dict[str, Type] = {}
        self._agent_models: Dict[str, Dict[str, Type]] = {}
    
    def register_model(self, agent_type: str, model_name: str, model_class: Type):
        """Register a dynamic model."""
        if agent_type not in self._agent_models:
            self._agent_models[agent_type] = {}
        
        self._agent_models[agent_type][model_name] = model_class
        
        # Also register globally with prefixed name
        global_name = f"{agent_type}_{model_name}"
        self._models[global_name] = model_class
    
    def get_model(self, agent_type: str, model_name: str) -> Optional[Type]:
        """Get a model by agent type and model name."""
        return self._agent_models.get(agent_type, {}).get(model_name)
    
    def get_agent_models(self, agent_type: str) -> Dict[str, Type]:
        """Get all models for an agent type."""
        return self._agent_models.get(agent_type, {})
    
    def unregister_agent_models(self, agent_type: str):
        """Unregister all models for an agent type."""
        if agent_type in self._agent_models:
            # Remove from global registry
            for model_name in self._agent_models[agent_type]:
                global_name = f"{agent_type}_{model_name}"
                self._models.pop(global_name, None)
            
            # Remove from agent registry
            del self._agent_models[agent_type]
    
    def list_agent_types(self) -> List[str]:
        """List all registered agent types."""
        return list(self._agent_models.keys())
    
    def list_models(self, agent_type: Optional[str] = None) -> Dict[str, Type]:
        """List all models, optionally filtered by agent type."""
        if agent_type:
            return self.get_agent_models(agent_type)
        return self._models.copy()


# Global registry instance
dynamic_model_registry = DynamicModelRegistry()
"""
Unit tests for dynamic model generation.
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import DeclarativeBase
import uuid
from datetime import datetime

from app.db.dynamic_model import (
    DynamicModel, FieldTypeMapper, DynamicModelRegistry, DynamicModelError
)
from app.schemas.agent_schema import (
    DataModelDefinition, FieldDefinition, FieldType, IndexDefinition, 
    RelationshipDefinition
)


class TestFieldTypeMapper:
    """Test field type mapping functionality."""
    
    def test_string_field_mapping(self):
        """Test string field type mapping."""
        field_def = FieldDefinition(type=FieldType.STRING, max_length=100)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert isinstance(column_type, type(String(100)))
        assert column_type.length == 100
    
    def test_string_field_default_length(self):
        """Test string field with default length."""
        field_def = FieldDefinition(type=FieldType.STRING)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert isinstance(column_type, type(String(255)))
        assert column_type.length == 255
    
    def test_integer_field_mapping(self):
        """Test integer field type mapping."""
        field_def = FieldDefinition(type=FieldType.INTEGER)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'Integer'
    
    def test_float_field_mapping(self):
        """Test float field type mapping."""
        field_def = FieldDefinition(type=FieldType.FLOAT)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'Float'
    
    def test_boolean_field_mapping(self):
        """Test boolean field type mapping."""
        field_def = FieldDefinition(type=FieldType.BOOLEAN)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'Boolean'
    
    def test_text_field_mapping(self):
        """Test text field type mapping."""
        field_def = FieldDefinition(type=FieldType.TEXT)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'Text'
    
    def test_json_field_mapping(self):
        """Test JSON field type mapping."""
        field_def = FieldDefinition(type=FieldType.JSON)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'JSON'
    
    def test_uuid_field_mapping(self):
        """Test UUID field type mapping."""
        field_def = FieldDefinition(type=FieldType.UUID)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'UUID'
        assert column_type.as_uuid is True
    
    def test_datetime_field_mapping(self):
        """Test datetime field type mapping."""
        field_def = FieldDefinition(type=FieldType.DATETIME)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'DateTime'
        assert column_type.timezone is True
    
    def test_date_field_mapping(self):
        """Test date field type mapping."""
        field_def = FieldDefinition(type=FieldType.DATE)
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'Date'
    
    def test_array_string_field_mapping(self):
        """Test array of strings field type mapping."""
        field_def = FieldDefinition(type=FieldType.ARRAY, items="string")
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'ARRAY'
        assert column_type.item_type.__class__.__name__ == 'String'
    
    def test_array_integer_field_mapping(self):
        """Test array of integers field type mapping."""
        field_def = FieldDefinition(type=FieldType.ARRAY, items="integer")
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert column_type.__class__.__name__ == 'ARRAY'
        assert column_type.item_type.__class__.__name__ == 'Integer'
    
    def test_array_without_items_raises_error(self):
        """Test that array field without items raises error."""
        field_def = FieldDefinition(type=FieldType.ARRAY)
        
        with pytest.raises(DynamicModelError, match="Array field must specify items type"):
            FieldTypeMapper.get_column_type(field_def)
    
    def test_unsupported_array_items_type_raises_error(self):
        """Test that unsupported array items type raises error."""
        field_def = FieldDefinition(type=FieldType.ARRAY, items="unsupported")
        
        with pytest.raises(DynamicModelError, match="Unsupported array items type"):
            FieldTypeMapper.get_column_type(field_def)
    
    def test_enum_field_mapping(self):
        """Test enum field type mapping."""
        field_def = FieldDefinition(type=FieldType.ENUM, values=["option1", "option2"])
        column_type = FieldTypeMapper.get_column_type(field_def)
        
        assert isinstance(column_type, type(String()))
    
    def test_unsupported_field_type_raises_error(self):
        """Test that unsupported field type raises error."""
        # Create a mock field definition with unsupported type
        field_def = Mock()
        field_def.type = "unsupported_type"
        
        with pytest.raises(DynamicModelError, match="Unsupported field type"):
            FieldTypeMapper.get_column_type(field_def)


class TestDynamicModel:
    """Test dynamic model creation functionality."""
    
    def test_create_simple_model(self):
        """Test creating a simple model with basic fields."""
        model_def = DataModelDefinition(
            table_name="test_table",
            fields={
                "name": FieldDefinition(type=FieldType.STRING, required=True),
                "age": FieldDefinition(type=FieldType.INTEGER, required=False),
                "active": FieldDefinition(type=FieldType.BOOLEAN, default=True)
            }
        )
        
        model_class = DynamicModel.create_model("TestModel", model_def)
        
        # Check class name and table name
        assert model_class.__name__ == "TestModel"
        assert model_class.__tablename__ == "test_table"
        
        # Check that standard columns exist
        assert hasattr(model_class, 'id')
        assert hasattr(model_class, 'created_at')
        assert hasattr(model_class, 'updated_at')
        assert hasattr(model_class, 'task_id')
        
        # Check schema-defined fields
        assert hasattr(model_class, 'name')
        assert hasattr(model_class, 'age')
        assert hasattr(model_class, 'active')
        
        # Check utility methods
        assert hasattr(model_class, 'to_dict')
        assert hasattr(model_class, '__repr__')
    
    def test_create_model_with_agent_id(self):
        """Test creating a model with agent_id foreign key."""
        model_def = DataModelDefinition(
            table_name="agent_data",
            fields={
                "value": FieldDefinition(type=FieldType.STRING, required=True)
            }
        )
        
        model_class = DynamicModel.create_model(
            "AgentDataModel", 
            model_def, 
            agent_type_id="test-agent-type"
        )
        
        # Check that agent_id column exists
        assert hasattr(model_class, 'agent_id')
    
    def test_create_model_with_indexes(self):
        """Test creating a model with custom indexes."""
        model_def = DataModelDefinition(
            table_name="indexed_table",
            fields={
                "email": FieldDefinition(type=FieldType.STRING, required=True),
                "status": FieldDefinition(type=FieldType.STRING, required=True)
            },
            indexes=[
                IndexDefinition(name="idx_email", fields=["email"], unique=True),
                IndexDefinition(name="idx_status", fields=["status"], unique=False)
            ]
        )
        
        model_class = DynamicModel.create_model("IndexedModel", model_def)
        
        # Check that table args include indexes
        assert hasattr(model_class, '__table_args__')
        assert len(model_class.__table_args__) > 0
    
    def test_create_model_with_relationships(self):
        """Test creating a model with relationships."""
        model_def = DataModelDefinition(
            table_name="parent_table",
            fields={
                "name": FieldDefinition(type=FieldType.STRING, required=True)
            },
            relationships={
                "children": RelationshipDefinition(
                    type="one_to_many",
                    target_model="ChildModel",
                    back_populates="parent"
                )
            }
        )
        
        model_class = DynamicModel.create_model("ParentModel", model_def)
        
        # Check that relationship exists
        assert hasattr(model_class, 'children')
    
    def test_invalid_model_name_raises_error(self):
        """Test that invalid model name raises error."""
        model_def = DataModelDefinition(
            table_name="test_table",
            fields={
                "name": FieldDefinition(type=FieldType.STRING, required=True)
            }
        )
        
        with pytest.raises(DynamicModelError, match="Invalid model name"):
            DynamicModel.create_model("123InvalidName", model_def)
    
    def test_model_caching(self):
        """Test that models are cached properly."""
        model_def = DataModelDefinition(
            table_name="cached_table",
            fields={
                "name": FieldDefinition(type=FieldType.STRING, required=True)
            }
        )
        
        # Create model twice
        model_class1 = DynamicModel.create_model("CachedModel", model_def)
        model_class2 = DynamicModel.create_model("CachedModel", model_def)
        
        # Should be the same class (cached)
        assert model_class1 is model_class2
    
    def test_create_models_from_schema(self):
        """Test creating multiple models from agent schema."""
        agent_schema = {
            "data_models": {
                "user_data": {
                    "table_name": "user_data_table",
                    "fields": {
                        "username": {"type": "string", "required": True},
                        "email": {"type": "string", "required": True}
                    }
                },
                "user_preferences": {
                    "table_name": "user_preferences_table",
                    "fields": {
                        "theme": {"type": "string", "default": "light"},
                        "notifications": {"type": "boolean", "default": True}
                    }
                }
            }
        }
        
        models = DynamicModel.create_models_from_schema(agent_schema)
        
        assert len(models) == 2
        assert "user_data" in models
        assert "user_preferences" in models
        
        # Check model properties
        user_data_model = models["user_data"]
        assert user_data_model.__tablename__ == "user_data_table"
        assert hasattr(user_data_model, 'username')
        assert hasattr(user_data_model, 'email')
        
        user_prefs_model = models["user_preferences"]
        assert user_prefs_model.__tablename__ == "user_preferences_table"
        assert hasattr(user_prefs_model, 'theme')
        assert hasattr(user_prefs_model, 'notifications')
    
    def test_to_dict_method(self):
        """Test the generated to_dict method."""
        model_def = DataModelDefinition(
            table_name="test_dict_table",
            fields={
                "name": FieldDefinition(type=FieldType.STRING, required=True),
                "count": FieldDefinition(type=FieldType.INTEGER, default=0)
            }
        )
        
        model_class = DynamicModel.create_model("DictTestModel", model_def)
        
        # Create an instance (mock the attributes)
        instance = Mock(spec=model_class)
        instance.id = uuid.uuid4()
        instance.name = "test"
        instance.count = 42
        instance.created_at = datetime.now()
        instance.updated_at = datetime.now()
        instance.agent_id = None
        instance.task_id = None
        
        # Call the to_dict method
        to_dict_method = model_class.to_dict
        result = to_dict_method(instance)
        
        # Check result structure
        assert 'id' in result
        assert 'name' in result
        assert 'count' in result
        assert 'created_at' in result
        assert 'updated_at' in result
        assert result['name'] == "test"
        assert result['count'] == 42
    
    def test_repr_method(self):
        """Test the generated __repr__ method."""
        model_def = DataModelDefinition(
            table_name="test_repr_table",
            fields={
                "name": FieldDefinition(type=FieldType.STRING, required=True)
            }
        )
        
        model_class = DynamicModel.create_model("ReprTestModel", model_def)
        
        # Create an instance (mock the attributes)
        instance = Mock(spec=model_class)
        instance.id = uuid.uuid4()
        
        # Call the __repr__ method
        repr_method = model_class.__repr__
        result = repr_method(instance)
        
        assert "ReprTestModel" in result
        assert str(instance.id) in result


class TestDynamicModelRegistry:
    """Test dynamic model registry functionality."""
    
    def setup_method(self):
        """Set up test registry."""
        self.registry = DynamicModelRegistry()
    
    def test_register_and_get_model(self):
        """Test registering and retrieving models."""
        mock_model = Mock()
        mock_model.__name__ = "TestModel"
        
        self.registry.register_model("test_agent", "test_model", mock_model)
        
        # Test retrieval
        retrieved = self.registry.get_model("test_agent", "test_model")
        assert retrieved is mock_model
    
    def test_get_nonexistent_model(self):
        """Test getting a model that doesn't exist."""
        result = self.registry.get_model("nonexistent", "model")
        assert result is None
    
    def test_get_agent_models(self):
        """Test getting all models for an agent type."""
        mock_model1 = Mock()
        mock_model1.__name__ = "Model1"
        mock_model2 = Mock()
        mock_model2.__name__ = "Model2"
        
        self.registry.register_model("test_agent", "model1", mock_model1)
        self.registry.register_model("test_agent", "model2", mock_model2)
        
        models = self.registry.get_agent_models("test_agent")
        
        assert len(models) == 2
        assert "model1" in models
        assert "model2" in models
        assert models["model1"] is mock_model1
        assert models["model2"] is mock_model2
    
    def test_unregister_agent_models(self):
        """Test unregistering all models for an agent type."""
        mock_model = Mock()
        mock_model.__name__ = "TestModel"
        
        self.registry.register_model("test_agent", "test_model", mock_model)
        
        # Verify it's registered
        assert self.registry.get_model("test_agent", "test_model") is mock_model
        
        # Unregister
        self.registry.unregister_agent_models("test_agent")
        
        # Verify it's gone
        assert self.registry.get_model("test_agent", "test_model") is None
        assert self.registry.get_agent_models("test_agent") == {}
    
    def test_list_agent_types(self):
        """Test listing all registered agent types."""
        mock_model1 = Mock()
        mock_model2 = Mock()
        
        self.registry.register_model("agent1", "model1", mock_model1)
        self.registry.register_model("agent2", "model2", mock_model2)
        
        agent_types = self.registry.list_agent_types()
        
        assert len(agent_types) == 2
        assert "agent1" in agent_types
        assert "agent2" in agent_types
    
    def test_list_all_models(self):
        """Test listing all models."""
        mock_model1 = Mock()
        mock_model2 = Mock()
        
        self.registry.register_model("agent1", "model1", mock_model1)
        self.registry.register_model("agent2", "model2", mock_model2)
        
        all_models = self.registry.list_models()
        
        assert len(all_models) == 2
        assert "agent1_model1" in all_models
        assert "agent2_model2" in all_models
    
    def test_list_models_by_agent_type(self):
        """Test listing models filtered by agent type."""
        mock_model1 = Mock()
        mock_model2 = Mock()
        mock_model3 = Mock()
        
        self.registry.register_model("agent1", "model1", mock_model1)
        self.registry.register_model("agent1", "model2", mock_model2)
        self.registry.register_model("agent2", "model3", mock_model3)
        
        agent1_models = self.registry.list_models("agent1")
        
        assert len(agent1_models) == 2
        assert "model1" in agent1_models
        assert "model2" in agent1_models
        assert "model3" not in agent1_models


class TestFieldConstraints:
    """Test field constraint generation."""
    
    def test_numeric_range_constraints(self):
        """Test numeric range constraint generation."""
        field_def = FieldDefinition(
            type=FieldType.INTEGER,
            range=[1, 100]
        )
        
        constraints = FieldTypeMapper.get_column_constraints(field_def)
        
        assert len(constraints) == 1
        # Note: In actual implementation, we'd check the constraint SQL
    
    def test_string_length_constraints(self):
        """Test string length constraint generation."""
        field_def = FieldDefinition(
            type=FieldType.STRING,
            min_length=5
        )
        
        constraints = FieldTypeMapper.get_column_constraints(field_def)
        
        assert len(constraints) == 1
    
    def test_enum_value_constraints(self):
        """Test enum value constraint generation."""
        field_def = FieldDefinition(
            type=FieldType.ENUM,
            values=["active", "inactive", "pending"]
        )
        
        constraints = FieldTypeMapper.get_column_constraints(field_def)
        
        assert len(constraints) == 1
    
    def test_no_constraints_for_basic_fields(self):
        """Test that basic fields without constraints return empty list."""
        field_def = FieldDefinition(type=FieldType.STRING)
        
        constraints = FieldTypeMapper.get_column_constraints(field_def)
        
        assert len(constraints) == 0


if __name__ == "__main__":
    pytest.main([__file__])
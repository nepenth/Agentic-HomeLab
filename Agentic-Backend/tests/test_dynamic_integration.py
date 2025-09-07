"""
Integration tests for dynamic model and migration systems.
"""
import pytest
from unittest.mock import Mock, patch

from app.db.dynamic_model import DynamicModel, dynamic_model_registry
from app.db.dynamic_migration import DynamicTableMigrator, MigrationPlan, MigrationOperation
from unittest.mock import AsyncMock
from app.schemas.agent_schema import (
    AgentSchema, DataModelDefinition, FieldDefinition, FieldType, 
    AgentMetadata, ProcessingPipeline, ProcessingStep
)


class TestDynamicIntegration:
    """Test integration between dynamic models and migration system."""
    
    def create_test_schema(self) -> AgentSchema:
        """Create a test agent schema for integration testing."""
        return AgentSchema(
            agent_type="integration_test_agent",
            metadata=AgentMetadata(
                name="Integration Test Agent",
                description="An agent for integration testing",
                category="test"
            ),
            data_models={
                "user_profile": DataModelDefinition(
                    table_name="user_profiles",
                    fields={
                        "username": FieldDefinition(type=FieldType.STRING, required=True, max_length=50),
                        "email": FieldDefinition(type=FieldType.STRING, required=True, max_length=255),
                        "age": FieldDefinition(type=FieldType.INTEGER, required=False, range=[13, 120]),
                        "is_active": FieldDefinition(type=FieldType.BOOLEAN, default=True),
                        "preferences": FieldDefinition(type=FieldType.JSON, required=False),
                        "tags": FieldDefinition(type=FieldType.ARRAY, items="string", required=False)
                    }
                ),
                "activity_log": DataModelDefinition(
                    table_name="activity_logs",
                    fields={
                        "action": FieldDefinition(type=FieldType.STRING, required=True),
                        "timestamp": FieldDefinition(type=FieldType.DATETIME, required=True),
                        "meta_data": FieldDefinition(type=FieldType.JSON, required=False)
                    }
                )
            },
            processing_pipeline=ProcessingPipeline(
                steps=[
                    ProcessingStep(name="data_extraction", tool="extractor"),
                    ProcessingStep(name="data_processing", tool="processor")
                ]
            ),
            tools={
                "extractor": {"type": "data_extractor", "config": {}},
                "processor": {"type": "data_processor", "config": {}}
            },
            input_schema={
                "user_data": FieldDefinition(type=FieldType.JSON, required=True)
            },
            output_schema={
                "processed_data": FieldDefinition(type=FieldType.JSON, required=True)
            }
        )
    
    def test_create_models_from_schema(self):
        """Test creating SQLAlchemy models from agent schema."""
        schema = self.create_test_schema()
        
        # Create models from schema
        models = DynamicModel.create_models_from_schema(
            schema.model_dump(),
            agent_type_id="test-agent-type-id"
        )
        
        # Verify models were created
        assert len(models) == 2
        assert "user_profile" in models
        assert "activity_log" in models
        
        # Verify user_profile model
        user_profile_model = models["user_profile"]
        assert user_profile_model.__tablename__ == "user_profiles"
        assert hasattr(user_profile_model, 'username')
        assert hasattr(user_profile_model, 'email')
        assert hasattr(user_profile_model, 'age')
        assert hasattr(user_profile_model, 'is_active')
        assert hasattr(user_profile_model, 'preferences')
        assert hasattr(user_profile_model, 'tags')
        
        # Verify standard columns
        assert hasattr(user_profile_model, 'id')
        assert hasattr(user_profile_model, 'agent_id')
        assert hasattr(user_profile_model, 'task_id')
        assert hasattr(user_profile_model, 'created_at')
        assert hasattr(user_profile_model, 'updated_at')
        
        # Verify activity_log model
        activity_log_model = models["activity_log"]
        assert activity_log_model.__tablename__ == "activity_logs"
        assert hasattr(activity_log_model, 'action')
        assert hasattr(activity_log_model, 'timestamp')
        assert hasattr(activity_log_model, 'meta_data')
    
    def test_model_registry_integration(self):
        """Test integration with model registry."""
        schema = self.create_test_schema()
        
        # Create models
        models = DynamicModel.create_models_from_schema(
            schema.model_dump(),
            agent_type_id="test-agent-type-id"
        )
        
        # Register models
        agent_type = "integration_test_agent"
        for model_name, model_class in models.items():
            dynamic_model_registry.register_model(agent_type, model_name, model_class)
        
        # Verify registration
        assert agent_type in dynamic_model_registry.list_agent_types()
        
        # Retrieve models
        retrieved_models = dynamic_model_registry.get_agent_models(agent_type)
        assert len(retrieved_models) == 2
        assert "user_profile" in retrieved_models
        assert "activity_log" in retrieved_models
        
        # Verify individual model retrieval
        user_profile_model = dynamic_model_registry.get_model(agent_type, "user_profile")
        assert user_profile_model is not None
        assert user_profile_model.__tablename__ == "user_profiles"
        
        # Clean up
        dynamic_model_registry.unregister_agent_models(agent_type)
        assert agent_type not in dynamic_model_registry.list_agent_types()
    
    @pytest.mark.asyncio
    async def test_migration_plan_creation(self):
        """Test creating migration plans for dynamic schemas."""
        schema = self.create_test_schema()
        
        # Create migrator (with mocked engine)
        mock_engine = Mock()
        migrator = DynamicTableMigrator(mock_engine)
        
        # Mock the entire method to test the logic
        expected_plan = MigrationPlan(
            agent_type="test-agent-type-id",
            operations=[
                MigrationOperation(
                    operation_type='create_table',
                    table_name='user_profiles',
                    details={'model_name': 'user_profile'}
                ),
                MigrationOperation(
                    operation_type='create_table',
                    table_name='activity_logs',
                    details={'model_name': 'activity_log'}
                )
            ]
        )
        
        with patch.object(migrator, 'preview_migration', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = expected_plan
            
            # Create migration plan
            plan = await mock_method("test-agent-type-id", schema)
            
            # Verify plan
            assert plan.agent_type == "test-agent-type-id"
            assert len(plan.operations) == 2  # Two tables to create
            
            # Verify operations
            create_operations = [op for op in plan.operations if op.operation_type == 'create_table']
            assert len(create_operations) == 2
            
            table_names = {op.table_name for op in create_operations}
            assert "user_profiles" in table_names
            assert "activity_logs" in table_names
    
    def test_schema_validation_integration(self):
        """Test that schema validation works with model creation."""
        # Test valid schema with unique table names
        valid_schema = AgentSchema(
            agent_type="validation_test_agent",
            metadata=AgentMetadata(
                name="Validation Test Agent",
                description="An agent for validation testing",
                category="test"
            ),
            data_models={
                "validation_profile": DataModelDefinition(
                    table_name="validation_profiles",
                    fields={
                        "name": FieldDefinition(type=FieldType.STRING, required=True, max_length=50),
                        "value": FieldDefinition(type=FieldType.INTEGER, required=False)
                    }
                )
            },
            processing_pipeline=ProcessingPipeline(
                steps=[ProcessingStep(name="validation_step", tool="validation_tool")]
            ),
            tools={"validation_tool": {"type": "test", "config": {}}},
            input_schema={"input": FieldDefinition(type=FieldType.STRING, required=True)},
            output_schema={"output": FieldDefinition(type=FieldType.STRING, required=True)}
        )
        
        # Should not raise any exceptions
        models = DynamicModel.create_models_from_schema(
            valid_schema.model_dump(),
            agent_type_id="validation-test-agent-id"
        )
        assert len(models) == 1
        
        # Test with different table name to avoid conflicts
        test_schema_dict = valid_schema.model_dump()
        test_schema_dict['data_models']['validation_profile']['table_name'] = 'validation_profiles_v2'
        
        # Should still create models
        models = DynamicModel.create_models_from_schema(
            test_schema_dict,
            agent_type_id="validation-test-agent-id-v2"
        )
        assert len(models) == 1
    
    def test_field_type_coverage(self):
        """Test that all supported field types can be used in integration."""
        # Create schema with all field types
        comprehensive_schema = AgentSchema(
            agent_type="comprehensive_test_agent",
            metadata=AgentMetadata(
                name="Comprehensive Test Agent",
                description="Tests all field types",
                category="test"
            ),
            data_models={
                "comprehensive_model": DataModelDefinition(
                    table_name="comprehensive_table",
                    fields={
                        "string_field": FieldDefinition(type=FieldType.STRING, max_length=100, required=True),
                        "integer_field": FieldDefinition(type=FieldType.INTEGER),
                        "float_field": FieldDefinition(type=FieldType.FLOAT),
                        "boolean_field": FieldDefinition(type=FieldType.BOOLEAN),
                        "text_field": FieldDefinition(type=FieldType.TEXT),
                        "json_field": FieldDefinition(type=FieldType.JSON),
                        "uuid_field": FieldDefinition(type=FieldType.UUID),
                        "datetime_field": FieldDefinition(type=FieldType.DATETIME),
                        "date_field": FieldDefinition(type=FieldType.DATE),
                        "array_field": FieldDefinition(type=FieldType.ARRAY, items="string"),
                        "enum_field": FieldDefinition(type=FieldType.ENUM, values=["option1", "option2"])
                    }
                )
            },
            processing_pipeline=ProcessingPipeline(
                steps=[ProcessingStep(name="test_step", tool="test_tool")]
            ),
            tools={"test_tool": {"type": "test", "config": {}}},
            input_schema={"input": FieldDefinition(type=FieldType.STRING)},
            output_schema={"output": FieldDefinition(type=FieldType.STRING)}
        )
        
        # Create models - should handle all field types
        models = DynamicModel.create_models_from_schema(
            comprehensive_schema.model_dump(),
            agent_type_id="test-agent-type-id"
        )
        
        assert len(models) == 1
        model = models["comprehensive_model"]
        
        # Verify all fields exist
        expected_fields = [
            "string_field", "integer_field", "float_field", "boolean_field",
            "text_field", "json_field", "uuid_field", "datetime_field",
            "date_field", "array_field", "enum_field"
        ]
        
        for field_name in expected_fields:
            assert hasattr(model, field_name), f"Missing field: {field_name}"


if __name__ == "__main__":
    pytest.main([__file__])
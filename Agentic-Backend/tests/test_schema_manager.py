"""
Tests for the SchemaManager and schema validation functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.services.schema_manager import SchemaManager, SchemaValidationError, IncompatibleSchemaError
from app.schemas.agent_schema import AgentSchema, SchemaValidationResult, SchemaCompatibilityResult
from app.db.models.agent_type import AgentType, DynamicTable


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def schema_manager(mock_db_session):
    """Create SchemaManager instance with mocked database."""
    return SchemaManager(mock_db_session)


@pytest.fixture
def valid_agent_schema():
    """Valid agent schema for testing."""
    return {
        "agent_type": "test_email_analyzer",
        "metadata": {
            "name": "Test Email Analyzer",
            "description": "Analyzes emails for testing",
            "category": "productivity",
            "version": "1.0.0"
        },
        "data_models": {
            "email_analysis": {
                "table_name": "test_email_analysis",
                "fields": {
                    "email_id": {
                        "type": "string",
                        "required": True,
                        "max_length": 255
                    },
                    "importance_score": {
                        "type": "float",
                        "required": False,
                        "range": [0.0, 1.0],
                        "default": 0.5
                    },
                    "categories": {
                        "type": "array",
                        "items": "string",
                        "required": False
                    }
                },
                "indexes": [
                    {
                        "name": "idx_email_id",
                        "fields": ["email_id"],
                        "unique": True
                    }
                ]
            }
        },
        "processing_pipeline": {
            "steps": [
                {
                    "name": "extract_content",
                    "tool": "email_extractor",
                    "config": {"format": "text"}
                },
                {
                    "name": "analyze_importance",
                    "tool": "importance_analyzer",
                    "depends_on": ["extract_content"]
                }
            ]
        },
        "tools": {
            "email_extractor": {
                "type": "email_connector",
                "config": {"service": "imap"},
                "auth_config": {
                    "type": "basic_auth",
                    "config": {}
                }
            },
            "importance_analyzer": {
                "type": "ml_classifier",
                "config": {"model": "importance_v1"}
            }
        },
        "input_schema": {
            "email_source": {
                "type": "string",
                "required": True
            },
            "date_range": {
                "type": "string",
                "required": False,
                "default": "30d"
            }
        },
        "output_schema": {
            "processed_count": {
                "type": "integer",
                "required": True
            },
            "results": {
                "type": "array",
                "items": "email_analysis"
            }
        }
    }


class TestSchemaValidation:
    """Test schema validation functionality."""
    
    async def test_validate_valid_schema(self, schema_manager, valid_agent_schema):
        """Test validation of a valid schema."""
        result = await schema_manager.validate_schema(valid_agent_schema)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.schema_hash is not None
        assert len(result.schema_hash) == 64  # SHA-256 hash length
    
    async def test_validate_missing_required_fields(self, schema_manager):
        """Test validation fails for missing required fields."""
        invalid_schema = {
            "agent_type": "test_agent",
            "metadata": {
                "name": "Test Agent",
                "description": "Test description"
                # Missing category and version
            }
            # Missing other required fields
        }
        
        result = await schema_manager.validate_schema(invalid_schema)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("Missing required" in error for error in result.errors)
    
    async def test_validate_invalid_field_types(self, schema_manager, valid_agent_schema):
        """Test validation fails for invalid field types."""
        # Add invalid field type
        valid_agent_schema["data_models"]["email_analysis"]["fields"]["invalid_field"] = {
            "type": "invalid_type",
            "required": True
        }
        
        result = await schema_manager.validate_schema(valid_agent_schema)
        
        assert not result.is_valid
        assert any("Unsupported field type" in error for error in result.errors)
    
    async def test_validate_reserved_field_names(self, schema_manager, valid_agent_schema):
        """Test validation fails for reserved field names."""
        # Add reserved field name
        valid_agent_schema["data_models"]["email_analysis"]["fields"]["id"] = {
            "type": "string",
            "required": True
        }
        
        result = await schema_manager.validate_schema(valid_agent_schema)
        
        assert not result.is_valid
        assert any("Reserved field name" in error for error in result.errors)
    
    async def test_validate_circular_dependencies(self, schema_manager, valid_agent_schema):
        """Test validation fails for circular dependencies in pipeline."""
        # Create circular dependency
        valid_agent_schema["processing_pipeline"]["steps"] = [
            {
                "name": "step1",
                "tool": "tool1",
                "depends_on": ["step2"]
            },
            {
                "name": "step2", 
                "tool": "tool2",
                "depends_on": ["step1"]
            }
        ]
        
        result = await schema_manager.validate_schema(valid_agent_schema)
        
        assert not result.is_valid
        assert any("Circular dependency" in error for error in result.errors)
    
    async def test_validate_tool_references(self, schema_manager, valid_agent_schema):
        """Test validation fails for undefined tool references."""
        # Reference undefined tool
        valid_agent_schema["processing_pipeline"]["steps"][0]["tool"] = "undefined_tool"
        
        result = await schema_manager.validate_schema(valid_agent_schema)
        
        assert not result.is_valid
        assert any("undefined tools" in error for error in result.errors)
    
    async def test_validate_security_constraints(self, schema_manager, valid_agent_schema):
        """Test security constraint validation."""
        # Remove auth config from external tool
        del valid_agent_schema["tools"]["email_extractor"]["auth_config"]
        
        result = await schema_manager.validate_schema(valid_agent_schema)
        
        assert not result.is_valid
        assert any("must have auth_config" in error for error in result.errors)


class TestSchemaRegistration:
    """Test agent type registration functionality."""
    
    async def test_register_valid_agent_type(self, schema_manager, valid_agent_schema, mock_db_session):
        """Test successful registration of valid agent type."""
        # Mock database responses
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None  # No existing agent
        
        agent_type = await schema_manager.register_agent_type(valid_agent_schema, "test_user")
        
        assert isinstance(agent_type, AgentType)
        assert agent_type.type_name == "test_email_analyzer"
        assert agent_type.version == "1.0.0"
        assert agent_type.created_by == "test_user"
        
        # Verify database operations
        mock_db_session.add.assert_called()
        mock_db_session.flush.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    async def test_register_invalid_schema_fails(self, schema_manager, mock_db_session):
        """Test registration fails for invalid schema."""
        invalid_schema = {"agent_type": "test"}  # Missing required fields
        
        with pytest.raises(SchemaValidationError):
            await schema_manager.register_agent_type(invalid_schema)
        
        # Verify no database operations
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()
    
    async def test_register_duplicate_agent_type_fails(self, schema_manager, valid_agent_schema, mock_db_session):
        """Test registration fails for duplicate agent type."""
        # Mock existing agent type
        existing_agent = AgentType(
            type_name="test_email_analyzer",
            version="1.0.0",
            status="active"
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_agent
        
        with pytest.raises(IntegrityError):
            await schema_manager.register_agent_type(valid_agent_schema)


class TestSchemaCompatibility:
    """Test schema compatibility checking."""
    
    async def test_compatible_schema_changes(self, schema_manager, valid_agent_schema):
        """Test compatible schema changes."""
        old_schema = valid_agent_schema.copy()
        new_schema = valid_agent_schema.copy()
        
        # Add optional field (compatible change)
        new_schema["data_models"]["email_analysis"]["fields"]["new_optional_field"] = {
            "type": "string",
            "required": False,
            "default": "default_value"
        }
        
        result = await schema_manager.check_compatibility(old_schema, new_schema)
        
        assert result.is_compatible
        assert len(result.breaking_changes) == 0
    
    async def test_incompatible_field_removal(self, schema_manager, valid_agent_schema):
        """Test incompatible field removal."""
        old_schema = valid_agent_schema.copy()
        new_schema = valid_agent_schema.copy()
        
        # Remove required field (breaking change)
        del new_schema["data_models"]["email_analysis"]["fields"]["email_id"]
        
        result = await schema_manager.check_compatibility(old_schema, new_schema)
        
        assert not result.is_compatible
        assert len(result.breaking_changes) > 0
        assert any("was removed" in change for change in result.breaking_changes)
        assert result.migration_required
    
    async def test_incompatible_type_change(self, schema_manager, valid_agent_schema):
        """Test incompatible field type change."""
        old_schema = valid_agent_schema.copy()
        new_schema = valid_agent_schema.copy()
        
        # Change field type (breaking change)
        new_schema["data_models"]["email_analysis"]["fields"]["importance_score"]["type"] = "string"
        
        result = await schema_manager.check_compatibility(old_schema, new_schema)
        
        assert not result.is_compatible
        assert len(result.breaking_changes) > 0
        assert any("type changed" in change for change in result.breaking_changes)
        assert result.migration_required
    
    async def test_incompatible_new_required_field(self, schema_manager, valid_agent_schema):
        """Test incompatible addition of required field without default."""
        old_schema = valid_agent_schema.copy()
        new_schema = valid_agent_schema.copy()
        
        # Add required field without default (breaking change)
        new_schema["data_models"]["email_analysis"]["fields"]["new_required_field"] = {
            "type": "string",
            "required": True
        }
        
        result = await schema_manager.check_compatibility(old_schema, new_schema)
        
        assert not result.is_compatible
        assert len(result.breaking_changes) > 0
        assert any("required field" in change and "without default" in change for change in result.breaking_changes)
        assert result.migration_required


class TestSchemaRetrieval:
    """Test schema retrieval functionality."""
    
    async def test_get_agent_type_by_name_and_version(self, schema_manager, mock_db_session):
        """Test retrieving agent type by name and version."""
        # Mock database response
        expected_agent = AgentType(
            type_name="test_agent",
            version="1.0.0",
            status="active"
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = expected_agent
        
        result = await schema_manager.get_agent_type("test_agent", "1.0.0")
        
        assert result == expected_agent
        mock_db_session.execute.assert_called_once()
    
    async def test_get_latest_agent_type_version(self, schema_manager, mock_db_session):
        """Test retrieving latest version when no version specified."""
        # Mock database response
        expected_agent = AgentType(
            type_name="test_agent",
            version="2.0.0",
            status="active"
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = expected_agent
        
        result = await schema_manager.get_agent_type("test_agent")
        
        assert result == expected_agent
        mock_db_session.execute.assert_called_once()
    
    async def test_list_agent_types(self, schema_manager, mock_db_session):
        """Test listing all agent types."""
        # Mock database response
        agent_types = [
            AgentType(type_name="agent1", version="1.0.0", status="active"),
            AgentType(type_name="agent2", version="1.0.0", status="active"),
        ]
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = agent_types
        
        result = await schema_manager.list_agent_types()
        
        assert len(result) == 2
        assert all(isinstance(agent, AgentType) for agent in result)
        mock_db_session.execute.assert_called_once()
    
    async def test_deprecate_agent_type(self, schema_manager, mock_db_session):
        """Test deprecating an agent type."""
        # Mock database response
        agent_type = AgentType(
            type_name="test_agent",
            version="1.0.0",
            status="active"
        )
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [agent_type]
        
        result = await schema_manager.deprecate_agent_type("test_agent", "1.0.0")
        
        assert result is True
        assert agent_type.status == "deprecated"
        assert agent_type.deprecated_at is not None
        mock_db_session.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
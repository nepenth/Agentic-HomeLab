"""
Tests for the AgentRegistry class.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import (
    AgentRegistry, AgentRegistrationError, AgentTypeInfo, AgentCapabilities
)
from app.services.schema_manager import SchemaManager, SchemaValidationError
from app.schemas.agent_schema import (
    AgentSchema, AgentMetadata, DataModelDefinition, FieldDefinition, FieldType,
    ProcessingPipeline, ProcessingStep, ToolDefinition
)
from app.db.models.agent_type import AgentType


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_schema_manager():
    """Mock schema manager."""
    return AsyncMock(spec=SchemaManager)


@pytest.fixture
def sample_agent_schema():
    """Sample agent schema for testing."""
    return AgentSchema(
        agent_type="test_agent",
        metadata=AgentMetadata(
            name="Test Agent",
            description="A test agent for unit testing",
            category="testing",
            version="1.0.0",
            tags=["test", "example"]
        ),
        data_models={
            "test_result": DataModelDefinition(
                table_name="test_results",
                fields={
                    "message": FieldDefinition(type=FieldType.STRING, required=True),
                    "score": FieldDefinition(type=FieldType.FLOAT, default=0.0)
                }
            )
        },
        processing_pipeline=ProcessingPipeline(
            steps=[
                ProcessingStep(name="process", tool="llm_processor")
            ]
        ),
        tools={
            "llm_processor": ToolDefinition(
                type="llm_processor",
                config={"model_name": "llama2"}
            )
        },
        input_schema={
            "text": FieldDefinition(type=FieldType.STRING, required=True),
            "temperature": FieldDefinition(type=FieldType.FLOAT, default=0.7)
        },
        output_schema={
            "result": FieldDefinition(type=FieldType.STRING, required=True)
        }
    )


@pytest.fixture
def agent_registry(mock_db_session, mock_schema_manager):
    """Create AgentRegistry instance for testing."""
    return AgentRegistry(
        db_session=mock_db_session,
        schema_manager=mock_schema_manager
    )


@pytest.fixture
def mock_agent_type(sample_agent_schema):
    """Mock AgentType database record."""
    agent_type = MagicMock()
    agent_type.id = "test-id"
    agent_type.type_name = "test_agent"
    agent_type.version = "1.0.0"
    agent_type.status = "active"
    agent_type.created_at = datetime.utcnow()
    agent_type.deprecated_at = None
    agent_type.schema_definition = sample_agent_schema.dict()
    return agent_type


class TestAgentRegistry:
    """Test cases for AgentRegistry."""
    
    @pytest.mark.asyncio
    async def test_register_agent_type_success(
        self, agent_registry, mock_schema_manager, sample_agent_schema, mock_agent_type
    ):
        """Test successful agent type registration."""
        # Setup mock
        mock_schema_manager.register_agent_type.return_value = mock_agent_type
        
        # Register agent type
        schema_dict = sample_agent_schema.dict()
        result = await agent_registry.register_agent_type(schema_dict, "test_user")
        
        # Verify result
        assert result == mock_agent_type
        mock_schema_manager.register_agent_type.assert_called_once_with(schema_dict, "test_user")
    
    @pytest.mark.asyncio
    async def test_register_agent_type_validation_error(
        self, agent_registry, mock_schema_manager, sample_agent_schema
    ):
        """Test agent type registration with validation error."""
        # Setup mock to raise validation error
        mock_schema_manager.register_agent_type.side_effect = SchemaValidationError(
            ["Invalid field type"], "test_schema"
        )
        
        # Attempt registration
        schema_dict = sample_agent_schema.dict()
        with pytest.raises(AgentRegistrationError, match="Schema validation failed"):
            await agent_registry.register_agent_type(schema_dict)
    
    @pytest.mark.asyncio
    async def test_list_agent_types_basic(
        self, agent_registry, mock_db_session, mock_agent_type, sample_agent_schema
    ):
        """Test basic agent type listing."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_type]
        mock_db_session.execute.return_value = mock_result
        
        # List agent types
        agent_types = await agent_registry.list_agent_types()
        
        # Verify result
        assert len(agent_types) == 1
        assert isinstance(agent_types[0], AgentTypeInfo)
        assert agent_types[0].agent_type == "test_agent"
        assert agent_types[0].name == "Test Agent"
        assert agent_types[0].category == "testing"
        assert agent_types[0].version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_list_agent_types_with_filters(
        self, agent_registry, mock_db_session, mock_agent_type
    ):
        """Test agent type listing with filters."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_type]
        mock_db_session.execute.return_value = mock_result
        
        # List with filters
        agent_types = await agent_registry.list_agent_types(
            category="testing",
            status="active",
            search_term="test",
            limit=10,
            offset=0
        )
        
        # Verify result
        assert len(agent_types) == 1
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_agent_type_info_success(
        self, agent_registry, mock_schema_manager, mock_agent_type, sample_agent_schema
    ):
        """Test successful agent type info retrieval."""
        # Setup mock
        mock_schema_manager.get_agent_type.return_value = mock_agent_type
        
        # Get agent type info
        info = await agent_registry.get_agent_type_info("test_agent")
        
        # Verify result
        assert isinstance(info, AgentTypeInfo)
        assert info.agent_type == "test_agent"
        assert info.name == "Test Agent"
        assert info.description == "A test agent for unit testing"
        assert info.category == "testing"
        assert info.version == "1.0.0"
        assert info.status == "active"
        assert info.capabilities is not None
    
    @pytest.mark.asyncio
    async def test_get_agent_type_info_not_found(
        self, agent_registry, mock_schema_manager
    ):
        """Test agent type info retrieval when not found."""
        # Setup mock to return None
        mock_schema_manager.get_agent_type.return_value = None
        
        # Get agent type info
        info = await agent_registry.get_agent_type_info("nonexistent")
        
        # Verify result
        assert info is None
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities_success(
        self, agent_registry, mock_schema_manager, mock_agent_type, sample_agent_schema
    ):
        """Test successful agent capabilities retrieval."""
        # Setup mock
        mock_schema_manager.get_agent_type.return_value = mock_agent_type
        
        # Get capabilities
        capabilities = await agent_registry.get_agent_capabilities("test_agent")
        
        # Verify result
        assert isinstance(capabilities, AgentCapabilities)
        assert capabilities.agent_type == "test_agent"
        assert capabilities.version == "1.0.0"
        assert "text" in capabilities.input_schema
        assert "result" in capabilities.output_schema
        assert "test_result" in capabilities.data_models
        assert "llm_processor" in capabilities.tools
        assert capabilities.processing_steps == 1
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities_not_found(
        self, agent_registry, mock_schema_manager
    ):
        """Test agent capabilities retrieval when not found."""
        # Setup mock to return None
        mock_schema_manager.get_agent_type.return_value = None
        
        # Get capabilities
        capabilities = await agent_registry.get_agent_capabilities("nonexistent")
        
        # Verify result
        assert capabilities is None
    
    @pytest.mark.asyncio
    async def test_deprecate_agent_type_success(
        self, agent_registry, mock_schema_manager
    ):
        """Test successful agent type deprecation."""
        # Setup mock
        mock_schema_manager.deprecate_agent_type.return_value = True
        
        # Deprecate agent type
        result = await agent_registry.deprecate_agent_type("test_agent", reason="Outdated")
        
        # Verify result
        assert result is True
        mock_schema_manager.deprecate_agent_type.assert_called_once_with("test_agent", None)
    
    @pytest.mark.asyncio
    async def test_deprecate_agent_type_not_found(
        self, agent_registry, mock_schema_manager
    ):
        """Test agent type deprecation when not found."""
        # Setup mock
        mock_schema_manager.deprecate_agent_type.return_value = False
        
        # Deprecate agent type
        result = await agent_registry.deprecate_agent_type("nonexistent")
        
        # Verify result
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_agent_type_success(
        self, agent_registry, mock_db_session, mock_agent_type
    ):
        """Test successful agent type deletion."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_type]
        
        # Mock usage count query
        mock_usage_result = MagicMock()
        mock_usage_result.scalar.return_value = 0
        
        mock_db_session.execute.side_effect = [mock_result, mock_usage_result]
        
        # Delete agent type
        result = await agent_registry.delete_agent_type("test_agent")
        
        # Verify result
        assert result is True
        assert mock_agent_type.status == "deleted"
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_agent_type_in_use(
        self, agent_registry, mock_db_session, mock_agent_type
    ):
        """Test agent type deletion when in use."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_type]
        
        # Mock usage count query to return > 0
        mock_usage_result = MagicMock()
        mock_usage_result.scalar.return_value = 5
        
        mock_db_session.execute.side_effect = [mock_result, mock_usage_result]
        
        # Attempt deletion
        with pytest.raises(AgentRegistrationError, match="Cannot delete agent type"):
            await agent_registry.delete_agent_type("test_agent")
    
    @pytest.mark.asyncio
    async def test_delete_agent_type_force(
        self, agent_registry, mock_db_session, mock_agent_type
    ):
        """Test forced agent type deletion."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_type]
        mock_db_session.execute.return_value = mock_result
        
        # Force delete agent type
        result = await agent_registry.delete_agent_type("test_agent", force=True)
        
        # Verify result
        assert result is True
        mock_db_session.delete.assert_called_once_with(mock_agent_type)
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_agent_types(
        self, agent_registry, mock_db_session, mock_agent_type
    ):
        """Test agent type search functionality."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_type]
        mock_db_session.execute.return_value = mock_result
        
        # Search agent types
        results = await agent_registry.search_agent_types("test", categories=["testing"])
        
        # Verify result
        assert len(results) == 1
        assert isinstance(results[0], AgentTypeInfo)
        assert results[0].agent_type == "test_agent"
    
    @pytest.mark.asyncio
    async def test_get_agent_versions(
        self, agent_registry, mock_schema_manager
    ):
        """Test getting agent versions."""
        # Setup mock
        mock_versions = [
            MagicMock(version="1.0.0", created_at="2024-01-01T00:00:00Z", is_active=True),
            MagicMock(version="1.1.0", created_at="2024-01-02T00:00:00Z", is_active=False)
        ]
        mock_schema_manager.get_schema_versions.return_value = mock_versions
        
        # Get versions
        versions = await agent_registry.get_agent_versions("test_agent")
        
        # Verify result
        assert len(versions) == 2
        mock_schema_manager.get_schema_versions.assert_called_once_with("test_agent")
    
    @pytest.mark.asyncio
    async def test_get_categories(
        self, agent_registry, mock_db_session
    ):
        """Test getting available categories."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("testing", 5),
            ("productivity", 3),
            ("analysis", 2)
        ]
        mock_db_session.execute.return_value = mock_result
        
        # Get categories
        categories = await agent_registry.get_categories()
        
        # Verify result
        assert len(categories) == 3
        assert categories[0]["category"] == "testing"
        assert categories[0]["count"] == 5
        assert "description" in categories[0]
    
    @pytest.mark.asyncio
    async def test_get_statistics(
        self, agent_registry, mock_db_session
    ):
        """Test getting registry statistics."""
        # Setup mocks for different queries
        mock_results = [
            MagicMock(scalar=lambda: 10),  # total
            MagicMock(scalar=lambda: 8),   # active
            MagicMock(scalar=lambda: 2),   # deprecated
            MagicMock(scalar=lambda: 3),   # recent
            MagicMock(all=lambda: [("testing", 5), ("productivity", 3)])  # categories
        ]
        mock_db_session.execute.side_effect = mock_results
        
        # Get statistics
        stats = await agent_registry.get_statistics()
        
        # Verify result
        assert stats["total_agent_types"] == 10
        assert stats["active_agent_types"] == 8
        assert stats["deprecated_agent_types"] == 2
        assert stats["recent_registrations"] == 3
        assert stats["categories"] == 2
        assert len(stats["category_breakdown"]) == 2


class TestAgentTypeInfo:
    """Test cases for AgentTypeInfo class."""
    
    def test_agent_type_info_creation(self):
        """Test AgentTypeInfo creation and conversion."""
        created_at = datetime.utcnow()
        deprecated_at = datetime.utcnow() + timedelta(days=30)
        
        info = AgentTypeInfo(
            agent_type="test_agent",
            name="Test Agent",
            description="A test agent",
            category="testing",
            version="1.0.0",
            status="active",
            created_at=created_at,
            deprecated_at=deprecated_at,
            capabilities={"tools": 2, "steps": 3}
        )
        
        # Test properties
        assert info.agent_type == "test_agent"
        assert info.name == "Test Agent"
        assert info.status == "active"
        
        # Test dictionary conversion
        info_dict = info.to_dict()
        assert info_dict["agent_type"] == "test_agent"
        assert info_dict["name"] == "Test Agent"
        assert info_dict["created_at"] == created_at.isoformat()
        assert info_dict["deprecated_at"] == deprecated_at.isoformat()
        assert info_dict["capabilities"]["tools"] == 2


class TestAgentCapabilities:
    """Test cases for AgentCapabilities class."""
    
    def test_agent_capabilities_creation(self):
        """Test AgentCapabilities creation and conversion."""
        capabilities = AgentCapabilities(
            agent_type="test_agent",
            version="1.0.0",
            input_schema={"text": {"type": "string", "required": True}},
            output_schema={"result": {"type": "string"}},
            data_models={"test_result": {"table_name": "test_results"}},
            tools={"llm_processor": {"type": "llm_processor"}},
            processing_steps=3,
            resource_limits={"max_execution_time": 3600},
            metadata={"name": "Test Agent", "category": "testing"}
        )
        
        # Test properties
        assert capabilities.agent_type == "test_agent"
        assert capabilities.version == "1.0.0"
        assert capabilities.processing_steps == 3
        
        # Test dictionary conversion
        caps_dict = capabilities.to_dict()
        assert caps_dict["agent_type"] == "test_agent"
        assert caps_dict["version"] == "1.0.0"
        assert "input_schema" in caps_dict
        assert "output_schema" in caps_dict
        assert "data_models" in caps_dict
        assert "tools" in caps_dict
        assert caps_dict["processing_steps"] == 3


class TestAgentRegistryIntegration:
    """Integration tests for AgentRegistry."""
    
    @pytest.mark.asyncio
    async def test_full_agent_lifecycle(
        self, agent_registry, mock_schema_manager, mock_db_session, 
        sample_agent_schema, mock_agent_type
    ):
        """Test complete agent type lifecycle."""
        # Setup mocks
        mock_schema_manager.register_agent_type.return_value = mock_agent_type
        mock_schema_manager.get_agent_type.return_value = mock_agent_type
        mock_schema_manager.deprecate_agent_type.return_value = True
        
        # Mock list query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_type]
        mock_db_session.execute.return_value = mock_result
        
        # 1. Register agent type
        schema_dict = sample_agent_schema.dict()
        registered = await agent_registry.register_agent_type(schema_dict, "test_user")
        assert registered == mock_agent_type
        
        # 2. List agent types
        agent_types = await agent_registry.list_agent_types()
        assert len(agent_types) == 1
        assert agent_types[0].agent_type == "test_agent"
        
        # 3. Get agent info
        info = await agent_registry.get_agent_type_info("test_agent")
        assert info is not None
        assert info.agent_type == "test_agent"
        
        # 4. Get capabilities
        capabilities = await agent_registry.get_agent_capabilities("test_agent")
        assert capabilities is not None
        assert capabilities.agent_type == "test_agent"
        
        # 5. Deprecate agent type
        deprecated = await agent_registry.deprecate_agent_type("test_agent")
        assert deprecated is True
        
        # Verify all operations completed successfully
        mock_schema_manager.register_agent_type.assert_called_once()
        mock_schema_manager.get_agent_type.assert_called()
        mock_schema_manager.deprecate_agent_type.assert_called_once()
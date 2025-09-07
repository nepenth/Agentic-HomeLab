"""
Tests for the AgentFactory class.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.factory import AgentFactory, AgentConfigurationError
from app.agents.dynamic_agent import DynamicAgent
from app.agents.tools.registry import ToolRegistry
from app.services.schema_manager import SchemaManager
from app.schemas.agent_schema import (
    AgentSchema, AgentMetadata, DataModelDefinition, FieldDefinition, FieldType,
    ProcessingPipeline, ProcessingStep, ToolDefinition, ToolAuthConfig
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
def mock_tool_registry():
    """Mock tool registry."""
    return AsyncMock(spec=ToolRegistry)


@pytest.fixture
def sample_agent_schema():
    """Sample agent schema for testing."""
    return AgentSchema(
        agent_type="test_agent",
        metadata=AgentMetadata(
            name="Test Agent",
            description="A test agent",
            category="testing",
            version="1.0.0"
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
def agent_factory(mock_db_session, mock_schema_manager, mock_tool_registry):
    """Create AgentFactory instance for testing."""
    return AgentFactory(
        db_session=mock_db_session,
        schema_manager=mock_schema_manager,
        tool_registry=mock_tool_registry
    )


class TestAgentFactory:
    """Test cases for AgentFactory."""
    
    @pytest.mark.asyncio
    async def test_create_agent_success(
        self, agent_factory, mock_schema_manager, mock_tool_registry, sample_agent_schema
    ):
        """Test successful agent creation."""
        # Setup mocks
        agent_type_record = MagicMock()
        agent_type_record.schema_definition = sample_agent_schema.dict()
        mock_schema_manager.get_agent_type.return_value = agent_type_record
        
        mock_tool = AsyncMock()
        mock_tool_registry.get_tool.return_value = mock_tool
        
        # Create agent
        agent_id = uuid.uuid4()
        task_id = uuid.uuid4()
        
        agent = await agent_factory.create_agent(
            agent_id=agent_id,
            task_id=task_id,
            agent_type="test_agent",
            name="Test Agent Instance",
            config={"text": "Hello world"}
        )
        
        # Verify result
        assert isinstance(agent, DynamicAgent)
        assert agent.agent_id == agent_id
        assert agent.task_id == task_id
        assert agent.name == "Test Agent Instance"
        assert agent.schema.agent_type == "test_agent"
        
        # Verify schema manager was called
        mock_schema_manager.get_agent_type.assert_called_once_with("test_agent", None)
        
        # Verify tool registry was called
        mock_tool_registry.get_tool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_agent_type_not_found(
        self, agent_factory, mock_schema_manager
    ):
        """Test agent creation when agent type is not found."""
        # Setup mock to return None
        mock_schema_manager.get_agent_type.return_value = None
        
        # Attempt to create agent
        with pytest.raises(AgentConfigurationError, match="Agent type 'nonexistent' not found"):
            await agent_factory.create_agent(
                agent_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
                agent_type="nonexistent",
                name="Test Agent"
            )
    
    @pytest.mark.asyncio
    async def test_create_agent_from_schema(
        self, agent_factory, mock_tool_registry, sample_agent_schema
    ):
        """Test creating agent directly from schema."""
        # Setup mock
        mock_tool = AsyncMock()
        mock_tool_registry.get_tool.return_value = mock_tool
        
        # Create agent
        agent_id = uuid.uuid4()
        task_id = uuid.uuid4()
        
        agent = await agent_factory.create_agent_from_schema(
            agent_id=agent_id,
            task_id=task_id,
            name="Direct Schema Agent",
            schema=sample_agent_schema,
            config={"text": "Hello world"}
        )
        
        # Verify result
        assert isinstance(agent, DynamicAgent)
        assert agent.agent_id == agent_id
        assert agent.task_id == task_id
        assert agent.name == "Direct Schema Agent"
        assert agent.schema == sample_agent_schema
    
    @pytest.mark.asyncio
    async def test_validate_and_merge_config_success(
        self, agent_factory, sample_agent_schema
    ):
        """Test successful configuration validation and merging."""
        user_config = {
            "text": "Test input",
            "temperature": 0.8,
            "extra_param": "extra_value"
        }
        
        merged_config = await agent_factory._validate_and_merge_config(
            sample_agent_schema, user_config
        )
        
        # Verify merged configuration
        assert merged_config["text"] == "Test input"
        assert merged_config["temperature"] == 0.8
        assert merged_config["extra_param"] == "extra_value"
        assert "tools" in merged_config
        assert "llm_processor" in merged_config["tools"]
    
    @pytest.mark.asyncio
    async def test_validate_and_merge_config_missing_required(
        self, agent_factory, sample_agent_schema
    ):
        """Test configuration validation with missing required field."""
        user_config = {
            "temperature": 0.8  # Missing required 'text' field
        }
        
        with pytest.raises(AgentConfigurationError, match="Required field 'text' is missing"):
            await agent_factory._validate_and_merge_config(
                sample_agent_schema, user_config
            )
    
    @pytest.mark.asyncio
    async def test_validate_and_merge_config_with_defaults(
        self, agent_factory, sample_agent_schema
    ):
        """Test configuration validation with default values."""
        user_config = {
            "text": "Test input"
            # temperature should use default value
        }
        
        merged_config = await agent_factory._validate_and_merge_config(
            sample_agent_schema, user_config
        )
        
        # Verify default value is used
        assert merged_config["text"] == "Test input"
        assert merged_config["temperature"] == 0.7  # Default value
    
    def test_validate_field_value_string(self, agent_factory):
        """Test string field validation."""
        field_def = FieldDefinition(
            type=FieldType.STRING,
            max_length=10,
            min_length=2,
            pattern=r"^[A-Z].*"
        )
        
        # Valid string
        assert agent_factory._validate_field_value("test", "Hello", field_def) is None
        
        # Invalid type
        assert "must be a string" in agent_factory._validate_field_value("test", 123, field_def)
        
        # Too long
        assert "exceeds maximum length" in agent_factory._validate_field_value("test", "TooLongString", field_def)
        
        # Too short
        assert "below minimum length" in agent_factory._validate_field_value("test", "A", field_def)
        
        # Pattern mismatch
        assert "does not match required pattern" in agent_factory._validate_field_value("test", "hello", field_def)
    
    def test_validate_field_value_numeric(self, agent_factory):
        """Test numeric field validation."""
        int_field = FieldDefinition(type=FieldType.INTEGER, range=[1, 10])
        float_field = FieldDefinition(type=FieldType.FLOAT, range=[0.0, 1.0])
        
        # Valid integer
        assert agent_factory._validate_field_value("test", 5, int_field) is None
        
        # Invalid integer type
        assert "must be an integer" in agent_factory._validate_field_value("test", 5.5, int_field)
        
        # Integer out of range
        assert "must be between" in agent_factory._validate_field_value("test", 15, int_field)
        
        # Valid float
        assert agent_factory._validate_field_value("test", 0.5, float_field) is None
        
        # Float out of range
        assert "must be between" in agent_factory._validate_field_value("test", 1.5, float_field)
    
    def test_validate_field_value_enum(self, agent_factory):
        """Test enum field validation."""
        field_def = FieldDefinition(
            type=FieldType.ENUM,
            values=["option1", "option2", "option3"]
        )
        
        # Valid enum value
        assert agent_factory._validate_field_value("test", "option1", field_def) is None
        
        # Invalid enum value
        assert "must be one of" in agent_factory._validate_field_value("test", "invalid", field_def)
    
    @pytest.mark.asyncio
    async def test_load_tools_success(
        self, agent_factory, mock_tool_registry, sample_agent_schema
    ):
        """Test successful tool loading."""
        # Setup mock
        mock_tool = AsyncMock()
        mock_tool_registry.get_tool.return_value = mock_tool
        
        config = {
            "tools": {
                "llm_processor": {"custom_param": "value"}
            }
        }
        
        tools = await agent_factory._load_tools(sample_agent_schema.tools, config)
        
        # Verify tools were loaded
        assert "llm_processor" in tools
        assert tools["llm_processor"] == mock_tool
        
        # Verify tool registry was called with correct parameters
        mock_tool_registry.get_tool.assert_called_once_with(
            "llm_processor",
            {"model_name": "llama2", "custom_param": "value"},
            auth_config=None,
            rate_limit=None,
            timeout=None
        )
    
    @pytest.mark.asyncio
    async def test_load_tools_failure(
        self, agent_factory, mock_tool_registry, sample_agent_schema
    ):
        """Test tool loading failure."""
        # Setup mock to raise exception
        mock_tool_registry.get_tool.side_effect = Exception("Tool not found")
        
        config = {"tools": {}}
        
        with pytest.raises(AgentConfigurationError, match="Failed to load tool 'llm_processor'"):
            await agent_factory._load_tools(sample_agent_schema.tools, config)
    
    @pytest.mark.asyncio
    async def test_validate_agent_config_success(
        self, agent_factory, mock_schema_manager, sample_agent_schema
    ):
        """Test successful agent configuration validation."""
        # Setup mock
        agent_type_record = MagicMock()
        agent_type_record.schema_definition = sample_agent_schema.dict()
        mock_schema_manager.get_agent_type.return_value = agent_type_record
        
        config = {"text": "Test input"}
        
        result = await agent_factory.validate_agent_config("test_agent", config)
        
        # Verify result
        assert result["valid"] is True
        assert result["merged_config"]["text"] == "Test input"
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_validate_agent_config_failure(
        self, agent_factory, mock_schema_manager, sample_agent_schema
    ):
        """Test agent configuration validation failure."""
        # Setup mock
        agent_type_record = MagicMock()
        agent_type_record.schema_definition = sample_agent_schema.dict()
        mock_schema_manager.get_agent_type.return_value = agent_type_record
        
        config = {}  # Missing required 'text' field
        
        result = await agent_factory.validate_agent_config("test_agent", config)
        
        # Verify result
        assert result["valid"] is False
        assert result["merged_config"] is None
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities(
        self, agent_factory, mock_schema_manager, sample_agent_schema
    ):
        """Test getting agent capabilities."""
        # Setup mock
        agent_type_record = MagicMock()
        agent_type_record.schema_definition = sample_agent_schema.dict()
        mock_schema_manager.get_agent_type.return_value = agent_type_record
        
        capabilities = await agent_factory.get_agent_capabilities("test_agent")
        
        # Verify capabilities
        assert capabilities["agent_type"] == "test_agent"
        assert capabilities["name"] == "Test Agent"
        assert capabilities["description"] == "A test agent"
        assert capabilities["category"] == "testing"
        assert "input_schema" in capabilities
        assert "output_schema" in capabilities
        assert "data_models" in capabilities
        assert "tools" in capabilities
        assert capabilities["processing_steps"] == 1
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities_not_found(
        self, agent_factory, mock_schema_manager
    ):
        """Test getting capabilities for non-existent agent type."""
        # Setup mock to return None
        mock_schema_manager.get_agent_type.return_value = None
        
        with pytest.raises(AgentConfigurationError, match="Agent type 'nonexistent' not found"):
            await agent_factory.get_agent_capabilities("nonexistent")


class TestAgentFactoryIntegration:
    """Integration tests for AgentFactory."""
    
    @pytest.mark.asyncio
    async def test_full_agent_creation_workflow(
        self, agent_factory, mock_schema_manager, mock_tool_registry, sample_agent_schema
    ):
        """Test complete agent creation workflow."""
        # Setup mocks
        agent_type_record = MagicMock()
        agent_type_record.schema_definition = sample_agent_schema.dict()
        mock_schema_manager.get_agent_type.return_value = agent_type_record
        
        mock_tool = AsyncMock()
        mock_tool_registry.get_tool.return_value = mock_tool
        
        # Test configuration validation
        config = {"text": "Hello world", "temperature": 0.8}
        validation_result = await agent_factory.validate_agent_config("test_agent", config)
        assert validation_result["valid"] is True
        
        # Test capabilities retrieval
        capabilities = await agent_factory.get_agent_capabilities("test_agent")
        assert capabilities["agent_type"] == "test_agent"
        
        # Test agent creation
        agent = await agent_factory.create_agent(
            agent_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            agent_type="test_agent",
            name="Integration Test Agent",
            config=config
        )
        
        assert isinstance(agent, DynamicAgent)
        assert agent.schema.agent_type == "test_agent"
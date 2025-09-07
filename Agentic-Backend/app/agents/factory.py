"""
Agent factory for dynamic agent instantiation.
"""
from typing import Dict, Any, Optional, Type, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.base import BaseAgent
from app.agents.dynamic_agent import DynamicAgent
from app.services.schema_manager import SchemaManager
from app.agents.tools.registry import ToolRegistry
from app.db.models.agent_type import AgentType
from app.schemas.agent_schema import AgentSchema, ToolDefinition
from app.services.ollama_client import OllamaClient
from app.services.log_service import LogService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentConfigurationError(Exception):
    """Raised when agent configuration is invalid."""
    pass


class AgentFactory:
    """Factory for creating dynamic agent instances from schema definitions."""
    
    def __init__(
        self,
        db_session: AsyncSession,
        schema_manager: SchemaManager,
        tool_registry: ToolRegistry,
        ollama_client: Optional[OllamaClient] = None,
        log_service: Optional[LogService] = None
    ):
        self.db = db_session
        self.schema_manager = schema_manager
        self.tool_registry = tool_registry
        self.ollama_client = ollama_client
        self.log_service = log_service
    
    async def create_agent(
        self,
        agent_id: UUID,
        task_id: UUID,
        agent_type: str,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None
    ) -> DynamicAgent:
        """
        Create a dynamic agent instance from a registered agent type.
        
        Args:
            agent_id: Unique identifier for the agent instance
            task_id: Task ID this agent will process
            agent_type: The registered agent type name
            name: Human-readable name for the agent instance
            config: Optional configuration overrides
            version: Specific version of the agent type (None for latest)
            
        Returns:
            DynamicAgent instance ready for task processing
            
        Raises:
            AgentConfigurationError: If agent type not found or configuration invalid
        """
        try:
            # Get the agent type schema
            agent_type_record = await self.schema_manager.get_agent_type(agent_type, version)
            if not agent_type_record:
                raise AgentConfigurationError(f"Agent type '{agent_type}' not found")
            
            # Parse the schema
            agent_schema = AgentSchema(**agent_type_record.schema_definition)
            
            # Validate and merge configuration
            merged_config = await self._validate_and_merge_config(agent_schema, config or {})
            
            # Load required tools
            tools = await self._load_tools(agent_schema.tools, merged_config)
            
            # Create the dynamic agent
            dynamic_agent = DynamicAgent(
                agent_id=agent_id,
                task_id=task_id,
                name=name,
                model_name=merged_config.get("model_name", "llama2"),
                config=merged_config,
                schema=agent_schema,
                tools=tools,
                ollama_client=self.ollama_client,
                log_service=self.log_service
            )
            
            logger.info(f"Created dynamic agent: {name} (type: {agent_type}, id: {agent_id})")
            return dynamic_agent
            
        except Exception as e:
            logger.error(f"Failed to create agent '{name}' of type '{agent_type}': {e}")
            raise AgentConfigurationError(f"Failed to create agent: {str(e)}")
    
    async def create_agent_from_schema(
        self,
        agent_id: UUID,
        task_id: UUID,
        name: str,
        schema: AgentSchema,
        config: Optional[Dict[str, Any]] = None
    ) -> DynamicAgent:
        """
        Create a dynamic agent instance directly from a schema (for testing/development).
        
        Args:
            agent_id: Unique identifier for the agent instance
            task_id: Task ID this agent will process
            name: Human-readable name for the agent instance
            schema: The agent schema definition
            config: Optional configuration overrides
            
        Returns:
            DynamicAgent instance ready for task processing
            
        Raises:
            AgentConfigurationError: If configuration is invalid
        """
        try:
            # Validate and merge configuration
            merged_config = await self._validate_and_merge_config(schema, config or {})
            
            # Load required tools
            tools = await self._load_tools(schema.tools, merged_config)
            
            # Create the dynamic agent
            dynamic_agent = DynamicAgent(
                agent_id=agent_id,
                task_id=task_id,
                name=name,
                model_name=merged_config.get("model_name", "llama2"),
                config=merged_config,
                schema=schema,
                tools=tools,
                ollama_client=self.ollama_client,
                log_service=self.log_service
            )
            
            logger.info(f"Created dynamic agent from schema: {name} (id: {agent_id})")
            return dynamic_agent
            
        except Exception as e:
            logger.error(f"Failed to create agent '{name}' from schema: {e}")
            raise AgentConfigurationError(f"Failed to create agent from schema: {str(e)}")
    
    async def _validate_and_merge_config(
        self,
        schema: AgentSchema,
        user_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate user configuration against schema and merge with defaults.
        
        Args:
            schema: The agent schema
            user_config: User-provided configuration
            
        Returns:
            Merged and validated configuration
            
        Raises:
            AgentConfigurationError: If configuration is invalid
        """
        merged_config = {}
        errors = []
        
        # Start with schema defaults
        for field_name, field_def in schema.input_schema.items():
            if field_def.default is not None:
                merged_config[field_name] = field_def.default
        
        # Apply user configuration
        for key, value in user_config.items():
            if key in schema.input_schema:
                field_def = schema.input_schema[key]
                
                # Validate the value against field definition
                validation_error = self._validate_field_value(key, value, field_def)
                if validation_error:
                    errors.append(validation_error)
                else:
                    merged_config[key] = value
            else:
                # Allow additional config not in schema (for flexibility)
                merged_config[key] = value
        
        # Check required fields
        for field_name, field_def in schema.input_schema.items():
            if field_def.required and field_name not in merged_config:
                errors.append(f"Required field '{field_name}' is missing")
        
        # Add resource limits from schema
        if schema.max_execution_time:
            merged_config["max_execution_time"] = schema.max_execution_time
        if schema.max_memory_usage:
            merged_config["max_memory_usage"] = schema.max_memory_usage
        
        # Add tool configurations
        tool_configs = {}
        for tool_name, tool_def in schema.tools.items():
            tool_configs[tool_name] = tool_def.config.copy()
            
            # Override with user-provided tool config if present
            user_tool_config = user_config.get("tools", {}).get(tool_name, {})
            tool_configs[tool_name].update(user_tool_config)
        
        merged_config["tools"] = tool_configs
        
        if errors:
            raise AgentConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return merged_config
    
    def _validate_field_value(self, field_name: str, value: Any, field_def) -> Optional[str]:
        """
        Validate a field value against its definition.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            field_def: Field definition from schema
            
        Returns:
            Error message if validation fails, None if valid
        """
        from app.schemas.agent_schema import FieldType
        
        try:
            # Type validation
            if field_def.type == FieldType.STRING:
                if not isinstance(value, str):
                    return f"Field '{field_name}' must be a string"
                if field_def.max_length and len(value) > field_def.max_length:
                    return f"Field '{field_name}' exceeds maximum length of {field_def.max_length}"
                if field_def.min_length and len(value) < field_def.min_length:
                    return f"Field '{field_name}' is below minimum length of {field_def.min_length}"
                if field_def.pattern:
                    import re
                    if not re.match(field_def.pattern, value):
                        return f"Field '{field_name}' does not match required pattern"
            
            elif field_def.type == FieldType.INTEGER:
                if not isinstance(value, int):
                    return f"Field '{field_name}' must be an integer"
                if field_def.range:
                    if value < field_def.range[0] or value > field_def.range[1]:
                        return f"Field '{field_name}' must be between {field_def.range[0]} and {field_def.range[1]}"
            
            elif field_def.type == FieldType.FLOAT:
                if not isinstance(value, (int, float)):
                    return f"Field '{field_name}' must be a number"
                if field_def.range:
                    if value < field_def.range[0] or value > field_def.range[1]:
                        return f"Field '{field_name}' must be between {field_def.range[0]} and {field_def.range[1]}"
            
            elif field_def.type == FieldType.BOOLEAN:
                if not isinstance(value, bool):
                    return f"Field '{field_name}' must be a boolean"
            
            elif field_def.type == FieldType.ARRAY:
                if not isinstance(value, list):
                    return f"Field '{field_name}' must be an array"
            
            elif field_def.type == FieldType.ENUM:
                if field_def.values and value not in field_def.values:
                    return f"Field '{field_name}' must be one of: {', '.join(field_def.values)}"
            
            return None
            
        except Exception as e:
            return f"Validation error for field '{field_name}': {str(e)}"
    
    async def _load_tools(
        self,
        tool_definitions: Dict[str, ToolDefinition],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Load and configure tools for the agent.
        
        Args:
            tool_definitions: Tool definitions from schema
            config: Merged configuration including tool configs
            
        Returns:
            Dictionary of configured tool instances
            
        Raises:
            AgentConfigurationError: If tool loading fails
        """
        tools = {}
        tool_configs = config.get("tools", {})
        
        for tool_name, tool_def in tool_definitions.items():
            try:
                # Get tool configuration and merge with schema defaults
                tool_config = tool_def.config.copy()
                user_tool_config = tool_configs.get(tool_name, {})
                tool_config.update(user_tool_config)
                
                # Load the tool from registry
                tool_instance = await self.tool_registry.get_tool(
                    tool_def.type,
                    tool_config,
                    auth_config=tool_def.auth_config.dict() if tool_def.auth_config else None,
                    rate_limit=tool_def.rate_limit,
                    timeout=tool_def.timeout
                )
                
                tools[tool_name] = tool_instance
                
            except Exception as e:
                logger.error(f"Failed to load tool '{tool_name}': {e}")
                raise AgentConfigurationError(f"Failed to load tool '{tool_name}': {str(e)}")
        
        return tools
    
    async def validate_agent_config(
        self,
        agent_type: str,
        config: Dict[str, Any],
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate agent configuration without creating an agent instance.
        
        Args:
            agent_type: The agent type name
            config: Configuration to validate
            version: Specific version (None for latest)
            
        Returns:
            Dictionary with validation results
            
        Raises:
            AgentConfigurationError: If agent type not found
        """
        try:
            # Get the agent type schema
            agent_type_record = await self.schema_manager.get_agent_type(agent_type, version)
            if not agent_type_record:
                raise AgentConfigurationError(f"Agent type '{agent_type}' not found")
            
            # Parse the schema
            agent_schema = AgentSchema(**agent_type_record.schema_definition)
            
            # Validate configuration
            try:
                merged_config = await self._validate_and_merge_config(agent_schema, config)
                return {
                    "valid": True,
                    "merged_config": merged_config,
                    "errors": [],
                    "warnings": []
                }
            except AgentConfigurationError as e:
                return {
                    "valid": False,
                    "merged_config": None,
                    "errors": [str(e)],
                    "warnings": []
                }
                
        except Exception as e:
            logger.error(f"Failed to validate config for agent type '{agent_type}': {e}")
            raise AgentConfigurationError(f"Failed to validate configuration: {str(e)}")
    
    async def get_agent_capabilities(self, agent_type: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Get capabilities and requirements for an agent type.
        
        Args:
            agent_type: The agent type name
            version: Specific version (None for latest)
            
        Returns:
            Dictionary with agent capabilities information
            
        Raises:
            AgentConfigurationError: If agent type not found
        """
        try:
            # Get the agent type schema
            agent_type_record = await self.schema_manager.get_agent_type(agent_type, version)
            if not agent_type_record:
                raise AgentConfigurationError(f"Agent type '{agent_type}' not found")
            
            # Parse the schema
            agent_schema = AgentSchema(**agent_type_record.schema_definition)
            
            return {
                "agent_type": agent_type,
                "version": agent_schema.metadata.version,
                "name": agent_schema.metadata.name,
                "description": agent_schema.metadata.description,
                "category": agent_schema.metadata.category,
                "input_schema": {
                    name: {
                        "type": field.type.value,
                        "required": field.required,
                        "description": field.description,
                        "default": field.default
                    }
                    for name, field in agent_schema.input_schema.items()
                },
                "output_schema": {
                    name: {
                        "type": field.type.value,
                        "description": field.description
                    }
                    for name, field in agent_schema.output_schema.items()
                },
                "data_models": {
                    name: {
                        "table_name": model.table_name,
                        "description": model.description,
                        "fields": len(model.fields)
                    }
                    for name, model in agent_schema.data_models.items()
                },
                "tools": {
                    name: {
                        "type": tool.type,
                        "description": tool.description
                    }
                    for name, tool in agent_schema.tools.items()
                },
                "processing_steps": len(agent_schema.processing_pipeline.steps),
                "resource_limits": {
                    "max_execution_time": agent_schema.max_execution_time,
                    "max_memory_usage": agent_schema.max_memory_usage
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get capabilities for agent type '{agent_type}': {e}")
            raise AgentConfigurationError(f"Failed to get agent capabilities: {str(e)}")
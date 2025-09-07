"""
Tool registry for managing and instantiating tools for dynamic agents.
"""
from typing import Dict, Type, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.tools.base import Tool, ToolExecutionError
from app.db.models.agent_type import RegisteredTool
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ToolRegistrationError(Exception):
    """Raised when tool registration fails."""
    pass


class ToolNotFoundError(Exception):
    """Raised when requested tool is not found."""
    pass


class ToolRegistry:
    """Registry for managing tool types and creating tool instances."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db = db_session
        self._tool_classes: Dict[str, Type[Tool]] = {}
        self._builtin_tools_registered = False
    
    def register_tool(self, tool_type: str, tool_class: Type[Tool]) -> None:
        """
        Register a tool class with the registry.
        
        Args:
            tool_type: Unique identifier for the tool type
            tool_class: Tool class that implements the Tool interface
            
        Raises:
            ToolRegistrationError: If registration fails
        """
        if not issubclass(tool_class, Tool):
            raise ToolRegistrationError(f"Tool class must inherit from Tool base class")
        
        if tool_type in self._tool_classes:
            logger.warning(f"Overriding existing tool type: {tool_type}")
        
        self._tool_classes[tool_type] = tool_class
        logger.info(f"Registered tool type: {tool_type}")
    
    async def register_tool_in_db(
        self,
        tool_name: str,
        tool_class_path: str,
        schema_definition: Dict[str, Any],
        documentation: Optional[Dict[str, Any]] = None
    ) -> RegisteredTool:
        """
        Register a tool in the database for persistence.
        
        Args:
            tool_name: Unique name for the tool
            tool_class_path: Full path to the tool class (e.g., 'app.agents.tools.llm.LLMProcessor')
            schema_definition: Tool schema definition
            documentation: Optional documentation for the tool
            
        Returns:
            RegisteredTool instance
            
        Raises:
            ToolRegistrationError: If registration fails
        """
        if not self.db:
            raise ToolRegistrationError("Database session required for persistent registration")
        
        try:
            # Check if tool already exists
            existing = await self.db.execute(
                select(RegisteredTool).where(RegisteredTool.tool_name == tool_name)
            )
            if existing.scalar_one_or_none():
                raise ToolRegistrationError(f"Tool '{tool_name}' already registered")
            
            # Create registered tool record
            registered_tool = RegisteredTool(
                tool_name=tool_name,
                tool_class=tool_class_path,
                schema_definition=schema_definition,
                documentation=documentation or {}
            )
            
            self.db.add(registered_tool)
            await self.db.commit()
            
            logger.info(f"Registered tool in database: {tool_name}")
            return registered_tool
            
        except Exception as e:
            if self.db:
                await self.db.rollback()
            logger.error(f"Failed to register tool '{tool_name}' in database: {e}")
            raise ToolRegistrationError(f"Failed to register tool: {str(e)}")
    
    async def get_tool(
        self,
        tool_type: str,
        config: Dict[str, Any],
        auth_config: Optional[Dict[str, Any]] = None,
        rate_limit: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Tool:
        """
        Create a tool instance of the specified type.
        
        Args:
            tool_type: Type of tool to create
            config: Configuration for the tool
            auth_config: Authentication configuration
            rate_limit: Rate limiting configuration
            timeout: Timeout configuration
            
        Returns:
            Configured tool instance
            
        Raises:
            ToolNotFoundError: If tool type is not registered
            ToolExecutionError: If tool creation fails
        """
        # Ensure builtin tools are registered
        if not self._builtin_tools_registered:
            await self._register_builtin_tools()
        
        # Check in-memory registry first
        if tool_type in self._tool_classes:
            tool_class = self._tool_classes[tool_type]
        else:
            # Try to load from database
            tool_class = await self._load_tool_from_db(tool_type)
        
        if not tool_class:
            raise ToolNotFoundError(f"Tool type '{tool_type}' not found")
        
        try:
            # Prepare full configuration
            full_config = config.copy()
            if auth_config:
                full_config["auth_config"] = auth_config
            if rate_limit:
                full_config["rate_limit"] = rate_limit
            if timeout:
                full_config["timeout"] = timeout
            
            # Create tool instance
            tool_instance = tool_class(full_config)
            
            logger.debug(f"Created tool instance: {tool_type}")
            return tool_instance
            
        except Exception as e:
            logger.error(f"Failed to create tool '{tool_type}': {e}")
            raise ToolExecutionError(f"Failed to create tool: {str(e)}", tool_type)
    
    async def _load_tool_from_db(self, tool_type: str) -> Optional[Type[Tool]]:
        """
        Load a tool class from database registration.
        
        Args:
            tool_type: Tool type to load
            
        Returns:
            Tool class if found, None otherwise
        """
        if not self.db:
            return None
        
        try:
            # Get tool registration from database
            result = await self.db.execute(
                select(RegisteredTool).where(
                    RegisteredTool.tool_name == tool_type,
                    RegisteredTool.is_enabled == True
                )
            )
            registered_tool = result.scalar_one_or_none()
            
            if not registered_tool:
                return None
            
            # Dynamically import the tool class
            module_path, class_name = registered_tool.tool_class.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            tool_class = getattr(module, class_name)
            
            # Cache in memory for future use
            self._tool_classes[tool_type] = tool_class
            
            logger.info(f"Loaded tool from database: {tool_type}")
            return tool_class
            
        except Exception as e:
            logger.error(f"Failed to load tool '{tool_type}' from database: {e}")
            return None
    
    async def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        try:
            # Import and register built-in tools
            from app.agents.tools.llm_processor import LLMProcessor
            from app.agents.tools.database_writer import DatabaseWriter
            from app.agents.tools.email_connector import EmailConnector
            
            self.register_tool("llm_processor", LLMProcessor)
            self.register_tool("database_writer", DatabaseWriter)
            self.register_tool("email_connector", EmailConnector)
            
            self._builtin_tools_registered = True
            logger.info("Registered built-in tools")
            
        except ImportError as e:
            logger.warning(f"Some built-in tools not available: {e}")
            self._builtin_tools_registered = True
    
    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools.
        
        Returns:
            List of tool information dictionaries
        """
        tools = []
        
        # Ensure builtin tools are registered
        if not self._builtin_tools_registered:
            await self._register_builtin_tools()
        
        # Add in-memory tools
        for tool_type, tool_class in self._tool_classes.items():
            try:
                # Create temporary instance to get schema
                temp_instance = tool_class({})
                tools.append({
                    "tool_type": tool_type,
                    "source": "builtin",
                    "schema": temp_instance.get_schema(),
                    "class_name": tool_class.__name__
                })
            except Exception as e:
                logger.warning(f"Failed to get schema for tool '{tool_type}': {e}")
        
        # Add database-registered tools
        if self.db:
            try:
                result = await self.db.execute(
                    select(RegisteredTool).where(RegisteredTool.is_enabled == True)
                )
                registered_tools = result.scalars().all()
                
                for registered_tool in registered_tools:
                    if registered_tool.tool_name not in self._tool_classes:
                        tools.append({
                            "tool_type": registered_tool.tool_name,
                            "source": "database",
                            "schema": registered_tool.schema_definition,
                            "class_path": registered_tool.tool_class,
                            "documentation": registered_tool.documentation
                        })
            except Exception as e:
                logger.error(f"Failed to list database tools: {e}")
        
        return tools
    
    async def get_tool_schema(self, tool_type: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific tool type.
        
        Args:
            tool_type: Tool type to get schema for
            
        Returns:
            Tool schema if found, None otherwise
        """
        try:
            # Try to get from in-memory registry
            if tool_type in self._tool_classes:
                tool_class = self._tool_classes[tool_type]
                temp_instance = tool_class({})
                return temp_instance.get_schema()
            
            # Try to get from database
            if self.db:
                result = await self.db.execute(
                    select(RegisteredTool).where(
                        RegisteredTool.tool_name == tool_type,
                        RegisteredTool.is_enabled == True
                    )
                )
                registered_tool = result.scalar_one_or_none()
                
                if registered_tool:
                    return registered_tool.schema_definition
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get schema for tool '{tool_type}': {e}")
            return None
    
    async def disable_tool(self, tool_name: str) -> bool:
        """
        Disable a tool in the database.
        
        Args:
            tool_name: Name of the tool to disable
            
        Returns:
            True if tool was disabled, False if not found
        """
        if not self.db:
            return False
        
        try:
            result = await self.db.execute(
                select(RegisteredTool).where(RegisteredTool.tool_name == tool_name)
            )
            registered_tool = result.scalar_one_or_none()
            
            if registered_tool:
                registered_tool.is_enabled = False
                await self.db.commit()
                logger.info(f"Disabled tool: {tool_name}")
                return True
            
            return False
            
        except Exception as e:
            if self.db:
                await self.db.rollback()
            logger.error(f"Failed to disable tool '{tool_name}': {e}")
            return False
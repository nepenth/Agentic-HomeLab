"""
Email Assistant Tool System Base Classes

This module provides the base classes for the tool registry system.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logging import get_logger

logger = get_logger("email_tools")


class ToolDefinition(BaseModel):
    """Schema for a tool definition compatible with Ollama function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format


class EmailTool:
    """Base class for email assistant tools"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        """
        Return the tool definition for LLM consumption.

        Must be implemented by subclasses to define the tool's interface.
        """
        raise NotImplementedError(f"{cls.__name__} must implement get_definition()")

    @classmethod
    async def execute(cls, db: AsyncSession, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.

        Args:
            db: Database session
            user_id: User ID for permission checking
            **kwargs: Tool-specific parameters

        Returns:
            Dict containing execution results with at minimum:
                - success: bool indicating if execution succeeded
                - Additional tool-specific data
        """
        raise NotImplementedError(f"{cls.__name__} must implement execute()")


class ToolRegistry:
    """Registry for managing email assistant tools"""

    def __init__(self):
        self.tools: Dict[str, type[EmailTool]] = {}
        self.logger = get_logger("tool_registry")

    def register(self, tool_class: type[EmailTool]):
        """
        Register a new tool in the registry.

        Args:
            tool_class: EmailTool subclass to register
        """
        definition = tool_class.get_definition()
        self.tools[definition.name] = tool_class
        self.logger.info(f"Registered tool: {definition.name}")

    def get_all_definitions(self) -> List[ToolDefinition]:
        """
        Get all tool definitions for LLM consumption.

        Returns:
            List of tool definitions
        """
        return [tool.get_definition() for tool in self.tools.values()]

    async def execute_tool(
        self,
        db: AsyncSession,
        user_id: int,
        tool_name: str,
        **parameters
    ) -> Dict[str, Any]:
        """
        Execute a tool by name with given parameters.

        Args:
            db: Database session
            user_id: User ID for permission checking
            tool_name: Name of the tool to execute
            **parameters: Tool-specific parameters

        Returns:
            Dict containing execution results

        Raises:
            ValueError: If tool_name is not registered
        """
        if tool_name not in self.tools:
            available_tools = ", ".join(self.tools.keys())
            raise ValueError(
                f"Unknown tool: {tool_name}. Available tools: {available_tools}"
            )

        self.logger.info(f"Executing tool '{tool_name}' for user {user_id}")

        try:
            result = await self.tools[tool_name].execute(db, user_id, **parameters)
            self.logger.info(f"Tool '{tool_name}' completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Tool '{tool_name}' execution failed: {e}", exc_info=True)
            raise

    def get_tool_count(self) -> int:
        """Get the number of registered tools"""
        return len(self.tools)

    def list_tools(self) -> List[str]:
        """Get list of registered tool names"""
        return list(self.tools.keys())


# Global tool registry instance
email_tool_registry = ToolRegistry()

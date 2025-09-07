"""
Base tool interface and execution context for dynamic agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class ExecutionContext:
    """Context passed to tools during execution."""
    
    def __init__(self, agent_context: Dict[str, Any]):
        self.agent_context = agent_context
        self.step_data: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.start_time = datetime.utcnow()
    
    def get_agent_id(self) -> str:
        """Get the agent ID from context."""
        return self.agent_context.get("agent_id", "")
    
    def get_task_id(self) -> str:
        """Get the task ID from context."""
        return self.agent_context.get("task_id", "")
    
    def get_agent_type(self) -> str:
        """Get the agent type from context."""
        return self.agent_context.get("agent_type", "")
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the execution context."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the execution context."""
        return self.metadata.get(key, default)
    
    def get_execution_time(self) -> float:
        """Get execution time in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()


class Tool(ABC):
    """Abstract base class for all tools used by dynamic agents."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tool_type = self.__class__.__name__
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute the tool with the given input data and context.
        
        Args:
            input_data: Input data for the tool
            context: Execution context with agent and step information
            
        Returns:
            Dictionary with tool execution results
            
        Raises:
            ToolExecutionError: If tool execution fails
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the tool's input/output schema definition.
        
        Returns:
            Dictionary describing the tool's schema
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the tool.
        
        Returns:
            Dictionary with tool information
        """
        return {
            "tool_type": self.tool_type,
            "config_keys": list(self.config.keys()),
            "schema": self.get_schema()
        }
    
    async def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input data against the tool's schema.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            Validated input data
            
        Raises:
            ToolValidationError: If validation fails
        """
        # Default implementation - tools can override for custom validation
        return input_data
    
    async def cleanup(self) -> None:
        """
        Cleanup resources after tool execution.
        Override in subclasses if cleanup is needed.
        """
        pass


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    
    def __init__(self, message: str, tool_type: str, details: Optional[Dict[str, Any]] = None):
        self.tool_type = tool_type
        self.details = details or {}
        super().__init__(message)


class ToolValidationError(Exception):
    """Raised when tool input validation fails."""
    
    def __init__(self, message: str, tool_type: str, validation_errors: Optional[List[str]] = None):
        self.tool_type = tool_type
        self.validation_errors = validation_errors or []
        super().__init__(message)
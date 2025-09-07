from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID
from app.services.ollama_client import OllamaClient
from app.services.log_service import LogService


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(
        self,
        agent_id: UUID,
        task_id: UUID,
        name: str,
        model_name: str,
        config: Optional[Dict[str, Any]] = None,
        ollama_client: Optional[OllamaClient] = None,
        log_service: Optional[LogService] = None
    ):
        self.agent_id = agent_id
        self.task_id = task_id
        self.name = name
        self.model_name = model_name
        self.config = config or {}
        self.ollama_client = ollama_client
        self.log_service = log_service
        
    @abstractmethod
    async def process_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return the result."""
        pass
    
    async def log_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info message."""
        if self.log_service:
            await self.log_service.log_info(self.task_id, self.agent_id, message, context)
    
    async def log_error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log error message."""
        if self.log_service:
            await self.log_service.log_error(self.task_id, self.agent_id, message, context)
    
    async def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        if self.log_service:
            await self.log_service.log_warning(self.task_id, self.agent_id, message, context)
    
    async def log_debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        if self.log_service:
            await self.log_service.log_debug(self.task_id, self.agent_id, message, context)
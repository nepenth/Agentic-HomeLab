"""
Dynamic agent implementation that processes tasks based on schema definitions.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.agents.base import BaseAgent
from app.schemas.agent_schema import AgentSchema
from app.agents.processing.pipeline import ProcessingPipeline
from app.services.ollama_client import OllamaClient
from app.services.log_service import LogService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DynamicAgentError(Exception):
    """Raised when dynamic agent operations fail."""
    pass


class DynamicAgent(BaseAgent):
    """
    Dynamic agent that processes tasks based on schema-defined workflows.
    """
    
    def __init__(
        self,
        agent_id: UUID,
        task_id: UUID,
        name: str,
        model_name: str,
        config: Dict[str, Any],
        schema: AgentSchema,
        tools: Dict[str, Any],
        ollama_client: Optional[OllamaClient] = None,
        log_service: Optional[LogService] = None
    ):
        super().__init__(
            agent_id=agent_id,
            task_id=task_id,
            name=name,
            model_name=model_name,
            config=config,
            ollama_client=ollama_client,
            log_service=log_service
        )
        
        self.schema = schema
        self.tools = tools
        self.pipeline = ProcessingPipeline.from_schema(
            schema.processing_pipeline,
            tools,
            ollama_client,
            log_service
        )
        
        # Track execution state
        self.execution_start_time: Optional[datetime] = None
        self.execution_context: Dict[str, Any] = {}
    
    async def process_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task using the schema-defined pipeline.
        
        Args:
            input_data: Input data for the task
            
        Returns:
            Processed results according to output schema
            
        Raises:
            DynamicAgentError: If task processing fails
        """
        try:
            self.execution_start_time = datetime.utcnow()
            
            await self.log_info("Starting dynamic agent task processing", {
                "agent_type": self.schema.agent_type,
                "input_keys": list(input_data.keys())
            })
            
            # Validate input against schema
            validated_input = await self._validate_input(input_data)
            
            # Initialize execution context
            self.execution_context = {
                "agent_id": str(self.agent_id),
                "task_id": str(self.task_id),
                "agent_type": self.schema.agent_type,
                "start_time": self.execution_start_time.isoformat(),
                "input": validated_input
            }
            
            # Execute processing pipeline
            pipeline_result = await self.pipeline.execute(validated_input, self.execution_context)
            
            # Validate output against schema
            validated_output = await self._validate_output(pipeline_result)
            
            # Store results if data models are defined
            if self.schema.data_models:
                await self._store_results(validated_output)
            
            await self.log_info("Dynamic agent task processing completed successfully", {
                "execution_time": (datetime.utcnow() - self.execution_start_time).total_seconds(),
                "output_keys": list(validated_output.keys())
            })
            
            return validated_output
            
        except Exception as e:
            await self.log_error("Dynamic agent task processing failed", {
                "error": str(e),
                "execution_time": (datetime.utcnow() - self.execution_start_time).total_seconds() if self.execution_start_time else 0
            })
            raise DynamicAgentError(f"Task processing failed: {str(e)}")
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input data against the agent's input schema.
        
        Args:
            input_data: Raw input data
            
        Returns:
            Validated and processed input data
            
        Raises:
            DynamicAgentError: If validation fails
        """
        validated_input = {}
        errors = []
        
        # Check required fields
        for field_name, field_def in self.schema.input_schema.items():
            if field_def.required and field_name not in input_data:
                errors.append(f"Required field '{field_name}' is missing")
            elif field_name in input_data:
                # Validate field value
                value = input_data[field_name]
                validation_error = self._validate_field_value(field_name, value, field_def)
                if validation_error:
                    errors.append(validation_error)
                else:
                    validated_input[field_name] = value
            elif field_def.default is not None:
                validated_input[field_name] = field_def.default
        
        # Include additional fields not in schema (for flexibility)
        for field_name, value in input_data.items():
            if field_name not in self.schema.input_schema:
                validated_input[field_name] = value
        
        if errors:
            raise DynamicAgentError(f"Input validation failed: {'; '.join(errors)}")
        
        return validated_input
    
    async def _validate_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate output data against the agent's output schema.
        
        Args:
            output_data: Raw output data from pipeline
            
        Returns:
            Validated output data
            
        Raises:
            DynamicAgentError: If validation fails
        """
        validated_output = {}
        errors = []
        
        # Check required output fields
        for field_name, field_def in self.schema.output_schema.items():
            if field_def.required and field_name not in output_data:
                errors.append(f"Required output field '{field_name}' is missing")
            elif field_name in output_data:
                # Validate field value
                value = output_data[field_name]
                validation_error = self._validate_field_value(field_name, value, field_def)
                if validation_error:
                    errors.append(validation_error)
                else:
                    validated_output[field_name] = value
            elif field_def.default is not None:
                validated_output[field_name] = field_def.default
        
        # Include additional fields not in schema
        for field_name, value in output_data.items():
            if field_name not in self.schema.output_schema:
                validated_output[field_name] = value
        
        if errors:
            raise DynamicAgentError(f"Output validation failed: {'; '.join(errors)}")
        
        return validated_output
    
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
    
    async def _store_results(self, results: Dict[str, Any]) -> None:
        """
        Store results in dynamic tables based on data models.
        
        Args:
            results: Validated results to store
        """
        try:
            # This will be implemented when we have the dynamic model system
            # For now, we'll log that results would be stored
            await self.log_info("Results ready for storage", {
                "data_models": list(self.schema.data_models.keys()),
                "result_keys": list(results.keys())
            })
            
            # TODO: Implement actual storage using DynamicModel
            # for model_name, model_def in self.schema.data_models.items():
            #     if model_name in results:
            #         model_class = DynamicModel.from_schema(model_def)
            #         await self._save_to_database(model_class, results[model_name])
            
        except Exception as e:
            await self.log_error("Failed to store results", {"error": str(e)})
            # Don't raise here - storage failure shouldn't fail the entire task
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get information about the agent's schema.
        
        Returns:
            Dictionary with schema information
        """
        return {
            "agent_type": self.schema.agent_type,
            "version": self.schema.metadata.version,
            "name": self.schema.metadata.name,
            "description": self.schema.metadata.description,
            "category": self.schema.metadata.category,
            "input_fields": list(self.schema.input_schema.keys()),
            "output_fields": list(self.schema.output_schema.keys()),
            "data_models": list(self.schema.data_models.keys()),
            "tools": list(self.schema.tools.keys()),
            "processing_steps": len(self.schema.processing_pipeline.steps)
        }
    
    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get current execution status.
        
        Returns:
            Dictionary with execution status information
        """
        status = {
            "agent_id": str(self.agent_id),
            "task_id": str(self.task_id),
            "schema_info": self.get_schema_info(),
            "execution_context": self.execution_context.copy()
        }
        
        if self.execution_start_time:
            status["execution_time"] = (datetime.utcnow() - self.execution_start_time).total_seconds()
        
        return status
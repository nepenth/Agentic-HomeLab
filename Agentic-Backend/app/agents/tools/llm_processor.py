"""
LLM processor tool for dynamic agents.
"""
from typing import Dict, Any
from app.agents.tools.base import Tool, ExecutionContext, ToolExecutionError
from app.services.ollama_client import OllamaClient


class LLMProcessor(Tool):
    """Tool for processing text using LLM models."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model_name", "llama2")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1000)
        self.system_prompt = config.get("system_prompt", "")
    
    async def execute(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute LLM processing on input text.
        
        Args:
            input_data: Must contain 'text' or 'prompt' field
            context: Execution context
            
        Returns:
            Dictionary with 'response' field containing LLM output
        """
        try:
            # Extract input text
            text = input_data.get("text") or input_data.get("prompt")
            if not text:
                raise ToolExecutionError("Input must contain 'text' or 'prompt' field", self.tool_type)
            
            # Prepare prompt
            if self.system_prompt:
                full_prompt = f"{self.system_prompt}\n\n{text}"
            else:
                full_prompt = text
            
            # For now, return a mock response since we don't have OllamaClient integration
            # TODO: Integrate with actual OllamaClient when available
            response = f"[LLM Response to: {text[:100]}...]"
            
            context.add_metadata("model_used", self.model_name)
            context.add_metadata("input_length", len(text))
            context.add_metadata("output_length", len(response))
            
            return {
                "response": response,
                "model": self.model_name,
                "input_length": len(text),
                "output_length": len(response)
            }
            
        except Exception as e:
            raise ToolExecutionError(f"LLM processing failed: {str(e)}", self.tool_type)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's input/output schema."""
        return {
            "name": "LLMProcessor",
            "description": "Process text using Large Language Models",
            "input_schema": {
                "text": {
                    "type": "string",
                    "required": True,
                    "description": "Text to process with LLM"
                },
                "prompt": {
                    "type": "string",
                    "required": False,
                    "description": "Alternative to 'text' field"
                }
            },
            "output_schema": {
                "response": {
                    "type": "string",
                    "description": "LLM response"
                },
                "model": {
                    "type": "string",
                    "description": "Model used for processing"
                },
                "input_length": {
                    "type": "integer",
                    "description": "Length of input text"
                },
                "output_length": {
                    "type": "integer",
                    "description": "Length of output text"
                }
            },
            "config_schema": {
                "model_name": {
                    "type": "string",
                    "default": "llama2",
                    "description": "LLM model to use"
                },
                "temperature": {
                    "type": "float",
                    "default": 0.7,
                    "description": "Sampling temperature"
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Maximum tokens to generate"
                },
                "system_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "System prompt to prepend"
                }
            }
        }
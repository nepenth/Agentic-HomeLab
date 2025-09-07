from typing import Dict, Any, Optional, List
from uuid import UUID
import json
from app.agents.base import BaseAgent
from app.services.ollama_client import OllamaClient
from app.services.log_service import LogService


class SimpleAgent(BaseAgent):
    """Simple agent implementation for basic text processing tasks."""
    
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
        super().__init__(agent_id, task_id, name, model_name, config, ollama_client, log_service)
        
        # Agent-specific configuration
        self.max_tokens = self.config.get("max_tokens", 1000)
        self.temperature = self.config.get("temperature", 0.7)
        self.system_prompt = self.config.get("system_prompt", "You are a helpful AI assistant.")
    
    async def process_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task using the Ollama model."""
        await self.log_info("Processing task", {"input_keys": list(input_data.keys())})
        
        try:
            # Extract task parameters
            task_type = input_data.get("type", "generate")
            
            if task_type == "generate":
                return await self._handle_generate_task(input_data)
            elif task_type == "chat":
                return await self._handle_chat_task(input_data)
            elif task_type == "summarize":
                return await self._handle_summarize_task(input_data)
            elif task_type == "analyze":
                return await self._handle_analyze_task(input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
                
        except Exception as e:
            await self.log_error(f"Task processing failed: {str(e)}")
            raise
    
    async def _handle_generate_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text generation task."""
        prompt = input_data.get("prompt")
        if not prompt:
            raise ValueError("Prompt is required for generate task")
        
        await self.log_info("Generating text", {"prompt_length": len(prompt)})
        
        options = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens
        }
        
        # Add any custom options from config
        if "options" in self.config:
            options.update(self.config["options"])
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                model=self.model_name,
                system=input_data.get("system", self.system_prompt),
                options=options
            )
            
            result = {
                "type": "generate",
                "response": response.get("response", ""),
                "model": self.model_name,
                "tokens_used": response.get("eval_count", 0),
                "processing_time": response.get("total_duration", 0) / 1_000_000  # Convert to seconds
            }
            
            await self.log_info("Text generation completed", {
                "response_length": len(result["response"]),
                "tokens_used": result["tokens_used"]
            })
            
            return result
            
        except Exception as e:
            await self.log_error(f"Text generation failed: {str(e)}")
            raise
    
    async def _handle_chat_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat completion task."""
        messages = input_data.get("messages")
        if not messages:
            raise ValueError("Messages are required for chat task")
        
        await self.log_info("Processing chat", {"message_count": len(messages)})
        
        options = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens
        }
        
        if "options" in self.config:
            options.update(self.config["options"])
        
        try:
            response = await self.ollama_client.chat(
                messages=messages,
                model=self.model_name,
                options=options
            )
            
            result = {
                "type": "chat",
                "message": response.get("message", {}),
                "model": self.model_name,
                "tokens_used": response.get("eval_count", 0),
                "processing_time": response.get("total_duration", 0) / 1_000_000
            }
            
            await self.log_info("Chat completion completed", {
                "response_length": len(result["message"].get("content", "")),
                "tokens_used": result["tokens_used"]
            })
            
            return result
            
        except Exception as e:
            await self.log_error(f"Chat completion failed: {str(e)}")
            raise
    
    async def _handle_summarize_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text summarization task."""
        text = input_data.get("text")
        if not text:
            raise ValueError("Text is required for summarize task")
        
        await self.log_info("Summarizing text", {"text_length": len(text)})
        
        summary_length = input_data.get("length", "medium")
        length_instructions = {
            "short": "in 1-2 sentences",
            "medium": "in 3-5 sentences", 
            "long": "in 1-2 paragraphs"
        }
        
        prompt = f"""Please summarize the following text {length_instructions.get(summary_length, 'concisely')}:

{text}

Summary:"""
        
        options = {
            "temperature": 0.3,  # Lower temperature for more focused summaries
            "num_predict": min(self.max_tokens, 500)  # Limit summary length
        }
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                model=self.model_name,
                system="You are an expert at creating clear, concise summaries.",
                options=options
            )
            
            result = {
                "type": "summarize",
                "summary": response.get("response", "").strip(),
                "original_length": len(text),
                "summary_length": len(response.get("response", "")),
                "compression_ratio": len(text) / max(len(response.get("response", "")), 1),
                "model": self.model_name,
                "tokens_used": response.get("eval_count", 0)
            }
            
            await self.log_info("Text summarization completed", {
                "compression_ratio": result["compression_ratio"],
                "summary_length": result["summary_length"]
            })
            
            return result
            
        except Exception as e:
            await self.log_error(f"Text summarization failed: {str(e)}")
            raise
    
    async def _handle_analyze_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text analysis task."""
        text = input_data.get("text")
        analysis_type = input_data.get("analysis_type", "general")
        
        if not text:
            raise ValueError("Text is required for analyze task")
        
        await self.log_info("Analyzing text", {
            "text_length": len(text),
            "analysis_type": analysis_type
        })
        
        analysis_prompts = {
            "sentiment": "Analyze the sentiment of the following text and provide a detailed explanation:",
            "topics": "Identify and list the main topics and themes in the following text:",
            "entities": "Extract all named entities (people, places, organizations, etc.) from the following text:",
            "general": "Provide a comprehensive analysis of the following text, including sentiment, main themes, and key insights:"
        }
        
        base_prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
        prompt = f"""{base_prompt}

{text}

Analysis:"""
        
        options = {
            "temperature": 0.2,  # Low temperature for consistent analysis
            "num_predict": self.max_tokens
        }
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                model=self.model_name,
                system="You are an expert text analyst. Provide detailed, structured analysis.",
                options=options
            )
            
            result = {
                "type": "analyze",
                "analysis_type": analysis_type,
                "analysis": response.get("response", "").strip(),
                "text_length": len(text),
                "model": self.model_name,
                "tokens_used": response.get("eval_count", 0),
                "processing_time": response.get("total_duration", 0) / 1_000_000
            }
            
            await self.log_info("Text analysis completed", {
                "analysis_type": analysis_type,
                "analysis_length": len(result["analysis"])
            })
            
            return result
            
        except Exception as e:
            await self.log_error(f"Text analysis failed: {str(e)}")
            raise
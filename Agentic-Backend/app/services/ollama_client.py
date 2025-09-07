import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("ollama_client")


class OllamaClient:
    """Async client for Ollama API."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_default_model
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Create HTTP session."""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=300,  # 5 minutes total timeout
                connect=10,  # 10 seconds connection timeout
                sock_read=60  # 60 seconds read timeout
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Connected to Ollama at {self.base_url}")
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Ollama")
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[List[int]] = None,
        stream: bool = False,
        raw: bool = False,
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate text completion."""
        # Ensure session is available and reconnect if needed
        if not self.session or self.session.closed:
            await self.connect()

        # Double-check session is still available after connect
        if not self.session:
            raise Exception("Failed to establish Ollama connection")

        model = model or self.default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "raw": raw
        }
        
        # Add optional parameters
        if system:
            payload["system"] = system
        if template:
            payload["template"] = template
        if context:
            payload["context"] = context
        if format:
            payload["format"] = format
        if options:
            payload["options"] = options
        
        try:
            logger.debug(f"Generating with model {model}: {prompt[:100]}...")
            
            async with self.session.post(f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                
                if stream:
                    return await self._handle_streaming_response(response)
                else:
                    result = await response.json()
                    logger.debug(f"Generated response: {result.get('response', '')[:100]}...")
                    return result
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in generate: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in generate: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Chat completion."""
        # Ensure session is available and reconnect if needed
        if not self.session or self.session.closed:
            await self.connect()

        # Double-check session is still available after connect
        if not self.session:
            raise Exception("Failed to establish Ollama connection")

        model = model or self.default_model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        if format:
            payload["format"] = format
        if options:
            payload["options"] = options
        
        try:
            logger.debug(f"Chat with model {model}: {len(messages)} messages")
            
            async with self.session.post(f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                
                if stream:
                    return await self._handle_streaming_response(response)
                else:
                    result = await response.json()
                    logger.debug(f"Chat response: {result.get('message', {}).get('content', '')[:100]}...")
                    return result
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in chat: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise
    
    async def _handle_streaming_response(self, response: aiohttp.ClientResponse) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming response from Ollama."""
        import json
        
        async for line in response.content:
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    yield data
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON: {line}")
                    continue
    
    async def embeddings(
        self,
        prompt: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate embeddings."""
        # Ensure session is available and reconnect if needed
        if not self.session or self.session.closed:
            await self.connect()

        # Double-check session is still available after connect
        if not self.session:
            raise Exception("Failed to establish Ollama connection")

        model = model or self.default_model
        
        payload = {
            "model": model,
            "prompt": prompt
        }
        
        try:
            logger.debug(f"Generating embeddings with model {model}")
            
            async with self.session.post(f"{self.base_url}/api/embeddings", json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                
                logger.debug(f"Generated embeddings: {len(result.get('embedding', []))} dimensions")
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in embeddings: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in embeddings: {e}")
            raise
    
    async def list_models(self) -> Dict[str, Any]:
        """List available models."""
        # Ensure session is available and reconnect if needed
        if not self.session or self.session.closed:
            await self.connect()

        # Double-check session is still available after connect
        if not self.session:
            raise Exception("Failed to establish Ollama connection")

        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                response.raise_for_status()
                result = await response.json()

                models = [model["name"] for model in result.get("models", [])]
                logger.debug(f"Available models: {models}")

                return result

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in list_models: {e}")
            # Reset session on HTTP errors
            if self.session:
                await self.disconnect()
            raise
        except Exception as e:
            logger.error(f"Error in list_models: {e}")
            # Reset session on any error
            if self.session:
                await self.disconnect()
            raise
    
    async def pull_model(self, model: str) -> Dict[str, Any]:
        """Pull a model."""
        # Ensure session is available and reconnect if needed
        if not self.session or self.session.closed:
            await self.connect()

        # Double-check session is still available after connect
        if not self.session:
            raise Exception("Failed to establish Ollama connection")

        payload = {"name": model}
        
        try:
            logger.info(f"Pulling model: {model}")
            
            async with self.session.post(f"{self.base_url}/api/pull", json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                
                logger.info(f"Model pulled successfully: {model}")
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error in pull_model: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in pull_model: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama server health."""
        # Ensure session is available and reconnect if needed
        if not self.session or self.session.closed:
            await self.connect()

        # Double-check session is still available after connect
        if not self.session:
            return {
                "status": "unhealthy",
                "error": "Failed to establish Ollama connection"
            }

        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "status": "healthy",
                        "models_available": len(result.get("models", [])),
                        "default_model": self.default_model
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
ollama_client = OllamaClient()
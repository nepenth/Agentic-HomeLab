import aiohttp
import asyncio
import threading
from typing import Dict, Any, Optional, List, AsyncGenerator
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("ollama_client")


class OllamaClient:
    """Async client for Ollama API with context-aware session management."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_default_model
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        self._context_sessions: Dict[str, aiohttp.ClientSession] = {}
        self._context_lock = threading.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Create HTTP session."""
        async with self._session_lock:
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

    def get_context_session(self, context_id: str) -> aiohttp.ClientSession:
        """Get or create a context-specific session."""
        with self._context_lock:
            if context_id not in self._context_sessions:
                connector = aiohttp.TCPConnector(
                    limit=50,
                    limit_per_host=20,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )

                timeout = aiohttp.ClientTimeout(
                    total=300,
                    connect=10,
                    sock_read=60
                )

                self._context_sessions[context_id] = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"Content-Type": "application/json"}
                )

                logger.debug(f"Created context session for {context_id}")

            return self._context_sessions[context_id]

    async def cleanup_context_session(self, context_id: str):
        """Clean up a context-specific session."""
        with self._context_lock:
            if context_id in self._context_sessions:
                session = self._context_sessions[context_id]
                if not session.closed:
                    await session.close()
                del self._context_sessions[context_id]
                logger.debug(f"Cleaned up context session for {context_id}")
    
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
        options: Optional[Dict[str, Any]] = None,
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate text completion."""
        # Use context-specific session if provided, otherwise use global session
        if context_id:
            session = self.get_context_session(context_id)
        else:
            # Ensure session is available and reconnect if needed
            if not self.session or self.session.closed:
                await self.connect()
            session = self.session

        # Double-check session is still available after connect
        if not session:
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
            
            async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                
                if stream:
                    streaming_results = await self._handle_streaming_response(response)
                    # Return the last result or aggregate as needed
                    return streaming_results[-1] if streaming_results else {}
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
        options: Optional[Dict[str, Any]] = None,
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Chat completion."""
        # Use context-specific session if provided, otherwise use global session
        if context_id:
            session = self.get_context_session(context_id)
        else:
            # Ensure session is available and reconnect if needed
            if not self.session or self.session.closed:
                await self.connect()
            session = self.session

        # Double-check session is still available after connect
        if not session:
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
            
            async with session.post(f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                
                if stream:
                    streaming_results = await self._handle_streaming_response(response)
                    # Return the last result or aggregate as needed
                    return streaming_results[-1] if streaming_results else {}
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
    
    async def _handle_streaming_response(self, response: aiohttp.ClientResponse) -> List[Dict[str, Any]]:
        """Handle streaming response from Ollama."""
        import json

        results = []
        async for line in response.content:
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    results.append(data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON: {line}")
                    continue
        return results
    
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


class SyncOllamaClient:
    """Synchronous HTTP client for Ollama using requests library."""

    def __init__(self):
        import requests
        self.requests = requests
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_default_model
        self.session = self.requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Synchronous generate method using requests."""
        model = model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        # Add optional parameters
        if "system" in kwargs:
            payload["system"] = kwargs["system"]
        if "template" in kwargs:
            payload["template"] = kwargs["template"]
        if "context" in kwargs:
            payload["context"] = kwargs["context"]
        if "format" in kwargs:
            payload["format"] = kwargs["format"]
        if "options" in kwargs:
            payload["options"] = kwargs["options"]

        try:
            response = self.session.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in sync generate: {e}")
            raise

    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Synchronous chat method using requests."""
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        if "format" in kwargs:
            payload["format"] = kwargs["format"]
        if "options" in kwargs:
            payload["options"] = kwargs["options"]

        try:
            response = self.session.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in sync chat: {e}")
            raise

    def embeddings(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous embeddings method using requests."""
        model = model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt
        }

        try:
            response = self.session.post(f"{self.base_url}/api/embeddings", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in sync embeddings: {e}")
            raise

    def list_models(self) -> Dict[str, Any]:
        """Synchronous list models method using requests."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in sync list_models: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Synchronous health check method using requests."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "healthy",
                    "models_available": len(result.get("models", [])),
                    "default_model": self.default_model
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def pull_model(self, model: str) -> Dict[str, Any]:
        """Synchronous pull model method using requests."""
        payload = {"name": model}

        try:
            response = self.session.post(f"{self.base_url}/api/pull", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in sync pull_model: {e}")
            raise

    def close(self):
        """Close the requests session."""
        if self.session:
            self.session.close()


# Global instances
ollama_client = OllamaClient()
sync_ollama_client = SyncOllamaClient()
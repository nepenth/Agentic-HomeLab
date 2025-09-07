"""
Model Capability Detection and Management Service.

This service detects and manages AI model capabilities from Ollama,
including vision, audio, and embedding models for different processing tasks.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("model_capability_service")


class ModelCapability(Enum):
    """AI model capabilities."""
    TEXT_GENERATION = "text_generation"
    VISION_ANALYSIS = "vision_analysis"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    AUDIO_ANALYSIS = "audio_analysis"
    EMBEDDING_GENERATION = "embedding_generation"
    CODE_GENERATION = "code_generation"
    CHAT_CONVERSATION = "chat_conversation"


class ModelType(Enum):
    """Types of AI models."""
    TEXT_ONLY = "text_only"
    VISION = "vision"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"
    EMBEDDING = "embedding"


@dataclass
class ModelInfo:
    """Information about an AI model."""
    name: str
    model_type: ModelType
    capabilities: Set[ModelCapability]
    size_gb: Optional[float] = None
    quantization: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)
    is_available: bool = True


class ModelCapabilityService:
    """Service for detecting and managing AI model capabilities."""

    def __init__(self):
        self.models_cache: Dict[str, ModelInfo] = {}
        self.capabilities_cache: Dict[ModelCapability, List[str]] = {}
        self.cache_expiry = timedelta(hours=1)  # Cache for 1 hour
        self.last_cache_update: Optional[datetime] = None
        self.logger = get_logger("model_capability_service")

        # Known model patterns for capability detection
        self.vision_model_patterns = [
            'llava', 'bakllava', 'moondream', 'llama-vision',
            'vision', 'clip', 'blip', 'vit'
        ]

        self.audio_model_patterns = [
            'whisper', 'wav2vec', 'hubert', 'audio',
            'speech', 'voice', 'transcribe'
        ]

        self.embedding_model_patterns = [
            'embed', 'embedding', 'sentence-transformer',
            'all-minilm', 'text2vec', 'bge'
        ]

    async def initialize(self):
        """Initialize the model capability service."""
        try:
            await self._refresh_model_capabilities()
            self.logger.info("Model Capability Service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Capability Service: {e}")
            raise

    async def get_available_models(self, capability: Optional[ModelCapability] = None) -> List[ModelInfo]:
        """
        Get available models, optionally filtered by capability.

        Args:
            capability: Filter models by specific capability

        Returns:
            List of available ModelInfo objects
        """
        await self._ensure_cache_fresh()

        if capability:
            model_names = self.capabilities_cache.get(capability, [])
            return [self.models_cache[name] for name in model_names if name in self.models_cache]
        else:
            return list(self.models_cache.values())

    async def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.

        Args:
            model_name: Name of the model

        Returns:
            ModelInfo object or None if not found
        """
        await self._ensure_cache_fresh()
        return self.models_cache.get(model_name)

    async def get_models_by_type(self, model_type: ModelType) -> List[ModelInfo]:
        """
        Get models by type.

        Args:
            model_type: Type of models to retrieve

        Returns:
            List of ModelInfo objects
        """
        await self._ensure_cache_fresh()

        return [model for model in self.models_cache.values()
                if model.model_type == model_type and model.is_available]

    async def get_vision_models(self) -> List[ModelInfo]:
        """Get all available vision-capable models."""
        return await self.get_models_by_type(ModelType.VISION)

    async def get_audio_models(self) -> List[ModelInfo]:
        """Get all available audio-capable models."""
        return await self.get_models_by_type(ModelType.AUDIO)

    async def get_embedding_models(self) -> List[ModelInfo]:
        """Get all available embedding-capable models."""
        return await self.get_models_by_type(ModelType.EMBEDDING)

    async def detect_model_capabilities(self, model_name: str) -> Set[ModelCapability]:
        """
        Detect capabilities of a specific model based on its name and metadata.

        Args:
            model_name: Name of the model to analyze

        Returns:
            Set of detected capabilities
        """
        capabilities = set()

        # Convert to lowercase for pattern matching
        model_lower = model_name.lower()

        # Detect vision capabilities
        if any(pattern in model_lower for pattern in self.vision_model_patterns):
            capabilities.add(ModelCapability.VISION_ANALYSIS)
            capabilities.add(ModelCapability.TEXT_GENERATION)  # Most vision models can also generate text

        # Detect audio capabilities
        if any(pattern in model_lower for pattern in self.audio_model_patterns):
            capabilities.add(ModelCapability.AUDIO_TRANSCRIPTION)
            capabilities.add(ModelCapability.AUDIO_ANALYSIS)

        # Detect embedding capabilities
        if any(pattern in model_lower for pattern in self.embedding_model_patterns):
            capabilities.add(ModelCapability.EMBEDDING_GENERATION)

        # Most models have basic text generation capability
        if not capabilities:
            capabilities.add(ModelCapability.TEXT_GENERATION)
            capabilities.add(ModelCapability.CHAT_CONVERSATION)

        return capabilities

    async def _refresh_model_capabilities(self):
        """Refresh the model capabilities cache from Ollama."""
        try:
            # Get available models from Ollama
            models_response = await ollama_client.list_models()

            if not models_response or 'models' not in models_response:
                self.logger.warning("No models found in Ollama response")
                return

            models_data = models_response['models']
            self.logger.info(f"Found {len(models_data)} models in Ollama")

            # Clear existing cache
            self.models_cache.clear()
            self.capabilities_cache.clear()

            # Process each model
            for model_data in models_data:
                model_name = model_data.get('name', '')
                if not model_name:
                    continue

                # Detect capabilities
                capabilities = await self.detect_model_capabilities(model_name)

                # Determine model type
                model_type = self._determine_model_type(capabilities)

                # Extract size information if available
                size_gb = None
                if 'size' in model_data:
                    # Convert bytes to GB
                    size_gb = model_data['size'] / (1024 ** 3)

                # Create ModelInfo
                model_info = ModelInfo(
                    name=model_name,
                    model_type=model_type,
                    capabilities=capabilities,
                    size_gb=size_gb,
                    quantization=model_data.get('quantization'),
                    last_updated=datetime.now(),
                    is_available=True
                )

                self.models_cache[model_name] = model_info

                # Update capabilities cache
                for capability in capabilities:
                    if capability not in self.capabilities_cache:
                        self.capabilities_cache[capability] = []
                    self.capabilities_cache[capability].append(model_name)

            self.last_cache_update = datetime.now()
            self.logger.info(f"Refreshed capabilities for {len(self.models_cache)} models")

        except Exception as e:
            self.logger.error(f"Failed to refresh model capabilities: {e}")
            raise

    def _determine_model_type(self, capabilities: Set[ModelCapability]) -> ModelType:
        """Determine model type based on capabilities."""
        if ModelCapability.VISION_ANALYSIS in capabilities:
            if ModelCapability.AUDIO_TRANSCRIPTION in capabilities:
                return ModelType.MULTIMODAL
            else:
                return ModelType.VISION
        elif ModelCapability.AUDIO_TRANSCRIPTION in capabilities:
            return ModelType.AUDIO
        elif ModelCapability.EMBEDDING_GENERATION in capabilities:
            return ModelType.EMBEDDING
        else:
            return ModelType.TEXT_ONLY

    async def _ensure_cache_fresh(self):
        """Ensure the cache is fresh, refresh if needed."""
        if (self.last_cache_update is None or
            datetime.now() - self.last_cache_update > self.cache_expiry):
            await self._refresh_model_capabilities()

    async def get_capability_stats(self) -> Dict[str, Any]:
        """Get statistics about model capabilities."""
        await self._ensure_cache_fresh()

        stats = {
            'total_models': len(self.models_cache),
            'model_types': {},
            'capabilities': {},
            'last_updated': self.last_cache_update.isoformat() if self.last_cache_update else None
        }

        # Count model types
        for model in self.models_cache.values():
            model_type = model.model_type.value
            stats['model_types'][model_type] = stats['model_types'].get(model_type, 0) + 1

        # Count capabilities
        for capability, models in self.capabilities_cache.items():
            stats['capabilities'][capability.value] = len(models)

        return stats

    async def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available."""
        model_info = await self.get_model_info(model_name)
        return model_info is not None and model_info.is_available

    async def get_best_model_for_task(self, capability: ModelCapability) -> Optional[str]:
        """
        Get the best available model for a specific capability.
        Uses simple heuristics to select the most appropriate model.

        Args:
            capability: The capability needed

        Returns:
            Best model name or None if no suitable model found
        """
        await self._ensure_cache_fresh()

        candidates = self.capabilities_cache.get(capability, [])
        if not candidates:
            return None

        # For now, return the first available model
        # In the future, this could use more sophisticated selection logic
        # based on model size, performance, etc.
        for model_name in candidates:
            if model_name in self.models_cache and self.models_cache[model_name].is_available:
                return model_name

        return None


# Global instance
model_capability_service = ModelCapabilityService()
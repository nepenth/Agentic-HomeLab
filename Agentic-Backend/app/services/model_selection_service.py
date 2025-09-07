"""
Dynamic Model Selection System for intelligent AI model management.

This module provides comprehensive model registry, selection, and performance tracking
capabilities for Ollama models with content-aware selection algorithms.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from enum import Enum
import json

from app.config import settings
from app.services.ollama_client import OllamaClient
from app.utils.logging import get_logger

logger = get_logger("model_selection")


class TaskType(Enum):
    """Supported task types for model selection."""
    TEXT_GENERATION = "text_generation"
    TEXT_ANALYSIS = "text_analysis"
    TEXT_SUMMARIZATION = "text_summarization"
    QUESTION_ANSWERING = "question_answering"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    IMAGE_ANALYSIS = "image_analysis"
    IMAGE_CAPTIONING = "image_captioning"
    IMAGE_CLASSIFICATION = "image_classification"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    AUDIO_ANALYSIS = "audio_analysis"
    EMBEDDING_GENERATION = "embedding_generation"
    SEMANTIC_SEARCH = "semantic_search"
    MULTIMODAL_ANALYSIS = "multimodal_analysis"


class ContentType(Enum):
    """Supported content types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"
    CODE = "code"
    STRUCTURED = "structured"


class ModelCapability(Enum):
    """Model capabilities."""
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    EMBEDDING = "embedding"
    CODE = "code"
    MULTIMODAL = "multimodal"


@dataclass
class ModelInfo:
    """Comprehensive model information."""
    name: str
    capabilities: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    version: str = ""
    size_mb: int = 0
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_available: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelSelection:
    """Model selection result."""
    model_name: str
    model_info: ModelInfo
    selection_reason: str
    confidence_score: float
    fallback_models: List[str] = field(default_factory=list)
    performance_prediction: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Model performance tracking."""
    model_name: str
    task_type: str
    content_type: str
    success_rate: float
    average_response_time_ms: float
    average_tokens_per_second: float
    error_count: int
    total_requests: int
    last_updated: datetime
    performance_score: float = 0.0


@dataclass
class ProcessingTask:
    """Task specification for model selection."""
    task_type: TaskType
    content_type: ContentType
    requirements: Dict[str, Any] = field(default_factory=dict)
    priority: str = "balanced"  # 'speed', 'quality', 'balanced'
    max_tokens: Optional[int] = None
    context_length: Optional[int] = None


class ModelRegistry:
    """Registry for managing and discovering AI models."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama_client = ollama_client or OllamaClient()
        self.models: Dict[str, ModelInfo] = {}
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.last_discovery: Optional[datetime] = None
        self.discovery_interval = timedelta(minutes=5)  # Refresh every 5 minutes

    async def discover_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """Automatically discover available Ollama models."""
        now = datetime.now()

        # Check if we need to refresh
        if not force_refresh and self.last_discovery:
            if now - self.last_discovery < self.discovery_interval:
                return list(self.models.values())

        try:
            async with self.ollama_client:
                response = await self.ollama_client.list_models()

                if 'models' not in response:
                    logger.warning("No models found in Ollama response")
                    return []

                discovered_models = []
                for model_data in response['models']:
                    model_name = model_data.get('name', '')
                    if not model_name:
                        continue

                    # Get detailed model info
                    model_info = await self._analyze_model_capabilities(model_name, model_data)
                    self.models[model_name] = model_info
                    discovered_models.append(model_info)

                self.last_discovery = now
                logger.info(f"Discovered {len(discovered_models)} models")
                return discovered_models

        except Exception as e:
            logger.error(f"Failed to discover models: {e}")
            return list(self.models.values())

    async def _analyze_model_capabilities(self, model_name: str, model_data: Dict[str, Any]) -> ModelInfo:
        """Analyze model capabilities through testing."""
        capabilities = []
        performance_metrics = {}

        # Extract basic info
        size_mb = model_data.get('size', 0) // (1024 * 1024)  # Convert bytes to MB
        modified_at = model_data.get('modified_at', '')

        # Determine capabilities based on model name patterns
        name_lower = model_name.lower()

        if any(keyword in name_lower for keyword in ['llama', 'mistral', 'codellama', 'qwen']):
            capabilities.append(ModelCapability.TEXT.value)

        if any(keyword in name_lower for keyword in ['llava', 'moondream', 'bakllava']):
            capabilities.append(ModelCapability.VISION.value)

        if any(keyword in name_lower for keyword in ['whisper']):
            capabilities.append(ModelCapability.AUDIO.value)

        if any(keyword in name_lower for keyword in ['embed', 'nomic', 'all-minilm']):
            capabilities.append(ModelCapability.EMBEDDING.value)

        if 'codellama' in name_lower or 'code' in name_lower:
            capabilities.append(ModelCapability.CODE.value)

        # If model has multiple capabilities, it's multimodal
        if len(capabilities) > 1:
            capabilities.append(ModelCapability.MULTIMODAL.value)

        # Test model performance with a simple prompt
        try:
            performance_metrics = await self._test_model_performance(model_name)
        except Exception as e:
            logger.warning(f"Failed to test performance for {model_name}: {e}")
            performance_metrics = {
                'response_time_ms': 1000.0,  # Default fallback
                'tokens_per_second': 10.0,
                'success_rate': 0.5
            }

        return ModelInfo(
            name=model_name,
            capabilities=capabilities,
            performance_metrics=performance_metrics,
            version=self._extract_version(model_name),
            size_mb=size_mb,
            last_used=None,
            created_at=self._parse_datetime(modified_at),
            is_available=True,
            tags=self._generate_tags(model_name, capabilities),
            metadata=model_data
        )

    def _extract_version(self, model_name: str) -> str:
        """Extract version from model name."""
        # Handle common versioning patterns
        if ':' in model_name:
            return model_name.split(':')[-1]
        return "latest"

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string."""
        try:
            # Handle ISO format
            if date_str.endswith('Z'):
                return datetime.fromisoformat(date_str[:-1])
            return datetime.fromisoformat(date_str)
        except:
            return None

    def _generate_tags(self, model_name: str, capabilities: List[str]) -> List[str]:
        """Generate tags based on model characteristics."""
        tags = []

        name_lower = model_name.lower()

        # Size-based tags
        if '7b' in name_lower or '8b' in name_lower:
            tags.append('small')
        elif '13b' in name_lower or '14b' in name_lower:
            tags.append('medium')
        elif '30b' in name_lower or '34b' in name_lower or '70b' in name_lower:
            tags.append('large')

        # Capability-based tags
        if ModelCapability.TEXT.value in capabilities:
            tags.append('text')
        if ModelCapability.VISION.value in capabilities:
            tags.append('vision')
        if ModelCapability.AUDIO.value in capabilities:
            tags.append('audio')
        if ModelCapability.EMBEDDING.value in capabilities:
            tags.append('embedding')

        # Provider tags
        if 'llama' in name_lower:
            tags.append('llama')
        elif 'mistral' in name_lower:
            tags.append('mistral')
        elif 'codellama' in name_lower:
            tags.append('code')

        return tags

    async def _test_model_performance(self, model_name: str) -> Dict[str, float]:
        """Test model performance with a simple task."""
        test_prompt = "Hello, how are you?"
        start_time = time.time()

        try:
            async with self.ollama_client:
                response = await self.ollama_client.generate(
                    prompt=test_prompt,
                    model=model_name,
                    options={"num_predict": 20}  # Limit response length
                )

            response_time = (time.time() - start_time) * 1000  # Convert to ms
            response_text = response.get('response', '')
            token_count = len(response_text.split())

            tokens_per_second = token_count / (response_time / 1000) if response_time > 0 else 0

            return {
                'response_time_ms': response_time,
                'tokens_per_second': tokens_per_second,
                'success_rate': 1.0
            }

        except Exception as e:
            logger.warning(f"Performance test failed for {model_name}: {e}")
            return {
                'response_time_ms': 5000.0,  # High default for failed models
                'tokens_per_second': 0.0,
                'success_rate': 0.0
            }

    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        """Get model information by name."""
        return self.models.get(model_name)

    def get_models_by_capability(self, capability: str) -> List[ModelInfo]:
        """Get all models with specific capability."""
        return [
            model for model in self.models.values()
            if capability in model.capabilities
        ]

    def get_available_models(self) -> List[ModelInfo]:
        """Get all available models."""
        return [model for model in self.models.values() if model.is_available]


class ModelSelector:
    """Intelligent model selection engine."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.selection_cache: Dict[str, ModelSelection] = {}
        self.cache_ttl = timedelta(minutes=10)

    async def select_for_task(self, task: ProcessingTask) -> ModelSelection:
        """Select optimal model based on task characteristics."""
        # Create cache key
        cache_key = self._create_cache_key(task)

        # Check cache
        if cache_key in self.selection_cache:
            cached_selection = self.selection_cache[cache_key]
            # Check if cache is still valid
            if datetime.now() - cached_selection.model_info.created_at < self.cache_ttl:
                return cached_selection

        # Discover models if needed
        await self.registry.discover_models()

        # Find suitable models
        candidates = await self._find_candidates(task)

        if not candidates:
            raise ValueError(f"No suitable models found for task: {task.task_type.value}")

        # Score and rank candidates
        scored_candidates = await self._score_candidates(candidates, task)

        # Select best model
        best_candidate = max(scored_candidates, key=lambda x: x[1])
        model_info, score = best_candidate

        # Generate fallback models
        fallback_models = [
            m[0].name for m in sorted(scored_candidates[1:], key=lambda x: x[1], reverse=True)[:3]
        ]

        # Create selection result
        selection = ModelSelection(
            model_name=model_info.name,
            model_info=model_info,
            selection_reason=self._generate_selection_reason(task, model_info, score),
            confidence_score=min(score / 100.0, 1.0),
            fallback_models=fallback_models,
            performance_prediction=self._predict_performance(model_info, task)
        )

        # Cache selection
        self.selection_cache[cache_key] = selection

        # Update model usage
        model_info.last_used = datetime.now()

        logger.info(f"Selected model {model_info.name} for {task.task_type.value} (score: {score:.1f})")
        return selection

    def _create_cache_key(self, task: ProcessingTask) -> str:
        """Create cache key for task."""
        return f"{task.task_type.value}_{task.content_type.value}_{task.priority}_{task.max_tokens or 0}"

    async def _find_candidates(self, task: ProcessingTask) -> List[ModelInfo]:
        """Find candidate models for the task."""
        candidates = []

        # Get all available models
        available_models = self.registry.get_available_models()

        for model in available_models:
            if self._is_model_suitable(model, task):
                candidates.append(model)

        return candidates

    def _is_model_suitable(self, model: ModelInfo, task: ProcessingTask) -> bool:
        """Check if model is suitable for task."""
        # Check content type compatibility
        content_capability_map = {
            ContentType.TEXT: [ModelCapability.TEXT.value],
            ContentType.IMAGE: [ModelCapability.VISION.value],
            ContentType.AUDIO: [ModelCapability.AUDIO.value],
            ContentType.CODE: [ModelCapability.CODE.value, ModelCapability.TEXT.value],
            ContentType.MULTIMODAL: [ModelCapability.MULTIMODAL.value],
        }

        required_capabilities = content_capability_map.get(task.content_type, [])
        if not required_capabilities:
            return True

        # Check if model has required capabilities
        has_required = any(cap in model.capabilities for cap in required_capabilities)

        # Special handling for embedding tasks
        if task.task_type == TaskType.EMBEDDING_GENERATION:
            has_required = ModelCapability.EMBEDDING.value in model.capabilities

        return has_required

    async def _score_candidates(
        self,
        candidates: List[ModelInfo],
        task: ProcessingTask
    ) -> List[Tuple[ModelInfo, float]]:
        """Score candidate models based on task requirements."""
        scored = []

        for model in candidates:
            score = await self._calculate_model_score(model, task)
            scored.append((model, score))

        return scored

    async def _calculate_model_score(self, model: ModelInfo, task: ProcessingTask) -> float:
        """Calculate comprehensive score for model-task combination."""
        score = 0.0

        # Base capability score (40 points)
        capability_score = self._calculate_capability_score(model, task)
        score += capability_score * 40

        # Performance score (30 points)
        performance_score = self._calculate_performance_score(model, task)
        score += performance_score * 30

        # Size efficiency score (15 points)
        size_score = self._calculate_size_score(model, task)
        score += size_score * 15

        # Recency score (10 points) - prefer recently used models
        recency_score = self._calculate_recency_score(model)
        score += recency_score * 10

        # Priority adjustments
        if task.priority == "speed":
            # Favor faster models
            score += model.performance_metrics.get('tokens_per_second', 0) * 2
        elif task.priority == "quality":
            # Favor larger models
            score += (model.size_mb / 1000) * 10  # Bonus for larger models

        return min(score, 100.0)  # Cap at 100

    def _calculate_capability_score(self, model: ModelInfo, task: ProcessingTask) -> float:
        """Calculate capability match score."""
        # Perfect match for required capabilities
        if task.content_type == ContentType.TEXT and ModelCapability.TEXT.value in model.capabilities:
            return 1.0
        elif task.content_type == ContentType.IMAGE and ModelCapability.VISION.value in model.capabilities:
            return 1.0
        elif task.content_type == ContentType.AUDIO and ModelCapability.AUDIO.value in model.capabilities:
            return 1.0
        elif task.task_type == TaskType.EMBEDDING_GENERATION and ModelCapability.EMBEDDING.value in model.capabilities:
            return 1.0

        # Partial matches
        if ModelCapability.MULTIMODAL.value in model.capabilities:
            return 0.8

        return 0.5  # Basic compatibility

    def _calculate_performance_score(self, model: ModelInfo, task: ProcessingTask) -> float:
        """Calculate performance score."""
        metrics = model.performance_metrics

        # Response time score (faster is better)
        response_time = metrics.get('response_time_ms', 2000)
        time_score = max(0, 1.0 - (response_time / 5000))  # Normalize to 5s

        # Success rate score
        success_rate = metrics.get('success_rate', 0.8)
        success_score = success_rate

        # Tokens per second score
        tokens_per_sec = metrics.get('tokens_per_second', 10)
        speed_score = min(tokens_per_sec / 50, 1.0)  # Cap at 50 tokens/sec

        return (time_score + success_score + speed_score) / 3

    def _calculate_size_score(self, model: ModelInfo, task: ProcessingTask) -> float:
        """Calculate size efficiency score."""
        size_mb = model.size_mb

        # For speed priority, prefer smaller models
        if task.priority == "speed":
            if size_mb < 2000:  # < 2GB
                return 1.0
            elif size_mb < 5000:  # < 5GB
                return 0.7
            else:
                return 0.4

        # For quality priority, prefer larger models
        elif task.priority == "quality":
            if size_mb > 10000:  # > 10GB
                return 1.0
            elif size_mb > 5000:  # > 5GB
                return 0.8
            else:
                return 0.6

        # Balanced approach
        else:
            if 2000 <= size_mb <= 8000:  # 2-8GB sweet spot
                return 1.0
            elif size_mb < 2000 or size_mb > 15000:
                return 0.6
            else:
                return 0.8

    def _calculate_recency_score(self, model: ModelInfo) -> float:
        """Calculate recency score based on last usage."""
        if not model.last_used:
            return 0.5  # Neutral score for unused models

        hours_since_use = (datetime.now() - model.last_used).total_seconds() / 3600

        if hours_since_use < 1:  # Used within last hour
            return 1.0
        elif hours_since_use < 24:  # Used within last day
            return 0.8
        elif hours_since_use < 168:  # Used within last week
            return 0.6
        else:
            return 0.3

    def _generate_selection_reason(self, task: ProcessingTask, model: ModelInfo, score: float) -> str:
        """Generate human-readable selection reason."""
        reasons = []

        if task.priority == "speed":
            reasons.append("Optimized for speed")
        elif task.priority == "quality":
            reasons.append("Optimized for quality")
        else:
            reasons.append("Balanced performance")

        if model.size_mb < 2000:
            reasons.append("Lightweight model")
        elif model.size_mb > 10000:
            reasons.append("High-capacity model")

        capabilities = [cap for cap in model.capabilities if cap != ModelCapability.MULTIMODAL.value]
        if capabilities:
            reasons.append(f"Supports: {', '.join(capabilities)}")

        return f"Selected {model.name} ({', '.join(reasons)}) with score {score:.1f}/100"

    def _predict_performance(self, model: ModelInfo, task: ProcessingTask) -> Dict[str, Any]:
        """Predict performance for the selected model-task combination."""
        metrics = model.performance_metrics

        return {
            'estimated_response_time_ms': metrics.get('response_time_ms', 2000),
            'estimated_tokens_per_second': metrics.get('tokens_per_second', 10),
            'expected_success_rate': metrics.get('success_rate', 0.8),
            'model_size_mb': model.size_mb,
            'capabilities': model.capabilities
        }

    async def get_fallback_models(self, primary_model: str, task: ProcessingTask) -> List[str]:
        """Get fallback model options."""
        try:
            selection = await self.select_for_task(task)
            fallbacks = selection.fallback_models

            # Remove the primary model if it's in fallbacks
            return [m for m in fallbacks if m != primary_model]
        except:
            return []


class ModelPerformanceTracker:
    """Track and analyze model performance over time."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.performance_data: Dict[str, List[PerformanceMetrics]] = {}

    async def track_performance(
        self,
        model_name: str,
        task_type: TaskType,
        content_type: ContentType,
        metrics: PerformanceMetrics
    ) -> None:
        """Track model performance metrics."""
        if model_name not in self.performance_data:
            self.performance_data[model_name] = []

        self.performance_data[model_name].append(metrics)

        # Update model info in registry
        model_info = self.registry.get_model(model_name)
        if model_info:
            model_info.performance_metrics.update({
                'response_time_ms': metrics.average_response_time_ms,
                'tokens_per_second': metrics.average_tokens_per_second,
                'success_rate': metrics.success_rate
            })

        logger.debug(f"Tracked performance for {model_name}: {metrics.success_rate:.2f} success rate")

    def get_model_performance_history(self, model_name: str, limit: int = 100) -> List[PerformanceMetrics]:
        """Get performance history for a model."""
        return self.performance_data.get(model_name, [])[-limit:]

    def get_performance_summary(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get aggregated performance summary for a model."""
        history = self.get_model_performance_history(model_name)

        if not history:
            return None

        total_requests = sum(m.total_requests for m in history)
        total_errors = sum(m.error_count for m in history)
        avg_response_time = sum(m.average_response_time_ms for m in history) / len(history)
        avg_tokens_per_sec = sum(m.average_tokens_per_second for m in history) / len(history)

        return {
            'model_name': model_name,
            'total_requests': total_requests,
            'success_rate': (total_requests - total_errors) / total_requests if total_requests > 0 else 0,
            'average_response_time_ms': avg_response_time,
            'average_tokens_per_second': avg_tokens_per_sec,
            'performance_score': self._calculate_performance_score(avg_response_time, avg_tokens_per_sec)
        }

    def _calculate_performance_score(self, avg_response_time: float, avg_tokens_per_sec: float) -> float:
        """Calculate overall performance score."""
        # Normalize response time (lower is better)
        time_score = max(0, 1.0 - (avg_response_time / 5000))

        # Normalize tokens per second (higher is better)
        speed_score = min(avg_tokens_per_sec / 50, 1.0)

        return (time_score + speed_score) / 2


# Global instances
model_registry = ModelRegistry()
model_selector = ModelSelector(model_registry)
performance_tracker = ModelPerformanceTracker(model_registry)
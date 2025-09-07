"""
API routes for Dynamic Model Selection System.

This module provides REST endpoints for intelligent AI model selection,
performance tracking, and model registry management.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.model_selection_service import (
    model_registry,
    model_selector,
    performance_tracker,
    TaskType,
    ContentType,
    ProcessingTask,
    ModelInfo,
    ModelSelection
)
from app.utils.logging import get_logger

logger = get_logger("model_selection_routes")

router = APIRouter(prefix="/models", tags=["Model Selection"])


# Pydantic models for request/response
class ModelInfoModel(BaseModel):
    """Model information response."""
    name: str
    capabilities: List[str]
    performance_metrics: Dict[str, float]
    version: str
    size_mb: int
    last_used: Optional[datetime]
    created_at: Optional[datetime]
    is_available: bool
    tags: List[str]


class ModelSelectionRequest(BaseModel):
    """Model selection request."""
    task_type: str = Field(..., description="Type of task (text_generation, image_analysis, etc.)")
    content_type: str = Field(..., description="Type of content (text, image, audio, etc.)")
    priority: Optional[str] = Field(default="balanced", description="Selection priority (speed, quality, balanced)")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens for text generation")
    context_length: Optional[int] = Field(default=None, description="Context length requirement")
    requirements: Optional[Dict[str, Any]] = Field(default=None, description="Additional requirements")


class ModelSelectionResponse(BaseModel):
    """Model selection response."""
    selected_model: str
    model_info: ModelInfoModel
    selection_reason: str
    confidence_score: float
    fallback_models: List[str]
    performance_prediction: Dict[str, Any]


class PerformanceMetricsModel(BaseModel):
    """Performance metrics response."""
    model_name: str
    task_type: str
    content_type: str
    success_rate: float
    average_response_time_ms: float
    average_tokens_per_second: float
    error_count: int
    total_requests: int
    last_updated: datetime
    performance_score: float


class ModelStatsModel(BaseModel):
    """Model statistics response."""
    model_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_processing_time_ms: float
    average_tokens_per_request: float
    success_rate: float
    task_distribution: Dict[str, int]
    content_type_distribution: Dict[str, int]


@router.get("/available", response_model=List[ModelInfoModel])
async def get_available_models() -> List[ModelInfoModel]:
    """
    List all available models with their capabilities.

    Returns comprehensive information about all available Ollama models
    including their capabilities, performance metrics, and metadata.
    """
    try:
        models = await model_registry.discover_models()

        response_models = []
        for model in models:
            response_models.append(ModelInfoModel(
                name=model.name,
                capabilities=model.capabilities,
                performance_metrics=model.performance_metrics,
                version=model.version,
                size_mb=model.size_mb,
                last_used=model.last_used,
                created_at=model.created_at,
                is_available=model.is_available,
                tags=model.tags
            ))

        logger.info(f"Retrieved {len(response_models)} available models")
        return response_models

    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available models: {str(e)}")


@router.post("/select", response_model=ModelSelectionResponse)
async def select_model(request: ModelSelectionRequest) -> ModelSelectionResponse:
    """
    Select the optimal model for a given task.

    This endpoint uses intelligent algorithms to select the best AI model
    based on task requirements, content type, and performance metrics.
    """
    try:
        # Convert string enums to actual enums
        try:
            task_type = TaskType(request.task_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid task_type: {request.task_type}")

        try:
            content_type = ContentType(request.content_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid content_type: {request.content_type}")

        # Create processing task
        task = ProcessingTask(
            task_type=task_type,
            content_type=content_type,
            priority=request.priority or "balanced",
            max_tokens=request.max_tokens,
            context_length=request.context_length,
            requirements=request.requirements or {}
        )

        # Select optimal model
        selection = await model_selector.select_for_task(task)

        # Convert to response model
        model_info_response = ModelInfoModel(
            name=selection.model_info.name,
            capabilities=selection.model_info.capabilities,
            performance_metrics=selection.model_info.performance_metrics,
            version=selection.model_info.version,
            size_mb=selection.model_info.size_mb,
            last_used=selection.model_info.last_used,
            created_at=selection.model_info.created_at,
            is_available=selection.model_info.is_available,
            tags=selection.model_info.tags
        )

        response = ModelSelectionResponse(
            selected_model=selection.model_name,
            model_info=model_info_response,
            selection_reason=selection.selection_reason,
            confidence_score=selection.confidence_score,
            fallback_models=selection.fallback_models,
            performance_prediction=selection.performance_prediction
        )

        logger.info(f"Selected model {selection.model_name} for {task_type.value} task")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to select model: {str(e)}")


@router.get("/performance", response_model=List[PerformanceMetricsModel])
async def get_model_performance(
    task_type: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 50
) -> List[PerformanceMetricsModel]:
    """
    Get model performance metrics.

    Returns performance metrics for models, optionally filtered by task type
    and content type. Metrics include success rates, response times, and usage statistics.
    """
    try:
        # Get all available models
        models = await model_registry.discover_models()

        performance_data = []
        for model in models:
            # Get performance history for this model
            history = performance_tracker.get_model_performance_history(model.name, limit=limit)

            for metrics in history:
                # Apply filters
                if task_type and metrics.task_type != task_type:
                    continue
                if content_type and metrics.content_type != content_type:
                    continue

                performance_data.append(PerformanceMetricsModel(
                    model_name=metrics.model_name,
                    task_type=metrics.task_type,
                    content_type=metrics.content_type,
                    success_rate=metrics.success_rate,
                    average_response_time_ms=metrics.average_response_time_ms,
                    average_tokens_per_second=metrics.average_tokens_per_second,
                    error_count=metrics.error_count,
                    total_requests=metrics.total_requests,
                    last_updated=metrics.last_updated,
                    performance_score=metrics.performance_score
                ))

        # Sort by performance score (descending)
        performance_data.sort(key=lambda x: x.performance_score, reverse=True)

        logger.info(f"Retrieved performance metrics for {len(performance_data)} model-task combinations")
        return performance_data[:limit]

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/{model_name}/stats", response_model=ModelStatsModel)
async def get_model_stats(model_name: str) -> ModelStatsModel:
    """
    Get detailed statistics for a specific model.

    Returns comprehensive usage statistics and performance metrics
    for the specified model across all tasks and content types.
    """
    try:
        # Get model performance summary
        summary = performance_tracker.get_model_performance_summary(model_name)

        if not summary:
            raise HTTPException(status_code=404, detail=f"No performance data found for model: {model_name}")

        response = ModelStatsModel(
            model_name=summary['model_name'],
            total_requests=summary['total_requests'],
            successful_requests=int(summary['total_requests'] * summary['success_rate']),
            failed_requests=int(summary['total_requests'] * (1 - summary['success_rate'])),
            average_processing_time_ms=summary['average_response_time_ms'],
            average_tokens_per_request=summary['average_tokens_per_request'],
            success_rate=summary['success_rate'],
            task_distribution=summary['task_distribution'],
            content_type_distribution=summary['content_type_distribution']
        )

        logger.info(f"Retrieved statistics for model {model_name}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model stats: {str(e)}")


@router.post("/refresh")
async def refresh_model_registry(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Refresh the model registry.

    Forces a refresh of the model registry to discover new models
    and update capabilities. This operation runs in the background.
    """
    try:
        # Start background refresh
        background_tasks.add_task(model_registry.discover_models, force_refresh=True)

        response = {
            "message": "Model registry refresh initiated",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }

        logger.info("Model registry refresh initiated")
        return response

    except Exception as e:
        logger.error(f"Failed to initiate model registry refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh model registry: {str(e)}")


@router.get("/capabilities")
async def get_model_capabilities() -> Dict[str, Any]:
    """
    Get available model capabilities.

    Returns all available model capabilities and which models support them.
    Useful for understanding what tasks can be performed.
    """
    try:
        models = await model_registry.discover_models()

        capabilities = {}
        for model in models:
            for capability in model.capabilities:
                if capability not in capabilities:
                    capabilities[capability] = []
                capabilities[capability].append(model.name)

        # Sort model lists
        for capability in capabilities:
            capabilities[capability].sort()

        response = {
            "capabilities": capabilities,
            "total_models": len(models),
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get model capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model capabilities: {str(e)}")


@router.get("/recommendations")
async def get_model_recommendations(
    task_type: Optional[str] = None,
    content_type: Optional[str] = None,
    priority: str = "balanced"
) -> Dict[str, Any]:
    """
    Get model recommendations for specific use cases.

    Returns recommended models for common use cases and scenarios.
    """
    try:
        recommendations = {
            "text_generation": {
                "fast": ["llama2:7b", "mistral:7b"],
                "quality": ["llama2:13b", "codellama:13b"],
                "balanced": ["llama2:13b", "mistral:7b"]
            },
            "image_analysis": {
                "fast": ["moondream:1.8b"],
                "quality": ["llava:13b", "bakllava:7b"],
                "balanced": ["llava:7b", "moondream:1.8b"]
            },
            "code_generation": {
                "fast": ["codellama:7b"],
                "quality": ["codellama:13b", "codellama:34b"],
                "balanced": ["codellama:13b"]
            },
            "embedding_generation": {
                "fast": ["nomic-embed-text"],
                "quality": ["nomic-embed-text"],
                "balanced": ["nomic-embed-text"]
            }
        }

        if task_type and content_type:
            # Specific recommendation
            task_key = f"{content_type}_{task_type.split('_')[-1]}"  # e.g., "text_generation"
            if task_key in recommendations:
                recommended_models = recommendations[task_key].get(priority, [])
            else:
                recommended_models = []
        elif task_type:
            # Task-specific recommendations
            if task_type in recommendations:
                recommended_models = recommendations[task_type].get(priority, [])
            else:
                recommended_models = []
        else:
            # General recommendations
            recommended_models = ["llama2:13b", "codellama:13b", "llava:7b"]

        # Verify models are available
        available_models = await model_registry.discover_models()
        available_names = [model.name for model in available_models]
        verified_models = [model for model in recommended_models if model in available_names]

        response = {
            "recommendations": verified_models,
            "priority": priority,
            "task_type": task_type,
            "content_type": content_type,
            "total_available": len(available_models),
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Failed to get model recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")
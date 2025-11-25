"""
Global API Routes.

This module provides global API endpoints that can be used across multiple workflows
and components, such as model management, utilities, and shared resources.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, Any, List
from datetime import datetime

router = APIRouter()


# Mock data for models - in a real implementation, this would come from Ollama
MOCK_MODELS = [
    {
        "name": "qwen3",
        "display_name": "Qwen 3",
        "description": "Advanced general-purpose AI model",
        "capabilities": ["text", "chat", "code"],
        "recommended": True,
        "ranking_score": 850
    },
    {
        "name": "deepseek-r1",
        "display_name": "DeepSeek R1",
        "description": "Powerful reasoning model",
        "capabilities": ["text", "chat", "reasoning"],
        "recommended": True,
        "ranking_score": 800
    },
    {
        "name": "deepseek-ocr",
        "display_name": "DeepSeek OCR",
        "description": "Advanced OCR model optimized for document text extraction",
        "capabilities": ["vision", "ocr", "text"],
        "recommended": True,
        "ranking_score": 750
    },
    {
        "name": "qwen2.5",
        "display_name": "Qwen 2.5",
        "description": "Versatile AI model for various tasks",
        "capabilities": ["text", "chat"],
        "recommended": False,
        "ranking_score": 720
    },
    {
        "name": "phi4",
        "display_name": "Phi 4",
        "description": "Efficient coding and reasoning model",
        "capabilities": ["text", "chat", "code"],
        "recommended": False,
        "ranking_score": 700
    },
    {
        "name": "mistral-small3.1",
        "display_name": "Mistral Small 3.1",
        "description": "Lightweight and efficient model",
        "capabilities": ["text", "chat"],
        "recommended": False,
        "ranking_score": 650
    }
]


@router.get("/models/rich")
async def get_available_models_rich(capability_filter: Optional[str] = Query(None, description="Filter models by capability (e.g., 'vision', 'chat', 'code')")) -> Dict[str, Any]:
    """
    Get comprehensive model information with optional capability filtering.

    This global endpoint provides model data that can be used across all workflows
    and components in the system.

    Args:
        capability_filter: Optional filter for models with specific capabilities

    Returns:
        Dict containing models list and metadata
    """
    try:
        # Start with all models
        filtered_models = MOCK_MODELS.copy()

        # Apply capability filter if specified
        if capability_filter:
            filtered_models = [
                model for model in filtered_models
                if capability_filter in model["capabilities"]
            ]

        # Sort by ranking score (highest first)
        filtered_models.sort(key=lambda x: x["ranking_score"], reverse=True)

        # Group models by capability for better organization
        model_groups = {}
        ungrouped_models = []

        for model in filtered_models:
            # Simple grouping logic
            primary_capability = model["capabilities"][0] if model["capabilities"] else "general"

            if primary_capability not in model_groups:
                model_groups[primary_capability] = []

            model_groups[primary_capability].append(model)

        return {
            "models": filtered_models,  # Flat list for frontend compatibility
            "model_groups": model_groups,  # Grouped data for future use
            "ungrouped_models": filtered_models,  # Same as models for now
            "default_model": "qwen3",
            "total_available": len(filtered_models),
            "filtered_out": len(MOCK_MODELS) - len(filtered_models),
            "capability_filter": capability_filter,
            "groups_count": len(model_groups),
            "ungrouped_count": len(filtered_models),
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        # Return a basic error response
        return {
            "models": [],
            "model_groups": {},
            "ungrouped_models": [],
            "default_model": "qwen3",
            "error": str(e),
            "total_available": 0,
            "filtered_out": 0,
            "capability_filter": capability_filter,
            "groups_count": 0,
            "ungrouped_count": 0,
            "last_updated": datetime.now().isoformat()
        }


@router.get("/health")
async def get_global_health() -> Dict[str, Any]:
    """Get global system health status."""
    return {
        "status": "healthy",
        "message": "Global routes are working",
        "timestamp": datetime.now().isoformat()
    }
"""
Global API Routes.

This module provides global API endpoints that can be used across multiple workflows
and components, such as model management, utilities, and shared resources.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.services.ollama_client import ollama_client

router = APIRouter()


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
        # Get all available models from Ollama
        ollama_response = await ollama_client.list_models()

        # Convert Ollama models to our format
        all_models = []
        for model in ollama_response.get("models", []):
            model_name = model.get("name", "")
            model_details = model.get("details", {})
            model_family = model_details.get("family", "").lower()
            model_families = model_details.get("families", [])

            # Determine capabilities based on model family and name
            capabilities = ["text", "chat"]  # Default capabilities

            # Check for vision capabilities
            model_families_list = model_families or []
            is_vision_capable = (
                # Known vision model families
                any(family in ['mllama', 'llava', 'qwen25vl', 'deepseekocr'] for family in [model_family] + model_families_list) or
                # Models with vision in name
                'vision' in model_name.lower() or 'ocr' in model_name.lower() or
                # Specific known vision models
                any(vision_model in model_name.lower() for vision_model in [
                    'llama3.2-vision', 'qwen2.5vl', 'llava', 'deepseek-ocr'
                ])
            )


            if is_vision_capable:
                capabilities.extend(["vision", "ocr", "image-analysis"])

            # Check for coding capabilities
            if any(keyword in model_name.lower() for keyword in ['coder', 'code', 'phi']):
                capabilities.append("code")

            # Check for reasoning capabilities
            if any(keyword in model_name.lower() for keyword in ['r1', 'reasoning', 'think']):
                capabilities.append("reasoning")

            # Remove duplicates
            capabilities = list(set(capabilities))

            # Determine ranking score based on model characteristics
            ranking_score = 500  # Base score
            if 'qwen3' in model_name.lower():
                ranking_score = 850
            elif 'deepseek-r1' in model_name.lower():
                ranking_score = 800
            elif is_vision_capable:
                ranking_score = 750
            elif 'qwen2.5' in model_name.lower():
                ranking_score = 720
            elif 'phi4' in model_name.lower():
                ranking_score = 700
            elif 'mistral' in model_name.lower():
                ranking_score = 650

            # Determine if recommended
            recommended = (
                'qwen3' in model_name.lower() or
                'deepseek-r1' in model_name.lower() or
                is_vision_capable
            )

            all_models.append({
                "name": model_name,
                "display_name": model_name.replace('-', ' ').title(),
                "description": f"AI model: {model_name}",
                "capabilities": capabilities,
                "recommended": recommended,
                "ranking_score": ranking_score,
                "size": model.get("size", "Unknown")
            })

        # Apply capability filter if specified
        if capability_filter:
            filtered_models = [
                model for model in all_models
                if capability_filter in model["capabilities"]
            ]
        else:
            filtered_models = all_models

        # Sort by ranking score (highest first)
        filtered_models.sort(key=lambda x: x["ranking_score"], reverse=True)

        # Group models by capability for better organization
        model_groups = {}
        ungrouped_models = []

        for model in filtered_models:
            # Determine primary category based on capabilities
            capabilities = model["capabilities"]
            if "vision" in capabilities:
                primary_capability = "vision"
            elif "code" in capabilities:
                primary_capability = "code"
            elif "reasoning" in capabilities:
                primary_capability = "reasoning"
            elif "chat" in capabilities:
                primary_capability = "chat"
            else:
                primary_capability = "general"

            if primary_capability not in model_groups:
                model_groups[primary_capability] = []

            model_groups[primary_capability].append(model)

        return {
            "models": filtered_models,  # Flat list for frontend compatibility
            "model_groups": model_groups,  # Grouped data for future use
            "ungrouped_models": filtered_models,  # Same as models for now
            "default_model": "qwen3",
            "total_available": len(filtered_models),
            "filtered_out": len(all_models) - len(filtered_models),
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
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.services.ollama_client import ollama_client

router = APIRouter()


@router.get("/models", summary="List Available Ollama Models")
async def list_ollama_models() -> Dict[str, Any]:
    """
    Get a list of all available models from the Ollama server.

    This endpoint queries the Ollama API to retrieve information about all
    installed models that can be used for agent creation and task execution.

    Returns:
        Dict containing models array with name, size, modified date, and other metadata
    """
    try:
        async with ollama_client:
            result = await ollama_client.list_models()
            return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Ollama models: {str(e)}"
        )


@router.get("/models/names", summary="List Ollama Model Names")
async def list_ollama_model_names() -> Dict[str, List[str]]:
    """
    Get a simple list of available model names from Ollama.

    This is a simplified endpoint that returns only the model names,
    useful for dropdown selections in frontend interfaces.

    Returns:
        Dict with 'models' key containing array of model name strings
    """
    try:
        async with ollama_client:
            result = await ollama_client.list_models()
            model_names = [model["name"] for model in result.get("models", [])]
            return {"models": model_names}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Ollama model names: {str(e)}"
        )


@router.get("/health", summary="Check Ollama Server Health")
async def check_ollama_health() -> Dict[str, Any]:
    """
    Check the health status of the Ollama server.

    Returns connection status, number of available models, and default model info.
    """
    try:
        async with ollama_client:
            result = await ollama_client.health_check()
            return result
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.post("/models/pull/{model_name}", summary="Pull Ollama Model")
async def pull_ollama_model(model_name: str) -> Dict[str, Any]:
    """
    Pull (download) a model from the Ollama library.

    This endpoint allows you to download and install new models
    that aren't currently available on your Ollama server.

    Args:
        model_name: Name of the model to pull (e.g., "llama2", "codellama")

    Returns:
        Dict with pull status and model information
    """
    try:
        async with ollama_client:
            result = await ollama_client.pull_model(model_name)
            return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pull model '{model_name}': {str(e)}"
        )
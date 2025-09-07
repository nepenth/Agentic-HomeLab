"""
Vision AI API Routes.

This module provides REST API endpoints for vision AI processing including:
- Image analysis and description
- Object detection
- OCR (Optical Character Recognition)
- Image search and similarity
- Batch processing with resource management
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.vision_ai_service import vision_ai_service, VisionAIResult
from app.services.model_capability_service import model_capability_service
from app.api.dependencies import get_db_session, verify_api_key
from app.utils.logging import get_logger

logger = get_logger("vision_api")
router = APIRouter(
    tags=["Vision AI"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Vision AI Analysis Endpoints
# ============================================================================

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = Query("Describe this image in detail", description="Analysis prompt"),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    max_tokens: int = Query(500, ge=50, le=2000, description="Maximum tokens in response"),
    current_user: Dict = Depends(verify_api_key)
):
    """Analyze an uploaded image using vision AI."""
    try:
        # Read image data
        image_data = await file.read()

        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Empty image file provided"
            )

        # Validate image format
        is_valid_format = await vision_ai_service.validate_image_format(image_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported image format. Supported: JPEG, PNG, GIF, WebP, BMP"
            )

        # Analyze image
        result = await vision_ai_service.analyze_image(
            image_data=image_data,
            prompt=prompt,
            model_name=model_name,
            max_tokens=max_tokens
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "result": result.result,
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "analyzed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze image: {str(e)}"
        )


@router.post("/detect-objects", response_model=Dict[str, Any])
async def detect_objects(
    file: UploadFile = File(...),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Detect objects in an uploaded image."""
    try:
        # Read image data
        image_data = await file.read()

        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Empty image file provided"
            )

        # Validate image format
        is_valid_format = await vision_ai_service.validate_image_format(image_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported image format. Supported: JPEG, PNG, GIF, WebP, BMP"
            )

        # Detect objects
        result = await vision_ai_service.detect_objects(
            image_data=image_data,
            model_name=model_name
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "objects": result.result.get("objects", []),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "detected_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect objects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect objects: {str(e)}"
        )


@router.post("/extract-text", response_model=Dict[str, Any])
async def extract_text(
    file: UploadFile = File(...),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Extract text from an uploaded image (OCR)."""
    try:
        # Read image data
        image_data = await file.read()

        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Empty image file provided"
            )

        # Validate image format
        is_valid_format = await vision_ai_service.validate_image_format(image_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported image format. Supported: JPEG, PNG, GIF, WebP, BMP"
            )

        # Extract text
        result = await vision_ai_service.extract_text(
            image_data=image_data,
            model_name=model_name
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "extracted_text": result.result.get("extracted_text", ""),
                "has_text": result.result.get("has_text", False),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "extracted_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract text: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text: {str(e)}"
        )


@router.post("/search-similar", response_model=Dict[str, Any])
async def search_similar_images(
    file: UploadFile = File(...),
    search_prompt: str = Query("Find images with similar content", description="Search description"),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Search for images similar to the uploaded image."""
    try:
        # Read image data
        image_data = await file.read()

        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Empty image file provided"
            )

        # Validate image format
        is_valid_format = await vision_ai_service.validate_image_format(image_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported image format. Supported: JPEG, PNG, GIF, WebP, BMP"
            )

        # Search similar images
        result = await vision_ai_service.search_similar_images(
            query_image=image_data,
            search_prompt=search_prompt,
            model_name=model_name
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "search_criteria": result.result.get("search_criteria", {}),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "searched_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search similar images: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search similar images: {str(e)}"
        )


# ============================================================================
# Batch Processing Endpoints
# ============================================================================

@router.post("/batch/analyze", response_model=Dict[str, Any])
async def batch_analyze_images(
    files: List[UploadFile] = File(...),
    prompts: Optional[List[str]] = Query(None, description="Analysis prompts (one per image)"),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    max_tokens: int = Query(500, ge=50, le=2000, description="Maximum tokens per response"),
    current_user: Dict = Depends(verify_api_key)
):
    """Analyze multiple images in batch."""
    try:
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No image files provided"
            )

        if len(files) > 10:  # Limit batch size
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 images allowed in batch processing"
            )

        # Prepare image data for batch processing
        images_data = []
        for i, file in enumerate(files):
            image_data = await file.read()

            if not image_data:
                continue

            # Validate format
            is_valid = await vision_ai_service.validate_image_format(image_data)
            if not is_valid:
                continue

            prompt = "Describe this image in detail"
            if prompts and i < len(prompts):
                prompt = prompts[i]

            images_data.append({
                "id": file.filename,
                "data": image_data,
                "prompt": prompt
            })

        if not images_data:
            raise HTTPException(
                status_code=400,
                detail="No valid images found for processing"
            )

        # Process batch
        results = await vision_ai_service.batch_process_images(
            images=images_data,
            operation="analyze",
            model_name=model_name
        )

        # Format results
        formatted_results = []
        for i, result in enumerate(results):
            formatted_results.append({
                "filename": files[i].filename if i < len(files) else f"image_{i}",
                "success": result.success,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "result": result.result,
                "confidence": result.confidence,
                "error_message": result.error_message
            })

        return {
            "status": "completed",
            "data": {
                "total_images": len(images_data),
                "successful_analyses": sum(1 for r in results if r.success),
                "failed_analyses": sum(1 for r in results if not r.success),
                "results": formatted_results,
                "batch_processed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch analyze images: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch analyze images: {str(e)}"
        )


# ============================================================================
# Model Management Endpoints
# ============================================================================

@router.get("/models", response_model=Dict[str, Any])
async def get_vision_models(
    current_user: Dict = Depends(verify_api_key)
):
    """Get available vision-capable models."""
    try:
        models = await vision_ai_service.get_supported_models()

        return {
            "status": "success",
            "data": {
                "models": models,
                "total_models": len(models),
                "retrieved_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get vision models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve vision models: {str(e)}"
        )


@router.get("/models/capabilities", response_model=Dict[str, Any])
async def get_model_capabilities(
    current_user: Dict = Depends(verify_api_key)
):
    """Get model capabilities and statistics."""
    try:
        stats = await model_capability_service.get_capability_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get model capabilities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve model capabilities: {str(e)}"
        )


# ============================================================================
# Service Health and Statistics
# ============================================================================

@router.get("/health", response_model=Dict[str, Any])
async def get_vision_service_health():
    """Get vision AI service health status."""
    try:
        stats = await vision_ai_service.get_service_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get vision service health: {e}")
        return {
            "status": "error",
            "data": {
                "service": "vision_ai",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }


@router.get("/stats", response_model=Dict[str, Any])
async def get_vision_service_stats(
    current_user: Dict = Depends(verify_api_key)
):
    """Get comprehensive vision service statistics."""
    try:
        service_stats = await vision_ai_service.get_service_stats()
        model_stats = await model_capability_service.get_capability_stats()

        return {
            "status": "success",
            "data": {
                "service_stats": service_stats,
                "model_stats": model_stats,
                "combined_stats": {
                    "vision_models_available": len(service_stats.get("models", [])),
                    "total_models": model_stats.get("total_models", 0),
                    "max_concurrent_tasks": service_stats.get("max_concurrent_tasks", 0),
                    "supported_formats": service_stats.get("supported_formats", [])
                },
                "generated_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get vision service stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve vision service stats: {str(e)}"
        )
"""
Audio AI API Routes.

This module provides REST API endpoints for audio AI processing including:
- Audio transcription (speech-to-text)
- Speaker identification
- Emotion analysis
- Audio classification
- Music analysis
- Batch processing with resource management
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.audio_ai_service import audio_ai_service, AudioAIResult
from app.services.model_capability_service import model_capability_service
from app.api.dependencies import get_db_session, verify_api_key
from app.utils.logging import get_logger

logger = get_logger("audio_api")
router = APIRouter(
    tags=["Audio AI"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Audio AI Analysis Endpoints
# ============================================================================

@router.post("/transcribe", response_model=Dict[str, Any])
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Query("en", description="Language code (e.g., 'en', 'es', 'fr')"),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    include_timestamps: bool = Query(False, description="Include timestamps for speakers"),
    current_user: Dict = Depends(verify_api_key)
):
    """Transcribe audio to text (speech-to-text)."""
    try:
        # Read audio data
        audio_data = await file.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )

        # Validate audio format
        is_valid_format = await audio_ai_service.validate_audio_format(audio_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Supported: MP3, WAV, FLAC, AAC, OGG, WebM, M4A"
            )

        # Transcribe audio
        result = await audio_ai_service.transcribe_audio(
            audio_data=audio_data,
            language=language,
            model_name=model_name,
            include_timestamps=include_timestamps
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "transcription": result.result.get("transcription", ""),
                "language": result.result.get("language", language),
                "has_content": result.result.get("has_content", False),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "transcribed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )


@router.post("/identify-speakers", response_model=Dict[str, Any])
async def identify_speakers(
    file: UploadFile = File(...),
    num_speakers: Optional[int] = Query(None, description="Expected number of speakers"),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Identify speakers in audio."""
    try:
        # Read audio data
        audio_data = await file.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )

        # Validate audio format
        is_valid_format = await audio_ai_service.validate_audio_format(audio_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Supported: MP3, WAV, FLAC, AAC, OGG, WebM, M4A"
            )

        # Identify speakers
        result = await audio_ai_service.identify_speaker(
            audio_data=audio_data,
            num_speakers=num_speakers,
            model_name=model_name
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "speaker_analysis": result.result.get("speaker_analysis", ""),
                "speakers_identified": result.result.get("speakers_identified", 0),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "analyzed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to identify speakers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to identify speakers: {str(e)}"
        )


@router.post("/analyze-emotion", response_model=Dict[str, Any])
async def analyze_emotion(
    file: UploadFile = File(...),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Analyze emotions in audio."""
    try:
        # Read audio data
        audio_data = await file.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )

        # Validate audio format
        is_valid_format = await audio_ai_service.validate_audio_format(audio_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Supported: MP3, WAV, FLAC, AAC, OGG, WebM, M4A"
            )

        # Analyze emotion
        result = await audio_ai_service.analyze_emotion(
            audio_data=audio_data,
            model_name=model_name
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "emotion_analysis": result.result.get("emotion_analysis", ""),
                "detected_emotions": result.result.get("detected_emotions", []),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "analyzed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze emotion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze emotion: {str(e)}"
        )


@router.post("/classify", response_model=Dict[str, Any])
async def classify_audio(
    file: UploadFile = File(...),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Classify audio content type."""
    try:
        # Read audio data
        audio_data = await file.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )

        # Validate audio format
        is_valid_format = await audio_ai_service.validate_audio_format(audio_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Supported: MP3, WAV, FLAC, AAC, OGG, WebM, M4A"
            )

        # Classify audio
        result = await audio_ai_service.classify_audio(
            audio_data=audio_data,
            model_name=model_name
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "classification": result.result.get("classification", ""),
                "detected_categories": result.result.get("detected_categories", []),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "classified_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to classify audio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to classify audio: {str(e)}"
        )


@router.post("/analyze-music", response_model=Dict[str, Any])
async def analyze_music(
    file: UploadFile = File(...),
    model_name: Optional[str] = Query(None, description="Specific model to use"),
    current_user: Dict = Depends(verify_api_key)
):
    """Analyze music in audio."""
    try:
        # Read audio data
        audio_data = await file.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Empty audio file provided"
            )

        # Validate audio format
        is_valid_format = await audio_ai_service.validate_audio_format(audio_data)
        if not is_valid_format:
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Supported: MP3, WAV, FLAC, AAC, OGG, WebM, M4A"
            )

        # Analyze music
        result = await audio_ai_service.analyze_music(
            audio_data=audio_data,
            model_name=model_name
        )

        return {
            "status": "success" if result.success else "failed",
            "data": {
                "filename": file.filename,
                "model_used": result.model_used,
                "processing_time": result.processing_time,
                "music_analysis": result.result.get("music_analysis", ""),
                "detected_genres": result.result.get("detected_genres", []),
                "confidence": result.confidence,
                "error_message": result.error_message,
                "metadata": result.metadata,
                "analyzed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze music: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze music: {str(e)}"
        )


# ============================================================================
# Model Management Endpoints
# ============================================================================

@router.get("/models", response_model=Dict[str, Any])
async def get_audio_models(
    current_user: Dict = Depends(verify_api_key)
):
    """Get available audio-capable models."""
    try:
        models = await audio_ai_service.get_supported_models()

        return {
            "status": "success",
            "data": {
                "models": models,
                "total_models": len(models),
                "retrieved_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get audio models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audio models: {str(e)}"
        )


@router.get("/models/capabilities", response_model=Dict[str, Any])
async def get_audio_model_capabilities(
    current_user: Dict = Depends(verify_api_key)
):
    """Get audio model capabilities and statistics."""
    try:
        stats = await model_capability_service.get_capability_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get audio model capabilities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audio model capabilities: {str(e)}"
        )


# ============================================================================
# Service Health and Statistics
# ============================================================================

@router.get("/health", response_model=Dict[str, Any])
async def get_audio_service_health():
    """Get audio AI service health status."""
    try:
        stats = await audio_ai_service.get_service_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get audio service health: {e}")
        return {
            "status": "error",
            "data": {
                "service": "audio_ai",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }


@router.get("/stats", response_model=Dict[str, Any])
async def get_audio_service_stats(
    current_user: Dict = Depends(verify_api_key)
):
    """Get comprehensive audio service statistics."""
    try:
        service_stats = await audio_ai_service.get_service_stats()
        model_stats = await model_capability_service.get_capability_stats()

        return {
            "status": "success",
            "data": {
                "service_stats": service_stats,
                "model_stats": model_stats,
                "combined_stats": {
                    "audio_models_available": len(service_stats.get("models", [])),
                    "total_models": model_stats.get("total_models", 0),
                    "max_concurrent_tasks": service_stats.get("max_concurrent_tasks", 0),
                    "supported_formats": service_stats.get("supported_formats", []),
                    "emotion_categories": service_stats.get("emotion_categories", 0),
                    "audio_categories": service_stats.get("audio_categories", 0)
                },
                "generated_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get audio service stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audio service stats: {str(e)}"
        )
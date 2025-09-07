from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from app.api.dependencies import get_db_session, verify_api_key
from app.services.chat_service import ChatService
from app.services.ollama_client import ollama_client
from app.services.prompt_templates import prompt_manager
from app.utils.logging import get_logger

logger = get_logger("chat_api")
router = APIRouter()


class ChatSessionCreate(BaseModel):
    session_type: str = Field(..., description="Type of chat session (agent_creation, workflow_creation, general)")
    model_name: str = Field(..., description="Ollama model to use for the chat")
    user_id: str = Field(..., description="User identifier (required for session association)")
    title: Optional[str] = Field(None, description="Optional session title")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session configuration")


class ChatSessionResponse(BaseModel):
    id: str
    session_type: str
    user_id: Optional[str]
    model_name: str
    title: Optional[str]
    status: str
    is_active: bool
    is_resumable: bool
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    config: Dict[str, Any]
    message_count: int


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    message_type: Optional[str]
    metadata: Dict[str, Any]
    token_count: Optional[int]
    created_at: str


class SendMessageRequest(BaseModel):
    message: str = Field(..., description="User message to send")
    model_name: Optional[str] = Field(None, description="Override the session's model for this message")


class PerformanceMetrics(BaseModel):
    response_time_seconds: float = Field(..., description="Total response time in seconds")
    load_time_seconds: float = Field(..., description="Model loading time in seconds")
    prompt_eval_time_seconds: float = Field(..., description="Prompt evaluation time in seconds")
    generation_time_seconds: float = Field(..., description="Response generation time in seconds")
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    response_tokens: int = Field(..., description="Number of tokens generated in response")
    total_tokens: int = Field(..., description="Total tokens processed (prompt + response)")
    tokens_per_second: float = Field(..., description="Generation speed in tokens per second")
    context_length_chars: int = Field(..., description="Approximate context length in characters")
    model_name: str = Field(..., description="Model used for generation")
    timestamp: str = Field(..., description="Timestamp of the response")


class SendMessageResponse(BaseModel):
    session_id: str
    response: str
    model: str
    performance_metrics: PerformanceMetrics


class ChatStatsResponse(BaseModel):
    total_messages: int
    user_messages: int
    assistant_messages: int
    system_messages: int
    total_tokens: int
    message_types: Dict[str, int]


@router.post("/sessions", response_model=ChatSessionResponse, dependencies=[Depends(verify_api_key)])
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat session."""
    try:
        # Validate session type
        if session_data.session_type not in ["agent_creation", "workflow_creation", "general"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session_type. Must be: agent_creation, workflow_creation, or general"
            )

        # Validate model availability
        try:
            models_response = await ollama_client.list_models()
            available_models = [model["name"] for model in models_response.get("models", [])]

            if session_data.model_name not in available_models:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model '{session_data.model_name}' not available. Available models: {', '.join(available_models)}"
                )
        except Exception as e:
            logger.warning(f"Could not validate model availability: {e}")

        chat_service = ChatService(db)
        session = await chat_service.create_session(
            session_type=session_data.session_type,
            model_name=session_data.model_name,
            user_id=session_data.user_id,
            title=session_data.title,
            config=session_data.config
        )

        return ChatSessionResponse(**session.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    session_type: Optional[str] = Query(None, description="Filter by session type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List chat sessions with optional filtering."""
    try:
        chat_service = ChatService(db)
        sessions = await chat_service.list_sessions(
            user_id=user_id,
            session_type=session_type,
            status=status,
            limit=limit,
            offset=offset
        )

        return [ChatSessionResponse(**session.to_dict()) for session in sessions]

    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific chat session."""
    try:
        chat_service = ChatService(db)
        session = await chat_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        return ChatSessionResponse(**session.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat session"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get messages for a chat session."""
    try:
        chat_service = ChatService(db)
        messages = await chat_service.get_messages(
            session_id=session_id,
            limit=limit,
            offset=offset
        )

        return [ChatMessageResponse(**message.to_dict()) for message in messages]

    except Exception as e:
        logger.error(f"Failed to get messages for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat messages"
        )


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse, dependencies=[Depends(verify_api_key)])
async def send_chat_message(
    session_id: UUID,
    message_data: SendMessageRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Send a message to a chat session and get AI response."""
    try:
        chat_service = ChatService(db)
        result = await chat_service.send_message(
            session_id=session_id,
            user_message=message_data.message,
            model_name=message_data.model_name
        )

        return SendMessageResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to send message to session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.put("/sessions/{session_id}/status", dependencies=[Depends(verify_api_key)])
async def update_session_status(
    session_id: UUID,
    status: str = Query(..., description="New status (active, completed, archived, resumable)"),
    db: AsyncSession = Depends(get_db_session)
):
    """Update chat session status."""
    try:
        if status not in ["active", "completed", "archived", "resumable"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be: active, completed, archived, or resumable"
            )

        chat_service = ChatService(db)
        completed_at = datetime.utcnow() if status == "completed" else None

        success = await chat_service.update_session_status(
            session_id=session_id,
            status=status,
            completed_at=completed_at
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        return {"message": f"Session status updated to {status}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session status"
        )


@router.get("/sessions/{session_id}/stats", response_model=ChatStatsResponse)
async def get_session_stats(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get statistics for a chat session."""
    try:
        chat_service = ChatService(db)
        stats = await chat_service.get_session_stats(session_id)

        return ChatStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get stats for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session statistics"
        )


@router.delete("/sessions/{session_id}", dependencies=[Depends(verify_api_key)])
async def delete_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat session and all its messages."""
    try:
        chat_service = ChatService(db)
        success = await chat_service.delete_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        return {"message": "Chat session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )


@router.get("/templates")
async def list_chat_templates():
    """List available chat templates."""
    try:
        templates = prompt_manager.list_templates()
        return {"templates": templates}

    except Exception as e:
        logger.error(f"Failed to list chat templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat templates"
        )


@router.post("/cleanup", dependencies=[Depends(verify_api_key)])
async def cleanup_old_sessions(
    retention_days: int = Query(default=365, description="Retention period in days"),
    db: AsyncSession = Depends(get_db_session)
):
    """Clean up old chat sessions and messages beyond retention period."""
    try:
        chat_service = ChatService(db)
        deleted_count = await chat_service.cleanup_old_sessions(retention_days)

        return {
            "message": f"Cleaned up {deleted_count} chat sessions older than {retention_days} days",
            "deleted_sessions": deleted_count,
            "retention_days": retention_days
        }

    except Exception as e:
        logger.error(f"Failed to cleanup chat sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup chat sessions"
        )


@router.get("/models")
async def list_available_models():
    """List available Ollama models for chat."""
    try:
        models_response = await ollama_client.list_models()
        models = [model["name"] for model in models_response.get("models", [])]

        return {
            "models": models,
            "default_model": ollama_client.default_model
        }

    except Exception as e:
        logger.error(f"Failed to list available models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available models"
        )
"""
Enhanced Email Assistant API Routes.

This module provides REST API endpoints for the intelligent email assistant with:
- Model selection and switching
- Task-aware conversations
- Context persistence
- Rich message types
- Streaming support
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from starlette import status as status_codes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
import json
import asyncio

from app.api.dependencies import get_db_session, get_current_user
from app.db.models import User
from app.services.email_assistant_service import email_assistant_service, AssistantResponse
from app.utils.logging import get_logger

logger = get_logger("email_assistant_api")
router = APIRouter()


class ChatMessageRequest(BaseModel):
    """Request for sending a chat message to the email assistant."""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Chat session ID (creates new if None)")
    model_name: Optional[str] = Field(None, description="Specific model to use")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class ChatMessageResponse(BaseModel):
    """Response from the email assistant."""
    content: str
    message_type: str
    rich_content: Dict[str, Any] = Field(default_factory=dict)
    actions_performed: List[Dict[str, Any]] = Field(default_factory=list)
    related_entities: Dict[str, Any] = Field(default_factory=dict)
    suggested_actions: List[str] = Field(default_factory=list)
    model_used: str
    tokens_used: Optional[int] = None
    generation_time_ms: Optional[float] = None
    timestamp: str


class SessionCreateRequest(BaseModel):
    """Request to create a new chat session."""
    title: Optional[str] = Field(None, description="Session title")
    model_name: Optional[str] = Field(None, description="Model to use")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")


class SessionResponse(BaseModel):
    """Response containing session information."""
    id: str
    title: Optional[str]
    created_at: str
    last_activity: str
    selected_model: str
    message_count: int
    is_active: bool


class UserPreferencesResponse(BaseModel):
    """Response containing user chat preferences."""
    default_model: str
    default_temperature: float
    default_max_tokens: int
    show_model_selector: bool
    show_quick_actions: bool
    enable_auto_suggestions: bool
    enable_streaming: bool
    theme: str
    auto_save_conversations: bool
    max_conversation_history: int
    show_thinking: bool
    connection_timeout: int
    response_timeout: int
    max_retries: int
    auto_reconnect: bool
    quick_actions: List[Dict[str, Any]]
    frequent_models: List[str]


@router.post("/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Send a message to the email assistant and get an intelligent response.

    Features:
    - Model selection and switching
    - Context-aware conversations
    - Task management capabilities
    - Email search integration
    """
    try:
        # Process the message
        response = await email_assistant_service.process_message(
            message=request.message,
            user_id=current_user.id,
            session_id=request.session_id,
            model_name=request.model_name,
            db=db
        )

        # Convert to API response
        api_response = ChatMessageResponse(
            content=response.content,
            message_type=response.message_type.value,
            rich_content=response.rich_content,
            actions_performed=response.actions_performed,
            related_entities=response.related_entities,
            suggested_actions=response.suggested_actions,
            model_used=response.model_used,
            tokens_used=response.tokens_used,
            generation_time_ms=response.generation_time_ms,
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Chat message processed for user {current_user.username}")
        return api_response

    except Exception as e:
        logger.error(f"Chat message processing failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.post("/chat/stream")
async def send_chat_message_stream(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Send a message to the email assistant with streaming response.

    Provides real-time response streaming for better user experience.
    """
    async def generate_stream():
        try:
            # For now, simulate streaming by yielding the complete response
            # In a full implementation, this would stream tokens as they're generated
            response = await email_assistant_service.process_message(
                message=request.message,
                user_id=current_user.id,
                session_id=request.session_id,
                model_name=request.model_name,
                db=db
            )

            # Simulate streaming by breaking up the response
            words = response.content.split()
            chunk_size = max(1, len(words) // 10)  # Stream in ~10 chunks

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])

                stream_data = {
                    "type": "content",
                    "content": chunk + (" " if i + chunk_size < len(words) else ""),
                    "is_final": i + chunk_size >= len(words)
                }

                yield f"data: {json.dumps(stream_data)}\n\n"

                # Small delay to simulate real streaming
                await asyncio.sleep(0.1)

            # Send final metadata
            final_data = {
                "type": "metadata",
                "model_used": response.model_used,
                "generation_time_ms": response.generation_time_ms,
                "suggested_actions": response.suggested_actions,
                "rich_content": response.rich_content,
                "is_final": True
            }

            yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            error_data = {
                "type": "error",
                "error": str(e),
                "is_final": True
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_chat_session(
    request: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat session and persist to database."""
    try:
        from app.db.models.chat_session import ChatSession
        from uuid import uuid4

        # Create and persist session to database
        session = ChatSession(
            id=uuid4(),
            user_id=current_user.id,
            title=request.title or "New Chat",
            selected_model=request.model_name or "qwen3:30b-a3b-thinking-2507-q8_0",
            message_count=0,
            is_active=True
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Return the session information
        session_response = SessionResponse(
            id=str(session.id),
            title=session.title,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            selected_model=session.selected_model,
            message_count=session.message_count,
            is_active=session.is_active
        )

        logger.info(f"Created chat session {session.id} for user {current_user.id}")
        return session_response

    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get("/sessions", response_model=List[SessionResponse])
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's chat session history."""
    try:
        sessions = await email_assistant_service.get_session_history(
            user_id=current_user.id,
            limit=limit,
            db=db
        )

        session_responses = []
        for session in sessions:
            session_responses.append(SessionResponse(
                id=session["id"],
                title=session["title"],
                created_at=session["created_at"],
                last_activity=session["last_activity"],
                selected_model=session["selected_model"],
                message_count=session["message_count"],
                is_active=session["is_active"]
            ))

        return session_responses

    except Exception as e:
        logger.error(f"Get sessions failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Get messages from a specific chat session."""
    try:
        from app.db.models.chat_session import ChatSession, ChatMessage
        from sqlalchemy import select

        # Verify session exists and belongs to user
        session_stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Chat session {session_id} not found"
            )

        # Get messages
        messages_stmt = select(ChatMessage).where(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.sequence_number).limit(limit).offset(offset)

        messages_result = await db.execute(messages_stmt)
        messages = messages_result.scalars().all()

        return {
            "session_id": session_id,
            "messages": [msg.to_dict() for msg in messages],
            "total_count": session.message_count,
            "has_more": (offset + limit) < session.message_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session messages failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session messages"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat session and all its messages."""
    try:
        from app.db.models.chat_session import ChatSession
        from sqlalchemy import select, delete

        # Verify session exists and belongs to user
        session_stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Chat session {session_id} not found"
            )

        # Delete the session (messages will cascade delete)
        await db.delete(session)
        await db.commit()

        logger.info(f"Deleted chat session {session_id} for user {current_user.id}")
        return {
            "message": f"Chat session deleted successfully",
            "session_id": str(session_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )


@router.delete("/sessions")
async def purge_all_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete all chat sessions for the current user."""
    try:
        from app.db.models.chat_session import ChatSession
        from sqlalchemy import select, delete

        # Count sessions before deleting
        count_stmt = select(func.count()).select_from(ChatSession).where(
            ChatSession.user_id == current_user.id
        )
        count_result = await db.execute(count_stmt)
        session_count = count_result.scalar()

        # Delete all user's sessions (messages will cascade delete)
        delete_stmt = delete(ChatSession).where(
            ChatSession.user_id == current_user.id
        )
        await db.execute(delete_stmt)
        await db.commit()

        logger.info(f"Purged {session_count} chat sessions for user {current_user.id}")
        return {
            "message": f"All chat sessions purged successfully",
            "sessions_deleted": session_count
        }

    except Exception as e:
        logger.error(f"Purge sessions failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purge chat sessions"
        )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's chat preferences."""
    try:
        preferences = await email_assistant_service.get_user_preferences(
            user_id=current_user.id,
            db=db
        )

        return UserPreferencesResponse(**preferences)

    except Exception as e:
        logger.error(f"Get preferences failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user preferences"
        )


@router.put("/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update user's chat preferences."""
    try:
        updated_preferences = await email_assistant_service.update_user_preferences(
            user_id=current_user.id,
            preferences_update=preferences,
            db=db
        )

        return {
            "message": "Preferences updated successfully",
            "preferences": updated_preferences
        }

    except Exception as e:
        logger.error(f"Update preferences failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )


@router.post("/quick-actions")
async def execute_quick_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Execute a predefined quick action."""
    try:
        # Map quick actions to messages
        action_messages = {
            "show_pending_tasks": "Show me all my pending tasks",
            "search_emails": "Help me search my emails",
            "show_urgent": "Show me urgent emails that need attention",
            "workflow_status": "What's the current status of my email workflows?"
        }

        message = action_messages.get(action_id)
        if not message:
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Unknown quick action: {action_id}"
            )

        # Process as a regular chat message
        response = await email_assistant_service.process_message(
            message=message,
            user_id=current_user.id,
            session_id=None,  # Use default session or create new
            db=db
        )

        return {
            "action_id": action_id,
            "response": {
                "content": response.content,
                "rich_content": response.rich_content,
                "suggested_actions": response.suggested_actions
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick action execution failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute quick action"
        )


@router.get("/models")
async def get_available_models():
    """Get list of available Ollama models for the assistant (excludes embedding models)."""
    try:
        from app.services.ollama_client import ollama_client
        from app.config import settings

        models_response = await ollama_client.list_models()
        all_models = models_response.get("models", [])

        # Filter out embedding models - they typically have "embed" in the name
        # or are smaller models designed specifically for embeddings
        embedding_keywords = ["embed", "embedding", "nomic", "mxbai", "snowflake-arctic-embed"]

        chat_models = []
        for model in all_models:
            model_name = model["name"].lower()
            # Exclude if it contains embedding keywords
            if not any(keyword in model_name for keyword in embedding_keywords):
                chat_models.append(model["name"])

        # Get default model from settings
        default_model = settings.ollama_default_model

        logger.info(f"Found {len(chat_models)} chat models (filtered from {len(all_models)} total)")

        return {
            "models": sorted(chat_models),  # Sort alphabetically
            "default_model": default_model,
            "total_models": len(all_models),
            "chat_models": len(chat_models),
            "filtered_out": len(all_models) - len(chat_models)
        }

    except Exception as e:
        logger.error(f"Get models failed: {e}")
        from app.config import settings
        return {
            "models": [settings.ollama_default_model],
            "default_model": settings.ollama_default_model,
            "error": "Failed to fetch models from Ollama"
        }


@router.get("/analytics")
async def get_chat_analytics(
    current_user: User = Depends(get_current_user),
    period_days: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db_session)
):
    """Get analytics about user's chat usage."""
    try:
        # Mock analytics for now
        analytics = {
            "period_days": period_days,
            "total_messages": 150,
            "total_sessions": 25,
            "avg_messages_per_session": 6,
            "most_used_model": "llama2",
            "top_actions": [
                {"action": "show_tasks", "count": 45},
                {"action": "search_emails", "count": 30},
                {"action": "workflow_status", "count": 25}
            ],
            "response_times": {
                "avg_ms": 1250,
                "median_ms": 1100,
                "p95_ms": 2800
            },
            "satisfaction": {
                "positive_feedback": 85,
                "negative_feedback": 15,
                "total_feedback": 100
            }
        }

        return analytics

    except Exception as e:
        logger.error(f"Get analytics failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat analytics"
        )


@router.post("/feedback")
async def submit_feedback(
    message_id: str,
    feedback_type: str,  # "positive", "negative", "suggestion"
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Submit feedback for a specific assistant message."""
    try:
        # This would update the message feedback in the database
        # For now, just return success
        return {
            "message": "Feedback submitted successfully",
            "message_id": message_id,
            "feedback_type": feedback_type,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Submit feedback failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )
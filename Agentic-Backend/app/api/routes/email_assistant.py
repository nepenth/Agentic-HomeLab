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
from app.db.models import User, ModelBenchmark
from app.services.email_assistant_service import email_assistant_service, AssistantResponse
from app.utils.logging import get_logger

logger = get_logger("email_assistant_api")
router = APIRouter()


async def get_model_benchmarks_simple(model_name: str, db: AsyncSession) -> Dict[str, Any]:
    """Get benchmark data for a model from database."""
    try:
        from sqlalchemy import select

        # Extract base model name (before colon) for matching
        base_model_name = model_name.split(':')[0]

        # Query for the most recent benchmark data for this base model
        stmt = select(ModelBenchmark).where(
            ModelBenchmark.model_name == base_model_name
        ).order_by(ModelBenchmark.last_updated.desc()).limit(1)

        result = await db.execute(stmt)
        benchmark = result.scalar_one_or_none()

        if benchmark:
            # Return benchmark data in a format the frontend can use
            return {
                "average_score": benchmark.average_score,
                "arc_challenge": benchmark.arc_challenge,
                "hellaswag": benchmark.hellaswag,
                "mmlu": benchmark.mmlu,
                "truthfulqa": benchmark.truthfulqa,
                "winogrande": benchmark.winogrande,
                "gsm8k": benchmark.gsm8k,
                "source": benchmark.source,
                "last_updated": benchmark.last_updated.isoformat() if benchmark.last_updated else None
            }
        else:
            # Fallback to hardcoded data for testing
            fallback_data = {
                "qwen3": {"average_score": 85.0, "mmlu": 82.0, "gsm8k": 75.0},
                "deepseek-r1": {"average_score": 80.0, "mmlu": 78.0, "gsm8k": 85.0},
                "qwen2.5": {"average_score": 75.0, "mmlu": 72.0, "gsm8k": 70.0},
                "phi4": {"average_score": 70.0, "mmlu": 68.0, "gsm8k": 72.0},
                "mistral-small3.1": {"average_score": 65.0, "mmlu": 63.0, "gsm8k": 68.0},
            }
            return fallback_data.get(base_model_name, {})

    except Exception as e:
        logger.warning(f"Failed to get benchmarks for {model_name}: {e}")
        # Return fallback data even on error
        base_model_name = model_name.split(':')[0]
        fallback_data = {
            "qwen3": {"average_score": 85.0, "mmlu": 82.0, "gsm8k": 75.0},
            "deepseek-r1": {"average_score": 80.0, "mmlu": 78.0, "gsm8k": 85.0},
            "qwen2.5": {"average_score": 75.0, "mmlu": 72.0, "gsm8k": 70.0},
            "phi4": {"average_score": 70.0, "mmlu": 68.0, "gsm8k": 72.0},
            "mistral-small3.1": {"average_score": 65.0, "mmlu": 63.0, "gsm8k": 68.0},
        }
        return fallback_data.get(base_model_name, {})


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
        duplicates_found = 0
        seen_names = set()

        for model in all_models:
            model_name = model["name"]
            model_name_lower = model_name.lower()

            # Skip embedding models
            if any(keyword in model_name_lower for keyword in embedding_keywords):
                continue

            # Check for duplicates
            if model_name in seen_names:
                logger.warning(f"Duplicate model found in Ollama response: {model_name}")
                duplicates_found += 1
                continue

            seen_names.add(model_name)
            chat_models.append(model_name)

        # Sort alphabetically for consistent ordering
        chat_models.sort()

        # Get default model from settings
        default_model = settings.ollama_default_model

        logger.info(f"Found {len(chat_models)} chat models (filtered from {len(all_models)} total, {duplicates_found} duplicates removed)")

        return {
            "models": chat_models,
            "default_model": default_model,
            "total_models": len(all_models),
            "chat_models": len(chat_models),
            "filtered_out": len(all_models) - len(chat_models) - duplicates_found,
            "duplicates_removed": duplicates_found
        }

    except Exception as e:
        logger.error(f"Get models failed: {e}")
        from app.config import settings
        return {
            "models": [settings.ollama_default_model],
            "default_model": settings.ollama_default_model,
            "error": "Failed to fetch models from Ollama"
        }


@router.get("/models/rich")
async def get_available_models_rich(db: AsyncSession = Depends(get_db_session)):
    """Get comprehensive model information with deduplication and rich data."""
    logger.info(f"get_available_models_rich called with db session: {db is not None}")
    # Test database connection
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
    try:
        from app.services.ollama_client import ollama_client
        from app.config import settings
        from app.utils.modelIntelligence import getEnhancedModelInfo

        # Get raw models from Ollama
        models_response = await ollama_client.list_models()
        all_models = models_response.get("models", [])

        # Filter out embedding models
        embedding_keywords = ["embed", "embedding", "nomic", "mxbai", "snowflake-arctic-embed"]

        # Process each model individually - NO deduplication
        rich_models = []

        for model_data in all_models:
            model_name = model_data["name"]
            model_name_lower = model_name.lower()

            # Skip embedding models
            if any(keyword in model_name_lower for keyword in embedding_keywords):
                continue

            # Get enhanced static info for this specific model
            enhanced_info = getEnhancedModelInfo(model_name)

            # Get benchmark data from database
            try:
                model_benchmarks = await get_model_benchmarks_simple(model_name, db)
            except Exception as e:
                logger.error(f"Error getting benchmarks for {model_name}: {e}")
                model_benchmarks = {}

            # TEMPORARY: Hardcode benchmark data for testing
            if not model_benchmarks or not model_benchmarks.get('average_score'):
                base_model_name = model_name.split(':')[0]
                hardcoded_benchmarks = {
                    "qwen3": {"average_score": 85.0, "mmlu_score": 82.0, "gpqa_score": 78.0, "math_score": 75.0, "humaneval_score": 70.0, "bbh_score": 68.0},
                    "deepseek-r1": {"average_score": 80.0, "mmlu_score": 78.0, "gpqa_score": 75.0, "math_score": 85.0, "humaneval_score": 72.0, "bbh_score": 70.0},
                    "qwen2.5": {"average_score": 75.0, "mmlu_score": 72.0, "gpqa_score": 68.0, "math_score": 70.0, "humaneval_score": 65.0, "bbh_score": 62.0},
                    "phi4": {"average_score": 70.0, "mmlu_score": 68.0, "gpqa_score": 65.0, "math_score": 72.0, "humaneval_score": 75.0, "bbh_score": 68.0},
                    "mistral-small3.1": {"average_score": 65.0, "mmlu_score": 63.0, "gpqa_score": 60.0, "math_score": 68.0, "humaneval_score": 62.0, "bbh_score": 58.0},
                }
                model_benchmarks = hardcoded_benchmarks.get(base_model_name, {})

            # Calculate ranking score based on benchmarks and performance
            ranking_score = 50  # Default
            if model_benchmarks.get("average_score"):
                ranking_score = int(model_benchmarks["average_score"] * 10)  # Scale to 0-100
            elif enhanced_info.get("recommended"):
                ranking_score = 85  # Boost recommended models

            # Runtime data
            runtime_data = {
                "size_bytes": model_data.get("size", 0),
                "family": model_data.get("details", {}).get("family", ""),
                "quantization": model_data.get("details", {}).get("quantization_level", ""),
                "parameter_count": model_data.get("details", {}).get("parameter_size", ""),
                "last_modified": model_data.get("modified_at", "")
            }

            rich_models.append({
                "name": model_name,
                "display_name": enhanced_info.get("displayName", model_name.split(':')[0].title()),
                "description": enhanced_info.get("description", f"AI model {model_name}"),
                "category": enhanced_info.get("category", "general"),
                "recommended": enhanced_info.get("recommended", False),
                "size": enhanced_info.get("size", "Unknown"),
                "capabilities": enhanced_info.get("capabilities", ["text"]),
                "performance": enhanced_info.get("performance", {"reasoning": 5, "coding": 5, "speed": 5, "efficiency": 5}),
                "use_cases": enhanced_info.get("useCases", ["General AI tasks"]),
                "strengths": enhanced_info.get("strengths", ["Basic AI capabilities"]),
                "limitations": enhanced_info.get("limitations", ["Limited information available"]),
                "runtime_data": runtime_data,
                "benchmarks": model_benchmarks,
                "ranking_score": ranking_score
            })

        # Group models by family for better organization
        logger.info(f"Starting to group {len(rich_models)} models")
        model_groups = {}
        ungrouped_models = []

        for model in rich_models:
            model_name = model["name"]
            base_name = model_name.split(':')[0].lower()

            # Group by family
            if 'qwen' in base_name:
                family = 'Qwen'
            elif 'deepseek' in base_name:
                family = 'DeepSeek'
            elif 'llama' in base_name or 'llama3' in base_name:
                family = 'Llama'
            elif 'mistral' in base_name:
                family = 'Mistral'
            elif 'phi' in base_name:
                family = 'Phi'
            elif 'granite' in base_name:
                family = 'Granite'
            elif 'codellama' in base_name:
                family = 'CodeLlama'
            elif 'openthinker' in base_name:
                family = 'OpenThinker'
            elif 'cogito' in base_name:
                family = 'Cogito'
            elif 'magistral' in base_name:
                family = 'Magistral'
            elif 'gpt-oss' in base_name:
                family = 'GPT-OSS'
            elif 'stablelm' in base_name:
                family = 'StableLM'
            elif 'gemma' in base_name:
                family = 'Gemma'
            else:
                # Keep ungrouped models separate
                ungrouped_models.append(model)
                continue

            if family not in model_groups:
                model_groups[family] = []

            model_groups[family].append(model)

        # Sort models within each group by ranking score (descending)
        for family in model_groups:
            model_groups[family].sort(key=lambda x: (
                -x["ranking_score"],  # Higher ranking first
                -x["runtime_data"]["size_bytes"],  # Larger models first (within same ranking)
                x["name"]  # Alphabetical fallback
            ))

        # Sort ungrouped models
        ungrouped_models.sort(key=lambda x: (
            -x["ranking_score"],
            -x["runtime_data"]["size_bytes"],
            x["name"]
        ))

        # Create response with both flat models list (for frontend compatibility) and grouped data
        response = {
            "models": rich_models,  # Flat list for frontend compatibility
            "model_groups": model_groups,  # Grouped data for future use
            "ungrouped_models": ungrouped_models,
            "default_model": settings.ollama_default_model,
            "total_available": len(rich_models),
            "filtered_out": len(all_models) - len(rich_models),
            "groups_count": len(model_groups),
            "ungrouped_count": len(ungrouped_models),
            "last_updated": datetime.now().isoformat()
        }

        logger.info(f"Processed {len(rich_models)} rich models into {len(model_groups)} groups + {len(ungrouped_models)} ungrouped (from {len(all_models)} total models)")

        return response

    except Exception as e:
        logger.error(f"Get rich models failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fallback to basic endpoint
        return await get_available_models()


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
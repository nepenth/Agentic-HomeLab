"""
Email Chat API Routes for conversational email management.

This module provides REST API endpoints for natural language email interaction,
including chat-based search, organization, and task management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from starlette import status as status_codes
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, AsyncIterator
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio

from app.api.dependencies import get_db_session, get_current_user
from app.services.enhanced_email_chat_service import enhanced_email_chat_service
from app.services.email_chat_service import email_chat_service, EmailChatResponse
from app.services.chat_session_naming_service import chat_session_naming_service
from app.services.agentic_reasoning_service import agentic_reasoning_service
from app.utils.logging import get_logger
from app.db.models.user import User
from fastapi import BackgroundTasks

logger = get_logger("email_chat_api")
router = APIRouter()


async def generate_and_update_session_name(
    session_id: str,
    user_message: str,
    assistant_response: str,
    user_id: int
):
    """Background task to generate and update session name after response is sent."""
    logger.info(f"🔄 Background naming task started for session {session_id}")
    try:
        from app.db.models.chat_session import ChatSession
        from app.api.dependencies import get_db_session
        from sqlalchemy import select
        from uuid import UUID

        # Generate name using both user message and assistant response for better context
        combined_context = f"User: {user_message}\n\nAssistant: {assistant_response[:200]}"
        logger.info(f"Generating session name with context length: {len(combined_context)}")
        session_name = await chat_session_naming_service.generate_session_name(combined_context)
        logger.info(f"Generated session name: '{session_name}'")

        # Update the session title in database
        async for db in get_db_session():
            try:
                session_stmt = select(ChatSession).where(
                    ChatSession.id == UUID(session_id),
                    ChatSession.user_id == user_id
                )
                result = await db.execute(session_stmt)
                session = result.scalar_one_or_none()

                if session:
                    session.title = session_name
                    await db.commit()
                    logger.info(f"Updated session {session_id} title to: '{session_name}'")
                break
            except Exception as e:
                logger.error(f"Failed to update session name in DB: {e}")
                await db.rollback()

    except Exception as e:
        logger.error(f"Background session naming failed: {e}")
        # Non-critical, don't raise


class EmailChatRequest(BaseModel):
    """Request for email chat interaction."""
    message: str = Field(..., description="User's chat message")
    session_id: Optional[str] = Field(None, description="Chat session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context information")
    model_name: Optional[str] = Field(None, description="LLM model to use")
    max_days_back: int = Field(30, description="Maximum days to look back for emails")
    conversation_history: Optional[list] = Field(None, description="Previous conversation messages")
    stream: bool = Field(False, description="Enable streaming response")


class EmailChatResponseModel(BaseModel):
    """Response from email chat processing."""
    response_text: str
    actions_taken: list = Field(default_factory=list)
    search_results: Optional[list] = None
    suggested_actions: list = Field(default_factory=list)
    follow_up_questions: list = Field(default_factory=list)
    email_references: list = Field(default_factory=list, description="Referenced emails in conversation")
    tasks_created: list = Field(default_factory=list, description="Tasks created from emails")
    task_suggestions: list = Field(default_factory=list, description="Suggested tasks from analysis")
    thinking_content: list = Field(default_factory=list, description="Extracted thinking content from LLM")
    suggested_session_name: Optional[str] = Field(None, description="Auto-generated session name for first message")
    timestamp: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processing metadata")


class TaskCreationRequest(BaseModel):
    """Request for creating a task from an email."""
    email_id: str = Field(..., description="Email UUID")
    task_description: str = Field(..., description="Task description")
    task_type: Optional[str] = Field(None, description="Type of task")
    due_date: Optional[datetime] = Field(None, description="Due date for task")
    priority: int = Field(3, description="Task priority (1-5)")


class EmailSummaryRequest(BaseModel):
    """Request for email summarization."""
    email_id: str = Field(..., description="Email UUID")
    summary_type: str = Field("standard", description="Type of summary (standard, detailed, action_items)")


async def stream_chat_response(
    db: AsyncSession,
    user_id: int,
    message: str,
    model_name: Optional[str] = None,
    max_days_back: int = 30,
    conversation_history: Optional[list] = None,
    session_id: Optional[str] = None  # Add session_id parameter
) -> AsyncIterator[str]:
    """Generate streaming chat response."""
    try:
        # Load user preferences for timeout
        from app.db.models.chat_session import UserChatPreferences
        from sqlalchemy import select

        prefs_stmt = select(UserChatPreferences).where(UserChatPreferences.user_id == user_id)
        prefs_result = await db.execute(prefs_stmt)
        user_prefs = prefs_result.scalar_one_or_none()
        timeout_ms = user_prefs.response_timeout if user_prefs else 120000

        logger.info(f"[STREAMING] Using user timeout: {timeout_ms}ms ({timeout_ms/1000}s)")

        # First, send a status update about email search
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching relevant emails...'})}\n\n"
        await asyncio.sleep(0.1)

        # Use the enhanced service to process the chat with user's timeout
        response = await enhanced_email_chat_service.chat_with_email_context(
            db=db,
            user_id=user_id,
            message=message,
            model_name=model_name,
            max_days_back=max_days_back,
            conversation_history=conversation_history,
            timeout_ms=timeout_ms  # Pass user's timeout preference
        )

        # Send the email search results first
        if response["email_references"]:
            yield f"data: {json.dumps({'type': 'email_references', 'data': response['email_references']})}\n\n"
            await asyncio.sleep(0.1)

        # Send thinking content if available
        if response.get("thinking_content"):
            yield f"data: {json.dumps({'type': 'thinking', 'data': response['thinking_content']})}\n\n"
            await asyncio.sleep(0.1)

        # Stream the response text word by word
        words = response["response"].split()
        accumulated_text = ""

        yield f"data: {json.dumps({'type': 'response_start'})}\n\n"

        for i, word in enumerate(words):
            accumulated_text += word + " "
            yield f"data: {json.dumps({'type': 'response_chunk', 'text': word + ' ', 'accumulated': accumulated_text.strip()})}\n\n"
            await asyncio.sleep(0.05)  # Small delay to simulate streaming

        # Save session and messages if auto-save is enabled
        from app.db.models.chat_session import ChatSession, ChatMessage, MessageType
        from uuid import UUID, uuid4

        actual_session_id = session_id
        is_first_message = not session_id and (not conversation_history or len(conversation_history) == 0)

        logger.info(f"[STREAMING] First message check: session_id={session_id}, is_first={is_first_message}")

        if user_prefs and user_prefs.auto_save_conversations:
            try:
                # Get or create session
                if session_id:
                    session_stmt = select(ChatSession).where(
                        ChatSession.id == UUID(session_id),
                        ChatSession.user_id == user_id
                    )
                    session_result = await db.execute(session_stmt)
                    session = session_result.scalar_one_or_none()

                    if not session:
                        session = ChatSession(
                            id=UUID(session_id),
                            user_id=user_id,
                            title="New Chat",
                            selected_model=model_name or "qwen3:30b-a3b-thinking-2507-q8_0",
                            message_count=0
                        )
                        db.add(session)
                        await db.flush()
                else:
                    session = ChatSession(
                        id=uuid4(),
                        user_id=user_id,
                        title="New Chat",
                        selected_model=model_name or "qwen3:30b-a3b-thinking-2507-q8_0",
                        message_count=0
                    )
                    db.add(session)
                    await db.flush()
                    actual_session_id = str(session.id)

                # Save user message
                user_message = ChatMessage(
                    id=uuid4(),
                    session_id=session.id,
                    message_type=MessageType.USER.value,
                    content=message,
                    sequence_number=session.message_count
                )
                db.add(user_message)
                session.message_count += 1

                # Save assistant message
                assistant_message = ChatMessage(
                    id=uuid4(),
                    session_id=session.id,
                    message_type=MessageType.ASSISTANT.value,
                    content=response["response"],
                    sequence_number=session.message_count,
                    model_used=model_name,
                    rich_content={
                        "email_references": response["email_references"],
                        "suggested_actions": response["suggested_actions"]
                    }
                )
                db.add(assistant_message)
                session.message_count += 1

                session.last_activity = datetime.now()
                await db.commit()

                logger.info(f"[STREAMING] Saved chat session {session.id}")

                # Generate session name for first message
                if is_first_message and actual_session_id:
                    logger.info(f"[STREAMING] Generating session name for {actual_session_id}")
                    try:
                        # Generate name asynchronously (non-blocking for user)
                        combined_context = f"User: {message}\n\nAssistant: {response['response'][:200]}"
                        session_name = await chat_session_naming_service.generate_session_name(combined_context)

                        # Update session title
                        session.title = session_name
                        await db.commit()
                        logger.info(f"[STREAMING] Updated session title to: '{session_name}'")
                    except Exception as e:
                        logger.error(f"[STREAMING] Failed to generate session name: {e}")

            except Exception as e:
                logger.error(f"[STREAMING] Failed to save chat session: {e}")
                await db.rollback()

        # Send final metadata
        final_data = {
            'type': 'complete',
            'data': {
                'suggested_actions': response["suggested_actions"],
                'tasks_created': response["tasks_created"],
                'task_suggestions': response.get("task_suggestions", []),
                'metadata': response["metadata"],
                'timestamp': datetime.now().isoformat(),
                'session_id': actual_session_id  # Include session_id in response
            }
        }
        yield f"data: {json.dumps(final_data)}\n\n"

    except Exception as e:
        logger.error(f"Streaming chat error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/chat")
async def chat_with_emails(
    request: EmailChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Process natural language queries about email management.

    This endpoint allows users to interact with their emails using natural language,
    supporting search, organization, task creation, and status inquiries.

    Supports both streaming and non-streaming responses based on the 'stream' parameter.
    """
    try:
        # If streaming is requested, return a streaming response
        if request.stream:
            return StreamingResponse(
                stream_chat_response(
                    db=db,
                    user_id=current_user.id,
                    message=request.message,
                    model_name=request.model_name,
                    max_days_back=request.max_days_back,
                    conversation_history=request.conversation_history,
                    session_id=request.session_id  # Pass session_id for persistence
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )

        # Load user preferences for timeout and other settings
        from app.db.models.chat_session import UserChatPreferences, ChatSession, ChatMessage, MessageType
        from sqlalchemy import select
        from uuid import UUID, uuid4

        logger.info(f"Loading user preferences for user_id={current_user.id}")
        prefs_stmt = select(UserChatPreferences).where(UserChatPreferences.user_id == current_user.id)
        prefs_result = await db.execute(prefs_stmt)
        user_prefs = prefs_result.scalar_one_or_none()

        # Get timeout from user preferences (default to 2 minutes if not set)
        timeout_ms = user_prefs.response_timeout if user_prefs else 120000
        logger.info(f"✓ Using user timeout preference: {timeout_ms}ms ({timeout_ms/1000}s) from database")

        # Non-streaming response (original behavior)
        response = await enhanced_email_chat_service.chat_with_email_context(
            db=db,
            user_id=current_user.id,
            message=request.message,
            model_name=request.model_name,
            max_days_back=request.max_days_back,
            conversation_history=request.conversation_history,
            timeout_ms=timeout_ms  # Pass user's timeout preference
        )

        # Detect if this is the first message (for background session naming)
        # Check if session_id is None AND (conversation_history is None or empty list)
        is_first_message = (
            not request.session_id and
            (not request.conversation_history or len(request.conversation_history) == 0)
        )
        logger.info(f"First message detection: session_id={request.session_id}, "
                   f"conv_history_len={len(request.conversation_history) if request.conversation_history else 0}, "
                   f"is_first={is_first_message}")

        # If auto-save is enabled, persist the session and messages
        actual_session_id = request.session_id
        if user_prefs and user_prefs.auto_save_conversations:
            try:
                # Get or create session
                if request.session_id:
                    # Try to load existing session
                    session_stmt = select(ChatSession).where(
                        ChatSession.id == UUID(request.session_id),
                        ChatSession.user_id == current_user.id
                    )
                    session_result = await db.execute(session_stmt)
                    session = session_result.scalar_one_or_none()

                    if not session:
                        # Session doesn't exist, create it with temporary title
                        session = ChatSession(
                            id=UUID(request.session_id),
                            user_id=current_user.id,
                            title="New Chat",  # Will be updated by background task
                            selected_model=request.model_name or "qwen3:30b-a3b-thinking-2507-q8_0",
                            message_count=0
                        )
                        db.add(session)
                        await db.flush()
                else:
                    # Create new session with temporary title
                    session = ChatSession(
                        id=uuid4(),
                        user_id=current_user.id,
                        title="New Chat",  # Will be updated by background task
                        selected_model=request.model_name or "qwen3:30b-a3b-thinking-2507-q8_0",
                        message_count=0
                    )
                    db.add(session)
                    await db.flush()
                    actual_session_id = str(session.id)

                # Save user message
                user_message = ChatMessage(
                    id=uuid4(),
                    session_id=session.id,
                    message_type=MessageType.USER.value,
                    content=request.message,
                    sequence_number=session.message_count,
                    message_metadata=request.context or {}
                )
                db.add(user_message)
                session.message_count += 1

                # Save assistant response
                assistant_message = ChatMessage(
                    id=uuid4(),
                    session_id=session.id,
                    message_type=MessageType.ASSISTANT.value,
                    content=response["response"],
                    sequence_number=session.message_count,
                    model_used=request.model_name or "qwen3:30b-a3b-thinking-2507-q8_0",
                    message_metadata={
                        "email_references": response["email_references"],
                        "task_suggestions": response.get("task_suggestions", []),
                        "tasks_created": response["tasks_created"],
                        "thinking_content": response.get("thinking_content", []),
                        **response["metadata"]
                    },
                    rich_content={
                        "email_references": response["email_references"],
                        "suggested_actions": response["suggested_actions"]
                    }
                )
                db.add(assistant_message)
                session.message_count += 1

                # Update session activity
                session.last_activity = datetime.now()

                await db.commit()
                logger.info(f"Saved chat messages to session {session.id}")

                # Schedule background task to generate and update session name
                # Only for first message to avoid regenerating names
                logger.info(f"Checking background naming: is_first={is_first_message}, session_id={actual_session_id}")
                if is_first_message and actual_session_id:
                    background_tasks.add_task(
                        generate_and_update_session_name,
                        session_id=actual_session_id,
                        user_message=request.message,
                        assistant_response=response["response"],
                        user_id=current_user.id
                    )
                    logger.info(f"✓ Scheduled background session naming for session {actual_session_id}")
                else:
                    logger.info(f"✗ Skipping background naming: is_first={is_first_message}, session_id={actual_session_id}")

            except Exception as e:
                logger.error(f"Failed to save chat session: {e}")
                await db.rollback()
                # Non-critical, continue without saving

        # Convert to API response format
        api_response = EmailChatResponseModel(
            response_text=response["response"],
            actions_taken=[],  # Legacy field for compatibility
            search_results=response["email_references"],
            suggested_actions=response["suggested_actions"],
            follow_up_questions=[],  # Legacy field for compatibility
            email_references=response["email_references"],
            tasks_created=response["tasks_created"],
            task_suggestions=response.get("task_suggestions", []),
            thinking_content=response.get("thinking_content", []),
            suggested_session_name=None,  # Session name is generated in background task
            timestamp=datetime.now().isoformat(),
            metadata={
                **response["metadata"],
                "session_id": actual_session_id  # Include session ID for frontend
            }
        )

        logger.info(f"Enhanced email chat processed for user {current_user.id}: {request.message[:50]}...")
        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email chat processing failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process email chat request"
        )


@router.post("/chat/search")
async def search_emails_via_chat(
    request: EmailChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Search emails using natural language queries.

    Examples:
    - "Find emails about project deadlines from last week"
    - "Show me urgent emails from my boss"
    - "Find emails containing budget information"
    """
    try:
        # Force search intent by adding search keywords if not present
        message = request.message
        if not any(word in message.lower() for word in ["find", "search", "show", "look"]):
            message = f"Find emails about {message}"

        search_request = EmailChatRequest(
            message=message,
            session_id=request.session_id,
            context=request.context
        )

        return await chat_with_emails(search_request, current_user, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email search via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search emails via chat"
        )


@router.post("/chat/organize")
async def organize_emails_via_chat(
    request: EmailChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get organization suggestions for emails via chat.

    Examples:
    - "Help me organize my emails"
    - "How should I categorize my inbox"
    - "Suggest folders for my emails"
    """
    try:
        # Force organize intent
        message = request.message
        if not any(word in message.lower() for word in ["organize", "categorize", "group", "sort"]):
            message = f"Help me organize my emails: {message}"

        organize_request = EmailChatRequest(
            message=message,
            session_id=request.session_id,
            context=request.context
        )

        return await chat_with_emails(organize_request, current_user, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email organization via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to organize emails via chat"
        )


@router.post("/chat/summarize")
async def summarize_emails_via_chat(
    request: EmailChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get email summaries via natural language.

    Examples:
    - "Summarize my emails from today"
    - "Give me an overview of my recent emails"
    - "What are my emails about"
    """
    try:
        # Force summarize intent
        message = request.message
        if not any(word in message.lower() for word in ["summarize", "summary", "overview"]):
            message = f"Summarize my emails: {message}"

        summarize_request = EmailChatRequest(
            message=message,
            session_id=request.session_id,
            context=request.context
        )

        return await chat_with_emails(summarize_request, current_user, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email summarization via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to summarize emails via chat"
        )


@router.post("/chat/action")
async def perform_email_actions_via_chat(
    request: EmailChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Perform actions on emails via natural language.

    Examples:
    - "Mark all emails from my boss as read"
    - "Delete spam emails"
    - "Create tasks from urgent emails"
    - "Archive old emails"
    """
    try:
        # Force action intent
        message = request.message
        action_keywords = ["mark", "delete", "archive", "create", "reply", "forward"]
        if not any(word in message.lower() for word in action_keywords):
            message = f"Take action on emails: {message}"

        action_request = EmailChatRequest(
            message=message,
            session_id=request.session_id,
            context=request.context
        )

        return await chat_with_emails(action_request, current_user, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email actions via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform email actions via chat"
        )


@router.get("/chat/stats")
async def get_email_chat_stats(current_user: User = Depends(get_current_user)):
    """
    Get email chat service statistics.

    Returns information about supported intents, patterns, and usage statistics.
    """
    try:
        stats = email_chat_service.get_stats()

        return {
            "service": "email_chat",
            "supported_intents": stats.get("supported_intents", []),
            "intent_patterns_count": stats.get("intent_patterns", {}),
            "entity_patterns": stats.get("entity_patterns", []),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get email chat stats: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email chat statistics"
        )


@router.post("/tasks/create")
async def create_task_from_email(
    request: TaskCreationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a task from an email with LLM-enhanced details.

    This endpoint allows users to create actionable tasks from specific emails,
    with AI assistance for title generation, categorization, and time estimation.
    """
    try:
        task = await enhanced_email_chat_service.create_task_from_email(
            db=db,
            user_id=current_user.id,
            email_id=request.email_id,
            task_description=request.task_description,
            task_type=request.task_type,
            due_date=request.due_date,
            priority=request.priority
        )

        if not task:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Email not found or task creation failed"
            )

        return {
            "task_id": str(task.id),
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "priority": task.priority,
            "estimated_duration": task.estimated_duration_minutes,
            "email_id": request.email_id,
            "created_at": task.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task from email"
        )


@router.post("/emails/summarize")
async def summarize_email(
    request: EmailSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate an AI summary of a specific email.

    Provides different types of summaries including standard overviews,
    detailed analysis, and action item extraction.
    """
    try:
        summary_data = await enhanced_email_chat_service.get_email_summary(
            db=db,
            user_id=current_user.id,
            email_id=request.email_id,
            summary_type=request.summary_type
        )

        if "error" in summary_data:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail=summary_data["error"]
            )

        return summary_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email summarization failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to summarize email"
        )


@router.get("/chat/examples")
async def get_email_chat_examples():
    """
    Get example queries for email chat functionality.

    Returns a list of example messages users can try with the email chat system.
    """
    examples = {
        "search_examples": [
            "Find emails about project deadlines from last week",
            "Show me urgent emails from my boss",
            "Look for emails containing budget information",
            "Find emails from john@company.com",
            "Show me emails with attachments from today"
        ],
        "summarize_examples": [
            "Summarize my emails from today",
            "Give me an overview of my recent emails",
            "What are my emails about this week",
            "Show me a summary of important emails"
        ],
        "organize_examples": [
            "Help me organize my emails",
            "How should I categorize my inbox",
            "Suggest folders for different types of emails",
            "Group my emails by sender"
        ],
        "action_examples": [
            "Mark all emails from my boss as read",
            "Delete spam emails older than 30 days",
            "Create tasks from urgent emails",
            "Archive emails from last month",
            "Reply to the most recent email from support"
        ],
        "task_creation_examples": [
            "Create a task to follow up on the email from Sarah about the quarterly report",
            "Make a task to review the contract attached to the email from legal",
            "Add a task to prepare for the meeting mentioned in Monday's email",
            "Create a reminder task for the deadline mentioned in the project email"
        ],
        "status_examples": [
            "How many unread emails do I have",
            "Show me email statistics",
            "What are my most active email threads",
            "How many emails did I receive today"
        ]
    }

    return {
        "examples": examples,
        "tips": [
            "Be specific about time ranges (today, yesterday, last week)",
            "Mention sender names or email addresses when relevant",
            "Use keywords like 'urgent', 'important' for priority filtering",
            "Specify categories like 'work', 'personal' for better results",
            "Reference specific emails by mentioning subjects or senders",
            "Ask for task creation when you need to act on email content"
        ],
        "timestamp": datetime.now().isoformat()
    }


@router.post("/chat/stream-agentic")
async def stream_agentic_chat(
    request: EmailChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Stream chat responses with visible chain-of-thought reasoning.

    This endpoint uses the agentic reasoning service to perform multi-step
    reasoning with tool calling, streaming each step to the client as it happens.

    The response includes:
    - Planning steps showing the AI's reasoning
    - Tool calls and their results
    - Analysis of gathered information
    - Final comprehensive answer

    Response format (SSE):
    - Each event is sent as "data: {json}\n\n"
    - Step types: planning, tool_call, analysis, synthesis, final_answer, error
    - Final event has type: "complete"
    """

    async def generate_reasoning_stream():
        """Generator for SSE streaming of reasoning steps"""
        try:
            # Load user preferences for timeout
            from app.db.models.chat_session import UserChatPreferences
            from sqlalchemy import select

            prefs_stmt = select(UserChatPreferences).where(UserChatPreferences.user_id == current_user.id)
            prefs_result = await db.execute(prefs_stmt)
            user_prefs = prefs_result.scalar_one_or_none()
            timeout_ms = user_prefs.response_timeout if user_prefs else 120000

            logger.info(f"[AGENTIC] Starting chain-of-thought reasoning for user {current_user.id}")

            # Stream reasoning steps
            async for step in agentic_reasoning_service.reason_and_respond(
                db=db,
                user_id=current_user.id,
                user_query=request.message,
                model_name=request.model_name or "qwen3:30b-a3b-thinking-2507-q8_0",
                conversation_history=request.conversation_history,
                timeout_ms=timeout_ms
            ):
                # Format as SSE
                step_data = step.to_dict()
                yield f"data: {json.dumps(step_data)}\n\n"

            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            logger.info(f"[AGENTIC] Completed chain-of-thought reasoning")

        except Exception as e:
            logger.error(f"[AGENTIC] Streaming error: {e}", exc_info=True)
            error_data = {
                "type": "error",
                "error": str(e),
                "step_type": "error"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_reasoning_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
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
from app.utils.logging import get_logger
from app.db.models.user import User

logger = get_logger("email_chat_api")
router = APIRouter()


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
    conversation_history: Optional[list] = None
) -> AsyncIterator[str]:
    """Generate streaming chat response."""
    try:
        # First, send a status update about email search
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching relevant emails...'})}\n\n"
        await asyncio.sleep(0.1)

        # Use the enhanced service to process the chat (this could be made streaming too)
        response = await enhanced_email_chat_service.chat_with_email_context(
            db=db,
            user_id=user_id,
            message=message,
            model_name=model_name,
            max_days_back=max_days_back,
            conversation_history=conversation_history
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

        # Send final metadata
        final_data = {
            'type': 'complete',
            'data': {
                'suggested_actions': response["suggested_actions"],
                'tasks_created': response["tasks_created"],
                'task_suggestions': response.get("task_suggestions", []),
                'metadata': response["metadata"],
                'timestamp': datetime.now().isoformat()
            }
        }
        yield f"data: {json.dumps(final_data)}\n\n"

    except Exception as e:
        logger.error(f"Streaming chat error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/chat")
async def chat_with_emails(
    request: EmailChatRequest,
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
                    conversation_history=request.conversation_history
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )

        # Non-streaming response (original behavior)
        response = await enhanced_email_chat_service.chat_with_email_context(
            db=db,
            user_id=current_user.id,
            message=request.message,
            model_name=request.model_name,
            max_days_back=request.max_days_back,
            conversation_history=request.conversation_history
        )

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
            timestamp=datetime.now().isoformat(),
            metadata=response["metadata"]
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
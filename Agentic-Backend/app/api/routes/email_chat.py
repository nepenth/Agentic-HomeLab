"""
Email Chat API Routes for conversational email management.

This module provides REST API endpoints for natural language email interaction,
including chat-based search, organization, and task management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from starlette import status as status_codes
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.api.dependencies import get_db_session, verify_api_key
from app.services.email_chat_service import email_chat_service, EmailChatResponse
from app.utils.logging import get_logger

logger = get_logger("email_chat_api")
router = APIRouter()


class EmailChatRequest(BaseModel):
    """Request for email chat interaction."""
    message: str = Field(..., description="User's chat message")
    session_id: Optional[str] = Field(None, description="Chat session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context information")


class EmailChatResponseModel(BaseModel):
    """Response from email chat processing."""
    response_text: str
    actions_taken: list = Field(default_factory=list)
    search_results: Optional[list] = None
    suggested_actions: list = Field(default_factory=list)
    follow_up_questions: list = Field(default_factory=list)
    timestamp: str


@router.post("/chat", response_model=EmailChatResponseModel, dependencies=[Depends(verify_api_key)])
async def chat_with_emails(
    request: EmailChatRequest,
    user_id: str = Query(..., description="User identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Process natural language queries about email management.

    This endpoint allows users to interact with their emails using natural language,
    supporting search, organization, task creation, and status inquiries.
    """
    try:
        # Process the chat message
        response = await email_chat_service.process_email_chat(
            message=request.message,
            user_id=user_id,
            session_id=request.session_id,
            context=request.context
        )

        # Convert to API response format
        api_response = EmailChatResponseModel(
            response_text=response.response_text,
            actions_taken=response.actions_taken,
            search_results=response.search_results,
            suggested_actions=response.suggested_actions,
            follow_up_questions=response.follow_up_questions,
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Email chat processed for user {user_id}: {request.message[:50]}...")
        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email chat processing failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process email chat request"
        )


@router.post("/chat/search", dependencies=[Depends(verify_api_key)])
async def search_emails_via_chat(
    request: EmailChatRequest,
    user_id: str = Query(..., description="User identifier"),
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

        return await chat_with_emails(search_request, user_id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email search via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search emails via chat"
        )


@router.post("/chat/organize", dependencies=[Depends(verify_api_key)])
async def organize_emails_via_chat(
    request: EmailChatRequest,
    user_id: str = Query(..., description="User identifier"),
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

        return await chat_with_emails(organize_request, user_id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email organization via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to organize emails via chat"
        )


@router.post("/chat/summarize", dependencies=[Depends(verify_api_key)])
async def summarize_emails_via_chat(
    request: EmailChatRequest,
    user_id: str = Query(..., description="User identifier"),
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

        return await chat_with_emails(summarize_request, user_id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email summarization via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to summarize emails via chat"
        )


@router.post("/chat/action", dependencies=[Depends(verify_api_key)])
async def perform_email_actions_via_chat(
    request: EmailChatRequest,
    user_id: str = Query(..., description="User identifier"),
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

        return await chat_with_emails(action_request, user_id, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email actions via chat failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform email actions via chat"
        )


@router.get("/chat/stats", dependencies=[Depends(verify_api_key)])
async def get_email_chat_stats():
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
            "Specify categories like 'work', 'personal' for better results"
        ],
        "timestamp": datetime.now().isoformat()
    }
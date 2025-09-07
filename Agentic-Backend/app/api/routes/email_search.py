"""
Email Search and Filtering API Routes.

This module provides advanced search and filtering capabilities for emails,
including semantic search, thread-based filtering, and complex query support.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette import status as status_codes
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import re

from app.api.dependencies import get_db_session, verify_api_key
from app.services.email_semantic_search import email_semantic_search, EmailSearchQuery, EmailSearchResponse
from app.services.email_thread_detection import email_thread_detector, ThreadDetectionResult
from app.utils.logging import get_logger

logger = get_logger("email_search_api")
router = APIRouter()


class SearchType(str, Enum):
    """Email search types."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class SortOrder(str, Enum):
    """Search result sort orders."""
    RELEVANCE = "relevance"
    DATE_DESC = "date_desc"
    DATE_ASC = "date_asc"
    IMPORTANCE_DESC = "importance_desc"
    IMPORTANCE_ASC = "importance_asc"


class EmailSearchRequest(BaseModel):
    """Request for email search."""
    query: str = Field(..., description="Search query text")
    search_type: SearchType = Field(default=SearchType.SEMANTIC, description="Type of search to perform")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    include_threads: bool = Field(default=True, description="Include thread information")

    # Filters
    date_from: Optional[str] = Field(None, description="Start date filter (ISO format)")
    date_to: Optional[str] = Field(None, description="End date filter (ISO format)")
    sender: Optional[str] = Field(None, description="Filter by sender email")
    categories: Optional[List[str]] = Field(default_factory=list, description="Filter by categories")
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum importance score")
    has_attachments: Optional[bool] = Field(None, description="Filter by attachment presence")
    thread_id: Optional[str] = Field(None, description="Filter by specific thread")

    # Sorting
    sort_by: SortOrder = Field(default=SortOrder.RELEVANCE, description="Sort results by")


class EmailSearchResponseModel(BaseModel):
    """Response from email search."""
    query: str
    search_type: str
    total_count: int
    results: List[Dict[str, Any]]
    facets: Dict[str, Any]
    suggestions: List[str]
    search_time_ms: float
    timestamp: str


class ThreadDetectionRequest(BaseModel):
    """Request for thread detection."""
    emails: List[Dict[str, Any]] = Field(..., description="List of emails to analyze for threads")
    include_analysis: bool = Field(default=True, description="Include email analysis in results")


class ThreadDetectionResponse(BaseModel):
    """Response from thread detection."""
    threads: List[Dict[str, Any]]
    unthreaded_emails: List[Dict[str, Any]]
    total_emails_processed: int
    threads_created: int
    average_thread_length: float
    processing_time_ms: float
    timestamp: str


@router.post("/search", response_model=EmailSearchResponseModel, dependencies=[Depends(verify_api_key)])
async def search_emails(
    request: EmailSearchRequest,
    user_id: str = Query(..., description="User identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Perform advanced search across emails with semantic understanding.

    Supports semantic search, keyword matching, and hybrid approaches with
    comprehensive filtering and faceted results.
    """
    try:
        # Build search filters
        filters = {}
        if request.date_from:
            filters["date_from"] = request.date_from
        if request.date_to:
            filters["date_to"] = request.date_to
        if request.sender:
            filters["sender"] = request.sender
        if request.categories:
            filters["categories"] = request.categories
        if request.min_importance is not None:
            filters["min_importance"] = request.min_importance
        if request.has_attachments is not None:
            filters["has_attachments"] = request.has_attachments

        # Create search query
        search_query = EmailSearchQuery(
            query_text=request.query,
            user_id=user_id,
            filters=filters,
            limit=request.limit,
            offset=request.offset,
            include_threads=request.include_threads,
            search_type=request.search_type.value
        )

        # Perform search
        search_response = await email_semantic_search.search_emails(search_query, db)

        # Apply custom sorting if needed
        if request.sort_by != SortOrder.RELEVANCE:
            search_response.results = _sort_results(search_response.results, request.sort_by)

        # Convert to API response format
        api_response = EmailSearchResponseModel(
            query=request.query,
            search_type=request.search_type.value,
            total_count=search_response.total_count,
            results=[result.to_dict() for result in search_response.results],
            facets=search_response.facets,
            suggestions=search_response.suggestions,
            search_time_ms=search_response.search_time_ms,
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Email search completed for user {user_id}: {len(api_response.results)} results")
        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email search failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform email search"
        )


@router.post("/threads/detect", response_model=ThreadDetectionResponse, dependencies=[Depends(verify_api_key)])
async def detect_email_threads(
    request: ThreadDetectionRequest,
    user_id: str = Query(..., description="User identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Detect and group related emails into conversation threads.

    Analyzes email relationships based on subject lines, participants,
    and timing to create coherent conversation threads.
    """
    try:
        # Detect threads
        detection_result = await email_thread_detector.detect_threads(request.emails)

        # Convert to API response format
        api_response = ThreadDetectionResponse(
            threads=[thread.to_dict() for thread in detection_result.threads],
            unthreaded_emails=detection_result.unthreaded_emails,
            total_emails_processed=detection_result.total_emails_processed,
            threads_created=detection_result.threads_created,
            average_thread_length=detection_result.average_thread_length,
            processing_time_ms=detection_result.processing_time_ms,
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Thread detection completed for user {user_id}: {detection_result.threads_created} threads")
        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thread detection failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect email threads"
        )


@router.get("/search/suggestions", dependencies=[Depends(verify_api_key)])
async def get_search_suggestions(
    query: str = Query(..., description="Partial search query"),
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(default=10, ge=1, le=20, description="Maximum suggestions")
):
    """
    Get search suggestions based on partial query input.

    Provides intelligent suggestions to help users refine their search queries.
    """
    try:
        # Generate suggestions based on query patterns
        suggestions = await _generate_search_suggestions(query, user_id, limit)

        return {
            "query": query,
            "suggestions": suggestions,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        return {
            "query": query,
            "suggestions": [],
            "timestamp": datetime.now().isoformat()
        }


@router.get("/search/filters", dependencies=[Depends(verify_api_key)])
async def get_available_filters(
    user_id: str = Query(..., description="User identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get available filter options for email search.

    Returns dynamic filter options based on user's email data including
    available categories, senders, date ranges, etc.
    """
    try:
        # Get filter options from user's email data
        filters = await _get_dynamic_filters(user_id, db)

        return {
            "filters": filters,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Get filters failed: {e}")
        return {
            "filters": {
                "categories": ["work", "personal", "business", "finance"],
                "importance_levels": ["low", "medium", "high", "urgent"],
                "date_ranges": ["today", "yesterday", "this_week", "this_month"]
            },
            "timestamp": datetime.now().isoformat()
        }


@router.post("/search/advanced", response_model=EmailSearchResponseModel, dependencies=[Depends(verify_api_key)])
async def advanced_email_search(
    query: str = Query(..., description="Search query"),
    filters: Optional[Dict[str, Any]] = None,
    user_id: str = Query(..., description="User identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Perform advanced email search with complex filtering.

    Supports complex boolean queries, nested filters, and advanced search operators.
    """
    try:
        # Parse advanced query
        parsed_query, parsed_filters = _parse_advanced_query(query, filters or {})

        # Create search query
        search_query = EmailSearchQuery(
            query_text=parsed_query,
            user_id=user_id,
            filters=parsed_filters,
            limit=50,  # Larger limit for advanced search
            search_type="hybrid"
        )

        # Perform search
        search_response = await email_semantic_search.search_emails(search_query, db)

        # Convert to API response format
        api_response = EmailSearchResponseModel(
            query=parsed_query,
            search_type="advanced",
            total_count=search_response.total_count,
            results=[result.to_dict() for result in search_response.results],
            facets=search_response.facets,
            suggestions=search_response.suggestions,
            search_time_ms=search_response.search_time_ms,
            timestamp=datetime.now().isoformat()
        )

        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Advanced search failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform advanced email search"
        )


@router.get("/threads/{thread_id}", dependencies=[Depends(verify_api_key)])
async def get_email_thread(
    thread_id: str,
    user_id: str = Query(..., description="User identifier"),
    include_related: bool = Query(default=False, description="Include related threads"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed information about a specific email thread.

    Returns thread metadata, all emails in the thread, and optionally related threads.
    """
    try:
        # This would query the database for thread information
        # For now, return a placeholder response
        thread_info = {
            "thread_id": thread_id,
            "subject": "Sample Thread Subject",
            "message_count": 3,
            "participants": ["user@example.com", "sender@example.com"],
            "emails": [],
            "timestamp": datetime.now().isoformat()
        }

        if include_related:
            thread_info["related_threads"] = []

        return thread_info

    except Exception as e:
        logger.error(f"Get thread failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email thread"
        )


@router.get("/analytics/search", dependencies=[Depends(verify_api_key)])
async def get_search_analytics(
    user_id: str = Query(..., description="User identifier"),
    period_days: int = Query(default=30, ge=1, le=365, description="Analysis period in days"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get analytics about email search patterns and usage.

    Provides insights into search behavior, popular queries, and search effectiveness.
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        # This would query search analytics from database
        # For now, return placeholder analytics
        analytics = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": period_days
            },
            "search_metrics": {
                "total_searches": 150,
                "unique_queries": 45,
                "average_results_per_search": 8.5,
                "search_success_rate": 0.78
            },
            "popular_queries": [
                {"query": "project deadline", "count": 12},
                {"query": "meeting request", "count": 8},
                {"query": "budget approval", "count": 6}
            ],
            "search_types": {
                "semantic": 0.65,
                "keyword": 0.25,
                "hybrid": 0.10
            },
            "timestamp": datetime.now().isoformat()
        }

        return analytics

    except Exception as e:
        logger.error(f"Search analytics failed: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search analytics"
        )


def _sort_results(results: List[Any], sort_by: SortOrder) -> List[Any]:
    """Sort search results by the specified criteria."""
    if sort_by == SortOrder.DATE_DESC:
        return sorted(results, key=lambda x: x.sent_date, reverse=True)
    elif sort_by == SortOrder.DATE_ASC:
        return sorted(results, key=lambda x: x.sent_date)
    elif sort_by == SortOrder.IMPORTANCE_DESC:
        return sorted(results, key=lambda x: x.importance_score or 0, reverse=True)
    elif sort_by == SortOrder.IMPORTANCE_ASC:
        return sorted(results, key=lambda x: x.importance_score or 0)
    else:  # RELEVANCE (default)
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)


async def _generate_search_suggestions(query: str, user_id: str, limit: int) -> List[str]:
    """Generate search suggestions based on partial query."""
    suggestions = []

    if len(query) < 2:
        # General suggestions for short queries
        suggestions = [
            "recent emails",
            "important emails",
            "emails with attachments",
            "emails from today"
        ]
    else:
        # Context-aware suggestions
        query_lower = query.lower()

        if "project" in query_lower:
            suggestions.extend([
                f"{query} deadline",
                f"{query} status update",
                f"{query} meeting"
            ])
        elif "meeting" in query_lower:
            suggestions.extend([
                f"{query} request",
                f"{query} agenda",
                f"{query} notes"
            ])
        elif any(word in query_lower for word in ["urgent", "important", "asap"]):
            suggestions.extend([
                f"{query} from boss",
                f"{query} this week",
                f"{query} with attachments"
            ])
        else:
            # Generic suggestions
            suggestions.extend([
                f"{query} recent",
                f"{query} from last week",
                f"{query} important"
            ])

    return suggestions[:limit]


async def _get_dynamic_filters(user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Get dynamic filter options based on user's email data."""
    # This would query the database to get actual filter options
    # For now, return static options
    return {
        "categories": [
            "work/business",
            "personal",
            "finance",
            "social",
            "marketing",
            "support",
            "news",
            "spam"
        ],
        "importance_levels": [
            {"value": "low", "label": "Low (0.0 - 0.3)"},
            {"value": "medium", "label": "Medium (0.3 - 0.7)"},
            {"value": "high", "label": "High (0.7 - 0.9)"},
            {"value": "urgent", "label": "Urgent (0.9 - 1.0)"}
        ],
        "date_ranges": [
            {"value": "today", "label": "Today"},
            {"value": "yesterday", "label": "Yesterday"},
            {"value": "this_week", "label": "This Week"},
            {"value": "last_week", "label": "Last Week"},
            {"value": "this_month", "label": "This Month"},
            {"value": "last_month", "label": "Last Month"}
        ],
        "senders": [
            "boss@company.com",
            "team@company.com",
            "support@service.com"
        ]
    }


def _parse_advanced_query(query: str, filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Parse advanced search query with operators."""
    # Simple parsing for demonstration
    # In a full implementation, this would handle complex boolean logic

    parsed_filters = filters.copy()

    # Extract date filters
    date_patterns = [
        (r"after:(\d{4}-\d{2}-\d{2})", "date_from"),
        (r"before:(\d{4}-\d{2}-\d{2})", "date_to"),
        (r"from:([^\s]+)", "sender")
    ]

    for pattern, filter_key in date_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            parsed_filters[filter_key] = match.group(1)
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

    # Clean up query
    query = " ".join(query.split())

    return query.strip(), parsed_filters
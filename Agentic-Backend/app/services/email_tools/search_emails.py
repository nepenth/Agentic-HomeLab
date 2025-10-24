"""
Search Emails Tool

Provides semantic and keyword-based email search capabilities.
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_tools import EmailTool, ToolDefinition, email_tool_registry
from app.utils.logging import get_logger

logger = get_logger("search_emails_tool")


class SearchEmailsTool(EmailTool):
    """Search through user's emails using semantic search or keywords"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="search_emails",
            description="Search through user's emails using semantic search or keywords. Returns relevant emails matching the query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - can be natural language or keywords (e.g., 'tracking number', 'invoice from Amazon', 'meetings this week')"
                    },
                    "days_back": {
                        "type": "number",
                        "description": "How many days back to search (default: 30)",
                        "default": 30
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum number of emails to return (default: 10)",
                        "default": 10
                    },
                    "folder": {
                        "type": "string",
                        "description": "Specific folder to search (e.g., 'INBOX', 'Sent', 'Trash'). If not specified, searches all folders."
                    },
                    "sender": {
                        "type": "string",
                        "description": "Filter by sender email address"
                    }
                },
                "required": ["query"]
            }
        )

    @classmethod
    async def execute(cls, db: AsyncSession, user_id: int, **kwargs) -> Dict[str, Any]:
        from app.services.email_embedding_service import email_embedding_service
        from datetime import datetime, timedelta

        query = kwargs.get("query")
        days_back = kwargs.get("days_back", 30)
        max_results = kwargs.get("max_results", 10)
        folder = kwargs.get("folder")
        sender = kwargs.get("sender")

        if not query:
            return {
                "success": False,
                "error": "Query parameter is required"
            }

        logger.info(f"Searching emails for user {user_id}: query='{query}', days_back={days_back}, max_results={max_results}")

        try:
            # Calculate date range for filtering
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Use semantic search with date filtering
            similar_emails = await email_embedding_service.search_similar_emails(
                db=db,
                query_text=query,
                user_id=user_id,
                limit=max_results,
                similarity_threshold=0.3,
                temporal_boost=0.2
            )

            # Apply date filtering to results
            filtered_emails = []
            for email, score in similar_emails:
                # Check if email has a received_at date and falls within range
                if email.received_at:
                    email_date = email.received_at
                    # Handle timezone-naive datetimes
                    if email_date.tzinfo is None:
                        from datetime import timezone
                        email_date = email_date.replace(tzinfo=timezone.utc)

                    if start_date <= email_date <= end_date:
                        filtered_emails.append((email, score))

            # If we filtered out too many results, get more from the original search
            if len(filtered_emails) < max_results and len(similar_emails) > len(filtered_emails):
                additional_needed = max_results - len(filtered_emails)
                # Get more results from the original search
                more_emails = await email_embedding_service.search_similar_emails(
                    db=db,
                    query_text=query,
                    user_id=user_id,
                    limit=max_results * 2,  # Get more to filter
                    similarity_threshold=0.3,
                    temporal_boost=0.2
                )

                # Filter the additional results by date
                for email, score in more_emails:
                    if len(filtered_emails) >= max_results:
                        break

                    if email.received_at:
                        email_date = email.received_at
                        if email_date.tzinfo is None:
                            from datetime import timezone
                            email_date = email_date.replace(tzinfo=timezone.utc)

                        if start_date <= email_date <= end_date:
                            # Check if we already have this email
                            if not any(existing_email.id == email.id for existing_email, _ in filtered_emails):
                                filtered_emails.append((email, score))

            similar_emails = filtered_emails

            # Filter by folder if specified
            if folder and folder != "all":
                similar_emails = [
                    (email, score) for email, score in similar_emails
                    if email.folder_path and email.folder_path.startswith(folder)
                ]

            # Filter by sender if specified
            if sender:
                similar_emails = [
                    (email, score) for email, score in similar_emails
                    if sender.lower() in (email.sender_email or "").lower()
                ]

            # Format results
            results = []
            for email, score in similar_emails:
                results.append({
                    "email_id": str(email.id),
                    "subject": email.subject,
                    "sender": email.sender_email,
                    "received_at": email.received_at.isoformat() if email.received_at else None,
                    "folder": email.folder_path,
                    "preview": (email.body_text or "")[:200],
                    "similarity_score": round(score, 3)
                })

            logger.info(f"Found {len(results)} emails matching query")

            return {
                "success": True,
                "count": len(results),
                "emails": results,
                "query": query
            }

        except Exception as e:
            logger.error(f"Search emails failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Register the tool
email_tool_registry.register(SearchEmailsTool)

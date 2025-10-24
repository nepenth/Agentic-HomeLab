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
            # Use semantic search
            similar_emails = await email_embedding_service.search_similar_emails(
                db=db,
                query_text=query,
                user_id=user_id,
                limit=max_results,
                similarity_threshold=0.3,
                temporal_boost=0.2
            )

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

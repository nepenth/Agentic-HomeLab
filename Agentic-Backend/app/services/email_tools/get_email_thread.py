"""
Get Email Thread Tool

Retrieves complete email thread/conversation for context.
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.services.email_tools.base import EmailTool, ToolDefinition, email_tool_registry
from app.db.models.email import Email
from app.utils.logging import get_logger

logger = get_logger("get_email_thread_tool")


class GetEmailThreadTool(EmailTool):
    """Get the complete email thread/conversation for a given email"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_email_thread",
            description="Get the complete email thread/conversation for a given email. Useful for understanding context and previous exchanges.",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The email ID to get the thread for"
                    },
                    "include_sent": {
                        "type": "boolean",
                        "description": "Include sent emails in the thread (default: true)",
                        "default": True
                    },
                    "max_messages": {
                        "type": "number",
                        "description": "Maximum number of messages to return in the thread (default: 50)",
                        "default": 50
                    }
                },
                "required": ["email_id"]
            }
        )

    @classmethod
    async def execute(cls, db: AsyncSession, user_id: int, **kwargs) -> Dict[str, Any]:
        email_id = kwargs.get("email_id")
        include_sent = kwargs.get("include_sent", True)
        max_messages = kwargs.get("max_messages", 50)

        if not email_id:
            return {
                "success": False,
                "error": "email_id parameter is required"
            }

        logger.info(f"Getting email thread for user {user_id}: email_id={email_id}")

        try:
            # Convert string ID to integer
            try:
                email_id_int = int(email_id)
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid email_id: {email_id}"
                }

            # Get the original email
            query = select(Email).where(
                Email.id == email_id_int,
                Email.user_id == user_id
            )
            result = await db.execute(query)
            email = result.scalar_one_or_none()

            if not email:
                return {
                    "success": False,
                    "error": "Email not found"
                }

            # Get thread emails
            # If the email has a thread_id, use that; otherwise, use subject-based matching
            if email.thread_id:
                thread_query = select(Email).where(
                    and_(
                        Email.user_id == user_id,
                        Email.thread_id == email.thread_id
                    )
                ).order_by(Email.received_at).limit(max_messages)
            else:
                # Fallback: match by subject (remove Re:, Fwd:, etc.)
                base_subject = cls._normalize_subject(email.subject or "")
                if base_subject:
                    thread_query = select(Email).where(
                        and_(
                            Email.user_id == user_id,
                            Email.subject.ilike(f"%{base_subject}%")
                        )
                    ).order_by(Email.received_at).limit(max_messages)
                else:
                    # No subject, just return the single email
                    thread_emails = [email]
                    thread_query = None

            if thread_query:
                result = await db.execute(thread_query)
                thread_emails = result.scalars().all()
            else:
                thread_emails = [email]

            # Format thread
            thread = []
            for e in thread_emails:
                # Skip sent emails if requested
                if not include_sent and e.folder_path and "Sent" in e.folder_path:
                    continue

                thread.append({
                    "email_id": str(e.id),
                    "subject": e.subject,
                    "sender": e.sender_email,
                    "sender_name": e.sender_name,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                    "folder": e.folder_path,
                    "is_read": e.is_read,
                    "body_preview": (e.body_text or "")[:500] if e.body_text else ""
                })

            logger.info(f"Found {len(thread)} emails in thread")

            return {
                "success": True,
                "thread_count": len(thread),
                "thread": thread,
                "base_subject": email.subject
            }

        except Exception as e:
            logger.error(f"Get email thread failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def _normalize_subject(subject: str) -> str:
        """
        Normalize email subject by removing Re:, Fwd:, etc.

        Args:
            subject: Original email subject

        Returns:
            Normalized subject for thread matching
        """
        import re

        # Remove common email prefixes
        subject = re.sub(r'^(Re|RE|Fw|FW|Fwd|FWD):\s*', '', subject, flags=re.IGNORECASE)
        # Remove multiple spaces
        subject = re.sub(r'\s+', ' ', subject)
        # Strip whitespace
        subject = subject.strip()

        return subject


# Register the tool
email_tool_registry.register(GetEmailThreadTool)

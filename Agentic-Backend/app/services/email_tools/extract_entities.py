"""
Extract Entities Tool

Extracts structured entities from emails like tracking numbers, order IDs, dates, etc.
"""

from typing import Dict, Any, List
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.email_tools.base import EmailTool, ToolDefinition, email_tool_registry
from app.db.models.email import Email
from app.utils.logging import get_logger

logger = get_logger("extract_entities_tool")


class ExtractEntitiesTool(EmailTool):
    """Extract structured entities from emails (tracking numbers, order IDs, dates, etc.)"""

    # Entity extraction regex patterns
    PATTERNS = {
        "tracking_number": [
            r'\b1Z[0-9A-Z]{16}\b',  # UPS
            r'\b[0-9]{12,22}\b',    # Generic tracking
            r'\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b',  # Formatted tracking
        ],
        "order_number": [
            r'(?:Order|Order\s*Number|Order\s*#|#)\s*:?\s*([0-9A-Z-]{8,30})',
            r'\b[0-9]{3}-[0-9]{7}-[0-9]{7}\b',  # Amazon format
        ],
        "phone_number": [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',
        ],
        "email_address": [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        "amount": [
            r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            r'(?:USD|EUR|GBP)\s*\d+(?:,\d{3})*(?:\.\d{2})?',
        ],
        "url": [
            r'https?://[^\s<>"{}|\\^`\[\]]+',
        ],
        "date": [
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
        ],
        "address": [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)[,\s]+[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
        ]
    }

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="extract_entities",
            description="Extract specific types of entities from emails (tracking numbers, order numbers, phone numbers, dates, amounts, etc.)",
            parameters={
                "type": "object",
                "properties": {
                    "email_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email IDs to extract entities from"
                    },
                    "entity_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["tracking_number", "order_number", "phone_number", "email_address", "date", "amount", "url", "address"]
                        },
                        "description": "Types of entities to extract"
                    }
                },
                "required": ["email_ids", "entity_types"]
            }
        )

    @classmethod
    async def execute(cls, db: AsyncSession, user_id: int, **kwargs) -> Dict[str, Any]:
        email_ids = kwargs.get("email_ids", [])
        entity_types = kwargs.get("entity_types", [])

        if not email_ids:
            return {
                "success": False,
                "error": "email_ids parameter is required"
            }

        if not entity_types:
            return {
                "success": False,
                "error": "entity_types parameter is required"
            }

        logger.info(f"Extracting entities from {len(email_ids)} emails for user {user_id}: types={entity_types}")

        try:
            # Convert string IDs to integers
            email_id_ints = []
            for email_id in email_ids:
                try:
                    email_id_ints.append(int(email_id))
                except ValueError:
                    logger.warning(f"Invalid email ID: {email_id}")

            # Fetch emails
            query = select(Email).where(
                Email.id.in_(email_id_ints),
                Email.user_id == user_id
            )
            result = await db.execute(query)
            emails = result.scalars().all()

            if not emails:
                return {
                    "success": True,
                    "count": 0,
                    "entities": {},
                    "message": "No emails found with the provided IDs"
                }

            # Extract entities from each email
            extracted = {}
            total_entities = 0

            for email in emails:
                email_id = str(email.id)
                extracted[email_id] = {}

                # Combine subject and body for extraction
                content = f"{email.subject or ''}\n{email.body_text or ''}"

                for entity_type in entity_types:
                    if entity_type not in cls.PATTERNS:
                        logger.warning(f"Unknown entity type: {entity_type}")
                        continue

                    matches = set()
                    for pattern in cls.PATTERNS[entity_type]:
                        found = re.findall(pattern, content, re.IGNORECASE)
                        matches.update(found)

                    extracted[email_id][entity_type] = list(matches)
                    total_entities += len(matches)

            logger.info(f"Extracted {total_entities} entities from {len(emails)} emails")

            return {
                "success": True,
                "count": total_entities,
                "email_count": len(emails),
                "entities": extracted,
                "entity_types": entity_types
            }

        except Exception as e:
            logger.error(f"Extract entities failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Register the tool
email_tool_registry.register(ExtractEntitiesTool)

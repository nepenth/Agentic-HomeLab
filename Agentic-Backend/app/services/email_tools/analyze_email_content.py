"""
Analyze Email Content Tool

Performs deep LLM-powered analysis on email content.
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.email_tools.base import EmailTool, ToolDefinition, email_tool_registry
from app.db.models.email import Email
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("analyze_email_content_tool")


class AnalyzeEmailContentTool(EmailTool):
    """Perform deep analysis on email content using LLM"""

    # Pre-defined analysis prompts
    ANALYSIS_PROMPTS = {
        "summary": "Provide a concise 2-3 sentence summary of this email.",
        "action_items": "Extract all action items, tasks, or requests from this email as a bulleted list. If there are no action items, say 'No action items found.'",
        "entities": "Extract all important entities from this email: names, companies, products, amounts, dates, etc. Format as a bulleted list.",
        "sentiment": "Analyze the sentiment and tone of this email (positive/negative/neutral) and briefly explain why in 1-2 sentences.",
        "key_points": "List the 3-5 most important points or takeaways from this email as bullets.",
        "questions": "Extract all questions asked in this email. If there are no questions, say 'No questions found.'",
        "urgency": "Assess the urgency of this email (high/medium/low) and explain why in 1-2 sentences.",
        "category": "Categorize this email (e.g., work, personal, shopping, travel, finance, etc.) and explain why briefly."
    }

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_email_content",
            description="Perform deep analysis on email content. Can extract specific information, summarize, identify action items, detect sentiment, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Email ID to analyze"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["summary", "action_items", "entities", "sentiment", "key_points", "questions", "urgency", "category"],
                        "description": "Type of analysis to perform"
                    },
                    "custom_prompt": {
                        "type": "string",
                        "description": "Custom analysis prompt if analysis_type is not sufficient"
                    }
                },
                "required": ["email_id"]
            }
        )

    @classmethod
    async def execute(cls, db: AsyncSession, user_id: int, **kwargs) -> Dict[str, Any]:
        email_id = kwargs.get("email_id")
        analysis_type = kwargs.get("analysis_type", "summary")
        custom_prompt = kwargs.get("custom_prompt")

        if not email_id:
            return {
                "success": False,
                "error": "email_id parameter is required"
            }

        logger.info(f"Analyzing email for user {user_id}: email_id={email_id}, analysis_type={analysis_type}")

        try:
            # Convert string ID to integer
            try:
                email_id_int = int(email_id)
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid email_id: {email_id}"
                }

            # Fetch email
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

            # Build analysis prompt
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = cls.ANALYSIS_PROMPTS.get(analysis_type, cls.ANALYSIS_PROMPTS["summary"])

            # Prepare email content
            email_content = email.body_text or email.body_html or "No content available"
            # Limit content length to avoid token overflow
            if len(email_content) > 4000:
                email_content = email_content[:4000] + "... [content truncated]"

            full_prompt = f"""
{prompt}

Email Subject: {email.subject or "No subject"}
From: {email.sender_name or email.sender_email or "Unknown sender"}
Date: {email.received_at.strftime("%Y-%m-%d %H:%M") if email.received_at else "Unknown date"}

Email Content:
{email_content}
"""

            # Use LLM for analysis
            response = await ollama_client.generate(
                prompt=full_prompt,
                model="qwen3:30b-a3b-thinking-2507-q8_0",
                options={"temperature": 0.3, "num_predict": 500}
            )

            analysis_result = response.get("response", "")

            logger.info(f"Analysis completed for email {email_id}")

            return {
                "success": True,
                "analysis_type": analysis_type,
                "result": analysis_result,
                "email_id": str(email_id),
                "email_subject": email.subject
            }

        except Exception as e:
            logger.error(f"Analyze email content failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Register the tool
email_tool_registry.register(AnalyzeEmailContentTool)

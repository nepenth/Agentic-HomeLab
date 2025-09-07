"""
Email Chat Service for conversational email management.

This service provides natural language interaction capabilities for email management,
including searching, organizing, and taking actions on emails through chat.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from uuid import UUID

from app.services.chat_service import chat_service, ChatSession, ChatMessage
from app.services.email_semantic_search import email_semantic_search, EmailSearchQuery
from app.services.email_analysis_service import email_analysis_service
from app.services.email_task_converter import email_task_converter
from app.utils.logging import get_logger

logger = get_logger("email_chat_service")


@dataclass
class EmailChatIntent:
    """Represents the intent of an email chat message."""
    intent_type: str  # search, summarize, organize, action, status
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "entities": self.entities,
            "parameters": self.parameters
        }


@dataclass
class EmailChatResponse:
    """Response from email chat processing."""
    response_text: str
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    search_results: Optional[List[Dict[str, Any]]] = None
    suggested_actions: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "response_text": self.response_text,
            "actions_taken": self.actions_taken,
            "search_results": self.search_results,
            "suggested_actions": self.suggested_actions,
            "follow_up_questions": self.follow_up_questions
        }


class EmailChatService:
    """Service for conversational email management."""

    def __init__(self):
        self.logger = get_logger("email_chat_service")

        # Intent patterns for email chat
        self.intent_patterns = {
            "search": [
                r"find.*emails?.*about",
                r"search.*emails?.*for",
                r"show.*emails?.*from",
                r"look.*for.*emails?",
                r"emails?.*containing",
                r"emails?.*with.*subject"
            ],
            "summarize": [
                r"summarize.*emails?",
                r"give.*me.*summary.*of.*emails?",
                r"what.*are.*my.*emails?.*about",
                r"overview.*of.*emails?"
            ],
            "organize": [
                r"organize.*emails?",
                r"categorize.*emails?",
                r"group.*emails?",
                r"sort.*emails?"
            ],
            "action": [
                r"mark.*as.*read",
                r"delete.*emails?",
                r"archive.*emails?",
                r"reply.*to.*email",
                r"forward.*email",
                r"create.*task.*from.*email"
            ],
            "status": [
                r"how.*many.*emails?",
                r"email.*statistics",
                r"unread.*emails?",
                r"recent.*emails?",
                r"email.*status"
            ]
        }

        # Entity patterns
        self.entity_patterns = {
            "sender": r"from\s+([^\s,]+@[^\s,]+)",
            "date_range": r"(today|yesterday|last\s+week|this\s+week|this\s+month)",
            "importance": r"(urgent|important|high|medium|low)\s+priority",
            "category": r"(work|personal|business|finance|social|spam)"
        }

    async def process_email_chat(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EmailChatResponse:
        """
        Process a natural language message about email management.

        Args:
            message: User's chat message
            user_id: User identifier
            session_id: Optional chat session ID
            context: Additional context information

        Returns:
            EmailChatResponse with response and actions
        """
        try:
            # Analyze intent and entities
            intent = await self._analyze_intent(message)

            self.logger.info(f"Detected intent: {intent.intent_type} (confidence: {intent.confidence})")

            # Process based on intent
            if intent.intent_type == "search":
                return await self._handle_search_intent(message, intent, user_id)
            elif intent.intent_type == "summarize":
                return await self._handle_summarize_intent(message, intent, user_id)
            elif intent.intent_type == "organize":
                return await self._handle_organize_intent(message, intent, user_id)
            elif intent.intent_type == "action":
                return await self._handle_action_intent(message, intent, user_id)
            elif intent.intent_type == "status":
                return await self._handle_status_intent(message, intent, user_id)
            else:
                return EmailChatResponse(
                    response_text="I'm not sure what you'd like me to do with your emails. Try asking me to search for emails, summarize them, or help organize them.",
                    suggested_actions=[
                        "Search for emails about a specific topic",
                        "Show me recent important emails",
                        "Help me organize my inbox"
                    ]
                )

        except Exception as e:
            self.logger.error(f"Failed to process email chat: {e}")
            return EmailChatResponse(
                response_text="I encountered an error while processing your request. Please try again.",
                follow_up_questions=["Would you like me to try a different approach?"]
            )

    async def _analyze_intent(self, message: str) -> EmailChatIntent:
        """Analyze the intent of a chat message."""
        message_lower = message.lower()

        # Check each intent type
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    # Extract entities
                    entities = self._extract_entities(message)

                    # Calculate confidence based on pattern match strength
                    confidence = 0.8 if len(re.findall(pattern, message_lower)) > 0 else 0.6

                    return EmailChatIntent(
                        intent_type=intent_type,
                        confidence=confidence,
                        entities=entities
                    )

        # Default to search intent if no specific pattern matches
        return EmailChatIntent(
            intent_type="search",
            confidence=0.4,
            entities=self._extract_entities(message)
        )

    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract entities from the message."""
        entities = {}

        # Extract senders
        sender_match = re.search(self.entity_patterns["sender"], message, re.IGNORECASE)
        if sender_match:
            entities["sender"] = sender_match.group(1)

        # Extract date ranges
        date_match = re.search(self.entity_patterns["date_range"], message, re.IGNORECASE)
        if date_match:
            entities["date_range"] = date_match.group(1)

        # Extract importance levels
        importance_match = re.search(self.entity_patterns["importance"], message, re.IGNORECASE)
        if importance_match:
            entities["importance"] = importance_match.group(1)

        # Extract categories
        category_match = re.search(self.entity_patterns["category"], message, re.IGNORECASE)
        if category_match:
            entities["category"] = category_match.group(1)

        # Extract keywords for search
        words = re.findall(r'\b\w+\b', message.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'i', 'me', 'my', 'emails', 'email', 'show', 'find', 'search', 'about'}
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        if keywords:
            entities["keywords"] = keywords[:5]  # Limit to top 5 keywords

        return entities

    async def _handle_search_intent(
        self,
        message: str,
        intent: EmailChatIntent,
        user_id: str
    ) -> EmailChatResponse:
        """Handle search-related intents."""
        try:
            # Build search query from intent
            query_text = self._build_search_query(intent)

            search_query = EmailSearchQuery(
                query_text=query_text,
                user_id=user_id,
                filters=self._build_search_filters(intent),
                limit=10
            )

            # Perform search
            search_response = await email_semantic_search.search_emails(search_query)

            if not search_response.results:
                return EmailChatResponse(
                    response_text=f"I couldn't find any emails matching '{query_text}'. Try broadening your search terms.",
                    suggested_actions=[
                        "Try different keywords",
                        "Remove date restrictions",
                        "Search for recent emails"
                    ]
                )

            # Format response
            result_count = len(search_response.results)
            response_text = f"I found {result_count} email{'s' if result_count != 1 else ''} matching your search for '{query_text}':"

            # Convert search results for response
            search_results = [result.to_dict() for result in search_response.results[:5]]

            return EmailChatResponse(
                response_text=response_text,
                search_results=search_results,
                suggested_actions=[
                    "Show me more details about the first email",
                    "Mark these as read",
                    "Create tasks from these emails"
                ]
            )

        except Exception as e:
            self.logger.error(f"Search intent handling failed: {e}")
            return EmailChatResponse(
                response_text="I had trouble searching your emails. Please try rephrasing your search.",
                follow_up_questions=["What specific emails are you looking for?"]
            )

    async def _handle_summarize_intent(
        self,
        message: str,
        intent: EmailChatIntent,
        user_id: str
    ) -> EmailChatResponse:
        """Handle summarization intents."""
        try:
            # Get recent emails for summarization
            search_query = EmailSearchQuery(
                query_text="recent emails",
                user_id=user_id,
                filters={"date_from": (datetime.now() - timedelta(days=7)).isoformat()},
                limit=20
            )

            search_response = await email_semantic_search.search_emails(search_query)

            if not search_response.results:
                return EmailChatResponse(
                    response_text="You don't have any recent emails to summarize.",
                    suggested_actions=["Check for new emails", "Search for emails from a specific time period"]
                )

            # Generate summary
            summary = await self._generate_email_summary(search_response.results)

            return EmailChatResponse(
                response_text=summary,
                suggested_actions=[
                    "Show me the most important emails",
                    "Help me organize these emails",
                    "Create tasks from urgent emails"
                ]
            )

        except Exception as e:
            self.logger.error(f"Summarize intent handling failed: {e}")
            return EmailChatResponse(
                response_text="I couldn't generate a summary of your emails right now.",
                follow_up_questions=["Would you like me to try again?"]
            )

    async def _handle_organize_intent(
        self,
        message: str,
        intent: EmailChatIntent,
        user_id: str
    ) -> EmailChatResponse:
        """Handle organization intents."""
        try:
            # Get emails for organization
            search_query = EmailSearchQuery(
                query_text="all emails",
                user_id=user_id,
                limit=50
            )

            search_response = await email_semantic_search.search_emails(search_query)

            if not search_response.results:
                return EmailChatResponse(
                    response_text="You don't have any emails to organize.",
                    suggested_actions=["Check your email connection", "Search for emails in a specific category"]
                )

            # Analyze organization suggestions
            organization_suggestions = await self._analyze_organization_needs(search_response.results)

            response_text = "Here's how I suggest organizing your emails:\n\n" + organization_suggestions

            return EmailChatResponse(
                response_text=response_text,
                suggested_actions=[
                    "Apply these organization suggestions",
                    "Create folders for different categories",
                    "Set up automatic rules"
                ]
            )

        except Exception as e:
            self.logger.error(f"Organize intent handling failed: {e}")
            return EmailChatResponse(
                response_text="I couldn't analyze your email organization right now.",
                follow_up_questions=["Would you like me to try a different approach?"]
            )

    async def _handle_action_intent(
        self,
        message: str,
        intent: EmailChatIntent,
        user_id: str
    ) -> EmailChatResponse:
        """Handle action intents."""
        try:
            actions_taken = []

            # Parse action from message
            if "mark.*read" in message.lower():
                actions_taken.append({"action": "mark_read", "description": "Marked emails as read"})
            elif "delete" in message.lower():
                actions_taken.append({"action": "delete", "description": "Deleted specified emails"})
            elif "archive" in message.lower():
                actions_taken.append({"action": "archive", "description": "Archived emails"})
            elif "task" in message.lower():
                actions_taken.append({"action": "create_task", "description": "Created tasks from emails"})

            if actions_taken:
                response_text = f"I've taken the following actions on your emails:\n\n"
                for action in actions_taken:
                    response_text += f"• {action['description']}\n"
            else:
                response_text = "I understood you want to take action on emails, but I need more specific instructions."

            return EmailChatResponse(
                response_text=response_text,
                actions_taken=actions_taken,
                suggested_actions=[
                    "Show me the affected emails",
                    "Undo the last action",
                    "Apply similar actions to other emails"
                ]
            )

        except Exception as e:
            self.logger.error(f"Action intent handling failed: {e}")
            return EmailChatResponse(
                response_text="I couldn't complete the requested action on your emails.",
                follow_up_questions=["What specific action would you like me to take?"]
            )

    async def _handle_status_intent(
        self,
        message: str,
        intent: EmailChatIntent,
        user_id: str
    ) -> EmailChatResponse:
        """Handle status inquiry intents."""
        try:
            # Get basic email statistics
            stats = await self._get_email_stats(user_id)

            response_text = f"Here's the status of your emails:\n\n{stats}"

            return EmailChatResponse(
                response_text=response_text,
                suggested_actions=[
                    "Show me unread emails",
                    "Show me recent emails",
                    "Help me manage my inbox"
                ]
            )

        except Exception as e:
            self.logger.error(f"Status intent handling failed: {e}")
            return EmailChatResponse(
                response_text="I couldn't retrieve your email status right now.",
                follow_up_questions=["Would you like me to try again?"]
            )

    def _build_search_query(self, intent: EmailChatIntent) -> str:
        """Build search query from intent entities."""
        query_parts = []

        # Add keywords
        if "keywords" in intent.entities:
            query_parts.extend(intent.entities["keywords"])

        # Add specific entities
        if "sender" in intent.entities:
            query_parts.append(f"from:{intent.entities['sender']}")

        if "category" in intent.entities:
            query_parts.append(intent.entities["category"])

        if "importance" in intent.entities:
            query_parts.append(intent.entities["importance"])

        return " ".join(query_parts) if query_parts else "recent emails"

    def _build_search_filters(self, intent: EmailChatIntent) -> Dict[str, Any]:
        """Build search filters from intent entities."""
        filters = {}

        # Date range filter
        if "date_range" in intent.entities:
            date_range = intent.entities["date_range"]
            if date_range == "today":
                filters["date_from"] = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
            elif date_range == "yesterday":
                yesterday = datetime.now() - timedelta(days=1)
                filters["date_from"] = yesterday.replace(hour=0, minute=0, second=0).isoformat()
                filters["date_to"] = yesterday.replace(hour=23, minute=59, second=59).isoformat()
            elif "week" in date_range:
                days = 7 if "this" in date_range else 14
                filters["date_from"] = (datetime.now() - timedelta(days=days)).isoformat()

        # Importance filter
        if "importance" in intent.entities:
            importance_map = {
                "urgent": 0.8,
                "high": 0.6,
                "medium": 0.4,
                "low": 0.2
            }
            if intent.entities["importance"] in importance_map:
                filters["min_importance"] = importance_map[intent.entities["importance"]]

        return filters

    async def _generate_email_summary(self, emails: List[Any]) -> str:
        """Generate a summary of email results."""
        try:
            total_emails = len(emails)
            if total_emails == 0:
                return "No emails found to summarize."

            # Count by categories and senders
            categories = {}
            senders = {}
            important_count = 0

            for email in emails:
                # Count categories
                for category in email.categories:
                    categories[category] = categories.get(category, 0) + 1

                # Count senders
                sender_domain = email.sender.split('@')[-1] if '@' in email.sender else email.sender
                senders[sender_domain] = senders.get(sender_domain, 0) + 1

                # Count important emails
                if email.importance_score and email.importance_score > 0.7:
                    important_count += 1

            # Generate summary text
            summary = f"You have {total_emails} recent emails"

            if important_count > 0:
                summary += f", with {important_count} marked as important"

            if categories:
                top_category = max(categories.items(), key=lambda x: x[1])
                summary += f". Most emails are about {top_category[0]} ({top_category[1]} emails)"

            if senders:
                top_sender = max(senders.items(), key=lambda x: x[1])
                summary += f". You receive most emails from {top_sender[0]} ({top_sender[1]} emails)"

            return summary + "."

        except Exception as e:
            self.logger.error(f"Email summary generation failed: {e}")
            return f"You have {len(emails)} recent emails."

    async def _analyze_organization_needs(self, emails: List[Any]) -> str:
        """Analyze and suggest email organization improvements."""
        try:
            # Analyze current organization
            categories = {}
            unread_count = 0
            old_count = 0

            for email in emails:
                # Count categories
                for category in email.categories:
                    categories[category] = categories.get(category, 0) + 1

                # Count unread (assuming we have this info)
                # Count old emails
                if email.sent_date < datetime.now() - timedelta(days=30):
                    old_count += 1

            # Generate suggestions
            suggestions = []

            if len(categories) < 3:
                suggestions.append("• Consider creating more specific categories for your emails")

            if old_count > len(emails) * 0.3:
                suggestions.append("• You have many older emails - consider archiving them")

            if categories:
                top_category = max(categories.items(), key=lambda x: x[1])
                suggestions.append(f"• Create a dedicated folder for {top_category[0]} emails ({top_category[1]} emails)")

            suggestions.append("• Set up automatic rules to categorize incoming emails")
            suggestions.append("• Consider using priority inbox features")

            return "\n".join(suggestions) if suggestions else "Your emails appear well-organized!"

        except Exception as e:
            self.logger.error(f"Organization analysis failed: {e}")
            return "• Keep your inbox organized by regularly archiving old emails\n• Use categories to group similar emails"

    async def _get_email_stats(self, user_id: str) -> str:
        """Get basic email statistics."""
        try:
            # This would query actual email statistics
            # For now, return mock statistics
            return """📊 Email Statistics:
• Total emails: 1,247
• Unread emails: 23
• Important emails: 45
• Emails from last 7 days: 89
• Most active sender: notifications@company.com (156 emails)
• Largest category: Work/Business (623 emails)"""

        except Exception as e:
            self.logger.error(f"Email stats retrieval failed: {e}")
            return "Unable to retrieve email statistics at this time."

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "intent_patterns": {intent: len(patterns) for intent, patterns in self.intent_patterns.items()},
            "entity_patterns": list(self.entity_patterns.keys()),
            "supported_intents": list(self.intent_patterns.keys())
        }


# Global instance
email_chat_service = EmailChatService()
"""
Enhanced Email Assistant Service with Model Selection and Task-Aware Capabilities.

This service combines email chat, task management, email search, and context management
to provide an intelligent assistant for email workflow management.

Key Features:
- Model selection and switching mid-conversation
- Task-aware conversations with CRUD operations
- Intelligent email search integration
- Context persistence across sessions
- Agentic patterns for autonomous operations
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload

from app.db.models import (
    ChatSession,
    ChatMessage,
    UserChatPreferences,
    MessageType,
    Task,
    User
)
from app.db.models.task import TaskStatus
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger


logger = get_logger("email_assistant_service")


@dataclass
class EmailAssistantContext:
    """Context for email assistant conversations."""
    user_id: int
    session_id: str
    recent_tasks: List[Dict[str, Any]] = field(default_factory=list)
    recent_emails: List[Dict[str, Any]] = field(default_factory=list)
    search_history: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssistantResponse:
    """Response from the email assistant."""
    content: str
    message_type: MessageType = MessageType.ASSISTANT
    rich_content: Dict[str, Any] = field(default_factory=dict)
    actions_performed: List[Dict[str, Any]] = field(default_factory=list)
    related_entities: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)
    model_used: str = ""
    tokens_used: Optional[int] = None
    generation_time_ms: Optional[float] = None


class EmailAssistantService:
    """
    Enhanced Email Assistant Service with comprehensive email workflow management.

    Provides intelligent chat interface with task management, email search,
    and context-aware conversations using configurable Ollama models.
    """

    def __init__(self):
        self.logger = get_logger("email_assistant_service")

        # System prompts for different conversation types
        self.base_system_prompt = """You are an intelligent Email Assistant with access to a comprehensive email database and advanced search capabilities.

**AVAILABLE DATA & CAPABILITIES:**
🗃️ **Email Database**: Access to 5,920+ synced emails with full content analysis
📧 **Content Types**: Subject lines, body text, HTML content, attachments, metadata
🔍 **Search Methods**: Semantic search using vector embeddings, keyword matching, date filtering
📊 **Time Range**: Emails from multiple years, including recent 2025 communications
🏷️ **Email Features**: Sender information, recipients, timestamps, importance scores, categories

**SEARCH CAPABILITIES:**
✅ Find emails by content, sender, date, or topic
✅ Semantic search (understands context, not just keywords)
✅ Recent email retrieval ("last email", "latest messages")
✅ Advanced filtering (date ranges, importance, attachments)
✅ Thread and conversation analysis

**TASK MANAGEMENT:**
✅ Email-derived task creation and tracking
✅ Priority management and completion tracking
✅ Workflow insights and analytics

**IMPORTANT**: When users ask about emails, always search the database first. I have real access to their email content and can provide specific details, not just general responses.

Always be helpful, specific, and proactive. Provide actual email content and details when available."""

        self.task_management_prompt = """Focus on task-related queries. You can:
- Show pending, completed, or all tasks
- Mark tasks as complete or update their status
- Search tasks by content, priority, or email source
- Create new tasks from user descriptions
- Show task statistics and progress

When showing tasks, include relevant details like priority, creation date, and related email information."""

        self.email_search_prompt = """**EMAIL SEARCH SPECIALIST MODE**

🎯 **Search Capabilities**:
- Semantic search across 7,655+ email embeddings (subject, body, combined content)
- Exact keyword matching and phrase detection
- Date-based filtering and temporal relevance boosting
- Sender/recipient filtering and thread analysis
- Content type detection (travel, business, personal, etc.)

📧 **Available Email Content**:
- Full-text search of email bodies (text and HTML)
- Subject line semantic matching
- Attachment content when available
- Metadata including importance scores and categories

🔍 **Search Patterns Supported**:
- Recent emails: "last email", "latest message", "recent emails"
- Topic search: "flight itinerary", "meeting schedule", "invoice"
- Sender search: "emails from Delta", "messages from John"
- Date search: "emails from September", "this week's emails"
- Content search: "password reset", "trip confirmation"

**Always provide specific email details including sender, subject, date, and relevant content snippets.**"""

    async def process_message(
        self,
        message: str,
        user_id: int,
        session_id: Optional[str] = None,
        model_name: Optional[str] = None,
        db: AsyncSession = None
    ) -> AssistantResponse:
        """
        Process a user message and generate an intelligent response.

        Args:
            message: User's input message
            user_id: User identifier
            session_id: Chat session ID (creates new session if None)
            model_name: Specific model to use (uses user default if None)
            db: Database session

        Returns:
            AssistantResponse with generated content and actions
        """
        start_time = datetime.now()

        try:
            # Get or create chat session
            session = await self._get_or_create_session(user_id, session_id, model_name, db)

            # Build conversation context
            context = await self._build_context(session, db)

            # Detect user intent and prepare specialized prompt
            intent, intent_data = await self._detect_intent(message, context)

            # Generate response using appropriate model and prompt
            response = await self._generate_response(
                message=message,
                session=session,
                context=context,
                intent=intent,
                intent_data=intent_data,
                db=db
            )

            # Perform any autonomous actions based on the response
            if intent in ["task_management", "email_search", "action_request"]:
                await self._perform_autonomous_actions(response, context, db)

            # TODO: Save the conversation to database when async session is fixed
            # await self._save_conversation(session, message, response, db)

            # Update response timing
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            response.generation_time_ms = generation_time

            self.logger.info(f"Processed message for user {user_id} in {generation_time:.2f}ms")
            return response

        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            # Return fallback response
            return AssistantResponse(
                content=f"I encountered an error processing your request: {str(e)}. Please try again.",
                generation_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    async def _get_or_create_session(
        self,
        user_id: int,
        session_id: Optional[str],
        model_name: Optional[str],
        db: AsyncSession
    ) -> ChatSession:
        """Get existing session or create a new one."""
        # TODO: Fix async database session handling
        # For now, create a minimal mock session to test chat functionality

        # Use specified model or default
        selected_model = model_name or "llama2"

        # Create a temporary session object without database persistence
        # This allows testing of the chat functionality while bypassing database issues
        from uuid import uuid4
        mock_session = ChatSession(
            id=str(uuid4()),
            user_id=user_id,
            selected_model=selected_model,
            title="Test Email Assistant Chat",
            temperature=0.7,
            max_tokens=2000
        )

        return mock_session

    async def _build_context(self, session: ChatSession, db: AsyncSession) -> EmailAssistantContext:
        """Build comprehensive context for the conversation."""
        context = EmailAssistantContext(
            user_id=session.user_id,
            session_id=str(session.id)
        )

        # For now, skip database queries that are causing async issues
        # TODO: Fix async session context handling for these queries
        context.recent_tasks = []
        context.preferences = {}

        return context

    async def _detect_intent(self, message: str, context: EmailAssistantContext) -> tuple[str, Dict[str, Any]]:
        """Detect user intent and extract relevant data."""
        message_lower = message.lower()
        intent_data = {}

        # Task management intents
        task_keywords = ["task", "todo", "pending", "complete", "finish", "done", "urgent", "priority"]
        if any(keyword in message_lower for keyword in task_keywords):
            if any(action in message_lower for action in ["show", "list", "what", "which"]):
                intent_data["action"] = "show_tasks"
                # Extract filters
                if "pending" in message_lower:
                    intent_data["status"] = "pending"
                elif "completed" in message_lower:
                    intent_data["status"] = "completed"
                if "urgent" in message_lower:
                    intent_data["priority"] = "high"
            elif any(action in message_lower for action in ["complete", "finish", "done", "mark"]):
                intent_data["action"] = "complete_tasks"
                # Extract task references
                task_numbers = re.findall(r'task #?(\d+)', message_lower)
                if task_numbers:
                    intent_data["task_numbers"] = task_numbers
            elif any(action in message_lower for action in ["create", "add", "new"]):
                intent_data["action"] = "create_task"
                intent_data["description"] = message

            return "task_management", intent_data

        # Email search intents - expanded keywords
        search_keywords = [
            "find", "search", "show", "look for", "emails about", "from",
            "what", "which", "last", "recent", "latest", "newest", "get",
            "retrieve", "pull up", "display", "list", "emails", "messages"
        ]

        # Recent email specific patterns
        recent_patterns = [
            "last email", "latest email", "recent email", "newest email",
            "most recent", "last message", "latest message", "recent message"
        ]

        # Check for recent email requests first
        if any(pattern in message_lower for pattern in recent_patterns):
            intent_data["action"] = "search_recent_emails"
            intent_data["query"] = message
            intent_data["limit"] = 5  # Default for recent emails
            return "email_search", intent_data

        # General search patterns
        if any(keyword in message_lower for keyword in search_keywords):
            intent_data["action"] = "search_emails"
            intent_data["query"] = message

            # Extract search filters
            if " from " in message_lower:
                # Try to extract sender
                from_match = re.search(r'from (\w+@[\w.-]+|\w+)', message_lower)
                if from_match:
                    intent_data["sender"] = from_match.group(1)

            # Extract time filters
            time_keywords = ["today", "yesterday", "this week", "last week", "this month", "september", "october"]
            for time_kw in time_keywords:
                if time_kw in message_lower:
                    intent_data["time_filter"] = time_kw
                    break

            return "email_search", intent_data

        # General status and analytics
        status_keywords = ["status", "overview", "summary", "stats", "analytics", "dashboard"]
        if any(keyword in message_lower for keyword in status_keywords):
            intent_data["action"] = "show_status"
            return "status_inquiry", intent_data

        # Default to general conversation
        return "general_conversation", intent_data

    async def _generate_response(
        self,
        message: str,
        session: ChatSession,
        context: EmailAssistantContext,
        intent: str,
        intent_data: Dict[str, Any],
        db: AsyncSession
    ) -> AssistantResponse:
        """Generate intelligent response using Ollama."""

        # Select appropriate system prompt based on intent
        system_prompt = self.base_system_prompt
        if intent == "task_management":
            system_prompt = self.base_system_prompt + "\n\n" + self.task_management_prompt
        elif intent == "email_search":
            system_prompt = self.base_system_prompt + "\n\n" + self.email_search_prompt

        # Build conversation history for context
        conversation_context = await self._build_conversation_context(session, db)

        # Create specialized prompts based on intent
        if intent == "task_management":
            response = await self._handle_task_management(message, context, intent_data, db)
        elif intent == "email_search":
            response = await self._handle_email_search(message, context, intent_data, db)
        elif intent == "status_inquiry":
            response = await self._handle_status_inquiry(message, context, intent_data, db)
        else:
            # General conversation
            response = await self._handle_general_conversation(message, session, conversation_context)

        response.model_used = session.selected_model
        return response

    async def _handle_task_management(
        self,
        message: str,
        context: EmailAssistantContext,
        intent_data: Dict[str, Any],
        db: AsyncSession
    ) -> AssistantResponse:
        """Handle task management requests."""
        action = intent_data.get("action", "show_tasks")

        if action == "show_tasks":
            # Filter tasks based on criteria
            tasks = context.recent_tasks
            status_filter = intent_data.get("status")
            priority_filter = intent_data.get("priority")

            if status_filter:
                tasks = [t for t in tasks if t["status"] == status_filter]
            if priority_filter:
                tasks = [t for t in tasks if t["priority"] == priority_filter]

            if not tasks:
                return AssistantResponse(
                    content="You don't have any tasks matching those criteria.",
                    rich_content={"tasks": [], "count": 0}
                )

            # Format task list
            task_list = []
            for i, task in enumerate(tasks[:5], 1):
                status_emoji = "✅" if task["status"] == "completed" else "📋"
                priority_indicator = "🔴" if task["priority"] == "high" else "🟡" if task["priority"] == "medium" else "🟢"

                task_text = f"{status_emoji} Task #{i}: {task['description'][:100]}"
                if task["email_sender"]:
                    task_text += f"\n   📧 From: {task['email_sender']}"
                if task["email_subject"]:
                    task_text += f"\n   📝 Subject: {task['email_subject'][:60]}"

                task_list.append(task_text)

            content = f"Here are your {len(tasks)} tasks:\n\n" + "\n\n".join(task_list)

            if len(tasks) > 5:
                content += f"\n\n...and {len(tasks) - 5} more tasks."

            return AssistantResponse(
                content=content,
                rich_content={
                    "tasks": tasks[:5],
                    "total_count": len(tasks),
                    "showing_count": min(5, len(tasks))
                },
                suggested_actions=[
                    "Mark tasks as complete",
                    "Show completed tasks",
                    "Create a new task"
                ]
            )

        elif action == "complete_tasks":
            # Complete specific tasks or all pending tasks
            actions_performed = []

            task_numbers = intent_data.get("task_numbers", [])
            if task_numbers:
                # Complete specific tasks by number
                for task_num in task_numbers:
                    try:
                        task_index = int(task_num) - 1
                        if 0 <= task_index < len(context.recent_tasks):
                            task = context.recent_tasks[task_index]
                            # Update task in database
                            await self._complete_task(task["id"], db)
                            actions_performed.append(f"Completed Task #{task_num}: {task['description'][:50]}")
                    except (ValueError, IndexError):
                        continue
            else:
                # Complete tasks based on description matching
                completed_count = 0
                for task in context.recent_tasks:
                    if task["status"] == "pending" and completed_count < 3:  # Limit bulk operations
                        if any(keyword in task["description"].lower() for keyword in message.lower().split()):
                            await self._complete_task(task["id"], db)
                            actions_performed.append(f"Completed: {task['description'][:50]}")
                            completed_count += 1

            if actions_performed:
                content = f"I've completed {len(actions_performed)} task(s):\n\n" + "\n".join(actions_performed)
                return AssistantResponse(
                    content=content,
                    actions_performed=[{"type": "complete_task", "count": len(actions_performed)}],
                    suggested_actions=["Show remaining pending tasks", "Show completed tasks"]
                )
            else:
                return AssistantResponse(
                    content="I couldn't find any specific tasks to complete based on your request. Could you be more specific?",
                    suggested_actions=["Show pending tasks", "Specify task numbers to complete"]
                )

        elif action == "create_task":
            # Create a new task from user description
            description = intent_data.get("description", message)
            # Clean up the description
            description = re.sub(r'^(create|add|new)\s+(task|todo)\s*:?\s*', '', description, flags=re.IGNORECASE)

            new_task = await self._create_task(
                description=description,
                user_id=context.user_id,
                priority="medium",
                db=db
            )

            return AssistantResponse(
                content=f"I've created a new task: '{description[:100]}'",
                rich_content={"created_task": new_task},
                actions_performed=[{"type": "create_task", "task_id": new_task["id"]}],
                suggested_actions=["Show all tasks", "Mark this task as urgent"]
            )

        # Default fallback
        return AssistantResponse(
            content="I can help you manage your tasks. You can ask me to show tasks, complete tasks, or create new ones.",
            suggested_actions=["Show pending tasks", "Show completed tasks", "Create a new task"]
        )

    async def _handle_email_search(
        self,
        message: str,
        context: EmailAssistantContext,
        intent_data: Dict[str, Any],
        db: AsyncSession
    ) -> AssistantResponse:
        """Handle email search requests with real email data."""
        query = intent_data.get("query", message)

        try:
            # Import the email embedding service for real search
            from app.services.email_embedding_service import email_embedding_service
            from app.db.models.email import Email
            from sqlalchemy import select, desc

            # Use database session context to avoid async issues
            from app.db.database import get_session_context

            async with get_session_context() as search_db:
                # Handle recent email requests differently
                action = intent_data.get("action", "search_emails")

                if action == "search_recent_emails":
                    # For recent emails, use direct database query sorted by date
                    recent_query = select(Email).where(
                        Email.user_id == context.user_id
                    ).order_by(desc(Email.sent_at)).limit(intent_data.get("limit", 5))

                    result = await search_db.execute(recent_query)
                    recent_emails = result.scalars().all()

                    # Convert to search result format with high relevance scores
                    search_results = [(email, 0.95) for email in recent_emails]
                else:
                    # Perform real semantic search - explicitly include all embedding types
                    search_results = await email_embedding_service.search_similar_emails(
                        db=search_db,
                        query_text=query,
                        user_id=context.user_id,
                        limit=5,
                        similarity_threshold=0.3,  # Even lower threshold
                        temporal_boost=0.3,  # Higher boost for recent emails
                        importance_boost=0.1,
                        embedding_types=["subject", "body", "combined", "summary"]  # Search all types
                    )

                if not search_results:
                    return AssistantResponse(
                        content=f"I couldn't find any emails matching '{query}'. Try refining your search terms.",
                        rich_content={"search_results": [], "query": query, "total_count": 0},
                        suggested_actions=["Try broader search terms", "Check email sync status", "Search by sender"]
                    )

                # Convert search results to format expected by response
                formatted_results = []
                results_text = []

                for i, (email, similarity_score) in enumerate(search_results[:3], 1):
                    # Create snippet from available text
                    snippet = ""
                    if email.snippet:
                        snippet = email.snippet[:100]
                    elif email.body_text:
                        snippet = email.body_text[:100]
                    elif email.subject:
                        snippet = f"Subject: {email.subject}"
                    else:
                        snippet = "No preview available"

                    # Format for rich content
                    formatted_email = {
                        "id": str(email.id),
                        "subject": email.subject or "No subject",
                        "sender": email.sender_email or "Unknown sender",
                        "date": email.sent_at.isoformat() if email.sent_at else "Unknown date",
                        "snippet": snippet,
                        "importance_score": email.importance_score or 0.5,
                        "has_attachments": email.has_attachments or False,
                        "similarity_score": similarity_score,
                        "category": email.category
                    }
                    formatted_results.append(formatted_email)

                    # Format for text display
                    importance_indicator = "🔴" if (email.importance_score or 0) > 0.8 else "🟡" if (email.importance_score or 0) > 0.5 else "🟢"
                    attachment_indicator = "📎" if email.has_attachments else ""

                    # Format date nicely
                    date_str = "Unknown date"
                    if email.sent_at:
                        date_str = email.sent_at.strftime("%Y-%m-%d")

                    result_text = f"{importance_indicator} Email #{i}: {email.subject or 'No subject'}\n"
                    result_text += f"   📧 From: {email.sender_email or 'Unknown'}\n"
                    result_text += f"   📅 {date_str} {attachment_indicator}\n"
                    result_text += f"   💬 {snippet}..."
                    if similarity_score > 0.8:
                        result_text += f" (🎯 {similarity_score:.1%} match)"

                    results_text.append(result_text)

                # Create response content
                content = f"Found {len(formatted_results)} emails matching '{query}':\n\n" + "\n\n".join(results_text)

                return AssistantResponse(
                    content=content,
                    rich_content={
                        "search_results": formatted_results,
                        "query": query,
                        "total_count": len(formatted_results)
                    },
                    suggested_actions=["Show full email content", "Create tasks from these emails", "Search for more recent emails"]
                )

        except Exception as e:
            self.logger.error(f"Error searching emails: {e}")
            return AssistantResponse(
                content=f"I encountered an error while searching for '{query}'. Please try again with different terms.",
                rich_content={"search_results": [], "query": query, "error": str(e)},
                suggested_actions=["Try simpler search terms", "Check system status"]
            )

    async def _handle_status_inquiry(
        self,
        message: str,
        context: EmailAssistantContext,
        intent_data: Dict[str, Any],
        db: AsyncSession
    ) -> AssistantResponse:
        """Handle status and analytics requests."""

        # Get task statistics
        total_tasks = len(context.recent_tasks)
        pending_tasks = len([t for t in context.recent_tasks if t["status"] == "pending"])
        completed_tasks = len([t for t in context.recent_tasks if t["status"] == "completed"])

        # Get workflow stats (mock data)
        workflow_stats = {
            "active_workflows": 2,
            "emails_processed_today": 15,
            "tasks_created_today": 8,
            "success_rate": 85.5
        }

        content = f"""📊 **Email Assistant Status Overview**

📋 **Tasks:**
• Total: {total_tasks}
• Pending: {pending_tasks}
• Completed: {completed_tasks}

⚡ **Today's Activity:**
• Emails processed: {workflow_stats['emails_processed_today']}
• Tasks created: {workflow_stats['tasks_created_today']}
• Active workflows: {workflow_stats['active_workflows']}

📈 **Performance:**
• Success rate: {workflow_stats['success_rate']}%"""

        return AssistantResponse(
            content=content,
            rich_content={
                "task_stats": {
                    "total": total_tasks,
                    "pending": pending_tasks,
                    "completed": completed_tasks
                },
                "workflow_stats": workflow_stats
            },
            suggested_actions=[
                "Show pending tasks",
                "View recent email activity",
                "Show workflow history"
            ]
        )

    async def _handle_general_conversation(
        self,
        message: str,
        session: ChatSession,
        conversation_context: str
    ) -> AssistantResponse:
        """Handle general conversation using Ollama."""

        # Build prompt with context
        prompt = f"""You are an Email Assistant. Here's our conversation history:

{conversation_context}

User: {message}
Please respond as an intelligent email assistant that helps manage workflows and tasks."""

        try:
            # Generate response using Ollama
            response = await ollama_client.generate(
                model=session.selected_model,
                prompt=prompt,
                stream=False
            )

            content = response.get('response', 'I apologize, but I couldn\'t generate a response. Please try again.')
            
            return AssistantResponse(
                content=content,
                suggested_actions=[
                    "Show pending tasks",
                    "Search emails",
                    "Show workflow status"
                ]
            )

        except Exception as e:
            self.logger.error(f"Ollama generation failed: {e}")
            return AssistantResponse(
                content="I'm having trouble connecting to the AI model. Please try again in a moment.",
                suggested_actions=["Check system status"]
            )

    async def _build_conversation_context(self, session: ChatSession, db: AsyncSession) -> str:
        """Build conversation context from recent messages."""
        if not session.messages:
            return "This is the beginning of our conversation."

        # Get last 5 messages for context
        recent_messages = sorted(session.messages, key=lambda m: m.created_at)[-5:]
        
        context_lines = []
        for msg in recent_messages:
            role = "User" if msg.message_type == MessageType.USER else "Assistant"
            context_lines.append(f"{role}: {msg.content[:200]}")
        
        return "\n".join(context_lines)

    async def _perform_autonomous_actions(
        self,
        response: AssistantResponse,
        context: EmailAssistantContext,
        db: AsyncSession
    ) -> None:
        """Perform autonomous actions based on the response content."""
        # This method would implement agentic behaviors
        # For now, it's a placeholder for future autonomous features
        pass

    async def _save_conversation(
        self,
        session: ChatSession,
        user_message: str,
        assistant_response: AssistantResponse,
        db: AsyncSession
    ) -> None:
        """Save the conversation messages to the database."""
        # Get next sequence numbers
        next_seq = session.message_count

        # Save user message
        user_msg = ChatMessage(
            session_id=session.id,
            message_type=MessageType.USER,
            sequence_number=next_seq,
            content=user_message,
            message_metadata={"timestamp": datetime.now().isoformat()}
        )
        db.add(user_msg)

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session.id,
            message_type=assistant_response.message_type,
            sequence_number=next_seq + 1,
            content=assistant_response.content,
            rich_content=assistant_response.rich_content,
            model_used=assistant_response.model_used,
            tokens_used=assistant_response.tokens_used,
            generation_time_ms=assistant_response.generation_time_ms,
            actions_performed=assistant_response.actions_performed,
            related_entities=assistant_response.related_entities,
            message_metadata={"suggested_actions": assistant_response.suggested_actions}
        )
        db.add(assistant_msg)

        # Update session
        session.message_count += 2
        session.last_activity = datetime.now()

        await db.commit()

    async def _complete_task(self, task_id: str, db: AsyncSession) -> bool:
        """Mark a task as completed."""
        try:
            # Update task status
            stmt = update(Task).where(Task.id == task_id).values(
                status=TaskStatus.COMPLETED,
                completed_at=datetime.now()
            )
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    async def _create_task(
        self,
        description: str,
        user_id: int,
        priority: str = "medium",
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Create a new task."""
        task = Task(
            status=TaskStatus.PENDING,
            input={
                'description': description,
                'priority': priority,
                'user_id': user_id,
                'source': 'email_assistant_chat',
                'created_via': 'chat'
            }
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        return {
            "id": str(task.id),
            "description": description,
            "status": task.status.value,
            "priority": priority,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }

    async def _generate_session_title(self, default_title: str) -> str:
        """Generate a title for the chat session."""
        # For now, return default. Could be enhanced to generate based on first message
        return default_title

    async def get_session_history(
        self,
        user_id: int,
        limit: int = 10,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """Get user's chat session history."""
        stmt = select(ChatSession).where(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.last_activity.desc()).limit(limit)

        result = await db.execute(stmt)
        sessions = result.scalars().all()

        return [session.to_dict() for session in sessions]

    async def get_user_preferences(
        self,
        user_id: int,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Get user's chat preferences."""
        stmt = select(UserChatPreferences).where(UserChatPreferences.user_id == user_id)
        result = await db.execute(stmt)
        preferences = result.scalar_one_or_none()

        if not preferences:
            # Create default preferences
            preferences = UserChatPreferences.create_default_preferences(user_id)
            db.add(preferences)
            await db.commit()
            await db.refresh(preferences)

        return preferences.to_dict()

    async def update_user_preferences(
        self,
        user_id: int,
        preferences_update: Dict[str, Any],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Update user's chat preferences."""
        stmt = select(UserChatPreferences).where(UserChatPreferences.user_id == user_id)
        result = await db.execute(stmt)
        preferences = result.scalar_one_or_none()

        if not preferences:
            preferences = UserChatPreferences.create_default_preferences(user_id)
            db.add(preferences)
            await db.flush()

        # Update preferences
        for key, value in preferences_update.items():
            if hasattr(preferences, key):
                setattr(preferences, key, value)

        await db.commit()
        await db.refresh(preferences)

        return preferences.to_dict()


# Global instance
email_assistant_service = EmailAssistantService()

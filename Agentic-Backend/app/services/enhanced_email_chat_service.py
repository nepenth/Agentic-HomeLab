"""
Enhanced Email Chat Service

Provides LLM-powered chat functionality with email context integration.
Allows users to chat about their synced emails, get summaries, create tasks,
and reference actual email content in conversations.
"""

import asyncio
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, text
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
from functools import lru_cache

from app.db.models.email import Email, EmailEmbedding, EmailTask, EmailAccount
from app.db.models.user import User
from app.db.models.task import LogLevel
from app.services.email_embedding_service import email_embedding_service
from app.services.semantic_processing_service import semantic_processing_service
from app.services.ollama_client import ollama_client
from app.services.unified_log_service import unified_log_service, WorkflowType, LogScope
from app.utils.logging import get_logger

logger = get_logger("enhanced_email_chat_service")


class EnhancedEmailChatService:
    """Service for LLM-powered chat with email context integration."""

    def __init__(self):
        self.logger = get_logger("enhanced_email_chat_service")
        self.max_email_context = 8  # Max emails to include in context (increased for better coverage)
        self.max_context_length = 4000  # Max chars for email context
        self._redis_cache = None
        self._query_cache = {}  # In-memory cache for frequent queries
        self.cache_ttl = 1800  # 30 minutes cache TTL

    async def chat_with_email_context(
        self,
        db: AsyncSession,
        user_id: int,
        message: str,
        model_name: Optional[str] = None,
        include_email_search: bool = True,
        max_days_back: int = 1095,  # Default to 3 years instead of 30 days
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process chat message with email context integration.

        Args:
            db: Database session
            user_id: User ID
            message: User's chat message
            model_name: LLM model to use
            include_email_search: Whether to search emails for context
            max_days_back: Maximum days to look back for emails
            conversation_history: Previous conversation messages

        Returns:
            Dict with response and email references
        """
        # Create unified workflow context for email chat
        async with unified_log_service.workflow_context(
            user_id=user_id,
            workflow_type=WorkflowType.CHAT_SESSION,
            workflow_name=f"Email chat: {message[:50]}...",
            scope=LogScope.USER
        ) as workflow_context:

            try:
                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.INFO,
                    message="Starting email chat session",
                    component="enhanced_email_chat_service",
                    extra_metadata={
                        "message_length": len(message),
                        "include_email_search": include_email_search,
                        "max_days_back": max_days_back,
                        "model_name": model_name
                    }
                )

                # Initialize response
                response_data = {
                    "response": "",
                    "email_references": [],
                    "tasks_created": [],
                    "suggested_actions": [],
                    "metadata": {
                        "emails_searched": 0,
                        "emails_referenced": 0,
                        "processing_time_ms": 0
                    }
                }

                start_time = datetime.now()

                # Search for relevant emails if requested
                relevant_emails = []
                if include_email_search:
                    async with unified_log_service.task_context(
                        parent_context=workflow_context,
                        task_name="Search relevant emails",
                        agent_id="email_search_agent"
                    ) as search_context:

                        relevant_emails = await self._search_relevant_emails_with_logging(
                            db, user_id, message, max_days_back, search_context
                        )
                        response_data["metadata"]["emails_searched"] = len(relevant_emails)

                # Generate LLM response with email context
                async with unified_log_service.task_context(
                    parent_context=workflow_context,
                    task_name="Generate LLM response",
                    agent_id="llm_response_agent"
                ) as llm_context:

                    # Build context for LLM
                    email_context = await self._build_email_context(relevant_emails)

                    await unified_log_service.log(
                        context=llm_context,
                        level=LogLevel.INFO,
                        message="Generating LLM response with email context",
                        component="enhanced_email_chat_service",
                        extra_metadata={
                            "email_context_length": len(email_context),
                            "relevant_emails_count": len(relevant_emails)
                        }
                    )

                    # Prepare LLM prompt
                    system_prompt = await self._build_system_prompt(email_context)
                    user_prompt = await self._build_user_prompt(message, relevant_emails)

                    # Check cache for similar LLM responses
                    llm_cache_key = self._generate_cache_key(
                        "llm_response", user_id, system_prompt[:500], user_prompt[:500], model_name or "default"
                    )

                    cached_llm_response = await self._cache_get(llm_cache_key)
                    if cached_llm_response:
                        try:
                            llm_response = json.loads(cached_llm_response)
                            self.logger.debug("Using cached LLM response")
                        except Exception as e:
                            self.logger.debug(f"Failed to parse cached LLM response: {e}")
                            llm_response = await self._generate_llm_response(
                                system_prompt, user_prompt, conversation_history, model_name
                            )
                    else:
                        # Generate LLM response
                        llm_response = await self._generate_llm_response(
                            system_prompt, user_prompt, conversation_history, model_name
                        )
                        # Cache the LLM response
                        try:
                            await self._cache_set(llm_cache_key, json.dumps(llm_response), ttl=3600)  # 1 hour cache
                        except Exception as e:
                            self.logger.debug(f"Failed to cache LLM response: {e}")

                    # Parse response for email references and task creation
                    parsed_response = await self._parse_llm_response(
                        db, user_id, llm_response, relevant_emails
                    )

                    response_data.update(parsed_response)

                    await unified_log_service.log(
                        context=llm_context,
                        level=LogLevel.INFO,
                        message="LLM response generated successfully",
                        component="enhanced_email_chat_service",
                        extra_metadata={
                            "response_length": len(parsed_response.get("response", "")),
                            "email_references": len(parsed_response.get("email_references", [])),
                            "tasks_created": len(parsed_response.get("tasks_created", []))
                        }
                    )

                # Calculate processing time
                end_time = datetime.now()
                response_data["metadata"]["processing_time_ms"] = int(
                    (end_time - start_time).total_seconds() * 1000
                )

                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.INFO,
                    message="Email chat session completed successfully",
                    component="enhanced_email_chat_service",
                    extra_metadata={
                        "processing_time_ms": response_data["metadata"]["processing_time_ms"],
                        "emails_referenced": len(relevant_emails),
                        "response_length": len(response_data.get("response", ""))
                    }
                )

                return response_data

            except Exception as e:
                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.ERROR,
                    message="Email chat session failed",
                    component="enhanced_email_chat_service",
                    error=e
                )
                return {
                    "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                    "email_references": [],
                    "tasks_created": [],
                    "suggested_actions": [],
                    "metadata": {"error": str(e)}
                }

    async def create_task_from_email(
        self,
        db: AsyncSession,
        user_id: int,
        email_id: str,
        task_description: str,
        task_type: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: int = 3
    ) -> Optional[EmailTask]:
        """
        Create a task from an email with LLM-enhanced details.

        Args:
            db: Database session
            user_id: User ID
            email_id: Email UUID
            task_description: Task description
            task_type: Type of task
            due_date: Due date for task
            priority: Task priority (1-5)

        Returns:
            Created EmailTask or None if failed
        """
        try:
            # Get email details
            email_query = select(Email).where(
                and_(Email.id == email_id, Email.user_id == user_id)
            )
            result = await db.execute(email_query)
            email = result.scalar_one_or_none()

            if not email:
                self.logger.warning(f"Email {email_id} not found for user {user_id}")
                return None

            # Generate enhanced task details using LLM
            enhanced_details = await self._enhance_task_details(
                email, task_description, task_type
            )

            # Create task
            email_task = EmailTask(
                email_id=email.id,
                user_id=user_id,
                title=enhanced_details.get("title", task_description[:500]),
                description=enhanced_details.get("description", task_description),
                task_type=task_type or enhanced_details.get("task_type", "general"),
                due_date=due_date or enhanced_details.get("suggested_due_date"),
                priority=priority,
                estimated_duration_minutes=enhanced_details.get("estimated_duration"),
                auto_generated=False,  # User-initiated
                generation_prompt=task_description,
                generation_model=ollama_client.default_model,
                confidence_score=enhanced_details.get("confidence_score", 0.8),
                related_emails=[str(email.id)],
                action_required=enhanced_details.get("action_required", True),
                external_references=enhanced_details.get("external_references", {})
            )

            db.add(email_task)
            await db.commit()
            await db.refresh(email_task)

            self.logger.info(f"Created task {email_task.id} from email {email_id}")
            return email_task

        except Exception as e:
            self.logger.error(f"Error creating task from email: {e}")
            await db.rollback()
            return None

    async def get_email_summary(
        self,
        db: AsyncSession,
        user_id: int,
        email_id: str,
        summary_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        Generate an AI summary of a specific email.

        Args:
            db: Database session
            user_id: User ID
            email_id: Email UUID
            summary_type: Type of summary (standard, detailed, action_items)

        Returns:
            Dict with summary and metadata
        """
        try:
            # Get email with embeddings
            email_query = select(Email).options(
                selectinload(Email.embeddings),
                selectinload(Email.attachments)
            ).where(and_(Email.id == email_id, Email.user_id == user_id))

            result = await db.execute(email_query)
            email = result.scalar_one_or_none()

            if not email:
                return {"error": "Email not found"}

            # Get email context
            context = await email_embedding_service.get_email_context(
                db, email, include_similar=True, include_thread=True
            )

            # Generate summary using LLM
            summary_prompt = self._build_summary_prompt(email, context, summary_type)
            summary = await ollama_client.generate_completion(summary_prompt)

            return {
                "summary": summary,
                "email_id": email_id,
                "summary_type": summary_type,
                "similar_emails": len(context["similar_emails"]),
                "thread_emails": len(context["thread_emails"]),
                "has_attachments": email.has_attachments,
                "metadata": {
                    "subject": email.subject,
                    "sender": email.sender_email,
                    "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                    "importance_score": email.importance_score,
                    "category": email.category
                }
            }

        except Exception as e:
            self.logger.error(f"Error generating email summary: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _search_relevant_emails_with_logging(
        self,
        db: AsyncSession,
        user_id: int,
        message: str,
        max_days_back: int,
        search_context
    ) -> List[Email]:
        """Search relevant emails with unified logging."""
        try:
            await unified_log_service.log(
                context=search_context,
                level=LogLevel.INFO,
                message="Searching for relevant emails",
                component="enhanced_email_chat_service",
                extra_metadata={
                    "message_length": len(message),
                    "max_days_back": max_days_back
                }
            )

            # Call original method
            emails = await self._search_relevant_emails(db, user_id, message, max_days_back)

            await unified_log_service.log(
                context=search_context,
                level=LogLevel.INFO,
                message=f"Found {len(emails)} relevant emails",
                component="enhanced_email_chat_service",
                extra_metadata={"emails_found": len(emails)}
            )

            return emails

        except Exception as e:
            await unified_log_service.log(
                context=search_context,
                level=LogLevel.ERROR,
                message="Failed to search relevant emails",
                component="enhanced_email_chat_service",
                error=e
            )
            return []

    async def _get_redis_cache(self):
        """Get Redis cache connection."""
        if not self._redis_cache:
            try:
                self._redis_cache = redis.from_url("redis://redis:6379/1")
            except Exception as e:
                self.logger.warning(f"Redis cache not available: {e}")
                self._redis_cache = None
        return self._redis_cache

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments."""
        key_parts = [str(arg) for arg in args]
        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    async def _cache_get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        # Try in-memory cache first
        if key in self._query_cache:
            cached_item = self._query_cache[key]
            if datetime.now() - cached_item["timestamp"] < timedelta(seconds=self.cache_ttl):
                return cached_item["value"]
            else:
                del self._query_cache[key]

        # Try Redis cache
        redis_cache = await self._get_redis_cache()
        if redis_cache:
            try:
                return await redis_cache.get(key)
            except Exception as e:
                self.logger.debug(f"Redis cache get failed: {e}")
        return None

    async def _cache_set(self, key: str, value: str, ttl: int = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.cache_ttl

        # Store in in-memory cache
        self._query_cache[key] = {
            "value": value,
            "timestamp": datetime.now()
        }

        # Clean up old in-memory cache entries
        if len(self._query_cache) > 100:
            old_keys = [
                k for k, v in self._query_cache.items()
                if datetime.now() - v["timestamp"] > timedelta(seconds=ttl)
            ]
            for old_key in old_keys:
                del self._query_cache[old_key]

        # Store in Redis cache
        redis_cache = await self._get_redis_cache()
        if redis_cache:
            try:
                await redis_cache.setex(key, ttl, value)
            except Exception as e:
                self.logger.debug(f"Redis cache set failed: {e}")

    async def _search_relevant_emails(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        max_days_back: int
    ) -> List[Email]:
        """Search for emails relevant to the user's query with caching."""
        try:
            # Generate cache key for email search
            cache_key = self._generate_cache_key(
                "email_search", user_id, query[:100], max_days_back
            )

            # Try to get from cache first
            cached_result = await self._cache_get(cache_key)
            if cached_result:
                try:
                    cached_ids = json.loads(cached_result)
                    # Fetch emails by cached IDs with optimized query
                    email_query = select(Email).where(
                        and_(
                            Email.id.in_(cached_ids),
                            Email.user_id == user_id
                        )
                    ).options(
                        # Only load necessary fields for better performance
                        selectinload(Email.embeddings).load_only('embedding_type')
                    ).order_by(
                        desc(Email.sent_at)
                    )

                    result = await db.execute(email_query)
                    cached_emails = result.scalars().all()

                    if cached_emails:
                        self.logger.debug(f"Cache hit for email search: {len(cached_emails)} emails")
                        return cached_emails
                except Exception as e:
                    self.logger.debug(f"Cache parsing failed: {e}")

            # Use embedding service for semantic search with optimizations
            similar_emails = await email_embedding_service.search_similar_emails(
                db=db,
                query_text=query,
                user_id=user_id,
                limit=self.max_email_context * 2,  # Get more for better filtering
                similarity_threshold=0.15,  # Much lower threshold for better recall
                temporal_boost=0.2,
                importance_boost=0.3
            )

            # Filter by date range and optimize
            from datetime import timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_days_back)
            relevant_emails = []
            seen_threads = set()  # Avoid duplicate thread emails

            for email, similarity_score in similar_emails:
                # Handle timezone-aware comparison
                email_date = email.received_at
                if email_date and email_date.tzinfo is None:
                    email_date = email_date.replace(tzinfo=timezone.utc)

                if email_date and email_date >= cutoff_date:
                    # Avoid duplicate thread emails for better performance
                    if email.thread_id not in seen_threads:
                        seen_threads.add(email.thread_id)
                        # Add similarity score to email object for context
                        email._similarity_score = similarity_score
                        relevant_emails.append(email)

                        # Stop once we have enough emails
                        if len(relevant_emails) >= self.max_email_context:
                            break

            # Cache the results for future use
            if relevant_emails:
                email_ids = [str(email.id) for email in relevant_emails]
                try:
                    await self._cache_set(cache_key, json.dumps(email_ids))
                except Exception as e:
                    self.logger.debug(f"Failed to cache email search results: {e}")

            return relevant_emails

        except Exception as e:
            self.logger.error(f"Error searching relevant emails: {e}")
            return []

    async def _build_email_context(self, emails: List[Email]) -> str:
        """Build email context string for LLM."""
        if not emails:
            return "No relevant emails found."

        context_parts = []
        total_length = 0

        for i, email in enumerate(emails, 1):
            similarity = getattr(email, '_similarity_score', 0.0)

            email_summary = f"""
Email {i} (Similarity: {similarity:.2f}):
- Subject: {email.subject or 'No subject'}
- From: {email.sender_email} ({email.sender_name or 'Unknown'})
- Date: {email.sent_at.strftime('%Y-%m-%d %H:%M') if email.sent_at else 'Unknown'}
- Category: {email.category or 'General'}
- Important: {'Yes' if email.is_important else 'No'}
- Body Preview: {(email.body_text or '')[:300]}...
"""

            if total_length + len(email_summary) > self.max_context_length:
                break

            context_parts.append(email_summary)
            total_length += len(email_summary)

        return "\n---\n".join(context_parts)

    async def _build_system_prompt(self, email_context: str) -> str:
        """Build system prompt for LLM with email context."""
        return f"""You are an intelligent email assistant that helps users understand and manage their emails. You have access to the user's email data and can reference specific emails in your responses.

IMPORTANT GUIDELINES:
1. When referencing emails, use the format: [Email X] where X is the email number from the context
2. Provide helpful summaries and insights about the emails
3. Suggest actionable tasks when appropriate
4. Be concise but informative
5. If asked to create tasks, suggest specific, actionable items with estimated timeframes
6. Respect user privacy - only reference information that's directly relevant

EMAIL CONTEXT:
{email_context}

When creating tasks, format them as:
TASK: [Title] - [Description] (Priority: 1-5, Estimated: X minutes, Due: YYYY-MM-DD or "flexible")

Guidelines for task generation:
- For meeting requests: Create calendar tasks with specific dates
- For purchase confirmations: Create tracking/delivery tasks
- For deadlines: Create reminder tasks with proper due dates
- For follow-ups: Create communication tasks with context
- For documents: Create review/action tasks

When referencing emails, include the email number and key details like sender and subject."""

    async def _build_user_prompt(self, message: str, relevant_emails: List[Email]) -> str:
        """Build user prompt with detailed email references and content."""
        email_refs = ""
        if relevant_emails:
            email_refs = f"\n\nRELEVANT EMAILS ({len(relevant_emails)} found):\n"
            for i, email in enumerate(relevant_emails, 1):
                similarity = getattr(email, '_similarity_score', 0.0)

                # Basic email metadata
                subject = email.subject or "No subject"
                sender = f"{email.sender_name or email.sender_email}" if email.sender_email else "Unknown"
                date_str = email.sent_at.strftime("%Y-%m-%d") if email.sent_at else "Unknown date"

                # Extract meaningful content excerpt
                content_preview = ""
                if email.body_text:
                    # Clean up and extract meaningful content
                    clean_text = email.body_text.replace('\n', ' ').replace('\r', '').strip()
                    if len(clean_text) > 150:
                        content_preview = clean_text[:150] + "..."
                    else:
                        content_preview = clean_text
                elif email.snippet:
                    content_preview = email.snippet[:150].strip()

                email_refs += f"[{i}] Subject: \"{subject}\"\n"
                email_refs += f"    From: {sender} | Date: {date_str} | Match: {similarity:.1%}\n"
                if content_preview:
                    email_refs += f"    Content: {content_preview}\n"
                email_refs += "\n"

        return f"User Query: {message}{email_refs}"

    async def _generate_llm_response(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]],
        model_name: Optional[str]
    ) -> str:
        """Generate LLM response with conversation context."""
        try:
            # Build conversation context
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages
                    messages.append(msg)

            messages.append({"role": "user", "content": user_prompt})

            # Generate response
            ollama_response = await ollama_client.chat(
                messages=messages,
                model=model_name or ollama_client.default_model
            )

            # Extract the actual message content from the Ollama response
            if isinstance(ollama_response, dict) and "message" in ollama_response:
                return ollama_response["message"].get("content", str(ollama_response))
            elif isinstance(ollama_response, str):
                return ollama_response
            else:
                return str(ollama_response)

        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}", exc_info=True)
            return "I apologize, but I'm having trouble processing your request right now."

    async def _parse_llm_response(
        self,
        db: AsyncSession,
        user_id: int,
        response: str,
        relevant_emails: List[Email]
    ) -> Dict[str, Any]:
        """Parse LLM response for email references, task creation, and thinking content."""
        try:
            # Process thinking content
            thinking_content = []
            clean_response = response

            # Extract thinking sections
            import re
            thinking_pattern = r'<think>(.*?)</think>'
            thinking_matches = re.findall(thinking_pattern, response, re.DOTALL | re.IGNORECASE)

            if thinking_matches:
                for i, thinking in enumerate(thinking_matches):
                    thinking_content.append({
                        "id": f"thinking_{i+1}",
                        "content": thinking.strip()
                    })

                # Remove thinking sections from the main response
                clean_response = re.sub(thinking_pattern, '', response, flags=re.DOTALL | re.IGNORECASE)
                clean_response = clean_response.strip()

            # Also handle other thinking tag formats
            alt_thinking_patterns = [
                r'<thinking>(.*?)</thinking>',
                r'\*thinking\*(.*?)\*/thinking\*'
            ]

            for pattern in alt_thinking_patterns:
                matches = re.findall(pattern, clean_response, re.DOTALL | re.IGNORECASE)
                if matches:
                    for i, thinking in enumerate(matches):
                        thinking_content.append({
                            "id": f"alt_thinking_{len(thinking_content)+i+1}",
                            "content": thinking.strip()
                        })
                    clean_response = re.sub(pattern, '', clean_response, flags=re.DOTALL | re.IGNORECASE)
                    clean_response = clean_response.strip()
            # Extract email references
            email_references = []
            import re

            # Find email references like [1], [Email 1], etc.
            email_refs = re.findall(r'\[(?:Email )?(\d+)\]', clean_response)
            for ref in email_refs:
                email_index = int(ref) - 1  # Convert to 0-based index
                if 0 <= email_index < len(relevant_emails):
                    email = relevant_emails[email_index]
                    email_references.append({
                        "email_id": str(email.id),
                        "subject": email.subject,
                        "sender": email.sender_email,
                        "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                        "similarity_score": getattr(email, '_similarity_score', 0.0)
                    })

            # Extract suggested tasks (not auto-created) with enhanced format
            task_suggestions = []
            # Try enhanced format first: TASK: [Title] - [Description] (Priority: X, Estimated: X minutes, Due: DATE)
            enhanced_pattern = r'TASK: (.+?) - (.+?) \(Priority: (\d+), Estimated: (\d+) minutes, Due: ([^)]+)\)'
            enhanced_matches = re.findall(enhanced_pattern, clean_response)

            for match in enhanced_matches:
                title, description, priority, duration, due_date = match
                task_data = {
                    "title": title.strip(),
                    "description": description.strip(),
                    "priority": int(priority),
                    "estimated_duration": int(duration),
                    "suggested": True,  # Mark as suggested, not created
                    "source": "email_chat",
                    "status": "suggested"
                }

                # Parse due date
                if due_date.strip().lower() != "flexible":
                    try:
                        from datetime import datetime
                        parsed_date = datetime.strptime(due_date.strip(), "%Y-%m-%d")
                        task_data["due_date"] = parsed_date.isoformat()
                    except ValueError:
                        # If parsing fails, leave due_date empty
                        pass

                task_suggestions.append(task_data)

            # Fallback to old format if no enhanced tasks found
            if not task_suggestions:
                old_pattern = r'TASK: (.+?) - (.+?) \(Priority: (\d+), Estimated: (\d+) minutes\)'
                old_matches = re.findall(old_pattern, clean_response)
                for match in old_matches:
                    title, description, priority, duration = match
                    task_suggestions.append({
                        "title": title.strip(),
                        "description": description.strip(),
                        "priority": int(priority),
                        "estimated_duration": int(duration),
                        "suggested": True,
                        "source": "email_chat",
                        "status": "suggested"
                    })

            # Generate suggested actions (use clean response without thinking content)
            suggested_actions = await self._generate_suggested_actions(
                clean_response, relevant_emails
            )

            return {
                "response": clean_response,  # Use cleaned response without thinking tags
                "thinking_content": thinking_content,  # Include extracted thinking content
                "email_references": email_references,
                "task_suggestions": task_suggestions,  # Change from tasks_created to task_suggestions
                "tasks_created": [],  # Empty - no auto-created tasks
                "suggested_actions": suggested_actions,
                "metadata": {
                    "emails_referenced": len(email_references),
                    "tasks_suggested": len(task_suggestions)
                }
            }

        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {
                "response": response,
                "email_references": [],
                "tasks_created": [],
                "suggested_actions": []
            }

    async def _enhance_task_details(
        self,
        email: Email,
        task_description: str,
        task_type: Optional[str]
    ) -> Dict[str, Any]:
        """Use LLM to enhance task details."""
        try:
            prompt = f"""
Based on this email and task description, provide enhanced task details:

EMAIL:
Subject: {email.subject}
From: {email.sender_email}
Date: {email.sent_at}
Body: {(email.body_text or '')[:500]}...

TASK DESCRIPTION: {task_description}

Please provide a JSON response with:
- title: Concise task title (max 100 chars)
- description: Detailed description
- task_type: Category (meeting, follow_up, review, research, etc.)
- estimated_duration: Minutes to complete
- suggested_due_date: ISO format date (or null)
- action_required: true/false
- confidence_score: 0.0-1.0 based on email clarity
- external_references: Any URLs, contacts, or external items mentioned

Response format: {{"title": "...", "description": "...", ...}}
"""

            response = await ollama_client.generate_completion(prompt)

            # Try to parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback to basic enhancement
                return {
                    "title": task_description[:100],
                    "description": task_description,
                    "task_type": task_type or "general",
                    "estimated_duration": 30,
                    "confidence_score": 0.5
                }

        except Exception as e:
            self.logger.error(f"Error enhancing task details: {e}")
            return {"title": task_description[:100], "description": task_description}

    def _build_summary_prompt(self, email: Email, context: Dict[str, Any], summary_type: str) -> str:
        """Build prompt for email summarization."""
        thread_info = ""
        if context["thread_emails"]:
            thread_info = f"This email is part of a thread with {len(context['thread_emails'])} other messages."

        similar_info = ""
        if context["similar_emails"]:
            similar_info = f"Found {len(context['similar_emails'])} similar emails in the mailbox."

        prompts = {
            "standard": f"Provide a concise summary of this email in 2-3 sentences.",
            "detailed": f"Provide a detailed analysis including key points, action items, and context.",
            "action_items": f"Extract all action items, tasks, and follow-ups mentioned in this email."
        }

        return f"""
{prompts.get(summary_type, prompts["standard"])}

EMAIL:
Subject: {email.subject}
From: {email.sender_email} ({email.sender_name or 'Unknown'})
Date: {email.sent_at}
Body: {email.body_text or 'No text content'}

{thread_info}
{similar_info}

Attachments: {email.attachment_count if email.has_attachments else 0}
Category: {email.category or 'General'}
Importance: {email.importance_score:.2f}
"""

    async def _generate_suggested_actions(
        self,
        response: str,
        relevant_emails: List[Email]
    ) -> List[str]:
        """Generate suggested actions based on the conversation."""
        actions = []

        # Basic action suggestions based on response content
        if "task" in response.lower() or "todo" in response.lower():
            actions.append("Create Task")

        if "schedule" in response.lower() or "meeting" in response.lower():
            actions.append("Schedule Meeting")

        if relevant_emails:
            actions.append("Mark as Important")

        return actions


# Global instance
enhanced_email_chat_service = EnhancedEmailChatService()
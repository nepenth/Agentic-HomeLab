from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import json

from app.db.models.chat_session import ChatSession, ChatMessage
from app.services.ollama_client import sync_ollama_client as ollama_client
from app.services.prompt_templates import prompt_manager
from app.utils.logging import get_logger

logger = get_logger("chat_service")


class ChatService:
    """Service for managing interactive LLM chat sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        session_type: str,
        model_name: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> ChatSession:
        """Create a new chat session."""
        try:
            session = ChatSession(
                session_type=session_type,
                user_id=user_id,
                model_name=model_name,
                title=title,
                config=config or {}
            )

            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

            # Add initial system message if template exists
            system_prompt = prompt_manager.get_system_prompt(session_type)
            if system_prompt:
                await self.add_message(
                    session_id=session.id,
                    role="system",
                    content=system_prompt,
                    message_type="system"
                )

            # Add initial assistant greeting for agent creation
            if session_type == "agent_creation":
                greeting = prompt_manager.render_template("agent_creation", {
                    "user_input": "",
                    "task_summary": "",
                    "suggested_agent_type": "",
                    "suggested_model": model_name,
                    "suggested_tools": "",
                    "valid_items": "",
                    "attention_items": "",
                    "invalid_items": "",
                    "security_notes": "",
                    "performance_tips": "",
                    "model": model_name,
                    "available_models": ""
                })

                # Extract the greeting from the template
                greeting_text = self._extract_greeting_from_template(greeting)
                if greeting_text:
                    await self.add_message(
                        session_id=session.id,
                        role="assistant",
                        content=greeting_text,
                        message_type="greeting"
                    )

            logger.info(f"Created chat session: {session.id} ({session_type})")
            return session

        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            await self.db.rollback()
            raise

    def _extract_greeting_from_template(self, template_content: str) -> str:
        """Extract greeting text from template."""
        # Simple extraction - in production, this would parse XML properly
        if "Hello! I'm your AI assistant" in template_content:
            start = template_content.find("Hello! I'm your AI assistant")
            end = template_content.find("Feel free to describe", start)
            if end > start:
                return template_content[start:end + len("Feel free to describe your use case in natural language, and I'll guide you through the setup process.")]
        return ""

    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        try:
            result = await self.db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        session_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """List chat sessions with optional filtering."""
        try:
            query = select(ChatSession)

            if user_id:
                query = query.where(ChatSession.user_id == user_id)
            if session_type:
                query = query.where(ChatSession.session_type == session_type)
            if status:
                query = query.where(ChatSession.status == status)

            query = query.order_by(ChatSession.updated_at.desc()).limit(limit).offset(offset)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        message_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """Add a message to a chat session."""
        try:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                message_type=message_type,
                metadata=metadata or {}
            )

            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)

            # Update session's updated_at timestamp
            await self.db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(updated_at=datetime.utcnow())
            )
            await self.db.commit()

            logger.debug(f"Added message to session {session_id}: {role} ({message_type})")
            return message

        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def get_messages(
        self,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get messages for a chat session."""
        try:
            result = await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []

    async def send_message(
        self,
        session_id: UUID,
        user_message: str,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a user message and get AI response."""
        try:
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            if not session.is_active:
                raise ValueError(f"Session {session_id} is not active")

            # Add user message
            await self.add_message(
                session_id=session_id,
                role="user",
                content=user_message,
                message_type="user_input"
            )

            # Get conversation history
            messages = await self.get_messages(session_id)
            conversation = self._format_conversation_for_ollama(messages)

            # Use specified model or session's model
            model = model_name or session.model_name

            # Get AI response using synchronous client
            response = ollama_client.chat(
                messages=conversation,
                model=model,
                options=session.config.get("ollama_options", {})
            )

            ai_response = response.get("message", {}).get("content", "")

            # Extract comprehensive performance metrics
            performance_metrics = self._extract_performance_metrics(response, conversation)

            # Add AI response to session
            await self.add_message(
                session_id=session_id,
                role="assistant",
                content=ai_response,
                message_type="ai_response",
                metadata={
                    "model": model,
                    **performance_metrics
                }
            )

            logger.info(f"Processed message for session {session_id} with model {model}")
            return {
                "session_id": str(session_id),
                "response": ai_response,
                "model": model,
                "performance_metrics": performance_metrics
            }

        except Exception as e:
            logger.error(f"Failed to send message for session {session_id}: {e}")
            # Add error message to session
            await self.add_message(
                session_id=session_id,
                role="assistant",
                content=f"I apologize, but I encountered an error: {str(e)}",
                message_type="error"
            )
            raise

    def _extract_performance_metrics(self, ollama_response: Dict[str, Any], conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract comprehensive performance metrics from Ollama response."""
        metrics = {}

        # Basic timing metrics (convert from nanoseconds to seconds)
        total_duration = ollama_response.get("total_duration", 0) / 1e9
        load_duration = ollama_response.get("load_duration", 0) / 1e9
        prompt_eval_duration = ollama_response.get("prompt_eval_duration", 0) / 1e9
        eval_duration = ollama_response.get("eval_duration", 0) / 1e9

        # Token metrics
        prompt_tokens = ollama_response.get("prompt_eval_count", 0)
        response_tokens = ollama_response.get("eval_count", 0)
        total_tokens = prompt_tokens + response_tokens

        # Calculate tokens per second
        tokens_per_second = 0.0
        if eval_duration > 0:
            tokens_per_second = response_tokens / eval_duration

        # Context length (approximate from conversation)
        context_length = sum(len(msg.get("content", "")) for msg in conversation)

        metrics.update({
            "response_time_seconds": round(total_duration, 3),
            "load_time_seconds": round(load_duration, 3),
            "prompt_eval_time_seconds": round(prompt_eval_duration, 3),
            "generation_time_seconds": round(eval_duration, 3),
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": total_tokens,
            "tokens_per_second": round(tokens_per_second, 2),
            "context_length_chars": context_length,
            "model_name": ollama_response.get("model", ""),
            "timestamp": datetime.utcnow().isoformat()
        })

        return metrics

    def _format_conversation_for_ollama(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Format chat messages for Ollama API."""
        formatted = []

        for msg in messages:
            if msg.role in ["user", "assistant", "system"]:
                formatted.append({
                    "role": msg.role,
                    "content": msg.content
                })

        return formatted

    async def update_session_status(
        self,
        session_id: UUID,
        status: str,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """Update session status."""
        try:
            update_data = {"status": status}
            if completed_at:
                update_data["completed_at"] = completed_at
            if status in ["completed", "archived"]:
                update_data["is_active"] = False
            elif status == "resumable":
                # Keep session active and resumable
                update_data["is_active"] = True
                update_data["is_resumable"] = True

            await self.db.execute(
                update(ChatSession)
                .where(ChatSession.id == session_id)
                .values(**update_data)
            )
            await self.db.commit()

            logger.info(f"Updated session {session_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update session {session_id} status: {e}")
            await self.db.rollback()
            return False

    async def cleanup_old_sessions(self, retention_days: int = 365):
        """Clean up chat sessions and messages older than retention period."""
        try:
            from sqlalchemy import and_, or_
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Find sessions that are completed/archived and older than retention period
            # But keep active/resumable sessions regardless of age
            result = await self.db.execute(
                select(ChatSession).where(
                    and_(
                        or_(
                            ChatSession.status.in_(["completed", "archived"]),
                            ChatSession.is_active == False
                        ),
                        ChatSession.created_at < cutoff_date
                    )
                )
            )
            old_sessions = result.scalars().all()

            deleted_count = 0
            for session in old_sessions:
                # Delete messages first
                await self.db.execute(
                    delete(ChatMessage).where(ChatMessage.session_id == session.id)
                )
                # Delete session
                await self.db.delete(session)
                deleted_count += 1

            await self.db.commit()

            logger.info(f"Cleaned up {deleted_count} chat sessions older than {retention_days} days")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old chat sessions: {e}")
            await self.db.rollback()
            return 0

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a chat session and all its messages."""
        try:
            # Delete messages first (cascade should handle this, but being explicit)
            await self.db.execute(
                delete(ChatMessage).where(ChatMessage.session_id == session_id)
            )

            # Delete session
            await self.db.execute(
                delete(ChatSession).where(ChatSession.id == session_id)
            )

            await self.db.commit()

            logger.info(f"Deleted chat session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            await self.db.rollback()
            return False

    async def get_session_stats(self, session_id: UUID) -> Dict[str, Any]:
        """Get statistics for a chat session."""
        try:
            # Get message count
            result = await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
            )
            messages = result.scalars().all()

            stats = {
                "total_messages": len(messages),
                "user_messages": len([m for m in messages if m.role == "user"]),
                "assistant_messages": len([m for m in messages if m.role == "assistant"]),
                "system_messages": len([m for m in messages if m.role == "system"]),
                "total_tokens": sum(m.token_count or 0 for m in messages),
                "message_types": {}
            }

            # Count message types
            for msg in messages:
                msg_type = msg.message_type or "unknown"
                stats["message_types"][msg_type] = stats["message_types"].get(msg_type, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"Failed to get stats for session {session_id}: {e}")
            return {}


class SyncChatService:
    """Synchronous version of ChatService for contexts where async is problematic."""

    def __init__(self):
        from app.db.database import get_sync_session
        self.db_session = get_sync_session()

    def create_session_sync(self, session_type: str, model_name: str, user_id: Optional[str] = None, title: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Create a new chat session synchronously."""
        try:
            from app.db.models.chat_session import ChatSession
            session = ChatSession(
                session_type=session_type,
                user_id=user_id,
                model_name=model_name,
                title=title,
                config=config or {}
            )

            self.db_session.add(session)
            self.db_session.commit()
            self.db_session.refresh(session)

            # Add initial system message if template exists
            system_prompt = prompt_manager.get_system_prompt(session_type)
            if system_prompt:
                self.add_message_sync(
                    session_id=session.id,
                    role="system",
                    content=system_prompt,
                    message_type="system"
                )

            return session

        except Exception as e:
            self.db_session.rollback()
            raise

    def add_message_sync(self, session_id, role: str, content: str, message_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Add a message synchronously."""
        try:
            from app.db.models.chat_session import ChatMessage
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                message_type=message_type,
                metadata=metadata or {}
            )

            self.db_session.add(message)
            self.db_session.commit()
            self.db_session.refresh(message)

            return message

        except Exception as e:
            self.db_session.rollback()
            raise

    def send_message_sync(self, session_id, user_message: str):
        """Send a message synchronously."""
        try:
            from app.db.models.chat_session import ChatSession, ChatMessage
            from app.services.ollama_client import sync_ollama_client

            # Get session
            session = self.db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise ValueError(f"Session {session_id} not found")

            if not session.is_active:
                raise ValueError(f"Session {session_id} is not active")

            # Add user message
            self.add_message_sync(
                session_id=session_id,
                role="user",
                content=user_message,
                message_type="user_input"
            )

            # Get conversation history
            messages = self.db_session.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
            conversation = self._format_conversation_for_ollama(messages)

            # Use specified model or session's model
            model = session.model_name

            # Get AI response using sync client
            response = sync_ollama_client.chat(
                messages=conversation,
                model=model,
                options=session.config.get("ollama_options", {}),
                context_id=f"chat_session_{session_id}"
            )

            ai_response = response.get("message", {}).get("content", "")

            # Extract comprehensive performance metrics
            performance_metrics = self._extract_performance_metrics(response, conversation)

            # Add AI response to session
            self.add_message_sync(
                session_id=session_id,
                role="assistant",
                content=ai_response,
                message_type="ai_response",
                metadata={
                    "model": model,
                    **performance_metrics
                }
            )

            return {
                "session_id": str(session_id),
                "response": ai_response,
                "model": model,
                "performance_metrics": performance_metrics
            }

        except Exception as e:
            # Add error message to session
            try:
                self.add_message_sync(
                    session_id=session_id,
                    role="assistant",
                    content=f"I apologize, but I encountered an error: {str(e)}",
                    message_type="error"
                )
            except:
                pass  # Don't let error logging fail the main operation
            raise

    def _format_conversation_for_ollama(self, messages):
        """Format chat messages for Ollama API."""
        formatted = []

        for msg in messages:
            if msg.role in ["user", "assistant", "system"]:
                formatted.append({
                    "role": msg.role,
                    "content": msg.content
                })

        return formatted

    def _extract_performance_metrics(self, ollama_response: Dict[str, Any], conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract comprehensive performance metrics from Ollama response."""
        metrics = {}

        # Basic timing metrics (convert from nanoseconds to seconds)
        total_duration = ollama_response.get("total_duration", 0) / 1e9
        load_duration = ollama_response.get("load_duration", 0) / 1e9
        prompt_eval_duration = ollama_response.get("prompt_eval_duration", 0) / 1e9
        eval_duration = ollama_response.get("eval_duration", 0) / 1e9

        # Token metrics
        prompt_tokens = ollama_response.get("prompt_eval_count", 0)
        response_tokens = ollama_response.get("eval_count", 0)
        total_tokens = prompt_tokens + response_tokens

        # Calculate tokens per second
        tokens_per_second = 0.0
        if eval_duration > 0:
            tokens_per_second = response_tokens / eval_duration

        # Context length (approximate from conversation)
        context_length = sum(len(msg.get("content", "")) for msg in conversation)

        metrics.update({
            "response_time_seconds": round(total_duration, 3),
            "load_time_seconds": round(load_duration, 3),
            "prompt_eval_time_seconds": round(prompt_eval_duration, 3),
            "generation_time_seconds": round(eval_duration, 3),
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": total_tokens,
            "tokens_per_second": round(tokens_per_second, 2),
            "context_length_chars": context_length,
            "model_name": ollama_response.get("model", ""),
            "timestamp": datetime.utcnow().isoformat()
        })

        return metrics

    def close(self):
        """Close the database session."""
        if self.db_session:
            self.db_session.close()


# Global instance (will be initialized with database session when needed)
chat_service = None
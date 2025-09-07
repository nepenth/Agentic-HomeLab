"""
AI-Assisted Agent Builder Service for dynamic agent creation.
"""
import uuid
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.schemas.agent_schema import AgentSchema, DataModelDefinition, ProcessingStep, ProcessingPipeline, ToolDefinition
from app.services.ollama_client import ollama_client
from app.services.schema_manager import SchemaManager
from app.services.conversation_templates import (
    template_manager,
    question_generator,
    schema_preview_generator
)
from app.db.models.agent_type import AgentBuilderSession, AgentType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BuilderSession:
    """Represents an AI-assisted agent builder session."""

    def __init__(self, session_id: str, initial_description: str):
        self.id = session_id
        self.initial_description = initial_description
        self.conversation_history: List[Dict[str, Any]] = []
        self.requirements: Dict[str, Any] = {}
        self.generated_schema: Optional[Dict[str, Any]] = None
        self.status = "active"
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.conversation_history.append(message)
        self.updated_at = datetime.utcnow()

    def update_requirements(self, new_requirements: Dict[str, Any]):
        """Update the requirements based on conversation."""
        self.requirements.update(new_requirements)
        self.updated_at = datetime.utcnow()

    def set_generated_schema(self, schema: Dict[str, Any]):
        """Set the generated schema."""
        self.generated_schema = schema
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "initial_description": self.initial_description,
            "conversation_history": self.conversation_history,
            "requirements": self.requirements,
            "generated_schema": self.generated_schema,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ConversationResponse:
    """Response from a conversation interaction."""

    def __init__(self, message: str, questions: Optional[List[str]] = None,
                 suggestions: Optional[List[str]] = None, schema_ready: bool = False):
        self.message = message
        self.questions = questions or []
        self.suggestions = suggestions or []
        self.schema_ready = schema_ready

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "questions": self.questions,
            "suggestions": self.suggestions,
            "schema_ready": self.schema_ready
        }


class AgentBuilderService:
    """Service for AI-assisted agent creation through conversation."""

    def __init__(self, db_session: AsyncSession, schema_manager: SchemaManager):
        self.db = db_session
        self.schema_manager = schema_manager
        self.sessions: Dict[str, BuilderSession] = {}

    async def start_session(self, user_description: str, created_by: Optional[str] = None) -> BuilderSession:
        """
        Start a new AI-assisted agent builder session.

        Args:
            user_description: User's initial description of the desired agent
            created_by: User who started the session

        Returns:
            BuilderSession instance
        """
        session_id = str(uuid.uuid4())
        session = BuilderSession(session_id, user_description)

        # Add initial user message
        session.add_message("user", user_description)

        # Analyze initial requirements using LLM
        analysis_response = await self._analyze_initial_requirements(user_description)

        # Add AI response
        session.add_message("assistant", analysis_response.message, {
            "questions": analysis_response.questions,
            "suggestions": analysis_response.suggestions
        })

        # Update requirements based on analysis
        initial_requirements = await self._extract_requirements_from_description(user_description)
        session.update_requirements(initial_requirements)

        # Save to database
        await self._save_session_to_db(session, created_by)

        # Cache in memory
        self.sessions[session_id] = session

        logger.info(f"Started new builder session: {session_id}")
        return session

    async def continue_conversation(self, session_id: str, user_input: str) -> ConversationResponse:
        """
        Continue a conversation in an existing session.

        Args:
            session_id: The session ID
            user_input: User's new input

        Returns:
            ConversationResponse with AI response
        """
        # Load session
        session = await self._load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Add user message
        session.add_message("user", user_input)

        # Get conversation context
        context = self._build_conversation_context(session)

        # Generate AI response
        response = await self._generate_conversation_response(context, user_input, session.requirements)

        # Add AI response to session
        session.add_message("assistant", response.message, {
            "questions": response.questions,
            "suggestions": response.suggestions,
            "schema_ready": response.schema_ready
        })

        # Update requirements if new information was provided
        updated_requirements = await self._extract_requirements_from_input(user_input, session.requirements)
        if updated_requirements != session.requirements:
            session.update_requirements(updated_requirements)

        # Save session
        await self._save_session_to_db(session)

        logger.info(f"Continued conversation in session: {session_id}")
        return response

    async def generate_schema(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a complete agent schema from the conversation.

        Args:
            session_id: The session ID

        Returns:
            Generated agent schema dictionary
        """
        session = await self._load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Generate schema using LLM
        schema = await self._generate_schema_from_conversation(session)

        # Validate the generated schema
        validation_result = await self.schema_manager.validate_schema(schema)
        if not validation_result.is_valid:
            # Try to fix validation errors
            schema = await self._fix_schema_validation_errors(schema, validation_result.errors)

        # Set the generated schema
        session.set_generated_schema(schema)
        session.status = "completed"

        # Save session
        await self._save_session_to_db(session)

        logger.info(f"Generated schema for session: {session_id}")
        return schema

    async def get_session(self, session_id: str) -> Optional[BuilderSession]:
        """Get a session by ID."""
        return await self._load_session(session_id)

    async def get_schema_preview(self, session_id: str) -> Dict[str, Any]:
        """
        Get a schema preview for the current session.

        Args:
            session_id: The session ID

        Returns:
            Schema preview dictionary
        """
        session = await self._load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Generate schema preview based on current requirements
        return schema_preview_generator.generate_preview(session.requirements)

    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        Get all available conversation templates.

        Returns:
            List of template information
        """
        templates = template_manager.get_all_templates()
        return [
            {
                "agent_type": template.agent_type,
                "name": template.agent_type.replace("_", " ").title(),
                "keywords": template.keywords,
                "description": f"Template for {template.agent_type.replace('_', ' ')} agents"
            }
            for template in templates
        ]

    async def list_sessions(self, created_by: Optional[str] = None) -> List[BuilderSession]:
        """List all sessions, optionally filtered by creator."""
        query = select(AgentBuilderSession)
        if created_by:
            query = query.where(AgentBuilderSession.created_by == created_by)

        result = await self.db.execute(query)
        db_sessions = result.scalars().all()

        sessions = []
        for db_session in db_sessions:
            session = BuilderSession(
                str(getattr(db_session, 'id')),
                str(getattr(db_session, 'initial_description', ''))
            )
            session.conversation_history = getattr(db_session, 'conversation_history', []) or []
            session.requirements = getattr(db_session, 'requirements', {}) or {}
            session.generated_schema = getattr(db_session, 'generated_schema', None)
            session.status = str(getattr(db_session, 'status', 'active'))
            session.created_at = getattr(db_session, 'created_at', datetime.utcnow())
            session.updated_at = getattr(db_session, 'updated_at', datetime.utcnow())
            sessions.append(session)

        return sessions

    async def _analyze_initial_requirements(self, description: str) -> ConversationResponse:
        """Analyze initial user description and generate response using templates."""
        # First, try to match against conversation templates
        template = template_manager.find_matching_template(description)

        if template:
            # Use template-based response
            message = f"I understand you want to create a {template.agent_type.replace('_', ' ')} agent. This is a great fit for your needs!"

            # Get template questions and suggestions
            questions = template.questions[:3]  # Limit to first 3 questions
            suggestions = template.suggestions[:4]  # Limit to first 4 suggestions

            return ConversationResponse(
                message=message,
                questions=questions,
                suggestions=suggestions,
                schema_ready=False
            )
        else:
            # Fall back to LLM analysis for unrecognized patterns
            prompt = f"""
            You are an AI assistant helping users create custom agents. Analyze this user description and provide a helpful response.

            User Description: "{description}"

            Your task:
            1. Understand what kind of agent the user wants
            2. Identify any missing information needed to create the agent
            3. Suggest appropriate features and capabilities
            4. Ask clarifying questions if needed

            Respond in JSON format with:
            {{
                "message": "Your friendly response to the user",
                "questions": ["List of clarifying questions"],
                "suggestions": ["List of suggested features or capabilities"],
                "schema_ready": false
            }}
            """

            try:
                response = await ollama_client.generate(
                    prompt=prompt,
                    model="llama2",
                    format="json"
                )

                result = json.loads(response.get("response", "{}"))

                return ConversationResponse(
                    message=result.get("message", "I understand you want to create an agent. Let me help you with that."),
                    questions=result.get("questions", []),
                    suggestions=result.get("suggestions", []),
                    schema_ready=result.get("schema_ready", False)
                )

            except Exception as e:
                logger.error(f"Error analyzing requirements: {e}")
                return ConversationResponse(
                    message="I understand you want to create an agent. Could you tell me more about what it should do?",
                    questions=["What specific tasks should the agent perform?", "What kind of data will it work with?"],
                    suggestions=["Data processing", "API integration", "File management"]
                )

    async def _generate_conversation_response(self, context: str, user_input: str, current_requirements: Dict[str, Any]) -> ConversationResponse:
        """Generate a conversation response based on context using intelligent question generation."""
        # First, try intelligent question generation
        followup_questions = question_generator.generate_followup_questions(user_input, current_requirements)

        # Assess completeness of requirements
        completeness = question_generator.assess_completeness(current_requirements)

        # Generate response message
        if completeness["ready_for_schema"]:
            message = "Great! I have enough information to create your agent schema. Would you like me to generate it now?"
            schema_ready = True
        else:
            missing_fields = completeness["missing_fields"]
            if missing_fields:
                message = f"I need a bit more information about: {', '.join(missing_fields)}. Could you help me with that?"
            else:
                message = "Thanks for the additional information. I'm learning more about your agent requirements."
            schema_ready = False

        # Add intelligent suggestions based on user input
        suggestions = []
        if "email" in user_input.lower():
            suggestions.extend(["Email categorization", "Priority scoring", "Follow-up detection"])
        elif "data" in user_input.lower():
            suggestions.extend(["Data validation", "Format conversion", "Quality assurance"])
        elif "api" in user_input.lower():
            suggestions.extend(["Authentication handling", "Rate limiting", "Error recovery"])

        # Combine intelligent questions with any additional questions
        all_questions = followup_questions[:2]  # Limit to 2 intelligent questions

        # If we don't have enough questions, add generic ones
        if len(all_questions) < 2 and not completeness["ready_for_schema"]:
            generic_questions = [
                "What specific outcome are you hoping to achieve?",
                "Are there any particular tools or services you want to integrate?",
                "How should the agent handle errors or unexpected situations?"
            ]
            # Add questions for missing fields
            for field in completeness["missing_fields"][:2]:
                if field == "data_sources":
                    all_questions.append("What data or information will your agent work with?")
                elif field == "processing_steps":
                    all_questions.append("What should the agent do with the data?")
                elif field == "output_format":
                    all_questions.append("What should be the result or output of the agent?")

            # Fill remaining slots with generic questions
            for q in generic_questions:
                if len(all_questions) < 3 and q not in all_questions:
                    all_questions.append(q)

        return ConversationResponse(
            message=message,
            questions=all_questions[:3],  # Limit to 3 questions max
            suggestions=suggestions[:3],  # Limit to 3 suggestions max
            schema_ready=schema_ready
        )

    async def _generate_schema_from_conversation(self, session: BuilderSession) -> Dict[str, Any]:
        """Generate a complete agent schema from the conversation using schema preview generator."""
        try:
            # Use schema preview generator to create initial schema
            schema = schema_preview_generator.generate_preview(session.requirements)

            # Enhance with conversation context
            context = self._build_conversation_context(session)

            # Use LLM to refine and enhance the schema
            prompt = f"""
            Refine this agent schema based on the conversation context.

            Current Schema: {json.dumps(schema, indent=2)}
            Conversation Context: {context}
            Requirements: {json.dumps(session.requirements, indent=2)}

            Enhance the schema to be more specific and complete based on the conversation.
            Ensure all components are properly configured and realistic.

            Respond with ONLY the enhanced JSON schema, no additional text.
            """

            response = await ollama_client.generate(
                prompt=prompt,
                model="llama2",
                format="json"
            )

            schema_text = response.get("response", "{}")
            enhanced_schema = json.loads(schema_text)

            # Ensure required fields are present
            if "agent_type" not in enhanced_schema:
                enhanced_schema["agent_type"] = f"custom_agent_{uuid.uuid4().hex[:8]}"

            if "metadata" not in enhanced_schema:
                enhanced_schema["metadata"] = {
                    "name": "Custom Agent",
                    "description": session.initial_description,
                    "category": "custom",
                    "version": "1.0.0"
                }

            return enhanced_schema

        except Exception as e:
            logger.error(f"Error generating schema: {e}")
            # Return a basic fallback schema
            return self._create_fallback_schema(session)

    async def _extract_requirements_from_description(self, description: str) -> Dict[str, Any]:
        """Extract initial requirements from user description."""
        prompt = f"""
        Extract key requirements from this agent description: "{description}"

        Identify:
        - Agent type/purpose
        - Data sources needed
        - Processing steps required
        - Output format
        - Any specific tools mentioned

        Respond in JSON format.
        """

        try:
            response = await ollama_client.generate(
                prompt=prompt,
                model="llama2",
                format="json"
            )

            return json.loads(response.get("response", "{}"))

        except Exception as e:
            logger.error(f"Error extracting requirements: {e}")
            return {"description": description}

    async def _extract_requirements_from_input(self, user_input: str, current_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and merge new requirements from user input."""
        updated = current_requirements.copy()

        # Simple keyword-based extraction (could be enhanced with LLM)
        if "email" in user_input.lower():
            updated["data_sources"] = updated.get("data_sources", [])
            if "email" not in updated["data_sources"]:
                updated["data_sources"].append("email")

        if "database" in user_input.lower() or "store" in user_input.lower():
            updated["needs_storage"] = True

        if "api" in user_input.lower() or "external" in user_input.lower():
            updated["needs_api_integration"] = True

        return updated

    def _build_conversation_context(self, session: BuilderSession) -> str:
        """Build a context string from the conversation history."""
        context_parts = []
        for msg in session.conversation_history[-5:]:  # Last 5 messages for context
            role = msg["role"]
            content = msg["content"]
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)

    async def _fix_schema_validation_errors(self, schema: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Attempt to fix validation errors in generated schema."""
        prompt = f"""
        Fix these validation errors in the agent schema:

        Schema: {json.dumps(schema, indent=2)}
        Errors: {json.dumps(errors, indent=2)}

        Provide a corrected version of the schema that addresses these errors.
        Respond with ONLY the corrected JSON schema.
        """

        try:
            response = await ollama_client.generate(
                prompt=prompt,
                model="llama2",
                format="json"
            )

            return json.loads(response.get("response", "{}"))

        except Exception as e:
            logger.error(f"Error fixing schema: {e}")
            return schema

    def _create_fallback_schema(self, session: BuilderSession) -> Dict[str, Any]:
        """Create a basic fallback schema when generation fails."""
        return {
            "agent_type": f"custom_agent_{uuid.uuid4().hex[:8]}",
            "version": "1.0.0",
            "metadata": {
                "name": "Custom Agent",
                "description": session.initial_description,
                "category": "custom"
            },
            "data_models": {
                "results": {
                    "table_name": "custom_agent_results",
                    "fields": {
                        "id": {"type": "uuid", "required": True},
                        "data": {"type": "json", "required": True},
                        "created_at": {"type": "datetime", "required": True}
                    }
                }
            },
            "processing_pipeline": {
                "steps": [
                    {"name": "process", "tool": "llm_processor"}
                ]
            },
            "tools": {
                "llm_processor": {
                    "type": "llm",
                    "config": {"model": "llama2"}
                }
            },
            "input_schema": {
                "input": {"type": "string", "required": True}
            },
            "output_schema": {
                "result": {"type": "string"}
            }
        }

    async def _save_session_to_db(self, session: BuilderSession, created_by: Optional[str] = None):
        """Save session to database."""
        session_data = session.to_dict()

        # Upsert session
        stmt = update(AgentBuilderSession).where(
            AgentBuilderSession.id == session.id
        ).values(
            conversation_history=session_data["conversation_history"],
            requirements=session_data["requirements"],
            generated_schema=session_data["generated_schema"],
            status=session_data["status"],
            updated_at=datetime.utcnow()
        )

        result = await self.db.execute(stmt)

        # If no rows updated, insert new session
        if result.rowcount == 0:
            db_session = AgentBuilderSession(
                id=session.id,
                initial_description=session.initial_description,
                conversation_history=session.conversation_history,
                requirements=session.requirements,
                generated_schema=session.generated_schema,
                status=session.status,
                created_by=created_by
            )
            self.db.add(db_session)

        await self.db.commit()

    async def _load_session(self, session_id: str) -> Optional[BuilderSession]:
        """Load session from database or memory cache."""
        # Check memory cache first
        if session_id in self.sessions:
            return self.sessions[session_id]

        # Load from database
        result = await self.db.execute(
            select(AgentBuilderSession).where(AgentBuilderSession.id == session_id)
        )
        db_session = result.scalar_one_or_none()

        if not db_session:
            return None

        # Convert to BuilderSession
        session = BuilderSession(str(getattr(db_session, 'id')), str(getattr(db_session, 'initial_description', '')))
        session.conversation_history = getattr(db_session, 'conversation_history', []) or []
        session.requirements = getattr(db_session, 'requirements', {}) or {}
        session.generated_schema = getattr(db_session, 'generated_schema', None)
        session.status = str(getattr(db_session, 'status', 'active'))
        session.created_at = getattr(db_session, 'created_at', datetime.utcnow())
        session.updated_at = getattr(db_session, 'updated_at', datetime.utcnow())

        # Cache in memory
        self.sessions[session_id] = session

        return session
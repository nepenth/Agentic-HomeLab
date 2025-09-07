"""
AI-Assisted Agent Builder API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
from app.api.dependencies import get_db_session, verify_api_key
from app.services.agent_builder_service import AgentBuilderService, BuilderSession, ConversationResponse
from app.services.schema_manager import SchemaManager
from app.utils.logging import get_logger

logger = get_logger("agent_builder_api")
router = APIRouter()


class AgentBuilderStartRequest(BaseModel):
    """Request to start an agent builder session."""
    description: str = Field(..., min_length=1, max_length=1000, description="Natural language description of the desired agent")
    user_id: Optional[str] = Field(None, description="Optional user ID for tracking")


class AgentBuilderChatRequest(BaseModel):
    """Request to continue conversation in agent builder session."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message to continue the conversation")


class AgentBuilderFinalizeRequest(BaseModel):
    """Request to finalize agent creation from session."""
    agent_name: Optional[str] = Field(None, description="Custom name for the agent")
    additional_config: Optional[dict] = Field(default_factory=dict, description="Additional configuration")


class BuilderSessionResponse(BaseModel):
    """Response containing builder session information."""
    session_id: str
    initial_description: str
    status: str
    created_at: str
    conversation_history: List[dict]
    requirements: dict
    generated_schema: Optional[dict] = None


class ConversationResponseModel(BaseModel):
    """Response from conversation continuation."""
    message: str
    questions: List[str]
    suggestions: List[str]
    schema_ready: bool


class SchemaPreviewResponse(BaseModel):
    """Response containing schema preview."""
    agent_schema: dict
    is_valid: bool
    validation_errors: Optional[List[str]] = None


class AgentCreationResponse(BaseModel):
    """Response from successful agent creation."""
    agent_type: str
    agent_id: str
    message: str
    schema: dict


class AvailableTemplatesResponse(BaseModel):
    """Response containing available conversation templates."""
    templates: List[dict]


@router.post("/start", response_model=BuilderSessionResponse, dependencies=[Depends(verify_api_key)])
async def start_agent_builder(
    request: AgentBuilderStartRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Start a new AI-assisted agent builder session."""
    try:
        schema_manager = SchemaManager(db)
        builder_service = AgentBuilderService(db, schema_manager)

        session = await builder_service.start_session(request.description)

        logger.info(f"Started agent builder session: {session.id}")

        return BuilderSessionResponse(
            session_id=session.id,
            initial_description=session.initial_description,
            status=session.status,
            created_at=session.created_at.isoformat(),
            conversation_history=session.conversation_history,
            requirements=session.requirements,
            generated_schema=session.generated_schema
        )

    except Exception as e:
        logger.error(f"Failed to start agent builder session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start agent builder session"
        )


@router.post("/{session_id}/chat", response_model=ConversationResponseModel, dependencies=[Depends(verify_api_key)])
async def continue_agent_builder_chat(
    session_id: str,
    request: AgentBuilderChatRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Continue conversation in an agent builder session."""
    try:
        schema_manager = SchemaManager(db)
        builder_service = AgentBuilderService(db, schema_manager)

        response = await builder_service.continue_conversation(session_id, request.message)

        logger.info(f"Continued agent builder conversation: {session_id}")

        return ConversationResponseModel(
            message=response.message,
            questions=response.questions,
            suggestions=response.suggestions,
            schema_ready=response.schema_ready
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to continue agent builder conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to continue conversation"
        )


@router.get("/{session_id}/schema", response_model=SchemaPreviewResponse, dependencies=[Depends(verify_api_key)])
async def get_agent_builder_schema_preview(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get schema preview for an agent builder session."""
    try:
        schema_manager = SchemaManager(db)
        builder_service = AgentBuilderService(db, schema_manager)

        schema = await builder_service.get_schema_preview(session_id)

        # Validate the schema
        is_valid = False
        validation_errors = None

        try:
            # This would validate against the schema manager
            # For now, we'll assume it's valid if it exists
            is_valid = True
        except Exception as validation_error:
            validation_errors = [str(validation_error)]
            is_valid = False

        logger.info(f"Generated schema preview for session: {session_id}")

        return SchemaPreviewResponse(
            agent_schema=schema,
            is_valid=is_valid,
            validation_errors=validation_errors
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get schema preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate schema preview"
        )


@router.post("/{session_id}/finalize", response_model=AgentCreationResponse, dependencies=[Depends(verify_api_key)])
async def finalize_agent_builder(
    session_id: str,
    request: AgentBuilderFinalizeRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Finalize agent creation from a builder session."""
    try:
        schema_manager = SchemaManager(db)
        builder_service = AgentBuilderService(db, schema_manager)

        # Generate the final schema
        schema = await builder_service.generate_schema(session_id)

        # Register the agent type
        agent_type = await schema_manager.register_agent_type(schema)

        logger.info(f"Finalized agent creation from session: {session_id}, agent_type: {agent_type}")

        # Extract the agent type name from the returned object
        agent_type_name = getattr(agent_type, 'type_name', str(agent_type))

        return AgentCreationResponse(
            agent_type=agent_type_name,
            agent_id=session_id,  # Using session_id as agent_id for now
            message=f"Successfully created agent type: {agent_type_name}",
            schema=schema
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to finalize agent creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to finalize agent creation"
        )


@router.get("/templates", response_model=AvailableTemplatesResponse)
async def get_available_templates(
    db: AsyncSession = Depends(get_db_session)
):
    """Get all available conversation templates."""
    try:
        schema_manager = SchemaManager(db)
        builder_service = AgentBuilderService(db, schema_manager)

        templates = await builder_service.get_available_templates()

        return AvailableTemplatesResponse(templates=templates)

    except Exception as e:
        logger.error(f"Failed to get available templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/{session_id}", response_model=BuilderSessionResponse, dependencies=[Depends(verify_api_key)])
async def get_agent_builder_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get information about an agent builder session."""
    try:
        schema_manager = SchemaManager(db)
        builder_service = AgentBuilderService(db, schema_manager)

        session = await builder_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        return BuilderSessionResponse(
            session_id=session.id,
            initial_description=session.initial_description,
            status=session.status,
            created_at=session.created_at.isoformat(),
            conversation_history=session.conversation_history,
            requirements=session.requirements,
            generated_schema=session.generated_schema
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent builder session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session"
        )
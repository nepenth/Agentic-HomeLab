from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.db.models.agent import Agent
from app.db.models.agent_type import AgentType
from app.db.models.secret import AgentSecret
from app.api.dependencies import get_db_session, verify_api_key
from app.services.schema_manager import SchemaManager
from app.services.secrets_service import SecretsService
from app.utils.logging import get_logger

logger = get_logger("agents_api")
router = APIRouter()


class SecretInput(BaseModel):
    key: str = Field(..., min_length=1, max_length=255, description="Secret key")
    value: str = Field(..., min_length=1, description="Secret value")
    description: Optional[str] = Field(None, description="Secret description")


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    model_name: str = Field(default="llama2", min_length=1, max_length=255)
    config: Optional[dict] = Field(default_factory=dict)
    agent_type: Optional[str] = Field(None, description="Agent type for dynamic agents")
    secrets: Optional[List[SecretInput]] = Field(default_factory=list, description="List of secrets to create for this agent")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    model_name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    model_name: str
    config: dict
    is_active: bool
    created_at: str
    updated_at: str
    secrets_count: int = Field(default=0, description="Number of secrets associated with this agent")


@router.post("/create", response_model=AgentResponse, dependencies=[Depends(verify_api_key)])
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new agent (static or dynamic)."""
    try:
        # Check if this is a dynamic agent creation
        if agent_data.agent_type:
            # Dynamic agent - validate agent type exists
            schema_manager = SchemaManager(db)
            agent_type_obj = await schema_manager.get_agent_type(agent_data.agent_type)

            if not agent_type_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent type '{agent_data.agent_type}' not found"
                )

            # Create dynamic agent
            agent = Agent(
                name=agent_data.name,
                description=agent_data.description,
                model_name=agent_data.model_name,
                config=agent_data.config or {},
                agent_type_id=agent_type_obj.id
            )

            logger.info(f"Created dynamic agent: {agent_data.name} of type {agent_data.agent_type}")
        else:
            # Static agent (legacy)
            agent = Agent(
                name=agent_data.name,
                description=agent_data.description,
                model_name=agent_data.model_name,
                config=agent_data.config or {}
            )

            logger.info(f"Created static agent: {agent_data.name}")

        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        # Create secrets if provided
        if agent_data.secrets:
            secrets_service = SecretsService(db)
            for secret_input in agent_data.secrets:
                try:
                    await secrets_service.create_secret(
                        agent_id=agent.id,
                        secret_key=secret_input.key,
                        secret_value=secret_input.value,
                        description=secret_input.description
                    )
                    logger.info(f"Created secret '{secret_input.key}' for agent {agent.id}")
                except Exception as e:
                    logger.error(f"Failed to create secret '{secret_input.key}' for agent {agent.id}: {e}")
                    # Continue with other secrets, don't fail the whole agent creation

        # Get secrets count for the newly created agent
        agent_dict = agent.to_dict()
        secrets_count = len(agent_data.secrets) if agent_data.secrets else 0
        agent_dict["secrets_count"] = secrets_count

        return AgentResponse(**agent_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create agent"
        )


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    active_only: bool = True,
    agent_type: Optional[str] = Query(None, description="Filter by agent type (for dynamic agents)"),
    include_dynamic: bool = Query(True, description="Include dynamic agents in results"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List all agents with optional filtering."""
    try:
        query = select(Agent)

        if active_only:
            query = query.where(Agent.is_active == True)

        # Filter by agent type if specified
        if agent_type:
            # Join with AgentType to filter by type name
            from sqlalchemy import and_
            query = query.join(AgentType, Agent.agent_type_id == AgentType.id)
            query = query.where(AgentType.type_name == agent_type)

        # Filter dynamic vs static agents
        if not include_dynamic:
            # Only static agents (no agent_type_id)
            query = query.where(Agent.agent_type_id.is_(None))
        elif include_dynamic is False:
            # This would be an explicit request to exclude dynamic agents
            query = query.where(Agent.agent_type_id.is_(None))

        query = query.offset(offset).limit(limit).order_by(Agent.created_at.desc())

        result = await db.execute(query)
        agents = result.scalars().all()

        # Get secrets count for each agent
        agent_responses = []
        for agent in agents:
            agent_dict = agent.to_dict()
            # Count active secrets for this agent
            secrets_count_result = await db.execute(
                select(AgentSecret).where(
                    AgentSecret.agent_id == agent.id,
                    AgentSecret.is_active == True
                )
            )
            secrets_count = len(secrets_count_result.scalars().all())
            agent_dict["secrets_count"] = secrets_count
            agent_responses.append(AgentResponse(**agent_dict))

        return agent_responses

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents"
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific agent by ID."""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )

        # Get secrets count for this agent
        agent_dict = agent.to_dict()
        secrets_count_result = await db.execute(
            select(AgentSecret).where(
                AgentSecret.agent_id == agent.id,
                AgentSecret.is_active == True
            )
        )
        secrets_count = len(secrets_count_result.scalars().all())
        agent_dict["secrets_count"] = secrets_count

        return AgentResponse(**agent_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent"
        )


@router.put("/{agent_id}", response_model=AgentResponse, dependencies=[Depends(verify_api_key)])
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update an existing agent."""
    try:
        # Check if agent exists
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        # Update fields
        update_data = agent_data.dict(exclude_unset=True)
        if update_data:
            stmt = update(Agent).where(Agent.id == agent_id).values(**update_data)
            await db.execute(stmt)
            await db.commit()
            await db.refresh(agent)
        
        # Get secrets count for the updated agent
        agent_dict = agent.to_dict()
        secrets_count_result = await db.execute(
            select(AgentSecret).where(
                AgentSecret.agent_id == agent.id,
                AgentSecret.is_active == True
            )
        )
        secrets_count = len(secrets_count_result.scalars().all())
        agent_dict["secrets_count"] = secrets_count

        logger.info(f"Updated agent: {agent_id}")
        return AgentResponse(**agent_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent"
        )


@router.delete("/{agent_id}", dependencies=[Depends(verify_api_key)])
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete an agent."""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        await db.execute(delete(Agent).where(Agent.id == agent_id))
        await db.commit()
        
        logger.info(f"Deleted agent: {agent_id}")
        return {"message": "Agent deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent"
        )
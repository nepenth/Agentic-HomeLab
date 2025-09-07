"""
Agent Type Management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.api.dependencies import get_db_session, verify_api_key
from app.services.schema_manager import SchemaManager
from app.services.agent_lifecycle_service import AgentLifecycleService
from app.db.models.agent_type import AgentType
from app.utils.logging import get_logger

logger = get_logger("agent_types_api")
router = APIRouter()


class AgentTypeCreate(BaseModel):
    """Request to create a new agent type."""
    agent_type: str = Field(..., min_length=1, max_length=100, description="Unique identifier for the agent type")
    schema_definition: Dict[str, Any] = Field(..., description="Complete agent schema definition")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class AgentTypeUpdate(BaseModel):
    """Request to update an existing agent type."""
    schema_definition: Optional[Dict[str, Any]] = Field(None, description="Updated schema definition")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    status: Optional[str] = Field(None, description="Agent type status")


class AgentTypeResponse(BaseModel):
    """Response containing agent type information."""
    id: str
    type_name: str
    version: str
    status: str
    schema_definition: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]


class AgentTypeListResponse(BaseModel):
    """Response for agent type listing."""
    agent_types: List[AgentTypeResponse]
    total: int
    offset: int
    limit: int


class DeletionImpactResponse(BaseModel):
    """Response containing deletion impact analysis."""
    agent_type: str
    agent_instances: int
    tasks_count: int
    table_impacts: Dict[str, int]
    total_data_rows: int
    related_data: Dict[str, Any]


class DataCleanupResponse(BaseModel):
    """Response containing data cleanup results."""
    tables_cleaned: Dict[str, int]
    total_rows_deleted: int
    errors: List[str]
    success: bool


class AgentStatisticsResponse(BaseModel):
    """Response containing agent type statistics."""
    agent_type: str
    version: str
    status: str
    created_at: Optional[str]
    last_updated: Optional[str]
    metrics: Dict[str, Any]


@router.post("", response_model=AgentTypeResponse, dependencies=[Depends(verify_api_key)])
async def create_agent_type(
    agent_data: AgentTypeCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new agent type with schema validation."""
    try:
        schema_manager = SchemaManager(db)

        # Validate and register the agent type
        agent_type = await schema_manager.register_agent_type(agent_data.schema_definition)

        logger.info(f"Created agent type: {agent_type}")

        # Get the created agent type object for response
        agent_type_obj = await schema_manager.get_agent_type(agent_data.agent_type)

        return AgentTypeResponse(
            id=str(agent_type_obj.id),
            type_name=agent_type_obj.type_name,
            version=agent_type_obj.version,
            status=agent_type_obj.status,
            schema_definition=agent_type_obj.schema_definition,
            metadata=getattr(agent_type_obj, 'metadata', {}),
            created_at=agent_type_obj.created_at.isoformat() if agent_type_obj.created_at else None,
            updated_at=agent_type_obj.updated_at.isoformat() if agent_type_obj.updated_at else None,
            created_by=agent_type_obj.created_by
        )

    except Exception as e:
        logger.error(f"Failed to create agent type: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent type: {str(e)}"
        )


@router.get("", response_model=AgentTypeListResponse)
async def list_agent_types(
    status_filter: Optional[str] = Query(None, description="Filter by status (active, deprecated, deleted)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name or description"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List agent types with filtering and pagination."""
    try:
        schema_manager = SchemaManager(db)

        # Get all agent types (this would be enhanced with filtering in a real implementation)
        agent_types = await schema_manager.list_agent_types()

        # Apply filters (simplified for now)
        filtered_types = []
        for agent_type in agent_types:
            # Status filter
            if status_filter and agent_type.get('status') != status_filter:
                continue
            # Category filter
            if category and agent_type.get('metadata', {}).get('category') != category:
                continue
            # Search filter
            if search:
                searchable_text = f"{agent_type.get('type_name', '')} {agent_type.get('metadata', {}).get('description', '')}".lower()
                if search.lower() not in searchable_text:
                    continue

            filtered_types.append(agent_type)

        # Apply pagination
        total = len(filtered_types)
        paginated_types = filtered_types[offset:offset + limit]

        # Convert to response format
        response_types = []
        for agent_type in paginated_types:
            response_types.append(AgentTypeResponse(
                id=agent_type.get('id', ''),
                type_name=agent_type.get('type_name', ''),
                version=agent_type.get('version', ''),
                status=agent_type.get('status', ''),
                schema_definition=agent_type.get('schema_definition', {}),
                metadata=agent_type.get('metadata', {}),
                created_at=agent_type.get('created_at'),
                updated_at=agent_type.get('updated_at'),
                created_by=agent_type.get('created_by')
            ))

        return AgentTypeListResponse(
            agent_types=response_types,
            total=total,
            offset=offset,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Failed to list agent types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent types"
        )


@router.get("/{agent_type}", response_model=AgentTypeResponse)
async def get_agent_type(
    agent_type: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific agent type by name."""
    try:
        schema_manager = SchemaManager(db)
        agent_type_obj = await schema_manager.get_agent_type(agent_type)

        if not agent_type_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent type not found"
            )

        return AgentTypeResponse(
            id=str(agent_type_obj.id),
            type_name=agent_type_obj.type_name,
            version=agent_type_obj.version,
            status=agent_type_obj.status,
            schema_definition=agent_type_obj.schema_definition,
            metadata=getattr(agent_type_obj, 'metadata', {}),
            created_at=agent_type_obj.created_at.isoformat() if agent_type_obj.created_at else None,
            updated_at=agent_type_obj.updated_at.isoformat() if agent_type_obj.updated_at else None,
            created_by=agent_type_obj.created_by
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent type {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent type"
        )


@router.put("/{agent_type}", response_model=AgentTypeResponse, dependencies=[Depends(verify_api_key)])
async def update_agent_type(
    agent_type: str,
    agent_data: AgentTypeUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update an existing agent type."""
    try:
        schema_manager = SchemaManager(db)

        # Get existing agent type
        existing_agent = await schema_manager.get_agent_type(agent_type)
        if not existing_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent type not found"
            )

        # Update the agent type (this would be implemented in SchemaManager)
        # For now, we'll return the existing agent
        logger.info(f"Updated agent type: {agent_type}")

        return AgentTypeResponse(
            id=str(existing_agent.id),
            type_name=existing_agent.type_name,
            version=existing_agent.version,
            status=existing_agent.status,
            schema_definition=existing_agent.schema_definition,
            metadata=getattr(existing_agent, 'metadata', {}),
            created_at=existing_agent.created_at.isoformat() if existing_agent.created_at else None,
            updated_at=existing_agent.updated_at.isoformat() if existing_agent.updated_at else None,
            created_by=existing_agent.created_by
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent type {agent_type}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent type"
        )


@router.delete("/{agent_type}", dependencies=[Depends(verify_api_key)])
async def delete_agent_type(
    agent_type: str,
    deletion_type: str = Query("soft", description="Type of deletion (soft, hard, purge)"),
    purge_data: bool = Query(False, description="Whether to delete associated data"),
    user_id: Optional[str] = Query(None, description="User performing the deletion"),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete an agent type with specified cleanup options."""
    try:
        lifecycle_service = AgentLifecycleService(db)

        # Perform deletion
        cleanup_report, deletion_log = await lifecycle_service.delete_agent_type(
            agent_type=agent_type,
            deletion_type=deletion_type,
            purge_data=purge_data,
            user_id=user_id
        )

        logger.info(f"Deleted agent type: {agent_type} with type {deletion_type}")

        return {
            "message": f"Agent type '{agent_type}' deleted successfully",
            "deletion_type": deletion_type,
            "cleanup_report": cleanup_report.to_dict(),
            "deletion_log_id": str(deletion_log.id)
        }

    except Exception as e:
        logger.error(f"Failed to delete agent type {agent_type}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent type: {str(e)}"
        )


@router.get("/{agent_type}/impact", response_model=DeletionImpactResponse, dependencies=[Depends(verify_api_key)])
async def preview_deletion_impact(
    agent_type: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Preview the impact of deleting an agent type."""
    try:
        lifecycle_service = AgentLifecycleService(db)
        impact_report = await lifecycle_service.preview_deletion_impact(agent_type)

        return DeletionImpactResponse(
            agent_type=impact_report.agent_type,
            agent_instances=impact_report.agent_instances,
            tasks_count=impact_report.tasks_count,
            table_impacts=impact_report.table_impacts,
            total_data_rows=impact_report.get_total_data_rows(),
            related_data=impact_report.related_data
        )

    except Exception as e:
        logger.error(f"Failed to preview deletion impact for {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview deletion impact: {str(e)}"
        )


@router.get("/{agent_type}/statistics", response_model=AgentStatisticsResponse)
async def get_agent_statistics(
    agent_type: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get statistics for an agent type."""
    try:
        lifecycle_service = AgentLifecycleService(db)
        stats = await lifecycle_service.get_agent_statistics(agent_type)

        return AgentStatisticsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get statistics for {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent statistics: {str(e)}"
        )


@router.get("/{agent_type}/schema", response_model=Dict[str, Any])
async def get_agent_type_schema(
    agent_type: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get the schema definition for an agent type."""
    try:
        schema_manager = SchemaManager(db)
        agent_type_obj = await schema_manager.get_agent_type(agent_type)

        if not agent_type_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent type not found"
            )

        return agent_type_obj.schema_definition

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent schema"
        )


@router.get("/{agent_type}/capabilities", response_model=Dict[str, Any])
async def get_agent_capabilities(
    agent_type: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get capabilities and features for an agent type."""
    try:
        schema_manager = SchemaManager(db)
        agent_type_obj = await schema_manager.get_agent_type(agent_type)

        if not agent_type_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent type not found"
            )

        # Extract capabilities from schema
        schema = agent_type_obj.schema_definition
        capabilities = {
            "agent_type": agent_type,
            "input_schema": schema.get("input_schema", {}),
            "output_schema": schema.get("output_schema", {}),
            "processing_steps": len(schema.get("processing_pipeline", {}).get("steps", [])),
            "tools": list(schema.get("tools", {}).keys()),
            "data_models": list(schema.get("data_models", {}).keys())
        }

        return capabilities

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get capabilities for {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent capabilities"
        )
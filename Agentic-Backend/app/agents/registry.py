"""
Agent registry for managing agent types, versioning, and capabilities.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError

from app.services.schema_manager import SchemaManager, SchemaValidationError
from app.schemas.agent_schema import AgentSchema, AgentSchemaVersion
from app.db.models.agent_type import AgentType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentRegistrationError(Exception):
    """Raised when agent registration fails."""
    pass


class AgentTypeInfo:
    """Information about an agent type."""
    
    def __init__(
        self,
        agent_type: str,
        name: str,
        description: str,
        category: str,
        version: str,
        status: str,
        created_at: datetime,
        deprecated_at: Optional[datetime] = None,
        capabilities: Optional[Dict[str, Any]] = None
    ):
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.category = category
        self.version = version
        self.status = status
        self.created_at = created_at
        self.deprecated_at = deprecated_at
        self.capabilities = capabilities or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "deprecated_at": self.deprecated_at.isoformat() if self.deprecated_at else None,
            "capabilities": self.capabilities
        }


class AgentCapabilities:
    """Detailed capabilities of an agent type."""
    
    def __init__(
        self,
        agent_type: str,
        version: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        data_models: Dict[str, Any],
        tools: Dict[str, Any],
        processing_steps: int,
        resource_limits: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        self.agent_type = agent_type
        self.version = version
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.data_models = data_models
        self.tools = tools
        self.processing_steps = processing_steps
        self.resource_limits = resource_limits
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_type": self.agent_type,
            "version": self.version,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "data_models": self.data_models,
            "tools": self.tools,
            "processing_steps": self.processing_steps,
            "resource_limits": self.resource_limits,
            "metadata": self.metadata
        }


class AgentRegistry:
    """Registry for managing agent types, versions, and capabilities."""
    
    def __init__(self, db_session: AsyncSession, schema_manager: SchemaManager):
        self.db = db_session
        self.schema_manager = schema_manager
    
    async def register_agent_type(
        self,
        schema_dict: Dict[str, Any],
        created_by: Optional[str] = None,
        replace_existing: bool = False
    ) -> AgentType:
        """
        Register a new agent type with schema validation.
        
        Args:
            schema_dict: Agent schema dictionary
            created_by: User who created the agent type
            replace_existing: Whether to replace existing agent type
            
        Returns:
            Created AgentType instance
            
        Raises:
            AgentRegistrationError: If registration fails
            SchemaValidationError: If schema validation fails
        """
        try:
            # Use schema manager for validation and registration
            agent_type = await self.schema_manager.register_agent_type(schema_dict, created_by)
            
            logger.info(f"Registered agent type: {agent_type.type_name} v{agent_type.version}")
            return agent_type
            
        except SchemaValidationError as e:
            logger.error(f"Schema validation failed for agent type registration: {e}")
            raise AgentRegistrationError(f"Schema validation failed: {'; '.join(e.errors)}")
        except IntegrityError as e:
            if replace_existing:
                # Try to update existing agent type
                return await self._update_existing_agent_type(schema_dict, created_by)
            else:
                logger.error(f"Agent type already exists: {e}")
                raise AgentRegistrationError("Agent type already exists. Use replace_existing=True to update.")
        except Exception as e:
            logger.error(f"Failed to register agent type: {e}")
            raise AgentRegistrationError(f"Registration failed: {str(e)}")
    
    async def _update_existing_agent_type(
        self,
        schema_dict: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> AgentType:
        """Update an existing agent type with a new version."""
        try:
            agent_schema = AgentSchema(**schema_dict)
            
            # Get existing agent type
            existing = await self.schema_manager.get_agent_type(
                agent_schema.agent_type,
                agent_schema.metadata.version
            )
            
            if existing:
                # Update existing record
                existing.schema_definition = schema_dict
                existing.updated_at = datetime.utcnow()
                existing.created_by = created_by or existing.created_by
                
                await self.db.commit()
                return existing
            else:
                # Create new version
                return await self.schema_manager.register_agent_type(schema_dict, created_by)
                
        except Exception as e:
            await self.db.rollback()
            raise AgentRegistrationError(f"Failed to update agent type: {str(e)}")
    
    async def list_agent_types(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        include_deprecated: bool = False,
        search_term: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[AgentTypeInfo]:
        """
        List available agent types with filtering and pagination.
        
        Args:
            category: Filter by category
            status: Filter by status
            include_deprecated: Whether to include deprecated agent types
            search_term: Search in name and description
            limit: Maximum number of results
            offset: Number of results to skip
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            List of AgentTypeInfo instances
        """
        try:
            # Build query
            query = select(AgentType).where(AgentType.status != "deleted")
            
            # Apply filters
            if category:
                query = query.where(AgentType.schema_definition["metadata"]["category"].astext == category)
            
            if status:
                query = query.where(AgentType.status == status)
            elif not include_deprecated:
                query = query.where(AgentType.status == "active")
            
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.where(
                    or_(
                        AgentType.schema_definition["metadata"]["name"].astext.ilike(search_pattern),
                        AgentType.schema_definition["metadata"]["description"].astext.ilike(search_pattern),
                        AgentType.type_name.ilike(search_pattern)
                    )
                )
            
            # Apply sorting
            sort_column = getattr(AgentType, sort_by, AgentType.created_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            # Execute query
            result = await self.db.execute(query)
            agent_types = result.scalars().all()
            
            # Convert to AgentTypeInfo objects
            agent_type_infos = []
            for agent_type in agent_types:
                schema = AgentSchema(**agent_type.schema_definition)
                
                info = AgentTypeInfo(
                    agent_type=agent_type.type_name,
                    name=schema.metadata.name,
                    description=schema.metadata.description,
                    category=schema.metadata.category,
                    version=agent_type.version,
                    status=agent_type.status,
                    created_at=agent_type.created_at,
                    deprecated_at=agent_type.deprecated_at,
                    capabilities=self._extract_basic_capabilities(schema)
                )
                agent_type_infos.append(info)
            
            return agent_type_infos
            
        except Exception as e:
            logger.error(f"Failed to list agent types: {e}")
            raise AgentRegistrationError(f"Failed to list agent types: {str(e)}")
    
    async def get_agent_type_info(
        self,
        agent_type: str,
        version: Optional[str] = None
    ) -> Optional[AgentTypeInfo]:
        """
        Get detailed information about a specific agent type.
        
        Args:
            agent_type: Agent type name
            version: Specific version (None for latest)
            
        Returns:
            AgentTypeInfo instance or None if not found
        """
        try:
            agent_type_record = await self.schema_manager.get_agent_type(agent_type, version)
            if not agent_type_record:
                return None
            
            schema = AgentSchema(**agent_type_record.schema_definition)
            
            return AgentTypeInfo(
                agent_type=agent_type_record.type_name,
                name=schema.metadata.name,
                description=schema.metadata.description,
                category=schema.metadata.category,
                version=agent_type_record.version,
                status=agent_type_record.status,
                created_at=agent_type_record.created_at,
                deprecated_at=agent_type_record.deprecated_at,
                capabilities=self._extract_basic_capabilities(schema)
            )
            
        except Exception as e:
            logger.error(f"Failed to get agent type info for '{agent_type}': {e}")
            return None
    
    async def get_agent_capabilities(
        self,
        agent_type: str,
        version: Optional[str] = None
    ) -> Optional[AgentCapabilities]:
        """
        Get detailed capabilities for an agent type.
        
        Args:
            agent_type: Agent type name
            version: Specific version (None for latest)
            
        Returns:
            AgentCapabilities instance or None if not found
        """
        try:
            agent_type_record = await self.schema_manager.get_agent_type(agent_type, version)
            if not agent_type_record:
                return None
            
            schema = AgentSchema(**agent_type_record.schema_definition)
            
            # Extract detailed capabilities
            input_schema = {
                name: {
                    "type": field.type.value,
                    "required": field.required,
                    "description": field.description,
                    "default": field.default
                }
                for name, field in schema.input_schema.items()
            }
            
            output_schema = {
                name: {
                    "type": field.type.value,
                    "description": field.description
                }
                for name, field in schema.output_schema.items()
            }
            
            data_models = {
                name: {
                    "table_name": model.table_name,
                    "description": model.description,
                    "fields": {
                        field_name: {
                            "type": field.type.value,
                            "required": field.required,
                            "description": field.description
                        }
                        for field_name, field in model.fields.items()
                    }
                }
                for name, model in schema.data_models.items()
            }
            
            tools = {
                name: {
                    "type": tool.type,
                    "description": tool.description,
                    "auth_required": tool.auth_config is not None,
                    "rate_limited": tool.rate_limit is not None
                }
                for name, tool in schema.tools.items()
            }
            
            resource_limits = {
                "max_execution_time": schema.max_execution_time,
                "max_memory_usage": schema.max_memory_usage,
                "allowed_domains": schema.allowed_domains
            }
            
            return AgentCapabilities(
                agent_type=agent_type,
                version=agent_type_record.version,
                input_schema=input_schema,
                output_schema=output_schema,
                data_models=data_models,
                tools=tools,
                processing_steps=len(schema.processing_pipeline.steps),
                resource_limits=resource_limits,
                metadata=schema.metadata.dict()
            )
            
        except Exception as e:
            logger.error(f"Failed to get agent capabilities for '{agent_type}': {e}")
            return None
    
    async def deprecate_agent_type(
        self,
        agent_type: str,
        version: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Deprecate an agent type or specific version.
        
        Args:
            agent_type: Agent type name
            version: Specific version (None for all versions)
            reason: Reason for deprecation
            
        Returns:
            True if any agent types were deprecated
        """
        try:
            success = await self.schema_manager.deprecate_agent_type(agent_type, version)
            
            if success:
                logger.info(f"Deprecated agent type: {agent_type}" + 
                           (f" v{version}" if version else " (all versions)") +
                           (f" - Reason: {reason}" if reason else ""))
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to deprecate agent type '{agent_type}': {e}")
            return False
    
    async def delete_agent_type(
        self,
        agent_type: str,
        version: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Delete an agent type (soft delete by default).
        
        Args:
            agent_type: Agent type name
            version: Specific version (None for all versions)
            force: Whether to perform hard delete
            
        Returns:
            True if agent type was deleted
        """
        try:
            # Build query
            query = select(AgentType).where(AgentType.type_name == agent_type)
            if version:
                query = query.where(AgentType.version == version)
            
            result = await self.db.execute(query)
            agent_types = result.scalars().all()
            
            if not agent_types:
                return False
            
            # Check if any agents are using this type
            if not force:
                from app.db.models.agent import Agent
                usage_query = select(func.count(Agent.id)).where(
                    Agent.agent_type_id.in_([at.id for at in agent_types])
                )
                usage_result = await self.db.execute(usage_query)
                usage_count = usage_result.scalar()
                
                if usage_count > 0:
                    raise AgentRegistrationError(
                        f"Cannot delete agent type '{agent_type}': {usage_count} agents are using it. "
                        "Use force=True to delete anyway."
                    )
            
            # Perform deletion
            for agent_type_record in agent_types:
                if force:
                    await self.db.delete(agent_type_record)
                else:
                    agent_type_record.status = "deleted"
                    agent_type_record.deprecated_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Deleted agent type: {agent_type}" + 
                       (f" v{version}" if version else " (all versions)"))
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete agent type '{agent_type}': {e}")
            raise AgentRegistrationError(f"Failed to delete agent type: {str(e)}")
    
    async def search_agent_types(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[AgentTypeInfo]:
        """
        Search agent types by name, description, or capabilities.
        
        Args:
            query: Search query
            categories: Filter by categories
            limit: Maximum number of results
            
        Returns:
            List of matching AgentTypeInfo instances
        """
        try:
            # Build search query
            search_pattern = f"%{query}%"
            db_query = select(AgentType).where(
                and_(
                    AgentType.status == "active",
                    or_(
                        AgentType.type_name.ilike(search_pattern),
                        AgentType.schema_definition["metadata"]["name"].astext.ilike(search_pattern),
                        AgentType.schema_definition["metadata"]["description"].astext.ilike(search_pattern),
                        AgentType.schema_definition["metadata"]["tags"].astext.ilike(search_pattern)
                    )
                )
            )
            
            # Filter by categories if provided
            if categories:
                db_query = db_query.where(
                    AgentType.schema_definition["metadata"]["category"].astext.in_(categories)
                )
            
            # Order by relevance (name matches first, then description)
            db_query = db_query.order_by(
                AgentType.type_name.ilike(search_pattern).desc(),
                AgentType.schema_definition["metadata"]["name"].astext.ilike(search_pattern).desc(),
                AgentType.created_at.desc()
            ).limit(limit)
            
            result = await self.db.execute(db_query)
            agent_types = result.scalars().all()
            
            # Convert to AgentTypeInfo objects
            search_results = []
            for agent_type in agent_types:
                schema = AgentSchema(**agent_type.schema_definition)
                
                info = AgentTypeInfo(
                    agent_type=agent_type.type_name,
                    name=schema.metadata.name,
                    description=schema.metadata.description,
                    category=schema.metadata.category,
                    version=agent_type.version,
                    status=agent_type.status,
                    created_at=agent_type.created_at,
                    deprecated_at=agent_type.deprecated_at,
                    capabilities=self._extract_basic_capabilities(schema)
                )
                search_results.append(info)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search agent types: {e}")
            return []
    
    async def get_agent_versions(self, agent_type: str) -> List[AgentSchemaVersion]:
        """
        Get all versions of an agent type.
        
        Args:
            agent_type: Agent type name
            
        Returns:
            List of AgentSchemaVersion instances
        """
        try:
            return await self.schema_manager.get_schema_versions(agent_type)
        except Exception as e:
            logger.error(f"Failed to get versions for agent type '{agent_type}': {e}")
            return []
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get all available agent categories with counts.
        
        Returns:
            List of category information dictionaries
        """
        try:
            # Query for categories and their counts
            query = select(
                AgentType.schema_definition["metadata"]["category"].astext.label("category"),
                func.count(AgentType.id).label("count")
            ).where(
                AgentType.status == "active"
            ).group_by(
                AgentType.schema_definition["metadata"]["category"].astext
            ).order_by(
                func.count(AgentType.id).desc()
            )
            
            result = await self.db.execute(query)
            categories = result.all()
            
            return [
                {
                    "category": category,
                    "count": count,
                    "description": self._get_category_description(category)
                }
                for category, count in categories
                if category  # Filter out null categories
            ]
            
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        try:
            # Total agent types
            total_query = select(func.count(AgentType.id)).where(AgentType.status != "deleted")
            total_result = await self.db.execute(total_query)
            total_count = total_result.scalar()
            
            # Active agent types
            active_query = select(func.count(AgentType.id)).where(AgentType.status == "active")
            active_result = await self.db.execute(active_query)
            active_count = active_result.scalar()
            
            # Deprecated agent types
            deprecated_query = select(func.count(AgentType.id)).where(AgentType.status == "deprecated")
            deprecated_result = await self.db.execute(deprecated_query)
            deprecated_count = deprecated_result.scalar()
            
            # Recent registrations (last 30 days)
            recent_date = datetime.utcnow() - timedelta(days=30)
            recent_query = select(func.count(AgentType.id)).where(
                and_(
                    AgentType.created_at >= recent_date,
                    AgentType.status != "deleted"
                )
            )
            recent_result = await self.db.execute(recent_query)
            recent_count = recent_result.scalar()
            
            # Categories
            categories = await self.get_categories()
            
            return {
                "total_agent_types": total_count,
                "active_agent_types": active_count,
                "deprecated_agent_types": deprecated_count,
                "recent_registrations": recent_count,
                "categories": len(categories),
                "category_breakdown": categories
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def _extract_basic_capabilities(self, schema: AgentSchema) -> Dict[str, Any]:
        """Extract basic capabilities from schema for listing."""
        return {
            "input_fields": len(schema.input_schema),
            "output_fields": len(schema.output_schema),
            "data_models": len(schema.data_models),
            "tools": len(schema.tools),
            "processing_steps": len(schema.processing_pipeline.steps),
            "has_resource_limits": bool(schema.max_execution_time or schema.max_memory_usage),
            "tags": schema.metadata.tags or []
        }
    
    def _get_category_description(self, category: str) -> str:
        """Get description for a category."""
        category_descriptions = {
            "productivity": "Agents that help with productivity and task management",
            "analysis": "Agents that perform data analysis and insights",
            "communication": "Agents that handle communication and messaging",
            "automation": "Agents that automate repetitive tasks",
            "content": "Agents that create or process content",
            "integration": "Agents that integrate with external services",
            "monitoring": "Agents that monitor systems and processes",
            "testing": "Agents used for testing and development"
        }
        return category_descriptions.get(category, f"Agents in the {category} category")
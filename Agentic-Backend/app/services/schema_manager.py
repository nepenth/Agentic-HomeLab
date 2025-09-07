"""
Schema management service for dynamic agent schemas.
"""
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, text
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

from app.schemas.agent_schema import (
    AgentSchema,
    SchemaValidationResult,
    SchemaCompatibilityResult,
    AgentSchemaVersion,
    DataModelDefinition,
    FieldDefinition,
    FieldType
)
from app.db.models.agent_type import AgentType, DynamicTable, RegisteredTool
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_security_service():
    """Lazy import to avoid circular imports."""
    from app.services.security_service import SecurityService
    return SecurityService()


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""
    def __init__(self, errors: List[str], schema_path: str = ""):
        self.errors = errors
        self.schema_path = schema_path
        super().__init__(f"Schema validation failed: {', '.join(errors)}")


class IncompatibleSchemaError(Exception):
    """Raised when schema changes are incompatible."""
    def __init__(self, breaking_changes: List[str]):
        self.breaking_changes = breaking_changes
        super().__init__(f"Incompatible schema changes: {', '.join(breaking_changes)}")


class SchemaManager:
    """Manages dynamic agent schemas, validation, and versioning."""

    def __init__(self, db_session: AsyncSession, security_service=None):
        self.db = db_session
        self._meta_schema = self._load_meta_schema()
        self.security_service = security_service or get_security_service()
    
    def _load_meta_schema(self) -> Dict[str, Any]:
        """Load the meta-schema that defines valid agent schema structure."""
        return {
            "required_fields": [
                "agent_type", "metadata", "data_models", 
                "processing_pipeline", "tools", "input_schema", "output_schema"
            ],
            "metadata_required_fields": ["name", "description", "category", "version"],
            "max_data_models": 10,
            "max_pipeline_steps": 20,
            "max_tools": 15,
            "max_field_name_length": 63,
            "max_table_name_length": 63,
            "reserved_field_names": ["id", "created_at", "updated_at", "agent_id", "task_id"],
            "supported_field_types": [ft.value for ft in FieldType],
            "max_execution_time": 7200,  # 2 hours
            "max_memory_usage": 2048,  # 2GB
        }
    
    async def validate_schema(self, schema_dict: Dict[str, Any]) -> SchemaValidationResult:
        """
        Validate an agent schema against the meta-schema and business rules.
        
        Args:
            schema_dict: The schema dictionary to validate
            
        Returns:
            SchemaValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []
        
        try:
            # First, validate with Pydantic model
            agent_schema = AgentSchema(**schema_dict)
            
            # Additional meta-schema validation
            meta_errors = self._validate_against_meta_schema(schema_dict)
            errors.extend(meta_errors)
            
            # Business rule validation
            business_errors, business_warnings = self._validate_business_rules(agent_schema)
            errors.extend(business_errors)
            warnings.extend(business_warnings)
            
            # Enhanced security validation using SecurityService
            is_secure, security_errors, security_warnings = await self.security_service.validate_agent_schema_security(agent_schema)
            if not is_secure:
                errors.extend(security_errors)
            warnings.extend(security_warnings)

            # Legacy security validation (keeping for backward compatibility)
            legacy_security_errors = self._validate_security_constraints(agent_schema)
            errors.extend(legacy_security_errors)
            
            # Generate schema hash if valid
            schema_hash = None
            if not errors:
                schema_hash = self._generate_schema_hash(schema_dict)
            
            return SchemaValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                schema_hash=schema_hash
            )
            
        except ValidationError as e:
            # Convert Pydantic validation errors to our format
            pydantic_errors = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                pydantic_errors.append(f"{field_path}: {error['msg']}")
            
            return SchemaValidationResult(
                is_valid=False,
                errors=pydantic_errors,
                warnings=warnings
            )
        except Exception as e:
            logger.error(f"Unexpected error during schema validation: {e}")
            return SchemaValidationResult(
                is_valid=False,
                errors=[f"Unexpected validation error: {str(e)}"],
                warnings=warnings
            )
    
    def _validate_against_meta_schema(self, schema_dict: Dict[str, Any]) -> List[str]:
        """Validate schema against meta-schema constraints."""
        errors = []
        meta = self._meta_schema
        
        # Check required top-level fields
        for field in meta["required_fields"]:
            if field not in schema_dict:
                errors.append(f"Missing required field: {field}")
        
        # Check metadata required fields
        metadata = schema_dict.get("metadata", {})
        for field in meta["metadata_required_fields"]:
            if field not in metadata:
                errors.append(f"Missing required metadata field: {field}")
        
        # Check limits
        data_models = schema_dict.get("data_models", {})
        if len(data_models) > meta["max_data_models"]:
            errors.append(f"Too many data models: {len(data_models)} > {meta['max_data_models']}")
        
        pipeline = schema_dict.get("processing_pipeline", {})
        steps = pipeline.get("steps", [])
        if len(steps) > meta["max_pipeline_steps"]:
            errors.append(f"Too many pipeline steps: {len(steps)} > {meta['max_pipeline_steps']}")
        
        tools = schema_dict.get("tools", {})
        if len(tools) > meta["max_tools"]:
            errors.append(f"Too many tools: {len(tools)} > {meta['max_tools']}")
        
        # Validate field names and types in data models
        for model_name, model_def in data_models.items():
            if isinstance(model_def, dict):
                fields = model_def.get("fields", {})
                for field_name, field_def in fields.items():
                    if len(field_name) > meta["max_field_name_length"]:
                        errors.append(f"Field name too long in {model_name}: {field_name}")
                    
                    if field_name in meta["reserved_field_names"]:
                        errors.append(f"Reserved field name in {model_name}: {field_name}")
                    
                    if isinstance(field_def, dict):
                        field_type = field_def.get("type")
                        if field_type not in meta["supported_field_types"]:
                            errors.append(f"Unsupported field type in {model_name}.{field_name}: {field_type}")
        
        return errors
    
    def _validate_business_rules(self, schema: AgentSchema) -> Tuple[List[str], List[str]]:
        """Validate business rules and best practices."""
        errors = []
        warnings = []
        
        # Ensure each data model has at least one required field or default value
        for model_name, model_def in schema.data_models.items():
            has_required_or_default = any(
                field.required or field.default is not None 
                for field in model_def.fields.values()
            )
            if not has_required_or_default:
                errors.append(f"Data model '{model_name}' must have at least one required field or default value")
        
        # Check for circular dependencies in pipeline
        step_names = {step.name for step in schema.processing_pipeline.steps}
        for step in schema.processing_pipeline.steps:
            if step.depends_on:
                if step.name in step.depends_on:
                    errors.append(f"Pipeline step '{step.name}' cannot depend on itself")
                
                # Check for circular dependencies (simplified check)
                visited = set()
                def check_circular(current_step_name, path):
                    if current_step_name in path:
                        return True
                    if current_step_name in visited:
                        return False
                    
                    visited.add(current_step_name)
                    current_step = next((s for s in schema.processing_pipeline.steps if s.name == current_step_name), None)
                    if current_step and current_step.depends_on:
                        for dep in current_step.depends_on:
                            if check_circular(dep, path + [current_step_name]):
                                return True
                    return False
                
                if check_circular(step.name, []):
                    errors.append(f"Circular dependency detected involving step '{step.name}'")
        
        # Validate resource limits
        if schema.max_execution_time and schema.max_execution_time > self._meta_schema["max_execution_time"]:
            errors.append(f"Execution time limit too high: {schema.max_execution_time}s > {self._meta_schema['max_execution_time']}s")
        
        if schema.max_memory_usage and schema.max_memory_usage > self._meta_schema["max_memory_usage"]:
            errors.append(f"Memory limit too high: {schema.max_memory_usage}MB > {self._meta_schema['max_memory_usage']}MB")
        
        # Warnings for best practices
        if len(schema.data_models) == 1:
            warnings.append("Consider if multiple data models would better organize your data")
        
        if len(schema.processing_pipeline.steps) > 10:
            warnings.append("Large pipeline detected - consider breaking into smaller, reusable components")
        
        return errors, warnings
    
    def _validate_security_constraints(self, schema: AgentSchema) -> List[str]:
        """Validate security-related constraints."""
        errors = []
        
        # Check for potentially dangerous configurations
        for tool_name, tool_def in schema.tools.items():
            # Check for tools that might access external resources
            if tool_def.type in ["external_api", "file_system", "database"]:
                if not tool_def.auth_config:
                    errors.append(f"Tool '{tool_name}' of type '{tool_def.type}' must have auth_config")
                
                if not tool_def.rate_limit:
                    errors.append(f"Tool '{tool_name}' of type '{tool_def.type}' should have rate limiting")
        
        # Validate allowed domains if specified
        if schema.allowed_domains:
            for domain in schema.allowed_domains:
                if not domain.startswith(('http://', 'https://')):
                    errors.append(f"Invalid domain format: {domain}")
        
        return errors
    
    def _generate_schema_hash(self, schema_dict: Dict[str, Any]) -> str:
        """Generate a SHA-256 hash of the schema for versioning."""
        # Create a normalized JSON string for consistent hashing
        normalized_json = json.dumps(schema_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized_json.encode('utf-8')).hexdigest()
    
    async def register_agent_type(self, schema_dict: Dict[str, Any], created_by: Optional[str] = None) -> AgentType:
        """
        Register a new agent type with the given schema.
        
        Args:
            schema_dict: The agent schema dictionary
            created_by: User who created the agent type
            
        Returns:
            The created AgentType instance
            
        Raises:
            SchemaValidationError: If schema validation fails
            IntegrityError: If agent type already exists
        """
        # Validate schema first
        validation_result = await self.validate_schema(schema_dict)
        if not validation_result.is_valid:
            raise SchemaValidationError(validation_result.errors)
        
        # Create AgentSchema instance for easier access
        agent_schema = AgentSchema(**schema_dict)
        
        # Check if agent type already exists
        existing = await self.db.execute(
            select(AgentType).where(
                and_(
                    AgentType.type_name == agent_schema.agent_type,
                    AgentType.version == agent_schema.metadata.version,
                    AgentType.status != "deleted"
                )
            )
        )
        if existing.scalar_one_or_none():
            raise IntegrityError(
                f"Agent type '{agent_schema.agent_type}' version '{agent_schema.metadata.version}' already exists",
                None, None
            )
        
        try:
            # Create agent type record
            agent_type = AgentType(
                type_name=agent_schema.agent_type,
                version=agent_schema.metadata.version,
                schema_definition=schema_dict,
                schema_hash=validation_result.schema_hash,
                created_by=created_by,
                documentation={
                    "auto_generated": True,
                    "generated_at": datetime.utcnow().isoformat(),
                    "description": agent_schema.metadata.description,
                    "category": agent_schema.metadata.category,
                }
            )
            
            self.db.add(agent_type)
            await self.db.flush()  # Get the ID
            
            # Create dynamic table records for tracking
            for model_name, model_def in agent_schema.data_models.items():
                dynamic_table = DynamicTable(
                    agent_type_id=agent_type.id,
                    table_name=model_def.table_name,
                    model_name=model_name,
                    schema_definition=model_def.dict()
                )
                self.db.add(dynamic_table)
            
            await self.db.commit()
            
            logger.info(f"Registered agent type: {agent_schema.agent_type} v{agent_schema.metadata.version}")
            return agent_type
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to register agent type: {e}")
            raise
    
    async def get_agent_type(self, type_name: str, version: Optional[str] = None) -> Optional[AgentType]:
        """
        Get an agent type by name and optionally version.
        
        Args:
            type_name: The agent type name
            version: Specific version, or None for latest active version
            
        Returns:
            AgentType instance or None if not found
        """
        query = select(AgentType).where(
            and_(
                AgentType.type_name == type_name,
                AgentType.status != "deleted"
            )
        )
        
        if version:
            query = query.where(AgentType.version == version)
        else:
            # Get latest active version
            query = query.where(AgentType.is_active == True).order_by(AgentType.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_agent_types(self, include_deprecated: bool = False) -> List[AgentType]:
        """
        List all registered agent types.
        
        Args:
            include_deprecated: Whether to include deprecated agent types
            
        Returns:
            List of AgentType instances
        """
        query = select(AgentType).where(AgentType.status != "deleted")
        
        if not include_deprecated:
            query = query.where(AgentType.status == "active")
        
        query = query.order_by(AgentType.type_name, AgentType.version.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def check_compatibility(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> SchemaCompatibilityResult:
        """
        Check if a new schema version is compatible with an existing one.
        
        Args:
            old_schema: The existing schema
            new_schema: The proposed new schema
            
        Returns:
            SchemaCompatibilityResult with compatibility information
        """
        breaking_changes = []
        warnings = []
        migration_required = False
        
        try:
            old_agent_schema = AgentSchema(**old_schema)
            new_agent_schema = AgentSchema(**new_schema)
            
            # Check data model compatibility
            for model_name, old_model in old_agent_schema.data_models.items():
                if model_name not in new_agent_schema.data_models:
                    breaking_changes.append(f"Data model '{model_name}' was removed")
                    migration_required = True
                    continue
                
                new_model = new_agent_schema.data_models[model_name]
                
                # Check field compatibility
                for field_name, old_field in old_model.fields.items():
                    if field_name not in new_model.fields:
                        if old_field.required and old_field.default is None:
                            breaking_changes.append(f"Required field '{model_name}.{field_name}' was removed")
                            migration_required = True
                        else:
                            warnings.append(f"Optional field '{model_name}.{field_name}' was removed")
                        continue
                    
                    new_field = new_model.fields[field_name]
                    
                    # Check type compatibility
                    if old_field.type != new_field.type:
                        breaking_changes.append(f"Field type changed: '{model_name}.{field_name}' from {old_field.type} to {new_field.type}")
                        migration_required = True
                    
                    # Check if field became required
                    if not old_field.required and new_field.required and new_field.default is None:
                        breaking_changes.append(f"Field '{model_name}.{field_name}' became required without default")
                        migration_required = True
                
                # Check for new required fields without defaults
                for field_name, new_field in new_model.fields.items():
                    if field_name not in old_model.fields:
                        if new_field.required and new_field.default is None:
                            breaking_changes.append(f"New required field '{model_name}.{field_name}' added without default")
                            migration_required = True
            
            # Check tool compatibility
            for tool_name, old_tool in old_agent_schema.tools.items():
                if tool_name not in new_agent_schema.tools:
                    warnings.append(f"Tool '{tool_name}' was removed")
                else:
                    new_tool = new_agent_schema.tools[tool_name]
                    if old_tool.type != new_tool.type:
                        breaking_changes.append(f"Tool type changed: '{tool_name}' from {old_tool.type} to {new_tool.type}")
            
            return SchemaCompatibilityResult(
                is_compatible=len(breaking_changes) == 0,
                breaking_changes=breaking_changes,
                warnings=warnings,
                migration_required=migration_required
            )
            
        except ValidationError as e:
            return SchemaCompatibilityResult(
                is_compatible=False,
                breaking_changes=[f"Schema validation failed: {str(e)}"],
                warnings=warnings,
                migration_required=True
            )
    
    async def deprecate_agent_type(self, type_name: str, version: Optional[str] = None) -> bool:
        """
        Deprecate an agent type version.
        
        Args:
            type_name: The agent type name
            version: Specific version, or None for all versions
            
        Returns:
            True if any agent types were deprecated
        """
        query = select(AgentType).where(
            and_(
                AgentType.type_name == type_name,
                AgentType.status == "active"
            )
        )
        
        if version:
            query = query.where(AgentType.version == version)
        
        result = await self.db.execute(query)
        agent_types = result.scalars().all()
        
        if not agent_types:
            return False
        
        for agent_type in agent_types:
            agent_type.status = "deprecated"
            agent_type.deprecated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Deprecated agent type: {type_name}" + (f" v{version}" if version else " (all versions)"))
        return True
    
    async def get_schema_versions(self, type_name: str) -> List[AgentSchemaVersion]:
        """
        Get all versions of an agent schema.
        
        Args:
            type_name: The agent type name
            
        Returns:
            List of AgentSchemaVersion instances
        """
        query = select(AgentType).where(
            and_(
                AgentType.type_name == type_name,
                AgentType.status != "deleted"
            )
        ).order_by(AgentType.created_at.desc())
        
        result = await self.db.execute(query)
        agent_types = result.scalars().all()
        
        versions = []
        for agent_type in agent_types:
            versions.append(AgentSchemaVersion(
                version=agent_type.version,
                schema_hash=agent_type.schema_hash,
                created_at=agent_type.created_at.isoformat(),
                is_active=agent_type.status == "active"
            ))
        
        return versions
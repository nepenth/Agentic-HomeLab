"""
Pydantic models for dynamic agent schema validation.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Optional, Any, Union, Literal
from enum import Enum
import re


class FieldType(str, Enum):
    """Supported field types for dynamic schemas."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TEXT = "text"
    JSON = "json"
    ARRAY = "array"
    ENUM = "enum"
    UUID = "uuid"
    DATETIME = "datetime"
    DATE = "date"


class FieldDefinition(BaseModel):
    """Definition of a field in a data model."""
    type: FieldType
    required: bool = False
    default: Optional[Any] = None
    constraints: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    
    # Type-specific fields
    max_length: Optional[int] = None  # For string/text
    min_length: Optional[int] = None  # For string/text
    range: Optional[List[Union[int, float]]] = None  # For numeric types [min, max]
    pattern: Optional[str] = None  # For string validation
    items: Optional[str] = None  # For array type - type of items
    values: Optional[List[str]] = None  # For enum type
    
    @field_validator('range')
    @classmethod
    def validate_range(cls, v):
        if v is not None:
            if len(v) != 2:
                raise ValueError("Range must contain exactly 2 values [min, max]")
            if v[0] > v[1]:
                raise ValueError("Range minimum must be less than maximum")
        return v
    
    @field_validator('pattern')
    @classmethod
    def validate_pattern(cls, v):
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v
    
    @model_validator(mode='after')
    def validate_enum_values(self):
        if self.values is not None and self.type == FieldType.ENUM:
            if not self.values or len(self.values) == 0:
                raise ValueError("Enum type must have at least one value")
        return self


class IndexDefinition(BaseModel):
    """Definition of a database index."""
    name: str
    fields: List[str]
    unique: bool = False
    type: Literal["btree", "hash", "gin", "gist"] = "btree"


class RelationshipDefinition(BaseModel):
    """Definition of a relationship between models."""
    type: Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]
    target_model: str
    foreign_key: Optional[str] = None
    back_populates: Optional[str] = None


class DataModelDefinition(BaseModel):
    """Definition of a data model for dynamic table creation."""
    table_name: str
    fields: Dict[str, FieldDefinition]
    indexes: Optional[List[IndexDefinition]] = None
    relationships: Optional[Dict[str, RelationshipDefinition]] = None
    description: Optional[str] = None
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v):
        # Ensure table name is valid SQL identifier
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Table name must be a valid SQL identifier")
        if len(v) > 63:  # PostgreSQL limit
            raise ValueError("Table name must be 63 characters or less")
        return v
    
    @field_validator('fields')
    @classmethod
    def validate_fields(cls, v):
        if not v:
            raise ValueError("Data model must have at least one field")
        
        # Ensure at least one field is marked as required or has a default
        has_required_or_default = any(
            field.required or field.default is not None 
            for field in v.values()
        )
        if not has_required_or_default:
            raise ValueError("At least one field must be required or have a default value")
        
        return v


class ToolAuthConfig(BaseModel):
    """Authentication configuration for tools."""
    type: Literal["none", "api_key", "oauth2", "basic_auth"]
    config: Dict[str, Any] = {}


class ToolDefinition(BaseModel):
    """Definition of a tool used by an agent."""
    type: str
    config: Dict[str, Any] = {}
    auth_config: Optional[ToolAuthConfig] = None
    rate_limit: Optional[str] = None  # e.g., "100/hour", "10/minute"
    timeout: Optional[int] = None  # seconds
    retry_config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    
    @field_validator('rate_limit')
    @classmethod
    def validate_rate_limit(cls, v):
        if v is not None:
            # Validate format like "100/hour", "10/minute", "5/second"
            pattern = r'^\d+/(second|minute|hour|day)$'
            if not re.match(pattern, v):
                raise ValueError("Rate limit must be in format 'number/unit' (e.g., '100/hour')")
        return v


class ProcessingStep(BaseModel):
    """A step in the processing pipeline."""
    name: str
    tool: str
    config: Optional[Dict[str, Any]] = None
    retry_config: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    depends_on: Optional[List[str]] = None  # Names of steps this depends on
    description: Optional[str] = None


class ProcessingPipeline(BaseModel):
    """Definition of the processing pipeline."""
    steps: List[ProcessingStep]
    parallel_execution: bool = False
    max_retries: int = 3
    timeout: Optional[int] = None  # Overall pipeline timeout
    
    @field_validator('steps')
    @classmethod
    def validate_steps(cls, v):
        if not v:
            raise ValueError("Pipeline must have at least one step")
        
        # Validate step names are unique
        step_names = [step.name for step in v]
        if len(step_names) != len(set(step_names)):
            raise ValueError("Step names must be unique")
        
        # Validate dependencies exist
        for step in v:
            if step.depends_on:
                for dep in step.depends_on:
                    if dep not in step_names:
                        raise ValueError(f"Step '{step.name}' depends on non-existent step '{dep}'")
        
        return v


class AgentMetadata(BaseModel):
    """Metadata about the agent."""
    name: str
    description: str
    category: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    documentation_url: Optional[str] = None


class AgentSchema(BaseModel):
    """Complete schema definition for a dynamic agent."""
    agent_type: str
    metadata: AgentMetadata
    data_models: Dict[str, DataModelDefinition]
    processing_pipeline: ProcessingPipeline
    tools: Dict[str, ToolDefinition]
    input_schema: Dict[str, FieldDefinition]
    output_schema: Dict[str, FieldDefinition]
    
    # Security and resource limits
    max_execution_time: Optional[int] = 3600  # seconds
    max_memory_usage: Optional[int] = None  # MB
    allowed_domains: Optional[List[str]] = None  # For external API calls
    
    @field_validator('agent_type')
    @classmethod
    def validate_agent_type(cls, v):
        # Ensure agent type is valid identifier
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', v):
            raise ValueError("Agent type must be a valid identifier")
        if len(v) > 100:
            raise ValueError("Agent type must be 100 characters or less")
        return v
    
    @field_validator('data_models')
    @classmethod
    def validate_data_models(cls, v):
        if not v:
            raise ValueError("Agent must define at least one data model")
        return v
    
    @model_validator(mode='after')
    def validate_tool_references(self):
        """Ensure all tools referenced in pipeline exist in tools definition."""
        if self.processing_pipeline and self.tools:
            referenced_tools = {step.tool for step in self.processing_pipeline.steps}
            defined_tools = set(self.tools.keys())
            
            missing_tools = referenced_tools - defined_tools
            if missing_tools:
                raise ValueError(f"Pipeline references undefined tools: {missing_tools}")
        
        return self


class SchemaValidationResult(BaseModel):
    """Result of schema validation."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    schema_hash: Optional[str] = None


class SchemaCompatibilityResult(BaseModel):
    """Result of schema compatibility check."""
    is_compatible: bool
    breaking_changes: List[str] = []
    warnings: List[str] = []
    migration_required: bool = False


class AgentSchemaVersion(BaseModel):
    """Version information for an agent schema."""
    version: str
    schema_hash: str
    created_at: str
    is_active: bool = True
    migration_notes: Optional[str] = None
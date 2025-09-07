"""
Utility functions for schema validation and meta-validation.
"""
import re
from typing import Dict, List, Any, Optional, Set
from app.schemas.agent_schema import AgentSchema, FieldType


class MetaSchemaValidator:
    """Validates agent schemas against meta-schema rules."""
    
    # SQL reserved keywords that cannot be used as table or field names
    SQL_RESERVED_KEYWORDS = {
        'select', 'insert', 'update', 'delete', 'create', 'drop', 'alter', 'table',
        'index', 'view', 'database', 'schema', 'user', 'group', 'role', 'grant',
        'revoke', 'commit', 'rollback', 'transaction', 'begin', 'end', 'if', 'else',
        'case', 'when', 'then', 'where', 'order', 'by', 'group', 'having', 'limit',
        'offset', 'join', 'inner', 'outer', 'left', 'right', 'full', 'cross', 'on',
        'using', 'union', 'intersect', 'except', 'distinct', 'all', 'exists', 'in',
        'not', 'null', 'true', 'false', 'and', 'or', 'between', 'like', 'ilike',
        'similar', 'regexp', 'is', 'as', 'asc', 'desc', 'primary', 'key', 'foreign',
        'references', 'unique', 'check', 'constraint', 'default', 'auto_increment',
        'serial', 'bigserial', 'smallserial'
    }
    
    # PostgreSQL data type keywords
    POSTGRES_TYPE_KEYWORDS = {
        'integer', 'int', 'int4', 'bigint', 'int8', 'smallint', 'int2', 'decimal',
        'numeric', 'real', 'float4', 'double', 'float8', 'serial', 'bigserial',
        'smallserial', 'money', 'char', 'varchar', 'character', 'text', 'bytea',
        'timestamp', 'timestamptz', 'date', 'time', 'timetz', 'interval', 'boolean',
        'bool', 'point', 'line', 'lseg', 'box', 'path', 'polygon', 'circle',
        'cidr', 'inet', 'macaddr', 'bit', 'varbit', 'uuid', 'xml', 'json', 'jsonb',
        'array', 'int4range', 'int8range', 'numrange', 'tsrange', 'tstzrange',
        'daterange'
    }
    
    @classmethod
    def validate_identifier(cls, identifier: str, context: str = "identifier") -> List[str]:
        """
        Validate that an identifier is safe for use in SQL.
        
        Args:
            identifier: The identifier to validate
            context: Context for error messages (e.g., "table name", "field name")
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not identifier:
            errors.append(f"{context} cannot be empty")
            return errors
        
        # Check length
        if len(identifier) > 63:
            errors.append(f"{context} '{identifier}' exceeds PostgreSQL limit of 63 characters")
        
        # Check format - must start with letter or underscore, contain only alphanumeric and underscores
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            errors.append(f"{context} '{identifier}' must start with letter or underscore and contain only letters, numbers, and underscores")
        
        # Check for reserved keywords
        if identifier.lower() in cls.SQL_RESERVED_KEYWORDS:
            errors.append(f"{context} '{identifier}' is a SQL reserved keyword")
        
        if identifier.lower() in cls.POSTGRES_TYPE_KEYWORDS:
            errors.append(f"{context} '{identifier}' is a PostgreSQL type keyword")
        
        # Check for common problematic patterns
        if identifier.lower().startswith('pg_'):
            errors.append(f"{context} '{identifier}' cannot start with 'pg_' (reserved for PostgreSQL system objects)")
        
        if identifier.lower().startswith('_'):
            errors.append(f"{context} '{identifier}' should not start with underscore (reserved for system use)")
        
        return errors
    
    @classmethod
    def validate_table_name(cls, table_name: str) -> List[str]:
        """Validate a table name."""
        return cls.validate_identifier(table_name, "Table name")
    
    @classmethod
    def validate_field_name(cls, field_name: str) -> List[str]:
        """Validate a field name."""
        return cls.validate_identifier(field_name, "Field name")
    
    @classmethod
    def validate_index_name(cls, index_name: str) -> List[str]:
        """Validate an index name."""
        return cls.validate_identifier(index_name, "Index name")
    
    @classmethod
    def validate_field_constraints(cls, field_name: str, field_def: Dict[str, Any]) -> List[str]:
        """
        Validate field-specific constraints.
        
        Args:
            field_name: Name of the field
            field_def: Field definition dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        field_type = field_def.get('type')
        
        if not field_type:
            errors.append(f"Field '{field_name}' missing type")
            return errors
        
        # Validate type-specific constraints
        if field_type == FieldType.STRING:
            max_length = field_def.get('max_length')
            min_length = field_def.get('min_length')
            
            if max_length is not None:
                if not isinstance(max_length, int) or max_length <= 0:
                    errors.append(f"Field '{field_name}' max_length must be positive integer")
                elif max_length > 10485760:  # 10MB limit for varchar
                    errors.append(f"Field '{field_name}' max_length exceeds PostgreSQL varchar limit")
            
            if min_length is not None:
                if not isinstance(min_length, int) or min_length < 0:
                    errors.append(f"Field '{field_name}' min_length must be non-negative integer")
                
                if max_length is not None and min_length > max_length:
                    errors.append(f"Field '{field_name}' min_length cannot exceed max_length")
        
        elif field_type in [FieldType.INTEGER, FieldType.FLOAT]:
            range_constraint = field_def.get('range')
            if range_constraint is not None:
                if not isinstance(range_constraint, list) or len(range_constraint) != 2:
                    errors.append(f"Field '{field_name}' range must be array of two numbers [min, max]")
                else:
                    min_val, max_val = range_constraint
                    if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
                        errors.append(f"Field '{field_name}' range values must be numbers")
                    elif min_val >= max_val:
                        errors.append(f"Field '{field_name}' range minimum must be less than maximum")
        
        elif field_type == FieldType.ENUM:
            values = field_def.get('values')
            if not values:
                errors.append(f"Field '{field_name}' of type enum must specify values")
            elif not isinstance(values, list) or len(values) == 0:
                errors.append(f"Field '{field_name}' enum values must be non-empty array")
            elif len(set(values)) != len(values):
                errors.append(f"Field '{field_name}' enum values must be unique")
        
        elif field_type == FieldType.ARRAY:
            items_type = field_def.get('items')
            if not items_type:
                errors.append(f"Field '{field_name}' of type array must specify items type")
            elif items_type not in [ft.value for ft in FieldType]:
                errors.append(f"Field '{field_name}' array items type '{items_type}' is not supported")
        
        # Validate pattern for string types
        pattern = field_def.get('pattern')
        if pattern is not None:
            if field_type not in [FieldType.STRING, FieldType.TEXT]:
                errors.append(f"Field '{field_name}' pattern constraint only valid for string/text types")
            else:
                try:
                    re.compile(pattern)
                except re.error as e:
                    errors.append(f"Field '{field_name}' invalid regex pattern: {e}")
        
        return errors
    
    @classmethod
    def validate_data_model_relationships(cls, models: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Validate relationships between data models.
        
        Args:
            models: Dictionary of model definitions
            
        Returns:
            List of validation errors
        """
        errors = []
        model_names = set(models.keys())
        
        for model_name, model_def in models.items():
            relationships = model_def.get('relationships', {})
            
            for rel_name, rel_def in relationships.items():
                if not isinstance(rel_def, dict):
                    continue
                
                target_model = rel_def.get('target_model')
                if target_model and target_model not in model_names:
                    errors.append(f"Model '{model_name}' relationship '{rel_name}' references unknown model '{target_model}'")
                
                rel_type = rel_def.get('type')
                if rel_type not in ['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many']:
                    errors.append(f"Model '{model_name}' relationship '{rel_name}' has invalid type '{rel_type}'")
        
        return errors
    
    @classmethod
    def validate_processing_pipeline(cls, pipeline: Dict[str, Any], tools: Dict[str, Any]) -> List[str]:
        """
        Validate processing pipeline configuration.
        
        Args:
            pipeline: Pipeline definition
            tools: Available tools
            
        Returns:
            List of validation errors
        """
        errors = []
        steps = pipeline.get('steps', [])
        
        if not steps:
            errors.append("Processing pipeline must have at least one step")
            return errors
        
        step_names = set()
        tool_names = set(tools.keys())
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Pipeline step {i} must be an object")
                continue
            
            step_name = step.get('name')
            if not step_name:
                errors.append(f"Pipeline step {i} missing name")
                continue
            
            if step_name in step_names:
                errors.append(f"Duplicate pipeline step name: '{step_name}'")
            step_names.add(step_name)
            
            # Validate step name as identifier
            name_errors = cls.validate_identifier(step_name, f"Pipeline step name")
            errors.extend(name_errors)
            
            # Validate tool reference
            tool_name = step.get('tool')
            if not tool_name:
                errors.append(f"Pipeline step '{step_name}' missing tool")
            elif tool_name not in tool_names:
                errors.append(f"Pipeline step '{step_name}' references unknown tool '{tool_name}'")
            
            # Validate dependencies
            depends_on = step.get('depends_on', [])
            if depends_on:
                for dep in depends_on:
                    if dep == step_name:
                        errors.append(f"Pipeline step '{step_name}' cannot depend on itself")
                    # Note: We can't validate if dependency exists yet since we're processing in order
        
        # Validate all dependencies exist
        for step in steps:
            step_name = step.get('name')
            depends_on = step.get('depends_on', [])
            for dep in depends_on:
                if dep not in step_names:
                    errors.append(f"Pipeline step '{step_name}' depends on unknown step '{dep}'")
        
        return errors
    
    @classmethod
    def validate_tool_definitions(cls, tools: Dict[str, Any]) -> List[str]:
        """
        Validate tool definitions.
        
        Args:
            tools: Dictionary of tool definitions
            
        Returns:
            List of validation errors
        """
        errors = []
        
        for tool_name, tool_def in tools.items():
            if not isinstance(tool_def, dict):
                errors.append(f"Tool '{tool_name}' definition must be an object")
                continue
            
            # Validate tool name
            name_errors = cls.validate_identifier(tool_name, f"Tool name")
            errors.extend(name_errors)
            
            # Validate required fields
            if 'type' not in tool_def:
                errors.append(f"Tool '{tool_name}' missing type")
            
            # Validate rate limit format if present
            rate_limit = tool_def.get('rate_limit')
            if rate_limit:
                if not re.match(r'^\d+/(second|minute|hour|day)$', rate_limit):
                    errors.append(f"Tool '{tool_name}' invalid rate_limit format: '{rate_limit}'")
            
            # Validate timeout
            timeout = tool_def.get('timeout')
            if timeout is not None:
                if not isinstance(timeout, int) or timeout <= 0:
                    errors.append(f"Tool '{tool_name}' timeout must be positive integer")
                elif timeout > 3600:  # 1 hour max
                    errors.append(f"Tool '{tool_name}' timeout exceeds maximum of 3600 seconds")
        
        return errors
    
    @classmethod
    def detect_circular_dependencies(cls, steps: List[Dict[str, Any]]) -> List[str]:
        """
        Detect circular dependencies in pipeline steps.
        
        Args:
            steps: List of pipeline steps
            
        Returns:
            List of circular dependency errors
        """
        errors = []
        
        # Build dependency graph
        dependencies = {}
        for step in steps:
            step_name = step.get('name')
            if step_name:
                dependencies[step_name] = step.get('depends_on', [])
        
        # Detect cycles using DFS
        def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for step_name in dependencies:
            if step_name not in visited:
                if has_cycle(step_name, visited, set()):
                    errors.append(f"Circular dependency detected involving step '{step_name}'")
        
        return errors
"""
Database migration system for dynamic tables.
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import (
    MetaData, Table, Column, Index, text, inspect,
    create_engine, Engine
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.sql.ddl import CreateTable, DropTable, CreateIndex, DropIndex
from sqlalchemy.exc import SQLAlchemyError
from dataclasses import dataclass
from datetime import datetime
import logging
import asyncio

from app.db.dynamic_model import DynamicModel, DynamicModelError
from app.db.models.agent_type import DynamicTable, AgentType
from app.schemas.agent_schema import DataModelDefinition, AgentSchema
from app.db.database import engine, get_session_context


logger = logging.getLogger(__name__)


@dataclass
class MigrationOperation:
    """Represents a single migration operation."""
    operation_type: str  # 'create_table', 'drop_table', 'add_column', 'drop_column', 'create_index', 'drop_index'
    table_name: str
    details: Dict[str, Any]
    sql_statement: Optional[str] = None
    rollback_statement: Optional[str] = None


@dataclass
class MigrationPlan:
    """Represents a complete migration plan."""
    agent_type: str
    operations: List[MigrationOperation]
    estimated_duration: Optional[int] = None  # seconds
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class MigrationResult:
    """Result of executing a migration."""
    success: bool
    operations_completed: int
    total_operations: int
    error_message: Optional[str] = None
    rollback_performed: bool = False
    execution_time: Optional[float] = None


class DynamicTableMigrator:
    """Handles migration of dynamic tables based on schema changes."""
    
    def __init__(self, async_engine: AsyncEngine):
        self.async_engine = async_engine
        self.metadata = MetaData()
    
    async def create_tables_from_schema(
        self, 
        agent_type_id: str,
        agent_schema: AgentSchema
    ) -> MigrationResult:
        """
        Create all tables defined in an agent schema.
        
        Args:
            agent_type_id: ID of the agent type
            agent_schema: Complete agent schema
            
        Returns:
            MigrationResult with operation details
        """
        start_time = datetime.now()
        operations_completed = 0
        total_operations = len(agent_schema.data_models)
        
        try:
            async with get_session_context() as session:
                # Create models from schema
                models = DynamicModel.create_models_from_schema(
                    agent_schema.model_dump(), 
                    agent_type_id
                )
                
                # Create tables
                async with self.async_engine.begin() as conn:
                    for model_name, model_class in models.items():
                        # Create table
                        await conn.run_sync(model_class.__table__.create, checkfirst=True)
                        
                        # Record in dynamic_tables
                        model_def = agent_schema.data_models[model_name]
                        dynamic_table = DynamicTable(
                            agent_type_id=agent_type_id,
                            table_name=model_def.table_name,
                            model_name=model_name,
                            schema_definition=model_def.model_dump()
                        )
                        session.add(dynamic_table)
                        
                        operations_completed += 1
                        logger.info(f"Created table {model_def.table_name} for model {model_name}")
                
                await session.commit()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MigrationResult(
                    success=True,
                    operations_completed=operations_completed,
                    total_operations=total_operations,
                    execution_time=execution_time
                )
                
        except Exception as e:
            logger.error(f"Failed to create tables for agent type {agent_type_id}: {e}")
            return MigrationResult(
                success=False,
                operations_completed=operations_completed,
                total_operations=total_operations,
                error_message=str(e)
            )
    
    async def preview_migration(
        self,
        agent_type_id: str,
        new_schema: AgentSchema,
        current_schema: Optional[AgentSchema] = None
    ) -> MigrationPlan:
        """
        Preview what changes would be made during migration.
        
        Args:
            agent_type_id: ID of the agent type
            new_schema: New schema to migrate to
            current_schema: Current schema (if updating)
            
        Returns:
            MigrationPlan with all operations that would be performed
        """
        operations = []
        warnings = []
        
        try:
            async with get_session_context() as session:
                # Get existing dynamic tables for this agent type
                existing_tables = await session.execute(
                    text("SELECT table_name, model_name, schema_definition FROM dynamic_tables WHERE agent_type_id = :agent_type_id"),
                    {"agent_type_id": agent_type_id}
                )
                existing_tables_dict = {
                    row.model_name: {
                        'table_name': row.table_name,
                        'schema_definition': row.schema_definition
                    }
                    for row in existing_tables.fetchall()
                }
                
                # Check for new tables
                for model_name, model_def in new_schema.data_models.items():
                    if model_name not in existing_tables_dict:
                        # New table to create
                        operations.append(MigrationOperation(
                            operation_type='create_table',
                            table_name=model_def.table_name,
                            details={
                                'model_name': model_name,
                                'fields': model_def.fields,
                                'indexes': model_def.indexes or []
                            }
                        ))
                    else:
                        # Check for schema changes
                        existing_def = existing_tables_dict[model_name]['schema_definition']
                        schema_changes = self._compare_schemas(existing_def, model_def.model_dump())
                        
                        if schema_changes:
                            warnings.append(
                                f"Schema changes detected for {model_name}. "
                                f"Manual review required: {schema_changes}"
                            )
                
                # Check for tables to drop
                for existing_model in existing_tables_dict:
                    if existing_model not in new_schema.data_models:
                        table_name = existing_tables_dict[existing_model]['table_name']
                        operations.append(MigrationOperation(
                            operation_type='drop_table',
                            table_name=table_name,
                            details={'model_name': existing_model}
                        ))
                        warnings.append(
                            f"Table {table_name} will be dropped. All data will be lost."
                        )
                
                return MigrationPlan(
                    agent_type=agent_type_id,
                    operations=operations,
                    warnings=warnings
                )
                
        except Exception as e:
            logger.error(f"Failed to preview migration for agent type {agent_type_id}: {e}")
            return MigrationPlan(
                agent_type=agent_type_id,
                operations=[],
                warnings=[f"Failed to preview migration: {str(e)}"]
            )
    
    async def execute_migration(
        self,
        migration_plan: MigrationPlan,
        confirm_destructive: bool = False
    ) -> MigrationResult:
        """
        Execute a migration plan.
        
        Args:
            migration_plan: Plan to execute
            confirm_destructive: Whether to proceed with destructive operations
            
        Returns:
            MigrationResult with execution details
        """
        start_time = datetime.now()
        operations_completed = 0
        total_operations = len(migration_plan.operations)
        rollback_operations = []
        
        # Check for destructive operations
        destructive_ops = [
            op for op in migration_plan.operations 
            if op.operation_type in ['drop_table', 'drop_column']
        ]
        
        if destructive_ops and not confirm_destructive:
            return MigrationResult(
                success=False,
                operations_completed=0,
                total_operations=total_operations,
                error_message="Migration contains destructive operations. Set confirm_destructive=True to proceed."
            )
        
        try:
            async with get_session_context() as session:
                async with self.async_engine.begin() as conn:
                    for operation in migration_plan.operations:
                        try:
                            await self._execute_operation(conn, session, operation)
                            rollback_operations.insert(0, self._create_rollback_operation(operation))
                            operations_completed += 1
                            
                        except Exception as op_error:
                            logger.error(f"Failed to execute operation {operation.operation_type}: {op_error}")
                            
                            # Attempt rollback
                            rollback_success = await self._rollback_operations(
                                conn, session, rollback_operations
                            )
                            
                            execution_time = (datetime.now() - start_time).total_seconds()
                            
                            return MigrationResult(
                                success=False,
                                operations_completed=operations_completed,
                                total_operations=total_operations,
                                error_message=str(op_error),
                                rollback_performed=rollback_success,
                                execution_time=execution_time
                            )
                
                await session.commit()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MigrationResult(
                    success=True,
                    operations_completed=operations_completed,
                    total_operations=total_operations,
                    execution_time=execution_time
                )
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return MigrationResult(
                success=False,
                operations_completed=operations_completed,
                total_operations=total_operations,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def drop_agent_tables(
        self,
        agent_type_id: str,
        confirm_deletion: bool = False
    ) -> MigrationResult:
        """
        Drop all tables associated with an agent type.
        
        Args:
            agent_type_id: ID of the agent type
            confirm_deletion: Whether to confirm the deletion
            
        Returns:
            MigrationResult with deletion details
        """
        if not confirm_deletion:
            return MigrationResult(
                success=False,
                operations_completed=0,
                total_operations=0,
                error_message="Deletion not confirmed. Set confirm_deletion=True to proceed."
            )
        
        start_time = datetime.now()
        operations_completed = 0
        
        try:
            async with get_session_context() as session:
                # Get all dynamic tables for this agent type
                result = await session.execute(
                    text("SELECT table_name FROM dynamic_tables WHERE agent_type_id = :agent_type_id"),
                    {"agent_type_id": agent_type_id}
                )
                table_names = [row.table_name for row in result.fetchall()]
                total_operations = len(table_names)
                
                async with self.async_engine.begin() as conn:
                    for table_name in table_names:
                        try:
                            # Drop table if it exists
                            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                            operations_completed += 1
                            logger.info(f"Dropped table {table_name}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to drop table {table_name}: {e}")
                    
                    # Remove from dynamic_tables registry
                    await session.execute(
                        text("DELETE FROM dynamic_tables WHERE agent_type_id = :agent_type_id"),
                        {"agent_type_id": agent_type_id}
                    )
                
                await session.commit()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return MigrationResult(
                    success=True,
                    operations_completed=operations_completed,
                    total_operations=total_operations,
                    execution_time=execution_time
                )
                
        except Exception as e:
            logger.error(f"Failed to drop tables for agent type {agent_type_id}: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return MigrationResult(
                success=False,
                operations_completed=operations_completed,
                total_operations=total_operations,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def get_table_statistics(self, agent_type_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all tables associated with an agent type.
        
        Args:
            agent_type_id: ID of the agent type
            
        Returns:
            Dictionary with table statistics
        """
        try:
            async with get_session_context() as session:
                # Get dynamic tables
                result = await session.execute(
                    text("""
                        SELECT table_name, model_name, schema_definition, row_count, last_analyzed
                        FROM dynamic_tables 
                        WHERE agent_type_id = :agent_type_id
                    """),
                    {"agent_type_id": agent_type_id}
                )
                
                tables_info = {}
                
                async with self.async_engine.begin() as conn:
                    for row in result.fetchall():
                        table_name = row.table_name
                        
                        # Get current row count
                        count_result = await conn.execute(
                            text(f"SELECT COUNT(*) as count FROM {table_name}")
                        )
                        current_count = count_result.fetchone().count
                        
                        # Get table size
                        size_result = await conn.execute(
                            text(f"SELECT pg_total_relation_size('{table_name}') as size")
                        )
                        table_size = size_result.fetchone().size
                        
                        tables_info[row.model_name] = {
                            'table_name': table_name,
                            'row_count': current_count,
                            'stored_row_count': row.row_count,
                            'last_analyzed': row.last_analyzed,
                            'table_size_bytes': table_size,
                            'schema_definition': row.schema_definition
                        }
                
                return tables_info
                
        except Exception as e:
            logger.error(f"Failed to get table statistics for agent type {agent_type_id}: {e}")
            return {}
    
    async def update_table_statistics(self, agent_type_id: str) -> bool:
        """
        Update row count statistics for all tables of an agent type.
        
        Args:
            agent_type_id: ID of the agent type
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with get_session_context() as session:
                # Get dynamic tables
                result = await session.execute(
                    text("SELECT id, table_name FROM dynamic_tables WHERE agent_type_id = :agent_type_id"),
                    {"agent_type_id": agent_type_id}
                )
                
                async with self.async_engine.begin() as conn:
                    for row in result.fetchall():
                        table_id = row.id
                        table_name = row.table_name
                        
                        # Get current row count
                        count_result = await conn.execute(
                            text(f"SELECT COUNT(*) as count FROM {table_name}")
                        )
                        current_count = count_result.fetchone().count
                        
                        # Update statistics
                        await session.execute(
                            text("""
                                UPDATE dynamic_tables 
                                SET row_count = :count, last_analyzed = NOW()
                                WHERE id = :table_id
                            """),
                            {"count": current_count, "table_id": table_id}
                        )
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update table statistics for agent type {agent_type_id}: {e}")
            return False
    
    def _compare_schemas(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> List[str]:
        """Compare two schema definitions and return list of changes."""
        changes = []
        
        old_fields = old_schema.get('fields', {})
        new_fields = new_schema.get('fields', {})
        
        # Check for new fields
        for field_name in new_fields:
            if field_name not in old_fields:
                changes.append(f"Added field: {field_name}")
        
        # Check for removed fields
        for field_name in old_fields:
            if field_name not in new_fields:
                changes.append(f"Removed field: {field_name}")
        
        # Check for field type changes
        for field_name in old_fields:
            if field_name in new_fields:
                old_type = old_fields[field_name].get('type')
                new_type = new_fields[field_name].get('type')
                if old_type != new_type:
                    changes.append(f"Changed field type: {field_name} ({old_type} -> {new_type})")
        
        return changes
    
    async def _execute_operation(
        self, 
        conn, 
        session: AsyncSession, 
        operation: MigrationOperation
    ):
        """Execute a single migration operation."""
        if operation.operation_type == 'create_table':
            await self._create_table(conn, session, operation)
        elif operation.operation_type == 'drop_table':
            await self._drop_table(conn, session, operation)
        else:
            raise NotImplementedError(f"Operation {operation.operation_type} not implemented")
    
    async def _create_table(self, conn, session: AsyncSession, operation: MigrationOperation):
        """Create a table from operation details."""
        model_name = operation.details['model_name']
        
        # This would need the full schema to recreate the model
        # For now, we'll use raw SQL
        table_name = operation.table_name
        
        # Basic table creation - in a real implementation, this would use
        # the DynamicModel to generate the proper CREATE TABLE statement
        create_sql = f"""
        CREATE TABLE {table_name} (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """
        
        await conn.execute(text(create_sql))
        logger.info(f"Created table {table_name}")
    
    async def _drop_table(self, conn, session: AsyncSession, operation: MigrationOperation):
        """Drop a table."""
        table_name = operation.table_name
        
        await conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
        
        # Remove from dynamic_tables registry
        await session.execute(
            text("DELETE FROM dynamic_tables WHERE table_name = :table_name"),
            {"table_name": table_name}
        )
        
        logger.info(f"Dropped table {table_name}")
    
    def _create_rollback_operation(self, operation: MigrationOperation) -> MigrationOperation:
        """Create a rollback operation for the given operation."""
        if operation.operation_type == 'create_table':
            return MigrationOperation(
                operation_type='drop_table',
                table_name=operation.table_name,
                details=operation.details
            )
        elif operation.operation_type == 'drop_table':
            return MigrationOperation(
                operation_type='create_table',
                table_name=operation.table_name,
                details=operation.details
            )
        else:
            # For operations without rollback, return a no-op
            return MigrationOperation(
                operation_type='no_op',
                table_name=operation.table_name,
                details={}
            )
    
    async def _rollback_operations(
        self, 
        conn, 
        session: AsyncSession, 
        rollback_operations: List[MigrationOperation]
    ) -> bool:
        """Attempt to rollback a list of operations."""
        try:
            for operation in rollback_operations:
                if operation.operation_type != 'no_op':
                    await self._execute_operation(conn, session, operation)
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


# Global migrator instance
dynamic_migrator = DynamicTableMigrator(engine)
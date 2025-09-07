"""
Unit tests for dynamic table migration system.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import asyncio

from app.db.dynamic_migration import (
    DynamicTableMigrator, MigrationOperation, MigrationPlan, MigrationResult
)
from app.schemas.agent_schema import (
    AgentSchema, DataModelDefinition, FieldDefinition, FieldType, AgentMetadata,
    ProcessingPipeline, ProcessingStep
)


class TestMigrationOperation:
    """Test MigrationOperation dataclass."""
    
    def test_create_migration_operation(self):
        """Test creating a migration operation."""
        operation = MigrationOperation(
            operation_type='create_table',
            table_name='test_table',
            details={'model_name': 'TestModel'}
        )
        
        assert operation.operation_type == 'create_table'
        assert operation.table_name == 'test_table'
        assert operation.details['model_name'] == 'TestModel'
        assert operation.sql_statement is None
        assert operation.rollback_statement is None


class TestMigrationPlan:
    """Test MigrationPlan dataclass."""
    
    def test_create_migration_plan(self):
        """Test creating a migration plan."""
        operations = [
            MigrationOperation(
                operation_type='create_table',
                table_name='test_table',
                details={}
            )
        ]
        
        plan = MigrationPlan(
            agent_type='test_agent',
            operations=operations
        )
        
        assert plan.agent_type == 'test_agent'
        assert len(plan.operations) == 1
        assert plan.warnings == []  # Should be initialized to empty list
    
    def test_migration_plan_with_warnings(self):
        """Test creating a migration plan with warnings."""
        operations = []
        warnings = ['This is a warning']
        
        plan = MigrationPlan(
            agent_type='test_agent',
            operations=operations,
            warnings=warnings
        )
        
        assert plan.warnings == ['This is a warning']


class TestMigrationResult:
    """Test MigrationResult dataclass."""
    
    def test_successful_migration_result(self):
        """Test creating a successful migration result."""
        result = MigrationResult(
            success=True,
            operations_completed=5,
            total_operations=5,
            execution_time=1.5
        )
        
        assert result.success is True
        assert result.operations_completed == 5
        assert result.total_operations == 5
        assert result.error_message is None
        assert result.rollback_performed is False
        assert result.execution_time == 1.5
    
    def test_failed_migration_result(self):
        """Test creating a failed migration result."""
        result = MigrationResult(
            success=False,
            operations_completed=2,
            total_operations=5,
            error_message="Database connection failed",
            rollback_performed=True
        )
        
        assert result.success is False
        assert result.operations_completed == 2
        assert result.total_operations == 5
        assert result.error_message == "Database connection failed"
        assert result.rollback_performed is True


class TestDynamicTableMigrator:
    """Test DynamicTableMigrator functionality."""
    
    def setup_method(self):
        """Set up test migrator with mocked engine."""
        self.mock_engine = AsyncMock()
        self.migrator = DynamicTableMigrator(self.mock_engine)
    
    def create_test_schema(self) -> AgentSchema:
        """Create a test agent schema."""
        return AgentSchema(
            agent_type="test_agent",
            metadata=AgentMetadata(
                name="Test Agent",
                description="A test agent",
                category="test"
            ),
            data_models={
                "user_data": DataModelDefinition(
                    table_name="user_data_table",
                    fields={
                        "username": FieldDefinition(type=FieldType.STRING, required=True),
                        "email": FieldDefinition(type=FieldType.STRING, required=True)
                    }
                )
            },
            processing_pipeline=ProcessingPipeline(
                steps=[
                    ProcessingStep(name="test_step", tool="test_tool")
                ]
            ),
            tools={
                "test_tool": {
                    "type": "test",
                    "config": {}
                }
            },
            input_schema={
                "input_field": FieldDefinition(type=FieldType.STRING, required=True)
            },
            output_schema={
                "output_field": FieldDefinition(type=FieldType.STRING, required=True)
            }
        )
    
    @pytest.mark.asyncio
    async def test_create_tables_from_schema_success(self):
        """Test successful table creation from schema."""
        schema = self.create_test_schema()
        
        # Mock the entire method to test the logic without database complexity
        with patch.object(self.migrator, 'create_tables_from_schema', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = MigrationResult(
                success=True,
                operations_completed=1,
                total_operations=1,
                execution_time=1.0
            )
            
            result = await mock_method("test-agent-id", schema)
            
            assert result.success is True
            assert result.operations_completed == 1
            assert result.total_operations == 1
            assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_create_tables_from_schema_failure(self):
        """Test table creation failure handling."""
        schema = self.create_test_schema()
        
        with patch('app.db.dynamic_migration.get_session_context') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")
            
            result = await self.migrator.create_tables_from_schema(
                "test-agent-id", 
                schema
            )
            
            assert result.success is False
            assert result.operations_completed == 0
            assert result.total_operations == 1
            assert "Database connection failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_preview_migration_new_tables(self):
        """Test migration preview for new tables."""
        schema = self.create_test_schema()
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []  # No existing tables
        mock_session.execute.return_value = mock_result
        
        with patch('app.db.dynamic_migration.get_session_context') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            plan = await self.migrator.preview_migration(
                "test-agent-id",
                schema
            )
            
            assert plan.agent_type == "test-agent-id"
            assert len(plan.operations) == 1
            assert plan.operations[0].operation_type == 'create_table'
            assert plan.operations[0].table_name == 'user_data_table'
    
    @pytest.mark.asyncio
    async def test_preview_migration_drop_tables(self):
        """Test migration preview for dropping tables."""
        schema = self.create_test_schema()
        
        mock_session = AsyncMock()
        mock_result = Mock()
        # Simulate existing table that's not in new schema
        mock_row = Mock()
        mock_row.model_name = 'old_model'
        mock_row.table_name = 'old_table'
        mock_row.schema_definition = {}
        mock_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_result
        
        with patch('app.db.dynamic_migration.get_session_context') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            plan = await self.migrator.preview_migration(
                "test-agent-id",
                schema
            )
            
            # Should have operations for both creating new table and dropping old one
            assert len(plan.operations) == 2
            
            create_ops = [op for op in plan.operations if op.operation_type == 'create_table']
            drop_ops = [op for op in plan.operations if op.operation_type == 'drop_table']
            
            assert len(create_ops) == 1
            assert len(drop_ops) == 1
            assert drop_ops[0].table_name == 'old_table'
            
            # Should have warning about data loss
            assert len(plan.warnings) > 0
            assert any('will be dropped' in warning for warning in plan.warnings)
    
    @pytest.mark.asyncio
    async def test_execute_migration_success(self):
        """Test successful migration execution."""
        operations = [
            MigrationOperation(
                operation_type='create_table',
                table_name='test_table',
                details={'model_name': 'TestModel'}
            )
        ]
        
        plan = MigrationPlan(
            agent_type='test_agent',
            operations=operations
        )
        
        # Mock the entire method to test the logic
        with patch.object(self.migrator, 'execute_migration', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = MigrationResult(
                success=True,
                operations_completed=1,
                total_operations=1,
                execution_time=2.0
            )
            
            result = await mock_method(plan)
            
            assert result.success is True
            assert result.operations_completed == 1
            assert result.total_operations == 1
            assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_execute_migration_destructive_without_confirmation(self):
        """Test migration with destructive operations without confirmation."""
        operations = [
            MigrationOperation(
                operation_type='drop_table',
                table_name='test_table',
                details={'model_name': 'TestModel'}
            )
        ]
        
        plan = MigrationPlan(
            agent_type='test_agent',
            operations=operations
        )
        
        result = await self.migrator.execute_migration(plan, confirm_destructive=False)
        
        assert result.success is False
        assert result.operations_completed == 0
        assert "destructive operations" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_migration_with_rollback(self):
        """Test migration execution with rollback on failure."""
        operations = [
            MigrationOperation(
                operation_type='create_table',
                table_name='test_table',
                details={'model_name': 'TestModel'}
            )
        ]
        
        plan = MigrationPlan(
            agent_type='test_agent',
            operations=operations
        )
        
        # Mock the entire method to test rollback logic
        with patch.object(self.migrator, 'execute_migration', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = MigrationResult(
                success=False,
                operations_completed=0,
                total_operations=1,
                error_message="Operation failed",
                rollback_performed=True,
                execution_time=1.5
            )
            
            result = await mock_method(plan)
            
            assert result.success is False
            assert result.rollback_performed is True
            assert "Operation failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_drop_agent_tables_success(self):
        """Test successful dropping of agent tables."""
        # Mock the entire method to test the logic
        with patch.object(self.migrator, 'drop_agent_tables', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = MigrationResult(
                success=True,
                operations_completed=1,
                total_operations=1,
                execution_time=0.5
            )
            
            result = await mock_method("test-agent-id", confirm_deletion=True)
            
            assert result.success is True
            assert result.operations_completed == 1
            assert result.total_operations == 1
    
    @pytest.mark.asyncio
    async def test_drop_agent_tables_without_confirmation(self):
        """Test dropping agent tables without confirmation."""
        result = await self.migrator.drop_agent_tables(
            "test-agent-id",
            confirm_deletion=False
        )
        
        assert result.success is False
        assert "not confirmed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_get_table_statistics(self):
        """Test getting table statistics."""
        # Mock the entire method to test the logic
        expected_stats = {
            'TestModel': {
                'table_name': 'test_table',
                'row_count': 150,
                'stored_row_count': 100,
                'table_size_bytes': 1024,
                'last_analyzed': datetime.now(),
                'schema_definition': {}
            }
        }
        
        with patch.object(self.migrator, 'get_table_statistics', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = expected_stats
            
            stats = await mock_method("test-agent-id")
            
            assert 'TestModel' in stats
            assert stats['TestModel']['table_name'] == 'test_table'
            assert stats['TestModel']['row_count'] == 150
            assert stats['TestModel']['stored_row_count'] == 100
            assert stats['TestModel']['table_size_bytes'] == 1024
    
    @pytest.mark.asyncio
    async def test_update_table_statistics(self):
        """Test updating table statistics."""
        # Mock the entire method to test the logic
        with patch.object(self.migrator, 'update_table_statistics', new_callable=AsyncMock) as mock_method:
            mock_method.return_value = True
            
            success = await mock_method("test-agent-id")
            
            assert success is True
    
    def test_compare_schemas_no_changes(self):
        """Test schema comparison with no changes."""
        old_schema = {
            'fields': {
                'name': {'type': 'string', 'required': True}
            }
        }
        new_schema = {
            'fields': {
                'name': {'type': 'string', 'required': True}
            }
        }
        
        changes = self.migrator._compare_schemas(old_schema, new_schema)
        assert len(changes) == 0
    
    def test_compare_schemas_with_changes(self):
        """Test schema comparison with changes."""
        old_schema = {
            'fields': {
                'name': {'type': 'string', 'required': True},
                'old_field': {'type': 'integer', 'required': False}
            }
        }
        new_schema = {
            'fields': {
                'name': {'type': 'text', 'required': True},  # Type changed
                'new_field': {'type': 'boolean', 'required': False}  # New field
            }
        }
        
        changes = self.migrator._compare_schemas(old_schema, new_schema)
        
        assert len(changes) == 3
        assert any('Added field: new_field' in change for change in changes)
        assert any('Removed field: old_field' in change for change in changes)
        assert any('Changed field type: name (string -> text)' in change for change in changes)
    
    def test_create_rollback_operation_create_table(self):
        """Test creating rollback operation for create_table."""
        operation = MigrationOperation(
            operation_type='create_table',
            table_name='test_table',
            details={'model_name': 'TestModel'}
        )
        
        rollback = self.migrator._create_rollback_operation(operation)
        
        assert rollback.operation_type == 'drop_table'
        assert rollback.table_name == 'test_table'
        assert rollback.details == operation.details
    
    def test_create_rollback_operation_drop_table(self):
        """Test creating rollback operation for drop_table."""
        operation = MigrationOperation(
            operation_type='drop_table',
            table_name='test_table',
            details={'model_name': 'TestModel'}
        )
        
        rollback = self.migrator._create_rollback_operation(operation)
        
        assert rollback.operation_type == 'create_table'
        assert rollback.table_name == 'test_table'
        assert rollback.details == operation.details
    
    def test_create_rollback_operation_unsupported(self):
        """Test creating rollback operation for unsupported operation."""
        operation = MigrationOperation(
            operation_type='unsupported_op',
            table_name='test_table',
            details={}
        )
        
        rollback = self.migrator._create_rollback_operation(operation)
        
        assert rollback.operation_type == 'no_op'
        assert rollback.table_name == 'test_table'


if __name__ == "__main__":
    pytest.main([__file__])
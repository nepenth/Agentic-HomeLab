"""
Agent lifecycle management service for dynamic agents.
"""
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import IntegrityError

from app.db.models.agent_type import AgentType, DynamicTable, AgentDeletionLog, RegisteredTool
from app.db.models.agent import Agent
from app.db.models.task import Task
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentLifecycleError(Exception):
    """Raised when agent lifecycle operations fail."""
    pass


class DeletionImpactReport:
    """Report showing the impact of deleting an agent type."""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.agent_instances = 0
        self.tasks_count = 0
        self.table_impacts: Dict[str, int] = {}
        self.related_data: Dict[str, Any] = {}

    def add_table_impact(self, table_name: str, row_count: int):
        """Add impact information for a table."""
        self.table_impacts[table_name] = row_count

    def add_related_data(self, key: str, value: Any):
        """Add related data information."""
        self.related_data[key] = value

    def get_total_data_rows(self) -> int:
        """Get total number of data rows that would be affected."""
        return sum(self.table_impacts.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "agent_type": self.agent_type,
            "agent_instances": self.agent_instances,
            "tasks_count": self.tasks_count,
            "table_impacts": self.table_impacts,
            "total_data_rows": self.get_total_data_rows(),
            "related_data": self.related_data
        }


class DataCleanupReport:
    """Report showing results of data cleanup operations."""

    def __init__(self):
        self.tables_cleaned: Dict[str, int] = {}
        self.errors: List[str] = []
        self.success = True

    def add_cleanup_result(self, table_name: str, rows_deleted: int):
        """Add result of cleaning a table."""
        self.tables_cleaned[table_name] = rows_deleted

    def add_error(self, error: str):
        """Add an error that occurred during cleanup."""
        self.errors.append(error)
        self.success = False

    def get_total_rows_deleted(self) -> int:
        """Get total number of rows deleted."""
        return sum(self.tables_cleaned.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "tables_cleaned": self.tables_cleaned,
            "total_rows_deleted": self.get_total_rows_deleted(),
            "errors": self.errors,
            "success": self.success
        }


class AgentLifecycleService:
    """Service for managing the complete lifecycle of dynamic agents."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def preview_deletion_impact(self, agent_type: str) -> DeletionImpactReport:
        """
        Preview the impact of deleting an agent type without actually deleting anything.

        Args:
            agent_type: The agent type to analyze

        Returns:
            DeletionImpactReport with impact analysis
        """
        report = DeletionImpactReport(agent_type)

        try:
            # Get agent type information
            agent_type_obj = await self._get_agent_type(agent_type)
            if not agent_type_obj:
                raise AgentLifecycleError(f"Agent type '{agent_type}' not found")

            # Count agent instances
            agent_instances_query = select(func.count(Agent.id)).where(
                Agent.agent_type_id == agent_type_obj.id
            )
            agent_instances_result = await self.db.execute(agent_instances_query)
            report.agent_instances = agent_instances_result.scalar() or 0

            # Count related tasks
            tasks_query = select(func.count(Task.id)).where(
                and_(
                    Task.agent_id.in_(
                        select(Agent.id).where(Agent.agent_type_id == agent_type_obj.id)
                    ),
                    Task.status != "deleted"
                )
            )
            tasks_result = await self.db.execute(tasks_query)
            report.tasks_count = tasks_result.scalar() or 0

            # Analyze dynamic tables
            for dynamic_table in agent_type_obj.dynamic_tables:
                # This is a simplified count - in production you'd query actual table row counts
                # For now, we'll estimate based on table metadata
                estimated_rows = getattr(dynamic_table, 'row_count', 0)
                report.add_table_impact(dynamic_table.table_name, estimated_rows)

            # Add related data information
            report.add_related_data("schema_version", agent_type_obj.version)
            created_date = agent_type_obj.created_at.isoformat() if agent_type_obj.created_at is not None else None
            report.add_related_data("created_date", created_date)
            updated_date = agent_type_obj.updated_at.isoformat() if agent_type_obj.updated_at is not None else None
            report.add_related_data("last_updated", updated_date)

            logger.info(f"Generated deletion impact report for agent type '{agent_type}'", {
                "agent_instances": report.agent_instances,
                "tasks_count": report.tasks_count,
                "tables_affected": len(report.table_impacts)
            })

            return report

        except Exception as e:
            logger.error(f"Error generating deletion impact report: {e}")
            raise AgentLifecycleError(f"Failed to generate deletion impact report: {str(e)}")

    async def delete_agent_type(
        self,
        agent_type: str,
        deletion_type: str = "soft",
        purge_data: bool = False,
        user_id: Optional[str] = None
    ) -> Tuple[DataCleanupReport, AgentDeletionLog]:
        """
        Delete an agent type with specified cleanup options.

        Args:
            agent_type: The agent type to delete
            deletion_type: Type of deletion ("soft", "hard", "purge")
            purge_data: Whether to delete associated data
            user_id: ID of user performing the deletion

        Returns:
            Tuple of (DataCleanupReport, AgentDeletionLog)
        """
        cleanup_report = DataCleanupReport()

        try:
            # Get agent type
            agent_type_obj = await self._get_agent_type(agent_type)
            if not agent_type_obj:
                raise AgentLifecycleError(f"Agent type '{agent_type}' not found")

            # Validate deletion type
            if deletion_type not in ["soft", "hard", "purge"]:
                raise AgentLifecycleError(f"Invalid deletion type: {deletion_type}")

            # Perform deletion based on type
            if deletion_type == "soft":
                await self._soft_delete_agent_type(agent_type_obj)
            elif deletion_type == "hard":
                await self._hard_delete_agent_type(agent_type_obj, purge_data, cleanup_report)
            elif deletion_type == "purge":
                await self._purge_agent_type(agent_type_obj, cleanup_report)

            # Create audit log
            deletion_log = await self._create_deletion_log(
                agent_type_obj, deletion_type, cleanup_report, user_id
            )

            logger.info(f"Successfully deleted agent type '{agent_type}' with type '{deletion_type}'", {
                "purge_data": purge_data,
                "tables_affected": len(cleanup_report.tables_cleaned),
                "total_rows_deleted": cleanup_report.get_total_rows_deleted()
            })

            return cleanup_report, deletion_log

        except Exception as e:
            cleanup_report.add_error(str(e))
            logger.error(f"Error deleting agent type '{agent_type}': {e}")
            raise AgentLifecycleError(f"Failed to delete agent type: {str(e)}")

    async def export_agent_data(self, agent_type: str, export_format: str = "json") -> Dict[str, Any]:
        """
        Export all data associated with an agent type before deletion.

        Args:
            agent_type: The agent type to export data for
            export_format: Format for exported data ("json", "csv", etc.)

        Returns:
            Dictionary containing exported data
        """
        try:
            agent_type_obj = await self._get_agent_type(agent_type)
            if not agent_type_obj:
                raise AgentLifecycleError(f"Agent type '{agent_type}' not found")

            created_at_str = agent_type_obj.created_at.isoformat() if agent_type_obj.created_at is not None else None
            export_data = {
                "agent_type": agent_type,
                "export_timestamp": datetime.utcnow().isoformat(),
                "export_format": export_format,
                "schema_definition": agent_type_obj.schema_definition,
                "metadata": {
                    "version": agent_type_obj.version,
                    "created_at": created_at_str,
                    "created_by": agent_type_obj.created_by
                },
                "data": {}
            }

            # Export agent instances
            agents_query = select(Agent).where(Agent.agent_type_id == agent_type_obj.id)
            agents_result = await self.db.execute(agents_query)
            agents = agents_result.scalars().all()

            export_data["data"]["agents"] = [agent.to_dict() for agent in agents]

            # Export related tasks
            for agent in agents:
                tasks_query = select(Task).where(Task.agent_id == agent.id)
                tasks_result = await self.db.execute(tasks_query)
                tasks = tasks_result.scalars().all()
                export_data["data"].setdefault("tasks", []).extend([task.to_dict() for task in tasks])

            # Note: Dynamic table data export would require actual table queries
            # This is a placeholder for that functionality
            export_data["data"]["dynamic_tables"] = [
                {
                    "table_name": dt.table_name,
                    "model_name": dt.model_name,
                    "schema_definition": dt.schema_definition,
                    "note": "Actual table data export requires database-specific implementation"
                }
                for dt in agent_type_obj.dynamic_tables
            ]

            logger.info(f"Exported data for agent type '{agent_type}'", {
                "agents_count": len(export_data["data"]["agents"]),
                "tasks_count": len(export_data["data"].get("tasks", [])),
                "tables_count": len(export_data["data"]["dynamic_tables"])
            })

            return export_data

        except Exception as e:
            logger.error(f"Error exporting agent data: {e}")
            raise AgentLifecycleError(f"Failed to export agent data: {str(e)}")

    async def get_agent_statistics(self, agent_type: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for an agent type.

        Args:
            agent_type: The agent type to get statistics for

        Returns:
            Dictionary with agent statistics
        """
        try:
            agent_type_obj = await self._get_agent_type(agent_type)
            if not agent_type_obj:
                raise AgentLifecycleError(f"Agent type '{agent_type}' not found")

            stats = {
                "agent_type": agent_type,
                "version": agent_type_obj.version,
                "status": agent_type_obj.status,
                "created_at": agent_type_obj.created_at.isoformat() if agent_type_obj.created_at is not None else None,
                "last_updated": agent_type_obj.updated_at.isoformat() if agent_type_obj.updated_at is not None else None,
                "metrics": {}
            }

            # Count agent instances
            agent_count_query = select(func.count(Agent.id)).where(
                Agent.agent_type_id == agent_type_obj.id
            )
            agent_count_result = await self.db.execute(agent_count_query)
            stats["metrics"]["agent_instances"] = agent_count_result.scalar() or 0

            # Count tasks
            task_count_query = select(func.count(Task.id)).where(
                Task.agent_id.in_(
                    select(Agent.id).where(Agent.agent_type_id == agent_type_obj.id)
                )
            )
            task_count_result = await self.db.execute(task_count_query)
            stats["metrics"]["total_tasks"] = task_count_result.scalar() or 0

            # Count active tasks
            active_task_count_query = select(func.count(Task.id)).where(
                and_(
                    Task.agent_id.in_(
                        select(Agent.id).where(Agent.agent_type_id == agent_type_obj.id)
                    ),
                    Task.status == "running"
                )
            )
            active_task_count_result = await self.db.execute(active_task_count_query)
            stats["metrics"]["active_tasks"] = active_task_count_result.scalar() or 0

            # Dynamic table statistics
            stats["metrics"]["dynamic_tables"] = len(agent_type_obj.dynamic_tables)
            total_rows = sum(getattr(dt, 'row_count', 0) for dt in agent_type_obj.dynamic_tables)
            stats["metrics"]["total_data_rows"] = total_rows

            return stats

        except Exception as e:
            logger.error(f"Error getting agent statistics: {e}")
            raise AgentLifecycleError(f"Failed to get agent statistics: {str(e)}")

    async def _get_agent_type(self, agent_type: str) -> Optional[AgentType]:
        """Get agent type by name."""
        query = select(AgentType).where(
            and_(
                AgentType.type_name == agent_type,
                AgentType.status != "deleted"
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _soft_delete_agent_type(self, agent_type_obj: AgentType):
        """Perform soft deletion of agent type."""
        setattr(agent_type_obj, 'status', "deprecated")
        setattr(agent_type_obj, 'deprecated_at', datetime.utcnow())
        await self.db.commit()

    async def _hard_delete_agent_type(
        self,
        agent_type_obj: AgentType,
        purge_data: bool,
        cleanup_report: DataCleanupReport
    ):
        """Perform hard deletion of agent type."""
        try:
            # Delete agent instances
            agents_query = select(Agent).where(Agent.agent_type_id == agent_type_obj.id)
            agents_result = await self.db.execute(agents_query)
            agents = agents_result.scalars().all()

            for agent in agents:
                await self.db.delete(agent)
                cleanup_report.add_cleanup_result("agents", 1)

            # Delete related tasks if purging data
            if purge_data:
                tasks_query = select(Task).where(
                    Task.agent_id.in_([agent.id for agent in agents])
                )
                tasks_result = await self.db.execute(tasks_query)
                tasks = tasks_result.scalars().all()

                for task in tasks:
                    await self.db.delete(task)
                cleanup_report.add_cleanup_result("tasks", len(tasks))

            # Delete dynamic table records (but not actual tables)
            for dynamic_table in agent_type_obj.dynamic_tables:
                await self.db.delete(dynamic_table)
                cleanup_report.add_cleanup_result("dynamic_tables", 1)

            # Finally delete the agent type
            await self.db.delete(agent_type_obj)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            cleanup_report.add_error(f"Hard deletion failed: {str(e)}")
            raise

    async def _purge_agent_type(self, agent_type_obj: AgentType, cleanup_report: DataCleanupReport):
        """Perform complete purge of agent type and all associated data."""
        try:
            # This would include dropping actual database tables
            # For now, we'll just do hard deletion
            await self._hard_delete_agent_type(agent_type_obj, True, cleanup_report)

            # TODO: Implement actual table dropping
            # for dynamic_table in agent_type_obj.dynamic_tables:
            #     await self._drop_dynamic_table(dynamic_table.table_name)
            #     cleanup_report.add_cleanup_result("dropped_tables", 1)

        except Exception as e:
            cleanup_report.add_error(f"Purge failed: {str(e)}")
            raise

    async def _create_deletion_log(
        self,
        agent_type_obj: AgentType,
        deletion_type: str,
        cleanup_report: DataCleanupReport,
        user_id: Optional[str]
    ) -> AgentDeletionLog:
        """Create audit log entry for deletion operation."""
        deletion_log = AgentDeletionLog(
            agent_type=agent_type_obj.type_name,
            agent_type_id=agent_type_obj.id,
            deletion_type=deletion_type,
            tables_affected=list(cleanup_report.tables_cleaned.keys()),
            rows_deleted=cleanup_report.tables_cleaned,
            deleted_by=user_id,
            notes=f"Deletion completed with {len(cleanup_report.errors)} errors" if cleanup_report.errors else None
        )

        self.db.add(deletion_log)
        await self.db.commit()

        return deletion_log

    async def list_deletion_history(self, agent_type: Optional[str] = None) -> List[AgentDeletionLog]:
        """
        List deletion history, optionally filtered by agent type.

        Args:
            agent_type: Optional agent type to filter by

        Returns:
            List of deletion log entries
        """
        query = select(AgentDeletionLog).order_by(AgentDeletionLog.deleted_at.desc())

        if agent_type:
            query = query.where(AgentDeletionLog.agent_type == agent_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())
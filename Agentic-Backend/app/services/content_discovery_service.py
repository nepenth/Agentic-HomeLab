"""
Content Discovery Service for automated content acquisition and processing.

This service orchestrates content discovery from various sources, manages
discovery workflows, and integrates with the real-time indexing system.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentSource, ContentBatch, ContentBatchItem
from app.services.content_framework import ContentData, ContentType
from app.services.realtime_indexing_service import realtime_indexing_service, IndexOperation, Priority
from app.connectors.base import ContentConnector
from app.utils.logging import get_logger

logger = get_logger("content_discovery_service")


class DiscoveryStrategy(Enum):
    """Content discovery strategies."""
    SCHEDULED = "scheduled"      # Regular interval discovery
    TRIGGERED = "triggered"      # Event-triggered discovery
    CONTINUOUS = "continuous"    # Continuous monitoring
    ON_DEMAND = "on_demand"      # Manual discovery


class DiscoveryScope(Enum):
    """Scope of content discovery."""
    ALL_SOURCES = "all_sources"
    SPECIFIC_SOURCES = "specific_sources"
    NEW_SOURCES = "new_sources"
    FAILED_SOURCES = "failed_sources"


@dataclass
class DiscoveryConfig:
    """Configuration for content discovery."""
    strategy: DiscoveryStrategy = DiscoveryStrategy.SCHEDULED
    scope: DiscoveryScope = DiscoveryScope.ALL_SOURCES
    source_ids: Optional[List[str]] = None
    content_types: Optional[List[str]] = None
    max_items_per_source: int = 100
    discovery_timeout_seconds: int = 300
    parallel_sources: int = 3
    retry_failed_sources: bool = True
    index_immediately: bool = True


@dataclass
class DiscoveryResult:
    """Result of a content discovery operation."""
    discovery_id: str
    total_sources: int
    successful_sources: int
    failed_sources: int
    total_items_discovered: int
    total_items_processed: int
    processing_time_seconds: float
    errors: List[str] = field(default_factory=list)
    source_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ContentWorkflow:
    """Content processing workflow definition."""
    workflow_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    triggers: List[str]  # Events that trigger this workflow
    schedule: Optional[str] = None  # Cron-like schedule
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class ContentDiscoveryService:
    """Service for orchestrating content discovery and processing workflows."""

    def __init__(self):
        self.active_workflows: Dict[str, ContentWorkflow] = {}
        self.discovery_history: List[DiscoveryResult] = []
        self.connector_registry: Dict[str, ContentConnector] = {}

    def register_connector(self, source_type: str, connector: ContentConnector):
        """Register a content connector."""
        self.connector_registry[source_type] = connector
        logger.info(f"Registered connector for source type: {source_type}")

    async def discover_content(
        self,
        config: DiscoveryConfig,
        user_id: Optional[str] = None
    ) -> DiscoveryResult:
        """
        Discover content from configured sources.

        Args:
            config: Discovery configuration
            user_id: User initiating the discovery

        Returns:
            DiscoveryResult with operation summary
        """
        discovery_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Starting content discovery {discovery_id} with strategy {config.strategy.value}")

        try:
            # Get sources to discover from
            sources = await self._get_discovery_sources(config)

            if not sources:
                return DiscoveryResult(
                    discovery_id=discovery_id,
                    total_sources=0,
                    successful_sources=0,
                    failed_sources=0,
                    total_items_discovered=0,
                    total_items_processed=0,
                    processing_time_seconds=0.0,
                    errors=["No sources available for discovery"]
                )

            # Create discovery batch
            batch_id = await self._create_discovery_batch(discovery_id, sources, user_id)

            # Execute discovery
            source_results = await self._execute_discovery(
                sources, config, batch_id
            )

            # Process results
            total_items = sum(result.get('items_discovered', 0) for result in source_results)
            successful_sources = sum(1 for result in source_results if result.get('success', False))
            failed_sources = len(source_results) - successful_sources

            # Calculate processing time
            processing_time = time.time() - start_time

            result = DiscoveryResult(
                discovery_id=discovery_id,
                total_sources=len(sources),
                successful_sources=successful_sources,
                failed_sources=failed_sources,
                total_items_discovered=total_items,
                total_items_processed=total_items,  # For now, assume all discovered items are processed
                processing_time_seconds=processing_time,
                source_results=source_results
            )

            # Store in history
            self.discovery_history.append(result)

            # Update batch status
            await self._update_batch_status(batch_id, "completed")

            logger.info(f"Content discovery {discovery_id} completed: {total_items} items from {successful_sources} sources")
            return result

        except Exception as e:
            logger.error(f"Content discovery {discovery_id} failed: {e}")

            # Update batch status on failure
            if 'batch_id' in locals():
                await self._update_batch_status(batch_id, "failed")

            return DiscoveryResult(
                discovery_id=discovery_id,
                total_sources=0,
                successful_sources=0,
                failed_sources=0,
                total_items_discovered=0,
                total_items_processed=0,
                processing_time_seconds=time.time() - start_time,
                errors=[str(e)]
            )

    async def _get_discovery_sources(self, config: DiscoveryConfig) -> List[ContentSource]:
        """Get sources for discovery based on configuration."""
        db = next(get_db())

        try:
            query = db.query(ContentSource).filter(ContentSource.is_active == True)

            if config.scope == DiscoveryScope.SPECIFIC_SOURCES and config.source_ids:
                query = query.filter(ContentSource.id.in_(config.source_ids))
            elif config.scope == DiscoveryScope.NEW_SOURCES:
                # Sources that haven't been discovered recently
                cutoff_time = datetime.now() - timedelta(hours=24)
                query = query.filter(
                    (ContentSource.last_discovery_at.is_(None)) |
                    (ContentSource.last_discovery_at < cutoff_time)
                )
            elif config.scope == DiscoveryScope.FAILED_SOURCES:
                # Sources with recent failures
                query = query.filter(ContentSource.last_error_at.isnot(None))

            sources = query.all()
            return sources

        finally:
            db.close()

    async def _create_discovery_batch(
        self,
        discovery_id: str,
        sources: List[ContentSource],
        user_id: Optional[str]
    ) -> str:
        """Create a discovery batch record."""
        db = next(get_db())

        try:
            batch = ContentBatch(
                batch_name=f"Discovery {discovery_id}",
                batch_type="discovery",
                status="running",
                started_at=datetime.now(),
                source_ids=[str(s.id) for s in sources],
                created_by=user_id or "system"
            )

            db.add(batch)
            db.commit()

            # Create batch items
            for i, source in enumerate(sources):
                batch_item = ContentBatchItem(
                    batch_id=batch.id,
                    item_identifier=str(source.id),
                    item_type="content_source",
                    item_order=i
                )
                db.add(batch_item)

            db.commit()
            return str(batch.id)

        finally:
            db.close()

    async def _execute_discovery(
        self,
        sources: List[ContentSource],
        config: DiscoveryConfig,
        batch_id: str
    ) -> List[Dict[str, Any]]:
        """Execute discovery across sources."""
        source_results = []

        # Process sources in parallel batches
        for i in range(0, len(sources), config.parallel_sources):
            batch_sources = sources[i:i + config.parallel_sources]

            # Create tasks for parallel processing
            tasks = []
            for source in batch_sources:
                task = self._discover_from_source(source, config, batch_id)
                tasks.append(task)

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for j, result in enumerate(batch_results):
                source = batch_sources[j]

                if isinstance(result, Exception):
                    source_result = {
                        "source_id": str(source.id),
                        "source_name": source.name,
                        "success": False,
                        "error": str(result),
                        "items_discovered": 0
                    }
                else:
                    source_result = result

                source_results.append(source_result)

                # Update batch item status
                await self._update_batch_item_status(
                    batch_id, str(source.id),
                    "completed" if source_result.get("success") else "failed"
                )

        return source_results

    async def _discover_from_source(
        self,
        source: ContentSource,
        config: DiscoveryConfig,
        batch_id: str
    ) -> Dict[str, Any]:
        """Discover content from a single source."""
        start_time = time.time()

        try:
            # Get connector for this source type
            connector = self.connector_registry.get(source.source_type)
            if not connector:
                raise ValueError(f"No connector registered for source type: {source.source_type}")

            # Prepare source configuration
            source_config = source.config or {}
            source_config.update({
                "max_items": config.max_items_per_source,
                "timeout": config.discovery_timeout_seconds
            })

            # Execute discovery
            content_items = await connector.discover(source_config)

            # Process discovered items
            processed_items = 0
            for item in content_items:
                try:
                    # Fetch content data
                    content_data = await connector.fetch(item)

                    # Create content item in database
                    content_item_id = await self._create_content_item(
                        item, content_data, source
                    )

                    # Queue for indexing if configured
                    if config.index_immediately:
                        realtime_indexing_service.queue_content_for_indexing(
                            content_item_id=content_item_id,
                            content_data=content_data,
                            operation=IndexOperation.CREATE,
                            priority=Priority.NORMAL
                        )

                    processed_items += 1

                except Exception as e:
                    logger.error(f"Failed to process item {item.id}: {e}")
                    continue

            # Update source statistics
            await self._update_source_stats(source.id, processed_items, True)

            processing_time = time.time() - start_time

            return {
                "source_id": str(source.id),
                "source_name": source.name,
                "success": True,
                "items_discovered": len(content_items),
                "items_processed": processed_items,
                "processing_time_seconds": processing_time
            }

        except Exception as e:
            # Update source statistics on failure
            await self._update_source_stats(source.id, 0, False, str(e))

            processing_time = time.time() - start_time

            return {
                "source_id": str(source.id),
                "source_name": source.name,
                "success": False,
                "error": str(e),
                "items_discovered": 0,
                "processing_time_seconds": processing_time
            }

    async def _create_content_item(
        self,
        item: Any,
        content_data: ContentData,
        source: ContentSource
    ) -> str:
        """Create a content item in the database."""
        db = next(get_db())

        try:
            # Check if item already exists
            existing_item = db.query(ContentItem).filter(
                ContentItem.source_id == item.id,
                ContentItem.source_type == source.source_type
            ).first()

            if existing_item:
                # Update existing item
                existing_item.title = getattr(item, 'title', existing_item.title)
                existing_item.description = getattr(item, 'description', existing_item.description)
                existing_item.last_processed_at = datetime.now()
                db.commit()
                return str(existing_item.id)

            # Create new content item
            content_item = ContentItem(
                source_id=item.id,
                source_type=source.source_type,
                connector_type=source.connector_type,
                content_type=content_data.content_type.value,
                title=getattr(item, 'title', None),
                description=getattr(item, 'description', None),
                url=getattr(item, 'url', None),
                author=getattr(item, 'author', None),
                published_at=getattr(item, 'published_at', None),
                metadata=getattr(content_data, 'metadata', {}),
                processing_status="discovered"
            )

            db.add(content_item)
            db.commit()

            return str(content_item.id)

        finally:
            db.close()

    async def _update_source_stats(
        self,
        source_id: str,
        items_discovered: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Update source statistics."""
        db = next(get_db())

        try:
            source = db.query(ContentSource).filter(ContentSource.id == source_id).first()
            if source:
                source.total_items_discovered += items_discovered
                source.last_discovery_at = datetime.now()

                if success:
                    source.last_success_at = datetime.now()
                    source.success_rate = (
                        (source.total_items_discovered - (source.total_items_discovered - items_discovered)) /
                        max(source.total_items_discovered, 1)
                    )
                else:
                    source.last_error_at = datetime.now()
                    source.last_error_message = error_message

                db.commit()

        finally:
            db.close()

    async def _update_batch_status(self, batch_id: str, status: str):
        """Update batch status."""
        db = next(get_db())

        try:
            batch = db.query(ContentBatch).filter(ContentBatch.id == batch_id).first()
            if batch:
                batch.status = status
                if status in ["completed", "failed"]:
                    batch.completed_at = datetime.now()
                db.commit()

        finally:
            db.close()

    async def _update_batch_item_status(self, batch_id: str, item_identifier: str, status: str):
        """Update batch item status."""
        db = next(get_db())

        try:
            batch_item = db.query(ContentBatchItem).filter(
                ContentBatchItem.batch_id == batch_id,
                ContentBatchItem.item_identifier == item_identifier
            ).first()

            if batch_item:
                batch_item.status = status
                if status in ["completed", "failed"]:
                    batch_item.completed_at = datetime.now()
                db.commit()

        finally:
            db.close()

    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        triggers: List[str],
        schedule: Optional[str] = None
    ) -> str:
        """
        Create a content processing workflow.

        Args:
            name: Workflow name
            description: Workflow description
            steps: List of workflow steps
            triggers: Events that trigger the workflow
            schedule: Optional schedule for automatic execution

        Returns:
            Workflow ID
        """
        workflow_id = str(uuid.uuid4())

        workflow = ContentWorkflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            steps=steps,
            triggers=triggers,
            schedule=schedule
        )

        self.active_workflows[workflow_id] = workflow

        logger.info(f"Created workflow {workflow_id}: {name}")
        return workflow_id

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a content processing workflow.

        Args:
            workflow_id: ID of the workflow to execute
            trigger_data: Data from the trigger event

        Returns:
            Execution results
        """
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        logger.info(f"Executing workflow {workflow_id}: {workflow.name}")

        results = []
        for step in workflow.steps:
            try:
                step_result = await self._execute_workflow_step(step, trigger_data)
                results.append(step_result)
            except Exception as e:
                logger.error(f"Workflow step failed: {e}")
                results.append({
                    "step": step.get("name", "unknown"),
                    "success": False,
                    "error": str(e)
                })

        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "steps_executed": len(results),
            "results": results,
            "execution_time": datetime.now().isoformat()
        }

    async def _execute_workflow_step(
        self,
        step: Dict[str, Any],
        trigger_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""
        step_type = step.get("type")
        step_config = step.get("config", {})

        if step_type == "discovery":
            # Execute content discovery
            config = DiscoveryConfig(**step_config)
            result = await self.discover_content(config)
            return {
                "step": step.get("name", "discovery"),
                "success": True,
                "result": {
                    "items_discovered": result.total_items_discovered,
                    "sources_processed": result.successful_sources
                }
            }

        elif step_type == "processing":
            # Execute content processing
            # This would integrate with the content processing pipeline
            return {
                "step": step.get("name", "processing"),
                "success": True,
                "result": {"message": "Processing step executed"}
            }

        elif step_type == "indexing":
            # Execute indexing
            await realtime_indexing_service.force_reindex_content()
            return {
                "step": step.get("name", "indexing"),
                "success": True,
                "result": {"message": "Indexing completed"}
            }

        else:
            raise ValueError(f"Unknown step type: {step_type}")

    def get_discovery_history(self, limit: int = 10) -> List[DiscoveryResult]:
        """Get recent discovery history."""
        return self.discovery_history[-limit:]

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return None

        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "is_active": workflow.is_active,
            "steps_count": len(workflow.steps),
            "triggers": workflow.triggers,
            "schedule": workflow.schedule,
            "created_at": workflow.created_at.isoformat()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the discovery service."""
        db = next(get_db())

        try:
            # Check database connectivity
            source_count = db.query(ContentSource).count()
            active_workflows = len([w for w in self.active_workflows.values() if w.is_active])

            return {
                "service": "content_discovery",
                "status": "healthy",
                "registered_connectors": len(self.connector_registry),
                "active_sources": source_count,
                "active_workflows": active_workflows,
                "recent_discoveries": len(self.discovery_history),
                "timestamp": datetime.now().isoformat()
            }

        finally:
            db.close()


# Global instance
content_discovery_service = ContentDiscoveryService()
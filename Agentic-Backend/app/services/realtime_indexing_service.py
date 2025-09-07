"""
Real-time Indexing Service for incremental content updates.

This service provides real-time indexing capabilities for content updates,
automatic reindexing, and background processing to maintain search index freshness.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import queue
from queue import Queue, PriorityQueue
import heapq

from app.db.database import get_db
from app.db.models.content import ContentItem, ContentEmbedding, ContentAnalytics
from app.services.vector_search_service import vector_search_service
from app.services.content_framework import ContentData
from app.utils.logging import get_logger

logger = get_logger("realtime_indexing_service")


class IndexOperation(Enum):
    """Types of indexing operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BATCH_UPDATE = "batch_update"


class Priority(Enum):
    """Indexing priority levels."""
    CRITICAL = 1  # Immediate indexing required
    HIGH = 2      # High priority updates
    NORMAL = 3    # Normal priority updates
    LOW = 4       # Low priority updates (background)


@dataclass(order=True)
class IndexTask:
    """Indexing task with priority."""
    priority: int
    operation: IndexOperation
    content_item_id: str
    content_data: Optional[ContentData] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        # Make priority the first comparison key
        self._priority = (self.priority, self.timestamp, self.content_item_id)


@dataclass
class IndexBatch:
    """Batch of indexing operations."""
    batch_id: str
    tasks: List[IndexTask]
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    status: str = "pending"  # pending, processing, completed, failed


@dataclass
class IndexingStats:
    """Real-time indexing statistics."""
    total_tasks_processed: int = 0
    total_batches_processed: int = 0
    average_processing_time_ms: float = 0.0
    queue_size: int = 0
    failed_tasks: int = 0
    last_processed_at: Optional[datetime] = None
    active_workers: int = 0


class RealTimeIndexingService:
    """Real-time indexing service with priority queuing and background processing."""

    def __init__(
        self,
        max_workers: int = 4,
        batch_size: int = 10,
        max_queue_size: int = 1000
    ):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size

        # Priority queue for indexing tasks
        self.task_queue: PriorityQueue[IndexTask] = PriorityQueue()

        # Thread pool for background processing
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="indexer")

        # Statistics
        self.stats = IndexingStats()

        # Control flags
        self.running = False
        self.shutdown_event = threading.Event()

        # Content change tracking
        self.content_watchlist: Set[str] = set()
        self.batch_operations: Dict[str, IndexBatch] = {}

        # Start background workers
        self._start_workers()

    def _start_workers(self):
        """Start background worker threads."""
        self.running = True
        for i in range(self.max_workers):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"IndexerWorker-{i}",
                daemon=True
            )
            thread.start()

        logger.info(f"Started {self.max_workers} indexing worker threads")

    def _worker_loop(self):
        """Main worker loop for processing indexing tasks."""
        while not self.shutdown_event.is_set():
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=1.0)

                # Process the task
                self._process_task(task)

                # Mark task as done
                self.task_queue.task_done()

            except queue.Empty:
                # Queue is empty, continue waiting
                continue
            except Exception as e:
                # Actual processing error
                logger.error(f"Worker error: {e}")
                continue

    def _process_task(self, task: IndexTask):
        """Process a single indexing task."""
        start_time = time.time()

        try:
            if task.operation == IndexOperation.CREATE:
                self._index_content_create(task)
            elif task.operation == IndexOperation.UPDATE:
                self._index_content_update(task)
            elif task.operation == IndexOperation.DELETE:
                self._index_content_delete(task)
            elif task.operation == IndexOperation.BATCH_UPDATE:
                self._index_content_batch(task)

            processing_time = (time.time() - start_time) * 1000
            self.stats.total_tasks_processed += 1
            self.stats.last_processed_at = datetime.now()

            # Update average processing time
            if self.stats.total_tasks_processed == 1:
                self.stats.average_processing_time_ms = processing_time
            else:
                self.stats.average_processing_time_ms = (
                    (self.stats.average_processing_time_ms * (self.stats.total_tasks_processed - 1) +
                     processing_time) / self.stats.total_tasks_processed
                )

            logger.info(f"Processed {task.operation.value} task for {task.content_item_id} in {processing_time:.2f}ms")

        except Exception as e:
            logger.error(f"Failed to process task {task.content_item_id}: {e}")
            self.stats.failed_tasks += 1

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                # Re-queue with lower priority
                task.priority = min(task.priority + 1, Priority.LOW.value)
                self.task_queue.put(task)
                logger.info(f"Re-queued task {task.content_item_id} (attempt {task.retry_count})")

    def _index_content_create(self, task: IndexTask):
        """Index new content."""
        if not task.content_data:
            return

        # Extract text content
        content_text = self._extract_text_content(task.content_data)

        if content_text:
            asyncio.run(vector_search_service.index_content(
                content_item_id=task.content_item_id,
                content_text=content_text
            ))

    def _index_content_update(self, task: IndexTask):
        """Update existing content index."""
        # First remove old index
        asyncio.run(vector_search_service.remove_from_index(task.content_item_id))

        # Then re-index
        if task.content_data:
            content_text = self._extract_text_content(task.content_data)
            if content_text:
                asyncio.run(vector_search_service.index_content(
                    content_item_id=task.content_item_id,
                    content_text=content_text
                ))

    def _index_content_delete(self, task: IndexTask):
        """Remove content from index."""
        asyncio.run(vector_search_service.remove_from_index(task.content_item_id))

    def _index_content_batch(self, task: IndexTask):
        """Process batch indexing operation."""
        # This would handle batch operations
        pass

    def _extract_text_content(self, content_data: ContentData) -> str:
        """Extract text content from ContentData."""
        # This is a simplified extraction - in practice, this would handle
        # different content types and extract text appropriately
        if hasattr(content_data, 'content'):
            return content_data.content
        elif hasattr(content_data, 'text'):
            return content_data.text
        elif hasattr(content_data, 'description'):
            return content_data.description
        else:
            return ""

    def queue_content_for_indexing(
        self,
        content_item_id: str,
        content_data: Optional[ContentData] = None,
        operation: IndexOperation = IndexOperation.CREATE,
        priority: Priority = Priority.NORMAL
    ):
        """
        Queue content for indexing.

        Args:
            content_item_id: ID of the content item
            content_data: Content data (required for CREATE/UPDATE)
            operation: Type of indexing operation
            priority: Priority level for the operation
        """
        if self.task_queue.qsize() >= self.max_queue_size:
            logger.warning(f"Indexing queue full ({self.max_queue_size}), dropping task for {content_item_id}")
            return

        task = IndexTask(
            priority=priority.value,
            operation=operation,
            content_item_id=content_item_id,
            content_data=content_data
        )

        self.task_queue.put(task)
        self.stats.queue_size = self.task_queue.qsize()

        logger.info(f"Queued {operation.value} task for {content_item_id} with {priority.name} priority")

    def queue_batch_operation(
        self,
        batch_id: str,
        content_items: List[Tuple[str, ContentData, IndexOperation]],
        priority: Priority = Priority.NORMAL
    ):
        """
        Queue a batch of indexing operations.

        Args:
            batch_id: Unique identifier for the batch
            content_items: List of (content_id, content_data, operation) tuples
            priority: Priority level for the batch
        """
        batch = IndexBatch(
            batch_id=batch_id,
            tasks=[]
        )

        for content_id, content_data, operation in content_items:
            task = IndexTask(
                priority=priority.value,
                operation=operation,
                content_item_id=content_id,
                content_data=content_data
            )
            batch.tasks.append(task)

        self.batch_operations[batch_id] = batch

        # Queue individual tasks
        for task in batch.tasks:
            self.task_queue.put(task)

        logger.info(f"Queued batch {batch_id} with {len(batch.tasks)} tasks")

    async def index_content_change(
        self,
        content_item_id: str,
        change_type: str,
        content_data: Optional[ContentData] = None
    ):
        """
        Handle content change events for automatic indexing.

        Args:
            content_item_id: ID of changed content
            change_type: Type of change (created, updated, deleted)
            content_data: New content data (for create/update)
        """
        if change_type == "created":
            self.queue_content_for_indexing(
                content_item_id=content_item_id,
                content_data=content_data,
                operation=IndexOperation.CREATE,
                priority=Priority.HIGH
            )
        elif change_type == "updated":
            self.queue_content_for_indexing(
                content_item_id=content_item_id,
                content_data=content_data,
                operation=IndexOperation.UPDATE,
                priority=Priority.NORMAL
            )
        elif change_type == "deleted":
            self.queue_content_for_indexing(
                content_item_id=content_item_id,
                operation=IndexOperation.DELETE,
                priority=Priority.CRITICAL
            )

    async def watch_content_changes(self):
        """
        Monitor database for content changes and automatically queue indexing.

        This method should be run as a background task to continuously monitor
        for content changes and trigger automatic indexing.
        """
        logger.info("Starting content change monitoring")

        while not self.shutdown_event.is_set():
            try:
                # Check for new or updated content
                await self._check_for_content_changes()

                # Small delay to avoid excessive database queries
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in content change monitoring: {e}")
                await asyncio.sleep(10)  # Longer delay on error

    async def _check_for_content_changes(self):
        """Check database for content changes that need indexing."""
        db = next(get_db())

        try:
            # Find content items that have been created/updated recently but not indexed
            recent_content = db.query(ContentItem).filter(
                ContentItem.discovered_at >= datetime.now() - timedelta(minutes=10),
                ContentItem.processing_status.in_(['discovered', 'processed'])
            ).all()

            for item in recent_content:
                if item.id not in self.content_watchlist:
                    # Check if already indexed
                    existing_embedding = db.query(ContentEmbedding).filter(
                        ContentEmbedding.content_item_id == item.id
                    ).first()

                    if not existing_embedding:
                        # Queue for indexing
                        content_data = ContentData(
                            content_type=item.content_type,
                            content=item.description or "",
                            metadata=item.metadata or {}
                        )

                        await self.index_content_change(
                            content_item_id=item.id,
                            change_type="created",
                            content_data=content_data
                        )

                        self.content_watchlist.add(item.id)

            # Clean up old watchlist entries (keep last 1000)
            if len(self.content_watchlist) > 1000:
                # Remove oldest entries
                sorted_watchlist = sorted(self.content_watchlist)
                self.content_watchlist = set(sorted_watchlist[-500:])

        finally:
            db.close()

    async def force_reindex_content(
        self,
        content_item_ids: Optional[List[str]] = None,
        priority: Priority = Priority.LOW
    ):
        """
        Force reindexing of content items.

        Args:
            content_item_ids: Specific content IDs to reindex (None for all)
            priority: Priority level for reindexing
        """
        db = next(get_db())

        try:
            query = db.query(ContentItem)
            if content_item_ids:
                query = query.filter(ContentItem.id.in_(content_item_ids))

            content_items = query.all()

            for item in content_items:
                content_data = ContentData(
                    content_type=item.content_type,
                    content=item.description or "",
                    metadata=item.metadata or {}
                )

                self.queue_content_for_indexing(
                    content_item_id=item.id,
                    content_data=content_data,
                    operation=IndexOperation.UPDATE,
                    priority=priority
                )

            logger.info(f"Queued {len(content_items)} items for reindexing")

        finally:
            db.close()

    def get_indexing_stats(self) -> Dict[str, Any]:
        """Get current indexing statistics."""
        return {
            "total_tasks_processed": self.stats.total_tasks_processed,
            "total_batches_processed": self.stats.total_batches_processed,
            "average_processing_time_ms": self.stats.average_processing_time_ms,
            "queue_size": self.task_queue.qsize(),
            "failed_tasks": self.stats.failed_tasks,
            "last_processed_at": self.stats.last_processed_at.isoformat() if self.stats.last_processed_at else None,
            "active_workers": self.max_workers,
            "is_running": self.running
        }

    def shutdown(self):
        """Shutdown the indexing service."""
        logger.info("Shutting down real-time indexing service")

        self.running = False
        self.shutdown_event.set()

        # Wait for queue to empty
        self.task_queue.join()

        # Shutdown thread pool
        self.executor.shutdown(wait=True)

        logger.info("Real-time indexing service shutdown complete")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the indexing service."""
        health_status = {
            "service": "realtime_indexing",
            "status": "healthy" if self.running else "stopped",
            "queue_size": self.task_queue.qsize(),
            "active_workers": self.max_workers,
            "total_processed": self.stats.total_tasks_processed,
            "failed_tasks": self.stats.failed_tasks,
            "last_activity": self.stats.last_processed_at.isoformat() if self.stats.last_processed_at else None,
            "timestamp": datetime.now().isoformat()
        }

        # Check if queue is growing too large
        if self.task_queue.qsize() > self.max_queue_size * 0.8:
            health_status["status"] = "warning"
            health_status["message"] = "Queue size is high"

        # Check if there are too many failed tasks
        if self.stats.failed_tasks > self.stats.total_tasks_processed * 0.1:
            health_status["status"] = "warning"
            health_status["message"] = "High failure rate detected"

        return health_status


# Global instance
realtime_indexing_service = RealTimeIndexingService()


async def start_content_monitoring():
    """Start the content change monitoring task."""
    asyncio.create_task(realtime_indexing_service.watch_content_changes())


def get_realtime_indexing_service() -> RealTimeIndexingService:
    """Get the global real-time indexing service instance."""
    return realtime_indexing_service
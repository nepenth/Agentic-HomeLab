"""
Integration Layer Service

This service provides a comprehensive integration layer including:
- API Gateway (unified access to all workflow capabilities)
- Webhook Support (real-time notifications and external integrations)
- Queue Management (asynchronous processing with priority queues)
- Load Balancing (intelligent distribution of processing workloads)

Author: Kilo Code
"""

import asyncio
import json
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

import aio_pika
import redis.asyncio as redis
from aiohttp import web, ClientSession, FormData
from aiohttp.web import Request, Response
import aiohttp
from urllib.parse import urlparse, parse_qs

from app.services.workflow_automation_service import workflow_automation_service
from app.services.pubsub_service import RedisPubSubService as PubSubService
from app.services.system_metrics_service import SystemMetricsService
from app.utils.logging import get_logger
from app.db.database import get_db
from app.db.models import (
    WebhookSubscription,
    WebhookDeliveryLog,
    QueueItem,
    BackendService,
    BackendServiceMetrics,
    LoadBalancerStats,
    APIGatewayMetrics
)

logger = get_logger(__name__)


class QueuePriority(Enum):
    """Queue priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class WebhookEvent(Enum):
    """Webhook event types"""
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_CANCELLED = "workflow.cancelled"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"


@dataclass
class QueueItem:
    """Represents an item in the processing queue"""
    id: str
    type: str
    priority: QueuePriority
    data: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    processing_deadline: Optional[datetime] = None
    callback_url: Optional[str] = None


@dataclass
class WebhookSubscription:
    """Represents a webhook subscription"""
    id: str
    url: str
    events: List[WebhookEvent]
    secret: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    failure_count: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIEndpoint:
    """Represents an API endpoint in the gateway"""
    path: str
    methods: List[str]
    handler: Callable
    requires_auth: bool = True
    rate_limit: Optional[int] = None  # requests per minute
    timeout: int = 30
    description: str = ""


@dataclass
class LoadBalancerStats:
    """Load balancer statistics"""
    total_requests: int = 0
    active_connections: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    backend_health: Dict[str, bool] = field(default_factory=dict)


class IntegrationLayerService:
    """
    Comprehensive integration layer for workflow orchestration and external connectivity.
    """

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.pubsub_service = PubSubService()
        self.metrics_service = SystemMetricsService()
        self.workflow_service = workflow_automation_service

        # Core components
        self.api_gateway = None
        self.webhook_manager = None
        self.queue_manager = None
        self.load_balancer = None

        # Configuration
        self.api_endpoints: Dict[str, APIEndpoint] = {}
        self.webhook_subscriptions: Dict[str, WebhookSubscription] = {}
        self.processing_queues: Dict[str, List[QueueItem]] = {}
        self.backend_services: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize the integration layer service"""
        try:
            # Initialize Redis for distributed state management
            self.redis = redis.Redis(
                host="localhost",
                port=6379,
                db=2,  # Use separate DB for integration layer
                decode_responses=True
            )

            # Initialize core components
            self.api_gateway = APIGateway(self)
            self.webhook_manager = WebhookManager(self)
            self.queue_manager = QueueManager(self)
            self.load_balancer = LoadBalancer(self)

            # Register default API endpoints
            await self._register_default_endpoints()

            # Load existing configuration
            await self._load_webhook_subscriptions()
            await self._load_backend_services()

            # Start background tasks
            asyncio.create_task(self._process_queues_background())
            asyncio.create_task(self._health_check_backends())

            logger.info("Integration Layer Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Integration Layer Service: {e}")
            raise

    async def shutdown(self):
        """Shutdown the integration layer service"""
        try:
            # Stop background tasks
            # (Tasks will be cancelled when the event loop stops)

            # Close Redis connection
            if self.redis:
                await self.redis.close()

            logger.info("Integration Layer Service shutdown complete")

        except Exception as e:
            logger.error(f"Error during Integration Layer Service shutdown: {e}")


# ============================================================================
# API Gateway Component
# ============================================================================

class APIGateway:
    """Unified API gateway for all workflow capabilities"""

    def __init__(self, integration_service):
        self.integration_service = integration_service
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.request_cache: Dict[str, Any] = {}

    async def handle_request(self, request: Request) -> Response:
        """Handle incoming API requests"""
        try:
            path = request.path
            method = request.method

            # Find matching endpoint
            endpoint = self.integration_service.api_endpoints.get(path)
            if not endpoint:
                return web.json_response(
                    {"error": "Endpoint not found", "path": path},
                    status=404
                )

            # Check method support
            if method not in endpoint.methods:
                return web.json_response(
                    {"error": "Method not allowed", "method": method},
                    status=405
                )

            # Check authentication if required
            if endpoint.requires_auth:
                auth_result = await self._check_authentication(request)
                if not auth_result['valid']:
                    return web.json_response(
                        {"error": "Authentication failed", "details": auth_result.get('error')},
                        status=401
                    )

            # Check rate limiting
            if endpoint.rate_limit:
                rate_check = await self._check_rate_limit(request, endpoint)
                if not rate_check['allowed']:
                    return web.json_response(
                        {"error": "Rate limit exceeded", "retry_after": rate_check['retry_after']},
                        status=429
                    )

            # Route to appropriate handler
            try:
                # Set timeout for the request
                timeout = aiohttp.ClientTimeout(total=endpoint.timeout)

                # Call the handler
                result = await asyncio.wait_for(
                    endpoint.handler(request),
                    timeout=endpoint.timeout
                )

                # Log successful request
                logger.info(f"API request completed: {method} {path}")

                return result

            except asyncio.TimeoutError:
                logger.error(f"Request timeout: {method} {path}")
                return web.json_response(
                    {"error": "Request timeout"},
                    status=504
                )

            except Exception as e:
                logger.error(f"Request handler error: {method} {path} - {e}")
                return web.json_response(
                    {"error": "Internal server error"},
                    status=500
                )

        except Exception as e:
            logger.error(f"API Gateway error: {e}")
            return web.json_response(
                {"error": "Gateway error"},
                status=500
            )

    async def _check_authentication(self, request: Request) -> Dict[str, Any]:
        """Check request authentication"""
        try:
            # Check for API key in header
            api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')

            if not api_key:
                return {"valid": False, "error": "No API key provided"}

            # Validate API key (placeholder - integrate with your auth system)
            if api_key.startswith('Bearer '):
                api_key = api_key[7:]

            # Here you would validate against your user/auth system
            # For now, accept any non-empty key
            if not api_key or len(api_key) < 10:
                return {"valid": False, "error": "Invalid API key format"}

            return {"valid": True, "user_id": "placeholder_user"}

        except Exception as e:
            logger.error(f"Authentication check error: {e}")
            return {"valid": False, "error": "Authentication system error"}

    async def _check_rate_limit(self, request: Request, endpoint: APIEndpoint) -> Dict[str, Any]:
        """Check rate limiting for the request"""
        try:
            # Get client identifier (IP or API key)
            client_id = request.headers.get('X-API-Key') or request.remote

            # Create rate limit key
            rate_key = f"rate_limit:{client_id}:{endpoint.path}"

            # Get current request count
            current_count = await self.integration_service.redis.get(rate_key) or 0
            current_count = int(current_count)

            # Check if limit exceeded
            if current_count >= endpoint.rate_limit:
                # Calculate retry after time (1 minute window)
                retry_after = 60
                return {"allowed": False, "retry_after": retry_after}

            # Increment counter
            await self.integration_service.redis.incr(rate_key)

            # Set expiry if this is the first request
            if current_count == 0:
                await self.integration_service.redis.expire(rate_key, 60)  # 1 minute window

            return {"allowed": True}

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow request on error to avoid blocking legitimate traffic
            return {"allowed": True}

    async def register_endpoint(self, endpoint: APIEndpoint):
        """Register a new API endpoint"""
        self.integration_service.api_endpoints[endpoint.path] = endpoint
        logger.info(f"Registered API endpoint: {endpoint.methods} {endpoint.path}")

    async def unregister_endpoint(self, path: str):
        """Unregister an API endpoint"""
        if path in self.integration_service.api_endpoints:
            del self.integration_service.api_endpoints[path]
            logger.info(f"Unregistered API endpoint: {path}")


# ============================================================================
# Webhook Manager Component
# ============================================================================

class WebhookManager:
    """Manages webhook subscriptions and notifications"""

    def __init__(self, integration_service):
        self.integration_service = integration_service
        self.http_session: Optional[ClientSession] = None

    async def initialize(self):
        """Initialize webhook manager"""
        self.http_session = ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    async def shutdown(self):
        """Shutdown webhook manager"""
        if self.http_session:
            await self.http_session.close()

    async def subscribe_webhook(self, subscription_data: Dict[str, Any]) -> str:
        """Create a new webhook subscription"""
        try:
            # Validate subscription data
            required_fields = ['url', 'events']
            for field in required_fields:
                if field not in subscription_data:
                    raise ValueError(f"Missing required field: {field}")

            # Generate secret for webhook verification
            secret = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

            # Create subscription
            subscription = WebhookSubscription(
                id=str(uuid.uuid4()),
                url=subscription_data['url'],
                events=[WebhookEvent(event) for event in subscription_data['events']],
                secret=secret,
                headers=subscription_data.get('headers', {}),
                filters=subscription_data.get('filters', {})
            )

            # Store subscription
            self.integration_service.webhook_subscriptions[subscription.id] = subscription

            # Persist to database
            await self._persist_webhook_subscription(subscription)

            logger.info(f"Created webhook subscription: {subscription.id} for {subscription.url}")
            return subscription.id

        except Exception as e:
            logger.error(f"Failed to create webhook subscription: {e}")
            raise

    async def unsubscribe_webhook(self, subscription_id: str) -> bool:
        """Remove a webhook subscription"""
        try:
            if subscription_id not in self.integration_service.webhook_subscriptions:
                return False

            # Remove from memory
            del self.integration_service.webhook_subscriptions[subscription_id]

            # Remove from database
            await self._delete_webhook_subscription(subscription_id)

            logger.info(f"Removed webhook subscription: {subscription_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove webhook subscription: {e}")
            raise

    async def trigger_webhook(self, event: WebhookEvent, data: Dict[str, Any]):
        """Trigger webhooks for a specific event"""
        try:
            matching_subscriptions = [
                sub for sub in self.integration_service.webhook_subscriptions.values()
                if event in sub.events and sub.is_active
            ]

            if not matching_subscriptions:
                return

            # Prepare webhook payload
            payload = {
                "event": event.value,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }

            # Trigger webhooks asynchronously
            tasks = [
                self._send_webhook(subscription, payload)
                for subscription in matching_subscriptions
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Failed to trigger webhooks for event {event.value}: {e}")

    async def _send_webhook(self, subscription: WebhookSubscription, payload: Dict[str, Any]):
        """Send webhook to a specific subscription"""
        try:
            # Check filters
            if not self._matches_filters(payload, subscription.filters):
                return

            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Agentic-Backend-Webhook/1.0',
                'X-Webhook-ID': subscription.id,
                'X-Webhook-Event': payload['event'],
                **subscription.headers
            }

            # Add signature for verification
            signature = self._generate_signature(json.dumps(payload, sort_keys=True), subscription.secret)
            headers['X-Webhook-Signature'] = signature

            # Send webhook
            async with self.http_session.post(
                subscription.url,
                json=payload,
                headers=headers
            ) as response:

                # Update subscription stats
                subscription.last_triggered = datetime.utcnow()

                if response.status >= 200 and response.status < 300:
                    subscription.failure_count = 0
                    logger.info(f"Webhook sent successfully: {subscription.id} -> {subscription.url}")
                else:
                    subscription.failure_count += 1
                    logger.warning(f"Webhook failed: {subscription.id} -> {subscription.url} (status: {response.status})")

                    # Deactivate after too many failures
                    if subscription.failure_count >= 5:
                        subscription.is_active = False
                        logger.error(f"Deactivated webhook subscription {subscription.id} due to repeated failures")

                # Persist updated subscription
                await self._persist_webhook_subscription(subscription)

        except Exception as e:
            logger.error(f"Failed to send webhook {subscription.id}: {e}")
            subscription.failure_count += 1

            if subscription.failure_count >= 5:
                subscription.is_active = False

    def _matches_filters(self, payload: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if webhook payload matches subscription filters"""
        try:
            for key, expected_value in filters.items():
                actual_value = self._get_nested_value(payload, key)
                if actual_value != expected_value:
                    return False
            return True

        except Exception:
            return False

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        try:
            keys = path.split('.')
            value = data

            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None

            return value

        except Exception:
            return None

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook verification"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    async def _persist_webhook_subscription(self, subscription: WebhookSubscription):
        """Persist webhook subscription to database"""
        try:
            async with get_db() as session:
                db_subscription = WebhookSubscription(
                    id=subscription.id,
                    url=subscription.url,
                    events=subscription.events,
                    secret=subscription.secret,
                    is_active=subscription.is_active,
                    created_at=subscription.created_at,
                    headers=subscription.headers,
                    filters=subscription.filters
                )
                session.add(db_subscription)
                await session.commit()
                await session.refresh(db_subscription)

                logger.info(f"Persisted webhook subscription: {subscription.id}")

        except Exception as e:
            logger.error(f"Failed to persist webhook subscription {subscription.id}: {e}")
            raise

    async def _delete_webhook_subscription(self, subscription_id: str):
        """Delete webhook subscription from database"""
        try:
            async with get_db() as session:
                # Find the subscription
                result = await session.execute(
                    select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
                )
                db_subscription = result.scalar_one_or_none()

                if db_subscription:
                    await session.delete(db_subscription)
                    await session.commit()
                    logger.info(f"Deleted webhook subscription: {subscription_id}")
                else:
                    logger.warning(f"Webhook subscription not found for deletion: {subscription_id}")

        except Exception as e:
            logger.error(f"Failed to delete webhook subscription {subscription_id}: {e}")
            raise


# ============================================================================
# Queue Manager Component
# ============================================================================

class QueueManager:
    """Manages asynchronous processing queues with priority support"""

    def __init__(self, integration_service):
        self.integration_service = integration_service
        self.processing_workers: Dict[str, asyncio.Task] = {}

    async def enqueue_item(self, queue_name: str, item_data: Dict[str, Any], priority: QueuePriority = QueuePriority.NORMAL) -> str:
        """Add an item to a processing queue"""
        try:
            item = QueueItem(
                id=str(uuid.uuid4()),
                type=item_data.get('type', 'generic'),
                priority=priority,
                data=item_data,
                created_at=datetime.utcnow(),
                max_retries=item_data.get('max_retries', 3),
                processing_deadline=item_data.get('deadline'),
                callback_url=item_data.get('callback_url')
            )

            # Initialize queue if it doesn't exist
            if queue_name not in self.integration_service.processing_queues:
                self.integration_service.processing_queues[queue_name] = []

            # Add item to queue (maintain priority order)
            queue = self.integration_service.processing_queues[queue_name]
            insert_index = 0

            for i, existing_item in enumerate(queue):
                if item.priority.value > existing_item.priority.value:
                    insert_index = i
                    break
                insert_index = i + 1

            queue.insert(insert_index, item)

            # Persist to Redis for distributed processing
            await self._persist_queue_item(queue_name, item)

            logger.info(f"Enqueued item {item.id} in queue {queue_name} with priority {priority.name}")
            return item.id

        except Exception as e:
            logger.error(f"Failed to enqueue item: {e}")
            raise

    async def dequeue_item(self, queue_name: str) -> Optional[QueueItem]:
        """Remove and return the next item from a queue"""
        try:
            queue = self.integration_service.processing_queues.get(queue_name, [])

            if not queue:
                return None

            # Get highest priority item
            item = queue.pop(0)

            # Remove from Redis
            await self._remove_queue_item(queue_name, item.id)

            logger.info(f"Dequeued item {item.id} from queue {queue_name}")
            return item

        except Exception as e:
            logger.error(f"Failed to dequeue item from {queue_name}: {e}")
            return None

    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get statistics for a processing queue"""
        try:
            queue = self.integration_service.processing_queues.get(queue_name, [])

            stats = {
                "queue_name": queue_name,
                "total_items": len(queue),
                "items_by_priority": {},
                "oldest_item_age_seconds": None,
                "average_wait_time_seconds": None
            }

            if queue:
                # Count items by priority
                priority_counts = {}
                for item in queue:
                    priority_name = item.priority.name
                    priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1

                stats["items_by_priority"] = priority_counts

                # Calculate oldest item age
                oldest_item = min(queue, key=lambda x: x.created_at)
                stats["oldest_item_age_seconds"] = (datetime.utcnow() - oldest_item.created_at).total_seconds()

            return stats

        except Exception as e:
            logger.error(f"Failed to get queue stats for {queue_name}: {e}")
            return {"error": str(e)}

    async def retry_failed_item(self, queue_name: str, item_id: str) -> bool:
        """Retry processing a failed queue item"""
        try:
            # Find item in Redis (for failed items that were removed from memory)
            item_data = await self.integration_service.redis.hgetall(f"queue:{queue_name}:failed:{item_id}")

            if not item_data:
                return False

            # Recreate item and re-enqueue
            item_data['retry_count'] = str(int(item_data.get('retry_count', 0)) + 1)

            await self.enqueue_item(queue_name, item_data, QueuePriority(item_data.get('priority', 2)))

            # Remove from failed items
            await self.integration_service.redis.delete(f"queue:{queue_name}:failed:{item_id}")

            logger.info(f"Retried failed item {item_id} in queue {queue_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to retry item {item_id}: {e}")
            return False

    async def _process_queues_background(self):
        """Background task to process queued items"""
        while True:
            try:
                # Process each queue
                for queue_name in list(self.integration_service.processing_queues.keys()):
                    item = await self.dequeue_item(queue_name)

                    if item:
                        # Process item asynchronously
                        asyncio.create_task(self._process_queue_item(queue_name, item))

                # Wait before next processing cycle
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in queue processing background task: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _process_queue_item(self, queue_name: str, item: QueueItem):
        """Process a single queue item"""
        try:
            logger.info(f"Processing queue item {item.id} of type {item.type}")

            # Process based on item type
            if item.type == 'workflow_execution':
                await self._process_workflow_item(item)
            elif item.type == 'webhook_delivery':
                await self._process_webhook_item(item)
            elif item.type == 'data_processing':
                await self._process_data_item(item)
            else:
                # Generic processing
                await self._process_generic_item(item)

            # Send callback if specified
            if item.callback_url:
                await self._send_processing_callback(item, {"status": "completed"})

        except Exception as e:
            logger.error(f"Failed to process queue item {item.id}: {e}")

            # Handle retry logic
            item.retry_count += 1

            if item.retry_count < item.max_retries:
                # Re-enqueue for retry
                await self.enqueue_item(queue_name, item.data, item.priority)
            else:
                # Mark as failed
                await self._mark_item_failed(queue_name, item)

                # Send failure callback
                if item.callback_url:
                    await self._send_processing_callback(item, {"status": "failed", "error": str(e)})

    async def _process_workflow_item(self, item: QueueItem):
        """Process a workflow execution item"""
        workflow_id = item.data.get('workflow_id')
        parameters = item.data.get('parameters', {})

        if workflow_id:
            await self.integration_service.workflow_service.execute_workflow(workflow_id, parameters)

    async def _process_webhook_item(self, item: QueueItem):
        """Process a webhook delivery item"""
        event = WebhookEvent(item.data.get('event'))
        data = item.data.get('data', {})

        await self.integration_service.webhook_manager.trigger_webhook(event, data)

    async def _process_data_item(self, item: QueueItem):
        """Process a data processing item"""
        # Placeholder for data processing logic
        logger.info(f"Processing data item: {item.data}")

    async def _process_generic_item(self, item: QueueItem):
        """Process a generic queue item"""
        # Placeholder for generic processing logic
        logger.info(f"Processing generic item: {item.data}")

    async def _mark_item_failed(self, queue_name: str, item: QueueItem):
        """Mark a queue item as failed"""
        try:
            # Store in Redis for potential retry
            failed_key = f"queue:{queue_name}:failed:{item.id}"
            item_data = {
                "id": item.id,
                "type": item.type,
                "priority": item.priority.value,
                "data": json.dumps(item.data),
                "retry_count": item.retry_count,
                "failed_at": datetime.utcnow().isoformat(),
                "error": "Processing failed"
            }

            await self.integration_service.redis.hset(failed_key, mapping=item_data)
            await self.integration_service.redis.expire(failed_key, 86400)  # 24 hours

        except Exception as e:
            logger.error(f"Failed to mark item {item.id} as failed: {e}")

    async def _send_processing_callback(self, item: QueueItem, result: Dict[str, Any]):
        """Send callback notification for processed item"""
        try:
            async with ClientSession() as session:
                await session.post(item.callback_url, json=result)

        except Exception as e:
            logger.error(f"Failed to send callback for item {item.id}: {e}")

    async def _persist_queue_item(self, queue_name: str, item: QueueItem):
        """Persist queue item to database and Redis"""
        try:
            # Persist to database
            async with get_db() as session:
                db_item = QueueItem(
                    id=item.id,
                    queue_name=queue_name,
                    type=item.type,
                    priority=item.priority.name.lower(),
                    data=item.data,
                    status="pending",
                    created_at=item.created_at,
                    retry_count=item.retry_count,
                    max_retries=item.max_retries,
                    callback_url=item.callback_url,
                    processing_deadline=item.processing_deadline
                )
                session.add(db_item)
                await session.commit()

            # Also persist to Redis for fast access
            item_key = f"queue:{queue_name}:item:{item.id}"
            item_data = {
                "id": item.id,
                "type": item.type,
                "priority": item.priority.value,
                "data": json.dumps(item.data),
                "created_at": item.created_at.isoformat(),
                "retry_count": item.retry_count,
                "max_retries": item.max_retries,
                "callback_url": item.callback_url or ""
            }

            await self.integration_service.redis.hset(item_key, mapping=item_data)

        except Exception as e:
            logger.error(f"Failed to persist queue item {item.id}: {e}")

    async def _remove_queue_item(self, queue_name: str, item_id: str):
        """Remove queue item from database and Redis"""
        try:
            # Remove from database
            async with get_db() as session:
                result = await session.execute(
                    select(QueueItem).where(
                        QueueItem.id == item_id,
                        QueueItem.queue_name == queue_name
                    )
                )
                db_item = result.scalar_one_or_none()
                if db_item:
                    await session.delete(db_item)
                    await session.commit()

            # Remove from Redis
            item_key = f"queue:{queue_name}:item:{item_id}"
            await self.integration_service.redis.delete(item_key)

        except Exception as e:
            logger.error(f"Failed to remove queue item {item_id}: {e}")


# ============================================================================
# Load Balancer Component
# ============================================================================

class LoadBalancer:
    """Intelligent load balancer for distributing processing workloads"""

    def __init__(self, integration_service):
        self.integration_service = integration_service
        self.backend_health: Dict[str, bool] = {}
        self.request_counts: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = {}

    async def distribute_request(self, request_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Distribute a request to the most appropriate backend"""
        try:
            # Get available backends for this request type
            available_backends = await self._get_available_backends(request_type)

            if not available_backends:
                raise RuntimeError(f"No available backends for request type: {request_type}")

            # Select best backend
            selected_backend = await self._select_best_backend(available_backends, request_data)

            # Route request to selected backend
            result = await self._route_to_backend(selected_backend, request_data)

            # Update statistics
            await self._update_backend_stats(selected_backend, result)

            return result

        except Exception as e:
            logger.error(f"Failed to distribute request: {e}")
            raise

    async def register_backend(self, backend_id: str, backend_config: Dict[str, Any]):
        """Register a new backend service"""
        try:
            # Persist to database
            async with get_db() as session:
                db_service = BackendService(
                    id=backend_id,
                    name=backend_config.get("name", backend_id),
                    url=backend_config["url"],
                    service_type=backend_config.get("service_type", "generic"),
                    supported_request_types=backend_config.get("supported_request_types", []),
                    is_active=backend_config.get("is_active", True),
                    health_check_url=backend_config.get("health_check_url"),
                    max_concurrent_requests=backend_config.get("max_concurrent_requests", 10),
                    request_timeout_seconds=backend_config.get("request_timeout_seconds", 30),
                    rate_limit_per_minute=backend_config.get("rate_limit_per_minute", 60),
                    config=backend_config.get("config", {})
                )
                session.add(db_service)
                await session.commit()

            # Add to in-memory cache
            self.integration_service.backend_services[backend_id] = {
                "config": backend_config,
                "health": True,
                "last_health_check": datetime.utcnow(),
                "stats": {
                    "total_requests": 0,
                    "active_requests": 0,
                    "average_response_time": 0.0,
                    "error_rate": 0.0
                }
            }

            logger.info(f"Registered backend: {backend_id}")

        except Exception as e:
            logger.error(f"Failed to register backend {backend_id}: {e}")
            raise

    async def unregister_backend(self, backend_id: str):
        """Unregister a backend service"""
        try:
            # Remove from database
            async with get_db() as session:
                result = await session.execute(
                    select(BackendService).where(BackendService.id == backend_id)
                )
                db_service = result.scalar_one_or_none()
                if db_service:
                    await session.delete(db_service)
                    await session.commit()

            # Remove from in-memory cache
            if backend_id in self.integration_service.backend_services:
                del self.integration_service.backend_services[backend_id]
                logger.info(f"Unregistered backend: {backend_id}")

        except Exception as e:
            logger.error(f"Failed to unregister backend {backend_id}: {e}")
            raise

    async def get_backend_stats(self) -> Dict[str, Any]:
        """Get comprehensive backend statistics"""
        try:
            stats = {
                "total_backends": len(self.integration_service.backend_services),
                "healthy_backends": sum(1 for b in self.integration_service.backend_services.values() if b["health"]),
                "backend_details": {}
            }

            for backend_id, backend_info in self.integration_service.backend_services.items():
                stats["backend_details"][backend_id] = {
                    "health": backend_info["health"],
                    "last_health_check": backend_info["last_health_check"].isoformat(),
                    "stats": backend_info["stats"]
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get backend stats: {e}")
            return {"error": str(e)}

    async def _get_available_backends(self, request_type: str) -> List[str]:
        """Get list of available backends for a request type"""
        try:
            available = []

            for backend_id, backend_info in self.integration_service.backend_services.items():
                if not backend_info["health"]:
                    continue

                # Check if backend supports this request type
                supported_types = backend_info["config"].get("supported_request_types", [])
                if request_type in supported_types or not supported_types:
                    available.append(backend_id)

            return available

        except Exception as e:
            logger.error(f"Failed to get available backends for {request_type}: {e}")
            return []

    async def _select_best_backend(self, available_backends: List[str], request_data: Dict[str, Any]) -> str:
        """Select the best backend using load balancing algorithm"""
        try:
            if len(available_backends) == 1:
                return available_backends[0]

            # Use round-robin with health and load consideration
            backend_scores = {}

            for backend_id in available_backends:
                backend_info = self.integration_service.backend_services[backend_id]
                stats = backend_info["stats"]

                # Calculate score based on multiple factors
                health_score = 1.0 if backend_info["health"] else 0.0
                load_score = max(0, 1.0 - (stats["active_requests"] / 10))  # Prefer less loaded
                response_time_score = max(0, 1.0 - (stats["average_response_time"] / 5000))  # Prefer faster
                error_rate_score = max(0, 1.0 - stats["error_rate"])  # Prefer lower error rate

                # Weighted score
                total_score = (
                    health_score * 0.4 +
                    load_score * 0.3 +
                    response_time_score * 0.2 +
                    error_rate_score * 0.1
                )

                backend_scores[backend_id] = total_score

            # Select backend with highest score
            return max(backend_scores, key=backend_scores.get)

        except Exception as e:
            logger.error(f"Failed to select best backend: {e}")
            # Fallback to first available
            return available_backends[0] if available_backends else None

    async def _route_to_backend(self, backend_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to selected backend"""
        try:
            backend_info = self.integration_service.backend_services[backend_id]
            backend_config = backend_info["config"]

            # Increment active request count
            backend_info["stats"]["active_requests"] += 1

            try:
                # Simulate backend processing (replace with actual backend call)
                start_time = datetime.utcnow()

                # Here you would make actual call to backend service
                result = await self._call_backend_service(backend_config, request_data)

                # Calculate response time
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Update response time statistics
                if backend_id not in self.response_times:
                    self.response_times[backend_id] = []

                self.response_times[backend_id].append(response_time)

                # Keep only last 100 response times
                if len(self.response_times[backend_id]) > 100:
                    self.response_times[backend_id].pop(0)

                # Update average response time
                backend_info["stats"]["average_response_time"] = sum(self.response_times[backend_id]) / len(self.response_times[backend_id])

                return result

            finally:
                # Decrement active request count
                backend_info["stats"]["active_requests"] -= 1
                backend_info["stats"]["total_requests"] += 1

        except Exception as e:
            logger.error(f"Failed to route to backend {backend_id}: {e}")
            raise

    async def _call_backend_service(self, backend_config: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call the actual backend service"""
        # Placeholder implementation
        # In real implementation, this would make HTTP call to backend service
        await asyncio.sleep(0.1)  # Simulate processing time

        return {
            "backend_id": backend_config.get("id"),
            "result": "processed",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _update_backend_stats(self, backend_id: str, result: Dict[str, Any]):
        """Update backend statistics after request completion"""
        try:
            backend_info = self.integration_service.backend_services[backend_id]

            # Check if request was successful
            if "error" in result:
                # Calculate error rate
                total_requests = backend_info["stats"]["total_requests"]
                if total_requests > 0:
                    backend_info["stats"]["error_rate"] = (backend_info["stats"].get("error_count", 0) + 1) / total_requests
                backend_info["stats"]["error_count"] = backend_info["stats"].get("error_count", 0) + 1

        except Exception as e:
            logger.error(f"Failed to update backend stats for {backend_id}: {e}")

    async def _health_check_backends(self):
        """Background task to health check all backends"""
        while True:
            try:
                for backend_id, backend_info in self.integration_service.backend_services.items():
                    try:
                        # Perform health check
                        is_healthy = await self._check_backend_health(backend_info["config"])

                        # Update health status
                        backend_info["health"] = is_healthy
                        backend_info["last_health_check"] = datetime.utcnow()

                        if not is_healthy:
                            logger.warning(f"Backend {backend_id} is unhealthy")

                    except Exception as e:
                        logger.error(f"Health check failed for backend {backend_id}: {e}")
                        backend_info["health"] = False

                # Wait before next health check cycle
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in backend health check task: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _check_backend_health(self, backend_config: Dict[str, Any]) -> bool:
        """Check health of a specific backend"""
        try:
            # Placeholder health check implementation
            # In real implementation, this would make HTTP call to backend health endpoint
            health_url = backend_config.get("health_url")

            if health_url:
                async with ClientSession() as session:
                    async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        return response.status == 200

            # Default to healthy if no health URL
            return True

        except Exception:
            return False


# ============================================================================
# Integration Layer Service Registration
# ============================================================================

async def _register_default_endpoints(self):
    """Register default API endpoints"""
    try:
        # Workflow endpoints
        await self.api_gateway.register_endpoint(APIEndpoint(
            path="/api/v1/workflows/execute",
            methods=["POST"],
            handler=self._handle_workflow_execution,
            requires_auth=True,
            rate_limit=100,
            description="Execute a workflow"
        ))

        await self.api_gateway.register_endpoint(APIEndpoint(
            path="/api/v1/workflows/schedule",
            methods=["POST"],
            handler=self._handle_workflow_schedule,
            requires_auth=True,
            rate_limit=50,
            description="Schedule a workflow"
        ))

        # Webhook endpoints
        await self.api_gateway.register_endpoint(APIEndpoint(
            path="/api/v1/webhooks/subscribe",
            methods=["POST"],
            handler=self._handle_webhook_subscribe,
            requires_auth=True,
            rate_limit=20,
            description="Subscribe to webhooks"
        ))

        await self.api_gateway.register_endpoint(APIEndpoint(
            path="/api/v1/webhooks/unsubscribe",
            methods=["DELETE"],
            handler=self._handle_webhook_unsubscribe,
            requires_auth=True,
            description="Unsubscribe from webhooks"
        ))

        # Queue endpoints
        await self.api_gateway.register_endpoint(APIEndpoint(
            path="/api/v1/queues/enqueue",
            methods=["POST"],
            handler=self._handle_queue_enqueue,
            requires_auth=True,
            rate_limit=200,
            description="Add item to processing queue"
        ))

        await self.api_gateway.register_endpoint(APIEndpoint(
            path="/api/v1/queues/stats",
            methods=["GET"],
            handler=self._handle_queue_stats,
            requires_auth=True,
            description="Get queue statistics"
        ))

        # Load balancer endpoints
        await self.api_gateway.register_endpoint(APIEndpoint(
            path="/api/v1/backends/stats",
            methods=["GET"],
            handler=self._handle_backend_stats,
            requires_auth=True,
            description="Get backend statistics"
        ))

        logger.info("Registered default API endpoints")

    except Exception as e:
        logger.error(f"Failed to register default endpoints: {e}")

# Add the method to the IntegrationLayerService class
IntegrationLayerService._register_default_endpoints = _register_default_endpoints

# Complete API endpoint handlers
async def _handle_workflow_execution(self, request):
    """Handle workflow execution requests with comprehensive validation and monitoring"""
    try:
        data = await request.json()

        # Validate request data
        workflow_id = data.get('workflow_id')
        if not workflow_id:
            return web.json_response(
                {"error": "workflow_id is required", "status": "error"},
                status=400
            )

        # Check if workflow exists
        if workflow_id not in self.workflow_service.workflow_definitions:
            return web.json_response(
                {"error": f"Workflow not found: {workflow_id}", "status": "error"},
                status=404
            )

        # Validate priority
        priority_str = data.get('priority', 'normal')
        if priority_str not in ['low', 'normal', 'high', 'critical']:
            return web.json_response(
                {"error": "Invalid priority level. Must be: low, normal, high, critical", "status": "error"},
                status=400
            )

        # Execute workflow
        execution_id = await self.workflow_service.execute_workflow(
            workflow_id,
            data.get('parameters', {}),
            Priority[priority_str.upper()]
        )

        # Log successful execution start
        logger.info(f"Workflow execution started: {execution_id} for workflow {workflow_id}")

        return web.json_response({
            "status": "success",
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "message": "Workflow execution started successfully",
            "priority": priority_str
        })

    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON in request body", "status": "error"},
            status=400
        )
    except ValueError as e:
        return web.json_response(
            {"error": str(e), "status": "error"},
            status=400
        )
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return web.json_response(
            {"error": "Internal server error", "status": "error"},
            status=500
        )

async def _handle_workflow_schedule(self, request):
    """Handle workflow scheduling requests"""
    try:
        data = await request.json()

        # Validate request data
        workflow_id = data.get('workflow_id')
        trigger_config = data.get('trigger_config')

        if not workflow_id:
            return web.json_response(
                {"error": "workflow_id is required", "status": "error"},
                status=400
            )

        if not trigger_config:
            return web.json_response(
                {"error": "trigger_config is required", "status": "error"},
                status=400
            )

        # Check if workflow exists
        if workflow_id not in self.workflow_service.workflow_definitions:
            return web.json_response(
                {"error": f"Workflow not found: {workflow_id}", "status": "error"},
                status=404
            )

        # Schedule workflow
        schedule_id = await self.workflow_service.schedule_workflow(
            workflow_id,
            trigger_config,
            data.get('parameters', {})
        )

        return web.json_response({
            "status": "success",
            "schedule_id": schedule_id,
            "workflow_id": workflow_id,
            "message": "Workflow scheduled successfully"
        })

    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON in request body", "status": "error"},
            status=400
        )
    except Exception as e:
        logger.error(f"Workflow scheduling failed: {e}")
        return web.json_response(
            {"error": "Internal server error", "status": "error"},
            status=500
        )

async def _handle_webhook_subscribe(self, request):
    """Handle webhook subscription requests"""
    try:
        data = await request.json()

        # Validate request data
        url = data.get('url')
        events = data.get('events')

        if not url:
            return web.json_response(
                {"error": "url is required", "status": "error"},
                status=400
            )

        if not events or not isinstance(events, list):
            return web.json_response(
                {"error": "events must be a non-empty array", "status": "error"},
                status=400
            )

        # Validate events
        valid_events = ['workflow.started', 'workflow.completed', 'workflow.failed', 'step.completed', 'step.failed']
        invalid_events = [event for event in events if event not in valid_events]
        if invalid_events:
            return web.json_response(
                {"error": f"Invalid events: {invalid_events}. Valid events: {valid_events}", "status": "error"},
                status=400
            )

        # Create subscription
        subscription_id = await self.webhook_manager.subscribe_webhook(data)

        return web.json_response({
            "status": "success",
            "subscription_id": subscription_id,
            "message": "Webhook subscription created successfully"
        })

    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON in request body", "status": "error"},
            status=400
        )
    except Exception as e:
        logger.error(f"Webhook subscription failed: {e}")
        return web.json_response(
            {"error": "Internal server error", "status": "error"},
            status=500
        )

async def _handle_webhook_unsubscribe(self, request):
    """Handle webhook unsubscription requests"""
    try:
        subscription_id = request.match_info.get('subscription_id')

        if not subscription_id:
            return web.json_response(
                {"error": "subscription_id is required", "status": "error"},
                status=400
            )

        # Unsubscribe
        success = await self.webhook_manager.unsubscribe_webhook(subscription_id)

        if not success:
            return web.json_response(
                {"error": f"Subscription not found: {subscription_id}", "status": "error"},
                status=404
            )

        return web.json_response({
            "status": "success",
            "message": "Webhook subscription removed successfully"
        })

    except Exception as e:
        logger.error(f"Webhook unsubscription failed: {e}")
        return web.json_response(
            {"error": "Internal server error", "status": "error"},
            status=500
        )

async def _handle_queue_enqueue(self, request):
    """Handle queue item enqueue requests"""
    try:
        data = await request.json()

        # Validate request data
        queue_name = data.get('queue_name')
        item_data = data.get('data')

        if not queue_name:
            return web.json_response(
                {"error": "queue_name is required", "status": "error"},
                status=400
            )

        if not item_data:
            return web.json_response(
                {"error": "data is required", "status": "error"},
                status=400
            )

        # Validate priority
        priority_str = data.get('priority', 'normal')
        if priority_str not in ['low', 'normal', 'high', 'critical']:
            return web.json_response(
                {"error": "Invalid priority level. Must be: low, normal, high, critical", "status": "error"},
                status=400
            )

        # Enqueue item
        item_id = await self.queue_manager.enqueue_item(
            queue_name,
            item_data,
            QueuePriority[priority_str.upper()]
        )

        return web.json_response({
            "status": "success",
            "item_id": item_id,
            "queue_name": queue_name,
            "message": "Item enqueued successfully"
        })

    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON in request body", "status": "error"},
            status=400
        )
    except Exception as e:
        logger.error(f"Queue enqueue failed: {e}")
        return web.json_response(
            {"error": "Internal server error", "status": "error"},
            status=500
        )

async def _handle_queue_stats(self, request):
    """Handle queue statistics requests"""
    try:
        queue_name = request.match_info.get('queue_name')

        if not queue_name:
            return web.json_response(
                {"error": "queue_name is required", "status": "error"},
                status=400
            )

        # Get queue statistics
        stats = await self.queue_manager.get_queue_stats(queue_name)

        return web.json_response({
            "status": "success",
            "queue_name": queue_name,
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Queue stats retrieval failed: {e}")
        return web.json_response(
            {"error": "Internal server error", "status": "error"},
            status=500
        )

async def _handle_backend_stats(self, request):
    """Handle backend statistics requests"""
    try:
        # Get backend statistics
        stats = await self.load_balancer.get_backend_stats()

        return web.json_response({
            "status": "success",
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Backend stats retrieval failed: {e}")
        return web.json_response(
            {"error": "Internal server error", "status": "error"},
            status=500
        )

# Add placeholder methods to IntegrationLayerService
IntegrationLayerService._handle_workflow_execution = _handle_workflow_execution
IntegrationLayerService._handle_workflow_schedule = _handle_workflow_schedule
IntegrationLayerService._handle_webhook_subscribe = _handle_webhook_subscribe
IntegrationLayerService._handle_webhook_unsubscribe = _handle_webhook_unsubscribe
IntegrationLayerService._handle_queue_enqueue = _handle_queue_enqueue
IntegrationLayerService._handle_queue_stats = _handle_queue_stats
IntegrationLayerService._handle_backend_stats = _handle_backend_stats

# ============================================================================
# Database Persistence Methods (Placeholders)
# ============================================================================

async def _load_webhook_subscriptions(self):
    """Load webhook subscriptions from database"""
    try:
        async with get_db() as session:
            result = await session.execute(select(WebhookSubscription))
            db_subscriptions = result.scalars().all()

            for db_sub in db_subscriptions:
                # Convert to service model
                subscription = WebhookSubscription(
                    id=str(db_sub.id),
                    url=db_sub.url,
                    events=db_sub.events,
                    secret=db_sub.secret,
                    is_active=db_sub.is_active,
                    created_at=db_sub.created_at,
                    last_triggered=db_sub.last_triggered,
                    failure_count=db_sub.failure_count,
                    headers=db_sub.headers,
                    filters=db_sub.filters
                )
                self.webhook_subscriptions[subscription.id] = subscription

            logger.info(f"Loaded {len(db_subscriptions)} webhook subscriptions from database")

    except Exception as e:
        logger.error(f"Failed to load webhook subscriptions: {e}")
        raise

async def _load_backend_services(self):
    """Load backend services from database"""
    try:
        async with get_db() as session:
            result = await session.execute(select(BackendService))
            db_services = result.scalars().all()

            for db_service in db_services:
                # Convert to service format
                service_config = {
                    "id": str(db_service.id),
                    "name": db_service.name,
                    "url": db_service.url,
                    "service_type": db_service.service_type,
                    "supported_request_types": db_service.supported_request_types,
                    "health_check_url": db_service.health_check_url,
                    "max_concurrent_requests": db_service.max_concurrent_requests,
                    "request_timeout_seconds": db_service.request_timeout_seconds,
                    "rate_limit_per_minute": db_service.rate_limit_per_minute,
                    **db_service.config
                }

                self.backend_services[str(db_service.id)] = {
                    "config": service_config,
                    "health": db_service.health_status == "healthy",
                    "last_health_check": db_service.last_health_check,
                    "stats": {
                        "total_requests": 0,  # Will be loaded from metrics
                        "active_requests": 0,
                        "average_response_time": 0.0,
                        "error_rate": 0.0
                    }
                }

            logger.info(f"Loaded {len(db_services)} backend services from database")

    except Exception as e:
        logger.error(f"Failed to load backend services: {e}")
        raise

# Add methods to IntegrationLayerService
IntegrationLayerService._load_webhook_subscriptions = _load_webhook_subscriptions
IntegrationLayerService._load_backend_services = _load_backend_services

# ============================================================================
# Global Service Instance
# ============================================================================

integration_layer_service = IntegrationLayerService()
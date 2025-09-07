"""
Integration Layer API Routes

Provides REST API endpoints for:
- API Gateway management and routing
- Webhook subscription and management
- Queue management and monitoring
- Load balancer statistics and control

Author: Kilo Code
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.integration_layer_service import (
    integration_layer_service,
    QueuePriority,
    WebhookEvent
)
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/integration",
    tags=["Integration Layer"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Pydantic Models for API
# ============================================================================

class WebhookSubscriptionCreate(BaseModel):
    """API model for creating webhook subscription"""
    url: str = Field(..., description="Webhook URL endpoint")
    events: List[str] = Field(..., description="List of events to subscribe to")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers for webhook requests")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Event filters")


class WebhookSubscriptionResponse(BaseModel):
    """API model for webhook subscription response"""
    id: str
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime
    last_triggered: Optional[datetime] = None
    failure_count: int = 0
    headers: Dict[str, str] = {}
    filters: Dict[str, Any] = {}


class QueueItemCreate(BaseModel):
    """API model for creating queue item"""
    type: str = Field(..., description="Type of queue item")
    priority: QueuePriority = Field(QueuePriority.NORMAL, description="Queue priority")
    data: Dict[str, Any] = Field(..., description="Queue item data")
    max_retries: int = Field(3, description="Maximum retry attempts")
    callback_url: Optional[str] = Field(None, description="Callback URL for completion notification")


class QueueItemResponse(BaseModel):
    """API model for queue item response"""
    id: str
    type: str
    priority: QueuePriority
    data: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    processing_deadline: Optional[datetime] = None
    callback_url: Optional[str] = None


class BackendRegistration(BaseModel):
    """API model for backend registration"""
    id: str = Field(..., description="Unique backend identifier")
    url: str = Field(..., description="Backend service URL")
    supported_request_types: List[str] = Field(default_factory=list, description="Supported request types")
    health_check_url: Optional[str] = Field(None, description="Health check endpoint URL")
    max_concurrent_requests: int = Field(10, description="Maximum concurrent requests")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional backend metadata")


class LoadBalancerStats(BaseModel):
    """API model for load balancer statistics"""
    total_requests: int = 0
    active_connections: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    backend_health: Dict[str, bool] = {}


# ============================================================================
# API Gateway Endpoints
# ============================================================================

@router.get("/gateway/endpoints", response_model=Dict[str, Any])
async def list_api_endpoints(
    current_user: Dict = Depends(get_current_user)
):
    """List all registered API endpoints in the gateway"""
    try:
        endpoints = []
        for path, endpoint in integration_layer_service.api_endpoints.items():
            endpoints.append({
                "path": path,
                "methods": endpoint.methods,
                "requires_auth": endpoint.requires_auth,
                "rate_limit": endpoint.rate_limit,
                "timeout": endpoint.timeout,
                "description": endpoint.description
            })

        return {
            "status": "success",
            "data": {
                "endpoints": endpoints,
                "total": len(endpoints)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list API endpoints: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list API endpoints: {str(e)}")


@router.get("/gateway/stats", response_model=Dict[str, Any])
async def get_gateway_stats(
    current_user: Dict = Depends(get_current_user)
):
    """Get API gateway statistics and performance metrics"""
    try:
        # Get rate limiting stats from Redis
        rate_limit_keys = await integration_layer_service.redis.keys("rate_limit:*")
        active_rate_limits = len(rate_limit_keys)

        # Get request cache stats
        cache_size = len(integration_layer_service.api_gateway.request_cache)

        return {
            "status": "success",
            "data": {
                "endpoints_registered": len(integration_layer_service.api_endpoints),
                "active_rate_limits": active_rate_limits,
                "cache_size": cache_size,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get gateway stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get gateway stats: {str(e)}")


# ============================================================================
# Webhook Management Endpoints
# ============================================================================

@router.post("/webhooks/subscribe", response_model=Dict[str, Any])
async def subscribe_webhook(
    subscription: WebhookSubscriptionCreate,
    current_user: Dict = Depends(get_current_user)
):
    """
    Subscribe to webhook events

    This endpoint creates a webhook subscription for receiving real-time notifications
    about workflow events, system status changes, and other platform activities.
    """
    try:
        # Validate events
        valid_events = [event.value for event in WebhookEvent]
        invalid_events = [event for event in subscription.events if event not in valid_events]

        if invalid_events:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid events: {invalid_events}. Valid events: {valid_events}"
            )

        subscription_id = await integration_layer_service.webhook_manager.subscribe_webhook({
            "url": subscription.url,
            "events": subscription.events,
            "headers": subscription.headers,
            "filters": subscription.filters
        })

        return {
            "status": "success",
            "message": "Webhook subscription created successfully",
            "data": {
                "subscription_id": subscription_id,
                "url": subscription.url,
                "events": subscription.events
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to subscribe webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to subscribe webhook: {str(e)}")


@router.get("/webhooks/subscriptions", response_model=Dict[str, Any])
async def list_webhook_subscriptions(
    active_only: bool = Query(True, description="Show only active subscriptions"),
    current_user: Dict = Depends(get_current_user)
):
    """List all webhook subscriptions"""
    try:
        subscriptions = []
        for sub_id, subscription in integration_layer_service.webhook_subscriptions.items():
            if active_only and not subscription.is_active:
                continue

            subscriptions.append({
                "id": sub_id,
                "url": subscription.url,
                "events": [event.value for event in subscription.events],
                "is_active": subscription.is_active,
                "created_at": subscription.created_at.isoformat(),
                "last_triggered": subscription.last_triggered.isoformat() if subscription.last_triggered else None,
                "failure_count": subscription.failure_count,
                "headers": subscription.headers,
                "filters": subscription.filters
            })

        return {
            "status": "success",
            "data": {
                "subscriptions": subscriptions,
                "total": len(subscriptions)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list webhook subscriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list webhook subscriptions: {str(e)}")


@router.delete("/webhooks/subscriptions/{subscription_id}", response_model=Dict[str, Any])
async def unsubscribe_webhook(
    subscription_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Unsubscribe from webhook events"""
    try:
        success = await integration_layer_service.webhook_manager.unsubscribe_webhook(subscription_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Webhook subscription not found: {subscription_id}")

        return {
            "status": "success",
            "message": "Webhook subscription removed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unsubscribe webhook {subscription_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe webhook: {str(e)}")


@router.post("/webhooks/test/{subscription_id}", response_model=Dict[str, Any])
async def test_webhook_subscription(
    subscription_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Test a webhook subscription by sending a test event"""
    try:
        if subscription_id not in integration_layer_service.webhook_subscriptions:
            raise HTTPException(status_code=404, detail=f"Webhook subscription not found: {subscription_id}")

        subscription = integration_layer_service.webhook_subscriptions[subscription_id]

        # Send test event
        test_event = {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": "This is a test webhook event",
                "subscription_id": subscription_id,
                "test_time": datetime.utcnow().isoformat()
            }
        }

        await integration_layer_service.webhook_manager._send_webhook(subscription, test_event)

        return {
            "status": "success",
            "message": "Test webhook sent successfully",
            "data": {
                "subscription_id": subscription_id,
                "url": subscription.url,
                "test_event": test_event
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test webhook subscription {subscription_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test webhook subscription: {str(e)}")


# ============================================================================
# Queue Management Endpoints
# ============================================================================

@router.post("/queues/{queue_name}/enqueue", response_model=Dict[str, Any])
async def enqueue_item(
    queue_name: str,
    item: QueueItemCreate,
    current_user: Dict = Depends(get_current_user)
):
    """
    Add an item to a processing queue

    This endpoint allows queuing items for asynchronous processing with priority support.
    Items are processed in priority order (CRITICAL > HIGH > NORMAL > LOW).
    """
    try:
        item_id = await integration_layer_service.queue_manager.enqueue_item(
            queue_name,
            {
                "type": item.type,
                "data": item.data,
                "max_retries": item.max_retries,
                "callback_url": item.callback_url
            },
            item.priority
        )

        return {
            "status": "success",
            "message": "Item enqueued successfully",
            "data": {
                "item_id": item_id,
                "queue_name": queue_name,
                "priority": item.priority.value
            }
        }

    except Exception as e:
        logger.error(f"Failed to enqueue item in queue {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enqueue item: {str(e)}")


@router.get("/queues/{queue_name}/stats", response_model=Dict[str, Any])
async def get_queue_stats(
    queue_name: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get statistics for a processing queue"""
    try:
        stats = await integration_layer_service.queue_manager.get_queue_stats(queue_name)

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get queue stats for {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


@router.post("/queues/{queue_name}/retry/{item_id}", response_model=Dict[str, Any])
async def retry_failed_item(
    queue_name: str,
    item_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Retry processing a failed queue item"""
    try:
        success = await integration_layer_service.queue_manager.retry_failed_item(queue_name, item_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Failed item not found: {item_id}")

        return {
            "status": "success",
            "message": "Item retry initiated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry item {item_id} in queue {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retry item: {str(e)}")


@router.get("/queues", response_model=Dict[str, Any])
async def list_queues(
    current_user: Dict = Depends(get_current_user)
):
    """List all processing queues and their statistics"""
    try:
        queue_stats = {}
        for queue_name in integration_layer_service.processing_queues.keys():
            queue_stats[queue_name] = await integration_layer_service.queue_manager.get_queue_stats(queue_name)

        return {
            "status": "success",
            "data": {
                "queues": queue_stats,
                "total_queues": len(queue_stats)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list queues: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list queues: {str(e)}")


# ============================================================================
# Load Balancer Endpoints
# ============================================================================

@router.post("/backends/register", response_model=Dict[str, Any])
async def register_backend(
    backend: BackendRegistration,
    current_user: Dict = Depends(get_current_user)
):
    """Register a new backend service with the load balancer"""
    try:
        await integration_layer_service.load_balancer.register_backend(
            backend.id,
            {
                "url": backend.url,
                "supported_request_types": backend.supported_request_types,
                "health_check_url": backend.health_check_url,
                "max_concurrent_requests": backend.max_concurrent_requests,
                "timeout_seconds": backend.timeout_seconds,
                "metadata": backend.metadata
            }
        )

        return {
            "status": "success",
            "message": "Backend registered successfully",
            "data": {
                "backend_id": backend.id,
                "url": backend.url,
                "supported_request_types": backend.supported_request_types
            }
        }

    except Exception as e:
        logger.error(f"Failed to register backend {backend.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register backend: {str(e)}")


@router.delete("/backends/{backend_id}", response_model=Dict[str, Any])
async def unregister_backend(
    backend_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Unregister a backend service from the load balancer"""
    try:
        success = await integration_layer_service.load_balancer.unregister_backend(backend_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Backend not found: {backend_id}")

        return {
            "status": "success",
            "message": "Backend unregistered successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister backend {backend_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unregister backend: {str(e)}")


@router.get("/backends/stats", response_model=Dict[str, Any])
async def get_backend_stats(
    current_user: Dict = Depends(get_current_user)
):
    """Get comprehensive backend statistics from the load balancer"""
    try:
        stats = await integration_layer_service.load_balancer.get_backend_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get backend stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backend stats: {str(e)}")


@router.post("/load-balance/{request_type}", response_model=Dict[str, Any])
async def distribute_request(
    request_type: str,
    request_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Distribute a request through the load balancer

    This endpoint routes requests to the most appropriate backend service
    based on load, health, and performance metrics.
    """
    try:
        result = await integration_layer_service.load_balancer.distribute_request(
            request_type,
            request_data
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to distribute request of type {request_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to distribute request: {str(e)}")


# ============================================================================
# Integration Layer Health and Monitoring Endpoints
# ============================================================================

@router.get("/health", response_model=Dict[str, Any])
async def get_integration_layer_health():
    """Get integration layer service health status"""
    try:
        # Check component health
        gateway_healthy = len(integration_layer_service.api_endpoints) > 0
        webhook_healthy = True  # Webhook manager is always healthy
        queue_healthy = len(integration_layer_service.processing_queues) >= 0
        load_balancer_healthy = len(integration_layer_service.backend_services) >= 0

        # Overall health
        components_healthy = all([
            gateway_healthy,
            webhook_healthy,
            queue_healthy,
            load_balancer_healthy
        ])

        health_status = "healthy" if components_healthy else "degraded"

        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "integration_layer",
            "components": {
                "api_gateway": {
                    "healthy": gateway_healthy,
                    "endpoints_registered": len(integration_layer_service.api_endpoints)
                },
                "webhook_manager": {
                    "healthy": webhook_healthy,
                    "subscriptions_active": len([
                        s for s in integration_layer_service.webhook_subscriptions.values()
                        if s.is_active
                    ])
                },
                "queue_manager": {
                    "healthy": queue_healthy,
                    "queues_active": len(integration_layer_service.processing_queues)
                },
                "load_balancer": {
                    "healthy": load_balancer_healthy,
                    "backends_registered": len(integration_layer_service.backend_services)
                }
            }
        }

    except Exception as e:
        logger.error(f"Failed to get integration layer health: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "integration_layer",
            "error": str(e)
        }


@router.get("/stats", response_model=Dict[str, Any])
async def get_integration_layer_stats():
    """Get comprehensive integration layer statistics"""
    try:
        # Get Redis stats
        redis_info = await integration_layer_service.redis.info()
        redis_memory_used = redis_info.get('used_memory_human', '0B')

        # Get queue stats
        queue_stats = {}
        for queue_name in integration_layer_service.processing_queues.keys():
            queue_stats[queue_name] = await integration_layer_service.queue_manager.get_queue_stats(queue_name)

        # Get backend stats
        backend_stats = await integration_layer_service.load_balancer.get_backend_stats()

        return {
            "status": "success",
            "data": {
                "redis": {
                    "memory_used": redis_memory_used,
                    "connected_clients": redis_info.get('connected_clients', 0)
                },
                "queues": queue_stats,
                "backends": backend_stats["data"] if "data" in backend_stats else backend_stats,
                "webhooks": {
                    "total_subscriptions": len(integration_layer_service.webhook_subscriptions),
                    "active_subscriptions": len([
                        s for s in integration_layer_service.webhook_subscriptions.values()
                        if s.is_active
                    ])
                },
                "api_gateway": {
                    "endpoints_registered": len(integration_layer_service.api_endpoints)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get integration layer stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get integration layer stats: {str(e)}")


# ============================================================================
# Webhook Event Triggering (Internal/Admin Use)
# ============================================================================

@router.post("/webhooks/trigger-event", response_model=Dict[str, Any])
async def trigger_webhook_event(
    event: str,
    data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Manually trigger a webhook event (admin use)

    This endpoint allows administrators to manually trigger webhook events
    for testing purposes or to simulate system events.
    """
    try:
        # Validate event type
        if event not in [e.value for e in WebhookEvent]:
            # Allow custom events for testing
            pass

        await integration_layer_service.webhook_manager.trigger_webhook(
            WebhookEvent(event) if event in [e.value for e in WebhookEvent] else event,
            data
        )

        return {
            "status": "success",
            "message": f"Webhook event '{event}' triggered successfully",
            "data": {
                "event": event,
                "data": data,
                "triggered_at": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to trigger webhook event {event}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger webhook event: {str(e)}")


# ============================================================================
# Queue Item Management (Admin Use)
# ============================================================================

@router.get("/queues/{queue_name}/items", response_model=Dict[str, Any])
async def list_queue_items(
    queue_name: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of items to return"),
    current_user: Dict = Depends(get_current_user)
):
    """List items in a processing queue (admin use)"""
    try:
        queue = integration_layer_service.processing_queues.get(queue_name, [])

        # Convert to response format
        items = []
        for item in queue[:limit]:
            items.append({
                "id": item.id,
                "type": item.type,
                "priority": item.priority.value,
                "created_at": item.created_at.isoformat(),
                "retry_count": item.retry_count,
                "max_retries": item.max_retries,
                "callback_url": item.callback_url
            })

        return {
            "status": "success",
            "data": {
                "queue_name": queue_name,
                "items": items,
                "total": len(queue),
                "returned": len(items)
            }
        }

    except Exception as e:
        logger.error(f"Failed to list queue items for {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list queue items: {str(e)}")


@router.delete("/queues/{queue_name}/items/{item_id}", response_model=Dict[str, Any])
async def remove_queue_item(
    queue_name: str,
    item_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Remove an item from a processing queue (admin use)"""
    try:
        queue = integration_layer_service.processing_queues.get(queue_name, [])

        # Find and remove item
        item_index = None
        for i, item in enumerate(queue):
            if item.id == item_id:
                item_index = i
                break

        if item_index is None:
            raise HTTPException(status_code=404, detail=f"Queue item not found: {item_id}")

        removed_item = queue.pop(item_index)

        # Remove from Redis
        await integration_layer_service.queue_manager._remove_queue_item(queue_name, item_id)

        return {
            "status": "success",
            "message": "Queue item removed successfully",
            "data": {
                "item_id": item_id,
                "queue_name": queue_name,
                "type": removed_item.type
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove queue item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove queue item: {str(e)}")
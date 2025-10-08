from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from typing import Optional, Dict, Any
from uuid import UUID
import json
import asyncio
from app.utils.logging import get_logger
from app.utils.metrics import MetricsCollector
from app.utils.auth import verify_token
from app.db.models.user import User
from sqlalchemy import select
from app.services.chat_service import ChatService
from app.db.models.email_workflow import EmailWorkflow, EmailWorkflowStatus
from app.db.models.task import Task, TaskStatus
from app.db.models.notification import Notification, NotificationStatus
from sqlalchemy import select, and_, or_, func
from uuid import UUID

logger = get_logger("websocket")
router = APIRouter()


async def validate_websocket_token(token: str) -> User:
    """Validate JWT token for WebSocket connections using scoped database session."""
    if not token:
        raise HTTPException(status_code=401, detail="Token required")

    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Use scoped session that will be properly closed
    from app.db.database import get_session_context
    async with get_session_context() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return user


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_users: Dict[str, User] = {}  # Track which user owns each connection
        self.task_subscriptions: Dict[UUID, set] = {}
        self.log_subscriptions: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user: Optional[User] = None):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        if user:
            self.connection_users[connection_id] = user
        MetricsCollector.increment_websocket_connections("logs", 1)
        logger.info(f"WebSocket connected: {connection_id} (user: {user.username if user else 'anonymous'})")

    def disconnect(self, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_users:
            del self.connection_users[connection_id]
        MetricsCollector.increment_websocket_connections("logs", -1)
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """Send message to specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast(self, message: dict, connection_ids: set):
        """Broadcast message to multiple connections."""
        if not connection_ids:
            return
        
        disconnected = set()
        for connection_id in connection_ids:
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to broadcast to {connection_id}: {e}")
                    disconnected.add(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    def subscribe_to_task(self, connection_id: str, task_id: UUID):
        """Subscribe connection to task updates."""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to task {task_id}")
    
    def unsubscribe_from_task(self, connection_id: str, task_id: UUID):
        """Unsubscribe connection from task updates."""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
        logger.info(f"Connection {connection_id} unsubscribed from task {task_id}")
    
    def subscribe_to_logs(self, connection_id: str, filters: dict):
        """Subscribe connection to log updates with filters."""
        self.log_subscriptions[connection_id] = filters
        logger.info(f"Connection {connection_id} subscribed to logs with filters: {filters}")
    
    def unsubscribe_from_logs(self, connection_id: str):
        """Unsubscribe connection from log updates."""
        if connection_id in self.log_subscriptions:
            del self.log_subscriptions[connection_id]
        logger.info(f"Connection {connection_id} unsubscribed from logs")

    async def broadcast_log(self, log_data: Dict[str, Any], user_id: Optional[int] = None, scope: str = "user"):
        """Broadcast log to appropriate WebSocket subscribers based on permissions and scope."""
        try:
            # Filter subscribers based on user permissions and scope
            eligible_connections = []

            for connection_id, filters in self.log_subscriptions.items():
                # Check if this connection should receive this log
                should_receive = False

                # System scope logs - only admins can see these
                if scope == "admin":
                    # Check if connection user is an admin/superuser
                    if connection_id in self.connection_users:
                        connection_user = self.connection_users[connection_id]
                        if connection_user.is_superuser:
                            should_receive = True

                # User scope logs - user can see their own logs, admins can see all user logs
                elif scope == "user":
                    # If log has user_id, only that user (or admins) should see it
                    if user_id and connection_id in self.connection_users:
                        connection_user = self.connection_users[connection_id]
                        # User can see their own logs, or admins can see all logs
                        if connection_user.id == user_id or connection_user.is_superuser:
                            should_receive = True
                    else:
                        # Logs without user_id are general system logs - visible to all authenticated users
                        if connection_id in self.connection_users:
                            should_receive = True

                # System logs - visible to all connected users
                else:
                    should_receive = True

                # Apply additional filters
                if should_receive and self._matches_log_filters(log_data, filters):
                    eligible_connections.append(connection_id)

            # Broadcast to eligible connections
            if eligible_connections:
                message = {
                    "type": "log",
                    "data": log_data,
                    "timestamp": log_data.get("timestamp"),
                    "scope": scope
                }

                disconnected = set()
                for connection_id in eligible_connections:
                    if connection_id in self.active_connections:
                        websocket = self.active_connections[connection_id]
                        try:
                            await websocket.send_text(json.dumps(message))
                        except Exception as e:
                            logger.error(f"Failed to broadcast log to {connection_id}: {e}")
                            disconnected.add(connection_id)

                # Clean up disconnected clients
                for connection_id in disconnected:
                    self.disconnect(connection_id)

                logger.debug(f"Broadcasted log to {len(eligible_connections) - len(disconnected)} connections")

        except Exception as e:
            logger.error(f"Failed to broadcast log: {e}")

    def _matches_log_filters(self, log_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if log data matches WebSocket subscription filters."""
        if not filters:
            return True

        for key, value in filters.items():
            # Skip special filter keys
            if key in ["admin_mode"]:
                continue

            if key not in log_data:
                continue

            if isinstance(value, list):
                if log_data[key] not in value:
                    return False
            elif log_data[key] != str(value):
                return False

        return True


manager = ConnectionManager()


@router.websocket("/logs")
async def websocket_logs(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    agent_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time log streaming with subscription filters."""
    connection_id = f"logs_{id(websocket)}"

    # Validate JWT token
    try:
        user = await validate_websocket_token(token)
        logger.info(f"WebSocket authenticated for user: {user.username}")
    except HTTPException as e:
        logger.warning(f"WebSocket authentication failed: {e.detail}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await manager.connect(websocket, connection_id, user)
    
    try:
        # Set up subscription filters
        filters = {}
        if agent_id:
            filters["agent_id"] = agent_id
        if task_id:
            filters["task_id"] = task_id
        if level:
            filters["level"] = level
        
        manager.subscribe_to_logs(connection_id, filters)
        
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": "Connected to log stream",
            "filters": filters
        }, connection_id)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": "2024-01-01T00:00:00Z"  # Will be dynamic
                    }, connection_id)
                
                elif message.get("type") == "update_filters":
                    new_filters = message.get("filters", {})
                    manager.subscribe_to_logs(connection_id, new_filters)
                    await manager.send_personal_message({
                        "type": "filters_updated",
                        "filters": new_filters
                    }, connection_id)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, connection_id)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": str(e)
                }, connection_id)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.unsubscribe_from_logs(connection_id)
        manager.disconnect(connection_id)


@router.websocket("/tasks/{task_id}")
async def websocket_task(
    websocket: WebSocket,
    task_id: UUID,
    token: str = Query(..., description="JWT authentication token")
):
    """WebSocket endpoint for real-time updates for specific task."""
    connection_id = f"task_{task_id}_{id(websocket)}"

    # Validate JWT token
    try:
        user = await validate_websocket_token(token)
        logger.info(f"Task WebSocket authenticated for user: {user.username}")
    except HTTPException as e:
        logger.warning(f"Task WebSocket authentication failed: {e.detail}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await manager.connect(websocket, connection_id, user)
    
    try:
        manager.subscribe_to_task(connection_id, task_id)
        
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": f"Connected to task {task_id}",
            "task_id": str(task_id)
        }, connection_id)
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": "2024-01-01T00:00:00Z"  # Will be dynamic
                    }, connection_id)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, connection_id)
    
    except WebSocketDisconnect:
        logger.info(f"Task WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Task WebSocket error: {e}")
    finally:
        manager.unsubscribe_from_task(connection_id, task_id)
        manager.disconnect(connection_id)


@router.websocket("/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: UUID,
    token: str = Query(..., description="JWT authentication token")
):
    """WebSocket endpoint for real-time chat with LLM."""
    connection_id = f"chat_{session_id}_{id(websocket)}"

    # Validate JWT token
    try:
        user = await validate_websocket_token(token)
        logger.info(f"Chat WebSocket authenticated for user: {user.username}")
    except HTTPException as e:
        logger.warning(f"Chat WebSocket authentication failed: {e.detail}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Validate chat session exists and is active
    chat_service = ChatService(db)
    session = await chat_service.get_session(session_id)

    if not session:
        logger.warning(f"Chat session {session_id} not found")
        await websocket.close(code=1008, reason="Chat session not found")
        return

    if not session.is_active:
        logger.warning(f"Chat session {session_id} is not active")
        await websocket.close(code=1008, reason="Chat session is not active")
        return

    await manager.connect(websocket, connection_id, user)

    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": f"Connected to chat session {session_id}",
            "session_id": str(session_id),
            "session_type": session.session_type,
            "model_name": session.model_name
        }, connection_id)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": "2024-01-01T00:00:00Z"  # Will be dynamic
                    }, connection_id)

                elif message.get("type") == "chat_message":
                    user_message = message.get("message", "").strip()
                    if not user_message:
                        await manager.send_personal_message({
                            "type": "error",
                            "message": "Message cannot be empty"
                        }, connection_id)
                        continue

                    # Send user message to LLM and get response
                    try:
                        result = await chat_service.send_message(
                            session_id=session_id,
                            user_message=user_message
                        )

                        # Send AI response back to client
                        await manager.send_personal_message({
                            "type": "chat_response",
                            "session_id": str(session_id),
                            "user_message": user_message,
                            "ai_response": result["response"],
                            "model": result["model"],
                            "metadata": result["metadata"]
                        }, connection_id)

                    except Exception as e:
                        logger.error(f"Error processing chat message: {e}")
                        await manager.send_personal_message({
                            "type": "error",
                            "message": f"Failed to process message: {str(e)}"
                        }, connection_id)

                elif message.get("type") == "get_history":
                    # Send chat history
                    messages = await chat_service.get_messages(session_id)
                    message_history = [msg.to_dict() for msg in messages]

                    await manager.send_personal_message({
                        "type": "chat_history",
                        "session_id": str(session_id),
                        "messages": message_history
                    }, connection_id)

                elif message.get("type") == "update_session_status":
                    new_status = message.get("status")
                    if new_status in ["active", "completed", "archived"]:
                        success = await chat_service.update_session_status(
                            session_id=session_id,
                            status=new_status
                        )

                        if success:
                            await manager.send_personal_message({
                                "type": "status_updated",
                                "session_id": str(session_id),
                                "status": new_status
                            }, connection_id)
                        else:
                            await manager.send_personal_message({
                                "type": "error",
                                "message": "Failed to update session status"
                            }, connection_id)
                    else:
                        await manager.send_personal_message({
                            "type": "error",
                            "message": "Invalid status"
                        }, connection_id)

                else:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown message type: {message.get('type')}"
                    }, connection_id)

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, connection_id)
            except Exception as e:
                logger.error(f"Error handling chat WebSocket message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": str(e)
                }, connection_id)

    except WebSocketDisconnect:
        logger.info(f"Chat WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Chat WebSocket error: {e}")
    finally:
        manager.disconnect(connection_id)


@router.websocket("/email/progress")
async def websocket_email_progress(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    user_id: Optional[str] = Query(None),
    workflow_id: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time email workflow progress monitoring."""
    connection_id = f"email_progress_{id(websocket)}"

    # Validate JWT token
    try:
        user = await validate_websocket_token(token)
        logger.info(f"Email progress WebSocket authenticated for user: {user.username}")
    except HTTPException as e:
        logger.warning(f"Email progress WebSocket authentication failed: {e.detail}")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await manager.connect(websocket, connection_id, user)

    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": "Connected to email progress monitoring",
            "user_id": user_id or user.username,
            "workflow_id": workflow_id
        }, connection_id)

        # Send initial status if workflow_id is provided
        if workflow_id:
            try:
                workflow_uuid = UUID(workflow_id)
                workflow = await db.get(EmailWorkflow, workflow_uuid)
                if workflow:
                    await manager.send_personal_message({
                        "type": "workflow_status",
                        "workflow_id": str(workflow.id),
                        "status": workflow.status.value,
                        "emails_processed": workflow.emails_processed,
                        "tasks_created": workflow.tasks_created,
                        "progress_percentage": min(100, (workflow.emails_processed / max(1, workflow.emails_processed + 10)) * 100),  # Estimate
                        "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
                        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
                    }, connection_id)
            except ValueError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid workflow_id format"
                }, connection_id)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    from datetime import datetime
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)

                elif message.get("type") == "subscribe_workflow":
                    # Subscribe to specific workflow updates
                    wf_id = message.get("workflow_id")
                    if wf_id:
                        try:
                            workflow_uuid = UUID(wf_id)
                            workflow = await db.get(EmailWorkflow, workflow_uuid)
                            if workflow:
                                await manager.send_personal_message({
                                    "type": "workflow_subscribed",
                                    "workflow_id": str(workflow.id),
                                    "status": workflow.status.value
                                }, connection_id)
                            else:
                                await manager.send_personal_message({
                                    "type": "error",
                                    "message": "Workflow not found"
                                }, connection_id)
                        except ValueError:
                            await manager.send_personal_message({
                                "type": "error",
                                "message": "Invalid workflow_id format"
                            }, connection_id)

                elif message.get("type") == "get_dashboard_stats":
                    # Send current dashboard statistics
                    target_user_id = user_id or str(user.id)

                    # Get workflow stats
                    total_workflows_query = select(func.count(EmailWorkflow.id)).where(EmailWorkflow.user_id == target_user_id)
                    total_workflows = await db.execute(total_workflows_query)
                    total_workflows = total_workflows.scalar() or 0

                    active_workflows_query = select(func.count(EmailWorkflow.id)).where(
                        and_(EmailWorkflow.user_id == target_user_id, EmailWorkflow.status == EmailWorkflowStatus.RUNNING)
                    )
                    active_workflows = await db.execute(active_workflows_query)
                    active_workflows = active_workflows.scalar() or 0

                    # Get task stats
                    pending_tasks_query = select(func.count(Task.id)).where(
                        and_(Task.input.op('->>')('user_id') == target_user_id, Task.status == TaskStatus.PENDING)
                    )
                    pending_tasks = await db.execute(pending_tasks_query)
                    pending_tasks = pending_tasks.scalar() or 0

                    completed_tasks_query = select(func.count(Task.id)).where(
                        and_(Task.input.op('->>')('user_id') == target_user_id, Task.status == TaskStatus.COMPLETED)
                    )
                    completed_tasks = await db.execute(completed_tasks_query)
                    completed_tasks = completed_tasks.scalar() or 0

                    # Get notification stats
                    unread_notifications_query = select(func.count(Notification.id)).where(
                        and_(Notification.user_id == target_user_id, Notification.status == NotificationStatus.UNREAD)
                    )
                    unread_notifications = await db.execute(unread_notifications_query)
                    unread_notifications = unread_notifications.scalar() or 0

                    await manager.send_personal_message({
                        "type": "dashboard_stats",
                        "stats": {
                            "total_workflows": total_workflows,
                            "active_workflows": active_workflows,
                            "pending_tasks": pending_tasks,
                            "completed_tasks": completed_tasks,
                            "unread_notifications": unread_notifications
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)

                elif message.get("type") == "get_recent_activity":
                    # Send recent activity
                    target_user_id = user_id or str(user.id)
                    limit = message.get("limit", 10)

                    activities = []

                    # Recent workflows
                    workflows_query = select(EmailWorkflow).where(EmailWorkflow.user_id == target_user_id).order_by(EmailWorkflow.created_at.desc()).limit(limit)
                    workflows_result = await db.execute(workflows_query)
                    workflows = workflows_result.scalars().all()

                    for workflow in workflows:
                        activities.append({
                            "type": "workflow",
                            "id": str(workflow.id),
                            "action": "created",
                            "title": f"Workflow {workflow.status.value}",
                            "timestamp": workflow.created_at.isoformat()
                        })

                    # Recent notifications
                    notifications_query = select(Notification).where(Notification.user_id == target_user_id).order_by(Notification.created_at.desc()).limit(limit)
                    notifications_result = await db.execute(notifications_query)
                    notifications = notifications_result.scalars().all()

                    for notification in notifications:
                        activities.append({
                            "type": "notification",
                            "id": str(notification.id),
                            "action": "created",
                            "title": notification.message[:50] + "..." if len(notification.message) > 50 else notification.message,
                            "timestamp": notification.created_at.isoformat()
                        })

                    # Sort and limit
                    activities.sort(key=lambda x: x['timestamp'], reverse=True)
                    activities = activities[:limit]

                    await manager.send_personal_message({
                        "type": "recent_activity",
                        "activities": activities,
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)

                else:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown message type: {message.get('type')}"
                    }, connection_id)

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, connection_id)
            except Exception as e:
                logger.error(f"Error handling email progress WebSocket message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": str(e)
                }, connection_id)

    except WebSocketDisconnect:
        logger.info(f"Email progress WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Email progress WebSocket error: {e}")
    finally:
        manager.disconnect(connection_id)


# Export manager for use by other modules
__all__ = ["manager"]
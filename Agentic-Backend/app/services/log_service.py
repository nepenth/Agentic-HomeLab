from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.task import TaskLog, LogLevel
from app.db.database import get_session_context
from app.services.pubsub_service import pubsub_service
from app.api.routes.websocket import manager as websocket_manager
from app.utils.logging import get_logger
from app.utils.metrics import MetricsCollector

logger = get_logger("log_service")


class LogService:
    """Service for managing structured logging with real-time streaming."""
    
    def __init__(self):
        self.websocket_manager = websocket_manager
        self.pubsub = pubsub_service
    
    async def log_message(
        self,
        task_id: UUID,
        agent_id: UUID,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskLog:
        """Log a message with both persistent storage and real-time streaming."""
        try:
            # Prepare log data
            log_data = {
                "task_id": str(task_id),
                "agent_id": str(agent_id),
                "level": level.value,
                "message": message,
                "context": context or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store in database
            log_record = await self._store_log(task_id, agent_id, level, message, context)
            
            # Publish to Redis Stream for real-time streaming
            try:
                stream_id = await self.pubsub.publish_log(log_data)
                # Update the database record with stream_id
                if log_record and stream_id:
                    async with get_session_context() as session:
                        log_record.stream_id = stream_id
                        session.add(log_record)
                        await session.commit()
            except Exception as e:
                logger.error(f"Failed to publish log to stream: {e}")
            
            # Broadcast to WebSocket subscribers
            await self._broadcast_to_websockets(log_data)
            
            # Update metrics
            MetricsCollector.increment_log_messages(level.value, "agent")
            
            return log_record
            
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
            raise
    
    async def _store_log(
        self,
        task_id: UUID,
        agent_id: UUID,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskLog:
        """Store log message in database."""
        try:
            async with get_session_context() as session:
                log_record = TaskLog(
                    task_id=task_id,
                    agent_id=agent_id,
                    level=level,
                    message=message,
                    context=context or {}
                )
                
                session.add(log_record)
                await session.commit()
                await session.refresh(log_record)
                
                return log_record
                
        except Exception as e:
            logger.error(f"Failed to store log in database: {e}")
            raise
    
    async def _broadcast_to_websockets(self, log_data: Dict[str, Any]):
        """Broadcast log message to WebSocket subscribers."""
        try:
            # Broadcast to log subscribers with matching filters
            for connection_id, filters in self.websocket_manager.log_subscriptions.items():
                if self._matches_subscription_filters(log_data, filters):
                    await self.websocket_manager.send_personal_message({
                        "type": "log",
                        "data": log_data
                    }, connection_id)
            
            # Broadcast to task-specific subscribers
            task_id = UUID(log_data["task_id"])
            if task_id in self.websocket_manager.task_subscriptions:
                connections = self.websocket_manager.task_subscriptions[task_id]
                await self.websocket_manager.broadcast({
                    "type": "task_log",
                    "data": log_data
                }, connections)
                
        except Exception as e:
            logger.error(f"Failed to broadcast to WebSocket: {e}")
    
    def _matches_subscription_filters(
        self,
        log_data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """Check if log data matches WebSocket subscription filters."""
        if not filters:
            return True
        
        for key, value in filters.items():
            if key not in log_data:
                return False
            
            if isinstance(value, list):
                if log_data[key] not in value:
                    return False
            elif log_data[key] != str(value):  # Convert to string for comparison
                return False
        
        return True
    
    async def get_task_logs(
        self,
        task_id: UUID,
        level: Optional[LogLevel] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskLog]:
        """Get task logs from database."""
        try:
            async with get_session_context() as session:
                from sqlalchemy import select
                
                query = select(TaskLog).where(TaskLog.task_id == task_id)
                
                if level:
                    query = query.where(TaskLog.level == level)
                
                query = query.offset(offset).limit(limit).order_by(TaskLog.timestamp.desc())
                
                result = await session.execute(query)
                logs = result.scalars().all()
                
                return logs
                
        except Exception as e:
            logger.error(f"Failed to get task logs: {e}")
            raise
    
    async def get_streaming_logs(
        self,
        start_id: str = "-",
        end_id: str = "+",
        count: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get logs from Redis Stream."""
        try:
            messages = await self.pubsub.get_log_history(start_id, end_id, count)
            
            # Apply filters if provided
            if filters:
                filtered_messages = []
                for msg in messages:
                    if self._matches_subscription_filters(msg, filters):
                        filtered_messages.append(msg)
                return filtered_messages
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get streaming logs: {e}")
            raise
    
    async def subscribe_to_log_stream(
        self,
        callback,
        consumer_group: str = "log_service",
        consumer_name: str = "default",
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Subscribe to log stream updates."""
        try:
            return await self.pubsub.subscribe_to_logs(
                callback, consumer_group, consumer_name, filters
            )
        except Exception as e:
            logger.error(f"Failed to subscribe to log stream: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for log service."""
        try:
            pubsub_health = await self.pubsub.health_check()
            
            # Check database connectivity
            db_health = {"status": "unknown"}
            try:
                async with get_session_context() as session:
                    from sqlalchemy import text
                    await session.execute(text("SELECT 1"))
                    db_health = {"status": "connected"}
            except Exception as e:
                db_health = {"status": "error", "error": str(e)}
            
            return {
                "status": "healthy" if pubsub_health["status"] == "connected" and db_health["status"] == "connected" else "degraded",
                "pubsub": pubsub_health,
                "database": db_health,
                "websocket_connections": len(self.websocket_manager.active_connections)
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}


# Convenience functions for easy logging
async def log_info(task_id: UUID, agent_id: UUID, message: str, context: Optional[Dict[str, Any]] = None):
    """Log info message."""
    service = LogService()
    return await service.log_message(task_id, agent_id, LogLevel.INFO, message, context)


async def log_error(task_id: UUID, agent_id: UUID, message: str, context: Optional[Dict[str, Any]] = None):
    """Log error message."""
    service = LogService()
    return await service.log_message(task_id, agent_id, LogLevel.ERROR, message, context)


async def log_warning(task_id: UUID, agent_id: UUID, message: str, context: Optional[Dict[str, Any]] = None):
    """Log warning message."""
    service = LogService()
    return await service.log_message(task_id, agent_id, LogLevel.WARNING, message, context)


async def log_debug(task_id: UUID, agent_id: UUID, message: str, context: Optional[Dict[str, Any]] = None):
    """Log debug message."""
    service = LogService()
    return await service.log_message(task_id, agent_id, LogLevel.DEBUG, message, context)


# Global instance
log_service = LogService()
import asyncio
import json
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import redis.asyncio as redis
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("pubsub")


class RedisPubSubService:
    """Redis Streams-based pub/sub service for real-time log streaming."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.consumer_tasks: Dict[str, asyncio.Task] = {}
        self.stream_name = settings.log_stream_name
        self.max_len = settings.log_stream_max_len
        self._running = False
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis")
            self._running = True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        self._running = False
        
        # Cancel all consumer tasks
        for task in self.consumer_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks.values(), return_exceptions=True)
        
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def publish_log(self, log_data: Dict[str, Any]) -> str:
        """Publish a log message to Redis Stream."""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            # Add timestamp if not present
            if "timestamp" not in log_data:
                log_data["timestamp"] = datetime.utcnow().isoformat()
            
            # Generate unique stream ID
            stream_id = await self.redis.xadd(
                name=self.stream_name,
                fields=log_data,
                maxlen=self.max_len,
                approximate=True
            )
            
            logger.debug(f"Published log to stream {self.stream_name}: {stream_id}")
            return stream_id
            
        except Exception as e:
            logger.error(f"Failed to publish log: {e}")
            raise
    
    async def subscribe_to_logs(
        self,
        callback: Callable[[Dict[str, Any]], None],
        consumer_group: str = "default",
        consumer_name: str = "worker",
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Subscribe to log stream with optional filters."""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        
        consumer_id = f"{consumer_group}_{consumer_name}"
        
        try:
            # Create consumer group if it doesn't exist
            try:
                await self.redis.xgroup_create(
                    name=self.stream_name,
                    groupname=consumer_group,
                    id="0",
                    mkstream=True
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            
            # Start consumer task
            task = asyncio.create_task(
                self._consume_logs(callback, consumer_group, consumer_name, filters)
            )
            self.consumer_tasks[consumer_id] = task
            
            logger.info(f"Started log consumer: {consumer_id}")
            return consumer_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to logs: {e}")
            raise
    
    async def _consume_logs(
        self,
        callback: Callable[[Dict[str, Any]], None],
        consumer_group: str,
        consumer_name: str,
        filters: Optional[Dict[str, Any]] = None
    ):
        """Internal method to consume logs from stream."""
        while self._running:
            try:
                # Read from stream
                messages = await self.redis.xreadgroup(
                    groupname=consumer_group,
                    consumername=consumer_name,
                    streams={self.stream_name: ">"},
                    count=10,
                    block=1000  # Block for 1 second
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        try:
                            # Apply filters if provided
                            if filters and not self._matches_filters(fields, filters):
                                # Acknowledge message even if filtered
                                await self.redis.xack(self.stream_name, consumer_group, msg_id)
                                continue
                            
                            # Add stream_id to message
                            fields["stream_id"] = msg_id
                            
                            # Call callback
                            await callback(fields)
                            
                            # Acknowledge message
                            await self.redis.xack(self.stream_name, consumer_group, msg_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing message {msg_id}: {e}")
                            # Still acknowledge to prevent redelivery
                            await self.redis.xack(self.stream_name, consumer_group, msg_id)
            
            except asyncio.CancelledError:
                logger.info(f"Consumer cancelled: {consumer_group}_{consumer_name}")
                break
            except Exception as e:
                logger.error(f"Error in log consumer: {e}")
                await asyncio.sleep(1)  # Backoff on error
    
    def _matches_filters(self, message: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if message matches the provided filters."""
        for key, value in filters.items():
            if key not in message:
                return False
            
            # Support multiple filter types
            if isinstance(value, list):
                if message[key] not in value:
                    return False
            elif message[key] != value:
                return False
        
        return True
    
    async def get_log_history(
        self,
        start_id: str = "-",
        end_id: str = "+",
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical logs from stream."""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            messages = await self.redis.xrange(
                name=self.stream_name,
                min=start_id,
                max=end_id,
                count=count
            )
            
            result = []
            for msg_id, fields in messages:
                fields["stream_id"] = msg_id
                result.append(fields)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get log history: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health."""
        if not self.redis:
            return {"status": "disconnected", "error": "No Redis connection"}
        
        try:
            await self.redis.ping()
            
            # Get stream info
            try:
                info = await self.redis.xinfo_stream(self.stream_name)
                stream_length = info.get("length", 0)
            except:
                stream_length = 0
            
            return {
                "status": "connected",
                "stream_name": self.stream_name,
                "stream_length": stream_length,
                "active_consumers": len(self.consumer_tasks)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global instance
pubsub_service = RedisPubSubService()
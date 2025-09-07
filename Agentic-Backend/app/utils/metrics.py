from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from typing import Dict, Any
import time

# Create a custom registry for better control
registry = CollectorRegistry()

# Define metrics
task_counter = Counter(
    'agent_tasks_total',
    'Total number of agent tasks',
    ['agent_id', 'status'],
    registry=registry
)

task_duration = Histogram(
    'agent_task_duration_seconds',
    'Time spent on agent tasks',
    ['agent_id'],
    registry=registry
)

active_tasks = Gauge(
    'agent_active_tasks',
    'Number of currently active tasks',
    ['agent_id'],
    registry=registry
)

api_requests = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

websocket_connections = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections',
    ['endpoint'],
    registry=registry
)

log_messages = Counter(
    'log_messages_total',
    'Total log messages by level',
    ['level', 'source'],
    registry=registry
)

redis_operations = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status'],
    registry=registry
)


class MetricsCollector:
    """Helper class for collecting application metrics."""
    
    @staticmethod
    def increment_task_counter(agent_id: str, status: str):
        """Increment task counter."""
        task_counter.labels(agent_id=agent_id, status=status).inc()
    
    @staticmethod
    def record_task_duration(agent_id: str, duration: float):
        """Record task duration."""
        task_duration.labels(agent_id=agent_id).observe(duration)
    
    @staticmethod
    def set_active_tasks(agent_id: str, count: int):
        """Set active tasks gauge."""
        active_tasks.labels(agent_id=agent_id).set(count)
    
    @staticmethod
    def increment_api_requests(method: str, endpoint: str, status_code: int):
        """Increment API request counter."""
        api_requests.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    
    @staticmethod
    def increment_websocket_connections(endpoint: str, delta: int = 1):
        """Increment/decrement WebSocket connections."""
        websocket_connections.labels(endpoint=endpoint).inc(delta)
    
    @staticmethod
    def increment_log_messages(level: str, source: str = "app"):
        """Increment log message counter."""
        log_messages.labels(level=level, source=source).inc()
    
    @staticmethod
    def increment_redis_operations(operation: str, status: str = "success"):
        """Increment Redis operation counter."""
        redis_operations.labels(operation=operation, status=status).inc()


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, metric_func, *args, **kwargs):
        self.metric_func = metric_func
        self.args = args
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.metric_func(duration, *self.args, **self.kwargs)
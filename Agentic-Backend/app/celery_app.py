from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "agentic-backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.agent_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_timeout,
    task_soft_time_limit=settings.celery_task_timeout - 30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_routes={
        "app.tasks.agent_tasks.*": {"queue": "agent_tasks"},
    },
    task_annotations={
        "app.tasks.agent_tasks.*": {"rate_limit": "100/m"},
    },
    result_expires=3600,  # 1 hour
)

# Task retry configuration
celery_app.conf.task_default_retry_delay = 60  # 1 minute
celery_app.conf.task_max_retries = 3

if __name__ == "__main__":
    celery_app.start()
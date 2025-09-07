#!/usr/bin/env python3
"""
Celery worker startup script with enhanced configuration.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.utils.logging import setup_logging, get_logger
from app.celery_app import celery_app

# Setup logging
setup_logging()
logger = get_logger("celery_worker")


def main():
    """Main worker function."""
    logger.info(f"Starting Celery worker for {settings.app_name}")
    logger.info(f"Broker URL: {settings.celery_broker_url}")
    logger.info(f"Result backend: {settings.celery_result_backend}")
    
    # Configure worker arguments
    worker_args = [
        "worker",
        f"--loglevel={settings.log_level.lower()}",
        f"--concurrency={settings.celery_worker_concurrency}",
        "--prefetch-multiplier=1",
        "--max-tasks-per-child=1000",
        "--time-limit=600",  # 10 minutes hard limit
        "--soft-time-limit=570",  # 9.5 minutes soft limit
        "--without-heartbeat",
        "--without-mingle",
        "--without-gossip",
    ]
    
    # Add queues if specified
    worker_args.extend(["--queues=agent_tasks,celery"])
    
    # Start the worker
    try:
        celery_app.worker_main(argv=worker_args)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
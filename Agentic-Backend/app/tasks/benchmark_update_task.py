"""
Scheduled task to update model benchmarks
"""
from app.services.model_registry_service import model_registry_service
from app.utils.logging import get_logger
import asyncio

logger = get_logger("benchmark_update")

async def update_model_benchmarks():
    """Update model benchmarks - run nightly at 2AM."""
    try:
        logger.info("Starting scheduled benchmark update")

        # Force refresh benchmark data (this will fetch from Hugging Face and store in DB)
        benchmarks = await model_registry_service.get_model_benchmarks(force_refresh=True)

        logger.info(f"Updated benchmarks for {len(benchmarks)} models")

        # Log any new high-performing models
        top_models = sorted(benchmarks.items(), key=lambda x: x[1].get('average_score', 0), reverse=True)[:5]
        logger.info(f"Top 5 models by benchmark: {[name for name, _ in top_models]}")

        # Cleanup old benchmark data (older than 30 days)
        await model_registry_service.cleanup_old_benchmarks(days_old=30)

    except Exception as e:
        logger.error(f"Benchmark update failed: {e}")
        raise

# Celery task wrapper
def scheduled_benchmark_update():
    """Celery task for benchmark updates."""
    asyncio.run(update_model_benchmarks())
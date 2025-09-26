"""
Email Synchronization Celery Tasks

Provides background tasks for automated email synchronization and scheduling.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from celery import Task
from celery.exceptions import Retry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.celery_app import celery_app
from app.db.database import get_session_context
from app.services.email_sync_service import email_sync_service
from app.services.email_connectors.base_connector import SyncType
from app.utils.logging import get_logger
from app.db.models.email import EmailAccount

logger = get_logger("email_sync_tasks")


class EmailSyncTask(Task):
    """Base class for email sync tasks with error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Email sync task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Email sync task {task_id} completed successfully")


@celery_app.task(base=EmailSyncTask, bind=True, max_retries=3, default_retry_delay=300)
def periodic_sync_scheduler(self):
    """
    Periodic task that schedules email synchronization for all auto-sync enabled accounts.

    This task runs every 5 minutes and checks which accounts need synchronization
    based on their sync intervals and last sync times.
    """
    try:
        return asyncio.run(_periodic_sync_scheduler_async())
    except Exception as exc:
        logger.error(f"Periodic sync scheduler failed: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying periodic sync scheduler, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60, exc=exc)
        raise


async def _periodic_sync_scheduler_async():
    """Async implementation of periodic sync scheduler."""
    logger.info("Running periodic email sync scheduler")

    try:
        async with get_session_context() as db:
            # Get all accounts with auto-sync enabled
            query = select(EmailAccount).where(
                EmailAccount.auto_sync_enabled == True
            )
            result = await db.execute(query)
            accounts = result.scalars().all()

            scheduled_count = 0
            now = datetime.now(timezone.utc)

            for account in accounts:
                try:
                    # Check if account needs sync
                    needs_sync = False

                    # If never synced, sync now
                    if account.last_sync_at is None:
                        needs_sync = True
                        logger.info(f"Account {account.id} has never been synced, scheduling sync")
                    else:
                        # Calculate time since last sync
                        last_sync = account.last_sync_at
                        if last_sync.tzinfo is None:
                            last_sync = last_sync.replace(tzinfo=timezone.utc)

                        time_since_sync = now - last_sync
                        sync_interval = timedelta(minutes=account.sync_interval_minutes)

                        if time_since_sync >= sync_interval:
                            needs_sync = True
                            logger.info(f"Account {account.id} needs sync (last: {last_sync}, interval: {account.sync_interval_minutes}m)")

                    if needs_sync:
                        # Schedule the sync as a background task
                        sync_single_account.delay(str(account.id), "incremental")
                        scheduled_count += 1

                        # Update next_sync_at
                        next_sync = now + timedelta(minutes=account.sync_interval_minutes)
                        await db.execute(
                            update(EmailAccount)
                            .where(EmailAccount.id == account.id)
                            .values(next_sync_at=next_sync)
                        )

                except Exception as e:
                    logger.error(f"Error processing account {account.id}: {e}")
                    continue

            await db.commit()
            logger.info(f"Scheduled {scheduled_count} email sync tasks")

        return {"scheduled_count": scheduled_count, "total_accounts": len(accounts)}

    except Exception as e:
        logger.error(f"Error in periodic sync scheduler: {e}")
        raise


@celery_app.task(base=EmailSyncTask, bind=True, max_retries=3, default_retry_delay=300)
def sync_single_account(self, account_id: str, sync_type: str = "incremental", force_sync: bool = False):
    """
    Sync a single email account.

    Args:
        account_id: The email account ID to sync
        sync_type: Type of sync (incremental, full)
        force_sync: Force sync even if recently synced
    """
    try:
        return asyncio.run(_sync_single_account_async(account_id, sync_type, force_sync))
    except Exception as exc:
        logger.error(f"Account sync failed for {account_id}: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying account sync for {account_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=120, exc=exc)
        raise


async def _sync_single_account_async(account_id: str, sync_type: str, force_sync: bool):
    """Async implementation of single account sync."""
    logger.info(f"Starting sync for account {account_id} (type: {sync_type})")

    try:
        # Convert sync type
        sync_enum = SyncType.FULL if sync_type.lower() == "full" else SyncType.INCREMENTAL

        async with get_session_context() as db:
            result = await email_sync_service.sync_account(
                db, account_id, sync_enum, force_sync
            )

        logger.info(f"Completed sync for account {account_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error syncing account {account_id}: {e}")
        raise


@celery_app.task(base=EmailSyncTask, bind=True, max_retries=2, default_retry_delay=600)
def sync_all_user_accounts(self, user_id: int, sync_type: str = "incremental"):
    """
    Sync all accounts for a specific user.

    Args:
        user_id: The user ID whose accounts to sync
        sync_type: Type of sync (incremental, full)
    """
    try:
        return asyncio.run(_sync_all_user_accounts_async(user_id, sync_type))
    except Exception as exc:
        logger.error(f"User account sync failed for user {user_id}: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying user sync for {user_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=300, exc=exc)
        raise


async def _sync_all_user_accounts_async(user_id: int, sync_type: str):
    """Async implementation of user account sync."""
    logger.info(f"Starting sync for all accounts of user {user_id} (type: {sync_type})")

    try:
        # Convert sync type
        sync_enum = SyncType.FULL if sync_type.lower() == "full" else SyncType.INCREMENTAL

        async with get_session_context() as db:
            result = await email_sync_service.sync_all_accounts(
                db, user_id, sync_enum
            )

        logger.info(f"Completed sync for user {user_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error syncing accounts for user {user_id}: {e}")
        raise


@celery_app.task(base=EmailSyncTask, bind=True)
def update_sync_schedules(self):
    """
    Update next_sync_at times for all auto-sync enabled accounts.

    This task recalculates and updates the next sync times based on
    current sync intervals and last sync times.
    """
    try:
        return asyncio.run(_update_sync_schedules_async())
    except Exception as exc:
        logger.error(f"Sync schedule update failed: {exc}")
        raise


async def _update_sync_schedules_async():
    """Async implementation of sync schedule update."""
    logger.info("Updating email sync schedules")

    try:
        async with get_session_context() as db:
            await email_sync_service.schedule_periodic_sync(db)

        logger.info("Email sync schedules updated successfully")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error updating sync schedules: {e}")
        raise
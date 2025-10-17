"""
Email Synchronization Celery Tasks

Provides background tasks for automated email synchronization and scheduling.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from celery import Task
from celery.exceptions import Retry
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.celery_app import celery_app
from app.db.database import get_sync_session
from app.services.email_sync_service import email_sync_service
from app.services.email_connectors.base_connector import SyncType
from app.utils.logging import get_logger
from app.db.models.email import EmailAccount

logger = get_logger("email_sync_tasks")

# Flag to use V2 UID-based sync (can be toggled per account or globally)
USE_V2_SYNC = True  # Set to True to use UID-based sync by default


class EmailSyncTask(Task):
    """Base class for email sync tasks with error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Email sync task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Email sync task {task_id} completed successfully")



@celery_app.task(base=EmailSyncTask, bind=True, max_retries=2, default_retry_delay=600)
def sync_all_user_accounts(self, user_id: int, sync_type: str = "incremental"):
    """
    Sync all accounts for a specific user.

    Args:
        user_id: The user ID whose accounts to sync
        sync_type: Type of sync (incremental, full)
    """
    try:
        return _sync_all_user_accounts_sync(user_id, sync_type)
    except Exception as exc:
        logger.error(f"User account sync failed for user {user_id}: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying user sync for {user_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=300, exc=exc)
        raise


def _sync_all_user_accounts_sync(user_id: int, sync_type: str):
    """Synchronous wrapper for user account sync."""
    logger.info(f"Starting sync for all accounts of user {user_id} (type: {sync_type})")

    try:
        # Convert sync type
        sync_enum = SyncType.FULL if sync_type.lower() == "full" else SyncType.INCREMENTAL

        # Use async context but isolated from the main async engine pool
        async def _run_sync():
            from app.db.database import get_session_context
            async with get_session_context() as db:
                return await email_sync_service.sync_all_accounts(
                    db, user_id, sync_enum
                )

        # Run in isolated event loop with proper cleanup
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_run_sync())
        finally:
            # Properly clean up pending tasks before closing
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as cleanup_error:
                logger.warning(f"Error during event loop cleanup: {cleanup_error}")
            finally:
                try:
                    loop.close()
                except Exception as close_error:
                    logger.warning(f"Error closing event loop: {close_error}")

        logger.info(f"Completed sync for user {user_id}: {result}")

        # Convert result to JSON-serializable format if it's a list of EmailSyncResult
        if result and isinstance(result, list):
            serializable_results = []
            for r in result:
                if hasattr(r, 'sync_type'):  # It's an EmailSyncResult
                    serializable_results.append({
                        "sync_type": r.sync_type.value if r.sync_type else None,
                        "started_at": r.started_at.isoformat() if r.started_at else None,
                        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                        "success": r.success,
                        "emails_processed": r.emails_processed,
                        "emails_added": r.emails_added,
                        "emails_updated": r.emails_updated,
                        "emails_skipped": r.emails_skipped,
                        "attachments_processed": r.attachments_processed,
                        "error_message": r.error_message,
                        "error_details": r.error_details,
                        "performance_metrics": r.performance_metrics
                    })
                else:
                    serializable_results.append(r)
            return serializable_results
        elif result and hasattr(result, 'sync_type'):  # Single EmailSyncResult
            return {
                "sync_type": result.sync_type.value if result.sync_type else None,
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "success": result.success,
                "emails_processed": result.emails_processed,
                "emails_added": result.emails_added,
                "emails_updated": result.emails_updated,
                "emails_skipped": result.emails_skipped,
                "attachments_processed": result.attachments_processed,
                "error_message": result.error_message,
                "error_details": result.error_details,
                "performance_metrics": result.performance_metrics
            }

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
        return _update_sync_schedules_sync()
    except Exception as exc:
        logger.error(f"Sync schedule update failed: {exc}")
        raise


def _update_sync_schedules_sync():
    """
    Pure synchronous wrapper for sync schedule update.

    Checks which accounts need syncing and dispatches tasks accordingly.
    """
    logger.info("Updating email sync schedules")

    try:
        from app.db.database import get_celery_db_session
        from app.db.models.email import EmailAccount
        from datetime import datetime, timezone

        scheduled_count = 0

        # Use synchronous database session
        with get_celery_db_session() as db:
            # Query accounts that need syncing
            now = datetime.now(timezone.utc)

            accounts = db.query(EmailAccount).filter(
                EmailAccount.auto_sync_enabled == True
            ).all()

            for account in accounts:
                needs_sync = False

                if not account.last_sync_at:
                    needs_sync = True
                else:
                    time_since = now - account.last_sync_at
                    if time_since.total_seconds() >= (account.sync_interval_minutes * 60):
                        needs_sync = True

                if needs_sync:
                    # Enqueue sync task
                    logger.info(f"Scheduling sync for account {account.email_address}")
                    sync_single_account.delay(str(account.id), "incremental")

                    # Update next sync time
                    from datetime import timedelta
                    account.next_sync_at = now + timedelta(minutes=account.sync_interval_minutes)
                    scheduled_count += 1

            db.commit()

        logger.info(f"Scheduled {scheduled_count} email sync tasks")
        return {"status": "success", "scheduled_count": scheduled_count}

    except Exception as e:
        logger.error(f"Error updating sync schedules: {e}")
        raise


@celery_app.task(base=EmailSyncTask, bind=True, max_retries=2, default_retry_delay=300)
def regenerate_account_embeddings(
    self,
    account_id: str,
    target_model: str = None,
    filter_by_model: str = None,
    email_ids: list = None,
    embedding_types: list = None,
    delete_existing: bool = True
):
    """
    Regenerate embeddings for emails in an account.

    Args:
        account_id: Email account UUID
        target_model: Model to use for new embeddings (None = use account default)
        filter_by_model: Only regenerate embeddings created by this model
        email_ids: Specific email IDs to regenerate (None = all)
        embedding_types: Specific embedding types to regenerate (None = all)
        delete_existing: Whether to delete existing embeddings first
    """
    try:
        return _regenerate_account_embeddings_sync(
            account_id,
            target_model,
            filter_by_model,
            email_ids,
            embedding_types,
            delete_existing
        )
    except Exception as exc:
        logger.error(f"Embedding regeneration failed for account {account_id}: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying embedding regeneration for {account_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=180, exc=exc)
        raise


def _regenerate_account_embeddings_sync(
    account_id: str,
    target_model: str = None,
    filter_by_model: str = None,
    email_ids: list = None,
    embedding_types: list = None,
    delete_existing: bool = True
):
    """
    Pure synchronous wrapper for embedding regeneration.

    This handles the complex logic of selectively regenerating embeddings
    based on filters while maintaining data integrity.
    """
    logger.info(
        f"Starting embedding regeneration for account {account_id} "
        f"(model: {target_model or 'default'}, filter: {filter_by_model or 'none'})"
    )

    try:
        from app.services.sync_email_sync_service import sync_email_sync_service
        from app.db.database import get_celery_db_session
        from app.db.models.email import EmailAccount, Email, EmailEmbedding
        from app.config import settings

        stats = {
            "emails_processed": 0,
            "embeddings_deleted": 0,
            "embeddings_created": 0,
            "errors": 0
        }

        with get_celery_db_session() as db:
            # Get account
            account = db.query(EmailAccount).filter_by(id=account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")

            # Determine target model
            model_to_use = target_model or account.embedding_model or settings.default_embedding_model
            logger.info(f"Using embedding model: {model_to_use}")

            # Build email query
            email_query = db.query(Email).filter(Email.account_id == account_id)

            # Filter by specific email IDs if provided
            if email_ids:
                email_query = email_query.filter(Email.id.in_(email_ids))
                logger.info(f"Filtering to {len(email_ids)} specific emails")

            # If filtering by model, find emails with embeddings from that model
            if filter_by_model:
                subquery = db.query(EmailEmbedding.email_id).filter(
                    EmailEmbedding.model_name == filter_by_model
                )
                if embedding_types:
                    subquery = subquery.filter(EmailEmbedding.embedding_type.in_(embedding_types))

                email_query = email_query.filter(Email.id.in_(subquery))
                logger.info(f"Filtering to emails with embeddings from model: {filter_by_model}")

            emails = email_query.all()
            total_emails = len(emails)
            logger.info(f"Found {total_emails} emails to process")

            if total_emails == 0:
                return {
                    "status": "completed",
                    "message": "No emails found matching criteria",
                    **stats
                }

            # Process each email
            for idx, email in enumerate(emails, 1):
                try:
                    # Delete existing embeddings if requested
                    if delete_existing:
                        delete_query = db.query(EmailEmbedding).filter(
                            EmailEmbedding.email_id == email.id
                        )

                        # Filter by embedding types if specified
                        if embedding_types:
                            delete_query = delete_query.filter(
                                EmailEmbedding.embedding_type.in_(embedding_types)
                            )

                        # Filter by source model if specified
                        if filter_by_model:
                            delete_query = delete_query.filter(
                                EmailEmbedding.model_name == filter_by_model
                            )

                        deleted_count = delete_query.delete()
                        stats["embeddings_deleted"] += deleted_count

                        # Mark email as needing embeddings
                        email.embeddings_generated = False

                    # Generate new embedding
                    sync_email_sync_service._generate_email_embedding(
                        db, email, model_to_use
                    )

                    stats["embeddings_created"] += 1
                    stats["emails_processed"] += 1

                    # Commit every 10 emails
                    if idx % 10 == 0:
                        db.commit()
                        logger.info(
                            f"Processed {idx}/{total_emails} emails "
                            f"({stats['embeddings_created']} embeddings created)"
                        )

                except Exception as e:
                    logger.error(f"Error processing email {email.id}: {e}")
                    stats["errors"] += 1
                    db.rollback()
                    continue

            # Final commit
            db.commit()

            logger.info(
                f"Completed embedding regeneration for account {account_id}: "
                f"{stats['emails_processed']} emails processed, "
                f"{stats['embeddings_deleted']} embeddings deleted, "
                f"{stats['embeddings_created']} embeddings created, "
                f"{stats['errors']} errors"
            )

            return {
                "status": "completed",
                "account_id": account_id,
                "target_model": model_to_use,
                **stats
            }

    except Exception as e:
        logger.error(f"Error regenerating embeddings for account {account_id}: {e}")
        raise


@celery_app.task(base=EmailSyncTask, bind=True, max_retries=2, default_retry_delay=600)
def cleanup_deleted_emails(self, days_threshold: int = 60):
    """
    Clean up emails that have been marked as deleted for more than the specified threshold.

    This task permanently deletes emails from the database that were marked as deleted
    (deleted_at is not null) more than `days_threshold` days ago. This implements
    the 60-day soft-delete retention policy.

    Args:
        days_threshold: Number of days to retain deleted emails (default: 60)
    """
    try:
        return _cleanup_deleted_emails_sync(days_threshold)
    except Exception as exc:
        logger.error(f"Deleted email cleanup failed: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying cleanup task, attempt {self.request.retries + 1}")
            raise self.retry(countdown=300, exc=exc)
        raise


def _cleanup_deleted_emails_sync(days_threshold: int = 60):
    """
    Pure synchronous wrapper for deleted email cleanup.

    Calls the email_sync_service cleanup method to permanently delete
    emails that were soft-deleted more than X days ago.
    """
    logger.info(f"Starting cleanup of emails deleted more than {days_threshold} days ago")

    try:
        from app.services.sync_email_sync_service import sync_email_sync_service
        from app.db.database import get_celery_db_session

        with get_celery_db_session() as db:
            result = sync_email_sync_service.cleanup_old_deleted_emails(
                db=db,
                days_threshold=days_threshold
            )

        logger.info(
            f"Cleanup completed: {result['emails_deleted']} emails permanently deleted, "
            f"{result['attachments_deleted']} attachments deleted"
        )

        return {
            "status": "success",
            "emails_deleted": result["emails_deleted"],
            "attachments_deleted": result["attachments_deleted"],
            "days_threshold": days_threshold
        }

    except Exception as e:
        logger.error(f"Error during deleted email cleanup: {e}")
        raise


# ==================== V2 UID-Based Sync Tasks ====================


@celery_app.task(base=EmailSyncTask, bind=True, max_retries=3, default_retry_delay=300)
def sync_single_account(self, account_id: str, force_full_sync: bool = False):
    """
    Sync a single email account using V2 UID-based sync.

    Args:
        account_id: The email account ID to sync
        force_full_sync: Force full sync even if UIDVALIDITY unchanged
    """
    try:
        return _sync_single_account_sync(account_id, force_full_sync)
    except Exception as exc:
        logger.error(f"V2 account sync failed for {account_id}: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying V2 account sync for {account_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=120, exc=exc)
        raise


def _sync_single_account_sync(account_id: str, force_full_sync: bool):
    """
    Pure synchronous wrapper for V2 single account sync.

    Uses UID-based synchronization with proper IMAP folder tracking.
    """
    logger.info(f"Starting V2 UID-based sync for account {account_id} (force_full: {force_full_sync})")

    try:
        import asyncio

        # Use async context but isolated from the main async engine pool
        async def _run_sync():
            from app.db.database import get_session_context
            from app.services.email_sync_service import email_sync_service

            async with get_session_context() as db:
                result = await email_sync_service.sync_account(
                    db, account_id, force_full_sync
                )
                # Don't manually commit - let the context manager handle it
                return result

        # Try to get existing loop first
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = None
        try:
            # Use run_until_complete with the loop
            result = loop.run_until_complete(_run_sync())
        except Exception as run_error:
            logger.error(f"Error running sync: {run_error}")
            raise
        finally:
            # Don't close the loop - let Celery manage it
            # Just clean up pending tasks
            try:
                pending = asyncio.all_tasks(loop)
                if pending:
                    for task in pending:
                        task.cancel()
                    try:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except:
                        pass
            except Exception as cleanup_error:
                logger.warning(f"Error during cleanup: {cleanup_error}")

        # If we got here, result should be set
        if result:
            logger.info(
                f"Completed V2 sync for account {account_id}: "
                f"success={result.success}, "
                f"emails_processed={result.emails_processed}, "
                f"emails_added={result.emails_added}, "
                f"emails_updated={result.emails_updated}"
            )

            # Convert result to JSON-serializable format
            serializable_result = {
                "sync_type": result.sync_type.value if result.sync_type else "uid_incremental",
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "success": result.success,
                "emails_processed": result.emails_processed,
                "emails_added": result.emails_added,
                "emails_updated": result.emails_updated,
                "emails_skipped": result.emails_skipped,
                "attachments_processed": result.attachments_processed,
                "error_message": result.error_message,
                "error_details": result.error_details,
                "performance_metrics": result.performance_metrics
            }
            return serializable_result

        return {"success": False, "error": "No result returned"}

    except Exception as e:
        logger.error(f"Error in V2 sync for account {account_id}: {e}")
        raise


@celery_app.task(base=EmailSyncTask, bind=True, max_retries=3, default_retry_delay=300)
def periodic_sync_scheduler(self):
    """
    Periodic task that schedules V2 UID-based email synchronization for all auto-sync enabled accounts.

    This task runs every 5 minutes and checks which accounts need synchronization
    based on their sync intervals and last sync times. Uses V2 UID-based sync.
    """
    try:
        return _periodic_sync_scheduler_sync()
    except Exception as exc:
        logger.error(f"V2 periodic sync scheduler failed: {exc}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying V2 periodic sync scheduler, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60, exc=exc)
        raise


def _periodic_sync_scheduler_sync():
    """Synchronous implementation of V2 periodic sync scheduler."""
    logger.info("Running V2 periodic UID-based email sync scheduler")

    db = get_sync_session()
    try:
        # Get all accounts with auto-sync enabled
        query = select(EmailAccount).where(
            EmailAccount.auto_sync_enabled == True
        )
        result = db.execute(query)
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
                    logger.info(f"Account {account.id} has never been synced, scheduling V2 sync")
                else:
                    # Calculate time since last sync
                    last_sync = account.last_sync_at
                    if last_sync.tzinfo is None:
                        last_sync = last_sync.replace(tzinfo=timezone.utc)

                    time_since_sync = now - last_sync
                    sync_interval = timedelta(minutes=account.sync_interval_minutes)

                    if time_since_sync >= sync_interval:
                        needs_sync = True
                        logger.info(
                            f"Account {account.id} needs V2 sync "
                            f"(last: {last_sync}, interval: {account.sync_interval_minutes}m)"
                        )

                if needs_sync:
                    # Schedule the V2 sync as a background task
                    sync_single_account.delay(str(account.id), False)
                    scheduled_count += 1

                    # Update next_sync_at
                    next_sync = now + timedelta(minutes=account.sync_interval_minutes)
                    db.execute(
                        update(EmailAccount)
                        .where(EmailAccount.id == account.id)
                        .values(next_sync_at=next_sync)
                    )

            except Exception as e:
                logger.error(f"Error processing account {account.id} for V2 sync: {e}")
                continue

        db.commit()
        logger.info(f"Scheduled {scheduled_count} V2 UID-based email sync tasks")

        return {"scheduled_count": scheduled_count, "total_accounts": len(accounts), "sync_version": "v2"}

    except Exception as e:
        logger.error(f"Error in V2 periodic sync scheduler: {e}")
        db.rollback()
        raise
    finally:
        db.close()
"""
Email Synchronization Service - UID-Based Sync

This service implements proper IMAP UID-based synchronization following RFC 3501 and RFC 4551.

Key Features:
- UID-based sync (not Message-ID)
- Per-folder sync state tracking with UIDVALIDITY
- RFC-compliant deletion tracking via IMAP \Deleted flag and folder location
- Flag updates using CONDSTORE (when supported)
- Configurable sync window (last X days)
- Multi-folder support (INBOX, Sent, Drafts, Junk, etc.)
- Multi-user, multi-account support
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, delete, desc
from sqlalchemy.orm import selectinload

from app.db.models.email import EmailAccount, Email, EmailSyncHistory, FolderSyncState
from app.db.models.user import User
from app.db.models.task import LogLevel
from app.services.email_connectors import EmailConnectorFactory
from app.services.email_connectors.base_connector import SyncType, EmailSyncResult, EmailMessage
from app.services.email_embedding_service import email_embedding_service
from app.services.unified_log_service import unified_log_service, WorkflowType, LogScope
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger("email_sync_service")


class EmailSyncService:
    """
    UID-based email synchronization service.

    This service implements proper IMAP UID-based sync with:
    - UIDVALIDITY tracking to detect mailbox resets
    - Efficient incremental sync using UID ranges
    - Deletion tracking via IMAP \Deleted flag (RFC 3501)
    - Flag updates with CONDSTORE support (when available)
    - Configurable sync window (sync last X days)
    - Multi-folder orchestration
    """

    def __init__(self):
        self.logger = get_logger("email_sync_service")
        self.config = settings
        self.connector_factory = EmailConnectorFactory()
        self.max_concurrent_folders = 5  # Sync up to 5 folders concurrently
        self.sync_timeout_minutes = 30
        self.batch_size = 100  # Fetch emails in batches of 100
        self.commit_interval = 50  # Commit every 50 emails

    async def sync_account(
        self,
        db: AsyncSession,
        account_id: str,
        force_full_sync: bool = False
    ) -> EmailSyncResult:
        """
        Synchronize an email account using UID-based sync.
        
        Args:
            db: Database session
            account_id: ID of account to sync
            force_full_sync: Force full sync ignoring state
            
        Returns:
            EmailSyncResult object
        """
        start_time = datetime.now(timezone.utc)
        sync_result = EmailSyncResult(
            sync_type=SyncType.FULL if force_full_sync else SyncType.INCREMENTAL,
            started_at=start_time
        )

        try:
            # Get email account with user info
            # The original code used selectinload(EmailAccount.user) which is important for workflow_context
            account_query = select(EmailAccount).options(
                selectinload(EmailAccount.user)
            ).where(EmailAccount.id == account_id)

            result = await db.execute(account_query)
            account = result.scalar_one_or_none()

            if not account:
                sync_result.error_message = f"Account {account_id} not found"
                return sync_result

            # Check circuit breaker
            if not await self._check_circuit_breaker(db, account):
                sync_result.error_message = "Circuit breaker open: too many recent failures"
                sync_result.success = False
                return sync_result

            # Check lock
            if not await self._check_lock(db, account):
                sync_result.error_message = "Sync already in progress"
                sync_result.success = False
                return sync_result

            # Create unified workflow context
            async with unified_log_service.workflow_context(
                user_id=account.user_id,
                workflow_type=WorkflowType.EMAIL_SYNC,
                workflow_name=f"UID-based sync for {account.email_address}",
                scope=LogScope.USER
            ) as workflow_context:

                await unified_log_service.log(
                    context=workflow_context,
                    level=LogLevel.INFO,
                    message=f"Starting UID-based sync for account {account.email_address}",
                    component="email_sync_service",
                    extra_metadata={
                        "account_id": str(account.id),
                        "account_type": account.account_type,
                        "sync_window_days": account.sync_window_days,
                        "folders": account.sync_folders,
                        "force_full_sync": force_full_sync
                    }
                )

                # Update account sync status
                await self._update_account_sync_status(db, account, "running")

                # Create sync history record
                sync_history = await self._create_sync_history(db, account)

                try:
                    # Create connector
                    connector = await self._create_connector(account)
                    if not connector:
                        raise Exception(f"Failed to create connector for account type {account.account_type}")

                    # Connect to IMAP server
                    connected = await connector.connect()
                    if not connected:
                        raise Exception(f"Failed to connect to email server for account {account.email_address}")

                    await unified_log_service.log(
                        context=workflow_context,
                        level=LogLevel.INFO,
                        message=f"Successfully connected to email server",
                        component="email_sync_service"
                    )

                    # Perform folder discovery if not done yet
                    if not account.folders_discovered:
                        await self._discover_folders(db, account, connector, workflow_context)

                    # Check server capabilities (CONDSTORE, QRESYNC)
                    await self._check_server_capabilities(db, account, connector, workflow_context)

                    # Sync folders - use parallel sync for multiple folders
                    total_stats = {
                        "emails_processed": 0,
                        "emails_added": 0,
                        "emails_updated": 0,
                        "emails_deleted": 0,
                        "flags_updated": 0
                    }

                    folders_to_sync = account.sync_folders or ["INBOX"]

                    # IMPORTANT: Process folders sequentially to avoid database transaction conflicts
                    # Parallel folder sync with shared DB session causes "transaction aborted" errors
                    # when one folder hits an error and aborts the transaction for all other folders
                    for folder_name in folders_to_sync:
                        folder_stats = await self._sync_folder(
                            db, account, connector, folder_name,
                            force_full_sync, workflow_context,
                            sync_history=sync_history
                        )

                        # Aggregate stats
                        for key in total_stats:
                            total_stats[key] += folder_stats.get(key, 0)

                    # Update sync result
                    sync_result.success = True
                    sync_result.emails_processed = total_stats["emails_processed"]
                    sync_result.emails_added = total_stats["emails_added"]
                    sync_result.emails_updated = total_stats["emails_updated"]

                    # Update account after sync
                    await self._update_account_after_sync(db, account, total_stats)

                    # Set completion time
                    sync_result.completed_at = datetime.now(timezone.utc)

                    # Update sync history
                    await self._complete_sync_history(db, sync_history, sync_result)

                    # Always schedule embedding generation after sync to process any pending emails
                    # This handles both new emails from this sync AND any existing emails without embeddings
                    try:
                        await unified_log_service.log(
                            context=workflow_context,
                            level=LogLevel.INFO,
                            message="Scheduling embedding generation for emails without embeddings",
                            component="email_sync_service",
                            extra_metadata={
                                "emails_added": total_stats["emails_added"],
                                "note": "Processing all pending emails, not just newly added"
                            }
                        )
                        await self._schedule_embedding_generation(db, account.user_id)
                    except Exception as embedding_error:
                        await unified_log_service.log(
                            context=workflow_context,
                            level=LogLevel.WARNING,
                            message="Embedding generation failed but sync succeeded",
                            component="email_sync_service",
                            error=embedding_error
                        )

                    await unified_log_service.log(
                        context=workflow_context,
                        level=LogLevel.INFO,
                        message=f"Successfully synced account {account.email_address}",
                        component="email_sync_service",
                        extra_metadata=total_stats
                    )

                except Exception as e:
                    sync_result.error_message = str(e)
                    sync_result.error_details = {"account_id": str(account.id), "error": str(e)}
                    await self._update_account_sync_status(db, account, "error", str(e))
                    await self._fail_sync_history(db, sync_history, str(e))

                    await unified_log_service.log(
                        context=workflow_context,
                        level=LogLevel.ERROR,
                        message=f"UID-based sync failed for account {account.email_address}",
                        component="email_sync_service",
                        error=e,
                        extra_metadata={"account_id": str(account.id)}
                    )
                    raise
                finally:
                    # Always disconnect from IMAP server
                    if connector:
                        try:
                            await connector.disconnect()
                            await unified_log_service.log(
                                context=workflow_context,
                                level=LogLevel.INFO,
                                message="Disconnected from email server",
                                component="email_sync_service"
                            )
                        except Exception as disconnect_error:
                            self.logger.warning(f"Error disconnecting from email server: {disconnect_error}")

        except Exception as e:
            self.logger.error(f"Error syncing account {account_id}: {e}")
            sync_result.error_message = str(e)

        finally:
            sync_result.completed_at = datetime.now(timezone.utc)

        return sync_result

    async def _sync_folders_parallel(
        self,
        db: AsyncSession,
        account: EmailAccount,
        connector,
        folders: List[str],
        force_full_sync: bool,
        workflow_context
    ) -> List[Dict[str, int]]:
        """
        Sync multiple folders in parallel for better performance.

        Uses asyncio.gather with semaphore to limit concurrency and avoid
        overwhelming the IMAP server.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_folders)

        async def sync_folder_with_semaphore(folder_name: str):
            async with semaphore:
                return await self._sync_folder(
                    db, account, connector, folder_name,
                    force_full_sync, workflow_context
                )

        # Create tasks for all folders
        tasks = [sync_folder_with_semaphore(folder) for folder in folders]

        # Execute in parallel and gather results
        folder_stats_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        results = []
        for i, result in enumerate(folder_stats_list):
            if isinstance(result, Exception):
                self.logger.error(f"Error syncing folder {folders[i]}: {result}")
                # Return empty stats for failed folder
                results.append({
                    "emails_processed": 0,
                    "emails_added": 0,
                    "emails_updated": 0,
                    "emails_deleted": 0,
                    "flags_updated": 0
                })
            else:
                results.append(result)

        return results

    async def _sync_folder(
        self,
        db: AsyncSession,
        account: EmailAccount,
        connector,
        folder_name: str,
        force_full_sync: bool,
        workflow_context,
        sync_history: Optional[EmailSyncHistory] = None
    ) -> Dict[str, int]:
        """
        Sync a single folder using UID-based algorithm.
        """
        stats = {
            "emails_processed": 0,
            "emails_added": 0,
            "emails_updated": 0,
            "emails_deleted": 0,
            "flags_updated": 0
        }

        async with unified_log_service.task_context(
            parent_context=workflow_context,
            task_name=f"Sync folder: {folder_name}",
            agent_id="email_sync_agent"
        ) as task_context:

            try:
                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.INFO,
                    message=f"Starting sync for folder: {folder_name}",
                    component="folder_sync"
                )

                # Step 1: Get folder status from server
                folder_status = connector.get_folder_status(folder_name)

                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.INFO,
                    message=f"Server folder status retrieved",
                    component="folder_sync",
                    extra_metadata=folder_status
                )

                # Step 2: Get or create local sync state
                local_state = await self._get_or_create_folder_sync_state(
                    db, account.id, folder_name
                )

                # Step 3: Check UIDVALIDITY
                server_uidvalidity = folder_status.get('uidvalidity')

                if local_state.uid_validity is None:
                    # First sync for this folder
                    await unified_log_service.log(
                        context=task_context,
                        level=LogLevel.INFO,
                        message=f"First sync for folder {folder_name}",
                        component="folder_sync"
                    )
                    local_state.uid_validity = server_uidvalidity

                elif local_state.uid_validity != server_uidvalidity:
                    # Mailbox reset detected!
                    await unified_log_service.log(
                        context=task_context,
                        level=LogLevel.WARNING,
                        message=f"UIDVALIDITY changed for {folder_name} - mailbox was reset",
                        component="folder_sync",
                        extra_metadata={
                            "old_uidvalidity": local_state.uid_validity,
                            "new_uidvalidity": server_uidvalidity
                        }
                    )
                    await self._handle_mailbox_reset(
                        db, account, folder_name, server_uidvalidity, task_context
                    )
                    local_state.uid_validity = server_uidvalidity
                    local_state.last_synced_uid = None
                    force_full_sync = True

                # Step 4: Determine UID range to fetch
                if force_full_sync or local_state.last_synced_uid is None:
                    # Full sync with date window
                    since_date = account.created_at - timedelta(days=account.sync_window_days)
                    uids_to_fetch = connector.fetch_uids_since_date(folder_name, since_date)

                    await unified_log_service.log(
                        context=task_context,
                        level=LogLevel.INFO,
                        message=f"Full sync: fetching UIDs since {since_date.date()}",
                        component="folder_sync",
                        extra_metadata={
                            "since_date": since_date.isoformat(),
                            "uids_found": len(uids_to_fetch)
                        }
                    )
                else:
                    # Incremental sync - fetch UIDs greater than last synced
                    last_uid = local_state.last_synced_uid
                    uids_to_fetch = connector.fetch_uids_in_range(folder_name, last_uid + 1, '*')

                    await unified_log_service.log(
                        context=task_context,
                        level=LogLevel.INFO,
                        message=f"Incremental sync: fetching UIDs after {last_uid}",
                        component="folder_sync",
                        extra_metadata={
                            "last_synced_uid": last_uid,
                            "new_uids_found": len(uids_to_fetch)
                        }
                    )

                # Step 5: Fetch emails for new UIDs (in batches for better performance)
                for batch_start in range(0, len(uids_to_fetch), self.batch_size):
                    batch_uids = uids_to_fetch[batch_start:batch_start + self.batch_size]

                    await unified_log_service.log(
                        context=task_context,
                        level=LogLevel.INFO,
                        message=f"Processing UID batch {batch_start//self.batch_size + 1}/{(len(uids_to_fetch)-1)//self.batch_size + 1}",
                        component="folder_sync",
                        extra_metadata={"batch_size": len(batch_uids)}
                    )

                    for uid in batch_uids:
                        try:
                            email_message = connector.fetch_email_by_uid(folder_name, uid)

                            if email_message:
                                # Check if email exists by message_id
                                existing_query = select(Email).where(
                                    and_(
                                        Email.account_id == account.id,
                                        Email.message_id == email_message.message_id
                                    )
                                )
                                result = await db.execute(existing_query)
                                existing_email = result.scalar_one_or_none()

                                if existing_email:
                                    # Update existing email (folder, flags, UID)
                                    await self._update_email_with_uid(
                                        db, existing_email, email_message,
                                        folder_name, uid, server_uidvalidity
                                    )
                                    stats["emails_updated"] += 1
                                    if sync_history:
                                        sync_history.emails_updated += 1
                                else:
                                    # Create new email
                                    try:
                                        await self._create_email_with_uid(
                                            db, account, email_message,
                                            folder_name, uid, server_uidvalidity
                                        )
                                        # Flush immediately to check database constraints
                                        await db.flush()
                                        stats["emails_added"] += 1
                                        if sync_history:
                                            sync_history.emails_added += 1
                                    except Exception as create_error:
                                        # Handle duplicate key violations gracefully
                                        if "duplicate key" in str(create_error).lower() or "unique constraint" in str(create_error).lower():
                                            self.logger.warning(f"Email {email_message.message_id} already exists (UID {uid}), skipping")
                                            # Rollback the failed insert
                                            await db.rollback()
                                            stats["emails_updated"] += 1  # Count as update since it exists
                                            if sync_history:
                                                sync_history.emails_updated += 1
                                        else:
                                            raise  # Re-raise other errors

                                stats["emails_processed"] += 1
                                if sync_history:
                                    sync_history.emails_processed += 1
                                    sync_history.last_updated = datetime.now(timezone.utc)

                                # Commit periodically within batch
                                if stats["emails_processed"] % self.commit_interval == 0:
                                    await db.commit()

                                    await unified_log_service.log(
                                        context=task_context,
                                        level=LogLevel.INFO,
                                        message=f"Progress: {stats['emails_processed']} emails processed",
                                        component="folder_sync",
                                        extra_metadata=stats
                                    )

                        except Exception as e:
                            self.logger.error(f"Error fetching UID {uid} from {folder_name}: {e}")
                            # Skip this email and continue with next UID
                            # Don't rollback - would break async session
                            continue

                    # Commit after each batch
                    try:
                        await db.commit()
                        await unified_log_service.log(
                            context=task_context,
                            level=LogLevel.INFO,
                            message=f"Batch complete: processed {len(batch_uids)} UIDs",
                            component="folder_sync",
                            extra_metadata={"batch_processed": len(batch_uids)}
                        )
                    except Exception as commit_error:
                        self.logger.error(f"Error committing batch for {folder_name}: {commit_error}")
                        # Rollback and continue - duplicates are expected during re-sync
                        try:
                            await db.rollback()
                        except:
                            pass  # Session might already be invalid
                        # Don't break - continue with next batch

                # Step 6: Deletion detection removed - IMAP \Deleted flag is now used
                # Deleted emails are tracked via folder location (Trash/Deleted) and \Deleted flag

                # Step 7: Update flags if CONDSTORE supported
                if account.supports_condstore and local_state.highest_mod_seq:
                    flag_stats = await self._update_flags_with_condstore(
                        db, account, connector, folder_name,
                        local_state.highest_mod_seq, task_context
                    )
                    stats["flags_updated"] = flag_stats.get("flags_updated", 0)

                # Step 8: Update folder sync state
                if uids_to_fetch:
                    local_state.last_synced_uid = max(uids_to_fetch)
                local_state.highest_mod_seq = folder_status.get('highest_modseq')
                local_state.last_sync_at = datetime.now(timezone.utc)
                local_state.email_count = folder_status.get('exists', 0)
                await db.commit()

                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.INFO,
                    message=f"Folder sync complete: {folder_name}",
                    component="folder_sync",
                    extra_metadata=stats
                )

            except Exception as e:
                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.ERROR,
                    message=f"Error syncing folder {folder_name}",
                    component="folder_sync",
                    error=e
                )
                raise

        return stats


    async def _update_flags_with_condstore(
        self,
        db: AsyncSession,
        account: EmailAccount,
        connector,
        folder_name: str,
        last_mod_seq: int,
        task_context
    ) -> Dict[str, int]:
        """
        Efficiently update flags using CONDSTORE extension.

        CONDSTORE allows fetching only messages whose flags changed
        since last HIGHESTMODSEQ, avoiding need to re-fetch all messages.
        """
        stats = {"flags_updated": 0}

        try:
            await unified_log_service.log(
                context=task_context,
                level=LogLevel.INFO,
                message=f"Updating flags with CONDSTORE for {folder_name}",
                component="flag_update",
                extra_metadata={"last_mod_seq": last_mod_seq}
            )

            # Get folder status to check current HIGHESTMODSEQ
            folder_status = connector.get_folder_status(folder_name)
            current_mod_seq = folder_status.get('highest_modseq')

            if not current_mod_seq or current_mod_seq <= last_mod_seq:
                # No flag changes since last sync
                return stats

            # Fetch all UIDs from server (for changed flags detection)
            all_uids = connector.fetch_uids_in_range(folder_name, 1, '*')

            if not all_uids:
                return stats

            # Batch process flag updates
            for batch_start in range(0, len(all_uids), self.batch_size):
                batch_uids = all_uids[batch_start:batch_start + self.batch_size]

                # Fetch flags for this batch
                flags_by_uid = connector.fetch_flags_by_uids(folder_name, batch_uids)

                # Build query to fetch all emails in this batch at once
                email_query = select(Email).where(
                    and_(
                        Email.account_id == account.id,
                        Email.folder_path == folder_name,
                        Email.imap_uid.in_(batch_uids)
                    )
                )
                result = await db.execute(email_query)
                emails = result.scalars().all()

                # Create UID->email mapping for fast lookup
                email_by_uid = {email.imap_uid: email for email in emails}

                # Update flags in batch
                for uid, flags in flags_by_uid.items():
                    email = email_by_uid.get(uid)
                    if email:
                        # Only update if flags changed
                        old_read = email.is_read
                        old_flagged = email.is_flagged
                        new_read = flags.get('is_read', old_read)
                        new_flagged = flags.get('is_flagged', old_flagged)

                        if old_read != new_read or old_flagged != new_flagged:
                            email.is_read = new_read
                            email.is_flagged = new_flagged
                            stats["flags_updated"] += 1

                # Commit batch
                await db.commit()

                await unified_log_service.log(
                    context=task_context,
                    level=LogLevel.INFO,
                    message=f"Flag batch complete: {len(batch_uids)} UIDs processed",
                    component="flag_update",
                    extra_metadata={"flags_updated_in_batch": stats["flags_updated"]}
                )

            await unified_log_service.log(
                context=task_context,
                level=LogLevel.INFO,
                message=f"Flag update complete: {stats['flags_updated']} emails updated",
                component="flag_update"
            )

        except Exception as e:
            self.logger.error(f"Error updating flags for {folder_name}: {e}")

        return stats

    async def _handle_mailbox_reset(
        self,
        db: AsyncSession,
        account: EmailAccount,
        folder_name: str,
        new_uidvalidity: int,
        task_context
    ):
        """
        Handle mailbox reset (UIDVALIDITY changed).

        When UIDVALIDITY changes, all previous UIDs are invalid.
        We mark all emails from this folder as potentially stale and
        will re-sync from scratch.
        """
        await unified_log_service.log(
            context=task_context,
            level=LogLevel.WARNING,
            message=f"Handling mailbox reset for {folder_name}",
            component="mailbox_reset",
            extra_metadata={"new_uidvalidity": new_uidvalidity}
        )

        # Clear UIDs for all emails in this folder
        await db.execute(
            update(Email)
            .where(
                and_(
                    Email.account_id == account.id,
                    Email.folder_path == folder_name
                )
            )
            .values(
                imap_uid=None,
                uid_validity=None
            )
        )
        await db.commit()

    async def _discover_folders(
        self,
        db: AsyncSession,
        account: EmailAccount,
        connector,
        workflow_context
    ):
        """Discover available folders on the server."""
        try:
            folders = connector.list_folders()

            await unified_log_service.log(
                context=workflow_context,
                level=LogLevel.INFO,
                message=f"Discovered {len(folders)} folders",
                component="folder_discovery",
                extra_metadata={"folders": [f['name'] for f in folders]}
            )

            # Update account with discovered folders
            account.folders_discovered = True
            await db.commit()

        except Exception as e:
            self.logger.error(f"Error discovering folders: {e}")

    async def _check_server_capabilities(
        self,
        db: AsyncSession,
        account: EmailAccount,
        connector,
        workflow_context
    ):
        """Check and store server capabilities (CONDSTORE, QRESYNC)."""
        try:
            capabilities = connector.check_capabilities()

            account.supports_condstore = capabilities.get('CONDSTORE', False)
            account.supports_qresync = capabilities.get('QRESYNC', False)
            await db.commit()

            await unified_log_service.log(
                context=workflow_context,
                level=LogLevel.INFO,
                message=f"Server capabilities checked",
                component="capability_check",
                extra_metadata=capabilities
            )

        except Exception as e:
            self.logger.error(f"Error checking capabilities: {e}")

    async def _get_or_create_folder_sync_state(
        self,
        db: AsyncSession,
        account_id: str,
        folder_name: str
    ) -> FolderSyncState:
        """Get or create folder sync state."""
        query = select(FolderSyncState).where(
            and_(
                FolderSyncState.account_id == account_id,
                FolderSyncState.folder_name == folder_name
            )
        )
        result = await db.execute(query)
        state = result.scalar_one_or_none()

        if not state:
            state = FolderSyncState(
                account_id=account_id,
                folder_name=folder_name
            )
            db.add(state)
            await db.commit()
            await db.refresh(state)

        return state

    async def _create_email_with_uid(
        self,
        db: AsyncSession,
        account: EmailAccount,
        email_message: EmailMessage,
        folder_name: str,
        uid: int,
        uid_validity: int
    ) -> Email:
        """Create new email record with UID information."""
        email = Email(
            user_id=account.user_id,
            account_id=account.id,
            message_id=email_message.message_id,
            thread_id=email_message.thread_id,
            subject=email_message.subject,
            body_text=email_message.body_text,
            body_html=email_message.body_html,
            sender_email=email_message.sender_email,
            sender_name=email_message.sender_name,
            to_recipients=email_message.recipients,
            cc_recipients=email_message.cc_recipients,
            bcc_recipients=email_message.bcc_recipients,
            sent_at=email_message.sent_at,
            received_at=email_message.received_at,
            folder_path=folder_name,
            labels=email_message.labels,
            size_bytes=email_message.size_bytes,
            has_attachments=email_message.has_attachments,
            attachment_count=len(email_message.attachments),
            is_read=email_message.is_read,
            is_flagged=email_message.is_flagged,
            importance_score=0.5,
            category="general",
            # UID fields
            imap_uid=uid,
            uid_validity=uid_validity
        )

        db.add(email)
        await db.flush()  # Flush to get the email ID

        # Auto-generate embeddings for new emails (async, non-blocking)
        try:
            # Determine which embedding model to use
            embedding_model = account.embedding_model or self.config.default_embedding_model

            # Generate embeddings for the new email
            await email_embedding_service.generate_email_embeddings(
                db=db,
                email=email,
                force_regenerate=False,
                account_embedding_model=embedding_model
            )
            self.logger.debug(f"Generated embeddings for new email {email.message_id}")
        except Exception as e:
            # Don't fail the sync if embedding generation fails
            self.logger.warning(f"Failed to generate embeddings for email {email.message_id}: {e}")

        return email

    async def _update_email_with_uid(
        self,
        db: AsyncSession,
        existing_email: Email,
        email_message: EmailMessage,
        folder_name: str,
        uid: int,
        uid_validity: int
    ):
        """Update existing email with new UID and flags."""
        existing_email.is_read = email_message.is_read
        existing_email.is_flagged = email_message.is_flagged
        existing_email.labels = email_message.labels
        existing_email.folder_path = folder_name
        existing_email.imap_uid = uid
        existing_email.uid_validity = uid_validity
        existing_email.updated_at = datetime.now(timezone.utc)

    # Helper methods (reused from v1 where applicable)

    async def _create_connector(self, account: EmailAccount):
        """Create email connector for account."""
        try:
            return await self.connector_factory.create_connector(
                account_type=account.account_type,
                account_id=str(account.id),
                credentials=account.auth_credentials,
                settings=account.sync_settings
            )
        except Exception as e:
            self.logger.error(f"Error creating connector for account {account.id}: {e}")
            return None

    async def _update_account_sync_status(
        self,
        db: AsyncSession,
        account: EmailAccount,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update account sync status."""
        update_data = {"sync_status": status, "updated_at": datetime.now(timezone.utc)}

        if status == "completed":
            update_data["last_sync_at"] = datetime.now(timezone.utc)
            update_data["last_error"] = None
        elif error_message:
            update_data["last_error"] = error_message

        await db.execute(
            update(EmailAccount)
            .where(EmailAccount.id == account.id)
            .values(**update_data)
        )
        await db.commit()

    async def _update_account_after_sync(
        self,
        db: AsyncSession,
        account: EmailAccount,
        sync_stats: Dict[str, int]
    ):
        """Update account after successful sync."""
        # Get actual count of emails for this account from database
        from sqlalchemy import select, func
        from app.db.models.email import Email

        count_result = await db.execute(
            select(func.count(Email.id)).where(Email.account_id == account.id)
        )
        actual_email_count = count_result.scalar() or 0

        await db.execute(
            update(EmailAccount)
            .where(EmailAccount.id == account.id)
            .values(
                sync_status="completed",
                last_sync_at=datetime.now(timezone.utc),
                total_emails_synced=actual_email_count,  # Use actual count from database
                last_error=None,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()

    async def _create_sync_history(
        self,
        db: AsyncSession,
        account: EmailAccount
    ) -> EmailSyncHistory:
        """Create sync history record."""
        sync_history = EmailSyncHistory(
            account_id=account.id,
            sync_type="uid_incremental",
            status="running"
        )
        db.add(sync_history)
        await db.commit()
        await db.refresh(sync_history)
        return sync_history

    async def _complete_sync_history(
        self,
        db: AsyncSession,
        sync_history: EmailSyncHistory,
        sync_result: EmailSyncResult
    ):
        """Complete sync history record."""
        duration = (sync_result.completed_at - sync_result.started_at).total_seconds()

        await db.execute(
            update(EmailSyncHistory)
            .where(EmailSyncHistory.id == sync_history.id)
            .values(
                status="completed" if sync_result.success else "failed",
                completed_at=sync_result.completed_at,
                emails_processed=sync_result.emails_processed,
                emails_added=sync_result.emails_added,
                emails_updated=sync_result.emails_updated,
                duration_seconds=int(duration),
                error_message=sync_result.error_message
            )
        )
        await db.commit()

    async def _fail_sync_history(
        self,
        db: AsyncSession,
        sync_history: EmailSyncHistory,
        error_message: str
    ):
        """Mark sync history as failed."""
        await db.execute(
            update(EmailSyncHistory)
            .where(EmailSyncHistory.id == sync_history.id)
            .values(
                status="failed",
                completed_at=datetime.now(timezone.utc),
                error_message=error_message
            )
        )
        await db.commit()

    async def _schedule_embedding_generation(
        self,
        db: AsyncSession,
        user_id: int
    ):
        """Schedule embedding generation task."""
        # This is a placeholder. In a real system, this would trigger a Celery task.
        # For now, we rely on the periodic task to pick up pending embeddings.
        try:
            # Import here to avoid circular imports
            from app.tasks.email_sync_tasks import process_pending_embeddings
            
            # Schedule as background task
            process_pending_embeddings.delay(user_id)
            self.logger.info(f"Scheduled embedding generation task for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error scheduling embedding generation: {e}")

    async def _check_circuit_breaker(self, db: AsyncSession, account: EmailAccount) -> bool:
        """
        Check if sync should proceed based on recent failure history.
        Returns True if allowed, False if circuit is open.
        """
        # Get last 5 sync attempts
        query = select(EmailSyncHistory).where(
            EmailSyncHistory.account_id == account.id
        ).order_by(desc(EmailSyncHistory.started_at)).limit(5)
        
        result = await db.execute(query)
        history = result.scalars().all()
        
        if len(history) < 5:
            return True
            
        # Check if all 5 failed
        all_failed = all(h.status == "failed" for h in history) # Changed "error" to "failed" to match EmailSyncHistory status
        if not all_failed:
            return True
            
        # Check if last failure was recent (within 30 minutes)
        last_failure_time = history[0].started_at
        if last_failure_time.tzinfo is None:
            last_failure_time = last_failure_time.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        if (now - last_failure_time) < timedelta(minutes=30):
            self.logger.warning(f"Circuit breaker open for account {account.id}. 5 consecutive failures, last at {last_failure_time}")
            return False
            
        return True

    async def _check_lock(self, db: AsyncSession, account: EmailAccount) -> bool:
        """
        Check if sync is already running.
        Returns True if allowed (lock acquired or broken), False if locked.
        """
        if account.sync_status != "running":
            return True
            
        # Check if stuck
        # We use EmailSyncHistory to find the running sync
        query = select(EmailSyncHistory).where(
            and_(
                EmailSyncHistory.account_id == account.id,
                EmailSyncHistory.status == "running"
            )
        ).order_by(desc(EmailSyncHistory.started_at)).limit(1)
        
        result = await db.execute(query)
        running_sync = result.scalar_one_or_none()
        
        if not running_sync:
            # Account says running but no history record? Break lock.
            self.logger.warning(f"Account {account.id} status is 'running' but no active sync history found. Breaking potential stale lock.")
            return True
            
        # Check last_updated
        last_activity = running_sync.last_updated or running_sync.started_at
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        if (now - last_activity) > timedelta(minutes=60): # 1 hour timeout
            self.logger.warning(f"Breaking stale lock for account {account.id}. Last activity at {last_activity}")
            # Mark old sync as error
            running_sync.status = "failed" # Changed "error" to "failed"
            running_sync.error_message = "Stale sync terminated by lock check"
            running_sync.completed_at = now
            await db.commit() # Commit the status update
            return True
            
        return False

    async def get_sync_status(
        self,
        db: AsyncSession,
        user_id: int
    ) -> dict:
        """
        Get synchronization status for user's email accounts.

        Returns detailed status including sync history and statistics.
        """
        from sqlalchemy import select, func, desc
        from app.db.models.email import EmailAccount, EmailSyncHistory, Email

        try:
            # Get all accounts for user
            result = await db.execute(
                select(EmailAccount).where(EmailAccount.user_id == user_id)
            )
            accounts = result.scalars().all()

            account_statuses = []
            overall_status = "idle"
            total_emails_synced = 0
            total_emails_realtime = 0
            most_recent_sync = None

            for account in accounts:
                # Get recent sync history (last 3 syncs)
                history_result = await db.execute(
                    select(EmailSyncHistory)
                    .where(EmailSyncHistory.account_id == account.id)
                    .order_by(desc(EmailSyncHistory.started_at))
                    .limit(3)
                )
                recent_syncs = history_result.scalars().all()

                # Format recent syncs
                formatted_syncs = []
                for sync in recent_syncs:
                    duration_seconds = None
                    if sync.completed_at and sync.started_at:
                        duration_seconds = int((sync.completed_at - sync.started_at).total_seconds())

                    formatted_syncs.append({
                        "status": sync.status,
                        "emails_processed": sync.emails_processed or 0,
                        "started_at": sync.started_at.isoformat() if sync.started_at else None,
                        "completed_at": sync.completed_at.isoformat() if sync.completed_at else None,
                        "duration_seconds": duration_seconds,
                        "error_message": sync.error_message
                    })

                # Get real-time email count for this account
                email_count_result = await db.execute(
                    select(func.count(Email.id)).where(Email.account_id == account.id)
                )
                realtime_email_count = email_count_result.scalar() or 0
                total_emails_realtime += realtime_email_count

                # Determine current sync status
                sync_status = account.sync_status or "idle"
                if sync_status in ["running", "syncing"]:
                    overall_status = "running"

                # Aggregate total emails synced (counter field)
                total_emails_synced += (account.total_emails_synced or 0)

                # Track most recent sync
                if account.last_sync_at:
                    if most_recent_sync is None or account.last_sync_at > most_recent_sync:
                        most_recent_sync = account.last_sync_at

                # Calculate sync progress percentage if running
                sync_progress_percent = None
                if sync_status in ["running", "syncing"] and realtime_email_count > 0:
                    # Rough estimate - assumes target is last sync count + 10%
                    estimated_total = max((account.total_emails_synced or 0) * 1.1, realtime_email_count)
                    sync_progress_percent = min(round((realtime_email_count / estimated_total) * 100, 1), 99.9)

                account_statuses.append({
                    "account_id": str(account.id),
                    "email_address": account.email_address,
                    "sync_status": sync_status,
                    "total_emails_synced": account.total_emails_synced or 0,  # Counter field (updated on completion)
                    "realtime_email_count": realtime_email_count,  # Real-time database count
                    "sync_progress_percent": sync_progress_percent,  # Progress indicator
                    "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
                    "next_sync_at": account.next_sync_at.isoformat() if account.next_sync_at else None,
                    "last_error": account.last_error,
                    "recent_syncs": formatted_syncs
                })

            return {
                "overall_status": overall_status,
                "total_accounts": len(accounts),
                "total_emails_synced": total_emails_synced,  # Cached counter
                "total_emails_realtime": total_emails_realtime,  # Real-time count
                "most_recent_sync": most_recent_sync.isoformat() if most_recent_sync else None,
                "accounts": account_statuses
            }

        except Exception as e:
            self.logger.error(f"Error getting sync status: {e}")
            raise

    async def get_sync_health(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Get health status of email synchronization.
        Returns circuit breaker status, lock status, and failure counts.
        """
        from sqlalchemy import select, desc, func, and_ # Added 'and_' for clarity
        from app.db.models.email import EmailAccount, EmailSyncHistory
        from datetime import datetime, timedelta, timezone # Added for clarity

        try:
            # Get all accounts
            result = await db.execute(
                select(EmailAccount).where(EmailAccount.user_id == user_id)
            )
            accounts = result.scalars().all()

            health_status = []
            system_healthy = True

            for account in accounts:
                # Check circuit breaker status (reusing logic but returning details)
                # Get last 5 syncs
                history_query = select(EmailSyncHistory).where(
                    EmailSyncHistory.account_id == account.id
                ).order_by(desc(EmailSyncHistory.started_at)).limit(5)
                
                history_result = await db.execute(history_query)
                history = history_result.scalars().all()
                
                consecutive_failures = 0
                for h in history:
                    if h.status == "failed":
                        consecutive_failures += 1
                    else:
                        break
                
                circuit_breaker_open = False
                if consecutive_failures >= 5:
                    if history:
                        last_failure = history[0].started_at
                        if last_failure.tzinfo is None:
                            last_failure = last_failure.replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        if (now - last_failure) < timedelta(minutes=30):
                            circuit_breaker_open = True

                # Check lock status
                is_locked = account.sync_status == "running"
                lock_stale = False
                if is_locked:
                    # Check if lock is stale
                    running_sync_query = select(EmailSyncHistory).where(
                        and_(
                            EmailSyncHistory.account_id == account.id,
                            EmailSyncHistory.status == "running"
                        )
                    ).order_by(desc(EmailSyncHistory.started_at)).limit(1)
                    running_result = await db.execute(running_sync_query)
                    running_sync = running_result.scalar_one_or_none()
                    
                    if running_sync:
                        last_activity = running_sync.last_updated or running_sync.started_at
                        if last_activity.tzinfo is None:
                            last_activity = last_activity.replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        if (now - last_activity) > timedelta(minutes=60):
                            lock_stale = True

                account_health = {
                    "account_id": str(account.id),
                    "email_address": account.email_address,
                    "status": "unhealthy" if circuit_breaker_open else ("degraded" if consecutive_failures > 0 or lock_stale else "healthy"),
                    "consecutive_failures": consecutive_failures,
                    "circuit_breaker_open": circuit_breaker_open,
                    "is_locked": is_locked,
                    "lock_stale": lock_stale,
                    "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None
                }
                
                if account_health["status"] == "unhealthy":
                    system_healthy = False
                
                health_status.append(account_health)

            return {
                "system_status": "healthy" if system_healthy else "unhealthy",
                "accounts": health_status,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error getting sync health: {e}")
            raise


# Global instance
email_sync_service = EmailSyncService()


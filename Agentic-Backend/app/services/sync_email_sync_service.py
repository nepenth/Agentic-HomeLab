"""
Synchronous Email Sync Service for Celery Tasks

This service provides a pure synchronous implementation of email synchronization
designed specifically for Celery worker processes. It avoids all async/await
complications that cause event loop issues in forked processes.

Key Design Principles:
1. Pure synchronous code (no async/await)
2. Uses sync database sessions (Session, not AsyncSession)
3. Direct IMAP library calls (imaplib is already synchronous)
4. Synchronous HTTP calls for embeddings (requests, not httpx)
5. No event loop management required
"""

import imaplib
import email
import hashlib
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.email import EmailAccount, Email, EmailEmbedding, EmailSyncHistory
from app.services.email_connectors.base_connector import SyncType, EmailSyncResult
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger("sync_email_sync_service")


class SyncEmailSyncService:
    """
    Synchronous email sync service for reliable Celery task execution.

    This service implements email synchronization without any async complexity,
    making it safe to use in Celery's forked worker processes.
    """

    def __init__(self):
        self.logger = get_logger("sync_email_sync_service")
        self.sync_timeout_minutes = 30

    def sync_account(
        self,
        db: Session,
        account_id: str,
        sync_type: SyncType = SyncType.INCREMENTAL,
        force_sync: bool = False
    ) -> EmailSyncResult:
        """
        Synchronize a single email account synchronously.

        Args:
            db: Synchronous database session
            account_id: EmailAccount UUID
            sync_type: Type of synchronization
            force_sync: Force sync even if recently synced

        Returns:
            EmailSyncResult with sync details
        """
        start_time = datetime.now(timezone.utc)
        sync_result = EmailSyncResult(
            sync_type=sync_type,
            started_at=start_time
        )

        try:
            # Get email account
            account = db.query(EmailAccount).filter_by(id=account_id).first()

            if not account:
                self.logger.error(f"Account {account_id} not found")
                sync_result.error_message = f"Account {account_id} not found"
                sync_result.completed_at = datetime.now(timezone.utc)
                return sync_result

            self.logger.info(f"Starting {sync_type.value} sync for {account.email_address}")

            # Check if sync is needed
            if not force_sync and not self._should_sync_account(account, sync_type):
                self.logger.info(f"Sync not needed for {account.email_address} - recently synced")
                sync_result.success = True
                sync_result.emails_skipped = 1
                sync_result.completed_at = datetime.now(timezone.utc)
                return sync_result

            # Update account status
            account.sync_status = "running"
            db.commit()

            # Create sync history record
            sync_history = EmailSyncHistory(
                account_id=account.id,
                sync_type=sync_type.value,
                started_at=start_time,
                status="running"
            )
            db.add(sync_history)
            db.commit()

            # Perform the actual sync
            sync_stats = self._perform_imap_sync(db, account, sync_type)

            # Update result
            sync_result.success = True
            sync_result.emails_processed = sync_stats["emails_processed"]
            sync_result.emails_added = sync_stats["emails_added"]
            sync_result.emails_updated = sync_stats["emails_updated"]
            sync_result.completed_at = datetime.now(timezone.utc)

            # Update account
            account.last_sync_at = sync_result.completed_at
            account.sync_status = "success"
            account.last_error = None

            # Calculate next sync time
            if account.auto_sync_enabled and account.sync_interval_minutes:
                account.next_sync_at = sync_result.completed_at + timedelta(
                    minutes=account.sync_interval_minutes
                )

            db.commit()

            # Update sync history
            sync_history.completed_at = sync_result.completed_at
            sync_history.status = "completed"
            sync_history.emails_processed = sync_result.emails_processed
            sync_history.emails_added = sync_result.emails_added
            sync_history.emails_updated = sync_result.emails_updated
            db.commit()

            self.logger.info(
                f"Sync completed for {account.email_address}: "
                f"{sync_result.emails_processed} processed, "
                f"{sync_result.emails_added} added, "
                f"{sync_result.emails_updated} updated"
            )

            return sync_result

        except Exception as e:
            self.logger.error(f"Sync failed for account {account_id}: {e}", exc_info=True)
            sync_result.success = False
            sync_result.error_message = str(e)
            sync_result.completed_at = datetime.now(timezone.utc)

            # Update account status
            try:
                account = db.query(EmailAccount).filter_by(id=account_id).first()
                if account:
                    account.sync_status = "error"
                    account.last_error = str(e)
                    db.commit()
            except:
                pass

            return sync_result

    def _should_sync_account(self, account: EmailAccount, sync_type: SyncType) -> bool:
        """Check if account should be synced."""
        # Always sync if full sync or first sync
        if sync_type == SyncType.FULL or not account.last_sync_at:
            return True

        # Check sync interval for incremental sync
        if account.sync_interval_minutes:
            time_since_sync = datetime.now(timezone.utc) - account.last_sync_at
            if time_since_sync.total_seconds() < (account.sync_interval_minutes * 60):
                return False

        return True

    def _perform_imap_sync(
        self,
        db: Session,
        account: EmailAccount,
        sync_type: SyncType
    ) -> Dict[str, int]:
        """
        Perform IMAP synchronization synchronously.

        This uses the imaplib library directly (which is already synchronous)
        instead of going through async wrappers.
        """
        stats = {
            "emails_processed": 0,
            "emails_added": 0,
            "emails_updated": 0,
            "attachments_processed": 0
        }

        connection = None

        try:
            # Get credentials from JSONB column
            # auth_credentials is a dict like: {"credentials": {"server": ..., "username": ..., "password": ...}}
            if not account.auth_credentials:
                raise ValueError("No authentication credentials configured for this account")

            credentials = account.auth_credentials.get("credentials", {})

            # Handle case where credentials might be at top level
            if not credentials:
                credentials = account.auth_credentials

            server = credentials.get("server")
            port = credentials.get("port", 993)
            username = credentials.get("username")
            password = credentials.get("password")
            use_ssl = credentials.get("use_ssl", True)

            self.logger.info(f"Extracting credentials - server: {server}, username: {username}, has_password: {bool(password)}")

            if not all([server, username, password]):
                raise ValueError(f"Missing required IMAP credentials - server: {bool(server)}, username: {bool(username)}, password: {bool(password)}")

            self.logger.info(f"Connecting to IMAP server {server}:{port}")

            # Connect to IMAP server
            if use_ssl:
                connection = imaplib.IMAP4_SSL(server, port)
            else:
                connection = imaplib.IMAP4(server, port)

            # Login
            connection.login(username, password)
            self.logger.info("IMAP login successful")

            # Select INBOX
            status, messages = connection.select('INBOX')
            if status != 'OK':
                raise Exception(f"Failed to select INBOX: {messages}")

            # Determine search criteria
            if sync_type == SyncType.FULL:
                # Sync all emails from last 365 days
                since_date = datetime.now(timezone.utc) - timedelta(days=365)
                search_criteria = f'SINCE {since_date.strftime("%d-%b-%Y")}'
            else:
                # Incremental: sync emails since last sync
                if account.last_sync_at:
                    since_date = account.last_sync_at - timedelta(hours=1)  # 1 hour overlap
                else:
                    since_date = datetime.now(timezone.utc) - timedelta(days=30)
                search_criteria = f'SINCE {since_date.strftime("%d-%b-%Y")}'

            self.logger.info(f"Searching with criteria: {search_criteria}")

            # Search for emails
            status, message_numbers = connection.search(None, search_criteria)
            if status != 'OK':
                raise Exception(f"Email search failed: {message_numbers}")

            email_ids = message_numbers[0].split()
            total_emails = len(email_ids)
            self.logger.info(f"Found {total_emails} emails to process")

            # Limit emails to process (avoid overwhelming the system)
            max_emails = 100 if sync_type == SyncType.INCREMENTAL else 500
            email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids

            # Process each email
            for email_id in email_ids:
                try:
                    stats["emails_processed"] += 1

                    # Fetch email
                    status, msg_data = connection.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        self.logger.warning(f"Failed to fetch email {email_id}")
                        continue

                    # Parse email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)

                    # Extract email data
                    email_data = self._extract_email_data(email_message, account.id, account.user_id)

                    # Check if email exists
                    existing_email = db.query(Email).filter_by(
                        account_id=account.id,
                        message_id=email_data["message_id"]
                    ).first()

                    if existing_email:
                        # Update existing email
                        for key, value in email_data.items():
                            if key not in ["id", "created_at"]:
                                setattr(existing_email, key, value)
                        stats["emails_updated"] += 1
                    else:
                        # Create new email
                        new_email = Email(**email_data)
                        db.add(new_email)
                        stats["emails_added"] += 1

                    # Commit every 10 emails
                    if stats["emails_processed"] % 10 == 0:
                        db.commit()
                        self.logger.info(f"Processed {stats['emails_processed']}/{len(email_ids)} emails")

                except Exception as e:
                    self.logger.error(f"Error processing email {email_id}: {e}")
                    continue

            # Final commit
            db.commit()

            # Generate embeddings for new emails
            if stats["emails_added"] > 0:
                self.logger.info(f"Generating embeddings for {stats['emails_added']} new emails")
                self._generate_embeddings_batch(db, account)

            return stats

        finally:
            # Clean up IMAP connection
            if connection:
                try:
                    connection.close()
                    connection.logout()
                except:
                    pass

    def _extract_email_data(self, email_message, account_id: str, user_id: int) -> Dict[str, Any]:
        """Extract structured data from email message."""
        from email.utils import parseaddr, parsedate_to_datetime
        from email.header import decode_header

        def decode_str(s):
            """Decode email header string."""
            if s is None:
                return None
            if isinstance(s, bytes):
                s = s.decode('utf-8', errors='ignore')

            decoded_parts = []
            for part, encoding in decode_header(s):
                if isinstance(part, bytes):
                    try:
                        decoded_parts.append(part.decode(encoding or 'utf-8'))
                    except:
                        decoded_parts.append(part.decode('utf-8', errors='ignore'))
                else:
                    decoded_parts.append(part)
            return ' '.join(decoded_parts)

        # Extract basic fields
        subject = decode_str(email_message.get('Subject', ''))
        from_addr = email_message.get('From', '')
        sender_name, sender_email = parseaddr(from_addr)

        # Get message ID
        message_id = email_message.get('Message-ID', '')
        if not message_id:
            # Generate message ID from content
            content_hash = hashlib.md5(str(email_message).encode()).hexdigest()
            message_id = f"<{content_hash}@generated>"

        # Parse date
        date_str = email_message.get('Date')
        try:
            sent_at = parsedate_to_datetime(date_str) if date_str else datetime.now(timezone.utc)
        except:
            sent_at = datetime.now(timezone.utc)

        # Extract body
        body_text = ""
        body_html = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
                elif content_type == "text/html":
                    try:
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body_text = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body_text = str(email_message.get_payload())

        return {
            "account_id": account_id,
            "user_id": user_id,
            "message_id": message_id,
            "subject": subject[:500] if subject else None,  # Limit length
            "sender_email": sender_email,
            "sender_name": sender_name or sender_email,
            "body_text": body_text[:50000] if body_text else None,  # Limit length
            "body_html": body_html[:100000] if body_html else None,  # Limit length
            "sent_at": sent_at,
            "received_at": datetime.now(timezone.utc),
            "folder_path": "INBOX",
            "has_attachments": False,  # TODO: Implement attachment detection
            "embeddings_generated": False
        }

    def _generate_embeddings_batch(self, db: Session, account: EmailAccount):
        """Generate embeddings for emails that don't have them yet."""
        try:
            # Get emails without embeddings
            emails = db.query(Email).filter(
                Email.account_id == account.id,
                Email.embeddings_generated == False
            ).limit(50).all()  # Process in batches of 50

            if not emails:
                return

            self.logger.info(f"Generating embeddings for {len(emails)} emails")

            # Determine which model to use
            embedding_model = account.embedding_model or settings.default_embedding_model

            for email_obj in emails:
                try:
                    self._generate_email_embedding(db, email_obj, embedding_model)
                except Exception as e:
                    self.logger.error(f"Failed to generate embedding for email {email_obj.id}: {e}")
                    continue

            db.commit()
            self.logger.info("Embedding generation completed")

        except Exception as e:
            self.logger.error(f"Batch embedding generation failed: {e}")

    def _generate_email_embedding(self, db: Session, email_obj: Email, model_name: str):
        """Generate embedding for a single email using synchronous HTTP."""
        # Prepare content for embedding
        content = f"{email_obj.subject or ''}\n\n{email_obj.body_text or ''}"
        content = content.strip()[:2000]  # Limit to 2000 chars

        if not content:
            return

        try:
            # Call Ollama API synchronously using requests
            response = requests.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={
                    "model": model_name,
                    "prompt": content
                },
                timeout=30
            )

            if response.status_code == 200:
                embedding_data = response.json()
                embedding_vector = embedding_data.get('embedding')

                if embedding_vector:
                    # Create embedding record
                    email_embedding = EmailEmbedding(
                        email_id=email_obj.id,
                        embedding_type="full_content",
                        content_hash=hashlib.sha256(content.encode()).hexdigest(),
                        embedding_vector=embedding_vector,
                        model_name=model_name,
                        model_version="1.0"
                    )

                    db.add(email_embedding)
                    email_obj.embeddings_generated = True

        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            raise


# Global instance
sync_email_sync_service = SyncEmailSyncService()

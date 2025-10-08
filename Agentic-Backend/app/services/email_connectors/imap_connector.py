"""
IMAP Email Connector

Handles IMAP email account connections and synchronization.
Supports standard IMAP servers with username/password authentication.
"""

import imaplib
import email
import ssl
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

from app.utils.logging import get_logger
from .base_connector import BaseEmailConnector, EmailMessage, SyncType, SyncError

logger = get_logger("imap_connector")


class IMAPConnector(BaseEmailConnector):
    """IMAP email connector for standard IMAP servers."""

    def __init__(self, account_id: str, auth_credentials, sync_settings):
        super().__init__(account_id, auth_credentials, sync_settings)
        self.logger = get_logger(f"imap_connector.{account_id}")

        # IMAP-specific settings
        self.server = auth_credentials.credentials.get("server")
        self.port = auth_credentials.credentials.get("port", 993)
        self.username = auth_credentials.credentials.get("username")
        self.password = auth_credentials.credentials.get("password")
        self.use_ssl = auth_credentials.credentials.get("use_ssl", True)

        self._connection = None

    async def connect(self) -> bool:
        """
        Connect to the IMAP server.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to IMAP server {self.server}:{self.port}")

            # Create IMAP connection
            if self.use_ssl:
                self._connection = imaplib.IMAP4_SSL(self.server, self.port)
            else:
                self._connection = imaplib.IMAP4(self.server, self.port)

            # Login
            self._connection.login(self.username, self.password)

            self.logger.info("IMAP connection established successfully")
            return True

        except imaplib.IMAP4.error as e:
            self.logger.error(f"IMAP authentication failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"IMAP connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the IMAP server."""
        try:
            if self._connection:
                try:
                    self._connection.close()
                except:
                    pass  # Ignore close errors
                self._connection.logout()
                self._connection = None
                self.logger.info("IMAP connection closed")
        except Exception as e:
            self.logger.warning(f"Error during IMAP disconnect: {e}")

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the IMAP connection.

        Returns:
            Dict containing connection test results
        """
        try:
            connected = await self.connect()
            if not connected:
                return {
                    "success": False,
                    "error": "Failed to connect to IMAP server",
                    "details": f"Could not connect to {self.server}:{self.port}"
                }

            # Test folder access
            status, folders = self._connection.list()
            if status != 'OK':
                return {
                    "success": False,
                    "error": "Failed to list folders",
                    "details": "Connected but could not access folders"
                }

            # Test INBOX access
            status, _ = self._connection.select('INBOX')
            if status != 'OK':
                return {
                    "success": False,
                    "error": "Failed to access INBOX",
                    "details": "Connected but could not select INBOX folder"
                }

            await self.disconnect()

            return {
                "success": True,
                "message": "IMAP connection test successful",
                "details": f"Connected to {self.server}:{self.port}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Connection test failed: {str(e)}",
                "details": f"Server: {self.server}:{self.port}"
            }

    async def sync_emails(
        self,
        sync_type: SyncType = SyncType.INCREMENTAL,
        last_sync_time: Optional[datetime] = None
    ) -> AsyncIterator[EmailMessage]:
        """
        Sync emails from IMAP server.

        Args:
            sync_type: Type of sync to perform
            last_sync_time: Last sync time for incremental sync

        Yields:
            EmailMessage: Individual email messages
        """
        try:
            # Connect to server
            connected = await self.connect()
            if not connected:
                self.logger.error("Failed to connect to IMAP server")
                return

            # Process folders
            for folder_name in self.settings.folders_to_sync:
                try:
                    self.logger.info(f"Starting sync for folder: {folder_name}")

                    # Select folder
                    status, _ = self._connection.select(folder_name)
                    if status != 'OK':
                        self.logger.error(f"Failed to access folder: {folder_name}")
                        continue

                    # Get email IDs based on sync type
                    search_criteria = self._build_search_criteria(sync_type, last_sync_time)
                    status, message_ids = self._connection.search(None, search_criteria)

                    if status != 'OK':
                        self.logger.error(f"Failed to search folder: {folder_name}")
                        continue

                    # Process emails in batches
                    ids = message_ids[0].split()

                    # CRITICAL FIX: Reverse order to process NEWEST emails first
                    # IMAP typically returns oldest-first, but we want newest-first
                    # so that recent emails are prioritized when hitting limits
                    ids.reverse()

                    total_emails = len(ids)

                    if total_emails == 0:
                        self.logger.info(f"No emails found in folder: {folder_name}")
                        continue

                    batch_size = min(self.settings.max_emails_per_batch, 50)

                    # Apply configured email limit (respect null = unlimited)
                    max_emails_limit = getattr(self.settings, 'max_emails_limit', None)
                    if max_emails_limit is None:
                        emails_to_process = total_emails
                        self.logger.info(f"Processing ALL {total_emails} emails (unlimited) in folder: {folder_name}")
                    else:
                        emails_to_process = min(total_emails, max_emails_limit)
                        self.logger.info(f"Processing {emails_to_process} emails (found {total_emails}, limit {max_emails_limit}) in folder: {folder_name}")

                        # VALIDATION: Warn if hitting email limit
                        if total_emails > max_emails_limit:
                            missing_count = total_emails - max_emails_limit
                            self.logger.warning(f"EMAIL SYNC LIMIT HIT: {missing_count} emails will be skipped due to max_emails_limit={max_emails_limit}")

                    # VALIDATION: Pre-sync validation
                    if total_emails > emails_to_process:
                        self.logger.warning(f"SYNC VALIDATION FAILURE: Only processing {emails_to_process} of {total_emails} emails - {total_emails - emails_to_process} emails will be missing")

                    for i in range(0, emails_to_process, batch_size):
                        batch_ids = ids[i:i + batch_size]

                        for msg_id in batch_ids:
                            try:
                                email_msg = await self._fetch_email(msg_id.decode(), folder_name)
                                if email_msg:
                                    yield email_msg
                            except Exception as e:
                                self.logger.warning(f"Failed to fetch email {msg_id}: {e}")
                                continue

                        # Rate limiting
                        if self.settings.rate_limit_delay_ms:
                            await asyncio.sleep(self.settings.rate_limit_delay_ms / 1000)

                except Exception as e:
                    self.logger.error(f"Error syncing folder {folder_name}: {str(e)}")

        except Exception as e:
            self.logger.error(f"IMAP sync failed: {str(e)}")
        finally:
            await self.disconnect()

    def _build_search_criteria(self, sync_type: SyncType, last_sync_time: Optional[datetime] = None) -> str:
        """Build IMAP search criteria based on sync type."""
        criteria = "ALL"

        if sync_type == SyncType.INCREMENTAL:
            if last_sync_time:
                # Use the last sync time if provided
                since_date = last_sync_time.strftime("%d-%b-%Y")
                criteria = f'SINCE "{since_date}"'
                self.logger.info(f"Using incremental sync since last sync: {since_date}")
            else:
                # Check for configured date range (respect null = unlimited)
                days_back = getattr(self.settings, 'sync_days_back', None)
                if days_back is None:
                    # If sync_days_back is null, sync ALL emails (no date filter)
                    criteria = "ALL"
                    self.logger.info("Using unlimited date range for incremental sync (sync_days_back=null)")
                else:
                    # Use configured days back for incremental sync
                    since_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%d-%b-%Y")
                    criteria = f'SINCE "{since_date}"'
                    self.logger.info(f"Using incremental sync for last {days_back} days since: {since_date}")
        else:
            # For FULL sync, always sync ALL emails regardless of date
            criteria = "ALL"
            self.logger.info("Using FULL sync - processing ALL emails regardless of date")

        return criteria

    async def _fetch_email(self, message_id: str, folder_name: str) -> Optional[EmailMessage]:
        """
        Fetch a single email message.

        Args:
            message_id: IMAP message ID
            folder_name: Name of the folder

        Returns:
            EmailMessage or None if failed
        """
        try:
            # Fetch email
            status, msg_data = self._connection.fetch(message_id, '(RFC822)')
            if status != 'OK':
                return None

            # Parse email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Extract email data
            subject = email_message.get('Subject', 'No Subject')
            from_addr = email_message.get('From', '')
            to_addr = email_message.get('To', '')
            date_str = email_message.get('Date', '')
            message_id_header = email_message.get('Message-ID', '')

            # Parse date and ensure timezone-aware
            received_at = None
            if date_str:
                try:
                    parsed_date = email.utils.parsedate_to_datetime(date_str)
                    # If the parsed date is timezone-naive, assume UTC
                    if parsed_date.tzinfo is None:
                        from datetime import timezone
                        received_at = parsed_date.replace(tzinfo=timezone.utc)
                    else:
                        received_at = parsed_date
                except:
                    pass

            # Extract body
            body_text = ""
            body_html = ""

            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                if email_message.get_content_type() == "text/plain":
                    body_text = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif email_message.get_content_type() == "text/html":
                    body_html = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

            # Create snippet
            snippet = (body_text or body_html)[:200] if (body_text or body_html) else ""

            return EmailMessage(
                message_id=message_id_header or f"imap_{message_id}",
                thread_id=message_id_header or f"thread_{message_id}",
                subject=subject,
                sender_email=self._extract_email_address(from_addr),
                sender_name=self._extract_display_name(from_addr),
                recipients=[{"email": to_addr, "name": ""}] if to_addr else [],
                received_at=received_at or datetime.utcnow(),
                sent_at=received_at,
                body_text=body_text,
                body_html=body_html,
                folder_path=folder_name,
                labels=[folder_name],
                has_attachments=self._has_attachments(email_message),
                is_read=False,  # IMAP doesn't easily provide read status
                is_flagged=False,
                attachments=[]  # TODO: Implement attachment extraction
            )

        except Exception as e:
            self.logger.error(f"Failed to fetch email {message_id}: {e}")
            return None

    def _extract_email_address(self, address_str: str) -> str:
        """Extract email address from address string."""
        try:
            if '<' in address_str and '>' in address_str:
                return address_str.split('<')[1].split('>')[0]
            return address_str.strip()
        except:
            return address_str

    def _extract_display_name(self, address_str: str) -> str:
        """Extract display name from address string."""
        try:
            if '<' in address_str:
                return address_str.split('<')[0].strip().strip('"')
            return ""
        except:
            return ""

    def _has_attachments(self, email_message) -> bool:
        """Check if email has attachments."""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_disposition = str(part.get('Content-Disposition', ''))
                    if "attachment" in content_disposition:
                        return True
            return False
        except:
            return False

    async def get_folders(self) -> List[Dict[str, Any]]:
        """
        Get list of available folders.

        Returns:
            List of folder information
        """
        try:
            connected = await self.connect()
            if not connected:
                return []

            status, folders = self._connection.list()
            if status != 'OK':
                return []

            folder_list = []
            for folder in folders:
                # Parse folder line
                folder_str = folder.decode() if isinstance(folder, bytes) else str(folder)
                parts = folder_str.split('"')
                if len(parts) >= 3:
                    folder_name = parts[-2]
                    folder_list.append({
                        "name": folder_name,
                        "display_name": folder_name,
                        "type": "folder"
                    })

            await self.disconnect()
            return folder_list

        except Exception as e:
            self.logger.error(f"Failed to get folders: {e}")
            return []

    async def get_email_by_id(self, email_id: str) -> Optional[EmailMessage]:
        """
        Get a specific email by its ID.

        Args:
            email_id: Email identifier

        Returns:
            EmailMessage or None if not found
        """
        try:
            connected = await self.connect()
            if not connected:
                return None

            # For IMAP, the email_id might be in format "folder:message_id"
            if ':' in email_id:
                folder_name, message_id = email_id.split(':', 1)
            else:
                folder_name = 'INBOX'
                message_id = email_id

            # Select folder
            status, _ = self._connection.select(folder_name)
            if status != 'OK':
                return None

            # Fetch the email
            email_msg = await self._fetch_email(message_id, folder_name)
            await self.disconnect()
            return email_msg

        except Exception as e:
            self.logger.error(f"Failed to get email by ID {email_id}: {e}")
            return None

    async def mark_as_read(self, email_id: str) -> bool:
        """
        Mark an email as read.

        Args:
            email_id: Email identifier

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            connected = await self.connect()
            if not connected:
                return False

            # For IMAP, the email_id might be in format "folder:message_id"
            if ':' in email_id:
                folder_name, message_id = email_id.split(':', 1)
            else:
                folder_name = 'INBOX'
                message_id = email_id

            # Select folder
            status, _ = self._connection.select(folder_name)
            if status != 'OK':
                return False

            # Mark as read
            self._connection.store(message_id, '+FLAGS', '\\Seen')
            await self.disconnect()
            return True

        except Exception as e:
            self.logger.error(f"Failed to mark email {email_id} as read: {e}")
            return False

    async def download_attachment(self, email_id: str, attachment_id: str) -> Optional[bytes]:
        """
        Download an email attachment.

        Args:
            email_id: Email identifier
            attachment_id: Attachment identifier

        Returns:
            bytes: Attachment content or None if failed
        """
        try:
            # For now, return None as attachment handling is complex
            # This can be implemented later when needed
            self.logger.warning(f"Attachment download not yet implemented for IMAP")
            return None

        except Exception as e:
            self.logger.error(f"Failed to download attachment {attachment_id} from {email_id}: {e}")
            return None

    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get synchronization status for this connector.

        Returns:
            Dict with sync status information
        """
        try:
            connected = await self.connect()
            if not connected:
                return {
                    "status": "error",
                    "message": "Cannot connect to IMAP server",
                    "folders": []
                }

            # Get folder information
            folders_info = []
            status, folders = self._connection.list()

            if status == 'OK':
                for folder in folders:
                    folder_str = folder.decode() if isinstance(folder, bytes) else str(folder)
                    parts = folder_str.split('"')
                    if len(parts) >= 3:
                        folder_name = parts[-2]

                        # Try to get message count
                        try:
                            status, count = self._connection.select(folder_name)
                            if status == 'OK':
                                message_count = int(count[0]) if count and count[0] else 0
                            else:
                                message_count = 0
                        except:
                            message_count = 0

                        folders_info.append({
                            "name": folder_name,
                            "message_count": message_count
                        })

            await self.disconnect()

            return {
                "status": "connected",
                "message": f"Connected to {self.server}:{self.port}",
                "folders": folders_info,
                "server": self.server,
                "port": self.port,
                "ssl": self.use_ssl
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"IMAP sync status error: {str(e)}",
                "folders": []
            }
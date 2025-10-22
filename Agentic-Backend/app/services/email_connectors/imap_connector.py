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

    def _quote_folder_name(self, folder: str) -> str:
        """
        Properly quote IMAP folder name for use with Python's imaplib.

        According to RFC 3501, folder names with special characters must be quoted.
        Uses imaplib's built-in _quote() method which properly handles:
        - Spaces in folder names
        - Special characters
        - Hierarchical separators (/)
        - Already-quoted strings

        Args:
            folder: Raw folder name as returned from LIST command

        Returns:
            Folder name ready for imaplib commands (quoted if needed)
        """
        # Use imaplib's built-in _quote() method for RFC 3501 compliance
        # This method properly handles all edge cases including:
        # - Folders with spaces: "INBOX/Applied to Jobs"
        # - Folders with special chars
        # - Already quoted strings (won't double-quote)
        # - Hierarchical folder names with / delimiter
        if self._connection:
            return self._connection._quote(folder)

        # Fallback if no connection (shouldn't happen in normal flow)
        # Manually quote if folder contains spaces
        if ' ' in folder and not (folder.startswith('"') and folder.endswith('"')):
            escaped = folder.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        return folder

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

                    # Select folder (quote for RFC 3501 compliance)
                    quoted_folder = self._quote_folder_name(folder_name)
                    status, _ = self._connection.select(quoted_folder)
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
            # Fetch email with FLAGS to get read/flagged status
            # IMPORTANT: Use BODY.PEEK[] instead of RFC822 to avoid marking emails as read
            # RFC822 automatically sets \Seen flag, BODY.PEEK[] is read-only
            status, msg_data = self._connection.fetch(message_id, '(BODY.PEEK[] FLAGS)')
            if status != 'OK':
                return None

            # Parse email and flags
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Extract FLAGS from response and parse RFC 3501 standard flags
            flags_match = msg_data[0][0] if isinstance(msg_data[0][0], bytes) else None
            flags_str = flags_match.decode() if flags_match else ""
            is_read = '\\Seen' in flags_str
            is_flagged = '\\Flagged' in flags_str
            is_deleted = '\\Deleted' in flags_str
            is_draft = '\\Draft' in flags_str
            is_answered = '\\Answered' in flags_str

            # Extract email data
            # Decode MIME encoded-word syntax (RFC 2047) for subject
            raw_subject = email_message.get('Subject', 'No Subject')
            subject = self._decode_mime_header(raw_subject)
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
                # RFC 3501 IMAP standard flags
                is_read=is_read,        # \Seen
                is_flagged=is_flagged,  # \Flagged
                is_deleted=is_deleted,  # \Deleted
                is_draft=is_draft,      # \Draft
                is_answered=is_answered,  # \Answered
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

    def _decode_mime_header(self, header_value: str) -> str:
        """
        Decode MIME encoded-word syntax (RFC 2047) in email headers.

        Examples:
            =?utf-8?Q?See=20You=20At=20Supercon=21=20=E2=98=A0=EF=B8=8F?=
            -> See You At Supercon! ☠️
        """
        try:
            from email.header import decode_header

            # decode_header returns list of (decoded_bytes, charset) tuples
            decoded_parts = decode_header(header_value)

            # Reconstruct the header from decoded parts
            result = []
            for decoded_bytes, charset in decoded_parts:
                if isinstance(decoded_bytes, bytes):
                    # Decode bytes to string using detected charset or utf-8 fallback
                    result.append(decoded_bytes.decode(charset or 'utf-8', errors='ignore'))
                else:
                    # Already a string
                    result.append(decoded_bytes)

            return ''.join(result)
        except Exception as e:
            self.logger.warning(f"Failed to decode MIME header '{header_value}': {e}")
            return header_value  # Return original if decoding fails

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

            # Select folder (quote for RFC 3501 compliance)
            quoted_folder = self._quote_folder_name(folder_name)
            status, _ = self._connection.select(quoted_folder)
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

            # Select folder (quote for RFC 3501 compliance)
            quoted_folder = self._quote_folder_name(folder_name)
            status, _ = self._connection.select(quoted_folder)
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
                            quoted_folder = self._quote_folder_name(folder_name)
                            status, count = self._connection.select(quoted_folder)
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

    # ============================================================================
    # UID-BASED SYNC METHODS (Phase 2 - RFC 3501 Compliant)
    # ============================================================================

    def get_folder_status(self, folder: str) -> Dict[str, Any]:
        """
        Get folder status including UIDVALIDITY, EXISTS, UIDNEXT, and HIGHESTMODSEQ.

        This is a synchronous method (called from sync workers).

        Args:
            folder: Folder name (e.g., "INBOX", "Sent", "INBOX/Applied to Jobs")

        Returns:
            Dict with:
                - uidvalidity: UIDVALIDITY value (mailbox unique ID)
                - exists: Number of messages in folder
                - uidnext: Next UID to be assigned
                - highest_modseq: HIGHESTMODSEQ (if CONDSTORE supported)
                - recent: Number of recent messages
        """
        try:
            # Quote folder name properly for IMAP commands
            quoted_folder = self._quote_folder_name(folder)

            # Select folder
            status, data = self._connection.select(quoted_folder)
            if status != 'OK':
                raise SyncError(f"Failed to select folder {folder}: {data}")

            # Parse SELECT response for message count
            exists = int(data[0]) if data and data[0] else 0

            # Get UIDVALIDITY and UIDNEXT from STATUS command
            status, status_data = self._connection.status(
                quoted_folder,
                '(UIDVALIDITY UIDNEXT MESSAGES RECENT)'
            )

            if status != 'OK':
                raise SyncError(f"Failed to get folder status: {status_data}")

            # Parse status response
            # Example: b'INBOX (MESSAGES 6365 RECENT 0 UIDNEXT 6366 UIDVALIDITY 1695053769)'
            status_str = status_data[0].decode() if isinstance(status_data[0], bytes) else status_data[0]

            result = {
                'exists': exists,
                'uidvalidity': None,
                'uidnext': None,
                'recent': 0,
                'highest_modseq': None
            }

            # Parse status string
            import re
            uidvalidity_match = re.search(r'UIDVALIDITY (\d+)', status_str)
            uidnext_match = re.search(r'UIDNEXT (\d+)', status_str)
            messages_match = re.search(r'MESSAGES (\d+)', status_str)
            recent_match = re.search(r'RECENT (\d+)', status_str)

            if uidvalidity_match:
                result['uidvalidity'] = int(uidvalidity_match.group(1))
            if uidnext_match:
                result['uidnext'] = int(uidnext_match.group(1))
            if messages_match:
                result['exists'] = int(messages_match.group(1))
            if recent_match:
                result['recent'] = int(recent_match.group(1))

            # Try to get HIGHESTMODSEQ if CONDSTORE is supported
            try:
                status, modseq_data = self._connection.status(quoted_folder, '(HIGHESTMODSEQ)')
                if status == 'OK':
                    modseq_str = modseq_data[0].decode() if isinstance(modseq_data[0], bytes) else modseq_data[0]
                    modseq_match = re.search(r'HIGHESTMODSEQ (\d+)', modseq_str)
                    if modseq_match:
                        result['highest_modseq'] = int(modseq_match.group(1))
            except:
                # CONDSTORE not supported, that's fine
                pass

            return result

        except Exception as e:
            self.logger.error(f"Failed to get folder status for {folder}: {e}")
            raise SyncError(f"Failed to get folder status: {e}")

    def fetch_uids_in_range(self, folder: str, uid_start: int, uid_end: str = '*') -> List[int]:
        """
        Fetch UIDs in a specified range.

        Args:
            folder: Folder name
            uid_start: Starting UID (inclusive)
            uid_end: Ending UID (inclusive), or '*' for highest UID

        Returns:
            List of UIDs in range
        """
        try:
            # Quote folder name properly
            quoted_folder = self._quote_folder_name(folder)

            # Select folder
            status, _ = self._connection.select(quoted_folder)
            if status != 'OK':
                raise SyncError(f"Failed to select folder {folder}")

            # UID SEARCH for range
            # Note: IMAP UID SEARCH requires 'UID' keyword in the search criteria
            search_criteria = f'UID {uid_start}:{uid_end}'
            status, data = self._connection.uid('SEARCH', None, search_criteria)

            if status != 'OK':
                raise SyncError(f"UID SEARCH failed: {data}")

            # Parse UIDs from response
            if not data or not data[0]:
                return []

            uid_bytes = data[0]
            uid_str = uid_bytes.decode() if isinstance(uid_bytes, bytes) else uid_bytes

            if not uid_str.strip():
                return []

            uids = [int(uid) for uid in uid_str.split()]
            return uids

        except Exception as e:
            self.logger.error(f"Failed to fetch UIDs in range {uid_start}:{uid_end}: {e}")
            raise SyncError(f"Failed to fetch UIDs: {e}")

    def fetch_uids_since_date(self, folder: str, since_date: datetime) -> List[int]:
        """
        Fetch UIDs for emails received since a specific date.

        Args:
            folder: Folder name
            since_date: Fetch emails since this date

        Returns:
            List of UIDs
        """
        try:
            # Quote folder name properly
            quoted_folder = self._quote_folder_name(folder)

            # Select folder
            status, _ = self._connection.select(quoted_folder)
            if status != 'OK':
                raise SyncError(f"Failed to select folder {folder}")

            # Format date for IMAP (DD-Mon-YYYY)
            date_str = since_date.strftime('%d-%b-%Y')

            # UID SEARCH SINCE
            status, data = self._connection.uid('SEARCH', None, f'SINCE {date_str}')

            if status != 'OK':
                raise SyncError(f"UID SEARCH SINCE failed: {data}")

            # Parse UIDs
            if not data or not data[0]:
                return []

            uid_bytes = data[0]
            uid_str = uid_bytes.decode() if isinstance(uid_bytes, bytes) else uid_bytes

            if not uid_str.strip():
                return []

            uids = [int(uid) for uid in uid_str.split()]
            return uids

        except Exception as e:
            self.logger.error(f"Failed to fetch UIDs since {since_date}: {e}")
            raise SyncError(f"Failed to fetch UIDs since date: {e}")

    def fetch_email_by_uid(self, folder: str, uid: int) -> Optional[EmailMessage]:
        """
        Fetch a single email by its UID.

        Args:
            folder: Folder name
            uid: IMAP UID

        Returns:
            EmailMessage object or None
        """
        try:
            # Quote folder name properly
            quoted_folder = self._quote_folder_name(folder)

            # Select folder
            status, _ = self._connection.select(quoted_folder)
            if status != 'OK':
                raise SyncError(f"Failed to select folder {folder}")

            # Fetch email with FLAGS (use BODY.PEEK[] to avoid marking as read)
            status, msg_data = self._connection.uid('FETCH', str(uid), '(BODY.PEEK[] FLAGS)')

            if status != 'OK' or not msg_data or not msg_data[0]:
                self.logger.warning(f"Failed to fetch email UID {uid}")
                return None

            # Parse email and flags
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Extract FLAGS from response and parse RFC 3501 standard flags
            flags_match = msg_data[0][0] if isinstance(msg_data[0][0], bytes) else None
            flags_str = flags_match.decode() if flags_match else ""
            is_read = '\\Seen' in flags_str
            is_flagged = '\\Flagged' in flags_str
            is_deleted = '\\Deleted' in flags_str
            is_draft = '\\Draft' in flags_str
            is_answered = '\\Answered' in flags_str

            # Extract email data (reuse existing logic from _fetch_email)
            # Decode MIME encoded-word syntax (RFC 2047) for subject
            raw_subject = email_message.get('Subject', 'No Subject')
            subject = self._decode_mime_header(raw_subject)
            from_addr = email_message.get('From', '')
            to_addr = email_message.get('To', '')
            date_str = email_message.get('Date', '')
            message_id_header = email_message.get('Message-ID', '')

            # Parse date
            received_at = None
            if date_str:
                try:
                    parsed_date = email.utils.parsedate_to_datetime(date_str)
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
                message_id=message_id_header or f"imap_uid_{uid}",
                thread_id=message_id_header or f"thread_uid_{uid}",
                subject=subject,
                sender_email=self._extract_email_address(from_addr),
                sender_name=self._extract_display_name(from_addr),
                recipients=[{"email": to_addr, "name": ""}] if to_addr else [],
                received_at=received_at or datetime.utcnow(),
                sent_at=received_at,
                body_text=body_text,
                body_html=body_html,
                folder_path=folder,
                labels=[folder],
                has_attachments=self._has_attachments(email_message),
                # RFC 3501 IMAP standard flags
                is_read=is_read,        # \Seen
                is_flagged=is_flagged,  # \Flagged
                is_deleted=is_deleted,  # \Deleted
                is_draft=is_draft,      # \Draft
                is_answered=is_answered,  # \Answered
                snippet=snippet,
                imap_uid=uid,  # Include UID in response
            )

        except Exception as e:
            self.logger.error(f"Failed to fetch email UID {uid}: {e}")
            return None

    def fetch_flags_by_uids(self, folder: str, uids: List[int]) -> Dict[int, Dict[str, bool]]:
        """
        Fetch only flags for multiple UIDs (efficient for flag updates).

        Args:
            folder: Folder name
            uids: List of UIDs

        Returns:
            Dict mapping UID to flags: {uid: {'is_read': bool, 'is_flagged': bool}}
        """
        try:
            if not uids:
                return {}

            # Select folder (quote for RFC 3501 compliance)
            quoted_folder = self._quote_folder_name(folder)
            status, _ = self._connection.select(quoted_folder)
            if status != 'OK':
                raise SyncError(f"Failed to select folder {folder}")

            # Fetch flags for multiple UIDs
            uid_set = ','.join(str(uid) for uid in uids)
            status, data = self._connection.uid('FETCH', uid_set, '(FLAGS)')

            if status != 'OK':
                raise SyncError(f"UID FETCH FLAGS failed: {data}")

            # Parse response
            result = {}
            for item in data:
                if isinstance(item, tuple) and len(item) >= 2:
                    # Parse UID and FLAGS from response
                    # Example: b'1234 (UID 1234 FLAGS (\\Seen \\Flagged))'
                    response_str = item[0].decode() if isinstance(item[0], bytes) else item[0]

                    import re
                    uid_match = re.search(r'UID (\d+)', response_str)
                    flags_match = re.search(r'FLAGS \(([^)]*)\)', response_str)

                    if uid_match:
                        uid = int(uid_match.group(1))
                        flags_str = flags_match.group(1) if flags_match else ""

                        result[uid] = {
                            'is_read': '\\Seen' in flags_str,
                            'is_flagged': '\\Flagged' in flags_str
                        }

            return result

        except Exception as e:
            self.logger.error(f"Failed to fetch flags for UIDs: {e}")
            raise SyncError(f"Failed to fetch flags: {e}")

    def list_folders(self) -> List[Dict[str, Any]]:
        """
        List all folders/mailboxes available on the server.

        Returns:
            List of dicts with folder information:
            [{'name': 'INBOX', 'delimiter': '/', 'flags': ['\\HasNoChildren']}]
        """
        try:
            # LIST command to get all folders
            status, folders = self._connection.list()

            if status != 'OK':
                raise SyncError(f"Failed to list folders: {folders}")

            result = []
            for folder_data in folders:
                if not folder_data:
                    continue

                # Parse folder list response
                # Example: b'(\\HasNoChildren) "/" "INBOX"'
                folder_str = folder_data.decode() if isinstance(folder_data, bytes) else folder_data

                import re
                # Match: (flags) "delimiter" "name"
                match = re.match(r'\(([^)]*)\)\s+"([^"]*)"\s+"?([^"]*)"?', folder_str)
                if match:
                    flags_str = match.group(1)
                    delimiter = match.group(2)
                    name = match.group(3)

                    flags = [f.strip() for f in flags_str.split()] if flags_str else []

                    # Check if folder is selectable (not \Noselect)
                    selectable = '\\Noselect' not in flags
                    has_children = '\\HasChildren' in flags

                    result.append({
                        'name': name,
                        'delimiter': delimiter,
                        'flags': flags,
                        'selectable': selectable,
                        'has_children': has_children
                    })

            return result

        except Exception as e:
            self.logger.error(f"Failed to list folders: {e}")
            raise SyncError(f"Failed to list folders: {e}")

    def check_capabilities(self) -> Dict[str, bool]:
        """
        Check server capabilities (CONDSTORE, QRESYNC, IDLE, etc.).

        Returns:
            Dict of capabilities: {'CONDSTORE': True, 'QRESYNC': False, 'IDLE': True}
        """
        try:
            # CAPABILITY command
            status, capabilities = self._connection.capability()

            if status != 'OK':
                raise SyncError(f"Failed to check capabilities: {capabilities}")

            # Parse capabilities
            cap_bytes = capabilities[0] if capabilities else b''
            cap_str = cap_bytes.decode() if isinstance(cap_bytes, bytes) else cap_bytes
            cap_list = cap_str.upper().split()

            return {
                'CONDSTORE': 'CONDSTORE' in cap_list,
                'QRESYNC': 'QRESYNC' in cap_list,
                'IDLE': 'IDLE' in cap_list,
                'UIDPLUS': 'UIDPLUS' in cap_list,
                'MOVE': 'MOVE' in cap_list,
                'COMPRESS': 'COMPRESS=DEFLATE' in cap_list,
            }

        except Exception as e:
            self.logger.error(f"Failed to check capabilities: {e}")
            return {
                'CONDSTORE': False,
                'QRESYNC': False,
                'IDLE': False,
                'UIDPLUS': False,
                'MOVE': False,
                'COMPRESS': False,
            }
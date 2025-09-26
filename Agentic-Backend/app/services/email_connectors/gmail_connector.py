"""
Gmail API Connector

Implements email synchronization using the Gmail API.
Supports OAuth2 authentication and efficient incremental syncing.
"""

import base64
import email
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
from urllib.parse import urlencode

from .base_connector import (
    BaseEmailConnector,
    EmailMessage,
    EmailAttachment,
    AuthCredentials,
    SyncSettings,
    SyncType,
    AuthenticationError,
    ConnectionError,
    SyncError
)


class GmailConnector(BaseEmailConnector):
    """
    Gmail API connector for email synchronization.

    Uses Gmail API v1 with OAuth2 authentication to sync emails
    efficiently while respecting rate limits.
    """

    def __init__(self, account_id: str, credentials: AuthCredentials, settings: SyncSettings):
        super().__init__(account_id, credentials, settings)
        self.base_url = "https://gmail.googleapis.com/gmail/v1"
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.session = None
        self._load_credentials()

    def _load_credentials(self):
        """Load OAuth2 credentials from the credentials object."""
        if self.credentials.auth_type != "oauth2":
            raise AuthenticationError("Gmail connector requires OAuth2 authentication")

        creds = self.credentials.credentials
        self.access_token = creds.get("access_token")
        self.refresh_token = creds.get("refresh_token")
        self.client_id = creds.get("client_id")
        self.client_secret = creds.get("client_secret")

        if creds.get("expires_at"):
            self.token_expires_at = datetime.fromisoformat(creds["expires_at"])

    async def connect(self) -> bool:
        """Establish connection to Gmail API."""
        try:
            self.session = aiohttp.ClientSession()

            # Check if token needs refresh
            if self._token_needs_refresh():
                await self._refresh_access_token()

            # Test the connection
            await self._make_api_request("GET", "/users/me/profile")
            self._connected = True
            self.logger.info("Successfully connected to Gmail API")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Gmail API: {e}")
            raise ConnectionError(f"Gmail connection failed: {str(e)}")

    async def disconnect(self) -> None:
        """Close connection to Gmail API."""
        if self.session:
            await self.session.close()
            self.session = None
        self._connected = False
        self.logger.info("Disconnected from Gmail API")

    async def test_connection(self) -> bool:
        """Test if the Gmail API connection is working."""
        try:
            response = await self._make_api_request("GET", "/users/me/profile")
            return response.get("emailAddress") is not None
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    async def get_folders(self) -> List[Dict[str, Any]]:
        """Get Gmail labels (equivalent to folders)."""
        try:
            response = await self._make_api_request("GET", "/users/me/labels")
            labels = response.get("labels", [])

            folders = []
            for label in labels:
                folders.append({
                    "id": label["id"],
                    "name": label["name"],
                    "type": label.get("type", "user"),
                    "messages_total": label.get("messagesTotal", 0),
                    "messages_unread": label.get("messagesUnread", 0),
                    "threads_total": label.get("threadsTotal", 0),
                    "threads_unread": label.get("threadsUnread", 0)
                })

            return folders

        except Exception as e:
            self.logger.error(f"Failed to get Gmail labels: {e}")
            raise SyncError(f"Failed to retrieve folders: {str(e)}")

    async def sync_emails(
        self,
        sync_type: SyncType = SyncType.INCREMENTAL,
        last_sync_time: Optional[datetime] = None
    ) -> AsyncIterator[EmailMessage]:
        """
        Sync emails from Gmail using the Gmail API.

        Args:
            sync_type: Type of synchronization
            last_sync_time: Last sync time for incremental sync

        Yields:
            EmailMessage: Individual email messages
        """
        try:
            # Build query parameters
            query_params = []

            # Add date filter for sync
            if sync_type == SyncType.INCREMENTAL and last_sync_time:
                # Gmail API uses epoch timestamp
                after_timestamp = int(last_sync_time.timestamp())
                query_params.append(f"after:{after_timestamp}")
            elif sync_type == SyncType.FULL:
                # For full sync, respect sync_days_back configuration
                sync_days_back = getattr(self.settings, 'sync_days_back', None)
                if sync_days_back:
                    cutoff_date = datetime.now() - timedelta(days=sync_days_back)
                    after_timestamp = int(cutoff_date.timestamp())
                    query_params.append(f"after:{after_timestamp}")

            # Add folder filters
            if self.settings.folders_to_sync:
                for folder in self.settings.folders_to_sync:
                    if folder.upper() == "INBOX":
                        query_params.append("in:inbox")
                    else:
                        query_params.append(f"label:{folder}")

            # Exclude spam and trash if configured
            if not self.settings.include_spam:
                query_params.append("-in:spam")
            if not self.settings.include_trash:
                query_params.append("-in:trash")

            query = " ".join(query_params) if query_params else ""

            # Get message list
            page_token = None
            processed = 0

            while True:
                # Apply configured email limit
                max_emails_limit = getattr(self.settings, 'max_emails_limit', None) or 5000
                batch_size = min(self.settings.max_emails_per_batch, 500)

                # Get list of message IDs
                list_params = {
                    "maxResults": batch_size,
                    "q": query
                }
                if page_token:
                    list_params["pageToken"] = page_token

                list_response = await self._make_api_request(
                    "GET", "/users/me/messages", params=list_params
                )

                message_ids = [msg["id"] for msg in list_response.get("messages", [])]

                if not message_ids:
                    break

                # Fetch detailed message data in batches
                for i in range(0, len(message_ids), 10):  # Process in smaller batches
                    batch_ids = message_ids[i:i+10]
                    batch_tasks = [
                        self._get_message_details(msg_id) for msg_id in batch_ids
                    ]

                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                    for result in batch_results:
                        if isinstance(result, Exception):
                            self.logger.warning(f"Failed to fetch message: {result}")
                            continue

                        if result:
                            yield result
                            processed += 1

                            # Check if we've reached the email limit
                            if processed >= max_emails_limit:
                                self.logger.info(f"Reached email limit of {max_emails_limit}, stopping sync")
                                return

                        # Rate limiting
                        if self.settings.rate_limit_delay_ms > 0:
                            await asyncio.sleep(self.settings.rate_limit_delay_ms / 1000)

                # Check for next page
                page_token = list_response.get("nextPageToken")
                if not page_token:
                    break

                self.logger.info(f"Processed {processed} emails so far...")

            self.logger.info(f"Gmail sync completed. Processed {processed} emails.")

        except Exception as e:
            self.logger.error(f"Gmail sync failed: {e}")
            raise SyncError(f"Gmail synchronization failed: {str(e)}")

    async def get_email_by_id(self, message_id: str) -> Optional[EmailMessage]:
        """Get a specific email by message ID."""
        try:
            return await self._get_message_details(message_id)
        except Exception as e:
            self.logger.error(f"Failed to get email {message_id}: {e}")
            return None

    async def download_attachment(
        self,
        message_id: str,
        attachment_id: str
    ) -> Optional[EmailAttachment]:
        """Download a Gmail attachment."""
        try:
            response = await self._make_api_request(
                "GET",
                f"/users/me/messages/{message_id}/attachments/{attachment_id}"
            )

            if "data" in response:
                # Decode base64 attachment data
                attachment_data = base64.urlsafe_b64decode(response["data"])

                return EmailAttachment(
                    attachment_id=attachment_id,
                    filename="attachment",  # Gmail API doesn't always provide filename
                    content_type=None,
                    size_bytes=response.get("size", len(attachment_data)),
                    data=attachment_data
                )

        except Exception as e:
            self.logger.error(f"Failed to download attachment {attachment_id}: {e}")

        return None

    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a Gmail message as read."""
        try:
            await self._make_api_request(
                "POST",
                f"/users/me/messages/{message_id}/modify",
                data={"removeLabelIds": ["UNREAD"]}
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark message as read: {e}")
            return False

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get Gmail sync status and statistics."""
        try:
            profile = await self._make_api_request("GET", "/users/me/profile")
            labels = await self.get_folders()

            inbox_label = next((l for l in labels if l["name"] == "INBOX"), {})

            return {
                "provider": "gmail",
                "email_address": profile.get("emailAddress"),
                "total_messages": profile.get("messagesTotal", 0),
                "total_threads": profile.get("threadsTotal", 0),
                "inbox_messages": inbox_label.get("messages_total", 0),
                "inbox_unread": inbox_label.get("messages_unread", 0),
                "quota_used": profile.get("historyId"),  # Can be used to track changes
                "last_history_id": profile.get("historyId"),
                "folders_count": len(labels)
            }

        except Exception as e:
            self.logger.error(f"Failed to get sync status: {e}")
            return {"provider": "gmail", "error": str(e)}

    # Private helper methods

    async def _get_message_details(self, message_id: str) -> Optional[EmailMessage]:
        """Fetch detailed message information from Gmail API."""
        try:
            response = await self._make_api_request(
                "GET",
                f"/users/me/messages/{message_id}",
                params={"format": "full"}
            )

            return self._parse_gmail_message(response)

        except Exception as e:
            self.logger.warning(f"Failed to get message details for {message_id}: {e}")
            return None

    def _parse_gmail_message(self, gmail_message: Dict[str, Any]) -> EmailMessage:
        """Parse Gmail API message response into EmailMessage object."""
        headers = {}
        payload = gmail_message.get("payload", {})

        # Extract headers
        for header in payload.get("headers", []):
            headers[header["name"].lower()] = header["value"]

        # Extract body content
        body_text = None
        body_html = None
        attachments = []

        self._extract_message_parts(payload, headers, attachments, body_text, body_html)

        # Parse recipients
        recipients = self._parse_recipients(headers.get("to", ""))
        cc_recipients = self._parse_recipients(headers.get("cc", ""))
        bcc_recipients = self._parse_recipients(headers.get("bcc", ""))

        # Extract sender info
        sender_email, sender_name = self._extract_email_address(headers.get("from", ""))

        # Parse dates
        sent_at = self._parse_gmail_date(headers.get("date"))
        received_at = datetime.fromtimestamp(int(gmail_message["internalDate"]) / 1000)

        # Extract labels/folders
        labels = gmail_message.get("labelIds", [])

        return EmailMessage(
            message_id=gmail_message["id"],
            thread_id=gmail_message.get("threadId"),
            subject=headers.get("subject"),
            sender_email=sender_email,
            sender_name=sender_name,
            recipients=recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            body_text=body_text,
            body_html=body_html,
            sent_at=sent_at,
            received_at=received_at,
            folder_path="INBOX" if "INBOX" in labels else labels[0] if labels else None,
            labels=labels,
            has_attachments=len(attachments) > 0,
            attachments=attachments,
            is_read="UNREAD" not in labels,
            is_flagged="STARRED" in labels,
            size_bytes=gmail_message.get("sizeEstimate"),
            raw_headers=headers,
            provider_data={
                "gmail_id": gmail_message["id"],
                "thread_id": gmail_message.get("threadId"),
                "label_ids": labels,
                "snippet": gmail_message.get("snippet"),
                "history_id": gmail_message.get("historyId")
            }
        )

    def _extract_message_parts(
        self,
        part: Dict[str, Any],
        headers: Dict[str, str],
        attachments: List[Dict[str, Any]],
        body_text: Optional[str],
        body_html: Optional[str]
    ) -> tuple:
        """Recursively extract body text and attachments from message parts."""
        mime_type = part.get("mimeType", "")

        if "body" in part and part["body"].get("data"):
            data = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")

            if mime_type == "text/plain":
                body_text = data
            elif mime_type == "text/html":
                body_html = data

        # Check for attachments
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            attachments.append({
                "attachment_id": part["body"]["attachmentId"],
                "filename": part["filename"],
                "content_type": mime_type,
                "size_bytes": part["body"].get("size", 0)
            })

        # Recursively process parts
        for subpart in part.get("parts", []):
            self._extract_message_parts(subpart, headers, attachments, body_text, body_html)

        return body_text, body_html

    def _parse_recipients(self, recipients_string: str) -> List[Dict[str, str]]:
        """Parse recipients string into list of email/name dicts."""
        if not recipients_string:
            return []

        recipients = []
        # Simple parsing - can be enhanced for complex cases
        for recipient in recipients_string.split(","):
            email, name = self._extract_email_address(recipient.strip())
            recipients.append({"email": email, "name": name})

        return recipients

    def _parse_gmail_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse Gmail date string into datetime object."""
        if not date_string:
            return None

        try:
            # Gmail uses RFC 2822 format
            from email.utils import parsedate_to_datetime
            from datetime import timezone
            parsed_date = parsedate_to_datetime(date_string)
            # If the parsed date is timezone-naive, assume UTC
            if parsed_date and parsed_date.tzinfo is None:
                return parsed_date.replace(tzinfo=timezone.utc)
            return parsed_date
        except Exception:
            return None

    def _token_needs_refresh(self) -> bool:
        """Check if access token needs to be refreshed."""
        if not self.access_token:
            return True

        if self.token_expires_at:
            # Refresh if token expires within 5 minutes
            return datetime.utcnow() >= (self.token_expires_at - timedelta(minutes=5))

        return False

    async def _refresh_access_token(self) -> None:
        """Refresh OAuth2 access token."""
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available")

        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }

            async with self.session.post(
                "https://oauth2.googleapis.com/token",
                data=data
            ) as response:
                if response.status != 200:
                    raise AuthenticationError("Failed to refresh access token")

                token_data = await response.json()
                self.access_token = token_data["access_token"]

                if "expires_in" in token_data:
                    expires_in = int(token_data["expires_in"])
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                self.logger.info("Successfully refreshed Gmail access token")

        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {str(e)}")

    async def _make_api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Gmail API."""
        if not self.session:
            raise ConnectionError("Not connected to Gmail API")

        if not self.access_token:
            raise AuthenticationError("No access token available")

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        if method == "GET":
            async with self.session.get(url, headers=headers, params=params) as response:
                return await self._handle_api_response(response)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            async with self.session.post(
                url, headers=headers, params=params, json=data
            ) as response:
                return await self._handle_api_response(response)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    async def _handle_api_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle Gmail API response and errors."""
        if response.status == 401:
            raise AuthenticationError("Gmail API authentication failed")
        elif response.status == 403:
            raise AuthenticationError("Gmail API access forbidden")
        elif response.status == 429:
            # Rate limit exceeded
            await asyncio.sleep(1)  # Simple backoff
            raise SyncError("Gmail API rate limit exceeded")
        elif response.status >= 400:
            error_text = await response.text()
            raise SyncError(f"Gmail API error {response.status}: {error_text}")

        try:
            return await response.json()
        except Exception as e:
            raise SyncError(f"Failed to parse Gmail API response: {str(e)}")
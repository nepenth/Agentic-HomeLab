"""
Base Email Connector

Defines the interface and common functionality for all email connectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncIterator, Tuple
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class EmailConnectorError(Exception):
    """Base exception for email connector errors."""
    pass


class AuthenticationError(EmailConnectorError):
    """Raised when authentication fails."""
    pass


class ConnectionError(EmailConnectorError):
    """Raised when connection to email provider fails."""
    pass


class SyncError(EmailConnectorError):
    """Raised when email synchronization fails."""
    pass


class SyncType(Enum):
    """Types of email synchronization."""
    FULL = "full"
    INCREMENTAL = "incremental"
    MANUAL = "manual"


@dataclass
class EmailMessage:
    """Represents an email message from any provider."""
    message_id: str
    thread_id: Optional[str]
    subject: Optional[str]
    sender_email: Optional[str]
    sender_name: Optional[str]
    recipients: List[Dict[str, str]]  # [{"email": "...", "name": "..."}]
    cc_recipients: List[Dict[str, str]] = field(default_factory=list)
    bcc_recipients: List[Dict[str, str]] = field(default_factory=list)
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    snippet: Optional[str] = None  # Short preview of email body (for UI display)
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    folder_path: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    has_attachments: bool = False
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    importance_level: Optional[str] = None  # high, normal, low

    # IMAP RFC 3501 standard flags
    is_read: bool = False      # \Seen - Message has been read
    is_flagged: bool = False   # \Flagged - Message is flagged for urgent/special attention
    is_deleted: bool = False   # \Deleted - Message is marked for deletion
    is_draft: bool = False     # \Draft - Message is a draft
    is_answered: bool = False  # \Answered - Message has been answered

    size_bytes: Optional[int] = None
    raw_headers: Dict[str, str] = field(default_factory=dict)
    provider_data: Dict[str, Any] = field(default_factory=dict)  # Provider-specific data

    # UID-based sync fields (Phase 2)
    imap_uid: Optional[int] = None  # IMAP UID (unique within folder)
    uid_validity: Optional[int] = None  # UIDVALIDITY (changes when mailbox reset)


@dataclass
class EmailAttachment:
    """Represents an email attachment."""
    attachment_id: str
    filename: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    content_id: Optional[str] = None  # For inline attachments
    is_inline: bool = False
    data: Optional[bytes] = None  # Actual file content (if downloaded)


@dataclass
class EmailSyncResult:
    """Result of an email synchronization operation."""
    sync_type: SyncType
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    emails_processed: int = 0
    emails_added: int = 0
    emails_updated: int = 0
    emails_skipped: int = 0
    attachments_processed: int = 0
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    # VALIDATION METRICS
    total_emails_in_mailbox: Optional[int] = None
    emails_within_date_range: Optional[int] = None
    emails_missing_due_to_limits: int = 0
    validation_warnings: List[str] = field(default_factory=list)
    sync_gaps_detected: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AuthCredentials:
    """Authentication credentials for email providers."""
    auth_type: str  # oauth2, password, app_password
    credentials: Dict[str, Any]  # Provider-specific credentials


@dataclass
class SyncSettings:
    """Settings for email synchronization."""
    folders_to_sync: List[str] = field(default_factory=lambda: ["INBOX"])
    sync_attachments: bool = True
    max_attachment_size_mb: int = 25
    date_range_days: Optional[int] = None  # None = sync all emails
    include_spam: bool = False
    include_trash: bool = False
    max_emails_per_batch: int = 100
    rate_limit_delay_ms: int = 100


class BaseEmailConnector(ABC):
    """
    Abstract base class for all email connectors.

    Defines the interface that all email connectors must implement
    to ensure consistent behavior across different email providers.
    """

    def __init__(self, account_id: str, credentials: AuthCredentials, settings: SyncSettings):
        self.account_id = account_id
        self.credentials = credentials
        self.settings = settings
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{account_id}")
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the email provider.

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the email provider."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the connection is working properly.

        Returns:
            bool: True if connection is healthy
        """
        pass

    @abstractmethod
    async def get_folders(self) -> List[Dict[str, Any]]:
        """
        Get list of available folders/labels.

        Returns:
            List of folders with metadata
        """
        pass

    @abstractmethod
    async def sync_emails(
        self,
        sync_type: SyncType = SyncType.INCREMENTAL,
        last_sync_time: Optional[datetime] = None
    ) -> AsyncIterator[EmailMessage]:
        """
        Sync emails from the provider.

        Args:
            sync_type: Type of synchronization to perform
            last_sync_time: Last successful sync time (for incremental sync)

        Yields:
            EmailMessage: Individual email messages

        Raises:
            SyncError: If synchronization fails
        """
        pass

    @abstractmethod
    async def get_email_by_id(self, message_id: str) -> Optional[EmailMessage]:
        """
        Retrieve a specific email by its ID.

        Args:
            message_id: Provider-specific message identifier

        Returns:
            EmailMessage if found, None otherwise
        """
        pass

    @abstractmethod
    async def download_attachment(
        self,
        message_id: str,
        attachment_id: str
    ) -> Optional[EmailAttachment]:
        """
        Download a specific email attachment.

        Args:
            message_id: Email message ID
            attachment_id: Attachment identifier

        Returns:
            EmailAttachment with data if successful, None otherwise
        """
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read.

        Args:
            message_id: Email message ID

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current synchronization status and statistics.

        Returns:
            Dictionary with sync status information
        """
        pass

    # Common utility methods

    def is_connected(self) -> bool:
        """Check if connector is currently connected."""
        return self._connected

    def get_account_id(self) -> str:
        """Get the account ID this connector is associated with."""
        return self.account_id

    def get_provider_name(self) -> str:
        """Get the name of the email provider."""
        return self.__class__.__name__.replace("Connector", "").lower()

    async def perform_health_check(self) -> bool:
        """
        Perform a health check on the email connection.

        Returns:
            bool: True if connection is healthy
        """
        try:
            if not await self.connect():
                return False
            return await self.test_connection()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
        finally:
            try:
                await self.disconnect()
            except Exception:
                pass

    def _extract_email_address(self, email_string: str) -> Tuple[str, str]:
        """
        Extract email address and name from email string.

        Args:
            email_string: String like "John Doe <john@example.com>" or "john@example.com"

        Returns:
            Tuple of (email, name)
        """
        import re

        # Pattern to match "Name <email@domain.com>" format
        match = re.match(r'^(.*?)\s*<(.+?)>$', email_string.strip())
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return email, name
        else:
            # Just an email address
            return email_string.strip(), ""

    def _calculate_importance_score(self, email: EmailMessage) -> float:
        """
        Calculate importance score based on email characteristics.

        Args:
            email: Email message to analyze

        Returns:
            float: Importance score between 0.0 and 1.0
        """
        score = 0.5  # Base score

        # Check for importance indicators in subject
        if email.subject:
            urgent_keywords = ['urgent', 'asap', 'important', 'priority', 'critical']
            subject_lower = email.subject.lower()
            for keyword in urgent_keywords:
                if keyword in subject_lower:
                    score += 0.2
                    break

        # Check provider importance level
        if email.importance_level == 'high':
            score += 0.3
        elif email.importance_level == 'low':
            score -= 0.2

        # Check if flagged
        if email.is_flagged:
            score += 0.2

        # Ensure score is within bounds
        return max(0.0, min(1.0, score))

    def _categorize_email(self, email: EmailMessage) -> str:
        """
        Automatically categorize email based on content and sender.

        Args:
            email: Email message to categorize

        Returns:
            str: Category name
        """
        # Simple categorization logic - can be enhanced with ML
        categories = {
            'finance': ['bank', 'payment', 'invoice', 'billing', 'transaction'],
            'travel': ['flight', 'hotel', 'booking', 'itinerary', 'travel'],
            'work': ['meeting', 'project', 'deadline', 'report', 'business'],
            'social': ['invitation', 'event', 'party', 'celebration'],
            'shopping': ['order', 'shipping', 'delivery', 'purchase', 'cart'],
            'newsletters': ['unsubscribe', 'newsletter', 'digest', 'updates']
        }

        text_to_check = ""
        if email.subject:
            text_to_check += email.subject.lower() + " "
        if email.sender_email:
            text_to_check += email.sender_email.lower() + " "
        if email.body_text:
            text_to_check += email.body_text[:200].lower()  # First 200 chars

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return category

        return 'general'
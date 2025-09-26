"""
Email Connector System

This module provides connectors for various email providers to enable
synchronization of email data into the local database.

Supported Providers:
- Gmail API
- Outlook/Exchange
- IMAP (Generic)
- Yahoo (via IMAP)
- Custom IMAP servers
"""

from .base_connector import BaseEmailConnector, EmailConnectorError, EmailSyncResult
from .gmail_connector import GmailConnector
from .connector_factory import EmailConnectorFactory

# TODO: Add these connectors when implemented
# from .outlook_connector import OutlookConnector
# from .imap_connector import IMAPConnector

__all__ = [
    "BaseEmailConnector",
    "EmailConnectorError",
    "EmailSyncResult",
    "GmailConnector",
    "EmailConnectorFactory"
]
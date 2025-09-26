"""
Email Connector Factory

Creates and manages email connectors for different providers.
Supports Gmail, Outlook, IMAP, and custom email providers.
"""

from typing import Dict, Any, Optional, Type, List
from app.utils.logging import get_logger

from .base_connector import BaseEmailConnector, AuthCredentials, SyncSettings
from .gmail_connector import GmailConnector
from .imap_connector import IMAPConnector

logger = get_logger("connector_factory")


class EmailConnectorFactory:
    """Factory for creating email connectors based on provider type."""

    def __init__(self):
        self.logger = get_logger("connector_factory")
        self._connector_registry: Dict[str, Type[BaseEmailConnector]] = {
            "gmail": GmailConnector,
            "imap": IMAPConnector,
            # Add other connectors as they're implemented
            # "outlook": OutlookConnector,
        }

    async def create_connector(
        self,
        account_type: str,
        account_id: str,
        credentials: Dict[str, Any],
        settings: Dict[str, Any]
    ) -> Optional[BaseEmailConnector]:
        """
        Create an email connector for the specified account type.

        Args:
            account_type: Type of email account (gmail, outlook, imap, etc.)
            account_id: Unique account identifier
            credentials: Authentication credentials
            settings: Sync settings and preferences

        Returns:
            BaseEmailConnector instance or None if unsupported
        """
        try:
            # Normalize account type
            account_type_lower = account_type.lower()

            if account_type_lower not in self._connector_registry:
                self.logger.error(f"Unsupported account type: {account_type}")
                return None

            # Get connector class
            connector_class = self._connector_registry[account_type_lower]

            # Create auth credentials object
            auth_credentials = AuthCredentials(
                auth_type=credentials.get("auth_type", "oauth2"),
                credentials=credentials
            )

            # Create sync settings object
            sync_settings = SyncSettings(
                folders_to_sync=settings.get("folders_to_sync", ["INBOX"]),
                sync_attachments=settings.get("sync_attachments", True),
                max_attachment_size_mb=settings.get("max_attachment_size_mb", 25),
                date_range_days=settings.get("date_range_days"),
                include_spam=settings.get("include_spam", False),
                include_trash=settings.get("include_trash", False),
                max_emails_per_batch=settings.get("max_emails_per_batch", 100),
                rate_limit_delay_ms=settings.get("rate_limit_delay_ms", 100)
            )

            # Add the configured sync limits to the settings object as dynamic attributes
            # This allows the connectors to access them via getattr()
            if "sync_days_back" in settings:
                setattr(sync_settings, "sync_days_back", settings["sync_days_back"])
            if "max_emails_limit" in settings:
                setattr(sync_settings, "max_emails_limit", settings["max_emails_limit"])

            # Create and return connector instance
            connector = connector_class(account_id, auth_credentials, sync_settings)

            self.logger.info(f"Created {account_type} connector for account {account_id}")
            return connector

        except Exception as e:
            self.logger.error(f"Error creating connector for {account_type}: {e}")
            return None

    def get_supported_providers(self) -> List[str]:
        """Get list of supported email providers."""
        return list(self._connector_registry.keys())

    def register_connector(
        self,
        provider_name: str,
        connector_class: Type[BaseEmailConnector]
    ) -> None:
        """
        Register a new connector type.

        Args:
            provider_name: Name of the email provider
            connector_class: Connector class that implements BaseEmailConnector
        """
        if not issubclass(connector_class, BaseEmailConnector):
            raise ValueError("Connector class must inherit from BaseEmailConnector")

        self._connector_registry[provider_name.lower()] = connector_class
        self.logger.info(f"Registered connector for provider: {provider_name}")

    def validate_credentials(
        self,
        account_type: str,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate credentials for a specific account type.

        Args:
            account_type: Type of email account
            credentials: Credentials to validate

        Returns:
            Dict with validation result
        """
        try:
            account_type_lower = account_type.lower()

            if account_type_lower not in self._connector_registry:
                return {
                    "valid": False,
                    "error": f"Unsupported account type: {account_type}"
                }

            # Provider-specific validation
            if account_type_lower == "gmail":
                return self._validate_gmail_credentials(credentials)
            elif account_type_lower == "outlook":
                return self._validate_outlook_credentials(credentials)
            elif account_type_lower == "imap":
                return self._validate_imap_credentials(credentials)
            else:
                return {"valid": True}  # Generic validation

        except Exception as e:
            return {
                "valid": False,
                "error": f"Credential validation error: {str(e)}"
            }

    def _validate_gmail_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Gmail OAuth2 credentials."""
        required_fields = ["access_token", "refresh_token", "client_id", "client_secret"]

        for field in required_fields:
            if field not in credentials:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}"
                }

        # Additional validation
        if not credentials["access_token"]:
            return {
                "valid": False,
                "error": "Access token is empty"
            }

        return {"valid": True}

    def _validate_outlook_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Outlook/Exchange credentials."""
        auth_type = credentials.get("auth_type", "oauth2")

        if auth_type == "oauth2":
            required_fields = ["access_token", "refresh_token", "client_id", "client_secret"]
        elif auth_type == "password":
            required_fields = ["username", "password", "server"]
        else:
            return {
                "valid": False,
                "error": f"Unsupported auth type for Outlook: {auth_type}"
            }

        for field in required_fields:
            if field not in credentials:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}"
                }

        return {"valid": True}

    def _validate_imap_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Validate IMAP credentials."""
        required_fields = ["server", "port", "username", "password"]

        for field in required_fields:
            if field not in credentials:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}"
                }

        # Validate port
        try:
            port = int(credentials["port"])
            if port < 1 or port > 65535:
                return {
                    "valid": False,
                    "error": "Port must be between 1 and 65535"
                }
        except ValueError:
            return {
                "valid": False,
                "error": "Port must be a valid integer"
            }

        return {"valid": True}


# Global instance
email_connector_factory = EmailConnectorFactory()
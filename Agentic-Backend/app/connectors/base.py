"""
Universal Content Connector Framework.

This module provides the abstract base classes and interfaces for content connectors
that can discover, fetch, and validate content from various sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from app.services.agentic_http_client import agentic_http_client
from app.utils.logging import get_logger

logger = get_logger("content_connectors")


class ContentType(Enum):
    """Types of content that can be processed."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STRUCTURED = "structured"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ConnectorType(Enum):
    """Types of content connectors."""
    WEB = "web"
    SOCIAL_MEDIA = "social_media"
    COMMUNICATION = "communication"
    FILE_SYSTEM = "file_system"
    API = "api"
    DATABASE = "database"


class ValidationStatus(Enum):
    """Status of content validation."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ContentItem:
    """Represents a discovered content item."""
    id: str
    source: str
    connector_type: ConnectorType
    content_type: ContentType
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    metadata: Dict[str, Any] = None
    discovered_at: datetime = None
    last_modified: Optional[datetime] = None
    size_bytes: Optional[int] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
        if self.discovered_at is None:
            self.discovered_at = datetime.now()


@dataclass
class ContentData:
    """Represents fetched content data."""
    item: ContentItem
    raw_data: bytes
    text_content: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    fetched_at: datetime = None
    processing_time_ms: Optional[float] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.fetched_at is None:
            self.fetched_at = datetime.now()


@dataclass
class ValidationResult:
    """Result of content validation."""
    is_valid: bool
    status: ValidationStatus
    message: str
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    validated_at: datetime = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
        if self.validated_at is None:
            self.validated_at = datetime.now()


@dataclass
class ConnectorConfig:
    """Configuration for a content connector."""
    name: str
    connector_type: ConnectorType
    source_config: Dict[str, Any]
    credentials: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    retry_config: Optional[Dict[str, Any]] = None
    enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContentConnector(ABC):
    """
    Abstract base class for content connectors.

    All content connectors must implement the discover, fetch, and validate methods.
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.logger = get_logger(f"connector_{config.name}")
        self.http_client = agentic_http_client

    @property
    def connector_type(self) -> ConnectorType:
        """Get the connector type."""
        return self.config.connector_type

    @property
    def name(self) -> str:
        """Get the connector name."""
        return self.config.name

    @abstractmethod
    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """
        Discover available content items from the source.

        Args:
            source_config: Configuration specific to the discovery operation

        Returns:
            List of discovered ContentItem objects

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement discover method")

    @abstractmethod
    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """
        Fetch content data for a given content reference.

        Args:
            content_ref: Content reference (ID, URL, or ContentItem)

        Returns:
            ContentData object with fetched content

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement fetch method")

    @abstractmethod
    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """
        Validate content data.

        Args:
            content: ContentData object or raw bytes to validate

        Returns:
            ValidationResult with validation status and details

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement validate method")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the connector.

        Returns:
            Dictionary with health status information
        """
        try:
            # Basic health check - can be overridden by subclasses
            return {
                "status": "healthy",
                "connector_name": self.name,
                "connector_type": self.connector_type.value,
                "enabled": self.config.enabled,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connector_name": self.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get connector capabilities and supported features.

        Returns:
            Dictionary describing connector capabilities
        """
        return {
            "connector_type": self.connector_type.value,
            "supported_content_types": [],
            "authentication_methods": [],
            "rate_limiting": bool(self.config.rate_limits),
            "retry_support": bool(self.config.retry_config),
            "batch_operations": False,
            "real_time_updates": False
        }

    async def cleanup(self):
        """
        Cleanup connector resources.

        This method should be called when the connector is no longer needed
        to release any resources like connections, file handles, etc.
        """
        pass


class ConnectorRegistry:
    """
    Registry for managing content connectors.

    Provides centralized management of all available content connectors.
    """

    def __init__(self):
        self._connectors: Dict[str, ContentConnector] = {}
        self._connector_types: Dict[ConnectorType, List[str]] = {}
        self.logger = get_logger("connector_registry")

    def register(self, connector: ContentConnector):
        """
        Register a content connector.

        Args:
            connector: ContentConnector instance to register
        """
        self._connectors[connector.name] = connector

        # Update type index
        if connector.connector_type not in self._connector_types:
            self._connector_types[connector.connector_type] = []
        self._connector_types[connector.connector_type].append(connector.name)

        self.logger.info(f"Registered connector: {connector.name} ({connector.connector_type.value})")

    def unregister(self, name: str):
        """
        Unregister a content connector.

        Args:
            name: Name of the connector to unregister
        """
        if name in self._connectors:
            connector = self._connectors[name]
            del self._connectors[name]

            # Update type index
            if connector.connector_type in self._connector_types:
                self._connector_types[connector.connector_type].remove(name)
                if not self._connector_types[connector.connector_type]:
                    del self._connector_types[connector.connector_type]

            self.logger.info(f"Unregistered connector: {name}")

    def get_connector(self, name: str) -> Optional[ContentConnector]:
        """
        Get a connector by name.

        Args:
            name: Name of the connector

        Returns:
            ContentConnector instance or None if not found
        """
        return self._connectors.get(name)

    def get_connectors_by_type(self, connector_type: ConnectorType) -> List[ContentConnector]:
        """
        Get all connectors of a specific type.

        Args:
            connector_type: Type of connectors to retrieve

        Returns:
            List of ContentConnector instances
        """
        names = self._connector_types.get(connector_type, [])
        return [self._connectors[name] for name in names if name in self._connectors]

    def list_connectors(self) -> List[Dict[str, Any]]:
        """
        List all registered connectors.

        Returns:
            List of connector information dictionaries
        """
        return [
            {
                "name": name,
                "type": connector.connector_type.value,
                "enabled": connector.config.enabled,
                "capabilities": connector.get_capabilities()
            }
            for name, connector in self._connectors.items()
        ]

    async def health_check_all(self) -> Dict[str, Any]:
        """
        Perform health check on all connectors.

        Returns:
            Dictionary with health status for all connectors
        """
        results = {}
        for name, connector in self._connectors.items():
            try:
                results[name] = await connector.health_check()
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        return {
            "overall_status": "healthy" if all(r["status"] == "healthy" for r in results.values()) else "degraded",
            "connectors": results,
            "total_connectors": len(results),
            "timestamp": datetime.now().isoformat()
        }


# Global connector registry instance
connector_registry = ConnectorRegistry()
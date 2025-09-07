"""
Web Content Connector.

This module provides connectors for web-based content sources including:
- RSS/Atom feeds
- Web scraping
- REST API endpoints
- GraphQL endpoints
"""

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from urllib.parse import urlparse, urljoin
import hashlib

from app.connectors.base import (
    ContentConnector,
    ContentItem,
    ContentData,
    ValidationResult,
    ConnectorConfig,
    ConnectorType,
    ContentType,
    ValidationStatus
)
from app.utils.logging import get_logger

logger = get_logger("web_connector")


class RSSFeedConnector(ContentConnector):
    """Connector for RSS/Atom feeds."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.feed_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content from RSS/Atom feeds."""
        feed_urls = source_config.get("feed_urls", [])
        if not feed_urls:
            raise ValueError("No feed URLs provided")

        all_items = []

        for feed_url in feed_urls:
            try:
                items = await self._discover_feed(feed_url, source_config)
                all_items.extend(items)
            except Exception as e:
                self.logger.error(f"Failed to discover feed {feed_url}: {e}")
                continue

        return all_items

    async def _discover_feed(self, feed_url: str, config: Dict[str, Any]) -> List[ContentItem]:
        """Discover items from a single RSS/Atom feed."""
        # Check cache first
        cache_key = hashlib.md5(feed_url.encode()).hexdigest()
        if cache_key in self.feed_cache:
            cached_data = self.feed_cache[cache_key]
            if (datetime.now() - cached_data["timestamp"]).seconds < self.cache_ttl:
                return cached_data["items"]

        # Fetch feed
        response = await self.http_client.request(
            method="GET",
            url=feed_url,
            headers={"User-Agent": "Agentic-Backend/1.0"},
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch feed: HTTP {response.status_code}")

        # Parse feed
        feed_content = response.text
        items = self._parse_feed(feed_content, feed_url)

        # Cache results
        self.feed_cache[cache_key] = {
            "items": items,
            "timestamp": datetime.now()
        }

        return items

    def _parse_feed(self, content: str, feed_url: str) -> List[ContentItem]:
        """Parse RSS/Atom feed content."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            raise ValueError("Invalid XML feed format")

        items = []

        # Detect feed type
        if root.tag == "{http://www.w3.org/2005/Atom}feed":
            # Atom feed
            entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for entry in entries:
                item = self._parse_atom_entry(entry, feed_url)
                if item:
                    items.append(item)
        else:
            # RSS feed
            rss_items = root.findall(".//item")
            for rss_item in rss_items:
                item = self._parse_rss_item(rss_item, feed_url)
                if item:
                    items.append(item)

        return items

    def _parse_atom_entry(self, entry, feed_url: str) -> Optional[ContentItem]:
        """Parse an Atom entry."""
        try:
            # Extract basic information
            id_elem = entry.find(".//{http://www.w3.org/2005/Atom}id")
            title_elem = entry.find(".//{http://www.w3.org/2005/Atom}title")
            content_elem = entry.find(".//{http://www.w3.org/2005/Atom}content")
            summary_elem = entry.find(".//{http://www.w3.org/2005/Atom}summary")
            updated_elem = entry.find(".//{http://www.w3.org/2005/Atom}updated")
            link_elem = entry.find(".//{http://www.w3.org/2005/Atom}link[@rel='alternate']")

            if not id_elem or not title_elem:
                return None

            item_id = id_elem.text
            title = title_elem.text or ""
            url = link_elem.get("href") if link_elem is not None else None

            # Extract content
            content = ""
            if content_elem is not None:
                content = content_elem.text or ""
            elif summary_elem is not None:
                content = summary_elem.text or ""

            # Parse date
            published_at = None
            if updated_elem is not None:
                try:
                    published_at = datetime.fromisoformat(updated_elem.text.replace('Z', '+00:00'))
                except ValueError:
                    pass

            return ContentItem(
                id=item_id,
                source=feed_url,
                connector_type=ConnectorType.WEB,
                content_type=ContentType.TEXT,
                title=title,
                description=content[:500] + "..." if len(content) > 500 else content,
                url=url,
                metadata={
                    "feed_type": "atom",
                    "content_length": len(content),
                    "has_content": bool(content_elem is not None),
                    "has_summary": bool(summary_elem is not None)
                },
                last_modified=published_at,
                tags=["rss", "atom", "feed"]
            )
        except Exception as e:
            self.logger.error(f"Failed to parse Atom entry: {e}")
            return None

    def _parse_rss_item(self, item, feed_url: str) -> Optional[ContentItem]:
        """Parse an RSS item."""
        try:
            # Extract basic information
            guid_elem = item.find("guid")
            title_elem = item.find("title")
            description_elem = item.find("description")
            link_elem = item.find("link")
            pub_date_elem = item.find("pubDate")

            if not title_elem:
                return None

            # Use GUID as ID, fallback to link or title hash
            if guid_elem is not None:
                item_id = guid_elem.text
            elif link_elem is not None:
                item_id = link_elem.text
            else:
                item_id = hashlib.md5(title_elem.text.encode()).hexdigest()

            title = title_elem.text or ""
            url = link_elem.text if link_elem is not None else None

            # Extract description
            description = ""
            if description_elem is not None:
                description = description_elem.text or ""

            # Parse publication date
            published_at = None
            if pub_date_elem is not None:
                try:
                    # RSS date format: "Wed, 02 Oct 2002 13:00:00 GMT"
                    from email.utils import parsedate_to_datetime
                    published_at = parsedate_to_datetime(pub_date_elem.text)
                except (ValueError, TypeError):
                    pass

            return ContentItem(
                id=item_id,
                source=feed_url,
                connector_type=ConnectorType.WEB,
                content_type=ContentType.TEXT,
                title=title,
                description=description[:500] + "..." if len(description) > 500 else description,
                url=url,
                metadata={
                    "feed_type": "rss",
                    "content_length": len(description),
                    "has_guid": bool(guid_elem is not None),
                    "has_description": bool(description_elem is not None)
                },
                last_modified=published_at,
                tags=["rss", "feed"]
            )
        except Exception as e:
            self.logger.error(f"Failed to parse RSS item: {e}")
            return None

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch content data for an RSS item."""
        if isinstance(content_ref, ContentItem):
            item = content_ref
        else:
            # If string, we need to find the item first
            raise ValueError("RSS connector requires ContentItem for fetching")

        # For RSS items, we typically already have the content in the description
        # But we can fetch the full article if URL is available
        start_time = datetime.now()

        if item.url:
            try:
                response = await self.http_client.request(
                    method="GET",
                    url=item.url,
                    headers={"User-Agent": "Agentic-Backend/1.0"},
                    timeout=30.0
                )

                if response.status_code == 200:
                    raw_data = response.content
                    text_content = response.text
                else:
                    raw_data = item.description.encode('utf-8') if item.description else b""
                    text_content = item.description
            except Exception as e:
                self.logger.warning(f"Failed to fetch full content from {item.url}: {e}")
                raw_data = item.description.encode('utf-8') if item.description else b""
                text_content = item.description
        else:
            raw_data = item.description.encode('utf-8') if item.description else b""
            text_content = item.description

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentData(
            item=item,
            raw_data=raw_data,
            text_content=text_content,
            metadata={
                "fetched_from_url": bool(item.url),
                "processing_time_ms": processing_time
            },
            processing_time_ms=processing_time
        )

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate RSS content."""
        if isinstance(content, ContentData):
            text_content = content.text_content or ""
        else:
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = ""

        errors = []
        warnings = []

        # Check content length
        if len(text_content.strip()) == 0:
            errors.append("Content is empty")
        elif len(text_content) < 10:
            warnings.append("Content is very short")

        # Check for basic HTML structure if it's HTML
        if "<html" in text_content.lower() and "</html>" not in text_content.lower():
            warnings.append("HTML content appears to be incomplete")

        # Check for RSS-specific validation
        if isinstance(content, ContentData):
            item = content.item
            if not item.title:
                errors.append("Missing title")
            if not item.id:
                errors.append("Missing ID")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="Content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "content_length": len(text_content),
                "has_title": bool(isinstance(content, ContentData) and content.item.title),
                "has_url": bool(isinstance(content, ContentData) and content.item.url)
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get RSS connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text"],
            "supported_feed_types": ["rss", "atom"],
            "features": ["feed_discovery", "content_fetching", "caching"],
            "authentication_methods": ["none", "basic_auth"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": False
        })
        return capabilities


class WebScrapingConnector(ContentConnector):
    """Connector for web scraping."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.page_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 600  # 10 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content through web scraping."""
        urls = source_config.get("urls", [])
        if not urls:
            raise ValueError("No URLs provided for scraping")

        selectors = source_config.get("selectors", {})
        all_items = []

        for url in urls:
            try:
                items = await self._scrape_url(url, selectors, source_config)
                all_items.extend(items)
            except Exception as e:
                self.logger.error(f"Failed to scrape {url}: {e}")
                continue

        return all_items

    async def _scrape_url(self, url: str, selectors: Dict[str, Any], config: Dict[str, Any]) -> List[ContentItem]:
        """Scrape content from a single URL."""
        # Check cache first
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.page_cache:
            cached_data = self.page_cache[cache_key]
            if (datetime.now() - cached_data["timestamp"]).seconds < self.cache_ttl:
                return cached_data["items"]

        # Fetch page
        response = await self.http_client.request(
            method="GET",
            url=url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Agentic-Backend/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            },
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch page: HTTP {response.status_code}")

        # Parse HTML content
        html_content = response.text
        items = self._parse_html_content(html_content, url, selectors)

        # Cache results
        self.page_cache[cache_key] = {
            "items": items,
            "timestamp": datetime.now()
        }

        return items

    def _parse_html_content(self, html: str, url: str, selectors: Dict[str, Any]) -> List[ContentItem]:
        """Parse HTML content using selectors."""
        items = []

        try:
            # Simple HTML parsing (in production, use BeautifulSoup or similar)
            # For now, we'll extract basic information

            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Untitled Page"

            # Extract meta description
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else ""

            # Create content item
            item_id = hashlib.md5(url.encode()).hexdigest()

            # Determine content type based on URL and content
            content_type = ContentType.TEXT
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                content_type = ContentType.IMAGE
            elif any(ext in url.lower() for ext in ['.mp4', '.avi', '.mov', '.webm']):
                content_type = ContentType.VIDEO
            elif any(ext in url.lower() for ext in ['.mp3', '.wav', '.flac', '.ogg']):
                content_type = ContentType.AUDIO
            elif any(ext in url.lower() for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.pptx']):
                content_type = ContentType.DOCUMENT

            item = ContentItem(
                id=item_id,
                source=url,
                connector_type=ConnectorType.WEB,
                content_type=content_type,
                title=title,
                description=description[:500] + "..." if len(description) > 500 else description,
                url=url,
                metadata={
                    "scraped": True,
                    "content_length": len(html),
                    "has_title": bool(title_match),
                    "has_description": bool(desc_match)
                },
                size_bytes=len(html.encode('utf-8')),
                tags=["web", "scraped", "html"]
            )

            items.append(item)

        except Exception as e:
            self.logger.error(f"Failed to parse HTML content: {e}")

        return items

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch content data for a scraped item."""
        if isinstance(content_ref, str):
            url = content_ref
            item = ContentItem(
                id=hashlib.md5(url.encode()).hexdigest(),
                source=url,
                connector_type=ConnectorType.WEB,
                content_type=ContentType.TEXT,
                url=url
            )
        else:
            item = content_ref
            url = item.url

        if not url:
            raise ValueError("No URL provided for fetching")

        start_time = datetime.now()

        response = await self.http_client.request(
            method="GET",
            url=url,
            headers={"User-Agent": "Agentic-Backend/1.0"},
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch content: HTTP {response.status_code}")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentData(
            item=item,
            raw_data=response.content,
            text_content=response.text,
            metadata={
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "processing_time_ms": processing_time
            },
            processing_time_ms=processing_time
        )

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate scraped content."""
        if isinstance(content, ContentData):
            raw_data = content.raw_data
            text_content = content.text_content or ""
        else:
            raw_data = content
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = ""

        errors = []
        warnings = []

        # Check content size
        if len(raw_data) == 0:
            errors.append("Content is empty")
        elif len(raw_data) < 100:
            warnings.append("Content is very small")

        # Check for HTML structure
        if "<html" in text_content.lower():
            if "</html>" not in text_content.lower():
                warnings.append("HTML content appears incomplete")
        elif len(text_content.strip()) > 0:
            # Check if it's likely binary content
            if len(raw_data) > len(text_content.encode('utf-8')) * 2:
                warnings.append("Content appears to be binary data")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="Web content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "content_size_bytes": len(raw_data),
                "text_length": len(text_content),
                "is_html": "<html" in text_content.lower(),
                "is_binary": len(raw_data) > len(text_content.encode('utf-8')) * 2
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get web scraping connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "image", "video", "audio", "document"],
            "features": ["web_scraping", "html_parsing", "content_extraction", "caching"],
            "authentication_methods": ["none", "basic_auth", "bearer_token"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": False
        })
        return capabilities


class APIEndpointConnector(ContentConnector):
    """Connector for REST API endpoints."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.endpoint_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content from API endpoints."""
        endpoints = source_config.get("endpoints", [])
        if not endpoints:
            raise ValueError("No API endpoints provided")

        all_items = []

        for endpoint_config in endpoints:
            try:
                items = await self._discover_endpoint(endpoint_config, source_config)
                all_items.extend(items)
            except Exception as e:
                self.logger.error(f"Failed to discover from endpoint {endpoint_config.get('url', 'unknown')}: {e}")
                continue

        return all_items

    async def _discover_endpoint(self, endpoint_config: Dict[str, Any], config: Dict[str, Any]) -> List[ContentItem]:
        """Discover items from a single API endpoint."""
        url = endpoint_config.get("url")
        if not url:
            raise ValueError("Endpoint URL is required")

        method = endpoint_config.get("method", "GET")
        headers = endpoint_config.get("headers", {})
        params = endpoint_config.get("params", {})
        data = endpoint_config.get("data", {})

        # Add authentication if configured
        if self.config.credentials:
            if "bearer_token" in self.config.credentials:
                headers["Authorization"] = f"Bearer {self.config.credentials['bearer_token']}"
            elif "api_key" in self.config.credentials:
                headers["X-API-Key"] = self.config.credentials["api_key"]

        # Check cache
        cache_key = hashlib.md5(f"{method}:{url}:{str(params)}:{str(data)}".encode()).hexdigest()
        if cache_key in self.endpoint_cache:
            cached_data = self.endpoint_cache[cache_key]
            if (datetime.now() - cached_data["timestamp"]).seconds < self.cache_ttl:
                return cached_data["items"]

        # Make API request
        response = await self.http_client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json_data=data if method in ["POST", "PUT", "PATCH"] else None,
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"API request failed: HTTP {response.status_code}")

        # Parse response
        try:
            response_data = response.json_data if response.json_data else json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("API response is not valid JSON")

        items = self._parse_api_response(response_data, url, endpoint_config)

        # Cache results
        self.endpoint_cache[cache_key] = {
            "items": items,
            "timestamp": datetime.now()
        }

        return items

    def _parse_api_response(self, data: Dict[str, Any], url: str, config: Dict[str, Any]) -> List[ContentItem]:
        """Parse API response data into ContentItems."""
        items = []

        # Extract items from response based on configuration
        items_path = config.get("items_path", "data")
        id_field = config.get("id_field", "id")
        title_field = config.get("title_field", "title")
        content_field = config.get("content_field", "content")
        url_field = config.get("url_field", "url")

        # Navigate to items in response
        items_data = data
        for path_part in items_path.split("."):
            if isinstance(items_data, dict) and path_part in items_data:
                items_data = items_data[path_part]
            else:
                break

        if not isinstance(items_data, list):
            items_data = [items_data] if items_data else []

        for item_data in items_data:
            if not isinstance(item_data, dict):
                continue

            try:
                item_id = str(item_data.get(id_field, hashlib.md5(str(item_data).encode()).hexdigest()))
                title = item_data.get(title_field, "")
                content = item_data.get(content_field, "")
                item_url = item_data.get(url_field)

                # Determine content type
                content_type = ContentType.TEXT
                if isinstance(content, dict):
                    content_type = ContentType.STRUCTURED
                elif item_url and any(ext in item_url.lower() for ext in ['.jpg', '.png', '.gif']):
                    content_type = ContentType.IMAGE

                item = ContentItem(
                    id=item_id,
                    source=url,
                    connector_type=ConnectorType.WEB,
                    content_type=content_type,
                    title=title,
                    description=str(content)[:500] + "..." if len(str(content)) > 500 else str(content),
                    url=item_url,
                    metadata={
                        "api_endpoint": url,
                        "raw_data": item_data,
                        "content_type_detected": content_type.value
                    },
                    tags=["api", "rest", "json"]
                )

                items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to parse API item: {e}")
                continue

        return items

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch content data from API."""
        if isinstance(content_ref, str):
            # Assume it's an API URL
            url = content_ref
            item = ContentItem(
                id=hashlib.md5(url.encode()).hexdigest(),
                source=url,
                connector_type=ConnectorType.WEB,
                content_type=ContentType.TEXT,
                url=url
            )
        else:
            item = content_ref
            url = item.url

        if not url:
            raise ValueError("No URL provided for fetching")

        start_time = datetime.now()

        response = await self.http_client.request(
            method="GET",
            url=url,
            headers={"Accept": "application/json"},
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch from API: HTTP {response.status_code}")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentData(
            item=item,
            raw_data=response.content,
            text_content=response.text,
            structured_data=response.json_data,
            metadata={
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "processing_time_ms": processing_time
            },
            processing_time_ms=processing_time
        )

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate API content."""
        if isinstance(content, ContentData):
            raw_data = content.raw_data
            structured_data = content.structured_data
        else:
            raw_data = content
            try:
                structured_data = json.loads(content.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                structured_data = None

        errors = []
        warnings = []

        # Check content size
        if len(raw_data) == 0:
            errors.append("Content is empty")

        # Validate JSON structure if present
        if structured_data is not None:
            if not isinstance(structured_data, (dict, list)):
                errors.append("Invalid JSON structure")
        else:
            # Check if content should be JSON
            content_type = ""
            if isinstance(content, ContentData):
                content_type = content.metadata.get("content_type", "")

            if "json" in content_type.lower():
                try:
                    json.loads(raw_data.decode('utf-8'))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("Content-Type indicates JSON but content is not valid JSON")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="API content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "content_size_bytes": len(raw_data),
                "is_json": structured_data is not None,
                "has_structure": isinstance(structured_data, (dict, list))
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get API connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "structured", "image", "video", "audio"],
            "supported_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "features": ["api_calls", "json_parsing", "authentication", "rate_limiting"],
            "authentication_methods": ["none", "bearer_token", "api_key", "basic_auth", "oauth"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": False
        })
        return capabilities
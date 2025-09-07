"""
API Content Connector.

This module provides connectors for various API types including:
- REST APIs
- GraphQL APIs
- WebSocket APIs
- Generic HTTP APIs
"""

import json
import websockets
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable, AsyncGenerator
from datetime import datetime
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

logger = get_logger("api_connector")


class RESTAPIConnector(ContentConnector):
    """Connector for REST APIs."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.endpoint_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content from REST API endpoints."""
        endpoints = source_config.get("endpoints", [])
        if not endpoints:
            raise ValueError("No endpoints provided")

        all_items = []

        for endpoint_config in endpoints:
            try:
                items = await self._discover_endpoint(endpoint_config)
                all_items.extend(items)
            except Exception as e:
                self.logger.error(f"Failed to discover from endpoint {endpoint_config.get('url', 'unknown')}: {e}")
                continue

        return all_items

    async def _discover_endpoint(self, endpoint_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover items from a single REST endpoint."""
        url = endpoint_config.get("url")
        method = endpoint_config.get("method", "GET")
        headers = endpoint_config.get("headers", {})
        params = endpoint_config.get("params", {})
        data = endpoint_config.get("data", {})
        auth_config = endpoint_config.get("auth", {})

        if not url:
            raise ValueError("Endpoint URL is required")

        # Add authentication
        if auth_config.get("type") == "bearer":
            headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"
        elif auth_config.get("type") == "basic":
            # Basic auth would be handled by the HTTP client
            pass

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
            raise Exception(f"REST API error: HTTP {response.status_code}")

        # Parse response
        try:
            response_data = response.json_data if response.json_data else json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("API response is not valid JSON")

        items = self._parse_rest_response(response_data, url, endpoint_config)

        # Cache results
        self.endpoint_cache[cache_key] = {
            "items": items,
            "timestamp": datetime.now()
        }

        return items

    def _parse_rest_response(self, data: Dict[str, Any], url: str, config: Dict[str, Any]) -> List[ContentItem]:
        """Parse REST API response into ContentItems."""
        items = []

        # Extract items from response based on configuration
        items_path = config.get("items_path", "data")
        id_field = config.get("id_field", "id")
        title_field = config.get("title_field", "title")
        content_field = config.get("content_field", "content")
        url_field = config.get("url_field", "url")
        timestamp_field = config.get("timestamp_field", "created_at")

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

                # Parse timestamp
                created_at = None
                if timestamp_field in item_data:
                    try:
                        # Try ISO format first
                        created_at = datetime.fromisoformat(item_data[timestamp_field].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        # Try unix timestamp
                        try:
                            created_at = datetime.fromtimestamp(float(item_data[timestamp_field]))
                        except (ValueError, TypeError):
                            pass

                # Determine content type
                content_type = ContentType.TEXT
                if isinstance(content, dict):
                    content_type = ContentType.STRUCTURED
                elif item_url and any(ext in item_url.lower() for ext in ['.jpg', '.png', '.gif']):
                    content_type = ContentType.IMAGE

                item = ContentItem(
                    id=f"rest_{item_id}",
                    source=f"rest:{url}",
                    connector_type=ConnectorType.API,
                    content_type=content_type,
                    title=title,
                    description=str(content)[:500] + "..." if len(str(content)) > 500 else str(content),
                    url=item_url,
                    metadata={
                        "platform": "rest_api",
                        "endpoint": url,
                        "raw_data": item_data,
                        "content_type_detected": content_type.value,
                        "api_response": True
                    },
                    last_modified=created_at,
                    tags=["rest", "api", "http"]
                )

                items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to parse REST API item: {e}")
                continue

        return items

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch content from REST API."""
        if isinstance(content_ref, str):
            # Assume it's an API URL
            url = content_ref
            item = ContentItem(
                id=hashlib.md5(url.encode()).hexdigest(),
                source=url,
                connector_type=ConnectorType.API,
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
            raise Exception(f"Failed to fetch from REST API: HTTP {response.status_code}")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentData(
            item=item,
            raw_data=response.content,
            text_content=response.text,
            structured_data=response.json_data,
            metadata={
                "fetched_at": datetime.now().isoformat(),
                "processing_time_ms": processing_time
            },
            processing_time_ms=processing_time
        )

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate REST API content."""
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
            errors.append("API response is empty")

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
            message="REST API content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "content_size_bytes": len(raw_data),
                "is_json": structured_data is not None,
                "has_structure": isinstance(structured_data, (dict, list))
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get REST API connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "structured", "image", "video", "audio"],
            "supported_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "features": ["http_methods", "json_parsing", "authentication", "rate_limiting"],
            "authentication_methods": ["none", "bearer_token", "basic_auth", "api_key", "oauth"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": False,
            "real_time_updates": False
        })
        return capabilities


class GraphQLConnector(ContentConnector):
    """Connector for GraphQL APIs."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.query_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content from GraphQL API."""
        endpoint = source_config.get("endpoint")
        queries = source_config.get("queries", [])

        if not endpoint:
            raise ValueError("GraphQL endpoint is required")

        if not queries:
            raise ValueError("No GraphQL queries provided")

        all_items = []

        for query_config in queries:
            try:
                items = await self._execute_query(endpoint, query_config)
                all_items.extend(items)
            except Exception as e:
                self.logger.error(f"Failed to execute GraphQL query: {e}")
                continue

        return all_items

    async def _execute_query(self, endpoint: str, query_config: Dict[str, Any]) -> List[ContentItem]:
        """Execute a GraphQL query."""
        query = query_config.get("query")
        variables = query_config.get("variables", {})
        operation_name = query_config.get("operation_name")

        if not query:
            raise ValueError("GraphQL query is required")

        # Check cache
        cache_key = hashlib.md5(f"{query}:{str(variables)}:{operation_name}".encode()).hexdigest()
        if cache_key in self.query_cache:
            cached_data = self.query_cache[cache_key]
            if (datetime.now() - cached_data["timestamp"]).seconds < self.cache_ttl:
                return cached_data["items"]

        # Prepare GraphQL request
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        headers = {"Content-Type": "application/json"}

        # Add authentication
        if self.config.credentials.get("bearer_token"):
            headers["Authorization"] = f"Bearer {self.config.credentials['bearer_token']}"

        # Execute query
        response = await self.http_client.request(
            method="POST",
            url=endpoint,
            headers=headers,
            json_data=payload,
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"GraphQL API error: HTTP {response.status_code}")

        # Parse GraphQL response
        try:
            response_data = response.json_data if response.json_data else json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("GraphQL response is not valid JSON")

        # Check for GraphQL errors
        if "errors" in response_data:
            errors = response_data["errors"]
            raise Exception(f"GraphQL errors: {errors}")

        # Extract data
        data = response_data.get("data", {})

        items = self._parse_graphql_response(data, query_config)

        # Cache results
        self.query_cache[cache_key] = {
            "items": items,
            "timestamp": datetime.now()
        }

        return items

    def _parse_graphql_response(self, data: Dict[str, Any], query_config: Dict[str, Any]) -> List[ContentItem]:
        """Parse GraphQL response into ContentItems."""
        items = []

        # Extract items from response based on configuration
        data_path = query_config.get("data_path", "")
        id_field = query_config.get("id_field", "id")
        title_field = query_config.get("title_field", "title")
        content_field = query_config.get("content_field", "content")
        url_field = query_config.get("url_field", "url")

        # Navigate to items in response
        items_data = data
        if data_path:
            for path_part in data_path.split("."):
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
                    id=f"graphql_{item_id}",
                    source=f"graphql:{query_config.get('query', '')[:50]}...",
                    connector_type=ConnectorType.API,
                    content_type=content_type,
                    title=title,
                    description=str(content)[:500] + "..." if len(str(content)) > 500 else str(content),
                    url=item_url,
                    metadata={
                        "platform": "graphql",
                        "query": query_config.get("query", ""),
                        "raw_data": item_data,
                        "content_type_detected": content_type.value,
                        "graphql_response": True
                    },
                    tags=["graphql", "api", "query"]
                )

                items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to parse GraphQL item: {e}")
                continue

        return items

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch content from GraphQL API."""
        # For GraphQL, we typically need to execute a specific query
        # This is a simplified implementation
        if isinstance(content_ref, str):
            raise ValueError("GraphQL connector requires ContentItem with query information for fetching")

        # Re-execute the original query to get fresh data
        query_config = content_ref.metadata.get("query_config", {})
        if not query_config:
            raise ValueError("Query configuration not found in ContentItem")

        start_time = datetime.now()

        # This would need the original endpoint - simplified for now
        endpoint = self.config.credentials.get("endpoint", "")
        if not endpoint:
            raise ValueError("GraphQL endpoint not configured")

        items = await self._execute_query(endpoint, query_config)

        # Find the matching item
        matching_item = None
        for item in items:
            if item.id == content_ref.id:
                matching_item = item
                break

        if not matching_item:
            raise ValueError("Item not found in GraphQL response")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentData(
            item=matching_item,
            raw_data=json.dumps(matching_item.metadata.get("raw_data", {})).encode('utf-8'),
            text_content=json.dumps(matching_item.metadata.get("raw_data", {}), indent=2),
            structured_data=matching_item.metadata.get("raw_data", {}),
            metadata={
                "fetched_at": datetime.now().isoformat(),
                "processing_time_ms": processing_time
            },
            processing_time_ms=processing_time
        )

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate GraphQL content."""
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
            errors.append("GraphQL response is empty")

        # Validate GraphQL response structure
        if structured_data is not None:
            if "errors" in structured_data:
                errors.extend([f"GraphQL error: {error.get('message', 'Unknown error')}" for error in structured_data["errors"]])

            if "data" not in structured_data:
                warnings.append("GraphQL response missing data field")
        else:
            try:
                json.loads(raw_data.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                errors.append("Invalid JSON in GraphQL response")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="GraphQL content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "content_size_bytes": len(raw_data),
                "is_json": structured_data is not None,
                "has_graphql_errors": structured_data and "errors" in structured_data,
                "has_data": structured_data and "data" in structured_data
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get GraphQL connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "structured", "image", "video", "audio"],
            "supported_operations": ["query", "mutation", "subscription"],
            "features": ["graphql_queries", "introspection", "authentication", "rate_limiting"],
            "authentication_methods": ["none", "bearer_token", "basic_auth", "api_key"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": False,
            "real_time_updates": False
        })
        return capabilities


class WebSocketConnector(ContentConnector):
    """Connector for WebSocket APIs."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.websocket_connections: Dict[str, Any] = {}
        self.message_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content from WebSocket API."""
        ws_url = source_config.get("ws_url")
        messages = source_config.get("messages", [])
        timeout = source_config.get("timeout", 30)

        if not ws_url:
            raise ValueError("WebSocket URL is required")

        if not messages:
            raise ValueError("No messages provided for WebSocket communication")

        try:
            items = await self._communicate_websocket(ws_url, messages, timeout)
            return items
        except Exception as e:
            raise Exception(f"WebSocket communication failed: {e}")

    async def _communicate_websocket(self, ws_url: str, messages: List[Dict[str, Any]], timeout: int) -> List[ContentItem]:
        """Communicate with WebSocket and collect responses."""
        items = []

        try:
            async with websockets.connect(ws_url) as websocket:
                for message_config in messages:
                    message = message_config.get("message", "")
                    message_type = message_config.get("type", "text")
                    expect_response = message_config.get("expect_response", True)

                    if message_type == "json" and isinstance(message, dict):
                        message = json.dumps(message)

                    # Send message
                    await websocket.send(message)

                    if expect_response:
                        # Receive response
                        try:
                            response = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=timeout
                            )

                            # Parse response
                            try:
                                if message_config.get("response_type") == "json":
                                    response_data = json.loads(response)
                                else:
                                    response_data = response
                            except json.JSONDecodeError:
                                response_data = response

                            # Create content item
                            item_id = hashlib.md5(f"{ws_url}:{message}:{response}".encode()).hexdigest()

                            item = ContentItem(
                                id=f"ws_{item_id}",
                                source=f"websocket:{ws_url}",
                                connector_type=ConnectorType.API,
                                content_type=ContentType.TEXT,
                                title=f"WebSocket Response",
                                description=str(response_data)[:500] + "..." if len(str(response_data)) > 500 else str(response_data),
                                url=ws_url,
                                metadata={
                                    "platform": "websocket",
                                    "ws_url": ws_url,
                                    "sent_message": message,
                                    "received_response": response_data,
                                    "message_type": message_type,
                                    "response_type": message_config.get("response_type", "text")
                                },
                                tags=["websocket", "api", "real_time"]
                            )

                            items.append(item)

                        except asyncio.TimeoutError:
                            self.logger.warning(f"Timeout waiting for WebSocket response to: {message}")

        except Exception as e:
            self.logger.error(f"WebSocket communication error: {e}")
            raise

        return items

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch content from WebSocket API."""
        # WebSocket fetching is more complex as it requires maintaining connections
        # This is a simplified implementation
        if isinstance(content_ref, str):
            raise ValueError("WebSocket connector requires ContentItem for fetching")

        # Re-establish connection and send the original message
        ws_url = content_ref.metadata.get("ws_url")
        sent_message = content_ref.metadata.get("sent_message")

        if not ws_url or not sent_message:
            raise ValueError("WebSocket URL and message not found in ContentItem")

        start_time = datetime.now()

        try:
            async with websockets.connect(ws_url) as websocket:
                await websocket.send(sent_message)

                # Receive response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=30.0
                )

                processing_time = (datetime.now() - start_time).total_seconds() * 1000

                return ContentData(
                    item=content_ref,
                    raw_data=response.encode('utf-8') if isinstance(response, str) else response,
                    text_content=response if isinstance(response, str) else str(response),
                    metadata={
                        "fetched_at": datetime.now().isoformat(),
                        "processing_time_ms": processing_time
                    },
                    processing_time_ms=processing_time
                )

        except Exception as e:
            raise Exception(f"Failed to fetch from WebSocket: {e}")

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate WebSocket content."""
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
            errors.append("WebSocket response is empty")

        # Try to validate as JSON if expected
        if isinstance(content, ContentData):
            response_type = content.item.metadata.get("response_type", "text")
            if response_type == "json":
                try:
                    json.loads(text_content)
                except json.JSONDecodeError:
                    errors.append("Expected JSON response but received invalid JSON")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="WebSocket content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "content_size_bytes": len(raw_data),
                "text_length": len(text_content),
                "is_json": self._is_json_content(text_content)
            }
        )

    def _is_json_content(self, content: str) -> bool:
        """Check if content is valid JSON."""
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False

    def get_capabilities(self) -> Dict[str, Any]:
        """Get WebSocket connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "structured"],
            "supported_operations": ["send_receive", "subscribe", "publish"],
            "features": ["real_time_communication", "bidirectional", "authentication"],
            "authentication_methods": ["none", "bearer_token", "basic_auth"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": False,
            "real_time_updates": True
        })
        return capabilities
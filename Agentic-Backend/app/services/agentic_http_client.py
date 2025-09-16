"""
Agentic HTTP Client Framework with enterprise-grade reliability features.

This module provides a sophisticated HTTP client designed for resilient external API interactions
with circuit breakers, rate limiting, comprehensive observability, and intelligent error handling.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator
from urllib.parse import urlparse, urljoin
import aiohttp
import hashlib
from enum import Enum

from app.config import settings
from app.utils.logging import get_logger
from app.db.database import get_db
from app.db.models.http_request_log import HttpRequestLog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = get_logger("agentic_http_client")


class HttpMethod(Enum):
    """HTTP methods supported by the client."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class AuthConfig:
    """Authentication configuration."""
    type: str  # 'api_key', 'bearer', 'basic', 'oauth2', 'custom'
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = None


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    retry_on_status_codes: List[int] = None
    retry_on_exceptions: List[str] = None

    def __post_init__(self):
        if self.retry_on_status_codes is None:
            self.retry_on_status_codes = [429, 500, 502, 503, 504]
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = ["aiohttp.ClientError", "asyncio.TimeoutError"]


@dataclass
class RateLimit:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    burst_limit: Optional[int] = None
    strategy: str = "fixed_window"  # 'fixed_window', 'sliding_window', 'token_bucket'


@dataclass
class HttpResponse:
    """Enhanced HTTP response with comprehensive metadata."""
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json_data: Optional[Dict[str, Any]] = None
    request_duration: float = 0.0
    retry_count: int = 0
    rate_limit_info: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class DownloadResult:
    """Result of a streaming download operation."""
    file_path: str
    total_size: int
    downloaded_size: int
    duration: float
    success: bool
    checksum: Optional[str] = None


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for resilient HTTP calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Exception = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.state != CircuitBreakerState.OPEN:
            return False

        if self.last_failure_time is None:
            return True

        return (datetime.now() - self.last_failure_time) > timedelta(seconds=self.recovery_timeout)

    def _record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
            raise e


class RateLimiter:
    """Rate limiter with multiple strategies."""

    def __init__(self, rate_limit: RateLimit):
        self.rate_limit = rate_limit
        self.requests = []
        self.tokens = rate_limit.requests_per_minute if rate_limit.burst_limit is None else rate_limit.burst_limit
        self.last_refill = time.time()

    def _refill_tokens(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        time_passed = now - self.last_refill

        if self.rate_limit.strategy == "token_bucket":
            # Refill tokens at rate per minute
            refill_rate = self.rate_limit.requests_per_minute / 60.0
            self.tokens = min(
                self.rate_limit.burst_limit or self.rate_limit.requests_per_minute,
                self.tokens + time_passed * refill_rate
            )
        else:
            # Fixed window: reset every minute
            if time_passed >= 60.0:
                self.tokens = self.rate_limit.requests_per_minute
                self.last_refill = now

    def _can_make_request(self) -> bool:
        """Check if request can be made."""
        self._refill_tokens()

        if self.rate_limit.strategy == "token_bucket":
            return self.tokens >= 1
        else:
            # Fixed/sliding window
            return len(self.requests) < self.rate_limit.requests_per_minute

    def _record_request(self):
        """Record a request."""
        now = time.time()
        self.requests.append(now)

        # Clean old requests for sliding window
        if self.rate_limit.strategy == "sliding_window":
            cutoff = now - 60.0
            self.requests = [r for r in self.requests if r > cutoff]

        # Consume token for token bucket
        if self.rate_limit.strategy == "token_bucket":
            self.tokens -= 1

    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        while not self._can_make_request():
            await asyncio.sleep(1.0)
            self._refill_tokens()

        self._record_request()


class AgenticHttpClient:
    """Modern HTTP client with agentic capabilities for resilient web interactions."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_connections: int = 100,
        circuit_breaker: Optional[CircuitBreaker] = None,
        default_retry_config: Optional[RetryConfig] = None,
        default_rate_limit: Optional[RateLimit] = None
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_connections = max_connections

        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.default_retry_config = default_retry_config or RetryConfig()
        self.default_rate_limit = default_rate_limit

        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter: Optional[RateLimiter] = None

        if self.default_rate_limit:
            self.rate_limiter = RateLimiter(self.default_rate_limit)

        # Request tracking
        self.request_count = 0
        self.request_log = []

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Create HTTP session with optimized settings."""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections // 2,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
                ttl_dns_cache=300
            )

            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=10.0,
                sock_read=30.0
            )

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": f"Agentic-Backend/{settings.app_version}"}
            )

            logger.info(f"Agentic HTTP client connected (max_connections={self.max_connections})")

    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Agentic HTTP client disconnected")

    def _build_url(self, url: str) -> str:
        """Build full URL from base URL and relative path."""
        if self.base_url and not url.startswith(('http://', 'https://')):
            return urljoin(self.base_url, url)
        return url

    def _apply_auth(self, headers: Dict[str, str], auth: Optional[AuthConfig]) -> Dict[str, str]:
        """Apply authentication to headers."""
        if not auth:
            return headers

        if auth.type == "api_key" and auth.api_key:
            headers["X-API-Key"] = auth.api_key
        elif auth.type == "bearer" and auth.bearer_token:
            headers["Authorization"] = f"Bearer {auth.bearer_token}"
        elif auth.type == "basic" and auth.username and auth.password:
            import base64
            credentials = base64.b64encode(f"{auth.username}:{auth.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif auth.custom_headers:
            headers.update(auth.custom_headers)

        return headers

    async def _execute_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Any,
        retry_config: RetryConfig
    ) -> HttpResponse:
        """Execute HTTP request with retry logic."""
        last_exception = None

        for attempt in range(retry_config.max_attempts + 1):
            try:
                # Rate limiting
                if self.rate_limiter:
                    await self.rate_limiter.wait_if_needed()

                # Circuit breaker protection
                async def make_request():
                    return await self._make_request(method, url, headers, data)

                response = await self.circuit_breaker.call(make_request)

                # Update response with retry info
                response.retry_count = attempt
                return response

            except Exception as e:
                last_exception = e
                should_retry = self._should_retry(e, retry_config)

                if attempt < retry_config.max_attempts and should_retry:
                    delay = min(
                        retry_config.initial_delay * (retry_config.backoff_factor ** attempt),
                        retry_config.max_delay
                    )
                    logger.warning(f"Request attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    break

        if last_exception:
            raise last_exception
        else:
            raise Exception("Request failed with unknown error")

    def _should_retry(self, exception: Exception, retry_config: RetryConfig) -> bool:
        """Determine if request should be retried."""
        # Check exception types
        for exc_type in retry_config.retry_on_exceptions:
            if exc_type in str(type(exception)) or exc_type in str(exception):
                return True

        # Check if it's an HTTP error with retryable status code
        if hasattr(exception, 'status'):
            return exception.status in retry_config.retry_on_status_codes

        return False

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Any
    ) -> HttpResponse:
        """Make the actual HTTP request."""
        if not self.session:
            await self.connect()

        start_time = time.time()
        request_id = hashlib.md5(f"{method}{url}{start_time}".encode()).hexdigest()[:8]

        try:
            logger.debug(f"[{request_id}] {method} {url}")

            # Prepare request data
            request_kwargs = {"headers": headers}

            if data is not None:
                if isinstance(data, dict):
                    request_kwargs["json"] = data
                elif isinstance(data, str):
                    request_kwargs["data"] = data.encode('utf-8')
                else:
                    request_kwargs["data"] = data

            # Make request
            async with self.session.request(method, url, **request_kwargs) as response:
                content = await response.read()
                text = content.decode('utf-8', errors='replace')

                # Parse JSON if possible
                json_data = None
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        json_data = json.loads(text)
                    except json.JSONDecodeError:
                        pass

                # Extract rate limit info
                rate_limit_info = self._extract_rate_limit_info(response.headers)

                duration = time.time() - start_time

                http_response = HttpResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    content=content,
                    text=text,
                    json_data=json_data,
                    request_duration=duration,
                    rate_limit_info=rate_limit_info,
                    request_id=request_id,
                    timestamp=datetime.now()
                )

                # Log request with method and URL
                await self._log_request(http_response, method, url, headers, data)

                logger.debug(f"[{request_id}] {response.status} in {duration:.2f}s")
                return http_response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[{request_id}] Request failed after {duration:.2f}s: {e}")
            raise e

    def _extract_rate_limit_info(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract rate limit information from response headers."""
        rate_info = {}

        # Common rate limit headers
        if 'x-ratelimit-remaining' in headers:
            rate_info['remaining'] = int(headers['x-ratelimit-remaining'])
        if 'x-ratelimit-limit' in headers:
            rate_info['limit'] = int(headers['x-ratelimit-limit'])
        if 'x-ratelimit-reset' in headers:
            rate_info['reset_time'] = headers['x-ratelimit-reset']
        if 'retry-after' in headers:
            rate_info['retry_after'] = int(headers['retry-after'])

        return rate_info if rate_info else None

    async def _log_request(self, response: HttpResponse, method: str, url: str, headers: Dict[str, str], data: Any):
        """Log request for monitoring and persist to database."""
        self.request_count += 1

        # Prepare request data for database
        request_body_size = None
        if data is not None:
            if isinstance(data, (str, bytes)):
                request_body_size = len(data)
            elif isinstance(data, dict):
                request_body_size = len(json.dumps(data).encode('utf-8'))

        # Extract user agent from headers
        user_agent = headers.get('User-Agent') or headers.get('user-agent')

        # Determine if request has sensitive data (basic check)
        has_sensitive_data = any(key.lower() in ['password', 'token', 'secret', 'key', 'auth']
                               for key in headers.keys())

        # Create database log entry
        db_log_entry = HttpRequestLog(
            request_id=response.request_id,
            method=method,
            url=url,
            headers=headers,
            request_body_size=request_body_size,
            user_agent=user_agent,
            status_code=response.status_code,
            response_headers=response.headers,
            response_body_size=len(response.content),
            response_time_ms=response.request_duration * 1000,
            retry_count=response.retry_count,
            circuit_breaker_state=self.circuit_breaker.state.value if hasattr(self.circuit_breaker, 'state') else None,
            rate_limit_hit=response.rate_limit_info is not None,
            rate_limit_info=response.rate_limit_info,
            is_success=response.status_code < 400,
            source="agentic_http_client",
            has_sensitive_data=has_sensitive_data,
            completed_at=response.timestamp
        )

        # Persist to database
        try:
            async for session in get_db():
                session.add(db_log_entry)
                await session.commit()
                logger.debug(f"Persisted HTTP request log: {response.request_id}")
                break
        except Exception as e:
            logger.warning(f"Failed to persist HTTP request log: {e}")

        # Keep in-memory log for backward compatibility
        self.request_log.append({
            "request_id": response.request_id,
            "timestamp": response.timestamp.isoformat() if response.timestamp else datetime.now().isoformat(),
            "method": method,
            "url": url,
            "status_code": response.status_code,
            "duration": response.request_duration,
            "size": len(response.content)
        })

        # Keep only last 1000 requests in memory
        if len(self.request_log) > 1000:
            self.request_log = self.request_log[-1000:]

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Dict] = None,
        auth: Optional[AuthConfig] = None,
        timeout: Optional[float] = None,
        retry_config: Optional[RetryConfig] = None,
        rate_limit: Optional[RateLimit] = None
    ) -> HttpResponse:
        """Make HTTP request with comprehensive error handling and observability."""
        # Build full URL
        full_url = self._build_url(url)

        # Prepare headers
        request_headers = headers.copy() if headers else {}
        request_headers = self._apply_auth(request_headers, auth)

        # Prepare data
        request_data = data
        if json_data is not None:
            request_data = json_data
            request_headers["Content-Type"] = "application/json"

        # Use provided configs or defaults
        effective_retry_config = retry_config or self.default_retry_config
        effective_rate_limit = rate_limit or self.default_rate_limit

        # Apply custom rate limit if provided
        if rate_limit and rate_limit != self.default_rate_limit:
            temp_limiter = RateLimiter(rate_limit)
            await temp_limiter.wait_if_needed()

        # Execute with retry
        return await self._execute_with_retry(
            method, full_url, request_headers, request_data, effective_retry_config
        )

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[AuthConfig] = None,
        **kwargs
    ) -> HttpResponse:
        """GET request with agentic features."""
        return await self.request("GET", url, headers=headers, auth=auth, **kwargs)

    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[AuthConfig] = None,
        **kwargs
    ) -> HttpResponse:
        """POST request with agentic features."""
        return await self.request("POST", url, headers=headers, data=data, json_data=json_data, auth=auth, **kwargs)

    async def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[AuthConfig] = None,
        **kwargs
    ) -> HttpResponse:
        """PUT request with agentic features."""
        return await self.request("PUT", url, headers=headers, data=data, json_data=json_data, auth=auth, **kwargs)

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[AuthConfig] = None,
        **kwargs
    ) -> HttpResponse:
        """DELETE request with agentic features."""
        return await self.request("DELETE", url, headers=headers, auth=auth, **kwargs)

    async def stream_download(
        self,
        url: str,
        destination: str,
        progress_callback: Optional[Callable] = None,
        chunk_size: int = 8192,
        auth: Optional[AuthConfig] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> DownloadResult:
        """Stream large file downloads with progress tracking."""
        if not self.session:
            await self.connect()

        if not self.session:
            raise Exception("Failed to initialize HTTP session")

        full_url = self._build_url(url)
        request_headers = headers.copy() if headers else {}
        request_headers = self._apply_auth(request_headers, auth)

        start_time = time.time()
        downloaded_size = 0
        total_size = 0
        checksum = hashlib.md5()

        try:
            async with self.session.get(full_url, headers=request_headers) as response:
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                with open(destination, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        checksum.update(chunk)
                        downloaded_size += len(chunk)

                        if progress_callback:
                            progress_callback(downloaded_size, total_size)

            duration = time.time() - start_time

            return DownloadResult(
                file_path=destination,
                total_size=total_size,
                downloaded_size=downloaded_size,
                duration=duration,
                success=True,
                checksum=checksum.hexdigest()
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Download failed after {duration:.2f}s: {e}")

            return DownloadResult(
                file_path=destination,
                total_size=total_size,
                downloaded_size=downloaded_size,
                duration=duration,
                success=False
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics."""
        return {
            "total_requests": self.request_count,
            "recent_requests": len(self.request_log),
            "circuit_breaker_state": getattr(self.circuit_breaker, 'state', CircuitBreakerState.CLOSED).value,
            "rate_limiter_active": self.rate_limiter is not None,
            "session_active": self.session is not None
        }

    def get_request_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent request log."""
        return self.request_log[-limit:]

    async def cleanup_old_logs(self, retention_days: int = 14):
        """Clean up HTTP request logs older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            async for session in get_db():
                # Delete old HTTP request logs
                result = await session.execute(
                    select(HttpRequestLog).where(HttpRequestLog.created_at < cutoff_date)
                )
                old_logs = result.scalars().all()

                deleted_count = len(old_logs)
                for log in old_logs:
                    await session.delete(log)

                await session.commit()

                logger.info(f"Cleaned up {deleted_count} HTTP request logs older than {retention_days} days")
                break

        except Exception as e:
            logger.error(f"Failed to cleanup old HTTP request logs: {e}")
            raise


# Global instance
agentic_http_client = AgenticHttpClient()
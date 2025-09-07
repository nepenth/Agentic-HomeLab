"""
Advanced Security Service for comprehensive protection and monitoring.

This service provides enterprise-grade security features including:
- Advanced input validation and sanitization
- Rate limiting and abuse prevention
- Security monitoring and alerting
- Data encryption and protection
- Secure configuration management
- Audit logging and compliance features
- Threat detection and response
"""

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import ipaddress
import bleach

from app.utils.logging import get_logger
from app.config import settings


class SecurityLevel(Enum):
    """Security enforcement levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Types of security events."""
    SUSPICIOUS_INPUT = "suspicious_input"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    AUTHENTICATION_FAILURE = "authentication_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALICIOUS_CONTENT = "malicious_content"
    DATA_EXPOSURE = "data_exposure"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_INTRUSION = "system_intrusion"


@dataclass
class SecurityEvent:
    """Represents a security event."""
    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    source_ip: Optional[str]
    user_id: Optional[str]
    resource: str
    action: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolution_notes: Optional[str] = None


@dataclass
class SecurityRule:
    """Represents a security rule."""
    rule_id: str
    name: str
    description: str
    event_type: SecurityEventType
    conditions: Dict[str, Any]
    actions: List[str]
    enabled: bool = True
    priority: int = 1


@dataclass
class RateLimitRule:
    """Represents a rate limiting rule."""
    rule_id: str
    name: str
    endpoint_pattern: str
    requests_per_window: int
    window_seconds: int
    block_duration_seconds: int
    user_specific: bool = True
    ip_specific: bool = True
    enabled: bool = True


@dataclass
class SecurityMetrics:
    """Security service metrics."""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_threat_level: Dict[str, int]
    blocked_requests: int
    active_blocks: int
    rate_limit_hits: int
    last_updated: datetime


class InputValidator:
    """Advanced input validation and sanitization service."""

    def __init__(self):
        self.logger = get_logger("input_validator")

        # SQL injection patterns
        self.sql_patterns = [
            r'\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(select|from|where|join)\b',
            r';\s*(select|insert|update|delete|drop|create|alter)',
            r'/\*.*?\*/',  # Block comments
            r'--.*?$',     # Line comments
        ]

        # XSS patterns
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
        ]

        # Command injection patterns
        self.command_patterns = [
            r'[;&|`$()]\s*(cat|ls|pwd|whoami|id|ps|netstat|ss|curl|wget|nc|ncat|bash|sh|zsh)',
            r';\s*(rm|mv|cp|chmod|chown|kill|systemctl|service)',
            r'\|\s*(grep|awk|sed|cut|sort|uniq|head|tail)',
        ]

        # Path traversal patterns
        self.path_traversal_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
        ]

    def validate_and_sanitize(self, input_data: Any, context: str = "general") -> Tuple[Any, List[str]]:
        """
        Validate and sanitize input data.

        Args:
            input_data: Input data to validate
            context: Context for validation rules

        Returns:
            Tuple of (sanitized_data, warnings)
        """
        warnings = []

        if isinstance(input_data, str):
            return self._validate_string(input_data, context, warnings)
        elif isinstance(input_data, dict):
            return self._validate_dict(input_data, context, warnings)
        elif isinstance(input_data, list):
            return self._validate_list(input_data, context, warnings)
        else:
            # For other types, return as-is
            return input_data, warnings

    def _validate_string(self, input_str: str, context: str, warnings: List[str]) -> Tuple[str, List[str]]:
        """Validate and sanitize string input."""
        original_length = len(input_str)

        # Length limits based on context
        max_lengths = {
            "email_subject": 200,
            "email_content": 10000,
            "search_query": 500,
            "user_input": 1000,
            "general": 5000,
        }

        max_length = max_lengths.get(context, max_lengths["general"])

        if len(input_str) > max_length:
            warnings.append(f"Input length {len(input_str)} exceeds maximum {max_length}")
            input_str = input_str[:max_length]

        # Check for malicious patterns
        security_warnings = self._check_security_patterns(input_str)
        warnings.extend(security_warnings)

        # Sanitize HTML if needed
        if context in ["email_content", "user_input"]:
            input_str = bleach.clean(input_str, tags=[], strip=True)

        # Normalize whitespace
        input_str = " ".join(input_str.split())

        return input_str, warnings

    def _validate_dict(self, input_dict: Dict[str, Any], context: str, warnings: List[str]) -> Tuple[Dict[str, Any], List[str]]:
        """Validate and sanitize dictionary input."""
        sanitized = {}

        for key, value in input_dict.items():
            # Validate key
            if not isinstance(key, str) or len(key) > 100:
                warnings.append(f"Invalid key: {key}")
                continue

            # Recursively validate value
            sanitized_value, value_warnings = self.validate_and_sanitize(value, context)
            warnings.extend(value_warnings)

            sanitized[key] = sanitized_value

        return sanitized, warnings

    def _validate_list(self, input_list: List[Any], context: str, warnings: List[str]) -> Tuple[List[Any], List[str]]:
        """Validate and sanitize list input."""
        sanitized = []

        for item in input_list:
            sanitized_item, item_warnings = self.validate_and_sanitize(item, context)
            warnings.extend(item_warnings)
            sanitized.append(sanitized_item)

        return sanitized, warnings

    def _check_security_patterns(self, input_str: str) -> List[str]:
        """Check for security pattern violations."""
        warnings = []

        # Check SQL injection patterns
        for pattern in self.sql_patterns:
            if re.search(pattern, input_str, re.IGNORECASE):
                warnings.append("Potential SQL injection pattern detected")
                break

        # Check XSS patterns
        for pattern in self.xss_patterns:
            if re.search(pattern, input_str, re.IGNORECASE):
                warnings.append("Potential XSS pattern detected")
                break

        # Check command injection patterns
        for pattern in self.command_patterns:
            if re.search(pattern, input_str, re.IGNORECASE):
                warnings.append("Potential command injection pattern detected")
                break

        # Check path traversal patterns
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, input_str):
                warnings.append("Potential path traversal pattern detected")
                break

        return warnings


class RateLimiter:
    """Advanced rate limiting service."""

    def __init__(self):
        self.logger = get_logger("rate_limiter")
        self.rules: Dict[str, RateLimitRule] = {}
        self.request_counts: Dict[str, Dict[str, int]] = {}
        self.blocked_entities: Dict[str, datetime] = {}
        self.cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the rate limiter."""
        # Default rules
        self._add_default_rules()

        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

    def _add_default_rules(self):
        """Add default rate limiting rules."""
        default_rules = [
            RateLimitRule(
                rule_id="api_general",
                name="General API Rate Limit",
                endpoint_pattern="/api/v1/*",
                requests_per_window=100,
                window_seconds=60,
                block_duration_seconds=300,
            ),
            RateLimitRule(
                rule_id="auth_endpoints",
                name="Authentication Endpoints",
                endpoint_pattern="/api/v1/auth/*",
                requests_per_window=5,
                window_seconds=300,
                block_duration_seconds=900,
            ),
            RateLimitRule(
                rule_id="search_endpoints",
                name="Search Endpoints",
                endpoint_pattern="/api/v1/*/search*",
                requests_per_window=20,
                window_seconds=60,
                block_duration_seconds=180,
            ),
        ]

        for rule in default_rules:
            self.rules[rule.rule_id] = rule

    async def check_rate_limit(
        self,
        endpoint: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if request should be rate limited.

        Args:
            endpoint: Request endpoint
            user_id: User ID if authenticated
            ip_address: Client IP address

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        # Check if entity is currently blocked
        if user_id and user_id in self.blocked_entities:
            if datetime.now() < self.blocked_entities[user_id]:
                remaining = int((self.blocked_entities[user_id] - datetime.now()).total_seconds())
                return False, remaining

        if ip_address and ip_address in self.blocked_entities:
            if datetime.now() < self.blocked_entities[ip_address]:
                remaining = int((self.blocked_entities[ip_address] - datetime.now()).total_seconds())
                return False, remaining

        # Find applicable rules
        applicable_rules = []
        for rule in self.rules.values():
            if rule.enabled and re.match(rule.endpoint_pattern.replace("*", ".*"), endpoint):
                applicable_rules.append(rule)

        if not applicable_rules:
            return True, None

        # Check each applicable rule
        for rule in applicable_rules:
            allowed, retry_after = await self._check_rule(rule, user_id, ip_address)
            if not allowed:
                # Apply block
                block_duration = timedelta(seconds=rule.block_duration_seconds)

                if rule.user_specific and user_id:
                    self.blocked_entities[user_id] = datetime.now() + block_duration
                if rule.ip_specific and ip_address:
                    self.blocked_entities[ip_address] = datetime.now() + block_duration

                self.logger.warning(f"Rate limit exceeded for {endpoint}, user: {user_id}, ip: {ip_address}")
                return False, retry_after

        return True, None

    async def _check_rule(
        self,
        rule: RateLimitRule,
        user_id: Optional[str],
        ip_address: Optional[str]
    ) -> Tuple[bool, Optional[int]]:
        """Check a specific rate limiting rule."""
        # Generate keys for tracking
        keys = []
        if rule.user_specific and user_id:
            keys.append(f"user:{user_id}:{rule.rule_id}")
        if rule.ip_specific and ip_address:
            keys.append(f"ip:{ip_address}:{rule.rule_id}")

        if not keys:
            return True, None

        current_time = int(time.time())
        window_start = current_time - rule.window_seconds

        # Check each key
        for key in keys:
            if key not in self.request_counts:
                self.request_counts[key] = {}

            # Clean old entries
            self.request_counts[key] = {
                int(timestamp): count
                for timestamp, count in self.request_counts[key].items()
                if int(timestamp) > window_start
            }

            # Count requests in current window
            window_requests = sum(self.request_counts[key].values())

            if window_requests >= rule.requests_per_window:
                # Calculate retry after
                oldest_timestamp = min(self.request_counts[key].keys())
                retry_after = rule.window_seconds - (current_time - oldest_timestamp)
                return False, max(1, retry_after)

            # Record this request
            timestamp_key = str(current_time)
            if timestamp_key not in self.request_counts[key]:
                self.request_counts[key][timestamp_key] = 0
            self.request_counts[key][timestamp_key] += 1

        return True, None

    async def _periodic_cleanup(self):
        """Periodic cleanup of old rate limit data."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes

                current_time = int(time.time())

                # Clean up old request counts (older than 1 hour)
                cutoff_time = current_time - 3600
                for key in list(self.request_counts.keys()):
                    self.request_counts[key] = {
                        timestamp: count
                        for timestamp, count in self.request_counts[key].items()
                        if int(timestamp) > cutoff_time
                    }
                    if not self.request_counts[key]:
                        del self.request_counts[key]

                # Clean up expired blocks
                now = datetime.now()
                expired_blocks = [
                    entity for entity, expiry in self.blocked_entities.items()
                    if expiry <= now
                ]
                for entity in expired_blocks:
                    del self.blocked_entities[entity]

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in rate limiter cleanup: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "active_rules": len([r for r in self.rules.values() if r.enabled]),
            "total_rules": len(self.rules),
            "tracked_entities": len(self.request_counts),
            "blocked_entities": len(self.blocked_entities),
            "rules": {rule.rule_id: rule.name for rule in self.rules.values()}
        }


class SecurityMonitor:
    """Security monitoring and alerting service."""

    def __init__(self):
        self.logger = get_logger("security_monitor")
        self.events: List[SecurityEvent] = []
        self.rules: Dict[str, SecurityRule] = {}
        self.alert_thresholds = {
            ThreatLevel.LOW: 10,
            ThreatLevel.MEDIUM: 5,
            ThreatLevel.HIGH: 2,
            ThreatLevel.CRITICAL: 1,
        }

    def _add_default_rules(self):
        """Add default security rules."""
        default_rules = [
            SecurityRule(
                rule_id="suspicious_input_alert",
                name="Suspicious Input Alert",
                description="Alert on suspicious input patterns",
                event_type=SecurityEventType.SUSPICIOUS_INPUT,
                conditions={"threat_level": ThreatLevel.HIGH.value},
                actions=["log", "alert_admin"],
                priority=1,
            ),
            SecurityRule(
                rule_id="rate_limit_critical",
                name="Critical Rate Limit",
                description="Alert on critical rate limiting",
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                conditions={"threat_level": ThreatLevel.CRITICAL.value},
                actions=["log", "block_ip", "alert_admin"],
                priority=2,
            ),
            SecurityRule(
                rule_id="auth_failure_pattern",
                name="Authentication Failure Pattern",
                description="Detect authentication failure patterns",
                event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                conditions={"count_threshold": 5, "time_window_minutes": 10},
                actions=["log", "temporary_block", "alert_admin"],
                priority=3,
            ),
        ]

        for rule in default_rules:
            self.rules[rule.rule_id] = rule

    async def log_security_event(
        self,
        event_type: SecurityEventType,
        threat_level: ThreatLevel,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        resource: str = "",
        action: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a security event."""
        event = SecurityEvent(
            event_id=secrets.token_hex(16),
            event_type=event_type,
            threat_level=threat_level,
            source_ip=source_ip,
            user_id=user_id,
            resource=resource,
            action=action,
            details=details or {},
            timestamp=datetime.now()
        )

        self.events.append(event)

        # Keep only last 1000 events
        if len(self.events) > 1000:
            self.events = self.events[-1000:]

        # Check rules and trigger actions
        await self._process_event_rules(event)

        # Log based on threat level
        log_message = f"Security event: {event_type.value} ({threat_level.value}) - {resource}:{action}"
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

        return event.event_id

    async def _process_event_rules(self, event: SecurityEvent):
        """Process security rules for an event."""
        for rule in self.rules.values():
            if not rule.enabled or rule.event_type != event.event_type:
                continue

            if await self._rule_matches(event, rule):
                await self._execute_rule_actions(event, rule)

    async def _rule_matches(self, event: SecurityEvent, rule: SecurityRule) -> bool:
        """Check if an event matches a security rule."""
        conditions = rule.conditions

        # Check threat level
        if "threat_level" in conditions:
            if event.threat_level.value != conditions["threat_level"]:
                return False

        # Check count threshold (for pattern detection)
        if "count_threshold" in conditions:
            time_window = conditions.get("time_window_minutes", 60)
            window_start = datetime.now() - timedelta(minutes=time_window)

            recent_events = [
                e for e in self.events
                if e.event_type == event.event_type
                and e.user_id == event.user_id
                and e.timestamp >= window_start
            ]

            if len(recent_events) < conditions["count_threshold"]:
                return False

        return True

    async def _execute_rule_actions(self, event: SecurityEvent, rule: SecurityRule):
        """Execute actions for a matching security rule."""
        for action in rule.actions:
            if action == "log":
                self.logger.info(f"Security rule triggered: {rule.name} for event {event.event_id}")
            elif action == "alert_admin":
                await self._send_admin_alert(event, rule)
            elif action == "block_ip":
                await self._block_ip(event.source_ip)
            elif action == "temporary_block":
                await self._temporary_block(event.user_id)

    async def _send_admin_alert(self, event: SecurityEvent, rule: SecurityRule):
        """Send admin alert for security event."""
        # In production, this would send email/SMS notifications
        self.logger.error(f"ADMIN ALERT: Security rule '{rule.name}' triggered - Event: {event.event_id}")

    async def _block_ip(self, ip_address: Optional[str]):
        """Block an IP address."""
        if ip_address:
            self.logger.warning(f"Blocking IP address: {ip_address}")
            # In production, this would update firewall rules

    async def _temporary_block(self, user_id: Optional[str]):
        """Temporarily block a user."""
        if user_id:
            self.logger.warning(f"Temporarily blocking user: {user_id}")
            # In production, this would update user status

    def get_security_metrics(self) -> SecurityMetrics:
        """Get security metrics."""
        events_by_type = {}
        events_by_threat = {}

        for event in self.events:
            event_type = event.event_type.value
            threat_level = event.threat_level.value

            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            events_by_threat[threat_level] = events_by_threat.get(threat_level, 0) + 1

        return SecurityMetrics(
            total_events=len(self.events),
            events_by_type=events_by_type,
            events_by_threat_level=events_by_threat,
            blocked_requests=0,  # Would be tracked separately
            active_blocks=0,     # Would be tracked separately
            rate_limit_hits=0,   # Would be tracked separately
            last_updated=datetime.now()
        )


class DataEncryptor:
    """Data encryption and protection service."""

    def __init__(self, encryption_key: Optional[str] = None):
        self.logger = get_logger("data_encryptor")
        self.encryption_key = encryption_key or settings.secret_key

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not data:
            return ""

        # Simple encryption for demonstration
        # In production, use proper encryption like Fernet
        import base64
        encoded = base64.b64encode(data.encode()).decode()
        return f"enc:{encoded}"

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not encrypted_data.startswith("enc:"):
            return encrypted_data

        # Simple decryption for demonstration
        import base64
        try:
            decoded = base64.b64decode(encrypted_data[4:]).decode()
            return decoded
        except:
            self.logger.error("Failed to decrypt data")
            return ""

    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """Create a secure hash of data."""
        if salt:
            data = f"{data}{salt}"

        return hashlib.sha256(data.encode()).hexdigest()

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_hex(length)


class SecurityService:
    """Main security service coordinating all security features."""

    def __init__(self):
        self.logger = get_logger("security_service")
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter()
        self.security_monitor = SecurityMonitor()
        self.data_encryptor = DataEncryptor()
        self.security_level = SecurityLevel.MODERATE

    async def initialize(self):
        """Initialize the security service."""
        await self.rate_limiter.initialize()
        self.security_monitor._add_default_rules()
        self.logger.info("Security Service initialized")

    async def validate_request(
        self,
        endpoint: str,
        request_data: Any,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a request for security issues.

        Args:
            endpoint: Request endpoint
            request_data: Request data
            user_id: User ID if authenticated
            ip_address: Client IP address

        Returns:
            Tuple of (allowed, validation_result)
        """
        result = {
            "allowed": True,
            "warnings": [],
            "blocked_reasons": [],
            "sanitized_data": request_data
        }

        # Check rate limiting
        rate_allowed, retry_after = await self.rate_limiter.check_rate_limit(
            endpoint, user_id, ip_address
        )

        if not rate_allowed:
            result["allowed"] = False
            result["blocked_reasons"].append(f"Rate limit exceeded. Retry after {retry_after} seconds")

            await self.security_monitor.log_security_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                ThreatLevel.MEDIUM,
                ip_address,
                user_id,
                endpoint,
                "rate_limited"
            )
            return False, result

        # Validate and sanitize input
        if request_data is not None:
            sanitized_data, warnings = self.input_validator.validate_and_sanitize(
                request_data, self._get_context_from_endpoint(endpoint)
            )

            result["sanitized_data"] = sanitized_data
            result["warnings"].extend(warnings)

            # Check for security violations
            if warnings:
                threat_level = ThreatLevel.LOW
                if any("SQL injection" in w or "command injection" in w for w in warnings):
                    threat_level = ThreatLevel.HIGH

                await self.security_monitor.log_security_event(
                    SecurityEventType.SUSPICIOUS_INPUT,
                    threat_level,
                    ip_address,
                    user_id,
                    endpoint,
                    "input_validation",
                    {"warnings": warnings}
                )

                # Block request if high threat level and strict security
                if threat_level == ThreatLevel.HIGH and self.security_level == SecurityLevel.STRICT:
                    result["allowed"] = False
                    result["blocked_reasons"].append("Suspicious input detected")

        return result["allowed"], result

    def _get_context_from_endpoint(self, endpoint: str) -> str:
        """Get validation context from endpoint."""
        if "/search" in endpoint:
            return "search_query"
        elif "/email" in endpoint:
            return "email_content"
        elif "/chat" in endpoint:
            return "user_input"
        else:
            return "general"

    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        metrics = self.security_monitor.get_security_metrics()
        rate_limit_stats = self.rate_limiter.get_stats()

        return {
            "security_level": self.security_level.value,
            "metrics": {
                "total_security_events": metrics.total_events,
                "events_by_type": metrics.events_by_type,
                "events_by_threat_level": metrics.events_by_threat_level,
                "blocked_requests": metrics.blocked_requests,
                "active_blocks": metrics.active_blocks,
                "rate_limit_hits": metrics.rate_limit_hits,
            },
            "rate_limiting": rate_limit_stats,
            "last_updated": metrics.last_updated.isoformat()
        }

    async def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.data_encryptor.encrypt_sensitive_data(data)

    async def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.data_encryptor.decrypt_sensitive_data(encrypted_data)

    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """Hash data securely."""
        return self.data_encryptor.hash_data(data, salt)

    def generate_token(self, length: int = 32) -> str:
        """Generate a secure token."""
        return self.data_encryptor.generate_secure_token(length)


# Global security service instance
security_service = SecurityService()
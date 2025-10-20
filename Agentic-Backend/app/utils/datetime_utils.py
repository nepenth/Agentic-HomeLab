"""
Datetime utility functions for consistent timezone handling.

This module provides timezone-aware datetime utilities to ensure consistent
time handling across the application. All functions return timezone-aware
datetime objects in UTC.

Best Practices:
- Always use utc_now() instead of datetime.utcnow()
- Always use timezone-aware datetime objects
- Store all timestamps in UTC in the database
- Convert to local timezone only in the presentation layer (frontend)

Examples:
    >>> from app.utils.datetime_utils import utc_now
    >>> current_time = utc_now()
    >>> print(current_time)  # 2025-10-20 12:30:45.123456+00:00
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC time as a timezone-aware datetime object.

    This is the preferred way to get the current time in the application.
    It replaces the deprecated datetime.utcnow() which returns a naive datetime.

    Returns:
        datetime: Current time in UTC with timezone information.

    Examples:
        >>> now = utc_now()
        >>> print(now.tzinfo)  # timezone.utc
        >>> print(now.isoformat())  # '2025-10-20T12:30:45.123456+00:00'
    """
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """
    Get current UTC timestamp as a float (seconds since epoch).

    Returns:
        float: Current Unix timestamp in UTC.

    Examples:
        >>> ts = utc_timestamp()
        >>> print(ts)  # 1729427445.123456
    """
    return datetime.now(timezone.utc).timestamp()


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC timezone.

    Args:
        dt: Datetime object (can be naive or timezone-aware).

    Returns:
        datetime: Timezone-aware datetime in UTC.

    Notes:
        - If dt is naive (no timezone), it's assumed to be UTC
        - If dt has a timezone, it's converted to UTC

    Examples:
        >>> import pytz
        >>> eastern = pytz.timezone('America/New_York')
        >>> local_time = datetime(2025, 10, 20, 8, 30, tzinfo=eastern)
        >>> utc_time = to_utc(local_time)
        >>> print(utc_time)  # 2025-10-20 12:30:00+00:00
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        return dt.astimezone(timezone.utc)


def format_utc_iso(dt: Optional[datetime] = None) -> str:
    """
    Format a datetime as ISO 8601 string in UTC.

    Args:
        dt: Datetime to format. If None, uses current time.

    Returns:
        str: ISO 8601 formatted string in UTC.

    Examples:
        >>> iso_str = format_utc_iso()
        >>> print(iso_str)  # '2025-10-20T12:30:45.123456+00:00'
    """
    if dt is None:
        dt = utc_now()
    return to_utc(dt).isoformat()


def timedelta_seconds(start: datetime, end: Optional[datetime] = None) -> float:
    """
    Calculate time difference in seconds between two datetimes.

    Args:
        start: Start datetime.
        end: End datetime. If None, uses current time.

    Returns:
        float: Time difference in seconds.

    Examples:
        >>> start = utc_now()
        >>> # ... do some work ...
        >>> duration = timedelta_seconds(start)
        >>> print(f"Operation took {duration:.2f} seconds")
    """
    if end is None:
        end = utc_now()
    return (end - start).total_seconds()


def add_seconds(dt: datetime, seconds: float) -> datetime:
    """
    Add seconds to a datetime, preserving timezone.

    Args:
        dt: Base datetime.
        seconds: Number of seconds to add (can be negative).

    Returns:
        datetime: New datetime with seconds added.

    Examples:
        >>> now = utc_now()
        >>> future = add_seconds(now, 3600)  # Add 1 hour
        >>> past = add_seconds(now, -3600)   # Subtract 1 hour
    """
    return dt + timedelta(seconds=seconds)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    Add minutes to a datetime, preserving timezone.

    Args:
        dt: Base datetime.
        minutes: Number of minutes to add (can be negative).

    Returns:
        datetime: New datetime with minutes added.

    Examples:
        >>> now = utc_now()
        >>> future = add_minutes(now, 30)  # Add 30 minutes
    """
    return dt + timedelta(minutes=minutes)


def add_days(dt: datetime, days: int) -> datetime:
    """
    Add days to a datetime, preserving timezone.

    Args:
        dt: Base datetime.
        days: Number of days to add (can be negative).

    Returns:
        datetime: New datetime with days added.

    Examples:
        >>> now = utc_now()
        >>> tomorrow = add_days(now, 1)
        >>> last_week = add_days(now, -7)
    """
    return dt + timedelta(days=days)


def is_expired(expiry_time: datetime) -> bool:
    """
    Check if a datetime is in the past (expired).

    Args:
        expiry_time: Datetime to check.

    Returns:
        bool: True if expiry_time is in the past, False otherwise.

    Examples:
        >>> token_expiry = utc_now() + timedelta(hours=2)
        >>> print(is_expired(token_expiry))  # False
        >>> old_expiry = utc_now() - timedelta(hours=1)
        >>> print(is_expired(old_expiry))    # True
    """
    return to_utc(expiry_time) < utc_now()


def time_until_expiry(expiry_time: datetime) -> float:
    """
    Get seconds until a datetime expires (negative if already expired).

    Args:
        expiry_time: Datetime to check.

    Returns:
        float: Seconds until expiry (negative if expired).

    Examples:
        >>> token_expiry = utc_now() + timedelta(hours=2)
        >>> seconds_left = time_until_expiry(token_expiry)
        >>> print(f"Token expires in {seconds_left/3600:.1f} hours")
    """
    return timedelta_seconds(utc_now(), to_utc(expiry_time))


# Timezone Strategy Documentation
"""
## Application Timezone Strategy

### Core Principles
1. **All containers run in UTC timezone**
   - API, workers, database, and all services use UTC
   - No local timezone configuration in containers

2. **All database timestamps are timezone-aware**
   - Use TIMESTAMP(timezone=True) in SQLAlchemy models
   - PostgreSQL stores as UTC with timezone offset (+00)

3. **All Python datetime objects should be timezone-aware**
   - Use datetime.now(timezone.utc) or utc_now() from this module
   - Never use datetime.utcnow() (deprecated and returns naive datetime)

4. **Timezone conversion happens in presentation layer**
   - Backend always works in UTC
   - Frontend converts to user's local timezone for display
   - API accepts ISO 8601 with timezone information

### Migration Path
- New code: Always use utc_now() from this module
- Existing code: Gradually replace datetime.utcnow() during maintenance
- Critical paths (auth, tokens): Already updated to use timezone-aware datetimes

### Examples

#### Creating timestamps:
```python
from app.utils.datetime_utils import utc_now

# Good
created_at = utc_now()

# Bad (deprecated)
created_at = datetime.utcnow()
```

#### Calculating durations:
```python
from app.utils.datetime_utils import utc_now, timedelta_seconds

start_time = utc_now()
# ... do work ...
duration = timedelta_seconds(start_time)
```

#### Token expiration:
```python
from app.utils.datetime_utils import utc_now, add_minutes, is_expired

expiry = add_minutes(utc_now(), 120)  # 2 hours from now
if is_expired(expiry):
    raise TokenExpiredError()
```
"""

from datetime import datetime, timezone
from typing import Optional


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime.datetime to integer timestamp in seconds"""
    return int(dt.timestamp())


def timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert integer timestamp in seconds to datetime.datetime"""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_str(dt: datetime) -> str:
    """Convert datetime to ISO 8601 format"""
    return dt.strftime('%Y-%m-%dT%H:%M:%S%z')


def now() -> datetime:
    """Return current datetime with UTC timezone set"""
    return datetime.now(timezone.utc)


def timestamp_pretty_ago(timestamp: int) -> str:
    """
    Convert past date to user-friendly description compared to current datetime.
    eg.: 'an hour ago', 'yesterday', '3 months ago', 'just now'
    """
    diff = now() - timestamp_to_datetime(timestamp)
    second_diff: int = diff.seconds
    day_diff: int = diff.days

    if day_diff < 0:
        return ''
    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return f"{second_diff} seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return f"{second_diff // 60} minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return f"{second_diff // 3600} hours ago"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return f"{day_diff} days ago"
    if day_diff // 7 == 1:
        return f"a week ago"
    if day_diff < 31:
        return f"{day_diff // 7} weeks ago"
    if day_diff // 30 == 1:
        return f"a month ago"
    if day_diff < 365:
        return f"{day_diff // 30} months ago"
    if day_diff // 365 == 1:
        return f"a year ago"
    return f"{day_diff // 365} years ago"


def nullable_timestamp_pretty_ago(timestamp: Optional[int]) -> str:
    """Convert past date to user-friendly description or "never" if it's empty"""
    if not timestamp:
        return 'never'
    return timestamp_pretty_ago(timestamp)


def days_ago(timestamp: Optional[int]) -> Optional[float]:
    """Return number of days ago from given timestamp"""
    if not timestamp:
        return None
    return (datetime_to_timestamp(now()) - timestamp) / (24 * 60 * 60)

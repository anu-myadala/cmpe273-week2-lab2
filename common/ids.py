"""
Shared utility functions for generating consistent IDs and timestamps
across all three communication model implementations.
"""

import uuid
from datetime import datetime, timezone


def generate_order_id() -> str:
    """Generate a unique order ID using UUID4."""
    return str(uuid.uuid4())


def generate_event_id() -> str:
    """Generate a unique event ID using UUID4."""
    return str(uuid.uuid4())


def current_timestamp() -> str:
    """
    Generate ISO-8601 formatted timestamp in UTC.
    
    Returns:
        str: Timestamp like '2026-02-10T14:30:00.123456Z'
    """
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def parse_timestamp(ts_str: str) -> datetime:
    """
    Parse ISO-8601 timestamp string back to datetime object.
    
    Args:
        ts_str: ISO-8601 formatted timestamp
        
    Returns:
        datetime object in UTC
    """
    return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))

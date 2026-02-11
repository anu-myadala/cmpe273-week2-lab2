"""
Idempotency tracking for InventoryService
Prevents duplicate processing of events
"""
import logging
from typing import Set

logger = logging.getLogger(__name__)


class IdempotencyTracker:
    """
    Tracks processed event IDs to ensure idempotent processing
    In production, this would use Redis or a database
    """
    
    def __init__(self):
        self.processed_events: Set[str] = set()
    
    def is_processed(self, event_id: str) -> bool:
        """Check if an event has been processed"""
        return event_id in self.processed_events
    
    def mark_processed(self, event_id: str) -> None:
        """Mark an event as processed"""
        self.processed_events.add(event_id)
        logger.info(f"Event {event_id} marked as processed")
    
    def get_processed_count(self) -> int:
        """Get count of processed events"""
        return len(self.processed_events)

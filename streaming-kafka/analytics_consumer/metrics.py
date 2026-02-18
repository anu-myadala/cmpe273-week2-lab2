"""
Metrics calculator for analytics consumer
Tracks orders per minute, failure rate, and other metrics
"""
from collections import deque
from datetime import datetime, timedelta, timezone
import json
import logging
import os

logger = logging.getLogger(__name__)


class MetricsCalculator:
    def __init__(self):
        self.events = deque()  # (timestamp, event_type)
        self.total_orders = 0
        self.failed_orders = 0
        self.reserved_orders = 0
        self.start_time = datetime.now(timezone.utc)
        self.max_event_time = None  # event-time window end
    
    def add_event(self, event_type, timestamp_str=None):
        """
        Add an event to metrics
        
        Args:
            event_type: Type of event (OrderPlaced, InventoryReserved, InventoryFailed)
            timestamp_str: ISO-8601 timestamp string (optional)
        """
        try:
            if timestamp_str:
                # Parse timestamp
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)
            
            self.events.append((timestamp, event_type))
            
            # Update counters
            if event_type == 'OrderPlaced':
                self.total_orders += 1
            elif event_type == 'InventoryFailed':
                self.failed_orders += 1
            elif event_type == 'InventoryReserved':
                self.reserved_orders += 1
            
            # Remove events older than 1 minute, based on event-time.
            # This makes replay deterministic: the window is relative to the
            # latest event timestamp seen, not wall-clock time.
            if self.max_event_time is None or timestamp > self.max_event_time:
                self.max_event_time = timestamp
            cutoff = self.max_event_time - timedelta(minutes=1)

            # Prune to the 1-minute event-time window
            self.events = deque((ts, et) for ts, et in self.events if ts >= cutoff)
        
        except Exception as e:
            logger.error(f"Error adding event to metrics: {e}")
    
    def get_orders_per_minute(self):
        """Get number of OrderPlaced events in last minute"""
        return sum(1 for _, event_type in self.events if event_type == 'OrderPlaced')
    
    def get_failure_rate(self):
        """Get failure rate as percentage"""
        if self.total_orders == 0:
            return 0.0
        return (self.failed_orders / self.total_orders) * 100
    
    def get_success_rate(self):
        """Get success rate as percentage"""
        if self.total_orders == 0:
            return 0.0
        return (self.reserved_orders / self.total_orders) * 100
    
    def get_throughput(self):
        """Get events per second since start"""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        total_events = self.total_orders + self.failed_orders + self.reserved_orders
        return total_events / elapsed
    
    def get_metrics(self):
        """Get all metrics as dictionary"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'window_end_timestamp': (self.max_event_time or datetime.now(timezone.utc)).isoformat().replace('+00:00', 'Z'),
            'orders_per_minute': self.get_orders_per_minute(),
            'failure_rate_percent': round(self.get_failure_rate(), 2),
            'success_rate_percent': round(self.get_success_rate(), 2),
            'total_orders': self.total_orders,
            'failed_orders': self.failed_orders,
            'reserved_orders': self.reserved_orders,
            'throughput_events_per_second': round(self.get_throughput(), 2),
            'elapsed_seconds': round((datetime.now(timezone.utc) - self.start_time).total_seconds(), 2)
        }
    
    def reset(self):
        """Reset all metrics"""
        self.events.clear()
        self.total_orders = 0
        self.failed_orders = 0
        self.reserved_orders = 0
        self.start_time = datetime.now(timezone.utc)
        self.max_event_time = None  # event-time window end
        logger.info("Metrics reset")
    
    def save_to_file(self, filename='/app/output/metrics_output.json'):
        """Save metrics to JSON file"""
        try:
            metrics = self.get_metrics()
            out_dir = os.path.dirname(filename)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(metrics, f, indent=2)
            logger.info(f"Metrics saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            return False

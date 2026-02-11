"""
In-memory database for OrderService
Stores orders and their status
"""
from typing import Dict, Optional
import threading


class OrderDatabase:
    def __init__(self):
        self.orders: Dict[str, dict] = {}
        self.lock = threading.Lock()
    
    def save_order(self, order: dict) -> bool:
        """Save an order to the database"""
        try:
            with self.lock:
                self.orders[order['order_id']] = order
            return True
        except Exception:
            return False
    
    def get_order(self, order_id: str) -> Optional[dict]:
        """Get an order by ID"""
        with self.lock:
            return self.orders.get(order_id)
    
    def get_all_orders(self) -> list:
        """Get all orders"""
        with self.lock:
            return list(self.orders.values())
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status"""
        try:
            with self.lock:
                if order_id in self.orders:
                    self.orders[order_id]['status'] = status
                    return True
                return False
        except Exception:
            return False

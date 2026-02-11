from flask import Flask, request, jsonify
import logging
import os
import sys
import time

sys.path.append('/app/common')
from ids import generate_order_id, generate_event_id, current_timestamp

from producer import OrderProducer

app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize producer
producer = OrderProducer()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/order', methods=['POST'])
def create_order():
    """
    Create a single order and publish to Kafka
    Returns 202 Accepted immediately
    """
    try:
        data = request.json
        
        # Validate input
        if not data or 'user_id' not in data or 'item' not in data:
            return jsonify({"error": "Missing required fields: user_id, item"}), 400
        
        # Generate IDs and timestamp
        order_id = generate_order_id()
        event_id = generate_event_id()
        timestamp = current_timestamp()
        
        # Create event
        event = {
            "event_id": event_id,
            "event_type": "OrderPlaced",
            "order_id": order_id,
            "timestamp": timestamp,
            "payload": {
                "user_id": data['user_id'],
                "item": data['item'],
                "quantity": data.get('quantity', 1)
            }
        }
        
        # Produce to Kafka
        if not producer.produce_event(event):
            logger.error(f"Failed to produce event for order {order_id}")
            return jsonify({"error": "Failed to publish event"}), 500
        
        logger.info(f"Order {order_id} published to Kafka")
        
        # Return 202 Accepted
        return jsonify({
            "order_id": order_id,
            "status": "accepted",
            "message": "Order received and published to Kafka",
            "timestamp": timestamp
        }), 202
        
    except Exception as e:
        logger.error(f"Error in create_order: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/orders/batch', methods=['POST'])
def create_batch_orders():
    """
    Create multiple orders in batch and publish to Kafka
    Optimized for high throughput
    """
    try:
        data = request.json
        
        if not data or 'orders' not in data:
            return jsonify({"error": "Missing 'orders' array"}), 400
        
        orders = data['orders']
        
        if not isinstance(orders, list):
            return jsonify({"error": "'orders' must be an array"}), 400
        
        if len(orders) > 1000:
            return jsonify({"error": "Batch size limited to 1000 orders"}), 400
        
        # Create events for all orders
        events = []
        order_ids = []
        
        for order_data in orders:
            if 'user_id' not in order_data or 'item' not in order_data:
                continue
            
            order_id = generate_order_id()
            event_id = generate_event_id()
            timestamp = current_timestamp()
            
            event = {
                "event_id": event_id,
                "event_type": "OrderPlaced",
                "order_id": order_id,
                "timestamp": timestamp,
                "payload": {
                    "user_id": order_data['user_id'],
                    "item": order_data['item'],
                    "quantity": order_data.get('quantity', 1)
                }
            }
            
            events.append(event)
            order_ids.append(order_id)
        
        # Produce batch to Kafka
        if not producer.produce_batch(events):
            logger.error(f"Failed to produce batch of {len(events)} events")
            return jsonify({"error": "Failed to publish events"}), 500
        
        logger.info(f"Batch of {len(events)} orders published to Kafka")
        
        # Return 202 Accepted
        return jsonify({
            "status": "accepted",
            "message": f"{len(events)} orders received and published to Kafka",
            "order_count": len(events),
            "order_ids": order_ids[:10]  # Return first 10 IDs
        }), 202
        
    except Exception as e:
        logger.error(f"Error in create_batch_orders: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


if __name__ == '__main__':
    try:
        port = int(os.getenv('PORT', '8201'))
        app.run(host='0.0.0.0', port=port)
    finally:
        producer.close()

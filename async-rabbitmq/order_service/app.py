from flask import Flask, request, jsonify
import logging
import os
import sys
import time

sys.path.append('/app/common')
from ids import generate_order_id, generate_event_id, current_timestamp

from publisher import OrderPublisher
from database import OrderDatabase

app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database and publisher
db = OrderDatabase()
publisher = OrderPublisher()

# Connect to RabbitMQ on startup with retries
MAX_RETRIES = 10
retry_count = 0
while retry_count < MAX_RETRIES:
    if publisher.connect():
        break
    retry_count += 1
    logger.warning(f"Retrying RabbitMQ connection ({retry_count}/{MAX_RETRIES})...")
    time.sleep(5)

if retry_count >= MAX_RETRIES:
    logger.error("Failed to connect to RabbitMQ after max retries")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/order', methods=['POST'])
def create_order():
    """
    Create a new order asynchronously
    Saves order locally and publishes event to RabbitMQ
    Returns immediately with 202 Accepted
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
        
        # Create order object
        order = {
            "order_id": order_id,
            "user_id": data['user_id'],
            "item": data['item'],
            "quantity": data.get('quantity', 1),
            "status": "pending",
            "timestamp": timestamp
        }
        
        # Save to local database
        if not db.save_order(order):
            return jsonify({"error": "Failed to save order"}), 500
        
        logger.info(f"Order {order_id} saved to database")
        
        # Create event for RabbitMQ
        event = {
            "event_id": event_id,
            "event_type": "OrderPlaced",
            "order_id": order_id,
            "timestamp": timestamp,
            "user_id": data['user_id'],
            "item": data['item'],
            "quantity": data.get('quantity', 1)
        }
        
        # Publish event to RabbitMQ
        if not publisher.publish_event(event):
            logger.error(f"Failed to publish event for order {order_id}")
            # Note: Order is still saved locally, event will need retry
        else:
            logger.info(f"Event published for order {order_id}")
        
        # Return immediately (202 Accepted)
        return jsonify({
            "order_id": order_id,
            "status": "accepted",
            "message": "Order received and being processed",
            "timestamp": timestamp
        }), 202
        
    except Exception as e:
        logger.error(f"Error in create_order: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/orders', methods=['GET'])
def list_orders():
    """List all orders"""
    try:
        orders = db.get_all_orders()
        return jsonify({
            "orders": orders,
            "count": len(orders)
        }), 200
    except Exception as e:
        logger.error(f"Error in list_orders: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get a specific order by ID"""
    try:
        order = db.get_order(order_id)
        if order:
            return jsonify(order), 200
        else:
            return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        logger.error(f"Error in get_order: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    try:
        port = int(os.getenv('PORT', '8101'))
        app.run(host='0.0.0.0', port=port)
    finally:
        publisher.close()

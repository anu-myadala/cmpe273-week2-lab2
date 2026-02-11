from flask import Flask, request, jsonify
import requests
import logging
import os
import sys

sys.path.append('/app/common')
from ids import generate_order_id, current_timestamp

app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory_service:8002')
NOTIFICATION_SERVICE_URL = os.getenv('NOTIFICATION_SERVICE_URL', 'http://notification_service:8003')
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '5'))


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/order', methods=['POST'])
def create_order():
    """
    Create a new order - synchronously calls Inventory and Notification services
    """
    try:
        data = request.json
        
        # Validate input
        if not data or 'user_id' not in data or 'item' not in data:
            return jsonify({"error": "Missing required fields: user_id, item"}), 400
        
        # Generate order ID and timestamp
        order_id = generate_order_id()
        timestamp = current_timestamp()
        
        order_data = {
            "order_id": order_id,
            "user_id": data['user_id'],
            "item": data['item'],
            "quantity": data.get('quantity', 1),
            "timestamp": timestamp
        }
        
        logger.info(f"Creating order {order_id} for user {data['user_id']}")
        
        # Step 1: Call Inventory Service synchronously
        try:
            logger.info(f"Calling inventory service for order {order_id}")
            inventory_response = requests.post(
                f"{INVENTORY_SERVICE_URL}/reserve",
                json=order_data,
                timeout=REQUEST_TIMEOUT
            )
            
            if inventory_response.status_code != 200:
                logger.error(f"Inventory reservation failed for order {order_id}: {inventory_response.text}")
                return jsonify({
                    "order_id": order_id,
                    "status": "failed",
                    "reason": "Inventory reservation failed",
                    "details": inventory_response.json() if inventory_response.content else {}
                }), 500
            
            logger.info(f"Inventory reserved for order {order_id}")
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout calling inventory service for order {order_id}")
            return jsonify({
                "order_id": order_id,
                "status": "failed",
                "reason": "Inventory service timeout"
            }), 504
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling inventory service for order {order_id}: {e}")
            return jsonify({
                "order_id": order_id,
                "status": "failed",
                "reason": f"Inventory service error: {str(e)}"
            }), 500
        
        # Step 2: Call Notification Service synchronously
        try:
            logger.info(f"Calling notification service for order {order_id}")
            notification_response = requests.post(
                f"{NOTIFICATION_SERVICE_URL}/send",
                json=order_data,
                timeout=REQUEST_TIMEOUT
            )
            
            if notification_response.status_code != 200:
                logger.warning(f"Notification failed for order {order_id}, but order is still placed")
            else:
                logger.info(f"Notification sent for order {order_id}")
                
        except Exception as e:
            logger.warning(f"Notification service error for order {order_id}: {e}, but order is still placed")
        
        # Return success
        return jsonify({
            "order_id": order_id,
            "status": "completed",
            "timestamp": timestamp,
            "user_id": data['user_id'],
            "item": data['item'],
            "quantity": data.get('quantity', 1)
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in create_order: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8001'))
    app.run(host='0.0.0.0', port=port)

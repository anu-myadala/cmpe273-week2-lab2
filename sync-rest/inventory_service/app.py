from flask import Flask, request, jsonify
import logging
import time
import os

app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration for fault injection
config = {
    'delay_seconds': 0,
    'failure_enabled': False
}


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/config', methods=['POST'])
def configure():
    """
    Configure fault injection for testing
    Body: {
        "delay_seconds": 0-10,
        "failure_enabled": true/false
    }
    """
    try:
        data = request.json
        
        if 'delay_seconds' in data:
            config['delay_seconds'] = max(0, min(10, float(data['delay_seconds'])))
            logger.info(f"Delay configured to {config['delay_seconds']} seconds")
        
        if 'failure_enabled' in data:
            config['failure_enabled'] = bool(data['failure_enabled'])
            logger.info(f"Failure injection {'enabled' if config['failure_enabled'] else 'disabled'}")
        
        return jsonify({
            "status": "configured",
            "delay_seconds": config['delay_seconds'],
            "failure_enabled": config['failure_enabled']
        }), 200
        
    except Exception as e:
        logger.error(f"Error in configure: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/reserve', methods=['POST'])
def reserve_inventory():
    """
    Reserve inventory for an order
    """
    try:
        data = request.json
        
        if not data or 'order_id' not in data:
            return jsonify({"error": "Missing order_id"}), 400
        
        order_id = data['order_id']
        item = data.get('item', 'unknown')
        quantity = data.get('quantity', 1)
        
        logger.info(f"Reserving inventory for order {order_id}: {quantity}x {item}")
        
        # Apply artificial delay if configured
        if config['delay_seconds'] > 0:
            logger.info(f"Applying artificial delay of {config['delay_seconds']} seconds")
            time.sleep(config['delay_seconds'])
        
        # Apply failure injection if configured
        if config['failure_enabled']:
            logger.error(f"Simulated failure for order {order_id}")
            return jsonify({
                "error": "Inventory service failure (simulated)",
                "order_id": order_id
            }), 500
        
        # Simulate successful inventory reservation
        logger.info(f"Inventory reserved for order {order_id}")
        return jsonify({
            "status": "reserved",
            "order_id": order_id,
            "item": item,
            "quantity": quantity
        }), 200
        
    except Exception as e:
        logger.error(f"Error in reserve_inventory: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8002'))
    app.run(host='0.0.0.0', port=port)

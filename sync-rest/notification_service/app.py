from flask import Flask, request, jsonify
import logging
import os

app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/send', methods=['POST'])
def send_notification():
    """
    Send notification for an order
    """
    try:
        data = request.json
        
        if not data or 'order_id' not in data:
            return jsonify({"error": "Missing order_id"}), 400
        
        order_id = data['order_id']
        user_id = data.get('user_id', 'unknown')
        item = data.get('item', 'unknown')
        
        logger.info(f"Sending notification for order {order_id} to user {user_id}")
        
        # Simulate notification sent
        return jsonify({
            "status": "sent",
            "order_id": order_id,
            "user_id": user_id,
            "message": f"Your order for {item} has been placed successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in send_notification: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8003'))
    app.run(host='0.0.0.0', port=port)

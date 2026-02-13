import json
import os
import uuid
import time
import pika
from flask import Flask, request, jsonify

app = Flask(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

orders = {}


def get_rabbit_connection(retries=10, delay=3):
    for i in range(retries):
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
        except pika.exceptions.AMQPConnectionError:
            print(f"[OrderService] RabbitMQ not ready, retrying ({i+1}/{retries})...")
            time.sleep(delay)
    raise Exception("Could not connect to RabbitMQ")


def setup_exchanges():
    """Declare exchanges and DLQ infrastructure."""
    conn = get_rabbit_connection()
    ch = conn.channel()

    # Main exchange for order events
    ch.exchange_declare(exchange="order_events", exchange_type="fanout", durable=True)

    # Dead-letter exchange
    ch.exchange_declare(exchange="dlx", exchange_type="fanout", durable=True)
    ch.queue_declare(queue="dead_letter_queue", durable=True)
    ch.queue_bind(queue="dead_letter_queue", exchange="dlx")

    # Inventory events exchange
    ch.exchange_declare(exchange="inventory_events", exchange_type="fanout", durable=True)

    conn.close()


@app.route("/order", methods=["POST"])
def create_order():
    data = request.get_json() or {}
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    item = data.get("item", "burger")
    qty = data.get("qty", 1)

    order = {"order_id": order_id, "item": item, "qty": qty, "status": "placed"}
    orders[order_id] = order

    message = {
        "event": "OrderPlaced",
        "order_id": order_id,
        "item": item,
        "qty": qty,
        "timestamp": time.time(),
    }

    conn = get_rabbit_connection()
    ch = conn.channel()
    ch.basic_publish(
        exchange="order_events",
        routing_key="",
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  
            message_id=order_id,
        ),
    )
    conn.close()

    return jsonify(order), 201


@app.route("/orders", methods=["GET"])
def list_orders():
    return jsonify(list(orders.values()))


@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    order = orders.get(order_id)
    if not order:
        return jsonify({"error": "not found"}), 404
    return jsonify(order)


if __name__ == "__main__":
    setup_exchanges()
    app.run(host="0.0.0.0", port=8001)

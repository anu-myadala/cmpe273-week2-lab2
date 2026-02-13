import json
import os
import time
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

inventory = {"burger": 100, "pizza": 100, "salad": 100}
processed_orders = set()  # idempotency: track already-processed order IDs


def get_rabbit_connection(retries=10, delay=3):
    for i in range(retries):
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
        except pika.exceptions.AMQPConnectionError:
            print(f"[InventoryService] RabbitMQ not ready, retrying ({i+1}/{retries})...")
            time.sleep(delay)
    raise Exception("Could not connect to RabbitMQ")


def on_order_placed(ch, method, properties, body):
    try:
        message = json.loads(body)
    except json.JSONDecodeError:
        print(f"[InventoryService] Malformed message, rejecting to DLQ: {body[:100]}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    order_id = message.get("order_id")
    item = message.get("item", "burger")
    qty = message.get("qty", 1)

    if order_id in processed_orders:
        print(f"[InventoryService] Duplicate order {order_id}, skipping (idempotent)")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    print(f"[InventoryService] Processing order {order_id}: {qty}x {item}")

    if item in inventory and inventory[item] >= qty:
        inventory[item] -= qty
        processed_orders.add(order_id)
        event = {
            "event": "InventoryReserved",
            "order_id": order_id,
            "item": item,
            "qty": qty,
            "remaining": inventory[item],
            "timestamp": time.time(),
        }
        print(f"[InventoryService] Reserved {qty}x {item}, remaining: {inventory[item]}")
    else:
        processed_orders.add(order_id)
        event = {
            "event": "InventoryFailed",
            "order_id": order_id,
            "item": item,
            "qty": qty,
            "reason": "insufficient stock",
            "timestamp": time.time(),
        }
        print(f"[InventoryService] Failed to reserve {qty}x {item}")

    ch.basic_publish(
        exchange="inventory_events",
        routing_key="",
        body=json.dumps(event),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    conn = get_rabbit_connection()
    ch = conn.channel()

    ch.exchange_declare(exchange="order_events", exchange_type="fanout", durable=True)
    ch.exchange_declare(exchange="inventory_events", exchange_type="fanout", durable=True)
    ch.exchange_declare(exchange="dlx", exchange_type="fanout", durable=True)

    ch.queue_declare(
        queue="inventory_order_queue",
        durable=True,
        arguments={"x-dead-letter-exchange": "dlx"},
    )
    ch.queue_bind(queue="inventory_order_queue", exchange="order_events")

    ch.queue_declare(queue="dead_letter_queue", durable=True)
    ch.queue_bind(queue="dead_letter_queue", exchange="dlx")

    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue="inventory_order_queue", on_message_callback=on_order_placed)

    print("[InventoryService] Waiting for OrderPlaced events...")
    ch.start_consuming()


if __name__ == "__main__":
    main()

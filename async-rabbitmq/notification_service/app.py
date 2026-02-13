import json
import os
import time
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")


def get_rabbit_connection(retries=10, delay=3):
    for i in range(retries):
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
        except pika.exceptions.AMQPConnectionError:
            print(f"[NotificationService] RabbitMQ not ready, retrying ({i+1}/{retries})...")
            time.sleep(delay)
    raise Exception("Could not connect to RabbitMQ")


def on_inventory_event(ch, method, properties, body):
    try:
        message = json.loads(body)
    except json.JSONDecodeError:
        print(f"[NotificationService] Malformed message: {body[:100]}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    event = message.get("event")
    order_id = message.get("order_id")

    if event == "InventoryReserved":
        print(
            f"[NotificationService] Sending confirmation for order {order_id}: "
            f"{message.get('qty')}x {message.get('item')} reserved successfully"
        )
    elif event == "InventoryFailed":
        print(
            f"[NotificationService] Sending failure notice for order {order_id}: "
            f"{message.get('reason')}"
        )
    else:
        print(f"[NotificationService] Unknown event: {event}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    conn = get_rabbit_connection()
    ch = conn.channel()

    ch.exchange_declare(exchange="inventory_events", exchange_type="fanout", durable=True)

    ch.queue_declare(queue="notification_queue", durable=True)
    ch.queue_bind(queue="notification_queue", exchange="inventory_events")

    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue="notification_queue", on_message_callback=on_inventory_event)

    print("[NotificationService] Waiting for inventory events...")
    ch.start_consuming()


if __name__ == "__main__":
    main()

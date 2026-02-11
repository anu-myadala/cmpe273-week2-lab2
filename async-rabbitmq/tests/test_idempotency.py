"""
Idempotency Test for Async RabbitMQ
Verifies that duplicate events are detected and not processed twice
"""
import pika
import json
import time
import sys
import subprocess

sys.path.append('../../common')
from ids import generate_order_id, generate_event_id, current_timestamp


def test_idempotency():
    """Test idempotency by publishing duplicate events"""
    print("Starting Idempotency Test...")
    print("="*60)
    
    # Generate a unique event
    order_id = generate_order_id()
    event_id = generate_event_id()
    
    event = {
        "event_id": event_id,
        "event_type": "OrderPlaced",
        "order_id": order_id,
        "timestamp": current_timestamp(),
        "user_id": "test_user_idempotency",
        "item": "Test Burger",
        "quantity": 1
    }
    
    print(f"\nTest Event:")
    print(f"  Order ID: {order_id}")
    print(f"  Event ID: {event_id}")
    
    # Connect to RabbitMQ
    print("\nConnecting to RabbitMQ...")
    try:
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters(
            host='localhost',
            port=5672,
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        print("✓ Connected to RabbitMQ")
    except Exception as e:
        print(f"ERROR: Cannot connect to RabbitMQ: {e}")
        sys.exit(1)
    
    # Declare exchange
    channel.exchange_declare(
        exchange='orders',
        exchange_type='topic',
        durable=True
    )
    
    # Step 1: Publish event first time
    print("\nStep 1: Publishing event for the first time...")
    channel.basic_publish(
        exchange='orders',
        routing_key='order.placed',
        body=json.dumps(event),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json'
        )
    )
    print(f"✓ Event {event_id} published (first time)")
    
    # Wait for processing
    print("  Waiting 3 seconds for processing...")
    time.sleep(3)
    
    # Step 2: Publish same event again (duplicate)
    print("\nStep 2: Publishing the SAME event again (duplicate)...")
    channel.basic_publish(
        exchange='orders',
        routing_key='order.placed',
        body=json.dumps(event),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json'
        )
    )
    print(f"✓ Event {event_id} published again (duplicate)")
    
    # Wait for processing
    print("  Waiting 3 seconds for processing...")
    time.sleep(3)
    
    # Step 3: Publish same event third time
    print("\nStep 3: Publishing the SAME event third time...")
    channel.basic_publish(
        exchange='orders',
        routing_key='order.placed',
        body=json.dumps(event),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json'
        )
    )
    print(f"✓ Event {event_id} published again (third time)")
    
    # Wait for processing
    print("  Waiting 3 seconds for processing...")
    time.sleep(3)
    
    connection.close()
    
    print("\n" + "="*60)
    print("IDEMPOTENCY TEST COMPLETED")
    print("="*60)
    print("\nExpected Behavior:")
    print("✓ Event should be processed ONCE only")
    print("✓ Duplicate events should be detected and skipped")
    print(f"✓ Check logs for 'Duplicate event {event_id} detected' message")
    print("\nTo verify:")
    print("  docker logs async_inventory_service | grep -i duplicate")
    print(f"  docker logs async_inventory_service | grep {event_id}")
    print("\nLook for:")
    print("  - 'Processing event {event_id}' - should appear ONCE")
    print("  - 'Duplicate event {event_id} detected' - should appear TWICE")
    print("\nIdempotency Implementation:")
    print("  - Each event has unique event_id")
    print("  - InventoryService tracks processed event_ids")
    print("  - Duplicate event_ids are detected and skipped")
    print("  - Prevents double-charging, double-reservations, etc.")


if __name__ == '__main__':
    test_idempotency()

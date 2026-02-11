"""
DLQ (Dead Letter Queue) Test for Async RabbitMQ
Tests poison message handling and DLQ routing
"""
import pika
import json
import time
import sys
import requests

ORDER_SERVICE_URL = "http://localhost:8101"


def test_dlq():
    """Test DLQ handling with poison messages"""
    print("Starting DLQ/Poison Message Test...")
    print("="*60)
    
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
    
    # Declare exchanges and queues
    channel.exchange_declare(exchange='orders', exchange_type='topic', durable=True)
    
    # Step 1: Send malformed JSON message
    print("\nStep 1: Sending malformed JSON message (poison message)...")
    malformed_message = "{ this is not valid JSON !!!!"
    
    channel.basic_publish(
        exchange='orders',
        routing_key='order.placed',
        body=malformed_message,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json'
        )
    )
    print("✓ Poison message sent")
    print(f"  Content: {malformed_message}")
    
    # Wait for processing
    print("  Waiting 5 seconds for DLQ routing...")
    time.sleep(5)
    
    # Step 2: Send valid messages
    print("\nStep 2: Sending 10 valid messages after poison message...")
    for i in range(10):
        order_data = {
            "user_id": f"user_dlq_test_{i}",
            "item": "DLQ Test Burger",
            "quantity": 1
        }
        try:
            response = requests.post(
                f"{ORDER_SERVICE_URL}/order",
                json=order_data,
                timeout=5
            )
            if response.status_code == 202:
                if (i + 1) % 5 == 0:
                    print(f"  Sent {i+1}/10 valid messages")
        except Exception as e:
            print(f"  Error sending message {i}: {e}")
    
    print("✓ 10 valid messages sent")
    
    # Wait for processing
    print("  Waiting 5 seconds for processing...")
    time.sleep(5)
    
    # Step 3: Check DLQ
    print("\nStep 3: Checking DLQ for poison message...")
    try:
        # Check if DLQ has messages
        dlq_result = channel.queue_declare(queue='order-events-dlq', durable=True, passive=True)
        dlq_message_count = dlq_result.method.message_count
        
        print(f"✓ DLQ message count: {dlq_message_count}")
        
        if dlq_message_count > 0:
            print("✓ Poison message successfully routed to DLQ")
            
            # Get message from DLQ
            method, properties, body = channel.basic_get(queue='order-events-dlq', auto_ack=False)
            if method:
                print(f"\nDLQ Message Content:")
                print(f"  Body: {body.decode() if body else 'None'}")
                print(f"  Routing Key: {method.routing_key}")
                # Don't ack - leave in DLQ for inspection
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            print("⚠ No messages in DLQ")
            print("  This could mean:")
            print("  - Poison message was not sent")
            print("  - DLQ routing is not configured correctly")
            print("  - Message was processed successfully (unlikely)")
    
    except Exception as e:
        print(f"  Error checking DLQ: {e}")
    
    connection.close()
    
    print("\n" + "="*60)
    print("DLQ TEST COMPLETED")
    print("="*60)
    print("\nExpected Behavior:")
    print("✓ Malformed JSON should be rejected by consumer")
    print("✓ Rejected message should be routed to DLQ")
    print("✓ Valid messages should continue processing normally")
    print("✓ Service should not crash on poison message")
    print("\nTo verify:")
    print("  1. Check inventory service logs:")
    print("     docker logs async_inventory_service | grep -i 'invalid json'")
    print("\n  2. Check RabbitMQ Management UI:")
    print("     http://localhost:15672")
    print("     - Queues tab")
    print("     - Look for 'order-events-dlq' queue")
    print("     - Should have 1 message")
    print("\n  3. Check that valid messages were processed:")
    print("     docker logs async_inventory_service | grep -i 'inventory reserved'")
    print("\nDLQ Configuration:")
    print("  - Queue: order-events-dlq")
    print("  - Routing: x-dead-letter-exchange: 'dlx'")
    print("  - Trigger: Message rejected with requeue=False")
    print("  - Purpose: Isolate poison messages for debugging")


if __name__ == '__main__':
    test_dlq()

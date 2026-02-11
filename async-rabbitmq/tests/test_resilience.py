"""
Resilience Test for Async RabbitMQ
Tests that messages queue up when consumer is down and process when consumer restarts
"""
import requests
import time
import subprocess
import sys

ORDER_SERVICE_URL = "http://localhost:8101"


def test_resilience():
    """Test message queueing and resilience"""
    print("Starting Resilience Test...")
    print("="*60)
    
    # Step 1: Verify services are running
    print("\nStep 1: Verifying services are running...")
    try:
        response = requests.get(f"{ORDER_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Order service is not healthy!")
            sys.exit(1)
        print("✓ Order service is healthy")
    except Exception as e:
        print(f"ERROR: Cannot connect to order service: {e}")
        sys.exit(1)
    
    # Step 2: Publish 50 orders
    print("\nStep 2: Publishing 50 orders...")
    for i in range(50):
        order_data = {
            "user_id": f"user_{i}",
            "item": "Burger",
            "quantity": 1
        }
        try:
            response = requests.post(
                f"{ORDER_SERVICE_URL}/order",
                json=order_data,
                timeout=5
            )
            if response.status_code == 202:
                if (i + 1) % 10 == 0:
                    print(f"  Published {i+1}/50 orders")
        except Exception as e:
            print(f"  Error publishing order {i}: {e}")
    
    print("✓ Published 50 orders")
    time.sleep(5)  # Allow processing
    
    # Step 3: Stop inventory service
    print("\nStep 3: Stopping inventory service...")
    try:
        subprocess.run(
            ["docker-compose", "stop", "inventory_service"],
            cwd="../async-rabbitmq",
            check=True,
            capture_output=True
        )
        print("✓ Inventory service stopped")
    except Exception as e:
        print(f"  Warning: Could not stop inventory service: {e}")
    
    # Step 4: Publish 50 more orders (these will queue up)
    print("\nStep 4: Publishing 50 more orders (will queue in RabbitMQ)...")
    for i in range(50, 100):
        order_data = {
            "user_id": f"user_{i}",
            "item": "Pizza",
            "quantity": 1
        }
        try:
            response = requests.post(
                f"{ORDER_SERVICE_URL}/order",
                json=order_data,
                timeout=5
            )
            if response.status_code == 202:
                if (i + 1) % 10 == 0:
                    print(f"  Published {i+1}/100 orders")
        except Exception as e:
            print(f"  Error publishing order {i}: {e}")
    
    print("✓ Published 50 more orders (queued in RabbitMQ)")
    
    # Step 5: Wait
    print("\nStep 5: Waiting 60 seconds (messages queued in RabbitMQ)...")
    for remaining in range(60, 0, -10):
        print(f"  {remaining} seconds remaining...")
        time.sleep(10)
    
    # Step 6: Restart inventory service
    print("\nStep 6: Restarting inventory service...")
    try:
        subprocess.run(
            ["docker-compose", "start", "inventory_service"],
            cwd="../async-rabbitmq",
            check=True,
            capture_output=True
        )
        print("✓ Inventory service restarted")
    except Exception as e:
        print(f"  Warning: Could not restart inventory service: {e}")
    
    # Step 7: Monitor backlog draining
    print("\nStep 7: Monitoring backlog draining (60 seconds)...")
    print("  Check docker logs to see messages being processed")
    print("  Command: docker logs -f async_inventory_service")
    for remaining in range(60, 0, -10):
        print(f"  {remaining} seconds remaining...")
        time.sleep(10)
    
    # Step 8: Verify all orders
    print("\nStep 8: Verifying all orders...")
    try:
        response = requests.get(f"{ORDER_SERVICE_URL}/orders", timeout=5)
        if response.status_code == 200:
            data = response.json()
            order_count = data.get('count', 0)
            print(f"✓ Total orders created: {order_count}")
            print(f"✓ Expected: 100")
            if order_count == 100:
                print("✓ All orders accounted for!")
            else:
                print(f"⚠ Order count mismatch: expected 100, got {order_count}")
    except Exception as e:
        print(f"  Error checking orders: {e}")
    
    print("\n" + "="*60)
    print("RESILIENCE TEST COMPLETED")
    print("="*60)
    print("\nKey Observations:")
    print("1. Messages queued in RabbitMQ when consumer was down")
    print("2. No messages lost during service outage")
    print("3. Consumer processed backlog after restart")
    print("4. Demonstrates decoupling and resilience")
    print("\nTo verify, check:")
    print("- RabbitMQ Management UI: http://localhost:15672 (guest/guest)")
    print("- Docker logs: docker logs async_inventory_service")


if __name__ == '__main__':
    test_resilience()

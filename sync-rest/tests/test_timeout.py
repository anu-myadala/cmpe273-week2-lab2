"""
Timeout Test for Synchronous REST
Configures InventoryService delay to exceed OrderService timeout and measures 504 responses.
"""
import requests
import time
import csv
from datetime import datetime

ORDER_SERVICE_URL = "http://localhost:8001"
INVENTORY_SERVICE_URL = "http://localhost:8002"
NUM_REQUESTS = 20
DELAY_SECONDS = 10  # Exceeds REQUEST_TIMEOUT=5s


def test_timeout_behavior():
    """Test that OrderService returns 504 when InventoryService is too slow"""
    print("Starting Timeout Behavior Test...")

    # Step 1: Configure long delay in inventory service
    print(f"\nConfiguring {DELAY_SECONDS}s delay in inventory service...")
    try:
        config_response = requests.post(
            f"{INVENTORY_SERVICE_URL}/config",
            json={"delay_seconds": DELAY_SECONDS, "failure_enabled": False},
            timeout=5
        )
        if config_response.status_code == 200:
            print("✓ Delay configured successfully")
        else:
            print(f"✗ Failed to configure delay: {config_response.text}")
            return
    except Exception as e:
        print(f"✗ Error configuring delay: {e}")
        return

    print(f"\nSending {NUM_REQUESTS} requests; expecting HTTP 504 Gateway Timeout responses...")

    results = []
    timeouts = 0
    successes = 0
    failures = 0

    for i in range(NUM_REQUESTS):
        order_data = {
            "user_id": f"timeout_user_{i}",
            "item": "Timeout Burger",
            "quantity": 1
        }

        start_time = time.time()
        try:
            response = requests.post(
                f"{ORDER_SERVICE_URL}/order",
                json=order_data,
                timeout=12  # client timeout longer than server
            )
            elapsed_ms = (time.time() - start_time) * 1000

            outcome = ""
            if response.status_code == 504:
                outcome = "server_timeout_504"
                timeouts += 1
            elif response.status_code == 200:
                outcome = "success"
                successes += 1
            else:
                outcome = f"error_{response.status_code}"
                failures += 1

            results.append({
                "request": i + 1,
                "status_code": response.status_code,
                "latency_ms": f"{elapsed_ms:.2f}",
                "outcome": outcome
            })

            if (i + 1) % 5 == 0:
                print(f"  Progress: {i+1}/{NUM_REQUESTS} (timeouts so far: {timeouts})")

        except requests.exceptions.Timeout:
            elapsed_ms = (time.time() - start_time) * 1000
            results.append({
                "request": i + 1,
                "status_code": "CLIENT_TIMEOUT",
                "latency_ms": f"{elapsed_ms:.2f}",
                "outcome": "client_timeout"
            })
            failures += 1

    # Step 3: Reset delay to 0
    print("\nResetting delay to 0...")
    try:
        reset_response = requests.post(
            f"{INVENTORY_SERVICE_URL}/config",
            json={"delay_seconds": 0, "failure_enabled": False},
            timeout=5
        )
        if reset_response.status_code == 200:
            print("✓ Delay reset successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not reset delay: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TIMEOUT TEST RESULTS")
    print("=" * 60)
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"HTTP 504 Timeouts: {timeouts}")
    print(f"Successful (200): {successes}")
    print(f"Other Failures: {failures}")
    print("=" * 60)

    # Export CSV
    with open('timeout_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Request', 'Status Code', 'Outcome', 'Latency (ms)'])
        for r in results:
            writer.writerow([r['request'], r['status_code'], r['outcome'], r['latency_ms']])
        writer.writerow([])
        writer.writerow(['Summary', '', '', ''])
        writer.writerow(['Total Requests', NUM_REQUESTS, '', ''])
        writer.writerow(['HTTP 504 Timeouts', timeouts, '', ''])
        writer.writerow(['Successful (200)', successes, '', ''])
        writer.writerow(['Other Failures', failures, '', ''])
        writer.writerow(['Timestamp', datetime.now().isoformat(), '', ''])

    print("\n✓ Results exported to timeout_results.csv")


if __name__ == '__main__':
    # Check health endpoints
    try:
        r1 = requests.get(f"{ORDER_SERVICE_URL}/health", timeout=5)
        r2 = requests.get(f"{INVENTORY_SERVICE_URL}/health", timeout=5)
        if r1.status_code == 200 and r2.status_code == 200:
            print("Services healthy. Starting test...\n")
            test_timeout_behavior()
        else:
            print("ERROR: One or more services unhealthy")
    except Exception as e:
        print(f"ERROR: Cannot reach services: {e}")

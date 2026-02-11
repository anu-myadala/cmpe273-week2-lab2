"""
Failure Injection Test for Synchronous REST
Makes InventoryService return 500 errors and observes OrderService behavior.
"""
import requests
import time
import csv
from datetime import datetime

ORDER_SERVICE_URL = "http://localhost:8001"
INVENTORY_SERVICE_URL = "http://localhost:8002"
NUM_REQUESTS = 50


def test_failure_injection():
    """Test error handling with inventory service failures"""
    print("Starting Failure Injection Test...")
    
    # Step 1: Enable failure injection in inventory service
    print(f"\nEnabling failure injection in inventory service...")
    try:
        config_response = requests.post(
            f"{INVENTORY_SERVICE_URL}/config",
            json={"delay_seconds": 0, "failure_enabled": True},
            timeout=5
        )
        if config_response.status_code == 200:
            print(f"✓ Failure injection enabled")
        else:
            print(f"✗ Failed to enable failure injection: {config_response.text}")
            return
    except Exception as e:
        print(f"✗ Error enabling failure injection: {e}")
        return
    
    # Step 2: Send requests and observe failures
    print(f"\nSending {NUM_REQUESTS} requests with failure injection enabled...")
    
    results = []
    successful_orders = 0
    failed_orders = 0
    timeout_errors = 0
    server_errors = 0
    
    for i in range(NUM_REQUESTS):
        order_data = {
            "user_id": f"user_{i}",
            "item": "Salad",
            "quantity": 1
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{ORDER_SERVICE_URL}/order",
                json=order_data,
                timeout=10
            )
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            result = {
                'request_num': i + 1,
                'status_code': response.status_code,
                'latency_ms': latency_ms,
                'response': response.json() if response.content else {}
            }
            
            if response.status_code == 200:
                successful_orders += 1
                result['outcome'] = 'success'
            elif response.status_code == 504:
                timeout_errors += 1
                failed_orders += 1
                result['outcome'] = 'timeout'
            elif response.status_code >= 500:
                server_errors += 1
                failed_orders += 1
                result['outcome'] = 'server_error'
            else:
                failed_orders += 1
                result['outcome'] = 'other_error'
            
            results.append(result)
        
        except requests.exceptions.Timeout:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            timeout_errors += 1
            failed_orders += 1
            results.append({
                'request_num': i + 1,
                'status_code': 'TIMEOUT',
                'latency_ms': latency_ms,
                'outcome': 'client_timeout',
                'response': {}
            })
        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            failed_orders += 1
            results.append({
                'request_num': i + 1,
                'status_code': 'ERROR',
                'latency_ms': latency_ms,
                'outcome': 'exception',
                'response': {'error': str(e)}
            })
        
        # Print progress
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/{NUM_REQUESTS} requests completed")
    
    # Step 3: Disable failure injection
    print(f"\nDisabling failure injection...")
    try:
        reset_response = requests.post(
            f"{INVENTORY_SERVICE_URL}/config",
            json={"delay_seconds": 0, "failure_enabled": False},
            timeout=5
        )
        if reset_response.status_code == 200:
            print(f"✓ Failure injection disabled")
    except Exception as e:
        print(f"⚠ Warning: Could not disable failure injection: {e}")
    
    # Calculate statistics
    print("\n" + "="*60)
    print("FAILURE INJECTION TEST RESULTS")
    print("="*60)
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"Successful Orders: {successful_orders}")
    print(f"Failed Orders: {failed_orders}")
    print(f"  - Server Errors (5xx): {server_errors}")
    print(f"  - Timeouts: {timeout_errors}")
    print(f"\nFailure Rate: {(failed_orders / NUM_REQUESTS * 100):.1f}%")
    print("="*60)
    
    # Show sample failures
    print("\nSample Error Responses:")
    for result in results[:5]:
        print(f"\nRequest #{result['request_num']}:")
        print(f"  Status: {result['status_code']}")
        print(f"  Outcome: {result['outcome']}")
        print(f"  Latency: {result['latency_ms']:.2f}ms")
        if result['response']:
            print(f"  Response: {result['response']}")
    
    # Export to CSV
    with open('failure_results.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Request', 'Status Code', 'Outcome', 'Latency (ms)'])
        for result in results:
            writer.writerow([
                result['request_num'],
                result['status_code'],
                result['outcome'],
                f"{result['latency_ms']:.2f}"
            ])
        
        # Add summary
        writer.writerow([])
        writer.writerow(['Summary', '', '', ''])
        writer.writerow(['Total Requests', NUM_REQUESTS, '', ''])
        writer.writerow(['Successful', successful_orders, '', ''])
        writer.writerow(['Failed', failed_orders, '', ''])
        writer.writerow(['Server Errors', server_errors, '', ''])
        writer.writerow(['Timeouts', timeout_errors, '', ''])
        writer.writerow(['Failure Rate %', f"{(failed_orders / NUM_REQUESTS * 100):.1f}", '', ''])
        writer.writerow(['Timestamp', datetime.now().isoformat(), '', ''])
    
    print(f"\nResults exported to failure_results.csv")


if __name__ == '__main__':
    # Check if services are healthy
    try:
        response = requests.get(f"{ORDER_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Order service is not healthy!")
            exit(1)
        
        response = requests.get(f"{INVENTORY_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Inventory service is not healthy!")
            exit(1)
        
        print("All services are healthy. Starting test...\n")
    except Exception as e:
        print(f"ERROR: Cannot connect to services: {e}")
        exit(1)
    
    test_failure_injection()

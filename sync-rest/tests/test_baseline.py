"""
Baseline Latency Test for Synchronous REST
Sends 100 requests to OrderService and measures P50, P95, P99 latencies.
"""
import requests
import time
import statistics
import csv
from datetime import datetime

ORDER_SERVICE_URL = "http://localhost:8001"
NUM_REQUESTS = 100


def test_baseline_latency():
    """Test baseline latency without any fault injection"""
    print("Starting Baseline Latency Test...")
    print(f"Sending {NUM_REQUESTS} requests to {ORDER_SERVICE_URL}/order")
    
    latencies = []
    successful_requests = 0
    failed_requests = 0
    
    for i in range(NUM_REQUESTS):
        order_data = {
            "user_id": f"user_{i}",
            "item": "Burger",
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
            latencies.append(latency_ms)
            
            if response.status_code == 200:
                successful_requests += 1
            else:
                failed_requests += 1
                print(f"Request {i+1} failed with status {response.status_code}")
        
        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            failed_requests += 1
            print(f"Request {i+1} failed with error: {e}")
        
        # Print progress
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/{NUM_REQUESTS} requests completed")
    
    # Calculate statistics
    if latencies:
        latencies_sorted = sorted(latencies)
        p50 = statistics.median(latencies)
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        avg = statistics.mean(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        print("\n" + "="*60)
        print("BASELINE LATENCY TEST RESULTS")
        print("="*60)
        print(f"Total Requests: {NUM_REQUESTS}")
        print(f"Successful: {successful_requests}")
        print(f"Failed: {failed_requests}")
        print(f"\nLatency Statistics (ms):")
        print(f"  Average: {avg:.2f}")
        print(f"  Median (P50): {p50:.2f}")
        print(f"  P95: {p95:.2f}")
        print(f"  P99: {p99:.2f}")
        print(f"  Min: {min_latency:.2f}")
        print(f"  Max: {max_latency:.2f}")
        print("="*60)
        
        # Export to CSV
        with open('baseline_results.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Metric', 'Value (ms)'])
            writer.writerow(['Average', f'{avg:.2f}'])
            writer.writerow(['P50', f'{p50:.2f}'])
            writer.writerow(['P95', f'{p95:.2f}'])
            writer.writerow(['P99', f'{p99:.2f}'])
            writer.writerow(['Min', f'{min_latency:.2f}'])
            writer.writerow(['Max', f'{max_latency:.2f}'])
            writer.writerow(['Total Requests', NUM_REQUESTS])
            writer.writerow(['Successful', successful_requests])
            writer.writerow(['Failed', failed_requests])
            writer.writerow(['Timestamp', datetime.now().isoformat()])
        
        print(f"\nResults exported to baseline_results.csv")
        
        # Also export individual latencies
        with open('baseline_latencies.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Request', 'Latency (ms)'])
            for i, latency in enumerate(latencies, 1):
                writer.writerow([i, f'{latency:.2f}'])
        
        print(f"Individual latencies exported to baseline_latencies.csv")


if __name__ == '__main__':
    # Check if service is healthy
    try:
        response = requests.get(f"{ORDER_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Order service is not healthy!")
            exit(1)
        print("Order service is healthy. Starting test...\n")
    except Exception as e:
        print(f"ERROR: Cannot connect to order service: {e}")
        exit(1)
    
    test_baseline_latency()

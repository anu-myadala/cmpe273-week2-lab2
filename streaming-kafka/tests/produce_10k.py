"""
High Volume Test - Produce 10,000 events
Tests throughput and performance with batch production
"""
import requests
import time
import json
import sys

PRODUCER_URL = "http://localhost:8201"
TOTAL_EVENTS = 10000
BATCH_SIZE = 100


def produce_10k_events():
    """Produce 10,000 events using batch API"""
    print("Starting High Volume Test - 10,000 Events")
    print("="*60)
    
    # Verify service is healthy
    print("\nVerifying producer service...")
    try:
        response = requests.get(f"{PRODUCER_URL}/health", timeout=5)
        if response.status_code != 200:
            print("ERROR: Producer service not healthy!")
            sys.exit(1)
        print("✓ Producer service is healthy")
    except Exception as e:
        print(f"ERROR: Cannot connect to producer: {e}")
        sys.exit(1)
    
    # Calculate number of batches
    num_batches = TOTAL_EVENTS // BATCH_SIZE
    
    print(f"\nProducing {TOTAL_EVENTS} events in {num_batches} batches of {BATCH_SIZE}")
    print("Starting production...\n")
    
    start_time = time.time()
    total_produced = 0
    batch_times = []
    
    for batch_num in range(num_batches):
        # Create batch of orders
        orders = []
        for i in range(BATCH_SIZE):
            order = {
                "user_id": f"user_{batch_num * BATCH_SIZE + i}",
                "item": ["Burger", "Pizza", "Salad", "Sandwich", "Pasta"][i % 5],
                "quantity": (i % 3) + 1
            }
            orders.append(order)
        
        # Send batch
        batch_start = time.time()
        try:
            response = requests.post(
                f"{PRODUCER_URL}/orders/batch",
                json={"orders": orders},
                timeout=30
            )
            batch_end = time.time()
            batch_time = (batch_end - batch_start) * 1000
            
            if response.status_code == 202:
                total_produced += BATCH_SIZE
                batch_times.append(batch_time)
                
                if (batch_num + 1) % 10 == 0:
                    avg_batch_time = sum(batch_times[-10:]) / min(10, len(batch_times))
                    print(f"  Progress: {total_produced}/{TOTAL_EVENTS} events "
                          f"(Batch {batch_num + 1}/{num_batches}, "
                          f"Avg batch time: {avg_batch_time:.0f}ms)")
            else:
                print(f"  Batch {batch_num + 1} failed: {response.status_code}")
        
        except Exception as e:
            print(f"  Error in batch {batch_num + 1}: {e}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Calculate metrics
    events_per_second = total_produced / elapsed if elapsed > 0 else 0
    avg_batch_time = sum(batch_times) / len(batch_times) if batch_times else 0
    
    print("\n" + "="*60)
    print("HIGH VOLUME TEST RESULTS")
    print("="*60)
    print(f"Total Events: {total_produced}/{TOTAL_EVENTS}")
    print(f"Total Time: {elapsed:.2f} seconds")
    print(f"Throughput: {events_per_second:.2f} events/second")
    print(f"Average Batch Time: {avg_batch_time:.0f}ms")
    print(f"Batches: {num_batches}")
    print(f"Batch Size: {BATCH_SIZE}")
    print("="*60)
    
    # Export results
    results = {
        "test": "high_volume_10k",
        "total_events": total_produced,
        "target_events": TOTAL_EVENTS,
        "elapsed_seconds": round(elapsed, 2),
        "throughput_events_per_second": round(events_per_second, 2),
        "batch_size": BATCH_SIZE,
        "num_batches": num_batches,
        "avg_batch_time_ms": round(avg_batch_time, 2),
        "min_batch_time_ms": round(min(batch_times), 2) if batch_times else 0,
        "max_batch_time_ms": round(max(batch_times), 2) if batch_times else 0
    }
    
    with open('high_volume_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results exported to high_volume_results.json")
    
    print("\nMonitoring Tips:")
    print("1. Check consumer lag:")
    print("   docker exec streaming_kafka kafka-consumer-groups \\")
    print("     --bootstrap-server localhost:9092 \\")
    print("     --describe --group inventory-group")
    print("\n2. Check analytics metrics:")
    print("   docker logs streaming_analytics_consumer | tail -20")
    print("\n3. View metrics file:")
    print("   cat streaming-kafka/analytics_output/metrics_output.json")


if __name__ == '__main__':
    produce_10k_events()

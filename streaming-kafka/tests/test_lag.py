"""
Consumer Lag Test
Tests consumer lag behavior with throttled consumer
"""
import requests
import time
import subprocess
import sys
import json

PRODUCER_URL = "http://localhost:8201"
NUM_EVENTS = 1000
BATCH_SIZE = 100


def get_consumer_lag(group_id):
    """Get consumer lag from Kafka"""
    try:
        result = subprocess.run(
            [
                "docker", "exec", "streaming_kafka",
                "kafka-consumer-groups",
                "--bootstrap-server", "localhost:9092",
                "--describe",
                "--group", group_id
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            total_lag = 0
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        lag = int(parts[5])
                        total_lag += lag
                    except (ValueError, IndexError):
                        pass
            return total_lag
        return None
    except Exception as e:
        print(f"Error getting lag: {e}")
        return None


def test_consumer_lag():
    """Test consumer lag with rapid production"""
    print("Starting Consumer Lag Test")
    print("="*60)
    
    # Verify service
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
    
    # Get initial lag
    print("\nChecking initial consumer lag...")
    initial_lag = get_consumer_lag("analytics-group")
    print(f"Initial lag: {initial_lag if initial_lag is not None else 'unknown'}")
    
    # Produce events rapidly
    print(f"\nProducing {NUM_EVENTS} events rapidly...")
    start_time = time.time()
    
    num_batches = NUM_EVENTS // BATCH_SIZE
    for batch_num in range(num_batches):
        orders = []
        for i in range(BATCH_SIZE):
            orders.append({
                "user_id": f"lag_test_user_{batch_num * BATCH_SIZE + i}",
                "item": "Test Item",
                "quantity": 1
            })
        
        try:
            response = requests.post(
                f"{PRODUCER_URL}/orders/batch",
                json={"orders": orders},
                timeout=10
            )
            if (batch_num + 1) % 2 == 0:
                print(f"  Produced {(batch_num + 1) * BATCH_SIZE}/{NUM_EVENTS} events")
        except Exception as e:
            print(f"  Error: {e}")
    
    production_time = time.time() - start_time
    print(f"✓ Production complete in {production_time:.2f}s")
    
    # Monitor lag over time
    print("\nMonitoring consumer lag (60 seconds)...")
    print("Time(s) | Analytics Lag | Inventory Lag")
    print("-" * 50)
    
    lag_data = []
    monitoring_duration = 60
    check_interval = 10
    
    for elapsed in range(0, monitoring_duration + 1, check_interval):
        analytics_lag = get_consumer_lag("analytics-group")
        inventory_lag = get_consumer_lag("inventory-group")
        
        print(f"{elapsed:6d}  | {analytics_lag if analytics_lag is not None else 'N/A':13} | "
              f"{inventory_lag if inventory_lag is not None else 'N/A'}")
        
        lag_data.append({
            "elapsed_seconds": elapsed,
            "analytics_lag": analytics_lag,
            "inventory_lag": inventory_lag
        })
        
        if elapsed < monitoring_duration:
            time.sleep(check_interval)
    
    print("\n" + "="*60)
    print("CONSUMER LAG TEST RESULTS")
    print("="*60)
    print(f"Events Produced: {NUM_EVENTS}")
    print(f"Production Time: {production_time:.2f}s")
    print(f"Throughput: {NUM_EVENTS / production_time:.2f} events/s")
    print("\nLag Observations:")
    if lag_data:
        print(f"  Initial lag: {lag_data[0]['analytics_lag']}")
        print(f"  Peak lag: {max(d['analytics_lag'] for d in lag_data if d['analytics_lag'] is not None)}")
        print(f"  Final lag: {lag_data[-1]['analytics_lag']}")
    print("="*60)
    
    # Export results
    results = {
        "test": "consumer_lag",
        "events_produced": NUM_EVENTS,
        "production_time_seconds": round(production_time, 2),
        "throughput_events_per_second": round(NUM_EVENTS / production_time, 2),
        "lag_measurements": lag_data
    }
    
    with open('lag_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Also export CSV
    with open('lag_results.csv', 'w') as f:
        f.write('Elapsed(s),Analytics Lag,Inventory Lag\n')
        for data in lag_data:
            f.write(f"{data['elapsed_seconds']},{data['analytics_lag']},{data['inventory_lag']}\n")
    
    print(f"\n✓ Results exported to lag_results.json and lag_results.csv")
    
    print("\nKey Observations:")
    print("- Consumer lag increases when production rate > consumption rate")
    print("- Kafka persists messages while consumers catch up")
    print("- Multiple consumer groups process independently")
    print("- Consumers eventually catch up (lag → 0)")


if __name__ == '__main__':
    test_consumer_lag()

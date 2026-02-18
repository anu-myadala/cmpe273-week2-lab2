"""
Consumer Lag Test (with optional throttling)
Demonstrates consumer lag under throttling and recovery when throttling is removed.

How it works:
- Restarts the analytics_consumer with ANALYTICS_PROCESSING_DELAY_MS (default: 200ms)
- Produces a burst of events
- Monitors lag while throttled
- Restarts analytics_consumer with delay=0 and shows backlog draining
"""
import os
import requests
import time
import subprocess
import sys
import json

PRODUCER_URL = os.getenv("PRODUCER_URL", "http://localhost:8201")
NUM_EVENTS = int(os.getenv("NUM_EVENTS", "1000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))

# Throttling controls (used by docker-compose.yml env substitution)
THROTTLE_DELAY_MS = int(os.getenv("THROTTLE_DELAY_MS", "200"))
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "../docker-compose.yml")


def run(cmd, *, env=None, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)


def restart_analytics_consumer(delay_ms):
    """Restart analytics consumer with a per-message processing delay."""
    print(f"\nRestarting analytics_consumer with delay={delay_ms}ms...")
    # Stop service first (ignore failures if it's not running)
    try:
        run(["docker", "compose", "-f", COMPOSE_FILE, "stop", "analytics_consumer"], timeout=120)
    except Exception:
        pass

    env = os.environ.copy()
    env["ANALYTICS_PROCESSING_DELAY_MS"] = str(delay_ms)

    result = run(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d", "--build", "analytics_consumer"], env=env, timeout=300)
    if result.returncode != 0:
        print("ERROR: Could not restart analytics_consumer:")
        print(result.stderr or result.stdout)
        sys.exit(1)

    time.sleep(5)
    print("✓ analytics_consumer restarted")


def get_consumer_lag(group_id):
    """Get consumer lag from Kafka."""
    try:
        result = run(
            [
                "docker", "exec", "streaming_kafka",
                "kafka-consumer-groups",
                "--bootstrap-server", "localhost:9092",
                "--describe",
                "--group", group_id
            ],
            timeout=20
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            total_lag = 0
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        total_lag += int(parts[5])
                    except (ValueError, IndexError):
                        pass
            return total_lag
        return None
    except Exception as e:
        print(f"Error getting lag: {e}")
        return None


def produce_burst():
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
            requests.post(
                f"{PRODUCER_URL}/orders/batch",
                json={"orders": orders},
                timeout=10
            )
            if (batch_num + 1) % 2 == 0:
                print(f"  Produced {(batch_num + 1) * BATCH_SIZE}/{NUM_EVENTS} events")
        except Exception as e:
            print(f"  Error producing batch {batch_num}: {e}")

    production_time = time.time() - start_time
    print(f"✓ Production complete in {production_time:.2f}s")
    return production_time


def monitor_lag(duration_seconds, interval_seconds, label):
    print(f"\nMonitoring lag: {label} ({duration_seconds}s)...")
    print("Time(s) | Analytics Lag | Inventory Lag")
    print("-" * 50)

    lag_data = []
    for elapsed in range(0, duration_seconds + 1, interval_seconds):
        analytics_lag = get_consumer_lag("analytics-group")
        inventory_lag = get_consumer_lag("inventory-group")

        print(f"{elapsed:6d}  | {analytics_lag if analytics_lag is not None else 'N/A':13} | "
              f"{inventory_lag if inventory_lag is not None else 'N/A'}")

        lag_data.append({
            "phase": label,
            "elapsed_seconds": elapsed,
            "analytics_lag": analytics_lag,
            "inventory_lag": inventory_lag
        })

        if elapsed < duration_seconds:
            time.sleep(interval_seconds)

    return lag_data


def test_consumer_lag():
    print("Starting Consumer Lag Test (Throttling + Recovery)")
    print("=" * 60)

    # Verify producer
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

    # Throttle analytics consumer so lag is visible
    restart_analytics_consumer(THROTTLE_DELAY_MS)

    # Initial lag
    print("\nChecking initial consumer lag...")
    initial_lag = get_consumer_lag("analytics-group")
    print(f"Initial analytics lag: {initial_lag if initial_lag is not None else 'unknown'}")

    # Produce burst
    production_time = produce_burst()

    # Phase 1: lag under throttling
    lag_data = []
    lag_data += monitor_lag(duration_seconds=30, interval_seconds=5, label=f"throttled_{THROTTLE_DELAY_MS}ms")

    # Remove throttling and show drain
    restart_analytics_consumer(0)
    lag_data += monitor_lag(duration_seconds=60, interval_seconds=10, label="unthrottled_0ms")

    # Summarize
    analytics_lags = [d["analytics_lag"] for d in lag_data if d["analytics_lag"] is not None]
    peak_lag = max(analytics_lags) if analytics_lags else None
    final_lag = lag_data[-1]["analytics_lag"] if lag_data else None

    print("\n" + "=" * 60)
    print("CONSUMER LAG TEST RESULTS")
    print("=" * 60)
    print(f"Throttle delay: {THROTTLE_DELAY_MS}ms (analytics_consumer)")
    print(f"Events Produced: {NUM_EVENTS}")
    print(f"Production Time: {production_time:.2f}s")
    print(f"Producer Throughput: {NUM_EVENTS / production_time:.2f} events/s")
    print(f"Peak analytics lag: {peak_lag}")
    print(f"Final analytics lag: {final_lag}")
    print("=" * 60)

    results = {
        "test": "consumer_lag_throttling",
        "throttle_delay_ms": THROTTLE_DELAY_MS,
        "events_produced": NUM_EVENTS,
        "production_time_seconds": round(production_time, 2),
        "throughput_events_per_second": round(NUM_EVENTS / production_time, 2),
        "lag_measurements": lag_data
    }

    with open('lag_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    with open('lag_results.csv', 'w') as f:
        f.write('Phase,Elapsed(s),Analytics Lag,Inventory Lag\n')
        for d in lag_data:
            f.write(f"{d['phase']},{d['elapsed_seconds']},{d['analytics_lag']},{d['inventory_lag']}\n")

    print("\n✓ Results exported to lag_results.json and lag_results.csv")
    print("\nWhat to screenshot for Part C:")
    print("- The lag table during throttling showing lag increase")
    print("- The lag table after unthrottling showing lag draining to ~0")


if __name__ == '__main__':
    test_consumer_lag()

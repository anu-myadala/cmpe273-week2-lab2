# Streaming Kafka Tests

This directory contains automated tests for the streaming Kafka implementation.

## Prerequisites

- Docker and Docker Compose installed
- Services running: `docker-compose up -d`
- Python 3.11+ with requests: `pip install requests`

## Tests

### 1. High Volume Test (`produce_10k.py`)

Produces 10,000 events rapidly to test throughput and performance.

**What it does:**
- Uses batch API to produce 10,000 events
- Batch size: 100 events per request
- Measures throughput (events/second)
- Exports metrics to `high_volume_results.json`

**How to run:**
```bash
cd streaming-kafka/tests
python produce_10k.py
```

**Expected output:**
- ~1000-5000 events/second throughput
- Batch processing completes in seconds
- All events successfully produced

**To monitor:**
```bash
# Check consumer lag
docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group analytics-group

# Watch analytics logs
docker logs -f streaming_analytics_consumer
```

### 2. Consumer Lag Test (`test_lag.py`)

Tests consumer lag behavior when production rate exceeds consumption rate.

**What it does:**
1. Produces 1,000 events rapidly
2. Monitors consumer lag every 10 seconds for 60 seconds
3. Shows lag building up and then draining
4. Exports lag measurements to `lag_results.json` and `lag_results.csv`

**How to run:**
```bash
cd streaming-kafka/tests
python test_lag.py
```

**Expected output:**
- Initial lag: 0 or low
- Peak lag: 500-1000 (depends on consumption rate)
- Final lag: 0 (consumers catch up)

**Key Learning:**
- Lag indicates backlog in processing
- Kafka buffers messages while consumers catch up
- Multiple consumer groups process independently
- Consumers eventually catch up if consumption > production on average

### 3. Replay Test (`test_replay.py`)

Tests Kafka's event replay capability by resetting consumer offset.

**What it does:**
1. Produces 1,000 events
2. Waits for analytics consumer to process
3. Captures metrics: `metrics_before_replay.json`
4. Stops analytics consumer
5. Resets consumer offset to earliest
6. Restarts analytics consumer
7. Waits for reprocessing
8. Captures metrics: `metrics_after_replay.json`
9. Compares metrics (should be identical)

**How to run:**
```bash
cd streaming-kafka/tests
python test_replay.py
```

**Expected output:**
- Metrics before and after replay should match
- Demonstrates deterministic event processing
- Shows Kafka's event sourcing capability

**To manually reset offset:**
```bash
./reset_offset.sh
```

Or use the Kafka command directly:
```bash
docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group analytics-group \
  --reset-offsets \
  --to-earliest \
  --topic order-events \
  --topic inventory-events \
  --execute
```

## Running All Tests

Run all tests in sequence:

```bash
cd streaming-kafka/tests
python produce_10k.py
python test_lag.py
python test_replay.py
```

## Monitoring Tools

### Check Topics
```bash
docker exec streaming_kafka kafka-topics \
  --list \
  --bootstrap-server localhost:9092
```

### Check Consumer Groups
```bash
docker exec streaming_kafka kafka-consumer-groups \
  --list \
  --bootstrap-server localhost:9092
```

### Check Consumer Lag
```bash
docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group analytics-group
```

Output example:
```
TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
order-events    0          1000            1000            0
order-events    1          1002            1002            0
order-events    2          998             998             0
```

### View Messages in Topic
```bash
docker exec streaming_kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic order-events \
  --from-beginning \
  --max-messages 10
```

### Check Topic Details
```bash
docker exec streaming_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic order-events
```

## Metrics Files

### Analytics Metrics (`metrics_output.json`)

Located in `streaming-kafka/analytics_output/metrics_output.json`

Example:
```json
{
  "timestamp": "2026-02-11T00:00:00.000000Z",
  "orders_per_minute": 45,
  "failure_rate_percent": 10.5,
  "success_rate_percent": 89.5,
  "total_orders": 1000,
  "failed_orders": 105,
  "reserved_orders": 895,
  "throughput_events_per_second": 125.5,
  "elapsed_seconds": 23.5
}
```

### Test Results

- `high_volume_results.json` - Throughput metrics from 10k test
- `lag_results.json` / `lag_results.csv` - Consumer lag measurements
- `replay_comparison.json` - Before/after replay metrics

## Interpreting Results

### High Volume Test
- **Good:** 1000+ events/second throughput
- **Shows:** Kafka can handle high volume
- **Benefit:** Horizontal scalability

### Lag Test
- **Good:** Lag increases then decreases to 0
- **Shows:** Backpressure handling
- **Benefit:** Natural flow control

### Replay Test
- **Good:** Metrics identical before/after replay
- **Shows:** Deterministic processing, event sourcing
- **Benefit:** Can rebuild state from events

## Troubleshooting

### High consumer lag
- Scale consumers: `docker-compose up --scale inventory_consumer=3`
- Check consumer performance
- Verify Kafka has enough resources

### Offset reset fails
- Ensure consumer is stopped first
- Check consumer group exists
- Verify topic names are correct

### Events not producing
- Check producer logs: `docker logs streaming_producer_order`
- Verify Kafka is healthy: `docker ps`
- Check Kafka logs: `docker logs streaming_kafka`

## Cleanup

Stop services:
```bash
cd ..
docker-compose down
```

Clean up volumes and data:
```bash
docker-compose down -v
```

Remove test output files:
```bash
rm *.json *.csv
```

## Key Concepts

### Consumer Groups
- Multiple consumers in same group = parallel processing
- Each partition consumed by one consumer in group
- Different groups process same events independently

### Offsets
- Tracks position in topic for each consumer
- Committed after successful processing
- Can be reset for replay

### Partitions
- Topics divided into partitions (3 in this setup)
- Enables parallel processing
- Messages with same key go to same partition

### Lag
- Difference between latest offset and consumer offset
- Indicates backlog
- Should trend toward 0 over time

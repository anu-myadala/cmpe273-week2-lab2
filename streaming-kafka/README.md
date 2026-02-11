# Streaming Architecture with Kafka

This implementation demonstrates a campus food ordering system using Apache Kafka for streaming event processing. Services communicate via Kafka topics, enabling high throughput, event replay, and multiple independent consumers.

## Architecture

```
┌──────────────┐
│    Client    │
└──────┬───────┘
       │ POST /order (202 Accepted)
       │ POST /orders/batch
       ▼
┌─────────────────────┐
│  Producer (Order)   │
│  - Accept orders    │
│  - Batch support    │
│  - Return 202       │
└──────┬──────────────┘
       │ produce
       ▼
┌──────────────────────────────────┐
│          Kafka Cluster           │
│  ┌─────────────────────────────┐ │
│  │  order-events (3 partitions)│ │
│  └─────────┬───────────────────┘ │
│            │                      │
│  ┌─────────▼───────────────────┐ │
│  │ inventory-events (3 parts)  │ │
│  └─────────────────────────────┘ │
└──────────┬───────────┬───────────┘
           │           │
    consume│           │consume
           ▼           ▼
┌──────────────┐  ┌─────────────────┐
│ Inventory    │  │  Analytics      │
│ Consumer     │  │  Consumer       │
│ - Reserve    │  │  - Metrics      │
│ - Publish    │  │  - Sliding win  │
│   result     │  │  - JSON export  │
└──────────────┘  └─────────────────┘

Consumer Groups:
- inventory-group (processes orders)
- analytics-group (computes metrics)
```

### Event Flow

1. Client sends order → Producer
2. Producer publishes OrderPlaced → Kafka (order-events topic)
3. Producer returns 202 immediately
4. InventoryConsumer reads from order-events
5. InventoryConsumer reserves inventory
6. InventoryConsumer publishes InventoryReserved/Failed → Kafka (inventory-events)
7. AnalyticsConsumer reads from both topics
8. AnalyticsConsumer computes real-time metrics
9. Metrics exported to JSON file

**Key Features:**
- Multiple consumers process same events independently
- Events persisted (7-day retention)
- Replay capability via offset management
- High throughput via partitioning

## Services

### Producer (OrderService) - Port 8201

REST API that accepts orders and publishes to Kafka.

**Endpoints:**
- `GET /health` - Health check
- `POST /order` - Single order
- `POST /orders/batch` - Batch orders (up to 1000)

**Single Order:**
```json
{
  "user_id": "string",
  "item": "string",
  "quantity": 1
}
```

**Batch Orders:**
```json
{
  "orders": [
    {"user_id": "user1", "item": "Burger", "quantity": 1},
    {"user_id": "user2", "item": "Pizza", "quantity": 2}
  ]
}
```

**Response (202):**
```json
{
  "order_id": "uuid",
  "status": "accepted",
  "message": "Order published to Kafka",
  "timestamp": "ISO-8601"
}
```

**Event Schema:**
```json
{
  "event_id": "uuid",
  "event_type": "OrderPlaced",
  "order_id": "uuid",
  "timestamp": "ISO-8601",
  "payload": {
    "user_id": "string",
    "item": "string",
    "quantity": 1
  }
}
```

### Inventory Consumer (inventory-group)

Background consumer that processes orders and updates inventory.

**Functionality:**
- Reads from: order-events topic
- Consumer group: inventory-group
- Processing: Reserve inventory (90% success)
- Publishes to: inventory-events topic
- Commit: Manual (after successful processing)

**Inventory Event Schema:**
```json
{
  "event_id": "uuid",
  "event_type": "InventoryReserved|InventoryFailed",
  "order_id": "uuid",
  "timestamp": "ISO-8601",
  "success": true/false
}
```

### Analytics Consumer (analytics-group)

Background consumer that computes real-time metrics.

**Functionality:**
- Reads from: order-events, inventory-events
- Consumer group: analytics-group
- Metrics computed:
  - Orders per minute (sliding 1-minute window)
  - Failure rate percentage
  - Success rate percentage
  - Total counters
  - Throughput (events/second)
- Output: `metrics_output.json` (updated every 10s)

**Metrics Schema:**
```json
{
  "timestamp": "ISO-8601",
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

## Kafka Configuration

### Topics

1. **order-events**
   - Partitions: 3
   - Replication: 1
   - Retention: 7 days
   - Purpose: Order placement events

2. **inventory-events**
   - Partitions: 3
   - Replication: 1
   - Retention: 7 days
   - Purpose: Inventory reservation results

### Consumer Groups

1. **inventory-group**
   - Consumers: 1 (can scale)
   - Topics: order-events
   - Offset management: Manual commit

2. **analytics-group**
   - Consumers: 1 (can scale)
   - Topics: order-events, inventory-events
   - Offset management: Manual commit (enables replay)

### Partitioning

- Key: order_id
- Ensures: Orders with same ID go to same partition
- Benefit: Ordering within partition preserved

## Environment Variables

**Producer:**
- `PORT` - Service port (default: 8201)
- `KAFKA_BROKER` - Kafka broker address

**Consumers:**
- `KAFKA_BROKER` - Kafka broker address

## Building and Running

### Prerequisites
- Docker and Docker Compose
- 8GB RAM minimum (Kafka + Zookeeper)
- Ports 2181, 9092, 9093, 8201 available

### Start Services

```bash
cd streaming-kafka
docker-compose up --build
```

Services start order:
1. Zookeeper
2. Kafka (waits for Zookeeper)
3. Topic creation
4. Producer, Consumers

**Wait time:** ~60 seconds for Kafka to fully initialize

### Verify Services

```bash
# Check producer
curl http://localhost:8201/health

# Check topics
docker exec streaming_kafka kafka-topics \
  --list --bootstrap-server localhost:9092

# Check consumer groups
docker exec streaming_kafka kafka-consumer-groups \
  --list --bootstrap-server localhost:9092
```

### Create Orders

Single order:
```bash
curl -X POST http://localhost:8201/order \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "item": "Burger", "quantity": 2}'
```

Batch orders:
```bash
curl -X POST http://localhost:8201/orders/batch \
  -H "Content-Type: application/json" \
  -d '{
    "orders": [
      {"user_id": "user1", "item": "Burger", "quantity": 1},
      {"user_id": "user2", "item": "Pizza", "quantity": 2},
      {"user_id": "user3", "item": "Salad", "quantity": 1}
    ]
  }'
```

### Monitor Processing

```bash
# Watch inventory consumer
docker logs -f streaming_inventory_consumer

# Watch analytics consumer
docker logs -f streaming_analytics_consumer

# View metrics
cat analytics_output/metrics_output.json
```

### Check Consumer Lag

```bash
docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group analytics-group
```

## Running Tests

See [tests/README.md](tests/README.md) for detailed test instructions.

Quick start:

```bash
pip install requests

cd tests
python produce_10k.py       # High volume test
python test_lag.py           # Consumer lag test
python test_replay.py        # Replay test
```

## Offset Management and Replay

### Check Current Offsets

```bash
docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group analytics-group
```

### Reset to Earliest (Replay All)

```bash
cd tests
./reset_offset.sh
```

Or manually:
```bash
docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group analytics-group \
  --reset-offsets --to-earliest \
  --topic order-events --topic inventory-events \
  --execute
```

### Reset to Latest (Skip to Now)

```bash
docker exec streaming_kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group analytics-group \
  --reset-offsets --to-latest \
  --topic order-events \
  --execute
```

## Stopping Services

```bash
docker-compose down
```

Clean up all data:
```bash
docker-compose down -v
```

## Key Characteristics

### Advantages ✓

1. **High Throughput** - 10,000+ events/second
2. **Horizontal Scalability** - Add more partitions/consumers
3. **Event Replay** - Reprocess historical events
4. **Multiple Consumers** - Independent processing
5. **Durability** - Events persisted to disk
6. **Ordering** - Preserved within partition
7. **Decoupling** - Producers/consumers independent

### Disadvantages ✗

1. **Complexity** - Kafka cluster management
2. **Infrastructure** - Requires Zookeeper + Kafka
3. **Memory** - Higher resource requirements
4. **Learning Curve** - Concepts: partitions, offsets, consumer groups
5. **Eventual Consistency** - Not ACID transactions
6. **Debugging** - Distributed tracing needed

## When to Use Streaming/Kafka

### ✓ Excellent For

1. **High Volume** - 10,000+ events/second
2. **Event Sourcing** - Build state from events
3. **Analytics** - Real-time metrics, dashboards
4. **Multiple Consumers** - Same events, different purposes
5. **Replay** - Reprocess historical data
6. **Audit Logs** - Immutable event stream
7. **Data Pipelines** - ETL, data integration

### ✗ Avoid When

1. **Low Volume** - < 100 events/second
2. **Simple CRUD** - Overhead not justified
3. **Request-Response** - Need immediate result
4. **Small Team** - Can't manage Kafka cluster
5. **Limited Resources** - < 8GB RAM available

## Troubleshooting

### Kafka won't start
- Ensure 8GB RAM available
- Wait 60s for initialization
- Check logs: `docker logs streaming_kafka`

### Consumer lag growing
- Check consumer logs for errors
- Scale consumers: `docker-compose up --scale inventory_consumer=2`
- Verify sufficient partitions

### Events not processing
- Check consumer is running: `docker ps`
- Verify topic exists: `kafka-topics --list`
- Check consumer group: `kafka-consumer-groups --describe`

### Offset reset fails
- Stop consumer first: `docker stop streaming_analytics_consumer`
- Run reset command
- Start consumer: `docker start streaming_analytics_consumer`

## Comparison with Other Models

See main README.md for detailed comparison table.

**Quick Summary:**
- **vs Sync REST**: 135x lower client latency, better scalability
- **vs Async RabbitMQ**: Higher throughput, replay capability, more complex

## Further Reading

- Kafka documentation: https://kafka.apache.org/documentation/
- Compare with sync-rest/RESULTS.md and async-rabbitmq/RESULTS.md
- Confluent Kafka Python: https://docs.confluent.io/kafka-clients/python/
